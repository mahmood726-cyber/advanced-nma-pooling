"""Publication-grade simulation and benchmark suite for methods manuscripts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping

import numpy as np

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import ModelSpec, SurvivalNPHSpec
from nma_pool.models.survival_nph import SurvivalNPHPooler
from nma_pool.validation.simulation import (
    ContinuousSimulationSpec,
    SurvivalNonPHSimulationSpec,
    simulate_continuous_abc_network,
    simulate_survival_nonph_network,
    survival_nonph_truth_log_hazard_ratios,
)


@dataclass(frozen=True)
class ModelAggregateMetrics:
    model: str
    n_networks: int
    n_estimates: int
    estimable_rate: float
    median_abs_bias: float
    rmse: float
    coverage_95: float
    mean_log_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "n_networks": self.n_networks,
            "n_estimates": self.n_estimates,
            "estimable_rate": self.estimable_rate,
            "median_abs_bias": self.median_abs_bias,
            "rmse": self.rmse,
            "coverage_95": self.coverage_95,
            "mean_log_score": self.mean_log_score,
        }


@dataclass(frozen=True)
class PredictiveSuperiority:
    """Paired predictive superiority diagnostics for candidate vs baseline."""

    n_pairs: int
    mean_delta_log_score: float | None
    median_delta_log_score: float | None
    ci95_lower: float | None
    ci95_upper: float | None
    superiority_probability: float | None
    one_sided_sign_p_value: float | None
    strict_win_rate: float | None
    tie_rate: float | None
    standardized_mean_delta: float | None
    one_sided_permutation_p_value: float | None = None
    one_sided_signed_rank_p_value: float | None = None
    permutation_method: str | None = None
    permutation_draws_used: int | None = None
    permutation_mcse: float | None = None
    signed_rank_method: str | None = None
    signed_rank_draws_used: int | None = None
    signed_rank_mcse: float | None = None
    superiority_probability_mcse: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_pairs": self.n_pairs,
            "mean_delta_log_score": self.mean_delta_log_score,
            "median_delta_log_score": self.median_delta_log_score,
            "ci95_lower": self.ci95_lower,
            "ci95_upper": self.ci95_upper,
            "superiority_probability": self.superiority_probability,
            "one_sided_sign_p_value": self.one_sided_sign_p_value,
            "one_sided_permutation_p_value": self.one_sided_permutation_p_value,
            "one_sided_signed_rank_p_value": self.one_sided_signed_rank_p_value,
            "strict_win_rate": self.strict_win_rate,
            "tie_rate": self.tie_rate,
            "standardized_mean_delta": self.standardized_mean_delta,
            "permutation_method": self.permutation_method,
            "permutation_draws_used": self.permutation_draws_used,
            "permutation_mcse": self.permutation_mcse,
            "signed_rank_method": self.signed_rank_method,
            "signed_rank_draws_used": self.signed_rank_draws_used,
            "signed_rank_mcse": self.signed_rank_mcse,
            "superiority_probability_mcse": self.superiority_probability_mcse,
        }


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario_id: str
    description: str
    baseline_model: str
    candidate_model: str
    metrics: tuple[ModelAggregateMetrics, ...]
    candidate_bias_improvement_fraction: float | None
    candidate_logscore_win_rate: float | None
    predictive_superiority: PredictiveSuperiority | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "baseline_model": self.baseline_model,
            "candidate_model": self.candidate_model,
            "candidate_bias_improvement_fraction": self.candidate_bias_improvement_fraction,
            "candidate_logscore_win_rate": self.candidate_logscore_win_rate,
            "predictive_superiority": (
                self.predictive_superiority.to_dict()
                if self.predictive_superiority is not None
                else None
            ),
            "metrics": [row.to_dict() for row in self.metrics],
        }

    def metric_by_model(self) -> dict[str, ModelAggregateMetrics]:
        return {row.model: row for row in self.metrics}


@dataclass(frozen=True)
class PublicationSuiteResult:
    created_at_utc: str
    python_version: str
    platform: str
    git_commit: str | None
    config_sha256: str
    thresholds: dict[str, float]
    continuous: ScenarioEvaluation
    survival_nonph: ScenarioEvaluation
    gates: dict[str, bool]
    overall_pass: bool
    inferential_adjustment_method: str | None = None
    inferential_adjusted_p_values: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "python_version": self.python_version,
            "platform": self.platform,
            "git_commit": self.git_commit,
            "config_sha256": self.config_sha256,
            "thresholds": self.thresholds,
            "continuous": self.continuous.to_dict(),
            "survival_nonph": self.survival_nonph.to_dict(),
            "gates": self.gates,
            "overall_pass": self.overall_pass,
            "inferential_adjustment_method": self.inferential_adjustment_method,
            "inferential_adjusted_p_values": self.inferential_adjusted_p_values or {},
        }

    def to_markdown(self) -> str:
        cont = self.continuous.metric_by_model()
        surv = self.survival_nonph.metric_by_model()
        lines = [
            "# Publication-Readiness Results",
            "",
            f"- `created_at_utc`: {self.created_at_utc}",
            f"- `overall_pass`: {self.overall_pass}",
            f"- `git_commit`: {self.git_commit or 'unknown'}",
            "",
            "## Gates",
        ]
        for key, passed in sorted(self.gates.items()):
            lines.append(f"- `{key}`: {'PASS' if passed else 'FAIL'}")
        lines.extend(
            [
                "",
                "## Continuous Scenario",
                f"- Candidate: `{self.continuous.candidate_model}`",
                f"- Baseline: `{self.continuous.baseline_model}`",
                f"- Candidate coverage: {_fmt_metric(cont[self.continuous.candidate_model].coverage_95)}",
                f"- Candidate median abs bias: {_fmt_metric(cont[self.continuous.candidate_model].median_abs_bias)}",
                f"- Candidate logscore win-rate vs baseline: {_fmt_metric(self.continuous.candidate_logscore_win_rate)}",
                f"- Mean logscore delta (candidate-baseline): {_fmt_metric(_superiority_metric(self.continuous, 'mean_delta_log_score'))}",
                f"- 95% CI for mean delta: [{_fmt_metric(_superiority_metric(self.continuous, 'ci95_lower'))}, {_fmt_metric(_superiority_metric(self.continuous, 'ci95_upper'))}]",
                f"- One-sided sign-test p-value: {_fmt_metric(_superiority_metric(self.continuous, 'one_sided_sign_p_value'))}",
                f"- One-sided permutation p-value: {_fmt_metric(_superiority_metric(self.continuous, 'one_sided_permutation_p_value'))}",
                f"- One-sided signed-rank p-value: {_fmt_metric(_superiority_metric(self.continuous, 'one_sided_signed_rank_p_value'))}",
                f"- Permutation method: {_superiority_text_metric(self.continuous, 'permutation_method')}",
                f"- Permutation draws used: {_fmt_metric(_superiority_metric(self.continuous, 'permutation_draws_used'))}",
                f"- Permutation p-value MCSE: {_fmt_metric(_superiority_metric(self.continuous, 'permutation_mcse'))}",
                f"- Signed-rank method: {_superiority_text_metric(self.continuous, 'signed_rank_method')}",
                f"- Signed-rank draws used: {_fmt_metric(_superiority_metric(self.continuous, 'signed_rank_draws_used'))}",
                f"- Signed-rank p-value MCSE: {_fmt_metric(_superiority_metric(self.continuous, 'signed_rank_mcse'))}",
                f"- Superiority probability (bootstrap): {_fmt_metric(_superiority_metric(self.continuous, 'superiority_probability'))}",
                f"- Superiority probability MCSE: {_fmt_metric(_superiority_metric(self.continuous, 'superiority_probability_mcse'))}",
                "",
                "## Survival Non-PH Scenario",
                f"- Candidate: `{self.survival_nonph.candidate_model}`",
                f"- Baseline: `{self.survival_nonph.baseline_model}`",
                f"- Candidate coverage: {_fmt_metric(surv[self.survival_nonph.candidate_model].coverage_95)}",
                f"- Candidate median abs bias: {_fmt_metric(surv[self.survival_nonph.candidate_model].median_abs_bias)}",
                f"- Baseline median abs bias: {_fmt_metric(surv[self.survival_nonph.baseline_model].median_abs_bias)}",
                f"- Candidate bias improvement: {_fmt_metric(self.survival_nonph.candidate_bias_improvement_fraction)}",
                f"- Candidate logscore win-rate vs baseline: {_fmt_metric(self.survival_nonph.candidate_logscore_win_rate)}",
                f"- Mean logscore delta (candidate-baseline): {_fmt_metric(_superiority_metric(self.survival_nonph, 'mean_delta_log_score'))}",
                f"- 95% CI for mean delta: [{_fmt_metric(_superiority_metric(self.survival_nonph, 'ci95_lower'))}, {_fmt_metric(_superiority_metric(self.survival_nonph, 'ci95_upper'))}]",
                f"- One-sided sign-test p-value: {_fmt_metric(_superiority_metric(self.survival_nonph, 'one_sided_sign_p_value'))}",
                f"- One-sided permutation p-value: {_fmt_metric(_superiority_metric(self.survival_nonph, 'one_sided_permutation_p_value'))}",
                f"- One-sided signed-rank p-value: {_fmt_metric(_superiority_metric(self.survival_nonph, 'one_sided_signed_rank_p_value'))}",
                f"- Permutation method: {_superiority_text_metric(self.survival_nonph, 'permutation_method')}",
                f"- Permutation draws used: {_fmt_metric(_superiority_metric(self.survival_nonph, 'permutation_draws_used'))}",
                f"- Permutation p-value MCSE: {_fmt_metric(_superiority_metric(self.survival_nonph, 'permutation_mcse'))}",
                f"- Signed-rank method: {_superiority_text_metric(self.survival_nonph, 'signed_rank_method')}",
                f"- Signed-rank draws used: {_fmt_metric(_superiority_metric(self.survival_nonph, 'signed_rank_draws_used'))}",
                f"- Signed-rank p-value MCSE: {_fmt_metric(_superiority_metric(self.survival_nonph, 'signed_rank_mcse'))}",
                f"- Superiority probability (bootstrap): {_fmt_metric(_superiority_metric(self.survival_nonph, 'superiority_probability'))}",
                f"- Superiority probability MCSE: {_fmt_metric(_superiority_metric(self.survival_nonph, 'superiority_probability_mcse'))}",
            ]
        )
        if self.inferential_adjustment_method and self.inferential_adjusted_p_values:
            lines.extend(
                [
                    "",
                    "## Multiplicity-Adjusted Inferential P-Values",
                    f"- Method: `{self.inferential_adjustment_method}`",
                ]
            )
            for key, value in sorted(self.inferential_adjusted_p_values.items()):
                lines.append(f"- `{key}`: {_fmt_metric(value)}")
        return "\n".join(lines) + "\n"


def run_publication_suite(config: Mapping[str, Any]) -> PublicationSuiteResult:
    thresholds_cfg = config.get("thresholds", {})
    coverage_lo = float(thresholds_cfg.get("coverage_lo", 0.93))
    coverage_hi = float(thresholds_cfg.get("coverage_hi", 0.97))
    bias_improvement_min = float(thresholds_cfg.get("bias_improvement_min", 0.20))
    logscore_win_rate_min = float(thresholds_cfg.get("logscore_win_rate_min", 0.80))
    continuous_logscore_win_rate_min = float(
        thresholds_cfg.get("continuous_logscore_win_rate_min", 0.70)
    )
    continuous_logscore_delta_ci95_lb_min = _optional_float(
        thresholds_cfg.get("continuous_logscore_delta_ci95_lb_min")
    )
    continuous_logscore_sign_p_max = _optional_float(
        thresholds_cfg.get("continuous_logscore_sign_p_max")
    )
    continuous_logscore_signed_rank_p_max = _optional_float(
        thresholds_cfg.get("continuous_logscore_signed_rank_p_max")
    )
    continuous_superiority_probability_min = _optional_float(
        thresholds_cfg.get("continuous_superiority_probability_min")
    )
    continuous_logscore_permutation_p_max = _optional_float(
        thresholds_cfg.get("continuous_logscore_permutation_p_max")
    )
    continuous_logscore_permutation_mcse_max = _optional_float(
        thresholds_cfg.get("continuous_logscore_permutation_mcse_max")
    )
    continuous_superiority_probability_mcse_max = _optional_float(
        thresholds_cfg.get("continuous_superiority_probability_mcse_max")
    )
    survival_logscore_delta_ci95_lb_min = _optional_float(
        thresholds_cfg.get("survival_logscore_delta_ci95_lb_min")
    )
    survival_logscore_sign_p_max = _optional_float(
        thresholds_cfg.get("survival_logscore_sign_p_max")
    )
    survival_logscore_signed_rank_p_max = _optional_float(
        thresholds_cfg.get("survival_logscore_signed_rank_p_max")
    )
    survival_superiority_probability_min = _optional_float(
        thresholds_cfg.get("survival_superiority_probability_min")
    )
    survival_logscore_permutation_p_max = _optional_float(
        thresholds_cfg.get("survival_logscore_permutation_p_max")
    )
    survival_logscore_permutation_mcse_max = _optional_float(
        thresholds_cfg.get("survival_logscore_permutation_mcse_max")
    )
    survival_superiority_probability_mcse_max = _optional_float(
        thresholds_cfg.get("survival_superiority_probability_mcse_max")
    )
    familywise_holm_alpha = _optional_float(thresholds_cfg.get("familywise_holm_alpha"))
    require_git_commit = parse_bool_value(
        config.get("require_git_commit", False),
        field_name="require_git_commit",
    )

    _validate_thresholds(
        coverage_lo=coverage_lo,
        coverage_hi=coverage_hi,
        bias_improvement_min=bias_improvement_min,
        logscore_win_rate_min=logscore_win_rate_min,
        continuous_logscore_win_rate_min=continuous_logscore_win_rate_min,
        continuous_logscore_delta_ci95_lb_min=continuous_logscore_delta_ci95_lb_min,
        continuous_logscore_sign_p_max=continuous_logscore_sign_p_max,
        continuous_logscore_signed_rank_p_max=continuous_logscore_signed_rank_p_max,
        continuous_superiority_probability_min=continuous_superiority_probability_min,
        continuous_logscore_permutation_p_max=continuous_logscore_permutation_p_max,
        continuous_logscore_permutation_mcse_max=continuous_logscore_permutation_mcse_max,
        continuous_superiority_probability_mcse_max=continuous_superiority_probability_mcse_max,
        survival_logscore_delta_ci95_lb_min=survival_logscore_delta_ci95_lb_min,
        survival_logscore_sign_p_max=survival_logscore_sign_p_max,
        survival_logscore_signed_rank_p_max=survival_logscore_signed_rank_p_max,
        survival_superiority_probability_min=survival_superiority_probability_min,
        survival_logscore_permutation_p_max=survival_logscore_permutation_p_max,
        survival_logscore_permutation_mcse_max=survival_logscore_permutation_mcse_max,
        survival_superiority_probability_mcse_max=survival_superiority_probability_mcse_max,
        familywise_holm_alpha=familywise_holm_alpha,
    )

    continuous_cfg = _as_dict(config.get("continuous"))
    survival_cfg = _as_dict(config.get("survival_nonph"))
    continuity_correction = float(config.get("continuity_correction", 0.5))
    _validate_positive_finite("continuity_correction", continuity_correction)

    continuous_eval = _evaluate_continuous_scenario(continuous_cfg)
    survival_eval = _evaluate_survival_nonph_scenario(
        survival_cfg,
        continuity_correction=continuity_correction,
    )
    git_commit = _try_git_commit()

    cont_candidate = continuous_eval.metric_by_model()[continuous_eval.candidate_model]
    surv_candidate = survival_eval.metric_by_model()[survival_eval.candidate_model]

    gates = {
        "continuous_coverage_95_in_target": _within_closed_interval(
            cont_candidate.coverage_95,
            lo=coverage_lo,
            hi=coverage_hi,
        ),
        "continuous_logscore_win_rate_vs_baseline": _meets_minimum(
            continuous_eval.candidate_logscore_win_rate,
            minimum=continuous_logscore_win_rate_min,
        ),
        "survival_coverage_95_in_target": _within_closed_interval(
            surv_candidate.coverage_95,
            lo=coverage_lo,
            hi=coverage_hi,
        ),
        "survival_bias_improvement_vs_baseline": _meets_minimum(
            survival_eval.candidate_bias_improvement_fraction,
            minimum=bias_improvement_min,
        ),
        "survival_logscore_win_rate_vs_baseline": _meets_minimum(
            survival_eval.candidate_logscore_win_rate,
            minimum=logscore_win_rate_min,
        ),
    }
    if require_git_commit:
        gates["git_commit_present"] = bool(git_commit)

    if continuous_logscore_delta_ci95_lb_min is not None:
        gates["continuous_logscore_delta_ci95_lb_vs_baseline"] = _meets_minimum(
            _superiority_metric(continuous_eval, "ci95_lower"),
            minimum=continuous_logscore_delta_ci95_lb_min,
        )
    if continuous_logscore_sign_p_max is not None:
        gates["continuous_logscore_sign_test_p_vs_baseline"] = _at_most(
            _superiority_metric(continuous_eval, "one_sided_sign_p_value"),
            maximum=continuous_logscore_sign_p_max,
        )
    if continuous_logscore_signed_rank_p_max is not None:
        gates["continuous_logscore_signed_rank_p_vs_baseline"] = _at_most(
            _superiority_metric(continuous_eval, "one_sided_signed_rank_p_value"),
            maximum=continuous_logscore_signed_rank_p_max,
        )
    if continuous_superiority_probability_min is not None:
        gates["continuous_superiority_probability_vs_baseline"] = _meets_minimum(
            _superiority_metric(continuous_eval, "superiority_probability"),
            minimum=continuous_superiority_probability_min,
        )
    if continuous_logscore_permutation_p_max is not None:
        gates["continuous_logscore_permutation_p_vs_baseline"] = _at_most(
            _superiority_metric(continuous_eval, "one_sided_permutation_p_value"),
            maximum=continuous_logscore_permutation_p_max,
        )
    if continuous_logscore_permutation_mcse_max is not None:
        gates["continuous_logscore_permutation_mcse_within_max"] = _at_most(
            _superiority_metric(continuous_eval, "permutation_mcse"),
            maximum=continuous_logscore_permutation_mcse_max,
        )
    if continuous_superiority_probability_mcse_max is not None:
        gates["continuous_superiority_probability_mcse_within_max"] = _at_most(
            _superiority_metric(continuous_eval, "superiority_probability_mcse"),
            maximum=continuous_superiority_probability_mcse_max,
        )
    if survival_logscore_delta_ci95_lb_min is not None:
        gates["survival_logscore_delta_ci95_lb_vs_baseline"] = _meets_minimum(
            _superiority_metric(survival_eval, "ci95_lower"),
            minimum=survival_logscore_delta_ci95_lb_min,
        )
    if survival_logscore_sign_p_max is not None:
        gates["survival_logscore_sign_test_p_vs_baseline"] = _at_most(
            _superiority_metric(survival_eval, "one_sided_sign_p_value"),
            maximum=survival_logscore_sign_p_max,
        )
    if survival_logscore_signed_rank_p_max is not None:
        gates["survival_logscore_signed_rank_p_vs_baseline"] = _at_most(
            _superiority_metric(survival_eval, "one_sided_signed_rank_p_value"),
            maximum=survival_logscore_signed_rank_p_max,
        )
    if survival_superiority_probability_min is not None:
        gates["survival_superiority_probability_vs_baseline"] = _meets_minimum(
            _superiority_metric(survival_eval, "superiority_probability"),
            minimum=survival_superiority_probability_min,
        )
    if survival_logscore_permutation_p_max is not None:
        gates["survival_logscore_permutation_p_vs_baseline"] = _at_most(
            _superiority_metric(survival_eval, "one_sided_permutation_p_value"),
            maximum=survival_logscore_permutation_p_max,
        )
    if survival_logscore_permutation_mcse_max is not None:
        gates["survival_logscore_permutation_mcse_within_max"] = _at_most(
            _superiority_metric(survival_eval, "permutation_mcse"),
            maximum=survival_logscore_permutation_mcse_max,
        )
    if survival_superiority_probability_mcse_max is not None:
        gates["survival_superiority_probability_mcse_within_max"] = _at_most(
            _superiority_metric(survival_eval, "superiority_probability_mcse"),
            maximum=survival_superiority_probability_mcse_max,
        )
    inferential_adjusted_p_values: dict[str, float] = {}
    if familywise_holm_alpha is not None:
        raw_p_values = _inferential_raw_p_values(
            continuous=continuous_eval,
            survival=survival_eval,
        )
        inferential_adjusted_p_values = _holm_adjusted_p_values(raw_p_values)
        for key in _inferential_expected_keys():
            adjusted = inferential_adjusted_p_values.get(key)
            gates[f"{key}_holm_adjusted_p_vs_baseline"] = _at_most(
                adjusted,
                maximum=familywise_holm_alpha,
            )
    overall_pass = all(gates.values())

    config_sha = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return PublicationSuiteResult(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        git_commit=git_commit,
        config_sha256=config_sha,
        thresholds={
            "coverage_lo": coverage_lo,
            "coverage_hi": coverage_hi,
            "bias_improvement_min": bias_improvement_min,
            "logscore_win_rate_min": logscore_win_rate_min,
            "continuous_logscore_win_rate_min": continuous_logscore_win_rate_min,
            **_optional_threshold_dict(
                continuous_logscore_delta_ci95_lb_min=continuous_logscore_delta_ci95_lb_min,
                continuous_logscore_sign_p_max=continuous_logscore_sign_p_max,
                continuous_logscore_signed_rank_p_max=continuous_logscore_signed_rank_p_max,
                continuous_superiority_probability_min=continuous_superiority_probability_min,
                continuous_logscore_permutation_p_max=continuous_logscore_permutation_p_max,
                continuous_logscore_permutation_mcse_max=continuous_logscore_permutation_mcse_max,
                continuous_superiority_probability_mcse_max=continuous_superiority_probability_mcse_max,
                survival_logscore_delta_ci95_lb_min=survival_logscore_delta_ci95_lb_min,
                survival_logscore_sign_p_max=survival_logscore_sign_p_max,
                survival_logscore_signed_rank_p_max=survival_logscore_signed_rank_p_max,
                survival_superiority_probability_min=survival_superiority_probability_min,
                survival_logscore_permutation_p_max=survival_logscore_permutation_p_max,
                survival_logscore_permutation_mcse_max=survival_logscore_permutation_mcse_max,
                survival_superiority_probability_mcse_max=survival_superiority_probability_mcse_max,
                familywise_holm_alpha=familywise_holm_alpha,
            ),
        },
        continuous=continuous_eval,
        survival_nonph=survival_eval,
        gates=gates,
        overall_pass=overall_pass,
        inferential_adjustment_method=(
            "holm" if familywise_holm_alpha is not None else None
        ),
        inferential_adjusted_p_values=inferential_adjusted_p_values,
    )


def _evaluate_continuous_scenario(cfg: Mapping[str, Any]) -> ScenarioEvaluation:
    n_networks = int(cfg.get("n_networks", 120))
    seed_start = int(cfg.get("seed_start", 1000))
    n_per_arm = int(cfg.get("n_per_arm", 120))
    se = float(cfg.get("se", 0.25))
    noise_sd = float(cfg.get("noise_sd", 0.25))
    study_heterogeneity_sd = float(cfg.get("study_heterogeneity_sd", 0.0))
    bootstrap_draws = int(cfg.get("bootstrap_draws", 2500))
    bootstrap_seed = int(cfg.get("bootstrap_seed", seed_start + 1777))
    permutation_draws = int(cfg.get("permutation_draws", 20000))
    permutation_seed = int(cfg.get("permutation_seed", seed_start + 2783))
    permutation_exact_max_pairs = int(cfg.get("permutation_exact_max_pairs", 20))
    selection_mode = str(cfg.get("selection_mode", "pre_specified")).strip().lower()
    requested_candidate_model = str(cfg.get("candidate_model", "core_fixed_effects"))
    requested_baseline_model = str(cfg.get("baseline_model", "core_random_effects"))
    selection_holdout_fraction = float(cfg.get("selection_holdout_fraction", 0.5))
    selection_split_seed = int(cfg.get("selection_split_seed", seed_start + 3889))

    _validate_int_at_least("continuous.n_networks", n_networks, 1)
    _validate_int_at_least("continuous.n_per_arm", n_per_arm, 1)
    _validate_int_at_least("continuous.bootstrap_draws", bootstrap_draws, 200)
    _validate_int_at_least("continuous.permutation_draws", permutation_draws, 1000)
    _validate_int_at_least("continuous.permutation_exact_max_pairs", permutation_exact_max_pairs, 1)
    if permutation_exact_max_pairs > 24:
        raise ValueError("continuous.permutation_exact_max_pairs must be <= 24.")
    _validate_finite("continuous.seed_start", float(seed_start))
    _validate_finite("continuous.bootstrap_seed", float(bootstrap_seed))
    _validate_finite("continuous.permutation_seed", float(permutation_seed))
    _validate_finite("continuous.selection_holdout_fraction", selection_holdout_fraction)
    _validate_finite("continuous.selection_split_seed", float(selection_split_seed))
    _validate_positive_finite("continuous.se", se)
    _validate_non_negative_finite("continuous.noise_sd", noise_sd)
    _validate_non_negative_finite(
        "continuous.study_heterogeneity_sd",
        study_heterogeneity_sd,
    )
    _validate_continuous_selection(
        selection_mode=selection_mode,
        candidate_model=requested_candidate_model,
        baseline_model=requested_baseline_model,
        holdout_fraction=selection_holdout_fraction,
    )

    truth = {"A": 0.0, "B": 1.0, "C": 2.0}
    estimate_records: dict[str, list[tuple[float, float, bool, bool]]] = {
        "core_fixed_effects": [],
        "core_random_effects": [],
    }
    network_scores: dict[str, list[float]] = {
        "core_fixed_effects": [],
        "core_random_effects": [],
    }

    for offset in range(n_networks):
        sim_seed = seed_start + offset
        payload = simulate_continuous_abc_network(
            ContinuousSimulationSpec(
                seed=sim_seed,
                n_per_arm=n_per_arm,
                se=se,
                noise_sd=noise_sd,
            )
        )
        if study_heterogeneity_sd > 0:
            _inject_study_heterogeneity(
                payload=payload,
                seed=sim_seed + 7919,
                heterogeneity_sd=study_heterogeneity_sd,
            )
        dataset = DatasetBuilder().from_payload(payload)
        fit_fixed = ADNMAPooler().fit(
            dataset,
            ModelSpec(
                outcome_id="efficacy",
                measure_type="continuous",
                reference_treatment="A",
                random_effects=False,
            ),
        )
        fit_random = ADNMAPooler().fit(
            dataset,
            ModelSpec(
                outcome_id="efficacy",
                measure_type="continuous",
                reference_treatment="A",
                random_effects=True,
            ),
        )

        model_map = {
            "core_fixed_effects": fit_fixed,
            "core_random_effects": fit_random,
        }
        for model_name, fit in model_map.items():
            per_network_log_scores: list[float] = []
            for treatment in ("B", "C"):
                estimate = fit.treatment_effects[treatment]
                se_est = fit.treatment_ses[treatment]
                target = truth[treatment]
                estimable = bool(np.isfinite(estimate) and np.isfinite(se_est) and se_est > 0)
                covered = estimable and ((estimate - (1.96 * se_est)) <= target <= (estimate + (1.96 * se_est)))
                estimate_records[model_name].append((estimate, target, covered, estimable))
                if estimable:
                    per_network_log_scores.append(_gaussian_log_score(target=target, mean=estimate, se=se_est))
            network_scores[model_name].append(
                float(np.mean(per_network_log_scores)) if per_network_log_scores else float("nan")
            )

    metrics = tuple(
        _aggregate_model_metrics(
            model=name,
            n_networks=n_networks,
            records=estimate_records[name],
            network_log_scores=network_scores[name],
        )
        for name in ("core_fixed_effects", "core_random_effects")
    )
    metric_map = _metric_by_name(metrics)
    candidate_model, baseline_model, eval_candidate_scores, eval_baseline_scores = (
        _continuous_pair_and_eval_scores(
            network_scores=network_scores,
            selection_mode=selection_mode,
            requested_candidate_model=requested_candidate_model,
            requested_baseline_model=requested_baseline_model,
            selection_holdout_fraction=selection_holdout_fraction,
            selection_split_seed=selection_split_seed,
        )
    )
    win_rate = _win_rate(
        candidate=eval_candidate_scores,
        baseline=eval_baseline_scores,
    )
    superiority = _predictive_superiority(
        candidate=eval_candidate_scores,
        baseline=eval_baseline_scores,
        bootstrap_draws=bootstrap_draws,
        bootstrap_seed=bootstrap_seed,
        permutation_draws=permutation_draws,
        permutation_seed=permutation_seed,
        permutation_exact_max_pairs=permutation_exact_max_pairs,
    )
    bias_improvement = _bias_improvement_fraction(
        candidate=metric_map[candidate_model].median_abs_bias,
        baseline=metric_map[baseline_model].median_abs_bias,
    )
    return ScenarioEvaluation(
        scenario_id="continuous_abc",
        description=(
            "Continuous A-B-C network calibration scenario "
            f"(selection_mode={selection_mode})."
        ),
        baseline_model=baseline_model,
        candidate_model=candidate_model,
        metrics=metrics,
        candidate_bias_improvement_fraction=bias_improvement,
        candidate_logscore_win_rate=win_rate,
        predictive_superiority=superiority,
    )


def _evaluate_survival_nonph_scenario(
    cfg: Mapping[str, Any],
    *,
    continuity_correction: float,
) -> ScenarioEvaluation:
    n_networks = int(cfg.get("n_networks", 100))
    seed_start = int(cfg.get("seed_start", 2000))
    n_per_arm = int(cfg.get("n_per_arm", 650))
    replicates_per_pair = int(cfg.get("replicates_per_pair", 2))
    follow_up_fraction = float(cfg.get("follow_up_fraction", 0.85))
    bootstrap_draws = int(cfg.get("bootstrap_draws", 2500))
    bootstrap_seed = int(cfg.get("bootstrap_seed", seed_start + 2777))
    permutation_draws = int(cfg.get("permutation_draws", 20000))
    permutation_seed = int(cfg.get("permutation_seed", seed_start + 3787))
    permutation_exact_max_pairs = int(cfg.get("permutation_exact_max_pairs", 20))

    _validate_int_at_least("survival_nonph.n_networks", n_networks, 1)
    _validate_int_at_least("survival_nonph.n_per_arm", n_per_arm, 1)
    _validate_int_at_least("survival_nonph.replicates_per_pair", replicates_per_pair, 1)
    _validate_int_at_least("survival_nonph.bootstrap_draws", bootstrap_draws, 200)
    _validate_int_at_least("survival_nonph.permutation_draws", permutation_draws, 1000)
    _validate_int_at_least("survival_nonph.permutation_exact_max_pairs", permutation_exact_max_pairs, 1)
    if permutation_exact_max_pairs > 24:
        raise ValueError("survival_nonph.permutation_exact_max_pairs must be <= 24.")
    _validate_finite("survival_nonph.seed_start", float(seed_start))
    _validate_finite("survival_nonph.bootstrap_seed", float(bootstrap_seed))
    _validate_finite("survival_nonph.permutation_seed", float(permutation_seed))
    _validate_probability("survival_nonph.follow_up_fraction", follow_up_fraction)
    _validate_positive_finite("continuity_correction", continuity_correction)

    estimate_records: dict[str, list[tuple[float, float, bool, bool]]] = {
        "survival_ph_fixed_effects": [],
        "survival_nph_fixed_effects": [],
        "survival_nph_random_effects": [],
    }
    network_scores: dict[str, list[float]] = {
        "survival_ph_fixed_effects": [],
        "survival_nph_fixed_effects": [],
        "survival_nph_random_effects": [],
    }

    for offset in range(n_networks):
        sim_seed = seed_start + offset
        sim_spec = SurvivalNonPHSimulationSpec(
            seed=sim_seed,
            n_per_arm=n_per_arm,
            replicates_per_pair=replicates_per_pair,
            follow_up_fraction=follow_up_fraction,
        )
        payload = simulate_survival_nonph_network(sim_spec)
        truth = survival_nonph_truth_log_hazard_ratios(sim_spec)
        dataset = DatasetBuilder().from_payload(payload)

        nph_fixed = SurvivalNPHPooler().fit(
            dataset,
            SurvivalNPHSpec(
                outcome_id="os",
                reference_treatment="A",
                random_effects=False,
                continuity_correction=continuity_correction,
            ),
        )
        nph_random = SurvivalNPHPooler().fit(
            dataset,
            SurvivalNPHSpec(
                outcome_id="os",
                reference_treatment="A",
                random_effects=True,
                continuity_correction=continuity_correction,
            ),
        )
        ph_payload = _collapse_survival_to_ph_payload(
            payload=payload,
            continuity_correction=continuity_correction,
        )
        ph_dataset = DatasetBuilder().from_payload(ph_payload)
        ph_fit = ADNMAPooler().fit(
            ph_dataset,
            ModelSpec(
                outcome_id="os",
                measure_type="continuous",
                reference_treatment="A",
                random_effects=False,
            ),
        )

        # PH baseline: one effect per treatment reused across all intervals.
        ph_network_scores: list[float] = []
        for interval_id in nph_fixed.interval_ids:
            for treatment in ("B", "C"):
                target = truth[interval_id][treatment]
                estimate = ph_fit.treatment_effects[treatment]
                se_est = ph_fit.treatment_ses[treatment]
                estimable = bool(np.isfinite(estimate) and np.isfinite(se_est) and se_est > 0)
                covered = estimable and ((estimate - (1.96 * se_est)) <= target <= (estimate + (1.96 * se_est)))
                estimate_records["survival_ph_fixed_effects"].append((estimate, target, covered, estimable))
                if estimable:
                    ph_network_scores.append(_gaussian_log_score(target=target, mean=estimate, se=se_est))
        network_scores["survival_ph_fixed_effects"].append(
            float(np.mean(ph_network_scores)) if ph_network_scores else float("nan")
        )

        _accumulate_survival_model_records(
            fit=nph_fixed,
            model_name="survival_nph_fixed_effects",
            truth=truth,
            estimate_records=estimate_records,
            network_scores=network_scores,
        )
        _accumulate_survival_model_records(
            fit=nph_random,
            model_name="survival_nph_random_effects",
            truth=truth,
            estimate_records=estimate_records,
            network_scores=network_scores,
        )

    metrics = tuple(
        _aggregate_model_metrics(
            model=name,
            n_networks=n_networks,
            records=estimate_records[name],
            network_log_scores=network_scores[name],
        )
        for name in (
            "survival_ph_fixed_effects",
            "survival_nph_fixed_effects",
            "survival_nph_random_effects",
        )
    )
    metric_map = _metric_by_name(metrics)
    win_rate = _win_rate(
        candidate=network_scores["survival_nph_random_effects"],
        baseline=network_scores["survival_ph_fixed_effects"],
    )
    superiority = _predictive_superiority(
        candidate=network_scores["survival_nph_random_effects"],
        baseline=network_scores["survival_ph_fixed_effects"],
        bootstrap_draws=bootstrap_draws,
        bootstrap_seed=bootstrap_seed,
        permutation_draws=permutation_draws,
        permutation_seed=permutation_seed,
        permutation_exact_max_pairs=permutation_exact_max_pairs,
    )
    bias_improvement = _bias_improvement_fraction(
        candidate=metric_map["survival_nph_random_effects"].median_abs_bias,
        baseline=metric_map["survival_ph_fixed_effects"].median_abs_bias,
    )
    return ScenarioEvaluation(
        scenario_id="survival_nonph_abc",
        description="Piecewise exponential non-PH scenario comparing NPH vs PH baseline.",
        baseline_model="survival_ph_fixed_effects",
        candidate_model="survival_nph_random_effects",
        metrics=metrics,
        candidate_bias_improvement_fraction=bias_improvement,
        candidate_logscore_win_rate=win_rate,
        predictive_superiority=superiority,
    )


def _accumulate_survival_model_records(
    *,
    fit: Any,
    model_name: str,
    truth: Mapping[str, Mapping[str, float]],
    estimate_records: dict[str, list[tuple[float, float, bool, bool]]],
    network_scores: dict[str, list[float]],
) -> None:
    per_network_log_scores: list[float] = []
    for interval_id in fit.interval_ids:
        for treatment in ("B", "C"):
            target = truth[interval_id][treatment]
            estimate = fit.treatment_effects_by_interval[interval_id][treatment]
            se_est = fit.treatment_ses_by_interval[interval_id][treatment]
            estimable_flag = bool(fit.estimable_by_interval[interval_id][treatment])
            estimable = bool(
                estimable_flag
                and np.isfinite(estimate)
                and np.isfinite(se_est)
                and se_est > 0
            )
            covered = estimable and ((estimate - (1.96 * se_est)) <= target <= (estimate + (1.96 * se_est)))
            estimate_records[model_name].append((estimate, target, covered, estimable))
            if estimable:
                per_network_log_scores.append(_gaussian_log_score(target=target, mean=estimate, se=se_est))
    network_scores[model_name].append(
        float(np.mean(per_network_log_scores)) if per_network_log_scores else float("nan")
    )


def _collapse_survival_to_ph_payload(
    *,
    payload: Mapping[str, Any],
    continuity_correction: float,
) -> dict[str, Any]:
    studies = payload.get("studies", [])
    arms = payload.get("arms", [])
    survival_ad = payload.get("survival_ad", [])

    grouped: dict[tuple[str, str], dict[str, float]] = {}
    for row in survival_ad:
        study_id = str(row["study_id"])
        arm_id = str(row["arm_id"])
        key = (study_id, arm_id)
        if key not in grouped:
            grouped[key] = {"events": 0.0, "person_time": 0.0}
        grouped[key]["events"] += float(row["events"])
        grouped[key]["person_time"] += float(row["person_time"])

    outcomes_ad: list[dict[str, Any]] = []
    for arm in arms:
        key = (str(arm["study_id"]), str(arm["arm_id"]))
        sums = grouped.get(key)
        if sums is None:
            continue
        events = sums["events"]
        person_time = sums["person_time"]
        if person_time <= 0:
            continue
        log_hazard = math.log((events + continuity_correction) / person_time)
        se = math.sqrt(1.0 / (events + continuity_correction))
        outcomes_ad.append(
            {
                "study_id": key[0],
                "arm_id": key[1],
                "outcome_id": "os",
                "measure_type": "continuous",
                "value": float(log_hazard),
                "se": float(se),
            }
        )
    return {
        "studies": studies,
        "arms": arms,
        "outcomes_ad": outcomes_ad,
    }


def _inject_study_heterogeneity(
    *,
    payload: dict[str, Any],
    seed: int,
    heterogeneity_sd: float,
) -> None:
    if heterogeneity_sd <= 0:
        return
    rng = np.random.default_rng(seed)
    arm_to_treatment = {
        (str(row["study_id"]), str(row["arm_id"])): str(row["treatment_id"])
        for row in payload.get("arms", [])
    }
    offsets: dict[tuple[str, str], float] = {}
    for outcome in payload.get("outcomes_ad", []):
        study_id = str(outcome["study_id"])
        arm_id = str(outcome["arm_id"])
        treatment = arm_to_treatment.get((study_id, arm_id))
        if treatment is None or treatment == "A":
            continue
        key = (study_id, treatment)
        if key not in offsets:
            offsets[key] = float(rng.normal(loc=0.0, scale=heterogeneity_sd))
        outcome["value"] = float(outcome["value"]) + offsets[key]


def _aggregate_model_metrics(
    *,
    model: str,
    n_networks: int,
    records: list[tuple[float, float, bool, bool]],
    network_log_scores: list[float],
) -> ModelAggregateMetrics:
    errors: list[float] = []
    abs_errors: list[float] = []
    covered: list[bool] = []
    estimable_count = 0
    for estimate, target, is_covered, estimable in records:
        if not estimable or not np.isfinite(estimate):
            continue
        estimable_count += 1
        err = float(estimate - target)
        errors.append(err)
        abs_errors.append(abs(err))
        covered.append(bool(is_covered))

    if not errors:
        return ModelAggregateMetrics(
            model=model,
            n_networks=n_networks,
            n_estimates=0,
            estimable_rate=0.0,
            median_abs_bias=float("nan"),
            rmse=float("nan"),
            coverage_95=float("nan"),
            mean_log_score=float("nan"),
        )

    finite_scores = [score for score in network_log_scores if np.isfinite(score)]
    return ModelAggregateMetrics(
        model=model,
        n_networks=n_networks,
        n_estimates=len(errors),
        estimable_rate=float(estimable_count / len(records)) if records else 0.0,
        median_abs_bias=float(np.median(np.asarray(abs_errors, dtype=float))),
        rmse=float(np.sqrt(np.mean(np.square(np.asarray(errors, dtype=float))))),
        coverage_95=float(np.mean(np.asarray(covered, dtype=float))),
        mean_log_score=float(np.mean(np.asarray(finite_scores, dtype=float)))
        if finite_scores
        else float("nan"),
    )


def _gaussian_log_score(*, target: float, mean: float, se: float) -> float:
    var = max(se * se, 1e-10)
    return float(-0.5 * (math.log(2.0 * math.pi * var) + (((target - mean) ** 2) / var)))


def _win_rate(*, candidate: list[float], baseline: list[float]) -> float:
    wins = 0
    losses = 0
    for c, b in zip(candidate, baseline, strict=True):
        if not np.isfinite(c) or not np.isfinite(b):
            continue
        if c > b:
            wins += 1
        elif c < b:
            losses += 1
    non_tie = wins + losses
    if non_tie == 0:
        return float("nan")
    return float(wins / non_tie)


def _predictive_superiority(
    *,
    candidate: list[float],
    baseline: list[float],
    bootstrap_draws: int,
    bootstrap_seed: int,
    permutation_draws: int,
    permutation_seed: int,
    permutation_exact_max_pairs: int,
) -> PredictiveSuperiority:
    deltas, strict_wins, strict_losses, ties = _paired_deltas(
        candidate=candidate,
        baseline=baseline,
    )
    n_pairs = int(deltas.shape[0])
    if n_pairs == 0:
        return PredictiveSuperiority(
            n_pairs=0,
            mean_delta_log_score=None,
            median_delta_log_score=None,
            ci95_lower=None,
            ci95_upper=None,
            superiority_probability=None,
            one_sided_sign_p_value=None,
            one_sided_permutation_p_value=None,
            one_sided_signed_rank_p_value=None,
            strict_win_rate=None,
            tie_rate=None,
            standardized_mean_delta=None,
            permutation_method=None,
            permutation_draws_used=None,
            permutation_mcse=None,
            signed_rank_method=None,
            signed_rank_draws_used=None,
            signed_rank_mcse=None,
            superiority_probability_mcse=None,
        )

    mean_delta = float(np.mean(deltas))
    median_delta = float(np.median(deltas))
    std_delta = float(np.std(deltas, ddof=1)) if n_pairs > 1 else float("nan")
    standardized = float(mean_delta / std_delta) if np.isfinite(std_delta) and std_delta > 0 else None

    ci_low, ci_high, superiority_probability, superiority_probability_mcse = _bootstrap_mean_delta_summary(
        deltas=deltas,
        n_draws=bootstrap_draws,
        seed=bootstrap_seed,
    )
    non_tie = strict_wins + strict_losses
    sign_p = _sign_test_p_value_one_sided(
        wins=strict_wins,
        non_tie_count=non_tie,
    )
    permutation_p, permutation_method, permutation_draws_used, permutation_mcse = (
        _paired_permutation_p_value_one_sided(
            deltas=deltas,
            n_draws=permutation_draws,
            seed=permutation_seed,
            exact_max_pairs=permutation_exact_max_pairs,
        )
    )
    signed_rank_p, signed_rank_method, signed_rank_draws_used, signed_rank_mcse = (
        _signed_rank_p_value_one_sided(
            deltas=deltas,
            n_draws=permutation_draws,
            seed=(permutation_seed + 104729),
            exact_max_pairs=permutation_exact_max_pairs,
        )
    )
    strict_win_rate = float(strict_wins / non_tie) if non_tie > 0 else None
    tie_rate = float(ties / n_pairs)

    return PredictiveSuperiority(
        n_pairs=n_pairs,
        mean_delta_log_score=mean_delta,
        median_delta_log_score=median_delta,
        ci95_lower=ci_low,
        ci95_upper=ci_high,
        superiority_probability=superiority_probability,
        one_sided_sign_p_value=sign_p,
        one_sided_permutation_p_value=permutation_p,
        one_sided_signed_rank_p_value=signed_rank_p,
        strict_win_rate=strict_win_rate,
        tie_rate=tie_rate,
        standardized_mean_delta=standardized,
        permutation_method=permutation_method,
        permutation_draws_used=permutation_draws_used,
        permutation_mcse=permutation_mcse,
        signed_rank_method=signed_rank_method,
        signed_rank_draws_used=signed_rank_draws_used,
        signed_rank_mcse=signed_rank_mcse,
        superiority_probability_mcse=superiority_probability_mcse,
    )


def _paired_deltas(
    *,
    candidate: list[float],
    baseline: list[float],
) -> tuple[np.ndarray, int, int, int]:
    values: list[float] = []
    strict_wins = 0
    strict_losses = 0
    ties = 0
    for c, b in zip(candidate, baseline, strict=True):
        if not np.isfinite(c) or not np.isfinite(b):
            continue
        delta = float(c - b)
        values.append(delta)
        if c > b:
            strict_wins += 1
        elif c < b:
            strict_losses += 1
        else:
            ties += 1
    return np.asarray(values, dtype=float), strict_wins, strict_losses, ties


def _bootstrap_mean_delta_summary(
    *,
    deltas: np.ndarray,
    n_draws: int,
    seed: int,
) -> tuple[float | None, float | None, float | None, float | None]:
    if deltas.ndim != 1 or deltas.size == 0:
        return None, None, None, None
    if n_draws < 1:
        return None, None, None, None
    n = int(deltas.shape[0])
    rng = np.random.default_rng(seed)
    draw_idx = rng.integers(low=0, high=n, size=(n_draws, n))
    sample_means = np.mean(deltas[draw_idx], axis=1)
    ci_low = float(np.quantile(sample_means, 0.025))
    ci_high = float(np.quantile(sample_means, 0.975))
    superiority_probability = float(np.mean(sample_means > 0.0))
    superiority_probability_mcse = float(
        math.sqrt(
            max(
                superiority_probability * (1.0 - superiority_probability),
                0.0,
            )
            / n_draws
        )
    )
    return ci_low, ci_high, superiority_probability, superiority_probability_mcse


def _sign_test_p_value_one_sided(*, wins: int, non_tie_count: int) -> float | None:
    if non_tie_count <= 0:
        return None
    # Exact one-sided binomial test under H0: p(win)=0.5
    tail = 0.0
    for k in range(wins, non_tie_count + 1):
        tail += math.comb(non_tie_count, k) * (0.5 ** non_tie_count)
    return float(min(max(tail, 0.0), 1.0))


def _paired_permutation_p_value_one_sided(
    *,
    deltas: np.ndarray,
    n_draws: int,
    seed: int,
    exact_max_pairs: int,
) -> tuple[float | None, str | None, int | None, float | None]:
    if deltas.ndim != 1 or deltas.size == 0:
        return None, None, None, None
    if n_draws < 1:
        return None, None, None, None
    observed = float(np.mean(deltas))
    n = int(deltas.shape[0])

    if n <= exact_max_pairs:
        total = 1 << n
        ge = 0
        for mask in range(total):
            signed_sum = 0.0
            for idx, delta in enumerate(deltas):
                sign = -1.0 if ((mask >> idx) & 1) else 1.0
                signed_sum += sign * float(delta)
            if (signed_sum / n) >= observed:
                ge += 1
        p_value = float(ge / total)
        return p_value, "exact", total, 0.0

    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0], dtype=float), size=(n_draws, n), replace=True)
    perm_means = np.mean(signs * deltas[np.newaxis, :], axis=1)
    ge = int(np.sum(perm_means >= observed))
    p_value = float((ge + 1) / (n_draws + 1))
    mcse = float(math.sqrt(max(p_value * (1.0 - p_value), 0.0) / (n_draws + 1)))
    return p_value, "monte_carlo", int(n_draws), mcse


def _signed_rank_p_value_one_sided(
    *,
    deltas: np.ndarray,
    n_draws: int,
    seed: int,
    exact_max_pairs: int,
) -> tuple[float | None, str | None, int | None, float | None]:
    if deltas.ndim != 1 or deltas.size == 0:
        return None, None, None, None
    if n_draws < 1:
        return None, None, None, None

    finite = deltas[np.isfinite(deltas)]
    nonzero = finite[finite != 0.0]
    n = int(nonzero.shape[0])
    if n == 0:
        return None, None, None, None

    ranks = _average_ranks(np.abs(nonzero))
    observed = float(np.sum(ranks[nonzero > 0.0]))

    if n <= exact_max_pairs:
        total = 1 << n
        ge = 0
        for mask in range(total):
            signed_rank_sum = 0.0
            for idx, rank in enumerate(ranks):
                if ((mask >> idx) & 1) == 0:
                    signed_rank_sum += float(rank)
            if signed_rank_sum >= observed:
                ge += 1
        p_value = float(ge / total)
        return p_value, "exact", total, 0.0

    rng = np.random.default_rng(seed)
    positives = rng.integers(low=0, high=2, size=(n_draws, n), dtype=np.int8)
    sample_sums = np.sum(positives * ranks[np.newaxis, :], axis=1)
    ge = int(np.sum(sample_sums >= observed))
    p_value = float((ge + 1) / (n_draws + 1))
    mcse = float(math.sqrt(max(p_value * (1.0 - p_value), 0.0) / (n_draws + 1)))
    return p_value, "monte_carlo", int(n_draws), mcse


def _average_ranks(values: np.ndarray) -> np.ndarray:
    n = int(values.shape[0])
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i + 1
        while j < n and values[order[j]] == values[order[i]]:
            j += 1
        mean_rank = 0.5 * ((i + 1) + j)
        for pos in range(i, j):
            ranks[order[pos]] = mean_rank
        i = j
    return ranks


def _bias_improvement_fraction(*, candidate: float, baseline: float) -> float | None:
    if not np.isfinite(candidate) or not np.isfinite(baseline):
        return None
    if baseline <= 0:
        return None
    return float((baseline - candidate) / baseline)


def _metric_by_name(metrics: tuple[ModelAggregateMetrics, ...]) -> dict[str, ModelAggregateMetrics]:
    return {row.model: row for row in metrics}


def _continuous_pair_and_eval_scores(
    *,
    network_scores: Mapping[str, list[float]],
    selection_mode: str,
    requested_candidate_model: str,
    requested_baseline_model: str,
    selection_holdout_fraction: float,
    selection_split_seed: int,
) -> tuple[str, str, list[float], list[float]]:
    model_names = ("core_fixed_effects", "core_random_effects")
    for name in model_names:
        if name not in network_scores:
            raise ValueError(f"Continuous scenario missing model scores for '{name}'.")

    if selection_mode == "pre_specified":
        return (
            requested_candidate_model,
            requested_baseline_model,
            list(network_scores[requested_candidate_model]),
            list(network_scores[requested_baseline_model]),
        )

    # Adaptive split: select model on one split, infer on held-out split.
    total = len(network_scores[model_names[0]])
    if total < 4:
        raise ValueError(
            "continuous.selection_mode='adaptive_split' requires at least 4 networks."
        )
    if len(network_scores[model_names[1]]) != total:
        raise ValueError("Continuous model score vectors must have equal length.")

    eval_n = int(round(total * selection_holdout_fraction))
    eval_n = min(max(eval_n, 2), total - 2)
    rng = np.random.default_rng(selection_split_seed)
    order = rng.permutation(total)
    selection_idx = order[: total - eval_n]
    eval_idx = order[total - eval_n :]

    selection_means = {
        name: _mean_finite_subset(network_scores[name], selection_idx)
        for name in model_names
    }
    candidate_model, baseline_model = _select_predictive_pair_for_continuous(
        mean_log_score_by_model=selection_means
    )
    return (
        candidate_model,
        baseline_model,
        _subset_by_indices(network_scores[candidate_model], eval_idx),
        _subset_by_indices(network_scores[baseline_model], eval_idx),
    )


def _select_predictive_pair_for_continuous(
    *,
    mean_log_score_by_model: Mapping[str, float],
) -> tuple[str, str]:
    candidates = ("core_fixed_effects", "core_random_effects")
    missing = [name for name in candidates if name not in mean_log_score_by_model]
    if missing:
        raise ValueError(
            "Continuous model ordering missing mean log score for: "
            + ", ".join(sorted(missing))
        )
    complexity_rank = {
        "core_fixed_effects": 0,
        "core_random_effects": 1,
    }
    ranked = sorted(
        candidates,
        key=lambda name: (
            _finite_or_neg_inf(mean_log_score_by_model[name]),
            -complexity_rank[name],  # Prefer fixed-effects on exact predictive ties.
        ),
        reverse=True,
    )
    return ranked[0], ranked[-1]


def _fmt_metric(value: float | None) -> str:
    if value is None:
        return "NA"
    if not np.isfinite(value):
        return "NA"
    return f"{value:.4f}"


def _within_closed_interval(value: float | None, *, lo: float, hi: float) -> bool:
    if value is None or not np.isfinite(value):
        return False
    return bool(lo <= value <= hi)


def _meets_minimum(value: float | None, *, minimum: float) -> bool:
    if value is None or not np.isfinite(value):
        return False
    return bool(value >= minimum)


def _at_most(value: float | None, *, maximum: float) -> bool:
    if value is None or not np.isfinite(value):
        return False
    return bool(value <= maximum)


def _superiority_metric(
    scenario: ScenarioEvaluation,
    metric: str,
) -> float | None:
    sup = scenario.predictive_superiority
    if sup is None:
        return None
    value = getattr(sup, metric, None)
    if value is None:
        return None
    return float(value)


def _superiority_text_metric(
    scenario: ScenarioEvaluation,
    metric: str,
) -> str:
    sup = scenario.predictive_superiority
    if sup is None:
        return "NA"
    value = getattr(sup, metric, None)
    if value is None:
        return "NA"
    return str(value)


def _optional_float(raw: Any) -> float | None:
    if raw is None:
        return None
    return float(raw)


def _optional_threshold_dict(**kwargs: float | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        out[key] = float(value)
    return out


def _inferential_expected_keys() -> tuple[str, ...]:
    return (
        "continuous_logscore_sign_test_p",
        "continuous_logscore_permutation_p",
        "continuous_logscore_signed_rank_p",
        "survival_logscore_sign_test_p",
        "survival_logscore_permutation_p",
        "survival_logscore_signed_rank_p",
    )


def _inferential_raw_p_values(
    *,
    continuous: ScenarioEvaluation,
    survival: ScenarioEvaluation,
) -> dict[str, float]:
    expected = {
        "continuous_logscore_sign_test_p": _superiority_metric(
            continuous,
            "one_sided_sign_p_value",
        ),
        "continuous_logscore_permutation_p": _superiority_metric(
            continuous,
            "one_sided_permutation_p_value",
        ),
        "continuous_logscore_signed_rank_p": _superiority_metric(
            continuous,
            "one_sided_signed_rank_p_value",
        ),
        "survival_logscore_sign_test_p": _superiority_metric(
            survival,
            "one_sided_sign_p_value",
        ),
        "survival_logscore_permutation_p": _superiority_metric(
            survival,
            "one_sided_permutation_p_value",
        ),
        "survival_logscore_signed_rank_p": _superiority_metric(
            survival,
            "one_sided_signed_rank_p_value",
        ),
    }
    out: dict[str, float] = {}
    for key, value in expected.items():
        if value is None or not np.isfinite(value):
            continue
        out[key] = float(value)
    return out


def _holm_adjusted_p_values(raw_p_values: Mapping[str, float]) -> dict[str, float]:
    if not raw_p_values:
        return {}
    ordered = sorted(raw_p_values.items(), key=lambda item: item[1])
    m = len(ordered)
    adjusted_in_order: list[tuple[str, float]] = []
    running_max = 0.0
    for index, (key, raw) in enumerate(ordered):
        multiplier = m - index
        adjusted = min(max(raw * multiplier, 0.0), 1.0)
        running_max = max(running_max, adjusted)
        adjusted_in_order.append((key, running_max))
    return {key: value for key, value in adjusted_in_order}


def _finite_or_neg_inf(value: float) -> float:
    return float(value) if np.isfinite(value) else float("-inf")


def _subset_by_indices(values: list[float], indices: np.ndarray) -> list[float]:
    return [float(values[int(idx)]) for idx in indices]


def _mean_finite_subset(values: list[float], indices: np.ndarray) -> float:
    subset = np.asarray([values[int(idx)] for idx in indices], dtype=float)
    finite = subset[np.isfinite(subset)]
    if finite.size == 0:
        return float("-inf")
    return float(np.mean(finite))


def _validate_continuous_selection(
    *,
    selection_mode: str,
    candidate_model: str,
    baseline_model: str,
    holdout_fraction: float,
) -> None:
    allowed_models = {"core_fixed_effects", "core_random_effects"}
    if candidate_model not in allowed_models:
        raise ValueError(
            "continuous.candidate_model must be one of: core_fixed_effects, core_random_effects."
        )
    if baseline_model not in allowed_models:
        raise ValueError(
            "continuous.baseline_model must be one of: core_fixed_effects, core_random_effects."
        )
    if candidate_model == baseline_model:
        raise ValueError("continuous.candidate_model must differ from continuous.baseline_model.")

    allowed_selection_modes = {"pre_specified", "adaptive_split"}
    if selection_mode not in allowed_selection_modes:
        raise ValueError(
            "continuous.selection_mode must be one of: pre_specified, adaptive_split."
        )
    if selection_mode == "adaptive_split":
        if holdout_fraction <= 0.0 or holdout_fraction >= 1.0:
            raise ValueError(
                "continuous.selection_holdout_fraction must be in (0, 1) when "
                "selection_mode='adaptive_split'."
            )


def _validate_thresholds(
    *,
    coverage_lo: float,
    coverage_hi: float,
    bias_improvement_min: float,
    logscore_win_rate_min: float,
    continuous_logscore_win_rate_min: float,
    continuous_logscore_delta_ci95_lb_min: float | None,
    continuous_logscore_sign_p_max: float | None,
    continuous_logscore_signed_rank_p_max: float | None,
    continuous_superiority_probability_min: float | None,
    continuous_logscore_permutation_p_max: float | None,
    continuous_logscore_permutation_mcse_max: float | None,
    continuous_superiority_probability_mcse_max: float | None,
    survival_logscore_delta_ci95_lb_min: float | None,
    survival_logscore_sign_p_max: float | None,
    survival_logscore_signed_rank_p_max: float | None,
    survival_superiority_probability_min: float | None,
    survival_logscore_permutation_p_max: float | None,
    survival_logscore_permutation_mcse_max: float | None,
    survival_superiority_probability_mcse_max: float | None,
    familywise_holm_alpha: float | None,
) -> None:
    _validate_probability("thresholds.coverage_lo", coverage_lo)
    _validate_probability("thresholds.coverage_hi", coverage_hi)
    if coverage_lo > coverage_hi:
        raise ValueError("thresholds.coverage_lo must be <= thresholds.coverage_hi.")
    _validate_finite("thresholds.bias_improvement_min", bias_improvement_min)
    _validate_probability("thresholds.logscore_win_rate_min", logscore_win_rate_min)
    _validate_probability(
        "thresholds.continuous_logscore_win_rate_min",
        continuous_logscore_win_rate_min,
    )
    if continuous_logscore_delta_ci95_lb_min is not None:
        _validate_finite(
            "thresholds.continuous_logscore_delta_ci95_lb_min",
            continuous_logscore_delta_ci95_lb_min,
        )
    if continuous_logscore_sign_p_max is not None:
        _validate_probability(
            "thresholds.continuous_logscore_sign_p_max",
            continuous_logscore_sign_p_max,
        )
    if continuous_logscore_signed_rank_p_max is not None:
        _validate_probability(
            "thresholds.continuous_logscore_signed_rank_p_max",
            continuous_logscore_signed_rank_p_max,
        )
    if continuous_superiority_probability_min is not None:
        _validate_probability(
            "thresholds.continuous_superiority_probability_min",
            continuous_superiority_probability_min,
        )
    if continuous_logscore_permutation_p_max is not None:
        _validate_probability(
            "thresholds.continuous_logscore_permutation_p_max",
            continuous_logscore_permutation_p_max,
        )
    if continuous_logscore_permutation_mcse_max is not None:
        _validate_non_negative_finite(
            "thresholds.continuous_logscore_permutation_mcse_max",
            continuous_logscore_permutation_mcse_max,
        )
    if continuous_superiority_probability_mcse_max is not None:
        _validate_non_negative_finite(
            "thresholds.continuous_superiority_probability_mcse_max",
            continuous_superiority_probability_mcse_max,
        )
    if survival_logscore_delta_ci95_lb_min is not None:
        _validate_finite(
            "thresholds.survival_logscore_delta_ci95_lb_min",
            survival_logscore_delta_ci95_lb_min,
        )
    if survival_logscore_sign_p_max is not None:
        _validate_probability(
            "thresholds.survival_logscore_sign_p_max",
            survival_logscore_sign_p_max,
        )
    if survival_logscore_signed_rank_p_max is not None:
        _validate_probability(
            "thresholds.survival_logscore_signed_rank_p_max",
            survival_logscore_signed_rank_p_max,
        )
    if survival_superiority_probability_min is not None:
        _validate_probability(
            "thresholds.survival_superiority_probability_min",
            survival_superiority_probability_min,
        )
    if survival_logscore_permutation_p_max is not None:
        _validate_probability(
            "thresholds.survival_logscore_permutation_p_max",
            survival_logscore_permutation_p_max,
        )
    if survival_logscore_permutation_mcse_max is not None:
        _validate_non_negative_finite(
            "thresholds.survival_logscore_permutation_mcse_max",
            survival_logscore_permutation_mcse_max,
        )
    if survival_superiority_probability_mcse_max is not None:
        _validate_non_negative_finite(
            "thresholds.survival_superiority_probability_mcse_max",
            survival_superiority_probability_mcse_max,
        )
    if familywise_holm_alpha is not None:
        _validate_probability(
            "thresholds.familywise_holm_alpha",
            familywise_holm_alpha,
        )


def _validate_int_at_least(name: str, value: int, minimum: int) -> None:
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")


def _validate_non_negative_finite(name: str, value: float) -> None:
    _validate_finite(name, value)
    if value < 0:
        raise ValueError(f"{name} must be >= 0.")


def _validate_positive_finite(name: str, value: float) -> None:
    _validate_finite(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be > 0.")


def _validate_probability(name: str, value: float) -> None:
    _validate_finite(name, value)
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in [0, 1].")


def _validate_finite(name: str, value: float) -> None:
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite.")


def _as_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return {str(k): v for k, v in raw.items()}
    raise ValueError("Expected mapping/object for scenario configuration.")


def _try_git_commit() -> str | None:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None
