"""Unified exploratory benchmark for Q1 domain-mixture models.

The run compares a small, pre-specified model family under one composition
representation and one A4/A5-only model-selection protocol. A6/A7 are held
out for same-scale external validation; A8-A15 are diagnostics only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.cross_decomposition import PLSRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.model_selection import KFold

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
FEATURE_TABLE = ROOT / "experiments" / "runs" / "q1-scale-feature-table-20260924-r01" / "q1_scale_features_wide.csv"
RUN_ID = "q1-model-benchmark-20260924-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
EPSILON = 1e-4

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
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def load_data() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], list[str], list[str]]:
    feature_table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in feature_table.columns if column.startswith("p_")]
    x_by_dataset: dict[str, np.ndarray] = {}
    index_by_dataset: dict[str, np.ndarray] = {}
    y_by_dataset: dict[str, np.ndarray] = {}
    target_names: list[str] | None = None
    for dataset, (loss_file, _) in PAIRS.items():
        subset = feature_table[feature_table["dataset"] == dataset].sort_values("index")
        if subset.empty:
            raise ValueError(f"Missing feature rows for {dataset}")
        indices = subset["index"].to_numpy()
        loss = pd.read_csv(SOURCE / loss_file).sort_values("index")
        if not np.array_equal(indices, loss["index"].to_numpy()):
            raise ValueError(f"Index mismatch for {dataset}")
        if target_names is None:
            target_names = [column for column in loss.columns if column != "index"]
        current_targets = [column for column in loss.columns if column != "index"]
        if current_targets != target_names:
            raise ValueError(f"Target columns differ for {dataset}")
        x_by_dataset[dataset] = subset[p_columns].to_numpy(dtype=float)
        index_by_dataset[dataset] = indices
        y_by_dataset[dataset] = loss[target_names].to_numpy(dtype=float)
    return x_by_dataset, y_by_dataset, [column[2:] for column in p_columns], target_names or []


def metrics(y: np.ndarray, prediction: np.ndarray) -> dict[str, object]:
    residual = y - prediction
    r2 = []
    centered_r2 = []
    mae = []
    rmse = []
    spearman = []
    centered_spearman = []
    for j in range(y.shape[1]):
        yj = y[:, j]
        pj = prediction[:, j]
        denominator = float(np.sum((yj - yj.mean()) ** 2))
        r2.append(float(1.0 - np.sum((yj - pj) ** 2) / denominator) if denominator > 0 else float("nan"))
        centered_yj = yj - yj.mean()
        centered_pj = pj - pj.mean()
        centered_denominator = float(np.sum(centered_yj ** 2))
        centered_r2.append(
            float(1.0 - np.sum((centered_yj - centered_pj) ** 2) / centered_denominator)
            if centered_denominator > 0 else float("nan")
        )
        mae.append(float(np.mean(np.abs(yj - pj))))
        rmse.append(float(np.sqrt(np.mean((yj - pj) ** 2))))
        if np.allclose(yj, yj[0]) or np.allclose(pj, pj[0]):
            spearman.append(None)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                spearman.append(float(pd.Series(yj).corr(pd.Series(pj), method="spearman")))
        if np.allclose(centered_yj, centered_yj[0]) or np.allclose(centered_pj, centered_pj[0]):
            centered_spearman.append(None)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                centered_spearman.append(float(pd.Series(centered_yj).corr(pd.Series(centered_pj), method="spearman")))
    finite_spearman = [v for v in spearman if v is not None and np.isfinite(v)]
    finite_centered_spearman = [v for v in centered_spearman if v is not None and np.isfinite(v)]
    return {
        "mean_target_r2": float(np.nanmean(r2)),
        "median_target_r2": float(np.nanmedian(r2)),
        "centered_relative_mean_target_r2": float(np.nanmean(centered_r2)),
        "mean_target_spearman": float(np.mean(finite_spearman)) if finite_spearman else None,
        "centered_relative_mean_spearman": float(np.mean(finite_centered_spearman)) if finite_centered_spearman else None,
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "per_target_r2": r2,
        "per_target_centered_relative_r2": centered_r2,
        "per_target_mae": mae,
        "per_target_rmse": rmse,
        "per_target_spearman": spearman,
        "per_target_centered_relative_spearman": centered_spearman,
        "per_target_mean_residual": [float(v) for v in residual.mean(axis=0)],
    }


def make_model(name: str, parameter: float | int | None):
    if name == "mean_baseline":
        return DummyRegressor(strategy="mean")
    if name == "ilr_ols":
        return Pipeline([("scale", StandardScaler()), ("ols", LinearRegression())])
    if name == "ilr_ridge":
        return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=float(parameter)))])
    if name == "pls":
        return PLSRegression(n_components=int(parameter), scale=True, max_iter=2000, tol=1e-6)
    if name == "quadratic_ridge":
        return Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=float(parameter))),
        ])
    if name == "shallow_gbdt":
        base = GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.03, max_depth=2,
            min_samples_leaf=10, random_state=20260924,
        )
        return MultiOutputRegressor(base)
    raise ValueError(name)


MODEL_GRID: dict[str, list[float | int | None]] = {
    "mean_baseline": [None],
    "ilr_ols": [None],
    "ilr_ridge": [0.01, 0.1, 1.0, 10.0, 100.0],
    "pls": [1, 2, 4, 6, 8],
    "quadratic_ridge": [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0],
    "shallow_gbdt": [None],
}


def cv_rows(name: str, parameter: float | int | None, x: np.ndarray, y: np.ndarray, seeds: list[int]) -> list[dict]:
    rows: list[dict] = []
    for seed in seeds:
        splitter = KFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, valid_idx) in enumerate(splitter.split(x), start=1):
            estimator = make_model(name, parameter)
            estimator.fit(x[train_idx], y[train_idx])
            prediction = estimator.predict(x[valid_idx])
            row = metrics(y[valid_idx], prediction)
            rows.append({
                "model": name,
                "parameter": parameter,
                "seed": seed,
                "fold": fold,
                "mean_target_r2": row["mean_target_r2"],
                "centered_relative_mean_target_r2": row["centered_relative_mean_target_r2"],
                "mean_target_spearman": row["mean_target_spearman"],
                "centered_relative_mean_spearman": row["centered_relative_mean_spearman"],
                "mae": row["mae"],
                "rmse": row["rmse"],
            })
    return rows


def aggregate_cv(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    return frame.groupby(["model", "parameter"], dropna=False).agg(
        cv_mean_target_r2=("mean_target_r2", "mean"),
        cv_sd_target_r2=("mean_target_r2", "std"),
        cv_mean_target_spearman=("mean_target_spearman", "mean"),
        cv_mae=("mae", "mean"),
        cv_rmse=("rmse", "mean"),
        cv_replicates=("mean_target_r2", "size"),
    ).reset_index()


def bootstrap_external(
    name: str, parameter: float | int | None, x_fit: np.ndarray, y_fit: np.ndarray,
    x_external: np.ndarray, y_external: np.ndarray, seed: int, replicates: int,
) -> dict:
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(replicates):
        indices = rng.integers(0, len(x_fit), size=len(x_fit))
        estimator = make_model(name, parameter)
        estimator.fit(x_fit[indices], y_fit[indices])
        values.append(metrics(y_external, estimator.predict(x_external))["mean_target_r2"])
    values = np.asarray(values, dtype=float)
    return {
        "replicates": int(replicates),
        "mean_target_r2_mean": float(values.mean()),
        "mean_target_r2_sd": float(values.std(ddof=1)),
        "mean_target_r2_ci95": [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    x_raw, y_by_dataset, component_names, target_names = load_data()
    basis = helmert_basis(len(component_names))
    x_by_dataset = {name: zero_replaced_clr(x, EPSILON) @ basis.T for name, x in x_raw.items()}
    fit_name = "A4_A5_train_1m"
    external_name = "A6_A7_validation_1m"
    x_fit, y_fit = x_by_dataset[fit_name], y_by_dataset[fit_name]

    cv_rows_all: list[dict] = []
    for model_name, parameters in MODEL_GRID.items():
        for parameter in parameters:
            cv_rows_all.extend(cv_rows(model_name, parameter, x_fit, y_fit, [20260924, 20260925, 20260926]))
    cv_frame = pd.DataFrame(cv_rows_all)
    cv_summary = aggregate_cv(cv_rows_all)
    selected_rows = []
    selected: dict[str, float | int | None] = {}
    for model_name in MODEL_GRID:
        candidates = cv_summary[cv_summary["model"] == model_name].sort_values(
            ["cv_mean_target_r2", "cv_mae"], ascending=[False, True]
        )
        row = candidates.iloc[0].to_dict()
        parameter = row["parameter"]
        selected[model_name] = None if pd.isna(parameter) else parameter
        row["parameter"] = selected[model_name]
        selected_rows.append(row)
    selected_frame = pd.DataFrame(selected_rows)

    evaluations: dict[str, dict] = {}
    prediction_rows: list[dict] = []
    bootstrap: dict[str, dict] = {}
    for model_name, parameter in selected.items():
        estimator = make_model(model_name, parameter)
        estimator.fit(x_fit, y_fit)
        bootstrap[model_name] = bootstrap_external(
            model_name, parameter, x_fit, y_fit,
            x_by_dataset[external_name], y_by_dataset[external_name],
            seed=20260924, replicates=100,
        )
        for dataset, x in x_by_dataset.items():
            prediction = estimator.predict(x)
            evaluations[f"{model_name}::{dataset}"] = {
                "model": model_name,
                "parameter": parameter,
                "dataset": dataset,
                "role": PAIRS[dataset][1],
                **metrics(y_by_dataset[dataset], prediction),
            }
            for row_index, index_value in enumerate(x_raw[dataset].shape[0] and pd.read_csv(FEATURE_TABLE).query("dataset == @dataset").sort_values("index")["index"].to_numpy()):
                record = {"model": model_name, "parameter": parameter, "dataset": dataset, "index": index_value}
                for target_index, target in enumerate(target_names):
                    record[f"actual_{target}"] = float(y_by_dataset[dataset][row_index, target_index])
                    record[f"predicted_{target}"] = float(prediction[row_index, target_index])
                prediction_rows.append(record)

    cv_frame.to_csv(output_dir / "cv_folds.csv", index=False, encoding="utf-8-sig")
    cv_summary.to_csv(output_dir / "cv_summary.csv", index=False, encoding="utf-8-sig")
    selected_frame.to_csv(output_dir / "selected_models.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(prediction_rows).to_csv(output_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.model-benchmark.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "EXPERIMENTAL_REVIEW",
        "fit_rule": "A4/A5 only; model family and hyperparameters selected by repeated five-fold CV on A4/A5",
        "external_validation": "A6/A7 same-scale external validation",
        "cross_scale_usage": "A8-A15 post-fit diagnostics only",
        "feature_table": {"path": FEATURE_TABLE.relative_to(ROOT).as_posix(), "sha256": sha256(FEATURE_TABLE)},
        "basis": {"name": "Helmert ilr", "zero_replacement": "multiplicative", "epsilon": EPSILON, "component_names": component_names},
        "target_names": target_names,
        "selected_models": selected,
        "cv_summary_path": (output_dir / "cv_summary.csv").relative_to(ROOT).as_posix(),
        "selected_models_path": (output_dir / "selected_models.csv").relative_to(ROOT).as_posix(),
        "evaluations": evaluations,
        "bootstrap_external_A6": bootstrap,
        "limitations": [
            "Quality score Q is excluded because domain q_i is not frozen.",
            "Cross-scale absolute predictions are diagnostics, not scale-invariant success claims.",
            "A12-A15 are extrapolation scenarios, not independent validation data.",
            "No causal domain-effect or optimum-mixture claim is produced.",
            "The shallow GBDT is a fixed nonlinear reference, not a tuned primary candidate.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs" / "q1-model-benchmark.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "selected_models": selected, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
