---
Status: CLOSED / REJECTED
Branch: Counterfactual exposure-policy learning
Decision: Do not train or evaluate a simulator-derived exposure policy
Date: 2026-08-29
---

# Policy Learning — Final Decision

## Reason

Synthetic counterfactual policy learning requires sufficiently
deployment-like target and transition distributions. That prerequisite was not
met. Simulator-derived action values or labels would therefore encode source
shift that cannot be trusted as deployment-oriented policy supervision.

## Evidence

### R101 — severe static distribution mismatch

R100's synthetic targets were unlike released development. Mean target
popularity percentile was `.502573` synthetic versus `.957580` released, initial
Top-10 rate was `.750` versus `.220`, mean session length was `7.09` versus
`2.83`, and substantive-answer rate was `.218` versus `.517`. A grouped
diagnostic discriminator separated the sources with logistic AUC `.971867` and
depth-3 tree AUC `.938533`.

This invalidated the original simulator population as a basis for exposure
policy learning.

### R102 — sensible policy geometry restored, calibration still failed

R102 replaced the visibly uniform target population with 500 unique non-public
targets matched to released-development category and global popularity-decile
margins. On complete frozen sessions, K006C led the predefined fixed-policy
matrix and was no longer strongly dominated by fixed k10:

| Policy | Technical score |
| --- | ---: |
| K006C | .797061 |
| fixed k1 | .733000 |
| fixed k3 | .770420 |
| fixed k5 | .784430 |
| fixed k10 | .785907 |

This restored sensible exposure-policy geometry, but not source calibration.
The category×popularity distribution retained TV `.214667` and JS `.156672`
bits; session-level source discrimination and the `4.44` versus `2.83` turn
length gap remained material.

### R102D — residual transition/dynamics shift remains

R102D used one equal-weight row per session and five-fold target-grouped cross
validation. Static information remained strongly source-identifying, while a
trajectory-only discriminator that explicitly excluded popularity, category,
and target-static metadata still achieved logistic AUC `.715260`.

Reliable target-static reweighting closed only `19.4%` of the session-length
gap. The larger apparent `81.8%` closure from category×tail weighting was not
decision-grade: it covered only `71.3%` of released mass and reduced the frozen
500-session sample to effective sample size `42`.

The raw survival decomposition localized the dynamics gap. Turns 2–5 account
for `.988000` of the `1.613333`-turn difference, or `61.2%`.

Two requested uncertainty/information analyses were not recoverable from the
frozen artifacts: per-target outcomes for fixed-k policies and R102 per-turn
question/answer traces were not retained. They were not recreated because doing
so would require forbidden fresh R102 rollouts. This missing provenance is an
additional reason not to use the matrix as policy-training evidence.

## Conclusion

**Current simulator is unsuitable for training deployment-oriented
counterfactual exposure policies.** R102 showed that target-population repair
can restore reasonable fixed-policy ordering, but R102D did not establish that
the remaining sequential behavior is deployment-like. Static mismatch is still
strong, trajectory-only separation remains material, and adequately supported
reweighting does not explain most of the session-length gap.

This is a terminal rejection of this policy-learning branch, not a pause for
more simulator tuning.

## Frozen actions

- Do not start R103 or R104.
- Do not generate new R102 dialogues or counterfactual rollouts.
- Do not fit, label, select, or evaluate an exposure policy from synthetic
  simulator trajectories.
- Do not alter K006C or P007D under this branch.
- Do not use offline target rank, ASIN, or hidden target information as a
  runtime feature.
- Do not run a public evaluation to revisit this decision.

Future retrieval or ranking experiments must be treated as independent runtime
mechanisms with their own frozen design and evidence. They do not reopen this
simulator-policy-learning branch.

## Record

- `R100_counterfactual_validation.md`
- `R101_R102_calibration.md`
- `R102D_residual_calibration.md`
- `R102D_residual_calibration.json`

R102D's documented operator-session public-set inspection exception remains
part of the provenance record. No holdout observation entered its features,
models, weights, or decision; the branch is rejected on the archived
released-development/R102 evidence above.
