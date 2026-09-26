"""Run the strict-track-A same-scale Q1 mixture experiment.

Fit uses A4/A5 only. A6/A7 are the same-scale external validation pair.
A8-A15 are reported only as post-fit scale diagnostics and never influence
alpha selection or fitting.
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
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
FEATURE_TABLE = ROOT / "experiments" / "runs" / "q1-scale-feature-table-20260924-r01" / "q1_scale_features_wide.csv"
RUN_ID = "q1-track-a-same-scale-20260924-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
EPSILON = 1e-4
ALPHAS = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]

PAIRS = {
    "A4_A5_train_1m": ("train_pile_loss_1m.csv", "fit"),
    "A6_A7_validation_1m": ("test_pile_loss_1m.csv", "same_scale_validation"),
    "A8_A9_validation_60m": ("test_pile_loss_60m.csv", "cross_scale_diagnostic"),
    "A10_A11_validation_1b": ("test_pile_loss_1B.csv", "cross_scale_diagnostic"),
    "A12_A13_extrapolation_10b": ("est_pile_loss_10b.csv", "extrapolation_diagnostic"),
    "A14_A15_extrapolation_70b": ("est_pile_loss_70b.csv", "extrapolation_diagnostic"),
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


def load_features() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], list[str]]:
    table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in table.columns if column.startswith("p_")]
    p_by_dataset = {}
    index_by_dataset = {}
    for dataset in PAIRS:
        subset = table[table["dataset"] == dataset].copy().sort_values("index")
        p_by_dataset[dataset] = subset[p_columns].to_numpy(dtype=float)
        index_by_dataset[dataset] = subset["index"].to_numpy()
    return p_by_dataset, index_by_dataset, [column[2:] for column in p_columns]


def load_targets(index_by_dataset: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], list[str], dict]:
    targets = {}
    source_meta = {}
    target_names = None
    for dataset, (loss_file, _) in PAIRS.items():
        frame = pd.read_csv(SOURCE / loss_file).sort_values("index")
        if not np.array_equal(frame["index"].to_numpy(), index_by_dataset[dataset]):
            raise ValueError(f"feature/Loss index mismatch: {dataset}")
        current_names = [column for column in frame.columns if column != "index"]
        if target_names is None:
            target_names = current_names
        elif current_names != target_names:
            raise ValueError(f"target columns differ: {dataset}")
        targets[dataset] = frame[current_names].to_numpy(dtype=float)
        source_path = SOURCE / loss_file
        source_meta[dataset] = {"relative_path": source_path.relative_to(ROOT).as_posix(), "sha256": sha256(source_path), "rows": int(len(frame))}
    return targets, target_names or [], source_meta


def metrics(y: np.ndarray, prediction: np.ndarray) -> dict:
    residual = y - prediction
    absolute_r2 = [float(r2_score(y[:, j], prediction[:, j])) for j in range(y.shape[1])]
    centered_y = y - y.mean(axis=0, keepdims=True)
    centered_prediction = prediction - prediction.mean(axis=0, keepdims=True)
    centered_r2 = [float(r2_score(centered_y[:, j], centered_prediction[:, j])) for j in range(y.shape[1])]
    spearman = [float(pd.Series(y[:, j]).corr(pd.Series(prediction[:, j]), method="spearman")) for j in range(y.shape[1])]
    return {
        "mean_target_r2": float(np.mean(absolute_r2)),
        "per_target_r2": absolute_r2,
        "centered_relative_mean_target_r2": float(np.mean(centered_r2)),
        "per_target_centered_relative_r2": centered_r2,
        "mean_target_spearman": float(np.nanmean(spearman)),
        "per_target_spearman": spearman,
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "per_target_mae": [float(v) for v in np.abs(residual).mean(axis=0)],
        "per_target_rmse": [float(v) for v in np.sqrt((residual ** 2).mean(axis=0))],
        "per_target_mean_residual": [float(v) for v in residual.mean(axis=0)],
        "prediction_mean": float(prediction.mean()),
        "target_mean": float(y.mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    p_by_dataset, index_by_dataset, component_names = load_features()
    targets, target_names, target_sources = load_targets(index_by_dataset)
    basis = helmert_basis(len(component_names))
    z_by_dataset = {dataset: zero_replaced_clr(p, EPSILON) @ basis.T for dataset, p in p_by_dataset.items()}
    x_fit = z_by_dataset["A4_A5_train_1m"]
    y_fit = targets["A4_A5_train_1m"]
    cv = KFold(n_splits=5, shuffle=True, random_state=20260924)
    candidates = []
    for alpha in ALPHAS:
        estimator = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        scores = cross_val_score(estimator, x_fit, y_fit, cv=cv, scoring="r2")
        candidates.append({"alpha": alpha, "cv_mean_r2": float(scores.mean()), "cv_fold_r2": [float(v) for v in scores]})
    selected = max(candidates, key=lambda row: row["cv_mean_r2"])
    estimator = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x_fit, y_fit)
    evaluations = {}
    prediction_rows = []
    for dataset, (_, role) in PAIRS.items():
        prediction = estimator.predict(z_by_dataset[dataset])
        evaluations[dataset] = {"role": role, **metrics(targets[dataset], prediction)}
        for row_index, index_value in enumerate(index_by_dataset[dataset]):
            record = {"dataset": dataset, "role": role, "index": index_value}
            for target_index, target in enumerate(target_names):
                record[f"actual_{target}"] = float(targets[dataset][row_index, target_index])
                record[f"predicted_{target}"] = float(prediction[row_index, target_index])
            prediction_rows.append(record)
    prediction_path = output_dir / "predictions.csv"
    pd.DataFrame(prediction_rows).to_csv(prediction_path, index=False, encoding="utf-8-sig")
    design = np.c_[np.ones(len(x_fit)), StandardScaler().fit_transform(x_fit)]
    output = {
        "schema_version": "q1.track-a-same-scale.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "EXPERIMENTAL_REVIEW",
        "fit_rule": "A4/A5 only; alpha selected by five-fold CV on A4/A5",
        "same_scale_validation": "A6/A7",
        "cross_scale_usage": "A8-A15 post-fit scale diagnostics only; no model selection or fitting",
        "input_feature_table": {"path": FEATURE_TABLE.relative_to(ROOT).as_posix(), "sha256": sha256(FEATURE_TABLE)},
        "target_sources": target_sources,
        "basis": {"name": "Helmert ilr", "zero_replacement": "multiplicative", "epsilon": EPSILON, "component_names": component_names},
        "selected_model": selected,
        "candidate_alphas": candidates,
        "design_diagnostics": {
            "predictor_count": int(x_fit.shape[1]),
            "rank_with_intercept": int(np.linalg.matrix_rank(design)),
            "standardized_condition_number_with_intercept": float(np.linalg.cond(design)),
        },
        "evaluations": evaluations,
        "prediction_output": {"path": prediction_path.relative_to(ROOT).as_posix(), "sha256": sha256(prediction_path), "rows": int(len(prediction_rows))},
        "limitations": [
            "This is a same-scale candidate experiment, not a final accepted model.",
            "Scale-conditioned parameters are not estimated in this track.",
            "A8-A15 metrics are diagnostic and cannot be reported as scale-generalization success.",
            "No optimum mixture or causal domain-effect claim is produced.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
