from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_publication_pipeline_writes_artifacts(tmp_path: Path) -> None:
    cfg = {
        "thresholds": {
            "coverage_lo": 0.8,
            "coverage_hi": 1.0,
            "bias_improvement_min": 0.0,
            "logscore_win_rate_min": 0.0,
        },
        "continuous": {
            "n_networks": 10,
            "seed_start": 11,
            "n_per_arm": 100,
            "se": 0.25,
            "noise_sd": 0.05,
        },
        "survival_nonph": {
            "n_networks": 8,
            "seed_start": 37,
            "n_per_arm": 350,
            "replicates_per_pair": 2,
            "follow_up_fraction": 0.85,
        },
        "continuity_correction": 0.5,
    }
    cfg_path = tmp_path / "publication-config.json"
    out_path = tmp_path / "publication-suite.json"
    summary_path = tmp_path / "publication-summary.md"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "pipelines/run_publication_suite.py",
            "--config",
            str(cfg_path),
            "--out",
            str(out_path),
            "--summary",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()
    assert summary_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "overall_pass" in payload
    assert "continuous" in payload
    assert "survival_nonph" in payload
    assert "gates" in payload
