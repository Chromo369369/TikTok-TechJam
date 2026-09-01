---
experiment: "10"
title: "Addressing `problem.md`'s other pillars"
type: analysis
technical_score: n/a
delta: n/a
decision: "Documented"
summary: "Honest non-coverage of dual-track routing and long-term profiles"
source: "REPORT.md"
---
# Addressing `problem.md`'s other pillars

Beyond the vector-similarity gap closed above, `problem.md` names three other things worth flagging honestly rather than silently claiming coverage. **Dual-track Buying/Browsing routing** (Pillar I) is deliberately *not* implemented as a hard pipeline switch: the evaluator's own `initial_message` uses an identical vague template for Browsing and Intent Override sessions, so a classifier can't reliably tell them apart before enough is disclosed, and a premature hard route risks steering into the wrong retrieval strategy -- the agent instead reacts generically to whatever's disclosed each turn, which the measured results show already reaches HR@10=1.0 and per-scenario MRR 0.87-0.94 without scenario-specific branching. **Personalized Context Distillation / long-term profile evolution** (Pillar III) isn't meaningfully actionable within the given API: `user_profile` is supplied once at `reset()` and each session is an isolated single-user interaction with no cross-session persistence mechanism in the contract, so there is no "long-term" state to distill beyond what the agent already does with the profile's `preference_tags` within a session. **Proactive, pool-size-triggered clarification** (Pillar II's "Over-Generality" cutoff) is addressed below.
