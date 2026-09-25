"""Run the strict Q1 mixture baseline with a partial quality proxy.

The fit role is frozen to A4/A5.  A6/A7 are same-scale external validation,
A8-A11 are cross-scale diagnostics, and A12-A15 are extrapolation scenarios.
The unmapped mixture domains remain in the composition vector; only the
quality proxy is partial and therefore carries an explicit mapped-mass
coverage feature.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
INTEGRATION_RUN = "q1-mixture-quality-integration-20260925-r01"
INTEGRATION_TABLE = ROOT / "experiments" / "runs" / INTEGRATION_RUN / "mixture_quality_integration_wide.csv"
INTEGRATION_METRICS = ROOT / "experiments" / "runs" / INTEGRATION_RUN / "metrics.json"
RUN_ID = "q1-mixture-quality-baseline-20260925-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
EPSILON = 1e-4
ALPHAS = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]
SEED = 20260925

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
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def evaluate(y: np.ndarray, prediction: np.ndarray) -> dict[str, object]:
    residual = y - prediction
    r2: list[float] = []
    centered_r2: list[float] = []
    spearman: list[float | None] = []
    per_target_mae: list[float] = []
    per_target_rmse: list[float] = []
    per_target_bias: list[float] = []
    for j in range(y.shape[1]):
        actual = y[:, j]
        predicted = prediction[:, j]
        denominator = float(np.sum((actual - actual.mean()) ** 2))
        r2.append(float(1.0 - np.sum((actual - predicted) ** 2) / denominator) if denominator > 0 else float("nan"))
        centered_actual = actual - actual.mean()
        centered_predicted = predicted - predicted.mean()
        centered_denominator = float(np.sum(centered_actual ** 2))
        centered_r2.append(
            float(1.0 - np.sum((centered_actual - centered_predicted) ** 2) / centered_denominator)
            if centered_denominator > 0 else float("nan")
        )
        if np.allclose(actual, actual[0]) or np.allclose(predicted, predicted[0]):
            spearman.append(None)
        else:
            spearman.append(float(pd.Series(actual).corr(pd.Series(predicted), method="spearman")))
        per_target_mae.append(float(np.mean(np.abs(actual - predicted))))
        per_target_rmse.append(float(np.sqrt(np.mean((actual - predicted) ** 2))))
        per_target_bias.append(float(np.mean(actual - predicted)))
    finite_spearman = [value for value in spearman if value is not None and np.isfinite(value)]
    return {
        "mean_target_r2": float(np.nanmean(r2)),
        "median_target_r2": float(np.nanmedian(r2)),
        "centered_relative_mean_target_r2": float(np.nanmean(centered_r2)),
        "mean_target_spearman": float(np.mean(finite_spearman)) if finite_spearman else None,
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "per_target_r2": r2,
        "per_target_centered_relative_r2": centered_r2,
        "per_target_spearman": spearman,
        "per_target_mae": per_target_mae,
        "per_target_rmse": per_target_rmse,
        "per_target_mean_residual": per_target_bias,
    }


def load_data() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray], list[str], list[str], dict[str, dict]]:
    table = pd.read_csv(INTEGRATION_TABLE)
    p_columns = [column for column in table.columns if column.startswith("p_train_the_pile_")]
    if len(p_columns) != 17:
        raise ValueError(f"expected 17 mixture proportion columns, got {len(p_columns)}")
    p_by_dataset: dict[str, np.ndarray] = {}
    quality_by_dataset: dict[str, np.ndarray] = {}
    index_by_dataset: dict[str, np.ndarray] = {}
    y_by_dataset: dict[str, np.ndarray] = {}
    target_names: list[str] | None = None
    source_meta: dict[str, dict] = {}
    required_quality = [
        "quality_mapped_raw_0_100",
        "quality_mapped_mass",
        "quality_mapped_renorm_0_100",
    ]
    for dataset, (loss_file, _) in PAIRS.items():
        subset = table[table["dataset"] == dataset].sort_values("index")
        if subset.empty:
            raise ValueError(f"missing integration rows for {dataset}")
        if subset[["quality_mapped_raw_0_100", "quality_mapped_mass"]].isna().any().any():
            raise ValueError(f"missing raw quality features for {dataset}")
        loss_path = SOURCE / loss_file
        loss = pd.read_csv(loss_path).sort_values("index")
        indices = subset["index"].to_numpy()
        if not np.array_equal(indices, loss["index"].to_numpy()):
            raise ValueError(f"feature/Loss index mismatch: {dataset}")
        current_targets = [column for column in loss.columns if column != "index"]
        if target_names is None:
            target_names = current_targets
        elif current_targets != target_names:
            raise ValueError(f"target columns differ: {dataset}")
        p_by_dataset[dataset] = subset[p_columns].to_numpy(dtype=float)
        quality_by_dataset[dataset] = subset[required_quality].to_numpy(dtype=float)
        index_by_dataset[dataset] = indices
        y_by_dataset[dataset] = loss[current_targets].to_numpy(dtype=float)
        source_meta[dataset] = {
            "path": loss_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(loss_path),
            "rows": int(len(loss)),
        }
    return p_by_dataset, quality_by_dataset, index_by_dataset, y_by_dataset, target_names or [], source_meta


def make_blocks(
    p_by_dataset: dict[str, np.ndarray], quality_by_dataset: dict[str, np.ndarray], component_count: int,
    renorm_fill: float,
) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, object]]:
    basis = helmert_basis(component_count)
    blocks: dict[str, dict[str, np.ndarray]] = {
        "p_only": {},
        "p_q_raw_coverage": {},
        "p_q_renorm_coverage": {},
    }
    for dataset, p in p_by_dataset.items():
        z = zero_replaced_clr(p, EPSILON) @ basis.T
        raw = quality_by_dataset[dataset][:, 0:1]
        mass = quality_by_dataset[dataset][:, 1:2]
        renorm_observed = quality_by_dataset[dataset][:, 2:3]
        renorm_available = np.isfinite(renorm_observed).astype(float)
        renorm = np.where(np.isfinite(renorm_observed), renorm_observed, renorm_fill)
        blocks["p_only"][dataset] = z
        blocks["p_q_raw_coverage"][dataset] = np.c_[z, raw, mass]
        blocks["p_q_renorm_coverage"][dataset] = np.c_[z, renorm, mass, renorm_available]
    return blocks, {
        "name": "Helmert ilr",
        "zero_replacement": "multiplicative",
        "epsilon": EPSILON,
        "component_count": component_count,
        "conditional_quality_fill": "A4/A5 finite median only when mapped_mass=0",
        "conditional_quality_fill_value": float(renorm_fill),
    }


def fit_cv(block: str, x: np.ndarray, y: np.ndarray) -> tuple[dict, list[dict]]:
    splitter = KFold(n_splits=5, shuffle=True, random_state=SEED)
    rows: list[dict] = []
    for alpha in ALPHAS:
        fold_metrics = []
        for fold, (train_idx, valid_idx) in enumerate(splitter.split(x), start=1):
            estimator = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=float(alpha)))])
            estimator.fit(x[train_idx], y[train_idx])
            fold_result = evaluate(y[valid_idx], estimator.predict(x[valid_idx]))
            row = {
                "block": block,
                "alpha": float(alpha),
                "fold": fold,
                "mean_target_r2": fold_result["mean_target_r2"],
                "centered_relative_mean_target_r2": fold_result["centered_relative_mean_target_r2"],
                "mean_target_spearman": fold_result["mean_target_spearman"],
                "mae": fold_result["mae"],
                "rmse": fold_result["rmse"],
            }
            rows.append(row)
            fold_metrics.append(row)
    summary_rows = []
    for alpha in ALPHAS:
        candidate = [row for row in rows if row["alpha"] == float(alpha)]
        summary_rows.append({
            "block": block,
            "alpha": float(alpha),
            "cv_mean_target_r2": float(np.mean([r["mean_target_r2"] for r in candidate])),
            "cv_sd_target_r2": float(np.std([r["mean_target_r2"] for r in candidate], ddof=1)),
            "cv_mean_target_spearman": float(np.nanmean([r["mean_target_spearman"] for r in candidate])),
            "cv_mae": float(np.mean([r["mae"] for r in candidate])),
            "cv_rmse": float(np.mean([r["rmse"] for r in candidate])),
            "cv_replicates": len(candidate),
        })
    selected = max(summary_rows, key=lambda row: (row["cv_mean_target_r2"], -row["cv_mae"]))
    return selected, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    p_by_dataset, quality_by_dataset, index_by_dataset, y_by_dataset, target_names, target_sources = load_data()
    renorm_fill = float(np.nanmedian(quality_by_dataset["A4_A5_train_1m"][:, 2]))
    blocks, basis_meta = make_blocks(
        p_by_dataset, quality_by_dataset, len(next(iter(p_by_dataset.values())).T), renorm_fill
    )
    fit_dataset = "A4_A5_train_1m"
    y_fit = y_by_dataset[fit_dataset]

    selected_models: dict[str, dict] = {}
    cv_rows: list[dict] = []
    evaluations: dict[str, dict] = {}
    prediction_rows: list[dict] = []
    design_diagnostics: dict[str, dict] = {}
    for block, x_by_dataset in blocks.items():
        x_fit = x_by_dataset[fit_dataset]
        selected, rows = fit_cv(block, x_fit, y_fit)
        selected_models[block] = selected
        cv_rows.extend(rows)
        estimator = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x_fit, y_fit)
        x_standardized = StandardScaler().fit_transform(x_fit)
        design = np.c_[np.ones(len(x_fit)), x_standardized]
        design_diagnostics[block] = {
            "predictor_count_without_intercept": int(x_fit.shape[1]),
            "rank_with_intercept": int(np.linalg.matrix_rank(design)),
            "condition_number_with_intercept": float(np.linalg.cond(design)),
        }
        for dataset, x in x_by_dataset.items():
            prediction = estimator.predict(x)
            role = PAIRS[dataset][1]
            result = evaluate(y_by_dataset[dataset], prediction)
            evaluations[f"{block}::{dataset}"] = {
                "block": block,
                "dataset": dataset,
                "role": role,
                "alpha": selected["alpha"],
                **result,
            }
            for row_index, index_value in enumerate(index_by_dataset[dataset]):
                record = {"block": block, "dataset": dataset, "role": role, "index": int(index_value)}
                for target_index, target in enumerate(target_names):
                    record[f"actual_{target}"] = float(y_by_dataset[dataset][row_index, target_index])
                    record[f"predicted_{target}"] = float(prediction[row_index, target_index])
                prediction_rows.append(record)

    cv_frame = pd.DataFrame(cv_rows)
    evaluation_rows = []
    per_target_rows = []
    for result in evaluations.values():
        evaluation_rows.append({
            key: value for key, value in result.items()
            if not isinstance(value, list)
        })
        for target_index, target in enumerate(target_names):
            per_target_rows.append({
                "block": result["block"],
                "dataset": result["dataset"],
                "role": result["role"],
                "alpha": result["alpha"],
                "target": target,
                "r2": result["per_target_r2"][target_index],
                "centered_relative_r2": result["per_target_centered_relative_r2"][target_index],
                "spearman": result["per_target_spearman"][target_index],
                "mae": result["per_target_mae"][target_index],
                "rmse": result["per_target_rmse"][target_index],
                "mean_residual": result["per_target_mean_residual"][target_index],
            })
    predictions_path = output_dir / "predictions.csv"
    selected_path = output_dir / "selected_models.csv"
    evaluation_frame = pd.DataFrame(evaluation_rows)
    baseline_by_dataset = evaluation_frame[evaluation_frame["block"] == "p_only"].set_index("dataset")
    comparison_rows = []
    for result in evaluation_rows:
        baseline = baseline_by_dataset.loc[result["dataset"]]
        comparison_rows.append({
            "block": result["block"],
            "dataset": result["dataset"],
            "role": result["role"],
            "alpha": result["alpha"],
            "mean_target_r2": result["mean_target_r2"],
            "centered_relative_mean_target_r2": result["centered_relative_mean_target_r2"],
            "mean_target_spearman": result["mean_target_spearman"],
            "mae": result["mae"],
            "rmse": result["rmse"],
            "delta_mean_target_r2_vs_p_only": result["mean_target_r2"] - baseline["mean_target_r2"],
            "delta_centered_relative_mean_target_r2_vs_p_only": result["centered_relative_mean_target_r2"] - baseline["centered_relative_mean_target_r2"],
            "delta_mae_vs_p_only": result["mae"] - baseline["mae"],
            "delta_rmse_vs_p_only": result["rmse"] - baseline["rmse"],
        })
    comparison_path = output_dir / "paper_comparison_summary.csv"
    per_target_frame = pd.DataFrame(per_target_rows)
    baseline_target = per_target_frame[per_target_frame["block"] == "p_only"].set_index(["dataset", "target"])
    target_comparison_rows = []
    for row in per_target_rows:
        baseline = baseline_target.loc[(row["dataset"], row["target"])]
        target_comparison_rows.append({
            "block": row["block"],
            "dataset": row["dataset"],
            "role": row["role"],
            "target": row["target"],
            "delta_r2_vs_p_only": row["r2"] - baseline["r2"],
            "delta_mae_vs_p_only": row["mae"] - baseline["mae"],
            "delta_rmse_vs_p_only": row["rmse"] - baseline["rmse"],
            "delta_mean_residual_vs_p_only": row["mean_residual"] - baseline["mean_residual"],
        })
    target_comparison_path = output_dir / "paper_comparison_target_summary.csv"
    cv_frame.to_csv(output_dir / "cv_folds.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    evaluation_frame.to_csv(output_dir / "evaluation_summary.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    per_target_frame.to_csv(output_dir / "evaluation_per_target.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    pd.DataFrame(selected_models.values()).to_csv(selected_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    pd.DataFrame(comparison_rows).to_csv(comparison_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    pd.DataFrame(target_comparison_rows).to_csv(target_comparison_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    pd.DataFrame(prediction_rows).to_csv(predictions_path, index=False, encoding="utf-8-sig", lineterminator="\n")
    cv_path = output_dir / "cv_folds.csv"
    evaluation_path = output_dir / "evaluation_summary.csv"
    per_target_path = output_dir / "evaluation_per_target.csv"

    integration_meta = json.loads(INTEGRATION_METRICS.read_text(encoding="utf-8"))
    output = {
        "schema_version": "q1.mixture-quality-baseline.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "code": {
            "path": Path(__file__).relative_to(ROOT).as_posix(),
            "sha256": sha256(Path(__file__)),
        },
        "status": "LOCAL_RESULT_PENDING_TEAM_REVIEW",
        "fit_rule": "A4/A5 only; alpha selected by five-fold CV on A4/A5",
        "same_scale_validation": "A6/A7",
        "cross_scale_usage": "A8-A11 post-fit diagnostics only; no model selection or fitting",
        "extrapolation_usage": "A12-A15 scenario diagnostics only",
        "inputs": {
            "integration_table": {
                "path": INTEGRATION_TABLE.relative_to(ROOT).as_posix(),
                "sha256": sha256(INTEGRATION_TABLE),
                "rows": int(sum(len(v) for v in p_by_dataset.values())),
            },
            "integration_run_id": integration_meta.get("run_id"),
            "mapping_version": integration_meta.get("mapping_version"),
            "quality_score_version": integration_meta.get("quality_score_version"),
            "target_sources": target_sources,
        },
        "basis": basis_meta,
        "feature_blocks": {
            "p_only": "Helmert ilr composition only",
            "p_q_raw_coverage": "Helmert ilr + partial mapped Q_raw + mapped_mass",
        "p_q_renorm_coverage": "Helmert ilr + conditional Q_raw/mapped_mass + mapped_mass + availability sensitivity",
        },
        "target_names": target_names,
        "selected_models": selected_models,
        "design_diagnostics": design_diagnostics,
        "evaluations": evaluations,
        "outputs": {
            "cv_folds": {
                "path": cv_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(cv_path),
                "rows": int(len(cv_frame)),
            },
            "evaluation_summary": {
                "path": evaluation_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(evaluation_path),
                "rows": int(len(evaluation_rows)),
            },
            "evaluation_per_target": {
                "path": per_target_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(per_target_path),
                "rows": int(len(per_target_rows)),
            },
            "selected_models": {
                "path": selected_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(selected_path),
                "rows": int(len(selected_models)),
            },
            "paper_comparison_summary": {
                "path": comparison_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(comparison_path),
                "rows": int(len(comparison_rows)),
            },
            "paper_comparison_target_summary": {
                "path": target_comparison_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(target_comparison_path),
                "rows": int(len(target_comparison_rows)),
            },
            "predictions": {
                "path": predictions_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(predictions_path),
                "rows": int(len(prediction_rows)),
            },
        },
        "mapping": integration_meta.get("mapping", {}),
        "limitations": [
            "The quality block is a partial mapped proxy; eleven mixture domains remain unmapped.",
            "Unmapped domains remain in p and are not assigned quality zero.",
            "A6-A7 are the only same-scale external validation; A8-A15 are diagnostic under the frozen fit rule.",
            "No causal quality effect, universal scale law, or optimum mixture is claimed.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text(
        (ROOT / "configs" / "q1-mixture-quality-baseline.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (output_dir / "command.txt").write_text(
        "python -X utf8 scripts/q1_mixture_quality_baseline.py\n", encoding="utf-8"
    )
    (output_dir / "environment.json").write_text(json.dumps({
        "python": sys.version,
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# Q1 配比—质量基线模型\n\n"
        f"运行号：`{RUN_ID}`。A4/A5 仅用于拟合和五折选择 alpha，A6/A7 为同尺度外部验证，"
        "A8–A11 为跨尺度诊断，A12–A15 为外推情景诊断。模型比较 p-only、"
        "p + Q_raw + mapped_mass，以及 Q_raw/mapped_mass 敏感性分支。未映射领域保留在配比向量中，"
        "不填充质量零值。\n\n"
        "该运行是候选基线，状态为 LOCAL_RESULT_PENDING_TEAM_REVIEW，不支持因果质量效应、"
        "通用跨规模定律或最优配比结论。Q_renorm 对 mapped_mass=0 的行使用训练行中位数并带有可用性指示，"
        "不是质量为零的填充。`paper_comparison_summary.csv` 给出联合指标差值，"
        "`paper_comparison_target_summary.csv` 给出逐目标误差差值。\n\n"
        "重跑命令：`python -X utf8 scripts/q1_mixture_quality_baseline.py`\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": RUN_ID, "selected_models": selected_models, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
