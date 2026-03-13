"""Benchmark harness for comparing NMA pooling approaches."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Protocol

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import EvidenceDataset
from nma_pool.data.schemas import ValidationError
from nma_pool.models.core_ad import ADNMAPooler
from nma_pool.models.spec import ModelSpec

from .contrasts import extract_study_contrasts


ContrastKey = tuple[str, str]  # (numerator_treatment, denominator_treatment)


class BenchmarkAdapter(Protocol):
    name: str

    def run(
        self,
        dataset: EvidenceDataset,
        spec: ModelSpec,
        requested_contrasts: tuple[ContrastKey, ...],
    ) -> "BenchmarkModelResult":
        ...


@dataclass(frozen=True)
class BenchmarkModelResult:
    name: str
    status: str
    treatment_effects: dict[str, float] = field(default_factory=dict)
    treatment_ses: dict[str, float] = field(default_factory=dict)
    contrasts: dict[str, dict[str, float]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class BenchmarkSuiteResult:
    requested_contrasts: tuple[ContrastKey, ...]
    models: tuple[BenchmarkModelResult, ...]
    reference_model: str | None
    best_model: str | None
    score_metric: str
    scores: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_contrasts": [list(pair) for pair in self.requested_contrasts],
            "reference_model": self.reference_model,
            "best_model": self.best_model,
            "score_metric": self.score_metric,
            "scores": self.scores,
            "models": [
                {
                    "name": row.name,
                    "status": row.status,
                    "treatment_effects": row.treatment_effects,
                    "treatment_ses": row.treatment_ses,
                    "contrasts": row.contrasts,
                    "warnings": list(row.warnings),
                    "error": row.error,
                }
                for row in self.models
            ],
        }

    def write_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


class CoreRandomEffectsAdapter:
    name = "core_random_effects"

    def run(
        self,
        dataset: EvidenceDataset,
        spec: ModelSpec,
        requested_contrasts: tuple[ContrastKey, ...],
    ) -> BenchmarkModelResult:
        fit = ADNMAPooler().fit(
            dataset,
            ModelSpec(
                outcome_id=spec.outcome_id,
                measure_type=spec.measure_type,
                reference_treatment=spec.reference_treatment,
                random_effects=True,
            ),
        )
        return _from_fit_result(
            name=self.name,
            fit=fit,
            requested_contrasts=requested_contrasts,
        )


class CoreFixedEffectsAdapter:
    name = "core_fixed_effects"

    def run(
        self,
        dataset: EvidenceDataset,
        spec: ModelSpec,
        requested_contrasts: tuple[ContrastKey, ...],
    ) -> BenchmarkModelResult:
        fit = ADNMAPooler().fit(
            dataset,
            ModelSpec(
                outcome_id=spec.outcome_id,
                measure_type=spec.measure_type,
                reference_treatment=spec.reference_treatment,
                random_effects=False,
            ),
        )
        return _from_fit_result(
            name=self.name,
            fit=fit,
            requested_contrasts=requested_contrasts,
        )


class DirectPairwiseAdapter:
    """Direct-only pooled contrasts (fixed effect)."""

    name = "direct_pairwise"

    def run(
        self,
        dataset: EvidenceDataset,
        spec: ModelSpec,
        requested_contrasts: tuple[ContrastKey, ...],
    ) -> BenchmarkModelResult:
        rows = extract_study_contrasts(
            dataset=dataset,
            outcome_id=spec.outcome_id,
            measure_type=spec.measure_type,
        )
        grouped: dict[tuple[str, str], list[tuple[float, float]]] = {}
        for row in rows:
            grouped.setdefault((row.treatment_lo, row.treatment_hi), []).append(
                (row.effect_hi_minus_lo, row.variance)
            )

        contrast_payload: dict[str, dict[str, float]] = {}
        warnings: list[str] = []
        for numerator, denominator in requested_contrasts:
            canon = tuple(sorted((numerator, denominator)))
            data = grouped.get(canon)
            label = _contrast_label((numerator, denominator))
            if not data:
                warnings.append(f"No direct evidence for requested contrast {label}.")
                continue
            effect_canon, se_canon = _pool_effect_variance(data)
            sign = 1.0 if (numerator == canon[1] and denominator == canon[0]) else -1.0
            contrast_payload[label] = {
                "effect": sign * effect_canon,
                "se": se_canon,
            }

        status = "success" if contrast_payload else "partial"
        return BenchmarkModelResult(
            name=self.name,
            status=status,
            treatment_effects={},
            treatment_ses={},
            contrasts=contrast_payload,
            warnings=tuple(warnings),
            error=None if contrast_payload else "No direct contrasts available.",
        )


class ExternalCommandAdapter:
    """Adapter for external benchmark methods via command-line executable."""

    def __init__(
        self,
        *,
        name: str,
        command: list[str],
        timeout_seconds: int = 120,
        fail_on_stderr_patterns: list[str] | None = None,
    ) -> None:
        self.name = name
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.fail_on_stderr_patterns = tuple(
            pattern.lower() for pattern in (fail_on_stderr_patterns or [])
        )

    def run(
        self,
        dataset: EvidenceDataset,
        spec: ModelSpec,
        requested_contrasts: tuple[ContrastKey, ...],
    ) -> BenchmarkModelResult:
        if not self.command:
            return BenchmarkModelResult(
                name=self.name,
                status="error",
                error="External command cannot be empty.",
            )
        with tempfile.TemporaryDirectory(prefix="nma_bench_") as tmp:
            in_path = Path(tmp) / "input.json"
            out_path = Path(tmp) / "output.json"
            payload = {
                "analysis": {
                    "outcome_id": spec.outcome_id,
                    "measure_type": spec.measure_type,
                    "reference_treatment": spec.reference_treatment,
                },
                "data": _dataset_to_payload(dataset),
                "requested_contrasts": [list(pair) for pair in requested_contrasts],
                "output_path": str(out_path),
            }
            in_path.write_text(json.dumps(payload), encoding="utf-8")
            resolved_exe = _resolve_executable(self.command[0])
            cmd = [resolved_exe, *self.command[1:], "--input", str(in_path), "--output", str(out_path)]
            try:
                proc = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except FileNotFoundError as exc:
                return BenchmarkModelResult(
                    name=self.name,
                    status="unavailable",
                    error=f"Executable not found: {exc}",
                )
            except subprocess.TimeoutExpired:
                return BenchmarkModelResult(
                    name=self.name,
                    status="error",
                    error=f"Timed out after {self.timeout_seconds}s.",
                )

            warnings: list[str] = []
            stderr_text = proc.stderr.strip()
            if stderr_text:
                stderr_lower = stderr_text.lower()
                if any(pattern in stderr_lower for pattern in self.fail_on_stderr_patterns):
                    return BenchmarkModelResult(
                        name=self.name,
                        status="error",
                        error=f"External command stderr matched fail patterns: {stderr_text}",
                        warnings=tuple(warnings),
                    )

            if proc.returncode != 0:
                return BenchmarkModelResult(
                    name=self.name,
                    status="error",
                    error=f"External command failed: {proc.stderr.strip()}",
                    warnings=tuple(warnings),
                )
            if not out_path.exists():
                return BenchmarkModelResult(
                    name=self.name,
                    status="error",
                    error="External command did not produce output JSON.",
                    warnings=tuple(warnings),
                )

            try:
                out_payload = json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return BenchmarkModelResult(
                    name=self.name,
                    status="error",
                    error=f"Invalid JSON output: {exc}",
                    warnings=tuple(warnings),
                )

            treatment_effects = {
                str(k): float(v) for k, v in out_payload.get("treatment_effects", {}).items()
            }
            treatment_ses = {
                str(k): float(v) for k, v in out_payload.get("treatment_ses", {}).items()
            }
            contrasts = {}
            for label, values in out_payload.get("contrasts", {}).items():
                if not isinstance(values, dict):
                    continue
                if "effect" not in values or "se" not in values:
                    continue
                contrasts[str(label)] = {
                    "effect": float(values["effect"]),
                    "se": float(values["se"]),
                }

            diagnostics_payload = out_payload.get("diagnostics")
            diagnostics_pass = True
            diagnostics_issues: list[str] = []
            if isinstance(diagnostics_payload, dict):
                diagnostics_pass = parse_bool_value(
                    diagnostics_payload.get("pass", True),
                    field_name="diagnostics.pass",
                )
                diagnostics_issues = _coerce_str_list(diagnostics_payload.get("issues"))
                warnings.extend(_coerce_str_list(diagnostics_payload.get("warnings")))

            expected_labels = {_contrast_label(pair) for pair in requested_contrasts}
            missing = sorted(label for label in expected_labels if label not in contrasts)
            if missing:
                warnings.append(
                    "Missing requested contrasts from external output: "
                    + ", ".join(missing)
                )

            status = "success"
            error: str | None = None
            if not diagnostics_pass:
                status = "error"
                error = (
                    "External diagnostics failed: "
                    + (", ".join(diagnostics_issues) if diagnostics_issues else "unspecified")
                )
            elif missing:
                status = "partial" if contrasts else "error"
                if not contrasts:
                    error = "No requested contrasts returned by external adapter."

            return BenchmarkModelResult(
                name=self.name,
                status=status,
                treatment_effects=treatment_effects,
                treatment_ses=treatment_ses,
                contrasts=contrasts,
                warnings=tuple(warnings),
                error=error,
            )


class BenchmarkRunner:
    """Run multiple benchmark adapters and score results."""

    def __init__(self, adapters: list[BenchmarkAdapter] | None = None) -> None:
        self._adapters = adapters or [
            CoreRandomEffectsAdapter(),
            CoreFixedEffectsAdapter(),
            DirectPairwiseAdapter(),
        ]

    def run(
        self,
        dataset: EvidenceDataset,
        spec: ModelSpec,
        *,
        requested_contrasts: tuple[ContrastKey, ...] | None = None,
        truth_effects_vs_reference: dict[str, float] | None = None,
    ) -> BenchmarkSuiteResult:
        if requested_contrasts is None:
            requested_contrasts = _default_requested_contrasts(dataset, spec.outcome_id)
        results: list[BenchmarkModelResult] = []
        for adapter in self._adapters:
            try:
                result = adapter.run(dataset, spec, requested_contrasts)
                results.append(result)
            except Exception as exc:  # pragma: no cover
                results.append(
                    BenchmarkModelResult(
                        name=adapter.name,
                        status="error",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

        reference = _first_successful(results)
        if truth_effects_vs_reference:
            scores, metric = _score_against_truth(
                results=results,
                requested_contrasts=requested_contrasts,
                truth_effects_vs_reference=truth_effects_vs_reference,
            )
        else:
            scores, metric = _score_against_reference(
                results=results,
                requested_contrasts=requested_contrasts,
                reference_model=reference,
            )

        best = _best_model_name(scores)
        return BenchmarkSuiteResult(
            requested_contrasts=requested_contrasts,
            models=tuple(results),
            reference_model=reference,
            best_model=best,
            score_metric=metric,
            scores=scores,
        )


def _default_requested_contrasts(
    dataset: EvidenceDataset,
    outcome_id: str,
) -> tuple[ContrastKey, ...]:
    treatments = list(dataset.treatments_for_outcome(outcome_id))
    pairs: list[ContrastKey] = []
    for i in range(len(treatments)):
        for j in range(i + 1, len(treatments)):
            pairs.append((treatments[j], treatments[i]))
    return tuple(pairs)


def _from_fit_result(name: str, fit: Any, requested_contrasts: tuple[ContrastKey, ...]) -> BenchmarkModelResult:
    contrasts = {}
    for numerator, denominator in requested_contrasts:
        effect, se = fit.contrast(numerator, denominator)
        contrasts[_contrast_label((numerator, denominator))] = {
            "effect": float(effect),
            "se": float(se),
        }
    return BenchmarkModelResult(
        name=name,
        status="success",
        treatment_effects={k: float(v) for k, v in fit.treatment_effects.items()},
        treatment_ses={k: float(v) for k, v in fit.treatment_ses.items()},
        contrasts=contrasts,
        warnings=tuple(fit.warnings),
    )


def _score_against_truth(
    *,
    results: list[BenchmarkModelResult],
    requested_contrasts: tuple[ContrastKey, ...],
    truth_effects_vs_reference: dict[str, float],
) -> tuple[dict[str, float], str]:
    scores: dict[str, float] = {}
    for row in results:
        if row.status != "success":
            continue
        mae = _mae_against_truth(row, requested_contrasts, truth_effects_vs_reference)
        if mae is not None:
            scores[row.name] = mae
    return scores, "mae_vs_truth"


def _score_against_reference(
    *,
    results: list[BenchmarkModelResult],
    requested_contrasts: tuple[ContrastKey, ...],
    reference_model: str | None,
) -> tuple[dict[str, float], str]:
    if reference_model is None:
        return {}, "mae_vs_reference"
    ref = next((row for row in results if row.name == reference_model), None)
    if ref is None or ref.status != "success":
        return {}, "mae_vs_reference"
    scores: dict[str, float] = {}
    for row in results:
        if row.status != "success":
            continue
        mae = _mae_against_model(row, ref, requested_contrasts)
        if mae is not None:
            scores[row.name] = mae
    return scores, "mae_vs_reference"


def _mae_against_truth(
    row: BenchmarkModelResult,
    requested_contrasts: tuple[ContrastKey, ...],
    truth_effects_vs_reference: dict[str, float],
) -> float | None:
    errors: list[float] = []
    for numerator, denominator in requested_contrasts:
        label = _contrast_label((numerator, denominator))
        if label not in row.contrasts:
            continue
        if numerator not in truth_effects_vs_reference or denominator not in truth_effects_vs_reference:
            continue
        truth = truth_effects_vs_reference[numerator] - truth_effects_vs_reference[denominator]
        errors.append(abs(row.contrasts[label]["effect"] - truth))
    if not errors:
        return None
    return sum(errors) / len(errors)


def _mae_against_model(
    row: BenchmarkModelResult,
    reference: BenchmarkModelResult,
    requested_contrasts: tuple[ContrastKey, ...],
) -> float | None:
    errors: list[float] = []
    for numerator, denominator in requested_contrasts:
        label = _contrast_label((numerator, denominator))
        if label not in row.contrasts or label not in reference.contrasts:
            continue
        errors.append(abs(row.contrasts[label]["effect"] - reference.contrasts[label]["effect"]))
    if not errors:
        return None
    return sum(errors) / len(errors)


def _first_successful(results: list[BenchmarkModelResult]) -> str | None:
    for row in results:
        if row.status == "success":
            return row.name
    return None


def _best_model_name(scores: dict[str, float]) -> str | None:
    if not scores:
        return None
    return min(scores, key=lambda name: scores[name])


def _contrast_label(pair: ContrastKey) -> str:
    return f"{pair[0]}_vs_{pair[1]}"


def _pool_effect_variance(rows: list[tuple[float, float]]) -> tuple[float, float]:
    weights = [1.0 / variance for _, variance in rows if variance > 0]
    if not weights or len(weights) != len(rows):
        raise ValidationError("Invalid variance in direct contrast pooling.")
    total_w = sum(weights)
    effect = sum(w * row[0] for w, row in zip(weights, rows)) / total_w
    se = math.sqrt(1.0 / total_w)
    return effect, se


def _dataset_to_payload(dataset: EvidenceDataset) -> dict[str, Any]:
    return {
        "studies": [
            {
                "study_id": row.study_id,
                "design": row.design,
                "year": row.year,
                "source_id": row.source_id,
                "rob_domain_summary": row.rob_domain_summary,
            }
            for row in dataset.studies
        ],
        "arms": [
            {
                "study_id": row.study_id,
                "arm_id": row.arm_id,
                "treatment_id": row.treatment_id,
                "n": row.n,
                "dose": row.dose,
                "components": list(row.components),
            }
            for row in dataset.arms
        ],
        "outcomes_ad": [
            {
                "study_id": row.study_id,
                "arm_id": row.arm_id,
                "outcome_id": row.outcome_id,
                "measure_type": row.measure_type,
                "value": row.value,
                "se": row.se,
            }
            for row in dataset.outcomes_ad
        ],
    }


def _resolve_executable(exe: str) -> str:
    # Keep explicit paths untouched when present.
    if os.path.isabs(exe) and os.path.exists(exe):
        return exe

    # Standard PATH lookup first.
    found = shutil.which(exe)
    if found:
        return found

    # Windows fallback: common R installation locations.
    low = exe.lower()
    if low in {"rscript", "rscript.exe"}:
        candidates = [
            Path("C:/Program Files/R"),
            Path("C:/Program Files (x86)/R"),
        ]
        for base in candidates:
            if not base.exists():
                continue
            # Prefer the latest version folder.
            versions = sorted(
                [p for p in base.iterdir() if p.is_dir()],
                key=lambda p: p.name,
                reverse=True,
            )
            for version_dir in versions:
                for sub in ("bin/Rscript.exe", "bin/x64/Rscript.exe"):
                    path = version_dir / sub
                    if path.exists():
                        return str(path)

    return exe


def _coerce_str_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return [str(raw)]
