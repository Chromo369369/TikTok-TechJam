# E058 — Reading the ranking score as a log-posterior

## Status

EVALUATED — KEEP; current best. Full public technical score `0.949592`.

## Question

A rival team reported `0.9769` and described their method only as "some sort of
probability distribution graph". Working backwards from the score, that requires
MRR near `1.0` at MTTC near `2.1` — the target ranked first, almost always,
within about two turns.

Is that reachable by tuning the Monte Carlo planner, or is the planner the wrong
place to be spending effort?

## Hypothesis

The planner is the wrong place, for a reason that can be stated before running
anything: the planner only chooses *which of ten questions to ask*, and the
spread between the best and worst question is bounded. The ranking function
decides where the target lands once the answer arrives, and it was never derived
— it is a hand-weighted linear sum.

Read that sum as what it structurally already is:

```text
score(row) = log P(row is the target)              # a prior over rows
           + sum over evidence of log-likelihood   # what the shopper said
```

Under that reading two defects follow directly:

1. **The prior is incomplete.** `POPULARITY_WEIGHT * log1p(rating_number)` is the
   only prior term; `PRICE_BONUS`, `FEATURE_BONUS` and `RATING_BONUS` are wired
   up at `0.0`, dismissed by an earlier sweep as redundant. Under a *linear
   ranking* they are redundant. Under a *posterior* they are independent log-odds
   and should add.
2. **The category is not used as evidence at all.** It is dissolved into BM25
   tokens, so "novelty socks" matches `novelty OR socks`.

## Baseline

E057 (`0.921754`), the joint question/list-length planner.

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 150 | 0.980000 | 0.915185 | 3.366667 | 0.917222 |
| Holdout | 50 | 0.980000 | 0.945833 | 2.920000 | 0.935350 |
| Full | 200 | 0.980000 | 0.922847 | 3.255000 | 0.921754 |

## Supporting measurements

Taken before implementation, to decide where effort was worth spending.

### The score ceiling this evaluator permits

An intent-override session cannot record a hit until the override lands;
`local_evaluator.evaluate` gates the hit check on `override_applied`. The sampled
override turns are **12 sessions at turn 3 and 18 at turn 4**. Browsing and
boundary sessions open with nothing but a coarse category, and a boundary
session's first question is always rebuffed.

| Bound | MTTC floor | Max score at HR=MRR=1 |
| --- | ---: | ---: |
| Evaluator scripting alone | 1.390 | 0.9922 |
| Plus "a bare category cannot identify a row" | 1.890 | **0.9822** |

`0.9769` therefore requires MTTC `2.155` at MRR `1.0` — within `0.005` of the
achievable floor. It is real, but it is near-perfect play, not a comfortable
margin.

### The target prior is strong and was being discarded

Sessions are drawn from the Clothing 5-core review split, so rows that can be
targets are a distinctive subset of the catalog:

| Signal | Catalog | Targets | Log-odds (nats) |
| --- | ---: | ---: | ---: |
| >= 1000 ratings | 3.1% | 74.5% | +3.19 |
| has a price | 21.1% | 89.0% | +1.44 |
| >= 5 feature bullets | 64.8% | 95.0% | +0.38 |
| average rating >= 4.0 | 67.4% | 92.0% | +0.31 |
| has a description | 52.2% | 44.5% | −0.16 |

Median `rating_number` is 12 across the catalog and 6,846 across targets.

### The category is a retrieval route, not a bag of words

The catalog has 1,115 distinct coarse category nodes, median size 8 rows. The
session target's own node has a median size of 181. Ranking **only** by review
count **within that node**, with no questions asked at all:

| | |
| --- | ---: |
| Target is rank 1 | 35.0% |
| Target is in the top 10 | 81.5% |
| Median target rank | 2 |

E057 converted 19% of sessions at turn 1.

### How identifiable is the target from what is actually disclosed

