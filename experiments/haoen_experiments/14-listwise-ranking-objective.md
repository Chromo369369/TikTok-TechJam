---
experiment: "14"
title: "Listwise ranking objective"
type: experiment
technical_score: 0.951089
delta: +0.0026
decision: "Adopted"
summary: "Pointwise to ListNet/Plackett-Luce softmax cross-entropy"
source: "REPORT.md"
---
# Listwise ranking objective

The other open question from the "fully optimized?" audit was the training objective itself: `fit_logistic` is *pointwise* -- every (candidate, session) row is scored as an independent binary classification, a proxy for what actually matters (the target's rank within its own session), not the thing itself. Since every session here has exactly one relevant candidate, the natural listwise alternative collapses to a clean, tractable special case: softmax cross-entropy over each session's full candidate pool (the single-relevant-item case of ListNet, equivalently a top-1 Plackett-Luce model) -- `loss_s = -log(softmax(X_s w)[target])`. Implemented as `fit_listwise` in `tools/fit_reranker.py`, fit via Newton-Raphson with a per-session-covariance Hessian (still pure numpy, no new dependency): each session contributes `X_s^T @ diag(p) @ X_s - (X_s^T p)(X_s^T p)^T` to a single shared 22×22 Hessian, so the per-iteration cost stays small regardless of how many candidates a session's pool holds.

One real numerical quirk worth documenting rather than silently patching around: softmax cross-entropy is invariant to adding a constant to every score in a list, so the bias term is mathematically unidentifiable for this objective specifically -- the Hessian's bias direction is exactly flat, and Newton-Raphson reported bias values as large as -1.1 trillion at some L2 settings during tuning. This is functionally harmless (`argsort` is unaffected by a constant shift, so ranking output was identical either way, confirmed directly), but a tiny dedicated regularizer on just the bias term (`_LISTWISE_BIAS_L2 = 1e-3`) pins it near zero for a clean, reproducible weight vector without changing ranking behavior at all -- verified identical OOF rank-1/top-10/MRR with and without it.

L2 tuning here found a sharp, narrow optimum rather than the pointwise objective's flat plateau: OOF rank-1 jumped from ~90-93 (pointwise, post-override-fix) to 98-99 at L2=1.8-2.5, with real instability below L2≈1.5 (rank-1 collapsing to 34-50). Tested candidate L2 values end-to-end rather than trusting the diagnostic alone (same discipline as every prior round): L2=1.8 and L2=2.0 tied for the best real score. Deployed L2=2.0: **HR@10 1.000, MRR 0.920, technical score 0.951089**, confirmed by a strict target-product-disjoint OOF refit at **0.950189**. Per-scenario, Intent Override's MRR rose from 0.888 to 0.918 -- the clearest sign this is genuinely leveraging the now-functional `override_hit` feature well, not just re-fitting noise, since that's exactly the scenario type the override-gating fix targeted.

Asked to push this toward 0.96 specifically: it didn't get there. 0.951 is a real, validated 0.003 gain over the pointwise-objective baseline (0.948), consistent in size with every other individual improvement in this report's later rounds -- not the kind of jump that closes a 0.03+ gap on its own. See below for why that specific target looks structurally out of reach from here regardless of which individual lever gets pulled next.
