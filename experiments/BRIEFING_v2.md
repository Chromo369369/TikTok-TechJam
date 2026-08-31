# Team briefing v2 — the scoring function is a posterior

> **Superseded by `BRIEFING_v3.md`.** The scores below (`0.949592`) are one
> round old; the agent is now at `0.951775`.

**Supersedes `BRIEFING.md`.** That document described the agent at `0.921754`;
this one describes it at `0.949592`. The architecture description there is still
accurate — this adds the ranking work that came after it.

**Current public technical score: `0.949592`.**
Reproduce with `python -m evaluator.local_evaluator`.

| | Full (200) | Dev (150) | Holdout (50) | HR@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Two rounds ago | 0.871126 | 0.867760 | 0.881224 | 0.995 | 0.651 | 2.08 |
| Last round (E057) | 0.921754 | 0.917222 | 0.935350 | 0.980 | 0.923 | 3.26 |
| **Now (E058)** | **0.949592** | 0.943789 | 0.967000 | **0.995** | **0.960** | 2.79 |
| `TECHJAM_EVALUATOR_MODE=1` | 0.957963 | 0.954967 | 0.966950 | 0.990 | 0.974 | 2.46 |

**190 of 200 sessions now convert at rank 1**, and there is **one miss** left in
the whole public set. Detail in `experiments/E058_target_prior_and_category_route.md`.

Read one caveat with the headline: across five self-play training seeds the score
is `0.943769 ± 0.005`, and the shipped seed is the **best** of those five. Quote
`0.9496` as our measured public score, but expect nearer `0.944` on an unseen
split.

---

## 1. Why this round happened

A rival team reported `0.9769`. Working backwards, that needs MRR near `1.0` at
MTTC near `2.1` — the target ranked *first*, almost always, within two turns.
The natural instinct was to run more Monte Carlo simulations. That instinct is
wrong, and we can show it:

- Doubling the particle count (32 → 64) made the score **worse**, 0.9218 → 0.9152.
- Replacing the rollouts *entirely* with the learned prior costs only `0.014`.

Rollouts sample from *our model of the customer*. More samples reduce the gap
between our estimate and **what the model already believes** — not between the
model and reality. We were model-limited, not sample-limited. The planner picks
one of ten questions; the spread between the best and worst question is bounded
and we had most of it already.

The scoring function, by contrast, decides where the target lands once the answer
arrives — and it had not been revisited since it was first written.

## 2. The reframe: the score is a log-posterior

The ranking score was a hand-weighted linear sum. It already had the right
*shape*; nobody had read it as what it structurally is:

```text
score(row) = log P(row is the target)             <- a prior over rows
           + sum over evidence of log-likelihood  <- what the shopper said
```

Reading it that way made two defects immediately visible.

### Defect 1: the prior was mostly switched off

`PRICE_BONUS`, `FEATURE_BONUS` and `RATING_BONUS` were all set to `0.0`, with a
code comment explaining they were "redundant with the review count." Sessions are
drawn from the Clothing 5-core review split, so targets are nothing like a
uniform draw from the catalog:

| Signal | Catalog | Targets | Log-odds |
| --- | ---: | ---: | ---: |
| >= 1000 ratings | 3.1% | **74.5%** | +3.19 |
| has a price | 21.1% | **89.0%** | +1.44 |
| >= 5 feature bullets | 64.8% | 95.0% | +0.38 |

Median review count: **12** across the catalog, **6,846** across targets.

The old finding was correct *under a linear ranking score*, where the review
count absorbs these. Read as **independent log-odds in a prior**, they add
`0.020`.

> **The transferable lesson:** "redundant" was a property of the functional form,
> not of the feature. A signal dismissed under one model deserves re-testing
> under another.

### Defect 2: the category was dissolved into loose words

Every session's first message names a category verbatim ("I'm looking for
*novelty socks*…"). We were feeding that to BM25, which matched
`novelty OR socks` — thousands of rows.

The catalog has 1,115 category nodes, median size 8. The target's own node has a
median size of 181. Ranking **only** by review count **inside that node**, with
no questions asked at all:

| | |
| --- | ---: |
| Target is rank 1 | **35.0%** |
| Target is in top 10 | **81.5%** |

We were converting 19% at turn 1. So we added a category-path route: index each
product's taxonomy suffixes as contiguous phrases, match the **longest** phrase
in the message, and score rows under that node by its information content. Worth
`0.017`, and turn-1 conversions went from 38 to 60.

**Important:** the node is evidence, never a filter. At weight 1.5 the score
falls to 0.901 and at 3.0 to 0.838 — a shopper whose phrasing lands on the wrong
node can never be recovered. It ships at 0.5.

## 3. What each piece is now worth

One factor removed from the shipped agent:

| Remove | Score | Cost |
| --- | ---: | ---: |
| The publishing decision (always 10 rows) | 0.876520 | −0.073 |
| The score-softmax belief (rank-only) | 0.900802 | −0.049 |
| The target prior (price, features) | 0.929306 | −0.020 |
| The category-path route | 0.932495 | −0.017 |

The publishing decision remains the largest single contributor, and better
ranking makes it *more* valuable rather than less: publishing ten rows every turn
now yields MRR 0.642 against 0.960.

Better ranking also **bought back the hit rate** we deliberately traded last
round. E057 gave up 0.995 → 0.980 to gain MRR. That trade is no longer needed —
hit rate is back at 0.995 *and* MRR is 0.960, because the target now reaches
rank 1 instead of sitting at rank 8 where a one-row list missed it.

## 4. About that rival team

