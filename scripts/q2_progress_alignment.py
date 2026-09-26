"""Reconcile the canonical Q2 migration gate with newer exploratory runs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/runs/q2-progress-alignment-20260925-r01"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(rel: str) -> tuple[Path, dict]:
    path = ROOT / rel
    return path, json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    sources = {
        "migration_gate": "experiments/runs/q2-migration-gate-20250925-r01/metrics.json",
        "m3_preflight": "experiments/runs/q2-m3-preflight-20250925-r01/metrics.json",
        "interface_reaudit": "experiments/runs/q2-interface-reaudit-20260925-r01/metrics.json",
        "exploratory_summary": "experiments/runs/q2-exploratory-summary-20260925-r01/metrics.json",
        "qp_preflight": "experiments/runs/q2-qp-interface-preflight-20260925-r01/metrics.json",
        "scenario_sensitivity": "experiments/runs/q2-qp-scenario-sensitivity-20260925-r01/metrics.json",
        "b1": "experiments/runs/q2-m0-baseline-audit-20260925-r02/metrics.json",
        "m1": "experiments/runs/q2-m1-sensitivity-audit-20260925-r02/metrics.json",
        "b8": "experiments/runs/q2-b8-provenance-20260925-r02/metrics.json",
    }
    loaded = {}
    input_meta = {}
    for name, rel in sources.items():
        path, payload = load(rel)
        loaded[name] = payload
        input_meta[name] = {"path": rel, "sha256": sha256(path), "internal_run_id": payload.get("run_id")}

    gate = loaded["migration_gate"]
    reaudit = loaded["interface_reaudit"]
    summary = loaded["exploratory_summary"]
    qp = loaded["qp_preflight"]
    scenario = loaded["scenario_sensitivity"]
    scenario_summary_path = ROOT / "experiments/runs/q2-qp-scenario-sensitivity-20260925-r01/scenario_summary.csv"
    scenario_summary_rows = list(csv.DictReader(scenario_summary_path.open("r", encoding="utf-8-sig", newline="")))

    # The 6/17 and 7-anchor statements use different denominators and are
    # intentionally retained as separate facts.
    reconciliation = {
        "validated_candidate_mixture_mappings": reaudit["mapping"]["mapped_candidate_domains"],
        "mixture_domain_total": reaudit["mapping"]["total_mixture_domains"],
        "q1_anchor_score_count": summary["q1_quality_interface"]["anchor_quality_score_count"],
        "semantic_official_reference_rows": summary["q1_quality_interface"]["official_reference_rows"],
        "semantic_exploratory_prior_rows": summary["q1_quality_interface"]["exploratory_prior_rows"],
        "computed_qp_domains": summary["q1_quality_interface"]["p_column_count"],
        "formal_mapping_validated": summary["q1_quality_interface"]["formal_mapping_validated"],
        "q1_score_accepted_in_canonical_gate": reaudit["checks"]["q1_score_accepted"],
    }

    metrics = {
        "schema_version": "q2.progress.alignment.v1",
        "run_id": "q2-progress-alignment-20260925-r01",
        "task_id": "T-Q2-MIGRATION",
        "status": "ALIGNMENT_RECONCILED_FORMAL_GATE_BLOCKED",
        "canonical_repo_state": {
            "task_status": "PEER_REVIEW",
            "gate": "G0",
            "migration_gate_status": gate["status"],
            "m3_preflight_status": loaded["m3_preflight"]["status"],
            "canonical_blockers": gate["blockers"],
        },
        "reconciliation": reconciliation,
        "new_exploratory_evidence": {
            "qp_preflight_status": qp["status"],
            "qp_rows": qp["checks"]["row_count"],
            "qp_observed_rows": qp["checks"]["observed_rows"],
            "qp_extrapolation_rows": qp["checks"]["extrapolation_rows"],
            "scenario_status": scenario["status"],
            "scenario_count": scenario["scenario_count"],
            "scenario_max_abs_delta": max(float(row["delta_max_abs_0_100"]) for row in scenario_summary_rows),
            "scenario_formal_fit": scenario["checks"]["q2_model_fit"],
            "scenario_a_to_b_join": scenario["checks"]["a_to_b_row_join"],
        },
        "decision": {
            "formal_joint_fit_allowed": False,
            "allowed_claims": [
                "B1 grouped baseline and B2/B3/B4/B5 stratified diagnostics",
                "B6/B7 conditional semi-synthetic sensitivity",
                "Q1-derived Q/p interface structural preflight",
                "Q/p and approved c4 scenario sensitivity",
            ],
            "prohibited_claims": [
                "validated 17-domain quality mapping",
                "Q1 Q equals B6/B7 Q_score",
                "A-B row-level quality-Loss relationship",
                "formal joint L(N,D,Q,p) fit",
                "B8 quality effect or causal direction",
            ],
        },
        "bookkeeping": {
            "q2_interface_reaudit_indexed": False,
            "q2_p6_claim_boundaries_directory_present": False,
            "r02_internal_run_id_year_mismatch": [
                "q2-m0-baseline-audit-20260925-r02",
                "q2-m1-sensitivity-audit-20260925-r02",
                "q2-b8-provenance-20260925-r02",
            ],
        },
        "inputs": input_meta,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Q2 progress alignment\n\n"
        "This read-only report reconciles the canonical G0 migration gate and the newer exploratory Q/p artifacts. The newer artifacts extend the exploratory interface but do not change the formal gate.\n",
        encoding="utf-8",
    )

    doc = ROOT / "docs/decisions/q2-progress-alignment-20260925.md"
    doc.write_text(
        """# 问题二最新仓库进度对齐

