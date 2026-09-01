---
experiment: "12"
title: "Re-tuning `SCORE_WEIGHTS`'s regularization strength"
type: experiment
technical_score: 0.945854
delta: +0.0004
decision: "Adopted"
summary: "L2 3.0 to 50 after feature count grew to 22"
source: "REPORT.md"
---
# Re-tuning `SCORE_WEIGHTS`'s regularization strength

Every prior fit used `L2_LAMBDA = 3.0`, chosen when the model had 20 features and the sweep across it looked flat. With 22 features now (`distinct_phrase_match_count` and `tfidf_cosine` added since), there's more redundancy between features that a fixed L2 doesn't account for (`exact_score` vs `has_exact_evidence`, `category_hit` vs `category_specificity`) -- worth re-sweeping rather than assuming the old value still holds. A grid from 0.5 to 100 on the target-product-disjoint OOF ranking-gate diagnostic found a real, non-flat optimum this time: rank-1 count 74→79/200 and OOF MRR 0.532→0.548 moving from L2=3 to a plateau at L2=40-65, not the marginal noise the earlier 20-feature sweep showed. Deployed L2=50 (plateau center): end-to-end MRR rose 0.901→0.903 for a technical score of **0.945854**, confirmed by a strict OOF refit at **0.946854** (HR@10 1.000 throughout) -- the OOF number slightly *exceeding* the all-development-fit number this time, which is additional reassurance against overfitting rather than a concern.

The other loose end this warranted re-checking: `_CONFIDENCE_GUARD_LAST_TURN` (still 6, chosen before the ranker had this many features) and whether re-tuned ranking quality shifted its optimal value. Swept 4 through 8 directly against the full evaluator with the new L2=50 weights: every value produced a byte-identical result. Whatever convergence needs the guard to still be active for has already resolved by turn 4 with the current evidence/ranking pipeline, so this parameter isn't binding in that range any more -- there's no further gain available here without a more fundamental change.
