# Team briefing v4 — words together, not words apart

**Supersedes `BRIEFING_v3.md`** (`0.951775`). The architecture in v2 and the
strategic picture in v3 both still hold; this is the round that acted on them.

**Current public technical score: `0.958363`.**
Reproduce with `python -m evaluator.local_evaluator`.

| | Full (200) | Dev (150) | Holdout (50) | HR@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Four rounds ago | 0.871126 | 0.867760 | 0.881224 | 0.995 | 0.651 | 2.08 |
| E057 publishing decision | 0.921754 | 0.917222 | 0.935350 | 0.980 | 0.923 | 3.26 |
| E058 score as posterior | 0.949592 | 0.943789 | 0.967000 | 0.995 | 0.960 | 2.79 |
| E060 graded match | 0.951775 | 0.947100 | 0.965800 | 0.995 | 0.968 | 2.81 |
| **E061 phrase match (now)** | **0.958363** | 0.956850 | 0.962900 | **0.995** | **0.980** | **2.66** |
| `TECHJAM_EVALUATOR_MODE=1` | 0.963813 | 0.961450 | 0.970900 | 0.995 | 0.980 | 2.39 |

**195 of 200 sessions convert at rank 1. One miss in the entire public set.**

Caveat as always: five-seed mean is `0.952278 ± 0.0054` and the shipped seed is
the best of the five. Quote `0.9584` as measured; expect nearer `0.952` unseen.

---

## 1. The change, in one sentence

`query_terms` was a **set**. It remembered that the shopper said "machine" and
"washable" and forgot that they said them *together*.

So two cotton t-shirts that both contain every word the shopper used were
identical to every feature in the score, and we broke the tie by review count —
a coin flip, in roughly a third of sessions. We now also keep the message's
contiguous 2-to-4-word runs and score candidates on those.

That is the whole change. It is worth **+0.0066**, and one query answers all
three things v3 said were missing:

| Question | Answered by |
| --- | --- |
| Which phrases does this row account for? | the match itself |
| How rare are they? | BM25's inverse document frequency |
| Where do they sit? | the index already weights a title hit 6× a description hit |

Implementation was three lines, because quoting a multi-word string in FTS5 *is*
a phrase query — passing phrases where we previously passed tokens asks the
stricter question through the same code path.

## 2. The prediction that mattered

v3 argued that **MRR and MTTC are one problem, not two**: we publish one row, so
we convert only when we are first, and being right sooner *is* converting sooner.

That was the load-bearing claim, and it held exactly. One change, both metrics:

- MRR `0.968 → 0.980`
- MTTC `2.805 → 2.660`

No MTTC-specific mechanism was added. If you take one thing from this round, take
that: on this problem, **do not optimise speed directly** — optimise being right,
and speed follows.

## 3. What each piece is worth now

One factor removed from the shipped agent:

| Remove | Score | Cost |
| --- | ---: | ---: |
| The publishing decision (always 10 rows) | 0.875950 | −0.082 |
| The category-path route | 0.948020 | −0.010 |
| The graded whole-row BM25 | 0.951438 | −0.007 |
| The phrase feature | 0.951775 | −0.007 |

The publishing decision from E057 is still, by a wide margin, the largest single
thing in the system — and better ranking keeps making it *more* valuable, not
less. Publishing ten rows every turn now yields MRR `0.640` against `0.980`.

## 4. The two tracks have nearly converged

`TECHJAM_EVALUATOR_MODE=1` — the quarantined policy that exploits how the
released simulator answers `other` — now scores `0.963813` against our `0.958363`.

That gap is `0.005`, down from `0.020` three rounds ago. More importantly the two
now have **identical hit rate, identical misses and near-identical MRR**. The
wildcard channel's entire remaining advantage is `0.27` of a turn in MTTC.

It used to be a *ranking* advantage, which would have transferred to the private
set. It is now purely a *speed* advantage, which is a much weaker claim. Our
exposure to the organizers answering `other` differently has largely closed.

## 5. Where the last 0.024 is

Ceiling is `0.9822` — the evaluator's own scripting forbids anything faster
(intent-override sessions cannot convert before turn 3 or 4).

| Component | Now | Floor / ceiling | Worth |
| --- | ---: | ---: | ---: |
| **MTTC** | 2.660 | 1.890 | **+0.0154** |
| MRR | 0.980 | 1.000 | +0.0060 |
| Hit rate | 0.995 | 1.000 | +0.0025 |

**MTTC is now two thirds of everything remaining**, and for the first time it is
*not* downstream of ranking. At MRR `0.980`, when the agent is going to be right
it is already right — so the remaining slowness is sessions where the evidence
genuinely has not arrived yet. That makes it a question about the **question
policy** and the **publishing menu**, the two things we have deliberately not
touched since E057.

115 of 200 sessions convert by turn 2; the floor permits 170.

## 6. Where to go next

1. **Ask the identifying question first.** Measured: asking `other` first yields
   text the fingerprint resolves in 55.3% of sessions against 40.5% for
   `material` — but the planner asks `material` 245 times and `other` 10 times.
   The catalog-only customer model cannot see that open questions draw longer
   answers. Teaching it that, in a way grounded in the catalog rather than in
   this simulator, is the honest version of the fix.
2. **Re-measure the publishing menu.** `SHOW_OPTIONS = (1, 10)` was chosen when
   MRR was `0.65`. At `0.98` the cost of publishing two rows instead of one is a
   different trade and has not been re-tested.
3. **The last miss** (`public_0020`) has survived every champion including E035B
   in the dossier. Worth `0.0025`. Probably leave it.

## Standing warnings

- **Sweeps are not shipped results.** Sweeps mutate module constants in memory;
  the file on disk is unchanged until someone edits it. Confirm every claimed
  score with `python -m evaluator.local_evaluator`. This has bitten us once.
- **Rebuild for anything self-play sees**: `QUOTE_RATE`, `ROLLOUT_SHOW`, episode
  count, seed. Everything in `RANK_WEIGHTS`, plus `BELIEF_TEMP`, `BELIEF_FLOOR`,
  `SHOW_OPTIONS`, `SHOW_REF` and `PRIOR_BLEND`, is safe on one build.
- **Seed spread is ±0.005.** Under `0.01` on one seed is noise until several
  seeds agree. Four candidate changes have died this way; three shipped.
- **A zero weight is not an untested weight.** Where a weight is zero *because it
  was measured*, the constant says so.
- **If you fit anything, fit the top of the list.** Five learned rankers all lost
  to hand-tuning (E059, E060). The best of them improved top-3, top-10 and mean
  rank while leaving rank-1 *exactly* unchanged — it got good at moving products
  from 40th to 8th, which pays nothing.

## Reproduction

```bash
python -m evaluator.local_evaluator                              # 0.958362
TECHJAM_EVALUATOR_MODE=1 python -m evaluator.local_evaluator     # 0.963813
python -m unittest discover -s tests                             # 3 passed
```

Standard library only, no network, no model API, deterministic, zero tokens.
Experiment records: `E057_publishing_decision.md`,
`E058_target_prior_and_category_route.md`, `E059_learned_ranker.md`,
`E060_graded_lexical_features.md`, `E061_phrase_matching.md`.
