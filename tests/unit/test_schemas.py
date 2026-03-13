from __future__ import annotations

import pytest

from nma_pool.data.builder import DatasetBuilder
from nma_pool.data.schemas import ValidationError


def _valid_payload() -> dict:
    return {
        "studies": [
            {
                "study_id": "S1",
                "design": "rct",
                "year": 2020,
                "source_id": "src1",
                "rob_domain_summary": "low",
            }
        ],
        "arms": [
            {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 100},
            {"study_id": "S1", "arm_id": "A2", "treatment_id": "B", "n": 100},
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
        ],
    }


def test_dataset_builder_accepts_valid_payload() -> None:
    builder = DatasetBuilder()
    dataset = builder.from_payload(_valid_payload())
    assert dataset.study_ids == ("S1",)
    assert set(dataset.treatments_for_outcome("efficacy")) == {"A", "B"}


def test_dataset_builder_rejects_duplicate_arms() -> None:
    builder = DatasetBuilder()
    payload = _valid_payload()
    payload["arms"].append(payload["arms"][0])
    with pytest.raises(ValidationError, match="Duplicate"):
        builder.from_payload(payload)


def test_dataset_builder_rejects_binary_count_above_n() -> None:
    builder = DatasetBuilder()
    payload = _valid_payload()
    payload["outcomes_ad"] = [
        {
            "study_id": "S1",
            "arm_id": "A1",
            "outcome_id": "response",
            "measure_type": "binary",
            "value": 110,
        },
        {
            "study_id": "S1",
            "arm_id": "A2",
            "outcome_id": "response",
            "measure_type": "binary",
            "value": 50,
        },
    ]
    with pytest.raises(ValidationError, match="cannot exceed arm n"):
        builder.from_payload(payload)


def test_dataset_builder_rejects_non_integral_numeric_integer_fields() -> None:
    builder = DatasetBuilder()

    payload = _valid_payload()
    payload["studies"][0]["year"] = 2020.5
    with pytest.raises(ValidationError, match="Field 'year' must be an integer"):
        builder.from_payload(payload)

    payload = _valid_payload()
    payload["arms"][0]["n"] = 100.25
    with pytest.raises(ValidationError, match="Field 'n' must be an integer"):
        builder.from_payload(payload)

    payload = _valid_payload()
    payload["outcomes_ad"] = []
    payload["survival_ad"] = [
        {
            "study_id": "S1",
            "arm_id": "A1",
            "outcome_id": "os",
            "interval_id": "I1",
            "t_start": 0.0,
            "t_end": 3.0,
            "events": 10.5,
            "person_time": 300.0,
        },
        {
            "study_id": "S1",
            "arm_id": "A2",
            "outcome_id": "os",
            "interval_id": "I1",
            "t_start": 0.0,
            "t_end": 3.0,
            "events": 12,
            "person_time": 300.0,
        },
    ]
    with pytest.raises(ValidationError, match="Field 'events' must be an integer"):
        builder.from_payload(payload)
