# E059 — Learning the ranking weights from real sessions

## Status

EVALUATED — **REJECT**. Shipped configuration unchanged at `0.949592`.
The experiment's value is in what it rules out, and in the oracle measurement
that motivated it.

## Question

The ranking weights are hand constants chosen by grid sweeps on the public 200.
Can they instead be *learned* from real sessions — show a model the labelled
targets and let it order the pool — rather than tuned by hand?

And is ordering even the right place to spend effort?

## Hypothesis

Two claims, tested in order.

1. **Ordering is where everything is.** If the target is already in the pool the
   agent retrieves, then every point between our score and a perfect one is
   ordering — not retrieval, not question choice, not list length.
2. **A model fitted to labelled sessions will order better than hand-set
   constants**, because it can find weights no human would sweep for, in
   particular the per-attribute weights E058 failed to derive from coverage.

## Baseline

E058 shipped: `0.949592` (HR `0.995`, MRR `0.959639`, MTTC `2.790`).

## The oracle measurement

Rank oracle: at every turn, if the target is anywhere in the 512-row working set
the agent has already built, publish it first. Retrieval, questions and list
length are untouched; only the ordering of rows already in hand changes.

| | HR@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: |
| Shipped | 0.995 | 0.959639 | 2.790 | 0.949592 |
| **Rank oracle** | **1.000** | **1.000** | **1.390** | **0.992200** |

The oracle misses nothing and converts 170 of 200 sessions on turn 1; the other
30 are the intent-override sessions, which convert at turns 3 and 4 exactly as
the evaluator's scripting forces. `1.390` is the absolute MTTC floor computed in
E058, so the oracle is not merely good — it is *exactly optimal*.

**The target is in our working set at turn 1 in every single session.** Retrieval
is solved. All `0.0426` of the remaining gap is ordering, and hypothesis 1 is
confirmed as strongly as it can be. When the target is present its median rank is
2, p75 6, p90 15 — we are close, and consistently not first.

## Change tested

A linear ranker over the score's own feature vector, fitted on the 200 public
sessions. `_ranked_ids` was first refactored so the score is an explicit
`weights . features` dot product (`RANK_WEIGHTS`, `F_*` layout) — verified
behaviour-neutral at `0.949592` — so a fitted vector is a drop-in replacement.

**Features (16, later 25).** Prior: `log1p(rating_number)`, has-price, feature
richness, average rating. Evidence: quoted-specification information, category
node information, nine per-attribute constraint-match counts, `-log(bm25 rank)`.
Later extended with nine contradiction indicators — the row records *some* value
for the attribute and it is not the one named.

**Training data.** Replay all 200 sessions under the current policy; at each turn
where the target is in the working set, emit one ranking problem: the target
against the 48 highest-scoring competitors plus 48 sampled from the rest. 524
groups, 50,304 pairs.

**Leakage control.** Five folds. For each, the fold's sessions *and every catalog
row that is a target of that fold* are removed from training entirely — as a
positive and as a negative — before fitting; the resulting weights are then
scored on that fold only. Reported as **honest**, against the **optimistic**
number from fitting on all 200 and scoring all 200. If those diverge, the model
is memorising which rows are targets rather than what a target looks like.

## Results

| Fit | Objective | Optimistic | Honest (out-of-fold) | vs baseline |
| --- | --- | ---: | ---: | ---: |
| Pairwise logistic | pair accuracy | 0.935600 | 0.930468 | −0.019 |
| Listwise softmax | P(target first) | 0.944733 | 0.940481 | −0.009 |
| Listwise + contradiction | P(target first) | 0.939600 | — | −0.010 |
| **Hand-tuned (shipped)** | — | **0.949592** | — | — |

Training-set fit improved in every case. It simply did not transfer to score:

| | Pairwise accuracy | Listwise loss |
| --- | ---: | ---: |
| Hand-tuned weights | 0.9275 | 2.3443 |
| Pairwise fit | **0.9475** | — |
| Listwise fit | 0.9376 | **2.1959** |
| Listwise + contradiction | 0.9376 | 2.1928 |

