"""Run design-stratified bias-adjusted NMA and emit JSON artifact."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.bias_adjusted import BiasAdjustedNMAPooler
from nma_pool.models.spec import BiasAdjustedSpec
from nma_pool.pipelines._common import load_json_object, write_json_object


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to bias-adjusted analysis config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/bias-adjusted-result.json"),
        help="Output artifact path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    analysis = payload["analysis"]
    data = payload["data"]

    spec = BiasAdjustedSpec(
        outcome_id=str(analysis["outcome_id"]),
        measure_type=str(analysis["measure_type"]),  # type: ignore[arg-type]
        reference_treatment=str(analysis["reference_treatment"]),
        random_effects=parse_bool_value(
            analysis.get("random_effects", True),
            field_name="analysis.random_effects",
        ),
        reference_design=str(analysis.get("reference_design", "rct")),  # type: ignore[arg-type]
        bias_prior_sd=float(analysis.get("bias_prior_sd", 1.0)),
    )
    dataset = DatasetBuilder().from_payload(data)
    fit = BiasAdjustedNMAPooler().fit(dataset, spec)

    artifact = {
        "analysis": {
            "outcome_id": spec.outcome_id,
            "measure_type": spec.measure_type,
            "reference_treatment": spec.reference_treatment,
            "random_effects": spec.random_effects,
            "reference_design": spec.reference_design,
            "bias_prior_sd": spec.bias_prior_sd,
        },
        "fit": {
            "tau": fit.tau,
            "treatment_effects_vs_reference": fit.treatment_effects,
            "treatment_ses_vs_reference": fit.treatment_ses,
            "design_bias_effects_vs_reference_design": fit.design_bias_effects,
            "design_bias_ses_vs_reference_design": fit.design_bias_ses,
            "n_studies": fit.n_studies,
            "n_contrasts": fit.n_contrasts,
            "warnings": list(fit.warnings),
        },
    }
    write_json_object(args.out, artifact)

    print(f"Wrote bias-adjusted artifact: {args.out}")
    print(f"tau={fit.tau:.4f}")
    print("Treatment effects (reference design):")
    for treatment in sorted(fit.treatment_effects):
        effect = fit.treatment_effects[treatment]
        se = fit.treatment_ses[treatment]
        print(f"  {treatment}: effect={effect:.4f}, se={se:.4f}")
    print("Design bias effects:")
    for design in sorted(fit.design_bias_effects):
        effect = fit.design_bias_effects[design]
        se = fit.design_bias_ses[design]
        print(f"  {design}: bias={effect:.4f}, se={se:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
