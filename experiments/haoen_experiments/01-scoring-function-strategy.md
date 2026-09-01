---
experiment: "01"
title: "The scoring function determines the strategy"
type: context
technical_score: n/a
delta: n/a
decision: "Reference"
summary: "Why all three metric terms reward the same behaviour"
source: "REPORT.md"
---
# The scoring function determines the strategy

```
TechnicalScore = 0.50 × HitRate@10 + 0.30 × MRR + 0.20 × Efficiency
Efficiency = clip((11 − MTTC) / 10, 0, 1)
```

Every one of these terms rewards the same underlying behavior at different resolutions. Hit Rate@10 only cares whether the target ever lands in a top-10 list across the ten turns, so it is maximized by casting as wide a net as possible over the session. MRR additionally rewards ranking the target near the top of the list the turn it is found, so precision matters once recall is likely. MTTC rewards finding it in as few turns as possible, which is a function of how quickly the agent can narrow the candidate set — i.e., how good its clarification questions are. Because all three terms are computed per session from the same underlying "which turn, which rank did the hit happen" event, there is no real tension between them: an agent that retrieves well with partial information and asks maximally informative questions improves all three simultaneously. Reported token usage is a disclosure item, not part of the score, but a rule-based agent with no LLM calls reports exactly zero, which is the best possible value and also removes latency and API cost risk entirely.
