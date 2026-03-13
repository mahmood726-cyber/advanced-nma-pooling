from __future__ import annotations

import pytest

from nma_pool.data.builder import DatasetBuilder
from nma_pool.data.schemas import ValidationError


def _survival_payload() -> dict:
    return {
        "studies": [
            {
                "study_id": "S1",
                "design": "rct",
                "year": 2025,
                "source_id": "src-surv",
                "rob_domain_summary": "low",
            }
        ],
        "arms": [
            {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 120},
            {"study_id": "S1", "arm_id": "A2", "treatment_id": "B", "n": 120},
        ],
        "survival_ad": [
            {
                "study_id": "S1",
                "arm_id": "A1",
                "outcome_id": "os",
                "interval_id": "I1",
                "t_start": 0.0,
                "t_end": 3.0,
                "events": 24,
                "person_time": 300.0,
            },
            {
                "study_id": "S1",
                "arm_id": "A2",
                "outcome_id": "os",
                "interval_id": "I1",
                "t_start": 0.0,
                "t_end": 3.0,
                "events": 18,
                "person_time": 300.0,
            },
        ],
    }


def test_dataset_builder_accepts_survival_payload() -> None:
    dataset = DatasetBuilder().from_payload(_survival_payload())
    assert dataset.measure_type_for_outcome("os") == "survival"
    assert dataset.treatments_for_outcome("os") == ("A", "B")
    assert len(dataset.survival_intervals_by_study_outcome("S1", "os")) == 2


def test_dataset_builder_rejects_duplicate_survival_interval_keys() -> None:
    payload = _survival_payload()
    payload["survival_ad"].append(dict(payload["survival_ad"][0]))
    with pytest.raises(ValidationError, match="Duplicate .*survival_ad"):
        DatasetBuilder().from_payload(payload)


def test_dataset_builder_rejects_mixed_survival_and_continuous_same_outcome() -> None:
    payload = _survival_payload()
    payload["outcomes_ad"] = [
        {
            "study_id": "S1",
            "arm_id": "A1",
            "outcome_id": "os",
            "measure_type": "continuous",
            "value": 0.0,
            "se": 0.2,
        },
        {
            "study_id": "S1",
            "arm_id": "A2",
            "outcome_id": "os",
            "measure_type": "continuous",
            "value": 0.4,
            "se": 0.2,
        },
    ]
    with pytest.raises(ValidationError, match="Mixed measure types"):
        DatasetBuilder().from_payload(payload)


def test_dataset_builder_requires_two_arms_per_survival_interval() -> None:
    payload = _survival_payload()
    payload["survival_ad"] = [payload["survival_ad"][0]]
    with pytest.raises(ValidationError, match="at least 2 survival arms"):
        DatasetBuilder().from_payload(payload)


def test_dataset_builder_rejects_overlapping_survival_intervals_within_arm() -> None:
    payload = _survival_payload()
    payload["survival_ad"].extend(
        [
            {
                "study_id": "S1",
                "arm_id": "A1",
                "outcome_id": "os",
                "interval_id": "I2",
                "t_start": 2.0,
                "t_end": 4.0,
                "events": 10,
                "person_time": 180.0,
            },
            {
                "study_id": "S1",
                "arm_id": "A2",
                "outcome_id": "os",
                "interval_id": "I2",
                "t_start": 2.0,
                "t_end": 4.0,
                "events": 9,
                "person_time": 180.0,
            },
        ]
    )
    with pytest.raises(ValidationError, match="Overlapping survival intervals"):
        DatasetBuilder().from_payload(payload)


def test_dataset_builder_rejects_mismatched_interval_grid_between_arms() -> None:
    payload = _survival_payload()
    payload["survival_ad"].extend(
        [
            {
                "study_id": "S1",
                "arm_id": "A1",
                "outcome_id": "os",
                "interval_id": "I2",
                "t_start": 3.0,
                "t_end": 6.0,
                "events": 10,
                "person_time": 300.0,
            },
            {
                "study_id": "S1",
                "arm_id": "A2",
                "outcome_id": "os",
                "interval_id": "I2",
                "t_start": 3.5,
                "t_end": 6.0,
                "events": 9,
                "person_time": 250.0,
            },
        ]
    )
    with pytest.raises(ValidationError, match="interval_id bounds are inconsistent"):
        DatasetBuilder().from_payload(payload)
