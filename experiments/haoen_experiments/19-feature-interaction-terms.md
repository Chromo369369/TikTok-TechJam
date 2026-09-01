---
experiment: "19"
title: "Feature-interaction terms"
type: experiment
technical_score: 0.956500
delta: +0.00025
decision: "Adopted"
summary: "Six pairwise interactions; hypothesis on sign was wrong"
source: "REPORT.md"
---
# Feature-interaction terms

The model is a linear (listwise softmax) classifier, so it can only combine `_extract_features`'s 22 signals additively -- it can't natively express "category correctness matters more when combined with strong exact-phrase evidence" without that product being handed to it as its own column. Added six hand-picked pairwise interaction terms rather than an exhaustive combinatorial sweep (with only ~200 positive training examples, `21*20/2 = 210` possible pairs would risk overfitting badly): `category_hit * exact_score`, `category_hit * tfidf_cosine`, `has_exact_evidence * catalog_completeness`, `has_exact_evidence * rating_number_scaled`, `distinct_phrase_match_count * exact_score`, and `material_hit * color_hit`. The two `has_exact_evidence *` terms specifically targeted the `public_0092`-style regression documented earlier in this report, where `catalog_completeness`/`rating_number_scaled` dominated ranking in the *absence* of hard evidence -- the hypothesis was that a negative learned weight here would let the model de-weight the popularity prior specifically once real evidence exists.

Refit (fresh harvest at the now-deployed `_CATEGORY_POOL_CAP=5`, 28 features): all six interactions converged to non-trivial, non-zero weights (0.18-0.48) rather than being shrunk out by L2 regularization, so they are picking up *something* real in the training data. But `evidence_x_completeness`'s fitted weight came out positive (+0.42), not the hypothesized negative -- the model learned to treat evidence and completeness as *reinforcing* signals (both present is stronger than either alone) rather than using evidence to override the popularity prior the way the hypothesis expected. The isolated ranking-gate diagnostic barely moved as a result (OOF rank-1 125→126, MRR 0.738→0.7395 versus the pre-interaction cap=5 baseline) -- a noise-level difference despite the interactions clearly being "used."

End-to-end confirmed a real, if modest, gain consistent with that small diagnostic movement: **HR@10 1.000, MRR 0.940, technical score 0.956500**, confirmed by a strict OOF refit at **0.955625**. L2=2.0 scored marginally higher in this same sweep (0.957125) but was not adopted -- L2=2.0 was independently established as numerically fragile for this objective in an earlier round, and a +0.0006 difference was not judged worth reintroducing that risk for.
