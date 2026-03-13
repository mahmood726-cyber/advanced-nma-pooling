"""Run prior sensitivity scenarios for Bayesian bias-adjusted NMA."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import itertools
from pathlib import Path
from typing import Any

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.bayesian_bias_adjusted import BayesianBiasAdjustedNMAPooler
from nma_pool.models.spec import BayesianBiasAdjustedSpec
from nma_pool.pipelines._common import load_json_object, write_json_object


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to bias sensitivity config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/bias-sensitivity-result.json"),
        help="Output artifact path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    analysis = payload["analysis"]
    data = payload["data"]
    sensitivity = payload.get("sensitivity", {})

    bias_grid = _coerce_float_grid(sensitivity.get("bias_prior_sd_grid", [0.3, 0.6, 1.0, 2.0]))
    trt_grid = _coerce_float_grid(
        sensitivity.get("treatment_prior_sd_grid", [2.0, 5.0, 10.0])
    )
    seeds = _coerce_int_grid(sensitivity.get("seed_grid", [11, 29]))
    backend = str(sensitivity.get("backend", analysis.get("backend", "analytic")))
    n_draws = int(sensitivity.get("n_draws", analysis.get("n_draws", 1200)))
    n_warmup = int(sensitivity.get("n_warmup", analysis.get("n_warmup", 500)))
    n_chains = int(sensitivity.get("n_chains", analysis.get("n_chains", 2)))
    random_effects = parse_bool_value(
        analysis.get("random_effects", True),
        field_name="analysis.random_effects",
    )

    dataset = DatasetBuilder().from_payload(data)
    pooler = BayesianBiasAdjustedNMAPooler()
    scenarios: list[dict[str, Any]] = []

    for bias_prior_sd, treatment_prior_sd, seed in itertools.product(bias_grid, trt_grid, seeds):
        spec = BayesianBiasAdjustedSpec(
            outcome_id=str(analysis["outcome_id"]),
            measure_type=str(analysis["measure_type"]),  # type: ignore[arg-type]
            reference_treatment=str(analysis["reference_treatment"]),
            random_effects=random_effects,
            reference_design=str(analysis.get("reference_design", "rct")),  # type: ignore[arg-type]
            bias_prior_sd=float(bias_prior_sd),
            backend=backend,  # type: ignore[arg-type]
            treatment_prior_sd=float(treatment_prior_sd),
            n_draws=n_draws,
            n_warmup=n_warmup,
            n_chains=n_chains,
            seed=int(seed),
        )
        fit = pooler.fit(dataset, spec)
        scenarios.append(
            {
                "bias_prior_sd": spec.bias_prior_sd,
                "treatment_prior_sd": spec.treatment_prior_sd,
                "seed": spec.seed,
                "backend_requested": spec.backend,
                "backend_used": fit.backend_used,
                "tau": fit.tau,
                "treatment_effects_vs_reference": fit.treatment_effects,
                "design_bias_effects_vs_reference_design": fit.design_bias_effects,
                "n_draws": fit.n_draws,
                "warnings": list(fit.warnings),
            }
        )

    summary = _summarize_scenarios(
        scenarios=scenarios,
        reference_design=str(analysis.get("reference_design", "rct")),
    )
    artifact = {
        "analysis": {
            "outcome_id": str(analysis["outcome_id"]),
            "measure_type": str(analysis["measure_type"]),
            "reference_treatment": str(analysis["reference_treatment"]),
            "random_effects": random_effects,
            "reference_design": str(analysis.get("reference_design", "rct")),
        },
        "sensitivity": {
            "backend": backend,
            "bias_prior_sd_grid": bias_grid,
            "treatment_prior_sd_grid": trt_grid,
            "seed_grid": seeds,
            "n_draws": n_draws,
            "n_warmup": n_warmup,
            "n_chains": n_chains,
        },
        "summary": summary,
        "scenarios": scenarios,
    }
    write_json_object(args.out, artifact)

    print(f"Wrote bias sensitivity artifact: {args.out}")
    print(f"scenario_count={len(scenarios)}")
    for treatment, stats in sorted(summary.get("treatment_effect_ranges", {}).items()):
        print(
            f"{treatment}: min={stats['min']:.4f}, max={stats['max']:.4f}, "
            f"span={stats['span']:.4f}"
        )
    for design, stats in sorted(summary.get("design_bias_ranges", {}).items()):
        print(
            f"{design}: min={stats['min']:.4f}, max={stats['max']:.4f}, "
            f"span={stats['span']:.4f}"
        )
    return 0


def _summarize_scenarios(*, scenarios: list[dict[str, Any]], reference_design: str) -> dict[str, Any]:
    treatment_values: dict[str, list[float]] = {}
    design_values: dict[str, list[float]] = {}
    for row in scenarios:
        for treatment, value in row["treatment_effects_vs_reference"].items():
            treatment_values.setdefault(str(treatment), []).append(float(value))
        for design, value in row["design_bias_effects_vs_reference_design"].items():
            if design == reference_design:
                continue
            design_values.setdefault(str(design), []).append(float(value))
    return {
        "treatment_effect_ranges": {
            key: _range_payload(values)
            for key, values in sorted(treatment_values.items())
        },
        "design_bias_ranges": {
            key: _range_payload(values)
            for key, values in sorted(design_values.items())
        },
    }


def _range_payload(values: list[float]) -> dict[str, float]:
    lo = min(values)
    hi = max(values)
    return {"min": lo, "max": hi, "span": hi - lo}


def _coerce_float_grid(raw: Any) -> list[float]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("Sensitivity grids must be non-empty lists.")
    values = [float(item) for item in raw]
    if any(value <= 0 for value in values):
        raise ValueError("Sensitivity grid values must be > 0.")
    return values


def _coerce_int_grid(raw: Any) -> list[int]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("seed_grid must be a non-empty list.")
    return [int(item) for item in raw]


if __name__ == "__main__":
    raise SystemExit(main())
