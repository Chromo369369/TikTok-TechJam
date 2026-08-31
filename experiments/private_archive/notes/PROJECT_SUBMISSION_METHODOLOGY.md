# Project Submission Methodology and Research Record

## Document purpose

This document is the end-to-end methodological record for the conversational
product-search project. It explains the task, scoring, runtime pipeline,
experimental design, mathematical models, validation controls, successful
mechanisms, rejected mechanisms, deployment choices, and limitations.

It is deliberately not a claim that every experimental branch improved the
system. A central part of the project was identifying which apparently plausible
ideas did **not** generalize or did not meet a predeclared safety/effect gate.
The runtime configuration, experiment configuration, diagnostic artifact, and
notes cited in this document are retained in this repository.

## 1. Problem definition

The system is a stateful conversational recommender over a 50,000-product
catalog. At each turn it receives a shopper utterance and returns:

- at most one clarification question; and
- an ordered slate of up to ten recommendations.

The agent is not given the hidden target product at runtime. It may use only the
catalog, visible dialogue, user profile, and its own prior state. Target ASINs,
target ranks, evaluator labels, and experiment outcomes are used only after a
run for offline evaluation or diagnostics.

The implementation is centered in [starter/agent.py](../../starter/agent.py).
The evaluator is [evaluator/local_evaluator.py](../../evaluator/local_evaluator.py).

### 1.1 Evaluation score

For a session (i), let:

- (H_i) be 1 when the target appears in the first ten recommendations at any
  turn and 0 otherwise;
- (RR_i) be reciprocal rank of the best target appearance;
- (T_i) be mean time to conversion / first successful turn, capped by a
  ten-turn horizon.

The reported aggregate Technical Score is:

\[
\operatorname{TechnicalScore}
= 0.50\operatorname{HR@10}
+ 0.30\operatorname{MRR}
+ 0.20\operatorname{Efficiency},
\]

where

\[
\operatorname{Efficiency} = \frac{11-\operatorname{MTTC}}{10}.
\]

This objective makes the task explicitly sequential. A system can improve
later rank by withholding products while waiting for useful information, but
can lose immediate conversion opportunity and efficiency. Therefore, retrieval,
ranking, question choice, repeat policy, and slate size all interact.

### 1.2 Data and split discipline

The public benchmark supplied 200 sessions. A deterministic SHA-256 ordering
defines a 150-session development split and a 50-session holdout split. The
development split was used for investigation and model selection. Where a
branch was eligible for confirmation, one frozen configuration was then run on
holdout; holdout was never used to choose among a sweep.

The historical holdout has been observed in multiple earlier campaigns and is
therefore confirmation evidence, not a pristine future model-selection set.
Later work consequently emphasized strict out-of-fold development estimates,
predeclared gates, and no post-holdout retuning.

## 2. Runtime system

The runtime pipeline is:

```text
shopper message
  -> normalization and intent-operation detection
  -> constraint extraction and dialogue-state update
  -> lexical candidate retrieval
  -> field-aware phrase/evidence fusion
  -> static-prior fusion and hard-safety partition
  -> optional frozen E060 posterior within the existing candidate domain
  -> clarification-question selection
  -> exposure-policy display limit
  -> recommendations and target-free state diagnostics
```

### 2.1 Normalization, state, and intent operations

Messages are normalized so punctuation and hyphenation do not change the
meaning of catalog phrase matching. E057 fixed a real inconsistency in which
punctuation/category conjunctions were represented differently in retrieval and
evidence lookup. The fix was score-neutral on both development and holdout,
which is the expected signature of a correctness hardening rather than a tuned
ranking change.

The agent tracks constraints with attributes, values, strengths, source turns,
asked attributes, known attributes, no-preference responses, prior shown items,
and wildcard-question state. Important semantic rules include:

- unknown is not treated as contradiction;
- explicit hard material/color conflicts are distinguished from missing data;
- an intent override resets stale intent-specific state and repeat inventory;
- wildcard replies can contribute multiple atomic facts rather than one averaged
  pseudo-constraint;
- repeated wildcard questioning is stopped only under explicit exhaustion
  conditions.

The E012--E017 series evaluated constraint strength, operation awareness,
selective reset, soft decay, contradiction resolution, and semantic ranking.
The durable parts were explicit constraint semantics and intent reset; more
complex state/planner variants were not promoted.

