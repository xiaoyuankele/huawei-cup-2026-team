"""Systematic collinearity audit for the Q1 compositional mixture inputs.

This audit separates three effects that are easy to conflate:

1. the exact rank deficiency caused by the simplex closure (the 17 mixture
   columns sum to one after row normalisation);
2. dependence among a full-rank representation of the composition (reference
   coding and Aitchison/ilr coordinates); and
3. the much larger ill-conditioning introduced by a quadratic feature map.

The source attachments are read-only.  Zero replacement is used only for the
clr/ilr sensitivity diagnostic and is never written back to the source data.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import PolynomialFeatures


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-mixture-collinearity-20260924-r01"
PAIRS = {
    "A4_A5_train_1m": ("train_mixture_1m.csv", "fit"),
    "A6_A7_validation_1m": ("test_mixture_1m.csv", "validation"),
    "A8_A9_validation_60m": ("test_mixture_60m.csv", "validation"),
    "A10_A11_validation_1b": ("test_mixture_1B.csv", "validation"),
    "A12_A13_extrapolation_10b": ("est_mixture_10b.csv", "extrapolation"),
    "A14_A15_extrapolation_70b": ("est_mixture_70b.csv", "extrapolation"),
}
ZERO_EPSILONS = (1e-6, 1e-4, 1e-3)


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def read_mixture(filename: str) -> tuple[pd.DataFrame, np.ndarray]:
    frame = pd.read_csv(SOURCE / filename)
    p = frame.drop(columns="index").astype(float)
    sums = p.sum(axis=1).to_numpy()
    if np.any(sums <= 0):
        raise ValueError(f"non-positive mixture row sum in {filename}")
    p = p.div(sums, axis=0)
    return p, sums


def helmert_basis(dimension: int) -> np.ndarray:
    """Return an orthonormal (D-1) x D Helmert contrast basis."""
    basis = np.zeros((dimension - 1, dimension), dtype=float)
    for i in range(1, dimension):
        denominator = np.sqrt(i * (i + 1.0))
        basis[i - 1, :i] = 1.0 / denominator
        basis[i - 1, i] = -i / denominator
    return basis


def zero_replaced_clr(p: np.ndarray, epsilon: float) -> np.ndarray:
    # Multiplicative replacement preserves the relative proportions of the
    # observed non-zero components.  It is still a sensitivity device: a zero
    # may be structural, rounded, or below the reporting resolution.
    replaced = p.copy()
    for row_index in range(len(replaced)):
        zeros = replaced[row_index] == 0.0
        zero_count = int(zeros.sum())
        if zero_count == 0:
            continue
        if zero_count * epsilon >= 1.0:
            raise ValueError("zero replacement mass must be less than one")
        positive = ~zeros
        positive_sum = replaced[row_index, positive].sum()
        replaced[row_index, zeros] = epsilon
        replaced[row_index, positive] *= (1.0 - zero_count * epsilon) / positive_sum
    logs = np.log(replaced)
    return logs - logs.mean(axis=1, keepdims=True)


def correlation_summary(x: np.ndarray, names: list[str]) -> dict:
    corr = np.corrcoef(x, rowvar=False)
    upper = np.triu_indices_from(corr, k=1)
    abs_values = np.abs(corr[upper])
    order = np.argsort(abs_values)[::-1][:5]
    top_pairs = []
    for position in order:
        left = int(upper[0][position])
        right = int(upper[1][position])
        top_pairs.append({
            "left": names[left],
            "right": names[right],
            "correlation": float(corr[left, right]),
            "absolute_correlation": float(abs_values[position]),
        })
    return {
        "max_absolute_correlation": float(np.max(abs_values)) if len(abs_values) else 0.0,
        "median_absolute_correlation": float(np.median(abs_values)) if len(abs_values) else 0.0,
        "pairs_absolute_corr_ge_0_8": int(np.sum(abs_values >= 0.8)),
        "pairs_absolute_corr_ge_0_9": int(np.sum(abs_values >= 0.9)),
        "top_pairs": top_pairs,
        "correlation_matrix": corr.tolist(),
    }


def vif_values(x: np.ndarray, names: list[str]) -> dict:
    """Compute VIF by least-squares auxiliary regressions.

    VIF is reported only for full-rank coordinates.  It is reference-basis
    dependent, so it is paired with the basis name in the output.
    """
    values = {}
    for j, name in enumerate(names):
        y = x[:, j]
        others = np.delete(x, j, axis=1)
        design = np.c_[np.ones(len(x)), others]
        fitted = design @ np.linalg.lstsq(design, y, rcond=None)[0]
        residual = y - fitted
        total = y - y.mean()
        ss_total = float(total @ total)
        ss_resid = float(residual @ residual)
        if ss_total <= 1e-15:
            values[name] = None
            continue
        r2 = max(0.0, min(1.0, 1.0 - ss_resid / ss_total))
        values[name] = float(1.0 / max(1e-15, 1.0 - r2))
    numeric = np.array([v for v in values.values() if v is not None], dtype=float)
    return {
        "values": values,
        "max": float(np.max(numeric)) if len(numeric) else None,
        "median": float(np.median(numeric)) if len(numeric) else None,
        "p95": float(np.quantile(numeric, 0.95)) if len(numeric) else None,
        "count_ge_5": int(np.sum(numeric >= 5.0)),
        "count_ge_10": int(np.sum(numeric >= 10.0)),
    }


def design_diagnostics(x: np.ndarray) -> dict:
    names = [f"x{j + 1}" for j in range(x.shape[1])]
    intercept_design = np.c_[np.ones(len(x)), x]
    centered = x - x.mean(axis=0, keepdims=True)
    scales = centered.std(axis=0, ddof=0)
    positive = scales > 1e-14
    standardized = centered[:, positive] / scales[positive]
    standardized_with_intercept = np.c_[np.ones(len(x)), standardized]
    singular_raw = np.linalg.svd(intercept_design, compute_uv=False)
    singular_standardized = np.linalg.svd(standardized_with_intercept, compute_uv=False)
    predictor_corr = np.corrcoef(x[:, positive], rowvar=False)
    corr_eigenvalues = np.linalg.eigvalsh(predictor_corr)
    result = {
        "rows": int(x.shape[0]),
        "predictor_columns": int(x.shape[1]),
        "constant_predictor_columns": int(np.sum(~positive)),
        "rank_with_intercept": int(np.linalg.matrix_rank(intercept_design)),
        "raw_condition_number_with_intercept": float(np.linalg.cond(intercept_design)),
        "standardized_condition_number_with_intercept": float(np.linalg.cond(standardized_with_intercept)),
        "raw_singular_values": [float(v) for v in singular_raw],
        "standardized_singular_values": [float(v) for v in singular_standardized],
        "predictor_correlation_eigenvalues": [float(v) for v in corr_eigenvalues],
        "predictor_correlation_min_eigenvalue": float(np.min(corr_eigenvalues)),
        "predictor_correlation_condition_number": float(np.linalg.cond(predictor_corr)),
        "correlation": correlation_summary(x[:, positive], [names[i] for i in np.flatnonzero(positive)]),
        "vif": vif_values(x[:, positive], [names[i] for i in np.flatnonzero(positive)]),
    }
    return result


def reference_sensitivity(p: np.ndarray, component_names: list[str]) -> dict:
    """Repeat reference coding for every component to expose basis dependence."""
    rows = []
    for dropped in range(p.shape[1]):
        x = np.delete(p, dropped, axis=1)
        diag = design_diagnostics(x)
        rows.append({
            "dropped_reference": component_names[dropped],
            "rank_with_intercept": diag["rank_with_intercept"],
            "standardized_condition_number_with_intercept": diag["standardized_condition_number_with_intercept"],
            "vif_max": diag["vif"]["max"],
            "vif_p95": diag["vif"]["p95"],
        })
    by_condition = sorted(rows, key=lambda row: row["standardized_condition_number_with_intercept"])
    by_vif = sorted(rows, key=lambda row: row["vif_max"])
    conditions = np.array([row["standardized_condition_number_with_intercept"] for row in rows])
    vifs = np.array([row["vif_max"] for row in rows])
    return {
        "all_references": rows,
        "condition_summary": {
            "min": float(np.min(conditions)),
            "median": float(np.median(conditions)),
            "max": float(np.max(conditions)),
            "best_reference": by_condition[0]["dropped_reference"],
            "worst_reference": by_condition[-1]["dropped_reference"],
        },
        "vif_max_summary": {
            "min": float(np.min(vifs)),
            "median": float(np.median(vifs)),
            "max": float(np.max(vifs)),
            "best_reference": by_vif[0]["dropped_reference"],
            "worst_reference": by_vif[-1]["dropped_reference"],
        },
        "note": "Reference-coded VIF and condition values are coordinate-dependent; the fixed reference in the main audit is reported separately.",
    }


def clr_ilr_diagnostics(p: np.ndarray, component_names: list[str]) -> dict:
    basis = helmert_basis(p.shape[1])
    by_epsilon = {}
    for epsilon in ZERO_EPSILONS:
        clr = zero_replaced_clr(p, epsilon)
        ilr = clr @ basis.T
        names = [f"ilr{j + 1}" for j in range(ilr.shape[1])]
        by_epsilon[str(epsilon)] = {
            "zero_replacement": "multiplicative_replacement",
            "epsilon": epsilon,
            "clr_rank": int(np.linalg.matrix_rank(clr)),
            "ilr_diagnostics": design_diagnostics(ilr),
        }
    return {
        "basis": "orthonormal Helmert ilr basis",
        "component_order": component_names,
        "sensitivity": by_epsilon,
    }


def quadratic_diagnostics(reference_x: np.ndarray) -> dict:
    transformer = PolynomialFeatures(degree=2, include_bias=False)
    quadratic = transformer.fit_transform(reference_x)
    design = np.c_[np.ones(len(quadratic)), quadratic]
    scales = quadratic.std(axis=0, ddof=0)
    positive = scales > 1e-14
    standardized = (quadratic[:, positive] - quadratic[:, positive].mean(axis=0)) / scales[positive]
    standardized_design = np.c_[np.ones(len(quadratic)), standardized]
    return {
        "feature_count_without_intercept": int(quadratic.shape[1]),
        "constant_feature_count": int(np.sum(~positive)),
        "rank_with_intercept": int(np.linalg.matrix_rank(design)),
        "raw_condition_number_with_intercept": float(np.linalg.cond(design)),
        "standardized_condition_number_with_intercept": float(np.linalg.cond(standardized_design)),
        "singular_values": [float(v) for v in np.linalg.svd(design, compute_uv=False)],
    }


def compare_correlations(reference: np.ndarray, other: np.ndarray) -> dict:
    left = np.corrcoef(reference, rowvar=False)
    right = np.corrcoef(other, rowvar=False)
    delta = left - right
    upper = np.triu_indices_from(delta, k=1)
    values = np.abs(delta[upper])
    return {
        "max_absolute_pairwise_correlation_change": float(np.max(values)) if len(values) else 0.0,
        "median_absolute_pairwise_correlation_change": float(np.median(values)) if len(values) else 0.0,
        "frobenius_relative_change": float(np.linalg.norm(delta) / max(np.linalg.norm(left), 1e-15)),
    }


def modeling_gates(dataset_results: dict) -> dict:
    """Translate diagnostics into conservative, reviewable modeling gates."""
    gates = {
        "full_17_component_linear_with_intercept": {
            "status": "BLOCKED",
            "reason": "simplex closure makes the 17 columns plus intercept structurally rank deficient",
        },
        "reference_or_ilr_linear_design": {
            "status": "REVIEW_REQUIRED",
            "reason": "reference-coded VIF/condition values depend on the coordinate basis; retain the all-reference sensitivity",
        },
        "quadratic_design_A4": {
            "status": "REVIEW_REQUIRED",
            "reason": "A4 has 512 rows for 152 quadratic predictors; regularization and nested validation are required",
        },
        "quadratic_design_A10_A15": {
            "status": "BLOCKED_FOR_UNREGULARIZED_EFFECT_ESTIMATION",
            "reason": "64 or 63 rows cannot identify 152 quadratic predictors without strong structural restrictions",
        },
        "p_only_absolute_cross_scale_forecast": {
            "status": "BLOCKED",
            "reason": "A6=A8 and A12=A14 have identical mixture designs but different scale-conditioned Loss targets",
        },
    }
    return gates


def main() -> None:
    loaded = {}
    for label, (filename, role) in PAIRS.items():
        frame, original_sums = read_mixture(filename)
        loaded[label] = {
            "role": role,
            "p": frame.to_numpy(),
            "component_names": list(frame.columns),
            "original_sum_min": float(original_sums.min()),
            "original_sum_max": float(original_sums.max()),
        }

    train = loaded["A4_A5_train_1m"]
    train_p = train["p"]
    train_ref = train_p[:, :-1]
    train_17_design = np.c_[np.ones(len(train_p)), train_p]
    dataset_results = {}
    for label, item in loaded.items():
        p = item["p"]
        reference = p[:, :-1]
        full_design = np.c_[np.ones(len(p)), p]
        reference_result = design_diagnostics(reference)
        clr_result = clr_ilr_diagnostics(p, item["component_names"])
        dataset_results[label] = {
            "role": item["role"],
            "rows": int(len(p)),
            "component_count": int(p.shape[1]),
            "original_row_sum_min": item["original_sum_min"],
            "original_row_sum_max": item["original_sum_max"],
            "normalized_row_sum_max_abs_deviation": float(np.max(np.abs(p.sum(axis=1) - 1.0))),
            "zero_cell_fraction": float(np.mean(p == 0.0)),
            "full_simplex_design": {
                "columns_with_intercept": int(full_design.shape[1]),
                "rank_with_intercept": int(np.linalg.matrix_rank(full_design)),
                "condition_number_with_intercept": float(np.linalg.cond(full_design)),
                "expected_exact_relation": "intercept equals sum of the 17 composition columns after normalization",
            },
            "reference_component": item["component_names"][-1],
            "reference_design": reference_result,
            "reference_sensitivity": reference_sensitivity(p, item["component_names"]),
            "aitchison_ilr": clr_result,
            "quadratic_reference_design": quadratic_diagnostics(reference),
        }

    train_ilr = {}
    for epsilon in ZERO_EPSILONS:
        basis = helmert_basis(train_p.shape[1])
        train_ilr[str(epsilon)] = zero_replaced_clr(train_p, epsilon) @ basis.T
    drift = {}
    for label, item in loaded.items():
        if label == "A4_A5_train_1m":
            continue
        p = item["p"]
        drift[str(label)] = {
            "reference_raw": compare_correlations(train_ref, p[:, :-1]),
            "ilr_by_zero_replacement": {
                str(epsilon): compare_correlations(train_ilr[str(epsilon)], zero_replaced_clr(p, epsilon) @ helmert_basis(p.shape[1]).T)
                for epsilon in ZERO_EPSILONS
            },
        }

    output = {
        "schema_version": "q1.mixture-collinearity.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "fit_rule": "A4/A5 design is the fit reference; A6-A11 validation; A12-A15 extrapolation/sensitivity",
        "zero_replacement_epsilons": list(ZERO_EPSILONS),
        "datasets": dataset_results,
        "design_drift_relative_to_A4": drift,
        "modeling_gates": modeling_gates(dataset_results),
        "all_17_component_design": {
            "columns_with_intercept": int(train_17_design.shape[1]),
            "rank_with_intercept": int(np.linalg.matrix_rank(train_17_design)),
            "note": "The rank loss is structural closure, not evidence that two domains are identical.",
        },
        "interpretation_limits": [
            "Raw Pearson correlations among closed compositions partly reflect the sum-to-one constraint and are descriptive only.",
            "VIF values are basis-dependent; they are reported for the 16-component reference basis and for each orthonormal ilr basis, never for all 17 columns simultaneously.",
            "clr/ilr values depend on zero replacement; the epsilon sensitivity is exploratory because about 45 percent of cells are zero.",
            "A quadratic feature map raises the feature count from 16 to 152 and must be judged using rank, condition number, cross-validation and coefficient stability together.",
            "A6=A8 and A12=A14 are exact mixture-table duplicates, so their design diagnostics are duplicates rather than independent evidence.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
