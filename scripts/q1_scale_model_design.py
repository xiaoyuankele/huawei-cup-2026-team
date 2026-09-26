"""Build a candidate scale-conditioned model design from the derived table."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "experiments" / "runs" / "q1-scale-feature-table-20260924-r01" / "q1_scale_features_wide.csv"
RUN_ID = "q1-scale-model-design-20260924-r01"
OUTPUT_DIR = ROOT / "experiments" / "runs" / RUN_ID
EPSILON = 1e-4


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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(INPUT)
    component_columns = [column for column in source.columns if column.startswith("p_")]
    p = source[component_columns].to_numpy(dtype=float)
    ilr = zero_replaced_clr(p, EPSILON) @ helmert_basis(p.shape[1]).T
    log_scale = source["log10_scale"].to_numpy(dtype=float)
    design = source[["dataset", "role", "scale_label", "total_scale_tokens", "log10_scale", "index"]].copy()
    for column_index in range(ilr.shape[1]):
        design[f"ilr_{column_index + 1}"] = ilr[:, column_index]
        design[f"ilr_{column_index + 1}_x_log10_scale"] = ilr[:, column_index] * log_scale
    output_path = OUTPUT_DIR / "q1_scale_model_design_epsilon_1e-4.csv"
    design.to_csv(output_path, index=False, encoding="utf-8-sig")
    design_matrix = design.drop(columns=["dataset", "role", "scale_label", "total_scale_tokens", "index"]).to_numpy()
    standardized = (design_matrix - design_matrix.mean(axis=0)) / design_matrix.std(axis=0, ddof=0)
    standardized_design = np.c_[np.ones(len(standardized)), standardized]
    output = {
        "schema_version": "q1.scale-model-design.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "input": {"path": INPUT.relative_to(ROOT).as_posix(), "sha256": sha256(INPUT), "rows": int(len(source))},
        "output": {"path": output_path.relative_to(ROOT).as_posix(), "sha256": sha256(output_path), "rows": int(len(design)), "columns": int(len(design.columns))},
        "basis": "Helmert ilr",
        "zero_replacement": {"method": "multiplicative", "epsilon": EPSILON},
        "features": ["16 ilr coordinates", "log10_scale", "16 ilr_x_log10_scale interactions"],
        "design_diagnostics": {
            "predictor_count_without_intercept": int(design_matrix.shape[1]),
            "rank_with_intercept": int(np.linalg.matrix_rank(standardized_design)),
            "standardized_condition_number_with_intercept": float(np.linalg.cond(standardized_design)),
        },
        "limitations": [
            "This is an input-only candidate design; no Loss target is loaded.",
            "The epsilon choice is a candidate and remains subject to zero-replacement sensitivity review.",
            "The design does not authorize fitting scale effects under the current A4-only fit protocol.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
