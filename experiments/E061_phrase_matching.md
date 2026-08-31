# E061 — Matching the shopper's wording, not their vocabulary

## Status

EVALUATED — KEEP; current best. Full public technical score `0.958363`.

## Question

E059 and E060 established that retrieval is finished (the target is in the
working set at turn 1 in 200 of 200 sessions), that the rank oracle scores
`0.992200`, and that the target's median rank when present is **2**. Something
separates the target from the row immediately above it, and nothing in the score
can see it.

E060 added graded BM25 and found `0.002` of the `0.040` available. What is the
rest?

## Hypothesis

Every feature in the score is a bag of words. `query_terms` is a *set* — it
remembers that the shopper said "machine" and "washable" and forgets that they
said them together. Two cotton t-shirts that both contain every word the shopper
used are therefore identical to every feature we have, and the tie is broken by
review count, which is a coin flip.

Contiguous wording should break it. A row that contains "machine washable" **as
the shopper said it** is the row being described; a row that happens to contain
"machine" in one bullet and "washable" in another merely shares vocabulary.

The secondary prediction: **MTTC should improve at the same time and for free.**
The policy publishes one row, so it converts only when it is first. Being right
sooner *is* converting sooner — MRR and MTTC are not two problems.

## Baseline

E060 shipped: `0.951775` (HR `0.995`, MRR `0.967917`, MTTC `2.805`).
Three-seed mean `0.949387`, SD `0.0030`.

## Change

Accumulate the contiguous token n-grams of every customer message
(`PHRASE_MIN_WORDS = 2` to `PHRASE_MAX_WORDS = 4`, most recent
`MAX_PHRASES = 40`) alongside the existing bag of tokens, and score candidates by
a BM25 query over those phrases.

The implementation is three lines of query construction, because quoting a
multi-word string in FTS5 *is* a phrase query — `_bm25_ranked` already quotes
each term it is given, so passing phrases instead of tokens asks the stricter
question through the same code path.

One query answers all three parts of what E060 said was missing:

| Question | Answered by |
| --- | --- |
| Which phrases does this row account for? | the match itself |
| How rare are they? | BM25's inverse document frequency |
| Where do they sit? | the index already weights a title hit 6x a description hit |

Nothing else changed. Verified behaviour-neutral at `0.951775` with the weight at
zero before tuning.

## Everything else

Unchanged. Planner, publishing decision, belief, quote channel, self-play,
retrieval, constraint extraction, spec fingerprinting, category route, target
prior, override handling and repeat suppression all retain their E060 values.

Phrases are kept across an intent override, matching the existing treatment of
`query_terms`, rather than cleared like `spec`. Not separately tested.

## Expected

MRR rises as ties break correctly. MTTC falls as a consequence, not as a separate
fix. Hit rate holds — the feature adds evidence rather than filtering.

## Results

- Hit Rate@10: **0.995000** (unchanged)
- MRR: **0.980208** (E060 `0.967917`)
- MTTC: **2.660000** (E060 `2.805000`)
- Technical score: **0.958363** (E060 `0.951775`, **+0.006588**)
- Buying: n=80, HR 0.987500, MRR 0.981250, MTTC 2.100000
- Browsing: n=80, HR 1.000000, MRR 0.989583, MTTC 2.650000
- Intent override: n=30, HR 1.000000, MRR 0.975000, MTTC 4.066667
- Boundary: n=10, HR 1.000000, MRR 0.912500, MTTC 3.000000

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 150 | 0.993333 | 0.981944 | 2.720000 | 0.956850 |
| Holdout | 50 | 1.000000 | 0.975000 | 2.480000 | 0.962900 |
| Full | 200 | 0.995000 | 0.980208 | 2.660000 | **0.958363** |

**195 of 200 sessions convert at rank 1.** One at 2, one at 4, one at 6, one at
8, and one miss.

First-hit turn: 58 / 57 / 36 / 27 / 10 / 3 / 3 / 1 / 4 / 0 across turns 1–10.

**The secondary prediction held.** MRR and MTTC moved together off one change:
`0.968 -> 0.980` and `2.805 -> 2.660`. No MTTC-specific mechanism was added.

### Weight selection

| Weight | Full (shipped seed) | Three-seed mean | SD | HR |
| --- | ---: | ---: | ---: | ---: |
| 0.0 | 0.951775 | 0.949387 | 0.0030 | 0.9933 |
| 1.0 | 0.955975 | 0.952496 | 0.0057 | 0.9950 |
| **3.0** | **0.958363** | **0.956610** | **0.0013** | **0.9950** |
| 4.0 | 0.955279 | 0.957764 | 0.0040 | 0.9933 |
| 6.0 | 0.954092 | 0.952083 | 0.0039 | 0.9917 |

