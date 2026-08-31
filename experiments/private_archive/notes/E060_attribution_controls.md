# E060 — Label-Permutation and Feature-Attribution Controls

These are offline development-only diagnostics over the frozen E060 candidate
manifest. They do not run the evaluator, write a runtime model, select an
ablation, touch holdout, or modify the E060 challenger.

## Label-permutation falsification

For each of 100 controls, every training group retains exactly one positive,
but its location is replaced by a deterministic hash-selected random candidate.
The real target label is retained only when scoring the strict held-out fold.
Candidate groups, target-product-disjoint folds, scaling, regularization, sample
weights, and tie-breaking remain identical to E060.

| Training labels | OOF MRR delta vs archived ordering |
| --- | ---: |
| Real labels | **+.136820** |
| Permuted labels, mean | -.504213 |
| Permuted labels, best of 100 | -.277816 |
| Permuted labels, worst of 100 | -.624326 |

No permutation approaches the real-label result. The finite-sample empirical
tail probability with the standard plus-one correction is `.009901`. The E060
advantage therefore disappears completely when the target association is
destroyed; it is not created by candidate injection, fold assignment, or an
unlabeled implementation artifact.

## Predeclared ablations

All values below are strict OOF candidate-group metrics for the same 149 groups.
They are attribution measurements, not model-selection results.

| Features | Rank 1 | Top 10 | MRR | Δ vs archived | Δ vs full E060 |
| --- | ---: | ---: | ---: | ---: | ---: |
| All E060 | 103 | 145 | .786338 | **+.136820** | — |
| Remove popularity/propensity | 87 | 131 | .673647 | +.024129 | -.112691 |
| Remove dialogue/relevance | 52 | 134 | .541162 | -.108356 | -.245176 |
| Remove exact category | 94 | 141 | .740122 | +.090604 | -.046216 |

Definitions:

- Popularity/propensity comprises global catalog completeness and selection
  priors (`rating_number`, price presence, feature count, average rating,
  description presence) plus conditional category-popularity rank.
- Dialogue/relevance comprises the existing baseline rank, lexical/evidence
  scores, and exact opening-category agreement.
- Exact category comprises exact path match, path information content, and the
  within-path popularity rank.

The components are deliberately not additive. Static propensity by itself
cannot replace relevance: after removing dialogue/relevance, MRR falls below the
archived ordering. But relevance without propensity captures only `+.024129` of
the full `+.136820` improvement. Adding the propensity family to that relevance
base contributes a marginal `+.112691` MRR. Exact category contributes another
large conditional marginal (`+.046216`), while the non-category feature set
still retains `+.090604` over the archive.

## Scientific conclusion

E060 works primarily by improving the observable target prior
`P(target)` among products already made plausible by dialogue relevance. It is
not mainly learning a better generic `P(dialogue | product)` scorer. Relevance
is a necessary gate, but the late-stage gain comes from combining it with
catalog selection propensity and exact category conditioning.

The remaining gap to the `.975867` hidden-target oracle is therefore most
plausibly in a richer target prior: leave-last-out item-selection frequency,
category-conditional item propensity, and product interaction/co-occurrence
history. Generic semantic reranking or another hand-designed exposure schedule
is much less well supported by these controls.

Artifact: `experiments/diagnostics/E060_attribution_controls.json`.
