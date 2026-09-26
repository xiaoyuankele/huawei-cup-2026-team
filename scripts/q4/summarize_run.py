"""Publish aggregate-only Q4 metrics from the ignored run artifacts."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import shutil

from q4_paths import RUN_DIR

FILES = {
    "baseline_metrics.csv": "baseline/baseline_metrics.csv",
    "robustness_metrics.csv": "robustness/robustness_metrics.csv",
    "c8_panel_holdout.csv": "c8_panel/nested_holdout_results.csv",
    "c8_compute_scenarios.csv": "c8_compute/compute_constrained_forecasts.csv",
    "c8_cluster_bootstrap.csv": "c8_bootstrap/cluster_bootstrap_summary.csv",
    "c8_panel_errors.csv": "error/panel_error_metrics.csv",
    "baseline_errors.csv": "error/baseline_error_metrics.csv",
    "c8_r2.csv": "error/r2_metrics.csv",
    "task_frontiers.csv": "task_frontier/task_frontier_summary.csv",
    "time_placebo.csv": "time_placebo/monthly_slope_placebo.csv",
    "loss_bridge.csv": "loss_bridge/bridge_regression_summary.csv",
    "family_quantile_holdout.csv": "family_quantile/quantile_holdout_results.csv",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def select(table: list[dict[str, str]], **filters: str) -> dict[str, str]:
    found = [row for row in table if all(row.get(key) == value for key, value in filters.items())]
    if len(found) != 1:
        raise ValueError(f"expected one row for {filters}, got {len(found)}")
    return found[0]


def main() -> None:
    public = RUN_DIR / "metrics"
    public.mkdir(parents=True, exist_ok=True)
    for name, relative in FILES.items():
        shutil.copy2(RUN_DIR / "artifacts" / relative, public / name)
    panel = rows(public / "c8_panel_errors.csv")
    baseline = rows(public / "baseline_metrics.csv")
    bootstrap = rows(public / "c8_cluster_bootstrap.csv")
    full = select(panel, tau="0.95", model="full")
    naive = select(baseline, target="c8_equal_task", method="naive_last")
    linear = select(baseline, target="c8_equal_task", method="linear_trend")
    h12 = select(bootstrap, quantity="frontier_q95_h12")
    h24 = select(bootstrap, quantity="frontier_q95_h24")
    summary = {
        "run_id": RUN_DIR.name,
        "status": "REVIEW",
        "c8_q95_holdout": {
            "n_test_models": int(full["n"]),
            "pinball_loss": float(full["pinball_loss"]),
            "empirical_coverage": float(full["coverage_y_le_pred"]),
            "MAE_for_quantile_only": float(full["MAE"]),
            "RMSE_for_quantile_only": float(full["RMSE"]),
        },
        "c8_monthly_one_step": {
            "n_test_months": int(naive["n_forecasts"]),
            "naive_MAE": float(naive["MAE"]),
            "linear_MAE": float(linear["MAE"]),
        },
        "trend_scenario_cluster_bootstrap": {
            "draws": int(h12["n_boot"]),
            "h12_q025_q975": [float(h12["q025"]), float(h12["q975"])],
            "h24_q025_q975": [float(h24["q025"]), float(h24["q975"])],
        },
        "limitations": [
            "Only 10 comparable months and one calendar-year holdout",
            "No 12/24-month forecast-error backtest",
            "Compute scaling is an external exploratory Q3 assumption",
            "Time coefficient is not a causal technology effect",
        ],
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
