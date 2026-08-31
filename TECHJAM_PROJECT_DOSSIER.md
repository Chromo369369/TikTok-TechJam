# TechJam Shopping Copilot: Final Project Dossier

**Status:** frozen champion validation complete  
**Final robust champion:** E035B — ungated named-attribute exhaustion recovery  
**Final released-evaluator champion:** E022 — repeated `other` plus fingerprint retrieval  
**Evaluation date:** 27 August 2026  
**Repository state evaluated:** commit `5f66f94` plus the repository's existing uncommitted experiment implementation and artifacts  
**Validation result:** 30/30 tests pass; no champion regression found

## Executive summary

This project began with a weak stateless BM25 agent and ended with two deliberately separate champions:

- **E035B is the defensible robust system.** It uses cumulative dialogue state, override-aware repeat suppression, confidence-aware constraints, answerability-adjusted clarification, catalog-only fingerprint and field-aware evidence retrieval, and a final named-attribute fallback when normal clarification becomes exhausted. It contains no wildcard behavior.
- **E022 is the released-evaluator specialist.** It repeatedly asks `other`, exploiting a high-bandwidth response behavior in the public simulator, and fuses the resulting phrases with fingerprint retrieval. It scores higher locally, but its advantage depends on evaluator semantics that may not generalize.

The fresh final run confirms that E035B remains stable and E022 remains the evaluator leader. E035B exactly reproduced every archived aggregate on development, holdout, and full data. E022 exactly reproduced holdout and full aggregates. Its fresh development score is slightly higher than the older narrative artifact (`.854816` versus `.854294`), a `+.000522` difference caused by the current integrated implementation/artifact state; it is not a regression and does not change selection.

The strongest defensible project claim is:

> We systematically removed the dominant retrieval, dialogue, and convergence bottlenecks until the remaining robust errors were largely retrieval-limited or observationally ambiguous under the evidence available at runtime.

The project should remain frozen unless new evaluator guidance, a newly observed recurring failure class, a truly new runtime-observable signal, or an implementation defect changes the evidence.

## 1. Problem and evaluation contract

The agent must identify a hidden target product from a frozen 50,000-product clothing, shoes, and jewelry catalog. It can ask one allowed clarification attribute and return up to ten recommendations per turn. A session succeeds when the target appears in the scored Top 10, with at most ten turns.

The public set contains 200 sessions across Buying, Browsing, Intent Override, and Boundary behavior. The experiment workflow deterministically partitions these into 150 development and 50 holdout sessions by hashing `techjam-v1:<sample_id>`.

The technical score is:

```text
Technical Score = 0.50 × HR@10 + 0.30 × MRR + 0.20 × Efficiency
Efficiency       = clip((11 − MTTC) / 10, 0, 1)
```

This objective creates three related but distinct goals:

- **HR@10:** recover the target at all.
- **MRR:** rank it high when it is recoverable.
- **MTTC:** acquire enough useful information early.

## 2. Final fresh evaluation

### 2.1 Aggregate results

| Champion | Split | N | HR@10 | MRR | MTTC | Efficiency | Technical score | Misses |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E035B robust | Development | 150 | .986667 | .557614 | 2.973333 | .802667 | **.821151** | 2 |
| E035B robust | Holdout | 50 | .980000 | .601746 | 3.020000 | .798000 | **.830124** | 1 |
| E035B robust | Full | 200 | .985000 | .568647 | 2.985000 | .801500 | **.823394** | 3 |
| E022 evaluator | Development | 150 | .973333 | .675164 | 2.720000 | .828000 | **.854816** | 4 |
| E022 evaluator | Holdout | 50 | .980000 | .668325 | 2.740000 | .826000 | **.855697** | 1 |
| E022 evaluator | Full | 200 | .975000 | .673454 | 2.725000 | .827500 | **.855036** | 5 |

E035B gives up MRR and speed relative to E022, but has slightly higher full-set hit rate and avoids the evaluator-specific wildcard dependency. The comparison is therefore not “weaker versus stronger” in one universal sense; it is robust policy versus simulator-specialized policy.

