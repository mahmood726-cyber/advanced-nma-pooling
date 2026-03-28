from __future__ import annotations

import pytest

from nma_pool.data.builder import DatasetBuilder
from nma_pool.data.schemas import ValidationError
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import ModelSpec
from nma_pool.validation.diagnostics import summarize_network


def _continuous_network_payload() -> dict:
    return {
        "studies": [
            {
                "study_id": "S1",
                "design": "rct",
                "year": 2020,
                "source_id": "src1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "S2",
                "design": "rct",
                "year": 2021,
                "source_id": "src2",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "S3",
                "design": "rct",
                "year": 2022,
                "source_id": "src3",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 100},
            {"study_id": "S1", "arm_id": "A2", "treatment_id": "B", "n": 100},
            {"study_id": "S2", "arm_id": "B1", "treatment_id": "A", "n": 100},
            {"study_id": "S2", "arm_id": "B2", "treatment_id": "C", "n": 100},
            {"study_id": "S3", "arm_id": "C1", "treatment_id": "B", "n": 100},
            {"study_id": "S3", "arm_id": "C2", "treatment_id": "C", "n": 100},
        ],
        "outcomes_ad": [
            {
                "study_id": "S1",
                "arm_id": "A1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": 0.2,
            },
            {
                "study_id": "S1",
                "arm_id": "A2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 1.0,
                "se": 0.2,
            },
            {
                "study_id": "S2",
                "arm_id": "B1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": 0.2,
            },
            {
                "study_id": "S2",
                "arm_id": "B2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 2.0,
                "se": 0.2,
            },
            {
                "study_id": "S3",
                "arm_id": "C1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 1.0,
                "se": 0.2,
            },
            {
                "study_id": "S3",
                "arm_id": "C2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 2.0,
                "se": 0.2,
            },
        ],
    }


def _binary_network_payload() -> dict:
    return {
        "studies": [
            {
                "study_id": "R1",
                "design": "rct",
                "year": 2020,
                "source_id": "src1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "R2",
                "design": "rct",
                "year": 2021,
                "source_id": "src2",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "R1", "arm_id": "A1", "treatment_id": "A", "n": 100},
            {"study_id": "R1", "arm_id": "A2", "treatment_id": "B", "n": 100},
            {"study_id": "R2", "arm_id": "B1", "treatment_id": "A", "n": 80},
            {"study_id": "R2", "arm_id": "B2", "treatment_id": "B", "n": 80},
        ],
        "outcomes_ad": [
            {
                "study_id": "R1",
                "arm_id": "A1",
                "outcome_id": "response",
                "measure_type": "binary",
                "value": 20,
            },
            {
                "study_id": "R1",
                "arm_id": "A2",
                "outcome_id": "response",
                "measure_type": "binary",
                "value": 33,
            },
            {
                "study_id": "R2",
                "arm_id": "B1",
                "outcome_id": "response",
                "measure_type": "binary",
                "value": 10,
            },
            {
                "study_id": "R2",
                "arm_id": "B2",
                "outcome_id": "response",
                "measure_type": "binary",
                "value": 18,
            },
        ],
    }


def _disconnected_continuous_network_payload() -> dict:
    return {
        "studies": [
            {
                "study_id": "S1",
                "design": "rct",
                "year": 2020,
                "source_id": "src1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "S2",
                "design": "rct",
                "year": 2021,
                "source_id": "src2",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 100},
            {"study_id": "S1", "arm_id": "A2", "treatment_id": "B", "n": 100},
            {"study_id": "S2", "arm_id": "C1", "treatment_id": "C", "n": 100},
            {"study_id": "S2", "arm_id": "C2", "treatment_id": "D", "n": 100},
        ],
        "outcomes_ad": [
            {
                "study_id": "S1",
                "arm_id": "A1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": 0.2,
            },
            {
                "study_id": "S1",
                "arm_id": "A2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 1.0,
                "se": 0.2,
            },
            {
                "study_id": "S2",
                "arm_id": "C1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 2.0,
                "se": 0.2,
            },
            {
                "study_id": "S2",
                "arm_id": "C2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 3.0,
                "se": 0.2,
            },
        ],
    }


def test_core_ad_model_recovers_consistent_continuous_network() -> None:
    dataset = DatasetBuilder().from_payload(_continuous_network_payload())
    fit = ADNMAPooler().fit(
        dataset,
        ModelSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=True,
        ),
    )

    assert abs(fit.treatment_effects["B"] - 1.0) < 0.1
    assert abs(fit.treatment_effects["C"] - 2.0) < 0.1
    effect_cb, se_cb = fit.contrast("C", "B")
    assert abs(effect_cb - 1.0) < 0.1
    assert se_cb > 0
    assert fit.tau < 0.05


def test_core_ad_model_binary_effect_direction() -> None:
    dataset = DatasetBuilder().from_payload(_binary_network_payload())
    fit = ADNMAPooler().fit(
        dataset,
        ModelSpec(
            outcome_id="response",
            measure_type="binary",
            reference_treatment="A",
            random_effects=True,
        ),
    )
    # Positive effect indicates better odds for B than A on log-odds scale.
    assert fit.treatment_effects["B"] > 0
    assert fit.treatment_ses["B"] > 0


def test_core_ad_model_rejects_disconnected_network() -> None:
    dataset = DatasetBuilder().from_payload(_disconnected_continuous_network_payload())

    with pytest.raises(ValidationError, match="disconnected treatment network"):
        ADNMAPooler().fit(
            dataset,
            ModelSpec(
                outcome_id="efficacy",
                measure_type="continuous",
                reference_treatment="A",
                random_effects=False,
            ),
        )


def test_network_diagnostics_report_connected_components() -> None:
    dataset = DatasetBuilder().from_payload(_disconnected_continuous_network_payload())
    diagnostics = summarize_network(dataset, "efficacy")

    assert diagnostics.is_connected is False
    assert diagnostics.connected_components == (("A", "B"), ("C", "D"))
