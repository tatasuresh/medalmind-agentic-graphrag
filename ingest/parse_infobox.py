"""Deterministic parsing of corpus documents into structured records.

Olympic event pages carry an `[Infobox Olympic event]` block with typed fields;
we parse it with regexes (no LLM), derive sport/games from the title, and split
the body into chunks for embedding.
"""
import json
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "hackathon-resources" / "corpus" / "corpus.jsonl"
TITLE_RE = re.compile(r"^(?P<sport>.+?) at the (?P<games>\d{4} (?:Summer|Winter) Olympics)")
FIELD_RE = re.compile(r"^  (\w+): ?(.*)$", re.M)


def load_docs(path: Path = CORPUS):
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def split_infobox(text: str):
    """Return (infobox_name, fields, body). Only the first infobox block is parsed into fields."""
    head, _, body = text.partition("\n\n")
    m = re.match(r"\[(Infobox [^\]]+)\]", head)
    name = m.group(1) if m else None
    fields = {k: v.strip() for k, v in FIELD_RE.findall(head)} if name else {}
    return name, fields, (body if name else text)


def to_int(s):
    if s is None:
        return None
    m = re.search(r"\d[\d,]*", s)
    return int(m.group(0).replace(",", "")) if m else None


def parse_olympic_event(doc: dict):
    name, f, body = split_infobox(doc["text"])
    if name != "Infobox Olympic event":
        return None
    tm = TITLE_RE.match(doc["title"])
    games = tm.group("games") if tm else f.get("games", "")
    year = int(games[:4]) if games[:4].isdigit() else None
    season = "Summer" if "Summer" in games else "Winter" if "Winter" in games else ""
    medals = []
    for medal in ("gold", "silver", "bronze"):
        for suffix in ("", "2", "3"):
            ath = f.get(medal + suffix)
            if ath:
                medals.append({"medal": medal, "athlete": ath, "noc": f.get(f"{medal}NOC{suffix}", "")})
    return {
        "doc_id": doc["doc_id"],
        "title": doc["title"],
        "sport": tm.group("sport") if tm else "",
        "games": games,
        "year": year,
        "season": season,
        "event": f.get("event", ""),
        "venue": f.get("venue", ""),
        "date": f.get("date") or f.get("dates") or "",
        "competitors": to_int(f.get("competitors")),
        "nations": to_int(f.get("nations")),
        "medals": medals,
    }


def chunk_text(text: str, max_chars: int = 1800, overlap: int = 200):
    """Paragraph-aware chunking; infobox kept in the first chunk."""
    paras = [p for p in text.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > max_chars:
            chunks.append(cur)
            cur = cur[-overlap:] + "\n\n" + p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur:
        chunks.append(cur)
    return chunks


if __name__ == "__main__":
    n = 0
    for d in load_docs():
        r = parse_olympic_event(d)
        if r:
            n += 1
            if n <= 2:
                print(json.dumps(r, ensure_ascii=False, indent=1))
    print("olympic events parsed:", n)
