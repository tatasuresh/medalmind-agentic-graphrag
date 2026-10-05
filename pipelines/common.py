import time

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except Exception:  # offline fallback
    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)

ANSWER_RULES = (
    "You answer questions using ONLY the provided evidence from a corpus of Wikipedia articles "
    "(mostly Olympic events). Never use outside knowledge. Give the shortest complete answer "
    "(a name, a number, or an event title) on the first line as 'ANSWER: ...', then one sentence "
    "of justification citing the doc ids you used like [Q12345]. If the evidence is insufficient, "
    "give your best supported answer and say what is missing."
)


def extract_answer(text: str) -> str:
    for line in text.splitlines():
        if line.strip().upper().startswith("ANSWER:"):
            return line.split(":", 1)[1].strip()
    return text.strip().splitlines()[0] if text.strip() else ""


class Timer:
    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *a):
        self.seconds = time.time() - self.t0
