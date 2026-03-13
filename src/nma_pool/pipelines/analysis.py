"""Run an AD NMA analysis from config and write model card output."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from nma_pool.inference.runner import FitRunner
from nma_pool.reporting.model_card import write_json_report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to analysis config (.json/.yaml).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/model-card.json"),
        help="Output JSON report path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    runner = FitRunner()
    artifacts = runner.run_from_config(args.config)
    write_json_report(args.out, artifacts.model_card)
    print(f"Wrote report: {args.out}")
    print(f"tau={artifacts.fit.tau:.4f}")
    for treatment, effect in sorted(artifacts.fit.treatment_effects.items()):
        se = artifacts.fit.treatment_ses[treatment]
        print(f"{treatment}: effect={effect:.4f}, se={se:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
