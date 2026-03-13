from __future__ import annotations

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.bayesian_bias_adjusted import BayesianBiasAdjustedNMAPooler
from nma_pool.models.bias_adjusted import BiasAdjustedNMAPooler
from nma_pool.models.spec import BayesianBiasAdjustedSpec, BiasAdjustedSpec


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


def test_bayesian_bias_adjusted_analytic_matches_gls_center() -> None:
    dataset = DatasetBuilder().from_payload(_cross_design_biased_payload())
    gls = BiasAdjustedNMAPooler().fit(
        dataset,
        BiasAdjustedSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=False,
            reference_design="rct",
            bias_prior_sd=1000.0,
        ),
    )
    bayes = BayesianBiasAdjustedNMAPooler().fit(
        dataset,
        BayesianBiasAdjustedSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=False,
            reference_design="rct",
            bias_prior_sd=1000.0,
            backend="analytic",
            treatment_prior_sd=1000.0,
            n_draws=3000,
            seed=9,
        ),
    )
    assert bayes.backend_used == "analytic"
    assert abs(bayes.treatment_effects["B"] - gls.treatment_effects["B"]) < 0.08
    assert abs(bayes.treatment_effects["C"] - gls.treatment_effects["C"]) < 0.08
    assert abs(bayes.design_bias_effects["nrs"] - gls.design_bias_effects["nrs"]) < 0.08
    effect_nrs, se_nrs = bayes.contrast("B", "A", design="nrs")
    assert effect_nrs > 1.2
    assert se_nrs > 0


def test_bayesian_bias_adjusted_stan_fallback_when_cmdstanpy_missing() -> None:
    dataset = DatasetBuilder().from_payload(_cross_design_biased_payload())
    fit = BayesianBiasAdjustedNMAPooler().fit(
        dataset,
        BayesianBiasAdjustedSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=True,
            reference_design="rct",
            bias_prior_sd=1.0,
            backend="stan",
            treatment_prior_sd=10.0,
            n_draws=700,
            n_warmup=300,
            n_chains=2,
            seed=17,
        ),
    )
    assert fit.backend_used in {"stan", "analytic_fallback"}
    if fit.backend_used == "analytic_fallback":
        assert any("CmdStanPy is not installed" in warning for warning in fit.warnings)
