---
experiment: "18"
title: "Sweeping the hand-picked constants"
type: experiment
technical_score: 0.956250
delta: +0.0049
decision: "Adopted"
summary: "BIGGEST LEVER: _CATEGORY_POOL_CAP 300 to 5"
source: "REPORT.md"
---
# Sweeping the hand-picked constants

Every remaining magic number in the file that had never been revisited since introduction got extracted into a named constant and swept: `_BM25_POOL_LIMIT` (150, `_candidate_pool`'s recall cap), `_CATEGORY_POOL_CAP` (300, category-index candidates unioned into the pool), `_EXACT_HIT_MAX_FANOUT` (300, the exact-phrase weighted-tier cutoff), `_TFIDF_TOP_K` (40, per-vector term cap), and the stagnant-turn rotation's `_ROTATION_STABLE_COUNT`/`_ROTATION_WINDOW` (3/7).

**Three dead ends, checked directly rather than assumed.** The rotation constants: swept 7 combinations directly against the full evaluator (free to test -- they only affect the stagnant-turn fallback, not retrieval or training) and got a bit-for-bit identical score every time. Checked why: max `first_hit_turn` across all 200 public sessions is 4, meaning every session already resolves comfortably inside the confidence guard's window and never reaches the rotation logic at all -- same dead-end shape as the `ASK_ORDER` fix, kept only as a defensive safety net for harder private-set sessions. `_EXACT_HIT_MAX_FANOUT` and `_TFIDF_TOP_K` both required a full re-harvest per candidate value (they change what gets recorded, not just deployment-time behavior) and came back essentially flat across a wide range (fanout 100-3000: OOF rank-1 96-97 throughout; top-k 15-100: rank-1 97-98 throughout) -- the *learned* reranker adapts its weighting to whatever threshold is in place, so neither placement matters much once the model can compensate for it. None of the three changed.

**`_CATEGORY_POOL_CAP` was the opposite: a large, real effect no one had looked for.** The original 300 assumed more category-matched recall is strictly better. Swept 0 through 1400 with a fresh harvest + fit at each value and found a strong, monotonic trend in the *wrong* direction from that assumption: OOF rank-1 fell from 135 (cap=0) to 91 (cap=1400) as the cap grew, and MRR from 0.776 to 0.600. The mechanism: category-index matches are weak evidence (just "this product is in the same coarse category"), and unioning in hundreds of them floods the pool with noise the reranker has to fight through to find genuinely well-evidenced candidates -- more of this specific kind of recall actively hurts ranking quality. `cap=0` (no category injection at all) scored best in isolation but introduced a real regression: a genuine full-10-turn miss-check (not just the harvest-time proxy) found 1/200 sessions where the target was never recoverable at all without that safety net. `cap=5` avoided the miss entirely (confirmed with the same full 10-turn check, 0/200 missed) while capturing nearly all of the gain: OOF rank-1 125, MRR 0.738 -- a huge jump from the original cap's 97/0.624.

Re-checked L2 at the new pool composition before deploying, since the harvested row count dropped substantially (55,053 → 33,530 rows) along with everything else: L2=3.0 remained solidly inside a flat, stable plateau (rank-1 123-126, MRR 0.732-0.742, max|weight| well-behaved across L2=1 through 15) -- no re-tuning needed. Deployed `_CATEGORY_POOL_CAP = 5` with a fresh L2=3.0 listwise fit: **HR@10 1.000, MRR 0.939, technical score 0.956250** -- the single largest improvement found anywhere in this report, confirmed by a strict target-product-disjoint OOF refit at **0.954675**.
