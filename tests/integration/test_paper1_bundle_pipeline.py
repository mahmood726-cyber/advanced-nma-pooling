from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_paper1_bundle_pipeline_writes_manifest_and_summary(tmp_path: Path) -> None:
    publication_cfg = {
        "thresholds": {
            "coverage_lo": 0.80,
            "coverage_hi": 1.00,
            "bias_improvement_min": 0.0,
            "logscore_win_rate_min": 0.0,
        },
        "continuous": {
            "n_networks": 8,
            "seed_start": 101,
            "n_per_arm": 100,
            "se": 0.25,
            "noise_sd": 0.25,
            "study_heterogeneity_sd": 0.0,
        },
        "survival_nonph": {
            "n_networks": 6,
            "seed_start": 303,
            "n_per_arm": 320,
            "replicates_per_pair": 2,
            "follow_up_fraction": 0.85,
        },
        "continuity_correction": 0.5,
    }
    pub_path = tmp_path / "publication.json"
    pub_path.write_text(json.dumps(publication_cfg), encoding="utf-8")

    small_bias_data = {
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
    }

    bias_cfg = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": False,
            "reference_design": "rct",
            "bias_prior_sd": 1.0,
        },
        "data": small_bias_data,
    }
    bias_cfg_path = tmp_path / "bias.json"
    bias_cfg_path.write_text(json.dumps(bias_cfg), encoding="utf-8")

    bias_bayes_cfg = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": True,
            "reference_design": "rct",
            "bias_prior_sd": 1.0,
            "backend": "analytic",
            "treatment_prior_sd": 10.0,
            "n_draws": 800,
            "n_warmup": 300,
            "n_chains": 2,
            "seed": 17,
        },
        "data": small_bias_data,
    }
    bias_bayes_path = tmp_path / "bias-bayes.json"
    bias_bayes_path.write_text(json.dumps(bias_bayes_cfg), encoding="utf-8")

    sensitivity_cfg = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": True,
            "reference_design": "rct",
            "backend": "analytic",
        },
        "sensitivity": {
            "backend": "analytic",
            "bias_prior_sd_grid": [0.5, 1.5],
            "treatment_prior_sd_grid": [5.0],
            "seed_grid": [7],
            "n_draws": 600,
            "n_warmup": 250,
            "n_chains": 2,
        },
        "data": small_bias_data,
    }
    sensitivity_path = tmp_path / "sensitivity.json"
    sensitivity_path.write_text(json.dumps(sensitivity_cfg), encoding="utf-8")

    bundle_cfg = {
        "bundle": {
            "name": "paper1-test",
            "run_publication_suite": True,
            "run_bias_adjusted": True,
            "run_bias_adjusted_bayesian": True,
            "run_bias_sensitivity": True,
        },
        "paths": {
            "publication_config": str(pub_path),
            "bias_adjusted_config": str(bias_cfg_path),
            "bias_adjusted_bayesian_config": str(bias_bayes_path),
            "bias_sensitivity_config": str(sensitivity_path),
        },
        "docs": {
            "copy": [],
        },
    }
    bundle_cfg_path = tmp_path / "bundle.json"
    bundle_cfg_path.write_text(json.dumps(bundle_cfg), encoding="utf-8")

    out_dir = tmp_path / "paper1"
    proc = subprocess.run(
        [
            sys.executable,
            "pipelines/run_paper1_bundle.py",
            "--config",
            str(bundle_cfg_path),
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    manifest_path = out_dir / "manifest.json"
    summary_path = out_dir / "paper1-executive-summary.md"
    assert manifest_path.exists()
    assert summary_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    step_names = {row["name"] for row in manifest["steps"]}
    assert "publication_suite" in step_names
    assert "bias_adjusted" in step_names
    assert "bias_adjusted_bayesian" in step_names
    assert "bias_sensitivity" in step_names
    for step in manifest["steps"]:
        assert step["command"][:3] == [sys.executable, "-m", "nma_pool.cli"]


def test_paper1_bundle_pipeline_parses_string_false_step_flags(tmp_path: Path) -> None:
    bundle_cfg_path = tmp_path / "bundle.json"
    bundle_cfg_path.write_text(
        json.dumps(
            {
                "bundle": {
                    "name": "paper1-test",
                    "run_publication_suite": "false",
                    "run_bias_adjusted": "false",
                    "run_bias_adjusted_bayesian": "false",
                    "run_bias_sensitivity": "false",
                },
                "docs": {
                    "copy": [],
                },
            }
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "paper1"
    proc = subprocess.run(
        [
            sys.executable,
            "pipelines/run_paper1_bundle.py",
            "--config",
            str(bundle_cfg_path),
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["steps"] == []
