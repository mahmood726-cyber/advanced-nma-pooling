"""Inference runner for config-driven AD NMA analyses."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder, EvidenceDataset
from nma_pool.models.core_ad import ADNMAPooler, NMAFitResult
from nma_pool.models.spec import ModelSpec
from nma_pool.reporting.model_card import build_model_card
from nma_pool.validation.diagnostics import NetworkDiagnostics, summarize_network
from nma_pool.validation.inconsistency import (
    InconsistencyDiagnostics,
    run_inconsistency_diagnostics,
)


@dataclass(frozen=True)
class RunArtifacts:
    spec: ModelSpec
    dataset: EvidenceDataset
    diagnostics: NetworkDiagnostics
    inconsistency: InconsistencyDiagnostics
    fit: NMAFitResult
    model_card: dict[str, Any]


class FitRunner:
    """High-level runner for analysis payloads/configs."""

    def __init__(
        self,
        dataset_builder: DatasetBuilder | None = None,
        model: ADNMAPooler | None = None,
    ) -> None:
        self._dataset_builder = dataset_builder or DatasetBuilder()
        self._model = model or ADNMAPooler()

    def run_from_config(self, config_path: str | Path) -> RunArtifacts:
        payload = _load_config(config_path)
        return self.run_from_payload(payload)

    def run_from_payload(self, payload: Mapping[str, Any]) -> RunArtifacts:
        analysis = payload.get("analysis", {})
        data = payload.get("data", {})
        spec = ModelSpec(
            outcome_id=str(analysis["outcome_id"]),
            measure_type=str(analysis["measure_type"]),  # type: ignore[arg-type]
            reference_treatment=str(analysis["reference_treatment"]),
            random_effects=parse_bool_value(
                analysis.get("random_effects", True),
                field_name="analysis.random_effects",
            ),
        )
        dataset = self._dataset_builder.from_payload(data)
        diagnostics = summarize_network(dataset, spec.outcome_id)
        inconsistency = run_inconsistency_diagnostics(dataset=dataset, spec=spec)
        fit = self._model.fit(dataset, spec)
        model_card = build_model_card(
            spec=spec,
            fit=fit,
            diagnostics=diagnostics,
            inconsistency=inconsistency,
        )
        return RunArtifacts(
            spec=spec,
            dataset=dataset,
            diagnostics=diagnostics,
            inconsistency=inconsistency,
            fit=fit,
            model_card=model_card,
        )


def _load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))

    if suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "YAML config requested but pyyaml is not installed. "
                "Use JSON config or install pyyaml."
            ) from exc
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("Config root must be a mapping/object.")
        return loaded

    raise ValueError("Unsupported config extension. Use .json/.yml/.yaml")
