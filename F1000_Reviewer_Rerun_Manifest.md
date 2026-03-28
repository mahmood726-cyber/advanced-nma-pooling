# Advanced NMA Pooling: reviewer rerun manifest

This manifest is the shortest reviewer-facing rerun path for the local software package. It lists the files that should be sufficient to recreate one worked example, inspect saved outputs, and verify that the manuscript claims remain bounded to what the repository actually demonstrates.

## Reviewer Entry Points
- Project directory: `C:\Models\advanced-nma-pooling`.
- Preferred documentation start points: `README.md`, `external/r/README.md`, `f1000_artifacts/tutorial_walkthrough.md`.
- Detected public repository root: `https://github.com/mahmood726-cyber/advanced-nma-pooling`.
- Detected public source snapshot: `https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-15-r3`.
- Detected public archive record: No project-specific DOI or Zenodo record URL was detected locally; archive registration pending.
- Environment capture files: `requirements.txt`.
- Validation/test artifacts: `f1000_artifacts/validation_summary.md`, `tests/__init__.py`, `tests/integration/test_benchmark.py`, `tests/integration/test_bias_sensitivity_pipeline.py`, `tests/integration/test_build_artifacts.py`, `tests/integration/test_cli.py`, `tests/integration/test_paper1_bundle_pipeline.py`, `tests/integration/test_publication_pipeline.py`.

## Worked Example Inputs
- Manuscript-named example paths: `configs/` example payloads for every CLI workflow; `artifacts/paper1-bundle/` for a reproducible manuscript-support bundle; `f1000_artifacts/tutorial_walkthrough.md` for a reviewer rerun path; configs/example-analysis.json; configs/example-benchmark.json; configs/example-bias-adjusted-bayesian.json.
- Auto-detected sample/example files: `configs/example-analysis.json`, `configs/example-benchmark.json`, `configs/example-bias-adjusted-bayesian.json`, `configs/example-bias-adjusted.json`, `configs/example-bias-sensitivity.json`, `configs/example-mlnmr.json`.

## Expected Outputs To Inspect
- Structured model-card JSON outputs for analysis runs.
- Benchmark summaries comparing internal and optional external backends.
- Publication summaries and copied artifacts intended for reviewer audit.

## Minimal Reviewer Rerun Sequence
- Start with the README/tutorial files listed below and keep the manuscript paths synchronized with the public archive.
- Create the local runtime from the detected environment capture files if available: `requirements.txt`.
- Run at least one named example path from the manuscript and confirm that the generated outputs match the saved validation materials.
- Quote one concrete numeric result from the local validation snippets below when preparing the final software paper.

## Local Numeric Evidence Available
- `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.
- `artifacts/publication-summary.md` reports git_commit: 694a31770a8e4e51d4ceab43a77d12aaad8795ea.
- `artifacts/publication-summary.review.md` reports created_at_utc: 2026-02-28T20:16:33.285622+00:00.
