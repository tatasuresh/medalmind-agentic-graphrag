"""Retrieval / graph tools shared by the pipelines.

Each tool is owned by a named specialised agent so traces can report which agent acted:
  EntityLinker      -> link_entity
  Retriever         -> vector_search, get_chunks
  GraphTraverser    -> get_event, previous_games, previous_edition
  Aggregator        -> find_events (filter / count / rank over typed Event attributes in TigerGraph)
  EvidenceEvaluator -> check_evidence (LLM, in agent pipeline)
"""
import difflib
import json
import re
from pathlib import Path

import numpy as np

import tg
from llm import embed

RESULTS = Path(__file__).resolve().parents[1] / "results"


_STOP = {"to", "and", "the", "at", "of", "on", "in"}


def _toks(s):
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in _STOP}


def _squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


class Toolbox:
    def __init__(self):
        self.chunks = [json.loads(l) for l in open(RESULTS / "chunks.jsonl", encoding="utf-8")]
        self.emb = np.load(RESULTS / "chunk_emb.npy")
        self._names = None

    # ------------------------------------------------------------------ Retriever
    def vector_search(self, query: str, k: int = 5):
        q = np.asarray(embed(query)[0], dtype=np.float32)
        q /= np.linalg.norm(q) + 1e-9
        idx = np.argsort(-(self.emb @ q))[:k]
        return [{**self.chunks[i], "score": float(self.emb[i] @ q)} for i in idx]

    def get_chunks(self, doc_id: str, max_chars: int = 3000):
        out, n = [], 0
        for c in self.chunks:
            if c["doc_id"] == doc_id:
                out.append(c["text"])
                n += len(c["text"])
                if n > max_chars:
                    break
        return "\n".join(out)[:max_chars]

    # ---------------------------------------------------------------- EntityLinker
    def _load_names(self):
        if self._names is None:
            names = []
            for vt, key in (("Sport", "name"), ("Games", "name"), ("Venue", "name")):
                for v in tg.vertices(vt, limit=5000):
                    names.append((vt, v["v_id"], v["v_id"]))
            for v in tg.vertices("Event", limit=5000, select="title"):
                names.append(("Event", v["v_id"], v["attributes"]["title"]))
            self._names = names
        return self._names

    @staticmethod
    def _norm(s):
        return re.sub(r"[^a-z0-9 ]", " ", s.lower())

    def link_entity(self, text: str, types=("Sport", "Games", "Venue", "Event"), k: int = 5):
        t = self._norm(text)
        toks = set(t.split())
        scored = []
        for vt, vid, label in self._load_names():
            if vt not in types:
                continue
            ln = self._norm(label)
            ltoks = set(ln.split())
            if not ltoks:
                continue
            substr = 1.0 if ln.strip() and ln.strip() in t else 0.0
            overlap = len(toks & ltoks) / len(ltoks)
            ratio = difflib.SequenceMatcher(None, t, ln).ratio() if len(t) < 120 else 0
            scored.append((max(substr, 0.9 * overlap, ratio), vt, vid, label))
        scored.sort(key=lambda x: -x[0])
        return [{"type": vt, "id": vid, "label": label, "score": round(s, 2)} for s, vt, vid, label in scored[:k]]

    # ------------------------------------------------------------------ Aggregator
    def find_events(self, sport=None, games=None, year=None, season=None, min_competitors=None,
                    max_competitors=None, venue=None, date_contains=None, name_contains=None, sort_by=None,
                    descending=True, limit=40, count_only=False, include_medals=False):
        # TigerGraph's REST filter returns nothing for string values containing spaces, so numeric/single-word
        # conditions are pushed down to the database and spaced strings (sport, games, venue) are matched here.
        m = re.match(r"\s*(\d{4})\s+(Summer|Winter)", games or "")
        if m:
            year, season = year or int(m.group(1)), season or m.group(2)
        conds = []
        if year:
            conds.append(f"year={int(year)}")
        if season:
            conds.append(f'season="{season}"')
        if min_competitors is not None:
            conds.append(f"competitors>{int(min_competitors)}")
        if max_competitors is not None:
            conds.append(f"competitors<{int(max_competitors)}")
        narrowed = False
        res = tg.vertices("Event", filter=",".join(conds) or None, limit=5000)
        rows = [{**r["attributes"], "doc_id": r["v_id"]} for r in res]
        if sport:
            rows = [r for r in rows if r["sport"].lower() == sport.lower()]
        if venue:  # whitespace/punctuation-insensitive: corpus has typos like "TechnologyUniversity"
            rows = [r for r in rows if _squash(venue) in _squash(r["venue"]) or _squash(r["venue"]) in _squash(venue)]
        if date_contains:  # token-subset match, so "August 12, 2008" matches "12 August 2008" and "3 to 4 August"
            want = _toks(date_contains)
            rows = [r for r in rows if want and want <= (_toks(r["date_str"]) | {str(r["year"])})]
            # Several events can share a venue and overlap a date (multi-day events). If some events were recorded with exactly
            # this date (and venue), they are the unambiguous match, so narrow to them.
            exact = [r for r in rows if _toks(r["date_str"]) | {str(r["year"])} == want | {str(r["year"])}
                     and (not venue or _squash(venue) == _squash(r["venue"]))]
            if exact and len(exact) < len(rows):
                rows, narrowed = exact, True
        if name_contains:
            nc = name_contains.lower()
            rows = [r for r in rows if nc in r["title"].lower()]
        if sort_by in ("competitors", "nations", "year"):
            rows = [r for r in rows if r[sort_by] is not None and r[sort_by] >= 0]
            rows.sort(key=lambda r: r[sort_by], reverse=descending)
        compact = [{"doc_id": r["doc_id"], "title": r["title"], "competitors": r["competitors"],
                    "nations": r["nations"], "date": r["date_str"], "venue": r["venue"]} for r in rows]
        out = {"count": len(rows)}
        if narrowed:
            out["note_exact"] = "narrowed to events whose recorded date and venue match exactly"
        if not count_only:
            out["events"] = compact[:limit]
            if include_medals:  # saves one get_event round trip per event
                for e in out["events"][:12]:
                    e["medals"] = [f"{m['medal']}: {m['athlete']}" for m in self.get_event(e["doc_id"]).get("medals", [])]
            if len(compact) > limit:
                out["note"] = f"showing {limit} of {len(compact)}"
        return out

    # -------------------------------------------------------------- GraphTraverser
    def get_event(self, doc_id: str):
        v = tg.vertices("Event", vid=doc_id)
        if not v:
            return {"error": f"no event {doc_id}"}
        a = v[0]["attributes"]
        medals = [{"medal": e["attributes"]["medal"], "athlete": e["to_id"], "noc": e["attributes"]["noc"]}
                  for e in tg.edges("Event", doc_id, "MEDAL", "Athlete")]
        order = {"gold": 0, "silver": 1, "bronze": 2}
        medals.sort(key=lambda m: order.get(m["medal"], 3))
        prev = [e["to_id"] for e in tg.edges("Event", doc_id, "PREV_EDITION", "Event")]
        return {"doc_id": doc_id, **a, "medals": medals, "previous_edition_doc_ids": prev}

    def previous_games(self, games: str):
        return [e["to_id"] for e in tg.edges("Games", games, "PREV_GAMES", "Games")]

    def previous_edition(self, doc_id: str):
        return [e["to_id"] for e in tg.edges("Event", doc_id, "PREV_EDITION", "Event")]
