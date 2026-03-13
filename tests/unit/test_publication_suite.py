from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from nma_pool.validation import publication
from nma_pool.validation.publication import run_publication_suite


def test_publication_suite_returns_structured_results() -> None:
    config = {
        "thresholds": {
            "coverage_lo": 0.80,
            "coverage_hi": 1.00,
            "bias_improvement_min": 0.0,
            "logscore_win_rate_min": 0.0,
        },
        "continuous": {
            "n_networks": 16,
            "seed_start": 100,
            "n_per_arm": 100,
            "se": 0.25,
            "noise_sd": 0.05,
        },
        "survival_nonph": {
            "n_networks": 12,
            "seed_start": 200,
            "n_per_arm": 450,
            "replicates_per_pair": 2,
            "follow_up_fraction": 0.85,
        },
        "continuity_correction": 0.5,
    }
    result = run_publication_suite(config)
    payload = result.to_dict()

    assert isinstance(payload["overall_pass"], bool)
    assert "continuous" in payload
    assert "survival_nonph" in payload
    assert "gates" in payload
    assert "continuous_coverage_95_in_target" in payload["gates"]
    assert "continuous_logscore_win_rate_vs_baseline" in payload["gates"]
    assert "survival_coverage_95_in_target" in payload["gates"]
    assert "survival_bias_improvement_vs_baseline" in payload["gates"]
    assert "survival_logscore_win_rate_vs_baseline" in payload["gates"]
    assert payload["continuous"]["predictive_superiority"] is not None
    assert payload["survival_nonph"]["predictive_superiority"] is not None

    cont_metrics = payload["continuous"]["metrics"]
    surv_metrics = payload["survival_nonph"]["metrics"]
    assert len(cont_metrics) >= 2
    assert len(surv_metrics) >= 3
    assert result.to_markdown().startswith("# Publication-Readiness Results")


def test_publication_suite_bias_gate_allows_exact_zero_at_zero_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = (
        publication.ModelAggregateMetrics(
            model="baseline",
            n_networks=1,
            n_estimates=2,
            estimable_rate=1.0,
            median_abs_bias=0.2,
            rmse=0.2,
            coverage_95=0.95,
            mean_log_score=0.0,
        ),
        publication.ModelAggregateMetrics(
            model="candidate",
            n_networks=1,
            n_estimates=2,
            estimable_rate=1.0,
            median_abs_bias=0.2,
            rmse=0.2,
            coverage_95=0.95,
            mean_log_score=0.1,
        ),
    )

    monkeypatch.setattr(
        publication,
        "_evaluate_continuous_scenario",
        lambda _cfg: publication.ScenarioEvaluation(
            scenario_id="cont",
            description="cont",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.0,
            candidate_logscore_win_rate=1.0,
        ),
    )
    monkeypatch.setattr(
        publication,
        "_evaluate_survival_nonph_scenario",
        lambda _cfg, *, continuity_correction: publication.ScenarioEvaluation(
            scenario_id="surv",
            description=f"surv-{continuity_correction}",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.0,
            candidate_logscore_win_rate=1.0,
        ),
    )
    monkeypatch.setattr(publication, "_try_git_commit", lambda: "abc123")

    result = run_publication_suite(
        {
            "thresholds": {
                "coverage_lo": 0.90,
                "coverage_hi": 0.99,
                "bias_improvement_min": 0.0,
                "continuous_logscore_win_rate_min": 0.5,
                "logscore_win_rate_min": 0.5,
            },
            "continuity_correction": 0.5,
        }
    )
    assert result.gates["survival_bias_improvement_vs_baseline"] is True
    assert result.overall_pass is True


