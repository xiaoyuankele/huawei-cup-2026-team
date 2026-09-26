"""Quantify the irreducible disagreement for duplicate mixture designs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-scale-identifiability-20260924-r01"
PAIRS = {
    "A6_A8_same_mixture_1m_vs_60m": (
        "test_mixture_1m.csv", "test_pile_loss_1m.csv",
        "test_mixture_60m.csv", "test_pile_loss_60m.csv", "validation",
    ),
    "A12_A14_same_mixture_10b_vs_70b": (
        "est_mixture_10b.csv", "est_pile_loss_10b.csv",
        "est_mixture_70b.csv", "est_pile_loss_70b.csv", "extrapolation",
    ),
}


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def read(mixture_file: str, loss_file: str) -> tuple[pd.DataFrame, np.ndarray]:
    mixture = pd.read_csv(SOURCE / mixture_file)
    loss = pd.read_csv(SOURCE / loss_file)
    if not mixture["index"].equals(loss["index"]):
        raise ValueError("mixture/Loss index mismatch")
    return mixture.drop(columns="index"), loss.drop(columns="index").astype(float).to_numpy()


def main() -> None:
    results = {}
    for label, (mix_a, loss_a, mix_b, loss_b, role) in PAIRS.items():
        p_a, y_a = read(mix_a, loss_a)
        p_b, y_b = read(mix_b, loss_b)
        if not p_a.equals(p_b):
            raise ValueError(f"expected exact duplicate mixture designs: {label}")
        delta = y_a - y_b
        # For two targets attached to the same p, the best shared prediction
        # has per-cell absolute error |delta|/2 and squared error delta^2/4.
        per_target = {
            "mean_delta": [float(v) for v in delta.mean(axis=0)],
            "mean_absolute_delta": [float(v) for v in np.abs(delta).mean(axis=0)],
            "shared_prediction_mae_lower_bound": [float(v) for v in (np.abs(delta).mean(axis=0) / 2.0)],
            "shared_prediction_rmse_lower_bound": [float(v) for v in np.sqrt((delta ** 2).mean(axis=0) / 4.0)],
        }
        results[label] = {
            "role": role,
            "rows": int(len(delta)),
            "target_count": int(delta.shape[1]),
            "mean_loss_a": float(y_a.mean()),
            "mean_loss_b": float(y_b.mean()),
            "mean_delta_a_minus_b": float(delta.mean()),
            "mean_absolute_delta": float(np.abs(delta).mean()),
            "shared_prediction_mae_lower_bound": float(np.abs(delta).mean() / 2.0),
            "shared_prediction_rmse_lower_bound": float(np.sqrt((delta ** 2).mean() / 4.0)),
            "per_target": per_target,
            "interpretation": "A p-only deterministic predictor assigns one value to each duplicated mixture row, so it cannot attain zero error on both scale targets.",
        }
    output = {
        "schema_version": "q1.scale-identifiability.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "results": results,
        "limitations": [
            "The lower bound concerns a shared deterministic p-only prediction and does not estimate a scale-conditioned model.",
            "A12/A14 are extrapolation tables and remain sensitivity evidence rather than independent validation.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
