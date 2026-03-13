"""Model card and run report builders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nma_pool.models.core_ad import NMAFitResult
from nma_pool.models.spec import ModelSpec
from nma_pool.validation.diagnostics import NetworkDiagnostics
from nma_pool.validation.inconsistency import InconsistencyDiagnostics


def build_model_card(
    spec: ModelSpec,
    fit: NMAFitResult,
    diagnostics: NetworkDiagnostics,
    inconsistency: InconsistencyDiagnostics | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "analysis": {
            "outcome_id": spec.outcome_id,
            "measure_type": spec.measure_type,
            "reference_treatment": spec.reference_treatment,
            "random_effects": spec.random_effects,
        },
        "network": {
            "study_count": diagnostics.study_count,
            "treatment_count": diagnostics.treatment_count,
            "contrast_count": diagnostics.contrast_count,
        },
        "fit": {
            "tau": fit.tau,
            "n_studies": fit.n_studies,
            "n_contrasts": fit.n_contrasts,
            "warnings": list(fit.warnings),
            "effects_vs_reference": fit.treatment_effects,
            "ses_vs_reference": fit.treatment_ses,
        },
    }
    if inconsistency is not None:
        payload["inconsistency"] = {
            "flagged": inconsistency.flagged,
            "warnings": list(inconsistency.warnings),
            "global_test": {
                "q_consistency": inconsistency.global_test.q_consistency,
                "q_design": inconsistency.global_test.q_design,
                "q_inconsistency": inconsistency.global_test.q_inconsistency,
                "df": inconsistency.global_test.df,
                "p_value": inconsistency.global_test.p_value,
                "flagged": inconsistency.global_test.flagged,
            },
            "node_splits": [
                {
                    "pair": [row.treatment_lo, row.treatment_hi],
                    "n_direct_studies": row.n_direct_studies,
                    "direct_effect_hi_minus_lo": row.direct_effect_hi_minus_lo,
                    "direct_se": row.direct_se,
                    "indirect_effect_hi_minus_lo": row.indirect_effect_hi_minus_lo,
                    "indirect_se": row.indirect_se,
                    "difference": row.difference,
                    "z_score": row.z_score,
                    "p_value": row.p_value,
                    "flagged": row.flagged,
                }
                for row in inconsistency.node_splits
            ],
        }
    return payload


def write_json_report(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
