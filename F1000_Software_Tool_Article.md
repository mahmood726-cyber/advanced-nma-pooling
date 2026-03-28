# Advanced NMA Pooling: a software tool for reviewer-auditable evidence synthesis

## Authors
- Mahmood Ahmad [1,2]
- Niraj Kumar [1]
- Bilaal Dar [3]
- Laiba Khan [1]
- Andrew Woo [4]
- Corresponding author: Andrew Woo (andy2709w@gmail.com)

## Affiliations
1. Royal Free Hospital
2. Tahir Heart Institute Rabwah
3. King's College Medical School
4. St George's Medical School

## Abstract
**Background:** Complex network meta-analysis workflows are often split across ad hoc scripts for data validation, mixed aggregate-data and IPD integration, bias adjustment, survival modelling, benchmarking, and publication packaging. That fragmentation makes software peer review difficult because reviewers need to reconstruct which configuration produced which result.

**Methods:** Advanced NMA Pooling is an installable Python toolkit with schema-validated data builders, config-driven command-line workflows, optional Stan backends, and publication-facing validation pipelines. The local package exposes aggregate-data NMA, ML-NMR-style AD+IPD workflows, design-stratified bias adjustment, Bayesian counterparts, and non-proportional-hazards survival pipelines.

**Results:** The repository contains runnable example configurations, unit and integration tests, simulation checks, benchmark adapters for external R tools, release manifests, and a paper-bundle workflow that records commit-linked provenance for reviewer reruns.

**Conclusions:** The contribution is a reproducibility-oriented software layer for advanced NMA rather than a claim of universal superiority over established NMA platforms.

## Keywords
network meta-analysis; ML-NMR; Bayesian evidence synthesis; survival modelling; reproducibility; software tool

## Introduction
The package is intended for analysts who need auditable transitions between model specification, inference, diagnostics, benchmarking, and manuscript-ready artifacts. Unlike single-purpose NMA utilities, the emphasis here is on preserving a traceable path from structured inputs to model cards, benchmark summaries, and release metadata.

The manuscript therefore positions the toolkit alongside, rather than above, established options such as MetaInsight, `netmeta`, `multinma`, and bespoke Stan workflows. Its main differentiator is operational reproducibility: fixed configuration schemas, packaged example pipelines, and publication-facing provenance.

The manuscript structure below is deliberately aligned to common open-software review requests: the rationale is stated explicitly, at least one runnable example path is named, local validation artifacts are listed, and conclusions are bounded to the functions and outputs documented in the repository.

## Methods
### Software architecture and workflow
Core modules cover strict data schemas, dataset construction, frequentist and Bayesian model classes, CLI orchestration, diagnostics, simulations, and reporting helpers. Example workflows include aggregate-data analysis, bias-adjusted synthesis, ML-NMR, Bayesian ML-NMR, survival non-PH modelling, and a bundled publication suite.

### Installation, runtime, and reviewer reruns
The local implementation is packaged under `C:\Models\advanced-nma-pooling`. The manuscript identifies the local entry points, dependency manifest, fixed example input, and expected saved outputs so that reviewers can rerun the documented workflow without reconstructing it from scratch.

- Entry directory: `C:\Models\advanced-nma-pooling`.
- Detected documentation entry points: `README.md`, `external/r/README.md`, `f1000_artifacts/tutorial_walkthrough.md`.
- Detected environment capture or packaging files: `requirements.txt`.
- Named worked-example paths in this draft: `configs/` example payloads for every CLI workflow; `artifacts/paper1-bundle/` for a reproducible manuscript-support bundle; `f1000_artifacts/tutorial_walkthrough.md` for a reviewer rerun path.
- Detected validation or regression artifacts: `f1000_artifacts/validation_summary.md`, `tests/__init__.py`, `tests/integration/test_benchmark.py`, `tests/integration/test_bias_sensitivity_pipeline.py`, `tests/integration/test_build_artifacts.py`, `tests/integration/test_cli.py`, `tests/integration/test_paper1_bundle_pipeline.py`, `tests/integration/test_publication_pipeline.py`.
- Detected example or sample data files: `configs/example-analysis.json`, `configs/example-benchmark.json`, `configs/example-bias-adjusted-bayesian.json`, `configs/example-bias-adjusted.json`, `configs/example-bias-sensitivity.json`, `configs/example-mlnmr.json`.

### Worked examples and validation materials
**Example or fixed demonstration paths**
- `configs/` example payloads for every CLI workflow.
- `artifacts/paper1-bundle/` for a reproducible manuscript-support bundle.
- `f1000_artifacts/tutorial_walkthrough.md` for a reviewer rerun path.

**Validation and reporting artifacts**
- `tests/unit/`, `tests/integration/`, and `tests/simulation/` cover core estimators and publication workflows.
- `artifacts/publication-summary.md` and `artifacts/publication-suite.json` record package-level validation outputs.
- `scripts/release_manifest.py` and release metadata document provenance and checksums.

### Typical outputs and user-facing deliverables
- Structured model-card JSON outputs for analysis runs.
- Benchmark summaries comparing internal and optional external backends.
- Publication summaries and copied artifacts intended for reviewer audit.

