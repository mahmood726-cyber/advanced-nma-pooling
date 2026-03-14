# Tutorial Walkthrough

Updated: 2026-03-14

This walkthrough is designed for a reviewer or new user who wants to reproduce the manuscript-grade outputs most directly cited in the F1000 draft.

## Path 1: publication-suite validation

1. Run `nma-pool publication-suite --config configs/example-publication-suite.json --out artifacts/publication-suite.json --summary artifacts/publication-summary.md`.
2. Open `artifacts/publication-summary.md` to review gate pass/fail status, continuous and survival candidate/baseline model pairs, coverage, median absolute bias, log-score comparisons, superiority probabilities, and multiplicity-adjusted p-values.
3. Cross-check any manuscript number against `artifacts/publication-suite.json`, which stores the same outputs in machine-readable form.

## Path 2: paper-bundle reproducibility run

1. Run `nma-pool paper1-bundle --config configs/example-paper1-bundle.json --out-dir artifacts/paper1-bundle`.
2. Open `artifacts/paper1-bundle/paper1-executive-summary.md` to confirm the four executed steps, overall publication-gate status, the frequentist `nrs` bias estimate, the Bayesian backend used, and the prior-sensitivity spans.
3. Open `artifacts/paper1-bundle/manifest.json` to inspect file hashes, copied support documents, and the bundle inventory.

## Path 3: worked mixed-design interpretation

1. Open `configs/example-bias-adjusted.json` to inspect the illustrative A-B and A-C network with two `rct` studies and two `nrs` studies.
2. Note that the randomized studies encode treatment differences of 1.0 (`B` vs `A`) and 2.0 (`C` vs `A`), whereas the non-randomized studies encode larger apparent differences of 1.6 and 2.6.
3. Open `artifacts/paper1-bundle/bias-adjusted-result.json` and `artifacts/paper1-bundle/paper1-executive-summary.md` to confirm that the fitted `nrs` bias term is positive and that the resulting treatment effects for `B` and `C` remain close to the randomized scale.

## Interpretation boundaries

- These walkthroughs reproduce the exact workflow families quantified in the manuscript.
- They are reviewer-facing validation and reproducibility paths, not substitutes for a broader applied case-study paper.
- These walkthroughs point to the public GitHub submission snapshot `f1000-submission-2026-03-14-r2`; DOI-backed archival through Zenodo remains pending.
