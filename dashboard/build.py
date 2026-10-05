"""Build a self-contained metrics dashboard (dashboard/index.html) from results/public_*.jsonl.

  python -m dashboard.build
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PIPES = ["rag", "graphrag", "agentic", "adaptive"]
LABEL = {"rag": "RAG", "graphrag": "GraphRAG", "agentic": "Agentic GraphRAG", "adaptive": "Adaptive router"}


def load(split):
    out = {}
    for p in PIPES:
        f = RESULTS / f"{split}_{p}.jsonl"
        out[p] = {r["qid"]: r for r in (json.loads(l) for l in open(f, encoding="utf-8") if l.strip())} if f.exists() else {}
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def summarize(recs):
    return {
        "n": len(recs),
        "accuracy": mean([1.0 if r.get("correct") else 0.0 for r in recs if "correct" in r]),
        "completeness": mean([r.get("completeness") for r in recs]),
        "grounding": mean([r.get("grounding") for r in recs]),
        "avg_total_tokens": mean([r.get("total_tokens") for r in recs]),
        "avg_context_tokens": mean([r.get("context_tokens") for r in recs]),
        "avg_input_tokens": mean([r.get("llm_input_tokens") for r in recs]),
        "avg_output_tokens": mean([r.get("llm_output_tokens") for r in recs]),
        "avg_seconds": mean([r.get("seconds") for r in recs]),
        "avg_llm_calls": mean([r.get("llm_calls") for r in recs]),
        "avg_steps": mean([r.get("steps") for r in recs if r.get("steps")]),
        "avg_chunks": mean([r.get("num_chunks") for r in recs]),
        "errors": sum(1 for r in recs if r.get("error")),
    }


def main():
    data = load("public")
    summary, by_type = {}, {}
    for p in PIPES:
        recs = list(data[p].values())
        if not recs:
            continue
        summary[p] = summarize(recs)
        types = sorted({r.get("qtype") for r in recs})
        by_type[p] = {t: summarize([r for r in recs if r.get("qtype") == t]) for t in types}
    qids = sorted({q for p in PIPES for q in data[p]})
    questions = []
    for q in qids:
        row = {"qid": q}
        for p in PIPES:
            r = data[p].get(q)
            if r:
                row.setdefault("question", r["question"])
                row.setdefault("qtype", r.get("qtype"))
                row[p] = {k: r.get(k) for k in ("answer", "correct", "total_tokens", "seconds", "citations", "steps", "tool_calls",
                                                "tools_used", "agents_used", "strategy_changes", "stop_reason", "trace", "grounding", "route")}
        questions.append(row)
    routes = {}
    for r in data["adaptive"].values():
        routes.setdefault(r.get("qtype"), {}).setdefault(r.get("route"), 0)
        routes[r.get("qtype")][r.get("route")] += 1
    payload = {"labels": LABEL, "routes": routes, "summary": summary, "by_type": by_type, "questions": questions}
    html = (Path(__file__).parent / "template.html").read_text(encoding="utf-8").replace(
        "/*DATA*/null", json.dumps(payload, ensure_ascii=False))
    out = Path(__file__).parent / "index.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out, "questions:", len(questions))
    for p in [x for x in PIPES if x in summary]:
        s = summary[p]
        print(f"{LABEL[p]:18} n={s['n']:3} acc={s['accuracy']} tokens={s['avg_total_tokens']} sec={s['avg_seconds']}")


if __name__ == "__main__":
    main()