### 2.2 Reproduction check

| Run | Archived reference | Fresh | Result |
|---|---:|---:|---|
| E035B development score | .821151 | .821151 | exact |
| E035B holdout score | .830124 | .830124 | exact |
| E035B full score | .823394 | .823394 | exact |
| E022 holdout score | .855697 | .855697 | exact |
| E022 full score | .855036 | .855036 | exact |
| E022 development score | .854294 in older note | .854816 | `+.000522`; benign drift |

The fresh E022 development run has MRR `.675164` and MTTC `2.720000`; the older note records `.673868` and `2.726667`. The current run uses the current frozen config against the integrated repository implementation. Because holdout and full reproduce exactly and development improves rather than regresses, there is no evidence to unfreeze or replace E022. Historical values remain historical rather than being retroactively edited.

### 2.3 Full-set scenario diagnostics

| Champion | Scenario | N | HR@10 | MRR | MTTC |
|---|---|---:|---:|---:|---:|
| E035B | Boundary | 10 | .9000 | .417619 | 4.500000 |
| E035B | Browsing | 80 | 1.0000 | .676647 | 2.662500 |
| E035B | Buying | 80 | .9750 | .486121 | 2.487500 |
| E035B | Intent Override | 30 | 1.0000 | .551058 | 4.666667 |
| E022 | Boundary | 10 | .9000 | .734286 | 4.200000 |
| E022 | Browsing | 80 | .9875 | .703522 | 2.487500 |
| E022 | Buying | 80 | .9625 | .613710 | 2.275000 |
| E022 | Intent Override | 30 | 1.0000 | .732315 | 4.066667 |

E035B fully covers Browsing and Intent Override on the public full set. Its clearest ranking weakness is Buying MRR; its slowest scenario is Intent Override, where old intent must be retired and new evidence accumulated. Boundary is the smallest slice and remains statistically fragile. E022's wildcard channel strongly raises rank across scenarios but loses two additional full-set hits.

### 2.4 Conversion-turn distribution

| First hit turn | E035B sessions | E022 sessions |
|---:|---:|---:|
| 1 | 30 | 24 |
| 2 | 74 | 100 |
| 3 | 43 | 41 |
| 4 | 25 | 21 |
| 5 | 9 | 1 |
| 6 | 6 | 3 |
| 7 | 6 | 4 |
| 8 | 3 | 1 |
| 9 | 0 | 0 |
| 10 | 1 | 0 |
| Miss | 3 | 5 |

E022's advantage is concentrated at turn 2: its wildcard response often provides target-specific evidence immediately. E035B has more turn-1 hits and fewer total misses, but a longer tail.

### 2.5 Dialogue and retrieval diagnostics

| Diagnostic, full set | E035B | E022 |
|---|---:|---:|
| Responses | 594 | 540 |
| Questions asked | 583 | 528 |
| `other` questions | 0 | 422 |
| No-preference replies | 148 | 68 |
| Target entered Top 10 after a question | 121 | 141 |
| Target moved upward after a question | 241 | 209 |
| Repeats suppressed | 4,533 | 2,827 |
| Unique products shown | 5,781 | 5,161 |
| Evidence-route recall@20 | .316498 | .220370 |
| Evidence-route recall@50 | .521886 | .270370 |
| Evidence-route recall@100 | .626263 | .292593 |
| Evidence-route recall@200 | .720539 | .338889 |
| Mean target tie group | 11.491770 | 1.022444 |

The E022 evidence-route figures should not be read as inferior end-to-end retrieval. Its fingerprint path and wildcard-derived evidence operate differently from E035B's aggregate field route. The near-unit tie group reflects highly specific wildcard-derived phrases, while E035B must rank broad catalog-equivalent groups from ordinary named attributes.

E035B's full-set question mix was: feature 208, color 124, material 117, brand 59, style 32, size 15, use case 15, and budget 13. Feature, material, and color provide most of the ordinary dialogue bandwidth.

