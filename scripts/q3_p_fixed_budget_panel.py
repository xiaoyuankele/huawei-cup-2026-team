"""Attach observed A-side p candidates to the fixed-budget Q3 frontier.

This is a declared scenario panel, not an A--B row-level join or a joint
objective.  A-side scores and Q1-derived Q_A(p) remain separate from the
native B6 Q_score used by the Q3 conditional model.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q3-p-fixed-budget-panel-20260926-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
P_SUMMARY = ROOT / "experiments" / "runs" / "q3-p-conditional-20260925-r01" / "tables" / "p_candidate_summary.csv"
Q1_WIDE = ROOT / "experiments" / "runs" / "q1-domain-transfer-matrix-20260925-r01" / "tables" / "A4_A15_quality_transfer_soft_wide.csv"
FRONTIER_SUMMARY = ROOT / "experiments" / "runs" / "q3-fixed-budget-frontier-20260926-r01" / "tables" / "fixed_budget_frontier_summary.csv"


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
    p_summary = pd.read_csv(P_SUMMARY)
    frontier = pd.read_csv(FRONTIER_SUMMARY)
    wide = pd.read_csv(Q1_WIDE)
    candidates = p_summary["candidate_index"].astype(int).tolist()
    q1 = wide[(wide["dataset"] == "A4_A5_train_1m") & wide["index"].isin(candidates)].copy()
    if len(q1) != len(candidates):
        raise RuntimeError(f"expected {len(candidates)} A4/A5 candidate rows, found {len(q1)}")
    q1 = q1[["index", "quality_score_soft_proxy_0_100", "quality_score_soft_low_0_100",
             "quality_score_soft_high_0_100", "official_mapped_mass", "quality_transfer_status"]]
    q1 = q1.rename(columns={"index": "candidate_index", "quality_score_soft_proxy_0_100": "Q_A_p_0_100",
                            "quality_score_soft_low_0_100": "Q_A_p_low_0_100",
                            "quality_score_soft_high_0_100": "Q_A_p_high_0_100"})
    candidates_frame = p_summary.merge(q1, on="candidate_index", validate="one_to_one")
    candidates_frame["candidate_index"] = candidates_frame["candidate_index"].astype(int)
    candidates_frame["Q_A_p_is_Q_score"] = False
    panel = candidates_frame.assign(_key=1).merge(frontier.assign(_key=1), on="_key", how="inner").drop(columns="_key")
    panel["p_effect_in_ndq_objective"] = False
    panel["joint_A_B_loss_claim"] = False
    panel["A_B_row_join"] = False
    panel["Q1_Q_A_p_to_B6_Q_score_conversion"] = False
    panel["panel_role"] = "A-side discrete p/Q_A(p) label alongside B-side fixed-budget N-D-Q_score frontier"
    panel.to_csv(RUN_DIR / "tables" / "p_fixed_budget_frontier_panel.csv", index=False, encoding="utf-8-sig")
    metrics = {
        "schema_version": "q3.p.fixed_budget.panel.v1",
        "run_id": RUN_ID,
        "status": "EXPLORATORY_Q3_P_TO_FIXED_BUDGET_PANEL",
        "candidate_count": len(candidates),
        "frontier_scenario_count": int(len(frontier)),
        "panel_rows": int(len(panel)),
        "candidate_indices": candidates,
        "inputs": {
            "p_candidate_summary": {"path": str(P_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(P_SUMMARY)},
            "q1_quality_transfer_wide": {"path": str(Q1_WIDE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(Q1_WIDE)},
            "fixed_budget_frontier_summary": {"path": str(FRONTIER_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(FRONTIER_SUMMARY)},
        },
        "checks": {
            "candidate_rows_complete": len(q1) == len(candidates),
            "panel_rows_expected": int(len(panel)) == len(candidates) * len(frontier),
            "p_effect_in_ndq_objective": False,
            "joint_A_B_loss_claim": False,
            "A_B_row_join": False,
            "Q1_Q_A_p_to_B6_Q_score_conversion": False,
            "formal_joint_fit": False,
        },
        "limitations": [
            "p candidates and B-side frontiers are paired as scenarios, not matched samples",
            "Q_A(p) is a Q1-derived 0-100 proxy with inferred domain mappings",
            "B-side Q is native B6 Q_score; the two quality quantities remain separate",
            "panel cannot identify a p coefficient or a cross-source joint optimum",
        ],
        "output_sha256": {"p_fixed_budget_frontier_panel.csv": sha256(RUN_DIR / "tables" / "p_fixed_budget_frontier_panel.csv")},
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(f"python={sys.version.split()[0]}\nplatform={platform.platform()}\npandas={pd.__version__}\n", encoding="utf-8")
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q3_p_fixed_budget_panel.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q3 p fixed-budget frontier panel

运行号：`{RUN_ID}`。

本运行把问题一中实际观测过的 {len(candidates)} 个配比候选与固定预算 Q3 `N-D-Q_score` 前沿做笛卡尔情景拼接，共 {len(panel)} 行。A 侧 `Q_A(p)` 和 Loss 与 B 侧原生 `Q_score`、N-D 配置并列保留，不进入同一个损失函数。

这是一张条件策略面板，不是样本级 A-B 连接，也不识别跨来源的 p 或质量系数。
""", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "panel_rows": len(panel)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
