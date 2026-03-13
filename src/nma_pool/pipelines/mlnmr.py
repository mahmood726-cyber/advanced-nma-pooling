"""Run initial ML-NMR AD+IPD model from config and emit JSON artifact."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.ml_nmr import MLNMRPooler
from nma_pool.models.spec import MLNMRSpec
from nma_pool.pipelines._common import load_json_object, write_json_object


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to ML-NMR analysis config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/mlnmr-result.json"),
        help="Output ML-NMR artifact path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    analysis = payload["analysis"]
    data = payload["data"]

    spec = MLNMRSpec(
        outcome_id=str(analysis["outcome_id"]),
        reference_treatment=str(analysis["reference_treatment"]),
        covariate_name=str(analysis["covariate_name"]),
        measure_type="continuous",
        integration_mode=str(analysis.get("integration_mode", "empirical")),  # type: ignore[arg-type]
        random_effects=parse_bool_value(
            analysis.get("random_effects", False),
            field_name="analysis.random_effects",
        ),
        mc_samples=int(analysis.get("mc_samples", 2000)),
        mc_seed=int(analysis.get("mc_seed", 123)),
    )
    dataset = DatasetBuilder().from_payload(data)
    fit = MLNMRPooler().fit(dataset, spec)

    artifact = {
        "analysis": {
            "outcome_id": spec.outcome_id,
            "reference_treatment": spec.reference_treatment,
            "covariate_name": spec.covariate_name,
            "integration_mode": spec.integration_mode,
            "random_effects": spec.random_effects,
            "mc_samples": spec.mc_samples,
            "mc_seed": spec.mc_seed,
        },
        "fit": {
            "treatment_effects_vs_reference": fit.treatment_effects,
            "treatment_ses_vs_reference": fit.treatment_ses,
            "interaction_effects_vs_reference": fit.interaction_effects,
            "interaction_ses_vs_reference": fit.interaction_ses,
            "beta_main": fit.beta_main,
            "beta_main_se": fit.beta_main_se,
            "n_studies": fit.n_studies,
            "n_contrasts": fit.n_contrasts,
            "n_ipd_rows": fit.n_ipd_rows,
            "warnings": list(fit.warnings),
        },
    }
    write_json_object(args.out, artifact)

    print(f"Wrote ML-NMR artifact: {args.out}")
    for treatment in sorted(fit.treatment_effects):
        d = fit.treatment_effects[treatment]
        g = fit.interaction_effects[treatment]
        print(f"{treatment}: d={d:.4f}, g={g:.4f}")
    print(f"beta_main={fit.beta_main:.4f}")
    if "B" in fit.treatment_effects and "C" in fit.treatment_effects:
        diff, se = fit.contrast("C", "B", covariate_value=0.0)
        print(f"C_vs_B at covariate=0: effect={diff:.4f}, se={se:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
