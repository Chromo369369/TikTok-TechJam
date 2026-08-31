# Final Remaining-Sequence Diagnostics — E067 / E064C / price_present

Development-only, read-only. No holdout, no champion change. E060 frozen
(.957400). Reproductions verified byte-identical (full E060 rank-level OOF
MRR .786338, rank1 103).

## E067 — state-conditioned propensity (CLOSE)

Read-only diagnostic: E060-vs-P008A reciprocal-rank delta at the first eligible
union state, stratified by state.

| Stratum | n | mean delta | mean rank P008A→E060 |
|---|---:|---:|---:|
| turn 1 | 62 | **+.2336** | 10.6 → 3.2 |
| turn 2 | 54 | +.0900 | 2.6 → 1.5 |
| turn 3 | 22 | +.0511 | 4.5 → 1.9 |
| turn 4+ | 11 | **−.0075** | 4.5 → 2.0 |
| constraints 1 / 2 / 3+ | 46/38/65 | +.124 / **+.222** / +.097 | — |
| intent_override | 22 | **−.0171** | 4.0 → 2.0 |
| buying / browsing / boundary | 62/61/4 | +.179 / +.158 / +.011 | — |

E060's propensity correction is strongly positive early (turn 1) and mildly
negative at late-union and override states. The negative tail is **small**:
fixing it is worth ≈ +.001 Technical Score (22 override sessions × ~.017, 11
turn-4+ sessions × ~.008, times 0.3 MRR / 150). **Below the +.003 gate → CLOSE
E067.** No E067B.

## E064C — fused-RRF residual descriptor (borderline, below gate)

Read-only diagnostic: add `signed_rank_disagreement = log1p(relevance_rank) −
log1p(popularity_rank)` (computed within the frozen Top-200 group) to E060's
linear model, refit with the identical five-fold target-product-disjoint setup.

| Model | OOF MRR | rank1 |
|---|---:|---:|
| E060 (17 feats) | .786338 | 103 |
| E060 + signed_rank_disagreement | **.793045** | **105** |

There **is** incremental signal (+.006707 MRR, +2 rank1), but it is modest. Using
the measured E060 rank→score transfer ratio (~.148), the expected end-to-end gain
is ≈ **+.002**, below the +.003 gate. E064C is therefore **not** worth a full
strict-OOF end-to-end run; close the E064 family.

## price_present — robustness attribution (KEEP)

| Model | OOF MRR | rank1 |
|---|---:|---:|
| E060 (17 feats) | .786338 | 103 |
| E060 − price_present | **.759500** | **100** |

Removing `price_present` costs −.026838 MRR and −3 rank1. Its large, fold-stable
coefficient (+.67) reflects a genuine catalog-completeness signal, not noise.
**Keep it.** No price-value engineering follows from this.

## Conclusion — STOP ALGORITHMIC DEVELOPMENT

- E067 (state-conditioned propensity): small, below gate → closed.
- E064C (fused-RRF residual descriptor): real but below-gate signal → closed.
- price_present: meaningful, retained.

Every remaining predeclared avenue has now been measured and either closed or
retained with evidence. Per the stated stopping rule, algorithmic development
stops here.

**Freeze E060 (strict OOF .957400) as the single confirmation candidate.** The
only remaining low-risk action is one explicitly authorized, predeclared
confirmation run, with the deployment requirements in Section 20 satisfied
(explicit E060 config supply; fail-loud model loading; hash identity check).

## Artifacts

- `experiments/e067_state_diagnostic.py`
- `experiments/e064c_price_attribution.py`
- `experiments/e062vx_analysis.py`, `experiments/e062g_disagreement_gate.py`
- `experiments/notes/E062_final_gates.md`, `experiments/notes/E062_stage1_diagnostics.md`
