"""Compute model-internal elasticities without fitting a new joint model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def summary_rows(frame: pd.DataFrame, group: str, columns: list[str]) -> list[dict[str, object]]:
    result = []
    for col in columns:
        values = frame[col].astype(float)
        result.append(
            {
                "group": group,
                "quantity": col,
                "n": int(values.notna().sum()),
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=0)),
                "p05": float(values.quantile(0.05)),
                "p50": float(values.quantile(0.50)),
                "p95": float(values.quantile(0.95)),
                "min": float(values.min()),
                "max": float(values.max()),
            }
        )
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="experiments/runs/q2-elasticity-audit-20260925-r01")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    tables = out / "tables"
    tables.mkdir(exist_ok=True)

    source_metrics_path = ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json"
    b1_path = ROOT / "data/origin/real_attachments/B_scaling_laws/pythia_training_log_existing.csv"
    b6_path = ROOT / "data/origin/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv"
    b7_path = ROOT / "data/origin/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv"
    source = json.loads(source_metrics_path.read_text(encoding="utf-8"))
    b1 = pd.read_csv(b1_path)
    b6 = pd.read_csv(b6_path)
    b7 = pd.read_csv(b7_path)

    E, A, B, alpha, beta = source["M0"]["fit_full_B1"]
    n1 = b1["N_params_B"].to_numpy(float)
    d1 = b1["D_tokens_B"].to_numpy(float)
    l0 = E + A * n1 ** (-alpha) + B * d1 ** (-beta)
    b1_out = b1[["run_id", "N_params_B", "D_tokens_B", "val_loss"]].copy()
    b1_out["L_hat"] = l0
    b1_out["epsilon_N"] = -A * alpha * n1 ** (-alpha) / l0
    b1_out["epsilon_D"] = -B * beta * d1 ** (-beta) / l0
    b1_out.to_csv(tables / "m0_row_elasticities.csv", index=False, encoding="utf-8-sig")

    E1, A1, B1, G1, alpha1, beta1 = source["M1"]["fit_B6"]
    def m1_elasticity(frame: pd.DataFrame) -> pd.DataFrame:
        n = frame["N_params_B"].to_numpy(float)
        d = frame["D_tokens_B"].to_numpy(float)
        q = frame["Q_score"].to_numpy(float)
        loss = E1 + A1 * n ** (-alpha1) + B1 * d ** (-beta1) + G1 * (1.0 - q)
        out_frame = frame[["experiment_id", "N_params_B", "D_tokens_B", "Q_score", "val_loss"]].copy()
        out_frame["L_hat"] = loss
        out_frame["epsilon_N"] = -A1 * alpha1 * n ** (-alpha1) / loss
        out_frame["epsilon_D"] = -B1 * beta1 * d ** (-beta1) / loss
        out_frame["epsilon_Q_score"] = -G1 * q / loss
        out_frame["epsilon_impurity"] = G1 * (1.0 - q) / loss
        out_frame["dlnN_dlnQ_score"] = -out_frame["epsilon_Q_score"] / out_frame["epsilon_N"]
        out_frame["dlnD_dlnQ_score"] = -out_frame["epsilon_Q_score"] / out_frame["epsilon_D"]
        base = E1 + A1 * n ** (-alpha1) + B1 * d ** (-beta1)
        out_frame["loss_qscore_0_1"] = base + G1 * 0.9
        out_frame["loss_qscore_1_0"] = base
        out_frame["relative_loss_reduction_qscore_0_1_to_1_0"] = (out_frame["loss_qscore_0_1"] - out_frame["loss_qscore_1_0"]) / out_frame["loss_qscore_0_1"]
        return out_frame

    b6_out = m1_elasticity(b6)
    b7_out = m1_elasticity(b7)
    b6_out.to_csv(tables / "m1_b6_elasticities.csv", index=False, encoding="utf-8-sig")
    b7_out.to_csv(tables / "m1_b7_elasticities_nested.csv", index=False, encoding="utf-8-sig")

    summary = summary_rows(b1_out, "M0_B1", ["epsilon_N", "epsilon_D"])
    summary += summary_rows(b6_out, "M1_B6", ["epsilon_N", "epsilon_D", "epsilon_Q_score", "epsilon_impurity", "dlnN_dlnQ_score", "dlnD_dlnQ_score", "relative_loss_reduction_qscore_0_1_to_1_0"])
    summary += summary_rows(b7_out, "M1_B7_nested", ["epsilon_N", "epsilon_D", "epsilon_Q_score", "epsilon_impurity", "dlnN_dlnQ_score", "dlnD_dlnQ_score", "relative_loss_reduction_qscore_0_1_to_1_0"])
    pd.DataFrame(summary).to_csv(tables / "elasticity_summary.csv", index=False, encoding="utf-8-sig")

    m0_folds = [row["fit"] for row in source["M0"]["leave_one_parameter_size_out"]]
    m1_folds = [row["fit"] for row in source["M1"]["grouped_ND_cell_cv"]]
    fold_rows = []
    for i, fit in enumerate(m0_folds, 1):
        fold_rows.append({"model": "M0", "fold": f"fold_{i}", "E": fit[0], "A": fit[1], "B": fit[2], "alpha": fit[3], "beta": fit[4], "G": ""})
    for i, fit in enumerate(m1_folds, 1):
        fold_rows.append({"model": "M1", "fold": f"fold_{i}", "E": fit[0], "A": fit[1], "B": fit[2], "alpha": fit[3], "beta": fit[5], "G": fit[3]})
    # M1 fit ordering is [E, A, B, alpha, beta, G] in the original metrics.
    for i, fit in enumerate(m1_folds, 1):
        fold_rows[-len(m1_folds) + i - 1].update({"alpha": fit[3], "beta": fit[4], "G": fit[5]})
    pd.DataFrame(fold_rows).to_csv(tables / "parameter_fold_values.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "schema_version": "q2.elasticity.audit.v1",
        "run_id": "q2-elasticity-audit-20260925-r01",
        "task_id": "T-Q2-MIGRATION",
        "status": "EXPLORATORY_MODEL_INTERNAL_ELASTICITY_AUDIT",
        "inputs": {
            "source_model_metrics": str(source_metrics_path.relative_to(ROOT)).replace("\\", "/"),
            "source_model_metrics_sha256": sha256(source_metrics_path),
            "B1": {"path": str(b1_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(b1_path), "rows": len(b1)},
            "B6": {"path": str(b6_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(b6_path), "rows": len(b6)},
            "B7": {"path": str(b7_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(b7_path), "rows": len(b7)},
        },
        "formulas": {
            "epsilon_N": "dL/dN * N/L",
            "epsilon_D": "dL/dD * D/L",
            "epsilon_Q_score": "dL/dQ_score * Q_score/L; M1 native B6/B7 scale only",
            "epsilon_impurity": "dL/d(1-Q_score) * (1-Q_score)/L; M1 native B6/B7 scale only",
            "dlnN_dlnQ_score": "-epsilon_Q_score/epsilon_N",
            "dlnD_dlnQ_score": "-epsilon_Q_score/epsilon_D",
        },
        "checks": {
            "m0_rows": len(b1_out),
            "m1_b6_rows": len(b6_out),
            "m1_b7_rows": len(b7_out),
            "m0_finite": bool(np.isfinite(b1_out[["L_hat", "epsilon_N", "epsilon_D"]].to_numpy()).all()),
            "m1_finite": bool(np.isfinite(b6_out[["L_hat", "epsilon_N", "epsilon_D", "epsilon_Q_score"]].to_numpy()).all()),
            "B7_nested_not_independent": True,
            "Q1_Q_used_in_M1": False,
            "a_to_b_row_join": False,
            "formal_joint_fit": False,
        },
        "full_fit_parameters": {
            "M0_B1": {"E": E, "A": A, "B": B, "alpha": alpha, "beta": beta},
            "M1_B6": {"E": E1, "A": A1, "B": B1, "alpha": alpha1, "beta": beta1, "G": G1},
        },
        "quality_counterfactual_within_M1": {
            "q_score_low": 0.1,
            "q_score_high": 1.0,
            "absolute_loss_change_high_minus_low": -0.9 * G1,
            "B6_relative_loss_reduction_summary": {
                "mean": float(b6_out["relative_loss_reduction_qscore_0_1_to_1_0"].mean()),
                "p05": float(b6_out["relative_loss_reduction_qscore_0_1_to_1_0"].quantile(0.05)),
                "p95": float(b6_out["relative_loss_reduction_qscore_0_1_to_1_0"].quantile(0.95)),
            },
            "interpretation": "conditional M1 counterfactual only; not Q1 migration and not causal evidence",
        },
        "interpretation": [
            "Elasticities are local derivatives of the frozen model forms, not new fitted effects.",
            "M0 epsilon_N and epsilon_D describe B1's conditional scaling baseline.",
            "M1 epsilon_Q_score and substitution ratios apply only to the native semi-synthetic B6/B7 Q_score.",
            "No Q1-derived Q, A-side p, B8, or A-B row linkage enters this audit.",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        "# Q2 model-internal elasticity audit\n\n"
        "This run computes local elasticities from the frozen M0 B1 and M1 B6/B7 parameterizations. It does not refit a model, merge A and B, or treat B6/B7 Q_score as the Q1-derived Q.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "checks": metrics["checks"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
