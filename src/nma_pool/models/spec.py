"""Declarative model specification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MeasureType = Literal["binary", "continuous"]
IntegrationMode = Literal["empirical", "normal_mc"]
DesignType = Literal["rct", "nrs", "other"]


@dataclass(frozen=True)
class ModelSpec:
    """Analysis specification for AD NMA model fitting."""

    outcome_id: str
    measure_type: MeasureType
    reference_treatment: str
    random_effects: bool = True


@dataclass(frozen=True)
class MLNMRSpec:
    """Specification for first-pass ML-NMR AD+IPD integration."""

    outcome_id: str
    reference_treatment: str
    covariate_name: str
    measure_type: Literal["continuous"] = "continuous"
    integration_mode: IntegrationMode = "empirical"
    random_effects: bool = False
    mc_samples: int = 2000
    mc_seed: int = 123


@dataclass(frozen=True)
class BayesianMLNMRSpec(MLNMRSpec):
    """Bayesian ML-NMR spec with backend selection."""

    backend: Literal["analytic", "stan"] = "analytic"
    prior_scale: float = 10.0
    n_draws: int = 2000
    n_warmup: int = 1000
    n_chains: int = 4
    seed: int = 123


@dataclass(frozen=True)
class SurvivalNPHSpec:
    """Specification for piecewise-exponential non-PH survival NMA."""

    outcome_id: str
    reference_treatment: str
    random_effects: bool = False
    continuity_correction: float = 0.5


@dataclass(frozen=True)
class BiasAdjustedSpec:
    """Specification for design-stratified bias-adjusted NMA."""

    outcome_id: str
    measure_type: MeasureType
    reference_treatment: str
    random_effects: bool = True
    reference_design: DesignType = "rct"
    bias_prior_sd: float = 1.0


@dataclass(frozen=True)
class BayesianBiasAdjustedSpec(BiasAdjustedSpec):
    """Bayesian spec for design-stratified bias-adjusted NMA."""

    backend: Literal["analytic", "stan"] = "analytic"
    treatment_prior_sd: float = 10.0
    n_draws: int = 2000
    n_warmup: int = 1000
    n_chains: int = 4
    seed: int = 123
