# Research Synthesis Methods Readiness

Date: 2026-02-28
Status: executable

## Objective

Provide a reproducible, manuscript-grade validation package for the NMA platform
with explicit pass/fail gates aligned to technical-spec release criteria.

## Publication Suite

Run:

```bash
python pipelines/run_publication_suite.py \
  --config configs/example-publication-suite.json \
  --out artifacts/publication-suite.json \
  --summary artifacts/publication-summary.md
```

Paper-1 full bundle:

```bash
python pipelines/run_paper1_bundle.py \
  --config configs/example-paper1-bundle.json \
  --out-dir artifacts/paper1-bundle
```

Outputs:

- `artifacts/publication-suite.json`: machine-readable metrics + gate results
- `artifacts/publication-summary.md`: manuscript-ready results summary

## Scenarios Included

1. Continuous A-B-C calibration scenario.
   - default pre-specified candidate: `core_fixed_effects`
   - default pre-specified baseline: `core_random_effects`
   - optional exploratory mode: `selection_mode=adaptive_split` with held-out evaluation
2. Survival non-PH scenario with piecewise hazards:
   - candidate: interval-varying NPH random-effects
   - baseline: PH fixed-effects approximation

## Core Endpoints

- median absolute bias
- RMSE
- 95% interval coverage
- average Gaussian log score
- strict candidate win-rate vs baseline in network-level log score (ties excluded)
- paired mean log-score delta (candidate minus baseline)
- bootstrap 95% CI for paired mean delta
- one-sided paired sign-test p-value
- one-sided paired randomization/permutation p-value
- one-sided paired signed-rank p-value
- Monte Carlo standard errors (MCSE) for permutation p-value and superiority probability
- bootstrap superiority probability `P(delta > 0)`
- optional Holm-adjusted family-wise inferential p-values across configured inferential tests

## Gate Definitions

- `continuous_coverage_95_in_target`: candidate coverage in [0.93, 0.97]
- `continuous_logscore_win_rate_vs_baseline`: strict win-rate >= 70% (ties excluded)
- `survival_coverage_95_in_target`: candidate coverage in [0.93, 0.97]
- `survival_bias_improvement_vs_baseline`: bias improvement >= 20%
- `survival_logscore_win_rate_vs_baseline`: strict win-rate >= 80% (ties excluded)
- `git_commit_present` (optional): enforced only when `require_git_commit=true`
- advanced predictive gates (optional, when thresholds are provided):
  - `*_logscore_delta_ci95_lb_vs_baseline`
  - `*_logscore_sign_test_p_vs_baseline`
  - `*_logscore_signed_rank_p_vs_baseline`
  - `*_logscore_permutation_p_vs_baseline`
  - `*_logscore_permutation_mcse_within_max`
  - `*_superiority_probability_vs_baseline`
  - `*_superiority_probability_mcse_within_max`
  - `*_holm_adjusted_p_vs_baseline` (enabled via `familywise_holm_alpha`)

## Reporting Guidance

Use `publication-summary.md` as results text seed and include:

- model assumptions
- estimability handling (`NaN` for non-estimable interval-treatment cells)
- random-effects support (`tau` reported)
- explicit limitation: interval independence approximation
