"""Typed schema records for NMA evidence ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import numbers
import re
from typing import Any, Literal, Mapping


MeasureType = Literal["binary", "continuous"]
DesignType = Literal["rct", "nrs", "other"]


class ValidationError(ValueError):
    """Raised when schema validation fails."""


_INTEGER_TEXT = re.compile(r"[+-]?\d+")


def _require_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Field '{key}' must be a non-empty string.")
    return value.strip()


def _optional_str(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"Field '{key}' must be a string when provided.")
    text = value.strip()
    return text or None


def _optional_float(data: Mapping[str, Any], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Field '{key}' must be numeric when provided.") from exc


def _require_float(data: Mapping[str, Any], key: str) -> float:
    value = data.get(key)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Field '{key}' must be numeric.") from exc


def _require_int(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool):
        raise ValidationError(f"Field '{key}' must be an integer.")
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        numeric = float(value)
        if math.isfinite(numeric) and numeric.is_integer():
            return int(numeric)
        raise ValidationError(f"Field '{key}' must be an integer.")
    if isinstance(value, str):
        text = value.strip()
        if _INTEGER_TEXT.fullmatch(text):
            return int(text)
    raise ValidationError(f"Field '{key}' must be an integer.")


def _parse_components(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        if not raw.strip():
            return ()
        items = [part.strip() for part in raw.split(",")]
        if any(not item for item in items):
            raise ValidationError("components must not include empty values.")
        return tuple(items)
    if isinstance(raw, list):
        if any(not isinstance(item, str) or not item.strip() for item in raw):
            raise ValidationError("components list must contain non-empty strings.")
        return tuple(item.strip() for item in raw)
    raise ValidationError("components must be a comma-separated string or list[str].")


def _parse_numeric_mapping(raw: Any, field_name: str) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValidationError(f"Field '{field_name}' must be a mapping/object.")
    out: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(f"Field '{field_name}' keys must be non-empty strings.")
        try:
            out[key.strip()] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Field '{field_name}' values must be numeric."
            ) from exc
    return out


@dataclass(frozen=True)
class StudyRecord:
    study_id: str
    design: DesignType
    year: int
    source_id: str
    rob_domain_summary: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "StudyRecord":
        study_id = _require_str(data, "study_id")
        design = _require_str(data, "design").lower()
        if design not in {"rct", "nrs", "other"}:
            raise ValidationError(
                "Field 'design' must be one of: rct, nrs, other."
            )
        year = _require_int(data, "year")
        if year < 1900 or year > 2200:
            raise ValidationError("Field 'year' must be between 1900 and 2200.")
        source_id = _require_str(data, "source_id")
        rob_domain_summary = _require_str(data, "rob_domain_summary")
        return cls(
            study_id=study_id,
            design=design,  # type: ignore[arg-type]
            year=year,
            source_id=source_id,
            rob_domain_summary=rob_domain_summary,
        )


@dataclass(frozen=True)
class ArmRecord:
    study_id: str
    arm_id: str
    treatment_id: str
    n: int
    dose: float | None
    components: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ArmRecord":
        study_id = _require_str(data, "study_id")
        arm_id = _require_str(data, "arm_id")
        treatment_id = _require_str(data, "treatment_id")
        n = _require_int(data, "n")
        if n <= 0:
            raise ValidationError("Field 'n' must be > 0.")
        dose = _optional_float(data, "dose")
        components = _parse_components(data.get("components"))
        return cls(
            study_id=study_id,
            arm_id=arm_id,
            treatment_id=treatment_id,
            n=n,
            dose=dose,
            components=components,
        )


@dataclass(frozen=True)
class OutcomeADRecord:
    study_id: str
    arm_id: str
    outcome_id: str
    measure_type: MeasureType
    value: float
    se: float | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "OutcomeADRecord":
        study_id = _require_str(data, "study_id")
        arm_id = _require_str(data, "arm_id")
        outcome_id = _require_str(data, "outcome_id")
        measure_type = _require_str(data, "measure_type").lower()
        if measure_type not in {"binary", "continuous"}:
            raise ValidationError(
                "Field 'measure_type' must be one of: binary, continuous."
            )
        value = _require_float(data, "value")
        se = _optional_float(data, "se")
        if measure_type == "continuous":
            if se is None or se <= 0:
                raise ValidationError(
                    "Continuous outcomes require field 'se' > 0."
                )
        else:
            if value < 0:
                raise ValidationError("Binary outcomes require value >= 0.")
            if se is not None and se <= 0:
                raise ValidationError("Field 'se' must be > 0 when provided.")
        return cls(
            study_id=study_id,
            arm_id=arm_id,
            outcome_id=outcome_id,
            measure_type=measure_type,  # type: ignore[arg-type]
            value=value,
            se=se,
        )


@dataclass(frozen=True)
class ProvenanceRecord:
    record_id: str
    source_hash: str
    transform_step: str
    timestamp: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProvenanceRecord":
        record_id = _require_str(data, "record_id")
        source_hash = _require_str(data, "source_hash")
        transform_step = _require_str(data, "transform_step")
        timestamp = _require_str(data, "timestamp")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(
                "Field 'timestamp' must be an ISO 8601 datetime string."
            ) from exc
        return cls(
            record_id=record_id,
            source_hash=source_hash,
            transform_step=transform_step,
            timestamp=timestamp,
        )


@dataclass(frozen=True)
class IPDRecord:
    study_id: str
    patient_id: str
    arm_id: str
    treatment_id: str
    outcome_id: str
    measure_type: MeasureType
    outcome_value: float
    covariates: dict[str, float]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "IPDRecord":
        study_id = _require_str(data, "study_id")
        patient_id = _require_str(data, "patient_id")
        arm_id = _require_str(data, "arm_id")
        treatment_id = _require_str(data, "treatment_id")
        outcome_id = _require_str(data, "outcome_id")
        measure_type = _require_str(data, "measure_type").lower()
        if measure_type not in {"binary", "continuous"}:
            raise ValidationError(
                "Field 'measure_type' must be one of: binary, continuous."
            )
        outcome_value = _require_float(data, "outcome_value")
        if measure_type == "binary" and outcome_value not in {0.0, 1.0}:
            raise ValidationError("Binary IPD outcomes must be 0 or 1.")
        covariates = _parse_numeric_mapping(data.get("covariates"), "covariates")
        return cls(
            study_id=study_id,
            patient_id=patient_id,
            arm_id=arm_id,
            treatment_id=treatment_id,
            outcome_id=outcome_id,
            measure_type=measure_type,  # type: ignore[arg-type]
            outcome_value=outcome_value,
            covariates=covariates,
        )


@dataclass(frozen=True)
class ADCovariateSummaryRecord:
    study_id: str
    arm_id: str
    covariate_name: str
    mean: float
    sd: float | None
    n: int | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ADCovariateSummaryRecord":
        study_id = _require_str(data, "study_id")
        arm_id = _require_str(data, "arm_id")
        covariate_name = _require_str(data, "covariate_name")
        mean = _require_float(data, "mean")
        sd = _optional_float(data, "sd")
        if sd is not None and sd < 0:
            raise ValidationError("Field 'sd' must be >= 0 when provided.")
        n_raw = data.get("n")
        n: int | None
        if n_raw is None:
            n = None
        else:
            n = _require_int(data, "n")
            if n <= 0:
                raise ValidationError("Field 'n' must be > 0 when provided.")
        return cls(
            study_id=study_id,
            arm_id=arm_id,
            covariate_name=covariate_name,
            mean=mean,
            sd=sd,
            n=n,
        )


@dataclass(frozen=True)
class SurvivalIntervalADRecord:
    study_id: str
    arm_id: str
    outcome_id: str
    interval_id: str
    t_start: float
    t_end: float
    events: int
    person_time: float

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SurvivalIntervalADRecord":
        study_id = _require_str(data, "study_id")
        arm_id = _require_str(data, "arm_id")
        outcome_id = _require_str(data, "outcome_id")
        interval_id = _require_str(data, "interval_id")
        t_start = _require_float(data, "t_start")
        t_end = _require_float(data, "t_end")
        events = _require_int(data, "events")
        person_time = _require_float(data, "person_time")

        if t_start < 0:
            raise ValidationError("Field 't_start' must be >= 0.")
        if t_end <= t_start:
            raise ValidationError("Field 't_end' must be > t_start.")
        if events < 0:
            raise ValidationError("Field 'events' must be >= 0.")
        if person_time <= 0:
            raise ValidationError("Field 'person_time' must be > 0.")

        return cls(
            study_id=study_id,
            arm_id=arm_id,
            outcome_id=outcome_id,
            interval_id=interval_id,
            t_start=t_start,
            t_end=t_end,
            events=events,
            person_time=person_time,
        )
