// Builds ../docs/MedalMindAgent_Hackathon.pptx. Every number comes from results/public_*.jsonl (see docs/slides_outline.md).
const pptxgen = require("pptxgenjs");
// Optional: a helper exporting applyTheme(pptxPath, THEME) that writes THEME's colors into the deck's theme part.
// Without it the deck still builds; scheme colors in the layout masters just fall back to Office defaults (white/near-black).
const applyTheme = process.env.APPLY_THEME_JS ? require(process.env.APPLY_THEME_JS).applyTheme : null;

const THEME = {
  name: "Agentic GraphRAG",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "111827", lt1: "FFFFFF", dk2: "1F2937", lt2: "F3F4F6",
    accent1: "F26B21", accent2: "2B6CB0", accent3: "8A8A85", accent4: "2F855A", accent5: "C53030", accent6: "6B7280",
    hlink: "2B6CB0", folHlink: "6B7280",
  },
};
const HEX = { agent: "F26B21", graph: "2B6CB0", rag: "8A8A85", ink: "111827", mute: "6B7280", card: "F3F4F6", ok: "2F855A", bad: "C53030" };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "MedalMindAgent: When Does an Agent Actually Pay Off?";
pres.author = "Suresh Kumar Tata";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.8, fontSize: 30, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } }],
  slideNumber: { x: 9.1, y: 5.2, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "DARK",
  background: { color: C.text1 },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.8, fontSize: 30, bold: true, color: C.background1, align: "left", valign: "middle", margin: 0 }, text: "" } }],
});

const shadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 90, opacity: 0.12 });
const dot = (s, x, y, color, d = 0.22, name = "dot") => s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 }, objectName: name });
function pill(s, text, x, y, w, color, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.36, fill: { color }, line: { color, width: 0 }, rectRadius: 0.18, objectName: name + " bg" });
  s.addText(text, { x, y, w, h: 0.36, fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: name });
}

// ---------------------------------------------------------------- 1. Title
{
  const s = pres.addSlide({ masterName: "DARK" });
  s.addText("MEDALMINDAGENT  Â·  TIGERGRAPH AGENTIC GRAPHRAG HACKATHON  Â·  ROUND 1", { x: 0.5, y: 0.55, w: 9, h: 0.3, fontSize: 11, bold: true, color: HEX.agent, charSpacing: 2, margin: 0, isTextBox: true, objectName: "kicker" });
  s.addText("When does an agent actually pay off?", { x: 0.5, y: 1.15, w: 5.6, h: 1.9, fontSize: 40, bold: true, fontFace: "Cambria", color: "FFFFFF", valign: "top", margin: 0, isTextBox: true, objectName: "title text" });
  s.addText("RAG answers. GraphRAG connects. MedalMindAgent investigates.", { x: 0.5, y: 2.9, w: 5.4, h: 0.8, fontSize: 16, color: "D1D5DB", margin: 0, isTextBox: true, objectName: "subtitle" });
  s.addText("Suresh Kumar Tata", { x: 0.5, y: 4.85, w: 5, h: 0.3, fontSize: 12, color: "9CA3AF", margin: 0, isTextBox: true, objectName: "author" });
  // right: accuracy ladder
  const rows = [["97%", "Agentic GraphRAG", HEX.agent, 66, 1.0], ["58%", "GraphRAG", HEX.graph, 40, 2.35], ["53%", "RAG", HEX.rag, 40, 3.35]];
  rows.forEach(([n, l, col, fs, y]) => {
    dot(s, 6.55, y + 0.12, col, 0.2, "legend dot");
    s.addText(n, { x: 6.85, y: y - 0.1, w: 2.7, h: n === "97%" ? 1.0 : 0.65, fontSize: fs, bold: true, fontFace: "Cambria", color: col, margin: 0, valign: "middle", isTextBox: true, objectName: "stat " + l });
    s.addText(l, { x: 6.85, y: y + (n === "97%" ? 0.85 : 0.55), w: 2.7, h: 0.3, fontSize: 14, color: "D1D5DB", margin: 0, isTextBox: true, objectName: "label " + l });
  });
  s.addText("accuracy on 100 public questions", { x: 6.55, y: 4.4, w: 3, h: 0.3, fontSize: 11, color: "9CA3AF", margin: 0, isTextBox: true, objectName: "stat caption" });
  s.addNotes("Hook: some questions need one lookup, some need an investigation. We built all three pipelines on TigerGraph and measured exactly where the agent earns its keep. Headline: 97% for the agent vs 53% for plain RAG on the 100 public questions.");
}