### 2.2 Candidate retrieval and evidence

The submitted runtime uses only the Python standard library plus SQLite FTS5;
it has no required GPU or model-serving dependency. Product text is indexed
across title, category paths, features, description, store/brand, and visible
details. BM25 supplies broad lexical retrieval.

Field-aware evidence then gives precise support to matches in participant-visible
catalog fields. The E025 family compared phrase-only, controlled-value,
structured-evidence, and aggregated-evidence routes. Aggregated field evidence
was the durable result. It is combined with exact phrase/fingerprint behavior,
not replaced by a generic semantic model.

E058 corrected a concrete implementation error: exact phrase document
frequency was written with one key namespace but read from another. The old
lookup silently gave all exact phrases unit weight. Correcting the key restored
the intended inverse-document-frequency term:

\[
w(p) = \log\left(\frac{N+1}{df(p)+1}\right) + 1,
\]

with (N) catalog documents and (df(p)) the normalized phrase document
frequency. E058 changed only that lookup; dialogue policy, candidate generation,
prior, repeat behavior, and safety were frozen. It became the robust baseline.

### 2.3 Static popularity prior and safety

The catalog field `rating_number` was unusually predictive of target selection.
The system did not replace relevance with popularity. It fused relevance rank
and within-candidate popularity rank using reciprocal-rank fusion with fixed
(k=60):

\[
\operatorname{RRF}(d)
= \frac{1}{60 + r_{\mathrm{relevance}}(d)}
+ \frac{1}{60 + r_{\mathrm{popularity}}(d)}.
\]

Pure popularity was unsafe and performed poorly: it introduced 379 development
Top-10 confirmed hard-constraint violations. P002 therefore added a *partition*,
not another score bonus:

```text
eligible non-violators in fused order
then confirmed hard violators in fused order
```

An item is demoted only when the user has an explicit hard constraint and the
catalog has enough information to establish a real conflict. Missing catalog
information remains UNKNOWN and is not treated as a violation. This preserved
or slightly improved score while removing 21 development and 6 holdout
violations in the robust path.

P003 then stress-tested the popularity signal by target-independent catalog
perturbations. Its degradation under within-category and global shuffles showed
that `rating_number` is a powerful but distribution-sensitive prior. The system
therefore retains a robust path without evaluator-specific wildcard assumptions
and labels the popularity mechanism as a portability risk.

### 2.4 Clarification policy

The agent selects at most one question per turn. The durable policy does not
attempt to estimate a fully Bayesian posterior over all possible answers.
Instead, it scores attributes using catalog coverage and empirically measured
answerability. This made question choice answerability-led rather than merely
entropy-led.

Experiments E004--E009 tested simple candidate splitting, unweighted/weighted
entropy, expected value, weighted split, and expected elimination. These did
not outperform answerability-led questioning. E010 established the answerability
split. E035 added exhaustion recovery so the system can return to a viable
named attribute after prior questions fail rather than looping or terminating
prematurely.

### 2.5 Recommendation exposure as sequential control

The ranking may be good before a clarification, but displaying a product marks
it as shown and interacts with repeat suppression. Consequently, the number of
recommendations displayed while asking a question is an exploration/exploitation
budget, not merely a UI parameter.

Let (k_t) be the display limit at turn (t). The system emits the top
(k_t) repeat-eligible products. A smaller (k_t) can preserve unshown products
until new evidence moves them higher; a larger (k_t) increases immediate hit
opportunity. The final actionable/no-question state releases (k=10).

K001 established the mechanism: 36 of 40 targets withheld at ranks 6--10 were
promoted to ranks 1--5 after the next genuine clarification. Subsequent,
bounded K002--K007 experiments tested lower limits, horizon release,
information-gain release, substantive-answer schedules, wildcard-aware limits,
cumulative caps, and ranking churn. This was intentionally stopped after the
new causal mechanisms were exhausted; it was not converted into an open-ended
threshold search.

## 3. Configurations retained for different risk profiles

The project does not claim there is one universally best configuration. The
three retained configurations make different assumptions.

