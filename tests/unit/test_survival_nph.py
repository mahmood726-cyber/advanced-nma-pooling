from __future__ import annotations

import math

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.spec import SurvivalNPHSpec
from nma_pool.models.survival_nph import SurvivalNPHPooler
from nma_pool.validation.simulation import (
    SurvivalNonPHSimulationSpec,
    simulate_survival_nonph_network,
    survival_nonph_truth_log_hazard_ratios,
)


def test_survival_nonph_recovers_interval_specific_effects() -> None:
    sim_spec = SurvivalNonPHSimulationSpec(
        seed=91,
        n_per_arm=900,
        replicates_per_pair=3,
    )
    payload = simulate_survival_nonph_network(sim_spec)
    dataset = DatasetBuilder().from_payload(payload)
    fit = SurvivalNPHPooler().fit(
        dataset,
        SurvivalNPHSpec(
            outcome_id="os",
            reference_treatment="A",
            continuity_correction=0.5,
        ),
    )
    truth = survival_nonph_truth_log_hazard_ratios(sim_spec)
    for interval_id in fit.interval_ids:
        assert abs(fit.treatment_effects_by_interval[interval_id]["B"] - truth[interval_id]["B"]) < 0.16
        assert abs(fit.treatment_effects_by_interval[interval_id]["C"] - truth[interval_id]["C"]) < 0.16

    # Non-PH pattern: B effect drifts across intervals in the truth and should be reflected.
    assert fit.treatment_effects_by_interval["I1"]["B"] < fit.treatment_effects_by_interval["I2"]["B"]
    assert fit.treatment_effects_by_interval["I2"]["B"] < fit.treatment_effects_by_interval["I3"]["B"]

    effect_cb_i1, se_cb_i1 = fit.contrast("C", "B", interval_id="I1")
    assert abs(effect_cb_i1 - (truth["I1"]["C"] - truth["I1"]["B"])) < 0.20
    assert se_cb_i1 > 0


def test_survival_nonph_random_effects_flag_warns_and_runs() -> None:
    sim_spec = SurvivalNonPHSimulationSpec(seed=19, n_per_arm=700, replicates_per_pair=2)
    payload = simulate_survival_nonph_network(sim_spec)
    fit = SurvivalNPHPooler().fit(
        DatasetBuilder().from_payload(payload),
        SurvivalNPHSpec(
            outcome_id="os",
            reference_treatment="A",
            random_effects=True,
        ),
    )
    assert fit.tau >= 0.0
    pooled_b = fit.pooled_treatment_effects["B"]
    assert math.isfinite(pooled_b)


def test_survival_non_estimable_interval_cell_set_to_nan() -> None:
    payload = {
        "studies": [
            {
                "study_id": "S1",
                "design": "rct",
                "year": 2025,
                "source_id": "x1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "S2",
                "design": "rct",
                "year": 2025,
                "source_id": "x2",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 100},
            {"study_id": "S1", "arm_id": "B1", "treatment_id": "B", "n": 100},
            {"study_id": "S2", "arm_id": "A2", "treatment_id": "A", "n": 100},
            {"study_id": "S2", "arm_id": "C2", "treatment_id": "C", "n": 100},
        ],
        "survival_ad": [
            {"study_id": "S1", "arm_id": "A1", "outcome_id": "os", "interval_id": "I1", "t_start": 0.0, "t_end": 3.0, "events": 10, "person_time": 300.0},
            {"study_id": "S1", "arm_id": "B1", "outcome_id": "os", "interval_id": "I1", "t_start": 0.0, "t_end": 3.0, "events": 8, "person_time": 300.0},
            {"study_id": "S2", "arm_id": "A2", "outcome_id": "os", "interval_id": "I1", "t_start": 0.0, "t_end": 3.0, "events": 10, "person_time": 300.0},
            {"study_id": "S2", "arm_id": "C2", "outcome_id": "os", "interval_id": "I1", "t_start": 0.0, "t_end": 3.0, "events": 7, "person_time": 300.0},
            {"study_id": "S1", "arm_id": "A1", "outcome_id": "os", "interval_id": "I2", "t_start": 3.0, "t_end": 6.0, "events": 10, "person_time": 300.0},
            {"study_id": "S1", "arm_id": "B1", "outcome_id": "os", "interval_id": "I2", "t_start": 3.0, "t_end": 6.0, "events": 9, "person_time": 300.0},
        ],
    }
    fit = SurvivalNPHPooler().fit(
        DatasetBuilder().from_payload(payload),
        SurvivalNPHSpec(outcome_id="os", reference_treatment="A"),
    )
    assert math.isnan(fit.treatment_effects_by_interval["I2"]["C"])
    assert math.isnan(fit.treatment_ses_by_interval["I2"]["C"])
    assert fit.estimable_by_interval["I2"]["C"] is False
    assert any("Non-estimable interval-treatment effects" in warning for warning in fit.warnings)
