# Advanced NMA Pooling v0.1.1: a reproducibility-oriented Python toolkit for advanced evidence-synthesis workflows

## Authors
Mahmood Ahmad [1,2], Niraj Kumar [1], Bilaal Dar [3], Laiba Khan [1], Andrew Woo [4]

### Affiliations
1. Royal Free Hospital, London, United Kingdom
2. Tahir Heart Institute, Rabwah, Pakistan
3. King's College London GKT School of Medical Education, London, United Kingdom
4. St George's, University of London, London, United Kingdom

Corresponding author: Mahmood Ahmad (mahmood.ahmad2@nhs.net)

## Abstract

**Background:** Advanced evidence-synthesis workflows often require several model families within one project, including aggregate-data network meta-analysis, mixed aggregate-data and individual patient data integration, design-aware bias adjustment, and survival modeling under non-proportional hazards. In practice these analyses are frequently spread across ad hoc scripts, making configuration capture, validation, and release provenance difficult.

**Methods:** We developed Advanced NMA Pooling v0.1.1 (`nma-pool`), an open-source Python toolkit for config-driven evidence-synthesis workflows. The implemented package scope includes aggregate-data network meta-analysis, ML-NMR-style AD+IPD integration, design-stratified bias adjustment, survival non-proportional hazards workflows [6], benchmark adapters for external R tools, a locked publication suite, and a one-command paper bundle that emits manifests and execution summaries. This article reports quantitative evidence only for the publication-suite and paper-bundle workflows; the remaining modules are described as implemented package capabilities rather than as separately validated case studies in this manuscript.

**Results:** Quantitative evaluation in this article focused on two locked manuscript-facing workflows. In the bundled publication suite, the pre-specified continuous calibration scenario (120 simulated networks, 240 estimable treatment effects) compared `core_fixed_effects` with `core_random_effects`, achieving 95% coverage 0.9417, strict log-score win rate 0.7805, and mean log-score delta 0.0450 (95% CI 0.0039 to 0.0828). In the survival non-proportional hazards scenario (100 simulated networks, 600 estimable interval-treatment effects), `survival_nph_random_effects` achieved coverage 0.9700, median absolute bias 0.0569 versus 0.1882 for the proportional-hazards baseline, bias improvement 0.6973, and strict win rate 1.0000. The example paper bundle completed four workflows successfully, estimated an `nrs` bias term of 0.5635 in the frequentist bias-adjusted example, reproduced similar Bayesian estimates with the analytic backend, and generated a manifest plus hashed outputs.

**Conclusions:** Advanced NMA Pooling v0.1.1 provides a reproducibility-oriented workflow layer for advanced evidence-synthesis projects. The contribution supported in this article is a software-tool claim centered on integration, locked configurations, reviewer-facing bundles, and release provenance, rather than a comprehensive benchmark of every implemented model family.

## Keywords
network meta-analysis, evidence synthesis, reproducibility, ML-NMR, non-proportional hazards, bias adjustment, software tool

## Introduction

Network meta-analysis is widely used to synthesize comparative effectiveness evidence across multiple treatments [1,2]. However, advanced evidence-synthesis projects often extend beyond standard aggregate-data models. Population-adjusted treatment comparisons may require multilevel network meta-regression over combined aggregate-data and individual patient data structures [3]. Mixed-design evidence may require explicit handling of design-related bias, and time-varying treatment effects require methods that do not assume proportional hazards. In research practice these tasks are frequently implemented as a collection of custom scripts, notebooks, and one-off validation code. That fragmentation makes it harder to audit model assumptions, reproduce results from configuration alone, or trace release artifacts back to a fixed source state.

Advanced NMA Pooling was developed as a package-level response to that problem. The project packages several related workflows behind a common CLI and schema-validated configuration layer. The aim is to complement, not replace, established statistical workflows by emphasizing repeatable execution, explicit manifests, manuscript-oriented validation routines, and release provenance. This article describes the current implementation in release v0.1.1, but its quantitative results are intentionally narrower than the full implemented feature set: the manuscript focuses on the publication suite, the survival non-proportional hazards validation path, and the bias-adjusted paper-bundle outputs. Accordingly, the paper should be read as a software-tool and reproducibility article anchored to two locked reference workflows, not as a comprehensive comparative validation study of every implemented estimator.

