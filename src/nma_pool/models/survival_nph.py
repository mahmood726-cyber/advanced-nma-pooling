"""Piecewise-exponential NMA with interval-specific treatment effects."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.spec import SurvivalNPHSpec


@dataclass(frozen=True)
class SurvivalNPHFitResult:
    outcome_id: str
    reference_treatment: str
    interval_ids: tuple[str, ...]
    interval_bounds: dict[str, tuple[float, float]]
    treatment_effects_by_interval: dict[str, dict[str, float]]
    treatment_ses_by_interval: dict[str, dict[str, float]]
    pooled_treatment_effects: dict[str, float]
    pooled_treatment_ses: dict[str, float]
    estimable_by_interval: dict[str, dict[str, bool]]
    parameter_treatments: tuple[str, ...]
    parameter_cov: np.ndarray
    tau: float
    n_studies: int
    n_contrasts: int
    warnings: tuple[str, ...]

    def contrast(
        self,
        treatment_a: str,
        treatment_b: str,
        *,
        interval_id: str,
    ) -> tuple[float, float]:
        effects = self.treatment_effects_by_interval.get(interval_id)
        if effects is None:
            raise KeyError(f"Unknown interval_id: {interval_id}")
        if treatment_a not in effects:
            raise KeyError(f"Unknown treatment: {treatment_a}")
        if treatment_b not in effects:
            raise KeyError(f"Unknown treatment: {treatment_b}")

        effect = effects[treatment_a] - effects[treatment_b]
        if not np.isfinite(effect):
            raise ValidationError(
                f"Contrast ({treatment_a} vs {treatment_b}) is not estimable in interval '{interval_id}'."
            )
        variance = self._contrast_variance(
            treatment_a=treatment_a,
            treatment_b=treatment_b,
            interval_id=interval_id,
        )
        return effect, math.sqrt(max(variance, 0.0))

    def _contrast_variance(
        self,
        *,
        treatment_a: str,
        treatment_b: str,
        interval_id: str,
    ) -> float:
        idx = self.interval_ids.index(interval_id)
        k = len(self.parameter_treatments)
        coeff = np.zeros((len(self.interval_ids) * k,), dtype=float)
        self._fill_coeff(coeff, treatment=treatment_a, sign=+1.0, interval_idx=idx)
        self._fill_coeff(coeff, treatment=treatment_b, sign=-1.0, interval_idx=idx)
        return float(coeff.T @ self.parameter_cov @ coeff)

    def _fill_coeff(
        self,
        coeff: np.ndarray,
        *,
        treatment: str,
        sign: float,
        interval_idx: int,
    ) -> None:
        if treatment == self.reference_treatment:
            return
        k = len(self.parameter_treatments)
        t_idx = self.parameter_treatments.index(treatment)
        coeff[(interval_idx * k) + t_idx] += sign


@dataclass(frozen=True)
class _IntervalArm:
    study_id: str
    interval_id: str
    arm_id: str
    treatment_id: str
    log_hazard: float
    variance: float


@dataclass(frozen=True)
class _IntervalBlock:
    study_id: str
    interval_id: str
    y: np.ndarray
    covariance: np.ndarray
    trt_plus: tuple[str, ...]
    trt_minus: tuple[str, ...]

    @property
    def n_rows(self) -> int:
        return int(self.y.shape[0])


class SurvivalNPHPooler:
    """Fixed-effects piecewise-exponential NMA with non-PH support."""

    def fit(self, dataset: EvidenceDataset, spec: SurvivalNPHSpec) -> SurvivalNPHFitResult:
        if spec.continuity_correction <= 0:
            raise ValidationError("continuity_correction must be > 0.")

        measure = dataset.measure_type_for_outcome(spec.outcome_id)
        if measure != "survival":
            raise ValidationError(
                "SurvivalNPHPooler requires survival_ad records for the selected outcome_id."
            )

        interval_bounds = self._interval_bounds(dataset, spec.outcome_id)
        interval_ids = tuple(
            interval_id
            for interval_id, _bounds in sorted(
                interval_bounds.items(),
                key=lambda item: (item[1][0], item[1][1], item[0]),
            )
        )
        blocks = self._build_blocks(
            dataset=dataset,
            outcome_id=spec.outcome_id,
            continuity_correction=spec.continuity_correction,
        )
        if not blocks:
            raise ValidationError(f"No usable survival intervals for '{spec.outcome_id}'.")

        treatments = sorted(
            {
                treatment
                for block in blocks
                for treatment in (*block.trt_plus, *block.trt_minus)
            }
        )
        if spec.reference_treatment not in treatments:
            raise ValidationError(
                f"reference_treatment '{spec.reference_treatment}' not present in network."
            )
        parameter_treatments = tuple(
            treatment for treatment in treatments if treatment != spec.reference_treatment
        )
        if not parameter_treatments:
            raise ValidationError("At least one non-reference treatment is required.")

        y, x, v = self._assemble_gls(
            blocks=blocks,
            interval_ids=interval_ids,
            parameter_treatments=parameter_treatments,
            reference_treatment=spec.reference_treatment,
        )
        warnings: list[str] = [
            "Interval rows use independent Poisson approximation; within-arm temporal correlation is not explicitly modeled."
        ]
        if np.linalg.matrix_rank(x) < x.shape[1]:
            warnings.append(
                "Survival non-PH design matrix is rank-deficient; estimates use pseudo-inverse."
            )
        tau = 0.0
        if spec.random_effects and y.shape[0] > x.shape[1]:
            tau = self._optimize_tau_reml(y=y, x=x, v=v)
        elif spec.random_effects:
            warnings.append(
                "random_effects=True requested but insufficient degrees of freedom; tau fixed at 0."
            )

        beta, cov = self._estimate_gls(y=y, x=x, v=v, tau=tau)
        estimable_flags = self._estimable_parameter_flags(x=x, v=v, tau=tau)
        effect_table, se_table, estimable_by_interval = self._effects_by_interval(
            beta=beta,
            cov=cov,
            interval_ids=interval_ids,
            parameter_treatments=parameter_treatments,
            reference_treatment=spec.reference_treatment,
            estimable_flags=estimable_flags,
        )
        non_estimable_cells = [
            f"{interval_id}:{treatment}"
            for interval_id in interval_ids
            for treatment, is_ok in estimable_by_interval[interval_id].items()
            if treatment != spec.reference_treatment and not is_ok
        ]
        if non_estimable_cells:
            warnings.append(
                "Non-estimable interval-treatment effects set to NaN: "
                + ", ".join(non_estimable_cells)
            )

        pooled_effects, pooled_ses = self._pooled_effects(
            effect_table=effect_table,
            se_table=se_table,
        )

        return SurvivalNPHFitResult(
            outcome_id=spec.outcome_id,
            reference_treatment=spec.reference_treatment,
            interval_ids=interval_ids,
            interval_bounds=interval_bounds,
            treatment_effects_by_interval=effect_table,
            treatment_ses_by_interval=se_table,
            pooled_treatment_effects=pooled_effects,
            pooled_treatment_ses=pooled_ses,
            estimable_by_interval=estimable_by_interval,
            parameter_treatments=parameter_treatments,
            parameter_cov=cov,
            tau=float(tau),
            n_studies=len({block.study_id for block in blocks}),
            n_contrasts=int(y.shape[0]),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _interval_bounds(
        dataset: EvidenceDataset,
        outcome_id: str,
    ) -> dict[str, tuple[float, float]]:
        bounds: dict[str, tuple[float, float]] = {}
        for row in dataset.survival_ad:
            if row.outcome_id != outcome_id:
                continue
            seen = bounds.get(row.interval_id)
            current = (row.t_start, row.t_end)
            if seen is None:
                bounds[row.interval_id] = current
                continue
            if seen != current:
                raise ValidationError(
                    f"Interval '{row.interval_id}' has inconsistent bounds: {seen} vs {current}."
                )
        if not bounds:
            raise ValidationError(f"No survival_ad rows found for outcome_id '{outcome_id}'.")
        return bounds

    def _build_blocks(
        self,
        *,
        dataset: EvidenceDataset,
        outcome_id: str,
        continuity_correction: float,
    ) -> list[_IntervalBlock]:
        arm_lookup = dataset.arm_lookup()
        grouped: dict[tuple[str, str], list[_IntervalArm]] = defaultdict(list)
        for row in dataset.survival_ad:
            if row.outcome_id != outcome_id:
                continue
            arm = arm_lookup[(row.study_id, row.arm_id)]
            hazard = (row.events + continuity_correction) / row.person_time
            log_hazard = math.log(hazard)
            variance = 1.0 / (row.events + continuity_correction)
            grouped[(row.study_id, row.interval_id)].append(
                _IntervalArm(
                    study_id=row.study_id,
                    interval_id=row.interval_id,
                    arm_id=row.arm_id,
                    treatment_id=arm.treatment_id,
                    log_hazard=log_hazard,
                    variance=variance,
                )
            )

        blocks: list[_IntervalBlock] = []
        for (study_id, interval_id), arms in sorted(grouped.items()):
            block = self._to_block(study_id=study_id, interval_id=interval_id, arms=arms)
            if block is not None:
                blocks.append(block)
        return blocks

    @staticmethod
    def _to_block(
        *,
        study_id: str,
        interval_id: str,
        arms: list[_IntervalArm],
    ) -> _IntervalBlock | None:
        if len(arms) < 2:
            return None
        arms.sort(key=lambda row: row.arm_id)
        baseline = arms[0]
        nonbaseline = arms[1:]
        y = np.array([row.log_hazard - baseline.log_hazard for row in nonbaseline], dtype=float)
        v = np.full((len(nonbaseline), len(nonbaseline)), baseline.variance, dtype=float)
        for idx, row in enumerate(nonbaseline):
            v[idx, idx] = baseline.variance + row.variance
        return _IntervalBlock(
            study_id=study_id,
            interval_id=interval_id,
            y=y,
            covariance=v,
            trt_plus=tuple(row.treatment_id for row in nonbaseline),
            trt_minus=tuple(baseline.treatment_id for _ in nonbaseline),
        )

    @staticmethod
    def _assemble_gls(
        *,
        blocks: list[_IntervalBlock],
        interval_ids: tuple[str, ...],
        parameter_treatments: tuple[str, ...],
        reference_treatment: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        interval_to_ix = {interval_id: idx for idx, interval_id in enumerate(interval_ids)}
        treatment_to_ix = {treatment: idx for idx, treatment in enumerate(parameter_treatments)}
        k = len(parameter_treatments)

        y_parts: list[np.ndarray] = []
        x_parts: list[np.ndarray] = []
        v_blocks: list[np.ndarray] = []
        for block in blocks:
            y_parts.append(block.y)
            n_rows = block.n_rows
            x = np.zeros((n_rows, len(interval_ids) * k), dtype=float)
            i_idx = interval_to_ix[block.interval_id]
            base = i_idx * k
            for row_idx in range(n_rows):
                trt_plus = block.trt_plus[row_idx]
                trt_minus = block.trt_minus[row_idx]
                if trt_plus != reference_treatment:
                    x[row_idx, base + treatment_to_ix[trt_plus]] += 1.0
                if trt_minus != reference_treatment:
                    x[row_idx, base + treatment_to_ix[trt_minus]] -= 1.0
            x_parts.append(x)
            v_blocks.append(block.covariance)

        y = np.concatenate(y_parts, axis=0)
        x_mat = np.vstack(x_parts)
        v = _block_diag(v_blocks)
        return y, x_mat, v

    @staticmethod
    def _estimate_gls(
        *,
        y: np.ndarray,
        x: np.ndarray,
        v: np.ndarray,
        tau: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        m = v + (np.eye(v.shape[0], dtype=float) * (tau * tau))
        v_inv = _inverse_or_pinv(m)
        xt_v_inv = x.T @ v_inv
        info = xt_v_inv @ x
        cov = _inverse_or_pinv(info)
        beta = cov @ xt_v_inv @ y
        return beta, cov

    @staticmethod
    def _effects_by_interval(
        *,
        beta: np.ndarray,
        cov: np.ndarray,
        interval_ids: tuple[str, ...],
        parameter_treatments: tuple[str, ...],
        reference_treatment: str,
        estimable_flags: np.ndarray,
    ) -> tuple[
        dict[str, dict[str, float]],
        dict[str, dict[str, float]],
        dict[str, dict[str, bool]],
    ]:
        k = len(parameter_treatments)
        effect_table: dict[str, dict[str, float]] = {}
        se_table: dict[str, dict[str, float]] = {}
        estimable_table: dict[str, dict[str, bool]] = {}
        for i_idx, interval_id in enumerate(interval_ids):
            effects = {reference_treatment: 0.0}
            ses = {reference_treatment: 0.0}
            estimable = {reference_treatment: True}
            base = i_idx * k
            for t_idx, treatment in enumerate(parameter_treatments):
                p_idx = base + t_idx
                is_estimable = bool(estimable_flags[p_idx])
                estimable[treatment] = is_estimable
                if is_estimable:
                    effects[treatment] = float(beta[p_idx])
                    ses[treatment] = math.sqrt(max(float(cov[p_idx, p_idx]), 0.0))
                else:
                    effects[treatment] = float("nan")
                    ses[treatment] = float("nan")
            effect_table[interval_id] = effects
            se_table[interval_id] = ses
            estimable_table[interval_id] = estimable
        return effect_table, se_table, estimable_table

    @staticmethod
    def _pooled_effects(
        *,
        effect_table: dict[str, dict[str, float]],
        se_table: dict[str, dict[str, float]],
    ) -> tuple[dict[str, float], dict[str, float]]:
        pooled_effects: dict[str, float] = {}
        pooled_ses: dict[str, float] = {}
        interval_ids = tuple(effect_table.keys())
        all_treatments = tuple(effect_table[interval_ids[0]].keys())
        if not all_treatments:
            return pooled_effects, pooled_ses
        reference_treatment = all_treatments[0]
        pooled_effects[reference_treatment] = 0.0
        pooled_ses[reference_treatment] = 0.0

        for treatment in all_treatments:
            if treatment == reference_treatment:
                continue
            weights: list[float] = []
            values: list[float] = []
            for interval_id in interval_ids:
                effect = effect_table[interval_id][treatment]
                se = se_table[interval_id][treatment]
                if not np.isfinite(effect) or not np.isfinite(se) or se <= 0:
                    continue
                w = 1.0 / (se * se)
                weights.append(w)
                values.append(effect)
            if not weights:
                pooled_effects[treatment] = float("nan")
                pooled_ses[treatment] = float("nan")
                continue
            w_sum = float(sum(weights))
            pooled_effects[treatment] = float(
                sum(w * v for w, v in zip(weights, values, strict=True)) / w_sum
            )
            pooled_ses[treatment] = math.sqrt(1.0 / w_sum)
        return pooled_effects, pooled_ses

    @staticmethod
    def _estimable_parameter_flags(
        *,
        x: np.ndarray,
        v: np.ndarray,
        tau: float,
        tol: float = 1e-8,
    ) -> np.ndarray:
        m = v + (np.eye(v.shape[0], dtype=float) * (tau * tau))
        m_inv = _inverse_or_pinv(m)
        info = x.T @ m_inv @ x
        info_pinv = np.linalg.pinv(info)
        projector = info @ info_pinv
        p = info.shape[0]
        flags = np.zeros((p,), dtype=bool)
        eye = np.eye(p, dtype=float)
        for idx in range(p):
            e = eye[:, idx]
            resid = e - (projector @ e)
            flags[idx] = bool(np.linalg.norm(resid) <= tol)
        return flags

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
