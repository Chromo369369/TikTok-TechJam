# P008 — Named-Information Exposure and Variant-Slot Audit

This follow-up is development-only. P007D remains the holdout-confirmed
evaluator-track configuration; no P008 holdout execution was performed.

## Pre-registered named-information policy

Starting from P007D/P006C, use:

| Question state | Display limit |
| --- | ---: |
| wildcard (`other`) | 1 |
| `feature` or `material` | 2 |
| other named attribute | 3 |
| no question | 10 |

The split is fixed from the existing answerability evidence, not from a
per-attribute score search. It dispatched on 353 wildcard states, 29
feature/material states, 49 other named states, and 11 no-question states.

## Development result

| Variant | HR@10 | MRR | MTTC | efficiency | score |
| --- | ---: | ---: | ---: | ---: | ---: |
| P007D | .986667 | .922619 | 2.906667 | .809333 | .931986 |
| P008A | .986667 | .943452 | 2.960000 | .804000 | .937169 |

P008A improves the technical score by `.005183`. Its 5,000-draw paired
bootstrap 95% interval is `[.000917, .010631]`, with probability `.9946` of a
positive delta. It has six MRR improvements, three worsened sessions, and 141
ties; HR@10 and hard-constraint violations are unchanged.

This clears the predeclared development continuation threshold. It is recorded
as a development-qualified challenger only, because P007D's holdout has already
been used and a further holdout selection would invalidate the evaluation rule.

## Variant-slot audit

The read-only audit used a deliberately conservative family definition:
normalized exact title, store, and leaf category. Among 50,000 products it found
614 duplicate families (1,276 products). In P007D's 434 displayed development
states, only three states contained an exact duplicate family, consuming four
extra slots total. One was a three-slot brand-question state; the other two were
late ten-slot no-question states.

This is far too sparse to justify a family-deduplication ranking change. Nearer
title similarity would require subjective assumptions about product
interchangeability and risks suppressing the exact target variant, so no dedupe
algorithm was added.
