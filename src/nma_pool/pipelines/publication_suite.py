"""Run publication-grade simulation suite and emit JSON/Markdown artifacts."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path

from nma_pool.pipelines._common import load_json_object
from nma_pool.validation.publication import run_publication_suite


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to publication-suite config JSON.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/publication-suite.json"),
        help="Output JSON artifact path.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/publication-summary.md"),
        help="Output Markdown summary path.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json_object(args.config)
    result = run_publication_suite(payload)
    artifact = result.to_dict()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")

    summary_md = result.to_markdown()
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(summary_md, encoding="utf-8")

    print(f"Wrote publication-suite artifact: {args.out}")
    print(f"Wrote publication summary: {args.summary}")
    print(f"overall_pass={result.overall_pass}")
    for gate, passed in sorted(result.gates.items()):
        print(f"{gate}: {'PASS' if passed else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
