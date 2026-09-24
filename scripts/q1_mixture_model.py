"""Exploratory, scale-audited Q1 mixture model.

The model is deliberately limited to the p-only contract.  A4/A5 is the only
fit pair; model selection uses an internal split of A4/A5.  A6-A11 remain
external validation and A12-A15 remain extrapolation scenarios.  The output is
evidence for review, not a paper-ready optimum or causal claim.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-mixture-model-20260924-r01"
PAIRS = {
    "A4_A5_train_1m": ("train_mixture_1m.csv", "train_pile_loss_1m.csv", "fit"),
    "A6_A7_validation_1m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv", "validation"),
    "A8_A9_validation_60m": ("test_mixture_60m.csv", "test_pile_loss_60m.csv", "validation"),
    "A10_A11_validation_1b": ("test_mixture_1B.csv", "test_pile_loss_1B.csv", "validation"),
    "A12_A13_extrapolation_10b": ("est_mixture_10b.csv", "est_pile_loss_10b.csv", "extrapolation"),
    "A14_A15_extrapolation_70b": ("est_mixture_70b.csv", "est_pile_loss_70b.csv", "extrapolation"),
}


def read_pair(mixture_name: str, loss_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    mixture = pd.read_csv(SOURCE / mixture_name)
    loss = pd.read_csv(SOURCE / loss_name)
    if not mixture["index"].equals(loss["index"]):
        raise ValueError(f"index order mismatch: {mixture_name} vs {loss_name}")
    p = mixture.drop(columns="index").astype(float)
    p = p.div(p.sum(axis=1), axis=0).iloc[:, :-1]
    y = loss.drop(columns="index").astype(float)
    return p, y


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def model(kind: str, alpha: float) -> Pipeline:
    if kind == "linear_ridge":
        return Pipeline([("ridge", Ridge(alpha=alpha))])
    if kind == "quadratic_ridge":
        return Pipeline(
            [
                ("polynomial", PolynomialFeatures(degree=2, include_bias=False)),
                ("ridge", Ridge(alpha=alpha)),
            ]
        )
    raise ValueError(kind)


def evaluate(estimator: Pipeline, x: pd.DataFrame, y: pd.DataFrame) -> dict:
    prediction = estimator.predict(x)
    y_array = y.to_numpy()
    centered_y = y_array - y_array.mean(axis=0, keepdims=True)
    centered_prediction = prediction - prediction.mean(axis=0, keepdims=True)
    absolute_r2 = [float(r2_score(y_array[:, j], prediction[:, j])) for j in range(y_array.shape[1])]
    relative_r2 = [
        float(r2_score(centered_y[:, j], centered_prediction[:, j])) for j in range(y_array.shape[1])
    ]
    relative_spearman = [
        float(pd.Series(centered_y[:, j]).corr(pd.Series(centered_prediction[:, j]), method="spearman"))
        for j in range(y_array.shape[1])
    ]
    return {
        "mean_target_r2": float(np.mean(absolute_r2)),
        "median_target_r2": float(np.median(absolute_r2)),
        "mae": float(mean_absolute_error(y_array, prediction)),
        "rmse": float(mean_squared_error(y_array, prediction) ** 0.5),
        "centered_relative_mean_target_r2": float(np.mean(relative_r2)),
        "centered_relative_mean_spearman": float(np.nanmean(relative_spearman)),
        "per_target_r2": absolute_r2,
        "centered_relative_per_target_r2": relative_r2,
    }


def main() -> None:
    pairs = {label: read_pair(mixture, loss) for label, (mixture, loss, _) in PAIRS.items()}
    x_fit, y_fit = pairs["A4_A5_train_1m"]
    cv = KFold(n_splits=5, shuffle=True, random_state=20260924)
    candidates = []
    for kind, alphas in {
        "linear_ridge": [0.001, 0.01, 0.1, 1.0],
        "quadratic_ridge": [0.0001, 0.001, 0.01, 0.1, 1.0],
    }.items():
        for alpha in alphas:
            estimator = model(kind, alpha)
            scores = cross_val_score(estimator, x_fit, y_fit, cv=cv, scoring="r2")
            candidates.append(
                {
                    "kind": kind,
                    "alpha": alpha,
                    "cv_mean_r2": float(scores.mean()),
                    "cv_fold_r2": [float(score) for score in scores],
                }
            )
    selected = max(candidates, key=lambda row: row["cv_mean_r2"])
    estimator = model(selected["kind"], selected["alpha"]).fit(x_fit, y_fit)
    selected_features = estimator.named_steps.get("polynomial", None)
    design = selected_features.transform(x_fit) if selected_features is not None else x_fit.to_numpy()
    design_with_intercept = np.c_[np.ones(len(design)), design]
    evaluations = {}
    for label, (x, y) in pairs.items():
        evaluations[label] = {"role": PAIRS[label][2], **evaluate(estimator, x, y)}

    output = {
        "schema_version": "q1.mixture-model.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "needs_human_review": True,
        "fit_rule": "A4/A5 only; internal five-fold CV for model selection",
        "selected_model": selected,
        "selected_design_diagnostics": {
            "feature_count_without_intercept": int(design.shape[1]),
            "rank_with_intercept": int(np.linalg.matrix_rank(design_with_intercept)),
            "condition_number_with_intercept": float(np.linalg.cond(design_with_intercept)),
        },
        "candidates": candidates,
        "evaluations": evaluations,
        "limitations": [
            "No quality score Q is included; its domain mapping and scale are not frozen.",
            "Absolute cross-scale predictions are reported but must not be interpreted as scale-invariant.",
            "Centered relative metrics remove each dataset-target mean only for composition-shape diagnostics.",
            "A12-A15 are estimated extrapolation scenarios, not independent validation data.",
            "No optimum mixture, causal effect or paper claim is produced by this run.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
