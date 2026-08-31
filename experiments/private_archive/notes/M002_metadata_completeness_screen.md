# M002 — Metadata Completeness Residual Screen

Read-only. Frozen E060 strict-OOF residual set (46 target-vs-top1 pairs; 22
"both-lower" hard pairs). Catalog-visible completeness features only.

## Results (W = target wins, L = competitor wins, T = ties)

| Feature | ALL (46) | both-lower (22) | price-tied (38) |
|---|---:|---:|---:|
| price_present | 1/7/38 (acc .125) | 1/2/19 (.333) | — |
| description_present | **14/1/31 (acc .933)** | **7/0/15 (1.000)** | **12/1 (acc .923)** |
| store_present | 0/0/46 (constant) | 0/0/22 | 0/0/38 |
| details_present | 0/0/46 (constant) | 0/0/22 | 0/0/38 |
| features_present | 0/0/46 (constant) | 0/0/22 | 0/0/38 |
| categories_present | 0/0/46 (constant) | 0/0/22 | 0/0/38 |
| nonempty_field_count | 13/6/27 (acc .684) | 7/1/14 (.875) | 12/1 (.923) |
| category_depth | 2/4/40 (acc .333) | 2/0/20 (sparse) | 1/3 (.250) |
| feature_count | 15/21/10 (acc .417) | 9/8/5 (.529) | 11/17 (.393) |
| completeness_score (−price) | 14/1/31 (acc .933) | 7/0/15 (1.000) | — |

## Interpretation

1. **description_present is the only completeness signal** — the target is much
   more likely to carry a non-empty description than the E060 top-1 (93% non-tied;
   92% even when price_present is tied; 7/7 on the hardest 22). This is genuinely
   independent of price missingness.

2. **It is not new.** `description_present` is already an E060 feature (index 13,
   coefficient +.135), and `price_present` is already E060's strongest feature
   (+.67). The composite `completeness_score_without_price` reduces exactly to
   `description_present + 4` because store/details/features/categories are present
   for every catalog product (100% constant), so it carries no new information.

3. **Every other completeness dimension is empty.** store/details/features/
   categories are constant (every product has them); category_depth and
   feature_count either favor the competitor or are noise. nonempty_field_count is
   just the price_present (negative) + description_present (positive) mix.

4. **On the strict gate the signal is sparse.** The hardest-22 slice shows only
   7/0 non-tied for description_present (below the ≥16/22 wins or ≥10–12 non-tied
   requirement), so it cannot be trusted as an independent residual signal there.

## Decision

**CLOSE metadata-completeness permanently.** No non-price completeness feature or
predeclared completeness score gives a strong target preference that E060 does not
already capture. The only varying completeness dimensions — price_present and
description_present — are both already inside E060. There is no new Z-information
to add.

Artifacts: `experiments/m002_metadata_completeness_screen.py`,
`experiments/diagnostics/M002_metadata_completeness_residual_screen.json`.
