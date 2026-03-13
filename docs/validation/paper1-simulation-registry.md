# Paper 1 Simulation Registry (Locked)

Version: 1.0  
Lock Date: February 28, 2026

## Purpose

Define all simulation families, parameter grids, and pass/fail metrics used in
Paper 1 before final result interpretation.

## Scenario Family A: Continuous Calibration (A-B-C)

Scenario ID: `CONT-ABC-V1`

1. Network shape: 3 studies, connected A-B-C triangle.
2. True effects vs A: `B=1.0`, `C=2.0`.
3. Sample size per arm: 120.
4. Arm-level SE: 0.25.
5. Observation noise SD: 0.25.
6. Seeds: 1000..1119 (120 networks).

Primary evaluated models:

1. `core_fixed_effects`.
2. `core_random_effects`.
3. Primary gate comparison (pre-specified for confirmatory inference):
   - candidate = `core_fixed_effects`
   - baseline = `core_random_effects`
4. Optional exploratory comparison:
   - `selection_mode=adaptive_split`
   - candidate selected on training split by mean network-level log score
   - inference evaluated on held-out split

## Scenario Family B: Survival Non-PH

Scenario ID: `SURV-NPH-ABC-V1`

1. Pairwise structure: AB, AC, BC replicated networks.
2. Intervals: [0,3], [3,6], [6,12].
3. Baseline hazards: [0.06, 0.05, 0.04].
4. HR(B vs A): [0.70, 0.85, 1.05].
5. HR(C vs A): [0.55, 0.72, 0.95].
6. Sample size per arm: 650.
7. Replicates per pair: 2.
8. Follow-up fraction: 0.85.
9. Seeds: 2000..2099 (100 networks).

Primary evaluated models:

1. `survival_ph_fixed_effects` (baseline).
2. `survival_nph_random_effects` (candidate).

## Scenario Family C: Cross-Design Bias Stress

Scenario ID: `BIAS-MIXED-DESIGN-V1`

1. RCT effects anchored near truth (low bias).
2. NRS effects shifted positively (systematic upward bias).
3. Models evaluated:
   - frequentist bias-adjusted
   - Bayesian bias-adjusted
   - prior-sensitivity sweep

Sensitivity grid:

1. `bias_prior_sd`: [0.3, 0.6, 1.0, 2.0].
2. `treatment_prior_sd`: [2.0, 5.0, 10.0].
3. seeds: [11, 29].

## Primary Endpoints

1. 95% interval coverage.
2. Median absolute bias.
3. RMSE.
4. Mean Gaussian log score.
5. Log-score win rate against baseline.
   - strict wins only (`candidate > baseline`), ties excluded.
6. Paired mean log-score delta (candidate minus baseline).
7. Bootstrap 95% CI for paired mean delta.
8. One-sided paired sign-test p-value.
9. One-sided paired randomization/permutation p-value.
10. One-sided paired signed-rank p-value.
11. Bootstrap superiority probability `P(delta > 0)`.
12. MCSE diagnostics for stochastic inferential metrics.
13. Optional Holm-adjusted family-wise p-values across inferential tests.

## Locked Gates

1. Coverage gate: [0.93, 0.97].
2. Log-score win gate (continuous): >=70%.
3. Bias-improvement gate (survival): >=20%.
4. Log-score win gate (survival): >=80%.
5. Optional inferential predictive gates via config thresholds:
   - `*_logscore_delta_ci95_lb_min`
   - `*_logscore_sign_p_max`
   - `*_logscore_signed_rank_p_max`
   - `*_logscore_permutation_p_max`
   - `*_logscore_permutation_mcse_max`
   - `*_superiority_probability_min`
   - `*_superiority_probability_mcse_max`
   - `familywise_holm_alpha` (Holm-adjusted inferential p-value gates)

## Reproduction Entry Point

Use:

```bash
python pipelines/run_paper1_bundle.py --config configs/example-paper1-bundle.json --out-dir artifacts/paper1-bundle
```
