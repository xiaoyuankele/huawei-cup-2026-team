"""Reproducible low-complexity Q4 baselines.

Uses month-level 95th-percentile frontiers and strictly time-ordered rolling
one-step validation. Reports official leaderboard Average and an equal-weight
C8 detailed-task score.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file

import numpy as np
import pandas as pd

GROUPS = {
    "IFEval": ("leaderboard_ifeval", "inst_level_strict_acc,none"),
    "BBH": ("leaderboard_bbh", "acc_norm,none"),
    "MATH": ("leaderboard_math_hard", "exact_match,none"),
    "GPQA": ("leaderboard_gpqa", "acc_norm,none"),
    "MUSR": ("leaderboard_musr", "acc_norm,none"),
    "MMLU_PRO": ("leaderboard_mmlu_pro", "acc,none"),
}
METHODS = ["naive_last", "mean_last_3", "linear_trend"]


def load_c8_scores(details_dir: Path) -> pd.DataFrame:
    rows = []
    for fn in glob.glob(str(details_dir / "*" / "*.json")):
        try:
            d = json.loads(Path(fn).read_text(encoding="utf-8"))
            vals = {}
            for name, (group, metric) in GROUPS.items():
                value = d.get("results", {}).get(group, {}).get(metric)
                vals[name] = float(value) if value not in (None, "N/A") else np.nan
            if d.get("model_name") and np.isfinite(list(vals.values())).sum() == len(GROUPS):
                rows.append({"Model": d["model_name"], "eval_timestamp": d.get("date", np.nan), **vals})
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    raw = pd.DataFrame(rows)
    if raw.empty:
        return raw
    raw = raw.sort_values("eval_timestamp").drop_duplicates("Model", keep="last")
    task_cols = list(GROUPS)
    raw["c8_score"] = raw[task_cols].mean(axis=1, skipna=True) * 100.0
    return raw[["Model", *task_cols, "c8_score"]]


def build_monthly(source: Path, score_col: str = "Average ⬆️", c8_scores: pd.DataFrame | None = None) -> pd.DataFrame:
    df = pd.read_csv(source, parse_dates=["Submission Date"])
    df = df.dropna(subset=["Submission Date", "Model", score_col]).copy()
    if c8_scores is not None:
        df = df.merge(c8_scores[["Model", "c8_score"]], on="Model", how="inner")
        score_col = "c8_score"
    df["month"] = df["Submission Date"].dt.to_period("M").dt.to_timestamp()
    df = df.sort_values(["Submission Date", "Model"]).drop_duplicates(["month", "Model"], keep="last")
    g = df.groupby("month", sort=True)[score_col]
    return g.agg(
        n="size",
        median="median",
        q90=lambda x: x.quantile(0.90),
        q95=lambda x: x.quantile(0.95),
        maximum="max",
    ).reset_index()


def predict(train: np.ndarray, method: str) -> float:
    if method == "naive_last":
        return float(train[-1])
    if method == "mean_last_3":
        return float(np.mean(train[-3:]))
    if method == "linear_trend":
        x = np.arange(len(train), dtype=float)
        return float(np.polyval(np.polyfit(x, train, 1), len(train)))
    raise ValueError(method)


def rolling_eval(frontier: pd.DataFrame, min_train: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    y = frontier["q95"].to_numpy(float)
    dates = frontier["month"]
    for i in range(min_train, len(y)):
        for method in METHODS:
            pred = predict(y[:i], method)
            err = pred - y[i]
            rows.append({
                "test_month": dates.iloc[i].strftime("%Y-%m"),
                "method": method,
                "actual_q95": y[i],
                "prediction": pred,
                "error": err,
                "absolute_error": abs(err),
                "squared_error": err**2,
            })
    detail = pd.DataFrame(rows)
    metrics = detail.groupby("method").agg(
        n_forecasts=("error", "size"),
        MAE=("absolute_error", "mean"),
        RMSE=("squared_error", lambda x: float(np.sqrt(np.mean(x)))),
        mean_bias=("error", "mean"),
    ).reset_index()
    return detail, metrics


def project(frontier: pd.DataFrame, target: str, horizon: int) -> pd.DataFrame:
    y = frontier["q95"].to_numpy(float)
    last = frontier["month"].iloc[-1]
    rows = []
    for method in METHODS:
        if method == "linear_trend":
            x = np.arange(len(y), dtype=float)
            coef = np.polyfit(x, y, 1)
            vals = [float(np.polyval(coef, len(y) + h - 1)) for h in range(1, horizon + 1)]
        else:
            vals = [predict(y, method)] * horizon
        for h, value in enumerate(vals, 1):
            rows.append({
                "target": target,
                "method": method,
                "forecast_horizon": horizon,
                "horizon_month": h,
                "target_month": (last + pd.DateOffset(months=h)).strftime("%Y-%m"),
                "predicted_q95": value,
            })
    return pd.DataFrame(rows)


def annual_audit(extended: Path) -> pd.DataFrame:
    d = pd.read_csv(extended)
    return d.groupby("Year", sort=True).agg(
        rows=("Model", "size"),
        unique_models=("Model", "nunique"),
        median_score=("Average", "median"),
        q90=("Average", lambda x: x.quantile(0.90)),
        q95=("Average", lambda x: x.quantile(0.95)),
        maximum=("Average", "max"),
    ).reset_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=DATA_DIR)
    ap.add_argument("--out-dir", type=Path, default=output_dir("baseline"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    leaderboard = args.base / "leaderboard_cleaned.csv"
    c8 = load_c8_scores(args.base / "detailed_results")
    c8.to_csv(args.out_dir / "c8_model_scores.csv", index=False)

    average_frontier = build_monthly(leaderboard, "Average ⬆️")
    c8_frontier = build_monthly(leaderboard, "Average ⬆️", c8_scores=c8)
    average_frontier.to_csv(args.out_dir / "monthly_average_frontier.csv", index=False)
    c8_frontier.to_csv(args.out_dir / "monthly_c8_frontier.csv", index=False)

    all_metrics, all_projection = [], []
    for target, frontier in [("leaderboard_average", average_frontier), ("c8_equal_task", c8_frontier)]:
        detail, metrics = rolling_eval(frontier)
        detail.insert(0, "target", target)
        metrics.insert(0, "target", target)
        detail.to_csv(args.out_dir / f"{target}_rolling_predictions.csv", index=False)
        all_metrics.append(metrics)
        for horizon in (12, 24):
            all_projection.append(project(frontier, target, horizon))
    pd.concat(all_metrics, ignore_index=True).to_csv(args.out_dir / "baseline_metrics.csv", index=False)
    pd.concat(all_projection, ignore_index=True).to_csv(args.out_dir / "baseline_projections.csv", index=False)
    annual_audit(args.base / "leaderboard_extended_timeseries.csv").to_csv(args.out_dir / "annual_audit.csv", index=False)

    metadata = {
        "n_months_average": int(len(average_frontier)),
        "n_months_c8": int(len(c8_frontier)),
        "c8_models_joined": int(c8["Model"].nunique()) if not c8.empty else 0,
        "rolling_min_train_months": 3,
        "methods": METHODS,
        "frontier": "monthly q95",
        "warning": "Only seven rolling test points; baseline results are descriptive and not formal long-horizon validation.",
    }
    (args.out_dir / "run_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pd.concat(all_metrics, ignore_index=True).to_string(index=False))
    print("C8 joined models:", metadata["c8_models_joined"])


if __name__ == "__main__":
    main()