// ---------------------------------------------------------------- 2. The question
{
  pres.addSection({ title: "Problem" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
  s.addText("Does your RAG need an agent?", { placeholder: "title" });
  const cards = [
    ["1", "RAG", "Retrieves similar text. One lookup, one answer.", HEX.rag],
    ["2", "GraphRAG", "Adds structure: entities, relationships, multi-hop context.", HEX.graph],
    ["3", "Agentic GraphRAG", "Adds planning: it picks its own retrieval path from what it finds.", HEX.agent],
  ];
  cards.forEach(([n, t, d, col], i) => {
    const x = 0.5 + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.35, w: 2.85, h: 2.2, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, shadow: shadow(), objectName: "card " + t });
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 1.6, w: 0.5, h: 0.5, fill: { color: col }, line: { color: col, width: 0 }, objectName: "badge " + t });
    s.addText(n, { x: x + 0.25, y: 1.6, w: 0.5, h: 0.5, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "badge num " + t });
    s.addText(t, { x: x + 0.25, y: 2.2, w: 2.4, h: 0.4, fontSize: 18, bold: true, fontFace: "Cambria", color: HEX.ink, margin: 0, isTextBox: true, objectName: "card title " + t });
    s.addText(d, { x: x + 0.25, y: 2.65, w: 2.4, h: 0.8, fontSize: 14, color: "374151", margin: 0, valign: "top", isTextBox: true, objectName: "card body " + t });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.85, w: 9, h: 1.0, fill: { color: HEX.ink }, line: { color: HEX.ink, width: 0 }, objectName: "goal band" });
  s.addText("Which questions need an agent, and which don't?", { x: 0.8, y: 3.9, w: 8.4, h: 0.5, fontSize: 20, bold: true, fontFace: "Cambria", color: "FFFFFF", margin: 0, valign: "middle", isTextBox: true, objectName: "goal text" });
  s.addText("2,951 Wikipedia documents Â· 100 public + 50 hidden questions Â· lookup, multi-hop, aggregation, superlative, temporal", { x: 0.8, y: 4.4, w: 8.4, h: 0.35, fontSize: 12, color: "D1D5DB", margin: 0, isTextBox: true, objectName: "goal detail" });
  s.addNotes("The hackathon's headline question. Corpus is mostly Olympic event pages. Five question types let us see exactly where each approach wins or fails.");
}

// ---------------------------------------------------------------- 3. Three pipelines
{
  pres.addSection({ title: "System" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "System" });
  s.addText("Three pipelines, one benchmark", { placeholder: "title" });
  const lanes = [
    ["RAG", HEX.rag, ["Embed question", "Top-6 chunks", "1 LLM call"]],
    ["GraphRAG", HEX.graph, ["Vector seeds", "Link entities", "Expand the graph", "1 LLM call"]],
    ["Agentic GraphRAG", HEX.agent, ["Plan", "Call agent or tool", "Evaluate evidence", "Loop or finish"]],
  ];
  lanes.forEach(([name, col, steps], i) => {
    const y = 1.35 + i * 1.1;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 9, h: 0.9, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "lane " + name });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 1.75, h: 0.9, fill: { color: col }, line: { color: col, width: 0 }, objectName: "lane label bg " + name });
    s.addText(name, { x: 0.58, y, w: 1.6, h: 0.9, fontSize: 14, bold: true, color: "FFFFFF", valign: "middle", margin: 0, isTextBox: true, objectName: "lane label " + name });
    const n = steps.length, gap = 0.3, x0 = 2.45, bw = (7.0 - (n - 1) * gap) / n;
    steps.forEach((t, k) => {
      const x = x0 + k * (bw + gap);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y + 0.17, w: bw, h: 0.56, fill: { color: "FFFFFF" }, line: { color: col, width: 1.5 }, rectRadius: 0.08, objectName: `step ${name} ${k + 1}` });
      s.addText(t, { x, y: y + 0.17, w: bw, h: 0.56, fontSize: 12, bold: true, color: HEX.ink, align: "center", valign: "middle", margin: 0.04, isTextBox: true, objectName: `step text ${name} ${k + 1}` });
      if (k < n - 1) s.addText("â€º", { x: x + bw, y: y + 0.17, w: gap, h: 0.56, fontSize: 20, bold: true, color: col, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `arrow ${name} ${k + 1}` });
    });
  });
  s.addText("Every call is metered: input, output and embedding tokens, latency, steps, tools used, stop reason.", { x: 0.5, y: 4.7, w: 8.4, h: 0.35, fontSize: 12, color: HEX.mute, margin: 0, isTextBox: true, objectName: "metering note" });
  s.addNotes("RAG and GraphRAG are fixed recipes. The agent decides its next action from the question and the evidence so far. All three go through one metering wrapper so token comparisons are fair.");
}