| Configuration | Dev score | Holdout score | Scope and rationale |
|---|---:|---:|---|
| E058 robust/default | .871721 | .865174 | Field-aware lexical evidence, exact phrase-IDF correction, popularity RRF, and safety. Lowest evaluator-specific commitment. |
| K006C score-optimized | .918367 | .893400 | E058 plus action-conditioned exposure: K1 after a substantive answer, K3 after a no-information response, K10 otherwise. |
| P007D evaluator-specific | .931986 | .924000 | P006C wildcard/override lifecycle plus wildcard K1, named K3, and no-question K10. Depends on released evaluator semantics. |
| E060 strict OOF research model | .957400 | not run | Development-only learned posterior; not silently substituted for a champion or holdout-tuned. |

E058 is loaded by the no-argument submission path. K006C and P007D are
explicit configurations. This prevents an evaluator-specific branch from being
silently presented as the safest deployment default.

## 4. Experimental methodology

### 4.1 Experiment contract

Every material experiment specified:

- a frozen parent configuration;
- one mechanism-level change or a small predeclared factorial;
- development-only selection unless one later confirmation was authorized;
- target-free runtime behavior;
- metrics, safety checks, and a promotion gate;
- artifacts containing configuration, state traces, metrics, and paired
  comparisons.

Rejected experiments remain documented. A negative result was not silently
discarded and rerun under a renamed variation.

### 4.2 Correct statistical unit

End-to-end outcomes are clustered within sessions. Individual turns or ranking
states are not independent draws. Paired comparisons therefore use one
Technical-Score contribution per session/target:

\[
\Delta_i = S_i(\text{challenger}) - S_i(\text{baseline}).
\]

For a paired bootstrap, the system samples the set of (n) sessions with
replacement, computes the average sampled (Delta_i), and repeats this
deterministically (typically 5,000 or 10,000 draws). It reports mean delta,
95% percentile interval, positive-draw probability, and improved/worsened/tied
counts. Policy-learning diagnostics used equal-target weighting and
target-cluster bootstrap where multiple states belonged to a target.

This avoids falsely narrow intervals that would result from independently
bootstrapping 400+ turns from 150 sessions.

### 4.3 Product-disjoint cross-validation

E060 creates one naturally occurring early-union candidate group per eligible
development target. The target must already be present in the archived,
target-independent pre-popularity candidate pool; it is never injected.

Five deterministic folds are assigned with a SHA-256 hash of the session ID.
For each held-out fold:

1. all held-out target products are removed from **every** training candidate
   row, including rows where they would otherwise be negatives;
2. the model is fit only on the remaining four folds;
3. only the held-out groups are scored by that fold model.

This is stronger than row-wise random validation because a catalog product
cannot recur in training under a different dialogue and leak its static
identity. E060 produced 149 eligible groups and one true shortlist miss
(`public_0035`).

### 4.4 Falsification and attribution controls

E060 was subjected to two offline controls before being interpreted.

**Label permutation.** One hundred deterministic within-group permutations
kept candidate groups, folds, scaling, regularization, weights, and tie-breaking
unchanged. The training positive was replaced with a hash-selected random
candidate; held-out labels remained real. The real-label OOF MRR delta over the
archived order was `+.136820`; the permuted mean was `-.504213`, the best null
run was `-.277816`, and the plus-one empirical tail probability was `.009901`.
The advantage disappeared when target association was destroyed.

**Predeclared feature ablations.** Removing popularity/propensity reduced OOF
MRR by `.112691`; removing dialogue/relevance reduced it by `.245176`; removing
exact-category features reduced it by `.046216`. These were interpretation
experiments, not a search for an ablation to deploy.

### 4.5 Train/serve parity

The final Phase A audit replayed the raw archived messages for every E060
training state through the live runtime. It compared:

- candidate membership in the eligible model domain;
- pre-model baseline order;
- every input feature supplied to the fold model.

The first audit found two real mismatches: training used six-decimal serialized
dynamic scores while serving used full precision, and serving counted route-union
candidates outside the frozen Top-200 domain when computing baseline rank. Both
were corrected. The final audit matched **149/149** groups for membership,
order, and feature values; failure count was zero. A fresh strict-OOF end-to-end
replay then had identical compact session outcomes and the same `.957400` score.

### 4.6 Feature integrity and code lineage

The feature matrix was inspected directly. Four declared E060 inputs were
always zero: `evidence_score`, `interaction_score`, `matched_field_count`, and
`route_support`. `final_score` and `aggregate_score` were exactly equal. These
facts were recorded as model-integrity observations rather than used to tune a
new reduced model.

