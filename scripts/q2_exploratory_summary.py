"""Combine the Q1 quality-interface and Q2 exploratory audit outputs.

This is a read-only reporting step.  It does not join A and B rows, refit a
model, repair B8, or promote a semi-synthetic Q_score to the Q1 LaTeX score.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default="experiments/runs/q2-exploratory-summary-20260925-r01",
        help="output run directory",
    )
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "q_interface": ROOT / "experiments/runs/q2-qp-interface-preflight-20260925-r01/metrics.json",
        "b1": ROOT / "experiments/runs/q2-m0-baseline-audit-20260925-r02/metrics.json",
        "m1": ROOT / "experiments/runs/q2-m1-sensitivity-audit-20260925-r02/metrics.json",
        "b8": ROOT / "experiments/runs/q2-b8-provenance-20260925-r02/metrics.json",
        "q1_interface": ROOT / "experiments/runs/q1-latex-q-interface-20260925-r01/metrics.json",
        "mapping_decision": ROOT / "experiments/runs/q1-domain-conflict-review-decision-20260925-r01/metrics.json",
        "semantic_evidence": ROOT / "experiments/runs/q1-domain-semantic-evidence-20260925-r01/metrics.json",
    }
    data = {name: read_json(path) for name, path in paths.items()}

    qi = data["q_interface"]
    b1 = data["b1"]
    m1 = data["m1"]
    b8 = data["b8"]
    semantic = data["semantic_evidence"]

    q_interface_ok = all(
        [
            qi["checks"]["p_finite"],
            qi["checks"]["q_finite"],
            qi["checks"]["q_in_0_100"],
            qi["checks"]["q_interval_ordered"],
            qi["checks"]["duplicate_dataset_index_count"] == 0,
        ]
    )
    b8_blocked = b8["status"] == "BLOCKED_B8_PROVENANCE_AND_DIRECTION"

    metrics = {
        "schema_version": "q2.exploratory.summary.v1",
        "run_id": "q2-exploratory-summary-20260925-r01",
        "task_id": "T-Q2-MIGRATION",
        "status": "EXPLORATORY_Q2_AUDIT_COMPLETE_FORMAL_FIT_BLOCKED",
        "scope": [
            "freeze the Q1 LaTeX CRITIC-TOPSIS Q interface for exploratory use",
            "report the grouped B1 baseline audit",
            "report the conditional B6/B7 semi-synthetic quality sensitivity audit",
            "keep B8 as a provenance-and-direction blocker",
        ],
        "inputs": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "checks": {
            "q1_qp_interface_passed": q_interface_ok,
            "q1_mapping_decision_present": True,
            "b1_grouped_holdout_passed": b1["checks"]["grouped_leave_one_N_size_out"],
            "b1_external_diagnostics_separate": b1["checks"]["external_diagnostics_kept_separate"],
            "m1_grouped_nd_cell_holdout_passed": m1["checks"]["grouped_ND_cell_holdout"],
            "m1_b7_nested_not_independent": not m1["checks"]["B7_extension_treated_as_independent_validation"],
            "b8_blocked": b8_blocked,
            "formal_joint_fit": False,
            "a_to_b_row_join": False,
        },
        "q1_quality_interface": {
            "source": "Q1 first-subquestion LaTeX CRITIC-TOPSIS score",
            "row_count": qi["checks"]["row_count"],
            "p_column_count": qi["checks"]["p_column_count"],
            "observed_rows": qi["checks"]["observed_rows"],
            "extrapolation_rows": qi["checks"]["extrapolation_rows"],
            "p_sum_max_abs_error": qi["checks"]["p_sum_max_abs_error"],
            "q_range": [0.0, 100.0],
            "join_policy": qi["join_policy"],
            "anchor_quality_score_count": len(data["q1_interface"]["anchor_quality_scores"]),
            "official_reference_rows": semantic["official_reference_rows"],
            "exploratory_prior_rows": semantic["exploratory_prior_rows"],
            "formal_mapping_validated": semantic["formal_mapping_validated"],
        },
        "b1_baseline": {
            "status": b1["status"],
            "folds": b1["internal_metrics"]["folds"],
            "r2_range": [b1["internal_metrics"]["r2_min"], b1["internal_metrics"]["r2_max"]],
            "rmse_range": [b1["internal_metrics"]["rmse_min"], b1["internal_metrics"]["rmse_max"]],
            "external_diagnostics": b1["external_diagnostics"],
            "interpretation": "descriptive B1 baseline; no universal cross-source scaling-law claim",
        },
        "b6_b7_quality_sensitivity": {
            "status": m1["status"],
            "q_field": "B6/B7 Q_score (semi-synthetic field; not replaced by Q1 Q)",
            "folds": m1["internal_metrics"]["folds"],
            "r2_range": [m1["internal_metrics"]["r2_min"], m1["internal_metrics"]["r2_max"]],
            "rmse_range": [m1["internal_metrics"]["rmse_min"], m1["internal_metrics"]["rmse_max"]],
            "G_mean": m1["parameter_stability"]["G"]["mean"],
            "G_sd": m1["parameter_stability"]["G"]["sd"],
            "b7_extension": m1["nested_extension"],
            "interpretation": "conditional sensitivity result; B7 extension is nested and not independent validation",
        },
        "b8_gate": {
            "status": b8["status"],
            "data_type_counts": b8["files"]["B8"]["data_type_counts"],
            "q_monotonicity": b8["files"]["B8"]["q_monotonicity"],
            "blocking_flags": b8["blocking_flags"],
            "required_evidence_to_unlock": b8["required_evidence_to_unlock"],
        },
        "decision": {
            "allowed_now": [
                "use Q1-derived Q and 17-domain p as an explicitly exploratory A-side interface",
                "report B1 grouped baseline and B6/B7 conditional sensitivity as separate evidence layers",
                "run mapping and Q-interface sensitivity analyses without claiming identification",
            ],
            "blocked_now": [
                "formal A-B joint fit or row-level A-B merge",
                "including B8 in a quality fit",
                "treating B6/B7 Q_score as the Q1 LaTeX Q",
                "causal quality effect, universal scaling law, or independent B7 validation",
            ],
        },
        "next_gates": [
            "obtain B8 generator/version, Q definition and direction, and calibrated/extrapolated split rule",
            "obtain a documented A-B bridge key or keep p as a scenario-level exploratory interface",
            "complete Q1 final acceptance before promoting Q/p beyond exploratory analysis",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (out / "gate_table.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["gate", "status", "evidence", "consequence"])
        writer.writerows(
            [
                ["Q1 LaTeX Q/p interface", "PASS_EXPLORATORY", "1214 rows; 17 p columns; finite and ordered intervals", "usable only as declared exploratory interface"],
                ["B1 grouped baseline", "PASS_EXPLORATORY", "8 leave-one-N-size-out folds; R2 > 0.9999992 internally", "descriptive B1 baseline; external diagnostics remain separate"],
                ["B6/B7 conditional sensitivity", "PASS_EXPLORATORY", "5 grouped N-D cell folds; R2 0.9526–0.9705", "conditional semi-synthetic result; no causal claim"],
                ["B8 provenance/direction", "BLOCKED", "1311 increasing-loss steps vs 2 decreasing-loss steps; missing source notes", "exclude from fit until metadata and direction are resolved"],
                ["A-B row linkage", "BLOCKED", "no documented row-level bridge key", "no formal joint fit or identified p effect"],
            ]
        )

    readme = """# Q2 exploratory summary\n\nThis run consolidates the Q1 LaTeX quality-score interface and the read-only Q2 audits. The Q1-derived `Q` and 17-domain `p` are an exploratory interface only: seven anchor domain scores are directly checked against the frozen Q1 table, six semantic-evidence rows have official/reference support, and eleven rows remain exploratory semantic priors; formal mapping validation is still false. B1 is reported as a grouped baseline; B6/B7 is a conditional semi-synthetic sensitivity result using its own `Q_score`; B8 is excluded because provenance and quality-direction gates are unresolved. No A-to-B row join, formal joint fit, causal claim, or universal scaling-law claim is made.\n"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    doc = ROOT / "docs/decisions/q2-exploratory-summary-20260925-r01.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        """# 问题二当前实验汇总（探索性）

