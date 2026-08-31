# K006 — Final exposure schedule campaign

Track A was selected on development only. Frozen E058, K3, P006C, and K004
configs were not changed.

| Variant | Policy while asking | HR@10 | MRR | MTTC | Score | Δ vs K3 | Paired 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|
| A1 | K3 control | .986667 | .791111 | 2.560000 | .899467 | — | — |
| A2 | K2 | .986667 | .840397 | 2.840000 | .908653 | +.009186 | [-.000748, .019467] |
| A3 | K1 | .973333 | .929222 | 3.460000 | .916233 | +.016767 | [-.003400, .035267] |
| A4 | turn 1 K1, later K2 | .986667 | .873730 | 2.953333 | .916386 | +.016919 | [.005905, .027938] |
| A5 | turns 1–2 K1, later K3 | .986667 | .875556 | 2.926667 | .917467 | +.018000 | [.006200, .030133] |
| A6 | substantive response K1, otherwise K3 | .986667 | .872778 | 2.840000 | .918367 | +.018900 | [.007933, .030067] |
| A7 | wildcard K1, named K3 | .986667 | .791111 | 2.560000 | .899467 | .000000 | [.000000, .000000] |

A6/K006C is frozen as the single Track A winner before holdout. It has the
largest development score, no additional miss versus K3, zero Top-10 hard
violations, and a paired interval excluding zero. Its mechanism is bounded:
spend one exposure after a substantive answer, while retaining three after an
uninformative response and ten on no-question turns.

No other K006 schedule is eligible for holdout. Full diagnostics are in
`experiments/diagnostics/final_track_a_exposure_matrix.json`.

## One-shot confirmation

A6/K006C confirms on holdout at `.960000` HR@10, `.843333` MRR, `2.980000`
MTTC, and `.893400` technical score. This is +`.013800` over K3 holdout with
the same HR. No schedule was changed after observing holdout.
