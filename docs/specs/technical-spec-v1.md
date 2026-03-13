# Technical Spec v1: Advanced Pooling Model for NMA

Date: 2026-02-28
Owner: Advanced NMA Core Team
Status: Draft for execution

## 1. Purpose

Build a production-grade evidence synthesis platform centered on a unified
Bayesian pooling framework for network meta-analysis that supports:

- aggregate data (AD) and individual patient data (IPD)
- randomized and non-randomized evidence (RCT + NRS)
- dose-response and component-based interventions
- binary, continuous, count, and survival outcomes
- robust inference under outliers, bias, and inconsistency
- living updates with full reproducibility and auditability

## 2. Product Goals

- Scientific: maximize calibration and decision reliability, not just ranking.
- Methodological: combine frontier methods in one coherent inferential graph.
- Operational: end-to-end reproducible runs from ingestion to decision report.
- External: benchmark above current open-source toolchains on stress tests.

## 3. Scope and Non-Goals

In scope:

- Bayesian hierarchical NMA core and advanced extensions
- unified data model and provenance
- simulation and benchmark harness
- CI-validated reporting outputs
- living NMA incremental update pipeline

Out of scope (v1):

- full UI product for non-technical users
- automatic PDF extraction from arbitrary sources without human QA
- causal identification for all observational designs without assumptions

## 4. Quantitative Success Criteria

Release gates require all criteria:

- posterior interval coverage within 93% to 97% on calibrated simulations for
  nominal 95% intervals
- median absolute bias at least 20% lower than baseline models on benchmark
  simulation suites
- equal or better expected log predictive density than baseline in at least
  80% of benchmark networks
- zero unreproducible runs in CI smoke suite
- full run reproducibility from manifest and seed within numeric tolerance

## 5. System Architecture

Layers:

1. Data layer
2. Model layer
3. Inference layer
4. Validation layer
5. Reporting layer
6. Orchestration and governance layer

Flow:

`ingest -> harmonize -> quality gates -> model registry -> fit -> diagnose -> compare -> report -> publish artifacts`

## 6. Statistical Model Stack

### 6.1 Notation

- studies: `i = 1..I`
- arms within study: `k = 1..K_i`
- treatments: `t in {1..T}`
- outcomes: `o in {1..O}`
- patient in IPD study: `p = 1..n_i`

Reference treatment is `t = 1`.

### 6.2 Core Random-Effects NMA (AD)

For study-arm contrasts:

- likelihood: `y_iab ~ Normal(d_iab, s_iab^2)`
- linear predictor: `d_iab = Delta_ab + u_iab`
- random effects: `u_iab ~ Normal(0, tau_ab^2)` with consistency-constrained
  covariance for multi-arm studies

Consistency:

- `Delta_ab = Delta_a1 - Delta_b1`

Heterogeneity options:

- common `tau`
- class-specific `tau_c`
- contrast-specific shrinkage prior for sparse networks

### 6.3 Outcome Family Extensions

Binary:

- `r_ik ~ Binomial(n_ik, p_ik)`
- `logit(p_ik) = mu_i + theta_i,t(ik)`

Continuous:

- `ybar_ik ~ Normal(mu_i + theta_i,t(ik), sigma_ik^2 / n_ik)`

Count:

- `e_ik ~ Poisson(lambda_ik * person_time_ik)`
- `log(lambda_ik) = mu_i + theta_i,t(ik)`

Survival (piecewise exponential baseline):

- interval hazard: `h_ikm = exp(mu_im + theta_i,t(ik),m)`
- supports non-proportional hazards via time-varying treatment effects

### 6.4 IPD + AD Integration (ML-NMR Core)

IPD:

- `g(E[y_ip]) = alpha_i + f_x(x_ip) + f_tx(t_ip, x_ip)`

AD bridge:

- expected arm response integrates IPD-level model over arm covariate
  distribution:
