"""Controlled retrospective mixture/scale/optional-quality ablation for Q1.3.

Only registered derived data are read; no individual predictions are exported.
Historical penalties are frozen. Evaluation rows do not select a model here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from q1_mixture_collinearity import helmert_basis, zero_replaced_clr
from q1_s03.reproduce import (
    P_COLS, L_COLS, DATASETS, Q_PROXY, X60, validate_input, paired_frames,
    fit_model, predict_model, correction_matrix, aggregate_metrics,
    scalar_metrics, json_model,
)

DEFAULT_CONFIG = ROOT / "configs/q1-mixture-scale-ablation.json"
EVAL_DATASETS = list(DATASETS)[1:]


def dump(path, value):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def features(p, q, name, epsilon=1e-4):
    """Pure-p branches never read q; Q is appended after the p-only map."""
    if name == "qproxy_only":
        return np.asarray(q)[:, None]
    z = zero_replaced_clr(np.asarray(p), epsilon) @ helmert_basis(p.shape[1]).T
    if name.startswith("quadratic"):
        z = PolynomialFeatures(degree=2, include_bias=False).fit_transform(z)
    return np.c_[z, q] if name.endswith("_qproxy") else z


def metric_pack(y, prediction):
    result = aggregate_metrics(y, prediction)
    domain = [scalar_metrics(y[:, j], prediction[:, j]) for j in range(y.shape[1])]
    result["r2_domain_macro"] = float(np.mean([m["r2"] for m in domain]))
    finite_spearman = [m["spearman"] for m in domain if np.isfinite(m["spearman"])]
    result["spearman_domain_macro"] = float(np.mean(finite_spearman)) if finite_spearman else np.nan
    return result, domain


def role(dataset, correction):
    if dataset == list(DATASETS)[0]:
        return "base_fit"
    if dataset in list(DATASETS)[-2:]:
        return "supplied_estimate_extrapolation_audit"
    if dataset == "A6_A7_test_1m":
        return "same_scale_retrospective; also_scale_calibration_member" if correction != "C0_none" else "same_scale_retrospective"
    if dataset == "A8_A9_test_60m" and correction != "C0_none":
        return "scale_calibration_in_sample"
    return "cross_scale_retrospective"


def oof_deltas(a6, delta, alpha, corrections):
    folds = np.arange(len(a6)) % 5
    outputs = {c: np.zeros_like(delta) for c in corrections}
    x = a6[P_COLS[:-1]].to_numpy(float)
    for fold in range(5):
        train, test = folds != fold, folds == fold
        c2 = fit_model(x[train], delta[train], alpha)
        conditional = predict_model(x[test], c2)
        for c in corrections:
            outputs[c][test] = correction_matrix(c, np.full(test.sum(), X60), delta[train].mean(0), conditional)
    return outputs


def paired_bootstrap(y, reference, candidate, draws):
    """Candidate-minus-reference error, resampling full recipe rows."""
    ref_sq = ((y-reference)**2).mean(1)
    new_sq = ((y-candidate)**2).mean(1)
    ref_abs = np.abs(y-reference).mean(1)
    new_abs = np.abs(y-candidate).mean(1)
    out = {}
    for key, a, b, transform in [
        ("rmse", ref_sq, new_sq, np.sqrt),
        ("mae", ref_abs, new_abs, lambda v: v),
    ]:
        ref, new = float(transform(a.mean())), float(transform(b.mean()))
        sampled = transform(b[draws].mean(1))-transform(a[draws].mean(1))
        low, high = np.quantile(sampled, [0.025, 0.975])
        out.update({f"{key}_reference": ref, f"{key}_candidate": new,
                    f"{key}_difference": new-ref, f"{key}_ci95_low": float(low),
                    f"{key}_ci95_high": float(high),
                    f"{key}_reduction_pct": 100*(ref-new)/ref if ref else 0.0})
    return out


def run(config_path, output=None):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = ROOT/config["input"]
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != config["input_sha256"]:
        raise ValueError("Input hash differs from the frozen protocol")
    out = output or ROOT/"experiments/runs"/config["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    frame, input_audit = validate_input(pd.read_csv(source))
    # Explicit dataset+ID sort ensures identical paired-bootstrap sample ordering.
    frame = frame.sort_values(["dataset", "index"]).reset_index(drop=True)
    p, q, y = frame[P_COLS].to_numpy(), frame[Q_PROXY].to_numpy(), frame[L_COLS].to_numpy()
    train = frame.dataset.eq("A4_A5_train_1m").to_numpy()
    masks = {d: frame.dataset.eq(d).to_numpy() for d in DATASETS}
    a6, a8 = paired_frames(frame, "A6_A7_test_1m", "A8_A9_test_60m")
    delta = a8[L_COLS].to_numpy()-a6[L_COLS].to_numpy()
    c2 = fit_model(a6[P_COLS[:-1]].to_numpy(), delta, config["c2_ridge_alpha"])
    conditional = predict_model(frame[P_COLS[:-1]].to_numpy(), c2)
    corr = {c: correction_matrix(c, frame.x_scale.to_numpy(), delta.mean(0), conditional)
            for c in config["corrections"]}
    oof = oof_deltas(a6, delta, config["c2_ridge_alpha"], config["corrections"])
    metrics, per_domain, oof_metrics, predictions, base_predictions, parameters = [], [], [], {}, {}, {}
    for name in config["base_models"]:
        x = features(p, q, name, config["epsilon"])
        estimator = make_pipeline(StandardScaler(), LinearRegression() if name == "qproxy_only" else Ridge(alpha=config["base_ridge_alpha"]))
        estimator.fit(x[train], y[train])
        pred0 = estimator.predict(x)
        base_predictions[name] = pred0
        scaler, regression = estimator.steps[0][1], estimator.steps[1][1]
        parameters[name] = {"feature_count": x.shape[1], "fit_n": int(train.sum()),
            "alpha": None if name == "qproxy_only" else config["base_ridge_alpha"],
            "feature_mean": scaler.mean_.tolist(), "feature_sd": scaler.scale_.tolist(),
            "coefficients_targets_by_features": regression.coef_.tolist(),
            "intercept_targets": regression.intercept_.tolist(),
            "quality_feature": "last feature, fixed v1 Q_proxy" if name.endswith("_qproxy") else ("only feature" if name=="qproxy_only" else "none")}
        for c in config["corrections"]:
            pred = pred0 + corr[c]
            predictions[(name, c)] = pred
            for dataset, mask in masks.items():
                meta = {"base_model": name, "correction": c, "dataset": dataset, "role": role(dataset,c), "n": int(mask.sum())}
                aggregate, domain = metric_pack(y[mask], pred[mask])
                metrics.append({**meta, **aggregate})
                per_domain.extend({**meta, "domain": target, **m} for target,m in zip(L_COLS,domain))
            pred_oof = pred0[masks["A8_A9_test_60m"]] + oof[c]
            pack, _ = metric_pack(y[masks["A8_A9_test_60m"]],pred_oof)
            oof_metrics.append({"base_model": name,"correction":c,"dataset":"A8_A9_test_60m",
                "role":"conditional_calibration_OOF_fixed_historical_alpha_not_independent_validation","n":len(a8),**pack})
    mf = pd.DataFrame(metrics)
    mf.to_csv(out/"metrics_aggregate.csv",index=False)
    pd.DataFrame(per_domain).to_csv(out/"metrics_by_domain.csv",index=False)
    pd.DataFrame(oof_metrics).to_csv(out/"metrics_calibration_oof.csv",index=False)
    specs = []
    for model in config["base_models"]:
        specs.extend(("scale_correction",model,"C0_none",model,c) for c in config["corrections"][1:])
    for model in ["ilr_ridge","quadratic_ridge"]:
        specs.extend(("optional_quality",model,c,model+"_qproxy",c) for c in config["corrections"])
    specs.extend(("quadratic_vs_linear","ilr_ridge",c,"quadratic_ridge",c) for c in config["corrections"])
    comparisons=[]
    for dataset in EVAL_DATASETS:
        mask=masks[dataset]
        draws=np.random.default_rng(config["bootstrap_seed"]+EVAL_DATASETS.index(dataset)).integers(0,int(mask.sum()),size=(config["bootstrap_repetitions"],int(mask.sum())))
        for kind,ref,rc,new,nc in specs:
            comparisons.append({"comparison":kind,"reference_base_model":ref,"reference_correction":rc,
                "candidate_base_model":new,"candidate_correction":nc,"dataset":dataset,"role":role(dataset,nc),"n":int(mask.sum()),
                **paired_bootstrap(y[mask],predictions[(ref,rc)][mask],predictions[(new,nc)][mask],draws)})
    pd.DataFrame(comparisons).to_csv(out/"paired_error_comparisons.csv",index=False)
    # Preserve explicit high-scale interval differences rather than infer them from absolute errors.
    left,right=paired_frames(frame,"A12_A13_est_10b","A14_A15_est_70b")
    reference_delta=right[L_COLS].to_numpy()-left[L_COLS].to_numpy()
    shift=[]
    for c in config["corrections"]:
        pred_delta=corr[c][masks["A14_A15_est_70b"]]-corr[c][masks["A12_A13_est_10b"]]
        pack,_=metric_pack(reference_delta,pred_delta)
        shift.append({"correction":c,"n":len(left),"supplied_mean_delta":float(reference_delta.mean()),
            "predicted_mean_delta":float(pred_delta.mean()),"role":"same_recipe_supplied_estimate_shift; identical_for_all_base_models",**pack})
    pd.DataFrame(shift).to_csv(out/"high_scale_shift.csv",index=False)
    dump(out/"model_parameters.json",{"p_columns":P_COLS,"loss_columns":L_COLS,
        "ilr_basis":helmert_basis(len(P_COLS)).tolist(),"zero_replacement_epsilon":config["epsilon"],
        "polynomial_powers":PolynomialFeatures(2,include_bias=False).fit(np.zeros((1,16))).powers_.tolist(),
        "base_models":parameters,"C1_domain_slope":(delta.mean(0)/X60).tolist(),
        "C1_global_slope":float(delta.mean()/X60),"C2_delta_model":json_model(c2,P_COLS[:-1]),
        "scale_formula":"x=log10(S/1M); correction = x/log10(60) times fitted 1M-to-60M difference"})
    checks=[]
    expected={"ilr_ridge":(0.2626453548842908,0.34644297705135874),"quadratic_ridge":(0.20191012143221612,0.2840065107729149)}
    for name,(mae,rmse) in expected.items():
        row=mf.query("base_model==@name and correction=='C0_none' and dataset=='A6_A7_test_1m'").iloc[0]
        error=max(abs(row.mae_domain_macro-mae),abs(row.rmse_pooled_all_domains-rmse))
        checks.append({"check":"historical_pure_p_benchmark","model":name,"max_absolute_difference":float(error),"passed":bool(error<1e-10)})
    historical=pd.read_csv(ROOT/"experiments/runs/q1-s03-handoff-audit-20260925-r01/metrics_aggregate.csv")
    legacy=historical[historical.base_model.eq("B1_Q_proxy")]
    new=mf[mf.base_model.eq("qproxy_only")]
    joined=legacy.merge(new,on=["correction","dataset"],suffixes=("_old","_new"))
    max_error=max(float(np.max(np.abs(joined[k+"_old"]-joined[k+"_new"]))) for k in ["rmse_pooled_all_domains","mae_domain_macro","rmse_mean_loss","mae_mean_loss"])
    checks.append({"check":"historical_quality_and_corrections_96_values","max_absolute_difference":max_error,"passed":bool(max_error<1e-10)})
    if not all(c["passed"] for c in checks):
        raise AssertionError(checks)
    dump(out/"validation.json",{"regression_checks":checks,"aggregate_rows":len(metrics),"domain_rows":len(per_domain),
        "paired_comparisons":len(comparisons),"oof_rows":len(oof_metrics)})
    q_design=np.c_[np.ones(len(p)),p]
    q_error=float(np.max(np.abs(q-q_design@np.linalg.lstsq(q_design,q,rcond=None)[0])))
    dump(out/"audit.json",{**input_audit,"input_sha256":source_hash,"quality_linear_reconstruction_max_error":q_error,
        "python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__,
        "base_fit_rows":int(train.sum()),"base_model_rows_identical":True,"parameters_retuned":False,
        "scale_calibration_pairs":len(a6),"row_predictions_exported":False,
        "interpretation_limits":["Retrospective comparison on previously inspected data, not a new independent blind evaluation.",
            "C2 fixed alpha was historically selected on A6/A8; OOF is conditional on that choice, not nested selection validation.",
            "Quality is a deterministic feature of composition; adding it changes representation and regularization, not independent causal information.",
            "A12/A14 are seen training recipes and supplied estimated Loss; no true high-scale performance claim.",
            "Paired bootstrap intervals condition on frozen fitted models and are descriptive, not simultaneous or multiplicity-adjusted inference.",
            "Scale slopes are calibrated at only one interval; uncertainty in extrapolation shape is not covered.",
            "Quadratic polynomial terms are in ilr coordinates, not direct causal pairwise domain interactions."]})
    # Small paper tables retain all corrections; no winner selected from the evaluation results.
    cols=["base_model","correction","dataset","role","n","rmse_pooled_all_domains","mae_domain_macro","rmse_mean_loss","mae_mean_loss","r2_domain_macro"]
    mf[mf.base_model.isin(["ilr_ridge","quadratic_ridge"]) & ~mf.dataset.eq("A4_A5_train_1m")][cols].to_csv(out/"table_pure_mixture_scale.csv",index=False)
    pd.DataFrame(comparisons).query("comparison=='optional_quality'").to_csv(out/"table_optional_quality.csv",index=False)
    print(json.dumps({"run_id":config["run_id"],"aggregate_rows":len(metrics),"regression_checks":"PASS"}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    run(args.config,args.output)
