from __future__ import annotations

import numpy as np

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.spec import SurvivalNPHSpec
from nma_pool.models.survival_nph import SurvivalNPHPooler
from nma_pool.validation.simulation import (
    SurvivalNonPHSimulationSpec,
    simulate_survival_nonph_network,
    survival_nonph_truth_log_hazard_ratios,
)


def test_survival_nonph_calibration_thresholds() -> None:
    mae_values: list[float] = []
    coverage_flags: list[bool] = []
    for seed in range(80):
        sim_spec = SurvivalNonPHSimulationSpec(
            seed=seed,
            n_per_arm=650,
            replicates_per_pair=2,
        )
        payload = simulate_survival_nonph_network(sim_spec)
        fit = SurvivalNPHPooler().fit(
            DatasetBuilder().from_payload(payload),
            SurvivalNPHSpec(
                outcome_id="os",
                reference_treatment="A",
                continuity_correction=0.5,
            ),
        )
        truth = survival_nonph_truth_log_hazard_ratios(sim_spec)
        for interval_id in fit.interval_ids:
            for treatment in ("B", "C"):
                estimate = fit.treatment_effects_by_interval[interval_id][treatment]
                se = fit.treatment_ses_by_interval[interval_id][treatment]
                target = truth[interval_id][treatment]
                mae_values.append(abs(estimate - target))
                lo = estimate - (1.96 * se)
                hi = estimate + (1.96 * se)
                coverage_flags.append(lo <= target <= hi)

    median_mae = float(np.median(np.asarray(mae_values, dtype=float)))
    coverage = float(np.mean(np.asarray(coverage_flags, dtype=float)))
    assert median_mae < 0.10
    assert 0.93 <= coverage <= 0.97
