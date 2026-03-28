from __future__ import annotations

import pytest

from nma_pool.data.builder import DatasetBuilder
from nma_pool.data.schemas import ValidationError
from nma_pool.models.ml_nmr import MLNMRPooler
from nma_pool.models.spec import MLNMRSpec
from tests.fixtures.mlnmr_payload import build_mlnmr_payload


def test_mlnmr_recovers_treatment_and_interaction_effects() -> None:
    dataset = DatasetBuilder().from_payload(build_mlnmr_payload())
    fit = MLNMRPooler().fit(
        dataset,
        MLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            integration_mode="empirical",
        ),
    )
    assert abs(fit.treatment_effects["B"] - 1.0) < 0.08
    assert abs(fit.treatment_effects["C"] - 2.0) < 0.08
    assert abs(fit.interaction_effects["B"] - 0.4) < 0.08
    assert abs(fit.interaction_effects["C"] - 0.9) < 0.08
    assert abs(fit.beta_main - 0.3) < 0.08
    effect_cb, se_cb = fit.contrast("C", "B", covariate_value=0.0)
    assert abs(effect_cb - 1.0) < 0.08
    assert se_cb > 0


def test_mlnmr_normal_mc_mode_runs() -> None:
    dataset = DatasetBuilder().from_payload(build_mlnmr_payload())
    fit = MLNMRPooler().fit(
        dataset,
        MLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            integration_mode="normal_mc",
            mc_samples=500,
            mc_seed=7,
        ),
    )
    assert fit.n_contrasts >= 5
    assert "B" in fit.treatment_effects
    assert "C" in fit.treatment_effects


def test_mlnmr_counts_only_ipd_rows_that_reach_the_fitted_design() -> None:
    payload = build_mlnmr_payload()
    payload["studies"].append(
        {
            "study_id": "IP5",
            "design": "rct",
            "year": 2024,
            "source_id": "ip5",
            "rob_domain_summary": "low",
        }
    )
    payload["arms"].extend(
        [
            {"study_id": "IP5", "arm_id": "E1", "treatment_id": "A", "n": 2},
            {"study_id": "IP5", "arm_id": "E2", "treatment_id": "B", "n": 2},
        ]
    )
    payload["ipd"].extend(
        [
            {
                "study_id": "IP5",
                "patient_id": "q1",
                "arm_id": "E1",
                "treatment_id": "A",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 0.1,
                "covariates": {"x": 0.0},
            },
            {
                "study_id": "IP5",
                "patient_id": "q2",
                "arm_id": "E1",
                "treatment_id": "A",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 0.2,
                "covariates": {"x": 0.2},
            },
            {
                "study_id": "IP5",
                "patient_id": "q3",
                "arm_id": "E2",
                "treatment_id": "B",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 1.1,
                "covariates": {},
            },
            {
                "study_id": "IP5",
                "patient_id": "q4",
                "arm_id": "E2",
                "treatment_id": "B",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 1.2,
                "covariates": {},
            },
        ]
    )

    fit = MLNMRPooler().fit(
        DatasetBuilder().from_payload(payload),
        MLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            integration_mode="empirical",
        ),
    )
    assert fit.n_ipd_rows == 8


def test_mlnmr_rejects_disconnected_network() -> None:
    payload = {
        "studies": [
            {"study_id": "AD1", "design": "rct", "year": 2024, "source_id": "ad1", "rob_domain_summary": "low"},
            {"study_id": "AD2", "design": "rct", "year": 2024, "source_id": "ad2", "rob_domain_summary": "low"},
        ],
        "arms": [
            {"study_id": "AD1", "arm_id": "A1", "treatment_id": "A", "n": 120},
            {"study_id": "AD1", "arm_id": "A2", "treatment_id": "B", "n": 120},
            {"study_id": "AD2", "arm_id": "C1", "treatment_id": "C", "n": 120},
            {"study_id": "AD2", "arm_id": "C2", "treatment_id": "D", "n": 120},
        ],
        "outcomes_ad": [
            {"study_id": "AD1", "arm_id": "A1", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.12},
            {"study_id": "AD1", "arm_id": "A2", "outcome_id": "efficacy", "measure_type": "continuous", "value": 1.0, "se": 0.12},
            {"study_id": "AD2", "arm_id": "C1", "outcome_id": "efficacy", "measure_type": "continuous", "value": 2.0, "se": 0.12},
            {"study_id": "AD2", "arm_id": "C2", "outcome_id": "efficacy", "measure_type": "continuous", "value": 3.0, "se": 0.12},
        ],
        "ad_covariates": [
            {"study_id": "AD1", "arm_id": "A1", "covariate_name": "x", "mean": 0.0, "sd": 1.0, "n": 120},
            {"study_id": "AD1", "arm_id": "A2", "covariate_name": "x", "mean": 0.1, "sd": 1.0, "n": 120},
            {"study_id": "AD2", "arm_id": "C1", "covariate_name": "x", "mean": 0.2, "sd": 1.0, "n": 120},
            {"study_id": "AD2", "arm_id": "C2", "covariate_name": "x", "mean": 0.3, "sd": 1.0, "n": 120},
        ],
    }

    with pytest.raises(ValidationError, match="disconnected treatment network"):
        MLNMRPooler().fit(
            DatasetBuilder().from_payload(payload),
            MLNMRSpec(
                outcome_id="efficacy",
                reference_treatment="A",
                covariate_name="x",
                integration_mode="empirical",
            ),
        )
