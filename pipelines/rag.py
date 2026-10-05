"""Pipeline 1: vanilla RAG. Embed question -> top-k chunks -> one LLM call."""
from llm import chat, metering
from pipelines.common import ANSWER_RULES, Timer, count_tokens, extract_answer

K = 6


def run(question: str, tb) -> dict:
    with metering() as m, Timer() as t:
        hits = tb.vector_search(question, k=K)
        context = "\n\n".join(f"[{h['doc_id']}] {h['title']}\n{h['text']}" for h in hits)
        r = chat([{"role": "system", "content": ANSWER_RULES},
                  {"role": "user", "content": f"Evidence:\n{context}\n\nQuestion: {question}"}])
        text = r.choices[0].message.content
    return {
        "pipeline": "rag", "answer": extract_answer(text), "raw_answer": text,
        "citations": sorted({h["doc_id"] for h in hits}), "num_chunks": len(hits),
        "context_tokens": count_tokens(context), **m.as_dict(), "seconds": round(t.seconds, 2),
        "trace": [{"step": 1, "agent": "Retriever", "tool": "vector_search", "args": {"k": K},
                   "result_summary": [h["title"] for h in hits]}],
    }
