"""Repository-relative paths for the exploratory Q4 experiments.

Run scripts from the repository root. Raw attachment C stays in the ignored
``data/origin`` directory, or can be selected with ``Q4_DATA_DIR``.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("Q4_DATA_DIR", "data/origin/C_efficiency_evolution"))
RUN_DIR = Path(os.environ.get("Q4_RUN_DIR", "experiments/runs/q4-frontier-20260926-r01"))


def output_dir(name: str) -> Path:
    path = RUN_DIR / "artifacts" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def q3_optima_file() -> Path:
    return Path(os.environ.get("Q4_Q3_OPTIMA_FILE", str(RUN_DIR / "q3_baseline_ND_optima.csv")))
