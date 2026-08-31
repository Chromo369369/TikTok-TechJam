# Team briefing v3 — retrieval is solved; ordering is everything

> **Superseded by `BRIEFING_v4.md`.** The scores below (`0.951775`) are one
> round old; the agent is now at `0.958363`.

**Supersedes `BRIEFING_v2.md`** (`0.949592`). Read v2 for the architecture, which
is unchanged. This adds what we now know about where the remaining points are —
and, more usefully, where they are *not*.

**Current public technical score: `0.951775`.**
Reproduce with `python -m evaluator.local_evaluator`.

| | Full (200) | Dev (150) | Holdout (50) | HR@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Three rounds ago | 0.871126 | 0.867760 | 0.881224 | 0.995 | 0.651 | 2.08 |
| E057 publishing decision | 0.921754 | 0.917222 | 0.935350 | 0.980 | 0.923 | 3.26 |
| E058 score as posterior | 0.949592 | 0.943789 | 0.967000 | 0.995 | 0.960 | 2.79 |
| **E060 graded match (now)** | **0.951775** | 0.947100 | 0.965800 | **0.995** | **0.968** | 2.81 |
| `TECHJAM_EVALUATOR_MODE=1` | 0.956485 | 0.952575 | 0.968217 | 0.990 | 0.970 | 2.48 |

**192 of 200 sessions convert at rank 1. One miss in the entire public set.**
Intent-override and boundary scenarios are now at MRR `1.000`.

Across five self-play seeds the score is `0.946506 ± 0.0042`; the shipped seed is
a good draw. Quote `0.9518` as measured, expect nearer `0.947` on an unseen split.

---

## 1. The single most useful measurement we have

**Rank oracle.** At every turn, if the target is anywhere in the 512-row pool the
agent already built, publish it first. Nothing else changes — same retrieval,
same questions, same list length.

| | HR | MRR | MTTC | Score |
| --- | ---: | ---: | ---: | ---: |
| Us | 0.995 | 0.968 | 2.81 | 0.9518 |
| **Rank oracle** | **1.000** | **1.000** | **1.39** | **0.9922** |

Two things follow, and they should shape everyone's effort:

**Retrieval is solved. Stop working on it.** The target is in our working set at
turn 1 in **200 of 200 sessions**. There is no recall problem left to find.

**Every remaining point is ordering.** `0.0404` of it. And `1.39` is the absolute
MTTC floor the evaluator's own scripting imposes, so the oracle isn't merely
good — it is exactly optimal. When the target is present its median rank is **2**:
we are close, and consistently not first.

## 2. What we shipped this round

FTS5 indexes `title`, `features` and `details` as separate columns, so we added
BM25 **scores** rather than just ranks, whole-row and per column. Rank is a
robust but flattened summary; the score separates a row carrying every word the
shopper used from one carrying only the commonest of them.

Only the whole-row score survived, at weight `0.5`:

| | Mean over 5 seeds | SD | Worst seed |
| --- | ---: | ---: | ---: |
| Without | 0.943769 | 0.0053 | 0.9356 |
| **With** | **0.946506** | **0.0042** | **0.9422** |

Better mean, lower spread, `+0.0066` on the worst seed, winning 4 of 5. It is
free — the score comes from a query we already run. Title-only and
features/details routes both lost and each costs an extra query per turn.

## 3. What we ruled out, and why it matters

We tried hard to *learn* the ranking weights from the labelled sessions rather
than hand-set them. Five objectives, each with five folds where the fold's
sessions **and every catalog row that is a target of that fold** were removed
from training entirely:

| Objective | Optimistic | Honest | vs hand-tuned |
| --- | ---: | ---: | ---: |
| Pairwise logistic | 0.9356 | 0.9305 | −0.019 |
| Listwise softmax | 0.9447 | 0.9405 | −0.009 |
| + contradiction features | 0.9396 | — | −0.010 |
| + graded features | 0.9434 | 0.9398 | −0.010 |
| Top-1 hardest negative | 0.8863 | — | −0.063 |

Training loss improved monotonically. The score never followed.

**Memorisation was never the problem** — the honest-to-optimistic gap held at
`0.004` throughout, so the fold discipline works and confirms the model learns
row-shape, not row-identity. It just loses anyway.

