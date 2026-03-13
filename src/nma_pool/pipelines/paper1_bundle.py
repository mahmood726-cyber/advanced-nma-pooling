"""Build a reproducible Paper-1 artifact bundle for RSM submission."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

from nma_pool.config_parsing import parse_bool_value
from nma_pool.pipelines._common import (
    cli_command,
    load_json_object,
    subprocess_env_with_package_path,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to paper1 bundle config JSON.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts/paper1-bundle"),
        help="Output directory for paper1 bundle artifacts.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cfg_path = args.config.resolve()
    payload = load_json_object(cfg_path)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle_cfg = payload.get("bundle", {})
    paths_cfg = payload.get("paths", {})
    docs_cfg = payload.get("docs", {})
    base_dir = cfg_path.parent

    steps: list[dict[str, Any]] = []
    outputs: list[Path] = []

    if parse_bool_value(
        bundle_cfg.get("run_publication_suite", True),
        field_name="bundle.run_publication_suite",
    ):
        publication_config = _resolve_path(paths_cfg["publication_config"], base_dir)
        publication_json = out_dir / "publication-suite.json"
        publication_summary = out_dir / "publication-summary.md"
        steps.append(
            _run_step(
                name="publication_suite",
                command=cli_command(
                    "publication-suite",
                    "--config",
                    str(publication_config),
                    "--out",
                    str(publication_json),
                    "--summary",
                    str(publication_summary),
                ),
            )
        )
        outputs.extend([publication_json, publication_summary])

    if parse_bool_value(
        bundle_cfg.get("run_bias_adjusted", True),
        field_name="bundle.run_bias_adjusted",
    ):
        bias_config = _resolve_path(paths_cfg["bias_adjusted_config"], base_dir)
        bias_json = out_dir / "bias-adjusted-result.json"
        steps.append(
            _run_step(
                name="bias_adjusted",
                command=cli_command(
                    "bias-adjusted",
                    "--config",
                    str(bias_config),
                    "--out",
                    str(bias_json),
                ),
            )
        )
        outputs.append(bias_json)

    if parse_bool_value(
        bundle_cfg.get("run_bias_adjusted_bayesian", True),
        field_name="bundle.run_bias_adjusted_bayesian",
    ):
        bias_bayes_config = _resolve_path(
            paths_cfg["bias_adjusted_bayesian_config"],
            base_dir,
        )
        bias_bayes_json = out_dir / "bias-adjusted-bayesian-result.json"
        steps.append(
            _run_step(
                name="bias_adjusted_bayesian",
                command=cli_command(
                    "bias-adjusted-bayesian",
                    "--config",
                    str(bias_bayes_config),
                    "--out",
                    str(bias_bayes_json),
                ),
            )
        )
        outputs.append(bias_bayes_json)

    if parse_bool_value(
        bundle_cfg.get("run_bias_sensitivity", True),
        field_name="bundle.run_bias_sensitivity",
    ):
        sensitivity_config = _resolve_path(paths_cfg["bias_sensitivity_config"], base_dir)
        sensitivity_json = out_dir / "bias-sensitivity-result.json"
        steps.append(
            _run_step(
                name="bias_sensitivity",
                command=cli_command(
                    "bias-sensitivity",
                    "--config",
                    str(sensitivity_config),
                    "--out",
                    str(sensitivity_json),
                ),
            )
        )
        outputs.append(sensitivity_json)

    copied_docs: list[dict[str, str]] = []
    docs_to_copy = docs_cfg.get(
        "copy",
        [
            "docs/methods/paper1-protocol.md",
            "docs/validation/paper1-simulation-registry.md",
            "docs/methods/paper1-manuscript-outline.md",
        ],
    )
    docs_dir = out_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    for raw in docs_to_copy:
        src = _resolve_path(raw, base_dir)
        if not src.exists():
            continue
        dst = docs_dir / src.name
        shutil.copyfile(src, dst)
        copied_docs.append({"source": str(src), "dest": str(dst)})
        outputs.append(dst)

    summary_path = out_dir / "paper1-executive-summary.md"
    summary_text = _build_executive_summary(
        steps=steps,
        publication_json=(out_dir / "publication-suite.json"),
        bias_json=(out_dir / "bias-adjusted-result.json"),
        bias_bayes_json=(out_dir / "bias-adjusted-bayesian-result.json"),
        sensitivity_json=(out_dir / "bias-sensitivity-result.json"),
    )
    summary_path.write_text(summary_text, encoding="utf-8")
    outputs.append(summary_path)

    manifest_path = out_dir / "manifest.json"
    manifest = {
        "bundle_name": str(bundle_cfg.get("name", "paper1-rsm-bundle")),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "input_config_path": str(cfg_path),
        "input_config_sha256": _sha256_file(cfg_path),
        "steps": steps,
        "copied_docs": copied_docs,
        "outputs": [
            {
                "path": str(path),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in outputs
            if path.exists()
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote paper1 bundle: {out_dir}")
    print(f"manifest={manifest_path}")
    print(f"summary={summary_path}")
    for step in steps:
        print(f"{step['name']}: {step['status']} ({step['elapsed_seconds']:.2f}s)")
    return 0


def _run_step(*, name: str, command: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=subprocess_env_with_package_path(),
    )
    elapsed = time.perf_counter() - start
    status = "success" if proc.returncode == 0 else "error"
    record = {
        "name": name,
        "status": status,
        "return_code": proc.returncode,
        "elapsed_seconds": elapsed,
        "command": command,
        "stdout_excerpt": _tail(proc.stdout, max_chars=1200),
        "stderr_excerpt": _tail(proc.stderr, max_chars=1200),
    }
    if proc.returncode != 0:
        raise RuntimeError(
            f"Step '{name}' failed with return_code={proc.returncode}: "
            f"{_tail(proc.stderr or proc.stdout, max_chars=400)}"
        )
    return record


def _build_executive_summary(
    *,
    steps: list[dict[str, Any]],
    publication_json: Path,
    bias_json: Path,
    bias_bayes_json: Path,
    sensitivity_json: Path,
) -> str:
    lines = [
        "# Paper 1 Executive Summary",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Step count: {len(steps)}",
        "",
        "## Step Status",
    ]
    for step in steps:
        lines.append(
            f"- `{step['name']}`: {step['status']} ({step['elapsed_seconds']:.2f}s)"
        )

    if publication_json.exists():
        pub = load_json_object(publication_json)
        lines.extend(
            [
                "",
                "## Publication Gates",
                f"- `overall_pass`: {pub.get('overall_pass')}",
            ]
        )
        for gate, passed in sorted(pub.get("gates", {}).items()):
            lines.append(f"- `{gate}`: {'PASS' if passed else 'FAIL'}")

    if bias_json.exists():
        bias = load_json_object(bias_json)
        nrs_bias = (
            bias.get("fit", {})
            .get("design_bias_effects_vs_reference_design", {})
            .get("nrs")
        )
        if nrs_bias is not None:
            lines.extend(
                [
                    "",
                    "## Bias-Adjusted Model",
                    f"- Estimated `nrs` bias term: {float(nrs_bias):.4f}",
                ]
            )

    if bias_bayes_json.exists():
        bayes = load_json_object(bias_bayes_json)
        backend = bayes.get("fit", {}).get("backend_used")
        n_draws = bayes.get("fit", {}).get("n_draws")
        lines.extend(
            [
                "",
                "## Bayesian Bias-Adjusted Model",
                f"- Backend used: `{backend}`",
                f"- Posterior draws: {n_draws}",
            ]
        )

    if sensitivity_json.exists():
        sens = load_json_object(sensitivity_json)
        lines.extend(
            [
                "",
                "## Prior Sensitivity",
                f"- Scenario count: {len(sens.get('scenarios', []))}",
            ]
        )
        trt_ranges = sens.get("summary", {}).get("treatment_effect_ranges", {})
        for treatment, stats in sorted(trt_ranges.items()):
            lines.append(
                f"- `{treatment}` span: {float(stats['span']):.4f} "
                f"(min={float(stats['min']):.4f}, max={float(stats['max']):.4f})"
            )

    lines.append("")
    return "\n".join(lines)


def _resolve_path(raw: Any, base_dir: Path) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        return path
    candidate = (base_dir / path).resolve()
    if candidate.exists():
        return candidate
    return path.resolve()


def _tail(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
