"""Discrete p-policy panel for Q3 without inventing an A--B bridge.

The panel carries observed A-side mixture candidates alongside the already
computed Q3 N-D baseline scenarios.  It reports p-dependent A-side scores and
N-D resource allocations separately; it deliberately does not add them into a
joint objective.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
FEATURE_TABLE = ROOT / "experiments" / "runs" / "q1-scale-feature-table-20260924-r01" / "q1_scale_features_wide.csv"
STABILITY_RUN = ROOT / "experiments" / "runs" / "q1-p-stability-20260925-r01"
ND_TABLE = ROOT / "experiments" / "runs" / "q3-nd-baseline-20260925-r01" / "tables" / "q3_nd_baseline_scenarios.csv"
RUN_ID = "q3-p-conditional-20260925-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
EPSILONS = [1e-6, 1e-4, 1e-3]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def design(p: np.ndarray, epsilon: float) -> np.ndarray:
    return zero_replaced_clr(p, epsilon) @ helmert_basis(p.shape[1]).T


def scalar_score(y: np.ndarray, mean: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return ((y - mean) / sd).mean(axis=1)


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "tables").mkdir(exist_ok=True)
    feature = pd.read_csv(FEATURE_TABLE)
    train_feature = feature[feature["dataset"] == "A4_A5_train_1m"].sort_values("index")
    p_cols = [c for c in feature.columns if c.startswith("p_")]
    y = pd.read_csv(SOURCE / "train_pile_loss_1m.csv").sort_values("index")
    if not np.array_equal(train_feature["index"].to_numpy(), y["index"].to_numpy()):
        raise ValueError("A4/A5 index mismatch")
    p = train_feature[p_cols].to_numpy(float)
    y_values = y.drop(columns="index").to_numpy(float)
    mean = y_values.mean(axis=0)
    sd = y_values.std(axis=0, ddof=1)
    sd[sd == 0] = 1.0
    observed_score = scalar_score(y_values, mean, sd)

    candidate_summary = pd.read_csv(STABILITY_RUN / "candidate_summary.csv")
    candidate_indices = sorted(set([int(train_feature.iloc[int(np.argmin(observed_score))]["index"])] + candidate_summary["predicted_best_index"].astype(int).tolist()))
    candidate_rows = []
    for epsilon in EPSILONS:
        for kind in ("ilr_ridge", "quadratic_ridge"):
            if kind == "ilr_ridge":
                model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=10.0))])
            else:
                model = Pipeline([("poly", PolynomialFeatures(degree=2, include_bias=False)),
                                  ("scale", StandardScaler()), ("ridge", Ridge(alpha=10.0))])
            x = design(p, epsilon)
            model.fit(x, y_values)
            pred = model.predict(x)
            for index_value in candidate_indices:
                row_pos = int(np.flatnonzero(train_feature["index"].to_numpy() == index_value)[0])
                candidate_rows.append({
                    "candidate_index": index_value,
                    "model": kind,
                    "epsilon": epsilon,
                    "predicted_scalar_loss_z": float(scalar_score(pred[row_pos:row_pos + 1], mean, sd)[0]),
                    "observed_scalar_loss_z": float(observed_score[row_pos]),
                })
    panel = pd.DataFrame(candidate_rows)
    robust = panel.groupby("candidate_index", as_index=False).agg(
        observed_scalar_loss_z=("observed_scalar_loss_z", "first"),
        predicted_scalar_loss_z_mean=("predicted_scalar_loss_z", "mean"),
        predicted_scalar_loss_z_median=("predicted_scalar_loss_z", "median"),
        predicted_scalar_loss_z_min=("predicted_scalar_loss_z", "min"),
        predicted_scalar_loss_z_max=("predicted_scalar_loss_z", "max"),
        model_representation_count=("predicted_scalar_loss_z", "size"),
    )
    robust["predicted_policy_rank"] = robust["predicted_scalar_loss_z_mean"].rank(method="min").astype(int)
    robust = robust.sort_values("predicted_policy_rank")

    nd = pd.read_csv(ND_TABLE)
    scenario = robust.assign(_key=1).merge(nd.assign(_key=1), on="_key").drop(columns="_key")
    scenario["p_effect_in_nd_objective"] = False
    scenario["joint_A_B_loss_claim"] = False
    panel.to_csv(RUN_DIR / "tables/p_candidate_predictions.csv", index=False, encoding="utf-8-sig")
    robust.to_csv(RUN_DIR / "tables/p_candidate_summary.csv", index=False, encoding="utf-8-sig")
    scenario.to_csv(RUN_DIR / "tables/p_candidate_q3_nd_panel.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "run_id": RUN_ID,
        "status": "EXPERIMENTAL_REVIEW",
        "candidate_count": len(candidate_indices),
        "candidate_indices": candidate_indices,
        "model_count": len(panel),
        "q3_nd_scenario_count": int(len(nd)),
        "panel_rows": int(len(scenario)),
        "p_effect_in_nd_objective": False,
        "joint_A_B_loss_claim": False,
        "inputs": {
            "stability_run": {"path": str(STABILITY_RUN.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(STABILITY_RUN / "candidate_summary.csv")},
            "feature_table": {"path": str(FEATURE_TABLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(FEATURE_TABLE)},
            "nd_scenarios": {"path": str(ND_TABLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(ND_TABLE)},
        },
        "limitations": [
            "p is a discrete observed-candidate policy label; no continuous simplex optimum is produced",
            "A-side p scores and Q3 N-D allocations are reported separately",
            "no A-B row-level bridge or joint Loss objective is assumed",
            "Q is not included",
        ],
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(f"python={sys.version.split()[0]}\nplatform={platform.platform()}\npandas={pd.__version__}\n", encoding="utf-8")
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q3_p_conditional.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q3 discrete p conditional panel

运行号：`{RUN_ID}`。本运行承接 Q1 配比稳定性审计，选择 A4/A5 中实际观测过的 {len(candidate_indices)} 个候选配比行，并与 Q3 N-D 基线的 15 个预算—上下文场景做笛卡尔组合。

A 侧配比 Loss 预测与 Q3 N-D 资源分配分开报告，不把两者相加为一个未经验证的联合目标。因此这是一组条件性策略面板，不是 A–B 联合最优解。
""", encoding="utf-8")
    print(RUN_DIR)


if __name__ == "__main__":
    main()
