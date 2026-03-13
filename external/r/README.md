# External R Benchmark Runners

These scripts implement external benchmark adapters for:

- `netmeta` (`netmeta_runner.R`)
- `multinma` (`multinma_runner.R`)

They are invoked by `pipelines/run_benchmark.py` through
`ExternalCommandAdapter`.

## Requirements

1. Install R and ensure `Rscript` is on `PATH`.
2. Install required packages:

```r
install.packages(c("jsonlite", "meta", "netmeta", "multinma"))
```

## Command Contract

Each script is called with:

```text
--input <input.json> --output <output.json>
```

Input JSON contains:

- `analysis`
- `data`
- `requested_contrasts`

Output JSON must contain:

- `treatment_effects` (named object of numeric values)
- `treatment_ses` (named object of numeric values)
- `contrasts` (named object with `{effect, se}` per requested contrast)
- `diagnostics` with:
  - `pass` (`true`/`false`)
  - `issues` (list of strings)
  - `warnings` (list of strings)

## Notes

- `multinma_runner.R` enforces MCMC diagnostics (Rhat/ESS/divergences).
- If a requested random-effects fit fails diagnostics, it automatically retries
  a fixed-effects model and records this in output diagnostics.
