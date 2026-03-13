from __future__ import annotations


def arm_mean(mu: float, d: float, beta: float, g: float, x: float) -> float:
    return mu + d + (beta * x) + (g * x)


def build_mlnmr_payload() -> dict:
    # True parameters
    d_b = 1.0
    d_c = 2.0
    g_b = 0.4
    g_c = 0.9
    beta = 0.3

    # Study-level baselines
    mu1 = 0.2
    mu2 = -0.1
    mu3 = 0.4
    mu4 = 0.0

    x_a1 = -0.2
    x_b1 = 0.1
    x_c1 = 0.6
    x_a2 = 0.0
    x_b2 = 0.8
    x_a3 = -0.5
    x_c3 = 0.3

    y_a1 = arm_mean(mu1, 0.0, beta, 0.0, x_a1)
    y_b1 = arm_mean(mu1, d_b, beta, g_b, x_b1)
    y_c1 = arm_mean(mu1, d_c, beta, g_c, x_c1)
    y_a2 = arm_mean(mu2, 0.0, beta, 0.0, x_a2)
    y_b2 = arm_mean(mu2, d_b, beta, g_b, x_b2)
    y_a3 = arm_mean(mu3, 0.0, beta, 0.0, x_a3)
    y_c3 = arm_mean(mu3, d_c, beta, g_c, x_c3)

    # IPD study means from deterministic outcomes.
    x_b_vals = [0.0, 0.1, 0.3, 0.4]
    x_c_vals = [0.5, 0.6, 0.8, 0.9]
    y_b_vals = [arm_mean(mu4, d_b, beta, g_b, x) for x in x_b_vals]
    y_c_vals = [arm_mean(mu4, d_c, beta, g_c, x) for x in x_c_vals]

    return {
        "studies": [
            {"study_id": "AD1", "design": "rct", "year": 2024, "source_id": "ad1", "rob_domain_summary": "low"},
            {"study_id": "AD2", "design": "rct", "year": 2024, "source_id": "ad2", "rob_domain_summary": "low"},
            {"study_id": "AD3", "design": "rct", "year": 2024, "source_id": "ad3", "rob_domain_summary": "low"},
            {"study_id": "IP4", "design": "rct", "year": 2024, "source_id": "ip4", "rob_domain_summary": "low"},
        ],
        "arms": [
            {"study_id": "AD1", "arm_id": "A1", "treatment_id": "A", "n": 120},
            {"study_id": "AD1", "arm_id": "A2", "treatment_id": "B", "n": 120},
            {"study_id": "AD1", "arm_id": "A3", "treatment_id": "C", "n": 120},
            {"study_id": "AD2", "arm_id": "B1", "treatment_id": "A", "n": 120},
            {"study_id": "AD2", "arm_id": "B2", "treatment_id": "B", "n": 120},
            {"study_id": "AD3", "arm_id": "C1", "treatment_id": "A", "n": 120},
            {"study_id": "AD3", "arm_id": "C2", "treatment_id": "C", "n": 120},
            {"study_id": "IP4", "arm_id": "D1", "treatment_id": "B", "n": 4},
            {"study_id": "IP4", "arm_id": "D2", "treatment_id": "C", "n": 4},
        ],
        "outcomes_ad": [
            {"study_id": "AD1", "arm_id": "A1", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_a1, "se": 0.12},
            {"study_id": "AD1", "arm_id": "A2", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_b1, "se": 0.12},
            {"study_id": "AD1", "arm_id": "A3", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_c1, "se": 0.12},
            {"study_id": "AD2", "arm_id": "B1", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_a2, "se": 0.12},
            {"study_id": "AD2", "arm_id": "B2", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_b2, "se": 0.12},
            {"study_id": "AD3", "arm_id": "C1", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_a3, "se": 0.12},
            {"study_id": "AD3", "arm_id": "C2", "outcome_id": "efficacy", "measure_type": "continuous", "value": y_c3, "se": 0.12},
        ],
        "ad_covariates": [
            {"study_id": "AD1", "arm_id": "A1", "covariate_name": "x", "mean": x_a1, "sd": 1.0, "n": 120},
            {"study_id": "AD1", "arm_id": "A2", "covariate_name": "x", "mean": x_b1, "sd": 1.0, "n": 120},
            {"study_id": "AD1", "arm_id": "A3", "covariate_name": "x", "mean": x_c1, "sd": 1.0, "n": 120},
            {"study_id": "AD2", "arm_id": "B1", "covariate_name": "x", "mean": x_a2, "sd": 1.0, "n": 120},
            {"study_id": "AD2", "arm_id": "B2", "covariate_name": "x", "mean": x_b2, "sd": 1.0, "n": 120},
            {"study_id": "AD3", "arm_id": "C1", "covariate_name": "x", "mean": x_a3, "sd": 1.0, "n": 120},
            {"study_id": "AD3", "arm_id": "C2", "covariate_name": "x", "mean": x_c3, "sd": 1.0, "n": 120},
        ],
        "ipd": [
            {"study_id": "IP4", "patient_id": "p1", "arm_id": "D1", "treatment_id": "B", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_b_vals[0], "covariates": {"x": x_b_vals[0]}},
            {"study_id": "IP4", "patient_id": "p2", "arm_id": "D1", "treatment_id": "B", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_b_vals[1], "covariates": {"x": x_b_vals[1]}},
            {"study_id": "IP4", "patient_id": "p3", "arm_id": "D1", "treatment_id": "B", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_b_vals[2], "covariates": {"x": x_b_vals[2]}},
            {"study_id": "IP4", "patient_id": "p4", "arm_id": "D1", "treatment_id": "B", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_b_vals[3], "covariates": {"x": x_b_vals[3]}},
            {"study_id": "IP4", "patient_id": "p5", "arm_id": "D2", "treatment_id": "C", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_c_vals[0], "covariates": {"x": x_c_vals[0]}},
            {"study_id": "IP4", "patient_id": "p6", "arm_id": "D2", "treatment_id": "C", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_c_vals[1], "covariates": {"x": x_c_vals[1]}},
            {"study_id": "IP4", "patient_id": "p7", "arm_id": "D2", "treatment_id": "C", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_c_vals[2], "covariates": {"x": x_c_vals[2]}},
            {"study_id": "IP4", "patient_id": "p8", "arm_id": "D2", "treatment_id": "C", "outcome_id": "efficacy", "measure_type": "continuous", "outcome_value": y_c_vals[3], "covariates": {"x": x_c_vals[3]}},
        ],
    }

