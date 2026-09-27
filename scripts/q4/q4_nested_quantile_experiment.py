"""Nested low-complexity quantile models for Q4 time-out-of-sample testing."""
from __future__ import annotations

import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = DATA_DIR
OUT = output_dir("nested_quantile")
OUT.mkdir(exist_ok=True)


def read_data() -> pd.DataFrame:
    d = pd.read_parquet(BASE / "data" / "train-00000-of-00001.parquet")
    d["date"] = pd.to_datetime(d["Submission Date"], errors="coerce")
    d["score"] = pd.to_numeric(d["Average ⬆️"], errors="coerce")
    d["params"] = pd.to_numeric(d["#Params (B)"], errors="coerce")
    d["family"] = d["Base Model"].replace({"Removed": np.nan})
    d["type_clean"] = d["Type"].fillna("unknown").astype(str)
    d = d.dropna(subset=["date", "score", "params"])
    d = d[d.params > 0].copy()
    d["year"] = d.date.dt.year
    d["time_month"] = (d.date.dt.to_period("M") - pd.Period("2024-06")).apply(lambda x: x.n)
    d["log_params"] = np.log1p(d.params)
    d = d.sort_values("date").drop_duplicates(["fullname", "date", "type_clean", "Precision"], keep="last")
    return d


def design(train: pd.DataFrame, test: pd.DataFrame, spec: tuple[bool, bool, bool]):
    use_params, use_time, use_type = spec
    cols = []
    if use_params:
        cols.append("log_params")
    if use_time:
        cols.append("time_month")
    tr = train[cols].copy() if cols else pd.DataFrame(index=train.index)
    te = test[cols].copy() if cols else pd.DataFrame(index=test.index)
    if use_type:
        tr_type = pd.get_dummies(train["type_clean"], prefix="type", dtype=float)
        te_type = pd.get_dummies(test["type_clean"], prefix="type", dtype=float)
        te_type = te_type.reindex(columns=tr_type.columns, fill_value=0.0)
        tr = pd.concat([tr, tr_type], axis=1)
        te = pd.concat([te, te_type], axis=1)
    te = te.reindex(columns=tr.columns, fill_value=0.0)
    return sm.add_constant(tr.astype(float), has_constant="add"), sm.add_constant(te.astype(float), has_constant="add")


def pinball(y, p, tau):
    e = y - p
    return float(np.mean(np.maximum(tau * e, (tau - 1) * e)))


def main():
    d = read_data()
    train = d[d.year == 2024].copy()
    test = d[d.year == 2025].copy()
    seen = set(train.family.dropna())
    test["family_seen"] = test.family.isin(seen)
    specs = {
        "intercept": (False, False, False),
        "params": (True, False, False),
        "params_type": (True, False, True),
        "params_time": (True, True, False),
        "full": (True, True, True),
    }
    rows, coef, forecast_rows = [], [], []
    future_profiles = {"profile_2024": train.copy(), "profile_2025": test.copy()}
    for tau in (0.90, 0.95):
        for name, spec in specs.items():
            xtr, xte = design(train, test, spec)
            fit = sm.QuantReg(train.score.to_numpy(float), xtr).fit(q=tau, max_iter=5000, p_tol=1e-8)
            pred = np.asarray(fit.predict(xte), float)
            coef.append({"tau": tau, "model": name, "prsquared": float(fit.prsquared),
                         "params": json.dumps({str(k): float(v) for k, v in fit.params.items()}, ensure_ascii=False)})
            for subset, mask in [("all_2025", np.ones(len(test), dtype=bool)), ("unseen_family_2025", ~test.family_seen.to_numpy(bool))]:
                y = test.loc[mask, "score"].to_numpy(float)
                p = pred[mask]
                rows.append({"tau": tau, "model": name, "subset": subset, "n": len(y),
                             "pinball_loss": pinball(y, p, tau), "MAE": np.mean(np.abs(y-p)),
                             "RMSE": np.sqrt(np.mean((y-p)**2)),
                             "mean_bias_pred_minus_actual": np.mean(p-y),
                             "pred_min": p.min(), "pred_max": p.max()})
            if tau == 0.95:
                for prof_name, prof in future_profiles.items():
                    for horizon, month_ahead in [(12, 12), (24, 24)]:
                        future = prof.copy()
                        future["time_month"] = 9 + month_ahead
                        _, xf = design(train, future, spec)
                        pf = np.asarray(fit.predict(xf), float)
                        forecast_rows.append({
                            "tau": tau, "model": name, "profile": prof_name,
                            "horizon_months": horizon, "n_profile": len(pf),
                            "predicted_frontier_q95_of_conditional": np.quantile(pf, .95),
                            "predicted_median_conditional": np.median(pf),
                            "predicted_max_conditional": np.max(pf),
                            "predicted_mean_conditional": np.mean(pf),
                        })
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "nested_holdout_results.csv", index=False)
    pd.DataFrame(coef).to_csv(OUT / "nested_fit_coefficients.csv", index=False)
    pd.DataFrame(forecast_rows).to_csv(OUT / "conditional_frontier_forecasts.csv", index=False)
    meta = {"n_total": len(d), "n_train_2024": len(train), "n_test_2025": len(test),
            "n_unseen_family_2025": int((~test.family_seen).sum()), "specs": specs,
            "warning": "Only one calendar-year holdout; model comparison is descriptive and not causal."}
    (OUT / "run_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result.sort_values(["tau", "subset", "pinball_loss"]).to_string(index=False))
    print("\nCoefficients:")
    print(pd.DataFrame(coef)[["tau", "model", "prsquared"]].to_string(index=False))
    print("\nConditional frontier scenarios (tau=.95):")
    print(pd.DataFrame(forecast_rows).sort_values(["profile", "horizon_months", "predicted_frontier_q95_of_conditional"]).to_string(index=False))


if __name__ == "__main__":
    main()