W001 performed a lineage replay across P007D, P008A, and E060 using the same
archived raw dialogue. A semantic-state fingerprint covered normalized
constraints, intent version/start, asked/known/no-preference attributes,
wildcard/exhaustion state, last operation, and inferred scenario. It separated
semantic divergences from intentional ranking/exposure differences. No semantic
wildcard regression was found; restoring old P007D exposure under E060 was
worse (`-.001467` Technical Score), so no further exposure restoration variant
was run.

### 4.7 Tests, hashes, and runtime hardening

The test suite contains 60 passing tests covering deterministic selection,
frozen candidate membership/order, transcript reconstruction, target/input
separation, identifier/rating leakage, metrics, product-disjoint splits,
structured parsing, semantic-state fingerprints, and exposure-rule IDs.

Champion and model artifacts have hash manifests. Submission hardening also
verified loading from a foreign working directory and fail-loud behavior for an
explicit E060 model. The local evaluator no-argument path intentionally loads
the robust default, so E060 requires an explicit configuration wrapper rather
than an implicit fallback.

## 5. Learned E060 target-propensity posterior

E060 is a development-only linear reranker used only within the already frozen
candidate domain. It is not candidate generation and does not receive target
identity at runtime.

For candidate (d) in state (s), the model forms a 17-dimensional feature
vector (x(d,s)), standardizes it using training-fold statistics, and computes:

\[
z(d,s) = b + \sum_j \beta_j\frac{x_j(d,s)-\mu_j}{\sigma_j},
\]

then orders eligible candidates by (z(d,s)), with deterministic baseline-rank
and ASIN tie-breaking. It is a regularized `sklearn.linear_model.LogisticRegression`
model trained with per-group-balanced weights, so a group with many negatives
does not dominate the objective.

The features are:

1. negative log baseline rank;
2. final lexical/evidence score;
3. aggregate score;
4. evidence score;
5. interaction score;
6. matched-field count;
7. route support;
8. BM25 score;
9. BM25 missingness;
10. log `rating_number`;
11. price presence;
12. log feature count;
13. average rating;
14. description presence;
15. exact opening-category match;
16. opening-category information content;
17. negative log category-popularity rank.

Some listed features were later shown to be degenerate in this data, as noted
above. The model was retained because the complete strict OOF protocol,
permutation control, and end-to-end replay supported its measured effect.

## 6. Chronological research record

### 6.1 Foundation: E000--E024

| Area | What was tested | Decision |
|---|---|---|
| Baseline/history/repeat policy | E000--E003 | Preserve dialogue history and hard exclusion/repeat policy. |
| Question criteria | E004--E011 entropy, split, expected-value, answerability, gating | Answerability split was retained; entropy/expected-utility variants were not. |
| Constraint semantics | E012--E017 strengths, operations, reset, decay, contradiction, semantic ranking | Explicit strengths and selective intent reset retained; complex extensions not promoted. |
| Wildcard initiation | E018--E020 always/first/until exhausted | Broad wildcard policies did not become robust defaults. |
| Fingerprint and routing | E021--E023 | Fingerprint retrieval and cautious scenario handling supplied the evaluator branch foundation. |
| Diversity | E024 | Explore-slot diversity variants did not justify promotion. |

### 6.2 Retrieval and ranking: E025--E058

| Area | Result |
|---|---|
| E025 field-aware evidence | Aggregated field evidence promoted; it improved lexical precision without requiring a dense model. |
| E026--E030 residual audits, multi-route fusion, coverage, learned reranking | Audits localized misses; fusion, coverage, and learned reranking did not pass. |
| E031--E034 protected ordering, pool expansion, structured BM25 | Rejected for technical-score regression or insufficient stable recall. |
| E035--E036 clarification exhaustion and terminal wildcard | Exhaustion recovery retained; evaluator-only terminal wildcard remained below the stronger route. |
| E037--E050 oracle/headroom/ambiguity work | Useful for locating theoretical headroom, but did not yield a stable observable learner. |
| E046 category-conditional specificity | Development-positive and five-fold positive, but failed holdout robustness; rejected. |
| E051--E054 collision proxy and synthetic interaction reranker | No target-aligned, generalizable collision signal. |
| E057 normalization | Correctness hardening; score-neutral as expected. |
| E058 phrase-IDF correction | Robust baseline: `.871721` development, `.865174` holdout, zero hard violations. |

