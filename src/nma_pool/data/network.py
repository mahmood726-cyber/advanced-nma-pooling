"""Treatment-network topology helpers."""

from __future__ import annotations

from collections import deque
from typing import Iterable

from nma_pool.data.builder import EvidenceDataset


def connected_components(
    treatments: Iterable[str],
    edges: Iterable[tuple[str, str]],
) -> tuple[tuple[str, ...], ...]:
    """Return sorted connected components for an undirected treatment graph."""

    adjacency: dict[str, set[str]] = {treatment: set() for treatment in treatments}
    for left, right in edges:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    unseen = set(adjacency)
    components: list[tuple[str, ...]] = []
    while unseen:
        start = min(unseen)
        queue: deque[str] = deque([start])
        component: set[str] = set()
        while queue:
            node = queue.popleft()
            if node in component:
                continue
            component.add(node)
            queue.extend(sorted(adjacency[node] - component))
        unseen -= component
        components.append(tuple(sorted(component)))
    return tuple(sorted(components, key=lambda row: row[0]))


def ad_treatment_components(
    dataset: EvidenceDataset,
    outcome_id: str,
    *,
    measure_type: str | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Return connected treatment components for an AD outcome network."""

    arm_lookup = dataset.arm_lookup()
    studies = sorted(
        {
            outcome.study_id
            for outcome in dataset.outcomes_ad
            if outcome.outcome_id == outcome_id
            and (measure_type is None or outcome.measure_type == measure_type)
        }
    )

    treatments: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for study_id in studies:
        study_treatments = sorted(
            {
                arm_lookup[(outcome.study_id, outcome.arm_id)].treatment_id
                for outcome in dataset.outcomes_by_study_outcome(study_id, outcome_id)
                if measure_type is None or outcome.measure_type == measure_type
            }
        )
        treatments.update(study_treatments)
        for left_idx, left in enumerate(study_treatments):
            for right in study_treatments[left_idx + 1 :]:
                edges.add((left, right))

    if not treatments:
        return ()
    return connected_components(treatments, edges)
