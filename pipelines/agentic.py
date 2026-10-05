"""Pipeline 3: Agentic GraphRAG.

An orchestrator LLM plans an investigation and picks its next action each turn (function calling) from
tools owned by specialised agents. State = the message history (question, tool results, evidence).
The loop ends when the orchestrator calls `finish`, or the step budget is exhausted (forced answer).
Every step is traced: agent, tool, args, result summary, seconds, tokens, and the stop reason.
"""
import json
import time

from llm import CHAT_MODEL, chat, metering
from pipelines.common import Timer, count_tokens

MAX_STEPS = 10
RESULT_CHAR_CAP = 3500

SYSTEM = """You are the orchestrator of an investigation over a corpus of Wikipedia articles, mostly Olympic events (1896-2022).
The corpus is the ONLY source of truth: never use outside knowledge, and answers must be supported by tool results.

Data model (TigerGraph): Event(doc_id, title, sport, event, games, year, season, venue, date_str, competitors, nations)
with MEDAL edges to athletes (gold/silver/bronze), PREV_EDITION to the same event at the previous Games, and
Games -PREV_GAMES-> previous Games of the same season. doc_id looks like Q12345. competitors/nations = -1 means unknown.
Games names look like "2016 Summer Olympics"; sport names like "Athletics", "Biathlon", "Alpine skiing".

Your tools belong to specialised agents:
- EntityLinker.link_entity: map words in the question to exact Sport/Games/Venue/Event names. Use it to get exact names before filtering.
- Aggregator.find_events: FILTER/COUNT/RANK events by sport, games, year, season, venue, competitors range. Use it for any
  "how many", "more than N", "highest/lowest/most" question: it scans ALL matching events, unlike similarity search.
- GraphTraverser.get_event: medalists + attributes of one event. (find_events(include_medals=true) returns medalists for many events at once.) previous_games / previous_edition: temporal hops
  ("held immediately before 2016" -> previous_games("2016 Summer Olympics")).
- Retriever.vector_search / get_chunks: similarity search and document text; use for descriptive questions or when the graph lacks the fact.
- EvidenceEvaluator.check_evidence: judge whether collected evidence suffices. Use only when unsure.
- finish: submit the final answer.

Recipes:
- Temporal ("at the Games held immediately before 2016"): previous_games -> find_events(games=<that Games>, sport=..., name_contains=<distinctive part of the event name>, include_medals=true). Do NOT use link_entity for this.
- "Event held at <venue> on <date> at <Games>": find_events(venue=..., date_contains=..., games=..., include_medals=true) in ONE call.
- Counting / thresholds / highest / lowest: find_events(sport, games, min_competitors / sort_by). The `count` field is exact.
Medal order: the first 'gold' listed is the winner; teams/pairs appear as one combined name.

Strategy: pick the cheapest path that is reliable. Simple lookups need 1-3 calls. Do NOT repeat identical calls. Verify counts by
reading returned rows if the answer depends on a threshold. If a call returns nothing, change strategy (different filter, different tool).
When you have enough evidence, call finish immediately. Final answer must be short (a name, number, or event title)."""

