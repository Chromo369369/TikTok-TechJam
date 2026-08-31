# Final code/policy red-team

The audit covered runtime target leakage, candidate membership, repeat timing,
exposure accounting, wildcard lifecycle, safety ordering, deterministic ties,
phrase IDF, popularity RRF, default submission configuration, local paths,
experiment dependencies, and metric recomputation.

No correctness bug was demonstrated in the active E058/K006C/P007D paths.
Accordingly, no speculative runtime fix was made. The only runtime addition in
this campaign is the explicit, config-gated `recommendation_schedule`; absence
of that key retains frozen champion behavior and focused tests cover all four
schedule modes.

P007D dispatch was audited from its development trace: 353 `other` questions
used K1; all named questions used K3; 11 no-question turns used K10. All final
development and holdout runs reported zero Top-10 confirmed hard violations.
No runtime source imports public targets, ground truth, experiment artifacts,
or absolute local paths. The no-argument submission path remains pinned to
`configs/best_robust.json`; score-optimized and evaluator-specific winners stay
separate explicit configs.
