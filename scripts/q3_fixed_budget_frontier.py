"""Fixed-budget N-D-Q grid frontiers for the Q3 conditional M1 model.

The grid makes the loss--cost trade-off visible inside a fixed budget.  It is
an exploratory scenario analysis using the full frozen B6 M1 parameters; it
does not fit a new model or create an A--B bridge.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q3-fixed-budget-frontier-20260926-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
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
    quality_cost,
    base_cost,
    total_cost,
    loss,
    sha256,
)

Q0_VALUES = [0.1, 0.3, 0.5]
N_GRID_SIZE = 15
D_GRID_SIZE = 15
Q_GRID_SIZE = 19


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"empty output: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def frontier(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return a discrete lower-loss/lower-cost frontier in cost order."""
    ordered = sorted(candidates, key=lambda row: (float(row["total_cost_flops"]), float(row["loss"])))
    output: list[dict[str, object]] = []
    best_loss = float("inf")
    for row in ordered:
        value = float(row["loss"])
        if value < best_loss - 1e-12:
            output.append(row)
            best_loss = value
    return output


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "tables").mkdir(exist_ok=True)
    params = load_m1()
    support = load_support()
    q_bounds = load_q_bounds()
    contexts = load_context_values()
    n_grid = np.geomspace(support["N_min_B"], support["N_max_B"], N_GRID_SIZE)
    d_grid = np.geomspace(support["D_min_B"], support["D_max_B"], D_GRID_SIZE)
    q_grid = np.linspace(q_bounds["Q_min"], q_bounds["Q_max"], Q_GRID_SIZE)

    frontier_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    scenario_count = 0
    for q0, kind, lctx, budget in product(Q0_VALUES, COSTS, contexts, BUDGETS):
        candidates: list[dict[str, object]] = []
        for n_b, d_b, q in product(n_grid, d_grid, q_grid):
            n_b, d_b, q = float(n_b), float(d_b), float(q)
            if q < q0:
                continue
            realized = total_cost(n_b, d_b, q, lctx, kind, q0)
            if realized > budget * (1.0 + 1e-12):
                continue
            candidates.append({
                "Q0": q0, "cost_family": kind, "Lctx": lctx, "budget_flops": budget,
                "N_B": n_b, "D_B": d_b, "Q": q,
                "loss": loss(n_b, d_b, q, params),
                "total_cost_flops": realized,
                "base_train_attn_cost_flops": base_cost(n_b, d_b, lctx),
                "quality_cost_flops": quality_cost(d_b, q, kind, q0),
            })
        if not candidates:
            raise RuntimeError(f"no feasible grid point for {q0=} {kind=} {lctx=} {budget=}")
        points = frontier(candidates)
        for rank, row in enumerate(points, start=1):
            frontier_rows.append({**row, "frontier_rank": rank, "frontier_count": len(points)})
        best = min(candidates, key=lambda row: float(row["loss"]))
        summary_rows.append({
            "Q0": q0, "cost_family": kind, "Lctx": lctx, "budget_flops": budget,
            "feasible_grid_points": len(candidates), "frontier_points": len(points),
            "best_N_B": best["N_B"], "best_D_B": best["D_B"], "best_Q": best["Q"],
            "best_loss": best["loss"], "best_total_cost_flops": best["total_cost_flops"],
            "best_quality_cost_flops": best["quality_cost_flops"],
            "best_base_train_attn_cost_flops": best["base_train_attn_cost_flops"],
            "Q_on_lower_bound": abs(float(best["Q"]) - q0) < 1e-12,
            "Q_on_upper_bound": abs(float(best["Q"]) - q_bounds["Q_max"]) < 1e-12,
        })
        scenario_count += 1

    frontier_table = RUN_DIR / "tables" / "fixed_budget_frontier_points.csv"
    summary_table = RUN_DIR / "tables" / "fixed_budget_frontier_summary.csv"
    write_csv(frontier_table, frontier_rows)
    write_csv(summary_table, summary_rows)
    metrics = {
        "schema_version": "q3.fixed_budget.frontier.v1",
        "run_id": RUN_ID,
        "status": "EXPLORATORY_Q3_FIXED_BUDGET_GRID_FRONTIER",
        "model": "frozen B6 M1 native Q_score conditional model",
        "grid": {"N_points": N_GRID_SIZE, "D_points": D_GRID_SIZE, "Q_points": Q_GRID_SIZE,
                 "N_range_B": [support["N_min_B"], support["N_max_B"]],
                 "D_range_B": [support["D_min_B"], support["D_max_B"]],
                 "Q_range": [q_bounds["Q_min"], q_bounds["Q_max"]]},
        "Q0_values": Q0_VALUES,
        "cost_families": COSTS,
        "budgets_flops": BUDGETS,
        "Lctx_values_from_metadata": contexts,
        "scenario_count": scenario_count,
        "frontier_definition": "within fixed Q0, cost family, Lctx and budget, sort feasible grid by realized cost and keep points with strictly improving loss",
        "inputs": {
            "m1_metrics": {"path": str(M1_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M1_SOURCE)},
            "b1_support": {"path": str(B1_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(B1_SOURCE)},
            "b6_q_range": {"path": str(B6_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(B6_SOURCE)},
            "c7_context": {"path": str(C7_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(C7_SOURCE)},
        },
        "checks": {
            "all_frontier_finite": bool(np.isfinite(pd.DataFrame(frontier_rows).select_dtypes(include=[np.number]).to_numpy()).all()),
            "all_summary_finite": bool(np.isfinite(pd.DataFrame(summary_rows).select_dtypes(include=[np.number]).to_numpy()).all()),
            "a_to_b_row_join": False,
            "formal_joint_fit": False,
            "Q1_Q_A_p_used": False,
            "B8_used": False,
        },
        "limitations": [
            "grid frontier is a discrete conditional scenario, not a continuous global optimum",
            "Q0 values are cost-reference assumptions and M1 is not refit at each Q0",
            "Q is native B6 Q_score, not Q1-derived Q_A(p)",
            "all N, D and Q values are restricted to observed B1/B6 support",
        ],
        "output_sha256": {"fixed_budget_frontier_points.csv": sha256(frontier_table),
                          "fixed_budget_frontier_summary.csv": sha256(summary_table)},
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "git_commit.txt").write_text(subprocess_commit() + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(
        f"python={sys.version.split()[0]}\nplatform={platform.platform()}\nnumpy={np.__version__}\npandas={pd.__version__}\n",
        encoding="utf-8",
    )
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q3_fixed_budget_frontier.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q3 fixed-budget frontier

运行号：`{RUN_ID}`。

本运行在固定预算、上下文长度、Q0 和质量成本族内，对 B6 M1 的 N-D-Q 候选网格进行筛选，输出 Loss—实际成本的离散前沿。N、D 和 Q 均限制在观测支持范围；Q 为 B6 原生 `Q_score`。

该运行不重新拟合、不使用 B8、不使用 Q1 `Q_A(p)`，也不建立 A-B 行级桥接。结果用于比较固定预算内的质量—规模权衡，不是正式联合标度律。
""",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": RUN_ID, "scenario_count": scenario_count, "frontier_rows": len(frontier_rows)}, ensure_ascii=False))


def subprocess_commit() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
