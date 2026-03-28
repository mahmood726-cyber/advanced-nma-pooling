# Advanced NMA Pooling: concrete submission fixes

This file converts the multi-persona review into repository-side actions that should be checked before external submission of the F1000 software paper for `advanced-nma-pooling`.

## Detectable Local State
- Documentation files detected: `README.md`, `external/r/README.md`, `f1000_artifacts/tutorial_walkthrough.md`.
- Environment lock or container files detected: `requirements.txt`.
- Package manifests detected: `pyproject.toml`.
- Example data files detected: `configs/example-analysis.json`, `configs/example-benchmark.json`, `configs/example-bias-adjusted-bayesian.json`, `configs/example-bias-adjusted.json`, `configs/example-bias-sensitivity.json`, `configs/example-mlnmr.json`.
- Validation artifacts detected: `f1000_artifacts/validation_summary.md`, `tests/__init__.py`, `tests/integration/test_benchmark.py`, `tests/integration/test_bias_sensitivity_pipeline.py`, `tests/integration/test_build_artifacts.py`, `tests/integration/test_cli.py`, `tests/integration/test_paper1_bundle_pipeline.py`, `tests/integration/test_publication_pipeline.py`.
- Detected public repository root: `https://github.com/mahmood726-cyber/advanced-nma-pooling`.
- Detected public source snapshot: `https://github.com/mahmood726-cyber/advanced-nma-pooling/tree/f1000-submission-2026-03-15-r3`.
- Detected public archive record: No project-specific DOI or Zenodo record URL was detected locally; archive registration pending.

## High-Priority Fixes
- Check that the manuscript's named example paths exist in the public archive and can be run without repository archaeology.
- Confirm that the cited repository root (`https://github.com/mahmood726-cyber/advanced-nma-pooling`) resolves to the same tagged release used for submission.
- Archive the tagged release and insert the Zenodo DOI or record URL once it has been minted; no project-specific archive DOI was detected locally.
- Reconfirm the quoted benchmark or validation sentence after the final rerun so the narrative text matches the shipped artifacts.

## Numeric Evidence Available To Quote
- `f1000_artifacts/validation_summary.md` reports These generated artifacts are intended to be exposed in the public GitHub submission snapshot f1000-submission-2026-03-15-r3; DOI-backed archival is still pending and remains a pre-submission blocker for external journal submission.
- `artifacts/publication-summary.md` reports git_commit: 694a31770a8e4e51d4ceab43a77d12aaad8795ea.
- `artifacts/publication-summary.review.md` reports created_at_utc: 2026-02-28T20:16:33.285622+00:00.

## Manuscript Files To Keep In Sync
- `F1000_Software_Tool_Article.md`
- `F1000_Reviewer_Rerun_Manifest.md`
- `F1000_MultiPersona_Review.md`
- `F1000_Submission_Checklist_RealReview.md` where present
- README/tutorial files and the public repository release metadata
