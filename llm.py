"""Shared OpenAI wrapper. Every call is metered (tokens, latency) into a per-question Meter."""
import os
import threading
import time
from contextlib import contextmanager

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
_client = OpenAI()


class Meter:
    """Accumulates LLM usage for one question/pipeline run."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.embed_tokens = 0
        self.llm_calls = 0
        self.llm_seconds = 0.0

    @property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens

    def as_dict(self):
        return {"llm_input_tokens": self.input_tokens, "llm_output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens, "embed_tokens": self.embed_tokens,
                "llm_calls": self.llm_calls, "llm_seconds": round(self.llm_seconds, 3)}


_local = threading.local()  # per-thread meter stack: eval runs questions in parallel threads


def _stack():
    if not hasattr(_local, "s"):
        _local.s = []
    return _local.s


@contextmanager
def metering():
    m = Meter()
    _stack().append(m)
    try:
        yield m
    finally:
        _stack().pop()


def chat(messages, model=None, temperature=0.0, max_tokens=700, tools=None, response_format=None):
    kw = dict(model=model or CHAT_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if tools:
        kw["tools"] = tools
    if response_format:
        kw["response_format"] = response_format
    for attempt in range(4):
        try:
            t0 = time.time()
            r = _client.chat.completions.create(**kw)
            dt = time.time() - t0
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    if _stack():
        m = _stack()[-1]
        m.input_tokens += r.usage.prompt_tokens
        m.output_tokens += r.usage.completion_tokens
        m.llm_calls += 1
        m.llm_seconds += dt
    return r


def embed(texts, model=None):
    if isinstance(texts, str):
        texts = [texts]
    texts = [t[:24000] for t in texts]
    for attempt in range(10):
        try:
            r = _client.embeddings.create(model=model or EMBED_MODEL, input=texts)
            break
        except Exception:
            if attempt == 9:
                raise
            time.sleep(min(3 * (attempt + 1), 20))  # rate limits (TPM) clear within seconds
    if _stack():
        _stack()[-1].embed_tokens += r.usage.total_tokens
    return [d.embedding for d in r.data]