### 2.6 Residual misses

E035B's three misses are unchanged:

| Session | Scenario | Diagnostic classification |
|---|---|---|
| `public_0028` | Buying | retrieval-limited; first reaches the recorded Top 200 at turn 3, but not Top 100 |
| `public_0161` | Buying | retrieval-limited; never enters the recorded Top 200 |
| `public_0180` | Boundary | retrieval-limited; never enters the recorded Top 200 |

Earlier offline work found no remaining allowed named attribute with a material separation effect for these sessions. They are not evidence for another generic fallback rule.

E022 misses `public_0020`, `public_0028`, `public_0035`, `public_0083`, and `public_0087`. Its extra MRR does not imply uniformly better recall: the repeated wildcard specializes in moving recoverable targets very high.

## 3. System architecture at freeze

### E035B robust path

```text
current message + session history
              ↓
override-aware dialogue state
              ↓
confidence/strength constraints and no-preference tracking
              ↓
BM25 + catalog-only fingerprint + aggregate field-evidence candidates
              ↓
constraint-aware ranking and repeat suppression
              ↓
answerability-adjusted candidate-split question
              ↓
if ordinary selection is exhausted:
highest-scored remaining named attribute with positive coverage
```

Key safeguards include deterministic operation, no runtime access to hidden targets or scenario labels, hard-constraint violation penalties, stale-constraint deactivation after overrides, and recommendations alongside questions.

### E022 evaluator-specific path

E022 retains dialogue state, reranking, repeat suppression, and fingerprint retrieval but repeatedly routes clarification through `other` until that channel is exhausted. In the released simulator, `other` reveals unusually discriminative product text. That is why E022 is intentionally isolated in `best_evaluator.json` rather than promoted to the robust default.

## 4. The experiment journey

### Phase A — establish state and exploration: E000–E003

- **E000 stateless BM25:** full score `.106710`. Searching only the latest message is fundamentally inadequate.
- **E001 cumulative history:** score `.228414`. Retaining requirements more than doubled HR and MRR.
- **E002 override-aware hard exclusion:** full score `.402072`. Suppressing already shown products broadened coverage, while resetting on explicit intent changes avoided permanently hiding viable products.
- **E003 confidence-weighted constraints:** full score `.409724`. Linguistic strength improved ordering and speed without changing overall hit rate.

Learning: the first large gain did not come from sophisticated ranking. It came from remembering the conversation and managing exploration correctly.

### Phase B — learn to ask: E004–E011

- **E004 candidate-split clarification:** development score `.727529`; the largest single architectural jump. Ask the sufficiently covered unresolved attribute whose largest value bucket is smallest.
- **E005 unweighted entropy:** `.718787`, rejected.
- **E006 probability-weighted entropy:** `.725229`, rejected despite recovering most of E005's loss.
- **E007 expected competition-value proxy:** `.716158`, rejected; proxy optimization did not align with actual target outcomes.
- **E008 weighted split:** `.722546`, rejected.
- **E009 expected elimination:** rejected; average elimination was less useful than controlling the worst remaining bucket.
- **E010 answerability-adjusted split:** development `.769408`, holdout `.785664`, accepted. Information gain matters only when the simulator/user can provide a substantive answer.
- **E011 confidence gating:** `.674503`, rejected. Suppressing low-score questions removed too much useful information.

Learning: simple, robust question heuristics beat more elaborate information-theoretic objectives. Answerability is a first-class part of question value.

### Phase C — improve dialogue semantics: E012–E017

- **E012 three-level constraint strength:** full `.778996`, accepted. Hard, normal, and soft evidence was a better representation than one undifferentiated confidence scheme.
- **E013 operation-aware state:** metric-neutral with suspicious lexical operations; rejected.
- **E014 selective intent reset:** tiny development-only MRR movement; rejected.
- **E015 soft decay:** no aged soft constraints in the evaluated paths, so all gamma variants were behavioral no-ops; rejected.
- **E016 contradiction resolution:** no contradictions detected; metric-neutral and rejected.
- **E017 state-semantic ranking:** improved some compliance/MTTC behavior but reduced MRR and score; rejected.

