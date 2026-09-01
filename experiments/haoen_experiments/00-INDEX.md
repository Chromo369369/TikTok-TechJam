# TechJam Experiment Record — Index

> This note explains how to build an agent that jointly maximizes Hit Rate@10, MRR, and MTTC/Efficiency (and, as a bonus, drives reported token usage to zero) for the TechJam Conversational E-Commerce Search Challenge. It also documents a reference implementation, `starter/agent.py`, and the measured effect of each design decision against the shipped baseline.

Every experiment trialled on this agent, split from `REPORT.md` into one file each.
Ordered chronologically; the score column is the end-to-end Technical Score on the
200-session public set after that change was deployed.

| # | Experiment | Score | Delta | Decision |
|---|---|---:|---:|---|
| 01 | [The scoring function determines the strategy](01-scoring-function-strategy.md) | -- | -- | Reference |
| 02 | [The evaluator's rules are public — read them as a specification, no...](02-evaluator-as-specification.md) | -- | -- | Reference |
| 03 | [Reference architecture (`starter/agent.py`)](03-reference-architecture.md) | 0.813 | +0.71 vs baseline | Adopted |
| 04 | [The reverse phrase index](04-reverse-phrase-index.md) | 0.878 | +0.065 | Adopted |
| 05 | [The rank-quality confidence guard](05-confidence-guard-gambling-strategy.md) | 0.929 | +0.051 | Adopted |
| 06 | [Measured effect](06-measured-effect-progression.md) | -- | -- | Reference |
| 07 | [The learned re-ranker](07-learned-reranker-v1.md) | 0.940 | +0.011 | Adopted |
| 08 | [Multi-phrase evidence, and a determinism bug fixed along the way](08-multi-phrase-evidence-determinism-fix.md) | 0.942 | +0.002 | Adopted |
| 09 | [TF-IDF cosine similarity: closing the "vector similarity" gap](09-tfidf-cosine-vector-similarity.md) | 0.945456 | +0.0035 | Adopted |
| 10 | [Addressing `problem.md`'s other pillars](10-problem-md-pillar-coverage.md) | -- | -- | Documented |
| 11 | [Over-Generality detection and structured clarification](11-over-generality-structured-clarification.md) | 0.945456 | 0.000 | Partially adopted |
| 12 | [Re-tuning `SCORE_WEIGHTS`'s regularization strength](12-l2-regularization-retune.md) | 0.945854 | +0.0004 | Adopted |
| 13 | [Feature audit: a real training bug, and a structurally dead feature](13-feature-audit-override-gating-bug.md) | 0.948464 | +0.0026 | Adopted |
| 14 | [Listwise ranking objective](14-listwise-ranking-objective.md) | 0.951089 | +0.0026 | Adopted |
| 15 | [BM25 field weights, and a numerical-stability bug caught in the pro...](15-bm25-field-weights-and-stability.md) | 0.951339 | +0.0003 | Rejected + stability fix |
| 16 | [Fold-assignment robustness check](16-fold-assignment-robustness-check.md) | 0.950725 | n/a | Validated |
| 17 | [A dead attribute removed from the clarification fallback](17-ask-order-dead-attribute.md) | 0.951339 | 0.000 | Adopted (defensive) |
| 18 | [Sweeping the hand-picked constants](18-constant-sweeps-category-pool-cap.md) | 0.956250 | +0.0049 | Adopted |
| 19 | [Feature-interaction terms](19-feature-interaction-terms.md) | 0.956500 | +0.00025 | Adopted |
| 20 | [Sub-phrase indexing: tried, measured, reverted](20-subphrase-indexing-reverted.md) | 0.956500 | 0.000 | Reverted |
| 21 | [Where this leaves the 0.98 target](21-ceiling-analysis-098-target.md) | 0.956500 | -- | Conclusion |

## The optimised gambling strategy

File `05-confidence-guard-gambling-strategy.md` is the decision the record calls the
rank-quality confidence guard, and it is the project's central gamble: a session ends
the instant the target appears in a published top-10, locking in whatever rank it had.
Showing a weak-evidence candidate early therefore *cashes out at a bad rank*; withholding
it spends a turn to buy a phrase that usually resolves the same product to rank 1.

The optimisation is the bound. Guarding for the whole session maximises rank but risks
never converting: measured at HR@10 0.99 and score 0.923. Bounding the guard to turn 6
(`_CONFIDENCE_GUARD_LAST_TURN`, flat across 5-7) keeps the rank upside while guaranteeing
full-recall turns before the budget runs out: score 0.929. That +0.051 over the
ungoverned agent is the single largest gain in this record apart from the phrase index.

## Score progression

| Stage | Score |
|---|---:|
| Shipped baseline (weak BM25) | ~0.10 |
| Constraint state + BM25 | 0.813 |
| + Reverse phrase index | 0.878 |
| + Confidence guard (the gamble) | 0.929 |
| + Learned re-ranker v1 | 0.940 |
| + Multi-phrase evidence + determinism fix | 0.942 |
| + TF-IDF cosine | 0.945456 |
| + L2 re-tune | 0.945854 |
| + Override-gating harvest fix | 0.948464 |
| + Listwise objective | 0.951089 |
| + Category-pool-cap fix | 0.956250 |
| + Interaction terms (current) | 0.956500 |