Existing open software already covers many standard evidence-synthesis tasks, including graphical environments aimed at non-programming users and programming packages focused on specific model families. Advanced NMA Pooling is not presented as a blanket replacement for those tools. Its narrower target is operational integration: running multiple advanced workflow families under one locked, auditable, release-managed interface when simulation gates, bundle manifests, and manuscript-facing outputs need to be regenerated from configuration rather than reconstructed from a mixture of scripts. Concretely, GUI tools such as MetaInsight are optimized for interactive standard analyses, while programming packages such as `netmeta` and `multinma` provide strong depth within a narrower modeling family. Advanced NMA Pooling instead emphasizes one CLI-centered workflow layer that can carry publication gates, mixed-design adjustment, survival non-proportional hazards workflows, and submission-facing provenance files together.

**Table 1. Positioning of Advanced NMA Pooling relative to common open-tool classes**

| Tool class | Typical strength | Typical gap for the current use case |
|---|---|---|
| GUI-oriented evidence-synthesis tools such as MetaInsight | Low barrier to entry and straightforward standard analyses | Less natural fit for config-locked, multi-workflow, manuscript-rebuild pipelines |
| Single-model programming packages such as `netmeta` and `multinma` | Strong depth within a specific modeling family | Often require additional scripting to combine validation, sensitivity, packaging, and release-manifest steps |
| Advanced NMA Pooling | One CLI-centered workflow layer spanning multiple advanced model families, publication gates, bundles, and provenance outputs | Command-line first, with less end-user accessibility than point-and-click tools |

## Methods

### Implementation

Advanced NMA Pooling is implemented in Python and distributed as the `nma-pool` package. The source tree is organized into `data`, `models`, `inference`, `validation`, `reporting`, and `pipelines` modules, with optional R adapters in `external/r/` for benchmark comparisons. Input payloads are assembled through a strict data-building layer that checks studies, arms, aggregate outcomes, survival fields, and configuration values before model fitting.

The currently implemented workflow families are:

1. **Aggregate-data NMA.** Config-driven fixed- and random-effects aggregate-data network meta-analysis for continuous and binary outcomes.
2. **ML-NMR-style AD+IPD integration.** A first-pass multilevel network meta-regression workflow for aggregate-data plus individual patient data integration. The current implementation is restricted to continuous outcomes and supports empirical or Monte Carlo integration.
3. **Design-stratified bias adjustment.** Frequentist and Bayesian workflows that estimate design-level offsets, for example differences between randomized controlled trials (`rct`) and non-randomized studies (`nrs`).
4. **Survival non-proportional hazards modeling.** A piecewise exponential survival workflow with interval-specific treatment effects and both fixed- and random-effects non-proportional hazards fits, benchmarked against a proportional-hazards baseline approximation.
5. **Benchmarking and publication workflows.** External adapter interfaces for R-based comparators, a publication suite built around locked simulation scenarios and gate criteria, and a one-command paper bundle that executes selected workflows and writes a manifest with checksums and copied supporting documents.

The installed CLI exposes these workflows as subcommands: `analysis`, `benchmark`, `bias-adjusted`, `bias-adjusted-bayesian`, `bias-sensitivity`, `mlnmr`, `mlnmr-bayesian`, `survival-nph`, `publication-suite`, and `paper1-bundle`. The release workflow additionally generates `SHA256SUMS.txt` and `release-manifest.json`, linking built artifacts to a specific commit.

The present manuscript does not claim that every implemented subcommand has been quantitatively validated in a standalone case study within this paper. In particular, ML-NMR and external benchmark adapters are described as package capabilities, while the formal numeric results reported here come from the publication-suite and paper-bundle artifacts.

### Operation

A typical user workflow consists of four steps:

1. **Configuration and data loading.** Users start from one of the example JSON configurations in `configs/` or provide a custom payload. The package validates study identifiers, arm structure, outcome types, design labels, and model settings before execution.
2. **Model execution.** The selected CLI subcommand runs the requested workflow and writes machine-readable JSON outputs. Publication-oriented commands also emit markdown summaries.
3. **Diagnostics and sensitivity assessment.** Workflow outputs include fit summaries, treatment effects, design-bias estimates where relevant, interval-specific survival effects, or predictive superiority diagnostics depending on the pipeline. Bayesian workflows can use the analytic backend or a Stan backend when available.
4. **Reproducibility export.** The `paper1-bundle` workflow writes a manifest, step timings, copied protocol documents, and the outputs of the executed workflows. Release builds separately generate hashed distribution artifacts and a release manifest.

