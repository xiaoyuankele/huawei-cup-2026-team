"""Q4 robustness checks for short, sparse frontier forecasting.

All operations are strictly time ordered.  The bootstrap intervals describe
uncertainty of the monthly cross-sectional q95 only; they do not claim to be
forecast intervals under future data-source drift.
"""
from __future__ import annotations

import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd

from q4_baseline_experiment import load_c8_scores

BASE = DATA_DIR
OUT = output_dir("robustness")
OUT.mkdir(exist_ok=True)


def frontier(raw: pd.DataFrame, score: str) -> pd.DataFrame:
    d = raw.dropna(subset=["Submission Date", score]).copy()
    d["month"] = d["Submission Date"].dt.to_period("M").dt.to_timestamp()
    d = d.sort_values(["Submission Date", "Model"]).drop_duplicates(["month", "Model"], keep="last")
    return d.groupby("month", sort=True)[score].agg(
        n="size", median="median", q90=lambda x: x.quantile(.90),
        q95=lambda x: x.quantile(.95), maximum="max"
    ).reset_index()


def pred(y: np.ndarray, method: str) -> float:
    if method == "naive_last":
        return float(y[-1])
    if method == "mean_last_3":
        return float(np.mean(y[-3:]))
    if method == "mean_all":
        return float(np.mean(y))
    if method == "linear_all":
        return float(np.polyval(np.polyfit(np.arange(len(y)), y, 1), len(y)))
    if method == "linear_last_4":
        z = y[-4:]
        return float(np.polyval(np.polyfit(np.arange(len(z)), z, 1), len(z)))
    raise ValueError(method)


def rolling(front: pd.DataFrame, min_train: int, method: str) -> pd.DataFrame:
    y = front.q95.to_numpy(float)
    rows = []
    for i in range(min_train, len(y)):
        p = pred(y[:i], method)
        e = p - y[i]
        rows.append({"test_month": front.month.iloc[i].strftime("%Y-%m"),
                     "min_train": min_train, "method": method,
                     "actual": y[i], "prediction": p, "error": e,
                     "abs_error": abs(e), "squared_error": e * e})
    return pd.DataFrame(rows)


def bootstrap_frontier(raw: pd.DataFrame, score: str, B: int = 2000, seed: int = 20260925) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    d = raw.dropna(subset=["Submission Date", score]).copy()
    d["month"] = d["Submission Date"].dt.to_period("M").dt.to_timestamp()
    d = d.sort_values(["Submission Date", "Model"]).drop_duplicates(["month", "Model"], keep="last")
    out = []
    for month, g in d.groupby("month", sort=True):
        vals = g[score].to_numpy(float)
        q = np.quantile(vals, .95)
        # sample-wise uncertainty only; resample models within the month
        idx = rng.integers(0, len(vals), size=(B, len(vals)))
        qs = np.quantile(vals[idx], .95, axis=1)
        out.append({"month": month, "n": len(vals), "q95": q,
                    "q95_boot_lo": np.quantile(qs, .025),
                    "q95_boot_hi": np.quantile(qs, .975),
                    "q95_boot_se": np.std(qs, ddof=1)})
    return pd.DataFrame(out)


def main() -> None:
    lb = pd.read_csv(BASE / "leaderboard_cleaned.csv", parse_dates=["Submission Date"])
    c8 = load_c8_scores(BASE / "detailed_results")
    joined = lb.merge(c8[["Model", "c8_score"]], on="Model", how="inner")
    joined = joined.dropna(subset=["c8_score"]).copy()
    # Restrict to the homogeneous Open LLM Leaderboard period used by Q4 baselines.
    joined = joined[(joined["Submission Date"] >= "2024-06-01") & (joined["Submission Date"] < "2025-04-01")]
    lb = lb[(lb["Submission Date"] >= "2024-06-01") & (lb["Submission Date"] < "2025-04-01")]

    all_metrics = []
    for target, raw, score in [
        ("c8_equal_task", joined, "c8_score"),
        ("leaderboard_average", lb, "Average ⬆️"),
    ]:
        f = frontier(raw, score)
        f.to_csv(OUT / f"{target}_frontier.csv", index=False)
        for min_train in (3, 5):
            for method in ("naive_last", "mean_last_3", "mean_all", "linear_all", "linear_last_4"):
                det = rolling(f, min_train, method)
                if det.empty:
                    continue
                all_metrics.append({"target": target, "min_train": min_train, "method": method,
                    "n_forecasts": len(det), "MAE": det.abs_error.mean(),
                    "RMSE": np.sqrt(det.squared_error.mean()),
                    "mean_bias": det.error.mean()})
                det.to_csv(OUT / f"{target}_{method}_min{min_train}_rolling.csv", index=False)
        boot = bootstrap_frontier(raw, score)
        boot.to_csv(OUT / f"{target}_frontier_bootstrap.csv", index=False)

    metrics = pd.DataFrame(all_metrics)
    metrics.to_csv(OUT / "robustness_metrics.csv", index=False)

    # Type-stratified descriptive q95: only report months with at least 10 models.
    s = joined.copy()
    s["month"] = s["Submission Date"].dt.to_period("M").dt.to_timestamp()
    strat = s.groupby(["month", "Type"], dropna=False).agg(n=("Model", "size"), q95=("c8_score", lambda x: x.quantile(.95))).reset_index()
    strat = strat[strat.n >= 10].sort_values(["month", "Type"])
    strat.to_csv(OUT / "c8_type_stratified_q95.csv", index=False)

    meta = {"period": "2024-06 to 2025-03", "months": 10, "bootstrap_B": 2000,
            "joined_c8_rows": int(len(joined)),
            "warning": "Bootstrap intervals cover cross-sectional model sampling only; temporal drift and benchmark changes remain unmodeled."}
    (OUT / "run_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(metrics.sort_values(["target", "min_train", "MAE"]).to_string(index=False))
    print("\nBootstrap C8:")
    print(pd.read_csv(OUT / "c8_equal_task_frontier_bootstrap.csv").to_string(index=False))
    print("\nType rows:", len(strat))


if __name__ == "__main__":
    main()
