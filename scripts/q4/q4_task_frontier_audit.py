"""Task-level and leave-one-task-out frontier audit for Q4."""
from __future__ import annotations
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
from q4_baseline_experiment import load_c8_scores

BASE = DATA_DIR
OUT = output_dir("task_frontier")
OUT.mkdir(exist_ok=True)
TASKS = ["IFEval", "BBH", "MATH", "GPQA", "MUSR", "MMLU_PRO"]


def qfront(d, col):
    return d.groupby("month", sort=True)[col].agg(n="size", median="median", q90=lambda x: x.quantile(.9), q95=lambda x: x.quantile(.95), maximum="max").reset_index()


def main():
    lb = pd.read_csv(BASE / "leaderboard_cleaned.csv", parse_dates=["Submission Date"])
    s = load_c8_scores(BASE / "detailed_results")
    d = lb[["Model", "Submission Date", "Type"]].merge(s, on="Model", how="inner")
    d = d[(d["Submission Date"] >= "2024-06-01") & (d["Submission Date"] < "2025-04-01")].copy()
    d["month"] = d["Submission Date"].dt.to_period("M").dt.to_timestamp()
    rows = []
    for task in TASKS:
        f = qfront(d, task)
        f.to_csv(OUT / f"{task}_monthly_frontier.csv", index=False)
        x = np.arange(len(f), dtype=float); y = f.q95.to_numpy(float) * 100
        rows.append({"target": task, "n_months": len(f), "first_q95": y[0], "last_q95": y[-1],
                     "change_last_minus_first": y[-1] - y[0], "linear_slope_per_month": np.polyfit(x, y, 1)[0]})
    # Leave one task out: recompute each model's mean over the remaining task groups.
    for held in TASKS:
        keep = [t for t in TASKS if t != held]
        d[f"loo_{held}"] = d[keep].mean(axis=1)
        f = qfront(d, f"loo_{held}")
        f.to_csv(OUT / f"loo_exclude_{held}_monthly_frontier.csv", index=False)
        y = f.q95.to_numpy(float) * 100; x = np.arange(len(y), dtype=float)
        rows.append({"target": f"C8_exclude_{held}", "n_months": len(f), "first_q95": y[0], "last_q95": y[-1],
                     "change_last_minus_first": y[-1] - y[0], "linear_slope_per_month": np.polyfit(x, y, 1)[0]})
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "task_frontier_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
