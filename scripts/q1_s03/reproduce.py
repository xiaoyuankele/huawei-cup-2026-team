"""Audited, portable reproduction of Q1.3 quality/mixture/scale models.

Only the original combined v1 table is supported. Base regularization values
are frozen historical choices, not retuned here. C2 tuning uses paired folds;
its selected CV score is a tuning score, not a nested generalization estimate.
Only aggregate outputs are exported unless --export-predictions is requested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

P_COLS = [
    "p_arxiv", "p_freelaw", "p_nih_exporter", "p_pubmed_central", "p_wikipedia_en",
    "p_dm_mathematics", "p_github", "p_philpapers", "p_stackexchange", "p_enron_emails",
    "p_gutenberg_pg_19", "p_pile_cc", "p_ubuntu_irc", "p_europarl", "p_hackernews",
    "p_pubmed_abstracts", "p_uspto_backgrounds",
]
L_COLS = [
    "metric/the_pile_arxiv_val_loss", "metric/the_pile_freelaw_val_loss",
    "metric/the_pile_pubmed_central_val_loss", "metric/the_pile_wikipedia_en_val_loss",
    "metric/the_pile_dm_mathematics_val_loss", "metric/the_pile_github_val_loss",
    "metric/the_pile_stackexchange_val_loss", "metric/the_pile_gutenberg_pg_19_val_loss",
    "metric/the_pile_pile_cc_val_loss", "metric/the_pile_ubuntu_irc_val_loss",
    "metric/the_pile_hackernews_val_loss", "metric/the_pile_pubmed_abstracts_val_loss",
    "metric/the_pile_uspto_backgrounds_val_loss",
]
DATASETS = {
    "A4_A5_train_1m": (512, "1m", 1e6, True),
    "A6_A7_test_1m": (256, "1m", 1e6, True),
    "A8_A9_test_60m": (256, "60m", 60e6, True),
    "A10_A11_test_1b": (64, "1b", 1e9, True),
    "A12_A13_est_10b": (63, "10b", 10e9, False),
    "A14_A15_est_70b": (63, "70b", 70e9, False),
}
Q_PROXY = "quality_score_proxy_0_1"
Q_MAPPED = "quality_score_mapped_0_1"
X60 = float(np.log10(60.0))


def paired_frames(frame, left, right, subset_left=False):
    """Align on original IDs, then require identical normalized mixtures."""
    a = frame[frame.dataset.eq(left)].sort_values("index").copy()
    b = frame[frame.dataset.eq(right)].sort_values("index").copy()
    if subset_left:
        a = a[a["index"].isin(b["index"])].copy()
    if a["index"].duplicated().any() or b["index"].duplicated().any():
        raise ValueError("Duplicate original IDs in a paired cohort")
    if not np.array_equal(a["index"].to_numpy(), b["index"].to_numpy()):
        raise ValueError(f"Original IDs do not match: {left}, {right}")
    if not len(a) or not np.allclose(a[P_COLS], b[P_COLS], atol=1e-12, rtol=0):
        raise ValueError(f"Mixture mismatch: {left}, {right}")
    return a.reset_index(drop=True), b.reset_index(drop=True)


def validate_input(frame):
    required = set(P_COLS + L_COLS + ["dataset", "index", "scale", "loss_observed", Q_PROXY, Q_MAPPED])
    if required - set(frame):
        raise ValueError(f"Missing fields: {sorted(required - set(frame))}")
    if set(c for c in frame if c.startswith("p_")) != set(P_COLS):
        raise ValueError("Expected exactly the 17 named mixture fields")
    if set(c for c in frame if c.startswith("metric/")) != set(L_COLS):
        raise ValueError("Expected exactly the 13 named Loss fields")
    if frame.duplicated(["dataset", "index"]).any():
        raise ValueError("dataset/index must be unique")
    if set(frame.dataset) != set(DATASETS):
        raise ValueError("Unexpected datasets; use the original combined v1 table")
    p, y = frame[P_COLS].to_numpy(float), frame[L_COLS].to_numpy(float)
    if not np.isfinite(p).all() or (p < 0).any():
        raise ValueError("Mixtures must be finite and nonnegative")
    sum_error = float(np.max(np.abs(p.sum(1) - 1)))
    if sum_error > 1e-10:
        raise ValueError("Input mixture shares are not normalized")
    if not np.isfinite(y).all():
        raise ValueError("Loss values must be finite")
    for q in [Q_PROXY, Q_MAPPED]:
        values = frame[q].to_numpy(float)
        finite = np.isfinite(values)
        if np.isinf(values).any() or ((values[finite] < 0) | (values[finite] > 1)).any():
            raise ValueError(f"Invalid quality values: {q}")
    if frame[Q_PROXY].isna().any():
        raise ValueError("Q_proxy must be complete")
    if frame[Q_MAPPED].isna().sum() != 5 or frame.loc[frame[Q_MAPPED].isna(), "dataset"].ne("A4_A5_train_1m").any():
        raise ValueError("Original v1 expects five unmapped A4/A5 quality rows only")
    for dataset, (count, scale, _, observed) in DATASETS.items():
        part = frame[frame.dataset.eq(dataset)]
        ids = part["index"].to_numpy(float)
        if len(part) != count or not part.scale.eq(scale).all():
            raise ValueError(f"Unexpected count or scale: {dataset}")
        start = 0 if dataset == "A10_A11_test_1b" else 1
        if not np.array_equal(np.sort(ids), np.arange(start, start + count)):
            raise ValueError(f"Unexpected original IDs: {dataset}")
        if not part.loss_observed.astype(str).str.lower().eq(str(observed).lower()).all():
            raise ValueError(f"Unexpected observed/estimated status: {dataset}")
    frame = frame.copy()
    # Remove floating-point roundoff only; substantive non-unit sums were rejected.
    frame[P_COLS] = frame[P_COLS].div(frame[P_COLS].sum(1), axis=0)
    pairs = []
    for left, right, subset in [
        ("A6_A7_test_1m", "A8_A9_test_60m", False),
        ("A12_A13_est_10b", "A14_A15_est_70b", False),
        ("A4_A5_train_1m", "A12_A13_est_10b", True),
    ]:
        a, _ = paired_frames(frame, left, right, subset)
        pairs.append({"left": left, "right": right, "n": len(a), "same_original_ids_and_mixtures": True})
    frame["x_scale"] = frame.dataset.map({k: np.log10(v[2] / 1e6) for k, v in DATASETS.items()})
    return frame, {"n_rows": len(frame), "max_input_simplex_sum_error": sum_error, "pair_checks": pairs}


def fit_model(x, y, penalty):
    mean, sd = x.mean(0), x.std(0)
    sd[sd < 1e-12] = 1.0
    z = np.c_[np.ones(len(x)), (x - mean) / sd]
    reg = np.eye(z.shape[1]) * penalty
    reg[0, 0] = 0
    beta = np.linalg.lstsq(z.T @ z + reg, z.T @ y, rcond=None)[0]
    return {"mean": mean, "sd": sd, "beta": beta, "lambda": float(penalty)}


def predict_model(x, model):
    return np.c_[np.ones(len(x)), (x - model["mean"]) / model["sd"]] @ model["beta"]


def scale_delta_correction(predicted_delta, x_scale):
    """Convert a predicted 1M-to-60M difference into a log-scale correction."""
    return np.asarray(x_scale, float)[:, None] * np.asarray(predicted_delta, float) / X60


def correction_matrix(kind, x, mean_delta, conditional_delta):
    if kind == "C0_none":
        return np.zeros((len(x), len(mean_delta)))
    if kind == "C1_global":
        delta = np.full((len(x), len(mean_delta)), mean_delta.mean())
    elif kind == "C1_domain":
        delta = np.broadcast_to(mean_delta, (len(x), len(mean_delta)))
    elif kind == "C2_mixture_conditioned":
        delta = conditional_delta
    else:
        raise ValueError(kind)
    return scale_delta_correction(delta, x)


def scalar_metrics(y, pred):
    error = y - pred
    denominator = float(np.sum((y - y.mean()) ** 2))
    rank_y, rank_pred = pd.Series(y).rank(), pd.Series(pred).rank()
    rho = float(rank_y.corr(rank_pred)) if rank_y.std() > 0 and rank_pred.std() > 0 else np.nan
    return {
        "rmse": float(np.sqrt(np.mean(error ** 2))),
        "mae": float(np.mean(np.abs(error))),
        "bias_observed_minus_pred": float(error.mean()),
        "r2": float(1 - np.sum(error ** 2) / denominator) if denominator > 0 else np.nan,
        "spearman": rho,
    }


def aggregate_metrics(y, pred):
    mean_metrics = scalar_metrics(y.mean(1), pred.mean(1))
    result = {f"{key}_mean_loss": value for key, value in mean_metrics.items()}
    error = y - pred
    result.update({
        "rmse_domain_macro": float(np.sqrt(np.mean(error ** 2, axis=0)).mean()),
        "mae_domain_macro": float(np.abs(error).mean(axis=0).mean()),
        "rmse_pooled_all_domains": float(np.sqrt(np.mean(error ** 2))),
    })
    return result


def select_c2(a6, delta):
    x = a6[P_COLS[:-1]].to_numpy(float)
    folds = np.arange(len(x)) % 5
    candidates = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]
    rows, scores = [], []
    for penalty in candidates:
        fold_scores = []
        for fold in range(5):
            tr, va = folds != fold, folds == fold
            model = fit_model(x[tr], delta[tr], penalty)
            pred = predict_model(x[va], model)
            metrics = aggregate_metrics(delta[va], pred)
            fold_scores.append(metrics["rmse_mean_loss"])
            rows.append({"model": "C2_mixture_conditioned", "lambda": penalty, "fold": fold,
                         "n_train": int(tr.sum()), "n_valid": int(va.sum()), **metrics})
        scores.append(float(np.mean(fold_scores)))
    selected = candidates[int(np.argmin(scores))]
    for kind in ["C1_global", "C1_domain"]:
        for fold in range(5):
            tr, va = folds != fold, folds == fold
            pred = correction_matrix(kind, np.full(va.sum(), X60), delta[tr].mean(0), None)
            rows.append({"model": kind, "lambda": 0.0, "fold": fold,
                         "n_train": int(tr.sum()), "n_valid": int(va.sum()),
                         **aggregate_metrics(delta[va], pred)})
    return fit_model(x, delta, selected), pd.DataFrame(rows), {
        "selected_lambda": selected, "selection_metric": "mean_of_fold_rmse_of_13_domain_mean_delta",
        "selected_cv_score": min(scores), "score_role": "non_nested_hyperparameter_tuning_score",
        "fold_assignment": "sorted_original_ID_position_mod_5", "standardization": "training_fold_only",
    }


def json_model(model, features):
    raw = model["beta"][1:] / model["sd"][:, None]
    return {
        "features": features, "outputs": L_COLS, "lambda": model["lambda"],
        "feature_mean": model["mean"].tolist(), "feature_sd": model["sd"].tolist(),
        "standardized_intercept_and_coefficients": model["beta"].tolist(),
        "raw_intercept": (model["beta"][0] - model["mean"] @ raw).tolist(),
        "raw_coefficients": raw.tolist(),
    }


def evaluation_role(dataset, correction):
    if dataset == "A4_A5_train_1m":
        return "base_fit"
    if dataset in ["A12_A13_est_10b", "A14_A15_est_70b"]:
        return "provided_estimates_extrapolation_audit"
    if correction != "C0_none" and dataset in ["A6_A7_test_1m", "A8_A9_test_60m"]:
        return "paired_calibration_member"
    return "external_retrospective_evaluation"


def field_dictionary(columns):
    descriptions = {
        "dataset": "Original A-table pair identifier", "role": "Original source role label",
        "scale": "Provided scale label; x_scale = log10(scale/1M)",
        "loss_observed": "True for A4-A11 observations; False for supplied A12-A15 estimates",
        "index": "Original within-table row ID; combined key is dataset/index",
        "mixture_sum_raw": "Mixture row sum before upstream normalization",
        "mapped_share_direct_near_direct": "Share covered by direct or near-direct quality mapping",
        Q_PROXY: "Existing composition-derived quality proxy; not an independent causal variable",
        Q_MAPPED: "Existing mapped quality score; five unmapped training rows excluded, never imputed",
        "loss_mean_13_domains": "Supplied equal-weight mean of the 13 named Loss columns; recomputed for metrics",
        "x_scale": "Derived log10(scale/1M), dimensionless",
    }
    rows = []
    for name in columns:
        group = "mixture" if name in P_COLS else "response" if name in L_COLS else "metadata_or_quality"
        description = descriptions.get(name, "Existing quality-proxy component share")
        if name in P_COLS:
            description = "Normalized mixture share; nonnegative; the 17 shares sum to one"
        if name in L_COLS:
            description = "Supplied cross-entropy Loss for the named evaluation domain"
        rows.append({"field": name, "group": group, "description": description})
    return pd.DataFrame(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run(input_path, output_path, bootstrap=5000, seed=20260925, export_predictions=False):
    if bootstrap < 1:
        raise ValueError("bootstrap must be positive")
    output_path.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_path)
    frame, audit = validate_input(raw)
    a6, a8 = paired_frames(frame, "A6_A7_test_1m", "A8_A9_test_60m")
    delta = a8[L_COLS].to_numpy(float) - a6[L_COLS].to_numpy(float)
    mean_delta = delta.mean(0)
    c2, cv, c2_info = select_c2(a6, delta)
    cv.to_csv(output_path / "paired_correction_cv.csv", index=False)
    transfer_rows = []
    for left_name, right_name, pair_role in [
        ("A6_A7_test_1m", "A8_A9_test_60m", "calibration_pair"),
        ("A12_A13_est_10b", "A14_A15_est_70b", "provided_estimates_shift_audit"),
    ]:
        left, right = paired_frames(frame, left_name, right_name)
        # Explicit arrays preserve sorted original-ID pairing, never pandas index alignment.
        reference_delta = right[L_COLS].to_numpy(float) - left[L_COLS].to_numpy(float)
        step = right.x_scale.to_numpy() - left.x_scale.to_numpy()
        conditional = predict_model(left[P_COLS[:-1]].to_numpy(float), c2)
        for correction in ["C1_global", "C1_domain", "C2_mixture_conditioned"]:
            predicted_delta = correction_matrix(correction, step, mean_delta, conditional)
            for j, domain in enumerate(L_COLS + ["loss_mean_13_domains"]):
                yy = reference_delta[:, j] if j < len(L_COLS) else reference_delta.mean(1)
                pp = predicted_delta[:, j] if j < len(L_COLS) else predicted_delta.mean(1)
                transfer_rows.append({
                    "left_dataset": left_name, "right_dataset": right_name, "pair_role": pair_role,
                    "correction": correction, "domain": domain, "n": len(left),
                    "reference_delta_mean": float(yy.mean()), "predicted_delta_mean": float(pp.mean()),
                    **scalar_metrics(yy, pp),
                })
    pd.DataFrame(transfer_rows).to_csv(output_path / "paired_shift_transfer.csv", index=False)
    all_conditional_delta = predict_model(frame[P_COLS[:-1]].to_numpy(float), c2)
    all_y = frame[L_COLS].to_numpy(float)
    aggregate, domains, predictions, params = [], [], [], {}
    configurations = [
        ("B1_Q_proxy", Q_PROXY, False, 0.0), ("M1_Q_proxy", Q_PROXY, True, 100.0),
        ("B1_Q_mapped", Q_MAPPED, False, 0.0), ("M1_Q_mapped", Q_MAPPED, True, 10.0),
    ]
    for name, q, mixture, penalty in configurations:
        features = [q] + (P_COLS[:-1] if mixture else [])
        valid = np.isfinite(frame[features].to_numpy(float)).all(1)
        train = frame.dataset.eq("A4_A5_train_1m").to_numpy() & valid
        x = frame[features].to_numpy(float)
        model = fit_model(x[train], all_y[train], penalty)
        base_prediction = predict_model(x, model)
        params[name] = {**json_model(model, features), "n_fit": int(train.sum()),
                        "fit_dataset": "A4_A5_train_1m", "regularization_role": "fixed_historical_choice_not_retuned"}
        for correction in ["C0_none", "C1_global", "C1_domain", "C2_mixture_conditioned"]:
            pred = base_prediction + correction_matrix(correction, frame.x_scale.to_numpy(), mean_delta, all_conditional_delta)
            for dataset in DATASETS:
                selected = frame.dataset.eq(dataset).to_numpy() & valid
                y, yh = all_y[selected], pred[selected]
                metadata = {"base_model": name, "correction": correction, "dataset": dataset,
                            "n": int(selected.sum()), "role": evaluation_role(dataset, correction)}
                aggregate.append({**metadata, **aggregate_metrics(y, yh)})
                for j, domain in enumerate(L_COLS):
                    domains.append({**metadata, "domain": domain, **scalar_metrics(y[:, j], yh[:, j])})
                if export_predictions:
                    for row, original_id in enumerate(frame.loc[selected, "index"]):
                        for j, domain in enumerate(L_COLS):
                            predictions.append({**metadata, "index": int(original_id), "domain": domain,
                                                "observed_or_supplied_estimate": y[row, j], "predicted": yh[row, j]})
    pd.DataFrame(aggregate).to_csv(output_path / "metrics_aggregate.csv", index=False)
    pd.DataFrame(domains).to_csv(output_path / "metrics_by_domain.csv", index=False)
    if export_predictions:
        pd.DataFrame(predictions).to_csv(output_path / "individual_predictions_private.csv", index=False)
    rng = np.random.default_rng(seed)
    boot = np.empty((bootstrap, len(L_COLS)))
    for iteration in range(bootstrap):
        boot[iteration] = delta[rng.integers(0, len(delta), len(delta))].mean(0) / X60
    slopes = np.r_[mean_delta / X60, mean_delta.mean() / X60]
    boot = np.c_[boot, boot.mean(1)]
    low, high = np.quantile(boot, [0.025, 0.975], axis=0)
    pd.DataFrame({"domain": L_COLS + ["loss_mean_13_domains"], "mean_delta_1m_to_60m": slopes * X60,
                  "slope_per_log10_scale": slopes, "bootstrap_ci95_low": low,
                  "bootstrap_ci95_high": high}).to_csv(output_path / "scale_coefficients.csv", index=False)
    inventory = []
    for dataset, (count, scale, _, observed) in DATASETS.items():
        part = frame[frame.dataset.eq(dataset)]
        inventory.append({"dataset": dataset, "n": count, "scale": scale, "loss_observed": observed,
                          "quality_proxy_missing": int(part[Q_PROXY].isna().sum()),
                          "quality_mapped_missing": int(part[Q_MAPPED].isna().sum()),
                          "p_columns": len(P_COLS), "loss_columns": len(L_COLS),
                          "train_composition_overlap": 63 if not observed else None})
    pd.DataFrame(inventory).to_csv(output_path / "data_inventory.csv", index=False)
    field_dictionary(raw.columns).to_csv(output_path / "field_dictionary.csv", index=False)
    write_json(output_path / "model_parameters.json", {
        "base_models": params, "base_scale_coefficient": "not_estimated_constant_scale_in_training",
        "C1_domain_slope": (mean_delta / X60).tolist(), "C1_global_slope": float(mean_delta.mean() / X60),
        "C2_delta_model": json_model(c2, P_COLS[:-1]), "C2_tuning": c2_info,
        "C2_formula": "predicted_delta_1M_to_60M(p) * log10(scale/1M) / log10(60)",
        "C3": "not_reproduced; legacy blend CV had fold leakage; old C3 results superseded",
        "bootstrap": {"seed": seed, "replicates": bootstrap, "unit": "matched mixture row; 13 responses resampled together"},
    })
    audit.update({
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "input_name": input_path.name, "python": platform.python_version(),
        "numpy": np.__version__, "pandas": pd.__version__, "export_predictions": export_predictions,
        "base_fit": "A4/A5 only; mapped quality drops five unmapped rows",
        "correction_fit": "A6/A8 matched composition differences only",
        "C2_units_fixed": True, "C2_fold_preprocessing": "training_fold_only",
        "metric_definitions": {
            "rmse_mean_loss": "sqrt(mean_rows((mean_domains(y)-mean_domains(pred))**2))",
            "rmse_domain_macro": "mean_domains(sqrt(mean_rows((y-pred)**2)))",
            "rmse_pooled_all_domains": "sqrt(mean_rows_and_domains((y-pred)**2))",
            "mae_mean_loss": "mean_rows(abs(mean_domains(y)-mean_domains(pred)))",
            "bias_observed_minus_pred_mean_loss": "mean_rows(mean_domains(y)-mean_domains(pred))",
        },
        "limitations": [
            "A6/A8 are calibration members for corrected models; A8 is not independent validation.",
            "A10/A11 and A12-A15 were previously inspected; evaluations are retrospective, not fresh blind tests.",
            "A12-A15 contain supplied estimated Loss values, not independent observed measurements.",
            "A12/A14 mixtures equal the first 63 A4 recipes; this is scale extrapolation, not unseen-mixture validation.",
            "Negative R2 means worse squared error than the evaluated table's own mean reference.",
            "C1 shifts all recipes at the same scale equally and cannot improve within-scale rank ordering.",
            "Bootstrap intervals quantify paired-row sampling variability, not scale-law form uncertainty.",
            "Quality is composition-derived; regression coefficients are predictive, not causal domain effects.",
            "Historical regularization is fixed; the C2 selected tuning score is not a nested performance estimate.",
        ],
    })
    write_json(output_path / "audit.json", audit)
    print(json.dumps({"output": str(output_path), "rows": len(frame), "selected_c2_lambda": c2["lambda"],
                      "aggregate_rows": len(aggregate), "predictions_exported": export_predictions}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--export-predictions", action="store_true", help="Private opt-in: export row-level targets and predictions")
    args = parser.parse_args()
    run(args.input, args.output, args.bootstrap, args.seed, args.export_predictions)


if __name__ == "__main__":
    main()
