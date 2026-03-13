"""Design-stratified bias-adjusted NMA for mixed RCT/NRS evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import BiasAdjustedSpec


@dataclass(frozen=True)
class BiasAdjustedNMAFitResult:
    outcome_id: str
    measure_type: str
    reference_treatment: str
    reference_design: str
    treatment_effects: dict[str, float]
    treatment_ses: dict[str, float]
    design_bias_effects: dict[str, float]
    design_bias_ses: dict[str, float]
    parameter_treatments: tuple[str, ...]
    parameter_designs: tuple[str, ...]
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
        design: str | None = None,
    ) -> tuple[float, float]:
        design_name = design or self.reference_design
        if treatment_a not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_a}")
        if treatment_b not in self.treatment_effects:
            raise KeyError(f"Unknown treatment: {treatment_b}")
        if design_name != self.reference_design and design_name not in self.design_bias_effects:
            raise KeyError(f"Unknown design stratum: {design_name}")

        effect = self.treatment_effects[treatment_a] - self.treatment_effects[treatment_b]
        if design_name != self.reference_design:
            effect += self.design_bias_effects[design_name]

        coeff = self._contrast_coeff(
            treatment_a=treatment_a,
            treatment_b=treatment_b,
            design=design_name,
        )
        variance = float(coeff.T @ self.parameter_cov @ coeff)
        return effect, math.sqrt(max(variance, 0.0))

    def _contrast_coeff(
        self,
        *,
        treatment_a: str,
        treatment_b: str,
        design: str,
    ) -> np.ndarray:
        k = len(self.parameter_treatments)
        q = len(self.parameter_designs)
        coeff = np.zeros((k + q,), dtype=float)
        self._fill_treatment_coeff(coeff, treatment=treatment_a, sign=+1.0)
        self._fill_treatment_coeff(coeff, treatment=treatment_b, sign=-1.0)
        if design != self.reference_design:
            d_idx = self.parameter_designs.index(design)
            coeff[k + d_idx] = 1.0
        return coeff

    def _fill_treatment_coeff(
        self,
        coeff: np.ndarray,
        *,
        treatment: str,
        sign: float,
    ) -> None:
        if treatment == self.reference_treatment:
            return
        t_idx = self.parameter_treatments.index(treatment)
        coeff[t_idx] += sign


@dataclass(frozen=True)
class BiasAdjustedDesignData:
    y: np.ndarray
    x: np.ndarray
    v: np.ndarray
    parameter_treatments: tuple[str, ...]
    parameter_designs: tuple[str, ...]
    n_studies: int
    n_contrasts: int
    warnings: tuple[str, ...]


class BiasAdjustedNMAPooler:
    """Frequentist bias-adjusted NMA with design-stratum shrinkage."""

    def prepare_design(self, dataset: EvidenceDataset, spec: BiasAdjustedSpec) -> BiasAdjustedDesignData:
        self._validate_spec(dataset=dataset, spec=spec)
        core = ADNMAPooler()
        blocks = core._build_study_blocks(dataset, spec.outcome_id, spec.measure_type)  # noqa: SLF001
        if not blocks:
            raise ValidationError(f"No studies available for outcome_id '{spec.outcome_id}'.")

        treatments = core._all_treatments(blocks)  # noqa: SLF001
        if spec.reference_treatment not in treatments:
            raise ValidationError(
                f"reference_treatment '{spec.reference_treatment}' not present in outcome network."
            )
        parameter_treatments = tuple(
            treatment
            for treatment in sorted(treatments)
            if treatment != spec.reference_treatment
        )
        if not parameter_treatments:
            raise ValidationError("At least one non-reference treatment is required.")

        y, x_trt, v = core._assemble_design(blocks, parameter_treatments, spec.reference_treatment)  # noqa: SLF001
        row_designs = self._row_designs(blocks=blocks, dataset=dataset)
        parameter_designs = tuple(
            design
            for design in sorted(set(row_designs))
            if design != spec.reference_design
        )
        z = self._build_design_matrix(row_designs=row_designs, parameter_designs=parameter_designs)
        x = np.hstack([x_trt, z]) if z.shape[1] > 0 else x_trt

        warnings: list[str] = []
        if spec.reference_design not in set(row_designs):
            warnings.append(
                f"No studies observed in reference_design '{spec.reference_design}'. "
                "Design bias terms may be weakly identified."
            )
        if not parameter_designs:
            warnings.append("No non-reference designs present; bias terms are omitted.")
        if np.linalg.matrix_rank(x) < x.shape[1]:
            warnings.append(
                "Bias-adjusted design matrix is rank-deficient; estimates use pseudo-inverse."
            )

        return BiasAdjustedDesignData(
            y=y,
            x=x,
            v=v,
            parameter_treatments=parameter_treatments,
            parameter_designs=parameter_designs,
            n_studies=len(blocks),
            n_contrasts=int(y.shape[0]),
            warnings=tuple(warnings),
        )

    def fit(self, dataset: EvidenceDataset, spec: BiasAdjustedSpec) -> BiasAdjustedNMAFitResult:
        design = self.prepare_design(dataset=dataset, spec=spec)
        if spec.bias_prior_sd <= 0:
            raise ValidationError("bias_prior_sd must be > 0.")
        core = ADNMAPooler()
        warnings = list(design.warnings)

        tau = 0.0
        if spec.random_effects and design.y.shape[0] > design.x.shape[1]:
            tau = core._optimize_tau_reml(y=design.y, x=design.x, v=design.v)  # noqa: SLF001
        elif spec.random_effects:
            warnings.append(
                "random_effects=True requested but insufficient degrees of freedom; tau fixed at 0."
            )

        k = len(design.parameter_treatments)
        beta, cov = self._estimate_gls_with_shrinkage(
            y=design.y,
            x=design.x,
            v=design.v,
            tau=tau,
            treatment_param_count=k,
            design_param_count=len(design.parameter_designs),
            bias_prior_sd=spec.bias_prior_sd,
        )
        treatment_effects = {spec.reference_treatment: 0.0}
        treatment_ses = {spec.reference_treatment: 0.0}
        for idx, treatment in enumerate(design.parameter_treatments):
            treatment_effects[treatment] = float(beta[idx])
            treatment_ses[treatment] = math.sqrt(max(float(cov[idx, idx]), 0.0))

        design_bias_effects = {spec.reference_design: 0.0}
        design_bias_ses = {spec.reference_design: 0.0}
        for jdx, design_name in enumerate(design.parameter_designs):
            p_idx = k + jdx
            design_bias_effects[design_name] = float(beta[p_idx])
            design_bias_ses[design_name] = math.sqrt(max(float(cov[p_idx, p_idx]), 0.0))

        return BiasAdjustedNMAFitResult(
            outcome_id=spec.outcome_id,
            measure_type=spec.measure_type,
            reference_treatment=spec.reference_treatment,
            reference_design=spec.reference_design,
            treatment_effects=treatment_effects,
            treatment_ses=treatment_ses,
            design_bias_effects=design_bias_effects,
            design_bias_ses=design_bias_ses,
            parameter_treatments=design.parameter_treatments,
            parameter_designs=design.parameter_designs,
            parameter_cov=np.asarray(cov, dtype=float),
            tau=float(tau),
            n_studies=design.n_studies,
            n_contrasts=design.n_contrasts,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_spec(*, dataset: EvidenceDataset, spec: BiasAdjustedSpec) -> None:
        measure = dataset.measure_type_for_outcome(spec.outcome_id)
        if measure != spec.measure_type:
            raise ValidationError(
                "BiasAdjustedSpec measure_type does not match dataset outcome measure type: "
                f"{spec.measure_type} vs {measure}."
            )
        if spec.reference_design not in {"rct", "nrs", "other"}:
            raise ValidationError("reference_design must be one of: rct, nrs, other.")

    @staticmethod
    def _row_designs(*, blocks: list[object], dataset: EvidenceDataset) -> tuple[str, ...]:
        design_by_study = {row.study_id: row.design for row in dataset.studies}
        out: list[str] = []
        for block in blocks:
            study_id = str(getattr(block, "study_id"))
            n_rows = int(getattr(block, "y").shape[0])
            design = design_by_study.get(study_id, "other")
            out.extend([design] * n_rows)
        return tuple(out)

    @staticmethod
    def _build_design_matrix(
        *,
        row_designs: tuple[str, ...],
        parameter_designs: tuple[str, ...],
    ) -> np.ndarray:
        n = len(row_designs)
        q = len(parameter_designs)
        if q == 0:
            return np.zeros((n, 0), dtype=float)
        design_to_ix = {design: idx for idx, design in enumerate(parameter_designs)}
        z = np.zeros((n, q), dtype=float)
        for i, design in enumerate(row_designs):
            idx = design_to_ix.get(design)
            if idx is not None:
                z[i, idx] = 1.0
        return z

    @staticmethod
    def _estimate_gls_with_shrinkage(
        *,
        y: np.ndarray,
        x: np.ndarray,
        v: np.ndarray,
        tau: float,
        treatment_param_count: int,
        design_param_count: int,
        bias_prior_sd: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        m = v + np.eye(v.shape[0], dtype=float) * (tau * tau)
        m_inv = _inverse_or_pinv(m)
        xt_m_inv = x.T @ m_inv
        info = xt_m_inv @ x

        p = treatment_param_count + design_param_count
        prior_precision = np.zeros((p, p), dtype=float)
        if design_param_count > 0:
            lam = 1.0 / (bias_prior_sd * bias_prior_sd)
            prior_precision[
                treatment_param_count:p,
                treatment_param_count:p,
            ] = np.eye(design_param_count, dtype=float) * lam

        post_info = info + prior_precision
        cov = _inverse_or_pinv(post_info)
        beta = cov @ xt_m_inv @ y
        return beta, cov


def _inverse_or_pinv(matrix: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(matrix)
