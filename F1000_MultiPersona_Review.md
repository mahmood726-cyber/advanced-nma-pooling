# Advanced NMA Pooling: multi-persona peer review

This memo applies the recurring concerns in the supplied peer-review document to the current F1000 draft for this project (`advanced-nma-pooling`). It distinguishes changes already made in the draft from repository-side items that still need to hold in the released repository and manuscript bundle.

## Detected Local Evidence
- Detected documentation files: `README.md`, `external/r/README.md`, `f1000_artifacts/tutorial_walkthrough.md`.
- Detected environment capture or packaging files: `requirements.txt`.
- Detected validation/test artifacts: `f1000_artifacts/validation_summary.md`, `tests/__init__.py`, `tests/integration/test_benchmark.py`, `tests/integration/test_bias_sensitivity_pipeline.py`, `tests/integration/test_build_artifacts.py`, `tests/integration/test_cli.py`, `tests/integration/test_paper1_bundle_pipeline.py`, `tests/integration/test_publication_pipeline.py`.
- Detected browser deliverables: no HTML file detected.
- Detected public repository root: `https://github.com/mahmood726-cyber/advanced-nma-pooling`.
- Detected public source snapshot: `https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-15-r3`.
- Detected public archive record: No project-specific DOI or Zenodo record URL was detected locally; archive registration pending.

## Reviewer Rerun Companion
- `F1000_Reviewer_Rerun_Manifest.md` consolidates the shortest reviewer-facing rerun path, named example files, environment capture, and validation checkpoints.

## Detected Quantitative Evidence
- `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.
- `artifacts/publication-summary.md` reports git_commit: 694a31770a8e4e51d4ceab43a77d12aaad8795ea.
- `artifacts/publication-summary.review.md` reports created_at_utc: 2026-02-28T20:16:33.285622+00:00.

## Current Draft Strengths
- States the project rationale and niche explicitly: Complex network meta-analysis workflows are often split across ad hoc scripts for data validation, mixed aggregate-data and IPD integration, bias adjustment, survival modelling, benchmarking, and publication packaging. That fragmentation makes software peer review difficult because reviewers need to reconstruct which configuration produced which result.
- Names concrete worked-example paths: `configs/` example payloads for every CLI workflow; `artifacts/paper1-bundle/` for a reproducible manuscript-support bundle; `f1000_artifacts/tutorial_walkthrough.md` for a reviewer rerun path.
- Points reviewers to local validation materials: `tests/unit/`, `tests/integration/`, and `tests/simulation/` cover core estimators and publication workflows; `artifacts/publication-summary.md` and `artifacts/publication-suite.json` record package-level validation outputs; `scripts/release_manifest.py` and release metadata document provenance and checksums.
- Moderates conclusions and lists explicit limitations for Advanced NMA Pooling.

## Remaining High-Priority Fixes
- Keep one minimal worked example public and ensure the manuscript paths match the released files.
- Ensure README/tutorial text, software availability metadata, and public runtime instructions stay synchronized with the manuscript.
- Confirm that the cited repository root resolves to the same tagged release used for the submission package.
- Mint and cite a Zenodo DOI or record URL for the tagged release; none was detected locally.
- Reconfirm the quoted benchmark or validation sentence after the final rerun so the narrative text stays synchronized with the shipped artifacts.

## Persona Reviews

### Reproducibility Auditor
- Review question: Looks for a frozen computational environment, a fixed example input, and an end-to-end rerun path with saved outputs.
- What the revised draft now provides: The revised draft names concrete rerun assets such as `configs/` example payloads for every CLI workflow; `artifacts/paper1-bundle/` for a reproducible manuscript-support bundle and ties them to validation files such as `tests/unit/`, `tests/integration/`, and `tests/simulation/` cover core estimators and publication workflows; `artifacts/publication-summary.md` and `artifacts/publication-suite.json` record package-level validation outputs.
- What still needs confirmation before submission: Before submission, freeze the public runtime with `requirements.txt` and keep at least one minimal example input accessible in the external archive.

### Validation and Benchmarking Statistician
- Review question: Checks whether the paper shows evidence that outputs are accurate, reproducible, and compared against known references or stress tests.
- What the revised draft now provides: The manuscript now cites concrete validation evidence including `tests/unit/`, `tests/integration/`, and `tests/simulation/` cover core estimators and publication workflows; `artifacts/publication-summary.md` and `artifacts/publication-suite.json` record package-level validation outputs; `scripts/release_manifest.py` and release metadata document provenance and checksums and frames conclusions as being supported by those materials rather than by interface availability alone.
- What still needs confirmation before submission: Concrete numeric evidence detected locally is now available for quotation: `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission; `artifacts/publication-summary.md` reports git_commit: 694a31770a8e4e51d4ceab43a77d12aaad8795ea.