### 6.3 Popularity, safety, and wildcard information flow: P001--P006

| Experiment | Result and decision |
|---|---|
| P001 popularity prior | Pure popularity rejected; RRF fusion (`k=60`) reached `.866824` dev / `.858864` holdout and was retained. |
| P002 safety partition | Eliminated confirmed hard violations while retaining score; P002A robust and P002C evaluator-specific safety paths retained. |
| P003 robustness | Demonstrated material dependence on `rating_number`; recorded as a risk rather than hidden. |
| P004 runtime profile | Measured cold start, RSS, and turn latency; clean reproduction passed. |
| P005 visible-signal audit | No independent participant-visible catalog signal surpassed `rating_number`. |
| P006 wildcard flow | Atomic wildcard facts plus override reset passed independently; P006C reached `.899220` dev / `.869145` holdout in its evaluator-specific scope. |

### 6.4 Exposure-policy research: K001--K007 and P007--P008

| Experiment | Result and decision |
|---|---|
| K001 | K5 while asking, K10 otherwise revealed large MRR gains from preserving candidate inventory. |
| K002 | Final-turn release was already implied by the baseline; no-preference release lost score. |
| K003/K005 | Bounded K7 through K0 sweep showed lower limits could improve development but K0 harmed HR/latency; stopped rather than continuing schedules. |
| K006 | Substantive-answer K1 / no-information K3 / otherwise K10 was best non-wildcard policy: `.918367` dev, `.893400` holdout. |
| K007 | Cumulative-cap and rank-churn policies did not exceed the simpler K006C schedule. |
| P007 | On the P006C wildcard path, wildcard K1 / named K3 / no-question K10 became P007D: `.931986` dev, `.924000` holdout. |
| P008 | Feature/material K2 and other named K3 gave a `.005183` development-only gain over P007D, but no additional holdout selection was performed. |

### 6.5 Semantic and LLM feasibility: E059/C0/M001

The system explicitly tested whether generic semantic models could resolve
ranking errors rather than assuming that larger neural models improve an exact
target task.

- E059 used a frozen Top-50 semantic-headroom probe. Generic semantic reranking
  did not meet its gate.
- C0 used 155 naturally occurring Top-10 states. The cached
  `cross-encoder/ms-marco-MiniLM-L6-v2` reduced MRR from `.662458` to `.471907`
  and hard-pair accuracy from `.817204` to `.681720`; it was rejected.
- Qwen3.5-9B Q6_K was run locally through `llama.cpp` for M001 structured
  collision extraction. It chose the target in 11/21 pairs, below the required
  16/21 and Wilson lower-bound gate. No prompt tuning or rerun followed.
- The attempted local Qwen ceiling probe was not accepted because the CUDA
  `llama.cpp` run reported ignored tensors; invalid model execution was not
  treated as evidence.

### 6.6 Planner and simulator-policy research: B001--B003 and R10--R102D

B001 calibrated offline beliefs. Score-softmax improved product-disjoint held-out
log loss from `4.033494` to `3.718934` and Brier score from `.933717` to
`.808972`, but it did not predict next-turn promotion (AUC `.414286`). B002
measured specification disclosure, including exact, rare, and unique phrases.

B003 combined belief and an empirical response-event model. B003B improved
development (`.894733` versus `.891833`) but reversed on holdout (`.869600`
versus `.874000`), so the planner branch was rejected.

The later counterfactual policy-learning branch was not simply abandoned for
runtime cost; it was measured and rejected for source shift:

- R100 synthetic sessions made fixed K10 appear much better than K006C,
  contradicting released behavior.
- R101 measured a severe source mismatch: synthetic popularity percentile
  `.502573` versus released `.957580`; source discriminator logistic AUC
  `.971867`.
- R102 matched target category and popularity margins, restoring sensible fixed
  policy ordering with K006C `.797061` above fixed K10 `.785907`.
- R102D still found trajectory-only source AUC `.715260`, only 19.4% reliable
  closure of the session-length gap through static reweighting, and substantial
  turns-2--5 dynamics mismatch.

The final decision was not to train a simulator-derived exposure policy. This
avoids converting an uncalibrated synthetic source into runtime policy labels.

### 6.7 Residual learned-ranking research: E060--E067

