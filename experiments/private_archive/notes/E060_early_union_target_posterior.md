# E060 — Early-Union Target-Propensity Posterior

E060 is a development-only challenger built on P008A/P006C. No public holdout
session was executed, and no champion configuration was changed.

## Why this branch was opened

On P008A's archived development trajectories, the hidden-label rank-1 oracle
over the naturally occurring candidate union scores `.975867`, compared with
P008A's `.937169`. The target is naturally present in the frozen early Top-200
pool for 149 of 150 sessions. This localizes the remaining large headroom to
ordering already-retrieved products, rather than retrieval, question choice, or
recommendation-count tuning.

## Frozen protocol

- Take the first post-override development state where the target naturally
  occurs in P008A's target-independent pre-popularity Top-200.
- Never inject the target and never change candidate membership.
- Fit a regularized logistic posterior with catalog-visible/runtime-observable
  fields only. There is no ASIN, sample ID, target rank, future response, hidden
  intent, or evaluator-only feature.
- Features cover baseline rank and lexical scores; rating count and catalog
  completeness; and the opening message's longest exact multi-component
  category path when its catalog posting has at most 200 products.
- Use deterministic five-fold target-product-disjoint validation. Every held-out
  target product is removed from all training candidate rows for that fold.
- Apply the qualified model only inside the already-frozen pre-popularity
  Top-200 and reapply the existing confirmed-hard-constraint partition after it.

The archived rank gate passes strongly: OOF rank-1 count rises from 83 to 103,
Top-10 from 125 to 145, and candidate-group MRR from `.649518` to `.786338`.
Its paired MRR delta is `+.136820`, bootstrap 95% CI
`[+.090407, +.184133]`, with 60 improved and 4 worsened groups.

## End-to-end development result

| Configuration | HR@10 | MRR | MTTC | Efficiency | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| P007D | .986667 | .922619 | 2.906667 | .809333 | .931986 |
| P008A | .986667 | .943452 | 2.960000 | .804000 | .937169 |
| E060 strict OOF | .993333 | .965556 | 2.446667 | .855333 | **.957400** |
| E060 all-development fitted | .993333 | .968889 | 2.440000 | .856000 | .958533 |

The strict OOF gain over P008A is `+.020231`. A 10,000-draw paired
session/target bootstrap gives a 95% interval of
`[+.010517, +.032667]`, with 43 improved, 5 worsened, and 102 unchanged
sessions. All five folds record zero Top-10 confirmed-hard-constraint
violations. Excluding held-out target products from training changes no
end-to-end result.

The all-trained result is reported only as the deployable-development model;
the `.957400` strict OOF result is the credible generalization estimate.

## Remaining branches

Exposure and question tuning are closed for this ranker. The post-ranker
target-aware exposure diagnostic found only four beneficial changes and
`+.000900` score headroom. The residual ambiguity audit found only four states
with target tie size above one, and none were eligible question decisions, so
the one-step question oracle produced no rows.

The only large measured ceiling left is the hidden-label `.975867` early-union
rank oracle. Reaching more of it requires a better observable item-target prior,
not another hand-tuned `k` schedule. The defensible next independent source is
the benchmark's underlying leave-last-out interaction history, if competition
rules and locally available data permit it. It must be evaluated with the same
target-product-disjoint protocol before any single holdout confirmation.

The label-permutation falsification and predeclared feature ablations reinforce
that conclusion. Across 100 within-group label permutations, the best null model
is `.277816` MRR below the archived ordering; the real model is `.136820` above
it. Removing popularity/propensity features eliminates `.112691` of the full
model's OOF MRR, whereas the relevance-only remainder improves the archive by
just `.024129`. See `experiments/notes/E060_attribution_controls.md`.

## Artifacts

- `experiments/early_union_posterior.py`
- `experiments/models/E060_early_union_posterior.json`
- `experiments/diagnostics/E060_early_union_posterior.json`
- `experiments/diagnostics/E060_end_to_end_oof_development.json`
- `experiments/diagnostics/E060_end_to_end_oof_paired.json`
- `experiments/runs/E060A_p008_target_propensity_development.json`
- `experiments/diagnostics/E060_residual_question_oracle.json`
- `experiments/diagnostics/E060A_runtime_profile.json`
- `experiments/diagnostics/E060_attribution_controls.json`
- `experiments/notes/E060_attribution_controls.md`

Decision: **DEVELOPMENT-QUALIFIED CHALLENGER; HOLDOUT NOT RUN**.
