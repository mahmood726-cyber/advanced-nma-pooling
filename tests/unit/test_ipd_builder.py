from __future__ import annotations

import pytest

from nma_pool.data.builder import DatasetBuilder
from nma_pool.data.schemas import ValidationError


def _payload_with_ipd_and_covariates() -> dict:
    return {
        "studies": [
            {
                "study_id": "S1",
                "design": "rct",
                "year": 2024,
                "source_id": "src1",
                "rob_domain_summary": "low",
            }
        ],
        "arms": [
            {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 4},
            {"study_id": "S1", "arm_id": "A2", "treatment_id": "B", "n": 4},
        ],
        "ipd": [
            {
                "study_id": "S1",
                "patient_id": "p1",
                "arm_id": "A1",
                "treatment_id": "A",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 0.1,
                "covariates": {"x": -0.5},
            },
            {
                "study_id": "S1",
                "patient_id": "p2",
                "arm_id": "A1",
                "treatment_id": "A",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 0.2,
                "covariates": {"x": 0.0},
            },
            {
                "study_id": "S1",
                "patient_id": "p3",
                "arm_id": "A2",
                "treatment_id": "B",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 1.0,
                "covariates": {"x": 0.2},
            },
            {
                "study_id": "S1",
                "patient_id": "p4",
                "arm_id": "A2",
                "treatment_id": "B",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "outcome_value": 1.3,
                "covariates": {"x": 0.8},
            },
        ],
        "ad_covariates": [
            {"study_id": "S1", "arm_id": "A1", "covariate_name": "x", "mean": -0.25, "sd": 0.2, "n": 4},
            {"study_id": "S1", "arm_id": "A2", "covariate_name": "x", "mean": 0.5, "sd": 0.2, "n": 4},
        ],
    }


def test_dataset_builder_accepts_ipd_and_covariates() -> None:
    dataset = DatasetBuilder().from_payload(_payload_with_ipd_and_covariates())
    assert dataset.measure_type_for_outcome("efficacy") == "continuous"
    assert dataset.treatments_for_outcome("efficacy") == ("A", "B")
    mean_empirical = dataset.arm_covariate_mean(
        study_id="S1",
        arm_id="A1",
        covariate_name="x",
        outcome_id="efficacy",
        mode="empirical",
    )
    assert mean_empirical is not None
    assert abs(mean_empirical - (-0.25)) < 1e-8


def test_dataset_builder_rejects_ipd_treatment_arm_mismatch() -> None:
    payload = _payload_with_ipd_and_covariates()
    payload["ipd"][0]["treatment_id"] = "B"
    with pytest.raises(ValidationError, match="does not match arm treatment_id"):
        DatasetBuilder().from_payload(payload)

