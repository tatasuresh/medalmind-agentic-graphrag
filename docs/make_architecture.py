"""Generates docs/architecture.svg (and an HTML wrapper used to screenshot docs/architecture.png)."""
from pathlib import Path
from xml.sax.saxutils import escape as esc

INK, MUTE, CARD = "#111827", "#6B7280", "#F3F4F6"
RAG, GRAPH, AGENT = "#8A8A85", "#2B6CB0", "#F26B21"
TGC, VEC = "#0F766E", "#7C3AED"  # badge colors: TigerGraph / vector index
W, H = 1600, 900
out = []


def add(s):
    out.append(s)


def text(x, y, s, size=14, weight="400", fill=INK, anchor="start", family="Calibri, Segoe UI, sans-serif"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" font-family="{family}">{esc(s)}</text>')


def rect(x, y, w, h, fill="#fff", stroke="none", sw=1.5, r=10):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def box(x, y, w, h, title, sub=(), fill="#fff", stroke=INK, tfill=INK, size=15, subsize=12.5):
    rect(x, y, w, h, fill, stroke)
    n = len(sub)
    top = y + (h - (22 + 17 * n)) / 2 + 17
    text(x + w / 2, top, title, size, "700", tfill, "middle")
    for i, line in enumerate(sub):
        text(x + w / 2, top + 20 + 17 * i, line, subsize, "400", MUTE if tfill == INK else "#fff", "middle")


def arrow(x1, y1, x2, y2, color=INK, dash=False):
    d = ' stroke-dasharray="5 4"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"{d} marker-end="url(#a{color[1:]})"/>')


def badge(x, y, label, color):
    w = 8 * len(label) + 14
    rect(x - w, y, w, 18, color, r=9)
    text(x - w / 2, y + 13, label, 10.5, "700", "#fff", "middle")


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add("<defs>")
for c in {INK, RAG, GRAPH, AGENT, MUTE}:
    add(f'<marker id="a{c[1:]}" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="{c}"/></marker>')
add("</defs>")
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(40, 52, "MedalMindAgent: architecture", 30, "700", INK, family="Cambria, Georgia, serif")
text(40, 80, "RAG answers. GraphRAG connects. MedalMindAgent investigates.", 16, "400", MUTE)

# ---------------------------------------------------------------- ingest panel
rect(40, 110, 320, 700, CARD, r=12)
text(60, 138, "INGEST  ·  one-off, no LLM extraction", 12.5, "700", MUTE)
box(60, 155, 280, 70, "corpus.jsonl", ["2,951 Wikipedia documents"])
arrow(200, 225, 200, 262)
box(60, 262, 280, 78, "Infobox parser + chunker", ["regex over [Infobox Olympic event]", "16,770 chunks"])
arrow(200, 340, 200, 392)
box(60, 392, 280, 215, "TigerGraph Savanna", ["graph: AgenticOlympics", "", "2,162 events · 5,264 athletes", "303 venues · 136 nations · 41 sports", "", "MEDAL · IN_GAMES · HELD_AT", "PREV_GAMES · PREV_EDITION"], fill="#fff", stroke=TGC)
add(f'<path d="M60,301 L50,301 L50,670 L58,670" fill="none" stroke="{MUTE}" stroke-width="2" marker-end="url(#a{MUTE[1:]})"/>')
box(60, 625, 280, 90, "Chunk embeddings", ["text-embedding-3-small", "cosine index (local numpy)"], stroke=VEC)

# ---------------------------------------------------------------- question bar
rect(396, 120, 8, 640, "#D1D5DB", r=4)
text(400, 100, "Question", 13, "700", INK, "middle")
for y in (165, 305, 490):
    arrow(404, y, 438, y)

# ---------------------------------------------------------------- lane 1: RAG
rect(440, 110, 760, 110, "#fff", RAG, 2, 12)
rect(440, 110, 120, 110, RAG, RAG, 0, 12)
text(500, 160, "1 · RAG", 16, "700", "#fff", "middle")
text(500, 182, "1 LLM call", 12, "400", "#fff", "middle")
for i, (t, s) in enumerate([("Embed question", ""), ("Top-6 chunks", "cosine similarity"), ("Answer", "gpt-4o-mini")]):
    x = 585 + i * 205
    box(x, 133, 175, 64, t, [s] if s else [], stroke=RAG)
    if i < 2:
        arrow(x + 175, 165, x + 205, 165)
badge(585 + 205 + 175 - 6, 124, "vector idx", VEC)

