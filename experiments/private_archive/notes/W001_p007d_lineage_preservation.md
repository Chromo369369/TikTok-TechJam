# W001 — P007D Lineage-Preservation Audit

Development-only audit. P007D, P008A, and E060 config bytes were frozen in
`W001_lineage_manifest.json`; no configuration was changed, no holdout ran,
and no model was trained.

## Instrumentation and micro-tests

Every new state update now records a target-independent
`semantic_state_fingerprint` (constraints, intent version, asked/known/no-
preference sets, and pending question only) and an `exposure_rule_id` describing
the display-limit decision. The fingerprint intentionally excludes the shown
and repeat inventories so an exposure difference cannot masquerade as semantic
state drift.

Ten deterministic, input-only wildcard micro-tests cover atomic facts,
multi-fact text, no-preference replies, negation, overrides, repeated details,
and soft preferences. All three frozen lineages selected the same question and
semantic state on those tests.

## Archived wildcard replay

The archived P007D public-development user-message trajectories were replayed
from reset through P008A and the appropriate strict-OOF E060 fold model. The
comparison covers all 353 archived states whose P007D selected question was
`other`.

| Replay | Semantic-state drift | Question drift | Exposure-action drift | Slate drift |
| --- | ---: | ---: | ---: | ---: |
| P008A | 0 / 353 | 0 / 353 | 0 / 353 | 0 / 353 |
| E060 | 0 / 353 | 0 / 353 | 0 / 353 | 167 / 353 |

P007D's `wildcard_aware` and P008A/E060's `named_information_aware` rules have
different provenance labels, but both deterministically choose wildcard `k=1`.
Those 353 label differences are therefore not policy-action differences.

The 167 E060 slate changes are expected consequences of E060's target-
propensity ranking layer. They do not indicate a change to wildcard semantics,
question selection, repeat behavior, or exposure budget.

## Decision

**STOP.** There is zero semantic or exposure-policy divergence. The prerequisite
for F0--F3 is not met, so no new variants and no strict-OOF factorial evaluation
were run. E060 already preserves the P007D wildcard mechanism; this branch
offers no independent score avenue.
