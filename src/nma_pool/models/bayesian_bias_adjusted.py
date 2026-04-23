"""Bayesian design-stratified bias-adjusted NMA with analytic/Stan backends."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.bias_adjusted import BiasAdjustedDesignData, BiasAdjustedNMAPooler
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.resources import stan_model_path
from nma_pool.models.spec import BayesianBiasAdjustedSpec


@dataclass(frozen=True)
class BayesianBiasAdjustedNMAFitResult:
    outcome_id: str
    measure_type: str
    reference_treatment: str
    reference_design: str
    backend_used: str
    n_draws: int
    treatment_effects: dict[str, float]
    treatment_ses: dict[str, float]
    design_bias_effects: dict[str, float]
    design_bias_ses: dict[str, float]
    parameter_treatments: tuple[str, ...]
    parameter_designs: tuple[str, ...]
    parameter_cov: np.ndarray
    tau: float
    n_studies: int
    n_contrasts: int
    warnings: tuple[str, ...]

    def contrast(
        self,
        treatment_a: str,
        treatment_b: str,
        *,
        design: str | None = None,
    ) -> tuple[float, float]:
        design_name = design or self.reference_design
        if treatment_a not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_a}")
        if treatment_b not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_b}")
        if design_name != self.reference_design and design_name not in self.design_bias_effects:
            raise KeyError(f"Unknown design stratum: {design_name}")

        effect = self.treatment_effects[treatment_a] - self.treatment_effects[treatment_b]
        if design_name != self.reference_design:
            effect += self.design_bias_effects[design_name]

        coeff = np.zeros((len(self.parameter_treatments) + len(self.parameter_designs),), dtype=float)
        self._fill_treatment_coeff(coeff, treatment=treatment_a, sign=+1.0)
        self._fill_treatment_coeff(coeff, treatment=treatment_b, sign=-1.0)
        if design_name != self.reference_design:
            d_idx = self.parameter_designs.index(design_name)
            coeff[len(self.parameter_treatments) + d_idx] = 1.0

        variance = float(coeff.T @ self.parameter_cov @ coeff)
        return effect, math.sqrt(max(variance, 0.0))

    def _fill_treatment_coeff(
        self,
        coeff: np.ndarray,
        *,
        treatment: str,
        sign: float,
    ) -> None:
        if treatment == self.reference_treatment:
            return
        t_idx = self.parameter_treatments.index(treatment)
        coeff[t_idx] += sign


class BayesianBiasAdjustedNMAPooler:
    """Bayesian bias-adjusted NMA with backend selection and fallback."""

    def __init__(self, design_builder: BiasAdjustedNMAPooler | None = None) -> None:
        self._design_builder = design_builder or BiasAdjustedNMAPooler()

    def fit(
        self,
        dataset: EvidenceDataset,
        spec: BayesianBiasAdjustedSpec,
    ) -> BayesianBiasAdjustedNMAFitResult:
        if spec.treatment_prior_sd <= 0:
            raise ValidationError("treatment_prior_sd must be > 0.")
        if spec.bias_prior_sd <= 0:
            raise ValidationError("bias_prior_sd must be > 0.")
        if spec.n_draws < 1:
            raise ValidationError("n_draws must be >= 1.")

        design = self._design_builder.prepare_design(dataset=dataset, spec=spec)
        warnings = list(design.warnings)

        tau = 0.0
        if spec.random_effects and design.y.shape[0] > design.x.shape[1]:
            tau = ADNMAPooler()._optimize_tau_reml(y=design.y, x=design.x, v=design.v)  # noqa: SLF001
        elif spec.random_effects:
            warnings.append(
                "random_effects=True requested but insufficient degrees of freedom; tau fixed at 0."
            )

        backend_used = spec.backend
        if spec.backend == "stan":
            draws, stan_warnings = self._fit_stan(design=design, spec=spec, tau=tau)
            warnings.extend(stan_warnings)
            if draws.size == 0:
                draws, analytic_warnings = self._fit_analytic(design=design, spec=spec, tau=tau)
                warnings.extend(analytic_warnings)
                backend_used = "analytic_fallback"
        else:
            draws, analytic_warnings = self._fit_analytic(design=design, spec=spec, tau=tau)
            warnings.extend(analytic_warnings)
            backend_used = "analytic"

        return _result_from_draws(
            design=design,
            draws=draws,
            spec=spec,
            tau=tau,
            backend_used=backend_used,
            warnings=tuple(warnings),
        )

    def _fit_analytic(
        self,
        *,
        design: BiasAdjustedDesignData,
        spec: BayesianBiasAdjustedSpec,
        tau: float,
    ) -> tuple[np.ndarray, tuple[str, ...]]:
        prior_sd = _prior_sd_vector(
            treatment_count=len(design.parameter_treatments),
            design_count=len(design.parameter_designs),
            treatment_prior_sd=spec.treatment_prior_sd,
            bias_prior_sd=spec.bias_prior_sd,
        )
        m = design.v + (np.eye(design.v.shape[0], dtype=float) * (tau * tau))
        m_inv = _inverse_or_pinv(m)
        xt_m_inv = design.x.T @ m_inv
        post_precision = (xt_m_inv @ design.x) + np.diag(1.0 / np.square(prior_sd))
        post_cov = _inverse_or_pinv(post_precision)
        post_mean = post_cov @ xt_m_inv @ design.y
        draws = _sample_mvn(
            mean=post_mean,
            cov=post_cov,
            n_draws=spec.n_draws,
            seed=spec.seed,
        )
        return draws, ()

    def _fit_stan(
        self,
        *,
        design: BiasAdjustedDesignData,
        spec: BayesianBiasAdjustedSpec,
        tau: float,
    ) -> tuple[np.ndarray, tuple[str, ...]]:
        try:
            import cmdstanpy  # type: ignore[import-not-found]
        except ImportError:
            return (
                np.empty((0, design.x.shape[1]), dtype=float),
                ("CmdStanPy is not installed; falling back to analytic backend.",),
            )


        n = int(design.y.shape[0])
        p = int(design.x.shape[1])
        m = design.v + (np.eye(n, dtype=float) * (tau * tau))
        jitter = 1e-8
        m_pd = np.asarray(m, dtype=float)
        for _ in range(6):
            try:
                l_m = np.linalg.cholesky(m_pd)
                break
            except np.linalg.LinAlgError:
                m_pd = m_pd + (np.eye(n, dtype=float) * jitter)
                jitter *= 10.0
        else:
            return (
                np.empty((0, p), dtype=float),
                ("Failed Cholesky decomposition for covariance in Stan backend.",),
            )

        prior_sd = _prior_sd_vector(
            treatment_count=len(design.parameter_treatments),
            design_count=len(design.parameter_designs),
            treatment_prior_sd=spec.treatment_prior_sd,
            bias_prior_sd=spec.bias_prior_sd,
        )
        draws_per_chain = max(1, int(math.ceil(spec.n_draws / max(spec.n_chains, 1))))
        try:
            with stan_model_path("bias_adjusted_normal_fixed.stan") as stan_file:
                model = cmdstanpy.CmdStanModel(stan_file=str(stan_file))
                fit = model.sample(
                    data={
                        "N": n,
                        "P": p,
                        "X": design.x.tolist(),
                        "y": design.y.tolist(),
                        "L_M": l_m.tolist(),
                        "prior_sd": prior_sd.tolist(),
                    },
                    chains=max(1, int(spec.n_chains)),
                    iter_warmup=max(1, int(spec.n_warmup)),
                    iter_sampling=draws_per_chain,
                    seed=int(spec.seed),
                    show_progress=False,
                )
        except FileNotFoundError as exc:
            return (
                np.empty((0, p), dtype=float),
                (str(exc),),
            )
        except Exception as exc:  # pragma: no cover
            return (
                np.empty((0, p), dtype=float),
                (f"Stan backend failed ({type(exc).__name__}: {exc}); falling back.",),
            )

        try:
            beta_draws = np.asarray(fit.stan_variable("beta"), dtype=float)
        except Exception as exc:  # pragma: no cover
            return (
                np.empty((0, p), dtype=float),
                (f"Stan backend output parsing failed ({type(exc).__name__}: {exc}).",),
            )
        if beta_draws.ndim != 2 or beta_draws.shape[1] != p:
            return (
                np.empty((0, p), dtype=float),
                ("Stan backend returned unexpected beta draw shape.",),
            )
        if beta_draws.shape[0] > spec.n_draws:
            beta_draws = beta_draws[: spec.n_draws, :]

        warnings: list[str] = []
        summary = fit.summary()
        max_rhat = float(summary["R_hat"].max()) if "R_hat" in summary else float("nan")
        if np.isfinite(max_rhat) and max_rhat > 1.01:
            warnings.append(f"Stan convergence warning: max R_hat={max_rhat:.4f} > 1.01.")
        return beta_draws, tuple(warnings)


def _result_from_draws(
    *,
    design: BiasAdjustedDesignData,
    draws: np.ndarray,
    spec: BayesianBiasAdjustedSpec,
    tau: float,
    backend_used: str,
    warnings: tuple[str, ...],
) -> BayesianBiasAdjustedNMAFitResult:
    if draws.ndim != 2 or draws.shape[0] < 1:
        raise ValidationError("Posterior draws are empty.")
    p = draws.shape[1]
    expected_p = len(design.parameter_treatments) + len(design.parameter_designs)
    if p != expected_p:
        raise ValidationError("Posterior draw parameter dimension mismatch.")

    means = np.mean(draws, axis=0)
    cov = np.cov(draws, rowvar=False) if draws.shape[0] > 1 else np.zeros((p, p), dtype=float)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]], dtype=float)

    treatment_effects = {spec.reference_treatment: 0.0}
    treatment_ses = {spec.reference_treatment: 0.0}
    for idx, treatment in enumerate(design.parameter_treatments):
        treatment_effects[treatment] = float(means[idx])
        treatment_ses[treatment] = math.sqrt(max(float(cov[idx, idx]), 0.0))

    design_bias_effects = {spec.reference_design: 0.0}
    design_bias_ses = {spec.reference_design: 0.0}
    k = len(design.parameter_treatments)
    for jdx, design_name in enumerate(design.parameter_designs):
        p_idx = k + jdx
        design_bias_effects[design_name] = float(means[p_idx])
        design_bias_ses[design_name] = math.sqrt(max(float(cov[p_idx, p_idx]), 0.0))

    return BayesianBiasAdjustedNMAFitResult(
        outcome_id=spec.outcome_id,
        measure_type=spec.measure_type,
        reference_treatment=spec.reference_treatment,
        reference_design=spec.reference_design,
        backend_used=backend_used,
        n_draws=int(draws.shape[0]),
        treatment_effects=treatment_effects,
        treatment_ses=treatment_ses,
        design_bias_effects=design_bias_effects,
        design_bias_ses=design_bias_ses,
        parameter_treatments=design.parameter_treatments,
        parameter_designs=design.parameter_designs,
        parameter_cov=np.asarray(cov, dtype=float),
        tau=float(tau),
        n_studies=design.n_studies,
        n_contrasts=design.n_contrasts,
        warnings=warnings,
    )


def _prior_sd_vector(
    *,
    treatment_count: int,
    design_count: int,
    treatment_prior_sd: float,
    bias_prior_sd: float,
) -> np.ndarray:
    if treatment_count < 0 or design_count < 0:
        raise ValidationError("Parameter counts must be non-negative.")
    return np.asarray(
        ([treatment_prior_sd] * treatment_count) + ([bias_prior_sd] * design_count),
        dtype=float,
    )


def _inverse_or_pinv(matrix: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(matrix)


def _sample_mvn(
    *,
    mean: np.ndarray,
    cov: np.ndarray,
    n_draws: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    cov_pd = np.asarray(cov, dtype=float)
    jitter = 1e-10
    for _ in range(6):
        try:
            return rng.multivariate_normal(mean=mean, cov=cov_pd, size=n_draws)
        except np.linalg.LinAlgError:
            cov_pd = cov_pd + (np.eye(cov_pd.shape[0]) * jitter)
            jitter *= 10.0
    eigvals, eigvecs = np.linalg.eigh(cov_pd)
    eigvals_clipped = np.clip(eigvals, a_min=0.0, a_max=None)
    stable_cov = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
    return rng.multivariate_normal(mean=mean, cov=stable_cov, size=n_draws)



