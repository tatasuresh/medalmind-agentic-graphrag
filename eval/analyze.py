"""Quick breakdown of public-split results by question type (accuracy, tokens, agent behaviour)."""
import collections
import json
import statistics
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
load = lambda p: [json.loads(l) for l in open(R / f"public_{p}.jsonl", encoding="utf-8")]
for p in ("rag", "graphrag", "agentic"):
    recs = load(p)
    by = collections.defaultdict(list)
    for r in recs:
        by[r["qtype"]].append(r)
    print(p.upper(), "errors:", sum(1 for r in recs if r.get("error")))
    for t, v in sorted(by.items()):
        print(f"  {t:12} acc {sum(x['correct'] for x in v)}/{len(v)}  avg tokens {round(statistics.mean(x['total_tokens'] for x in v))}")
a = load("agentic")
print("agent avg steps", round(statistics.mean(r["steps"] for r in a), 2), "avg tool calls", round(statistics.mean(r["tool_calls"] for r in a), 2))
print("stop reasons", dict(collections.Counter(r["stop_reason"] for r in a)), "strategy changes", sum(r["strategy_changes"] for r in a))
by = collections.defaultdict(list)
for r in a:
    by[r["qtype"]].append(r["steps"])
print("agent avg steps by type", {t: round(statistics.mean(v), 2) for t, v in sorted(by.items())})
print("agent wrong:", [(r["qid"], r["qtype"], r["answer"][:45]) for r in a if not r["correct"]])