Pure logical filtering, no semantics: intersect the catalog against each
disclosed constraint (exact spec match where the string is indexable, otherwise
token containment), starting from the named category node.

| Evidence held | Median rows still consistent | Uniquely identified | Within 10 |
| --- | ---: | ---: | ---: |
| Category only (turn 1) | 181 | 0.0% | 3.0% |
| + 1 constraint | 40 | 10.0% | 21.0% |
| + 2 constraints | 3 | 42.5% | 66.5% |
| + 3 constraints | 1 | 56.5% | 82.5% |
| + 4 (whole intent card) | 1 | 73.0% | 93.5% |

Three constraints — one or two questions — reduce 50,000 rows to a median of
one. **No semantic model is needed to reach MRR near 1.0; a calibrated posterior
and a good prior are sufficient.** This is the strongest available evidence that
the rival team's "probability distribution" is a posterior over catalog rows
rather than a language model.

### One lever checked and found dead

`intent_card` appends `budget around ${price}`, which would carry the exact price
— and an exact price selects 0.0082% of the catalog on average against 12.5% for
the agent's 8-quantile budget bin. It is the *last* candidate appended and never
survives the `cleaned[:4]` truncation: it appears in **0 of 200** intent cards.
Not pursued.

## Change

Three changes to the ranking score. The planner is untouched.

**1. Complete the target prior.** `PRICE_BONUS 0.0 -> 2.0`, `FEATURE_BONUS
0.0 -> 1.2`. `RATING_BONUS` stays at `0.0`; it adds nothing over the other two.

**2. Add a category-path retrieval route.** Index each product's taxonomy
suffixes (leaf, leaf+parent, leaf+parent+grandparent) as contiguous phrases, with
information content `log(N / rows under the node)`. At observation time, take the
**longest** phrase in the message that names a catalog node — a shopper naming a
leaf has not also stated its parent as a second wish — and score rows under it by
`CATEGORY_PHRASE_WEIGHT * information`. Those rows also enter the candidate pool
directly, since the lexical query ranks them poorly when the node's words are
common. The node survives an intent override: the shopper is still shopping for
the same kind of thing.

**3. Restructure `score()` as an explicit log-posterior** — prior terms first,
then one log-likelihood-ratio per piece of evidence. Arithmetically identical to
before at equal weights; it is the framing that made defects 1 and 2 visible.

Constants: `PRICE_BONUS 2.0`, `FEATURE_BONUS 1.2`, `CATEGORY_PHRASE_WEIGHT 0.5`,
`CATEGORY_PHRASE_DEPTH 3`, `MAX_CATEGORY_PHRASE_WORDS 8`.

## Everything else

Unchanged. The planner, the belief softmax, the publishing decision, the quote
channel, self-play, retrieval, constraint extraction, spec fingerprinting,
override handling and repeat suppression all retain their E057 values.

## Expected

MRR rises because the ranking is better informed. MTTC falls because the target
reaches rank 1 sooner, so the publishing decision converts earlier. Hit rate
should hold or improve, since both changes add evidence rather than filter.

## Results

- Hit Rate@10: **0.995000** (E057 0.980000)
- MRR: **0.959639** (E057 0.922847)
- MTTC: **2.790000** (E057 3.255000)
- Technical score: **0.949592** (E057 0.921754, **+0.027838**)
- Buying: n=80, HR 0.987500, MRR 0.978125, MTTC 2.050000
- Browsing: n=80, HR 1.000000, MRR 0.931389, MTTC 2.937500
- Intent override: n=30, HR 1.000000, MRR 0.972222, MTTC 4.233333
- Boundary: n=10, HR 1.000000, MRR 1.000000, MTTC 3.200000

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 150 | 0.993333 | 0.951741 | 2.920000 | 0.943789 |
| Holdout | 50 | 1.000000 | 0.983333 | 2.400000 | 0.967000 |
| Full | 200 | 0.995000 | 0.959639 | 2.790000 | 0.949592 |

