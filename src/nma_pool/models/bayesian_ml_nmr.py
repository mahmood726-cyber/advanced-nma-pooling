"""Bayesian ML-NMR for continuous outcomes with analytic and Stan backends."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.ml_nmr import MLNMRDesignData, MLNMRPooler
from nma_pool.models.resources import stan_model_path
from nma_pool.models.spec import BayesianMLNMRSpec


@dataclass(frozen=True)
class BayesianMLNMRFitResult:
    outcome_id: str
    covariate_name: str
    reference_treatment: str
    backend_used: str
    prior_scale: float
    n_draws: int
    treatment_effects: dict[str, float]
    treatment_ses: dict[str, float]
    interaction_effects: dict[str, float]
    interaction_ses: dict[str, float]
    beta_main: float
    beta_main_se: float
    parameter_treatments: tuple[str, ...]
    parameter_cov: np.ndarray
    n_studies: int
    n_contrasts: int
    n_ipd_rows: int
    warnings: tuple[str, ...]

    def contrast(
        self,
        treatment_a: str,
        treatment_b: str,
        *,
        covariate_value: float = 0.0,
    ) -> tuple[float, float]:
        if treatment_a not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_a}")
        if treatment_b not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_b}")
        effect = (
            (self.treatment_effects[treatment_a] - self.treatment_effects[treatment_b])
            + covariate_value
            * (
                self.interaction_effects[treatment_a]
                - self.interaction_effects[treatment_b]
            )
        )
        variance = self._contrast_variance(
            treatment_a=treatment_a,
            treatment_b=treatment_b,
            covariate_value=covariate_value,
        )
        return effect, math.sqrt(max(variance, 0.0))

    def _contrast_variance(
        self,
        *,
        treatment_a: str,
        treatment_b: str,
        covariate_value: float,
    ) -> float:
        k = len(self.parameter_treatments)
        coeff = np.zeros((2 * k) + 1, dtype=float)
        self._fill(coeff, treatment_a, +1.0, covariate_value)
        self._fill(coeff, treatment_b, -1.0, covariate_value)
        return float(coeff.T @ self.parameter_cov @ coeff)

    def _fill(
        self,
        coeff: np.ndarray,
        treatment: str,
        sign: float,
        covariate_value: float,
    ) -> None:
        if treatment == self.reference_treatment:
            return
        idx = self.parameter_treatments.index(treatment)
        k = len(self.parameter_treatments)
        coeff[idx] += sign
        coeff[k + idx] += sign * covariate_value


class BayesianMLNMRPooler:
    """Bayesian ML-NMR with backend selection and automatic fallback."""

    def __init__(self, design_builder: MLNMRPooler | None = None) -> None:
        self._design_builder = design_builder or MLNMRPooler()

    def fit(self, dataset: EvidenceDataset, spec: BayesianMLNMRSpec) -> BayesianMLNMRFitResult:
        design = self._design_builder.prepare_design(dataset=dataset, spec=spec)
        warnings = list(design.warnings)
        if spec.random_effects:
            warnings.append(
                "BayesianMLNMRPooler currently supports fixed-effects contrast model only."
            )

        draws: np.ndarray
        backend_used = spec.backend
        if spec.backend == "stan":
            draws, stan_warnings = self._fit_stan(design=design, spec=spec)
            if draws.size == 0:
                draws, analytic_warnings = self._fit_analytic(design=design, spec=spec)
                backend_used = "analytic_fallback"
                warnings.extend(stan_warnings)
                warnings.extend(analytic_warnings)
            else:
                warnings.extend(stan_warnings)
        else:
            draws, analytic_warnings = self._fit_analytic(design=design, spec=spec)
            backend_used = "analytic"
            warnings.extend(analytic_warnings)

        return _result_from_draws(
            design=design,
            draws=draws,
            spec=spec,
            backend_used=backend_used,
            warnings=tuple(warnings),
        )

    def _fit_analytic(
        self,
        *,
        design: MLNMRDesignData,
        spec: BayesianMLNMRSpec,
    ) -> tuple[np.ndarray, tuple[str, ...]]:
        if spec.prior_scale <= 0:
            raise ValidationError("prior_scale must be > 0.")
        if spec.n_draws < 1:
            raise ValidationError("n_draws must be >= 1.")

        p = design.x.shape[1]
        prior_precision = np.eye(p, dtype=float) / (spec.prior_scale * spec.prior_scale)
        v_inv = _inverse_or_pinv(design.v)
        xt_v_inv = design.x.T @ v_inv
        post_precision = (xt_v_inv @ design.x) + prior_precision
        post_cov = _inverse_or_pinv(post_precision)
        post_mean = post_cov @ xt_v_inv @ design.y
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
        design: MLNMRDesignData,
        spec: BayesianMLNMRSpec,
    ) -> tuple[np.ndarray, tuple[str, ...]]:
        warnings: list[str] = []
        try:
            import cmdstanpy  # type: ignore[import-not-found]
        except ImportError:
            return (
                np.empty((0, design.x.shape[1]), dtype=float),
                ("CmdStanPy is not installed; falling back to analytic backend.",),
            )

        n = int(design.y.shape[0])
        p = int(design.x.shape[1])
        jitter = 1e-8
        v_pd = design.v + (np.eye(n, dtype=float) * jitter)
        try:
            l_v = np.linalg.cholesky(v_pd)
        except np.linalg.LinAlgError:
            return (
                np.empty((0, p), dtype=float),
                ("Failed Cholesky decomposition for covariance in Stan backend.",),
            )

        draws_per_chain = max(1, int(math.ceil(spec.n_draws / max(spec.n_chains, 1))))
        try:
            with stan_model_path("mlnmr_continuous_fixed.stan") as stan_file:
                model = cmdstanpy.CmdStanModel(stan_file=str(stan_file))
                fit = model.sample(
                    data={
                        "N": n,
                        "P": p,
                        "X": design.x.tolist(),
                        "y": design.y.tolist(),
                        "L_V": l_v.tolist(),
                        "prior_scale": float(spec.prior_scale),
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
        summary = fit.summary()
        max_rhat = float(summary["R_hat"].max()) if "R_hat" in summary else float("nan")
        if np.isfinite(max_rhat) and max_rhat > 1.01:
            warnings.append(f"Stan convergence warning: max R_hat={max_rhat:.4f} > 1.01.")

        return beta_draws, tuple(warnings)


def _result_from_draws(
    *,
    design: MLNMRDesignData,
    draws: np.ndarray,
    spec: BayesianMLNMRSpec,
    backend_used: str,
    warnings: tuple[str, ...],
) -> BayesianMLNMRFitResult:
    if draws.ndim != 2 or draws.shape[0] < 1:
        raise ValidationError("Posterior draws are empty.")

    p = draws.shape[1]
    k = len(design.parameter_treatments)
    if p != (2 * k) + 1:
        raise ValidationError("Posterior draw parameter dimension mismatch.")

    means = np.mean(draws, axis=0)
    if draws.shape[0] > 1:
        cov = np.cov(draws, rowvar=False)
    else:
        cov = np.zeros((p, p), dtype=float)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]], dtype=float)

    treatment_effects = {spec.reference_treatment: 0.0}
    treatment_ses = {spec.reference_treatment: 0.0}
    interaction_effects = {spec.reference_treatment: 0.0}
    interaction_ses = {spec.reference_treatment: 0.0}

    for idx, treatment in enumerate(design.parameter_treatments):
        treatment_effects[treatment] = float(means[idx])
        treatment_ses[treatment] = math.sqrt(max(float(cov[idx, idx]), 0.0))
        g_idx = k + idx
        interaction_effects[treatment] = float(means[g_idx])
        interaction_ses[treatment] = math.sqrt(max(float(cov[g_idx, g_idx]), 0.0))

    beta_main_idx = 2 * k
    beta_main = float(means[beta_main_idx])
    beta_main_se = math.sqrt(max(float(cov[beta_main_idx, beta_main_idx]), 0.0))

    return BayesianMLNMRFitResult(
        outcome_id=spec.outcome_id,
        covariate_name=spec.covariate_name,
        reference_treatment=spec.reference_treatment,
        backend_used=backend_used,
        prior_scale=spec.prior_scale,
        n_draws=int(draws.shape[0]),
        treatment_effects=treatment_effects,
        treatment_ses=treatment_ses,
        interaction_effects=interaction_effects,
        interaction_ses=interaction_ses,
        beta_main=beta_main,
        beta_main_se=beta_main_se,
        parameter_treatments=design.parameter_treatments,
        parameter_cov=np.asarray(cov, dtype=float),
        n_studies=design.n_studies,
        n_contrasts=design.n_contrasts,
        n_ipd_rows=design.n_ipd_rows,
        warnings=warnings,
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
    # Final fallback if covariance remains numerically unstable.
    eigvals, eigvecs = np.linalg.eigh(cov_pd)
    eigvals_clipped = np.clip(eigvals, a_min=0.0, a_max=None)
    stable_cov = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
    return rng.multivariate_normal(mean=mean, cov=stable_cov, size=n_draws)




