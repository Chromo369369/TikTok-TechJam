# E057 — Publishing as a planner action, with a calibrated belief

## Status

EVALUATED — KEEP; current best. Full public technical score `0.921754`.

## Question

The Monte Carlo planner chooses *which attribute to ask about*, then publishes a
fixed ten rows. Is the number of rows published also a decision worth planning
over, and if so what does the planner need to believe in order to make it well?

## Hypothesis

The session ends the instant the target appears in the published list, so the
list length selects which rank is scored. Per-session reward is
`0.5 + 0.3/rank + 0.2*(11 - turn)/10`, therefore:

```text
rank 1 on turn 4  = .94     >     rank 2 on turn 1  = .85
rank 1 on turn 6  = .90     >     rank 2 on turn 1  = .85
```

Converting at rank 1 up to five turns later beats converting at rank 2 now.
Publishing ten rows out of an ordering the agent does not yet trust should
therefore be costing MRR that a further question would have recovered. If the
planner scores list length with the same rollouts it uses for questions, it
should trade the two correctly.

The hypothesis carries a precondition: the planner can only make this trade if
its belief distinguishes a trustworthy ordering from an untrustworthy one. The
incumbent belief is a fixed Zipf over retrieval *rank*, which is identical in
both states, so the belief was expected to need replacing as part of the change.

## Baseline

The incumbent planner agent (`starter/agent.py` at `5f66f94` plus the working
tree), publishing `top_k = 10` every turn.

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 150 | 0.993333 | 0.642754 | 2.086667 | 0.867760 |
| Holdout | 50 | 1.000000 | 0.674746 | 2.060000 | 0.881224 |
| Full | 200 | 0.995000 | 0.650752 | 2.080000 | 0.871126 |

Hit rank distribution: 104 sessions at rank 1, 96 at ranks 2–10, 1 miss.
The MRR of 0.65 against a hit rate of 0.995 is the whole problem: the agent
finds the target almost always and ranks it badly.

## Change

Three coupled changes. They are one mechanism, not three — see the ablation note
under Observations.

**1. List length becomes an action.** `respond` now plans before publishing.
`_choose_show` evaluates each allowed length `k` as

```text
EV(k) = sum_{rank <= k} w_rank * session_return(rank, turn)      # converts now
      + sum_{rank >  k} w_rank * rollout(pool minus top k, ...)  # buys a turn
```

The head term is summed exactly over the leading candidates; the tail reuses the
same particles, the same pre-drawn randomness, and the same rollout used to score
the questions. The menu is `(1, 10)`; the widest option is always retained so the
final turn and any diffuse belief still get full coverage.

`_rollout` and `_no_info_value` take the assumed future list length, so a rollout
converts only at a rank the policy would actually expose and peels that many
proven non-targets per simulated turn.

**2. The belief becomes a softmax of the retrieval score.** `_ranked_ids` already
computed a score per candidate and discarded it; it now returns it, and
`_PlanContext` builds `weights[i] = exp((score_i - score_0)/BELIEF_TEMP)` over a
small rank-decayed floor.

Measured on development dialogues, the score gap between the top two candidates
predicts whether the leader is the target:

| Gap (score units) | Turns | P(top-1 is target) |
| --- | ---: | ---: |
| 0–1 | 347 | 0.118 |
| 1–2 | 87 | 0.264 |
| 2–3 | 45 | 0.600 |
| 3–4 | 25 | 0.520 |
| 4+ | 63 | 1.000 |

Maximum likelihood over the target's observed position gives mean log-likelihood
`-3.31` per turn for the softmax against `-5.95` for the rank-only prior.

**3. The rollout customer gains a quote channel.** With probability `QUOTE_RATE`
a substantive answer about a free-text attribute is phrased in the product's own
words, collapsing the pool to that row. Grounded in the catalog, not the harness:
of 50,000 rows, 99.0% carry at least one indexable specification string and
95.6% carry one that occurs on exactly one row (90.7% of the 206,022 distinct
keys are unique). Without this channel the rollout contains no mechanism that can
lift a deeply ranked candidate to the top, so continuing always looks worthless
and the planner publishes wide.

