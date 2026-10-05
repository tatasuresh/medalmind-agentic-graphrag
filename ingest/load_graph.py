"""Load the corpus into TigerGraph and build the local chunk-embedding index.

Usage:  python -m ingest.load_graph [--skip-embed] [--skip-graph]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tg  # noqa: E402
from llm import embed  # noqa: E402
from ingest.parse_infobox import chunk_text, load_docs, parse_olympic_event, split_infobox  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results"
BATCH = 400


def flush(vs, es):
    tg.upsert(vs or None, es or None)


def build_graph():
    docs = list(load_docs())
    events = [e for e in (parse_olympic_event(d) for d in docs) if e]
    print(f"{len(docs)} docs, {len(events)} olympic events")

    # --- Doc + Chunk + HAS_CHUNK -------------------------------------------------------
    chunks_meta = []
    batch_v, batch_e = defaultdict(dict), {}
    n = 0
    for d in tqdm(docs, desc="docs/chunks"):
        name, _, _ = split_infobox(d["text"])
        batch_v["Doc"][d["doc_id"]] = {"title": d["title"], "doctype": name or "article"}
        for i, ch in enumerate(chunk_text(d["text"])):
            cid = f"{d['doc_id']}#{i}"
            batch_v["Chunk"][cid] = {"doc_id": d["doc_id"], "idx": i, "text": ch}
            batch_e.setdefault("Doc", {}).setdefault(d["doc_id"], {}).setdefault("HAS_CHUNK", {}).setdefault("Chunk", {})[cid] = {}
            chunks_meta.append({"chunk_id": cid, "doc_id": d["doc_id"], "title": d["title"], "idx": i, "text": ch})
        n += 1
        if n % 150 == 0:
            flush(batch_v, batch_e)
            batch_v, batch_e = defaultdict(dict), {}
    flush(batch_v, batch_e)
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks_meta:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(chunks_meta)} chunks")

    # --- Olympic entities ----------------------------------------------------------------
    games_seen = {}
    for e in events:
        games_seen[e["games"]] = {"year": e["year"] or 0, "season": e["season"]}
    # chronological chain per season -> PREV_GAMES
    by_season = defaultdict(list)
    for g, a in games_seen.items():
        by_season[a["season"]].append((a["year"], g))
    games_edges = {"Games": {}}
    for season, lst in by_season.items():
        lst.sort()
        for (_, prev), (_, cur) in zip(lst, lst[1:]):
            games_edges["Games"].setdefault(cur, {}).setdefault("PREV_GAMES", {}).setdefault("Games", {})[prev] = {}
    flush({"Games": {g: a for g, a in games_seen.items()}}, games_edges)

    # PREV_EDITION: same sport + event within the same season, previous year available
    key_map = defaultdict(list)
    for e in events:
        key_map[(e["sport"], e["season"], e["event"].strip().lower())].append(e)
    prev_edition = {}
    for lst in key_map.values():
        lst.sort(key=lambda x: x["year"] or 0)
        for p, c in zip(lst, lst[1:]):
            prev_edition[c["doc_id"]] = p["doc_id"]

    vs, es, n = defaultdict(dict), {}, 0
    for e in tqdm(events, desc="events"):
        did = e["doc_id"]
        vs["Event"][did] = {"title": e["title"], "sport": e["sport"], "event": e["event"], "games": e["games"],
                            "year": e["year"] or 0, "season": e["season"], "venue": e["venue"], "date_str": e["date"],
                            "competitors": e["competitors"] if e["competitors"] is not None else -1,
                            "nations": e["nations"] if e["nations"] is not None else -1}
        if e["sport"]:
            vs["Sport"][e["sport"]] = {}
        if e["venue"]:
            vs["Venue"][e["venue"]] = {}
        ev = es.setdefault("Event", {}).setdefault(did, {})
        ev.setdefault("IN_GAMES", {}).setdefault("Games", {})[e["games"]] = {}
        if e["sport"]:
            ev.setdefault("IN_SPORT", {}).setdefault("Sport", {})[e["sport"]] = {}
        if e["venue"]:
            ev.setdefault("HELD_AT", {}).setdefault("Venue", {})[e["venue"]] = {}
        if did in prev_edition:
            ev.setdefault("PREV_EDITION", {}).setdefault("Event", {})[prev_edition[did]] = {}
        for m in e["medals"]:
            vs["Athlete"][m["athlete"]] = {}
            # one edge per (event, athlete); medal type is an edge attribute
            ev.setdefault("MEDAL", {}).setdefault("Athlete", {})[m["athlete"]] = {"medal": m["medal"], "noc": m["noc"]}
            if m["noc"]:
                vs["Nation"][m["noc"]] = {}
                ev.setdefault("MEDAL_NATION", {}).setdefault("Nation", {})[m["noc"]] = {"medal": m["medal"]}
        es.setdefault("Doc", {}).setdefault(did, {}).setdefault("IS_EVENT", {}).setdefault("Event", {})[did] = {}
        n += 1
        if n % 100 == 0:
            flush(vs, es)
            vs, es = defaultdict(dict), {}
    flush(vs, es)
    print("graph loaded")


def build_embeddings():
    chunks = [json.loads(l) for l in open(RESULTS / "chunks.jsonl", encoding="utf-8")]
    out, part = RESULTS / "chunk_emb.npy", RESULTS / "chunk_emb.partial.npy"
    texts = [c["title"] + "\n" + c["text"] for c in chunks]
    vecs = list(np.load(part)) if part.exists() else []  # resume after interruption
    for i in tqdm(range(len(vecs), len(texts), 64), desc="embedding", initial=len(vecs) // 64, total=-(-len(texts) // 64)):
        vecs.extend(embed(texts[i:i + 64]))
        if (i // 64) % 20 == 0:
            np.save(part, np.asarray(vecs, dtype=np.float32))
    arr = np.asarray(vecs, dtype=np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
    np.save(out, arr)
    print("embeddings", arr.shape)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-graph", action="store_true")
    ap.add_argument("--skip-embed", action="store_true")
    a = ap.parse_args()
    if not a.skip_graph:
        build_graph()
    if not a.skip_embed:
        build_embeddings()