def test_publication_suite_can_enforce_git_commit_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = (
        publication.ModelAggregateMetrics(
            model="baseline",
            n_networks=1,
            n_estimates=1,
            estimable_rate=1.0,
            median_abs_bias=0.2,
            rmse=0.2,
            coverage_95=0.95,
            mean_log_score=0.0,
        ),
        publication.ModelAggregateMetrics(
            model="candidate",
            n_networks=1,
            n_estimates=1,
            estimable_rate=1.0,
            median_abs_bias=0.1,
            rmse=0.1,
            coverage_95=0.95,
            mean_log_score=0.1,
        ),
    )

    monkeypatch.setattr(
        publication,
        "_evaluate_continuous_scenario",
        lambda _cfg: publication.ScenarioEvaluation(
            scenario_id="cont",
            description="cont",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.5,
            candidate_logscore_win_rate=1.0,
        ),
    )
    monkeypatch.setattr(
        publication,
        "_evaluate_survival_nonph_scenario",
        lambda _cfg, *, continuity_correction: publication.ScenarioEvaluation(
            scenario_id="surv",
            description=f"surv-{continuity_correction}",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.5,
            candidate_logscore_win_rate=1.0,
        ),
    )
    monkeypatch.setattr(publication, "_try_git_commit", lambda: None)

    result = run_publication_suite(
        {
            "thresholds": {
                "coverage_lo": 0.90,
                "coverage_hi": 0.99,
                "bias_improvement_min": 0.0,
                "continuous_logscore_win_rate_min": 0.5,
                "logscore_win_rate_min": 0.5,
            },
            "continuity_correction": 0.5,
            "require_git_commit": True,
        }
    )
    assert result.gates["git_commit_present"] is False
    assert result.overall_pass is False


def test_publication_suite_string_false_does_not_enable_git_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = (
        publication.ModelAggregateMetrics(
            model="baseline",
            n_networks=1,
            n_estimates=1,
            estimable_rate=1.0,
            median_abs_bias=0.2,
            rmse=0.2,
            coverage_95=0.95,
            mean_log_score=0.0,
        ),
        publication.ModelAggregateMetrics(
            model="candidate",
            n_networks=1,
            n_estimates=1,
            estimable_rate=1.0,
            median_abs_bias=0.1,
            rmse=0.1,
            coverage_95=0.95,
            mean_log_score=0.1,
        ),
    )

    monkeypatch.setattr(
        publication,
        "_evaluate_continuous_scenario",
        lambda _cfg: publication.ScenarioEvaluation(
            scenario_id="cont",
            description="cont",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.5,
            candidate_logscore_win_rate=1.0,
        ),
    )
    monkeypatch.setattr(
        publication,
        "_evaluate_survival_nonph_scenario",
        lambda _cfg, *, continuity_correction: publication.ScenarioEvaluation(
            scenario_id="surv",
            description=f"surv-{continuity_correction}",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.5,
            candidate_logscore_win_rate=1.0,
        ),
    )
    monkeypatch.setattr(publication, "_try_git_commit", lambda: None)

    result = run_publication_suite(
        {
            "thresholds": {
                "coverage_lo": 0.90,
                "coverage_hi": 0.99,
                "bias_improvement_min": 0.0,
                "continuous_logscore_win_rate_min": 0.5,
                "logscore_win_rate_min": 0.5,
            },
            "continuity_correction": 0.5,
            "require_git_commit": "false",
        }
    )
    assert "git_commit_present" not in result.gates
    assert result.overall_pass is True


def test_try_git_commit_uses_repository_root_as_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    class _Proc:
        returncode = 0
        stdout = "abc123\n"

    def _fake_run(*args: Any, **kwargs: Any) -> _Proc:
        calls["cwd"] = kwargs.get("cwd")
        return _Proc()

    monkeypatch.setattr(publication.subprocess, "run", _fake_run)
    value = publication._try_git_commit()  # noqa: SLF001

    assert value == "abc123"
    assert calls["cwd"] == publication.Path(__file__).resolve().parents[2]


