from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_module_cli_runs_analysis_from_source_tree(tmp_path: Path) -> None:
    payload = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": False,
        },
        "data": {
            "studies": [
                {
                    "study_id": "S1",
                    "design": "rct",
                    "year": 2020,
                    "source_id": "src1",
                    "rob_domain_summary": "low",
                },
                {
                    "study_id": "S2",
                    "design": "rct",
                    "year": 2021,
                    "source_id": "src2",
                    "rob_domain_summary": "low",
                },
            ],
            "arms": [
                {"study_id": "S1", "arm_id": "A1", "treatment_id": "A", "n": 100},
                {"study_id": "S1", "arm_id": "A2", "treatment_id": "B", "n": 100},
                {"study_id": "S2", "arm_id": "B1", "treatment_id": "A", "n": 100},
                {"study_id": "S2", "arm_id": "B2", "treatment_id": "B", "n": 100},
            ],
            "outcomes_ad": [
                {
                    "study_id": "S1",
                    "arm_id": "A1",
                    "outcome_id": "efficacy",
                    "measure_type": "continuous",
                    "value": 0.0,
                    "se": 0.2,
                },
                {
                    "study_id": "S1",
                    "arm_id": "A2",
                    "outcome_id": "efficacy",
                    "measure_type": "continuous",
                    "value": 1.0,
                    "se": 0.2,
                },
                {
                    "study_id": "S2",
                    "arm_id": "B1",
                    "outcome_id": "efficacy",
                    "measure_type": "continuous",
                    "value": 0.0,
                    "se": 0.2,
                },
                {
                    "study_id": "S2",
                    "arm_id": "B2",
                    "outcome_id": "efficacy",
                    "measure_type": "continuous",
                    "value": 1.0,
                    "se": 0.2,
                },
            ],
        },
    }
    cfg_path = tmp_path / "analysis.json"
    out_path = tmp_path / "model-card.json"
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        os.pathsep.join([src_path, env["PYTHONPATH"]])
        if env.get("PYTHONPATH")
        else src_path
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "nma_pool",
            "analysis",
            "--config",
            str(cfg_path),
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["analysis"]["outcome_id"] == "efficacy"