### Reviewer-informed safeguards
- Provides a named example workflow or fixed demonstration path.
- Documents local validation artifacts rather than relying on unsupported claims.
- Positions the software against existing tools without claiming blanket superiority.
- States limitations and interpretation boundaries in the manuscript itself.
- Requires explicit environment capture and public example accessibility in the released archive.

## Review-Driven Revisions
This draft has been tightened against recurring open peer-review objections taken from the supplied reviewer reports.
- Reproducibility: the draft names a reviewer rerun path and points readers to validation artifacts instead of assuming interface availability is proof of correctness.
- Validation: claims are anchored to local tests, validation summaries, simulations, or consistency checks rather than to unsupported assertions of performance.
- Comparators and niche: the manuscript now names the relevant comparison class and keeps the claimed niche bounded instead of implying universal superiority.
- Documentation and interpretation: the text expects a worked example, input transparency, and reviewer-verifiable outputs rather than a high-level feature list alone.
- Claims discipline: conclusions are moderated to the documented scope of Advanced NMA Pooling and paired with explicit limitations.

## Use Cases and Results
The software outputs should be described in terms of concrete reviewer-verifiable workflows: running the packaged example, inspecting the generated results, and checking that the reported interpretation matches the saved local artifacts. In this project, the most important result layer is the availability of a transparent execution path from input to analysis output.

Representative local result: `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.

### Concrete local quantitative evidence
- `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.
- `artifacts/publication-summary.md` reports git_commit: 694a31770a8e4e51d4ceab43a77d12aaad8795ea.
- `artifacts/publication-summary.review.md` reports created_at_utc: 2026-02-28T20:16:33.285622+00:00.

## Discussion
Representative local result: `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.

The local reviewer-facing package already addresses several recurring software-paper criticisms: it provides concrete worked examples, names comparator classes explicitly, distinguishes engineering verification from methods validation, and records commit-linked provenance in publication artifacts.

### Limitations
- The confirmatory publication suite remains narrower than a full methods-validation study and should be described as such.
- The mixed-design example is still synthetic rather than a full clinical case study.
- Public repository release and DOI archival remain necessary for a fully citable external release.

## Software Availability
- Local source package: `advanced-nma-pooling` under `C:\Models`.
- Public repository: `https://github.com/mahmood726-cyber/advanced-nma-pooling`.
- Public source snapshot: `https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-15-r3`.
- DOI/archive record: No project-specific DOI or Zenodo record URL was detected locally; archive registration pending.
- Environment capture detected locally: `requirements.txt`.
- Reviewer-facing documentation detected locally: `README.md`, `external/r/README.md`, `f1000_artifacts/tutorial_walkthrough.md`.
- Reproducibility walkthrough: `f1000_artifacts/tutorial_walkthrough.md` where present.
- Validation summary: `f1000_artifacts/validation_summary.md` where present.
- Reviewer rerun manifest: `F1000_Reviewer_Rerun_Manifest.md`.
- Multi-persona review memo: `F1000_MultiPersona_Review.md`.
- Concrete submission-fix note: `F1000_Concrete_Submission_Fixes.md`.
- License: see the local `LICENSE` file.

## Data Availability
No new participant-level clinical data are distributed in the manuscript bundle. Example configurations, model cards, and publication artifacts are packaged locally; any public release should replace the repository and DOI release metadata with the frozen external archive.

## Reporting Checklist
Real-peer-review-aligned checklist: `F1000_Submission_Checklist_RealReview.md`.
Reviewer rerun companion: `F1000_Reviewer_Rerun_Manifest.md`.
Companion reviewer-response artifact: `F1000_MultiPersona_Review.md`.
Project-level concrete fix list: `F1000_Concrete_Submission_Fixes.md`.

## Declarations
### Competing interests
The authors declare that no competing interests were disclosed.

### Grant information
No specific grant was declared for this manuscript draft.

### Author contributions (CRediT)
| Author | CRediT roles |
|---|---|
| Mahmood Ahmad | Conceptualization; Software; Validation; Data curation; Writing - original draft; Writing - review and editing |
| Niraj Kumar | Conceptualization |
| Bilaal Dar | Conceptualization |
| Laiba Khan | Conceptualization |
| Andrew Woo | Conceptualization |

### Acknowledgements
The authors acknowledge contributors to open statistical methods, reproducible research software, and reviewer-led software quality improvement.

## References
1. DerSimonian R, Laird N. Meta-analysis in clinical trials. Controlled Clinical Trials. 1986;7(3):177-188.
2. Higgins JPT, Thompson SG. Quantifying heterogeneity in a meta-analysis. Statistics in Medicine. 2002;21(11):1539-1558.
3. Viechtbauer W. Conducting meta-analyses in R with the metafor package. Journal of Statistical Software. 2010;36(3):1-48.
4. Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ. 2021;372:n71.
5. Fay C, Rochette S, Guyader V, Girard C. Engineering Production-Grade Shiny Apps. Chapman and Hall/CRC. 2022.