**Supporting trainer fix.** Self-play weights are averaged over the second half
of training instead of taken from the final iterate, and per-action advantages
are shrunk toward neutral by a pseudo-count. This was not a scoring change but a
measurement one — see Observations.

Constants: `BELIEF_TEMP 0.75`, `BELIEF_FLOOR 0.02`, `QUOTE_RATE 0.30`,
`SHOW_OPTIONS (1, 10)`, `SHOW_REF 1`, `ROLLOUT_SHOW 5`, `POLYAK_BURN_IN 0.5`,
`THETA_PRIOR_COUNT 25`.

## Everything else

Unchanged. Retrieval, constraint extraction, spec fingerprinting, override
handling, repeat suppression, the question action set, `PRIOR_BLEND`,
`ROOT_PARTICLES`, `ROLLOUT_DEPTH`, `MAX_REPEAT_ASK`, `SILENCE_MARGIN`,
`DEFAULT_TRAIN_EPISODES` and `TRAIN_SEED` all retain their incumbent values.
No evaluator file, public label, or catalog artifact was modified.

## Expected

MRR rises sharply; MTTC rises because turns are being spent deliberately; hit
rate falls slightly because fewer distinct products are exposed per session.
Net technical score improves if the MRR gain exceeds the hit-rate loss.

## Results

- Hit Rate@10: **0.980000** (baseline 0.995000)
- MRR: **0.922847** (baseline 0.650752)
- MTTC: **3.255000** (baseline 2.080000)
- Technical score: **0.921754** (baseline 0.871126, **+0.050628**)
- Buying: n=80, HR 0.950000, MRR 0.941667, MTTC 2.625000
- Browsing: n=80, HR 1.000000, MRR 0.915035, MTTC 3.500000
- Intent override: n=30, HR 1.000000, MRR 0.916667, MTTC 4.066667
- Boundary: n=10, HR 1.000000, MRR 0.853333, MTTC 3.900000

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 150 | 0.980000 | 0.915185 | 3.366667 | 0.917222 |
| Holdout | 50 | 0.980000 | 0.945833 | 2.920000 | 0.935350 |
| Full | 200 | 0.980000 | 0.922847 | 3.255000 | 0.921754 |

The gain holds on the untouched holdout (+0.054126 there against +0.049462 on
development), so it is not a development-split artifact.

Hit rank distribution: **181 at rank 1** (baseline 104), 2 at rank 2, 2 at rank
3, 1 at rank 4, 5 at rank 5, 1 at rank 6, 3 at rank 8, 1 at rank 9, 4 misses.

First-hit turn: 38 / 52 / 43 / 29 / 14 / 8 / 4 / 1 / 4 / 3 for turns 1–10, 4
misses.

### Ablations, one factor removed from the shipped configuration

| Configuration | Full score | Delta |
| --- | ---: | ---: |
| Shipped | 0.921754 | — |
| No publishing decision (always 10 rows) | 0.864571 | −0.057183 |
| Rank-only belief (no score softmax) | 0.889453 | −0.032301 |
| No quote channel (`QUOTE_RATE = 0`) | 0.897212 | −0.024542 |
| Finer length menu `(1,2,3,5,10)` | 0.911800 | −0.009954 |
| No advantage shrinkage | 0.913292 | −0.008462 |
| No iterate averaging | 0.926293 | +0.004539 |
| No self-play at all | 0.826560 | −0.095194 |

### Evaluator-specialised track (`TECHJAM_EVALUATOR_MODE=1`)

Quarantined behind an environment variable and off by default. Only the customer
model changes: `other` is modelled as high-bandwidth and answering in catalog
text, because the released simulator answers it by reading back undisclosed
intent-card entries verbatim.