### Methods-Rigor Reviewer
- Review question: Examines modeling assumptions, scope conditions, and whether method-specific caveats are stated instead of implied.
- What the revised draft now provides: The architecture and discussion sections now state the method scope explicitly and keep caveats visible through limitations such as The confirmatory publication suite remains narrower than a full methods-validation study and should be described as such; The mixed-design example is still synthetic rather than a full clinical case study.
- What still needs confirmation before submission: Retain method-specific caveats in the final Results and Discussion and avoid collapsing exploratory thresholds or heuristics into universal recommendations.

### Comparator and Positioning Reviewer
- Review question: Asks what gap the tool fills relative to existing software and whether the manuscript avoids unsupported superiority claims.
- What the revised draft now provides: The introduction now positions the software against an explicit comparator class: The manuscript therefore positions the toolkit alongside, rather than above, established options such as MetaInsight, `netmeta`, `multinma`, and bespoke Stan workflows. Its main differentiator is operational reproducibility: fixed configuration schemas, packaged example pipelines, and publication-facing provenance.
- What still needs confirmation before submission: Keep the comparator discussion citation-backed in the final submission and avoid phrasing that implies blanket superiority over better-established tools.

### Documentation and Usability Reviewer
- Review question: Looks for a README, tutorial, worked example, input-schema clarity, and short interpretation guidance for outputs.
- What the revised draft now provides: The revised draft points readers to concrete walkthrough materials such as `configs/` example payloads for every CLI workflow; `artifacts/paper1-bundle/` for a reproducible manuscript-support bundle; `f1000_artifacts/tutorial_walkthrough.md` for a reviewer rerun path and spells out expected outputs in the Methods section.
- What still needs confirmation before submission: Make sure the public archive exposes a readable README/tutorial bundle: currently detected files include `README.md`, `external/r/README.md`, `f1000_artifacts/tutorial_walkthrough.md`.

### Software Engineering Hygiene Reviewer
- Review question: Checks for evidence of testing, deployment hygiene, browser/runtime verification, secret handling, and removal of obvious development leftovers.
- What the revised draft now provides: The draft now foregrounds regression and validation evidence via `f1000_artifacts/validation_summary.md`, `tests/__init__.py`, `tests/integration/test_benchmark.py`, `tests/integration/test_bias_sensitivity_pipeline.py`, `tests/integration/test_build_artifacts.py`, `tests/integration/test_cli.py`, `tests/integration/test_paper1_bundle_pipeline.py`, `tests/integration/test_publication_pipeline.py`, and browser-facing projects are described as self-validating where applicable.
- What still needs confirmation before submission: Before submission, remove any dead links, exposed secrets, or development-stage text from the public repo and ensure the runtime path described in the manuscript matches the shipped code.

### Claims-and-Limitations Editor
- Review question: Verifies that conclusions are bounded to what the repository actually demonstrates and that limitations are explicit.
- What the revised draft now provides: The abstract and discussion now moderate claims and pair them with explicit limitations, including The confirmatory publication suite remains narrower than a full methods-validation study and should be described as such; The mixed-design example is still synthetic rather than a full clinical case study; Public repository release and DOI archival remain necessary for a fully citable external release.
- What still needs confirmation before submission: Keep the conclusion tied to documented functions and artifacts only; avoid adding impact claims that are not directly backed by validation, benchmarking, or user-study evidence.

### F1000 and Editorial Compliance Reviewer
- Review question: Checks for manuscript completeness, software/data availability clarity, references, and reviewer-facing support files.
- What the revised draft now provides: The revised draft is more complete structurally and now points reviewers to software availability, data availability, and reviewer-facing support files.
- What still needs confirmation before submission: Confirm repository/archive metadata, figure/export requirements, and supporting-file synchronization before release.
