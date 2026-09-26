"""Strict time/family holdout for a low-complexity Q4 panel quantile baseline."""
from __future__ import annotations

import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import ks_2samp


BASE = DATA_DIR
OUT = output_dir("family_quantile")
OUT.mkdir(exist_ok=True)


def read_data() -> pd.DataFrame:
    p = BASE / "data" / "train-00000-of-00001.parquet"
    d = pd.read_parquet(p)
    d["date"] = pd.to_datetime(d["Submission Date"], errors="coerce")
    d["params"] = pd.to_numeric(d["#Params (B)"], errors="coerce")
    d["score"] = pd.to_numeric(d["Average ⬆️"], errors="coerce")
    d["family"] = d["Base Model"].replace({"Removed": np.nan})
    d["model_id"] = d["fullname"].astype(str)
    d["type_clean"] = d["Type"].fillna("unknown").astype(str)
    d = d.dropna(subset=["date", "params", "score"])
    d = d[d["params"] > 0].copy()
    d["year"] = d["date"].dt.year
    d["log_params"] = np.log1p(d["params"])
    d["time_month"] = (d["date"].dt.to_period("M") - pd.Period("2024-06")).apply(lambda x: x.n)
    # Use latest entry per model/date/type/precision; do not collapse by Model sha.
    d = d.sort_values("date").drop_duplicates(["model_id", "date", "type_clean", "Precision"], keep="last")
    return d


def make_design(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["log_params", "time_month"]
    tr = pd.get_dummies(train[cols + ["type_clean"]], columns=["type_clean"], dtype=float)
    te = pd.get_dummies(test[cols + ["type_clean"]], columns=["type_clean"], dtype=float)
    te = te.reindex(columns=tr.columns, fill_value=0.0)
    return sm.add_constant(tr, has_constant="add"), sm.add_constant(te, has_constant="add")


def pinball(y: np.ndarray, pred: np.ndarray, tau: float) -> float:
    e = y - pred
    return float(np.mean(np.maximum(tau * e, (tau - 1) * e)))


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, tau: float) -> tuple[np.ndarray, dict]:
    x_train, x_test = make_design(train, test)
    model = sm.QuantReg(train["score"].to_numpy(float), x_train)
    fit = model.fit(q=tau, max_iter=2000, p_tol=1e-8)
    pred = np.asarray(fit.predict(x_test), dtype=float)
    return pred, {
        "tau": tau,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "params": {str(k): float(v) for k, v in fit.params.items()},
        "prsquared": float(fit.prsquared),
    }


def main() -> None:
    d = read_data()
    train = d[d["year"] == 2024].copy()
    test = d[d["year"] == 2025].copy()
    seen = set(train["family"].dropna())
    test["family_seen_in_train"] = test["family"].isin(seen)

    # Descriptive homogeneity audit.
    audit_rows = []
    for label, g in d.groupby(["year", "type_clean"], dropna=False):
        audit_rows.append({"year": label[0], "type": label[1], "n": len(g), "median_score": g["score"].median(), "q95": g["score"].quantile(.95), "median_params_B": g["params"].median()})
    audit = pd.DataFrame(audit_rows)
    audit.to_csv(OUT / "year_type_audit.csv", index=False)

    # 2024 vs 2025 distribution shift, with a large-sample diagnostic only.
    ks = ks_2samp(train["score"], test["score"])
    shift = pd.DataFrame([{
        "n_train": len(train), "n_test": len(test), "n_test_unseen_family": int((~test["family_seen_in_train"]).sum()),
        "train_q95": train["score"].quantile(.95), "test_q95": test["score"].quantile(.95),
        "ks_statistic": float(ks.statistic), "ks_pvalue": float(ks.pvalue),
    }])
    shift.to_csv(OUT / "time_shift_audit.csv", index=False)

    result_rows = []
    pred_rows = []
    fit_metadata = {}
    for tau in (0.90, 0.95):
        pred, meta = fit_predict(train, test, tau)
        fit_metadata[str(tau)] = meta
        for subset_name, mask in [("all_2025", np.ones(len(test), dtype=bool)), ("unseen_family_2025", ~test["family_seen_in_train"].to_numpy(bool))]:
            y = test.loc[mask, "score"].to_numpy(float)
            p = pred[mask]
            if len(y) == 0:
                continue
            result_rows.append({
                "tau": tau, "subset": subset_name, "model": "quantile_regression", "n": len(y),
                "MAE": float(np.mean(np.abs(y - p))),
                "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
                "pinball_loss": pinball(y, p, tau),
                "mean_bias_pred_minus_actual": float(np.mean(p - y)),
            })
        tmp = test[["model_id", "date", "family", "type_clean", "params", "score", "family_seen_in_train"]].copy()
        tmp["tau"] = tau
        tmp["prediction"] = pred
        pred_rows.append(tmp)

    # Constant baselines for the same 2025 holdout: train-year q90/q95.
    for tau in (0.90, 0.95):
        constant = train["score"].quantile(tau)
        for subset_name, mask in [("all_2025", np.ones(len(test), dtype=bool)), ("unseen_family_2025", ~test["family_seen_in_train"].to_numpy(bool))]:
            y = test.loc[mask, "score"].to_numpy(float)
            p = np.repeat(constant, len(y))
            result_rows.append({
                "tau": tau, "subset": subset_name, "model": "2024_constant_frontier", "n": len(y),
                "MAE": float(np.mean(np.abs(y - p))), "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
                "pinball_loss": pinball(y, p, tau), "mean_bias_pred_minus_actual": float(np.mean(p - y)),
            })

    results = pd.DataFrame(result_rows)
    results["model"] = results.get("model", "quantile_regression")
    results.to_csv(OUT / "quantile_holdout_results.csv", index=False)
    pd.concat(pred_rows, ignore_index=True).to_csv(OUT / "quantile_holdout_predictions.csv", index=False)
    (OUT / "fit_metadata.json").write_text(json.dumps(fit_metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print("DATA", {"n": len(d), "train_2024": len(train), "test_2025": len(test), "unseen_family_test": int((~test["family_seen_in_train"]).sum())})
    print("SHIFT\n", shift.to_string(index=False))
    print("RESULTS\n", results.to_string(index=False))


if __name__ == "__main__":
    main()
