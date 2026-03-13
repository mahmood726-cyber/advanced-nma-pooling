# Paper 1 Manuscript Outline (RSM)

Version: 1.0  
Date: February 28, 2026

## Proposed Title

A reproducible, bias-adjusted, and non-PH-capable network meta-analysis engine:
calibration and benchmark evaluation.

## Abstract Structure

1. Background
2. Methods
3. Results
4. Conclusions
5. Keywords

## 1. Introduction

1. Limitations of single-design and PH-restricted NMA workflows.
2. Need for calibrated, reproducible, stress-tested NMA engines.
3. Paper objective and contributions.

## 2. Methods

1. Data contracts and validation layer.
2. Core AD model.
3. Bias-adjusted mixed-design model:
   - frequentist formulation
   - Bayesian formulation
4. Survival non-PH piecewise model.
5. Inference and diagnostics.
6. Simulation registry and locked gates.
7. External benchmark interfaces and comparators.

## 3. Results

1. Continuous calibration scenario.
2. Survival non-PH scenario.
3. Mixed-design bias-adjustment behavior.
4. Prior sensitivity summaries.
5. Robustness checks and failure-case handling.

## 4. Applied Demonstrations

1. Real mixed-design network (RCT + NRS).
2. Real survival non-PH network.

## 5. Discussion

1. Main findings.
2. Practical implications for evidence synthesis workflows.
3. Limitations:
   - interval independence approximation in current survival implementation
   - planned extensions for interval-correlation and richer bias structures
4. Future roadmap.

## 6. Reproducibility Statement

1. One-command paper bundle.
2. Manifested hashes and deterministic seeds.
3. Artifact list and command index.

## Tables and Figures (Locked Skeleton)

1. Table 1: Model modules and assumptions.
2. Table 2: Simulation scenarios and locked parameters.
3. Table 3: Primary endpoint summary by scenario/model.
4. Figure 1: Coverage and bias comparison across methods.
5. Figure 2: Survival interval-specific effect recovery.
6. Figure 3: Prior sensitivity tornado/range chart.
7. Figure 4: Reproducibility workflow diagram.

## Supplement Plan

1. Full mathematical specification.
2. Prior details and sensitivity grids.
3. Additional simulation strata.
4. Extended diagnostics and benchmark artifacts.
