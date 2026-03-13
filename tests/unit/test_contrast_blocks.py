from __future__ import annotations

from nma_pool.data.builder import DatasetBuilder
from nma_pool.validation.contrasts import extract_study_contrast_blocks


def test_extract_study_contrast_blocks_multiarm_covariance() -> None:
    payload = {
        "studies": [
            {
                "study_id": "M1",
                "design": "rct",
                "year": 2023,
                "source_id": "src-m1",
                "rob_domain_summary": "low",
            }
        ],
        "arms": [
            {"study_id": "M1", "arm_id": "A1", "treatment_id": "A", "n": 120},
            {"study_id": "M1", "arm_id": "A2", "treatment_id": "B", "n": 120},
            {"study_id": "M1", "arm_id": "A3", "treatment_id": "C", "n": 120},
        ],
        "outcomes_ad": [
            {
                "study_id": "M1",
                "arm_id": "A1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": 0.2,
            },
            {
                "study_id": "M1",
                "arm_id": "A2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 1.0,
                "se": 0.25,
            },
            {
                "study_id": "M1",
                "arm_id": "A3",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 2.0,
                "se": 0.3,
            },
        ],
    }
    dataset = DatasetBuilder().from_payload(payload)
    blocks = extract_study_contrast_blocks(
        dataset=dataset,
        outcome_id="efficacy",
        measure_type="continuous",
    )
    assert len(blocks) == 1
    block = blocks[0]
    assert block.covariance.shape == (2, 2)
    assert block.covariance[0, 1] > 0.0
    assert block.covariance[1, 0] > 0.0
    # diagonal should be larger than off-diagonal by non-baseline arm variance
    assert block.covariance[0, 0] > block.covariance[0, 1]
    assert block.covariance[1, 1] > block.covariance[1, 0]

