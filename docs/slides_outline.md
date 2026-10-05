# Slide deck: 9 slides (every number below comes from the run results)

## 1. Title
Agentic GraphRAG: When Does an Agent Actually Pay Off?
Three pipelines. One TigerGraph knowledge graph. 100 questions. Measured accuracy and token cost.

## 2. The question the industry hasn't settled
- RAG retrieves similar text; GraphRAG adds structure; Agentic GraphRAG adds planning.
- Goal: show which questions need an agent, and which don't, with numbers.
- Corpus: 2,951 Wikipedia docs, mostly Olympic events. Question types: lookup, multi-hop, aggregation, superlative, temporal.

## 3. What we built
1. RAG: top-6 chunks, one LLM call. 2. GraphRAG: fixed recipe (vector seeds, entity linking, one-hop expansion), one call.
3. Agentic GraphRAG: orchestrator plans, calls specialised agents, evaluates evidence, avoids loops, decides when to stop.
Everything metered: tokens, latency, steps, tools, stop reason.

## 4. Architecture
Deterministic graph from infoboxes in TigerGraph Savanna: 2,162 events, 5,264 athletes, 41 sports, 303 venues, 136 nations.
Agents: EntityLinker, Aggregator (find_events pushed down to TigerGraph), GraphTraverser, Retriever, EvidenceEvaluator.
Typed attributes make counting exact. (Diagram: docs/architecture.md)

## 5. Headline result (100 public questions)
| | RAG | GraphRAG | Agentic |
|---|---|---|---|
| Accuracy | 53% | 58% | **97%** |
| Avg tokens | 2,498 | 3,051 | 3,024 |
| LLM calls | 1.0 | 1.0 | 2.4 |
| Latency | 1.7 s | 13.9 s | 7.1 s |

## 6. Which questions need an agent?
| Type | RAG | GraphRAG | Agent | Agent tokens vs RAG |
|---|---|---|---|---|
| Aggregation | 0/21 | 6/21 | 21/21 | 0.9x |
| Superlative | 4/10 | 7/10 | 10/10 | 1.3x |
| Multi-hop | 12/28 | 7/28 | 25/28 | 1.1x |
| Temporal | 19/22 | 19/22 | 22/22 | 1.5x |
| Lookup | 18/19 | 19/19 | 19/19 | 1.3x (overkill) |

## 7. The agent in action
Biathlon 2018 >73 competitors: RAG 2, GraphRAG 6, Agent 5 (correct) via find_events inside TigerGraph.
20 km walk before 2016: previous_games -> 2012 -> find_events with medalists -> Chen Ding.

## 8. Engineering rigor and honesty
89% -> 96% -> 97% over three iterations driven by failure traces (REST filter bug on spaced strings, entity-link loops, venue/date ambiguity).
Adaptive router tested: saved ~0 tokens (3,019 vs 3,024), lost 4 points: reported as a negative result.
Limits: tuned on public set; hidden score likely lower; 3 public failures remain; vectors in a local index.

## 9. Judging criteria + takeaway
Accuracy 30% | Evidence/explainability 15% | Agentic effectiveness 15% | Engineering 15% | Innovation 15% | Presentation 10%.
Use an agent where the question needs one. Build it. Benchmark it. Prove when agents matter.
