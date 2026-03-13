from __future__ import annotations

import sys

from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.spec import ModelSpec
from nma_pool.validation.benchmark import BenchmarkRunner, ExternalCommandAdapter
from nma_pool.validation.simulation import (
    ContinuousSimulationSpec,
    simulate_continuous_abc_network,
)


def test_benchmark_runner_default_adapters() -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(noise_sd=0.0, se=0.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )

    result = BenchmarkRunner().run(
        dataset=dataset,
        spec=spec,
        requested_contrasts=(("B", "A"), ("C", "A"), ("C", "B")),
        truth_effects_vs_reference={"A": 0.0, "B": 1.0, "C": 2.0},
    )
    assert len(result.models) >= 3
    successes = [row for row in result.models if row.status == "success"]
    assert len(successes) >= 2
    assert result.score_metric == "mae_vs_truth"
    assert result.best_model in result.scores


def test_benchmark_external_adapter_unavailable_is_nonfatal() -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(noise_sd=0.0, se=0.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )
    runner = BenchmarkRunner(
        adapters=[
            ExternalCommandAdapter(
                name="missing_external",
                command=["definitely-not-a-real-command-xyz"],
            )
        ]
    )
    result = runner.run(dataset=dataset, spec=spec)
    assert len(result.models) == 1
    assert result.models[0].status == "unavailable"


def test_external_adapter_success_contract(tmp_path) -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(noise_sd=0.0, se=0.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )

    script = tmp_path / "fake_external_success.py"
    script.write_text(
        """
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

with open(args.input, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

contrasts = {}
for numerator, denominator in payload.get("requested_contrasts", []):
    label = f"{numerator}_vs_{denominator}"
    contrasts[label] = {"effect": 0.1, "se": 0.2}

out = {
    "treatment_effects": {"A": 0.0, "B": 0.1, "C": 0.2},
    "treatment_ses": {"A": 0.0, "B": 0.2, "C": 0.2},
    "contrasts": contrasts,
    "diagnostics": {"pass": True, "issues": [], "warnings": []}
}
with open(args.output, "w", encoding="utf-8") as fh:
    json.dump(out, fh)
""".strip(),
        encoding="utf-8",
    )
    adapter = ExternalCommandAdapter(
        name="fake_success",
        command=[sys.executable, str(script)],
    )
    result = BenchmarkRunner(adapters=[adapter]).run(
        dataset=dataset,
        spec=spec,
        requested_contrasts=(("B", "A"), ("C", "A"), ("C", "B")),
    )
    assert result.models[0].status == "success"
    assert len(result.models[0].contrasts) == 3


def test_external_adapter_partial_missing_contrasts_not_scored(tmp_path) -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(noise_sd=0.0, se=0.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )

    script = tmp_path / "fake_external_partial.py"
    script.write_text(
        """
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

with open(args.input, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

requested = payload.get("requested_contrasts", [])
contrasts = {}
if requested:
    numerator, denominator = requested[0]
    contrasts[f"{numerator}_vs_{denominator}"] = {"effect": 0.1, "se": 0.2}

out = {
    "treatment_effects": {"A": 0.0, "B": 0.1, "C": 0.2},
    "treatment_ses": {"A": 0.0, "B": 0.2, "C": 0.2},
    "contrasts": contrasts,
    "diagnostics": {"pass": True, "issues": [], "warnings": []}
}
with open(args.output, "w", encoding="utf-8") as fh:
    json.dump(out, fh)
""".strip(),
        encoding="utf-8",
    )
    adapter = ExternalCommandAdapter(
        name="fake_partial",
        command=[sys.executable, str(script)],
    )
    result = BenchmarkRunner(adapters=[adapter]).run(
        dataset=dataset,
        spec=spec,
        requested_contrasts=(("B", "A"), ("C", "A"), ("C", "B")),
        truth_effects_vs_reference={"A": 0.0, "B": 1.0, "C": 2.0},
    )
    model = result.models[0]
    assert model.status == "partial"
    assert "fake_partial" not in result.scores
    assert any("Missing requested contrasts" in warning for warning in model.warnings)


def test_external_adapter_diagnostics_fail_not_scored(tmp_path) -> None:
    payload = simulate_continuous_abc_network(
        ContinuousSimulationSpec(noise_sd=0.0, se=0.2)
    )
    dataset = DatasetBuilder().from_payload(payload)
    spec = ModelSpec(
        outcome_id="efficacy",
        measure_type="continuous",
        reference_treatment="A",
        random_effects=True,
    )

    script = tmp_path / "fake_external_bad_diag.py"
    script.write_text(
        """
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

with open(args.input, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

contrasts = {}
for numerator, denominator in payload.get("requested_contrasts", []):
    label = f"{numerator}_vs_{denominator}"
    contrasts[label] = {"effect": 0.1, "se": 0.2}

out = {
    "treatment_effects": {"A": 0.0, "B": 0.1, "C": 0.2},
    "treatment_ses": {"A": 0.0, "B": 0.2, "C": 0.2},
    "contrasts": contrasts,
    "diagnostics": {"pass": False, "issues": ["divergent_transitions=12"], "warnings": []}
}
with open(args.output, "w", encoding="utf-8") as fh:
    json.dump(out, fh)
""".strip(),
        encoding="utf-8",
    )
    adapter = ExternalCommandAdapter(
        name="fake_bad_diag",
        command=[sys.executable, str(script)],
    )
    result = BenchmarkRunner(adapters=[adapter]).run(
        dataset=dataset,
        spec=spec,
        requested_contrasts=(("B", "A"), ("C", "A"), ("C", "B")),
        truth_effects_vs_reference={"A": 0.0, "B": 1.0, "C": 2.0},
    )
    model = result.models[0]
    assert model.status == "error"
    assert "diagnostics failed" in (model.error or "").lower()
    assert "fake_bad_diag" not in result.scores
