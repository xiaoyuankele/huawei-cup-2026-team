"""Q3 quality-cost robustness sweep around the conditional Q experiment."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from q3_q_conditional import (  # noqa: E402
    BUDGETS,
    COSTS,
    M1_SOURCE,
    B1_SOURCE,
    B6_SOURCE,
    C7_SOURCE,
    load_context_values,
    load_m1,
    load_q_bounds,
    load_support,
    sha256,
    solve_one,
)


RUN_ID = "q3-q-robustness-20260925-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
Q0_VALUES = [0.1, 0.3, 0.5]


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "tables").mkdir(exist_ok=True)
    p = load_m1()
    support = load_support()
    q_bounds = load_q_bounds()
    contexts = load_context_values()
    rows = []
    for q0 in Q0_VALUES:
        bounded_q = {**q_bounds, "Q_min": max(float(q_bounds["Q_min"]), q0)}
        for kind in COSTS:
            for lctx in contexts:
                for budget in BUDGETS:
                    rows.append(solve_one(budget, lctx, kind, p, support, bounded_q, q0=q0))

    table = RUN_DIR / "tables" / "q3_q_robustness_scenarios.csv"
    with table.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    metrics = {
        "run_id": RUN_ID,
        "status": "EXPLORATORY_Q3_Q_ROBUSTNESS",
        "parent_experiment": "q3-q-conditional-20260925-r01",
        "m1_parameters": p,
        "Q0_values": Q0_VALUES,
        "cost_families": COSTS,
        "budgets_flops": BUDGETS,
        "Lctx_values_from_metadata": contexts,
        "scenario_count": len(rows),
        "inputs": {
            "m1_metrics": {"path": str(M1_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M1_SOURCE)},
            "b1_support": {"path": str(B1_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(B1_SOURCE)},
            "b6_q_range": {"path": str(B6_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(B6_SOURCE)},
            "c7_context": {"path": str(C7_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(C7_SOURCE)},
        },
        "output_sha256": {"q3_q_robustness_scenarios.csv": sha256(table)},
        "limitations": [
            "This is a parameter-sensitivity sweep around the B6/B7 semi-synthetic M1 conditional model.",
            "Q0 values are scenario assumptions; M1 is not refit at each Q0.",
            "The B6 Q score is not promoted to the Q1 A-side quality score.",
            "p remains fixed and no A-B row-level bridge is used.",
        ],
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(
        f"python={sys.version.split()[0]}\nplatform={platform.platform()}\npandas={pd.__version__}\n",
        encoding="utf-8",
    )
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q3_q_robustness.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q3 Q-cost robustness sweep

运行号：`{RUN_ID}`。本运行以 `q3-q-conditional-20260925-r01` 为父实验，固定 B6 M1 参数，扫描 `Q0={Q0_VALUES}`、附录 B 三种质量成本、C7 五种上下文长度和三档预算，共 135 个情景。

每个情景的 N、D、Q 都限制在 B1/B6 观测支持范围，使用六个确定性起点的显式约束 SLSQP。该运行用于判断前一轮“Q 被推到上界”的结论是否依赖 Q0 或成本函数；它不重新拟合 M1，不构造 A–B 逐行桥接，也不产生正式联合模型。

完整结果见 `tables/q3_q_robustness_scenarios.csv`。
""",
        encoding="utf-8",
    )
    print(table)


if __name__ == "__main__":
    main()
