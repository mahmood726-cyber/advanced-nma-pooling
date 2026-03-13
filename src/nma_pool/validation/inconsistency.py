"""Inconsistency diagnostics for AD NMA networks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math

import numpy as np

from nma_pool.data.builder import DatasetBuilder, EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import ModelSpec

from .contrasts import (
    StudyContrast,
    StudyContrastBlock,
    extract_study_contrast_blocks,
    extract_study_contrasts,
)
from .stats import chi_square_sf, two_sided_p_from_z


@dataclass(frozen=True)
class NodeSplitResult:
    treatment_lo: str
    treatment_hi: str
    n_direct_studies: int
    direct_effect_hi_minus_lo: float
    direct_se: float
    indirect_effect_hi_minus_lo: float
    indirect_se: float
    difference: float
    z_score: float
    p_value: float
    flagged: bool

    @property
    def pair(self) -> tuple[str, str]:
        return (self.treatment_lo, self.treatment_hi)


@dataclass(frozen=True)
class DesignByTreatmentResult:
    q_consistency: float
    q_design: float
    q_inconsistency: float
    df: int
    p_value: float
    flagged: bool


@dataclass(frozen=True)
class InconsistencyDiagnostics:
    global_test: DesignByTreatmentResult
    node_splits: tuple[NodeSplitResult, ...]
    flagged: bool
    warnings: tuple[str, ...]


def run_inconsistency_diagnostics(
    dataset: EvidenceDataset,
    spec: ModelSpec,
    *,
    alpha: float = 0.05,
    max_pairs: int | None = None,
) -> InconsistencyDiagnostics:
    contrasts = extract_study_contrasts(
        dataset=dataset,
        outcome_id=spec.outcome_id,
        measure_type=spec.measure_type,
    )
    warnings: list[str] = []
    if not contrasts:
        empty = DesignByTreatmentResult(
            q_consistency=0.0,
            q_design=0.0,
            q_inconsistency=0.0,
            df=0,
            p_value=1.0,
            flagged=False,
        )
        return InconsistencyDiagnostics(
            global_test=empty,
            node_splits=(),
            flagged=False,
            warnings=("No contrasts available for inconsistency diagnostics.",),
        )

    global_test = design_by_treatment_test(dataset=dataset, spec=spec, alpha=alpha)
    node_splits = node_splitting_diagnostics(
        dataset=dataset,
        spec=spec,
        alpha=alpha,
        max_pairs=max_pairs,
    )
    flagged = global_test.flagged or any(row.flagged for row in node_splits)
    if global_test.df == 0:
        warnings.append("Global inconsistency test has df=0 (no closed loops detected).")
    return InconsistencyDiagnostics(
        global_test=global_test,
        node_splits=node_splits,
        flagged=flagged,
        warnings=tuple(warnings),
    )


def design_by_treatment_test(
    dataset: EvidenceDataset,
    spec: ModelSpec,
    *,
    alpha: float = 0.05,
) -> DesignByTreatmentResult:
    blocks = extract_study_contrast_blocks(
        dataset=dataset,
        outcome_id=spec.outcome_id,
        measure_type=spec.measure_type,
    )
    if not blocks:
        return DesignByTreatmentResult(0.0, 0.0, 0.0, 0, 1.0, False)

    y, v, plus, minus, canonical_pairs, signs = _flatten_blocks(blocks)
    treatments = sorted(set(plus).union(minus))
    if not treatments:
        return DesignByTreatmentResult(0.0, 0.0, 0.0, 0, 1.0, False)

    reference = spec.reference_treatment if spec.reference_treatment in treatments else treatments[0]
    x_cons = _build_consistency_design(
        plus=plus,
        minus=minus,
        reference=reference,
        all_treatments=treatments,
    )
    unique_pairs = sorted(set(canonical_pairs))
    x_design = _build_design_interaction_matrix(
        canonical_pairs=canonical_pairs,
        signs_hi_minus_lo=signs,
        unique_pairs=unique_pairs,
    )

    q_consistency = _gls_q_stat(y=y, x=x_cons, v=v)
    q_design = _gls_q_stat(y=y, x=x_design, v=v)
    q_inconsistency = max(q_consistency - q_design, 0.0)

    rank_cons = int(np.linalg.matrix_rank(x_cons))
    rank_design = int(np.linalg.matrix_rank(x_design))
    df = max(rank_design - rank_cons, 0)
    p_value = chi_square_sf(q_inconsistency, df)
    return DesignByTreatmentResult(
        q_consistency=q_consistency,
        q_design=q_design,
        q_inconsistency=q_inconsistency,
        df=df,
        p_value=p_value,
        flagged=(df > 0 and p_value < alpha),
    )


def node_splitting_diagnostics(
    dataset: EvidenceDataset,
    spec: ModelSpec,
    *,
    alpha: float = 0.05,
    max_pairs: int | None = None,
) -> tuple[NodeSplitResult, ...]:
    contrasts = extract_study_contrasts(
        dataset=dataset,
        outcome_id=spec.outcome_id,
        measure_type=spec.measure_type,
    )
    pair_groups = _group_by_pair(contrasts)
    pairs = sorted(
        pair_groups,
        key=lambda pair: (-len(pair_groups[pair]), pair[0], pair[1]),
    )
    if max_pairs is not None:
        pairs = pairs[: max(0, max_pairs)]

    results: list[NodeSplitResult] = []
    for pair in pairs:
        direct_rows = pair_groups[pair]
        if not direct_rows:
            continue
        direct_study_ids = {row.study_id for row in direct_rows}
        direct_effect, direct_se = _pool_fixed_effect(direct_rows)

        try:
            reduced_dataset = _exclude_studies(dataset, direct_study_ids)
        except ValidationError:
            continue

        try:
            reduced_treatments = set(reduced_dataset.treatments_for_outcome(spec.outcome_id))
        except ValidationError:
            continue
        if pair[0] not in reduced_treatments or pair[1] not in reduced_treatments:
            continue

        ref = pair[0] if pair[0] in reduced_treatments else sorted(reduced_treatments)[0]
        try:
            indirect_fit = ADNMAPooler().fit(
                dataset=reduced_dataset,
                spec=ModelSpec(
                    outcome_id=spec.outcome_id,
                    measure_type=spec.measure_type,
                    reference_treatment=ref,
                    random_effects=spec.random_effects,
                ),
            )
        except ValidationError:
            continue

        try:
            indirect_effect, indirect_se = indirect_fit.contrast(pair[1], pair[0])
        except KeyError:
            continue

        total_se = math.sqrt(max(direct_se * direct_se + indirect_se * indirect_se, 1e-12))
        diff = direct_effect - indirect_effect
        z_score = diff / total_se
        p_value = two_sided_p_from_z(z_score)
        results.append(
            NodeSplitResult(
                treatment_lo=pair[0],
                treatment_hi=pair[1],
                n_direct_studies=len(direct_rows),
                direct_effect_hi_minus_lo=direct_effect,
                direct_se=direct_se,
                indirect_effect_hi_minus_lo=indirect_effect,
                indirect_se=indirect_se,
                difference=diff,
                z_score=z_score,
                p_value=p_value,
                flagged=p_value < alpha,
            )
        )
    return tuple(results)


def _group_by_pair(
    contrasts: list[StudyContrast],
) -> dict[tuple[str, str], list[StudyContrast]]:
    groups: dict[tuple[str, str], list[StudyContrast]] = defaultdict(list)
    for row in contrasts:
        groups[row.pair].append(row)
    return groups


def _pool_fixed_effect(rows: list[StudyContrast]) -> tuple[float, float]:
    weights = [1.0 / row.variance for row in rows]
    total_w = sum(weights)
    if total_w <= 0:
        raise ValidationError("Invalid contrast variances for direct pooling.")
    effect = sum(w * row.effect_hi_minus_lo for w, row in zip(weights, rows)) / total_w
    se = math.sqrt(1.0 / total_w)
    return effect, se


def _exclude_studies(
    dataset: EvidenceDataset,
    excluded_study_ids: set[str],
) -> EvidenceDataset:
    builder = DatasetBuilder()
    studies = [row for row in dataset.studies if row.study_id not in excluded_study_ids]
    arms = [row for row in dataset.arms if row.study_id not in excluded_study_ids]
    outcomes = [
        row for row in dataset.outcomes_ad if row.study_id not in excluded_study_ids
    ]
    provenance = list(dataset.provenance)
    return builder.from_records(
        studies=studies,
        arms=arms,
        outcomes_ad=outcomes,
        provenance=provenance,
    )


def _flatten_blocks(
    blocks: list[StudyContrastBlock],
) -> tuple[
    np.ndarray,
    np.ndarray,
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, str], ...],
    tuple[int, ...],
]:
    y_parts: list[np.ndarray] = []
    v_blocks: list[np.ndarray] = []
    plus: list[str] = []
    minus: list[str] = []
    canonical_pairs: list[tuple[str, str]] = []
    signs: list[int] = []
    for block in blocks:
        y_parts.append(block.effects)
        v_blocks.append(block.covariance)
        plus.extend(block.treatment_plus)
        minus.extend(block.treatment_minus)
        canonical_pairs.extend(block.canonical_pairs)
        signs.extend(block.signs_hi_minus_lo)
    y = np.concatenate(y_parts, axis=0)
    v = _block_diag(v_blocks)
    return (
        y,
        v,
        tuple(plus),
        tuple(minus),
        tuple(canonical_pairs),
        tuple(signs),
    )


def _build_consistency_design(
    *,
    plus: tuple[str, ...],
    minus: tuple[str, ...],
    reference: str,
    all_treatments: list[str],
) -> np.ndarray:
    columns = [treatment for treatment in all_treatments if treatment != reference]
    if not columns:
        return np.zeros((len(plus), 1), dtype=float)
    col_ix = {treatment: idx for idx, treatment in enumerate(columns)}
    x = np.zeros((len(plus), len(columns)), dtype=float)
    for row_ix, (trt_plus, trt_minus) in enumerate(zip(plus, minus)):
        if trt_plus != reference:
            x[row_ix, col_ix[trt_plus]] += 1.0
        if trt_minus != reference:
            x[row_ix, col_ix[trt_minus]] -= 1.0
    return x


def _build_design_interaction_matrix(
    *,
    canonical_pairs: tuple[tuple[str, str], ...],
    signs_hi_minus_lo: tuple[int, ...],
    unique_pairs: list[tuple[str, str]],
) -> np.ndarray:
    if not unique_pairs:
        return np.zeros((len(canonical_pairs), 1), dtype=float)
    col_ix = {pair: idx for idx, pair in enumerate(unique_pairs)}
    x = np.zeros((len(canonical_pairs), len(unique_pairs)), dtype=float)
    for row_ix, (pair, sign) in enumerate(zip(canonical_pairs, signs_hi_minus_lo)):
        x[row_ix, col_ix[pair]] = float(sign)
    return x


def _gls_q_stat(y: np.ndarray, x: np.ndarray, v: np.ndarray) -> float:
    if y.size == 0:
        return 0.0
    v_inv = _inverse_or_pinv(v)
    xt_v_inv = x.T @ v_inv
    info = xt_v_inv @ x
    beta = _solve_or_pinv(info, xt_v_inv @ y)
    resid = y - (x @ beta)
    q = float(resid.T @ v_inv @ resid)
    return max(q, 0.0)


def _block_diag(blocks: list[np.ndarray]) -> np.ndarray:
    size = sum(block.shape[0] for block in blocks)
    out = np.zeros((size, size), dtype=float)
    cursor = 0
    for block in blocks:
        n = block.shape[0]
        out[cursor : cursor + n, cursor : cursor + n] = block
        cursor += n
    return out


def _inverse_or_pinv(matrix: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(matrix)


def _solve_or_pinv(matrix: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(matrix) @ rhs