TOOLS = [
    {"type": "function", "function": {"name": "link_entity", "description": "EntityLinker: fuzzy-match text to Sport/Games/Venue/Event names in the graph.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "types": {"type": "array", "items": {"type": "string", "enum": ["Sport", "Games", "Venue", "Event"]}}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "find_events", "description": "Aggregator: filter/count/rank Event vertices in TigerGraph. Exact sport/games strings (use link_entity). Returns count and rows.",
        "parameters": {"type": "object", "properties": {
            "sport": {"type": "string"}, "games": {"type": "string", "description": "e.g. '2018 Winter Olympics'"},
            "year": {"type": "integer"}, "season": {"type": "string", "enum": ["Summer", "Winter"]}, "venue": {"type": "string"}, "date_contains": {"type": "string", "description": "e.g. '12 August 2008' or '3 to 4 August'"},
            "include_medals": {"type": "boolean", "description": "attach medalists to each returned event"},
            "min_competitors": {"type": "integer", "description": "strictly greater than"}, "max_competitors": {"type": "integer", "description": "strictly less than"},
            "name_contains": {"type": "string", "description": "substring of event title, case-insensitive"},
            "sort_by": {"type": "string", "enum": ["competitors", "nations", "year"]}, "descending": {"type": "boolean"},
            "limit": {"type": "integer"}, "count_only": {"type": "boolean"}}}}},
    {"type": "function", "function": {"name": "get_event", "description": "GraphTraverser: one event's attributes, medalists, previous edition.",
        "parameters": {"type": "object", "properties": {"doc_id": {"type": "string"}}, "required": ["doc_id"]}}},
    {"type": "function", "function": {"name": "previous_games", "description": "GraphTraverser: the Games edition immediately before the given one (same season).",
        "parameters": {"type": "object", "properties": {"games": {"type": "string"}}, "required": ["games"]}}},
    {"type": "function", "function": {"name": "vector_search", "description": "Retriever: similarity search over document chunks.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_chunks", "description": "Retriever: text of a document by doc_id.",
        "parameters": {"type": "object", "properties": {"doc_id": {"type": "string"}}, "required": ["doc_id"]}}},
    {"type": "function", "function": {"name": "check_evidence", "description": "EvidenceEvaluator: given a summary of evidence so far, says if it suffices and what is missing.",
        "parameters": {"type": "object", "properties": {"evidence_summary": {"type": "string"}}, "required": ["evidence_summary"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Submit the final answer.",
        "parameters": {"type": "object", "properties": {"answer": {"type": "string"}, "justification": {"type": "string"},
                       "doc_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["answer", "doc_ids"]}}},
]
AGENT_OF = {"link_entity": "EntityLinker", "find_events": "Aggregator", "get_event": "GraphTraverser",
            "previous_games": "GraphTraverser", "vector_search": "Retriever", "get_chunks": "Retriever",
            "check_evidence": "EvidenceEvaluator", "finish": "Orchestrator"}


def _execute(tb, name, args, question):
    if name == "link_entity":
        return tb.link_entity(args["text"], types=tuple(args.get("types") or ("Sport", "Games", "Venue", "Event")))
    if name == "find_events":
        return tb.find_events(**{k: v for k, v in args.items()})
    if name == "get_event":
        return tb.get_event(args["doc_id"])
    if name == "previous_games":
        return tb.previous_games(args["games"])
    if name == "vector_search":
        hits = tb.vector_search(args["query"], k=int(args.get("k") or 4))
        return [{"doc_id": h["doc_id"], "title": h["title"], "text": h["text"][:1200]} for h in hits]
    if name == "get_chunks":
        return tb.get_chunks(args["doc_id"], max_chars=2500)
    if name == "check_evidence":
        r = chat([{"role": "system", "content": "You judge whether evidence suffices to answer a question. Reply JSON: {\"sufficient\": bool, \"missing\": str}."},
                  {"role": "user", "content": f"Question: {question}\nEvidence so far:\n{args['evidence_summary'][:3000]}"}],
                 response_format={"type": "json_object"}, max_tokens=150)
        return json.loads(r.choices[0].message.content)
    raise ValueError(f"unknown tool {name}")


def _summarize(result):
    if isinstance(result, dict):
        if "count" in result:
            return {"count": result["count"], "rows": len(result.get("events", []))}
        if "error" in result:
            return result
        return {"keys": list(result)[:6]}
    if isinstance(result, list):
        return {"items": len(result)}
    return {"chars": len(str(result))}


def _is_empty(result):
    return (isinstance(result, dict) and (result.get("count") == 0 or "error" in result)) or result in ([], "", None) \
        or (isinstance(result, dict) and result.get("sufficient") is False)


def run(question: str, tb) -> dict:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    seen_calls = set()
    trace, cited, context_tokens, answer, stop_reason = [], set(), 0, None, "step_budget"
    strategy_changes, last_tool, last_poor = 0, None, False
    with metering() as m, Timer() as t:
        for step in range(1, MAX_STEPS + 1):
            before_in, before_out = m.input_tokens, m.output_tokens
            r = chat(messages, tools=TOOLS, max_tokens=500)
            msg = r.choices[0].message
            messages.append(msg)
            if not msg.tool_calls:  # plain text -> treat as final
                answer, stop_reason = (msg.content or "").strip(), "answered_without_finish"
                break
            finished = False
            for call in msg.tool_calls:
                name, t0 = call.function.name, time.time()
                try:
                    args = json.loads(call.function.arguments or "{}")
                    if name == "finish":
                        answer = args.get("answer", "")
                        cited.update(args.get("doc_ids", []))
                        out, finished = {"ok": True}, True
                    else:
                        sig = (name, json.dumps(args, sort_keys=True))
                        if sig in seen_calls:  # guard against loops: nudge the orchestrator to change strategy
                            out = {"error": "duplicate call: you already ran this exact call. Use a different tool or different parameters, or finish."}
                        else:
                            seen_calls.add(sig)
                            out = _execute(tb, name, args, question)
                except Exception as e:  # tool errors are fed back so the agent can recover
                    args, out = locals().get("args", {}), {"error": str(e)[:300]}
                payload = json.dumps(out, ensure_ascii=False)[:RESULT_CHAR_CAP]
                context_tokens += count_tokens(payload)
                if name != "finish":
                    if last_poor and last_tool and name != last_tool:
                        strategy_changes += 1
                    last_tool, last_poor = name, _is_empty(out)
                    for key in ("doc_id",):
                        if isinstance(out, dict) and key in out:
                            cited.add(out[key])
                    if isinstance(out, dict) and "events" in out:
                        cited.update(e["doc_id"] for e in out["events"][:10])
                trace.append({"step": step, "agent": AGENT_OF.get(name, "?"), "tool": name, "args": args,
                              "result_summary": _summarize(out), "seconds": round(time.time() - t0, 2),
                              "orchestrator_tokens": {"in": m.input_tokens - before_in, "out": m.output_tokens - before_out}})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": payload})
            if finished:
                stop_reason = "finish_called"
                break
        if answer is None:  # budget exhausted: force a final answer
            messages.append({"role": "user", "content": "Step budget exhausted. Give your best final answer now as plain text 'ANSWER: ...'."})
            r = chat(messages, max_tokens=200)
            answer = (r.choices[0].message.content or "").replace("ANSWER:", "").strip()
            stop_reason = "step_budget_forced_answer"
    used = [x["tool"] for x in trace]
    return {
        "pipeline": "agentic", "answer": answer, "raw_answer": answer,
        "citations": sorted(c for c in cited if c), "num_chunks": sum(1 for x in used if x in ("vector_search", "get_chunks")),
        "context_tokens": context_tokens, **m.as_dict(), "seconds": round(t.seconds, 2),
        "steps": len({x["step"] for x in trace}), "tool_calls": len(trace), "tools_used": sorted(set(used)),
        "agents_used": sorted({x["agent"] for x in trace}), "strategy_changes": strategy_changes,
        "stop_reason": stop_reason, "trace": trace,
    }
