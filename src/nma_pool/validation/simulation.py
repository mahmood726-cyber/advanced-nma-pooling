"""Small simulation utilities for calibration smoke tests."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ContinuousSimulationSpec:
    seed: int = 123
    n_per_arm: int = 120
    se: float = 0.25
    true_effect_b: float = 1.0
    true_effect_c: float = 2.0
    noise_sd: float = 0.05


@dataclass(frozen=True)
class InconsistentLoopSpec:
    n_per_arm: int = 120
    se: float = 0.15
    ab_effect: float = 1.0  # B - A
    ac_effect: float = 1.0  # C - A
    bc_direct_effect: float = -1.0  # C - B (inconsistent with indirect = 0)


@dataclass(frozen=True)
class SurvivalNonPHSimulationSpec:
    seed: int = 123
    n_per_arm: int = 500
    replicates_per_pair: int = 2
    interval_bounds: tuple[tuple[float, float], ...] = (
        (0.0, 3.0),
        (3.0, 6.0),
        (6.0, 12.0),
    )
    baseline_hazards: tuple[float, ...] = (0.06, 0.05, 0.04)
    hr_b: tuple[float, ...] = (0.70, 0.85, 1.05)
    hr_c: tuple[float, ...] = (0.55, 0.72, 0.95)
    follow_up_fraction: float = 0.85


def simulate_continuous_abc_network(
    spec: ContinuousSimulationSpec | None = None,
) -> dict[str, Any]:
    """Return minimal synthetic payload for a 3-treatment connected network."""
    spec = spec or ContinuousSimulationSpec()
    rng = random.Random(spec.seed)

    def jitter(value: float) -> float:
        return value + rng.gauss(0.0, spec.noise_sd)

    return {
        "studies": [
            {
                "study_id": "SIM1",
                "design": "rct",
                "year": 2025,
                "source_id": "sim-1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "SIM2",
                "design": "rct",
                "year": 2025,
                "source_id": "sim-2",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "SIM3",
                "design": "rct",
                "year": 2025,
                "source_id": "sim-3",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "SIM1", "arm_id": "A1", "treatment_id": "A", "n": spec.n_per_arm},
            {"study_id": "SIM1", "arm_id": "A2", "treatment_id": "B", "n": spec.n_per_arm},
            {"study_id": "SIM2", "arm_id": "B1", "treatment_id": "A", "n": spec.n_per_arm},
            {"study_id": "SIM2", "arm_id": "B2", "treatment_id": "C", "n": spec.n_per_arm},
            {"study_id": "SIM3", "arm_id": "C1", "treatment_id": "B", "n": spec.n_per_arm},
            {"study_id": "SIM3", "arm_id": "C2", "treatment_id": "C", "n": spec.n_per_arm},
        ],
        "outcomes_ad": [
            {
                "study_id": "SIM1",
                "arm_id": "A1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": jitter(0.0),
                "se": spec.se,
            },
            {
                "study_id": "SIM1",
                "arm_id": "A2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": jitter(spec.true_effect_b),
                "se": spec.se,
            },
            {
                "study_id": "SIM2",
                "arm_id": "B1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": jitter(0.0),
                "se": spec.se,
            },
            {
                "study_id": "SIM2",
                "arm_id": "B2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": jitter(spec.true_effect_c),
                "se": spec.se,
            },
            {
                "study_id": "SIM3",
                "arm_id": "C1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": jitter(spec.true_effect_b),
                "se": spec.se,
            },
            {
                "study_id": "SIM3",
                "arm_id": "C2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": jitter(spec.true_effect_c),
                "se": spec.se,
            },
        ],
    }


def simulate_inconsistent_abc_loop(
    spec: InconsistentLoopSpec | None = None,
) -> dict[str, Any]:
    """Return a deterministic inconsistent loop network A-B-C."""
    spec = spec or InconsistentLoopSpec()
    return {
        "studies": [
            {
                "study_id": "INC1",
                "design": "rct",
                "year": 2025,
                "source_id": "inc-1",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "INC2",
                "design": "rct",
                "year": 2025,
                "source_id": "inc-2",
                "rob_domain_summary": "low",
            },
            {
                "study_id": "INC3",
                "design": "rct",
                "year": 2025,
                "source_id": "inc-3",
                "rob_domain_summary": "low",
            },
        ],
        "arms": [
            {"study_id": "INC1", "arm_id": "A1", "treatment_id": "A", "n": spec.n_per_arm},
            {"study_id": "INC1", "arm_id": "A2", "treatment_id": "B", "n": spec.n_per_arm},
            {"study_id": "INC2", "arm_id": "B1", "treatment_id": "A", "n": spec.n_per_arm},
            {"study_id": "INC2", "arm_id": "B2", "treatment_id": "C", "n": spec.n_per_arm},
            {"study_id": "INC3", "arm_id": "C1", "treatment_id": "B", "n": spec.n_per_arm},
            {"study_id": "INC3", "arm_id": "C2", "treatment_id": "C", "n": spec.n_per_arm},
        ],
        "outcomes_ad": [
            {
                "study_id": "INC1",
                "arm_id": "A1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": spec.se,
            },
            {
                "study_id": "INC1",
                "arm_id": "A2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": spec.ab_effect,
                "se": spec.se,
            },
            {
                "study_id": "INC2",
                "arm_id": "B1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": spec.se,
            },
            {
                "study_id": "INC2",
                "arm_id": "B2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": spec.ac_effect,
                "se": spec.se,
            },
            {
                "study_id": "INC3",
                "arm_id": "C1",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": 0.0,
                "se": spec.se,
            },
            {
                "study_id": "INC3",
                "arm_id": "C2",
                "outcome_id": "efficacy",
                "measure_type": "continuous",
                "value": spec.bc_direct_effect,
                "se": spec.se,
            },
        ],
    }


def survival_nonph_truth_log_hazard_ratios(
    spec: SurvivalNonPHSimulationSpec | None = None,
) -> dict[str, dict[str, float]]:
    spec = spec or SurvivalNonPHSimulationSpec()
    _validate_survival_spec(spec)
    truth: dict[str, dict[str, float]] = {}
    for idx, _bounds in enumerate(spec.interval_bounds):
        interval_id = f"I{idx + 1}"
        truth[interval_id] = {
            "A": 0.0,
            "B": math.log(spec.hr_b[idx]),
            "C": math.log(spec.hr_c[idx]),
        }
    return truth


def simulate_survival_nonph_network(
    spec: SurvivalNonPHSimulationSpec | None = None,
) -> dict[str, Any]:
    """Return synthetic AD survival payload with interval-varying treatment effects."""
    spec = spec or SurvivalNonPHSimulationSpec()
    _validate_survival_spec(spec)
    rng = np.random.default_rng(spec.seed)

    studies: list[dict[str, Any]] = []
    arms: list[dict[str, Any]] = []
    survival_ad: list[dict[str, Any]] = []
    pair_defs = [("A", "B"), ("A", "C"), ("B", "C")]

    study_index = 1
    for pair in pair_defs:
        trt_a, trt_b = pair
        for rep in range(spec.replicates_per_pair):
            study_id = f"SURV{study_index}"
            study_index += 1
            studies.append(
                {
                    "study_id": study_id,
                    "design": "rct",
                    "year": 2025,
                    "source_id": f"surv-{pair[0]}{pair[1]}-{rep + 1}",
                    "rob_domain_summary": "low",
                }
            )
            arm_1 = f"{study_id}_A1"
            arm_2 = f"{study_id}_A2"
            arms.extend(
                [
                    {
                        "study_id": study_id,
                        "arm_id": arm_1,
                        "treatment_id": trt_a,
                        "n": spec.n_per_arm,
                    },
                    {
                        "study_id": study_id,
                        "arm_id": arm_2,
                        "treatment_id": trt_b,
                        "n": spec.n_per_arm,
                    },
                ]
            )
            for idx, (t_start, t_end) in enumerate(spec.interval_bounds):
                interval_id = f"I{idx + 1}"
                duration = t_end - t_start
                person_time = spec.n_per_arm * duration * spec.follow_up_fraction
                for arm_id, treatment in ((arm_1, trt_a), (arm_2, trt_b)):
                    hazard = spec.baseline_hazards[idx] * _treatment_hr(
                        treatment=treatment,
                        idx=idx,
                        spec=spec,
                    )
                    expected_events = hazard * person_time
                    events = int(rng.poisson(lam=max(expected_events, 1e-6)))
                    survival_ad.append(
                        {
                            "study_id": study_id,
                            "arm_id": arm_id,
                            "outcome_id": "os",
                            "interval_id": interval_id,
                            "t_start": float(t_start),
                            "t_end": float(t_end),
                            "events": events,
                            "person_time": float(person_time),
                        }
                    )

    return {
        "studies": studies,
        "arms": arms,
        "survival_ad": survival_ad,
        "truth": {"log_hazard_ratios_vs_A": survival_nonph_truth_log_hazard_ratios(spec)},
    }


def _treatment_hr(
    *,
    treatment: str,
    idx: int,
    spec: SurvivalNonPHSimulationSpec,
) -> float:
    if treatment == "A":
        return 1.0
    if treatment == "B":
        return spec.hr_b[idx]
    if treatment == "C":
        return spec.hr_c[idx]
    raise ValueError(f"Unsupported treatment in simulation: {treatment}")


def _validate_survival_spec(spec: SurvivalNonPHSimulationSpec) -> None:
    n_intervals = len(spec.interval_bounds)
    if n_intervals < 1:
        raise ValueError("SurvivalNonPHSimulationSpec requires at least one interval.")
    if spec.replicates_per_pair < 1:
        raise ValueError("replicates_per_pair must be >= 1.")
    if spec.n_per_arm <= 0:
        raise ValueError("n_per_arm must be > 0.")
    if spec.follow_up_fraction <= 0:
        raise ValueError("follow_up_fraction must be > 0.")
    if len(spec.baseline_hazards) != n_intervals:
        raise ValueError("baseline_hazards length must match interval_bounds.")
    if len(spec.hr_b) != n_intervals or len(spec.hr_c) != n_intervals:
        raise ValueError("hr_b/hr_c lengths must match interval_bounds.")
    for idx, (t_start, t_end) in enumerate(spec.interval_bounds):
        if t_start < 0 or t_end <= t_start:
            raise ValueError(
                f"Invalid interval_bounds[{idx}]={t_start, t_end}; require t_end > t_start >= 0."
            )
    if any(h <= 0 for h in spec.baseline_hazards):
        raise ValueError("baseline_hazards must be > 0.")
    if any(h <= 0 for h in spec.hr_b) or any(h <= 0 for h in spec.hr_c):
        raise ValueError("All hazard ratios must be > 0.")