### The reason, which is worth internalising

Running both weight vectors through live sessions and recording where the target
actually sat:

| | **rank 1** | top 3 | top 10 | mean rank |
| --- | ---: | ---: | ---: | ---: |
| Hand-tuned | **0.408** | 0.569 | 0.815 | 14.04 |
| Fitted | **0.408** | 0.637 | 0.861 | 13.37 |

The fitted model improved **everything except the only thing that pays.** We
publish one row, so we convert on rank 1 and nothing else. Likelihood spent
dragging a candidate from rank 40 to rank 8 is worth a great deal to a softmax
over 96 candidates and exactly nothing to the reward.

> **If you fit anything on this problem, fit the top of the list.** A loss that
> is easy to optimise is not the loss that pays, and the gap between them here is
> the whole result.

Attacking the boundary directly (push the target above its single strongest
competitor) is the right idea and blew up on optimisation: the rank-1 rate *fell*
from `0.408` to `0.267` and `pop` collapsed from `0.750` to `0.029`, destroying
the target prior E058 measured as worth `0.020`. A top-k softmax is the stable
version of the same idea and has not been tried.

## 4. Where the remaining 0.040 is

| Component | Now | Floor / ceiling | Worth |
| --- | ---: | ---: | ---: |
| **MTTC** | 2.805 | 1.890 | **+0.018** |
| MRR | 0.968 | 1.000 | +0.010 |
| Hit rate | 0.995 | 1.000 | +0.003 |

**MTTC is the largest single term and has not been attacked yet.** 112 of 200
sessions convert by turn 2 where the floor permits 170.

For MRR, the honest statement after this round is that E059's diagnosis was
*half* right. The features were impoverished, and a graded one helped — but by
`0.002`, not the `0.040` the oracle says is there. The rest is not reachable by
BM25 over a different column. The two rows the oracle says we confuse both
contain "cotton"; what differs is which *specific* phrases from the message
appear, in what order, and how rare they are. That is the feature nobody has
built yet.

## 5. Where to go next

1. **MTTC.** Largest term, untouched, and the evidence needed to convert is
   demonstrably in hand a turn before we act on it.
2. **Features that separate near-identical rows.** IDF-weighted n-gram overlap
   against the row's own text; character-level overlap against the specification
   index for half-quoted specifications; text-level (not gazetteer-level)
   contradiction — gazetteer-level contradiction was tried and carries no signal.
3. **A top-k objective.** All the machinery — feature extraction, listwise fit,
   target-held-out folds — is built and validated. It needs a gradient that
   cannot buy loss in the tail.

## Standing warnings

- **Sweeps are not shipped results.** Sweeps mutate module constants in memory;
  the file on disk is unchanged until someone edits it. Confirm every claimed
  score with `python -m evaluator.local_evaluator`. This has bitten us once.
- **Rebuild for anything self-play sees**: `QUOTE_RATE`, `ROLLOUT_SHOW`, episode
  count, seed. `BELIEF_TEMP`, `BELIEF_FLOOR`, `SHOW_OPTIONS`, `SHOW_REF`,
  `PRIOR_BLEND`, `CATEGORY_PHRASE_WEIGHT` and everything in `RANK_WEIGHTS` are
  safe on one build.
- **Seed spread is ±0.004–0.005.** Anything under `0.01` on one seed is noise
  until five seeds say otherwise. Three separate candidate changes have died this
  way; one (`bm25`) survived and shipped.
- **A zero weight is not an untested weight.** `PRICE_BONUS` sat at `0.0` labelled
  "redundant" and was worth `0.020`. Where a weight is zero *because it was
  measured*, the constant now says so.

## Reproduction

```bash
python -m evaluator.local_evaluator                              # 0.951775
TECHJAM_EVALUATOR_MODE=1 python -m evaluator.local_evaluator     # 0.956485
python -m unittest discover -s tests                             # 3 passed
```

Standard library only, no network, no model API, deterministic, zero tokens.
Experiment records: `E057_publishing_decision.md`,
`E058_target_prior_and_category_route.md`, `E059_learned_ranker.md`,
`E060_graded_lexical_features.md`.