Learning: representation changes help when the data actually exercises them. Several plausible state mechanisms were inactive or too rare, and instrumentation prevented mistaking code complexity for improvement.

### Phase D — expose evaluator semantics and improve representation: E018–E025

- **E018 always `other`:** development `.804084`, revealing a high-bandwidth simulator behavior but poor Boundary robustness.
- **E019 `other` first:** `.830475`.
- **E020 `other` until exhausted:** `.837037`.
- **E021 catalog-only intent fingerprint:** development `.792059`, holdout `.811433`; accepted as a robust representation gain.
- **E022 repeated `other` + fingerprint:** became the evaluator champion.
- **E023 observable scenario routing:** `.759382`, rejected.
- **E024 diversity schedules:** effectively neutral or slightly worse; rejected.
- **E025 field-aware retrieval ablation:** phrase-only, controlled-value, structured-only, and aggregate routes isolated the value of catalog fields. E025D aggregate evidence reached `.808106` development and `.824324` holdout and became robust champion.

Learning: richer catalog representation improved robust retrieval, while wildcard clarification exposed a separate evaluator-specific ceiling. Keeping the two tracks separate prevented a simulator shortcut from contaminating the production claim.

### Phase E — attack retrieval and reranking: E026–E034

- **E026 residual recall audit:** instrumented route ranks and failure stages.
- **E027 reranker regression audit:** found 128 target improvements versus 16 regressions, without one dominant fixable penalty mechanism.
- **E028 conservative multi-route fusion:** `.803935`, rejected.
- **E029 evidence-coverage reranker:** improved conditional ranking but lost HR and MTTC; `.799086`, rejected.
- **E030 learned reranker:** deferred because no stable promotable feature pattern existed.
- **E031 protected-ordering variants:** all preserved Top-10 membership; none improved ordering over E025D.
- **E032 structured candidate quotas 100/150/300:** wider admission peaked at `.806470`, still below E025D.
- **E033 guardrail audit:** no recurring global regression mechanism justified a new guardrail.
- **E034 structured-state BM25 expansion:** `.807482`, rejected.

Learning: once recall was high, adding routes or ranking terms mostly rearranged errors. Candidate width alone could admit a difficult target without ranking it anywhere near Top 10.

### Phase F — repair dead turns and measure residual headroom: E035–E046

- **E035A control:** `.808106`.
- **E035B ungated exhaustion recovery:** `.821151` development, `.830124` holdout; accepted. When normal selection has no question, ask the highest-scored remaining named attribute with positive coverage.
- **E035C explicit-only recovery:** `.820351`, slightly weaker than E035B.
- **E036 terminal `other`:** `.826801`; better than robust but far below E022 and still wildcard-dependent.
- **E037 residual miss audit:** all three E035B misses retrieval-limited.
- **E038 fallback actionability:** only 16 cases; four feature questions were strong but single-category and too sparse to justify E039.
- **E040 candidate-union oracle:** HR `.990` versus `.985` observed, only `.005` raw robust HR headroom.
- **E041 ambiguity stratification:** broad-ambiguity turns had much worse RR.
- **E043 one/two early wildcard:** first two disclosures were valuable, but bounded E043B failed holdout against E022.
- **E044 rank oracle:** development MRR `.993333` and score `.984267` if a hidden-target oracle places present targets first.
- **E045 question oracle:** on 60 high-ambiguity turns, the best allowed simulator-aware question improved RR by about `.17–.20` on average.
- **E046 category-conditional specificity:** `.834609` development, five of five CV folds won, bootstrap CI positive; nevertheless `.829067` holdout versus E035B `.830124`, so it was correctly rejected.