Also tested and rejected: uniform rescaling of the fitted vector (the norm ratio
to the hand-tuned vector is `0.995`, so there was nothing to correct) at
`0.946570`, and re-tuning `BELIEF_TEMP` around the fitted weights (`0.5` →
`0.944022`, `0.6` → `0.945958`).

## Observations

**Memorisation was not the problem.** The honest-to-optimistic gap is `0.005`
(pairwise) and `0.004` (listwise). The fold discipline works, and it says the
model is learning row-shape rather than row-identity — which is the good outcome,
and it still lost.

**Optimising pair accuracy actively hurts.** The pairwise fit improved pair
accuracy by `0.020` and cost `0.014` of score, because pair accuracy pays equally
for beating the 400th candidate and the 1st while the reward pays only for
beating the 1st. It also let `rating` — a near-constant feature — run to `13.065`,
a direction that moves the loss and not the outcome. **A ranking model must be
fitted to the metric's shape, and here that shape is "came first".**

**The listwise objective is the right one and still lost.** Softmax over the
candidate list is exactly the posterior the score is meant to be, and its
likelihood is literally "the target ranked first". With shrinkage toward the
hand-tuned weights the fitted vector is sane — every weight lands within ~20% of
its hand-set value, the largest moves being `lexical 1.00 -> 0.62` and
`pop 0.75 -> 0.64`. Loss improved `2.3443 -> 2.1959`; score fell `0.005`.

**That near-agreement is the finding.** A fit that starts from a sane prior,
optimises the right likelihood, and is honestly validated lands on essentially
the hand-tuned weights. **The hand-tuned constants are already near-optimal for
these features.** The remaining `0.043` to the oracle is not recoverable by
reweighting them.

**So the bottleneck is the feature set, not the fitting and not the weights.**
The features are coarse set-membership indicators: *does this row belong to the
set matching some extracted gazetteer value*. They cannot express how *well* a
row matches what the shopper actually wrote. Two rows both carrying "cotton" are
indistinguishable to every feature we have, and the oracle says one of them is
the target roughly half the time.

**Contradiction is not the missing signal.** Nine indicators for "records a
different value" moved the loss by `0.003` and cost `0.005` of score. Whatever
separates the target from its near-neighbours, it is not that they conflict.

## Failure cases and taxonomy

Not applicable — the change was rejected before shipping and the shipped miss
profile is unchanged from E058 (one miss, `public_0020`, RETRIEVAL_MISS).

## Conclusion

**REJECT** the learned ranker. Nothing changed in the shipped agent; `python -m
evaluator.local_evaluator` still reports `0.949592`.

Three things are now established and should not be re-litigated:

1. **Retrieval is solved.** The target is in the working set at turn 1 in 200 of
   200 sessions. Do not spend effort on recall.
2. **Ordering is the entire remaining gap**, worth `0.043` against an oracle of
   `0.992200`.
3. **Reweighting the current features cannot close it.** Two objectives, with and
   without contradiction features, with scale and temperature correction, all
   converge to roughly the hand-tuned weights and score at or below them.

The `RANK_WEIGHTS` refactor is kept: the score is now an explicit weights-times-
features dot product, so a future fit is a drop-in, and the nine contradiction
slots stay wired at zero with the negative result recorded at the constant so the
zero is not misread as untested. That misreading is exactly what cost us `0.020`
before E058, when `PRICE_BONUS` sat at zero labelled "redundant".

## Next experiment

**E060 — richer match features, then refit.** The fitting machinery from this
experiment (feature extraction, listwise objective, target-held-out folds) is
built and validated; it needs better inputs. Candidates, in order of expected
value:

1. **Graded text overlap** between the disclosed constraint text and the
   candidate's own text, IDF-weighted — replacing binary set membership. This is
   the direct fix for "two rows both carrying cotton are indistinguishable".
2. **Partial specification match.** A quoted specification only counts today if a
   20-character prefix matches exactly; near-misses score nothing. An n-gram
   overlap score against the specification index would grade them.
3. **Field-specific matching.** A match in the title is stronger evidence than one
   in the description; the score does not currently know which field it hit.

Re-run this experiment's fold protocol once those exist. The honest-versus-
optimistic gap of `0.004` establishes that the protocol is trustworthy, so the
next fit can be believed.