def test_publication_suite_optional_predictive_significance_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = (
        publication.ModelAggregateMetrics(
            model="baseline",
            n_networks=1,
            n_estimates=1,
            estimable_rate=1.0,
            median_abs_bias=0.2,
            rmse=0.2,
            coverage_95=0.95,
            mean_log_score=0.0,
        ),
        publication.ModelAggregateMetrics(
            model="candidate",
            n_networks=1,
            n_estimates=1,
            estimable_rate=1.0,
            median_abs_bias=0.1,
            rmse=0.1,
            coverage_95=0.95,
            mean_log_score=0.1,
        ),
    )
    superiority = publication.PredictiveSuperiority(
        n_pairs=30,
        mean_delta_log_score=0.12,
        median_delta_log_score=0.10,
        ci95_lower=0.03,
        ci95_upper=0.21,
        superiority_probability=0.99,
        one_sided_sign_p_value=0.001,
        one_sided_signed_rank_p_value=0.003,
        strict_win_rate=0.80,
        tie_rate=0.05,
        standardized_mean_delta=0.35,
        one_sided_permutation_p_value=0.002,
        permutation_method="exact",
        permutation_draws_used=4096,
        permutation_mcse=0.0,
        signed_rank_method="exact",
        signed_rank_draws_used=4096,
        signed_rank_mcse=0.0,
        superiority_probability_mcse=0.002,
    )

    monkeypatch.setattr(
        publication,
        "_evaluate_continuous_scenario",
        lambda _cfg: publication.ScenarioEvaluation(
            scenario_id="cont",
            description="cont",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.5,
            candidate_logscore_win_rate=0.9,
            predictive_superiority=superiority,
        ),
    )
    monkeypatch.setattr(
        publication,
        "_evaluate_survival_nonph_scenario",
        lambda _cfg, *, continuity_correction: publication.ScenarioEvaluation(
            scenario_id="surv",
            description=f"surv-{continuity_correction}",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=metrics,
            candidate_bias_improvement_fraction=0.5,
            candidate_logscore_win_rate=0.9,
            predictive_superiority=superiority,
        ),
    )
    monkeypatch.setattr(publication, "_try_git_commit", lambda: "abc123")

    result = run_publication_suite(
        {
            "thresholds": {
                "coverage_lo": 0.90,
                "coverage_hi": 0.99,
                "bias_improvement_min": 0.0,
                "continuous_logscore_win_rate_min": 0.5,
                "logscore_win_rate_min": 0.5,
                "continuous_logscore_delta_ci95_lb_min": 0.0,
                "continuous_logscore_sign_p_max": 0.05,
                "continuous_logscore_permutation_p_max": 0.05,
                "continuous_logscore_signed_rank_p_max": 0.05,
                "continuous_logscore_permutation_mcse_max": 0.01,
                "continuous_superiority_probability_min": 0.95,
                "continuous_superiority_probability_mcse_max": 0.01,
                "survival_logscore_delta_ci95_lb_min": 0.0,
                "survival_logscore_sign_p_max": 0.05,
                "survival_logscore_permutation_p_max": 0.05,
                "survival_logscore_signed_rank_p_max": 0.05,
                "survival_logscore_permutation_mcse_max": 0.01,
                "survival_superiority_probability_min": 0.95,
                "survival_superiority_probability_mcse_max": 0.01,
                "familywise_holm_alpha": 0.01,
            },
            "continuity_correction": 0.5,
        }
    )
    assert result.gates["continuous_logscore_delta_ci95_lb_vs_baseline"] is True
    assert result.gates["continuous_logscore_sign_test_p_vs_baseline"] is True
    assert result.gates["continuous_logscore_permutation_p_vs_baseline"] is True
    assert result.gates["continuous_logscore_signed_rank_p_vs_baseline"] is True
    assert result.gates["continuous_logscore_permutation_mcse_within_max"] is True
    assert result.gates["continuous_superiority_probability_vs_baseline"] is True
    assert result.gates["continuous_superiority_probability_mcse_within_max"] is True
    assert result.gates["survival_logscore_delta_ci95_lb_vs_baseline"] is True
    assert result.gates["survival_logscore_sign_test_p_vs_baseline"] is True
    assert result.gates["survival_logscore_permutation_p_vs_baseline"] is True
    assert result.gates["survival_logscore_signed_rank_p_vs_baseline"] is True
    assert result.gates["survival_logscore_permutation_mcse_within_max"] is True
    assert result.gates["survival_superiority_probability_vs_baseline"] is True
    assert result.gates["survival_superiority_probability_mcse_within_max"] is True
    assert result.gates["continuous_logscore_sign_test_p_holm_adjusted_p_vs_baseline"] is True
    assert result.gates["survival_logscore_signed_rank_p_holm_adjusted_p_vs_baseline"] is True
    assert result.inferential_adjustment_method == "holm"
    assert result.inferential_adjusted_p_values is not None
    assert "continuous_logscore_permutation_p" in result.inferential_adjusted_p_values
    assert result.overall_pass is True


