"""Audit rank/conditioning of a prospective scale-conditioned design.

Targets are not loaded.  This is a design audit only; the current data
contract still reserves A6-A15 for validation or extrapolation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-scale-design-rank-20260924-r01"
SETS = {
    "A4_train_1m": ("train_mixture_1m.csv", 1e6, "fit"),
    "A6_validation_1m": ("test_mixture_1m.csv", 1e6, "validation"),
    "A8_validation_60m": ("test_mixture_60m.csv", 60e6, "validation"),
    "A10_validation_1b": ("test_mixture_1B.csv", 1e9, "validation"),
    "A12_extrapolation_10b": ("est_mixture_10b.csv", 1e10, "extrapolation"),
    "A14_extrapolation_70b": ("est_mixture_70b.csv", 70e9, "extrapolation"),
}


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def read_p(filename: str) -> np.ndarray:
    frame = pd.read_csv(SOURCE / filename).drop(columns="index").astype(float)
    p = frame.div(frame.sum(axis=1), axis=0).to_numpy()
    return p


def make_design(p: np.ndarray, scale: float, epsilon: float) -> np.ndarray:
    z = zero_replaced_clr(p, epsilon) @ helmert_basis(p.shape[1]).T
    log_scale = np.full((len(p), 1), np.log10(scale))
    return np.c_[np.ones(len(p)), z, log_scale, z * log_scale]


def diagnostics(design: np.ndarray) -> dict:
    centered = design[:, 1:] - design[:, 1:].mean(axis=0, keepdims=True)
    scales = centered.std(axis=0, ddof=0)
    keep = scales > 1e-14
    standardized = centered[:, keep] / scales[keep]
    standardized_design = np.c_[np.ones(len(design)), standardized]
    singular = np.linalg.svd(design, compute_uv=False)
    standardized_singular = np.linalg.svd(standardized_design, compute_uv=False)
    return {
        "rows": int(len(design)),
        "columns": int(design.shape[1]),
        "rank_raw": int(np.linalg.matrix_rank(design)),
        "rank_standardized": int(np.linalg.matrix_rank(standardized_design)),
        "raw_condition_number": float(np.linalg.cond(design)),
        "standardized_condition_number": float(np.linalg.cond(standardized_design)),
        "minimum_raw_singular_value": float(np.min(singular)),
        "minimum_standardized_singular_value": float(np.min(standardized_singular)),
    }


def main() -> None:
    blocks = {}
    for label, (filename, scale, role) in SETS.items():
        p = read_p(filename)
        blocks[label] = {"p": p, "scale": scale, "role": role, "rows": len(p)}
    epsilons = [1e-6, 1e-4, 1e-3]
    results = {}
    for epsilon in epsilons:
        all_design = np.vstack([make_design(item["p"], item["scale"], epsilon) for item in blocks.values()])
        results[str(epsilon)] = {
            "pooled": diagnostics(all_design),
            "by_block": {label: diagnostics(make_design(item["p"], item["scale"], epsilon)) for label, item in blocks.items()},
        }
    output = {
        "schema_version": "q1.scale-design-rank.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "design": "[1, ilr(p), log10(scale), ilr(p)*log10(scale)]",
        "blocks": {label: {"scale": item["scale"], "log10_scale": float(np.log10(item["scale"])), "rows": item["rows"], "role": item["role"]} for label, item in blocks.items()},
        "by_zero_replacement": results,
        "interpretation_limits": [
            "This uses mixture inputs only and does not fit Loss targets.",
            "A4 alone has one scale level, so scale main effects and interactions are not estimable under the current fit-only role.",
            "The pooled rank result is a design feasibility audit, not permission to use validation or extrapolation targets for fitting.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