E060 had the strongest later development-only evidence. It produced strict OOF
Technical Score `.957400` versus P008A `.937169`, paired session delta
`+.020231`, 95% CI `[+.010517, +.032667]`, 43 improved / 5 worsened / 102 tied,
and zero hard-safety violations.

Residual work deliberately looked for a new independent information source
rather than endlessly refitting the same features:

| Experiment | Outcome |
|---|---|
| E061 | 46 non-rank-1 groups plus one shortlist miss; residuals mostly relevance-limited. The potentially valuable leave-last-out interaction source was unavailable and not fabricated. |
| E062R | Generic category shortlist expansion recovered one miss but diluted 16/23 triggered sessions; rejected. |
| E062G | Relevance/popularity disagreement gate solved 4 states and worsened 14; rejected. |
| E062X | No unused static catalog signal met its 16/22 target-win gate. |
| E063 | One-candidate shadow-category rescue caused zero terminal changes; rejected. |
| E064 | Unfused relevance/popularity representation gained `.002467` end-to-end with a CI crossing zero; rejected. |
| E065 | Broad category metadata lost `.001600` end-to-end; rejected. |
| E066 | Grouped softmax/conditional-logit objective gained `.003133` but bootstrap lower CI was negative; rejected. |
| E067 / E064C | Read-only state-conditioned and rank-disagreement signal was below the `.003` full-evaluation gate; closed. |
| W001 / O001/O002 | Wildcard lineage preserved; old exposure restoration was worse. Override retrieval/category re-anchoring was clearly negative. |

## 7. Libraries, frameworks, and execution environment

### 7.1 Runtime

- Python 3.10+ standard library only for the submitted E058 runtime.
- `sqlite3` with FTS5 for catalog indexing and BM25 retrieval.
- Deterministic Python sorting, SHA-256 split/tie logic, JSON configs, and
  target-free runtime diagnostics.

### 7.2 Research and diagnostics

- NumPy for feature matrices and numeric diagnostics.
- scikit-learn `LogisticRegression`, `StandardScaler`, `StratifiedKFold`,
  `StratifiedGroupKFold`, `Pipeline`, `ColumnTransformer`, and AUC metrics.
- SciPy optimization for the grouped-softmax/conditional-logit E066 audit and
  statistical helpers used in simulator calibration.
- `sentence-transformers` `CrossEncoder` for the frozen MiniLM semantic probe.
- Local `llama.cpp` plus Qwen3.5-9B Q6_K for the bounded M001 structured-LLM
  experiment.
- Python `unittest` for behavior and experiment-workflow regression tests.

Neither the MiniLM nor Qwen dependency is required by the submitted lexical
runtime; both were research-only probes and were rejected.

## 8. Safety, leakage, and audit controls

The project used several distinct safeguards. They address different risks and
should not be conflated.

| Safeguard | What it protects against |
|---|---|
| Runtime target-free design | Hidden target labels, ASIN dispatch, future answer, or target rank leaking into live decisions. |
| Candidate-membership freeze | A reranker appearing successful by injecting the target into its candidate pool. |
| Product-disjoint folds | Product identity leaking from another group or a negative example. |
| Paired session bootstrap | Treating correlated turns/states as independent evidence. |
| Label permutation | Spurious apparent learning caused by implementation/data geometry rather than target association. |
| Train/serve replay parity | Training inputs differing from inputs seen by the deployed model. |
| Feature integrity audit | Interpreting dead or duplicate feature columns as real signal. |
| Semantic lineage replay | Accidentally changing wildcard/override state semantics while changing exposure/ranking. |
| Hard-safety partition | Popularity or learned ranking surfacing a product known to violate an explicit hard preference. |
| Explicit configuration dispatch | Evaluator-specific or experimental behavior silently replacing the robust default. |
| Artifact hashes and test suite | Undetected drift in code/config/model artifacts. |

## 9. What worked, what did not, and why

### What worked

- Exact lexical and field-aware evidence matched the task's product-identification
  objective better than generic semantic relevance.
- Normalization and phrase-IDF correctness fixes improved trustworthiness and,
  for E058, score.
- Answerability-aware clarification and exhaustion recovery improved information
  acquisition without relying on an inaccurate answer simulator.
- Constraint-safe popularity RRF supplied a strong independent catalog prior
  while preserving explicit hard requirements.
- Atomic wildcard facts and override reset worked when the evaluator's exact
  wildcard behavior could be assumed.
