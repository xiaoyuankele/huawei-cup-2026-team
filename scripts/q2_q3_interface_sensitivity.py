"""Q2 -> Q3 interface sensitivity for M2 quality scenarios.

This is a conditional interface experiment.  It keeps the observed A-side
composition rows fixed, computes partial/renormalized/interval Q_A values,
and applies one explicitly named hypothetical affine calibration to the native
B6 Q_score interval before solving the existing M1 Q3 optimizer at fixed Q.

The Q1 0--100 -> B6 0.1--1.0 conversion is not established by data.  Every
converted result is therefore tagged as a scenario-only result.  No A--B row
join, B8 record, or new fit is introduced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q2-q3-interface-sensitivity-20260926-r01"
RUN_DIR = ROOT / "experiments/runs" / RUN_ID
M2_TABLE = ROOT / "experiments/runs/q2-m2-sensitivity-20250925-r01/tables/recipe_q_scenarios.csv"
M2_METRICS = ROOT / "experiments/runs/q2-m2-sensitivity-20250925-r01/metrics.json"
P_SUMMARY = ROOT / "experiments/runs/q3-p-conditional-20260925-r01/tables/p_candidate_summary.csv"
ND_TABLE = ROOT / "experiments/runs/q3-nd-baseline-20260925-r01/tables/q3_nd_baseline_scenarios.csv"
Q_TABLE = ROOT / "experiments/runs/q3-q-conditional-20260925-r01/tables/q3_q_conditional_scenarios.csv"
M1_METRICS = ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_q3_modules():
    """Import the frozen Q3 solver and its constants without copying them."""
    import importlib.util

    path = ROOT / "scripts/q3_q_conditional.py"
    spec = importlib.util.spec_from_file_location("q3_q_conditional_interface", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def calibrate_q1_to_b6(q_a: float, q_low: float, q_high: float) -> float:
    """Explicit scenario map from Q1 candidate scores to B6 support."""
    if not q_high > q_low:
        raise ValueError("q1 calibration range must have positive width")
    normalized = (float(q_a) - q_low) / (q_high - q_low)
    return float(0.1 + 0.9 * np.clip(normalized, 0.0, 1.0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RUN_DIR)
    args = parser.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)

    qc = load_q3_modules()
    m2 = pd.read_csv(M2_TABLE)
    candidates = pd.read_csv(P_SUMMARY)["candidate_index"].astype(int).tolist()
    m2 = m2[(m2["recipe"] == "A4_A5_train_1m") & m2["index"].astype(int).isin(candidates)].copy()
    if len(m2) != len(set(candidates)):
        raise RuntimeError("M2 table does not contain one A4/A5 row for every p candidate")
    m2["index"] = m2["index"].astype(int)

    # These are the three Q1-side constructions requested for the interface:
    # mapped mass only, mapped mass renormalized to one, and the semantic
    # low/mid/high interval.  They remain in the Q1 candidate 0--100 scale.
    m2["q_partial_renorm"] = np.where(
        m2["mapped_mass"] > 0,
        m2["q_partial_raw"] / m2["mapped_mass"],
        np.nan,
    ).clip(0.0, 100.0)
    q_columns = {
        "M2_partial_raw": "q_partial_raw",
        "M2_partial_renorm": "q_partial_renorm",
        "M2_interval_low": "q_scenario_low",
        "M2_interval_mid": "q_scenario_mid",
        "M2_interval_high": "q_scenario_high",
    }
    m2_rows = []
    for _, row in m2.iterrows():
        for scenario, column in q_columns.items():
            q_a = float(row[column])
            m2_rows.append({
                "candidate_index": int(row["index"]),
                "mapping_scenario": scenario,
                "Q_A_0_100": q_a,
                "mapped_mass": float(row["mapped_mass"]),
                "unmapped_mass": float(row["unmapped_mass"]),
            })
    m2_scenarios = pd.DataFrame(m2_rows)

    m2_meta = json.loads(M2_METRICS.read_text(encoding="utf-8"))
    calibration = m2_meta["q1_candidate_range_used_only_for_sensitivity"]
    q1_low = float(calibration["low"])
    q1_high = float(calibration["high"])
    m2_scenarios["Q_B_hypothetical_0_1"] = m2_scenarios["Q_A_0_100"].map(
        lambda value: calibrate_q1_to_b6(value, q1_low, q1_high)
    )
    m2_scenarios["q_scale_status"] = "HYPOTHETICAL_Q1_0_100_TO_B6_0.1_1.0"

    support = qc.load_support()
    contexts = qc.load_context_values()
    budgets = list(qc.BUDGETS)
    cost_families = list(qc.COSTS)
    q_bounds = {"Q_min": float(m2_scenarios["Q_B_hypothetical_0_1"].min()),
                "Q_max": float(m2_scenarios["Q_B_hypothetical_0_1"].max())}
    # Keep every candidate quality level fixed while optimizing N and D.  This
    # isolates the interface effect and avoids re-optimizing Q as if it were an
    # observed A-side measurement.
    m1_params = json.loads(M1_METRICS.read_text(encoding="utf-8"))["M1"]["fit_B6"]
    params = {name: float(value) for name, value in zip(("E", "A", "B", "G", "alpha", "beta"), m1_params)}

    rows = []
    for _, scenario in m2_scenarios.iterrows():
        q_fixed = float(scenario["Q_B_hypothetical_0_1"])
        for cost_family in cost_families:
            for lctx in contexts:
                for budget in budgets:
                    solved = qc.solve_one(
                        budget, lctx, cost_family, params, support,
                        {"Q_min": q_fixed, "Q_max": q_fixed},
                    )
                    rows.append({
                        "candidate_index": int(scenario["candidate_index"]),
                        "mapping_scenario": str(scenario["mapping_scenario"]),
                        "Q_A_0_100": float(scenario["Q_A_0_100"]),
                        "Q_B_hypothetical_0_1": q_fixed,
                        "mapped_mass": float(scenario["mapped_mass"]),
                        "unmapped_mass": float(scenario["unmapped_mass"]),
                        "cost_family": cost_family,
                        "Lctx": int(lctx),
                        "budget_flops": float(budget),
                        "N_B": float(solved["N_B"]),
                        "D_B": float(solved["D_B"]),
                        "Q_star": float(solved["Q"]),
                        "loss": float(solved["loss"]),
                        "total_cost_flops": float(solved["total_cost_flops"]),
                        "quality_cost_flops": float(solved["quality_cost_flops"]),
                        "quality_cost_share": float(solved["quality_cost_flops"] / solved["total_cost_flops"]),
                        "budget_slack_flops": float(solved["budget_slack_flops"]),
                        "budget_active": bool(abs(float(solved["budget_slack_flops"])) <= max(1.0, budget * 1e-8)),
                        "Q_at_fixed_bound": bool(solved["Q_at_bound"]),
                        "support_status": str(solved["support_status"]),
                        "q_scale_status": "HYPOTHETICAL_Q1_0_100_TO_B6_0.1_1.0",
                    })
    result = pd.DataFrame(rows)
    result.to_csv(out / "tables/m2_q3_fixed_q_scenarios.csv", index=False, encoding="utf-8-sig")
    summary = (result.groupby(["mapping_scenario", "cost_family", "Lctx", "budget_flops"], as_index=False)
               .agg(candidate_count=("candidate_index", "size"),
                    Q_A_min_0_100=("Q_A_0_100", "min"),
                    Q_A_median_0_100=("Q_A_0_100", "median"),
                    Q_A_max_0_100=("Q_A_0_100", "max"),
                    Q_B_min=("Q_B_hypothetical_0_1", "min"),
                    Q_B_median=("Q_B_hypothetical_0_1", "median"),
                    Q_B_max=("Q_B_hypothetical_0_1", "max"),
                    N_B_min=("N_B", "min"), N_B_median=("N_B", "median"), N_B_max=("N_B", "max"),
                    D_B_min=("D_B", "min"), D_B_median=("D_B", "median"), D_B_max=("D_B", "max"),
                    loss_min=("loss", "min"), loss_median=("loss", "median"), loss_max=("loss", "max"),
                    quality_cost_share_min=("quality_cost_share", "min"),
                    quality_cost_share_median=("quality_cost_share", "median"),
                    quality_cost_share_max=("quality_cost_share", "max"),
                    budget_active_rate=("budget_active", "mean")))
    summary.to_csv(out / "tables/m2_q3_interface_summary.csv", index=False, encoding="utf-8-sig")

    references = {
        "m0_nd_reference": pd.read_csv(ND_TABLE).to_dict("records"),
        "m1_native_q_reference": pd.read_csv(Q_TABLE).to_dict("records"),
    }
    (out / "tables/reference_m0_m1_q3.json").write_text(
        json.dumps(references, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    metrics = {
        "schema_version": "q2.q3.interface.sensitivity.v1",
        "run_id": RUN_ID,
        "status": "EXPLORATORY_INTERFACE_SENSITIVITY_SCENARIO_ONLY",
        "candidate_count": int(len(candidates)),
        "mapping_scenario_count": len(q_columns),
        "q3_row_count": int(len(result)),
        "inputs": {
            "m2_recipe_scenarios": {"path": str(M2_TABLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M2_TABLE)},
            "m2_metrics": {"path": str(M2_METRICS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M2_METRICS)},
            "p_candidate_summary": {"path": str(P_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(P_SUMMARY)},
            "m1_metrics": {"path": str(M1_METRICS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(M1_METRICS)},
            "q3_nd_reference": {"path": str(ND_TABLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(ND_TABLE)},
            "q3_q_reference": {"path": str(Q_TABLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(Q_TABLE)},
        },
        "mapping_scenarios": {
            name: {"source_column": column, "scale": "Q1 candidate 0-100", "role": "M2 conditional"}
            for name, column in q_columns.items()
        },
        "hypothetical_calibration": {
            "formula": "Q_B=0.1+0.9*clip((Q_A-q1_low)/(q1_high-q1_low),0,1)",
            "q1_low": q1_low, "q1_high": q1_high,
            "target_range": [0.1, 1.0],
            "status": "UNVERIFIED_SCENARIO_ONLY",
        },
        "checks": {
            "input_candidate_rows": int(len(m2)),
            "all_q_a_finite": bool(np.isfinite(m2_scenarios["Q_A_0_100"]).all()),
            "all_q_b_finite": bool(np.isfinite(m2_scenarios["Q_B_hypothetical_0_1"]).all()),
            "q_b_inside_b6_support": bool(m2_scenarios["Q_B_hypothetical_0_1"].between(0.1, 1.0).all()),
            "all_q3_finite": bool(np.isfinite(result.select_dtypes(include=[np.number]).to_numpy()).all()),
            "budget_violation_max_relative": float(np.max(np.maximum(0.0, -result["budget_slack_flops"].to_numpy()) / result["budget_flops"].to_numpy())),
            "a_b_row_join": False,
            "formal_m3_fit": False,
            "b8_used": False,
        },
        "interpretation": [
            "M2 values are Q1-side candidate-score scenarios; the affine conversion to B6 Q_score is hypothetical.",
            "Fixed-Q M1 solutions show how a proposed interface value would change N-D allocation and quality-cost share.",
            "These rows do not establish Q1/B6 scale equivalence, G_bridge, or a joint optimum over p.",
            "M0 and native-M1 Q3 references are preserved separately and are not averaged with M2 rows.",
        ],
        "output_sha256": {
            "m2_q3_fixed_q_scenarios.csv": sha256(out / "tables/m2_q3_fixed_q_scenarios.csv"),
            "m2_q3_interface_summary.csv": sha256(out / "tables/m2_q3_interface_summary.csv"),
        },
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (out / "environment.txt").write_text(
        f"python={sys.version.split()[0]}\nplatform={platform.platform()}\nnumpy={np.__version__}\npandas={pd.__version__}\n",
        encoding="utf-8",
    )
    (out / "command.txt").write_text("python -X utf8 scripts/q2_q3_interface_sensitivity.py\n", encoding="utf-8")
    (out / "README.md").write_text(
        f"""# Q2-Q3 interface sensitivity\n\n运行号：`{RUN_ID}`。\n\n本运行将 A4/A5 中已观测的 6 个配比候选接入 M2 的五种条件构造：部分映射、部分映射重归一化，以及低/中/高区间赋值。所有值先保留在 Q1 候选 `0-100` 尺度，再用显式的候选范围仿射变换映射到 B6 `0.1-1.0`，并把该变换标记为未经验证的情景假设。\n\n对每个固定的候选质量值，调用冻结的 M1 Q3 求解器比较 `N*`、`D*`、Loss、质量成本占比和预算活跃率。M0 N-D 基线和原生 B6 M1 Q3 结果作为独立参考保存，不参与参数平均或联合拟合。\n\n本运行不建立 A-B 行级连接，不使用 B8，不拟合 M3，也不把情景结果写成 Q1 与 B6 质量分数等价。\n""",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": RUN_ID, "status": metrics["status"], "rows": len(result), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
