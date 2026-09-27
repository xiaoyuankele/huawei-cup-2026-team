"""Nested panel quantile models on the detailed C8 task-score scale."""
from __future__ import annotations
import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
import statsmodels.api as sm
from q4_baseline_experiment import load_c8_scores

BASE = DATA_DIR
OUT = output_dir("c8_panel")
OUT.mkdir(exist_ok=True)


def read_data():
    lb = pd.read_csv(BASE / "leaderboard_cleaned.csv", parse_dates=["Submission Date"])
    c8 = load_c8_scores(BASE / "detailed_results")
    d = lb[["Model", "#Params (B)", "Submission Date", "Type"]].merge(c8[["Model", "c8_score"]], on="Model", how="inner")
    d = d.rename(columns={"#Params (B)": "params", "Submission Date": "date"})
    d["params"] = pd.to_numeric(d["params"], errors="coerce")
    d["type_clean"] = d["Type"].fillna("unknown").astype(str)
    d = d.dropna(subset=["date", "params", "c8_score"])
    d = d[d.params > 0].copy()
    d["score"] = d["c8_score"]
    d["year"] = d.date.dt.year
    d["time_month"] = (d.date.dt.to_period("M") - pd.Period("2024-06")).apply(lambda x: x.n)
    d["log_params"] = np.log1p(d.params)
    d = d.sort_values("date").drop_duplicates(["Model", "date", "type_clean"], keep="last")
    return d


def design(train, test, spec):
    use_params, use_time, use_type = spec
    cols = []
    if use_params: cols.append("log_params")
    if use_time: cols.append("time_month")
    tr = train[cols].copy() if cols else pd.DataFrame(index=train.index)
    te = test[cols].copy() if cols else pd.DataFrame(index=test.index)
    if use_type:
        a = pd.get_dummies(train.type_clean, prefix="type", dtype=float)
        b = pd.get_dummies(test.type_clean, prefix="type", dtype=float).reindex(columns=a.columns, fill_value=0.0)
        tr = pd.concat([tr, a], axis=1); te = pd.concat([te, b], axis=1)
    te = te.reindex(columns=tr.columns, fill_value=0.0)
    return sm.add_constant(tr.astype(float), has_constant="add"), sm.add_constant(te.astype(float), has_constant="add")


def pinball(y, p, tau):
    e = y - p
    return float(np.mean(np.maximum(tau * e, (tau - 1) * e)))


def main():
    d = read_data(); train = d[d.year == 2024].copy(); test = d[d.year == 2025].copy()
    specs = {"intercept": (False, False, False), "params": (True, False, False),
             "params_type": (True, False, True), "params_time": (True, True, False),
             "full": (True, True, True)}
    result, coefs, forecasts = [], [], []
    for tau in (.90, .95):
        for name, spec in specs.items():
            xtr, xte = design(train, test, spec)
            fit = sm.QuantReg(train.score.to_numpy(float), xtr).fit(q=tau, max_iter=5000, p_tol=1e-8)
            p = np.asarray(fit.predict(xte), float)
            y = test.score.to_numpy(float)
            result.append({"tau": tau, "model": name, "n_train": len(train), "n_test": len(test),
                           "pinball_loss": pinball(y, p, tau), "MAE": np.mean(np.abs(y-p)),
                           "RMSE": np.sqrt(np.mean((y-p)**2)), "mean_bias": np.mean(p-y),
                           "pred_min": p.min(), "pred_max": p.max()})
            coefs.append({"tau": tau, "model": name, "prsquared": float(fit.prsquared),
                          "params": json.dumps({str(k): float(v) for k,v in fit.params.items()}, ensure_ascii=False)})
            if tau == .95:
                for h in (12, 24):
                    future = test.copy(); future["time_month"] = 9 + h
                    _, xf = design(train, future, spec); pf = np.asarray(fit.predict(xf), float)
                    forecasts.append({"tau": tau, "model": name, "horizon_months": h, "n_profile": len(pf),
                                      "frontier_q95_conditional": np.quantile(pf, .95),
                                      "median_conditional": np.median(pf), "mean_conditional": np.mean(pf),
                                      "max_conditional": np.max(pf)})
    pd.DataFrame(result).to_csv(OUT / "nested_holdout_results.csv", index=False)
    pd.DataFrame(coefs).to_csv(OUT / "nested_fit_coefficients.csv", index=False)
    pd.DataFrame(forecasts).to_csv(OUT / "conditional_frontier_forecasts.csv", index=False)
    (OUT / "run_metadata.json").write_text(json.dumps({"n": len(d), "n_train": len(train), "n_test": len(test),
        "score": "detailed C8 six-task equal-weight score from JSON", "warning": "One short calendar split; descriptive only."}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pd.DataFrame(result).sort_values(["tau", "pinball_loss"]).to_string(index=False))
    print("\nForecasts")
    print(pd.DataFrame(forecasts).sort_values(["horizon_months", "frontier_q95_conditional"]).to_string(index=False))


if __name__ == "__main__":
    main()
