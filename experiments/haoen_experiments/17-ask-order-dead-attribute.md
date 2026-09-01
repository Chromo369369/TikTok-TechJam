---
experiment: "17"
title: "A dead attribute removed from the clarification fallback"
type: experiment
technical_score: 0.951339
delta: 0.000
decision: "Adopted (defensive)"
summary: "Removed budget from fallback cycle; simulator can never disclose it"
source: "REPORT.md"
---
# A dead attribute removed from the clarification fallback

`ASK_ORDER`, the specific-attribute cycle `_choose_attribute` falls back to if generic `"other"` probing stalls for three turns straight, still listed `"budget"` -- the exact attribute the feature audit already proved the simulator can never disclose on this catalog (`_sim_intent_card` always appends the budget phrase last among a product's candidate list, so it essentially never survives into the slice `customer_reply` can disclose from; confirmed directly, 0/200 public sessions ever reveal it). Asking for it would be a guaranteed wasted turn, by the same logic that already excludes `category`/`brand` from this list. Removed it: `ASK_ORDER = ["material", "color", "use_case", "style", "size", "feature"]`.

Confirmed the score is bit-for-bit unchanged (0.951339) -- expected, and checked directly rather than assumed: 0/200 public sessions ever enter this fallback cycle at all (`"other"` alone always keeps producing new information for the full session on every public sample), so the change has no way to move this specific evaluation. Its value is purely defensive, for exactly the scenario the fallback itself exists to hedge against: a private-set customer simulator whose clarification semantics diverge even slightly from the shipped local one, or any future session where "other" genuinely does stall. In that world, this removes one guaranteed dead turn from the cycle for free.