// ---------------------------------------------------------------- 4. Architecture
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "System" });
  s.addText("A deterministic graph and five agents", { placeholder: "title" });
  const stats = [["2,162", "events"], ["5,264", "athletes"], ["303", "venues"], ["136", "nations"]];
  stats.forEach(([n, l], i) => {
    const x = 0.5 + (i % 2) * 1.95, y = 1.35 + Math.floor(i / 2) * 1.35;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 1.8, h: 1.2, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "stat card " + l });
    s.addText(n, { x, y: y + 0.12, w: 1.8, h: 0.6, fontSize: 32, bold: true, fontFace: "Cambria", color: HEX.graph, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "stat " + l });
    s.addText(l, { x, y: y + 0.72, w: 1.8, h: 0.3, fontSize: 14, color: "374151", align: "center", margin: 0, isTextBox: true, objectName: "stat label " + l });
  });
  s.addText("TigerGraph Savanna graph, built with regex from Olympic infoboxes. No LLM extraction, so ingest is cheap and reproducible.", { x: 0.5, y: 4.1, w: 3.75, h: 0.9, fontSize: 12, color: HEX.mute, margin: 0, valign: "top", isTextBox: true, objectName: "graph note" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.7, y: 1.35, w: 4.8, h: 0.55, fill: { color: HEX.agent }, line: { color: HEX.agent, width: 0 }, rectRadius: 0.1, objectName: "orchestrator" });
  s.addText("Orchestrator LLM: plan, act, evaluate, stop", { x: 4.7, y: 1.35, w: 4.8, h: 0.55, fontSize: 14, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "orchestrator text" });
  const agents = [["EntityLinker", "link_entity"], ["Aggregator", "find_events: filter Â· count Â· rank"], ["GraphTraverser", "get_event Â· previous_games"], ["Retriever", "vector_search Â· get_chunks"], ["EvidenceEvaluator", "check_evidence"]];
  agents.forEach(([a, t], i) => {
    const y = 2.05 + i * 0.62;
    s.addShape(pres.shapes.RECTANGLE, { x: 4.7, y, w: 4.8, h: 0.52, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "agent row " + a });
    dot(s, 4.85, y + 0.15, HEX.agent, 0.22, "agent dot " + a);
    s.addText(a, { x: 5.2, y, w: 1.75, h: 0.52, fontSize: 13, bold: true, color: HEX.ink, valign: "middle", margin: 0, isTextBox: true, objectName: "agent name " + a });
    s.addText(t, { x: 6.95, y, w: 2.5, h: 0.52, fontSize: 11, color: "374151", valign: "middle", margin: 0, isTextBox: true, objectName: "agent tools " + a });
  });
  s.addNotes("Typed attributes in TigerGraph make counting exact: the Aggregator pushes numeric filters into the database. The GraphTraverser follows PREV_GAMES and MEDAL edges. The agent never counts by reading text.");
}

