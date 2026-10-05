"""Pipeline 4 (innovation): Adaptive router, "use the agent only when it pays off".

A cheap classifier call reads the question and decides whether a single retrieval suffices:
  - 'simple'  : one fact about ONE named event/entity (look-up) -> plain RAG (1 LLM call)
  - 'complex' : counting/thresholds, ranking, multi-hop joins (venue/date -> event -> medalist), or temporal hops
                -> full Agentic GraphRAG
The classifier sees only the question text (no labels). Its own tokens are included in the totals.
"""
import json

from llm import chat, metering
from pipelines import agentic, rag

ROUTER_PROMPT = """Classify a question about Olympic events as 'simple' or 'complex'.
simple  = asks for ONE fact about ONE explicitly named event (e.g. "How many nations competed in Judo at the 2016 Summer Olympics - Women's 57 kg?", "Who won gold in X at the 2008 Games?" where the event is named in full).
complex = needs counting or comparing across MANY events ("how many events had more than N competitors", "which event had the highest..."),
          or identifies the event only indirectly (by venue/date, or "the Games immediately before/after Y"), or chains several lookups.
Reply JSON: {"route": "simple"|"complex"}"""


def run(question: str, tb) -> dict:
    with metering() as m:
        r = chat([{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": question}],
                 response_format={"type": "json_object"}, max_tokens=20)
        try:
            route = json.loads(r.choices[0].message.content).get("route", "complex")
        except Exception:
            route = "complex"
        router_in, router_out, router_calls = m.input_tokens, m.output_tokens, m.llm_calls
    res = (rag if route == "simple" else agentic).run(question, tb)
    res["pipeline"] = "adaptive"
    res["route"] = route
    res["llm_input_tokens"] += router_in
    res["llm_output_tokens"] += router_out
    res["total_tokens"] = res["llm_input_tokens"] + res["llm_output_tokens"]
    res["llm_calls"] += router_calls
    res["trace"] = [{"step": 0, "agent": "Router", "tool": "classify", "args": {}, "result_summary": {"route": route}}] + res["trace"]
    return res
