---
experiment: "20"
title: "Sub-phrase indexing: tried, measured, reverted"
type: experiment
technical_score: 0.956500
delta: 0.000
decision: "Reverted"
summary: "Real signal, 11x lift on positives, never changed an outcome"
source: "REPORT.md"
---
# Sub-phrase indexing: tried, measured, reverted

The last untried candidate from the original "fully optimized?" audit. The initial concern going in was whether decomposing a revealed phrase into shorter windows could even help: for a short compositional string like `"95% Polyester, 5% Spandex"`, a sub-window is generally *more* common than the whole phrase, not less (e.g. "95% Polyester" alone matches far more products than the full three-ingredient combination). Checked this empirically against the real catalog before writing any absorption logic: across all product card phrases, 3-content-word windows have a *lower* mean fanout than full phrases (1.83 vs 3.28) and 86% are unique to a single product. The reason: most catalog phrases are long, distinctive marketing sentences (not short composition strings), and a 3-word window drawn from distinctive prose is usually still distinctive.

Implemented on that basis: a second index (`subphrase_index`) built the same way as the existing phrase index but keyed on contiguous 3-content-word windows (bounded to phrases with 4-12 tokens, to skip both trivially-short phrases and avoid excessive windows on very long ones), scored as an independent `subphrase_score` feature at half the weight of a full exact-phrase hit (corroborating evidence, not primary). Harvested and fit: the feature activates on only 1.96% of rows overall but 11% of *positive* (target) rows -- an 11x lift, confirming it isn't noise -- and the fitted weight came out positive and non-trivial (0.156), so the regularizer kept it rather than shrinking it to zero.

Despite all of that, the end-to-end result was **bit-for-bit identical** to the pre-sub-phrase model: HR@10 1.0000, MRR 0.940000, MTTC 2.2750, score 0.956500, matching to six decimal places. The isolated ranking-gate diagnostic told the same story in advance (rank-1 126→126, MRR 0.7395→0.7396, a noise-level move). The signal is real -- it just never ends up being the deciding factor in any of the 200 public sessions' outcomes, presumably because sessions where it fires already have strong corroborating evidence from other features (the exact-phrase match, `distinct_phrase_match_count`, or `tfidf_cosine`) that already puts the same candidate on top.

**Reverted rather than kept as a hedge.** This was a real engineering trade-off, not an automatic call: the feature is well-motivated, non-overfit, and provably harmless on the only data available to test it -- an argument for keeping it in case it helps on the private 800-session set in ways the public 200 don't exercise. Against that: it adds a second full-catalog index (~185K entries), extra per-message lookup work every turn, and meaningful code surface, all for a change that has never once been observed to affect an outcome. Consistent with not carrying speculative complexity for a hypothetical future case, and with how the BM25 field-weight investigation was handled earlier (measured honestly, discarded because it didn't earn its cost), the sub-phrase indexing code was fully reverted -- confirmed via a clean pytest + full-evaluator pass reproducing the pre-experiment 0.956500 exactly.
