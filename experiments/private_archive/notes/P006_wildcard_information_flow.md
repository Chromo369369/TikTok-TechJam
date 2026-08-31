# P006 — Released-wildcard information-flow audit

## Scope and frozen references

This is an evaluator-specific all-in pass under one explicit assumption: private
evaluation reproduces the released simulator's repeated `other` disclosures,
fixed response wrapper, semicolon formatting, and exhaustion behavior. E058 is
untouched as the robust champion. P002C remains the frozen wildcard reference;
P006C is exposed separately in `configs/best_evaluator_all_in.json`.

The audit did not revisit wildcard call-count sweeps, E058 factorials, RRF
parameters, dense ranking, candidate-pool width, conditional IDF, or
ranking-derived question selection.

## Information-flow audit

The P002C development trace contains 128 genuine wildcard disclosure responses
and 257 semicolon-delimited observable clauses. Of those responses, 124 contain
multiple clauses.

| Stage | Represented | Finding |
|---|---:|---|
| Visible wildcard clauses | 257 / 257 | Audit denominator |
| Captured by answer parser | 257 / 257 | No text dropped |
| Present in state | 257 / 257 | No state loss |
| Every clause term inside the 40-term BM25 query | 256 / 257 | Sole truncation already had target rank 1 |
| Available to overlap reranking | 257 / 257 | Full state value is consumed |

Thus the omitted-evidence fraction is effectively zero. There is no lead for
broader extraction or retrieval expansion.

The audit did find two decision/pipeline mismatches.

## P006 — Atomic wildcard facts

### Mechanism

P002C stores a response such as `black leather; slim enough for a front pocket`
as one strength-0.7 constraint. Token-overlap reranking therefore averages over
both clauses and caps the total reward at one constraint. P006 strips only the
released simulator's fixed wrapper and represents each visible semicolon clause
as its own strength-0.7 `other` constraint. Raw history, fingerprint phrase
splitting, candidate membership, questions, popularity RRF, and safety remain
unchanged.

### Why prior experiments did not falsify it

E052 changed the evidence architecture. E058 changed exact-phrase IDF. Neither
changed the granularity at which the existing P002C overlap scorer receives a
multi-fact wildcard answer. Preserving text can hide this scoring dilution in a
conventional parser-recall audit.

### Development gate and impact

Abandon if technical score improves by less than `.002`, HR falls, or hard
violations appear. The locked development replay passed:

| Variant | HR@10 | MRR | MTTC | Score |
|---|---:|---:|---:|---:|
| P002C | .993333 | .724873 | 2.153333 | .891062 |
| P006 atomic facts | .993333 | .748233 | 2.146667 | .898203 |

Across 150 paired sessions, reciprocal rank improved in 14, was unchanged in
131, and worsened in 5. The mean reciprocal-rank increase was `.023360`.

### Risk

High outside the released evaluator: the mechanism assumes both the fixed
wrapper and semicolon clause format. It is not suitable for E058 or ordinary
free-form conversation without a real clause parser.

## P006B — Wildcard lifecycle on intent override

### Mechanism

In all 22 development intent-override sessions, an override can arrive while an
`other` question is pending. P002C snapshots that pending state before detecting
the override, treats the override as an empty wildcard answer, sets
`other_exhausted`, and carries exhaustion into the new intent. Its trace also
incorrectly labels the extracted override constraint as
`wildcard_constraints_received`.

P006B makes an override replace—not answer—the pending question, clears prior
wildcard values/exhaustion as part of the existing intent reset, and reopens the
same released wildcard channel for the new intent. This is a lifecycle fix, not
a tuned number or timing of `other` calls.

### Why prior experiments did not falsify it

Earlier one/two/terminal wildcard experiments changed schedules globally.
Question-policy propagation experiments changed question selection. Neither
tested the state transition where an externally scheduled intent override
supersedes a pending wildcard question.

### Development gate and impact

Abandon if intent-override MRR or MTTC fails to improve with no global HR loss.
The independent gate passed:

| Variant | HR@10 | MRR | MTTC | Score |
|---|---:|---:|---:|---:|
| P002C | .993333 | .724873 | 2.153333 | .891062 |
| P006B override reset | .993333 | .727373 | 2.140000 | .892078 |

Intent-override MRR improved from `.812680` to `.829726`, and scenario MTTC
from `3.727273` to `3.636364`; every other development scenario was identical.

### Risk

The reset itself is decision-theoretically correct, but its gain depends on
private evaluation scheduling intent overrides while `other` is pending and on
allowing wildcard discovery again after an intent reset.

## P006C — Validated factorial

Atomic fact scoring acts after a disclosure; override reset governs whether a
new-intent disclosure can occur. The mechanisms affect different stages and
their independent development gains justified a two-way factorial.

| Variant | HR@10 | MRR | MTTC | Score | Hard violations |
|---|---:|---:|---:|---:|---:|
| P002C development | .993333 | .724873 | 2.153333 | .891062 | 0 |
| P006 development | .993333 | .748233 | 2.146667 | .898203 | 0 |
| P006B development | .993333 | .727373 | 2.140000 | .892078 | 0 |
| P006C development | .993333 | .750733 | 2.133333 | .899220 | 0 |
| P002C holdout | .980000 | .686405 | 2.360000 | .868722 | 0 |
| P006C holdout confirmation | .980000 | .686484 | 2.340000 | .869145 | 0 |

The holdout rule was frozen before confirmation and was not altered afterward.
Confirmation is positive but small (`+.000423` score), so the larger development
gain should not be extrapolated to private data.

## Decision

KEEP P006C only as `best_evaluator_all_in.json`. Do not replace E058, and do not
silently replace the frozen P002C `best_evaluator.json`. No third wildcard
hypothesis cleared the audit: text propagation is complete, BM25 truncation is
negligible, and the remaining single-token facts already affect both BM25 and
overlap ranking. Stop this branch unless released wildcard semantics and format
are explicitly guaranteed.
