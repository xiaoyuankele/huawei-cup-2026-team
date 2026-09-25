"""Compare shared and target-specific Ridge regularization in Q1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from q1_model_benchmark import FEATURE_TABLE, PAIRS, load_data, metrics
from q1_quality_migration import ADAPTATION, ALPHAS, DIAGNOSTIC, HOLDOUT, MAPPING_PATH, QUALITY_SOURCES, feature_blocks, load_mapping, load_quality_scores


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-target-specific-scale-20260925-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID


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


def select_shared(x_by: dict[str, np.ndarray], y_by: dict[str, np.ndarray]) -> tuple[Pipeline, dict]:
    x = np.vstack([x_by[d] for d in ADAPTATION])
    y = np.vstack([y_by[d] for d in ADAPTATION])
    groups = np.concatenate([np.full(len(y_by[d]), d) for d in ADAPTATION])
    candidates = []
    for alpha in ALPHAS:
        fold_scores = []
        for train_idx, valid_idx in LeaveOneGroupOut().split(x, y, groups=groups):
            model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))]).fit(x[train_idx], y[train_idx])
            fold_scores.append(metrics(y[valid_idx], model.predict(x[valid_idx]))["mean_target_r2"])
        candidates.append({"alpha": alpha, "logo_mean_target_r2": float(np.mean(fold_scores)), "fold_r2": fold_scores})
    selected = max(candidates, key=lambda row: row["logo_mean_target_r2"])
    return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x, y), selected


def select_target_specific(x_by: dict[str, np.ndarray], y_by: dict[str, np.ndarray], target_count: int) -> tuple[list[Pipeline], list[dict]]:
    x = np.vstack([x_by[d] for d in ADAPTATION])
    y = np.vstack([y_by[d] for d in ADAPTATION])
    groups = np.concatenate([np.full(len(y_by[d]), d) for d in ADAPTATION])
    models = []
    selections = []
    for target in range(target_count):
        candidates = []
        for alpha in ALPHAS:
            fold_scores = []
            for train_idx, valid_idx in LeaveOneGroupOut().split(x, y[:, target], groups=groups):
                model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))]).fit(x[train_idx], y[train_idx, target])
                pred = model.predict(x[valid_idx])
                fold_scores.append(float(metrics(y[valid_idx, target:target + 1], pred.reshape(-1, 1))["mean_target_r2"]))
            candidates.append({"target_index": target, "alpha": alpha, "logo_target_r2": float(np.mean(fold_scores)), "fold_r2": fold_scores})
        selected = max(candidates, key=lambda row: row["logo_target_r2"])
        models.append(Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x, y[:, target]))
        selections.append(selected)
    return models, selections


def predict_target_specific(models: list[Pipeline], x: np.ndarray) -> np.ndarray:
    return np.column_stack([model.predict(x) for model in models])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    _, y_by_dataset, component_names, target_names = load_data()
    table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in table.columns if column.startswith("p_")]
    p_by_dataset = {dataset: table[table["dataset"] == dataset].sort_values("index")[p_columns].to_numpy(dtype=float) for dataset in PAIRS}
    quality_map, _ = load_mapping()
    quality_scores, _ = load_quality_scores()
    quality = quality_scores["TOPSIS_CRITIC"]
    blocks = feature_blocks(table, p_by_dataset, component_names, quality, quality_map)

    summary = []
    selections = []
    for block_name in ("baseline", "q_raw_coverage"):
        shared_model, shared_selection = select_shared(blocks[block_name], y_by_dataset)
        target_models, target_selection = select_target_specific(blocks[block_name], y_by_dataset, len(target_names))
        selections.append({"block": block_name, "model": "shared_alpha_ridge", "selection": shared_selection})
        for row in target_selection:
            selections.append({"block": block_name, "model": "target_specific_alpha_ridge", "selection": row})
        for dataset in HOLDOUT + DIAGNOSTIC:
            shared_pred = shared_model.predict(blocks[block_name][dataset])
            target_pred = predict_target_specific(target_models, blocks[block_name][dataset])
            for model_name, pred in (("shared_alpha_ridge", shared_pred), ("target_specific_alpha_ridge", target_pred)):
                score = metrics(y_by_dataset[dataset], pred)
                summary.append({"block": block_name, "model": model_name, "dataset": dataset, "mean_target_r2": score["mean_target_r2"], "centered_relative_mean_target_r2": score["centered_relative_mean_target_r2"], "mae": score["mae"], "rmse": score["rmse"], "mean_target_spearman": score["mean_target_spearman"]})

    pd.DataFrame(summary).to_csv(output_dir / "target_specific_summary.csv", index=False, encoding="utf-8-sig")
    (output_dir / "target_specific_selection.json").write_text(json.dumps(selections, ensure_ascii=False, indent=2), encoding="utf-8")
    output = {
        "schema_version": "q1.target-specific-scale.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "ROLE_CHANGE_EXPLORATORY",
        "quality_source": {"name": "TOPSIS_CRITIC", "path": str(QUALITY_SOURCES["TOPSIS_CRITIC"].relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(QUALITY_SOURCES["TOPSIS_CRITIC"])},
        "mapping_source": {"path": str(MAPPING_PATH.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(MAPPING_PATH)},
        "summary": summary,
        "limitations": [
            "Target-specific alpha is selected on the same role-change LOGO protocol and remains exploratory.",
            "A10 is an unseen-scale holdout; A12-A15 are extrapolation diagnostics.",
            "No causal scale effect or official external-validation claim is made.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs" / "q1-target-specific-scale.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text("# Q1 target-specific scale audit\n\nThis run compares shared-alpha and target-specific-alpha standardized Ridge models under the role-change protocol.\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "targets": len(target_names), "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
