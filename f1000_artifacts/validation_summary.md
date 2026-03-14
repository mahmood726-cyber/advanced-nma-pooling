# Validation Summary

Updated: 2026-03-14

This file summarizes the manuscript-facing validation evidence used in the current F1000 draft and aligns the support materials to the release-tree artifacts cited in the paper.

## Primary artifact references

- Publication-suite machine-readable results: `artifacts/publication-suite.json`
- Publication-suite human-readable summary: `artifacts/publication-summary.md`
- Paper-bundle manifest: `artifacts/paper1-bundle/manifest.json`
- Paper-bundle executive summary: `artifacts/paper1-bundle/paper1-executive-summary.md`

## What these artifacts support

- The publication-suite files support the reported continuous and survival simulation results, including coverage, median absolute bias, strict win rate, log-score deltas, bootstrap superiority probabilities, multiplicity-adjusted p-values, and gate pass/fail status.
- The paper-bundle files support the reported four-step bundle execution, the frequentist and Bayesian `nrs` bias estimates, the analytic backend note, and the prior-sensitivity spans for treatments `B` and `C`.
- The manuscript is intentionally bounded to these generated artifacts plus the repository's automated test suite and release-manifest checks. It does not claim standalone evaluated case studies for every implemented module.

## Reviewer-facing interpretation notes

- The publication-suite workflows are synthetic validation scenarios designed to test calibration and predictive superiority under locked settings.
- The paper-bundle workflow is a reproducibility demonstration that assembles multiple outputs and supporting documents under one manifest; it is not presented as a full applied case-study analysis.
- These generated artifacts are intended to be exposed in the public GitHub submission snapshot `f1000-submission-2026-03-14-final`; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.
