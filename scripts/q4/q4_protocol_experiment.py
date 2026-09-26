"""Q4 protocol experiment for the sparse 10-month C8 frontier.

This script is deliberately conservative: the primary score is the detailed
six-task equal-weight C8 score, validation is chronological 70/30 (7 months
train, 3 months test), and the 12-month section is labelled as a scenario
projection rather than a validated 12-step forecast.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
from q4_baseline_experiment import GROUPS, load_c8_scores


SEED = 20260926
MONTHS = pd.period_range("2024-06", "2025-03", freq="M").to_timestamp()
TYPE_ORDER = ["pretrained", "chat", "fine-tuned", "merge"]
METHODS = ["naive_last", "mean_last_3", "linear_all", "linear_last_4"]


def canonical_type(value: object) -> str:
    s = str(value or "").lower()
    if "pretrained" in s:
        return "pretrained"
    if "chat" in s:
        return "chat"
    if "fine-tuned" in s or "fine tuned" in s:
        return "fine-tuned"
    if "merge" in s or "moerge" in s:
        return "merge"
    return "other"


def load_joined(base: Path) -> pd.DataFrame:
    lb = pd.read_csv(base / "leaderboard_cleaned.csv", parse_dates=["Submission Date"])
    c8 = load_c8_scores(base / "detailed_results")
    d = lb.merge(c8[["Model", "c8_score"]], on="Model", how="inner")
    d = d.dropna(subset=["Submission Date", "c8_score"]).copy()
    d["month"] = d["Submission Date"].dt.to_period("M").dt.to_timestamp()
    d = d[d["month"].isin(MONTHS)].copy()
    d["type_clean"] = d["Type"].map(canonical_type)
    d["model_family"] = d["Model"].astype(str).str.split("/", n=1).str[0]
    d["params"] = pd.to_numeric(d["#Params (B)"], errors="coerce")
    d["time_month"] = (d["month"].dt.to_period("M") - MONTHS[0].to_period("M")).apply(lambda x: x.n)
    d["log_params"] = np.log1p(d["params"])
    d = d.sort_values(["Submission Date", "Model"]).drop_duplicates(["Model", "month"], keep="last")
    return d


def frontier(d: pd.DataFrame, score: str = "c8_score") -> pd.DataFrame:
    x = d.groupby("month", sort=True)[score].agg(
        n="size", median="median", q90=lambda z: z.quantile(.90),
        q95=lambda z: z.quantile(.95), maximum="max"
    ).reset_index()
    return x.set_index("month").reindex(MONTHS).rename_axis("month").reset_index()


def predict(y: np.ndarray, method: str) -> float:
    if method == "naive_last":
        return float(y[-1])
    if method == "mean_last_3":
        return float(np.mean(y[-3:]))
    if method == "linear_all":
        return float(np.polyval(np.polyfit(np.arange(len(y)), y, 1), len(y)))
    if method == "linear_last_4":
        z = y[-4:]
        return float(np.polyval(np.polyfit(np.arange(len(z)), z, 1), len(z)))
    raise ValueError(method)


def horizon_metrics(f: pd.DataFrame, cohort: str, score_name: str) -> pd.DataFrame:
    """Evaluate only forecasts whose origin is in the 7-month training block."""
    y = f["q95"].to_numpy(float)
    rows = []
    train_end = 7
    for h in (1, 3):
        # origin index 6 is the end of the training block; h=1 has three
        # test observations, h=3 has one. Missing cohort months are excluded.
        for origin in range(train_end - 1, len(y) - h):
            if origin < 3 or not np.isfinite(y[origin]) or not np.isfinite(y[origin + h]):
                continue
            train_y = y[: origin + 1]
            if np.isnan(train_y).any():
                continue
            for method in METHODS:
                if method == "mean_last_3" and len(train_y) < 3:
                    continue
                if method == "linear_last_4" and len(train_y) < 4:
                    continue
                pred = predict(train_y, method)
                actual = float(y[origin + h])
                err = pred - actual
                rows.append({"score": score_name, "cohort": cohort, "horizon_months": h,
                             "origin_month": f["month"].iloc[origin].strftime("%Y-%m"),
                             "test_month": f["month"].iloc[origin + h].strftime("%Y-%m"),
                             "method": method, "actual_q95": actual, "prediction": pred,
                             "error": err, "absolute_error": abs(err), "squared_error": err * err})
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail
    out = detail.groupby(["score", "cohort", "horizon_months", "method"], as_index=False).agg(
        n_forecasts=("error", "size"), MAE=("absolute_error", "mean"),
        RMSE=("squared_error", lambda z: float(np.sqrt(np.mean(z)))),
        mean_bias=("error", "mean"),
        R2=("error", lambda z: np.nan),
    )
    # R2 needs the actual values; it is undefined for the single h=3 forecast.
    for idx, row in out.iterrows():
        z = detail[(detail.score == row.score) & (detail.cohort == row.cohort) &
                   (detail.horizon_months == row.horizon_months) & (detail.method == row.method)]
        if len(z) >= 2 and np.var(z.actual_q95) > 0:
            out.loc[idx, "R2"] = 1 - np.sum((z.prediction - z.actual_q95) ** 2) / np.sum((z.actual_q95 - z.actual_q95.mean()) ** 2)
    return out


def panel_design(train: pd.DataFrame, test: pd.DataFrame, include_type: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["log_params", "time_month"]
    a = train[cols].copy(); b = test[cols].copy()
    if include_type:
        da = pd.get_dummies(train["type_clean"], prefix="type", dtype=float)
        db = pd.get_dummies(test["type_clean"], prefix="type", dtype=float).reindex(columns=da.columns, fill_value=0.0)
        a = pd.concat([a, da], axis=1); b = pd.concat([b, db], axis=1)
    b = b.reindex(columns=a.columns, fill_value=0.0)
    return sm.add_constant(a.astype(float), has_constant="add"), sm.add_constant(b.astype(float), has_constant="add")


def panel_comparison(d: pd.DataFrame, out: Path) -> pd.DataFrame:
    train = d[d["month"].isin(MONTHS[:7])].dropna(subset=["params"]).copy()
    test = d[d["month"].isin(MONTHS[7:])].dropna(subset=["params"]).copy()
    rows = []
    for cohort, tr, te, use_type in [
        ("all_four_types", train[train.type_clean.isin(TYPE_ORDER)], test[test.type_clean.isin(TYPE_ORDER)], True),
        ("pretrained_only", train[train.type_clean == "pretrained"], test[test.type_clean == "pretrained"], False),
    ]:
        for tau in (.90, .95):
            xtr, xte = panel_design(tr, te, use_type)
            fit = sm.QuantReg(tr.c8_score.to_numpy(float), xtr).fit(q=tau, max_iter=5000, p_tol=1e-8)
            pred = np.asarray(fit.predict(xte), float)
            y = te.c8_score.to_numpy(float)
            rows.append({"cohort": cohort, "tau": tau, "n_train": len(tr), "n_test": len(te),
                         "pinball_loss": float(np.mean(np.maximum(tau * (y - pred), (tau - 1) * (y - pred)))),
                         "MAE": float(np.mean(np.abs(y - pred))), "RMSE": float(np.sqrt(np.mean((y - pred) ** 2))),
                         "bias": float(np.mean(pred - y)), "R2": float(1 - np.sum((pred-y)**2) / np.sum((y-y.mean())**2)),
                         "pseudo_R2": float(fit.prsquared)})
    result = pd.DataFrame(rows)
    result.to_csv(out / "c8_70_30_model_comparison.csv", index=False)
    return result


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values); v = values[order]; w = weights[order]
    c = np.cumsum(w) / np.sum(w)
    return float(v[np.searchsorted(c, q, side="left")])


def compute_elasticities(path: Path) -> tuple[float, float]:
    q3 = pd.read_csv(path)
    q3 = q3[q3["L_ctx"] == 4096]
    kN = float(np.polyfit(np.log(q3.budget_FLOPs), np.log(q3.N_B), 1)[0])
    kD = float(np.polyfit(np.log(q3.budget_FLOPs), np.log(q3.D_B), 1)[0])
    return kN, kD


def scenario_projection(d: pd.DataFrame, out: Path, q3_file: Path) -> pd.DataFrame:
    """Fit on all observed months and project 12 months; no validation claim."""
    use = d[d.type_clean.isin(TYPE_ORDER)].dropna(subset=["params"]).copy()
    x, _ = panel_design(use, use, True)
    fit = sm.QuantReg(use.c8_score.to_numpy(float), x).fit(q=.95, max_iter=5000, p_tol=1e-8)
    profile = use[use.month == MONTHS[-1]].copy()
    if profile.empty:
        profile = use.sort_values("month").tail(100).copy()
    kN, kD = compute_elasticities(q3_file)
    baseline_shares = profile.type_clean.value_counts(normalize=True).reindex(TYPE_ORDER, fill_value=0.0)
    rows = []
    multipliers = {"control_1x": 1.0, "conservative_1_5x": 1.5, "overall_stock_2_3x": 2.3,
                   "frontier_low_4x": 4.0, "frontier_high_5x": 5.0}
    for scenario, mult in multipliers.items():
        for type_shift in ["baseline", "pretrained_plus_10pp", "pretrained_minus_10pp", "chat_plus_10pp", "chat_minus_10pp"]:
            shares = baseline_shares.copy()
            if type_shift != "baseline":
                typ = type_shift.split("_")[0]
                delta = .10 if "plus" in type_shift else -.10
                delta = max(-shares[typ], delta)
                rest = [z for z in TYPE_ORDER if z != typ]
                shares[rest] *= (1 - shares[typ] - delta) / max(1e-12, shares[rest].sum())
                shares[typ] += delta
            nscale = mult ** kN; dscale = mult ** kD
            future = profile.copy(); future["params"] *= nscale; future["log_params"] = np.log1p(future.params)
            for form, time_value in [("platform", float(use.time_month.max())), ("trend", float(use.time_month.max() + 12))]:
                future["time_month"] = time_value
                _, xf = panel_design(use, future, True)
                pred = np.asarray(fit.predict(xf), float)
                weights = future.type_clean.map(shares).to_numpy(float)
                # weighted mean and weighted q95 are profile summaries, not prediction CIs
                rows.append({"scenario": scenario, "compute_multiplier": mult, "type_shift": type_shift,
                             "forecast_form": form, "horizon_months": 12, "N_scale": nscale, "D_scale": dscale,
                             "profile_n": len(future), "q95_point": weighted_quantile(pred, weights, .95),
                             "weighted_mean": float(np.average(pred, weights=weights)),
                             "profile_min": float(np.min(pred)), "profile_max": float(np.max(pred)),
                             "interval_note": "profile reweighting range; not a temporal forecast interval"})
    result = pd.DataFrame(rows)
    result.to_csv(out / "c8_12m_platform_trend_scenarios.csv", index=False)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=DATA_DIR)
    ap.add_argument("--run-dir", type=Path, default=RUN_DIR)
    ap.add_argument("--q3-optima", type=Path, default=q3_optima_file())
    args = ap.parse_args()
    out = args.run_dir / "artifacts" / "protocol"
    out.mkdir(parents=True, exist_ok=True)
    d = load_joined(args.base)
    d.to_csv(out / "joined_c8_dataset.csv", index=False)

    audit = {"rows_joined": int(len(d)), "models": int(d.Model.nunique()),
             "months": [x.strftime("%Y-%m") for x in MONTHS],
             "month_counts": {x.strftime("%Y-%m"): int((d.month == x).sum()) for x in MONTHS},
             "type_counts": {k: int((d.type_clean == k).sum()) for k in sorted(d.type_clean.unique())},
             "split": {"train_months": [x.strftime("%Y-%m") for x in MONTHS[:7]], "test_months": [x.strftime("%Y-%m") for x in MONTHS[7:]]},
             "metadata_fields_available": {k: False for k in ["model_family", "training_data_volume", "training_compute", "eval_version"]},
             "metadata_fields_derived": ["model_family=namespace_prefix"],
             "primary_score": "C8 detailed six-task equal-weight mean x 100",
             "warning": "12-month outputs are scenario projections, not validated 12-step forecasts; profile intervals are not prediction intervals."}
    (out / "data_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    metric_frames = []
    for cohort, subset in [("all_four_types", d[d.type_clean.isin(TYPE_ORDER)]), ("pretrained_only", d[d.type_clean == "pretrained"])]:
        metric_frames.append(horizon_metrics(frontier(subset), cohort, "c8_q95"))
    avg = d.copy(); avg["avg_score"] = pd.to_numeric(avg["Average ⬆️"], errors="coerce")
    metric_frames.append(horizon_metrics(frontier(avg, "avg_score"), "all_models", "leaderboard_average_q95"))
    metrics = pd.concat(metric_frames, ignore_index=True)
    metrics.to_csv(out / "c8_rolling_horizon_metrics.csv", index=False)
    comp = panel_comparison(d, out)
    scen = scenario_projection(d, out, args.q3_optima)
    summary = {"audit": audit, "best_rolling": metrics.sort_values("MAE").head(5).to_dict("records"),
               "best_70_30": comp.sort_values("pinball_loss").head(4).to_dict("records"),
               "scenario_rows": int(len(scen))}
    (out / "protocol_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(metrics.to_string(index=False))
    print("\n70/30 model comparison")
    print(comp.to_string(index=False))
    print("\n12m scenarios written:", len(scen))


if __name__ == "__main__":
    main()