Learning: E035B fixed a real dialogue exhaustion defect. Large oracle ceilings remained, but the holdout rejection of E046 demonstrated why theoretical headroom and development significance are not sufficient for promotion.

### Phase G — test whether oracle headroom is learnable: E047–E056

- **E047:** not run because the proposed ambiguity fallback was already E035B behavior.
- **E048:** oracle question labels were acknowledged as simulator-aware; no runtime learner was authorized without catalog-only predictors.
- **E049:** conditional-IDF gains did not form a stable observable regime.
- **E050:** 93.7% of high-tie false positives shared the target's matched-field bitmap.
- **E051:** richer comparison reduced exact collision rates, but 44.8% still shared the complete runtime feature vector.
- **Collision question proxy:** only 48.3% oracle-best agreement, a 1.7-point gain over E035B and below its predeclared gate.
- **E052 wildcard × field evidence:** `.851544`, rejected against E022 because HR/MTTC gains did not compensate for lost MRR.
- **E054 catalog-trained interaction reranker:** `.821075`, a `.000076` regression; rejected.
- **E055:** skipped because it duplicated E052 exactly.
- **E056:** target-independent robustness suite, ablation ladder, and contribution waterfall; champions unchanged.

Learning: much of the dramatic rank-oracle ceiling is not realistically learnable from current visible evidence. The final phase falsified the most plausible generic reranking and question-selection proxies.

## 5. Accepted contribution ladder

The deltas below are adjacent observed changes, not isolated causal effects; subsystems interact.

| Step | Score | Adjacent gain | Main lesson |
|---|---:|---:|---|
| Starter BM25 | .106710 | — | Stateless retrieval is insufficient |
| Conversation state / no-question control | .410032 | +.303322 | State and exploration matter |
| E004 candidate split | .727529 | +.317497 | Active clarification is transformative |
| E010 answerability | .769408 | +.041879 | Ask questions that can be answered |
| E021 fingerprint | .792059 | +.022651 | Catalog-grounded representation matters |
| E025D field evidence | .808106 | +.016047 | Combine complementary catalog fields |
| E035B exhaustion fallback | .821151 | +.013045 | Do not stop acquiring evidence prematurely |
| E022 evaluator specialist | .854816 fresh dev | separate track | Wildcard is a simulator-specific information channel |

## 6. Rejected branches and what they taught

| Branch | Outcome | Durable lesson |
|---|---|---|
| Entropy and probability-weighted question scores | Rejected | More sophisticated uncertainty measures did not beat largest-bucket splitting |
| Expected utility/elimination proxies | Rejected | Hand-built proxies were not calibrated to target rank and conversion |
| Minimum-score question gating | Rejected | Weak-looking questions can still be useful; premature silence is costly |
| Operation/contradiction/decay machinery | Neutral or inactive | Confirm that the evaluated data activates a mechanism before tuning it |
| Observable scenario router | Rejected | Coarse routing threw away stronger shared behavior |
| Result-list diversity | Neutral | Hard repeat suppression already supplied most useful exploration |
| Multi-route fusion | Rejected | Route agreement is not automatically evidence of target correctness |
| Evidence coverage reranking | Rejected | Better conditional MRR can still lose total score through HR/MTTC |
| Wider structured pools | Rejected | Admission without discriminative ordering does not solve ranking |
| Structured BM25 expansion | Rejected | Generic lexical expansion adds noise as well as recall |
| Bounded wildcard schedules | Rejected | The evaluator advantage was not captured reliably by one or two prompts |
| Category-conditional IDF | Rejected on holdout | Even strong CV and bootstrap evidence can fail a true holdout |
| Collision-based question policy | Failed gate | Observable ambiguity proxies did not predict the oracle question reliably |
| Catalog-trained interaction reranker | Rejected | Synthetic catalog supervision did not transfer to conversational ranking |
| Wildcard × aggregate field evidence | Rejected | Higher HR and faster hits can lose to a substantial MRR decline |

## 7. Robustness findings

E056 used the fixed 150-session development split and deterministic, target-independent perturbations.

