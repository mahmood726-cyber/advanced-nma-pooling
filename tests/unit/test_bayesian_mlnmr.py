from __future__ import annotations

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.bayesian_ml_nmr import BayesianMLNMRPooler
from nma_pool.models.ml_nmr import MLNMRPooler
from nma_pool.models.spec import BayesianMLNMRSpec, MLNMRSpec
from tests.fixtures.mlnmr_payload import build_mlnmr_payload


def test_bayesian_analytic_matches_gls_center() -> None:
    dataset = DatasetBuilder().from_payload(build_mlnmr_payload())
    gls = MLNMRPooler().fit(
        dataset,
        MLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            integration_mode="empirical",
        ),
    )
    bayes = BayesianMLNMRPooler().fit(
        dataset,
        BayesianMLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            backend="analytic",
            prior_scale=1000.0,
            n_draws=3000,
            seed=11,
        ),
    )
    assert bayes.backend_used == "analytic"
    assert abs(bayes.treatment_effects["B"] - gls.treatment_effects["B"]) < 0.06
    assert abs(bayes.treatment_effects["C"] - gls.treatment_effects["C"]) < 0.06
    assert abs(bayes.interaction_effects["B"] - gls.interaction_effects["B"]) < 0.08
    assert abs(bayes.interaction_effects["C"] - gls.interaction_effects["C"]) < 0.08
    assert abs(bayes.beta_main - gls.beta_main) < 0.08


def test_bayesian_analytic_draws_and_se_positive() -> None:
    dataset = DatasetBuilder().from_payload(build_mlnmr_payload())
    fit = BayesianMLNMRPooler().fit(
        dataset,
        BayesianMLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            backend="analytic",
            prior_scale=8.0,
            n_draws=1500,
            seed=7,
        ),
    )
    assert fit.n_draws == 1500
    assert fit.treatment_ses["B"] > 0
    assert fit.treatment_ses["C"] > 0
    effect_cb, se_cb = fit.contrast("C", "B", covariate_value=0.0)
    assert effect_cb > 0.5
    assert se_cb > 0


def test_bayesian_stan_fallback_when_cmdstanpy_missing() -> None:
    dataset = DatasetBuilder().from_payload(build_mlnmr_payload())
    fit = BayesianMLNMRPooler().fit(
        dataset,
        BayesianMLNMRSpec(
            outcome_id="efficacy",
            reference_treatment="A",
            covariate_name="x",
            backend="stan",
            prior_scale=10.0,
            n_draws=500,
            n_warmup=200,
            n_chains=2,
            seed=3,
        ),
    )
    # In this environment cmdstanpy is absent, so fallback is expected.
    assert fit.backend_used in {"stan", "analytic_fallback"}
    if fit.backend_used == "analytic_fallback":
        assert any("CmdStanPy is not installed" in w for w in fit.warnings)

