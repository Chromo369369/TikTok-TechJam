# E062 Residual Relevance Closure — Final Gate Results

Development-only. No holdout. No champion change. E060 frozen throughout
(SHA256 manifest `E060_freeze_manifest.json`).

## Gate summary

| Experiment | Gate | Result |
|---|---|---|
| E062R — generic shortlist recovery | no rank dilution; generic; recover public_0035 | **REJECT** (dilution) |
| E062G — relevance/propensity disagreement gate | >= +.003 Technical Score over E060 | **REJECT** (net negative) |
| E062X — new-signal screen (22 both-lower pairs) | >= 16/22 target wins | **CLOSED** (nothing passes) |
| E062V — value-ranked residual analysis | quantify distance to .9769 | done (below) |

## E062R — generic shortlist recovery (REJECT)

Rule: exact opening category 201..500 items -> augment union with top-20 by
rating_number. Offline audit:

- public_0035 recovered: **yes** (target is rating-rank 3 in "athletic walking").
- Generic: rule triggers on **23/150** sessions across ~10 categories.
- But only public_0035 is a true shortlist miss; the other 22 already have the
  target in the Top-200, so the augmentation adds candidates **without recovery
  benefit**.
- Dilution: **16/23** triggered sessions receive newly-added candidates with
  *higher* rating than the target (up to 19 new higher-rated items, e.g.
  public_0029 +16, public_0154 +15, public_0068 +14). E060's model weights
  `log_rating_number` +0.64 vs `final_score` +0.18, so these added popular
  items would outrank low-rating targets.

Net: +.0067 upside (one session) vs dilution across 16 sessions. Reject.

## E062G — relevance/propensity disagreement gate (REJECT)

24 disagreement states (target-vs-top1 where final_score and log_rating disagree):
10 relevance-favors-target, 14 popularity-favors-target. Cross-fitted regularized
logistic gate trained only on disagreement candidate pairs:

- Gate resolves **4** states to rank 1 (public_0059, 0183, 0176, 0068).
- Gate **worsens 14** states (e.g. 0029 6→14, 0164 4→15, 0161 10→18, 0083 2→9),
  6 unchanged.
- Net candidate-group rank change is clearly negative — nowhere near +.003.

A linear gate on existing features is a subset of E060's own linear model; with
only 24 disagreement states it overfits and fails to generalize. Reject.

## E062X — new-signal screen on 22 both-lower pairs (CLOSED)

Unused static fields, target-vs-top1 on the 22 "less relevant AND less popular"
residual pairs (gate >= 16/22):

- store_frequency: 9/22 (41%)
- leaf_category_size: 2/22 (9%)
- category_residual_popularity: 0/22 (0%)

Nothing passes. Consistent with P005 (no second rating-like prior). Close.

## E062V — value-ranked residual analysis

E060 OOF .957400; rival ~.9769; gap .0195. To reach .9769 requires solving the
**top 12 residual errors** (of 47), which are a *mix* of classes:

| Rank | Session | Class | Marginal reward |
|---|---:|---|---:|
| 1 | public_0035 | E shortlist miss | +.006667 |
| 2 | public_0161 | B propensity | +.001867 |
| 3 | public_0154 | B propensity | +.001533 |
| 4-7 | 0144 / 0076 / 0164 / 0047 | A relevance + B | +.0014 each |
| 8-9 | 0083 / 0146 | B propensity | +.001267 each |
| 10 | public_0087 | A relevance | +.0008 |
| 11-12 | 0029 / 0002 | B / A | +.0004 / +.000267 |

Fixing all 47 reaches .982533. No single class dominates the top-12; the
shortlist miss is the single largest item but is dilution-risky (E062R).

## Conclusion

All four E062 avenues fail their predeclared gates:

- Shortlist recovery: dilution risk > single-session upside.
- Disagreement gate: net negative (overfits 24 states).
- New-signal screen: nothing passes 16/22.
- Value-ranked: the gap is spread across a mixed class of relevance inversion,
  unavailable propensity, and the dilution-risky shortlist miss.

**Stop development research and freeze E060 (strict OOF .957400) as the single
confirmation candidate.** Rival-level .9769 is not reachable with the features
and legal catalog priors available in this workspace. The only remaining
low-risk action is one explicitly authorized confirmation run of E060.

## Artifacts

- `experiments/e062r_shortlist_audit.py`, `experiments/_e062r_dilution.py`
- `experiments/e062g_disagreement_gate.py`
- `experiments/e062vx_analysis.py`
- `experiments/e062_partial_oracles.py`, `e062_component_matrix.py`, `e062_learnable_oracles.py`
- `experiments/notes/E062_stage1_diagnostics.md`
