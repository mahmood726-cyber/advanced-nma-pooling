from __future__ import annotations

import json

from nma_pool.inference.runner import FitRunner
from nma_pool.reporting.model_card import write_json_report


def test_fit_runner_from_config(tmp_path) -> None:
    payload = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": True,
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

    config_path = tmp_path / "analysis.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    artifacts = FitRunner().run_from_config(config_path)

    assert artifacts.fit.treatment_effects["B"] > 0.5
    assert "inconsistency" in artifacts.model_card
    report_path = tmp_path / "report.json"
    write_json_report(report_path, artifacts.model_card)
    assert report_path.exists()


def test_fit_runner_parses_string_boolean_config_values() -> None:
    payload = {
        "analysis": {
            "outcome_id": "efficacy",
            "measure_type": "continuous",
            "reference_treatment": "A",
            "random_effects": "false",
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

    artifacts = FitRunner().run_from_payload(payload)
    assert artifacts.spec.random_effects is False
    assert artifacts.model_card["analysis"]["random_effects"] is False
