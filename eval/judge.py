"""LLM-as-judge scoring of public-split results against gold answers.

  python -m eval.judge            -> adds `correct` (bool), `grounded` (cited a gold doc) to results/public_*.jsonl
Correctness: PASS/FAIL by gpt-4o-mini comparing predicted vs gold (numeric/name tolerant).
Completeness: for multi-part gold answers, fraction of gold items matched (single-answer => same as correct).
Grounding: fraction of gold_doc_ids that the pipeline cited or retrieved.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import chat  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
QDIR = ROOT.parent / "hackathon-resources" / "questions"

PROMPT = """You grade a question-answering system.
Question: {q}
Gold answer(s): {gold}
System answer: {pred}

Reply JSON: {{"correct": true|false, "items_matched": <int number of gold answer items the system answer contains>}}.
Be strict about numbers and names (minor spelling/diacritic/format differences are fine; extra correct detail is fine).
A hedged or empty answer is incorrect."""


def judge(rec, gold):
    try:
        r = chat([{"role": "user", "content": PROMPT.format(q=rec["question"], gold=gold["answer"], pred=rec.get("answer") or "(empty)")}],
                 response_format={"type": "json_object"}, max_tokens=60)
        j = json.loads(r.choices[0].message.content)
        correct, matched = bool(j.get("correct")), int(j.get("items_matched", 0))
    except Exception:
        correct, matched = False, 0
    gold_docs = set(gold.get("gold_doc_ids", []))
    cited = set(rec.get("citations", []))
    rec["correct"] = correct
    rec["completeness"] = (min(matched, len(gold["answer"])) / len(gold["answer"])) if gold["answer"] else float(correct)
    rec["grounding"] = (len(gold_docs & cited) / len(gold_docs)) if gold_docs else None
    return rec


def main():
    gold = {}
    for l in open(QDIR / "eval_public.jsonl", encoding="utf-8"):
        g = json.loads(l)
        gold[g["qid"]] = g
    for path in sorted(RESULTS.glob("public_*.jsonl")):
        recs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        todo = [r for r in recs if "correct" not in r]
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda r: judge(r, gold[r["qid"]]), todo))
        with open(path, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        acc = sum(r["correct"] for r in recs) / max(1, len(recs))
        print(f"{path.name}: {len(recs)} recs, accuracy {acc:.1%}")


if __name__ == "__main__":
    main()