| Perturbation | HR@10 | MRR | Score | Δscore |
|---|---:|---:|---:|---:|
| Control | .986667 | .557614 | .821151 | — |
| Lowercase + remove punctuation | .960000 | .483892 | .777168 | −.043983 |
| Harmless filler | .986667 | .540471 | .816275 | −.004876 |
| No-preference paraphrase | .986667 | .559828 | .822482 | +.001331 |
| Override paraphrase | .980000 | .589632 | .828090 | +.006939 |
| Missing details | .973333 | .550640 | .810525 | −.010626 |
| Missing features | .560000 | .235696 | .435642 | **−.385509** |
| No description | .986667 | .531323 | .811397 | −.009754 |
| Lowercase catalog metadata | .986667 | .559836 | .821818 | +.000667 |
| Remove leaf category | .893333 | .492397 | .732119 | **−.089032** |
| Missing store | .986667 | .548688 | .818073 | −.003078 |

The robust champion is robust to casing and conversational paraphrase, mildly sensitive to filler and secondary catalog fields, materially sensitive to punctuation normalization and taxonomy depth, and critically dependent on feature metadata.

That feature dependence is not automatically a bug: the benchmark supplies features as valuable product evidence. It becomes a deployment risk if private or future catalogs differ in completeness or formatting.

## 8. Current weaknesses, unpatched items, and open risks

### Confirmed weaknesses

1. **Feature metadata is a single point of performance failure.** Removing it cuts score from `.821151` to `.435642`.
2. **Leaf-category depth carries major signal.** Removing the leaf category costs `.089032` score.
3. **Punctuation normalization is brittle.** Lowercasing alone is safe, but punctuation removal costs `.043983` when combined with lowercasing.
4. **Robust MRR remains ambiguity-limited.** Mean target tie groups are large, and high-ambiguity competitors frequently share the target's visible evidence.
5. **Buying ranking is weaker than browsing.** Full E035B Buying MRR is `.486121`, versus Browsing `.676647`.
6. **Intent changes take time.** E035B Intent Override MTTC is `4.666667` despite perfect HR.
7. **Three robust misses are retrieval-limited.** Current allowed questions do not repair them.
8. **E022 depends on unverified wildcard semantics.** Its local advantage may disappear if the private evaluator answers `other` differently.

### Things the process may still have missed

- No clean-environment packaging or latency/memory benchmark is recorded in the final experiment narrative.
- Public evaluation contains only 200 sessions; Boundary has only ten full-set examples. Fine-grained scenario conclusions have wide uncertainty.
- The development/holdout protocol protects promotion, but dozens of sequential hypotheses still create research-selection pressure around the public set.
- The stress suite deletes whole fields. It does not yet map partial missingness, adversarial malformed values, multilingual text, Unicode punctuation, unit normalization, or category-schema migrations.
- The evaluator reports zero model-token use because the champion is local/deterministic; production integration behavior, API failure handling, and latency are outside these runs.
- Exact target equality is appropriate for the benchmark but does not measure substitute quality, diversity, user satisfaction, or whether a near-equivalent product would be acceptable.
- There is no evidence yet that the public catalog distribution matches the 800 private sessions beyond the organizer's frozen-data specification.
- The current repository is a research working tree with extensive uncommitted files. Commit hashes alone do not identify the evaluated state; an immutable release snapshot and checksums are still needed.

### Important non-bugs

- The large `.984` rank-oracle score is not a realistic model target. The oracle knows which candidate is hidden truth; runtime does not.
- Low aggregate evidence-route recall in E022 is not by itself a defect because its wildcard fingerprint path supplies a different information channel.
- Dependence on rich metadata is acceptable if the catalog is truly frozen and consistently populated.
- E046's holdout loss is small, but promoting it anyway would violate the project's most valuable anti-overfitting rule.

## 9. Remaining evidence-backed avenues

These are ranked by expected value and risk. None currently justifies changing the champions without a new gated experiment.

### Tier 1 — engineering validation, not score chasing