def test_publication_suite_markdown_formats_missing_values() -> None:
    result = publication.PublicationSuiteResult(
        created_at_utc="2026-02-28T00:00:00+00:00",
        python_version="3.13.7",
        platform="windows",
        git_commit=None,
        config_sha256="x",
        thresholds={
            "coverage_lo": 0.93,
            "coverage_hi": 0.97,
            "bias_improvement_min": 0.2,
            "logscore_win_rate_min": 0.8,
            "continuous_logscore_win_rate_min": 0.7,
        },
        continuous=publication.ScenarioEvaluation(
            scenario_id="cont",
            description="cont",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=(
                publication.ModelAggregateMetrics(
                    model="baseline",
                    n_networks=1,
                    n_estimates=1,
                    estimable_rate=1.0,
                    median_abs_bias=0.2,
                    rmse=0.2,
                    coverage_95=0.95,
                    mean_log_score=0.0,
                ),
                publication.ModelAggregateMetrics(
                    model="candidate",
                    n_networks=1,
                    n_estimates=1,
                    estimable_rate=1.0,
                    median_abs_bias=float("nan"),
                    rmse=0.2,
                    coverage_95=float("nan"),
                    mean_log_score=0.1,
                ),
            ),
            candidate_bias_improvement_fraction=None,
            candidate_logscore_win_rate=None,
        ),
        survival_nonph=publication.ScenarioEvaluation(
            scenario_id="surv",
            description="surv",
            baseline_model="baseline",
            candidate_model="candidate",
            metrics=(
                publication.ModelAggregateMetrics(
                    model="baseline",
                    n_networks=1,
                    n_estimates=1,
                    estimable_rate=1.0,
                    median_abs_bias=0.2,
                    rmse=0.2,
                    coverage_95=0.95,
                    mean_log_score=0.0,
                ),
                publication.ModelAggregateMetrics(
                    model="candidate",
                    n_networks=1,
                    n_estimates=1,
                    estimable_rate=1.0,
                    median_abs_bias=0.1,
                    rmse=0.1,
                    coverage_95=0.95,
                    mean_log_score=0.1,
                ),
            ),
            candidate_bias_improvement_fraction=None,
            candidate_logscore_win_rate=None,
        ),
        gates={
            "continuous_coverage_95_in_target": False,
            "continuous_logscore_win_rate_vs_baseline": False,
            "survival_coverage_95_in_target": True,
            "survival_bias_improvement_vs_baseline": False,
            "survival_logscore_win_rate_vs_baseline": False,
        },
        overall_pass=False,
    )
    md = result.to_markdown()
    assert "Candidate coverage: NA" in md
    assert "Candidate logscore win-rate vs baseline: NA" in md
    assert "Mean logscore delta (candidate-baseline): NA" in md
    assert "One-sided permutation p-value: NA" in md
    assert "One-sided signed-rank p-value: NA" in md
    assert "Permutation method: NA" in md


def test_publication_suite_rejects_invalid_config_values() -> None:
    with pytest.raises(ValueError, match="continuous.n_networks"):
        run_publication_suite(
            {
                "continuous": {"n_networks": 0},
                "survival_nonph": {"n_networks": 1},
                "continuity_correction": 0.5,
            }
        )
    with pytest.raises(ValueError, match="continuous.selection_mode"):
        run_publication_suite(
            {
                "continuous": {
                    "n_networks": 4,
                    "selection_mode": "invalid_mode",
                },
                "survival_nonph": {"n_networks": 1},
                "continuity_correction": 0.5,
            }
        )


def test_publication_suite_continuous_default_pair_is_prespecified() -> None:
    result = run_publication_suite(
        {
            "thresholds": {
                "coverage_lo": 0.0,
                "coverage_hi": 1.0,
                "bias_improvement_min": -1.0,
                "continuous_logscore_win_rate_min": 0.0,
                "logscore_win_rate_min": 0.0,
            },
            "continuous": {
                "n_networks": 24,
                "seed_start": 1000,
                "n_per_arm": 120,
                "se": 0.25,
                "noise_sd": 0.25,
                "selection_mode": "pre_specified",
                "candidate_model": "core_fixed_effects",
                "baseline_model": "core_random_effects",
            },
            "survival_nonph": {
                "n_networks": 8,
                "seed_start": 2000,
                "n_per_arm": 450,
                "replicates_per_pair": 2,
                "follow_up_fraction": 0.85,
            },
            "continuity_correction": 0.5,
        }
    )
    assert result.continuous.candidate_model == "core_fixed_effects"
    assert result.continuous.baseline_model == "core_random_effects"


