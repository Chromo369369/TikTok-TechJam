# E060 — Graded match features, and why fitting them fails

## Status

EVALUATED — PARTIAL KEEP. Full public technical score `0.951775`.
One of three new features shipped. Every attempt to *fit* the weights was
rejected, for a reason this experiment finally isolates.

## Question

E059 established that the target is in the working set at turn 1 in 200 of 200
sessions, that the rank oracle scores `0.992200`, and that reweighting the
existing features cannot close the gap. Its diagnosis was that the features are
coarse set-membership indicators — *does this row belong to the set matching some
extracted gazetteer value* — which cannot say how **well** a row matches what the
shopper actually wrote.

Do graded match features close it, and can their weights be learned?

## Hypothesis

Two rows both carrying "cotton" are identical to every feature we have, and the
oracle says one of them is the target about half the time. Features that grade
the match — how much of what the shopper wrote this row actually contains, and
in which field — should separate them.

## Baseline

E058/E059 shipped: `0.949592` (HR `0.995`, MRR `0.959639`, MTTC `2.790`).
Five-seed mean `0.943769`, SD `0.005332`, worst seed `0.935564`.

## Change

FTS5 already indexes `title`, `features`, `details` and `description` as separate
columns, so all three ideas from E059's next-experiment list collapse into one
mechanism: **BM25 scores rather than BM25 ranks, whole-row and per column.**

`_bm25_ranked` now returns the score alongside the order, and accepts a column
restriction. Scores are normalised against the best hit for that query, so the
feature means the same thing at every turn regardless of how many terms have
accumulated. Three new slots:

| Feature | What it asks |
| --- | --- |
| `F_BM25` | whole-row match, graded instead of by rank |
| `F_TITLE` | `title : (...)` — a term in the title names the product; the same term in a description is small talk |
| `F_SPECTEXT` | `{features details} : (...)` — grades a shopper half-quoting a specification, the case the exact-prefix fingerprint drops entirely |

The per-column routes cost one extra query each and are only consulted when they
carry weight, so a configuration that does not use them pays what it paid before.

## Everything else

Unchanged. The planner, publishing decision, belief, quote channel, self-play,
retrieval, constraint extraction, override handling and repeat suppression all
retain their E058 values. Verified behaviour-neutral at `0.949592` with all three
new weights at zero before anything was tuned.

## Expected

The graded features carry information the set-membership features cannot, so
either direct search or a fit should find weight for them.

## Results

### Direct search, one feature at a time

| Weight | Full score |
| --- | ---: |
| Baseline, all graded at 0 | 0.949592 |
| **`bm25` 0.5** | **0.951775** |
| `bm25` 1.0 | 0.946012 |
| `bm25` 2.0 | 0.947654 |
| `bm25` 4.0 | 0.937950 |
| `title` 0.5 | 0.948527 |
| `title` 1.0 | 0.950191 |
| `title` 2.0 | 0.941600 |
| `spectext` 0.5 | 0.947068 |
| `spectext` 1.0 | 0.944700 |

### Five-seed verification of the survivor

`+0.0022` on one seed is inside this project's noise floor, so it was taken to
five training seeds before adoption.

| Configuration | Mean | SD | Worst seed |
| --- | ---: | ---: | ---: |
| Baseline | 0.943769 | 0.005332 | 0.935564 |
| **`bm25` 0.5** | **0.946506** | **0.004242** | **0.942164** |

Better mean, *lower* spread, and `+0.0066` on the worst seed, winning 4 of 5.
The worst-seed movement is the convincing part: the graded score never lets the
ranking collapse the way rank alone sometimes does.

`bm25 0.5 + title 1.0` was also taken to three seeds and averaged `0.945968` with
SD `0.0069` — below the whole-row feature alone and twice as variable. Rejected.

### Shipped configuration

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 150 | 0.993333 | 0.962778 | 2.920000 | 0.947100 |
| Holdout | 50 | 1.000000 | 0.983333 | 2.460000 | 0.965800 |
| Full | 200 | 0.995000 | 0.967917 | 2.805000 | **0.951775** |

- Buying: n=80, HR 0.987500, MRR 0.941146, MTTC 2.087500
- Browsing: n=80, HR 1.000000, MRR 0.978646, MTTC 2.850000
- Intent override: n=30, HR 1.000000, **MRR 1.000000**, MTTC 4.333333
- Boundary: n=10, HR 1.000000, **MRR 1.000000**, MTTC 3.600000

**192 of 200 sessions convert at rank 1.** One miss (`public_0020`). Intent
override and boundary are now perfect on rank.

Evaluator mode: `0.956485` (dev `0.952575`, holdout `0.968217`). The gap between
the tracks is now `0.0047`, down from `0.020` two experiments ago.

## The fitting result, and the diagnosis

Five surrogate objectives were fitted on the 200 sessions, each with five
target-held-out folds (the fold's sessions *and* every catalog row that is a
target of that fold removed from training entirely).

| Objective | Features | Optimistic | Honest | vs hand-tuned |
| --- | ---: | ---: | ---: | ---: |
| Pairwise logistic | 16 | 0.935600 | 0.930468 | −0.019 |
| Listwise softmax | 16 | 0.944733 | 0.940481 | −0.009 |
| Listwise + contradiction | 25 | 0.939600 | — | −0.010 |
| Listwise + graded | 28 | 0.943354 | 0.939818 | −0.010 |
| Top-1 hardest negative | 28 | 0.886313 | — | −0.063 |
| **Hand-tuned** | 28 | **0.951775** | — | — |

