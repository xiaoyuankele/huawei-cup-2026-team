"""Audit the loss-to-benchmark bridge without mixing comparability levels."""
from __future__ import annotations

import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd

BASE = DATA_DIR
OUT = output_dir("loss_bridge")
OUT.mkdir(exist_ok=True)
SCORES = ["LB_Average", "LB_IFEval", "LB_BBH", "LB_MATH", "LB_GPQA", "LB_MUSR", "LB_MMLU_PRO"]


def fit(x, y):
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def loo_mae(x, y):
    errs = []
    for i in range(len(x)):
        keep = np.arange(len(x)) != i
        b, a = fit(x[keep], y[keep])
        errs.append(a + b * x[i] - y[i])
    return float(np.mean(np.abs(errs)))


def bootstrap(x, y, B=5000, seed=20260925):
    rng = np.random.default_rng(seed)
    n = len(x)
    slopes, pred18, pred20, pred22 = [], [], [], []
    for _ in range(B):
        ix = rng.integers(0, n, n)
        b, a = fit(x[ix], y[ix])
        slopes.append(b); pred18.append(a + b * 1.8); pred20.append(a + b * 2.0); pred22.append(a + b * 2.2)
    def ci(v): return [float(np.quantile(v, .025)), float(np.quantile(v, .975))]
    return {"slope_ci95": ci(slopes), "pred_at_loss_1.8_ci95": ci(pred18),
            "pred_at_loss_2.0_ci95": ci(pred20), "pred_at_loss_2.2_ci95": ci(pred22)}


def main():
    d = pd.read_csv(BASE / "loss_benchmark_bridge.csv")
    d["level"] = np.where(d["Loss_Comparability"].str.startswith("High"), "High", "Medium")
    rows, tasks = [], []
    for level, g in d.groupby("level", sort=True):
        x = g.Val_Loss.to_numpy(float)
        for score in SCORES:
            y = g[score].to_numpy(float)
            slope, intercept = fit(x, y)
            boot = bootstrap(x, y)
            rows.append({"comparability": level, "n": len(g), "score": score,
                         "slope_score_per_loss": slope, "intercept": intercept,
                         "loo_MAE": loo_mae(x, y), **boot})
        # Store model-level predictions for the primary Average bridge.
        b, a = fit(x, g.LB_Average.to_numpy(float))
        tmp = g[["Model", "Val_Loss", "LB_Average"]].copy()
        tmp["comparability"] = level
        tmp["fitted_LB_Average"] = a + b * x
        tmp["residual"] = tmp.fitted_LB_Average - tmp.LB_Average
        tasks.append(tmp)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "bridge_regression_summary.csv", index=False)
    pd.concat(tasks, ignore_index=True).to_csv(OUT / "bridge_average_fitted.csv", index=False)
    meta = {"source": str(BASE / "loss_benchmark_bridge.csv"), "high_n": int((d.level == "High").sum()),
            "medium_n": int((d.level == "Medium").sum()),
            "warning": "Medium comparability rows are sensitivity only; no loss-to-frontier causal claim is made."}
    (OUT / "run_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result[result.score == "LB_Average"].to_string(index=False))
    print("\nHigh-comparability task slopes:")
    print(result[result.comparability == "High"].to_string(index=False))


if __name__ == "__main__":
    main()
