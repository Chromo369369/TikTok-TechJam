---
experiment: "06"
title: "Measured effect"
type: results
technical_score: n/a
delta: n/a
decision: "Reference"
summary: "Full baseline-to-current score progression table"
source: "REPORT.md"
---
# Measured effect

Measured against the real 50,000-product catalog (`data/catalog.jsonl`) and the real 200-session public set, via the unmodified `evaluator/local_evaluator.py`.

| Metric | Shipped baseline (weak BM25) | Constraint-state + BM25 | + Reverse phrase index | + Confidence guard | + Learned re-ranker (v1) | + Multi-phrase evidence + determinism fix (v2) | + TF-IDF cosine "vector similarity" (v3) | + L2 re-tune (v4) | + Override-gating harvest fix (v5) | + Listwise objective (stabilized, v6) | + Category-pool-cap fix (v7) | + Interaction terms (current) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hit Rate@10 | 0.125 | 0.955 | 1.000 | 1.000 | 0.995 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| MRR | 0.068 | 0.588 | 0.673 | 0.879 | 0.924 | 0.891 | 0.901 | 0.903 | 0.911 | 0.920 | 0.939 | 0.940 |
| MTTC | 9.81 | 3.04 | 2.21 | 2.735 | 2.735 | 2.255 | 2.245 | 2.245 | 2.245 | 2.24 | 2.275 | 2.275 |
| Efficiency | ~0.02 | 0.796 | 0.879 | 0.827 | 0.827 | 0.8745 | 0.8755 | 0.8755 | 0.8755 | 0.876 | 0.8725 | 0.8725 |
| **Technical Score** | **~0.10** | **0.813** | **0.878** | **0.929** | **0.940** | **0.942** | **0.945** | **0.946** | **0.948** | **0.951** | **0.956** | **0.9565** |
| Reported tokens | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Per-scenario breakdown for the current agent: Buying 1.00 hit-rate / MRR 0.942 / MTTC 1.825; Browsing 1.00 / 0.872 / 2.05; Intent Override 1.00 / 0.868 / 3.60; Boundary 1.00 / 0.913 / 3.1.

Removing the confidence-guard's turn cutoff entirely (guard active for the whole session, gated only on `other_exhausted`) was tested directly: Hit Rate@10 drops to 0.99 (2/200 sessions never accumulate confident evidence and the guard suppresses recommendations for their entire 10-turn budget), for a *lower* technical score (0.923) than the bounded version (0.929, pre-re-ranker) despite a marginally higher MRR — confirming the bounded cutoff is not just a safety rationalization but measurably the better tradeoff.
