from __future__ import annotations

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.bias_adjusted import BiasAdjustedNMAPooler
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import BiasAdjustedSpec, ModelSpec
from nma_pool.validation.simulation import ContinuousSimulationSpec, simulate_continuous_abc_network


def _cross_design_biased_payload() -> dict:
    return {
        "studies": [
            {"study_id": "R1", "design": "rct", "year": 2021, "source_id": "src-r1", "rob_domain_summary": "low"},
            {"study_id": "R2", "design": "rct", "year": 2021, "source_id": "src-r2", "rob_domain_summary": "low"},
            {"study_id": "N1", "design": "nrs", "year": 2022, "source_id": "src-n1", "rob_domain_summary": "high"},
            {"study_id": "N2", "design": "nrs", "year": 2022, "source_id": "src-n2", "rob_domain_summary": "high"},
        ],
        "arms": [
            {"study_id": "R1", "arm_id": "R1A", "treatment_id": "A", "n": 120},
            {"study_id": "R1", "arm_id": "R1B", "treatment_id": "B", "n": 120},
            {"study_id": "R2", "arm_id": "R2A", "treatment_id": "A", "n": 120},
            {"study_id": "R2", "arm_id": "R2C", "treatment_id": "C", "n": 120},
            {"study_id": "N1", "arm_id": "N1A", "treatment_id": "A", "n": 120},
            {"study_id": "N1", "arm_id": "N1B", "treatment_id": "B", "n": 120},
            {"study_id": "N2", "arm_id": "N2A", "treatment_id": "A", "n": 120},
            {"study_id": "N2", "arm_id": "N2C", "treatment_id": "C", "n": 120},
        ],
        "outcomes_ad": [
            {"study_id": "R1", "arm_id": "R1A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
            {"study_id": "R1", "arm_id": "R1B", "outcome_id": "efficacy", "measure_type": "continuous", "value": 1.0, "se": 0.18},
            {"study_id": "R2", "arm_id": "R2A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
            {"study_id": "R2", "arm_id": "R2C", "outcome_id": "efficacy", "measure_type": "continuous", "value": 2.0, "se": 0.18},
            {"study_id": "N1", "arm_id": "N1A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
            {"study_id": "N1", "arm_id": "N1B", "outcome_id": "efficacy", "measure_type": "continuous", "value": 1.6, "se": 0.18},
            {"study_id": "N2", "arm_id": "N2A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
            {"study_id": "N2", "arm_id": "N2C", "outcome_id": "efficacy", "measure_type": "continuous", "value": 2.6, "se": 0.18},
        ],
    }


def test_bias_adjusted_improves_over_naive_core_when_nrs_bias_present() -> None:
    dataset = DatasetBuilder().from_payload(_cross_design_biased_payload())
    core_fit = ADNMAPooler().fit(
        dataset,
        ModelSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=False,
        ),
    )
    bias_fit = BiasAdjustedNMAPooler().fit(
        dataset,
        BiasAdjustedSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=False,
            reference_design="rct",
            bias_prior_sd=1.0,
        ),
    )
    assert abs(bias_fit.treatment_effects["B"] - 1.0) < abs(core_fit.treatment_effects["B"] - 1.0)
    assert abs(bias_fit.treatment_effects["C"] - 2.0) < abs(core_fit.treatment_effects["C"] - 2.0)
    assert bias_fit.design_bias_effects["nrs"] > 0.3

    effect_rct, _ = bias_fit.contrast("B", "A", design="rct")
    effect_nrs, _ = bias_fit.contrast("B", "A", design="nrs")
    assert effect_nrs > effect_rct


def test_bias_adjusted_runs_without_non_reference_designs() -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(seed=7, noise_sd=0.0, se=0.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    fit = BiasAdjustedNMAPooler().fit(
        dataset,
        BiasAdjustedSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=True,
            reference_design="rct",
            bias_prior_sd=1.0,
        ),
    )
    assert any("No non-reference designs present" in warning for warning in fit.warnings)
    assert "B" in fit.treatment_effects
    assert "C" in fit.treatment_effects
