---
experiment: "03"
title: "Reference architecture (`starter/agent.py`)"
type: architecture
technical_score: 0.813
delta: +0.71 vs baseline
decision: "Adopted"
summary: "Cumulative constraint state replacing per-turn amnesia"
source: "REPORT.md"
---
# Reference architecture (`starter/agent.py`)

The reference implementation keeps the baseline's zero-dependency approach — pure Python standard library, an in-memory SQLite FTS5 index over the catalog, no network calls — and adds two structural layers on top of it: a cumulative constraint state (fixing the baseline's state amnesia), and a **reverse phrase index** that white-box-models the customer simulator itself.

The shipped baseline's core bug is that it rebuilds its search query from `user_message` alone on every turn, so anything disclosed on turn 1 is invisible by turn 3. The reference agent keeps a per-session `_ConstraintState`: a cumulative, never-forgotten set of material/color/style/use-case/size/budget/feature terms parsed from every message the customer has ever sent, plus the safe aggregate `user_profile` (`preference_tags`, `rating_style`, etc.). Every turn re-ranks against the full accumulated state, not just the latest sentence.
