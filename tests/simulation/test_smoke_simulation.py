from __future__ import annotations

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import ModelSpec
from nma_pool.validation.simulation import simulate_continuous_abc_network


def test_simulation_smoke_run() -> None:
    payload = simulate_continuous_abc_network()
    dataset = DatasetBuilder().from_payload(payload)
    fit = ADNMAPooler().fit(
        dataset,
        ModelSpec(
            outcome_id="efficacy",
            measure_type="continuous",
            reference_treatment="A",
            random_effects=True,
        ),
    )
    assert "B" in fit.treatment_effects
    assert "C" in fit.treatment_effects
    assert fit.n_studies == 3

