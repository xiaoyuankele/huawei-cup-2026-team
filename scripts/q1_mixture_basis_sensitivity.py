"""Compare linear Ridge under compositional coordinate bases.

This is a basis-sensitivity experiment, not a final scale model.  A4/A5 is
the only fit pair; A6/A8 are external checks and retain their contract roles.
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
from sklearn.preprocessing import StandardScaler

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-mixture-basis-sensitivity-20260924-r01"
PAIRS = {
    "A4_A5_train_1m": ("train_mixture_1m.csv", "train_pile_loss_1m.csv", "fit"),
    "A6_A7_validation_1m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv", "validation"),
    "A8_A9_validation_60m": ("test_mixture_60m.csv", "test_pile_loss_60m.csv", "validation"),
}
ALPHAS = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]
EPSILONS = [1e-6, 1e-4, 1e-3]


def read_pair(mixture_file: str, loss_file: str) -> tuple[np.ndarray, np.ndarray]:
    mixture = pd.read_csv(SOURCE / mixture_file)
    loss = pd.read_csv(SOURCE / loss_file)
    if not mixture["index"].equals(loss["index"]):
        raise ValueError("index mismatch")
    p = mixture.drop(columns="index").astype(float)
    p = p.div(p.sum(axis=1), axis=0).to_numpy()
    y = loss.drop(columns="index").astype(float).to_numpy()
    return p, y


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def basis_matrix(p: np.ndarray, basis: str) -> np.ndarray:
    if basis == "reference":
        return p[:, :-1]
    epsilon = float(basis.split("=")[-1])
    return zero_replaced_clr(p, epsilon) @ helmert_basis(p.shape[1]).T


def evaluate(model: Pipeline, x: np.ndarray, y: np.ndarray) -> dict:
    prediction = model.predict(x)
    centered_y = y - y.mean(axis=0, keepdims=True)
    centered_prediction = prediction - prediction.mean(axis=0, keepdims=True)
    residual = y - prediction
    absolute_r2 = [r2_score(y[:, j], prediction[:, j]) for j in range(y.shape[1])]
    centered_r2 = [r2_score(centered_y[:, j], centered_prediction[:, j]) for j in range(y.shape[1])]
    spearman = [float(pd.Series(y[:, j]).corr(pd.Series(prediction[:, j]), method="spearman")) for j in range(y.shape[1])]
    return {
        "mean_target_r2": float(np.mean(absolute_r2)),
        "centered_relative_mean_target_r2": float(np.mean(centered_r2)),
        "per_target_r2": [float(v) for v in absolute_r2],
        "per_target_spearman": spearman,
        "per_target_mae": [float(v) for v in np.abs(residual).mean(axis=0)],
        "per_target_rmse": [float(v) for v in np.sqrt((residual ** 2).mean(axis=0))],
        "per_target_mean_residual": [float(v) for v in residual.mean(axis=0)],
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "prediction_mean": float(prediction.mean()),
        "target_mean": float(y.mean()),
    }


def main() -> None:
    pairs = {label: read_pair(mixture, loss) for label, (mixture, loss, _) in PAIRS.items()}
    x_fit_p, y_fit = pairs["A4_A5_train_1m"]
    cv = KFold(n_splits=5, shuffle=True, random_state=20260924)
    bases = ["reference"] + [f"ilr_epsilon={epsilon}" for epsilon in EPSILONS]
    results = {}
    for basis in bases:
        x_fit = basis_matrix(x_fit_p, basis)
        candidates = []
        for alpha in ALPHAS:
            model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
            scores = cross_val_score(model, x_fit, y_fit, cv=cv, scoring="r2")
            candidates.append({"alpha": alpha, "cv_mean_r2": float(scores.mean()), "cv_fold_r2": [float(s) for s in scores]})
        selected = max(candidates, key=lambda row: row["cv_mean_r2"])
        model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x_fit, y_fit)
        evaluations = {}
        for label, (p, y) in pairs.items():
            evaluations[label] = {"role": PAIRS[label][2], **evaluate(model, basis_matrix(p, basis), y)}
        standardized = StandardScaler().fit_transform(x_fit)
        design = np.c_[np.ones(len(standardized)), standardized]
        results[basis] = {
            "selected": selected,
            "feature_count": int(x_fit.shape[1]),
            "standardized_condition_number_with_intercept": float(np.linalg.cond(design)),
            "candidates": candidates,
            "evaluations": evaluations,
        }
    output = {
        "schema_version": "q1.mixture-basis-sensitivity.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "fit_rule": "A4/A5 only; five-fold CV selects alpha; A6/A8 remain external checks",
        "bases": results,
        "limitations": [
            "This compares coordinate and regularization choices; it does not condition on scale.",
            "Aitchison bases use exploratory multiplicative zero replacement.",
            "A8 has the same mixture design as A6 and is not an independent design matrix.",
            "No optimum mixture or causal effect is produced.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