- `E[y_ik] = Integral g^{-1}(alpha_i + f_x(x) + f_tx(t_ik, x)) dF_ik(x)`

Implementation options for `F_ik(x)`:

- empirical IPD distribution
- parametric summary reconstruction from AD covariates
- quadrature or Monte Carlo integration with uncertainty propagation

### 6.5 Cross-Design Synthesis (RCT + NRS)

Bias-adjusted link:

- `delta_obs_iab = delta_true_iab + b_iab`
- `b_iab ~ Normal(mu_bias,d(i), sigma_bias,d(i)^2)`

Where `d(i)` is design stratum (RCT low RoB, RCT some concerns, NRS moderate,
NRS high, etc). Priors for `mu_bias` and `sigma_bias` are informed by bias
elicitation and sensitivity envelopes.

### 6.6 Dose-Response NMA

For treatment-dose pair `(t, dose)`:

- `theta_i,t,d = h_t(dose) + u_i,t,d`

Candidate `h_t`:

- Emax: `E0_t + Emax_t * dose / (ED50_t + dose)`
- spline basis: `sum_j beta_tj * B_j(dose)`

Model comparison via stacking weights across candidate dose functions.

### 6.7 Component NMA (CNMA)

Treatment represented as component vector `w_t`.

- `theta_t = sum_c w_tc * phi_c + sum_{c<d} w_tc w_td * psi_cd`

Interaction shrinkage prior encourages sparse synergistic terms.

### 6.8 Inconsistency and Robustness

Inconsistency:

- design-by-treatment random inconsistency terms
- node-splitting automatic diagnostic reports

Robust pooling:

- heavy-tailed random effects (`StudentT`)
- outlier mixture random effects
- study-level influence diagnostics and leave-one-out deltas

Publication/reporting bias sensitivity:

- selection model and limit meta-analysis style sensitivity as optional modules

### 6.9 Model Averaging

Candidate model family includes:

- heterogeneity structures
- inconsistency structures
- bias structures
- dose and component functional forms

Final ensemble weights:

- Bayesian stacking over leave-one-study-out predictive performance

## 7. Priors and Prior Governance

Default prior classes:

- weakly informative priors for baseline/intercept terms
- half-normal or half-t priors for heterogeneity
- skeptical priors for high-dimensional interactions
- bias priors stratified by RoB and design

Governance:

- every analysis must ship a prior rationale block
- sensitivity runs required for all key priors
- prior-data conflict diagnostics automatically generated

## 8. Inference and Computation

Primary engine:

- `Stan` (NUTS via CmdStan)

Optional acceleration:

- Pathfinder/ADVI warm starts
- parallel chains and within-chain threading

Run standards:

- minimum 4 chains
- Rhat < 1.01
- bulk/tail ESS thresholds by parameter block
- zero divergent transitions for release analyses

Fallback strategy:

- reparameterization and adaptive non-centered forms
- robust priors and tighter geometry constraints

## 9. Data Contracts

Core tables:

- `studies`: study_id, design, year, source_id, rob_domain_summary
- `arms`: study_id, arm_id, treatment_id, dose, components_json, n
- `outcomes_ad`: study_id, arm_id, outcome_id, measure_type, value, se
- `ipd`: study_id, patient_id, treatment_id, outcome columns, covariates
- `covariates`: covariate_name, type, transform, harmonization rules
- `mapping`: treatment ontology and cross-trial harmonization
- `provenance`: record_id, source_hash, transform_step, timestamp

Rules:

- schema validated with strict typed checks
- no model run allowed on failed schema validation
- every artifact traceable to immutable input hashes

## 10. Repository Structure

```text
advanced-nma-pooling/
  docs/
    specs/
      technical-spec-v1.md
      milestone-tickets-v1.md
    methods/
    validation/
  src/
    nma_pool/
      data/
      models/
      inference/
      validation/
      reporting/
  configs/
  pipelines/
  tests/
    unit/
    integration/
    simulation/
  notebooks/
```