Every non-zero weight beat zero on every seed tested. `4.0` has a mean `0.0012`
higher than `3.0` and three times the spread; `3.0` was taken for equal-best hit
rate and an SD of `0.0013`, the most stable configuration measured on this
project. Above `6` the feature decays as one rare phrase starts outvoting the
rest of the evidence.

### Ablations, one factor removed (matched build)

| Configuration | Full score | Delta |
| --- | ---: | ---: |
| Shipped | 0.958363 | — |
| No publishing decision (always 10 rows) | 0.875950 | −0.082413 |
| No category-path route | 0.948020 | −0.010343 |
| No graded whole-row BM25 | 0.951438 | −0.006925 |
| **No phrase feature** | 0.951775 | −0.006588 |

### Seed robustness

| Seed | Full score |
| --- | ---: |
| 20260828 (shipped) | 0.958363 |
| 7 | 0.956127 |
| 12345 | 0.955339 |
| 999 | 0.946531 |
| 42 | 0.945031 |

Mean `0.952278`, SD `0.005418`, worst `0.945031`. The shipped seed is again the
best of five, so `0.952278` is the better estimate for an unseen split.

### Evaluator-specialised track (`TECHJAM_EVALUATOR_MODE=1`)

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 150 | 0.993333 | 0.982167 | 2.493333 | 0.961450 |
| Holdout | 50 | 1.000000 | 0.975000 | 2.080000 | 0.970900 |
| Full | 200 | 0.995000 | 0.980375 | 2.390000 | 0.963813 |

The gap between the tracks is now `0.005`, and the two now have **identical hit
rate, identical misses and near-identical MRR** — the wildcard channel's entire
remaining advantage is `0.27` of a turn in MTTC. Three experiments ago the gap
was `0.020` and it was a ranking advantage. It is now purely a speed advantage,
which is a much weaker claim on the private set.

## Internal diagnostics

- Rank oracle unchanged at `0.992200`; retrieval still 200 of 200 at turn 1
- Hit rank: 195 at 1, one each at 2, 4, 6, 8; one miss
- Sessions converting by turn 2: 115 of 200 (floor permits 170)
- Cost: one extra FTS5 query per turn, only when the weight is non-zero

## Failure cases and taxonomy

- RETRIEVAL_MISS: **1** — `public_0020`, unchanged since E035B in the dossier.
- RERANK_FAILURE: 0 misses; four sessions convert at ranks 2–8, down from seven.
- PUBLISH_TOO_NARROW, BAD_QUESTION, REPEAT_WASTE, STATE_ERROR, OVERRIDE_ERROR,
  HARD_CONSTRAINT_VIOLATION, AMBIGUOUS_QUERY: 0.

Boundary MRR fell from `1.000` to `0.912500` — one of ten sessions now converts
below rank 1. On a ten-session slice that is a single session and not
interpretable; recorded rather than acted on.

## Conclusion

**KEEP.**

- Improves full technical score by `0.006588` over E060 and `0.087237` over the
  agent at the start of this line of work.
- Three-seed mean improves `0.949387 -> 0.956610` with the spread *narrowing* to
  `0.0013`.
- Hit rate holds at `0.995`; MRR reaches `0.980208`.
- Uses only catalog text and the shopper's own words. No hidden target, scenario
  label, or simulator-only signal at runtime.
- Verified through the official entrypoint: `python -m evaluator.local_evaluator`
  reports `recommended_technical_score: 0.958362`.

The result validates E059's diagnosis in the form E060 could not: the missing
information was never *more* text matching, it was **contiguity**. The same
corpus, the same index and the same BM25 scorer produce `0.007` more score purely
by being asked whether the words appeared together.

It also settles the MRR/MTTC question. They were one problem, and one change
moved both.

## Next experiment

**E062 — MTTC is now two thirds of everything left.** At `2.660` against a floor
of `1.890` it is worth `+0.0154`, against `+0.0060` for MRR and `+0.0025` for hit
rate. 115 of 200 sessions convert by turn 2 where the floor permits 170.

Unlike previous rounds this is no longer downstream of ranking: MRR is `0.980`,
so when the agent is going to be right it is already right. The remaining MTTC is
sessions where the evidence genuinely has not arrived yet, which makes it a
question about the *question policy* and the publishing decision — the two things
this line of work has deliberately not touched since E057.

Two concrete candidates:

1. **Ask the identifying question first.** Measured in E059: asking `other` first
   yields text the fingerprint resolves in 55.3% of sessions, against 40.5% for
   `material` — but the planner asks `material` 245 times and `other` 10. The
   catalog-only customer model cannot see that difference, and forcing it would
   be evaluator-specific. Making the *robust* model aware that open questions
   draw longer answers is not.
2. **Revisit the publishing menu now that ranking is strong.** `SHOW_OPTIONS` was
   fixed at `(1, 10)` when MRR was `0.65`. At MRR `0.98` the cost of publishing
   two rows instead of one has changed, and the trade has not been re-measured.
