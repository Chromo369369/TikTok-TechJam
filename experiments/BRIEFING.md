# Team briefing — how the shopping agent works, and what changed

> **Superseded by `BRIEFING_v2.md`.** The scores below (`0.921754`) are one round
> old; the agent is now at `0.949592`. The architecture description here is still
> accurate — read it first, then v2 for the ranking work that came after.

**Current public technical score: `0.921754`** (was `0.871126`).
Reproduce with `python -m evaluator.local_evaluator`.

| | Full (200) | Dev (150) | Holdout (50) | HR@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Previous agent | 0.871126 | 0.867760 | 0.881224 | 0.995 | 0.651 | 2.08 |
| **Current agent** | **0.921754** | 0.917222 | 0.935350 | 0.980 | 0.923 | 3.26 |
| `TECHJAM_EVALUATOR_MODE=1` | 0.941821 | 0.943628 | 0.936400 | 0.980 | 0.955 | 2.73 |

Everything lives in one file, `starter/agent.py`. Standard library only, no
network, no model API, deterministic. Full experiment record in
`experiments/E057_publishing_decision.md`; project history in
`TECHJAM_PROJECT_DOSSIER.md`.

---

## 1. What we are being scored on

Each session hides one product out of a frozen 50,000-row catalog. Every turn we
may ask one clarifying question and return a ranked list of **up to** ten
`parent_asin` values. The session ends the moment the target appears in that
list, or after turn 10.

```text
TechnicalScore = 0.50 * HitRate@10 + 0.30 * MRR + 0.20 * Efficiency
Efficiency     = clip((11 - MTTC) / 10, 0, 1)
```

Decomposed per session, a conversion is worth:

```text
0.5 + 0.3/rank + 0.2 * (11 - turn) / 10
```

**That formula is the single most important thing in this document.** Read off a
few values:

| | turn 1 | turn 2 | turn 4 | turn 6 |
| --- | ---: | ---: | ---: | ---: |
| **rank 1** | 1.00 | 0.98 | 0.94 | 0.90 |
| **rank 2** | 0.85 | 0.83 | 0.79 | 0.75 |
| **rank 5** | 0.76 | 0.74 | 0.70 | 0.66 |

Converting at rank 1 on turn 6 beats converting at rank 2 on turn 1. Turns are
cheap; rank is expensive. That asymmetry drives the whole design.

---

## 2. What the agent does each turn

```text
user message
     |
[1]  observe        -> update dialogue state (constraints, quoted specs,
     |                 no-preference flags, override detection)
     |
[2]  retrieve+rank  -> score all candidates, keep the top 512 as a working set
     |
[3]  believe        -> turn those scores into P(this candidate is the target)
     |
[4]  plan           -> Monte Carlo rollouts choose BOTH the question to ask
     |                 AND how many rows to publish
     |
[5]  publish        -> return that many rows + the question
```

Step 4 choosing the list length is the new part. Everything else predates this
round of work.

### [1] Observation — building dialogue state

From each message we extract, cumulatively across the session:

- **Attribute constraints** for nine attributes (category, material, color, size,
  style, brand, budget, use case, feature), via fixed phrase lists, a contextual
  size regex, whole-store-name matching for brand, and price binning for budget.
- **Quoted specification strings.** If the user's wording matches a product's own
  feature or detail text (≥20 characters, matched on a 120-character prefix so a
  truncated quote still lands), that is near-identifying — see §4.
- **No-preference flags**, which retire an attribute from the question set.
- **Intent overrides** ("actually, ignore my earlier…"), which clear accumulated
  constraints, quoted specs, and the shown-set.

Constraints are **evidence to rank by, never filters**. Attribute extraction is
incomplete (size is indexed on 19% of the catalog, style on 26%), so intersecting
would permanently delete any target whose indexed values happen to miss a phrase
the shopper used, with no way back.

### [2] Retrieval and ranking

