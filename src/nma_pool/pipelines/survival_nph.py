"""Run piecewise-exponential non-PH survival NMA from config and emit JSON artifact."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.spec import SurvivalNPHSpec
from nma_pool.models.survival_nph import SurvivalNPHPooler
from nma_pool.pipelines._common import load_json_object, write_json_object


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to survival non-PH analysis config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/survival-nph-result.json"),
        help="Output artifact path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    analysis = payload["analysis"]
    data = payload["data"]

    spec = SurvivalNPHSpec(
        outcome_id=str(analysis["outcome_id"]),
        reference_treatment=str(analysis["reference_treatment"]),
        random_effects=parse_bool_value(
            analysis.get("random_effects", False),
            field_name="analysis.random_effects",
        ),
        continuity_correction=float(analysis.get("continuity_correction", 0.5)),
    )
    dataset = DatasetBuilder().from_payload(data)
    fit = SurvivalNPHPooler().fit(dataset, spec)

    artifact = {
        "analysis": {
            "outcome_id": spec.outcome_id,
            "reference_treatment": spec.reference_treatment,
            "random_effects": spec.random_effects,
            "continuity_correction": spec.continuity_correction,
        },
        "fit": {
            "interval_ids": list(fit.interval_ids),
            "interval_bounds": {
                interval_id: list(fit.interval_bounds[interval_id])
                for interval_id in fit.interval_ids
            },
            "treatment_effects_by_interval": fit.treatment_effects_by_interval,
            "treatment_ses_by_interval": fit.treatment_ses_by_interval,
            "estimable_by_interval": fit.estimable_by_interval,
            "pooled_treatment_effects": fit.pooled_treatment_effects,
            "pooled_treatment_ses": fit.pooled_treatment_ses,
            "tau": fit.tau,
            "n_studies": fit.n_studies,
            "n_contrasts": fit.n_contrasts,
            "warnings": list(fit.warnings),
        },
    }
    write_json_object(args.out, artifact)

    print(f"Wrote survival non-PH artifact: {args.out}")
    print(f"tau={fit.tau:.4f}")
    for interval_id in fit.interval_ids:
        bounds = fit.interval_bounds[interval_id]
        print(f"[{interval_id}] {bounds[0]:.2f}-{bounds[1]:.2f}")
        for treatment in sorted(fit.treatment_effects_by_interval[interval_id]):
            effect = fit.treatment_effects_by_interval[interval_id][treatment]
            se = fit.treatment_ses_by_interval[interval_id][treatment]
            print(f"  {treatment}: log-HR={effect:.4f}, se={se:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