## 11. Package and Interface Design

Python package name: `nma_pool`

Key interfaces:

- `DatasetBuilder`: harmonize and validate inputs
- `ModelSpec`: declarative model configuration
- `FitRunner`: compile and run inference
- `DiagnosticsSuite`: convergence, fit, inconsistency, influence
- `BenchmarkRunner`: simulation and baseline comparison
- `ReportBuilder`: machine-readable and narrative outputs

Config first:

- all analyses are driven by versioned YAML specs
- each run emits manifest, seed, software versions, and hashes

## 12. Validation and Testing Matrix

### 12.1 Unit Tests

- parsing and schema checks
- likelihood component correctness
- prior construction and transform correctness

### 12.2 Integration Tests

- end-to-end AD run
- end-to-end AD+IPD run
- survival + non-PH workflow
- cross-design bias-adjusted run

### 12.3 Statistical Calibration Tests

- simulation-based calibration for major parameter blocks
- posterior predictive checks with predefined failure thresholds

### 12.4 Regression Tests

- freeze benchmark seeds and expected summary outputs
- CI alert on metric drift beyond tolerance

### 12.5 Performance Tests

- runtime and memory budget per reference dataset
- scaling tests for up to 200-study networks

## 13. Benchmark Program

Baselines:

- `multinma`
- `netmeta`
- `gemtc`
- `crossnma`
- dose-response baselines where applicable

Metrics:

- bias, RMSE, coverage
- predictive log score
- treatment ranking regret
- decision regret under utility model
- compute cost and failure rate

Stress scenarios:

- sparse/disconnected subnetworks
- strong effect-modifier imbalance
- high heterogeneity with outliers
- outcome missingness and selective reporting
- non-proportional hazards

## 14. Reporting Outputs

Required outputs per run:

- model card
- diagnostics report
- league table with uncertainty
- absolute effects by target population
- inconsistency report
- RoB-aware certainty summary
- reproducibility manifest

Output formats:

- JSON for machine interfaces
- HTML/PDF for review workflows

## 15. MLOps and Reproducibility

- containerized execution for fixed environments
- deterministic seeds and pinned dependencies
- CI matrix for OS and python versions
- artifact registry with immutable run IDs
- signed release bundles for external dissemination

## 16. Governance and Compliance

- protocol-first analysis with pre-specified estimands
- no silent model changes between reruns
- audit log for every transformed field
- de-identification checks for IPD pipelines

## 17. Delivery Plan (24 Months)

M0-M2:

- finalize protocol templates and data contracts
- stand up repo and CI
- implement AD core with minimal diagnostics

M3-M6:

- full core NMA + inconsistency diagnostics
- initial benchmark harness

M7-M10:

- AD+IPD ML-NMR module
- survival module with non-PH support

M11-M14:

- cross-design bias-adjusted pooling
- RoB integration and sensitivity engine

M15-M18:

- dose-response and CNMA modules
- model averaging and robust mixtures

M19-M22:

- living update pipeline and reporting automation
- extended benchmark publication package

M23-M24:

- external replication studies
- v1.0 release and methods manuscripts

## 18. Risks and Mitigations

Risk: model complexity reduces interpretability.

- Mitigation: mandatory model cards and ablation reports.

Risk: sparse networks destabilize rich models.

- Mitigation: structured shrinkage, model averaging, and fallback specs.

Risk: IPD access delays.

- Mitigation: AD-first architecture with pluggable IPD modules.

Risk: observational bias misspecification.

- Mitigation: explicit bias priors and scenario analyses, never single-point
  causal claims.

## 19. Immediate Next Actions (First 30 Days)

1. Lock disease domain and outcomes for v1 benchmark track.
2. Finalize schema contract and implement strict validators.
3. Implement reference AD random-effects NMA in `src/nma_pool/models`.
4. Build simulation generator and baseline comparison harness.
5. Define pass/fail thresholds and CI policy for statistical tests.

