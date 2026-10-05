"""Pipeline 2: GraphRAG with a FIXED retrieval recipe (no planning):
  vector seeds -> entity linking -> one-hop graph expansion -> one LLM call.

Graph context = structured facts pulled from TigerGraph for (a) the linked Sport/Games entities
(compact event table) and (b) the seed events (medalists + previous edition).
"""
import re

from llm import chat, metering
from pipelines.common import ANSWER_RULES, Timer, count_tokens, extract_answer

K_SEEDS = 4
MAX_TABLE_ROWS = 60


def _games_from_text(q: str):
    m = re.search(r"\b(19|20)\d{2}\b", q)
    season = "Winter" if re.search(r"winter", q, re.I) else "Summer" if re.search(r"summer", q, re.I) else None
    if m and season:
        return f"{m.group(0)} {season} Olympics"
    return None


def run(question: str, tb) -> dict:
    trace = []
    with metering() as m, Timer() as t:
        seeds = tb.vector_search(question, k=K_SEEDS)
        trace.append({"step": 1, "agent": "Retriever", "tool": "vector_search", "args": {"k": K_SEEDS},
                      "result_summary": [h["title"] for h in seeds]})
        links = tb.link_entity(question, types=("Sport", "Games"), k=6)
        sport = next((l["id"] for l in links if l["type"] == "Sport" and l["score"] >= 0.9), None)
        games = _games_from_text(question) or next((l["id"] for l in links if l["type"] == "Games" and l["score"] >= 0.9), None)
        trace.append({"step": 2, "agent": "EntityLinker", "tool": "link_entity", "args": {},
                      "result_summary": {"sport": sport, "games": games}})

        graph_facts, cited = [], {h["doc_id"] for h in seeds}
        if sport or games:
            res = tb.find_events(sport=sport, games=games, limit=MAX_TABLE_ROWS)
            rows = [f"- [{e['doc_id']}] {e['title']} | competitors={e['competitors']} | nations={e['nations']} | venue={e['venue']} | date={e['date']}"
                    for e in res["events"]]
            graph_facts.append(f"Events matching sport={sport} games={games} ({res['count']} total, showing {len(rows)}):\n" + "\n".join(rows))
            cited.update(e["doc_id"] for e in res["events"])
            trace.append({"step": 3, "agent": "GraphTraverser", "tool": "find_events", "args": {"sport": sport, "games": games},
                          "result_summary": {"count": res["count"]}})
        for h in seeds:
            ev = tb.get_event(h["doc_id"])
            if "error" in ev:
                continue
            med = "; ".join(f"{x['medal']}: {x['athlete']} ({x['noc']})" for x in ev["medals"])
            graph_facts.append(f"[{ev['doc_id']}] {ev['title']} | games={ev['games']} | venue={ev['venue']} | date={ev['date_str']} | "
                               f"competitors={ev['competitors']} | nations={ev['nations']} | medals: {med}")
        trace.append({"step": 4, "agent": "GraphTraverser", "tool": "get_event(seeds)", "args": {},
                      "result_summary": {"seed_events": len(seeds)}})

        text_ctx = "\n\n".join(f"[{h['doc_id']}] {h['title']}\n{h['text']}" for h in seeds)
        context = "GRAPH FACTS:\n" + "\n".join(graph_facts) + "\n\nTEXT PASSAGES:\n" + text_ctx
        r = chat([{"role": "system", "content": ANSWER_RULES},
                  {"role": "user", "content": f"Evidence:\n{context}\n\nQuestion: {question}"}])
        text = r.choices[0].message.content
    return {
        "pipeline": "graphrag", "answer": extract_answer(text), "raw_answer": text,
        "citations": sorted(cited), "num_chunks": len(seeds), "context_tokens": count_tokens(context),
        **m.as_dict(), "seconds": round(t.seconds, 2), "trace": trace,
    }
