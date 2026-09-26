"""Exploratory role-change run for a pooled multi-scale Q1 model.

This run deliberately reclassifies A6/A7 and A8/A9 as adaptation data. It is
not an official validation result and must not replace Track A.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
FEATURE_TABLE = ROOT / "experiments" / "runs" / "q1-scale-feature-table-20260924-r01" / "q1_scale_features_wide.csv"
RUN_ID = "q1-track-c-multiscale-exploratory-20260924-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
EPSILON = 1e-4
ALPHAS = [0.1, 1.0, 10.0, 100.0]
ADAPTATION_DATASETS = ["A4_A5_train_1m", "A6_A7_validation_1m", "A8_A9_validation_60m"]
HOLDOUT_DATASETS = ["A10_A11_validation_1b"]
DIAGNOSTIC_DATASETS = ["A12_A13_extrapolation_10b", "A14_A15_extrapolation_70b"]
PAIRS = {
    "A4_A5_train_1m": "train_pile_loss_1m.csv",
    "A6_A7_validation_1m": "test_pile_loss_1m.csv",
    "A8_A9_validation_60m": "test_pile_loss_60m.csv",
    "A10_A11_validation_1b": "test_pile_loss_1B.csv",
    "A12_A13_extrapolation_10b": "est_pile_loss_10b.csv",
    "A14_A15_extrapolation_70b": "est_pile_loss_70b.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def load_data() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray], list[str], dict]:
    table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in table.columns if column.startswith("p_")]
    basis = helmert_basis(len(p_columns))
    x_by_dataset = {}
    y_by_dataset = {}
    groups_by_dataset = {}
    target_names = None
    source_meta = {}
    for dataset, loss_file in PAIRS.items():
        subset = table[table["dataset"] == dataset].sort_values("index")
        p = subset[p_columns].to_numpy(dtype=float)
        z = zero_replaced_clr(p, EPSILON) @ basis.T
        log_scale = subset["log10_scale"].to_numpy(dtype=float).reshape(-1, 1)
        x_by_dataset[dataset] = np.c_[z, log_scale, z * log_scale]
        loss = pd.read_csv(SOURCE / loss_file).sort_values("index")
        if not np.array_equal(subset["index"].to_numpy(), loss["index"].to_numpy()):
            raise ValueError(f"feature/Loss index mismatch: {dataset}")
        current_targets = [column for column in loss.columns if column != "index"]
        if target_names is None:
            target_names = current_targets
        elif current_targets != target_names:
            raise ValueError(f"target columns differ: {dataset}")
        y_by_dataset[dataset] = loss[current_targets].to_numpy(dtype=float)
        groups_by_dataset[dataset] = np.full(len(loss), subset["scale_label"].iloc[0])
        source_meta[dataset] = {"path": (SOURCE / loss_file).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / loss_file), "rows": int(len(loss))}
    return x_by_dataset, y_by_dataset, groups_by_dataset, target_names or [], source_meta


def evaluate(y: np.ndarray, prediction: np.ndarray) -> dict:
    r2 = [float(r2_score(y[:, j], prediction[:, j])) for j in range(y.shape[1])]
    centered_y = y - y.mean(axis=0, keepdims=True)
    centered_prediction = prediction - prediction.mean(axis=0, keepdims=True)
    centered = [float(r2_score(centered_y[:, j], centered_prediction[:, j])) for j in range(y.shape[1])]
    residual = y - prediction
    return {
        "mean_target_r2": float(np.mean(r2)),
        "per_target_r2": r2,
        "centered_relative_mean_target_r2": float(np.mean(centered)),
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "mean_residual": float(residual.mean()),
        "per_target_mean_residual": [float(v) for v in residual.mean(axis=0)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    x_by, y_by, groups_by, target_names, target_sources = load_data()
    x_adapt = np.vstack([x_by[dataset] for dataset in ADAPTATION_DATASETS])
    y_adapt = np.vstack([y_by[dataset] for dataset in ADAPTATION_DATASETS])
    groups = np.concatenate([groups_by[dataset] for dataset in ADAPTATION_DATASETS])
    logo = LeaveOneGroupOut()
    candidates = []
    for alpha in ALPHAS:
        model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        scores = cross_val_score(model, x_adapt, y_adapt, groups=groups, cv=logo, scoring="r2")
        candidates.append({"alpha": alpha, "leave_one_scale_out_mean_r2": float(scores.mean()), "fold_r2": [float(v) for v in scores]})
    selected = max(candidates, key=lambda row: row["leave_one_scale_out_mean_r2"])
    model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x_adapt, y_adapt)
    evaluations = {}
    prediction_rows = []
    for dataset in ADAPTATION_DATASETS + HOLDOUT_DATASETS + DIAGNOSTIC_DATASETS:
        prediction = model.predict(x_by[dataset])
        role = "adaptation" if dataset in ADAPTATION_DATASETS else ("unseen_scale_holdout" if dataset in HOLDOUT_DATASETS else "extrapolation_diagnostic")
        evaluations[dataset] = {"role": role, **evaluate(y_by[dataset], prediction)}
        subset = pd.read_csv(FEATURE_TABLE)
        indices = subset[subset["dataset"] == dataset].sort_values("index")["index"].to_numpy()
        for row_index, index_value in enumerate(indices):
            record = {"dataset": dataset, "role": role, "index": index_value}
            for target_index, target in enumerate(target_names):
                record[f"actual_{target}"] = float(y_by[dataset][row_index, target_index])
                record[f"predicted_{target}"] = float(prediction[row_index, target_index])
            prediction_rows.append(record)
    prediction_path = output_dir / "predictions.csv"
    pd.DataFrame(prediction_rows).to_csv(prediction_path, index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.track-c-multiscale-exploratory.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "ROLE_CHANGE_EXPLORATORY",
        "role_change": "A6/A7 and A8/A9 are used as adaptation data in this run; they are not official validation after this use.",
        "feature_table": {"path": FEATURE_TABLE.relative_to(ROOT).as_posix(), "sha256": sha256(FEATURE_TABLE)},
        "adaptation_datasets": ADAPTATION_DATASETS,
        "unseen_scale_holdout": HOLDOUT_DATASETS,
        "extrapolation_diagnostics": DIAGNOSTIC_DATASETS,
        "basis": {"name": "Helmert ilr plus log10 scale and interactions", "zero_replacement": "multiplicative", "epsilon": EPSILON},
        "alpha_selection": {"method": "leave_one_scale_out_on_adaptation_scales", "candidates": candidates, "selected": selected},
        "evaluations": evaluations,
        "target_sources": target_sources,
        "prediction_output": {"path": prediction_path.relative_to(ROOT).as_posix(), "sha256": sha256(prediction_path), "rows": int(len(prediction_rows))},
        "limitations": [
            "This is an exploratory role-change run and cannot be compared as an official external-validation result.",
            "Only 1M and 60M are adaptation scales; 1B is the primary unseen-scale holdout.",
            "A12-A15 remain estimated extrapolation diagnostics.",
            "No optimum mixture or causal effect is produced.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