def test_publication_suite_continuous_adaptive_split_runs() -> None:
    result = run_publication_suite(
        {
            "thresholds": {
                "coverage_lo": 0.0,
                "coverage_hi": 1.0,
                "bias_improvement_min": -1.0,
                "continuous_logscore_win_rate_min": 0.0,
                "logscore_win_rate_min": 0.0,
            },
            "continuous": {
                "n_networks": 24,
                "seed_start": 1000,
                "n_per_arm": 120,
                "se": 0.25,
                "noise_sd": 0.25,
                "selection_mode": "adaptive_split",
                "selection_holdout_fraction": 0.5,
                "selection_split_seed": 909,
            },
            "survival_nonph": {
                "n_networks": 8,
                "seed_start": 2000,
                "n_per_arm": 450,
                "replicates_per_pair": 2,
                "follow_up_fraction": 0.85,
            },
            "continuity_correction": 0.5,
        }
    )
    assert result.continuous.candidate_model in {"core_fixed_effects", "core_random_effects"}
    assert result.continuous.baseline_model in {"core_fixed_effects", "core_random_effects"}
    assert result.continuous.candidate_model != result.continuous.baseline_model
    assert result.continuous.predictive_superiority is not None


def test_publication_win_rate_uses_strict_non_tie_definition() -> None:
    score = publication._win_rate(  # noqa: SLF001
        candidate=[1.0, 1.0, 0.0, 2.0],
        baseline=[1.0, 0.0, 1.0, 2.0],
    )
    assert score == pytest.approx(0.5)  # wins=1, losses=1, ties=2


def test_publication_permutation_p_value_behaves_on_positive_signal() -> None:
    p_value, method, draws, mcse = publication._paired_permutation_p_value_one_sided(  # noqa: SLF001
        deltas=np.asarray([0.4, 0.5, 0.6, 0.7, 0.8], dtype=float),
        n_draws=10000,
        seed=123,
        exact_max_pairs=10,
    )
    assert p_value is not None
    assert p_value < 0.05
    assert method == "exact"
    assert draws == 32
    assert mcse == 0.0


def test_publication_permutation_p_value_monte_carlo_reports_mcse() -> None:
    p_value, method, draws, mcse = publication._paired_permutation_p_value_one_sided(  # noqa: SLF001
        deltas=np.asarray([0.2, -0.1, 0.05, 0.4, -0.3], dtype=float),
        n_draws=5000,
        seed=123,
        exact_max_pairs=2,
    )
    assert p_value is not None
    assert 0.0 <= p_value <= 1.0
    assert method == "monte_carlo"
    assert draws == 5000
    assert mcse is not None
    assert mcse > 0.0


def test_publication_signed_rank_p_value_exact_path() -> None:
    p_value, method, draws, mcse = publication._signed_rank_p_value_one_sided(  # noqa: SLF001
        deltas=np.asarray([0.4, 0.5, 0.6, 0.7, 0.8], dtype=float),
        n_draws=10000,
        seed=123,
        exact_max_pairs=10,
    )
    assert p_value is not None
    assert p_value < 0.05
    assert method == "exact"
    assert draws == 32
    assert mcse == 0.0


def test_publication_signed_rank_p_value_monte_carlo_path() -> None:
    p_value, method, draws, mcse = publication._signed_rank_p_value_one_sided(  # noqa: SLF001
        deltas=np.asarray([0.2, -0.1, 0.05, 0.4, -0.3], dtype=float),
        n_draws=5000,
        seed=123,
        exact_max_pairs=2,
    )
    assert p_value is not None
    assert 0.0 <= p_value <= 1.0
    assert method == "monte_carlo"
    assert draws == 5000
    assert mcse is not None
    assert mcse > 0.0


def test_publication_suite_rejects_invalid_familywise_alpha() -> None:
    with pytest.raises(ValueError, match="thresholds.familywise_holm_alpha"):
        run_publication_suite(
            {
                "thresholds": {"familywise_holm_alpha": 1.5},
                "continuous": {"n_networks": 4},
                "survival_nonph": {"n_networks": 4},
                "continuity_correction": 0.5,
            }
        )


def test_publication_holm_adjustment_monotone_and_bounded() -> None:
    adjusted = publication._holm_adjusted_p_values(  # noqa: SLF001
        {
            "a": 0.01,
            "b": 0.03,
            "c": 0.02,
        }
    )
    assert adjusted["a"] == pytest.approx(0.03)
    assert adjusted["c"] == pytest.approx(0.04)
    assert adjusted["b"] == pytest.approx(0.04)
    assert all(0.0 <= value <= 1.0 for value in adjusted.values())
