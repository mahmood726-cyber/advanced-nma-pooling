"""Run benchmark suite across multiple NMA adapters."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from nma_pool.config_parsing import parse_bool_value
from nma_pool.data.builder import DatasetBuilder
from nma_pool.models.spec import ModelSpec
from nma_pool.pipelines._common import load_json_object
from nma_pool.validation.benchmark import (
    BenchmarkRunner,
    ContrastKey,
    ExternalCommandAdapter,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to benchmark config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/benchmark-results.json"),
        help="Output benchmark artifact path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    analysis = payload["analysis"]
    data = payload["data"]
    benchmark_cfg = payload.get("benchmark", {})

    dataset = DatasetBuilder().from_payload(data)
    spec = ModelSpec(
        outcome_id=str(analysis["outcome_id"]),
        measure_type=str(analysis["measure_type"]),  # type: ignore[arg-type]
        reference_treatment=str(analysis["reference_treatment"]),
        random_effects=parse_bool_value(
            analysis.get("random_effects", True),
            field_name="analysis.random_effects",
        ),
    )

    adapters = []
    for ext in benchmark_cfg.get("external_adapters", []):
        if not isinstance(ext, dict):
            continue
        name = str(ext.get("name", "external"))
        command = ext.get("command", [])
        if not isinstance(command, list) or not command:
            continue
        adapters.append(
            ExternalCommandAdapter(
                name=name,
                command=[str(token) for token in command],
                timeout_seconds=int(ext.get("timeout_seconds", 120)),
                fail_on_stderr_patterns=[
                    str(token) for token in ext.get("fail_on_stderr_patterns", [])
                ],
            )
        )

    runner = BenchmarkRunner()
    if adapters:
        from nma_pool.validation.benchmark import (
            CoreFixedEffectsAdapter,
            CoreRandomEffectsAdapter,
            DirectPairwiseAdapter,
        )

        runner = BenchmarkRunner(
            adapters=[
                CoreRandomEffectsAdapter(),
                CoreFixedEffectsAdapter(),
                DirectPairwiseAdapter(),
                *adapters,
            ]
        )

    requested_contrasts = _parse_requested_contrasts(benchmark_cfg.get("requested_contrasts"))
    truth_effects = benchmark_cfg.get("truth_effects_vs_reference")
    if truth_effects is not None:
        truth_effects = {str(k): float(v) for k, v in truth_effects.items()}

    suite = runner.run(
        dataset=dataset,
        spec=spec,
        requested_contrasts=requested_contrasts,
        truth_effects_vs_reference=truth_effects,
    )
    suite.write_json(args.out)
    print(f"Wrote benchmark results: {args.out}")
    print(f"best_model={suite.best_model}")
    print(f"score_metric={suite.score_metric}")
    for name, score in sorted(suite.scores.items()):
        print(f"{name}: {score:.6f}")
    return 0


def _parse_requested_contrasts(raw: Any) -> tuple[ContrastKey, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("benchmark.requested_contrasts must be a list of pairs.")
    out: list[ContrastKey] = []
    for item in raw:
        if (
            isinstance(item, list)
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], str)
            and item[0] != item[1]
        ):
            out.append((item[0], item[1]))
        else:
            raise ValueError(
                "Each requested contrast must be [numerator_treatment, denominator_treatment]."
            )
    return tuple(out)


if __name__ == "__main__":
    raise SystemExit(main())