// ---------------------------------------------------------------- 5. Headline result
{
  pres.addSection({ title: "Results" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("97% accuracy at RAG's token budget", { placeholder: "title" });
  s.addChart(pres.charts.BAR, [{ name: "Accuracy (%)", labels: ["RAG", "GraphRAG", "Agentic GraphRAG"], values: [53, 58, 97] }], {
    x: 0.4, y: 1.25, w: 5.3, h: 3.8, barDir: "col", chartColors: [HEX.rag, HEX.graph, HEX.agent],
    showTitle: true, title: "Accuracy on 100 public questions (%)", titleFontSize: 13, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: "374151", catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: HEX.mute, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
    valAxisMaxVal: 100, valAxisMinVal: 0, valAxisMajorUnit: 25, valGridLine: { color: "E5E7EB", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 60,
  });
  const k = [["3,024", "tokens per answer", "RAG 2,498 (agent +21%)", HEX.agent], ["2.4", "average agent steps", "2.0 for counts, 3.2 for temporal", HEX.agent], ["7.1 s", "average latency", "RAG 1.7 s Â· GraphRAG 13.9 s", HEX.agent]];
  k.forEach(([n, l, d, col], i) => {
    const y = 1.3 + i * 1.28;
    s.addShape(pres.shapes.RECTANGLE, { x: 6.0, y, w: 3.5, h: 1.15, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "kpi card " + l });
    s.addText(n, { x: 6.15, y: y + 0.05, w: 1.4, h: 1.05, fontSize: 28, bold: true, fontFace: "Cambria", color: col, valign: "middle", margin: 0, isTextBox: true, objectName: "kpi " + l });
    s.addText([{ text: l, options: { bold: true, fontSize: 14, color: HEX.ink, breakLine: true } }, { text: d, options: { fontSize: 11, color: HEX.mute } }], { x: 7.55, y: y + 0.1, w: 1.9, h: 0.95, valign: "middle", margin: 0, isTextBox: true, objectName: "kpi text " + l });
  });
  s.addNotes("Agent: 97%. RAG: 53%. GraphRAG: 58%. Token cost is within about 21% of RAG because the agent reads compact tool results (a count, a handful of rows) instead of six text chunks. LLM-as-judge accuracy with gpt-4o-mini.");
}

// ---------------------------------------------------------------- 6. By type
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Where an agent pays off", { placeholder: "title" });
  s.addChart(pres.charts.BAR, [
    { name: "RAG", labels: ["Aggregation", "Superlative", "Multi-hop", "Temporal", "Lookup"], values: [0, 40, 43, 86, 95] },
    { name: "GraphRAG", labels: ["Aggregation", "Superlative", "Multi-hop", "Temporal", "Lookup"], values: [29, 70, 25, 86, 100] },
    { name: "Agentic GraphRAG", labels: ["Aggregation", "Superlative", "Multi-hop", "Temporal", "Lookup"], values: [100, 100, 89, 100, 100] },
  ], {
    x: 0.4, y: 1.2, w: 6.1, h: 3.9, barDir: "col", barGrouping: "clustered", chartColors: [HEX.rag, HEX.graph, HEX.agent],
    showTitle: true, title: "Accuracy by question type (%)", titleFontSize: 13, titleColor: HEX.ink, titleFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: "374151", legendFontFace: "+mn-lt",
    catAxisLabelColor: "374151", catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: HEX.mute, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9, dataLabelColor: "374151", dataLabelFontFace: "+mn-lt",
    valAxisMaxVal: 110, valAxisMinVal: 0, valAxisMajorUnit: 25, valGridLine: { color: "E5E7EB", size: 0.5 }, catGridLine: { style: "none" }, barGapWidthPct: 50,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.8, y: 1.3, w: 2.7, h: 2.0, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "wins card" });
  dot(s, 6.98, 1.45, HEX.ok, 0.2, "wins dot");
  s.addText("Agent wins", { x: 7.3, y: 1.38, w: 2.1, h: 0.34, fontSize: 14, bold: true, color: HEX.ok, margin: 0, valign: "middle", isTextBox: true, objectName: "wins head" });
  s.addText("Counting questions: RAG 0 of 21, agent 21 of 21, at the same token cost. It needs every matching event, not the top-k.", { x: 6.98, y: 1.8, w: 2.4, h: 1.45, fontSize: 13, color: "374151", margin: 0, valign: "top", isTextBox: true, objectName: "wins body" });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.8, y: 3.5, w: 2.7, h: 1.55, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "overkill card" });
  dot(s, 6.98, 3.65, HEX.bad, 0.2, "overkill dot");
  s.addText("Overkill", { x: 7.3, y: 3.58, w: 2.1, h: 0.34, fontSize: 14, bold: true, color: HEX.bad, margin: 0, valign: "middle", isTextBox: true, objectName: "overkill head" });
  s.addText("Plain lookups: about 100% for all three, agent uses 30% more tokens.", { x: 6.98, y: 4.0, w: 2.4, h: 1.0, fontSize: 13, color: "374151", margin: 0, valign: "top", isTextBox: true, objectName: "overkill body" });
  s.addNotes("Counts per type (correct/total): aggregation RAG 0/21, GraphRAG 6/21, agent 21/21. Superlative 4/10, 7/10, 10/10. Multi-hop 12/28, 7/28, 25/28. Temporal 19/22, 19/22, 22/22. Lookup 18/19, 19/19, 19/19. Agent token cost vs RAG: aggregation 0.9x, superlative 1.3x, multi-hop 1.1x, temporal 1.5x, lookup 1.3x.");
}

