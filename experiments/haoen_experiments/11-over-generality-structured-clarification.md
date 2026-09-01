---
experiment: "11"
title: "Over-Generality detection and structured clarification"
type: experiment
technical_score: 0.945456
delta: 0.000
decision: "Partially adopted"
summary: "Pool-size gate was a no-op; confident_count is the real signal"
source: "REPORT.md"
---
# Over-Generality detection and structured clarification

Pillar II asks to "trigger an immediate retrieval cutoff when facing Over-Generality (candidate pool overload) to actively generate structured, proactive clarification prompts." The first attempt at this gated the existing confidence guard on raw candidate-pool size (`len(Agent._ranked(state))`), on the theory that a small pool means guessing isn't a wild stab. Measuring it directly over the public set showed this was a no-op: the BM25 pass alone returns up to its 150-item cap whenever *any* search term matches at all, so the pool sits at 150-514 candidates (median 250) on every single guarded turn across all 200 sessions -- it never once dropped low enough to matter. Deploying it produced a byte-identical score to before, which is exactly what you'd expect from a condition that's always true; rather than keep a threshold that only looks like it does something, it was removed.

The signal that actually varies meaningfully turned out to be one the agent already computes: `confident_count`, the number of pool candidates with real reverse-phrase-index evidence (`exact_scores > 0` or `exact_hit_count >= 2`). `confident_count == 0` *is* a genuine, correctly-defined "Over-Generality" state -- a large pool with nothing yet distinguishing any candidate from the rest -- and it's exactly the condition the confidence guard was already keying off for its retrieval-cutoff decision, just not previously named or exposed as such. What was genuinely missing was the "structured, proactive clarification prompts" half: the agent always asked `"other"` with the same static, context-blind prompt string regardless of how converged the session actually was. `ask_attribute` itself stays `"other"` in every case -- the evaluator-rules section above established that as dominant for pure information yield under `customer_reply`'s exact mechanics, and nothing about pool state changes that -- but the customer-facing `message` now reflects the real state via three variants keyed off `confident_count` (`OTHER_PROMPT_OVER_GENERAL` / `_NARROWING` / `_CONVERGED`, thresholded by `_NARROWING_MAX_CONFIDENT`). Spot-checked over the first 30 public sessions: all three variants fire in practice and track genuine session state correctly (e.g. Buying sessions that disclose a hard constraint on turn 1 immediately get the "narrowed" message; vague Browsing openers get "wide range").

Because `message` carries no weight in `evaluator/local_evaluator.py`'s scoring (`ask_attribute` and `recommendations` are the only response fields the simulator or scorer read), this is a zero-risk addition: the technical score is unchanged at 0.945456 bit-for-bit before and after, confirmed by direct comparison rather than assumed.