Package metadata requires Python 3.11 or later, with optional `.[dev]` extras for local build/test tooling and `.[stan]` extras for Stan-backed workflows when those are needed. The manuscript-facing publication outputs also record the Python version, platform, and git commit used for the run, and the submission package includes copied release provenance files in `f1000_artifacts/release-manifest-v0.1.1.json` and `f1000_artifacts/SHA256SUMS-v0.1.1.txt`.

Figure 1 summarizes the manuscript-facing workflow from schema-validated input through model execution, reviewer-facing summaries, and release provenance. The aligned figure asset and caption are provided in `f1000_artifacts/Figure_1_reproducibility_workflow.svg` and `f1000_artifacts/figure_captions.md`.

Representative commands are shown below.

```bash
nma-pool analysis --config configs/example-analysis.json --out artifacts/model-card.json
nma-pool publication-suite --config configs/example-publication-suite.json --out artifacts/publication-suite.json --summary artifacts/publication-summary.md
nma-pool paper1-bundle --config configs/example-paper1-bundle.json --out-dir artifacts/paper1-bundle
```

### Validation strategy

Validation evidence in the repository comes from four sources.

**Engineering verification.** The repository currently contains 69 automated tests across unit, integration, and simulation layers. These cover data contracts, model recovery, inconsistency diagnostics, benchmark adapters, CLI execution, build artifacts, and manuscript-oriented pipelines. They support software integrity and regression detection, but they are not presented here as substitutes for cross-software concordance or broad methodological validation.

**Model-behavior tests.** Unit tests verify that the core aggregate-data model recovers known treatment effects, ML-NMR recovers treatment and interaction effects under controlled settings, bias-adjusted models improve over naive pooling when design bias is injected, and inconsistency diagnostics flag deliberately inconsistent networks without overflagging consistent ones.

**Simulation calibration.** The strongest single quantitative test is the survival non-proportional hazards calibration test. Across 80 simulated seeds, the test asserts a median absolute error below 0.10 and empirical 95% interval coverage between 0.93 and 0.97 for interval-specific treatment effects.

**Publication and build pipelines.** Integration tests verify that the publication suite writes machine-readable and markdown outputs, the paper bundle writes a manifest and executive summary, and the build process produces a wheel, an sdist, bundled Stan assets, `SHA256SUMS.txt`, and `release-manifest.json`. These outputs make the manuscript claims auditable and reproducible, but they complement rather than replace methodological validation.

For this manuscript, the quantitative summaries were taken from the generated artifacts `artifacts/publication-suite.json`, `artifacts/publication-summary.md`, `artifacts/paper1-bundle/manifest.json`, and `artifacts/paper1-bundle/paper1-executive-summary.md`. These files are named explicitly because they are the immediate source for the numeric results reported below. In the current manuscript-facing configuration, the publication suite also requires git-commit capture. The artifacts are included in the public GitHub submission snapshot `f1000-submission-2026-03-15-r3`, while DOI-backed archival of that snapshot remains pending.

### Locked publication-suite metrics and scenarios

The publication-suite configuration is locked in `configs/example-publication-suite.json`, with scenario definitions summarized in `docs/validation/paper1-simulation-registry.md`. The continuous confirmatory scenario uses 120 A-B-C simulated networks (seeds 1000 to 1119; 120 participants per arm; arm-level SE 0.25; observation noise SD 0.25; study heterogeneity SD 0.0) and compares a pre-specified candidate model, `core_fixed_effects`, with a pre-specified baseline model, `core_random_effects`. The survival scenario uses 100 simulated non-proportional hazards networks (seeds 2000 to 2099; 650 participants per arm; intervals [0,3], [3,6], and [6,12]; follow-up fraction 0.85) and compares `survival_nph_random_effects` with `survival_ph_fixed_effects`.

