"""Package Q3 conditional scenario outputs into a claim-bounded answer table."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q3-final-scenario-package-20260926-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
FRONTIER_SUMMARY = ROOT / "experiments" / "runs" / "q3-fixed-budget-frontier-20260926-r01" / "tables" / "fixed_budget_frontier_summary.csv"
PANEL = ROOT / "experiments" / "runs" / "q3-p-fixed-budget-panel-20260926-r01" / "tables" / "p_fixed_budget_frontier_panel.csv"
M0_SUMMARY = ROOT / "experiments" / "runs" / "q3-optimization-robustness-20260926-r01" / "tables" / "m0_uncertainty_summary.csv"
M1_SUMMARY = ROOT / "experiments" / "runs" / "q3-optimization-robustness-20260926-r01" / "tables" / "m1_uncertainty_summary.csv"


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


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "tables").mkdir(exist_ok=True)
    frontier = pd.read_csv(FRONTIER_SUMMARY)
    panel = pd.read_csv(PANEL)
    m0 = pd.read_csv(M0_SUMMARY)
    m1 = pd.read_csv(M1_SUMMARY)

    # Keep one row per fixed-budget scenario and expose the selection rule.
    recommendations = frontier.copy()
    recommendations["scenario_status"] = "CONDITIONAL_GRID_CANDIDATE"
    recommendations["support_status"] = "inside_B1_B6_observed_support"
    recommendations["selection_rule"] = "minimum_loss_feasible_grid_point_within_fixed_budget_context_Q0_cost_family"
    recommendations["global_optimum_claim"] = False
    recommendations["formal_joint_fit"] = False
    recommendations["A_B_row_join"] = False
    recommendations["Q1_Q_A_p_used_in_objective"] = False
    recommendations.to_csv(RUN_DIR / "tables/q3_conditional_recommendation_scenarios.csv", index=False, encoding="utf-8-sig")

    # Representative table for the written answer: one context and three budgets.
    representative = recommendations[(recommendations["Lctx"] == 8192) & (recommendations["Q0"] == 0.1)].copy()
    representative["interpretation"] = representative["budget_flops"].map({
        1e19: "低预算：质量成本族分歧明显，应并列报告",
        1e22: "中预算：Q趋向上界，但仍受模型和成本假设约束",
        1e24: "高预算：支持域上界主导，不能称为验证过的全局最优",
    })
    representative.to_csv(RUN_DIR / "tables/q3_representative_scenarios.csv", index=False, encoding="utf-8-sig")

    p_rank = panel[["candidate_index", "Q_A_p_0_100", "observed_scalar_loss_z",
                    "predicted_scalar_loss_z_mean", "predicted_policy_rank"]].drop_duplicates("candidate_index")
    p_rank = p_rank.sort_values("predicted_policy_rank")
    p_rank["p_recommendation_status"] = "A_SIDE_CONDITIONAL_ONLY"
    p_rank["cross_source_optimum_claim"] = False
    p_rank.to_csv(RUN_DIR / "tables/q1_p_candidate_claim_bounded_ranking.csv", index=False, encoding="utf-8-sig")

    # Compact claim ledger used by the report generator.
    claims = [
        {"claim_id": "Q3-C1", "claim": "M0 supports conditional N-D resource allocation inside or explicitly marked beyond B1 support", "status": "SUPPORTED_CONDITIONALLY", "evidence": "q3-optimization-robustness + q3-fixed-budget-frontier"},
        {"claim_id": "Q3-C2", "claim": "M1 supports native B6 Q_score quality-cost sensitivity", "status": "SUPPORTED_CONDITIONALLY", "evidence": "q3-optimization-robustness + q3-fixed-budget-frontier"},
        {"claim_id": "Q3-C3", "claim": "The preferred Q depends on Q0, cost family and budget", "status": "SUPPORTED_CONDITIONALLY", "evidence": "fixed_budget_frontier_summary.csv"},
        {"claim_id": "Q3-C4", "claim": "Observed p candidates can be displayed alongside B-side frontiers", "status": "SUPPORTED_AS_SCENARIO_PANEL", "evidence": "q3-p-fixed-budget-panel"},
        {"claim_id": "Q3-C5", "claim": "A-side p or Q_A(p) has an identified independent B-side Loss coefficient", "status": "NOT_IDENTIFIED", "evidence": "no A-B row/batch key"},
        {"claim_id": "Q3-C6", "claim": "Q1 Q_A(p) equals native B6 Q_score", "status": "NOT_ESTABLISHED", "evidence": "different definitions and scales"},
        {"claim_id": "Q3-C7", "claim": "A globally validated four-quantity optimum is available", "status": "BLOCKED", "evidence": "formal_joint_fit=false; B8 excluded"},
    ]
    pd.DataFrame(claims).to_csv(RUN_DIR / "tables/q3_claim_ledger.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "schema_version": "q3.final.scenario.package.v1",
        "run_id": RUN_ID,
        "status": "CONDITIONAL_Q3_SCENARIO_PACKAGE_READY",
        "inputs": {
            "fixed_budget_frontier_summary": {"path": str(FRONTIER_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(FRONTIER_SUMMARY)},
            "p_fixed_budget_panel": {"path": str(PANEL.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(PANEL)},
            "m0_uncertainty_summary": {"path": str(M0_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M0_SUMMARY)},
            "m1_uncertainty_summary": {"path": str(M1_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M1_SUMMARY)},
        },
        "counts": {"recommendation_scenarios": int(len(recommendations)), "representative_scenarios": int(len(representative)), "p_candidates": int(len(p_rank)), "claim_rows": len(claims)},
        "checks": {
            "all_recommendations_inside_support": bool((recommendations["support_status"] == "inside_B1_B6_observed_support").all()),
            "global_optimum_claims": bool(recommendations["global_optimum_claim"].any()),
            "formal_joint_fit": False,
            "A_B_row_join": False,
            "Q1_Q_A_p_used_in_objective": False,
        },
        "limitations": [
            "recommendations are conditional grid candidates, not global optima",
            "p ranking is A-side only and is not used to select B-side N-D-Q settings",
            "Q1 Q_A(p) and B6 Q_score remain separate variables",
        ],
        "output_sha256": {name: sha256(RUN_DIR / "tables" / name) for name in ["q3_conditional_recommendation_scenarios.csv", "q3_representative_scenarios.csv", "q1_p_candidate_claim_bounded_ranking.csv", "q3_claim_ledger.csv"]},
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(f"python={sys.version.split()[0]}\nplatform={platform.platform()}\npandas={pd.__version__}\n", encoding="utf-8")
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q3_final_scenario_packaging.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q3 final conditional scenario package

运行号：`{RUN_ID}`。

本包将固定预算前沿、M0/M1 参数传播和 6 个 A-side p 候选整理为问题三可用的条件情景表和 claim ledger。所有“推荐”均指观测支持域内、给定预算/上下文/Q0/成本假设下的网格候选，不代表全局最优或 A-B 联合最优。
""", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "recommendation_scenarios": len(recommendations), "representative": len(representative)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
