---
experiment: "02"
title: "The evaluator's rules are public — read them as a specification, not just a test harness"
type: context
technical_score: n/a
delta: n/a
decision: "Reference"
summary: "Four exploitable facts in the public evaluator source"
source: "REPORT.md"
---
# The evaluator's rules are public — read them as a specification, not just a test harness

`evaluator/local_evaluator.py` is not a black box; it is the exact deterministic policy that plays the simulated customer, and the organizer states final judging reuses "the deterministic local evaluator" against a private 800-session split. Three details in that file change the optimal strategy substantially:

**`ask_attribute="other"` is a universal probe.** In `customer_reply`, a specific attribute (e.g. `"material"`) only reveals undisclosed constraints whose `classify_constraint(...)` matches that label. `"other"` matches *any* undisclosed constraint regardless of type. So `"other"` weakly dominates every specific attribute for pure information yield — it can only reveal at least as much on any given turn. `"category"` and `"brand"` are worse than useless: `classify_constraint` never emits either label, so asking for them can never surface new information under this exact policy. The agent should default to `"other"`, never ask `category`/`brand`, and only fall back to cycling specific attributes if repeated asks stop producing information (a hedge in case the official private-set customer simulator diverges even slightly from the shipped code).

**Recommending and asking are free to combine, every turn.** The API lets one response carry `message`, `ask_attribute`, and up to 10 `recommendations` simultaneously, and there is no penalty in the scoring formula for a wrong guess. So there is never a reason to withhold a best-effort top-10 while waiting for more information — every turn should submit the current best guess *and* ask the most informative available question. Any agent that "gathers info first, then guesses" is leaving Hit Rate@10 and MTTC on the table for free.

**A fixed, already-missed list will miss forever — so stop resubmitting it.** A session only keeps running after a miss. Once the agent has extracted all available conversational information (no more constraints to learn) and its best top-10 still didn't hit, resubmitting the identical list on every remaining turn cannot possibly help — the composite score for those items hasn't changed. Since the remaining turns are otherwise wasted, the agent should instead treat them as additional "shots on goal": keep the two or three highest-confidence items fixed (protects MRR in case they were actually right but ranked just outside top-3 last time) and rotate the rest of the list through the next-best unseen candidates each turn. This can only ever convert a would-be miss (MRR 0, MTTC contribution 11) into a later hit (MRR > 0, MTTC contribution < 11); it can never take away an already-achievable hit, because any session where the original top-10 was correct already ended on that turn.

**Intent Override hits don't count until the override lands.** The evaluator explicitly discounts hits before `override_applied` is set for Intent Override sessions — so a correct guess on turns 1–2 of such a session is wasted regardless. There is no reliable way to distinguish an Intent Override session from a Browsing one before the override message arrives (`initial_message` uses an identical vague template for both), so the correct response is not to special-case scenario type at all: react generically to whatever text arrives, including a lightweight regex for override language ("ignore", "actually", "what I need is") that heavily re-weights retrieval toward the newly stated value the moment it's detected. Submitting best-effort guesses every turn anyway costs nothing even when they can't score, and it keeps the agent uniform across the four undisclosed scenario types.
