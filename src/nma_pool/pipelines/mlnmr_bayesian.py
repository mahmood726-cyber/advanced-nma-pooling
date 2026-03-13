"""Run Bayesian ML-NMR AD+IPD model and emit JSON artifact."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.bayesian_ml_nmr import BayesianMLNMRPooler
from nma_pool.models.spec import BayesianMLNMRSpec
from nma_pool.pipelines._common import load_json_object, write_json_object


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to Bayesian ML-NMR analysis config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/mlnmr-bayesian-result.json"),
        help="Output artifact path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    analysis = payload["analysis"]
    data = payload["data"]

    spec = BayesianMLNMRSpec(
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
        backend=str(analysis.get("backend", "analytic")),  # type: ignore[arg-type]
        prior_scale=float(analysis.get("prior_scale", 10.0)),
        n_draws=int(analysis.get("n_draws", 2000)),
        n_warmup=int(analysis.get("n_warmup", 1000)),
        n_chains=int(analysis.get("n_chains", 4)),
        seed=int(analysis.get("seed", 123)),
    )

    dataset = DatasetBuilder().from_payload(data)
    fit = BayesianMLNMRPooler().fit(dataset, spec)
    artifact = {
        "analysis": {
            "outcome_id": spec.outcome_id,
            "reference_treatment": spec.reference_treatment,
            "covariate_name": spec.covariate_name,
            "integration_mode": spec.integration_mode,
            "backend": spec.backend,
            "prior_scale": spec.prior_scale,
            "n_draws": spec.n_draws,
            "n_warmup": spec.n_warmup,
            "n_chains": spec.n_chains,
            "seed": spec.seed,
        },
        "fit": {
            "backend_used": fit.backend_used,
            "treatment_effects_vs_reference": fit.treatment_effects,
            "treatment_ses_vs_reference": fit.treatment_ses,
            "interaction_effects_vs_reference": fit.interaction_effects,
            "interaction_ses_vs_reference": fit.interaction_ses,
            "beta_main": fit.beta_main,
            "beta_main_se": fit.beta_main_se,
            "n_studies": fit.n_studies,
            "n_contrasts": fit.n_contrasts,
            "n_ipd_rows": fit.n_ipd_rows,
            "n_draws": fit.n_draws,
            "warnings": list(fit.warnings),
        },
    }
    write_json_object(args.out, artifact)

    print(f"Wrote Bayesian ML-NMR artifact: {args.out}")
    print(f"backend_used={fit.backend_used}")
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
