"""Initial ML-NMR style AD+IPD integration for continuous outcomes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.spec import MLNMRSpec


@dataclass(frozen=True)
class MLNMRDesignData:
    y: np.ndarray
    x: np.ndarray
    v: np.ndarray
    parameter_treatments: tuple[str, ...]
    n_studies: int
    n_contrasts: int
    n_ipd_rows: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MLNMRFitResult:
    outcome_id: str
    covariate_name: str
    reference_treatment: str
    treatment_effects: dict[str, float]
    treatment_ses: dict[str, float]
    interaction_effects: dict[str, float]
    interaction_ses: dict[str, float]
    beta_main: float
    beta_main_se: float
    parameter_treatments: tuple[str, ...]
    parameter_cov: np.ndarray
    n_studies: int
    n_contrasts: int
    n_ipd_rows: int
    warnings: tuple[str, ...]

    def contrast(
        self,
        treatment_a: str,
        treatment_b: str,
        *,
        covariate_value: float = 0.0,
    ) -> tuple[float, float]:
        if treatment_a not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_a}")
        if treatment_b not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_b}")

        effect = (
            (self.treatment_effects[treatment_a] - self.treatment_effects[treatment_b])
            + covariate_value
            * (
                self.interaction_effects[treatment_a]
                - self.interaction_effects[treatment_b]
            )
        )
        variance = self._contrast_variance(
            treatment_a=treatment_a,
            treatment_b=treatment_b,
            covariate_value=covariate_value,
        )
        return effect, math.sqrt(max(variance, 0.0))

    def _contrast_variance(
        self,
        *,
        treatment_a: str,
        treatment_b: str,
        covariate_value: float,
    ) -> float:
        k = len(self.parameter_treatments)
        coeff = np.zeros((2 * k) + 1, dtype=float)
        self._fill_treatment_coeff(coeff, treatment_a, +1.0, covariate_value)
        self._fill_treatment_coeff(coeff, treatment_b, -1.0, covariate_value)
        # beta_main cancels in treatment-vs-treatment contrast at same covariate value.
        return float(coeff.T @ self.parameter_cov @ coeff)

    def _fill_treatment_coeff(
        self,
        coeff: np.ndarray,
        treatment: str,
        sign: float,
        covariate_value: float,
    ) -> None:
        if treatment == self.reference_treatment:
            return
        idx = self.parameter_treatments.index(treatment)
        k = len(self.parameter_treatments)
        coeff[idx] += sign
        coeff[k + idx] += sign * covariate_value


@dataclass(frozen=True)
class _ArmSummary:
    study_id: str
    arm_id: str
    treatment_id: str
    mean: float
    variance: float
    covariate_mean: float
    n_ipd_rows: int = 0


@dataclass(frozen=True)
class _ContrastBlock:
    study_id: str
    y: np.ndarray
    covariance: np.ndarray
    trt_plus: tuple[str, ...]
    trt_minus: tuple[str, ...]
    x_plus: tuple[float, ...]
    x_minus: tuple[float, ...]

    @property
    def n_rows(self) -> int:
        return int(self.y.shape[0])


class MLNMRPooler:
    """First-pass frequentist ML-NMR approximation using contrast GLS."""

    def prepare_design(self, dataset: EvidenceDataset, spec: MLNMRSpec) -> MLNMRDesignData:
        measure = dataset.measure_type_for_outcome(spec.outcome_id)
        if measure != "continuous" or spec.measure_type != "continuous":
            raise ValidationError("MLNMRPooler currently supports continuous outcomes only.")

        warnings: list[str] = []
        ad_blocks = self._build_ad_blocks(dataset, spec, warnings)
        ad_study_ids = {block.study_id for block in ad_blocks}
        ipd_blocks, n_ipd_rows = self._build_ipd_blocks(
            dataset=dataset,
            spec=spec,
            excluded_studies=ad_study_ids,
            warnings=warnings,
        )
        blocks = [*ad_blocks, *ipd_blocks]
        if not blocks:
            raise ValidationError(
                "No usable AD/IPD study blocks after covariate integration checks."
            )

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
            treatment
            for treatment in treatments
            if treatment != spec.reference_treatment
        )
        if not parameter_treatments:
            raise ValidationError("At least one non-reference treatment is required.")

        y, x, v = self._assemble_gls(blocks, parameter_treatments, spec.reference_treatment)
        if np.linalg.matrix_rank(x) < x.shape[1]:
            warnings.append(
                "ML-NMR design matrix is rank-deficient; estimates use pseudo-inverse and may be weakly identified."
            )
        return MLNMRDesignData(
            y=y,
            x=x,
            v=v,
            parameter_treatments=parameter_treatments,
            n_studies=len(blocks),
            n_contrasts=int(y.shape[0]),
            n_ipd_rows=n_ipd_rows,
            warnings=tuple(warnings),
        )

    def fit(self, dataset: EvidenceDataset, spec: MLNMRSpec) -> MLNMRFitResult:
        design = self.prepare_design(dataset=dataset, spec=spec)
        beta, cov = self._estimate_gls(y=design.y, x=design.x, v=design.v)
        warnings = list(design.warnings)

        k = len(design.parameter_treatments)
        treatment_effects = {spec.reference_treatment: 0.0}
        treatment_ses = {spec.reference_treatment: 0.0}
        interaction_effects = {spec.reference_treatment: 0.0}
        interaction_ses = {spec.reference_treatment: 0.0}
        for idx, treatment in enumerate(design.parameter_treatments):
            treatment_effects[treatment] = float(beta[idx])
            treatment_ses[treatment] = math.sqrt(max(float(cov[idx, idx]), 0.0))
            g_idx = k + idx
            interaction_effects[treatment] = float(beta[g_idx])
            interaction_ses[treatment] = math.sqrt(max(float(cov[g_idx, g_idx]), 0.0))

        beta_main_idx = 2 * k
        beta_main = float(beta[beta_main_idx])
        beta_main_se = math.sqrt(max(float(cov[beta_main_idx, beta_main_idx]), 0.0))

        if spec.random_effects:
            warnings.append(
                "random_effects=True requested, but initial MLNMRPooler currently fits fixed-effects GLS."
            )

        return MLNMRFitResult(
            outcome_id=spec.outcome_id,
            covariate_name=spec.covariate_name,
            reference_treatment=spec.reference_treatment,
            treatment_effects=treatment_effects,
            treatment_ses=treatment_ses,
            interaction_effects=interaction_effects,
            interaction_ses=interaction_ses,
            beta_main=beta_main,
            beta_main_se=beta_main_se,
            parameter_treatments=design.parameter_treatments,
            parameter_cov=cov,
            n_studies=design.n_studies,
            n_contrasts=design.n_contrasts,
            n_ipd_rows=design.n_ipd_rows,
            warnings=tuple(warnings),
        )

    def _build_ad_blocks(
        self,
        dataset: EvidenceDataset,
        spec: MLNMRSpec,
        warnings: list[str],
    ) -> list[_ContrastBlock]:
        arm_lookup = dataset.arm_lookup()
        study_ids = sorted(
            {
                row.study_id
                for row in dataset.outcomes_ad
                if row.outcome_id == spec.outcome_id and row.measure_type == "continuous"
            }
        )
        blocks: list[_ContrastBlock] = []
        for study_id in study_ids:
            outcomes = dataset.outcomes_by_study_outcome(study_id, spec.outcome_id)
            if len(outcomes) < 2:
                continue
            arms: list[_ArmSummary] = []
            for row in outcomes:
                if row.measure_type != "continuous":
                    continue
                if row.se is None or row.se <= 0:
                    warnings.append(
                        f"Skipping AD arm due to invalid SE: ({row.study_id}, {row.arm_id})."
                    )
                    continue
                cov_mean = dataset.arm_covariate_mean(
                    study_id=row.study_id,
                    arm_id=row.arm_id,
                    covariate_name=spec.covariate_name,
                    outcome_id=spec.outcome_id,
                    mode=spec.integration_mode,
                    mc_samples=spec.mc_samples,
                    mc_seed=spec.mc_seed,
                )
                if cov_mean is None:
                    warnings.append(
                        f"Missing covariate mean for AD arm ({row.study_id}, {row.arm_id})."
                    )
                    continue
                arm = arm_lookup[(row.study_id, row.arm_id)]
                arms.append(
                    _ArmSummary(
                        study_id=row.study_id,
                        arm_id=row.arm_id,
                        treatment_id=arm.treatment_id,
                        mean=row.value,
                        variance=row.se * row.se,
                        covariate_mean=float(cov_mean),
                    )
                )
            block = self._to_block(study_id=study_id, arms=arms)
            if block is not None:
                blocks.append(block)
        return blocks

    def _build_ipd_blocks(
        self,
        *,
        dataset: EvidenceDataset,
        spec: MLNMRSpec,
        excluded_studies: set[str],
        warnings: list[str],
    ) -> tuple[list[_ContrastBlock], int]:
        grouped: dict[tuple[str, str], list] = defaultdict(list)
        for row in dataset.ipd:
            if row.outcome_id != spec.outcome_id or row.measure_type != "continuous":
                continue
            if row.study_id in excluded_studies:
                continue
            grouped[(row.study_id, row.outcome_id)].append(row)

        blocks: list[_ContrastBlock] = []
        total_rows = 0
        for (study_id, _outcome_id), rows in sorted(grouped.items()):
            by_arm: dict[str, list] = defaultdict(list)
            for row in rows:
                by_arm[row.arm_id].append(row)

            arms: list[_ArmSummary] = []
            for arm_id, arm_rows in by_arm.items():
                treatment_ids = {row.treatment_id for row in arm_rows}
                if len(treatment_ids) != 1:
                    warnings.append(
                        f"Skipping IPD arm with inconsistent treatments: ({study_id}, {arm_id})."
                    )
                    continue
                y_vals = [float(row.outcome_value) for row in arm_rows]
                if not y_vals:
                    continue
                mean = float(np.mean(y_vals))
                if len(y_vals) > 1:
                    se = float(np.std(y_vals, ddof=1) / math.sqrt(len(y_vals)))
                else:
                    se = 1e3

                x_vals = [
                    row.covariates[spec.covariate_name]
                    for row in arm_rows
                    if spec.covariate_name in row.covariates
                ]
                if x_vals:
                    cov_mean = float(np.mean(x_vals))
                else:
                    cov_guess = dataset.arm_covariate_mean(
                        study_id=study_id,
                        arm_id=arm_id,
                        covariate_name=spec.covariate_name,
                        outcome_id=spec.outcome_id,
                        mode=spec.integration_mode,
                        mc_samples=spec.mc_samples,
                        mc_seed=spec.mc_seed,
                    )
                    if cov_guess is None:
                        warnings.append(
                            f"Missing covariate mean for IPD arm ({study_id}, {arm_id})."
                        )
                        continue
                    cov_mean = float(cov_guess)

                arms.append(
                    _ArmSummary(
                        study_id=study_id,
                        arm_id=arm_id,
                        treatment_id=next(iter(treatment_ids)),
                        mean=mean,
                        variance=se * se,
                        covariate_mean=cov_mean,
                        n_ipd_rows=len(arm_rows),
                    )
                )
            block = self._to_block(study_id=study_id, arms=arms)
            if block is not None:
                blocks.append(block)
                total_rows += sum(arm.n_ipd_rows for arm in arms)
        return blocks, total_rows

    @staticmethod
    def _to_block(study_id: str, arms: list[_ArmSummary]) -> _ContrastBlock | None:
        if len(arms) < 2:
            return None
        arms.sort(key=lambda row: row.arm_id)
        baseline = arms[0]
        nonbaseline = arms[1:]
        y = np.array([row.mean - baseline.mean for row in nonbaseline], dtype=float)
        v = np.full((len(nonbaseline), len(nonbaseline)), baseline.variance, dtype=float)
        for idx, row in enumerate(nonbaseline):
            v[idx, idx] = baseline.variance + row.variance
        return _ContrastBlock(
            study_id=study_id,
            y=y,
            covariance=v,
            trt_plus=tuple(row.treatment_id for row in nonbaseline),
            trt_minus=tuple(baseline.treatment_id for _ in nonbaseline),
            x_plus=tuple(row.covariate_mean for row in nonbaseline),
            x_minus=tuple(baseline.covariate_mean for _ in nonbaseline),
        )

    @staticmethod
    def _assemble_gls(
        blocks: list[_ContrastBlock],
        parameter_treatments: tuple[str, ...],
        reference_treatment: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        k = len(parameter_treatments)
        treatment_to_ix = {treatment: idx for idx, treatment in enumerate(parameter_treatments)}
        y_parts: list[np.ndarray] = []
        x_parts: list[np.ndarray] = []
        v_blocks: list[np.ndarray] = []
        for block in blocks:
            y_parts.append(block.y)
            n_rows = block.n_rows
            x = np.zeros((n_rows, (2 * k) + 1), dtype=float)
            for r in range(n_rows):
                trt_plus = block.trt_plus[r]
                trt_minus = block.trt_minus[r]
                x_plus = block.x_plus[r]
                x_minus = block.x_minus[r]
                if trt_plus != reference_treatment:
                    idx = treatment_to_ix[trt_plus]
                    x[r, idx] += 1.0
                    x[r, k + idx] += x_plus
                if trt_minus != reference_treatment:
                    idx = treatment_to_ix[trt_minus]
                    x[r, idx] -= 1.0
                    x[r, k + idx] -= x_minus
                x[r, 2 * k] = x_plus - x_minus
            x_parts.append(x)
            v_blocks.append(block.covariance)
        y = np.concatenate(y_parts, axis=0)
        x = np.vstack(x_parts)
        v = _block_diag(v_blocks)
        return y, x, v

    @staticmethod
    def _estimate_gls(
        *,
        y: np.ndarray,
        x: np.ndarray,
        v: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        v_inv = _inverse_or_pinv(v)
        xt_v_inv = x.T @ v_inv
        info = xt_v_inv @ x
        cov = _inverse_or_pinv(info)
        beta = cov @ xt_v_inv @ y
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
