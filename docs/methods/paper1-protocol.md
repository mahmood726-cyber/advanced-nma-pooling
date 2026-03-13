# Paper 1 Protocol (RSM Submission Track)

Version: 1.0  
Lock Date: February 28, 2026  
Target Journal: *Research Synthesis Methods*

## 1. Title

Bias-adjusted and non-proportional-hazards-capable network meta-analysis:
a reproducible calibration and benchmark study.

## 2. Primary Objective

Evaluate whether the integrated NMA engine improves calibration and decision
reliability over strong baselines in:

1. Mixed-design (RCT + NRS) aggregate-data networks.
2. Survival networks with non-proportional hazards (non-PH).

## 3. Estimands

1. Relative treatment effects vs reference treatment for continuous outcomes.
2. Interval-specific log-hazard ratios for piecewise survival outcomes.
3. Design-stratum bias offsets for non-reference design strata (for example,
   `nrs` vs `rct`).

## 4. Models Under Evaluation

1. Core AD fixed/random NMA.
   - Continuous primary comparison is pre-specified:
     candidate=`core_fixed_effects`, baseline=`core_random_effects`.
   - Optional exploratory mode uses split-sample adaptive selection with held-out inference.
2. Bias-adjusted AD NMA (frequentist).
3. Bayesian bias-adjusted AD NMA (analytic backend; Stan fallback path).
4. Survival NPH model (piecewise exponential, interval-varying effects).
5. PH baseline approximation for survival comparisons.

## 5. Prespecified Simulation Program

Simulation scenarios are locked in:

- `docs/validation/paper1-simulation-registry.md`

Primary scenario families:

1. Continuous A-B-C calibration.
2. Survival non-PH stress testing.
3. Cross-design bias stress conditions (RCT low bias, NRS positive bias shift).

## 6. Prespecified Endpoints

1. 95% interval coverage.
2. Median absolute bias.
3. RMSE.
4. Mean Gaussian log score.
5. Log-score win rate vs baseline.
   - defined as strict win rate with ties excluded from denominator.
6. Paired mean log-score delta (candidate minus baseline).
7. Bootstrap 95% CI for paired mean log-score delta.
8. One-sided paired sign-test p-value.
9. One-sided paired randomization/permutation p-value.
10. One-sided paired signed-rank p-value.
11. Bootstrap superiority probability `P(delta > 0)`.
12. MCSE diagnostics for stochastic inferential endpoints.
13. Optional Holm-adjusted family-wise p-values across inferential tests.

## 7. Prespecified Gates

1. Coverage gate: 95% interval coverage in [0.93, 0.97] for candidate models.
2. Continuous log-score win gate: >=70% win rate vs random-effects baseline.
3. Survival bias-improvement gate: >=20% median absolute bias reduction vs PH baseline.
4. Survival log-score win gate: >=80% win rate vs PH baseline.
5. Reproducibility gate (optional): git commit must be present when enforced.
6. Advanced predictive inference gates (optional):
   - CI lower bound of paired log-score delta above configured threshold.
   - paired sign-test p-value below configured alpha.
   - paired signed-rank p-value below configured alpha.
   - paired randomization/permutation p-value below configured alpha.
   - superiority probability above configured threshold.
   - MCSE below configured maxima for stochastic endpoints.
   - Holm-adjusted family-wise p-values below configured alpha.

## 8. Sensitivity Plan

Bayesian bias-prior and treatment-prior sensitivity grid:

- `bias_prior_sd`: [0.3, 0.6, 1.0, 2.0]
- `treatment_prior_sd`: [2.0, 5.0, 10.0]
- multiple random seeds

Sensitivity outputs must report effect-range spans and include any instability flags.

## 9. Reproducibility Rules

1. One-command bundle run from locked config.
2. Deterministic seeds in all stochastic runs.
3. Hash-tracked outputs via run manifest.
4. Manuscript figures/tables built from generated artifacts only.

## 10. Deliverables for Submission

1. Primary manuscript (`docs/methods/paper1-manuscript-outline.md`).
2. Supplement (full model equations, priors, and diagnostics).
3. Artifact bundle with manifest/checksums.
4. Reproduction command list and environment details.
