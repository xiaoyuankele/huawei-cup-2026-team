"""Exploratory M0/M1 runs for problem 2.

M0: classical N-D scaling law on B1 with leave-one-parameter-size-out folds.
M1: additive quality sensitivity on B6 with grouped (N,D)-cell folds and
    evaluation on the 90 B7 rows not present in B6.

This is an exploratory run. B8, B9 and B10 are deliberately excluded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fit_model(rows: list[dict[str, str]], quality: bool) -> np.ndarray:
    n = np.array([float(r["N_params_B"]) for r in rows])
    d = np.array([float(r["D_tokens_B"]) for r in rows])
    y = np.array([float(r["val_loss"]) for r in rows])
    q = np.array([float(r["Q_score"]) for r in rows]) if quality else None

    if quality:
        def predict(theta: np.ndarray) -> np.ndarray:
            e, a, b, g, alpha, beta = theta
            return e + a * n ** (-alpha) + b * d ** (-beta) + g * (1.0 - q)

        x0 = np.array([1.2, 0.4, 1.0, 0.5, 0.3, 0.3])
        lower = np.array([0.0, 0.0, 0.0, 0.0, 0.001, 0.001])
        upper = np.array([6.0, 30.0, 30.0, 30.0, 3.0, 3.0])
    else:
        def predict(theta: np.ndarray) -> np.ndarray:
            e, a, b, alpha, beta = theta
            return e + a * n ** (-alpha) + b * d ** (-beta)

        x0 = np.array([1.2, 0.4, 1.0, 0.3, 0.3])
        lower = np.array([0.0, 0.0, 0.0, 0.001, 0.001])
        upper = np.array([6.0, 30.0, 30.0, 3.0, 3.0])

    result = least_squares(lambda theta: predict(theta) - y, x0, bounds=(lower, upper), max_nfev=20000)
    return result.x


def predict(rows: list[dict[str, str]], theta: np.ndarray, quality: bool) -> np.ndarray:
    n = np.array([float(r["N_params_B"]) for r in rows])
    d = np.array([float(r["D_tokens_B"]) for r in rows])
    if quality:
        q = np.array([float(r["Q_score"]) for r in rows])
        e, a, b, g, alpha, beta = theta
        return e + a * n ** (-alpha) + b * d ** (-beta) + g * (1.0 - q)
    e, a, b, alpha, beta = theta
    return e + a * n ** (-alpha) + b * d ** (-beta)


def metrics(rows: list[dict[str, str]], pred: np.ndarray) -> dict[str, float | int]:
    y = np.array([float(r["val_loss"]) for r in rows])
    residual = pred - y
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return {
        "n": len(rows),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "r2": float(1.0 - np.sum(residual ** 2) / ss_tot) if ss_tot > 0 else None,
        "residual_median": float(np.median(residual)),
        "residual_p95_abs": float(np.quantile(np.abs(residual), 0.95)),
    }


def fold_indices(rows: list[dict[str, str]], key_fn, k: int = 5) -> list[tuple[list[int], list[int], str]]:
    groups = sorted({key_fn(row) for row in rows})
    folds = [[] for _ in range(k)]
    for i, group in enumerate(groups):
        folds[i % k].append(group)
    result = []
    for fold_id, held_groups in enumerate(folds):
        held = set(held_groups)
        test_idx = [i for i, row in enumerate(rows) if key_fn(row) in held]
        train_idx = [i for i, row in enumerate(rows) if key_fn(row) not in held]
        result.append((train_idx, test_idx, f"fold_{fold_id + 1}"))
    return result


def subset(rows: list[dict[str, str]], indices: list[int]) -> list[dict[str, str]]:
    return [rows[i] for i in indices]


def git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return "unavailable"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bdir = args.root / "B_scaling_laws"
    args.out.mkdir(parents=True, exist_ok=True)

    b1_path = bdir / "pythia_training_log_existing.csv"
    b2_path = bdir / "cerebras_training_log.csv"
    b4_path = bdir / "scaling_baseline.csv"
    b5_path = bdir / "published_scaling_data.csv"
    b6_path = bdir / "supplementary_NQ_experiment.csv"
    b7_path = bdir / "supplementary_NQ_experiment_expanded.csv"
    b8_path = bdir / "supplementary_NQ_experiment_large.csv"

    b1, b2, b4, b5 = (read_csv(p) for p in (b1_path, b2_path, b4_path, b5_path))
    b6, b7, b8 = read_csv(b6_path), read_csv(b7_path), read_csv(b8_path)

    result: dict = {
        "status": "exploratory_review",
        "models": {
            "M0": "E + A*N^(-alpha) + B*D^(-beta)",
            "M1": "E + A*N^(-alpha) + B*D^(-beta) + G*(1-Q_score)",
        },
        "exclusions": {
            "B8": "excluded because Q direction conflicts with B6/B7 and provenance is incomplete",
            "B9_B10": "excluded from fitting because they are metadata/estimated extrapolation inputs",
        },
        "inputs": {p.name: {"rows": len(read_csv(p)), "sha256": sha256(p)} for p in [b1_path, b2_path, b4_path, b5_path, b6_path, b7_path, b8_path]},
        "M0": {},
        "M1": {},
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "git_commit": git_commit(args.root.parent),
    }

    m0_folds = []
    for train_idx, test_idx, fold_name in fold_indices(b1, lambda r: r["N_params_B"], k=8):
        train, test = subset(b1, train_idx), subset(b1, test_idx)
        theta = fit_model(train, quality=False)
        m0_folds.append({"fold": fold_name, "held_out_N_params_B": sorted({r["N_params_B"] for r in test}), "fit": theta.tolist(), "metrics": metrics(test, predict(test, theta, quality=False))})
    m0_full = fit_model(b1, quality=False)
    result["M0"] = {
        "fit_full_B1": m0_full.tolist(),
        "leave_one_parameter_size_out": m0_folds,
        "external_diagnostics": {
            "B2": metrics(b2, predict(b2, m0_full, quality=False)),
            "B4": metrics(b4, predict(b4, m0_full, quality=False)),
            "B5": metrics(b5, predict(b5, m0_full, quality=False)),
        },
    }

    m1_folds = []
    cell_key = lambda r: (r["N_params_B"], r["D_tokens_B"])
    for train_idx, test_idx, fold_name in fold_indices(b6, cell_key, k=5):
        train, test = subset(b6, train_idx), subset(b6, test_idx)
        theta = fit_model(train, quality=True)
        m1_folds.append({"fold": fold_name, "held_out_cells": [list(cell) for cell in sorted({cell_key(r) for r in test})], "fit": theta.tolist(), "metrics": metrics(test, predict(test, theta, quality=True))})

    b6_ids = {r["experiment_id"] for r in b6}
    b7_extension = [r for r in b7 if r["experiment_id"] not in b6_ids]
    m1_full = fit_model(b6, quality=True)
    result["M1"] = {
        "fit_B6": m1_full.tolist(),
        "grouped_ND_cell_cv": m1_folds,
        "B7_extension_rows": len(b7_extension),
        "B7_extension_metrics": metrics(b7_extension, predict(b7_extension, m1_full, quality=True)),
        "B7_full_diagnostic": metrics(b7, predict(b7, m1_full, quality=True)),
        "note": "B7 contains all B6 rows; extension metrics are nested-extension diagnostics, not independent validation.",
    }

    (args.out / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "command.txt").write_text("python -X utf8 scripts/q2_m0_m1_explore.py --root data/origin/real_attachments --out " + str(args.out), encoding="utf-8")
    (args.out / "environment.txt").write_text(json.dumps(result["environment"], indent=2), encoding="utf-8")
    (args.out / "git_commit.txt").write_text(result["git_commit"], encoding="utf-8")
    (args.out / "README.md").write_text(
        "# Q2 M0/M1 exploratory run\n\n"
        "M0 fits the classical N-D law on B1 with leave-one-parameter-size-out folds. "
        "M1 fits an additive quality sensitivity term on B6 with grouped N-D-cell folds and evaluates the B7 nested extension. "
        "B8, B9 and B10 are excluded by the current migration gates. This run is exploratory and not a final paper result.\n",
        encoding="utf-8",
    )
    print(args.out)


if __name__ == "__main__":
    main()
