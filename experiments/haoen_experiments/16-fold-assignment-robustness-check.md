---
experiment: "16"
title: "Fold-assignment robustness check"
type: validation
technical_score: 0.950725
delta: n/a
decision: "Validated"
summary: "Six seeds; tuning seed sits mid-range, no split overfit"
source: "REPORT.md"
---
# Fold-assignment robustness check

Every OOF validation in this report -- across the L2 sweeps, the listwise objective, the override-gating fix, the BM25 comparison -- used the same 5-fold target-product-disjoint split (`RNG_SEED = 20260829`). Individually each round validated correctly against genuinely held-out folds, but after this many cumulative tuning decisions against one fixed split, there's a real risk the whole pipeline quietly overfit to that split's particular quirks rather than to the underlying task -- a classic failure mode of iterative tuning against a single validation partition, distinct from within-round overfitting.

Checked directly: re-ran the OOF ranking-gate diagnostic (rank of target within its harvested pool, L2=3.0) across five additional seeds the tuning process never saw. Rank-1 count ranged 93-99 and MRR 0.607-0.626 across all six seeds including the original -- and the original tuning seed (rank-1=97, MRR=0.624) sits in the *middle* of that range, not at an anomalous high end. If the pipeline had overfit to that specific split, it would be expected to look distinctly better on it than on fresh splits; it doesn't. The fitted weight magnitude was also stable (max|weight| 4.37-4.45) across every seed, confirming the L2=3.0 stability fix generalizes too, not just for the one split it was chosen on.

Took the worst-looking seed by that diagnostic (999999, rank-1=93) through a full strict OOF end-to-end confirmation as a genuine worst-case check: **HR@10 1.000, MRR 0.918, technical score 0.950725** -- essentially indistinguishable from the deployed 0.951339 and the original seed's own OOF confirmation of 0.950014. The pipeline's real-world performance does not meaningfully depend on which fold split validated it.