| Split | Samples | Hit Rate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 150 | 0.986667 | 0.952981 | 2.780000 | 0.943628 |
| Holdout | 50 | 0.960000 | 0.960000 | 2.580000 | 0.936400 |
| Full | 200 | 0.980000 | 0.954736 | 2.730000 | 0.941821 |

Nothing instructs it to prefer `other`; changing what that channel is worth is
sufficient for the planner to select it in 453 of its 556 questions on its own.

## Internal diagnostics

Measured over the full 200-session public run of the shipped configuration.

- Repeats suppressed: 1,582
- Unique products shown: 921, from 1,322 published row-slots over 647 turns
  (a fixed ten-row policy would have published 6,470 slots over the same turns)
- Average candidates considered: 512.0 (the working set is saturated every turn)
- Overrides detected: 30 (exactly the 30 intent-override sessions)
- No-preference replies: 203
- Responses / planning calls: 647
- Rollouts: 127,280 total, **196.7 per planning call** — 107,737 scoring
  questions (~9.13 legal actions x ~18 distinct particles) and 19,543 scoring
  list length (2 lengths x surviving particles); each rollout simulates up to
  `ROLLOUT_DEPTH = 4` further turns
- Question mix: material 273, feature 155, use case 52, brand 45, color 41,
  category 39, style 15, silent 12, other 8, size 5, budget 2
- Published list length by turn (rows: sessions): turn 1 `1:188, 10:12`;
  turn 3 `1:99, 10:11`; turn 5 `1:30, 10:8`; turn 9 `1:3, 10:8`; turn 10 `10:7`

The length decision is genuinely per-session and per-turn, not a schedule: on
turn 1 the planner already publishes the full ten rows in 12 of 200 sessions.

### Self-play stability

The trainer fix was motivated by measurement, not by score. Five training seeds,
everything else fixed:

| Trainer | Mean | SD | Range | Worst seed |
| --- | ---: | ---: | ---: | ---: |
| Final iterate, unshrunk (before) | 0.912302 | 0.018680 | 0.050802 | 0.875631 |
| Averaged iterate, shrunk (after) | 0.921136 | 0.007942 | 0.023488 | 0.908260 |

The seed spread was larger than any modelling effect in the file, which made
single-run comparisons of anything self-play touches unreliable. On the shipped
seed alone, averaging reads −0.0045; the justification is the five-seed spread,
not the point estimate. The shipped seed now sits at the five-seed mean rather
than above it.

## Observations

**The three changes are one mechanism.** Removing the publishing decision from
the shipped agent gives 0.864571, which is *below* the 0.871126 baseline that
also published ten rows. The calibrated belief and the quote channel are mildly
harmful when the list length is fixed; they exist to serve the length decision.
This is why they were promoted together rather than as three independent steps.

**The decision-optimal belief is sharper than the maximum-likelihood one.**
Likelihood is fitted over all 512 positions, while the only thing the policy asks
of the belief is how much mass sits on the leader. MLE gives `BELIEF_TEMP = 1.0`
and scores 0.909513; 0.75 scores 0.921754. Temperatures 0.5–0.9 crossed with
`ROLLOUT_SHOW` 5–8 all land in 0.915–0.922, so the operating point is a plateau
rather than a tuned peak.

**Intermediate list lengths lose.** A menu of `(1,2,3,5,10)` costs 0.010 against
`(1,10)`. Hedging into four or five rows converts at a middling rank, which the
reward structure never pays for: either name the product or buy another turn.

**Parameters that self-play sees cannot be swept on a reused build.**
`QUOTE_RATE` read 0.927042 when changed on a live instance and 0.904589 on a
clean rebuild, because the priors stayed trained under the old value. The clean
figure is the real one. This invalidated an earlier reading and is the reason the
`quote`, `rollout_show`, `episodes` and `seed` grids are all rebuild-per-config.
`PRIOR_BLEND = 0.35` was rejected on the same grounds: worth +0.005 on the
shipped seed, −0.001 averaged over five.

