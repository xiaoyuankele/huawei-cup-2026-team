"""Error evaluation for Q4 baselines and detailed-C8 quantile panel models."""
from __future__ import annotations
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

from q4_baseline_experiment import rolling_eval
from q4_c8_panel_quantile_experiment import read_data, design, pinball

OUT = output_dir("error"); OUT.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")


def summarize_errors(detail: pd.DataFrame, target: str, window: int | None = None) -> pd.DataFrame:
    rows = []
    for method, g in detail.groupby("method"):
        e = g.error.to_numpy(float)
        rows.append({"target": target, "method": method, "n": len(g),
                     "MAE": np.mean(np.abs(e)), "RMSE": np.sqrt(np.mean(e**2)),
                     "mean_bias": np.mean(e), "median_abs_error": np.median(np.abs(e)),
                     "max_abs_error": np.max(np.abs(e)),
                     "under_prediction_rate": np.mean(e < 0),
                     "over_prediction_rate": np.mean(e > 0),
                     "window_min_train": window})
    return pd.DataFrame(rows)


def panel_error_eval():
    d = read_data(); train = d[d.year == 2024].copy(); test = d[d.year == 2025].copy()
    specs = {"intercept": (False, False, False), "params": (True, False, False),
             "params_type": (True, False, True), "params_time": (True, True, False),
             "full": (True, True, True)}
    overall, by_type = [], []
    pred_store = []
    for tau in (.90, .95):
        for name, spec in specs.items():
            xtr, xte = design(train, test, spec)
            fit = sm.QuantReg(train.score.to_numpy(float), xtr).fit(q=tau, max_iter=5000, p_tol=1e-8)
            p = np.asarray(fit.predict(xte), float); y = test.score.to_numpy(float)
            e = p - y
            overall.append({"tau": tau, "model": name, "n": len(y),
                            "MAE": np.mean(np.abs(e)), "RMSE": np.sqrt(np.mean(e**2)),
                            "mean_bias_pred_minus_actual": np.mean(e),
                            "median_abs_error": np.median(np.abs(e)),
                            "max_abs_error": np.max(np.abs(e)),
                            "pinball_loss": pinball(y, p, tau),
                            "coverage_y_le_pred": np.mean(y <= p),
                            "coverage_error": np.mean(y <= p) - tau})
            tmp = test[["type_clean", "score"]].copy(); tmp["prediction"] = p; tmp["error"] = e
            tmp["tau"] = tau; tmp["model"] = name; pred_store.append(tmp)
            if name == "full":
                for typ, g in tmp.groupby("type_clean", dropna=False):
                    yy = g.score.to_numpy(float); pp = g.prediction.to_numpy(float); ee = pp - yy
                    by_type.append({"tau": tau, "type": typ, "n": len(g),
                                    "MAE": np.mean(np.abs(ee)), "RMSE": np.sqrt(np.mean(ee**2)),
                                    "mean_bias_pred_minus_actual": np.mean(ee),
                                    "pinball_loss": pinball(yy, pp, tau),
                                    "coverage_y_le_pred": np.mean(yy <= pp),
                                    "coverage_error": np.mean(yy <= pp) - tau})
    return pd.DataFrame(overall), pd.DataFrame(by_type), pd.concat(pred_store, ignore_index=True)


def main():
    all_base = []
    for target, fn in [("c8_equal_task", output_dir("baseline") / "c8_equal_task_rolling_predictions.csv"),
                       ("leaderboard_average", output_dir("baseline") / "leaderboard_average_rolling_predictions.csv")]:
        d = pd.read_csv(fn)
        all_base.append(summarize_errors(d, target, int(d.get("min_train", pd.Series([3])).iloc[0])))
    # Include the stricter min-train=5 sensitivity runs from robustness outputs.
    for target in ("c8_equal_task", "leaderboard_average"):
        for method in ("naive_last", "mean_last_3", "mean_all", "linear_all", "linear_last_4"):
            fn = output_dir("robustness") / f"{target}_{method}_min5_rolling.csv"
            if fn.exists():
                all_base.append(summarize_errors(pd.read_csv(fn), target, 5))
    base_metrics = pd.concat(all_base, ignore_index=True)
    base_metrics.to_csv(OUT / "baseline_error_metrics.csv", index=False)
    panel, by_type, preds = panel_error_eval()
    panel.to_csv(OUT / "panel_error_metrics.csv", index=False)
    by_type.to_csv(OUT / "panel_full_by_type_error_metrics.csv", index=False)
    preds.to_csv(OUT / "panel_predictions_errors.csv", index=False)
    print("BASELINE ERRORS\n", base_metrics.to_string(index=False))
    print("\nPANEL ERRORS\n", panel.sort_values(["tau", "pinball_loss"]).to_string(index=False))
    print("\nFULL BY TYPE\n", by_type.to_string(index=False))


if __name__ == "__main__":
    main()