The gain holds on the untouched holdout (+0.031650 there against +0.026567 on
development).

**190 of 200 sessions convert at rank 1** (E057: 181; the E057 baseline before
the publishing decision: 104). Remaining ranks: one at 2, one at 4, two at 5,
four at 6, one at 9. **One miss.**

First-hit turn: 60 / 56 / 28 / 25 / 12 / 6 / 5 / 4 / 2 / 1 across turns 1–10.
Turn-1 conversions rose from 38 to 60.

### Ablations, one factor removed from the shipped configuration

| Configuration | Full score | Delta |
| --- | ---: | ---: |
| Shipped | 0.949592 | — |
| No publishing decision (always 10 rows) | 0.876520 | −0.073072 |
| Rank-only belief (no score softmax) | 0.900802 | −0.048790 |
| No target prior (price and features at 0) | 0.929306 | −0.020286 |
| No category-path route | 0.932495 | −0.017097 |

### Seed robustness

Five self-play seeds, everything else fixed:

| Seed | Full score |
| --- | ---: |
| 20260828 (shipped) | 0.949592 |
| 7 | 0.943958 |
| 12345 | 0.949252 |
| 999 | 0.935564 |
| 42 | 0.940479 |

Mean `0.943769`, SD `0.005332`, range `0.014027`. **The shipped seed is the best
of the five**, so `0.943769` is the better estimate of the method and `0.949592`
should be read as a favourable draw. (In E057 the shipped seed sat at the mean;
that is no longer true and the difference is worth stating.)

### Evaluator-specialised track (`TECHJAM_EVALUATOR_MODE=1`)

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 150 | 0.986667 | 0.976111 | 2.560000 | 0.954967 |
| Holdout | 50 | 1.000000 | 0.965833 | 2.140000 | 0.966950 |
| Full | 200 | 0.990000 | 0.973542 | 2.455000 | 0.957963 |

The gap between the tracks has narrowed from `0.020` to `0.008`: the better
ranking captures much of what the wildcard channel was supplying.

## Internal diagnostics

Full 200-session run of the shipped configuration.

- Repeats suppressed: 824 (E057: 1,582 — fewer turns are needed)
- Unique products shown: 666, from 962 published row-slots over 557 turns
- Average candidates considered: 512.0
- Overrides detected: 30 (all 30 intent-override sessions)
- No-preference replies: 171
- Responses / planning calls: 557 (E057: 647)
- Rollouts: 97,110 total, **174.3 per planning call** — 82,726 scoring questions
  (~9.23 legal actions x ~18 distinct particles), 14,384 scoring list length
- Question mix: material 245, feature 121, use case 51, color 44, brand 39,
  category 26, other 10, style 10, silent 7, budget 3, size 1
- Published list length by turn (rows: sessions): turn 1 `1:193, 10:7`;
  turn 2 `1:126, 10:14`; turn 5 `1:27, 10:4`; turn 10 `10:2`

## Observations

**The planner was correctly identified as the wrong lever.** Its whole
contribution is bounded: replacing the rollouts entirely with the learned prior
costs `0.014`. The two ranking changes here are worth `0.037` between them, from
a subsystem that had not been revisited since the score was first written.

**"Redundant" is a property of the model, not of the feature.** The earlier
finding that price and feature richness added nothing was correct *under a
linear ranking score*, where the review count absorbs them. Read as independent
log-odds in a prior they are worth `0.020`. This is the most transferable lesson
in the experiment: a feature dismissed under one functional form deserves
re-testing under another.

**Better ranking bought hit rate back.** E057 traded hit rate `0.995 -> 0.980`
for MRR. That trade is now unnecessary: hit rate is back to `0.995` *and* MRR is
`0.960`. The `PUBLISH_TOO_NARROW` failure recorded in E057 (`public_0179`) is
gone, because the target now reaches rank 1 rather than sitting at rank 8.