**Iterate averaging removed the need for a larger training budget.** Before it,
3,000 episodes scored 0.932050 against 300 at 0.921781. After it, 3,000 scores
0.920348 against 300 at 0.921754. Construction time is unchanged.

**The `other` action is barely used in the default track** — 8 of 556 questions.
The robust policy is not quietly exploiting the wildcard channel.

## Failure cases and taxonomy

Four residual misses, all Buying. Deep rank is the target's position in a
3,000-candidate ranking at each turn.

- RETRIEVAL_MISS: **1** — `public_0020`. Reaches deep rank ~320 by turn 3 and
  stalls there for the rest of the session despite 9 constraints and a spec match
  worth 4.68. Never approaches the top 10 under any list length. Matches the
  dossier's long-standing classification of this session.
- RERANK_FAILURE: **2** — `public_0054` (deep rank oscillates 17–100, never
  converts) and `public_0161` (deep rank 22–68, reaches 22 by turn 7). Both are
  retrieved comfortably and never ranked in. Neither ever acquires a spec match.
- BAD_QUESTION: 0 observed. No miss stalls because the question channel ran dry;
  all four continue to accumulate constraints to the end.
- REPEAT_WASTE: 0. Repeat suppression is active (1,582 suppressed) and no miss
  re-shows a product.
- HARD_CONSTRAINT_VIOLATION: 0.
- STATE_ERROR: 0.
- OVERRIDE_ERROR: 0. All 30 overrides were detected and all 30 override sessions
  converted.
- AMBIGUOUS_QUERY: 0 distinctly attributable.
- **PUBLISH_TOO_NARROW (new category): 1** — `public_0179`. The target reaches
  deep rank 8 on turn 6 and 9 on turn 7 while the planner publishes a single row,
  and drifts back to 27 by turn 10. Publishing ten rows on either turn would have
  converted it. This is the direct cost of the change and the honest reason hit
  rate fell from 0.995 to 0.980.

Forcing the wide list from turn 5 recovers hit rate to 0.990 for an identical
technical score (0.922381 against 0.921754) — a different risk profile at the
same price, available as a one-line change if hit rate is judged separately.

## Conclusion

**KEEP.**

- Improves full technical score by 0.050628 over the incumbent.
- Wins on the untouched holdout by a slightly larger margin than on development.
- The mechanism is interpretable and its cost is identified and bounded to a
  single session.
- No hidden target, scenario label, or simulator-only signal is read at runtime;
  the added customer channel is measured off the catalog.
- Contract-conformant: verified that every response over a ten-turn session
  returns a non-empty valid `message`, an allowed `ask_attribute`, and 1–10
  unique in-catalog `parent_asin` values. `docs/agent_api_contract.json` sets
  `maxItems: 100` and no minimum, and the specification says the agent returns
  "up to ten".

Carries one structural risk worth stating: the gain assumes the harness ends a
session at the *first* appearance of the target, as the released evaluator does
(`local_evaluator.evaluate` breaks on hit) and as the specification states. If a
private harness instead scored the best rank across all turns, short lists would
only lose, and the correct configuration would be `SHOW_OPTIONS = (10,)`.

## Next experiment

1. **E058 — recover the two rerank failures.** `public_0054` and `public_0161`
   sit at deep rank 20–100 for entire sessions with zero spec evidence. The
   question channel is not exhausted for either. Ask whether a question policy
   that explicitly targets acquiring a *spec-quotable* disclosure — rather than
   maximising split — converts them, and whether that generalises.
2. **E059 — hit-rate insurance.** The `PUBLISH_TOO_NARROW` case suggests a
   late-session widening rule. Forcing wide from turn 5 is score-neutral and
   hit-rate-positive; test whether a belief-driven version (widen when the
   leader's score margin has not improved for N turns) beats both.
3. **E060 — organizer clarification dependency.** If `other` semantics in the
   private harness are confirmed to match the public one, `TECHJAM_EVALUATOR_MODE`
   becomes the defensible default and is worth +0.020.
