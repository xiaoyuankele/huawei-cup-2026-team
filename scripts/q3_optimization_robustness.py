"""Propagate frozen Q2 fold parameters into the Q3 conditional optimizers.

This is an exploratory, read-only robustness run.  It does not refit either
model, create an A--B join, convert Q1 quality to B6 Q_score, or use B8.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q3-optimization-robustness-20260926-r01"
DEFAULT_OUT = ROOT / "experiments" / "runs" / RUN_ID
FOLD_SOURCE = ROOT / "experiments" / "runs" / "q2-elasticity-audit-20260925-r01" / "tables" / "parameter_fold_values.csv"
Q2_SOURCE = ROOT / "experiments" / "runs" / "q2-m0-m1-20260925-r01" / "metrics.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nondominated(rows: list[dict[str, object]], loss_key: str, cost_key: str) -> set[int]:
    """Return row indices not dominated by lower loss and lower cost."""
    keep: set[int] = set()
    for i, row_i in enumerate(rows):
        loss_i = float(row_i[loss_key])
        cost_i = float(row_i[cost_key])
        dominated = False
        for j, row_j in enumerate(rows):
            if i == j:
                continue
            loss_j = float(row_j[loss_key])
            cost_j = float(row_j[cost_key])
            if (loss_j <= loss_i and cost_j <= cost_i
                    and (loss_j < loss_i or cost_j < cost_i)):
                dominated = True
                break
        if not dominated:
            keep.add(i)
    return keep


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(frame: pd.DataFrame, keys: list[str], values: list[str]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for key_values, group in frame.groupby(keys, dropna=False, sort=True):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        record = dict(zip(keys, key_values))
        for value in values:
            series = pd.to_numeric(group[value], errors="coerce").dropna()
            record[f"{value}_min"] = float(series.min())
            record[f"{value}_p05"] = float(series.quantile(0.05))
            record[f"{value}_median"] = float(series.median())
            record[f"{value}_p95"] = float(series.quantile(0.95))
            record[f"{value}_max"] = float(series.max())
        records.append(record)
    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)

    nd = load_module("q3_nd_baseline_for_robustness", ROOT / "scripts" / "q3_nd_baseline.py")
    qc = load_module("q3_q_conditional_for_robustness", ROOT / "scripts" / "q3_q_conditional.py")
    fold_frame = pd.read_csv(FOLD_SOURCE)
    if set(fold_frame["model"].unique()) != {"M0", "M1"}:
        raise RuntimeError("parameter fold file must contain M0 and M1")
    support = nd.load_support()
    contexts = nd.load_context_values()
    q_bounds = qc.load_q_bounds()
    budgets = list(nd.BUDGETS)

    m0_rows: list[dict[str, object]] = []
    for _, fold in fold_frame[fold_frame["model"] == "M0"].iterrows():
        params = {key: float(fold[key]) for key in ("E", "A", "B", "alpha", "beta")}
        for lctx in contexts:
            for budget in budgets:
                relaxed_n, relaxed_d, relaxed_l = nd.relaxed_solution(budget, lctx, params)
                bounded = nd.bounded_solution(budget, lctx, params, support)
                m0_rows.append({
                    "fold": str(fold["fold"]), "budget_flops": budget, "Lctx": lctx,
                    "relaxed_N_B": relaxed_n, "relaxed_D_B": relaxed_d,
                    "relaxed_loss": relaxed_l,
                    "relaxed_within_B1_support": (
                        support["N_min_B"] <= relaxed_n <= support["N_max_B"]
                        and support["D_min_B"] <= relaxed_d <= support["D_max_B"]
                    ),
                    "bounded_N_B": bounded["n_b"], "bounded_D_B": bounded["d_b"],
                    "bounded_loss": bounded["loss"],
                    "bounded_cost_flops": nd.feasible_cost(float(bounded["n_b"]), float(bounded["d_b"]), lctx),
                    "budget_slack_flops": bounded["budget_residual_flops"],
                    "bounded_support_status": bounded["support_status"],
                    "successful_starts": bounded["successful_starts"],
                })

    m1_rows: list[dict[str, object]] = []
    for _, fold in fold_frame[fold_frame["model"] == "M1"].iterrows():
        params = {key: float(fold[key]) for key in ("E", "A", "B", "G", "alpha", "beta")}
        for kind in qc.COSTS:
            for lctx in contexts:
                for budget in budgets:
                    solved = qc.solve_one(budget, lctx, kind, params, support, q_bounds)
                    solved["fold"] = str(fold["fold"])
                    m1_rows.append(solved)

    write_csv(out / "tables" / "m0_fold_scenarios.csv", m0_rows)
    write_csv(out / "tables" / "m1_fold_scenarios.csv", m1_rows)

    m0_frame = pd.DataFrame(m0_rows)
    m1_frame = pd.DataFrame(m1_rows)
    m0_summary = summarize(m0_frame, ["budget_flops", "Lctx"], ["bounded_N_B", "bounded_D_B", "bounded_loss"])
    m1_summary = summarize(
        m1_frame, ["cost_family", "budget_flops", "Lctx"],
        ["N_B", "D_B", "Q", "loss", "quality_cost_flops", "base_train_attn_cost_flops"],
    )
    m0_summary.to_csv(out / "tables" / "m0_uncertainty_summary.csv", index=False, encoding="utf-8-sig")
    m1_summary.to_csv(out / "tables" / "m1_uncertainty_summary.csv", index=False, encoding="utf-8-sig")

    # Discrete candidate frontiers across budgets for each fold and context.
    m0_front_rows: list[dict[str, object]] = []
    for (fold, lctx), group in m0_frame.groupby(["fold", "Lctx"], sort=True):
        records = group.to_dict("records")
        keep = nondominated(records, "bounded_loss", "bounded_cost_flops")
        for i, row in enumerate(records):
            m0_front_rows.append({"fold": fold, "Lctx": lctx, "budget_flops": row["budget_flops"],
                                  "bounded_loss": row["bounded_loss"], "bounded_cost_flops": row["bounded_cost_flops"],
                                  "pareto_flag": i in keep})
    m1_front_rows: list[dict[str, object]] = []
    for (fold, kind, lctx), group in m1_frame.groupby(["fold", "cost_family", "Lctx"], sort=True):
        records = group.to_dict("records")
        keep = nondominated(records, "loss", "total_cost_flops")
        for i, row in enumerate(records):
            m1_front_rows.append({"fold": fold, "cost_family": kind, "Lctx": lctx,
                                  "budget_flops": row["budget_flops"], "loss": row["loss"],
                                  "total_cost_flops": row["total_cost_flops"], "Q": row["Q"],
                                  "pareto_flag": i in keep})
    write_csv(out / "tables" / "m0_discrete_frontier.csv", m0_front_rows)
    write_csv(out / "tables" / "m1_discrete_frontier.csv", m1_front_rows)

    metrics = {
        "schema_version": "q3.optimization.robustness.v1",
        "run_id": RUN_ID,
        "status": "EXPLORATORY_Q3_PARAMETER_UNCERTAINTY_PROPAGATION",
        "inputs": {
            "parameter_fold_values": {"path": str(FOLD_SOURCE.relative_to(ROOT)), "sha256": sha256(FOLD_SOURCE), "rows": int(len(fold_frame))},
            "q2_model_metrics": {"path": str(Q2_SOURCE.relative_to(ROOT)), "sha256": sha256(Q2_SOURCE)},
        },
        "roles": {
            "M0": "B1 fold parameters propagated into Q3 N-D optimization",
            "M1": "B6 fold parameters propagated into Q3 native-Q_score optimization",
            "Q1_Q_A_p": "not used in M0/M1 optimization; no A-B row join",
            "B8": "excluded",
        },
        "support": {**support, **q_bounds},
        "contexts": contexts,
        "budgets_flops": budgets,
        "fold_counts": {"M0": int((fold_frame["model"] == "M0").sum()), "M1": int((fold_frame["model"] == "M1").sum())},
        "scenario_counts": {"M0": len(m0_rows), "M1": len(m1_rows)},
        "pareto_definition": "within each fold and context (and cost family for M1), lower loss and lower realized cost dominate",
        "checks": {
            "all_m0_finite": bool(np.isfinite(m0_frame.select_dtypes(include=[np.number]).to_numpy()).all()),
            "all_m1_finite": bool(np.isfinite(m1_frame.select_dtypes(include=[np.number]).to_numpy()).all()),
            "m1_budget_violation_max_relative": float(np.max(np.maximum(0.0, -m1_frame["budget_slack_flops"].to_numpy()) / m1_frame["budget_flops"].to_numpy())),
            "formal_joint_fit": False,
            "a_to_b_row_join": False,
        },
        "limitations": [
            "folds are propagated from frozen exploratory fits; no refit is performed here",
            "M0/M1 folds quantify parameter sensitivity, not independent external validation",
            "M1 Q is native B6 Q_score and is not Q1-derived Q_A(p)",
            "discrete frontier is a scenario frontier, not a globally validated optimum",
            "B1/B6 support bounds remain active; any relaxed solution outside support is extrapolation",
        ],
        "output_sha256": {
            name: sha256(out / "tables" / name)
            for name in ["m0_fold_scenarios.csv", "m1_fold_scenarios.csv", "m0_uncertainty_summary.csv", "m1_uncertainty_summary.csv", "m0_discrete_frontier.csv", "m1_discrete_frontier.csv"]
        },
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (out / "environment.txt").write_text(
        f"python={sys.version.split()[0]}\nplatform={platform.platform()}\nnumpy={np.__version__}\npandas={pd.__version__}\n",
        encoding="utf-8",
    )
    (out / "command.txt").write_text("python -X utf8 scripts/q3_optimization_robustness.py\n", encoding="utf-8")
    readme = f"""# Q3 optimization robustness run

运行号：`{RUN_ID}`。

本运行将问题二冻结的 M0/M1 折叠参数逐折传播到问题三优化器，输出支持域内的 N-D、N-D-Q 情景区间，并在固定折叠、上下文长度和质量成本族内标记离散 Pareto 情景。

本运行不重新拟合，不使用 B8，不建立 A-B 行级连接，也不把 Q1 的 `Q_A(p)` 转为 B6 的 `Q_score`。因此输出是参数不确定性和成本假设下的条件稳健性证据，不是正式联合定律或全局最优证明。
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "m0_rows": len(m0_rows), "m1_rows": len(m1_rows), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
