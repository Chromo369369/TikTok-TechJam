# Final maximum-score optimization campaign

## Outcome

The campaign found two meaningful winners without changing frozen E058, K3,
P006C, or K004 configurations:

- Score-optimized non-wildcard: **K006C substantive-answer exposure**.
- Released-evaluator wildcard: **P007D wildcard-aware exposure**.

Track C failed its smallest feasibility gate and Track D found no correctness
bug in active runtime paths. Recommendation: **STOP this architecture search**.

## Track A — development matrix

| Variant | Policy while asking | HR@10 | MRR | MTTC | Technical score | Δ vs K3 |
|---|---|---:|---:|---:|---:|---:|
| A1 | K3 | .986667 | .791111 | 2.560000 | .899467 | — |
| A2 | K2 | .986667 | .840397 | 2.840000 | .908653 | +.009186 |
| A3 | K1 | .973333 | .929222 | 3.460000 | .916233 | +.016767 |
| A4 | turn 1 K1; later K2 | .986667 | .873730 | 2.953333 | .916386 | +.016919 |
| A5 | turns 1–2 K1; later K3 | .986667 | .875556 | 2.926667 | .917467 | +.018000 |
| A6 | substantive response K1; otherwise K3 | .986667 | .872778 | 2.840000 | **.918367** | **+.018900** |
| A7 | wildcard K1; named K3 | .986667 | .791111 | 2.560000 | .899467 | .000000 |

A6's paired score interval versus K3 was `[.007933, .030067]`, with 29 MRR
wins, 8 losses, 113 ties, no additional misses, and zero hard violations. It
withheld 100 target-bearing states and promoted 64 on the next turn. It was
frozen before its sole holdout run.

Holdout confirmation: `.960000` HR@10, `.843333` MRR, `2.980000` MTTC,
`.893400` score. This is +`.013800` over K3 with unchanged HR.

## Track B — development factorials

| Variant | HR@10 | MRR | MTTC | Technical score | Δ vs K004 |
|---|---:|---:|---:|---:|---:|
| B1 P006C × K3 | .993333 | .860000 | 2.586667 | .922933 | — |
| B2 P006C × K2 | .986667 | .880944 | 2.760000 | .922417 | -.000517 |
| B3 P006C × K1 | .973333 | .918019 | 3.160000 | .918872 | -.004061 |
| B4 P006C × A6 | .986667 | .889286 | 2.786667 | .924386 | +.001452 |
| B5 wildcard K1; named K3 | .986667 | .922619 | 2.906667 | **.931986** | **+.009052** |

B5's paired interval `[-.005162, .021667]` includes zero, so uncertainty is
retained. It nevertheless cleared the predeclared `.003` effect threshold,
gained `.062619` MRR, had 24 MRR wins versus 10 losses, one additional miss,
and zero hard violations. Trace verification found 353 wildcard turns at K1,
all named questions at K3, and all no-question turns at K10.

Holdout confirmation: `.980000` HR@10, `.920000` MRR, `3.100000` MTTC,
`.924000` score. This is +`.023600` over K004 with unchanged HR.

## Track C — semantic feasibility

A deterministic 155-state development-only probe used naturally occurring
fixed E058/K3 Top-10 pools, at most two hard states per session, no target
injection, and input/evaluation separation. Zero-shot
`cross-encoder/ms-marco-MiniLM-L6-v2` produced:

| Method | MRR | Mean rank | Hard-pair accuracy |
|---|---:|---:|---:|
| Structured baseline | .662458 | 2.645161 | .817204 |
| MiniLM | .471907 | 3.864516 | .681720 |
| Delta | **-.190550** | +1.219355 | **-.135484** |

The MRR delta interval was `[-.257821, -.124352]`; 34 states improved, 84
worsened, and 37 tied. The prior Top-50 E059 probe also failed its safety gate.
The local Qwen ceiling probe was not valid because current CUDA llama.cpp
reported ignored model tensors, so no LLM ranks were accepted. C0 fails and no
simulator data, fine-tuning, C1, or C2 run is permitted.

## Track D — red-team

No correctness bug was demonstrated. Audited areas included target leakage,
candidate membership, repeat timing, wildcard lifecycle, override reset,
missing-value safety, popularity/phrase ordering, deterministic ties, config
dispatch, local paths, experiment dependencies, and metric recomputation.

The campaign's only runtime change is the tested, config-gated
`recommendation_schedule`. Configs without it exactly retain frozen behavior.
No default submission champion was silently replaced.

## Champion table

| Track | Configuration | Development | Holdout | Status |
|---|---|---:|---:|---|
| Robust baseline | E058 | .871721 | .865174 | frozen |
| Score-optimized non-wildcard | K006C | **.918367** | **.893400** | promoted |
| Released-evaluator wildcard | P007D | **.931986** | **.924000** | promoted |
| Experimental model-based | none | — | — | C0 rejected |

No new full-split score was run: full contains the already observed holdout and
would not be an independent confirmation.

## Runtime and memory

Cold 50,000-row catalog build plus deterministic `public_0001` session:

| Config | Turns | Wall time | Peak working set |
|---|---:|---:|---:|
| K006C | 7 | 12.593 s | 938.621 MiB |
| P007D | 2 | 4.589 s | 573.875 MiB |

These are Windows local-process measurements including both evaluator catalog
indexing and the agent's in-memory indexes, not steady-state per-turn latency.
Neither winner adds a model dependency or GPU requirement.

## Exact selected configs

- `configs/best_robust.json` — unchanged E058 submission default.
- `configs/best_score_optimized_final.json` — K006C explicit challenger.
- `configs/best_evaluator_final.json` — P007D explicit evaluator challenger.

## Reproduction

```powershell
python -m unittest tests.test_experiment_workflow tests.test_semantic_headroom -v
python experiments/run_experiment.py --config configs/K006C_substantive_answer_exposure.json --split development
python experiments/analyze_final_exposure_campaign.py
python experiments/run_experiment.py --config configs/K006C_substantive_answer_exposure.json --split holdout
python experiments/run_experiment.py --config configs/P007D_p006c_wildcard_aware_exposure.json --split development
python experiments/analyze_final_wildcard_factorials.py
python experiments/run_experiment.py --config configs/P007D_p006c_wildcard_aware_exposure.json --split holdout
python -m experiments.semantic_headroom.build_c0_top10
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; .venv/Scripts/python.exe -m experiments.semantic_headroom.run_c0_top10
```

## Rejections and risks

- Static K2/K1 improve aggregate development but are dominated by A6's
  recall-preserving schedule; K0 collapses HR and latency.
- A4/A5 are genuine improvements but are simpler-mechanism losers to A6.
- A7 is an exact non-wildcard control; its mechanism only activates under P006C.
- Uniform P006C K2/K1 regress; P006C × A6 is too small and unstable.
- MiniLM semantic reranking fails decisively; model training is abandoned.
- P007D assumes the private evaluator preserves repeated `other` questions,
  semicolon-delimited visible facts, and the same override lifecycle. It must
  remain separate from the robust default.
- Both new winners were optimized on 150 public development sessions. Holdout
  has historical exposure and is confirmation evidence, not a pristine model-
  selection set.

## Final recommendation

**STOP.** Track A converged with a stable confirmed schedule, Track B produced
a large confirmed evaluator-specific gain, Track C failed its feasibility gate,
and Track D found no correctness bug. Continue only for a materially new
mechanism or a valid supported semantic ceiling model—not another threshold or
schedule sweep.