1. **Punctuation invariance audit.** Trace token boundaries, phrase extraction, controlled-value canonicalization, category normalization, and SQLite FTS queries for equivalent forms such as `100% cotton`, `100 cotton`, ampersands, hyphens, and apostrophes. Promote only a natural normalization fix that is behavior-neutral on untouched data and passes dev/CV/holdout.
2. **Category backoff audit.** Verify graceful use of parent, grandparent, and department evidence when a leaf is absent. Do not tune directly against E056.
3. **Missing-feature degradation audit.** Determine whether absence merely removes genuine information or also causes abnormal score collapse, implicit contradiction, or failure to renormalize remaining evidence.
4. **Reproducible release packaging.** Freeze code, configs, catalog checksum, environment, and exact commands; add clean-checkout verification and resource measurements.
5. **Organizer clarification on `other`.** The answer determines whether E022 is a legitimate final policy or only a public-simulator diagnostic.

### Tier 2 — research only if new evidence appears

1. **Early high-ambiguity question-value prediction** from runtime-observable features, trained strictly out of fold on representative real conversations. E045 proves possible value, but current proxies fail.
2. **Confidence-gated additional clarification** only where uncertainty is high and answerability is strong. It must be genuinely different from E035B's existing exhaustion behavior.
3. **New semantic retrieval route** only after repeated examples show semantically correct targets missing lexical and structured routes, with measurable unique recall contribution.
4. **Richer conversational supervision for ranking.** Catalog-synthetic interaction training failed; a new attempt requires representative dialogue-labelled data rather than more synthetic variants.
5. **Sparse-category shrinkage for conditional specificity.** A principled global/category IDF blend is statistically plausible, but E046's holdout result means it needs new data, not more threshold tuning on the same split.

### Closed unless assumptions change

Generic BM25 tuning, broader candidate quotas, generic route fusion, coverage rerankers, simple entropy variants, repeated wildcard schedule sweeps, and catalog-only synthetic reranking are effectively exhausted by the existing evidence.

## 10. Promotion discipline and final decision

Any future robust challenger should:

1. state a falsifiable diagnostic trigger before implementation;
2. change one major mechanism;
3. beat E035B on full development for an interpretable reason;
4. win robust paired validation rather than one aggregate;
5. beat E035B on untouched holdout;
6. avoid material scenario or stress collapse;
7. use no hidden target or simulator-only label at runtime;
8. reproduce from a clean, immutable snapshot.

The fresh run provides no reason to replace either champion:

```text
best.json           → E035B
best_robust.json    → E035B
best_evaluator.json → E022
```

E035B remains the strongest robust model supported by the full experimental record. E022 remains the strongest released-evaluator-specific model. Neither is claimed to be globally optimal; both are the best justified choices under the available evidence and promotion rules.

## 11. Verification record

- Deterministic split verified by tests: 150 development, 50 holdout, disjoint and exhaustive.
- Complete automated suite: **30 passed, 0 failed**.
- Fresh runs completed for both champions on development, holdout, and full public data.
- E035B results exactly match archived aggregates on all three splits.
- E022 holdout and full results exactly match archived aggregates.
- E022 development is slightly better than the older note; discrepancy retained and explained.
- No source champion, selector, evaluator, or original experiment artifact was modified during this final pass. Evaluation was run from a preserved working-copy snapshot.

## 12. Closing project story

The journey was not a straight sequence of score improvements. It was a sequence of increasingly precise falsifications.

The early project learned that memory and exploration mattered. The middle project learned that asking the right answerable question mattered more than clever uncertainty formulas. The retrieval phase learned that catalog representation mattered more than piling on routes. The final phase learned that stopping clarification too early was a real fixable defect, but much of the remaining ranking ceiling was hidden behind genuine observational ambiguity.

That is the lasting result: not merely a `.823394` robust public score or a `.855036` simulator-specialized score, but a well-tested boundary around what the current interface, catalog, and evidence can reliably support.
