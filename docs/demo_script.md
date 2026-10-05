# MedalMindAgent: demo video script (target 3 minutes)

**0:00 Hook (15s)**: "Some questions need one lookup. Some need an investigation. We built RAG, GraphRAG and Agentic GraphRAG on TigerGraph to find out which is which." Show the dashboard header.

**0:15 Architecture (30s)**: Show docs/architecture.md diagram. Say: deterministic graph built from Olympic infoboxes (2,162 events, 5,264 athletes) in TigerGraph Savanna; one orchestrator, five specialised agents/tools.

**0:45 Live: aggregation (45s)**: Ask "How many biathlon events at the 2018 Winter Olympics had more than 73 competitors?"
- RAG answers 2 (wrong). GraphRAG answers 6 (wrong). Agent answers 5 (correct).
- Open the agent trace: link/find_events pushes the filter into TigerGraph and returns an exact count in 2 steps.

**1:30 Live: temporal / multi-hop (40s)**: "Who won gold in the men's 20 km walk at the Games immediately before 2016?" Show previous_games -> find_events with medalists. Then a venue+date question and the exact-match disambiguation.

**2:10 The headline result (40s)**: Dashboard, accuracy by question type chart. 97% vs 53% / 58%. Aggregation 0/21 -> 21/21 at the same token cost. Lookups: all ~100%, agent costs about 30% more tokens, so it is overkill there. We tried a router to skip the agent; it saved nothing, and we report that.

**2:50 Honesty + close (10s)**: Tuned on public questions (89 -> 97% over three iterations, all in the repo); hidden score unknown. "Build it. Benchmark it. Prove when agents matter."