The principal predictive endpoints are defined as follows. Mean Gaussian log score [4] is averaged over estimable paired predictions. Strict win rate is the proportion of non-tied paired comparisons where the candidate score exceeds the baseline score; ties are excluded from the denominator. Mean log-score delta is the paired candidate-minus-baseline difference in mean Gaussian log score. Superiority probability is the bootstrap estimate of `P(delta > 0)`. One-sided sign, permutation, and signed-rank tests are also reported, with Holm-adjusted multiplicity control [5] when configured. The locked gate thresholds in the example configuration were coverage 0.93 to 0.97, continuous strict win rate at least 0.70, survival bias improvement at least 0.20, survival strict win rate at least 0.80, and pre-specified maxima for inferential p-values and Monte Carlo standard errors. These thresholds are project-level release gates for the bundled scenarios, intended to detect regressions in the reference workflows rather than to define universal adequacy criteria for all network meta-analysis software or applied evidence-synthesis projects.

## Results

### Publication-suite validation

The default publication suite completed successfully and returned `overall_pass=True`. The exact numeric values summarized in Table 2 are taken from `artifacts/publication-suite.json` and `artifacts/publication-summary.md` in the release tree. The continuous comparison is confirmatory and pre-specified rather than adaptively selected. These results are presented as locked reference-workflow checks for the manuscript-facing pipelines rather than as an exhaustive comparative benchmark across all supported model classes.

**Table 2. Bundled publication-suite results generated from release v0.1.1**

| Scenario | Candidate model | Baseline model | Networks | Estimable effects | Coverage | Median absolute bias | Strict win rate vs baseline | Mean log-score delta (95% CI) | Gate summary |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| Continuous calibration | `core_fixed_effects` | `core_random_effects` | 120 | 240 | 0.9417 | 0.1967 | 0.7805 | 0.0450 (0.0039 to 0.0828) | All continuous gates passed |
| Survival non-PH | `survival_nph_random_effects` | `survival_ph_fixed_effects` | 100 | 600 | 0.9700 | 0.0569 | 1.0000 | 7.8906 (7.7282 to 8.0687) | All survival gates passed |

In the continuous scenario, the fixed-effects candidate and random-effects baseline had the same median absolute bias to machine precision, but the fixed-effects model achieved a better mean log score, a strict win rate of 0.7805, and multiplicity-adjusted permutation, sign-test, and signed-rank p-values below the configured thresholds. Practically, this indicates slightly better average predictive fit without sacrificing nominal interval coverage in the locked continuous setting. Because this confirmatory scenario uses zero between-study heterogeneity, it should be interpreted primarily as a regression-and-stability check for the publication workflow rather than as a broad stress test of random-effects behavior under heterogeneous evidence. In the survival scenario, the non-proportional hazards random-effects candidate materially outperformed the proportional-hazards baseline. The baseline median absolute bias was 0.1882, whereas the candidate median absolute bias was 0.0569, corresponding to a 69.7% improvement. The candidate also achieved strict win rate 1.0000, bootstrap superiority probability 1.0000, and coverage 0.9700. In practical terms, the non-proportional hazards workflow was clearly preferable when the data-generating process contained time-varying effects.

### Paper-bundle reproducibility run and worked mixed-design example

The example `paper1-bundle` workflow executed four steps successfully: `publication_suite`, `bias_adjusted`, `bias_adjusted_bayesian`, and `bias_sensitivity`. The generated manifest recorded hashes for all emitted outputs and copied four manuscript-supporting documents into the bundle.

The bundled bias-adjusted example estimated an `nrs` bias term of 0.5635 in the frequentist workflow. The Bayesian bias-adjusted example used the analytic backend and produced a similar `nrs` bias estimate of 0.5680. This example is still synthetic, but it is concrete enough to read as a worked mixed-design vignette: the input network contains two randomized A-B and A-C studies with observed treatment differences of 1.0 and 2.0 units, plus two non-randomized analogues with larger apparent differences of 1.6 and 2.6 units. In that setting, the positive `nrs` term means that the non-randomized evidence stream was estimated to sit above the randomized evidence scale by roughly 0.56 model-scale units, so the bias-adjusted fit separated the design strata rather than forcing a single pooled effect. The frequentist bias-adjusted fit then returned treatment effects of 1.0183 for `B` and 2.0183 for `C` versus `A`, which is directionally consistent with recovering the randomized scale in the presence of an upward non-randomized offset. The prior-sensitivity workflow evaluated 24 scenarios; across these runs, the estimated treatment effect span was 0.1525 for treatment `B` and 0.1517 for treatment `C`, while the `nrs` bias span was 0.2693. Those spans indicate modest movement across the tested prior grid in this example, but not a reversal of the treatment ordering. Together, these outputs show that the package can produce not only model fits but also a reproducibility bundle that documents what was run, how long it took, and which files were generated.

