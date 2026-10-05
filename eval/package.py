"""Combine results/hidden_*.jsonl into the submission file for the 50 hidden questions.

  python -m eval.package   ->  submission/hidden_outputs.json
Per question and pipeline: answer, citations, token breakdown, latency, and (for agentic) the full trace.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP = ("answer", "citations", "context_tokens", "llm_input_tokens", "llm_output_tokens", "total_tokens", "embed_tokens",
        "llm_calls", "seconds", "num_chunks", "steps", "tool_calls", "tools_used", "agents_used", "strategy_changes",
        "stop_reason", "route", "trace", "error")


def main():
    out = {}
    for pipe in ("rag", "graphrag", "agentic", "adaptive"):
        f = ROOT / "results" / f"hidden_{pipe}.jsonl"
        if not f.exists():
            continue
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            q = out.setdefault(r["qid"], {"qid": r["qid"], "question": r["question"], "qtype": r.get("qtype"), "pipelines": {}})
            q["pipelines"][pipe] = {k: r[k] for k in KEEP if k in r}
    dest = ROOT / "submission"
    dest.mkdir(exist_ok=True)
    rows = [out[k] for k in sorted(out)]
    (dest / "hidden_outputs.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    n_by = {p: sum(1 for r in rows if p in r["pipelines"]) for p in ("rag", "graphrag", "agentic", "adaptive")}
    print(f"wrote submission/hidden_outputs.json: {len(rows)} questions, per pipeline {n_by}")
    errs = [(r["qid"], p) for r in rows for p, v in r["pipelines"].items() if v.get("error")]
    print("pipeline errors:", errs or "none")


if __name__ == "__main__":
    main()
