"""Validate the three local Q2 model components on the original attachments.

The script deliberately keeps the observed blocks separate:
* B1 fits the N-D scaling baseline;
* A4/A5 fit the mixture response and are evaluated on A6-A11;
* B6/B7 provide a grouped quality-response check;
* A12-A15, B8 and B10 are audit/extrapolation sources only.

Outputs are CSV/JSON/Markdown evidence files, not a fabricated complete
observational (N, D, Q, p, Loss) table.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


from q2_research_paths import REPO, RAW_ROOT as RAW, RUNS, source_ref
OUT = RUNS / "q2-local-model-validation-20260925"


def metrics(y_true: pd.Series, y_pred: np.ndarray, label: str, n: int | None = None, model_type: str = "model") -> dict:
    y = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    rmse = math.sqrt(mean_squared_error(y, pred))
    denom = np.maximum(np.abs(y), 1e-8)
    return {
        "dataset": label,
        "model_type": model_type,
        "n": int(len(y) if n is None else n),
        "mae": float(mean_absolute_error(y, pred)),
        "rmse": float(rmse),
        "r2": float(r2_score(y, pred)) if len(y) > 1 else float("nan"),
        "mean_signed_error": float(np.mean(pred - y)),
        "mean_absolute_percentage": float(np.mean(np.abs(pred - y) / denom)),
    }


def fit_scale_model(train: pd.DataFrame) -> LinearRegression:
    x = np.log(train[["N_params_B", "D_tokens_B"]].astype(float))
    y = train["val_loss"].astype(float)
    model = LinearRegression().fit(x, y)
    return model


def prepare_a() -> dict[str, pd.DataFrame]:
    base = RAW / "A_data_value" / "regmix_tables"
    specs = {
        "A4_A5_train_1m": ("train_mixture_1m.csv", "train_pile_loss_1m.csv", "train", "1m", True),
        "A6_A7_test_1m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv", "test", "1m", True),
        "A8_A9_test_60m": ("test_mixture_60m.csv", "test_pile_loss_60m.csv", "test", "60m", True),
        "A10_A11_test_1b": ("test_mixture_1B.csv", "test_pile_loss_1B.csv", "test", "1b", True),
        "A12_A13_est_10b": ("est_mixture_10b.csv", "est_pile_loss_10b.csv", "estimate", "10b", False),
        "A14_A15_est_70b": ("est_mixture_70b.csv", "est_pile_loss_70b.csv", "estimate", "70b", False),
    }
    out = {}
    for name, (mix_name, loss_name, role, scale, observed) in specs.items():
        mix = pd.read_csv(base / mix_name)
        loss = pd.read_csv(base / loss_name)
        if not mix["index"].equals(loss["index"]):
            loss = loss.set_index("index").loc[mix["index"]].reset_index()
        df = mix.merge(loss, on="index", how="inner", validate="one_to_one")
        p_cols = [c for c in df.columns if c.startswith("train_the_pile_")]
        l_cols = [c for c in df.columns if c.startswith("metric/the_pile_")]
        df[p_cols] = df[p_cols].div(df[p_cols].sum(axis=1).replace(0, np.nan), axis=0)
        df["loss_mean_13_domains"] = df[l_cols].mean(axis=1)
        df["dataset"] = name
        df["role"] = role
        df["scale"] = scale
        df["loss_observed"] = observed
        out[name] = df
    return out


def mixture_validation(a: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = a["A4_A5_train_1m"]
    p_cols = [c for c in train.columns if c.startswith("train_the_pile_")]
    # Drop one component to avoid exact closure collinearity, and use ridge as
    # a stable first-order mixture model for each of the 13 domain losses.
    x_cols = p_cols[:-1]
    x_train = train[x_cols].to_numpy(float)
    model_rows = []
    pred_rows = []
    loss_cols = [c for c in train.columns if c.startswith("metric/the_pile_")]
    for target in loss_cols:
        model = Ridge(alpha=1e-5).fit(x_train, train[target].to_numpy(float))
        for dataset, df in a.items():
            pred = model.predict(df[x_cols].to_numpy(float))
            m = metrics(df[target], pred, dataset, model_type="mixture_ridge")
            m["target"] = target
            m["validation_role"] = "fit" if dataset == "A4_A5_train_1m" else ("external_validation" if df["loss_observed"].iloc[0] else "extrapolation_audit")
            pred_rows.append({"dataset": dataset, "target": target, "actual": df[target].to_numpy(float), "predicted": pred})
            model_rows.append(m)
            baseline = np.full(len(df), train[target].mean())
            bm = metrics(df[target], baseline, dataset, model_type="train_domain_mean")
            bm["target"] = target
            bm["validation_role"] = m["validation_role"]
            model_rows.append(bm)
    metrics_df = pd.DataFrame(model_rows)
    # Aggregate across domains without hiding the domain-level results.
    agg = (
        metrics_df.groupby(["dataset", "validation_role", "model_type"], as_index=False)
        .agg(n=("n", "sum"), mae=("mae", "mean"), rmse=("rmse", "mean"), r2=("r2", "mean"),
             mean_signed_error=("mean_signed_error", "mean"), mean_absolute_percentage=("mean_absolute_percentage", "mean"))
    )
    return metrics_df, agg


def scale_validation() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    bdir = RAW / "B_scaling_laws"
    b1 = pd.read_csv(bdir / "pythia_training_log_existing.csv")
    # Overall fit on all B1; external sources never feed the fit.
    full = fit_scale_model(b1)
    external_specs = {
        "B2_cerebras": bdir / "cerebras_training_log.csv",
        "B4_scaling_baseline": bdir / "scaling_baseline.csv",
        "B5_published_scaling": bdir / "published_scaling_data.csv",
    }
    rows = []
    pred = full.predict(np.log(b1[["N_params_B", "D_tokens_B"]].astype(float)))
    rows.append(metrics(b1["val_loss"], pred, "B1_in_sample", model_type="log_ND"))
    rows.append(metrics(b1["val_loss"], np.full(len(b1), b1["val_loss"].mean()), "B1_in_sample", model_type="train_mean"))
    for label, path in external_specs.items():
        df = pd.read_csv(path)
        p = full.predict(np.log(df[["N_params_B", "D_tokens_B"]].astype(float)))
        rows.append(metrics(df["val_loss"], p, label, model_type="log_ND"))
        rows.append(metrics(df["val_loss"], np.full(len(df), b1["val_loss"].mean()), label, model_type="train_mean"))

    loo_rows = []
    for n_value in sorted(b1["N_params_B"].unique()):
        train = b1[b1["N_params_B"] != n_value]
        test = b1[b1["N_params_B"] == n_value]
        model = fit_scale_model(train)
        p = model.predict(np.log(test[["N_params_B", "D_tokens_B"]].astype(float)))
        m = metrics(test["val_loss"], p, f"B1_leave_N_{n_value:g}", model_type="log_ND")
        m["held_out_N_params_B"] = float(n_value)
        loo_rows.append(m)
    coeff = {
        "intercept": float(full.intercept_),
        "coef_log_N": float(full.coef_[0]),
        "coef_log_D": float(full.coef_[1]),
        "n_rows": int(len(b1)),
        "n_parameter_sizes": int(b1["N_params_B"].nunique()),
    }
    return pd.DataFrame(rows), pd.DataFrame(loo_rows), coeff


def quality_validation() -> tuple[pd.DataFrame, dict]:
    bdir = RAW / "B_scaling_laws"
    b6 = pd.read_csv(bdir / "supplementary_NQ_experiment.csv")
    b7 = pd.read_csv(bdir / "supplementary_NQ_experiment_expanded.csv")
    b8 = pd.read_csv(bdir / "supplementary_NQ_experiment_large.csv")
    rows = []
    key_cols = ["N_params_B", "D_tokens_B", "Q_score"]
    b6_keys = b6[key_cols].drop_duplicates().assign(_in_b6=True)
    b7_tagged = b7.merge(b6_keys, on=key_cols, how="left")
    b7_new = b7_tagged[b7_tagged["_in_b6"].isna()].drop(columns=["_in_b6"])

    # B6 is a strict subset of B7. Only the 90 new B7 Q-level rows are a
    # non-overlapping holdout for a model fitted on B6.
    train = b6
    test = b7_new
    x_train = np.column_stack([np.log(train["N_params_B"]), np.log(train["D_tokens_B"]), train["Q_score"]])
    x_test = np.column_stack([np.log(test["N_params_B"]), np.log(test["D_tokens_B"]), test["Q_score"]])
    model = LinearRegression().fit(x_train, train["val_loss"])
    p = model.predict(x_test)
    m = metrics(test["val_loss"], p, "B6_to_B7_new_Q_levels", model_type="log_NDQ")
    m["train_source"] = "B6"
    m["test_source"] = "B7_new_only"
    rows.append(m)
    bm = metrics(test["val_loss"], np.full(len(test), train["val_loss"].mean()), "B6_to_B7_new_Q_levels", model_type="train_source_mean")
    bm["train_source"] = "B6"
    bm["test_source"] = "B7_new_only"
    rows.append(bm)

    # Within B7, leave one shared Q level out across all (N,D) groups.
    q_levels = sorted(b7["Q_score"].unique())
    for q in q_levels:
        train = b7[b7["Q_score"] != q]
        test = b7[b7["Q_score"] == q]
        x_train = np.column_stack([np.log(train["N_params_B"]), np.log(train["D_tokens_B"]), train["Q_score"]])
        x_test = np.column_stack([np.log(test["N_params_B"]), np.log(test["D_tokens_B"]), test["Q_score"]])
        model = LinearRegression().fit(x_train, train["val_loss"])
        p = model.predict(x_test)
        label = f"B7_leave_Q_{q:g}"
        m = metrics(test["val_loss"], p, label, model_type="log_NDQ")
        m["train_source"] = "B7_minus_level"
        m["test_source"] = "B7_heldout_level"
        rows.append(m)
        bm = metrics(test["val_loss"], np.full(len(test), train["val_loss"].mean()), label, model_type="train_source_mean")
        bm["train_source"] = "B7_minus_level"
        bm["test_source"] = "B7_heldout_level"
        rows.append(bm)

    # Direction audit within fixed (N,D) groups, including B8.
    direction_rows = []
    for name, df in [("B6", b6), ("B7", b7), ("B8", b8)]:
        slopes = []
        for _, group in df.groupby(["N_params_B", "D_tokens_B"]):
            if group["Q_score"].nunique() < 3:
                continue
            slope = np.polyfit(group["Q_score"], group["val_loss"], 1)[0]
            slopes.append(float(slope))
        direction_rows.append({
            "dataset": name,
            "n_ND_groups": len(slopes),
            "share_negative_Q_slope": float(np.mean(np.array(slopes) < 0)) if slopes else float("nan"),
            "share_positive_Q_slope": float(np.mean(np.array(slopes) > 0)) if slopes else float("nan"),
            "median_Q_slope": float(np.median(slopes)) if slopes else float("nan"),
        })
    return pd.DataFrame(rows), {
        "direction_audit": direction_rows,
        "B6_rows": len(b6),
        "B7_rows": len(b7),
        "B8_rows": len(b8),
        "B6_rows_overlapping_B7": int(len(b6.merge(b7, on=key_cols, how="inner"))),
        "B7_new_nonoverlap_rows": int(len(b7_new)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a = prepare_a()
    mix_detail, mix_aggregate = mixture_validation(a)
    scale_external, scale_loo, scale_coeff = scale_validation()
    quality_metrics, quality_meta = quality_validation()

    mix_detail.to_csv(OUT / "mixture_domain_validation.csv", index=False, encoding="utf-8-sig")
    mix_aggregate.to_csv(OUT / "mixture_validation_summary.csv", index=False, encoding="utf-8-sig")
    scale_external.to_csv(OUT / "scale_external_validation.csv", index=False, encoding="utf-8-sig")
    scale_loo.to_csv(OUT / "scale_leave_one_size_out.csv", index=False, encoding="utf-8-sig")
    quality_metrics.to_csv(OUT / "quality_cross_source_validation.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "run_id": "q2-local-model-validation-20260925",
        "status": "REVIEW_REQUIRED",
        "raw_attachment_root": source_ref(RAW),
        "scale_fit": "B1 pythia_training_log_existing.csv only",
        "mixture_fit": "A4/A5 train_mixture_1m.csv + train_pile_loss_1m.csv only",
        "quality_fit": "B6 predicts non-overlapping B7 rows and B7 Q-level leave-out checks; B8 direction audit only",
        "excluded_from_fit": ["A12-A15 estimated Loss", "B8 main quality fit", "B10 estimated Loss"],
        "scale_model": scale_coeff,
        "quality_meta": quality_meta,
        "note": "These are component validations. They do not establish empirical identification of a complete observed (N,D,Q,p,Loss) joint law.",
    }
    (OUT / "validation_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = f"""# Q2 local model validation\n\nRun ID: `q2-local-model-validation-20260925`\n\nThis run follows the block-missing validation plan:\n\n- Scale: fit only on real B1 and evaluate leave-one-size-out plus B2/B4/B5.\n- Mixture: fit first-order ridge models on real A4/A5 and evaluate A6/A7, A8/A9, A10/A11; A12-A15 remain extrapolation audits.\n- Quality: fit additive log-N-D-Q checks between B6 and B7; B8 is a direction-conflict audit.\n\nThe outputs are predictive checks for separate components. They are not evidence that a synthetic Cartesian product is an observed joint sample.\n"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
