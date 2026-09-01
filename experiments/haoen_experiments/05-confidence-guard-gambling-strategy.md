---
experiment: "05"
title: "The rank-quality confidence guard"
type: experiment
technical_score: 0.929
delta: +0.051
decision: "Adopted"
summary: "THE OPTIMISED GAMBLING STRATEGY: withhold a weak-rank guess, spend a turn for a better rank"
source: "REPORT.md"
---
# The rank-quality confidence guard

A session ends the instant the target first appears in the returned top-10, at whatever rank it was given. Empirically, this created a bad trade on early turns: the very first disclosed constraint is disproportionately likely to be one of those common material/colour words, so a target *could* already be recoverable via BM25 + weak priors (category, rating) on turn 1 — but only at a mediocre rank, since nothing yet distinguishes it from the thousands of other products sharing that word. One more `"other"` turn almost always reveals a second, highly specific phrase that would resolve the same candidate to rank 1 — but only if the session is still running to receive it.

So while the clarification channel is still open (`not state.other_exhausted`) and within a bounded number of early turns (`_CONFIDENCE_GUARD_LAST_TURN = 6`, tuned on the public set — flat across 5–7, meaningfully worse both uncapped and at 1–2 turns short), the agent only shows candidates it has *specific* reverse-phrase-index evidence for; if there are none yet, it submits nothing that turn and waits for sharper evidence. The turn cutoff is a deliberate safety net: it guarantees several full-recall turns before the 10-turn budget runs out, bounding the downside (a session that never gains confident evidence) to a fixed Efficiency cost rather than a Hit Rate@10 loss. Removing the cutoff entirely was tested and does cause exactly that failure mode (see measured effect below).
