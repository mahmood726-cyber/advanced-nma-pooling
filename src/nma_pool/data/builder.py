"""Dataset builders and integrity validators."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Sequence

import numpy as np

from .schemas import (
    ADCovariateSummaryRecord,
    ArmRecord,
    IPDRecord,
    OutcomeADRecord,
    ProvenanceRecord,
    SurvivalIntervalADRecord,
    StudyRecord,
    ValidationError,
)


IntegrationMode = Literal["empirical", "normal_mc"]


@dataclass(frozen=True)
class EvidenceDataset:
    """Validated evidence dataset for AD and optional IPD workflows."""

    studies: tuple[StudyRecord, ...]
    arms: tuple[ArmRecord, ...]
    outcomes_ad: tuple[OutcomeADRecord, ...]
    ipd: tuple[IPDRecord, ...] = ()
    ad_covariates: tuple[ADCovariateSummaryRecord, ...] = ()
    survival_ad: tuple[SurvivalIntervalADRecord, ...] = ()
    provenance: tuple[ProvenanceRecord, ...] = ()

    @property
    def study_ids(self) -> tuple[str, ...]:
        return tuple(study.study_id for study in self.studies)

    def arms_by_study(self, study_id: str) -> tuple[ArmRecord, ...]:
        return tuple(arm for arm in self.arms if arm.study_id == study_id)

    def outcomes_by_study_outcome(
        self,
        study_id: str,
        outcome_id: str,
    ) -> tuple[OutcomeADRecord, ...]:
        return tuple(
            outcome
            for outcome in self.outcomes_ad
            if outcome.study_id == study_id and outcome.outcome_id == outcome_id
        )

    def ipd_by_study_outcome(
        self,
        study_id: str,
        outcome_id: str,
    ) -> tuple[IPDRecord, ...]:
        return tuple(
            row
            for row in self.ipd
            if row.study_id == study_id and row.outcome_id == outcome_id
        )

    def ipd_by_arm_outcome(
        self,
        study_id: str,
        arm_id: str,
        outcome_id: str | None = None,
    ) -> tuple[IPDRecord, ...]:
        return tuple(
            row
            for row in self.ipd
            if row.study_id == study_id
            and row.arm_id == arm_id
            and (outcome_id is None or row.outcome_id == outcome_id)
        )

    def arm_lookup(self) -> dict[tuple[str, str], ArmRecord]:
        return {(arm.study_id, arm.arm_id): arm for arm in self.arms}

    def survival_intervals_by_study_outcome(
        self,
        study_id: str,
        outcome_id: str,
    ) -> tuple[SurvivalIntervalADRecord, ...]:
        return tuple(
            row
            for row in self.survival_ad
            if row.study_id == study_id and row.outcome_id == outcome_id
        )

    def treatments_for_outcome(self, outcome_id: str) -> tuple[str, ...]:
        arms_by_key = self.arm_lookup()
        treatments: set[str] = set()
        for outcome in self.outcomes_ad:
            if outcome.outcome_id != outcome_id:
                continue
            arm = arms_by_key[(outcome.study_id, outcome.arm_id)]
            treatments.add(arm.treatment_id)
        for row in self.ipd:
            if row.outcome_id != outcome_id:
                continue
            treatments.add(row.treatment_id)
        for row in self.survival_ad:
            if row.outcome_id != outcome_id:
                continue
            arm = arms_by_key[(row.study_id, row.arm_id)]
            treatments.add(arm.treatment_id)
        return tuple(sorted(treatments))

    def measure_type_for_outcome(self, outcome_id: str) -> str:
        if any(row.outcome_id == outcome_id for row in self.survival_ad):
            return "survival"
        measures = {
            outcome.measure_type
            for outcome in self.outcomes_ad
            if outcome.outcome_id == outcome_id
        }
        measures.update(
            row.measure_type for row in self.ipd if row.outcome_id == outcome_id
        )
        if not measures:
            raise ValidationError(f"No outcomes found for outcome_id '{outcome_id}'.")
        if len(measures) > 1:
            raise ValidationError(
                f"Outcome '{outcome_id}' mixes measure types: {sorted(measures)}."
            )
        return next(iter(measures))

    def arm_covariate_mean(
        self,
        *,
        study_id: str,
        arm_id: str,
        covariate_name: str,
        outcome_id: str | None = None,
        mode: IntegrationMode = "empirical",
        mc_samples: int = 2000,
        mc_seed: int = 123,
    ) -> float | None:
        ipd_rows = self.ipd_by_arm_outcome(study_id=study_id, arm_id=arm_id, outcome_id=outcome_id)
        ipd_values = [
            row.covariates[covariate_name]
            for row in ipd_rows
            if covariate_name in row.covariates
        ]
        if ipd_values:
            return float(sum(ipd_values) / len(ipd_values))

        summary = next(
            (
                row
                for row in self.ad_covariates
                if row.study_id == study_id
                and row.arm_id == arm_id
                and row.covariate_name == covariate_name
            ),
            None,
        )
        if summary is None:
            return None
        if mode == "empirical":
            return summary.mean
        if mode != "normal_mc":
            raise ValidationError(f"Unsupported integration mode: {mode}")
        if summary.sd is None or summary.sd == 0 or mc_samples <= 1:
            return summary.mean
        rng = np.random.default_rng(mc_seed)
        samples = rng.normal(loc=summary.mean, scale=summary.sd, size=mc_samples)
        return float(np.mean(samples))


class DatasetBuilder:
    """Builds and validates `EvidenceDataset` from raw records."""

    def from_payload(self, payload: Mapping[str, Any]) -> EvidenceDataset:
        studies = payload.get("studies", [])
        arms = payload.get("arms", [])
        outcomes_ad = payload.get("outcomes_ad", [])
        ipd = payload.get("ipd", [])
        ad_covariates = payload.get("ad_covariates", [])
        survival_ad = payload.get("survival_ad", [])
        provenance = payload.get("provenance", [])
        return self.from_records(
            studies=studies,
            arms=arms,
            outcomes_ad=outcomes_ad,
            ipd=ipd,
            ad_covariates=ad_covariates,
            survival_ad=survival_ad,
            provenance=provenance,
        )

    def from_records(
        self,
        studies: Iterable[StudyRecord | Mapping[str, Any]],
        arms: Iterable[ArmRecord | Mapping[str, Any]],
        outcomes_ad: Iterable[OutcomeADRecord | Mapping[str, Any]] | None = None,
        ipd: Iterable[IPDRecord | Mapping[str, Any]] | None = None,
        ad_covariates: Iterable[ADCovariateSummaryRecord | Mapping[str, Any]] | None = None,
        survival_ad: Iterable[SurvivalIntervalADRecord | Mapping[str, Any]] | None = None,
        provenance: Iterable[ProvenanceRecord | Mapping[str, Any]] | None = None,
    ) -> EvidenceDataset:
        study_rows = tuple(self._coerce_study(row) for row in studies)
        arm_rows = tuple(self._coerce_arm(row) for row in arms)
        outcome_rows = tuple(self._coerce_outcome(row) for row in (outcomes_ad or ()))
        ipd_rows = tuple(self._coerce_ipd(row) for row in (ipd or ()))
        ad_cov_rows = tuple(
            self._coerce_ad_covariate(row) for row in (ad_covariates or ())
        )
        survival_rows = tuple(
            self._coerce_survival_ad(row) for row in (survival_ad or ())
        )
        provenance_rows = tuple(
            self._coerce_provenance(row) for row in (provenance or ())
        )

        self._validate_uniques(
            study_rows, arm_rows, outcome_rows, ipd_rows, ad_cov_rows, survival_rows
        )
        self._validate_links(
            study_rows, arm_rows, outcome_rows, ipd_rows, ad_cov_rows, survival_rows
        )
        self._validate_binary_ranges(arm_rows, outcome_rows, ipd_rows)
        self._validate_study_outcome_completeness(outcome_rows, ipd_rows, survival_rows)
        self._validate_survival_interval_topology(survival_rows)
        self._validate_measure_type_consistency(outcome_rows, ipd_rows, survival_rows)

        return EvidenceDataset(
            studies=study_rows,
            arms=arm_rows,
            outcomes_ad=outcome_rows,
            ipd=ipd_rows,
            ad_covariates=ad_cov_rows,
            survival_ad=survival_rows,
            provenance=provenance_rows,
        )

    @staticmethod
    def _coerce_study(row: StudyRecord | Mapping[str, Any]) -> StudyRecord:
        return row if isinstance(row, StudyRecord) else StudyRecord.from_mapping(row)

    @staticmethod
    def _coerce_arm(row: ArmRecord | Mapping[str, Any]) -> ArmRecord:
        return row if isinstance(row, ArmRecord) else ArmRecord.from_mapping(row)

    @staticmethod
    def _coerce_outcome(
        row: OutcomeADRecord | Mapping[str, Any]
    ) -> OutcomeADRecord:
        return row if isinstance(row, OutcomeADRecord) else OutcomeADRecord.from_mapping(
            row
        )

    @staticmethod
    def _coerce_ipd(row: IPDRecord | Mapping[str, Any]) -> IPDRecord:
        return row if isinstance(row, IPDRecord) else IPDRecord.from_mapping(row)

    @staticmethod
    def _coerce_ad_covariate(
        row: ADCovariateSummaryRecord | Mapping[str, Any]
    ) -> ADCovariateSummaryRecord:
        return (
            row
            if isinstance(row, ADCovariateSummaryRecord)
            else ADCovariateSummaryRecord.from_mapping(row)
        )

    @staticmethod
    def _coerce_survival_ad(
        row: SurvivalIntervalADRecord | Mapping[str, Any]
    ) -> SurvivalIntervalADRecord:
        return (
            row
            if isinstance(row, SurvivalIntervalADRecord)
            else SurvivalIntervalADRecord.from_mapping(row)
        )

    @staticmethod
    def _coerce_provenance(
        row: ProvenanceRecord | Mapping[str, Any]
    ) -> ProvenanceRecord:
        return (
            row
            if isinstance(row, ProvenanceRecord)
            else ProvenanceRecord.from_mapping(row)
        )

    @staticmethod
    def _validate_uniques(
        studies: Sequence[StudyRecord],
        arms: Sequence[ArmRecord],
        outcomes: Sequence[OutcomeADRecord],
        ipd: Sequence[IPDRecord],
        ad_covariates: Sequence[ADCovariateSummaryRecord],
        survival_ad: Sequence[SurvivalIntervalADRecord],
    ) -> None:
        if not studies:
            raise ValidationError("At least one study record is required.")
        if not arms:
            raise ValidationError("At least one arm record is required.")
        if not outcomes and not ipd and not survival_ad:
            raise ValidationError(
                "At least one outcome record is required in outcomes_ad, ipd, or survival_ad."
            )

        study_ids = [row.study_id for row in studies]
        if len(set(study_ids)) != len(study_ids):
            raise ValidationError("Duplicate study_id values found.")

        arm_keys = [(row.study_id, row.arm_id) for row in arms]
        if len(set(arm_keys)) != len(arm_keys):
            raise ValidationError("Duplicate (study_id, arm_id) arm keys found.")

        outcome_keys = [
            (row.study_id, row.arm_id, row.outcome_id) for row in outcomes
        ]
        if len(set(outcome_keys)) != len(outcome_keys):
            raise ValidationError(
                "Duplicate (study_id, arm_id, outcome_id) outcome_ad keys found."
            )

        ipd_keys = [
            (row.study_id, row.patient_id, row.outcome_id) for row in ipd
        ]
        if len(set(ipd_keys)) != len(ipd_keys):
            raise ValidationError(
                "Duplicate (study_id, patient_id, outcome_id) IPD keys found."
            )

        cov_keys = [
            (row.study_id, row.arm_id, row.covariate_name) for row in ad_covariates
        ]
        if len(set(cov_keys)) != len(cov_keys):
            raise ValidationError(
                "Duplicate (study_id, arm_id, covariate_name) ad_covariates keys found."
            )

        survival_keys = [
            (row.study_id, row.arm_id, row.outcome_id, row.interval_id)
            for row in survival_ad
        ]
        if len(set(survival_keys)) != len(survival_keys):
            raise ValidationError(
                "Duplicate (study_id, arm_id, outcome_id, interval_id) survival_ad keys found."
            )

    @staticmethod
    def _validate_links(
        studies: Sequence[StudyRecord],
        arms: Sequence[ArmRecord],
        outcomes: Sequence[OutcomeADRecord],
        ipd: Sequence[IPDRecord],
        ad_covariates: Sequence[ADCovariateSummaryRecord],
        survival_ad: Sequence[SurvivalIntervalADRecord],
    ) -> None:
        study_ids = {row.study_id for row in studies}
        for arm in arms:
            if arm.study_id not in study_ids:
                raise ValidationError(
                    f"Arm ({arm.study_id}, {arm.arm_id}) references unknown study_id."
                )

        arm_map = {(row.study_id, row.arm_id): row for row in arms}
        for outcome in outcomes:
            if (outcome.study_id, outcome.arm_id) not in arm_map:
                raise ValidationError(
                    "Outcome record references unknown arm: "
                    f"({outcome.study_id}, {outcome.arm_id})."
                )

        for row in ipd:
            arm = arm_map.get((row.study_id, row.arm_id))
            if arm is None:
                raise ValidationError(
                    "IPD record references unknown arm: "
                    f"({row.study_id}, {row.arm_id})."
                )
            if arm.treatment_id != row.treatment_id:
                raise ValidationError(
                    "IPD record treatment_id does not match arm treatment_id for "
                    f"({row.study_id}, {row.arm_id}, {row.patient_id})."
                )

        for row in ad_covariates:
            if (row.study_id, row.arm_id) not in arm_map:
                raise ValidationError(
                    "ad_covariates record references unknown arm: "
                    f"({row.study_id}, {row.arm_id})."
                )

        for row in survival_ad:
            if (row.study_id, row.arm_id) not in arm_map:
                raise ValidationError(
                    "survival_ad record references unknown arm: "
                    f"({row.study_id}, {row.arm_id})."
                )

    @staticmethod
    def _validate_binary_ranges(
        arms: Sequence[ArmRecord],
        outcomes: Sequence[OutcomeADRecord],
        ipd: Sequence[IPDRecord],
    ) -> None:
        arm_map = {(arm.study_id, arm.arm_id): arm for arm in arms}
        for outcome in outcomes:
            if outcome.measure_type != "binary":
                continue
            arm = arm_map[(outcome.study_id, outcome.arm_id)]
            if outcome.value > arm.n:
                raise ValidationError(
                    "Binary outcome value cannot exceed arm n for "
                    f"({outcome.study_id}, {outcome.arm_id}, {outcome.outcome_id})."
                )
        for row in ipd:
            if row.measure_type != "binary":
                continue
            if row.outcome_value not in {0.0, 1.0}:
                raise ValidationError(
                    "Binary IPD outcomes must be 0 or 1 for "
                    f"({row.study_id}, {row.patient_id}, {row.outcome_id})."
                )

    @staticmethod
    def _validate_study_outcome_completeness(
        outcomes: Sequence[OutcomeADRecord],
        ipd: Sequence[IPDRecord],
        survival_ad: Sequence[SurvivalIntervalADRecord],
    ) -> None:
        ad_grouped: dict[tuple[str, str], list[OutcomeADRecord]] = defaultdict(list)
        for row in outcomes:
            ad_grouped[(row.study_id, row.outcome_id)].append(row)
        for key, rows in ad_grouped.items():
            if len(rows) < 2:
                raise ValidationError(
                    f"Study/outcome {key} must include at least 2 AD arms."
                )
            measure_types = {row.measure_type for row in rows}
            if len(measure_types) > 1:
                raise ValidationError(
                    f"Study/outcome {key} mixes AD measure types: {sorted(measure_types)}."
                )

        ipd_grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
        ipd_measure: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in ipd:
            key = (row.study_id, row.outcome_id)
            ipd_grouped[key].add(row.arm_id)
            ipd_measure[key].add(row.measure_type)
        for key, arms in ipd_grouped.items():
            if len(arms) < 2 and key not in ad_grouped:
                raise ValidationError(
                    f"Study/outcome {key} must include at least 2 IPD arms when AD is absent."
                )
            if len(ipd_measure[key]) > 1:
                raise ValidationError(
                    f"Study/outcome {key} mixes IPD measure types: {sorted(ipd_measure[key])}."
                )

        surv_grouped: dict[tuple[str, str, str], set[str]] = defaultdict(set)
        for row in survival_ad:
            key = (row.study_id, row.outcome_id, row.interval_id)
            surv_grouped[key].add(row.arm_id)
        for key, arms in surv_grouped.items():
            if len(arms) < 2:
                raise ValidationError(
                    f"Study/outcome/interval {key} must include at least 2 survival arms."
                )

    @staticmethod
    def _validate_measure_type_consistency(
        outcomes: Sequence[OutcomeADRecord],
        ipd: Sequence[IPDRecord],
        survival_ad: Sequence[SurvivalIntervalADRecord],
    ) -> None:
        by_outcome: dict[str, set[str]] = defaultdict(set)
        for row in outcomes:
            by_outcome[row.outcome_id].add(row.measure_type)
        for row in ipd:
            by_outcome[row.outcome_id].add(row.measure_type)
        for row in survival_ad:
            by_outcome[row.outcome_id].add("survival")
        inconsistent = {
            outcome_id: sorted(measures)
            for outcome_id, measures in by_outcome.items()
            if len(measures) > 1
        }
        if inconsistent:
            keys = ", ".join(f"{k}={v}" for k, v in sorted(inconsistent.items()))
            raise ValidationError(f"Mixed measure types across AD/IPD outcomes: {keys}.")

    @staticmethod
    def _validate_survival_interval_topology(
        survival_ad: Sequence[SurvivalIntervalADRecord],
    ) -> None:
        if not survival_ad:
            return

        eps = 1e-12
        by_study_outcome_arm: dict[tuple[str, str, str], list[SurvivalIntervalADRecord]] = defaultdict(list)
        by_study_outcome: dict[tuple[str, str], dict[str, list[SurvivalIntervalADRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )
        global_bounds: dict[tuple[str, str], tuple[float, float]] = {}

        for row in survival_ad:
            by_study_outcome_arm[(row.study_id, row.outcome_id, row.arm_id)].append(row)
            by_study_outcome[(row.study_id, row.outcome_id)][row.arm_id].append(row)
            key = (row.outcome_id, row.interval_id)
            bounds = (row.t_start, row.t_end)
            seen = global_bounds.get(key)
            if seen is None:
                global_bounds[key] = bounds
            elif seen != bounds:
                raise ValidationError(
                    "Survival interval_id bounds are inconsistent across studies for "
                    f"({row.outcome_id}, {row.interval_id}): {seen} vs {bounds}."
                )

        for key, rows in by_study_outcome_arm.items():
            ordered = sorted(rows, key=lambda r: (r.t_start, r.t_end, r.interval_id))
            prev_end: float | None = None
            for row in ordered:
                if prev_end is not None and row.t_start < (prev_end - eps):
                    raise ValidationError(
                        f"Overlapping survival intervals for {key}: "
                        f"start={row.t_start} < previous_end={prev_end}."
                    )
                prev_end = row.t_end

        for key, arm_rows in by_study_outcome.items():
            arm_ids = sorted(arm_rows.keys())
            if len(arm_ids) < 2:
                continue
            first_arm = arm_ids[0]
            expected_ids = {row.interval_id for row in arm_rows[first_arm]}
            expected_bounds = {
                row.interval_id: (row.t_start, row.t_end)
                for row in arm_rows[first_arm]
            }
            for arm_id in arm_ids[1:]:
                observed_ids = {row.interval_id for row in arm_rows[arm_id]}
                if observed_ids != expected_ids:
                    raise ValidationError(
                        f"Survival interval grids differ across arms in study/outcome {key}: "
                        f"{first_arm}={sorted(expected_ids)} vs {arm_id}={sorted(observed_ids)}."
                    )
                for row in arm_rows[arm_id]:
                    bounds = (row.t_start, row.t_end)
                    if expected_bounds[row.interval_id] != bounds:
                        raise ValidationError(
                            f"Survival interval bounds mismatch across arms in study/outcome {key} "
                            f"for interval_id '{row.interval_id}': "
                            f"{expected_bounds[row.interval_id]} vs {bounds}."
                        )
