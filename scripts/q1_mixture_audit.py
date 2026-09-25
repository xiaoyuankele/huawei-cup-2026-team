"""Audit the Q1 mixture/Loss tables without modifying source attachments.

This is a data-contract and baseline audit, not the final mixture model.  It
keeps the training pair A4/A5 separate from the real validation pairs A6/A11
and from the estimated extrapolation pairs A12/A15.  The baseline is included
only to expose scale leakage and to prevent unverified fit statistics from
entering the paper.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"

PAIRS = {
    "A4_A5_train_1m": ("train_mixture_1m.csv", "train_pile_loss_1m.csv", "fit"),
    "A6_A7_validation_1m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv", "validation"),
    "A8_A9_validation_60m": ("test_mixture_60m.csv", "test_pile_loss_60m.csv", "validation"),
    "A10_A11_validation_1b": ("test_mixture_1B.csv", "test_pile_loss_1B.csv", "validation"),
    "A12_A13_extrapolation_10b": ("est_mixture_10b.csv", "est_pile_loss_10b.csv", "extrapolation"),
    "A14_A15_extrapolation_70b": ("est_mixture_70b.csv", "est_pile_loss_70b.csv", "extrapolation"),
}


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def read_pair(mixture_name: str, loss_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    mixture = pd.read_csv(SOURCE / mixture_name)
    loss = pd.read_csv(SOURCE / loss_name)
    if not mixture["index"].equals(loss["index"]):
        raise ValueError(f"index order mismatch: {mixture_name} vs {loss_name}")
    if mixture["index"].duplicated().any() or loss["index"].duplicated().any():
        raise ValueError(f"duplicate index: {mixture_name} or {loss_name}")
    return mixture, loss


def summarize_pair(mixture: pd.DataFrame, loss: pd.DataFrame, role: str) -> dict:
    p = mixture.drop(columns="index").astype(float)
    y = loss.drop(columns="index").astype(float)
    sums = p.sum(axis=1)
    nonzero_counts = (p > 0).sum(axis=1)
    return {
        "role": role,
        "rows": int(len(p)),
        "mixture_columns": list(p.columns),
        "loss_columns": list(y.columns),
        "loss_target_count": int(y.shape[1]),
        "mixture_sum_min": float(sums.min()),
        "mixture_sum_max": float(sums.max()),
        "mixture_sum_max_abs_deviation": float(np.abs(sums - 1.0).max()),
        "zero_cell_fraction": float((p == 0).to_numpy().mean()),
        "nonzero_components_min": int(nonzero_counts.min()),
        "nonzero_components_median": float(nonzero_counts.median()),
        "nonzero_components_max": int(nonzero_counts.max()),
        "loss_mean": float(y.to_numpy().mean()),
        "loss_min": float(y.to_numpy().min()),
        "loss_max": float(y.to_numpy().max()),
    }


def normalized_features(mixture: pd.DataFrame) -> pd.DataFrame:
    p = mixture.drop(columns="index").astype(float)
    sums = p.sum(axis=1)
    if (sums <= 0).any():
        raise ValueError("non-positive mixture row sum")
    # The final component is omitted because the simplex makes it redundant.
    # Row normalization removes only the documented per-mille rounding error.
    return p.div(sums, axis=0).iloc[:, :-1]


def fit_baseline(train_mixture: pd.DataFrame, train_loss: pd.DataFrame, pairs: dict) -> dict:
    x_train = normalized_features(train_mixture)
    y_train = train_loss.drop(columns="index").astype(float)
    train_target_mean = y_train.mean(axis=0)
    model = LinearRegression().fit(x_train, y_train)
    relative_model = LinearRegression().fit(x_train, y_train - train_target_mean)
    design = np.c_[np.ones(len(x_train)), x_train.to_numpy()]
    singular_values = np.linalg.svd(design, compute_uv=False)
    result = {
        "feature_rule": "row_normalize_then_drop_last_simplex_component",
        "design_diagnostics": {
            "rows": int(design.shape[0]),
            "columns_with_intercept": int(design.shape[1]),
            "rank": int(np.linalg.matrix_rank(design)),
            "condition_number": float(np.linalg.cond(design)),
            "singular_values": [float(value) for value in singular_values],
        },
        "datasets": {},
    }
    for label, (mixture_name, loss_name, role) in pairs.items():
        mixture, loss = read_pair(mixture_name, loss_name)
        x = normalized_features(mixture)
        y = loss.drop(columns="index").astype(float)
        prediction = model.predict(x)
        relative_prediction = relative_model.predict(x)
        per_target_r2 = [float(r2_score(y.iloc[:, j], prediction[:, j])) for j in range(y.shape[1])]
        centered_y = y - y.mean(axis=0)
        centered_r2 = [float(r2_score(centered_y.iloc[:, j], relative_prediction[:, j])) for j in range(y.shape[1])]
        centered_spearman = [
            float(pd.Series(centered_y.iloc[:, j]).corr(pd.Series(relative_prediction[:, j]), method="spearman"))
            for j in range(y.shape[1])
        ]
        result["datasets"][label] = {
            "role": role,
            "mean_target_r2": float(np.mean(per_target_r2)),
            "median_target_r2": float(np.median(per_target_r2)),
            "min_target_r2": float(np.min(per_target_r2)),
            "max_target_r2": float(np.max(per_target_r2)),
            "mae": float(mean_absolute_error(y, prediction)),
            "rmse": float(mean_squared_error(y, prediction) ** 0.5),
            "per_target_r2": per_target_r2,
            "centered_relative_mean_target_r2": float(np.mean(centered_r2)),
            "centered_relative_mean_spearman": float(np.nanmean(centered_spearman)),
            "centered_relative_per_target_r2": centered_r2,
        }
    return result


def support_diagnostics(train_mixture: pd.DataFrame, mixture: pd.DataFrame) -> dict:
    train = train_mixture.drop(columns="index").astype(float)
    current = mixture.drop(columns="index").astype(float)
    train = train.div(train.sum(axis=1), axis=0).iloc[:, :-1]
    current = current.div(current.sum(axis=1), axis=0).iloc[:, :-1]
    mins = train.min(axis=0)
    maxs = train.max(axis=0)
    violations = (current.lt(mins, axis=1) | current.gt(maxs, axis=1)).any(axis=1)
    scale = train.std(axis=0).replace(0, 1.0)
    train_scaled = train.div(scale, axis=1).to_numpy()
    current_scaled = current.div(scale, axis=1).to_numpy()
    # A nearest observed-design distance is a conservative support diagnostic;
    # it is not a convex-hull membership test.
    nearest = []
    for row in current_scaled:
        nearest.append(float(np.sqrt(((train_scaled - row) ** 2).sum(axis=1)).min()))
    return {
        "coordinate_range_violation_rate": float(violations.mean()),
        "nearest_train_distance_mean": float(np.mean(nearest)),
        "nearest_train_distance_p95": float(np.quantile(nearest, 0.95)),
        "nearest_train_distance_max": float(np.max(nearest)),
        "note": "Nearest distance is a screening diagnostic, not a convex-hull test.",
    }


def main() -> None:
    summaries = {}
    loaded = {}
    for label, (mixture_name, loss_name, role) in PAIRS.items():
        mixture, loss = read_pair(mixture_name, loss_name)
        loaded[label] = (mixture, loss)
        summaries[label] = summarize_pair(mixture, loss, role)

    mixture_duplicates = {}
    scale_shift_diagnostics = {}
    labels = list(loaded)
    for left_index, left in enumerate(labels):
        left_mixture = loaded[left][0].drop(columns="index").to_numpy()
        for right in labels[left_index + 1 :]:
            right_mixture = loaded[right][0].drop(columns="index").to_numpy()
            if left_mixture.shape == right_mixture.shape and np.array_equal(left_mixture, right_mixture):
                mixture_duplicates[f"{left}__{right}"] = True
                left_loss = loaded[left][1].drop(columns="index").astype(float)
                right_loss = loaded[right][1].drop(columns="index").astype(float)
                delta = left_loss.to_numpy() - right_loss.to_numpy()
                scale_shift_diagnostics[f"{left}__{right}"] = {
                    "mean_loss_left": float(left_loss.to_numpy().mean()),
                    "mean_loss_right": float(right_loss.to_numpy().mean()),
                    "mean_delta_left_minus_right": float(delta.mean()),
                    "min_delta_left_minus_right": float(delta.min()),
                    "max_delta_left_minus_right": float(delta.max()),
                    "per_target_mean_delta_left_minus_right": [
                        float(value) for value in delta.mean(axis=0)
                    ],
                }

    train_mixture, train_loss = loaded["A4_A5_train_1m"]
    baseline = fit_baseline(train_mixture, train_loss, PAIRS)
    support = {
        label: support_diagnostics(train_mixture, mixture)
        for label, (mixture, _) in loaded.items()
    }
    output = {
        "schema_version": "q1.mixture-audit.v1",
        "git_commit": git_commit(),
        "source_root": "data/origin/real_attachments/A_data_value/regmix_tables",
        "fit_rule": "A4/A5 only; A6-A11 validation; A12-A15 extrapolation/sensitivity only",
        "summaries": summaries,
        "exact_mixture_duplicates": mixture_duplicates,
        "scale_shift_diagnostics": scale_shift_diagnostics,
        "support_diagnostics_relative_to_A4": support,
        "baseline": baseline,
        "interpretation_limits": [
            "The 17 mixture columns are compositional; coefficients are substitution effects after choosing a reference component.",
            "A6=A8 and A12=A14 mixture matrices are exact duplicates but have different scale-conditioned Loss values.",
            "Centered relative metrics remove each dataset-target mean only as a diagnostic of composition ranking; they are not absolute Loss forecasts.",
            "A12-A15 are estimated extrapolation tables and are not independent validation observations.",
            "The baseline is an audit only and must not be reported as the final domain model.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
