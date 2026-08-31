# Final Representation/Lineage Campaign

All work was development-only against frozen E060. No holdout, champion config,
or frozen E060 artifact was modified.

| Branch | Result | Decision |
| --- | ---: | --- |
| O001/O002 override intent scoping | O1/O3 sharply reduced retrieval; O2 also regressed; no positive rank evidence | Reject before OOF |
| E064 unfused relevance/popularity | Score `.959867`, delta `+.002467`, CI crosses zero | Reject |
| E065 broad category metadata | Score `.955800`, delta `-.001600` | Reject |
| W001 P007D exposure restoration | Score `.955933`, delta `-.001467` | Reject |
| Q001 recency-safe query terms | 15/442 states truncate a newer term; no retrieval gain and near-zero final-rank change | Reject |
| S001 named-answer canonicalization | 3/57 improved offline margins; none worsened, but below material gate; no missed evaluator no-preference forms | Reject |
| E066 grouped conditional softmax | Score `.960533`, delta `+.003133`, but CI lower `-.002400` | Reject |

W001’s hardened replay found identical wildcard parsing, repeated-`other`,
exhaustion, override-reset, semantic state, and question routing. Its only
control difference was P007D's `k=3` versus P008A/E060's `k=2` on 29
feature/material states; the authorized restoration failed.

**Final decision: stop algorithmic research and preserve frozen E060 as the
final qualified challenger.** No combination was authorized because no two
independent branches passed their strict gates.
