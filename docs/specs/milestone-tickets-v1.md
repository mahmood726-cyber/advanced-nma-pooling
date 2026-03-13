# Milestone Tickets v1

Date: 2026-02-28
Owner: Program Lead
Status: Ready for grooming

## Epic E1: Foundation and Core AD NMA (M0-M6)

T1. Create package skeleton and CI

- Deliverable: installable `nma_pool` package, lint/test pipeline
- Acceptance: CI green on unit smoke tests

T2. Implement schema contracts and validators

- Deliverable: strict parsers for studies, arms, outcomes, provenance
- Acceptance: malformed fixtures fail with deterministic errors

T3. Build core AD random-effects NMA model

- Deliverable: binary + continuous outcomes with multi-arm support
- Acceptance: reproduces reference examples within tolerance

T4. Add inconsistency diagnostics

- Deliverable: node-splitting and design-by-treatment diagnostics
- Acceptance: known inconsistency simulation is correctly flagged

T5. Release v0.1 benchmark harness

- Deliverable: baseline comparison runner against at least 2 external methods
- Acceptance: outputs comparable summary metrics and artifacts

## Epic E2: AD+IPD and Survival (M7-M10)

T6. Implement ML-NMR AD+IPD integration

- Deliverable: shared module for patient-level and aggregated likelihoods
- Acceptance: recovers truth in effect-modifier simulation scenarios

T7. Add covariate distribution integration for AD-only arms

- Deliverable: quadrature and Monte Carlo integration modes
- Acceptance: both modes agree within tolerance on reference cases

T8. Implement survival likelihood with non-PH support

- Deliverable: piecewise exponential model with time-varying effects
- Acceptance: passes non-PH simulation calibration thresholds

## Epic E3: Cross-Design Bias-Adjusted Synthesis (M11-M14)

T9. Add design- and RoB-stratified bias model

- Deliverable: hierarchical bias terms with configurable priors
- Acceptance: bias-injected simulations show improved calibration

T10. Add structured sensitivity workflows

- Deliverable: prior/bias scenario batch runner
- Acceptance: one command produces full sensitivity report

T11. Certainty integration outputs

- Deliverable: machine-readable certainty summaries linked to diagnostics
- Acceptance: report includes all required certainty fields

## Epic E4: Dose, Components, and Robustness (M15-M18)

T12. Implement dose-response module

- Deliverable: Emax and spline dose functions
- Acceptance: model selection works via stacking weights

T13. Implement CNMA module

- Deliverable: additive component effects with interaction shrinkage
- Acceptance: recovers synthetic component truths in sparse settings

T14. Add robust pooling distributions

- Deliverable: heavy-tailed and outlier-mixture random effects
- Acceptance: outlier stress tests outperform Gaussian baseline

T15. Add model stacking framework

- Deliverable: standardized model family interface and stacking optimizer
- Acceptance: ensemble improves predictive log score on benchmarks

## Epic E5: Living NMA and Productization (M19-M24)

T16. Build incremental update pipeline

- Deliverable: append-only evidence updates and rerun orchestration
- Acceptance: update run reuses cached artifacts and remains reproducible

T17. Build report generator

- Deliverable: HTML/PDF/JSON outputs with diagnostics and league tables
- Acceptance: single command builds complete decision package

T18. External replication package

- Deliverable: reproducible replication of selected published NMAs
- Acceptance: public artifact pack with manifests and checksums

T19. Release v1.0

- Deliverable: tagged release, docs, benchmark results, model cards
- Acceptance: all release criteria in spec satisfied

## Cross-Cutting Tickets

T20. Testing policy and thresholds

- Deliverable: codified statistical and software QA gates
- Acceptance: CI enforces all gates on PR

T21. Reproducibility and artifact registry

- Deliverable: run manifests with hash lineage and deterministic seeds
- Acceptance: independent rerun reproduces core metrics

T22. Security and de-identification checks for IPD

- Deliverable: automated checks and fail-fast policy
- Acceptance: policy violations block run artifacts

