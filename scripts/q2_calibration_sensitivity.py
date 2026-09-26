"""Audit source offsets, A scale shifts, and Q-axis mapping sensitivity."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error


from q2_research_paths import REPO, RAW_ROOT as RAW, RUNS, source_ref
OUT = RUNS / "q2-calibration-sensitivity-20260925"
SCENARIO = RUNS / "q2-combined-scenario-20260925" / "combined_scenario_examples.csv"
BRIDGE = RUNS / "q2-quality-scaling-linkage-20260925" / "q1_to_q2_quality_linkage.csv"


def error_row(dataset: str, mode: str, y: np.ndarray, pred: np.ndarray, offset: float) -> dict:
    err = pred - y
    return {
        "dataset": dataset,
        "calibration_mode": mode,
        "n": int(len(y)),
        "offset_added": float(offset),
        "mae": float(mean_absolute_error(y, pred)),
        "rmse": float(math.sqrt(mean_squared_error(y, pred))),
        "mean_signed_error": float(np.mean(err)),
    }


def b_source_offsets() -> pd.DataFrame:
    bdir = RAW / "B_scaling_laws"
    b1 = pd.read_csv(bdir / "pythia_training_log_existing.csv")
    x1 = np.log(b1[["N_params_B", "D_tokens_B"]].to_numpy(float))
    model = LinearRegression().fit(x1, b1["val_loss"].to_numpy(float))
    rows = []
    specs = {
        "B1": b1,
        "B2": pd.read_csv(bdir / "cerebras_training_log.csv"),
        "B4": pd.read_csv(bdir / "scaling_baseline.csv"),
        "B5": pd.read_csv(bdir / "published_scaling_data.csv"),
    }
    for name, df in specs.items():
        y = df["val_loss"].to_numpy(float)
        base = model.predict(np.log(df[["N_params_B", "D_tokens_B"]].to_numpy(float)))
        median_offset = float(np.median(y - base))
        mean_offset = float(np.mean(y - base))
        rows.append(error_row(name, "raw", y, base, 0.0))
        rows.append(error_row(name, "median_offset_demo", y, base + median_offset, median_offset))
        rows.append(error_row(name, "mean_offset_demo", y, base + mean_offset, mean_offset))
    return pd.DataFrame(rows)


def read_a_pair(mix_name: str, loss_name: str) -> pd.DataFrame:
    base = RAW / "A_data_value" / "regmix_tables"
    mix = pd.read_csv(base / mix_name)
    loss = pd.read_csv(base / loss_name)
    df = mix.merge(loss, on="index", validate="one_to_one")
    p_cols = [c for c in df.columns if c.startswith("train_the_pile_")]
    loss_cols = [c for c in df.columns if c.startswith("metric/the_pile_")]
    df[p_cols] = df[p_cols].div(df[p_cols].sum(axis=1), axis=0)
    df["loss_mean_13_domains"] = df[loss_cols].mean(axis=1)
    return df


def a_scale_shift() -> tuple[pd.DataFrame, dict]:
    train = read_a_pair("train_mixture_1m.csv", "train_pile_loss_1m.csv")
    test1 = read_a_pair("test_mixture_1m.csv", "test_pile_loss_1m.csv")
    test60 = read_a_pair("test_mixture_60m.csv", "test_pile_loss_60m.csv")
    p_cols = [c for c in train.columns if c.startswith("train_the_pile_")]
    x_cols = p_cols[:-1]
    targets = [c for c in train.columns if c.startswith("metric/the_pile_")]
    rows = []
    for target in targets:
        model = Ridge(alpha=1e-5).fit(train[x_cols].to_numpy(float), train[target].to_numpy(float))
        for name, df in [("A4_A5_train_1m", train), ("A6_A7_test_1m", test1), ("A8_A9_test_60m", test60)]:
            pred = model.predict(df[x_cols].to_numpy(float))
            y = df[target].to_numpy(float)
            offset = float(np.median(y - pred))
            rows.append({
                "dataset": name,
                "target": target,
                "n": len(y),
                "raw_mae": mean_absolute_error(y, pred),
                "median_offset": offset,
                "offset_adjusted_mae": mean_absolute_error(y, pred + offset),
                "raw_mean_signed_error": np.mean(pred - y),
            })
    a6 = test1.set_index("index")
    a8 = test60.set_index("index")
    common = sorted(set(a6.index) & set(a8.index))
    loss_cols = targets
    pair = a8.loc[common, loss_cols].to_numpy(float) - a6.loc[common, loss_cols].to_numpy(float)
    shift = {
        "n_common_mixtures": len(common),
        "mean_shift_A8_minus_A6_over_13_domains": float(pair.mean()),
        "median_shift_A8_minus_A6_over_13_domains": float(np.median(pair)),
        "share_negative_shift": float(np.mean(pair < 0)),
    }
    return pd.DataFrame(rows), shift


def q_mapping_sensitivity() -> tuple[pd.DataFrame, dict]:
    bridge = pd.read_csv(BRIDGE)
    corr = float(bridge[["Q_A_topsis_0_1", "quality_score_soft_proxy_0_1"]].corr().iloc[0, 1])
    scenario = pd.read_csv(SCENARIO)
    keys = ["source_row_dataset", "source_row_index", "N_params_B", "D_tokens_B", "scenario_variant"]
    top = scenario[scenario["quality_axis"] == "Q_A_topsis_0_1"][keys + ["predicted_loss"]].rename(columns={"predicted_loss": "pred_topsis"})
    soft = scenario[scenario["quality_axis"] == "quality_score_soft_proxy_0_1"][keys + ["predicted_loss"]].rename(columns={"predicted_loss": "pred_soft"})
    merged = top.merge(soft, on=keys, how="inner")
    merged["soft_minus_topsis"] = merged["pred_soft"] - merged["pred_topsis"]
    summary = (
        merged.groupby("scenario_variant", as_index=False)
        .agg(n=("soft_minus_topsis", "size"),
             min_difference=("soft_minus_topsis", "min"),
             median_difference=("soft_minus_topsis", "median"),
             max_difference=("soft_minus_topsis", "max"),
             mean_absolute_difference=("soft_minus_topsis", lambda x: float(np.mean(np.abs(x)))))
    )
    return summary, {"Q_A_topsis_vs_soft_corr": corr, "paired_scenarios": len(merged)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    b = b_source_offsets()
    a, a_shift = a_scale_shift()
    q, q_meta = q_mapping_sensitivity()
    b.to_csv(OUT / "B_source_offset_audit.csv", index=False, encoding="utf-8-sig")
    a.to_csv(OUT / "A_scale_offset_audit.csv", index=False, encoding="utf-8-sig")
    q.to_csv(OUT / "Q_axis_sensitivity.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "run_id": "q2-calibration-sensitivity-20260925",
        "status": "REVIEW_REQUIRED",
        "B_source_offset_note": "Offsets are post-hoc diagnostics; they are not a validated transport rule for unseen sources.",
        "A_scale_shift": a_shift,
        "Q_mapping": q_meta,
        "conclusion": "Source offsets and Q-axis choices materially change absolute predictions; use source-specific calibration and report sensitivity.",
    }
    (OUT / "sensitivity_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = f"""# Q2 calibration and sensitivity audit

This run quantifies source offsets and quality-axis uncertainty without treating post-hoc offsets as new observations.

## B source offsets

The B1 log-N-D baseline has substantial source shifts on B2/B4/B5. Median or mean offset correction is reported only as a diagnostic. It cannot be applied to an unseen source without a bridge observation.

## A scale shift

The common A6/A8 mixtures provide a direct within-A scale comparison. The observed A8 minus A6 mean shift across 13 domains is {a_shift['mean_shift_A8_minus_A6_over_13_domains']:.4f}; the negative share is {a_shift['share_negative_shift']:.3f}. This supports a scale shift, but does not recover B's token-count coordinate.

## Q-axis sensitivity

The Q1 TOPSIS and soft axes have correlation {q_meta['Q_A_topsis_vs_soft_corr']:.4f}. Their differences are propagated through the scenario model in `Q_axis_sensitivity.csv`. This is a mapping sensitivity result, not an empirical calibration.
"""
    (OUT / "calibration_sensitivity_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
