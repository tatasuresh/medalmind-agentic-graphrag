"""Run pipelines over a question file and write raw per-question outputs (answers, tokens, trace).

  python -m eval.run --split public --pipelines rag graphrag agentic [--n 15] [--judge]
  python -m eval.run --split hidden --pipelines rag graphrag agentic
Outputs: results/{split}_{pipeline}.jsonl  (resumable: already-answered qids are skipped)
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.graph_tools import Toolbox  # noqa: E402
from pipelines import adaptive, agentic, graphrag, rag  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QDIR = ROOT.parent / "hackathon-resources" / "questions"
RESULTS = ROOT / "results"
PIPES = {"rag": rag, "graphrag": graphrag, "agentic": agentic, "adaptive": adaptive}


def load_questions(split):
    return [json.loads(l) for l in open(QDIR / f"eval_{split}.jsonl", encoding="utf-8")]


def run_one(pipe, q, tb):
    try:
        out = PIPES[pipe].run(q["question"], tb)
    except Exception as e:
        out = {"pipeline": pipe, "answer": "", "error": f"{type(e).__name__}: {e}"[:400], "total_tokens": 0}
    return {"qid": q["qid"], "qtype": q.get("qtype"), "question": q["question"], **out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="public", choices=["public", "hidden"])
    ap.add_argument("--pipelines", nargs="+", default=["rag", "graphrag", "agentic"])
    ap.add_argument("--n", type=int, default=0, help="first N questions (0=all)")
    ap.add_argument("--qids", nargs="*", help="only these qids")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    qs = load_questions(a.split)
    if a.qids:
        qs = [q for q in qs if q["qid"] in a.qids]
    if a.n:
        # stratified-ish: round-robin over qtypes so small smoke runs cover every type
        by = {}
        for q in qs:
            by.setdefault(q.get("qtype"), []).append(q)
        qs, i = [], 0
        while len(qs) < a.n and any(by.values()):
            for lst in by.values():
                if lst and len(qs) < a.n:
                    qs.append(lst.pop(0))
    tb = Toolbox()
    RESULTS.mkdir(exist_ok=True)
    for pipe in a.pipelines:
        path = RESULTS / f"{a.split}_{pipe}.jsonl"
        done = set()
        if path.exists():
            done = {json.loads(l)["qid"] for l in open(path, encoding="utf-8") if l.strip()}
        todo = [q for q in qs if q["qid"] not in done]
        print(f"[{pipe}] {len(todo)} to run ({len(done)} cached)", flush=True)
        with ThreadPoolExecutor(a.workers) as ex, open(path, "a", encoding="utf-8") as f:
            for rec in ex.map(lambda q: run_one(pipe, q, tb), todo):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(f"  {rec['qid']} {rec.get('qtype')}: {str(rec.get('answer'))[:60]!r} tok={rec.get('total_tokens')} {rec.get('error','')}", flush=True)


if __name__ == "__main__":
    main()
