# E060 Strict-OOF Residual Error Audit (E061 gate)

Development-only diagnostic. No holdout run. No champion config changed. No new
prior integrated. E060 artifacts are frozen (SHA256 manifest:
`experiments/diagnostics/E060_freeze_manifest.json`).

## Purpose

Before reconstructing any leave-last-out (LLO) interaction prior, measure where
E060's remaining strict-OOF errors actually come from. The hidden-label
first-union rank oracle is `.975867`; E060 strict OOF is `.957400`; the
residual theoretical gap is `.018467`. This audit classifies the residual and
estimates how much of it any new prior could plausibly recover.

## External-data legality gate (blocked)

- The competition package is derived from **Amazon Reviews 2023** (McAuley Lab),
  per `DATA_ATTRIBUTION.md` and `docs/competition_specification.md`.
- `DATA_ATTRIBUTION.md` permits using the source "for the competition, research,
  and other permitted purposes", so the public source is *attributed but not
  explicitly green-lit for offline interaction preprocessing*, and the raw
  5-core interaction data is **not present** in this workspace (`data/` contains
  only `catalog.jsonl`, `public_set.jsonl`, and local llama.cpp binaries).
- **Conclusion: E061 LLO reconstruction is not executable here.** It cannot be
  tested zero-shot without the source data, and this agent will not fabricate
  access. If the organizer/user later supplies the source aggregates, the gate
  below is the exact test to run first.

## Residual error taxonomy (Section-26 classes)

Recomputed the E060 grouped-OOF target rank at the frozen early-union state from
`E060_early_union_posterior.json` (149 groups) + `E060_folds/fold_0..4.json`.
Non-rank1 residual = 46 sessions + 1 shortlist miss.

Classification (model logit `target - top1` decomposed by feature group; the
group with the most negative contribution is the "culprit"):

| Class | Count | Meaning |
|---|---:|---|
| A — relevance | 29 (63%) | incumbent ordering/dialogue relevance favors the competitor |
| B — propensity | 17 (37%) | static popularity/completeness features favor the competitor |
| C — category prior | 0 | no residual category-prior-only errors |
| D — complete collision | 0 | no observationally-identical pairs |
| E — shortlist miss | 1 (`public_0035`) | target outside reranker shortlist |
| F — hard-safety | 0 | consistent with zero Top-10 hard violations |

Candidate-group MRR oracle if each class were magically fixed (target → rank 1):

- A fixed: `.786338 → .917677`
- B fixed: `.786338 → .868661`
- all fixed: `1.0` (the `.975867` end-to-end rank oracle)

## Headroom flags (the decisive measurement)

For the 46 residual pairs, how often does the *target* beat the E060 top-1 on the
observable static/relevance axes?

| Signal | target wins vs top1 | fraction |
|---|---:|---:|
| rating_number (popularity) | 14 / 46 | **30.4%** |
| relevance (final_score) | 10 / 46 | 21.7% |
| category popularity rank | 5 / 46 | 10.9% |

Within the 17 "propensity-culprit" (Type B) errors, only 3/17 have the target
*more* popular than the competitor — the other 14 are genuine popularity gaps in
the competitor's favor.

## Zero-shot residual gate (proxy)

Section 20 requires a new prior to favor the target in **≥ ~65%** of non-tied
residual pairs before integration. The closest available proxy for the LLO prior
(`L_i`, which is highly correlated with `rating_number`) favors the target in
only **30.4%** of residual pairs — far below the gate. The residual is dominated
by Type A (relevance) errors where the target is *less* relevant and *less*
popular than the competitor, i.e. the dialogue and the incumbent ordering both
point elsewhere.

This does **not** rule out the *orthogonal* LLO residual
`r_i = log(1+L_i) - f(log(1+rating_number))`, which by construction captures
signal uncorrelated with `rating_number`. But it shows:

1. raw popularity is not the bottleneck (E060 already has it, and it points the
   wrong way in 70% of residuals), and
2. the dominant residual is relevance-limited, where any static prior must
   override the dialogue evidence — the least promising regime for a prior.

## Learnable residual ceiling

Most of the `.018467` gap sits in Type A (relevance, ~63%) — addressable only by
a better *dialogue-relevance* model (the "domain-trained ranking" branch, which
the handoff explicitly defers as overfit-prone with 150 labels). The propensity
component a prior would target (Type B) is only ~37% of the residual, and within
it the target is more popular in only ~18%. A defensible upper bound on
"propensity-prior-recoverable" score is therefore well under half of
`.018467`, and the proxy gate gives no evidence it is real.

## Cross-check against the parallel E061 audit

A second, more granular audit (`experiments/e061_residual_target_prior.py` →
`E061_residual_manifest.json`, `E061_residual_target_prior_audit.json`)
independently reconstructs the same frozen OOF ranking (rank1 103 / top10 145 /
MRR .786338) and decomposes the 46 residuals by feature-family margin:

- `both_feature_families_favor_competitor_or_tie`: 27 (58.7%) — target loses on
  relevance *and* static propensity; genuinely hard.
- `propensity_favors_target_relevance_favors_competitor`: 11 (23.9%) — the only
  regime a stronger item prior could address, and even then it must out-weight the
  relevance gap.
- `relevance_favors_target_propensity_favors_competitor`: 8 (17.4%) — a
  relevance-calibration signal, not a prior gap.

Its source phase is also blocked (`source_interaction_prior.available: false`)
pending an official 5-core `user_id,parent_asin,rating,timestamp` file. This is
consistent with the taxonomy and headroom flags above and does not change the
conclusion.

## Recommendation

**Stop algorithmic research; freeze E060.** The single remaining high-value
avenue (a true LLO item prior) is (a) not available in this workspace and
(b) fails the zero-shot proxy gate by a wide margin (30% vs 65%). Do not
integrate a popularity-correlated prior (it duplicates E060's `rating_number`
and points the wrong way). Do not reopen dense/semantic/LLM rankers or exposure
tuning (already closed, no new evidence).

Hold E060 (strict OOF `.957400`) for one explicitly authorized confirmation
run, with the exact frozen config/model/folds, no post-confirmation tuning.
If the organizer later supplies the source LLO aggregates, run the Section-20
zero-shot gate on this same residual dataset before touching E060.

## Artifacts

- `experiments/diagnostics/E060_freeze_manifest.json` (frozen hashes)
- `experiments/diagnostics/E060_residual_error_taxonomy.json` (full residual table)
- `experiments/audit_e060_residual_errors.py` (reproducible audit)
