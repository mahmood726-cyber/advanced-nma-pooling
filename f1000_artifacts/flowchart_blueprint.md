# Flowchart Blueprint

Updated: 2026-03-14
Project: advanced-nma-pooling

## Figure FA1 structure

Config and schema validation -> workflow selection -> model execution -> predictive diagnostics or bias/sensitivity evaluation -> manuscript-facing summaries and manifests -> release provenance

## Evidence links

- Publication validation summary: `f1000_artifacts/validation_summary.md`
- Reviewer walkthrough: `f1000_artifacts/tutorial_walkthrough.md`
- Publication-suite outputs: `artifacts/publication-suite.json`, `artifacts/publication-summary.md`
- Paper-bundle outputs: `artifacts/paper1-bundle/manifest.json`, `artifacts/paper1-bundle/paper1-executive-summary.md`

## Design notes

- Use method-centric labels rather than package-internal jargon where possible.
- Distinguish statistical validation outputs from packaging/provenance outputs in the figure layout.
- Keep the flow centered on reproducibility checkpoints instead of a generic software pipeline diagram.