### Software provenance and packaging

The repository-level evidence also includes software provenance separate from statistical validation. The build integration test confirms that the wheel contains the packaged Stan models and the `nma-pool` CLI entry point, and that the release-manifest script writes both `SHA256SUMS.txt` and `release-manifest.json`. In the current release tree, the public GitHub repository and `v0.1.1` tag correspond to commit `d7b61ea98be6ee6ce11e61ed6b391a2675bf5c0a`, and the checked release manifest records the wheel and source distribution hashes for that commit. To keep those provenance files publicly inspectable within the manuscript package, the submission snapshot also includes copies at `f1000_artifacts/release-manifest-v0.1.1.json` and `f1000_artifacts/SHA256SUMS-v0.1.1.txt`. These engineering outputs are included because they make the manuscript evidence traceable; they are not by themselves evidence of broad inferential validity or external concordance.

### Reviewer-facing reproducibility path 1: manuscript-grade simulation reporting

A reviewer can reproduce the manuscript-oriented validation path by running the publication suite from the example configuration. The command writes a JSON artifact plus a human-readable summary that reports candidate/baseline model pairs, coverage, median absolute bias, mean log score, bootstrap intervals for paired log-score deltas, one-sided sign, permutation, and signed-rank tests, Monte Carlo standard errors, and gate pass/fail status. This is a synthetic validation workflow aimed at methods evaluation rather than a clinical case-study analysis.

### Reviewer-facing reproducibility path 2: mixed-design bias adjustment and sensitivity analysis

A second reviewer-facing use case is the bias-adjusted bundle path. Starting from the example paper-bundle configuration, the package executes a frequentist bias-adjusted model, a Bayesian bias-adjusted model, and a prior-sensitivity grid. The resulting manifest and executive summary make it possible to compare the estimated treatment effects, the size of the `nrs` bias term, the backend actually used, and the stability of estimates under alternative prior settings without manually stitching together outputs from separate scripts. This section is deliberately framed as a reproducibility path; it is not presented here as a standalone applied mixed-design evidence-synthesis case study.

## Discussion

Advanced NMA Pooling v0.1.1 is best understood as a reproducibility-oriented toolkit for advanced evidence-synthesis workflows. The package brings together aggregate-data network meta-analysis, ML-NMR-style AD+IPD integration, mixed-design bias adjustment, survival non-proportional hazards modeling, benchmarking, and manuscript-oriented validation under a common config-driven interface. The main contribution is operational integration: tests, simulation gates, paper bundles, and release manifests are treated as first-class outputs rather than afterthoughts.

That positioning matters because the relevant comparison set already includes mature open tools for standard aggregate-data synthesis, including interactive systems such as MetaInsight and programming toolchains such as `netmeta` and `multinma`. The contribution claimed here is narrower and more operational: a reproducibility-first command-line layer that allows one project to carry schema validation, multiple advanced workflow families, publication-suite gates, and release manifests together. The package should therefore be judged primarily on integration, traceability, and workflow reproducibility rather than on whether it supersedes every existing GUI-oriented network meta-analysis environment.

The current results support three narrower practical claims. First, the package has non-trivial engineering verification breadth, with 69 tests covering schemas, model behavior, simulation calibration, CLI execution, and build provenance. Second, the bundled publication suite produces favorable quantitative results within its two locked manuscript-facing reference scenarios. Third, the paper-bundle workflow can assemble multiple outputs and supporting documents into a manifest-based bundle suitable for internal review and manuscript preparation. These are appropriate software-tool claims because they are backed by concrete generated artifacts, but they remain narrower than a full empirical validation of every implemented workflow or a broad cross-software benchmarking study.

