# Publication-Readiness Results

- `created_at_utc`: 2026-02-28T21:39:28.376938+00:00
- `overall_pass`: True
- `git_commit`: unknown

## Gates
- `continuous_coverage_95_in_target`: PASS
- `continuous_logscore_delta_ci95_lb_vs_baseline`: PASS
- `continuous_logscore_permutation_mcse_within_max`: PASS
- `continuous_logscore_permutation_p_holm_adjusted_p_vs_baseline`: PASS
- `continuous_logscore_permutation_p_vs_baseline`: PASS
- `continuous_logscore_sign_test_p_holm_adjusted_p_vs_baseline`: PASS
- `continuous_logscore_sign_test_p_vs_baseline`: PASS
- `continuous_logscore_signed_rank_p_holm_adjusted_p_vs_baseline`: PASS
- `continuous_logscore_signed_rank_p_vs_baseline`: PASS
- `continuous_logscore_win_rate_vs_baseline`: PASS
- `continuous_superiority_probability_mcse_within_max`: PASS
- `continuous_superiority_probability_vs_baseline`: PASS
- `survival_bias_improvement_vs_baseline`: PASS
- `survival_coverage_95_in_target`: PASS
- `survival_logscore_delta_ci95_lb_vs_baseline`: PASS
- `survival_logscore_permutation_mcse_within_max`: PASS
- `survival_logscore_permutation_p_holm_adjusted_p_vs_baseline`: PASS
- `survival_logscore_permutation_p_vs_baseline`: PASS
- `survival_logscore_sign_test_p_holm_adjusted_p_vs_baseline`: PASS
- `survival_logscore_sign_test_p_vs_baseline`: PASS
- `survival_logscore_signed_rank_p_holm_adjusted_p_vs_baseline`: PASS
- `survival_logscore_signed_rank_p_vs_baseline`: PASS
- `survival_logscore_win_rate_vs_baseline`: PASS
- `survival_superiority_probability_mcse_within_max`: PASS
- `survival_superiority_probability_vs_baseline`: PASS

## Continuous Scenario
- Candidate: `core_fixed_effects`
- Baseline: `core_random_effects`
- Candidate coverage: 0.9417
- Candidate median abs bias: 0.1967
- Candidate logscore win-rate vs baseline: 0.7805
- Mean logscore delta (candidate-baseline): 0.0450
- 95% CI for mean delta: [0.0039, 0.0828]
- One-sided sign-test p-value: 0.0002
- One-sided permutation p-value: 0.0123
- One-sided signed-rank p-value: 0.0025
- Permutation method: monte_carlo
- Permutation draws used: 20000.0000
- Permutation p-value MCSE: 0.0008
- Signed-rank method: monte_carlo
- Signed-rank draws used: 20000.0000
- Signed-rank p-value MCSE: 0.0004
- Superiority probability (bootstrap): 0.9856
- Superiority probability MCSE: 0.0024

## Survival Non-PH Scenario
- Candidate: `survival_nph_random_effects`
- Baseline: `survival_ph_fixed_effects`
- Candidate coverage: 0.9700
- Candidate median abs bias: 0.0569
- Baseline median abs bias: 0.1882
- Candidate bias improvement: 0.6973
- Candidate logscore win-rate vs baseline: 1.0000
- Mean logscore delta (candidate-baseline): 7.8906
- 95% CI for mean delta: [7.7282, 8.0687]
- One-sided sign-test p-value: 0.0000
- One-sided permutation p-value: 0.0000
- One-sided signed-rank p-value: 0.0000
- Permutation method: monte_carlo
- Permutation draws used: 20000.0000
- Permutation p-value MCSE: 0.0000
- Signed-rank method: monte_carlo
- Signed-rank draws used: 20000.0000
- Signed-rank p-value MCSE: 0.0000
- Superiority probability (bootstrap): 1.0000
- Superiority probability MCSE: 0.0000

## Multiplicity-Adjusted Inferential P-Values
- Method: `holm`
- `continuous_logscore_permutation_p`: 0.0123
- `continuous_logscore_sign_test_p`: 0.0006
- `continuous_logscore_signed_rank_p`: 0.0050
- `survival_logscore_permutation_p`: 0.0002
- `survival_logscore_sign_test_p`: 0.0000
- `survival_logscore_signed_rank_p`: 0.0002