Candidates come from BM25 over an in-memory SQLite FTS5 index, plus any row named
by a quoted spec, plus rows satisfying every constraint, plus a popularity
backfill. They are then scored on one log-rank scale:

```text
score = 1.0  * quoted-spec information
      + 2.0  * (number of constraints satisfied)
      - log(bm25 rank)
      + 0.75 * log1p(rating_number)
```

The popularity term is not a hack: sessions are drawn from the Clothing 5-core
review split, so rows that *can* be targets are a distinctive subset — median
target carries ~6,600 ratings against a catalog median of 12.

Products already published are dropped permanently. If one had been the target
the session would have ended, so each is a proven non-target.

### [3] Belief — the part that was wrong until this round

The planner needs `P(candidate i is the target)`. It used to assume a fixed curve
over *rank* — position 1 always got the same probability whether we had a unique
spec quote or nothing but a bare category.

The ranking score already knows the difference, and we were throwing it away.
Measured over development dialogues:

| Score gap between #1 and #2 | Turns | P(#1 is the target) |
| --- | ---: | ---: |
| under 1 | 347 | **0.118** |
| 1–2 | 87 | 0.264 |
| 2–3 | 45 | 0.600 |
| 3–4 | 25 | 0.520 |
| 4 or more | 63 | **1.000** |

The belief is now a softmax of that score (over a small rank-decayed floor). It
fits about 14x better per observation than the rank-only prior — mean
log-likelihood `-3.31` against `-5.95`.

### [4] Planning — the Monte Carlo simulation

For every legal question, and then for every allowed list length, the planner:

1. samples **hypothesis targets** ("particles") from the belief;
2. for each, simulates the conversation forward up to **4 further turns** using a
   synthetic customer (§3);
3. averages the realised session score across particles;
4. blends that 75/25 with a self-play-trained linear prior;
5. takes the best.

All actions and lengths reuse **one particle set and one pre-drawn table of
random numbers** (common random numbers), so comparisons are low-variance even at
small particle counts.

The working set is represented as a big-integer bitset: filtering a hypothetical
answer is one bitwise AND, and a candidate's rank is a population count. That is
what makes this many rollouts affordable in pure Python.

**Measured volume, per full 200-session run:**

| | |
| --- | ---: |
| Planning calls (= turns) | 647 |
| Rollouts total | 127,280 |
| **Rollouts per turn** | **196.7** |
| ...scoring questions | ~166 (≈9.1 legal questions x ≈18 particles) |
| ...scoring list length | ~30 (2 lengths x surviving particles) |
| Turns simulated per rollout | up to 4 |
| Rollouts per session | ~640 |

Note `ROOT_PARTICLES = 32` is the number of *draws*; duplicates collapse, so the
effective count is ~18 distinct hypotheses per turn. Separately, 300 self-play
episodes run **once at construction**, not per session.

### [5] Publishing — the new decision

For each candidate length `k`:

```text
EV(k) = sum over ranks <= k of  P(rank) * session_return(rank, turn)   # convert now
      + sum over ranks >  k of  P(rank) * rollout(pool minus top k)    # buy a turn
```

The head is summed exactly (a handful of terms); the tail is the same rollout
used for questions, re-run against the pool that publishing `k` rows would leave.
A wider list gives survivors better ranks next turn — that benefit has to be paid
for out of the ranks it locks in now.

**The menu is `(1, 10)` only.** Intermediate lengths were tested and cost 0.010:
hedging into four or five rows converts at a middling rank, which the reward
never pays for. Either name the product or buy another turn. The widest option is
always available, so the last turn and any diffuse belief still get full coverage.

This is **not a fixed schedule.** On turn 1 the planner publishes one row in 188
sessions and ten rows in 12. Observed distribution:

| Turn | 1 row | 10 rows |
| ---: | ---: | ---: |
| 1 | 188 | 12 |
| 3 | 99 | 11 |
| 5 | 30 | 8 |
| 9 | 3 | 8 |
| 10 | 0 | 7 |

---

