---
experiment: "13"
title: "Feature audit: a real training bug, and a structurally dead feature"
type: experiment
technical_score: 0.948464
delta: +0.0026
decision: "Adopted"
summary: "Found override_hit untrainable: harvest missed the override gate"
source: "REPORT.md"
---
# Feature audit: a real training bug, and a structurally dead feature

Asked directly whether the reorder algorithm was "fully optimized," the honest answer was no -- among other gaps, several `SCORE_WEIGHTS` entries sat at exactly 0.0 (`substring_hit`, `budget_score`, `has_budget_context`, `override_hit`), worth auditing rather than assuming they're either fine or wasted. Measured each feature's activation rate across the harvested training rows directly: `substring_hit`, `budget_score`, and `has_budget_context` were **0.00% active across all 53,439 rows** -- not rare, never fired once.

For budget, this is a real, structural fact about the customer simulator on this catalog, not a bug: `_sim_intent_card` always appends the `"budget around $X"` phrase *last* among a product's candidate list, after material/colour and every flattened feature/detail -- for it to ever land within `cleaned[:4]` (the only slice `customer_reply` can ever disclose from) a product would need three or fewer other candidate phrases total, which essentially never happens on this catalog. Budget genuinely cannot be disclosed here; `budget_score`/`has_budget_context` are correctly weighted at zero because the simulator never gives them anything to act on. `substring_hit` is mostly obsolete for a related but different reason: it was the original weak fallback for a phrase the reverse-phrase index didn't recognize at all, but the later `exact_hit_count` mechanism (see the multi-phrase-evidence section above) now absorbs almost every case that used to fall through to it.

`override_hit` was a different story -- and a real bug. Instrumenting the 30 public Intent Override sessions directly showed `harvest_dataset`'s hit-detection check (`if target in ranked:`) was missing the same `override_applied` gate `evaluate()` uses: **all 30 sessions were being harvested from a turn *before* the override even landed**, a state the real evaluator would never score as a hit. Consequently `override_hit` had zero representation in 53K+ training rows -- untrainable, not merely unhelpful. One-line fix (`if override_applied and target in ranked:` in `tools/fit_reranker.py`), confirmed after the fix that `override_hit` now activates on 10.7% of rows (15.0% of positive/target rows) as expected.

Re-harvesting and re-running the L2 sweep on the corrected data showed a materially better optimum across the board even before considering `override_hit` specifically (OOF rank-1 74→90-93, MRR 0.548→~0.60 depending on L2) -- confirming the training-data bug, not just the missing feature, was suppressing quality broadly. The isolated ranking-gate diagnostic kept improving up to L2≈150, but tracking end-to-end score directly (rather than trusting that diagnostic, per the lesson from the last tuning round) showed a real precision/HR tradeoff past L2≈50: HR@10 dipped to 0.995 at L2=35-40 despite the higher ranking-gate MRR, and L2=150's higher isolated MRR translated to a *lower* end-to-end score (0.946889) than L2=50's 0.948464. Deployed L2=50: **HR@10 1.000, MRR 0.911, technical score 0.948464**, confirmed by a strict target-product-disjoint OOF refit at **0.947927**.
