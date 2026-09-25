"""Ablate scale-conditioned feature blocks in the exploratory Track C run."""

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
RUN_ID = "q1-track-c-ablation-20260924-r01"
OUTPUT_DIR = ROOT / "experiments" / "runs" / RUN_ID
ALPHAS = [0.1, 1.0, 10.0, 100.0]


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def feature_blocks(x_by: dict[str, np.ndarray]) -> dict[str, dict[str, np.ndarray]]:
    return {
        "p_only_ilr": {key: value[:, :16] for key, value in x_by.items()},
        "scale_only": {key: value[:, 16:17] for key, value in x_by.items()},
        "shared_ilr_plus_scale": {key: value[:, :17] for key, value in x_by.items()},
        "full_interaction": x_by,
    }


def evaluate(y: np.ndarray, prediction: np.ndarray) -> dict:
    r2 = [float(r2_score(y[:, j], prediction[:, j])) for j in range(y.shape[1])]
    centered_y = y - y.mean(axis=0, keepdims=True)
    centered_prediction = prediction - prediction.mean(axis=0, keepdims=True)
    centered = [float(r2_score(centered_y[:, j], centered_prediction[:, j])) for j in range(y.shape[1])]
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
    blocks = feature_blocks(x_by)
    x_adapt_groups = np.concatenate([groups_by[dataset] for dataset in ADAPTATION_DATASETS])
    results = []
    for block_name, block in blocks.items():
        x_adapt = np.vstack([block[dataset] for dataset in ADAPTATION_DATASETS])
        y_adapt = np.vstack([y_by[dataset] for dataset in ADAPTATION_DATASETS])
        candidates = []
        for alpha in ALPHAS:
            model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
            scores = cross_val_score(model, x_adapt, y_adapt, groups=x_adapt_groups, cv=LeaveOneGroupOut(), scoring="r2")
            candidates.append({"alpha": alpha, "logo_mean_r2": float(scores.mean()), "fold_r2": [float(v) for v in scores]})
        selected = max(candidates, key=lambda row: row["logo_mean_r2"])
        model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x_adapt, y_adapt)
        for dataset in ADAPTATION_DATASETS + HOLDOUT_DATASETS + DIAGNOSTIC_DATASETS:
            metrics = evaluate(y_by[dataset], model.predict(block[dataset]))
            results.append({"block": block_name, "dataset": dataset, "selected_alpha": selected["alpha"], "role": "adaptation" if dataset in ADAPTATION_DATASETS else ("unseen_scale_holdout" if dataset in HOLDOUT_DATASETS else "extrapolation_diagnostic"), **metrics})
    result_frame = pd.DataFrame(results)
    result_path = OUTPUT_DIR / "ablation_metrics.csv"
    result_frame.to_csv(result_path, index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.track-c-ablation.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "ROLE_CHANGE_EXPLORATORY",
        "adaptation_data": ADAPTATION_DATASETS,
        "unseen_scale_holdout": HOLDOUT_DATASETS,
        "blocks": {"p_only_ilr": 16, "scale_only": 1, "shared_ilr_plus_scale": 17, "full_interaction": 33},
        "output": {"path": result_path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(), "rows": int(len(result_frame))},
        "limitations": [
            "A6/A7 and A8/A9 are adaptation data in this run and are not official validation.",
            "Ablation compares feature blocks under the same role-change protocol; it does not establish a final model.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