## 3. How the simulated customer is built

This is the heart of the method, and it is built **only from catalog rows** — it
never mirrors the released evaluator's phrasing or scripting.

**At construction**, for all 50,000 rows, we extract per-attribute values from the
*entire* searchable text (title, features, description, details, store,
categories — not just features and category names), and derive two statistics per
attribute:

- **coverage** — fraction of the catalog carrying any value for it;
- **fragmentation** — distinct values per covered row. Near 0 is a small
  controlled vocabulary (26 colors); near 1 is nearly an identifier (19,000
  stores), where a phrase the shopper uses is unlikely to land on exactly the
  value the index holds.

**At runtime**, asking attribute `a` about hypothesised target `t` runs this
sequence:

1. **If the question is `other`** — with probability 0.5 the customer engages at
   all; then a random attribute `t` actually has and has not already declined is
   selected. Modelled as a weak, generic "anything else?" channel *on purpose*
   (see §5).
2. **If `t` has no value for `a`** — the customer has no preference. The attribute
   is retired for the rest of that rollout.
3. **Reliability gate**, `0.25 + 0.6 * answerability(a)` — otherwise they answered,
   but not in a form the index can use. `answerability` is a Beta posterior that
   starts from catalog fragmentation and is then **updated online from the real
   session**, every time a live reply does or does not yield an extractable value.
   This is the one part of the customer learned from actual conversations.
4. **Quote channel** *(new)* — with probability `QUOTE_RATE = 0.30` on free-text
   attributes, they phrase it in the product's own words and the pool collapses to
   that row. See §4.
5. **Miss branch**, probability `min(.45, .04 + .25*(1-coverage) + .5*fragmentation)`
   — they name a value the index does not hold for `t`, so every *other* candidate
   that does carry the attribute is **promoted above it**. This is how the model
   prices the cost of an over-specific question: the target gets pushed down, not
   deleted.
6. **Otherwise** — one of `t`'s own values is named and the pool is intersected
   with the rows carrying it.

Subsequent questions inside a rollout come from a cheap stochastic default policy
weighted by a self-play-learned per-action advantage times its coverage in the
surviving pool.

### Things easy to get wrong about this

- It is built from the **whole** searchable text, not just features and categories.
- It has **two learned components**, not only catalog statistics: the online
  answerability posterior and the self-play-trained rollout policy.
- It explicitly models **failure** — declining, unusable phrasing, and naming a
  value we do not have (which actively hurts the target).
- Reranking is **not** a separate step after the question. The candidate set is
  re-scored every turn; the planner reads that ranking rather than producing it.

---

## 4. Why the quote channel matters

Before adding it, the planner had **no mechanism that could move a rank-300
candidate to rank 1**. Every rollout said continuing was near-worthless, so it
published ten rows to convert at a poor rank now rather than a good rank later —
and the publishing decision did nothing. Adding the list-length action alone
scored 0.868, i.e. no better than baseline.

The fix is measured off the catalog, not the harness:

- 50,000 rows produce 206,022 distinct indexable specification strings;
- **90.7%** of those strings occur on exactly one row;
- **99.0%** of rows carry at least one;
- **95.6%** of rows carry one that is globally unique.

So a shopper who elaborates in the product's own words has effectively named it,
and `_spec_index` already resolves that. The build order was: list-length action
alone `0.868`, plus the quote channel `0.893`, plus the calibrated belief at its
maximum-likelihood temperature `0.910`, then `0.922` after tuning the temperature,
the length menu and the assumed future list length.

**These three changes are one mechanism, not three wins.** Removing just the
publishing decision from the current agent gives 0.865 — *below* the 0.871
baseline. The belief and the quote channel are mildly harmful when the list
length is fixed; they exist to serve the length decision.

---

## 5. The two tracks

Following the project's existing discipline (E035B vs E022 in the dossier), the
evaluator-specialised policy is quarantined rather than shipped.

