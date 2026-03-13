from __future__ import annotations

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.spec import ModelSpec
from nma_pool.validation.inconsistency import run_inconsistency_diagnostics
from nma_pool.validation.simulation import (
    ContinuousSimulationSpec,
    InconsistentLoopSpec,
    simulate_continuous_abc_network,
    simulate_inconsistent_abc_loop,
)


def test_consistent_network_not_flagged() -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(noise_sd=0.0, se=0.15)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )
    diagnostics = run_inconsistency_diagnostics(dataset, spec, alpha=0.05)
    assert diagnostics.global_test.flagged is False
    assert all(row.flagged is False for row in diagnostics.node_splits)


def test_inconsistent_network_is_flagged() -> None:
    payload = simulate_inconsistent_abc_loop(
        InconsistentLoopSpec(se=0.12, bc_direct_effect=-1.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )
    diagnostics = run_inconsistency_diagnostics(dataset, spec, alpha=0.05)
    assert diagnostics.flagged is True
    assert diagnostics.global_test.df >= 1
    assert diagnostics.global_test.p_value < 0.05
    assert any(row.flagged for row in diagnostics.node_splits)


def test_multiarm_consistent_network_not_overflagged() -> None:
    payload = {
        "studies": [
            {
                "study_id": "M1",
                "design": "rct",
                "year": 2024,
                "source_id": "m1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "M2",
                "design": "rct",
                "year": 2024,
                "source_id": "m2",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "M3",
                "design": "rct",
                "year": 2024,
                "source_id": "m3",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "M1", "arm_id": "A1", "treatment_id": "A", "n": 120},
            {"study_id": "M1", "arm_id": "A2", "treatment_id": "B", "n": 120},
            {"study_id": "M1", "arm_id": "A3", "treatment_id": "C", "n": 120},
            {"study_id": "M2", "arm_id": "B1", "treatment_id": "A", "n": 100},
            {"study_id": "M2", "arm_id": "B2", "treatment_id": "B", "n": 100},
            {"study_id": "M3", "arm_id": "C1", "treatment_id": "A", "n": 100},
            {"study_id": "M3", "arm_id": "C2", "treatment_id": "C", "n": 100},
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
                "se": 0.2,
            },
            {
                "study_id": "M1",
                "arm_id": "A3",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 2.0,
                "se": 0.2,
            },
            {
                "study_id": "M2",
                "arm_id": "B1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": 0.2,
            },
            {
                "study_id": "M2",
                "arm_id": "B2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 1.0,
                "se": 0.2,
            },
            {
                "study_id": "M3",
                "arm_id": "C1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": 0.2,
            },
            {
                "study_id": "M3",
                "arm_id": "C2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 2.0,
                "se": 0.2,
            },
        ],
    }
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )
    diagnostics = run_inconsistency_diagnostics(dataset, spec, alpha=0.05)
    assert diagnostics.global_test.flagged is False
    assert diagnostics.global_test.p_value >= 0.05
