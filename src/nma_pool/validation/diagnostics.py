"""Basic diagnostics for initial NMA runs."""

from __future__ import annotations

from dataclasses import dataclass

from nma_pool.data.builder import EvidenceDataset


@dataclass(frozen=True)
class NetworkDiagnostics:
    study_count: int
    treatment_count: int
    contrast_count: int
    outcome_id: str


def summarize_network(dataset: EvidenceDataset, outcome_id: str) -> NetworkDiagnostics:
    studies = {
        outcome.study_id for outcome in dataset.outcomes_ad if outcome.outcome_id == outcome_id
    }
    treatments = set(dataset.treatments_for_outcome(outcome_id))
    contrasts = 0
    for study_id in studies:
        arms = dataset.outcomes_by_study_outcome(study_id, outcome_id)
        if len(arms) >= 2:
            contrasts += len(arms) - 1

    return NetworkDiagnostics(
        study_count=len(studies),
        treatment_count=len(treatments),
        contrast_count=contrasts,
        outcome_id=outcome_id,
    )