# ---------------------------------------------------------------- lane 2: GraphRAG
rect(440, 240, 760, 130, "#fff", GRAPH, 2, 12)
rect(440, 240, 120, 130, GRAPH, GRAPH, 0, 12)
text(500, 300, "2 · GraphRAG", 15, "700", "#fff", "middle")
text(500, 322, "fixed recipe", 12, "400", "#fff", "middle")
steps = [("Vector seeds", "top-4 chunks", VEC), ("Link entities", "sport · games", TGC), ("Expand graph", "events + medalists", TGC), ("Answer", "1 LLM call", None)]
for i, (t, s, b) in enumerate(steps):
    x = 580 + i * 155
    box(x, 275, 135, 64, t, [s], stroke=GRAPH, size=14)
    if b:
        badge(x + 128, 266, "vector idx" if b == VEC else "TigerGraph", b)
    if i < 3:
        arrow(x + 135, 307, x + 155, 307)

# ---------------------------------------------------------------- lane 3: Agentic
rect(440, 390, 760, 410, "#fff", AGENT, 2.5, 12)
rect(440, 390, 120, 410, AGENT, AGENT, 0, 12)
text(500, 560, "3 · Agentic", 16, "700", "#fff", "middle")
text(500, 580, "GraphRAG", 16, "700", "#fff", "middle")
text(500, 606, "plans · acts ·", 12, "400", "#fff", "middle")
text(500, 622, "evaluates · stops", 12, "400", "#fff", "middle")
box(580, 410, 600, 78, "Orchestrator LLM", ["plan → act → evaluate → replan → stop", "10-step budget · duplicate-call guard · full trace"], fill=AGENT, stroke=AGENT, tfill="#fff", size=17)
agents = [("EntityLinker", ["link_entity"], TGC), ("Aggregator", ["find_events", "filter · count", "rank · medals"], TGC), ("GraphTraverser", ["get_event", "previous_games"], TGC), ("Retriever", ["vector_search", "get_chunks"], VEC), ("EvidenceEvaluator", ["check_evidence", "(LLM judge)"], None)]
for i, (n, tools, b) in enumerate(agents):
    x = 580 + i * 122
    arrow(x + 55, 488, x + 55, 528, AGENT)
    box(x, 528, 112, 128, n, tools, stroke=AGENT, size=12.5, subsize=12)
    if b:
        badge(x + 108, 533 + 0, "TigerGraph" if b == TGC else "vector idx", b)
box(580, 690, 600, 80, "finish(answer, doc_ids)", ["answer + citations + step-by-step trace", "agents · tools · strategy changes · stop reason"], stroke=AGENT)
arrow(880, 656, 880, 690, AGENT)

# ---------------------------------------------------------------- evaluation panel
rect(1240, 110, 320, 700, CARD, r=12)
text(1260, 138, "EVALUATE  ·  same questions, all pipelines", 12.5, "700", MUTE)
box(1260, 155, 280, 108, "eval/run.py", ["answers · citations", "tokens (in / out / embed)", "latency · agent trace"])
arrow(1400, 263, 1400, 300)
box(1260, 300, 280, 84, "eval/judge.py", ["LLM-as-judge PASS / FAIL", "vs gold, 100 public questions"])
arrow(1400, 384, 1400, 421)
box(1260, 421, 280, 108, "Metrics dashboard", ["accuracy by question type", "tokens per answer", "per-question traces"], stroke=AGENT)
box(1260, 575, 280, 100, "Hidden-question outputs", ["from eval/run.py: 50 questions", "× 4 pipelines · tokens · trace"], stroke=INK)
for y in (165, 305, 590):
    add(f'<line x1="1200" y1="{y}" x2="1220" y2="{y}" stroke="{INK}" stroke-width="2"/>')
add(f'<line x1="1220" y1="165" x2="1220" y2="590" stroke="{INK}" stroke-width="2"/>')
arrow(1220, 209, 1258, 209)

# ---------------------------------------------------------------- legend
badge(120, 846, "TigerGraph", TGC)
text(130, 859, "step queries or traverses the graph", 12.5, "400", MUTE)
badge(470, 846, "vector idx", VEC)
text(480, 859, "step uses the embedding index", 12.5, "400", MUTE)
text(1560, 859, "gpt-4o-mini (pipelines + judge) · text-embedding-3-small", 12.5, "400", MUTE, "end")
add("</svg>")

here = Path(__file__).parent
svg = "\n".join(out)
(here / "architecture.svg").write_text(svg, encoding="utf-8")
(here / "_arch.html").write_text(f'<!doctype html><meta charset="utf-8"><body style="margin:0;background:#fff">{svg}</body>', encoding="utf-8")
print("wrote architecture.svg")
