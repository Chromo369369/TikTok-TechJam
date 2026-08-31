# P001 — Catalog popularity prior

## Question

Does the participant-visible `rating_number` signal retain value once it changes
actual recommendations, repeat exclusion, and session dynamics?

## Baseline

E035B with E057 normalization hardening. Dialogue state, question policy,
candidate membership, candidate limits, retrieval, and base ranking are frozen.

## Fixed family

- P001A: E035B control, explicit `popularity_order: none`.
- P001B: rank the existing E035B candidate set by descending `rating_number`.
- P001C: retain E035B order except inside score blocks spanning at most `.25`
  final-score points; use descending `rating_number` within each block.
- P001D: reciprocal-rank fusion of E035B candidate rank and popularity rank,
  with the predeclared `k=60`.

Only the order used to select recommendations changes. Question selection still
receives the original E035B order. All ties end with ASIN ordering.

## Acceptance

Run the fixed 150-session development split sequentially. Consider holdout only
for a clear improvement over E035B without material scenario regression.

## C4 motivation

`rating_number` is participant-visible. Its frozen-pool signal was strong, but
the Naive Bayes likelihood increment failed holdout; P001 tests popularity alone
as a separate hypothesis.

## Results

| Variant | Development score | Holdout score | Decision |
|---|---:|---:|---|
| P001A control | .821151 | — | Control reproduced E035B. |
| P001B pure popularity | .759802 | — | Reject: 379 Top-10 hard-constraint violations. |
| P001C near-tie | .831913 | — | Better, but below P001D. |
| P001D rank/popularity RRF | .866824 | .858864 | Keep and promote robust. |

P001D raises development MRR from `.557614` to `.639190` and lowers MTTC from
`2.973333` to `2.08`. On holdout it raises MRR from `.601746` to `.652214` and
lowers MTTC from `3.02` to `2.34`, while HR@10 remains `.98`. All scenario hit
rates improve or remain unchanged on both splits. Its hard-constraint diagnostic
is 21 dev / 6 holdout, so retain it as an explicit monitored risk; this is far
below the pure-popularity failure and did not create a scenario HR regression.
