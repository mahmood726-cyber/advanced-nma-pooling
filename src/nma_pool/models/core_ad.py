"""Core aggregate-data random-effects NMA pooling model."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.network import connected_components
from nma_pool.data.schemas import ValidationError
from nma_pool.models.spec import ModelSpec


@dataclass(frozen=True)
class NMAFitResult:
    """Model fit result container."""

    outcome_id: str
    measure_type: str
    reference_treatment: str
    treatment_effects: dict[str, float]
    treatment_ses: dict[str, float]
    parameter_treatments: tuple[str, ...]
    parameter_cov: np.ndarray
    tau: float
    n_studies: int
    n_contrasts: int
    warnings: tuple[str, ...]

    def contrast(self, treatment_a: str, treatment_b: str) -> tuple[float, float]:
        """Return effect and SE for treatment_a minus treatment_b."""
        if treatment_a not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_a}")
        if treatment_b not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_b}")

        effect = self.treatment_effects[treatment_a] - self.treatment_effects[treatment_b]
        variance = self._variance_for_contrast(treatment_a, treatment_b)
        return effect, math.sqrt(max(variance, 0.0))

    def summary_rows(self) -> list[dict[str, float | str]]:
        rows: list[dict[str, float | str]] = []
        for treatment in sorted(self.treatment_effects):
            rows.append(
                {
                    "treatment": treatment,
                    "effect_vs_reference": self.treatment_effects[treatment],
                    "se": self.treatment_ses[treatment],
                }
            )
        return rows

    def _variance_for_contrast(self, treatment_a: str, treatment_b: str) -> float:
        if treatment_a == treatment_b:
            return 0.0
        var_a = self._variance_for_treatment(treatment_a)
        var_b = self._variance_for_treatment(treatment_b)
        cov_ab = self._covariance_for_treatments(treatment_a, treatment_b)
        return var_a + var_b - (2.0 * cov_ab)

    def _variance_for_treatment(self, treatment: str) -> float:
        if treatment == self.reference_treatment:
            return 0.0
        idx = self.parameter_treatments.index(treatment)
        return float(self.parameter_cov[idx, idx])

    def _covariance_for_treatments(self, treatment_a: str, treatment_b: str) -> float:
        if treatment_a == self.reference_treatment or treatment_b == self.reference_treatment:
            return 0.0
        idx_a = self.parameter_treatments.index(treatment_a)
        idx_b = self.parameter_treatments.index(treatment_b)
        return float(self.parameter_cov[idx_a, idx_b])


@dataclass(frozen=True)
class _ArmEffect:
    study_id: str
    arm_id: str
    treatment_id: str
    mean: float
    variance: float


@dataclass(frozen=True)
class _StudyBlock:
    study_id: str
    y: np.ndarray
    v: np.ndarray
    trt_plus: tuple[str, ...]
    trt_minus: tuple[str, ...]


class ADNMAPooler:
    """Core random-effects contrast-based NMA estimator for AD."""

    def fit(self, dataset: EvidenceDataset, spec: ModelSpec) -> NMAFitResult:
        measure = dataset.measure_type_for_outcome(spec.outcome_id)
        if measure != spec.measure_type:
            raise ValidationError(
                "ModelSpec measure_type does not match dataset outcome measure type: "
                f"{spec.measure_type} vs {measure}."
            )

        blocks = self._build_study_blocks(dataset, spec.outcome_id, spec.measure_type)
        if not blocks:
            raise ValidationError(f"No studies available for outcome_id '{spec.outcome_id}'.")

        all_treatments = self._all_treatments(blocks)
        if spec.reference_treatment not in all_treatments:
            raise ValidationError(
                f"reference_treatment '{spec.reference_treatment}' not present in outcome network."
            )
        parameter_treatments = tuple(
            treatment
            for treatment in sorted(all_treatments)
            if treatment != spec.reference_treatment
        )
        if not parameter_treatments:
            raise ValidationError("At least one non-reference treatment is required.")

        self._validate_identifiable_network(
            blocks=blocks,
            reference_treatment=spec.reference_treatment,
            outcome_id=spec.outcome_id,
        )
        y, x, v = self._assemble_design(blocks, parameter_treatments, spec.reference_treatment)
        warnings: list[str] = []
        if np.linalg.matrix_rank(x) < x.shape[1]:
            raise ValidationError(
                f"Outcome '{spec.outcome_id}' design matrix is rank-deficient; "
                "treatment effects are not identifiable for the supplied network."
            )

        tau = 0.0
        if spec.random_effects and y.shape[0] > x.shape[1]:
            tau = self._optimize_tau_reml(y=y, x=x, v=v)

        beta, cov = self._estimate_beta_cov(y=y, x=x, v=v, tau=tau)
        treatment_effects = {spec.reference_treatment: 0.0}
        treatment_ses = {spec.reference_treatment: 0.0}
        for idx, treatment in enumerate(parameter_treatments):
            treatment_effects[treatment] = float(beta[idx])
            treatment_ses[treatment] = math.sqrt(max(float(cov[idx, idx]), 0.0))

        return NMAFitResult(
            outcome_id=spec.outcome_id,
            measure_type=spec.measure_type,
            reference_treatment=spec.reference_treatment,
            treatment_effects=treatment_effects,
            treatment_ses=treatment_ses,
            parameter_treatments=parameter_treatments,
            parameter_cov=cov,
            tau=float(tau),
            n_studies=len(blocks),
            n_contrasts=int(y.shape[0]),
            warnings=tuple(warnings),
        )

    def _build_study_blocks(
        self,
        dataset: EvidenceDataset,
        outcome_id: str,
        measure_type: str,
    ) -> list[_StudyBlock]:
        arm_lookup = dataset.arm_lookup()
        studies_with_outcome = sorted(
            {
                outcome.study_id
                for outcome in dataset.outcomes_ad
                if outcome.outcome_id == outcome_id
            }
        )

        blocks: list[_StudyBlock] = []
        for study_id in studies_with_outcome:
            outcomes = dataset.outcomes_by_study_outcome(study_id, outcome_id)
            if len(outcomes) < 2:
                continue

            arm_effects: list[_ArmEffect] = []
            for outcome in outcomes:
                if outcome.measure_type != measure_type:
                    continue
                arm = arm_lookup[(outcome.study_id, outcome.arm_id)]
                mean, variance = self._arm_measure_and_variance(
                    n=arm.n,
                    value=outcome.value,
                    se=outcome.se,
                    measure_type=measure_type,
                )
                arm_effects.append(
                    _ArmEffect(
                        study_id=study_id,
                        arm_id=arm.arm_id,
                        treatment_id=arm.treatment_id,
                        mean=mean,
                        variance=variance,
                    )
                )

            if len(arm_effects) < 2:
                continue
            arm_effects.sort(key=lambda row: row.arm_id)
            baseline = arm_effects[0]
            nonbaseline = arm_effects[1:]
            y = np.array(
                [arm.mean - baseline.mean for arm in nonbaseline],
                dtype=float,
            )
            baseline_var = baseline.variance
            v = np.full((len(nonbaseline), len(nonbaseline)), baseline_var, dtype=float)
            for idx, arm in enumerate(nonbaseline):
                v[idx, idx] = baseline_var + arm.variance
            blocks.append(
                _StudyBlock(
                    study_id=study_id,
                    y=y,
                    v=v,
                    trt_plus=tuple(arm.treatment_id for arm in nonbaseline),
                    trt_minus=tuple(baseline.treatment_id for _ in nonbaseline),
                )
            )
        return blocks

    @staticmethod
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

        if measure_type != "binary":
            raise ValidationError(f"Unsupported measure_type: {measure_type}")

        events = value
        non_events = float(n) - value
        if events < 0 or non_events < 0:
            raise ValidationError("Binary outcome value must be within [0, n].")

        cc = 0.5
        odds = (events + cc) / (non_events + cc)
        mean = math.log(odds)
        variance = (1.0 / (events + cc)) + (1.0 / (non_events + cc))
        return mean, variance

    @staticmethod
    def _all_treatments(blocks: Iterable[_StudyBlock]) -> set[str]:
        treatments: set[str] = set()
        for block in blocks:
            treatments.update(block.trt_plus)
            treatments.update(block.trt_minus)
        return treatments

    def _connected_treatment_components(
        self,
        blocks: Iterable[_StudyBlock],
    ) -> tuple[tuple[str, ...], ...]:
        treatments = self._all_treatments(blocks)
        edges: set[tuple[str, str]] = set()
        for block in blocks:
            study_treatments = sorted(set(block.trt_plus) | set(block.trt_minus))
            for left_idx, left in enumerate(study_treatments):
                for right in study_treatments[left_idx + 1 :]:
                    edges.add((left, right))
        return connected_components(treatments, edges)

    def _validate_identifiable_network(
        self,
        *,
        blocks: Iterable[_StudyBlock],
        reference_treatment: str,
        outcome_id: str,
    ) -> None:
        components = self._connected_treatment_components(blocks)
        if len(components) <= 1:
            return

        reference_component = next(
            component
            for component in components
            if reference_treatment in component
        )
        disconnected = tuple(
            component
            for component in components
            if reference_treatment not in component
        )
        disconnected_text = "; ".join(", ".join(component) for component in disconnected)
        raise ValidationError(
            f"Outcome '{outcome_id}' has a disconnected treatment network for "
            f"reference_treatment '{reference_treatment}'. Reference component: "
            f"{', '.join(reference_component)}. Disconnected components: {disconnected_text}."
        )

    @staticmethod
    def _assemble_design(
        blocks: Iterable[_StudyBlock],
        parameter_treatments: tuple[str, ...],
        reference_treatment: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        treatment_to_col = {treatment: i for i, treatment in enumerate(parameter_treatments)}
        y_parts: list[np.ndarray] = []
        x_parts: list[np.ndarray] = []
        v_blocks: list[np.ndarray] = []

        for block in blocks:
            y_parts.append(block.y)
            row_count = block.y.shape[0]
            x_block = np.zeros((row_count, len(parameter_treatments)), dtype=float)
            for row_idx, (trt_plus, trt_minus) in enumerate(zip(block.trt_plus, block.trt_minus)):
                if trt_plus != reference_treatment:
                    x_block[row_idx, treatment_to_col[trt_plus]] += 1.0
                if trt_minus != reference_treatment:
                    x_block[row_idx, treatment_to_col[trt_minus]] -= 1.0
            x_parts.append(x_block)
            v_blocks.append(block.v)

        y = np.concatenate(y_parts, axis=0)
        x = np.vstack(x_parts)
        v = _block_diag(v_blocks)
        return y, x, v

    def _optimize_tau_reml(self, y: np.ndarray, x: np.ndarray, v: np.ndarray) -> float:
        lo = 0.0
        hi = 1.0
        nll_lo = self._reml_nll(lo, y, x, v)
        nll_hi = self._reml_nll(hi, y, x, v)
        while nll_hi < nll_lo and hi < 16.0:
            lo = hi
            nll_lo = nll_hi
            hi *= 2.0
            nll_hi = self._reml_nll(hi, y, x, v)

        best_tau = 0.0
        best_nll = self._reml_nll(best_tau, y, x, v)
        left = 0.0
        right = hi
        for _ in range(6):
            grid = np.linspace(left, right, 81)
            nll_values = [self._reml_nll(float(tau), y, x, v) for tau in grid]
            idx = int(np.argmin(nll_values))
            if nll_values[idx] < best_nll:
                best_nll = nll_values[idx]
                best_tau = float(grid[idx])

            left_idx = max(0, idx - 1)
            right_idx = min(len(grid) - 1, idx + 1)
            left = float(grid[left_idx])
            right = float(grid[right_idx])
            if right - left < 1e-4:
                break
        return max(best_tau, 0.0)

    def _reml_nll(self, tau: float, y: np.ndarray, x: np.ndarray, v: np.ndarray) -> float:
        m = v + np.eye(v.shape[0], dtype=float) * (tau * tau)
        try:
            m_inv = np.linalg.inv(m)
        except np.linalg.LinAlgError:
            return float("inf")

        xt_m_inv = x.T @ m_inv
        info = xt_m_inv @ x
        sign_m, logdet_m = np.linalg.slogdet(m)
        sign_info, logdet_info = np.linalg.slogdet(info)
        if sign_m <= 0 or sign_info <= 0:
            return float("inf")

        beta = _solve_or_pinv(info, xt_m_inv @ y)
        resid = y - (x @ beta)
        q = float(resid.T @ m_inv @ resid)
        return 0.5 * (logdet_m + logdet_info + q)

    @staticmethod
    def _estimate_beta_cov(
        y: np.ndarray,
        x: np.ndarray,
        v: np.ndarray,
        tau: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        m = v + np.eye(v.shape[0], dtype=float) * (tau * tau)
        m_inv = np.linalg.inv(m)
        xt_m_inv = x.T @ m_inv
        info = xt_m_inv @ x
        cov = _inverse_or_pinv(info)
        beta = cov @ xt_m_inv @ y
        return beta, cov


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