状态：`ALIGNMENT_RECONCILED_FORMAL_GATE_BLOCKED`。

仓库任务 `T-Q2-MIGRATION` 当前仍为 `PEER_REVIEW`、`G0`。正式迁移门和 M3 失败即停预检都没有解锁，四个核心阻断仍然存在：Q1 分数尚未作为正式质量真值验收、A 与 B 没有逐行连接键、B8 的来源和质量方向未解决，以及正式联合模型的输入契约未满足。

本次对齐把两个容易混淆的口径分开：`6/17` 表示当前再审计中有 6 个混合域具有 direct/near_direct 的候选映射；`7 个锚定分数`表示当前 Q1 A1/full 分数表中可复核的质量锚点数量，其中包含 `c4`，不等于 7 个混合域都已完成映射。当前 17 域 Q/p 表可以计算，是把 11 个 inferred 域作为探索性语义先验保留下来的结果；`formal_mapping_validated=false`，因此它不能被称为 17 域已验证质量映射。

已经新增的 20260925 探索结果与仓库原有结论一致：Q/p 接口结构预检通过，Q/p 场景和 c4 分支敏感性已经完成，B1、B3、B4/B5、B6/B7、B8、B9/B10 均按各自角色分层审计。它们都没有建立 A-B 行级关系、没有把 Q1 分数转换成 B6/B7 的 `Q_score`，也没有启动正式 `L(N,D,Q,p)` 拟合。

索引上有两个需要保留的记录问题：`q2-interface-reaudit-20260925-r01` 已有运行目录但此前没有索引行；旧索引中的 `q2-p6-claim-boundaries-20250925-r01` 没有对应运行目录。`r02` 输出目录与部分 metrics 内部仍写着 `20250925-r01`，本报告按目录运行号登记并保留内部编号，不覆盖旧结果。

对齐后的统一状态是：可以继续报告分层基线、半合成条件敏感性、Q/p 结构预检和场景包络；不能报告已验证的 17 域质量映射、Q1 Q 与 B6/B7 `Q_score` 等价、A-B 质量—Loss 逐行关系或正式联合标度律。
""",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
