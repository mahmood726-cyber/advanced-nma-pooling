# Advanced NMA Pooling

`nma-pool` is a Python toolkit for advanced evidence-synthesis workflows in
network meta-analysis. The package includes aggregate-data NMA, ML-NMR-style
AD+IPD integration, design-stratified bias adjustment, Bayesian analytic and
Stan backends, survival non-proportional-hazards modeling, and
publication-grade validation pipelines.

## Status

- Package status: alpha, research-oriented
- Python support: 3.11+
- License: MIT

## What Is Included

- `nma_pool.data`: strict schema validation and dataset construction
- `nma_pool.models`: frequentist and Bayesian NMA/ML-NMR/bias-adjusted/survival fitters
- `nma_pool.inference`: config-driven model execution
- `nma_pool.validation`: diagnostics, benchmarks, simulation studies, and publication gates
- `nma_pool.reporting`: model-card JSON output helpers
- `nma_pool.pipelines`: installable workflow entrypoints for all example pipelines
- `external/r/`: optional `netmeta` and `multinma` benchmark adapters

The built wheel bundles the packaged Stan models used by the Bayesian ML-NMR
and Bayesian bias-adjusted workflows.

## Installation

Standard install:

```bash
python -m pip install .
```

Development install:

```bash
python -m pip install -e ".[dev]"
```

Install with the optional Stan backend:

```bash
python -m pip install -e ".[dev,stan]"
```

Build and validate release artifacts locally:

```bash
python scripts/build_release_artifacts.py --outdir dist
python -m twine check dist/*
```

## Installed CLI

The package installs a primary `nma-pool` command with workflow subcommands:

```bash
nma-pool analysis --config configs/example-analysis.json --out artifacts/model-card.json
nma-pool benchmark --config configs/example-benchmark.json --out artifacts/benchmark-results.json
nma-pool bias-adjusted --config configs/example-bias-adjusted.json --out artifacts/bias-adjusted-result.json
nma-pool bias-adjusted-bayesian --config configs/example-bias-adjusted-bayesian.json --out artifacts/bias-adjusted-bayesian-result.json
nma-pool bias-sensitivity --config configs/example-bias-sensitivity.json --out artifacts/bias-sensitivity-result.json
nma-pool mlnmr --config configs/example-mlnmr.json --out artifacts/mlnmr-result.json
nma-pool mlnmr-bayesian --config configs/example-mlnmr.json --out artifacts/mlnmr-bayesian-result.json
nma-pool survival-nph --config configs/example-survival-nph.json --out artifacts/survival-nph-result.json
nma-pool publication-suite --config configs/example-publication-suite.json --out artifacts/publication-suite.json --summary artifacts/publication-summary.md
nma-pool paper1-bundle --config configs/example-paper1-bundle.json --out-dir artifacts/paper1-bundle
```

Run `nma-pool --help` to list the supported workflow subcommands.

## Release Governance

Release governance is tag-driven and documented in `RELEASE.md`.

- Local release artifacts can be fingerprinted with `python scripts/release_manifest.py --version 0.1.1`.
- GitHub releases are built from annotated `v*` tags by `.github/workflows/release.yml`.
- The release workflow runs tests, builds the wheel and sdist, emits `SHA256SUMS.txt` and `release-manifest.json`, and generates a GitHub artifact attestation for provenance.

## Source-Tree Wrappers

The repo-root `pipelines/run_*.py` scripts remain available for local source
execution and now delegate to the same packaged modules used by the installed
CLI. That keeps source-tree and installed behavior aligned.

## Quick Start

Run the test suite and one representative analysis:

```bash
pytest
nma-pool analysis --config configs/example-analysis.json --out artifacts/model-card.json
```

Build the example paper bundle:

```bash
nma-pool paper1-bundle --config configs/example-paper1-bundle.json --out-dir artifacts/paper1-bundle-publish-check
```

That example bundle was previously verified locally and produced
`overall_pass: True` in the publication summary for the bundled example
configuration.

## Example Outputs

- `artifacts/model-card.json`: core AD NMA model card
- `artifacts/benchmark-results.json`: adapter comparison and scoring summary
- `artifacts/publication-suite.json`: simulation-based publication readiness results
- `artifacts/publication-summary.md`: human-readable gate summary
- `artifacts/paper1-bundle/`: reproducible paper bundle with manifest and copied docs

## Configuration Notes

- Boolean config fields are parsed strictly. Use real booleans or standard forms such as `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`.
- Integer schema fields such as study year, arm size, and survival event counts reject non-integer numerics.
- YAML configs are supported by the config loader only when `pyyaml` is installed. JSON examples are included in `configs/`.

## External Benchmarks

`configs/example-benchmark.json` includes optional external adapters for:

- `Rscript external/r/netmeta_runner.R`
- `Rscript external/r/multinma_runner.R`

If `Rscript` or the required R packages are unavailable, those adapters are
reported as `unavailable` without breaking the internal benchmark suite.

## Project Layout

- `src/nma_pool/`: installable package
- `configs/`: runnable example payloads
- `tests/`: unit, integration, and simulation tests
- `docs/`: technical spec and manuscript-supporting material
- `artifacts/`: generated outputs from example runs

Primary design docs:

- `docs/specs/technical-spec-v1.md`
- `docs/specs/milestone-tickets-v1.md`
