---
experiment: "07"
title: "The learned re-ranker"
type: experiment
technical_score: 0.940
delta: +0.011
decision: "Adopted"
summary: "20-feature logistic reranker, target-disjoint 5-fold OOF"
source: "REPORT.md"
---
# The learned re-ranker

`Agent._score` was a hand-tuned linear formula (fixed weights like "+3.0 for a material match, +2.5 for a colour match"). Once Hit Rate@10 hit 1.000, the only headroom left was in *ordering* the candidates already being retrieved -- confirmed directly by an isolated ranking-only diagnostic: sorting each session's already-harvested candidate pool by the old hand-tuned formula put the true target at rank 1 in only 43/200 sessions and in the top 10 in 100/200, well below what the retrieval pool itself supports.

`Agent._score` is now `Agent._extract_features(...) · SCORE_WEIGHTS` -- 20 named, catalog-visible / runtime-observable features (bare BM25 rank, the reverse-phrase-index score, category match, material/colour/style/use-case/size/feature match counts, budget proximity, override match, preference-tag overlap, rating, rating count, category-bucket specificity, and catalog-listing completeness), dot-producted against a fitted weight vector. `tools/fit_reranker.py` fits `SCORE_WEIGHTS` offline:

1. **Harvest** one labeled training state per public session: replay it exactly as the real evaluator would, stop at the first turn the target naturally occurs in `Agent._ranked()`'s full candidate pool (never injecting it, never touching candidate membership), and label every candidate in that pool (1 for the target, 0 otherwise). This produced 53,436 rows from all 200 sessions (0 misses).
2. **Fit** an L2-regularized logistic regression via Newton-Raphson/IRLS (pure numpy, in the offline tool only -- the deployed `starter/agent.py` stays zero-dependency), with positive rows up-weighted to offset the ~1:265 class imbalance.
3. **Validate** with deterministic 5-fold *target-product-disjoint* cross validation -- a fold's held-out target products never appear in that fold's training rows -- so the reported gain is an honest out-of-fold estimate, not a same-data fit.

| | Ranking-gate diagnostic (target rank within its harvested pool, OOF) |
|---|---|
| Rank-1 count | 43 → 67 / 200 |
| Top-10 count | 100 → 179 / 200 |
| Candidate-group MRR | 0.314 → 0.503 |
| Paired MRR delta | +0.189, bootstrap 95% CI [+0.13, +0.24] (10,000 draws) |

| Configuration | HR@10 | MRR | MTTC | Efficiency | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hand-tuned formula (pre-fit) | 1.000 | 0.880 | 2.735 | 0.827 | 0.929 |
| Learned re-ranker, strict OOF | 0.995 | 0.921 | 2.735 | 0.827 | 0.939 |
| Learned re-ranker, all-development fitted (deployed) | 0.995 | 0.924 | 2.735 | 0.827 | 0.940 |

MTTC is identical across all three because it depends only on *set membership* in a turn's top-10, which the confidence guard already governs via the (unweighted) reverse-phrase-index score; the re-ranker only changes *ordering within* that set, which is exactly what MRR measures. One session (`public_0092`, Browsing) regresses from a turn-4/rank-2 hit to a full miss: its target's own constraint phrases (`"95% Polyester, 5% Spandex"`, `"Imported"`, `"Button closure"`) all exceed `_EXACT_HIT_MAX_FANOUT` (346, 13642, and 1954 catalog matches respectively), so `exact_score` stays 0 all session and the ranker falls back to weaker signals, where its large learned coefficients on `catalog_completeness` (+10.18) and `rating_number_scaled` (+5.75) apparently favor more generic, better-reviewed competitors over this specific, thinly-reviewed listing. This regression was stable across an L2 grid (1 to 120) rather than shrinking with stronger regularization, so it reflects a real pattern the fit picked up (plausibly: benchmark ground-truth products skew toward more established listings) rather than fold-specific noise -- a genuine, small, statistically-bounded cost against a much larger, statistically-significant gain (the paired CI on the ranking-gate diagnostic excludes zero by a wide margin).

*Provenance note:* this mechanism was built from scratch against this repo's own agent, catalog, and public sessions. It was prompted by a pasted report describing a "P008A"/"E060" pipeline with fold-disjoint validation and a "target-propensity posterior" -- but no code, data, or artifact matching those names exists anywhere in this repository, and their specific numbers don't correspond to anything measurable here. What's implemented above is an independent, from-scratch application of the *methodology* that report described (learned re-ranking + target-disjoint OOF validation), not a port of unseen code, and every number in this section was measured directly against `evaluator/local_evaluator.py` in this repo.