// ---------------------------------------------------------------- 7. In action
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("The agent in action", { placeholder: "title" });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.25, w: 9, h: 0.65, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "question band" });
  s.addText("How many biathlon events at the 2018 Winter Olympics had more than 73 competitors?", { x: 0.7, y: 1.25, w: 8.6, h: 0.65, fontSize: 14, italic: true, color: HEX.ink, valign: "middle", margin: 0, isTextBox: true, objectName: "question text" });
  const res = [["RAG", "2", "wrong", HEX.rag, HEX.bad], ["GraphRAG", "6", "wrong", HEX.graph, HEX.bad], ["Agentic GraphRAG", "5", "correct", HEX.agent, HEX.ok]];
  res.forEach(([n, a, v, col, vc], i) => {
    const x = 0.5 + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.05, w: 2.85, h: 1.3, fill: { color: "FFFFFF" }, line: { color: col, width: 2 }, objectName: "answer card " + n });
    s.addText(n, { x: x + 0.15, y: 2.1, w: 2.55, h: 0.3, fontSize: 12, bold: true, color: col, margin: 0, isTextBox: true, objectName: "answer name " + n });
    s.addText(a, { x: x + 0.15, y: 2.4, w: 1.2, h: 0.85, fontSize: 44, bold: true, fontFace: "Cambria", color: HEX.ink, valign: "middle", margin: 0, isTextBox: true, objectName: "answer value " + n });
    s.addText(v, { x: x + 0.85, y: 2.4, w: 1.8, h: 0.85, fontSize: 18, bold: true, color: vc, valign: "middle", margin: 0, isTextBox: true, objectName: "answer verdict " + n });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.55, w: 9, h: 1.5, fill: { color: HEX.ink }, line: { color: HEX.ink, width: 0 }, objectName: "trace box" });
  s.addText([
    { text: "agent trace Â· 2 steps Â· 2,237 tokens", options: { fontSize: 11, color: "9CA3AF", breakLine: true } },
    { text: "1  Aggregator.find_events(sport=\"Biathlon\", games=\"2018 Winter Olympics\", min_competitors=73)", options: { fontSize: 11, color: "FFFFFF", breakLine: true } },
    { text: "   -> count: 5   (filter runs inside TigerGraph)", options: { fontSize: 11, color: HEX.agent, breakLine: true } },
    { text: "2  finish(answer=\"5\")", options: { fontSize: 11, color: "FFFFFF" } },
  ], { x: 0.7, y: 3.6, w: 8.6, h: 1.4, fontFace: "Courier New", valign: "middle", margin: 0, paraSpaceAfter: 3, isTextBox: true, objectName: "trace text" });
  s.addNotes("Same question to all three. RAG and GraphRAG each read a handful of passages and miscount. The agent chose the Aggregator and asked TigerGraph for the exact count. Second example if asked: 'men's 20 km walk at the Games before 2016' goes previous_games -> 2012, then find_events with medalists, answer Chen Ding, 3 steps.");
}