The released simulator answers `other` by reading back undisclosed intent-card
entries **verbatim**, and those entries are the product's own feature and detail
strings. In that harness `other` is not a vague prompt — it is close to an oracle.
The specification says the organizer may add paraphrasing to the private harness,
so we do not build on it.

`TECHJAM_EVALUATOR_MODE=1` swaps in a second customer model where `other` is
high-bandwidth and answers in catalog text. Nothing tells the planner to prefer
`other` — changing what that channel is *worth* is enough for it to select
`other` in 453 of 556 questions on its own. It scores 0.941821.

The 0.020 gap is our measurement of how much of the public score is specific to
this simulator. In the default track `other` is used 8 times out of 556.

---

## 6. Honest costs and open risks

**Hit rate fell 0.995 to 0.980.** Deliberate: worth −0.008 of score against +0.082
from ranking. Four misses, all Buying:

| Session | Classification | Detail |
| --- | --- | --- |
| `public_0020` | RETRIEVAL_MISS | Stalls at deep rank ~320 all session |
| `public_0054` | RERANK_FAILURE | Deep rank 17–100, never converts, no spec match |
| `public_0161` | RERANK_FAILURE | Deep rank 22–68, never converts, no spec match |
| `public_0179` | **PUBLISH_TOO_NARROW** | Sat at rank 8–9 on turns 6–7 while we published one row |

`public_0179` is the direct cost of the change. Forcing the wide list from turn 5
recovers hit rate to 0.990 at an identical score (0.9224) — a one-line change if
we decide hit rate is judged separately.

**Structural risk.** The gain assumes the harness ends a session at the *first*
appearance of the target, which is what the released evaluator does and what the
specification states. If a private harness scored best-rank-across-all-turns
instead, short lists would only lose and the right setting would be
`SHOW_OPTIONS = (10,)`. This is a one-constant reversal, worth confirming.

**Training variance was larger than any modelling effect.** Across five self-play
seeds the old trainer spread 0.051 of score (worst seed 0.876). Averaging the
weights over the second half of training and shrinking rarely-tried action
advantages cut that to 0.023 and raised the mean from 0.912 to 0.921. The shipped
seed now sits at the five-seed mean, not above it.

**Methodological warning for anyone tuning this next.** Self-play runs the same
customer model, so any parameter it touches **cannot** be swept on a reused agent
— the priors stay trained under the old value. `QUOTE_RATE` read 0.927 that way
and 0.905 on a clean rebuild. Rebuild per configuration for `QUOTE_RATE`,
`ROLLOUT_SHOW`, episode count and seed. `BELIEF_TEMP`, `BELIEF_FLOOR`,
`SHOW_OPTIONS`, `SHOW_REF` and `PRIOR_BLEND` are safe to sweep on one build.

Also treat sub-0.01 differences on a single seed as noise. `PRIOR_BLEND = 0.35`
looked worth +0.005 and averaged −0.001 across five seeds; we rejected it.

---

## 7. Where to look next

1. **The two rerank failures.** `public_0054` and `public_0161` sit at deep rank
   20–100 for entire sessions with no spec evidence and an unexhausted question
   channel. A question policy that targets acquiring a *spec-quotable* disclosure,
   rather than maximising the candidate split, is the most direct attack.
2. **Hit-rate insurance.** A belief-driven late widening rule (widen when the
   leader's score margin has not improved for N turns) should dominate both the
   current behaviour and the fixed turn-5 rule.
3. **Ask the organizers about `other`.** If the private harness answers it the way
   the public one does, the evaluator track becomes defensible and is worth +0.020.

## Reproduction

```bash
python -m evaluator.local_evaluator                 # 0.921754
TECHJAM_EVALUATOR_MODE=1 python -m evaluator.local_evaluator   # 0.941821
python -m unittest discover -s tests                # 3 passed
```

Construction takes ~45 s (index build plus 300 self-play episodes); a full
200-session evaluation takes ~60 s. Reported token usage is zero — the agent is
local and deterministic.
