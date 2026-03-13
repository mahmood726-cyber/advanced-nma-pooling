"""Study-level contrast extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError


@dataclass(frozen=True)
class ArmEffect:
    treatment_id: str
    mean: float
    variance: float


@dataclass(frozen=True)
class StudyContrast:
    study_id: str
    treatment_lo: str
    treatment_hi: str
    effect_hi_minus_lo: float
    variance: float

    @property
    def se(self) -> float:
        return math.sqrt(max(self.variance, 0.0))

    @property
    def pair(self) -> tuple[str, str]:
        return (self.treatment_lo, self.treatment_hi)


@dataclass(frozen=True)
class StudyContrastBlock:
    study_id: str
    effects: np.ndarray
    covariance: np.ndarray
    treatment_plus: tuple[str, ...]
    treatment_minus: tuple[str, ...]
    canonical_pairs: tuple[tuple[str, str], ...]
    signs_hi_minus_lo: tuple[int, ...]

    @property
    def n_rows(self) -> int:
        return int(self.effects.shape[0])


def extract_study_contrasts(
    dataset: EvidenceDataset,
    outcome_id: str,
    measure_type: str,
) -> list[StudyContrast]:
    arm_lookup = dataset.arm_lookup()
    study_ids = sorted(
        {
            row.study_id
            for row in dataset.outcomes_ad
            if row.outcome_id == outcome_id and row.measure_type == measure_type
        }
    )
    results: list[StudyContrast] = []
    for study_id in study_ids:
        rows = dataset.outcomes_by_study_outcome(study_id, outcome_id)
        effects: list[ArmEffect] = []
        for row in rows:
            if row.measure_type != measure_type:
                continue
            arm = arm_lookup[(row.study_id, row.arm_id)]
            mean, variance = _arm_measure_and_variance(
                n=arm.n,
                value=row.value,
                se=row.se,
                measure_type=measure_type,
            )
            effects.append(
                ArmEffect(
                    treatment_id=arm.treatment_id,
                    mean=mean,
                    variance=variance,
                )
            )
        results.extend(_all_pairwise_contrasts(study_id=study_id, effects=effects))
    return results


def extract_study_contrast_blocks(
    dataset: EvidenceDataset,
    outcome_id: str,
    measure_type: str,
) -> list[StudyContrastBlock]:
    arm_lookup = dataset.arm_lookup()
    study_ids = sorted(
        {
            row.study_id
            for row in dataset.outcomes_ad
            if row.outcome_id == outcome_id and row.measure_type == measure_type
        }
    )

    blocks: list[StudyContrastBlock] = []
    for study_id in study_ids:
        rows = dataset.outcomes_by_study_outcome(study_id, outcome_id)
        effects: list[ArmEffect] = []
        arms_order: list[str] = []
        for row in rows:
            if row.measure_type != measure_type:
                continue
            arm = arm_lookup[(row.study_id, row.arm_id)]
            mean, variance = _arm_measure_and_variance(
                n=arm.n,
                value=row.value,
                se=row.se,
                measure_type=measure_type,
            )
            effects.append(
                ArmEffect(
                    treatment_id=arm.treatment_id,
                    mean=mean,
                    variance=variance,
                )
            )
            arms_order.append(arm.arm_id)

        if len(effects) < 2:
            continue

        # Keep deterministic baseline choice via arm_id ordering.
        ordered = [
            effect
            for _, effect in sorted(zip(arms_order, effects), key=lambda item: item[0])
        ]
        baseline = ordered[0]
        nonbaseline = ordered[1:]

        y = np.array(
            [arm.mean - baseline.mean for arm in nonbaseline],
            dtype=float,
        )
        v = np.full((len(nonbaseline), len(nonbaseline)), baseline.variance, dtype=float)
        for idx, arm in enumerate(nonbaseline):
            v[idx, idx] = baseline.variance + arm.variance

        plus = tuple(arm.treatment_id for arm in nonbaseline)
        minus = tuple(baseline.treatment_id for _ in nonbaseline)
        canonical_pairs: list[tuple[str, str]] = []
        signs: list[int] = []
        for trt_plus, trt_minus in zip(plus, minus):
            lo, hi = sorted((trt_plus, trt_minus))
            canonical_pairs.append((lo, hi))
            signs.append(1 if (trt_plus == hi and trt_minus == lo) else -1)

        blocks.append(
            StudyContrastBlock(
                study_id=study_id,
                effects=y,
                covariance=v,
                treatment_plus=plus,
                treatment_minus=minus,
                canonical_pairs=tuple(canonical_pairs),
                signs_hi_minus_lo=tuple(signs),
            )
        )
    return blocks


def _all_pairwise_contrasts(
    study_id: str,
    effects: Iterable[ArmEffect],
) -> list[StudyContrast]:
    rows = list(effects)
    out: list[StudyContrast] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            arm_a = rows[i]
            arm_b = rows[j]
            trt_lo, trt_hi = sorted((arm_a.treatment_id, arm_b.treatment_id))
            if arm_a.treatment_id == trt_lo:
                lo = arm_a
                hi = arm_b
            else:
                lo = arm_b
                hi = arm_a
            out.append(
                StudyContrast(
                    study_id=study_id,
                    treatment_lo=trt_lo,
                    treatment_hi=trt_hi,
                    effect_hi_minus_lo=hi.mean - lo.mean,
                    variance=hi.variance + lo.variance,
                )
            )
    return out


def _arm_measure_and_variance(
    n: int,
    value: float,
    se: float | None,
    measure_type: str,
) -> tuple[float, float]:
    if measure_type == "continuous":
        if se is None or se <= 0:
            raise ValidationError("Continuous outcomes require SE > 0.")
        return value, se * se

    if measure_type == "binary":
        events = value
        non_events = float(n) - value
        if events < 0 or non_events < 0:
            raise ValidationError("Binary outcome value must be within [0, n].")
        cc = 0.5
        odds = (events + cc) / (non_events + cc)
        mean = math.log(odds)
        variance = (1.0 / (events + cc)) + (1.0 / (non_events + cc))
        return mean, variance

    raise ValidationError(f"Unsupported measure_type: {measure_type}")
