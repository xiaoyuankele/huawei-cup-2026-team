"""Build a labelled prototype of the additive Q2 scenario model.

This is intentionally a scenario generator, not a joint-observation fitter.
It uses the validated component models and records the assumptions used to
transport Q1 quality to the B quality axis and to center the Q1 mixture effect.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge


from q2_research_paths import REPO, RAW_ROOT as RAW, RUNS, source_ref
OUT = RUNS / "q2-combined-scenario-20260925"
BRIDGE = RUNS / "q2-quality-scaling-linkage-20260925" / "q1_to_q2_quality_linkage.csv"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bdir = RAW / "B_scaling_laws"
    b1 = pd.read_csv(bdir / "pythia_training_log_existing.csv")
    b7 = pd.read_csv(bdir / "supplementary_NQ_experiment_expanded.csv")
    bridge = pd.read_csv(BRIDGE)
    observed = bridge[bridge["loss_observed"] == True].copy()  # noqa: E712

    # B1 scale component.
    scale_model = LinearRegression().fit(
        np.log(b1[["N_params_B", "D_tokens_B"]].to_numpy(float)), b1["val_loss"].to_numpy(float)
    )

    # B7 residual quality slope, centered so the scale baseline remains the
    # absolute B1 baseline. The source intercept is intentionally not carried
    # into the scenario model because A and B have different Loss definitions.
    b7_base = scale_model.predict(np.log(b7[["N_params_B", "D_tokens_B"]].to_numpy(float)))
    q_ref = float(b7["Q_score"].median())
    q_resid_model = LinearRegression().fit(
        (b7[["Q_score"]].to_numpy(float) - q_ref), b7["val_loss"].to_numpy(float) - b7_base
    )
    q_slope = float(q_resid_model.coef_[0])

    # Q1 mixture component. Use the 1M observed training block and center the
    # predicted composition response at its training mean.
    p_cols = [c for c in bridge.columns if c.startswith("p_")]
    train = bridge[bridge["dataset"] == "A4_A5_train_1m"].copy()
    x_cols = p_cols[:-1]
    mixture_model = Ridge(alpha=1e-5).fit(
        train[x_cols].to_numpy(float), train["loss_mean_13_domains"].to_numpy(float)
    )
    mix_ref = float(train["loss_mean_13_domains"].mean())
    observed["delta_p_mean_loss"] = mixture_model.predict(observed[x_cols].to_numpy(float)) - mix_ref

    # Two explicitly assumption-based maps from Q1's dimensionless proxy to
    # the B7 Q control scale. No paired A/B observations identify these maps.
    q_min_b, q_max_b = float(b7.Q_score.min()), float(b7.Q_score.max())
    mapping_rows = []
    for axis in ["Q_A_topsis_0_1", "quality_score_soft_proxy_0_1"]:
        q_min_a = float(observed[axis].min())
        q_max_a = float(observed[axis].max())
        mapped = q_min_b + (observed[axis] - q_min_a) / (q_max_a - q_min_a) * (q_max_b - q_min_b)
        tmp = observed[["dataset", "index", axis, "delta_p_mean_loss"]].copy()
        tmp = tmp.rename(columns={axis: "Q_A"})
        tmp["quality_axis"] = axis
        tmp["Q_B_assumed"] = mapped
        tmp["delta_Q_mean_loss"] = q_slope * (mapped - q_ref)
        mapping_rows.append(tmp)
    support = pd.concat(mapping_rows, ignore_index=True)
    support.to_csv(OUT / "q1_support_effects_for_combination.csv", index=False, encoding="utf-8-sig")

    # A small, readable scenario grid: 10 observed Q1 compositions, all B1
    # parameter sizes, and five B1 token-count quantiles.
    example = observed.sort_values(["dataset", "index"]).head(10).copy()
    n_grid = sorted(b1["N_params_B"].unique())
    d_grid = b1["D_tokens_B"].quantile([0, .25, .5, .75, 1]).to_numpy()
    rows = []
    for _, arow in example.iterrows():
        for axis in ["Q_A_topsis_0_1", "quality_score_soft_proxy_0_1"]:
            qa_min = float(observed[axis].min())
            qa_max = float(observed[axis].max())
            qb = q_min_b + (float(arow[axis]) - qa_min) / (qa_max - qa_min) * (q_max_b - q_min_b)
            dq = q_slope * (qb - q_ref)
            dp = float(arow["delta_p_mean_loss"])
            for n in n_grid:
                for d in d_grid:
                    base = float(scale_model.predict(np.array([[np.log(n), np.log(d)]], dtype=float))[0])
                    variants = {
                        "scale_only": base,
                        "scale_plus_Q": base + dq,
                        "scale_plus_p": base + dp,
                        "scale_plus_Q_plus_p": base + dq + dp,
                    }
                    for variant, value in variants.items():
                        rows.append({
                            "source_row_dataset": arow["dataset"],
                            "source_row_index": int(arow["index"]),
                            "quality_axis": axis,
                            "N_params_B": float(n),
                            "D_tokens_B": float(d),
                            "Q_A": float(arow[axis]),
                            "Q_B_assumed": float(qb),
                            "p_effect_centered": dp,
                            "Q_effect_centered": dq,
                            "scenario_variant": variant,
                            "predicted_loss": float(value),
                            "observed_joint_row": False,
                            "interpretation": "model_based_scenario",
                        })
    scenario_df = pd.DataFrame(rows)
    scenario_df.to_csv(OUT / "combined_scenario_examples.csv", index=False, encoding="utf-8-sig")
    sensitivity = (
        scenario_df.groupby(["quality_axis", "scenario_variant"], as_index=False)
        .agg(predicted_loss_min=("predicted_loss", "min"),
             predicted_loss_median=("predicted_loss", "median"),
             predicted_loss_max=("predicted_loss", "max"),
             predicted_loss_mean=("predicted_loss", "mean"),
             n_scenarios=("predicted_loss", "size"))
    )
    sensitivity.to_csv(OUT / "scenario_sensitivity_summary.csv", index=False, encoding="utf-8-sig")

    coeff = {
        "run_id": "q2-combined-scenario-20260925",
        "status": "SCENARIO_ONLY / REVIEW_REQUIRED",
        "scale_model": {
            "fit_source": "B1",
            "intercept": float(scale_model.intercept_),
            "coef_log_N": float(scale_model.coef_[0]),
            "coef_log_D": float(scale_model.coef_[1]),
        },
        "quality_model": {
            "fit_source": "B7 residual relative to B1 scale baseline",
            "q_reference": q_ref,
            "q_slope": q_slope,
            "B_Q_range": [q_min_b, q_max_b],
        },
        "mixture_model": {
            "fit_source": "A4/A5",
            "reference_mean_loss": mix_ref,
            "p_columns": p_cols,
            "effect_is_centered": True,
        },
        "quality_maps": [
            "affine min-max from observed Q1 axis to B7 Q range",
            "not empirically identified because no paired A/B quality observations exist",
        ],
        "scenario_variants": ["scale_only", "scale_plus_Q", "scale_plus_p", "scale_plus_Q_plus_p"],
        "warning": "The combined table is not an observed joint sample. The additive Q+p variant is a sensitivity scenario and may double count quality information because Q_A is derived from p.",
    }
    (OUT / "scenario_manifest.json").write_text(json.dumps(coeff, ensure_ascii=False, indent=2), encoding="utf-8")
    report = "# Q2 组合情景敏感性\n\n"
    report += "本文件只总结模型生成的情景，不是联合观测验证。\n\n"
    report += "- `scale_only`：只使用 B1 规模基线。\n"
    report += "- `scale_plus_Q`：加入 Q1 质量代理经过 min-max 假设映射后的质量效应。\n"
    report += "- `scale_plus_p`：加入 A4/A5 配比模型相对于训练均值的中心化效应。\n"
    report += "- `scale_plus_Q_plus_p`：同时加入质量和配比，是敏感性情景，可能重复计算质量信息。\n\n"
    report += "Q1 到 B 的质量轴转换没有成对观测支持，因此不应把情景中的 `Q_B_assumed` 当作校准后的真实 Q。\n"
    (OUT / "scenario_report.md").write_text(report, encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Q2 combined scenario prototype\n\n"
        "This run combines validated component models only for labelled scenario prediction. "
        "It does not claim observed joint rows. `scale_plus_Q_plus_p` is an additive sensitivity "
        "variant and may double count quality information because Q1 quality is computed from p.\n",
        encoding="utf-8",
    )
    print(json.dumps(coeff, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
