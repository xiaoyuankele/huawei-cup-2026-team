"""Preflight a four-quantity conditional Q2 interface without fitting a joint model."""

from __future__ import annotations

import argparse
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


def stat_row(quantity: str, source: str, values: np.ndarray, role: str, scale: str = "") -> dict[str, object]:
    return {
        "quantity": quantity,
        "source": source,
        "role": role,
        "scale": scale,
        "n": int(values.size),
        "min": float(np.min(values)),
        "mean": float(np.mean(values)),
        "max": float(np.max(values)),
        "finite": bool(np.isfinite(values).all()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="experiments/runs/q2-four-quantity-conditional-preflight-20260925-r01")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    q1_path = ROOT / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/tables/A4_A15_quality_transfer_soft_wide.csv"
    q1_metrics_path = ROOT / "experiments/runs/q1-latex-q-interface-20260925-r01/metrics.json"
    b1_path = ROOT / "data/origin/real_attachments/B_scaling_laws/pythia_training_log_existing.csv"
    b6_path = ROOT / "data/origin/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv"

    q1 = pd.read_csv(q1_path)
    b1 = pd.read_csv(b1_path)
    b6 = pd.read_csv(b6_path)
    q1_metrics = json.loads(q1_metrics_path.read_text(encoding="utf-8"))
    p_cols = [col for col in q1.columns if col.startswith("p_")]
    p = q1[p_cols].to_numpy(float)
    q = q1["quality_score_soft_proxy_0_100"].to_numpy(float)
    p_sum = p.sum(axis=1)

    support = [
        stat_row("N", "B1 pythia_training_log_existing.csv", b1["N_params_B"].to_numpy(float), "B1 main baseline"),
        stat_row("D", "B1 pythia_training_log_existing.csv", b1["D_tokens_B"].to_numpy(float), "B1 main baseline"),
        stat_row("Q_score_native_B", "B6 supplementary_NQ_experiment.csv", b6["Q_score"].to_numpy(float), "B6 semi-synthetic native quality"),
        stat_row("Q_A(p)_baseline", "A4-A15 Q1-derived interface", q, "A-side conditional interface"),
        stat_row("p_sum", "A4-A15 Q1-derived interface", p_sum, "A-side simplex check"),
    ]
    pd.DataFrame(support).to_csv(out / "four_quantity_support.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "schema_version": "q2.four.quantity.conditional.preflight.v1",
        "run_id": "q2-four-quantity-conditional-preflight-20260925-r01",
        "task_id": "T-Q2-MIGRATION",
        "status": "FOUR_QUANTITY_CONDITIONAL_INTERFACE_READY_NOT_IDENTIFIED",
        "candidate_form": "L_cond(N,D,Q_A(p)) = E + A*N^(-alpha) + B*D^(-beta) + G_bridge*(1-Q_A(p))",
        "quantity_roles": {
            "N": "B-side parameter count",
            "D": "B-side token count",
            "Q": "A-side Q1-derived composite score in 0-100 scale",
            "p": "A-side 17-domain simplex; Q_A(p)=sum_j p_j*q_j",
        },
        "checks": {
            "p_column_count": len(p_cols),
            "p_sum_max_abs_error": float(np.max(np.abs(p_sum - 1.0))),
            "q_finite": bool(np.isfinite(q).all()),
            "q_in_0_100": bool(((q >= 0) & (q <= 100)).all()),
            "q1_formal_mapping_validated": False,
            "a_to_b_row_join_key": False,
            "G_bridge_identifiable": False,
            "formal_joint_fit": False,
        },
        "identified_components": {
            "M0_E_A_B_alpha_beta": "available from B1 grouped baseline",
            "M1_G_native": "available only for B6/B7 native Q_score",
            "Q_A_of_p": "computable for A4-A15 scenario interface",
        },
        "unidentified_components": {
            "G_bridge": "No A-B row or batch bridge; cannot estimate Q1-derived Q effect on B Loss",
            "p_independent_B_effect": "No A-B linkage; cannot estimate an independent p coefficient in B model",
        },
        "support_summary": support,
        "interpretation": [
            "Four quantities are represented in the conditional research design, but only N,D are fitted on B1.",
            "Q_A(p) remains an A-side scenario input and is not converted to B6/B7 Q_score.",
            "The candidate form is a specification and sensitivity interface, not an identified fitted law.",
            "B8 remains excluded from this interface because its provenance and direction gates are unresolved.",
        ],
        "next_gate": "Only an external A-B bridge at row or batch level can unlock estimation of G_bridge or an independent p effect.",
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        "# Four-quantity conditional Q2 preflight\n\n"
        "This run represents N, D, Q and p in one conditional interface while keeping identifiability explicit. It does not fit a joint law, join A and B, convert Q1 Q to B6/B7 Q_score, or include B8.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "checks": metrics["checks"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
