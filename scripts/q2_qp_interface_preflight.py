"""Preflight the approved exploratory Q/p interface for Q2 without fitting."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


DATASETS = [
    ("A4_A5_train_1m", "fit", True),
    ("A6_A7_test_1m", "validation", True),
    ("A8_A9_test_60m", "validation", True),
    ("A10_A11_test_1b", "validation", True),
    ("A12_A13_est_10b", "extrapolation", False),
    ("A14_A15_est_70b", "extrapolation", False),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    wide_path = root / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/tables/A4_A15_quality_transfer_soft_wide.csv"
    q_interface = root / "experiments/runs/q1-latex-q-interface-20260925-r01/metrics.json"
    decision = root / "experiments/runs/q1-domain-conflict-review-decision-20260925-r01/metrics.json"
    wide = pd.read_csv(wide_path)
    p_cols = [column for column in wide.columns if column.startswith("p_")]
    required = {"dataset", "index", "quality_score_soft_proxy_0_100", "quality_score_soft_low_0_100", "quality_score_soft_high_0_100", "quality_score_soft_range_width_0_100", "loss_observed"}
    missing = sorted(required - set(wide.columns))
    if missing:
        raise RuntimeError(f"missing Q/p interface columns: {missing}")
    p_sum = wide[p_cols].sum(axis=1)
    q = wide["quality_score_soft_proxy_0_100"]
    q_low = wide["quality_score_soft_low_0_100"]
    q_high = wide["quality_score_soft_high_0_100"]
    duplicate_keys = int(wide.duplicated(["dataset", "index"]).sum())
    summary_rows = []
    for dataset, role, observed in DATASETS:
        subset = wide[wide["dataset"] == dataset]
        summary_rows.append(
            {
                "dataset": dataset,
                "role": role,
                "loss_observed": observed,
                "row_count": len(subset),
                "mean_q_soft_0_100": float(subset["quality_score_soft_proxy_0_100"].mean()),
                "min_q_soft_0_100": float(subset["quality_score_soft_proxy_0_100"].min()),
                "max_q_soft_0_100": float(subset["quality_score_soft_proxy_0_100"].max()),
                "mean_q_range_width_0_100": float(subset["quality_score_soft_range_width_0_100"].mean()),
                "mean_official_mapped_mass": float(subset["official_mapped_mass"].mean()),
                "p_sum_max_abs_error": float((subset[p_cols].sum(axis=1) - 1.0).abs().max()),
            }
        )

    run_id = "q2-qp-interface-preflight-20260925-r01"
    run_dir = root / "experiments/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(run_dir / "dataset_summary.csv", index=False, encoding="utf-8-sig")
    metrics = {
        "schema_version": "q2.qp.interface.preflight.v1",
        "run_id": run_id,
        "task_id": "T-Q2-MIGRATION",
        "status": "Q2_QP_INTERFACE_PREFLIGHT_EXPLORATORY",
        "inputs": {
            "q1_latex_interface": str(q_interface.relative_to(root)).replace("\\", "/"),
            "q1_latex_interface_sha256": sha256(q_interface),
            "approved_mapping_decision": str(decision.relative_to(root)).replace("\\", "/"),
            "q_a4_a15_wide": str(wide_path.relative_to(root)).replace("\\", "/"),
            "q_a4_a15_wide_sha256": sha256(wide_path),
        },
        "checks": {
            "row_count": len(wide),
            "p_column_count": len(p_cols),
            "p_sum_max_abs_error": float((p_sum - 1.0).abs().max()),
            "p_finite": bool(wide[p_cols].notna().all().all() and wide[p_cols].apply(lambda column: pd.api.types.is_numeric_dtype(column)).all()),
            "q_finite": bool(q.notna().all()),
            "q_in_0_100": bool(((q >= 0) & (q <= 100)).all()),
            "q_interval_ordered": bool(((q_low <= q) & (q <= q_high)).all()),
            "duplicate_dataset_index_count": duplicate_keys,
            "observed_rows": int(wide["loss_observed"].sum()),
            "extrapolation_rows": int((~wide["loss_observed"]).sum()),
        },
        "dataset_summary": summary_rows,
        "join_policy": "Q/p are a declared interface; no A-to-B row-number join is performed",
        "formal_fit": False,
        "limitations": [
            "Q is the Q1 first-subquestion composite proxy and the 11 inferred mappings remain exploratory priors.",
            "A12-A15 are extrapolation/estimated roles, not independent validation.",
            "This preflight does not resolve B8's quality-direction issue or estimate scaling-law parameters.",
        ],
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        "# Q2 Q/p interface preflight\n\n"
        "This read-only preflight validates the approved exploratory Q/p table before any Q2 model fit. It checks row-level structure, ranges, intervals, duplicate keys, and dataset roles. It does not join A and B rows or fit a scaling law.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": run_id, "status": metrics["status"], "checks": metrics["checks"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