Training fit improved monotonically as features were added — listwise loss
`2.3443` (hand-tuned) → `2.1959` → `2.1928` → `2.1578` — and the score never
followed. The honest-to-optimistic gap stayed at `0.004`, so **memorisation was
never the problem**; the fold discipline works and says so.

### Why: the loss and the reward disagree about what a rank is worth

Running both weight vectors through live sessions and recording where the target
sat in the working set at every turn:

| | target rank 1 | top 3 | top 10 | mean rank |
| --- | ---: | ---: | ---: | ---: |
| Hand-tuned | **0.408** | 0.569 | 0.815 | 14.04 |
| Fitted (listwise, 28 features) | **0.408** | 0.637 | 0.861 | 13.37 |

The fitted vector improved every ranking statistic **except the only one that
pays**. A policy that publishes one row converts on rank 1 and on nothing else,
so likelihood spent dragging a candidate from rank 40 to rank 8 buys exactly
zero. The softmax spreads its mass over ~96 candidates and is delighted to raise
P(target) from .01 to .05 deep in the list; the reward is indifferent.

Attacking the boundary directly did not work either. Hardest-negative mining —
find the strongest competitor under the current weights and push the target above
that one — *reduced* the rank-1 rate from `0.4084` to `0.2672` and scored
`0.886313`. The objective is correct and the optimisation is not: chasing the
current argmax follows outliers, and `pop` collapsed from `0.750` to `0.029`,
destroying the target prior that E058 measured as worth `0.020`.

### What the fitted weights say when they behave

Under listwise shrinkage toward the hand-set values, every weight lands within
about 20% of where it started, the largest moves being `lexical 1.00 -> 0.62` and
`pop 0.75 -> 0.64`. Contradiction weights all fell within `0.03` of zero except
`x:category` at `0.288`. The per-column graded weights came out *negative*
(`title -0.352`, `spectext -0.428`) — a suppressor effect against the whole-row
score they are collinear with, and a sign the fit is exploiting the feature set
rather than learning from it. Only `bm25` at `+0.647` agreed in sign with what
direct search later found, and direct search put it at `0.5`.

## Internal diagnostics

- Rank oracle (publish the target first whenever it is in the working set):
  HR `1.000`, MRR `1.000`, MTTC `1.390`, score `0.992200` — the exact MTTC floor
- Target present in the working set at turn 1: **200 of 200 sessions**
- Target's median rank when present: 2 (p75 6, p90 15)
- Training groups: 524; pairs: 50,304
- Hit rank: 192 at 1, one each at 2 and 3, three at 6, two at 8, one miss
- First-hit turn: 60 / 52 / 32 / 28 / 12 / 3 / 4 / 3 / 2 / 3 across turns 1–10

## Failure cases and taxonomy

- RETRIEVAL_MISS: **1** — `public_0020`, unchanged since E035B in the dossier.
- RERANK_FAILURE: 0 misses; seven sessions convert at ranks 2–8.
- PUBLISH_TOO_NARROW, BAD_QUESTION, REPEAT_WASTE, STATE_ERROR, OVERRIDE_ERROR,
  HARD_CONSTRAINT_VIOLATION, AMBIGUOUS_QUERY: 0.

## Conclusion

**PARTIAL KEEP.** Ship the graded whole-row BM25 feature at weight `0.5`; reject
the per-column routes and every fitted weight vector.

- Score improves `0.949592 -> 0.951775`, five-seed mean `0.943769 -> 0.946506`,
  and the spread narrows.
- The feature is free: the score comes from a query already being run.
- Hit rate holds at `0.995` and MRR rises to `0.967917`.

The larger result is negative and worth stating plainly: **E059's diagnosis was
half right.** The features *were* impoverished, and adding a graded one helped —
but only `0.002`, not the `0.04` the oracle says is available. The rest of the
gap is not reachable by BM25 over a different column, and it is not reachable by
fitting the weights of any feature set tried so far, because the loss that is
easy to optimise is not the loss that pays.

The `RANK_WEIGHTS` machinery, the feature extractor, the listwise objective and
the target-held-out fold protocol are all built and validated. What is missing is
a feature that distinguishes two rows which match the same gazetteer values, and
an objective whose gradient only cares about the top of the list.

## Next experiment

1. **E061 — features that separate near-identical rows.** BM25 over columns is
   still bag-of-words. The two rows the oracle says we confuse both contain
   "cotton"; what differs is which *specific* phrases from the shopper's message
   appear, in what order, and how rare they are. Candidates: IDF-weighted n-gram
   overlap against the row's own text rather than token overlap; character-level
   overlap against the specification index for half-quoted specifications; a
   penalty for candidate text the shopper's message *contradicts*, measured on
   text rather than on gazetteer values (E059's contradiction indicators failed
   because they were gazetteer-level).
2. **E062 — an objective that only sees the top.** Softmax restricted to the
   current top-k candidates, k small, rather than the full list — the gradient
   then cannot buy loss deep in the tail. Hardest-negative mining failed on
   optimisation, not on principle; a top-k softmax is the stable version of the
   same idea.
3. **MTTC remains the largest single term** at `2.805` against a floor of `1.890`,
   worth `+0.018` against MRR's remaining `+0.010`. It has not been attacked yet.