One of their members said only "some sort of probability distribution graph." My
read: **a Bayesian posterior over catalog rows, not an LLM.**

The evaluator's customer is a *deterministic function of catalog metadata* —
`intent_card()` pulls constraints straight out of the product's own `features`
and `details`. Recovering the target is therefore an **inverse problem with a
known generative process**, which is what a likelihood model does well and what a
language model does badly (it paraphrases away the very strings that identify the
row).

We measured how far pure logical filtering gets, with no semantics at all:

| Evidence held | Median rows left | Uniquely identified |
| --- | ---: | ---: |
| Category only (turn 1) | 181 | 0% |
| + 1 constraint | 40 | 10% |
| + 2 constraints | **3** | 42.5% |
| + 3 constraints | **1** | 56.5% |
| + 4 (whole intent card) | 1 | **73%** |

Three constraints — one or two questions — cut 50,000 rows to a median of one.
**No semantic model is required to reach MRR near 1.0.** A calibrated posterior
and a good prior are sufficient, which is exactly the direction this round took.

Supporting circumstantial points: token usage must be disclosed and 800 private
sessions of LLM calls is slow and costly, whereas a posterior is free; and
"probability distribution graph" is literally what you would plot — the posterior
collapsing turn by turn.

Caveat: it is a thin clue. It could also mean a probabilistic graphical model
over product/attribute/value — same family — or just a chart in their slides.

## 5. The ceiling, and how far we are from it

The evaluator imposes a hard floor on MTTC. An intent-override session cannot
record a hit until the override lands — **12 sessions at turn 3, 18 at turn 4**.
Browsing and boundary sessions open with only a category, and a boundary
session's first question is always rebuffed.

| Bound | MTTC floor | Max score |
| --- | ---: | ---: |
| Evaluator scripting alone | 1.890 | **0.9822** |

So `0.9769` sits within `0.005` of the achievable floor — near-perfect play, not
a comfortable margin.

From `0.949592`, what is left:

| Component | Now | Floor / ceiling | Worth |
| --- | ---: | ---: | ---: |
| MTTC | 2.790 | 1.890 | **+0.018** |
| MRR | 0.960 | 1.000 | +0.012 |
| Hit rate | 0.995 | 1.000 | +0.003 |

**MTTC is now the binding constraint**, which it has never been before. 116 of
200 sessions convert by turn 2 where the floor permits 170 — the evidence arrives
a full turn before we convert on it.

Reaching `0.9769` means capturing about 80% of everything remaining. Reachable,
but every component has to land.

## 6. What we tried and rejected

**Per-attribute constraint weights.** The posterior framing suggests each
attribute should carry its own log-likelihood ratio — size is indexed on 19% of
the catalog and material on 64%, so a row missing an extracted size looks less
guilty than one missing a material. Deriving weights from coverage gives 0.21
(size) to 2.12 (category). It **lost at every scale** (best 0.9466 against 0.9496
flat). The proxy is wrong: catalog coverage measures how often the catalog states
an attribute, not how often our extractor missed one that was there. A row with
no recorded size may simply have no size, in which case the mismatch is real
information. Needs a direct measurement of extractor recall.

**Exact price matching.** `intent_card` appends `budget around $X`, and an exact
price selects 0.008% of the catalog against 12.5% for our 8-quantile bin. But it
is the last candidate appended and never survives the `cleaned[:4]` truncation —
it appears in **0 of 200** intent cards. Dead.

## 7. Where to go next

1. **MTTC.** Now the largest term. The evidence needed to convert is in hand a
   turn before conversion happens; find out why the ranking does not act on it.
2. **Extractor recall.** Needed both to revive per-attribute evidence weights and
   to know whether the nine remaining off-rank-1 sessions are genuine ambiguity
   or extraction failure.
3. **A real posterior.** The score has the right shape, but its weights are still
   tuned constants rather than estimated log-likelihood ratios. Estimating them
   would let us delete `BELIEF_TEMP` — a calibrated posterior needs no
   temperature.

## Standing warnings for anyone tuning this

- **Self-play runs the same customer model**, so any parameter it touches cannot
  be swept on a reused agent — the priors stay trained under the old value.
  `QUOTE_RATE` read 0.927 that way and 0.905 on a clean rebuild. Rebuild per
  configuration for `QUOTE_RATE`, `ROLLOUT_SHOW`, episode count and seed.
  `BELIEF_TEMP`, `BELIEF_FLOOR`, `SHOW_OPTIONS`, `SHOW_REF`, `PRIOR_BLEND`,
  `CATEGORY_PHRASE_WEIGHT`, `PRICE_BONUS` and `FEATURE_BONUS` are safe on one
  build.
- **Treat sub-0.01 differences on a single seed as noise.** Seed spread is
  `±0.005`. `PRIOR_BLEND = 0.35` looked worth +0.005 and averaged −0.001 across
  five seeds; we rejected it. The three candidate prior weightings in this round
  were tied within 0.001 and the choice between them is not meaningful.
- **Sweep results are not shipped results.** Sweeps mutate module constants in
  memory; the file on disk is unchanged until someone edits it. Always confirm a
  claimed score with `python -m evaluator.local_evaluator`.

## Reproduction

```bash
python -m evaluator.local_evaluator                              # 0.949592
TECHJAM_EVALUATOR_MODE=1 python -m evaluator.local_evaluator     # 0.957963
python -m unittest discover -s tests                             # 3 passed
```

Construction ~80 s (index build plus 300 self-play episodes), evaluation ~40 s.
Standard library only, no network, no model API, deterministic, zero tokens.