// ---------------------------------------------------------------- 8. Honesty
{
  pres.addSection({ title: "Rigor" });
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Rigor" });
  s.addText("Tuned honestly, reported honestly", { placeholder: "title" });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.3, w: 3.1, h: 1.9, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "iteration card" });
  s.addText("89 â†’ 96 â†’ 97%", { x: 0.6, y: 1.4, w: 2.9, h: 0.8, fontSize: 28, bold: true, fontFace: "Cambria", color: HEX.agent, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "iteration stat" });
  s.addText("public accuracy over three agent versions, each fix traced to real failures and archived in the repo", { x: 0.7, y: 2.2, w: 2.7, h: 0.95, fontSize: 12, color: "374151", align: "center", margin: 0, valign: "top", isTextBox: true, objectName: "iteration caption" });
  const fixes = [
    ["REST filter bug", "TigerGraph's filter returns nothing for strings with spaces, so those matches moved into Python"],
    ["Entity-link loops", "Recipes in the prompt plus a duplicate-call guard fixed temporal questions"],
    ["Shared venue and date", "Several events overlap, so the tool now prefers the exact match"],
  ];
  fixes.forEach(([h, d], i) => {
    const y = 1.3 + i * 0.66;
    s.addShape(pres.shapes.RECTANGLE, { x: 3.8, y, w: 5.7, h: 0.58, fill: { color: HEX.card }, line: { color: HEX.card, width: 0 }, objectName: "fix row " + h });
    s.addText([{ text: h + ": ", options: { bold: true, color: HEX.ink } }, { text: d, options: { color: "374151" } }], { x: 3.95, y, w: 5.45, h: 0.58, fontSize: 11, valign: "middle", margin: 0, isTextBox: true, objectName: "fix text " + h });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.45, w: 4.4, h: 1.5, fill: { color: "FFFFFF" }, line: { color: HEX.bad, width: 1.5 }, objectName: "negative card" });
  s.addText("Negative result", { x: 0.7, y: 3.55, w: 4.0, h: 0.32, fontSize: 14, bold: true, color: HEX.bad, margin: 0, isTextBox: true, objectName: "negative head" });
  s.addText("An adaptive router that skips the agent for easy questions saved almost nothing (3,019 vs 3,024 tokens) and lost 4 points. We report it and keep the agent always on.", { x: 0.7, y: 3.9, w: 4.0, h: 1.0, fontSize: 13, color: "374151", margin: 0, valign: "top", isTextBox: true, objectName: "negative body" });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 3.45, w: 4.4, h: 1.5, fill: { color: "FFFFFF" }, line: { color: HEX.mute, width: 1.5 }, objectName: "limits card" });
  s.addText("Limits", { x: 5.3, y: 3.55, w: 4.0, h: 0.32, fontSize: 14, bold: true, color: HEX.mute, margin: 0, isTextBox: true, objectName: "limits head" });
  s.addText("We tuned on the public set, so the hidden score will likely be lower. Three public misses remain, two caused by ambiguous questions. Vectors live in a local index.", { x: 5.3, y: 3.9, w: 4.0, h: 1.0, fontSize: 13, color: "374151", margin: 0, valign: "top", isTextBox: true, objectName: "limits body" });
  s.addNotes("Judges care about rigor. We tuned on public failures and say so. The router was a hypothesis that did not pay off: after the fixes the agent averages about RAG's token budget, so there was nothing left to save. Remaining misses: pub-060 and pub-099 name a venue and date shared by several events; pub-073 has a composite date the agent split.");
}

// ---------------------------------------------------------------- 9. Criteria + takeaway
{
  pres.addSection({ title: "Close" });
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
  s.addText("Built for the judging criteria", { placeholder: "title" });
  const rows = [["30%", "Investigation accuracy", "97% vs 53% for RAG; 21 of 21 on counts"], ["15%", "Evidence and explainability", "Full trace per answer: tools, arguments, results"], ["15%", "Agentic effectiveness", "2.4 steps, close to RAG's token budget"], ["15%", "Engineering quality", "Reproducible, resumable, metered, documented"], ["15%", "Innovation", "Push-down aggregation, exact disambiguation"], ["10%", "Presentation", "Interactive dashboard with every agent trace"]];
  rows.forEach(([w, n, d], i) => {
    const y = 1.2 + i * 0.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: y + 0.04, w: 0.75, h: 0.38, fill: { color: HEX.agent }, line: { color: HEX.agent, width: 0 }, rectRadius: 0.19, objectName: "weight pill " + n });
    s.addText(w, { x: 0.5, y: y + 0.04, w: 0.75, h: 0.38, fontSize: 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "weight " + n });
    s.addText(n, { x: 1.45, y, w: 2.9, h: 0.46, fontSize: 14, bold: true, color: "FFFFFF", valign: "middle", margin: 0, isTextBox: true, objectName: "criterion " + n });
    s.addText(d, { x: 4.4, y, w: 5.1, h: 0.46, fontSize: 13, color: "D1D5DB", valign: "middle", margin: 0, isTextBox: true, objectName: "evidence " + n });
  });
  s.addText("Use an agent where the question needs one.", { x: 0.5, y: 4.4, w: 9, h: 0.5, fontSize: 24, bold: true, fontFace: "Cambria", color: HEX.agent, margin: 0, valign: "middle", isTextBox: true, objectName: "takeaway" });
  s.addText("Build it. Benchmark it. Prove when agents matter.", { x: 0.5, y: 4.9, w: 9, h: 0.35, fontSize: 14, color: "D1D5DB", margin: 0, isTextBox: true, objectName: "tagline" });
  s.addNotes("Close on the takeaway: the agent is decisive for counting, ranking, multi-hop and temporal questions, and unnecessary for single lookups. Deliverables: working system, repo, architecture diagram, metrics dashboard, outputs for all 50 hidden questions.");
}

(async () => {
  const out = "../docs/MedalMindAgent_Hackathon.pptx";
  await pres.writeFile({ fileName: out });
  if (applyTheme) await applyTheme(out, THEME);
  console.log("wrote", out);
})();
