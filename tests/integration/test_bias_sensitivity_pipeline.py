from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_bias_sensitivity_pipeline_writes_artifact(tmp_path: Path) -> None:
    cfg = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": False,
            "reference_design": "rct",
            "backend": "analytic",
        },
        "sensitivity": {
            "backend": "analytic",
            "bias_prior_sd_grid": [0.5, 1.5],
            "treatment_prior_sd_grid": [3.0, 10.0],
            "seed_grid": [5],
            "n_draws": 600,
            "n_warmup": 200,
            "n_chains": 2,
        },
        "data": {
            "studies": [
                {"study_id": "R1", "design": "rct", "year": 2021, "source_id": "src-r1", "rob_domain_summary": "low"},
                {"study_id": "R2", "design": "rct", "year": 2021, "source_id": "src-r2", "rob_domain_summary": "low"},
                {"study_id": "N1", "design": "nrs", "year": 2022, "source_id": "src-n1", "rob_domain_summary": "high"},
                {"study_id": "N2", "design": "nrs", "year": 2022, "source_id": "src-n2", "rob_domain_summary": "high"},
            ],
            "arms": [
                {"study_id": "R1", "arm_id": "R1A", "treatment_id": "A", "n": 120},
                {"study_id": "R1", "arm_id": "R1B", "treatment_id": "B", "n": 120},
                {"study_id": "R2", "arm_id": "R2A", "treatment_id": "A", "n": 120},
                {"study_id": "R2", "arm_id": "R2C", "treatment_id": "C", "n": 120},
                {"study_id": "N1", "arm_id": "N1A", "treatment_id": "A", "n": 120},
                {"study_id": "N1", "arm_id": "N1B", "treatment_id": "B", "n": 120},
                {"study_id": "N2", "arm_id": "N2A", "treatment_id": "A", "n": 120},
                {"study_id": "N2", "arm_id": "N2C", "treatment_id": "C", "n": 120},
            ],
            "outcomes_ad": [
                {"study_id": "R1", "arm_id": "R1A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
                {"study_id": "R1", "arm_id": "R1B", "outcome_id": "efficacy", "measure_type": "continuous", "value": 1.0, "se": 0.18},
                {"study_id": "R2", "arm_id": "R2A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
                {"study_id": "R2", "arm_id": "R2C", "outcome_id": "efficacy", "measure_type": "continuous", "value": 2.0, "se": 0.18},
                {"study_id": "N1", "arm_id": "N1A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
                {"study_id": "N1", "arm_id": "N1B", "outcome_id": "efficacy", "measure_type": "continuous", "value": 1.6, "se": 0.18},
                {"study_id": "N2", "arm_id": "N2A", "outcome_id": "efficacy", "measure_type": "continuous", "value": 0.0, "se": 0.18},
                {"study_id": "N2", "arm_id": "N2C", "outcome_id": "efficacy", "measure_type": "continuous", "value": 2.6, "se": 0.18},
            ],
        },
    }
    cfg_path = tmp_path / "bias-sensitivity-config.json"
    out_path = tmp_path / "bias-sensitivity-result.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "pipelines/run_bias_sensitivity.py",
            "--config",
            str(cfg_path),
            "--out",
            str(out_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "scenarios" in payload
    assert len(payload["scenarios"]) == 4
    assert "summary" in payload
    assert "design_bias_ranges" in payload["summary"]