- Exposure control worked because recommendation display consumes candidate
  inventory before future evidence arrives.
- E060's catalog-visible target-propensity posterior showed strong strict-OOF
  signal under product-disjoint folds, permutations, ablations, and parity
  verification.

### What did not work

- Generic dense/cross-encoder reranking optimized semantic relevance but
  materially harmed exact target rank.
- Broad taxonomy/category expansion introduced false matches and candidate-cap
  pressure.
- Route fusion, wider pools, diversity, and coverage rerankers lacked a new
  discriminative signal and diluted strong lexical order.
- Entropy/expected-utility question policies depended on response assumptions
  not supported by observed answerability.
- Bayesian response/planner methods improved development in one case but did
  not generalize to holdout.
- Synthetic simulator policy learning suffered from both static target-source
  shift and sequential-dynamics shift.
- Structured LLM extraction did not pass its frozen collision gate.
- Fine-grained manual exposure schedules risked development overfitting after
  the main action-conditioned mechanism had been established.

## 10. Limitations and honest interpretation

- Popularity is predictive in this benchmark but is not automatically portable
  to a different catalog or private distribution.
- P007D depends on repeated wildcard questions, visible semicolon-delimited
  facts, and override lifecycle semantics matching the released evaluator.
- The historical holdout was inspected repeatedly across the research program;
  it should be treated as confirmation evidence, not untouched selection data.
- E060 has not received a new authorized external/holdout confirmation. Its
  `.957400` is a strict development OOF estimate, not a claim of private-test
  performance.
- The catalog interaction/leave-last-out source that might provide a genuinely
  independent target prior was unavailable locally. It was not reconstructed or
  guessed from hidden labels.
- The semantic probe results reject the tested checkpoint and prompt protocol;
  they do not prove that every future stronger model would fail.
- A score improvement does not override safety, provenance, or deployment-risk
  gates.

## 11. Reproduction and evidence map

Start with these entry points:

- [experiment log](../../experiments.md) for the chronological public record;
- [final exposure campaign](FINAL_MAXIMUM_SCORE_CAMPAIGN.md) for K006C/P007D;
- [E060 methodology](E060_early_union_target_posterior.md) and
  [attribution controls](E060_attribution_controls.md) for strict OOF model
  evidence;
- [Phase A report](PhaseA_consolidated_diagnostics.md) and its
  [machine-readable diagnostic](../diagnostics/PhaseA_consolidated_diagnostics.json)
  for final parity, lineage, integrity, and deployment checks;
- [stress-testing and assurance appendix](STRESS_TESTING_AND_ASSURANCE_APPENDIX.md)
  for exact perturbations, catalog ablations, source-shift tests, red-team
  controls, and their scope;
- [policy-learning decision](POLICY_LEARNING_FINAL_DECISION.md) for the
  simulator branch rejection;
- [mechanism matrix](../../research_transfer_bundle/MECHANISM_MATRIX.md) and
  [negative-results register](../../research_transfer_bundle/NEGATIVE_RESULTS.md)
  for compact portability guidance.

Representative reproduction commands are:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe experiments\run_experiment.py --config configs\E058_phrase_idf_key_correction.json --split development
.\.venv\Scripts\python.exe experiments\run_experiment.py --config configs\K006C_substantive_answer_exposure.json --split development
.\.venv\Scripts\python.exe experiments\evaluate_e060_oof.py
.\.venv\Scripts\python.exe experiments\audit_e060_attribution_controls.py
.\.venv\Scripts\python.exe experiments\phase_a_consolidated_diagnostics.py
```

Holdout must not be run merely to reproduce a result. It is reserved for an
explicitly frozen confirmation protocol.

## 12. Final project conclusion

The project progressed from a lexical conversational baseline to a
stateful, field-aware, safety-constrained sequential ranker. The strongest
durable mechanisms were not generic complexity: they were evidence correctness,
answerability-aware information acquisition, a constrained catalog prior, and
careful exposure of recommendations before new information arrives.

The research record is intentionally conservative. It retains the robust,
score-optimized, and evaluator-specific configurations separately; documents
why semantic, planner, taxonomy, and simulator-policy branches were rejected;
and validates the learned E060 branch with product-disjoint folds, permutation
controls, bootstrap confidence intervals, train/serve parity, feature audits,
lineage replay, hashes, and regression tests. This is the basis on which the
submission's performance claims should be interpreted.