状态：`EXPLORATORY_Q2_AUDIT_COMPLETE_FORMAL_FIT_BLOCKED`。

本轮已把问题一第一问 LaTeX 中的 CRITIC-TOPSIS 质量分数冻结为问题二的探索性 Q 接口，并检查 17 域配比向量：1214 行、17 个 p 列，p 和误差不超过 1.6e-15，Q 有限且位于 0--100，区间有序。这里的‘17 域可计算’不等于‘17 域已验证’：当前冻结表中有 7 个 Q1 锚定域分数，语义证据表有 6 个官方/参考行和 11 个探索性先验行，formal_mapping_validated 仍为 false。A4--A15 中 1088 行有观测 Loss，126 行属于估计/外推角色。该接口没有与 B 数据逐行连接。

B1 的 8 折按参数规模分组留出审计通过，内部 R2 为 0.9999992--0.9999998；B2/B4/B5 只作外部诊断，不能据此提出跨来源统一标度律。B6/B7 的 5 折 N-D 单元留出 R2 为 0.9526--0.9705，质量系数 G 的均值为 0.3622；B7 包含全部 B6 行，扩展行是嵌套诊断，不是独立验证。这里的 `Q_score` 是 B6/B7 半合成字段，不能改名为或替代 Q1 LaTeX 的 Q。

B8 保持阻断：其 1311 个固定 N,D 相邻步表现为 Loss 随 Q 增大而增大，仅 2 个相反步，同时 B7/B8 缺少来源和生成规则记录，calibrated 与 extrapolated 也需要分开解释。因此没有反转、删点或纳入拟合。

当前可以继续做 Q1-derived Q/p 的场景级敏感性、接口审计和分层报告；仍不能进行 A-B 行级合并、正式联合拟合、因果质量效应或普适标度律结论。解锁下一阶段需要补齐 B8 生成元数据，并提供 A-B 的可追溯桥接键；若没有桥接键，就把 p 明确写成探索性场景变量。
""",
        encoding="utf-8",
    )

    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "out": str(out.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
