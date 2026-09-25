"""Test low-dimensional scale-by-mixture interactions under exploratory Track C."""

from __future__ import annotations

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

from q1_track_c_multiscale_exploratory import (
    ADAPTATION_DATASETS,
    DIAGNOSTIC_DATASETS,
    HOLDOUT_DATASETS,
    load_data,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-track-c-reduced-interactions-20260924-r01"
OUTPUT_DIR = ROOT / "experiments" / "runs" / RUN_ID
ALPHAS = [0.1, 1.0, 10.0, 100.0]

# Pre-specified from the A6/A8 Track-B screen, ordered by aggregate absolute
# correlation across targets. This is an exploratory hypothesis set, not a
# data-independent final feature selection.
TOP_ILR = [12, 5, 3, 16, 6]


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def reduced_blocks(x_by: dict[str, np.ndarray]) -> dict[str, dict[str, np.ndarray]]:
    blocks: dict[str, dict[str, np.ndarray]] = {}
    # x layout: ilr_1..ilr_16, log10_scale, then ilr_1..ilr_16 * log10_scale.
    blocks["shared_ilr_plus_scale"] = {key: value[:, :17] for key, value in x_by.items()}
    for count in (1, 3, 5):
        cols = list(range(16)) + [16] + [16 + i for i in TOP_ILR[:count]]
        blocks[f"scale_plus_top{count}_interactions"] = {
            key: value[:, cols] for key, value in x_by.items()
        }
    blocks["full_interaction"] = x_by
    return blocks


def evaluate(y: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    r2 = [float(r2_score(y[:, j], prediction[:, j])) for j in range(y.shape[1])]
    centered_y = y - y.mean(axis=0, keepdims=True)
    centered_prediction = prediction - prediction.mean(axis=0, keepdims=True)
    centered = [
        float(r2_score(centered_y[:, j], centered_prediction[:, j]))
        for j in range(y.shape[1])
    ]
    return {
        "mean_target_r2": float(np.mean(r2)),
        "centered_relative_mean_target_r2": float(np.mean(centered)),
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "mean_residual": float((y - prediction).mean()),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    x_by, y_by, groups_by, _, _ = load_data()
    blocks = reduced_blocks(x_by)
    x_adapt_groups = np.concatenate([groups_by[dataset] for dataset in ADAPTATION_DATASETS])
    results = []
    selected_rows = []
    for block_name, block in blocks.items():
        x_adapt = np.vstack([block[dataset] for dataset in ADAPTATION_DATASETS])
        y_adapt = np.vstack([y_by[dataset] for dataset in ADAPTATION_DATASETS])
        candidates = []
        for alpha in ALPHAS:
            model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
            scores = cross_val_score(
                model,
                x_adapt,
                y_adapt,
                groups=x_adapt_groups,
                cv=LeaveOneGroupOut(),
                scoring="r2",
            )
            candidates.append(
                {
                    "alpha": alpha,
                    "logo_mean_r2": float(scores.mean()),
                    "fold_r2": [float(v) for v in scores],
                }
            )
        selected = max(candidates, key=lambda row: row["logo_mean_r2"])
        selected_rows.append({"block": block_name, **selected})
        model = Pipeline(
            [("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]
        ).fit(x_adapt, y_adapt)
        for dataset in ADAPTATION_DATASETS + HOLDOUT_DATASETS + DIAGNOSTIC_DATASETS:
            metrics = evaluate(y_by[dataset], model.predict(block[dataset]))
            role = (
                "adaptation"
                if dataset in ADAPTATION_DATASETS
                else (
                    "unseen_scale_holdout"
                    if dataset in HOLDOUT_DATASETS
                    else "extrapolation_diagnostic"
                )
            )
            results.append(
                {
                    "block": block_name,
                    "dataset": dataset,
                    "selected_alpha": selected["alpha"],
                    "role": role,
                    **metrics,
                }
            )
    result_frame = pd.DataFrame(results)
    result_path = OUTPUT_DIR / "reduced_interaction_metrics.csv"
    result_frame.to_csv(result_path, index=False, encoding="utf-8-sig")
    selection_path = OUTPUT_DIR / "selected_alpha_logo.csv"
    pd.DataFrame(selected_rows).to_csv(selection_path, index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.track-c-reduced-interactions.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "ROLE_CHANGE_EXPLORATORY",
        "adaptation_data": ADAPTATION_DATASETS,
        "unseen_scale_holdout": HOLDOUT_DATASETS,
        "diagnostic_data": DIAGNOSTIC_DATASETS,
        "blocks": {
            "shared_ilr_plus_scale": 17,
            "scale_plus_top1_interactions": 18,
            "scale_plus_top3_interactions": 20,
            "scale_plus_top5_interactions": 22,
            "full_interaction": 33,
        },
        "top_ilr_from_track_b_a6_a8_screen": TOP_ILR,
        "outputs": {
            "metrics": {
                "path": result_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
                "rows": int(len(result_frame)),
            },
            "alpha_selection": {
                "path": selection_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
                "rows": int(len(selected_rows)),
            },
        },
        "limitations": [
            "A6/A7 and A8/A9 are adaptation data and are not official validation in this role-change run.",
            "The top ilr set is a Track-B hypothesis screen and must not be treated as confirmatory feature selection.",
            "A12/A14 are diagnostic extrapolation data only and do not select hyperparameters.",
        ],
    }
    metrics_path = OUTPUT_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
