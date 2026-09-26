"""Exploratory scale-anchor audit using 1M, 60M and 1B adaptation scales."""

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
from q1_quality_migration import ALPHAS, DIAGNOSTIC, MAPPING_PATH, QUALITY_SOURCES, feature_blocks, load_mapping, load_quality_scores


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-midscale-anchor-20260925-r01"
DEFAULT_OUTPUT = ROOT / "experiments/runs" / RUN_ID
ADAPTATION = ["A4_A5_train_1m", "A6_A7_validation_1m", "A8_A9_validation_60m", "A10_A11_validation_1b"]


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


def fit_selected(x_by: dict[str, np.ndarray], y_by: dict[str, np.ndarray]) -> tuple[Pipeline, dict]:
    x = np.vstack([x_by[d] for d in ADAPTATION])
    y = np.vstack([y_by[d] for d in ADAPTATION])
    groups = np.concatenate([np.full(len(y_by[d]), d) for d in ADAPTATION])
    candidates = []
    for alpha in ALPHAS:
        folds = []
        for train_idx, valid_idx in LeaveOneGroupOut().split(x, y, groups=groups):
            model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))]).fit(x[train_idx], y[train_idx])
            folds.append(metrics(y[valid_idx], model.predict(x[valid_idx]))["mean_target_r2"])
        candidates.append({"alpha": alpha, "logo_mean_target_r2": float(np.mean(folds)), "logo_sd_target_r2": float(np.std(folds, ddof=1)), "fold_r2": folds})
    selected = max(candidates, key=lambda row: (row["logo_mean_target_r2"], -row["logo_sd_target_r2"]))
    return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x, y), selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    _, y_by_dataset, component_names, _ = load_data()
    table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in table.columns if column.startswith("p_")]
    p_by_dataset = {dataset: table[table["dataset"] == dataset].sort_values("index")[p_columns].to_numpy(dtype=float) for dataset in PAIRS}
    quality_map, _ = load_mapping()
    quality_scores, _ = load_quality_scores()
    blocks = feature_blocks(table, p_by_dataset, component_names, quality_scores["TOPSIS_CRITIC"], quality_map)
    rows = []
    for block_name in ("baseline", "q_raw_coverage"):
        model, selected = fit_selected(blocks[block_name], y_by_dataset)
        for dataset in DIAGNOSTIC:
            score = metrics(y_by_dataset[dataset], model.predict(blocks[block_name][dataset]))
            rows.append({"block": block_name, "dataset": dataset, "selected_alpha": selected["alpha"], "logo_mean_target_r2": selected["logo_mean_target_r2"], "logo_sd_target_r2": selected["logo_sd_target_r2"], "mean_target_r2": score["mean_target_r2"], "centered_relative_mean_target_r2": score["centered_relative_mean_target_r2"], "mae": score["mae"], "rmse": score["rmse"], "mean_target_spearman": score["mean_target_spearman"]})
    pd.DataFrame(rows).to_csv(output_dir / "midscale_anchor_summary.csv", index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.midscale-anchor.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "ROLE_CHANGE_EXPLORATORY",
        "adaptation": ADAPTATION,
        "diagnostic": DIAGNOSTIC,
        "quality_source": {"name": "TOPSIS_CRITIC", "path": str(QUALITY_SOURCES["TOPSIS_CRITIC"].relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(QUALITY_SOURCES["TOPSIS_CRITIC"])},
        "mapping_source": {"path": str(MAPPING_PATH.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(MAPPING_PATH)},
        "summary": rows,
        "limitations": [
            "A10/A11 are deliberately used as adaptation data in this role-change experiment.",
            "A12-A15 remain extrapolation diagnostics and are not official validation.",
            "No full quality score, causal scale law or optimum mixture is claimed.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs/q1-midscale-anchor.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text("# Q1 midscale anchor audit\n\nA role-change audit that uses 1M, 60M and 1B data for adaptation and holds 10B/70B for extrapolation diagnostics.\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "adaptation": ADAPTATION, "diagnostic": DIAGNOSTIC}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