Several limitations should be stated clearly. First, the strongest quantitative evidence in the repository comes from simulation and bundled example workflows rather than a large library of committed real-world case studies. Second, the current manuscript does not report standalone quantitative case studies for ML-NMR or the external benchmark adapters, even though those modules are implemented in the package. Third, the continuous publication scenario is a locked low-heterogeneity regression check rather than a broad stress test across heterogeneous aggregate-data settings. Fourth, the ML-NMR workflow is currently limited to continuous outcomes. Fifth, the survival workflow uses interval-specific modeling with an interval-independence approximation noted in the project documentation. Sixth, external R benchmarks depend on optional local availability of `Rscript` and the relevant R packages; the benchmark framework handles unavailable adapters gracefully, but that is not the same as shipping committed external benchmark results for every release. Seventh, the exact generated artifacts and copied provenance files cited in this draft are publicly inspectable in the GitHub submission snapshot, but they have not yet been deposited in a DOI-backed archive. Eighth, Zenodo archival for the source and submission snapshot remains pending, so the archived-source DOI required for final journal submission is not yet available. Finally, this is a command-line toolkit rather than a graphical application; it prioritizes reproducibility and explicit configuration over point-and-click accessibility.

Overall, the project supports a defensible software-tool narrative centered on integration, traceability, and locked reproducibility workflows. Before external submission, the mandatory remaining step is DOI archiving for the frozen GitHub submission snapshot. Beyond that, any future manuscript seeking broader methodological claims would benefit from additional heterogeneity-positive scenarios, cross-software concordance checks, and more applied case studies.

## Software availability

- **Source code:** https://github.com/mahmood726-cyber/advanced-nma-pooling
- **Release analyzed in this article:** https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/v0.1.1
- **Public submission snapshot for this manuscript:** https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-15-r3
- **Exact generated result files used in this draft:** `artifacts/publication-suite.json`, `artifacts/publication-summary.md`, `artifacts/paper1-bundle/manifest.json`, `artifacts/paper1-bundle/paper1-executive-summary.md` in the submission snapshot above
- **Figure asset and caption package:** `f1000_artifacts/Figure_1_reproducibility_workflow.svg` and `f1000_artifacts/figure_captions.md`
- **Copied release provenance files in the submission snapshot:** `f1000_artifacts/release-manifest-v0.1.1.json` and `f1000_artifacts/SHA256SUMS-v0.1.1.txt`
- **DOI-backed archival of source and manuscript-result artifacts:** Zenodo deposition pending
- **License:** MIT

## Data availability

No new participant-level clinical data were generated for this software article. The repository includes example JSON configurations, synthetic study fixtures used in tests, simulation registries, manuscript-supporting documents, the aligned figure asset/caption package, copied release provenance files, and the exact generated result files named in the Software availability section through the public GitHub submission snapshot. Those outputs remain pending DOI-backed archival through Zenodo.

## Competing interests

No competing interests were disclosed.

## Grant information

The authors declared that no grants were involved in supporting this work.

## Acknowledgements

The authors thank the developers of the open statistical software and methods literature on which the package builds. The repository also includes optional R adapters for external benchmarking workflows.

## References

[1] Lu G, Ades AE. Combination of direct and indirect evidence in mixed treatment comparisons. Stat Med. 2004;23(20):3105-3124.

[2] Salanti G. Indirect and mixed-treatment comparison, network, or multiple-treatments meta-analysis: many names, many benefits, many concerns for the next generation evidence synthesis tool. Res Synth Methods. 2012;3(2):80-97.

[3] Phillippo DM, Ades AE, Dias S, Palmer S, Abrams KR, Welton NJ. Multilevel network meta-regression for population-adjusted treatment comparisons. J R Stat Soc Ser A Stat Soc. 2020;183(3):1189-1210.

[4] Gneiting T, Raftery AE. Strictly proper scoring rules, prediction, and estimation. J Am Stat Assoc. 2007;102(477):359-378.

[5] Holm S. A simple sequentially rejective multiple test procedure. Scand J Stat. 1979;6(2):65-70.

[6] Holford TR. The analysis of rates and of survivorship using log-linear models. Biometrics. 1980;36(2):299-305.

[7] Page MJ, McKenzie JE, Bossuyt PM, Boutron I, Hoffmann TC, Mulrow CD, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ. 2021;372:n71.