**The publishing decision is still the single largest contributor** (`0.073`),
and it interacts favourably with better ranking rather than being superseded by
it: publishing ten rows every turn now scores `0.876520` with MRR `0.642`,
against `0.949592` with MRR `0.960`.

**The category route must not be trusted as a filter.** At weight 1.5 the score
falls to `0.901` and at 3.0 to `0.838`, because a shopper whose phrasing lands on
the wrong node can no longer be recovered. `0.5` was chosen over `0.75` and `1.0`
on a three-seed mean where it also had the lowest spread.

## Rejected within this experiment

**Per-attribute constraint weights.** The posterior framing suggests the
constraint bonus should be a log-likelihood ratio specific to each attribute:
size is indexed on 19% of the catalog and material on 64%, so a row missing an
extracted size looks far less guilty than one missing a material, and a flat
bonus asserts they are equally damning. Taking the miss rate as the uncovered
share gives weights from `0.21` (size) to `2.12` (category, brand).

| Configuration | Full score |
| --- | ---: |
| Flat 2.0 (kept) | 0.949592 |
| Per-attribute, scale 1.0 | 0.946575 |
| Per-attribute, scale 1.5 | 0.944029 |
| Per-attribute, scale 2.0 | 0.942614 |
| Per-attribute, scale 2.5 | 0.935550 |
| Per-attribute, scale 3.0 | 0.937650 |

Rejected at every scale. The proxy is wrong: catalog coverage measures how often
the catalog *states* an attribute, not how often our extractor *missed* one that
was present. A row with no recorded size may simply have no size, in which case
the mismatch is genuinely informative. The idea is sound but needs a direct
measurement of extractor recall, which nothing currently produces.

**Exact price matching.** Dead by measurement — see Supporting measurements.

## Failure cases and taxonomy

One miss, and nine sessions that convert below rank 1.

- RETRIEVAL_MISS: **1** — `public_0020`. The long-standing miss, present in every
  champion including E035B in the dossier. Reaches deep rank ~320 and stalls.
- RERANK_FAILURE: **0 misses**, but nine sessions convert at ranks 2–9. Both E057
  rerank failures (`public_0054`, `public_0161`) now convert.
- PUBLISH_TOO_NARROW: **0** — resolved; was 1 in E057.
- BAD_QUESTION, REPEAT_WASTE, STATE_ERROR, OVERRIDE_ERROR,
  HARD_CONSTRAINT_VIOLATION, AMBIGUOUS_QUERY: 0 observed. All 30 overrides
  detected and all 30 override sessions converted.

## Conclusion

**KEEP.**

- Improves full technical score by `0.027838` over E057, and by `0.078466` over
  the agent at the start of this line of work.
- Wins on the untouched holdout by a larger margin than on development.
- Hit rate improves rather than being traded away.
- Uses only catalog fields and the shopper's own words; no hidden target,
  scenario label, or simulator-only signal at runtime.
- Verified through the official entrypoint: `python -m evaluator.local_evaluator`
  reports `recommended_technical_score: 0.949592`.

Caveat carried forward: the shipped training seed is the best of five draws, so
the honest expectation for an unseen split is nearer `0.9438` than `0.9496`.

## Next experiment

1. **E059 — MTTC is now the binding term.** At `2.790` against a floor of
   `1.890`, it is worth `0.018` of score, more than MRR (`0.012`) or hit rate
   (`0.003`). 116 of 200 sessions convert by turn 2 where the floor permits 170.
   The evidence needed arrives a full turn before conversion happens.
2. **E060 — extractor recall.** Needed both to revive per-attribute evidence
   weights and to know whether the remaining nine off-rank-1 sessions are
   ambiguity or extraction failure.
3. **E061 — a real posterior.** The score now has the right shape but its weights
   are still tuned constants rather than estimated log-likelihood ratios. Making
   them estimates would remove `BELIEF_TEMP` as a free parameter, since a
   calibrated posterior needs no temperature.
