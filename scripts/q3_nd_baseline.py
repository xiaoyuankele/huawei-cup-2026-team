"""Q3 exploratory baseline: optimize N and D with Q and p fixed.

This script deliberately uses only the exploratory B1 M0 fit. It does not
read or modify raw A data, B6 quality scores, or B8. N and D are expressed in
billion parameters/tokens, matching the fitted B1 coefficients. FLOPs are
converted with 1e18 when using those units.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q3-nd-baseline-20260925-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
METRICS_SOURCE = ROOT / "experiments" / "runs" / "q2-m0-m1-20260925-r01" / "metrics.json"
C7_SOURCE = ROOT / "data" / "origin" / "real_attachments" / "C_efficiency_evolution" / "model_architecture_metadata.csv"
B1_SOURCE = ROOT / "data" / "origin" / "real_attachments" / "B_scaling_laws" / "pythia_training_log_existing.csv"
ETA = 2e-4
FLOPS_PER_BILLION_PAIR = 1e18
BUDGETS = [1e19, 1e22, 1e24]


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
            capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_m0() -> dict[str, float]:
    payload = json.loads(METRICS_SOURCE.read_text(encoding="utf-8"))
    values = payload["M0"]["fit_full_B1"]
    return {name: float(value) for name, value in zip(("E", "A", "B", "alpha", "beta"), values)}


def load_support() -> dict[str, float]:
    frame = pd.read_csv(B1_SOURCE)
    return {
        "N_min_B": float(frame["N_params_B"].min()),
        "N_max_B": float(frame["N_params_B"].max()),
        "D_min_B": float(frame["D_tokens_B"].min()),
        "D_max_B": float(frame["D_tokens_B"].max()),
        "B1_rows": int(len(frame)),
    }


def load_context_values() -> list[int]:
    frame = pd.read_csv(C7_SOURCE)
    values = sorted({int(v) for v in frame["max_position_embeddings"].dropna()})
    if not values:
        raise ValueError("No context values found in C7 architecture metadata")
    return values


def loss(n_b: float, d_b: float, p: dict[str, float]) -> float:
    return p["E"] + p["A"] * n_b ** (-p["alpha"]) + p["B"] * d_b ** (-p["beta"])


def budget_product(c_flops: float, lctx: int) -> float:
    return c_flops / (FLOPS_PER_BILLION_PAIR * (6.0 + ETA * lctx))


def relaxed_solution(c_flops: float, lctx: int, p: dict[str, float]) -> tuple[float, float, float]:
    k = budget_product(c_flops, lctx)
    n = ((p["alpha"] * p["A"] / (p["beta"] * p["B"])) * k ** p["beta"]) ** (1.0 / (p["alpha"] + p["beta"]))
    d = k / n
    return n, d, loss(n, d, p)


def feasible_cost(n_b: float, d_b: float, lctx: int) -> float:
    return FLOPS_PER_BILLION_PAIR * n_b * d_b * (6.0 + ETA * lctx)


def bounded_solution(c_flops: float, lctx: int, p: dict[str, float], support: dict[str, float]) -> dict[str, object]:
    n_lo, n_hi = support["N_min_B"], support["N_max_B"]
    d_lo, d_hi = support["D_min_B"], support["D_max_B"]
    k = budget_product(c_flops, lctx)
    bounds = [(math.log(n_lo), math.log(n_hi)), (math.log(d_lo), math.log(d_hi))]

    def objective(z: np.ndarray) -> float:
        return loss(float(math.exp(z[0])), float(math.exp(z[1])), p)

    def budget_constraint(z: np.ndarray) -> float:
        n_b, d_b = math.exp(float(z[0])), math.exp(float(z[1]))
        return k - n_b * d_b

    starts = [
        relaxed_solution(c_flops, lctx, p)[:2],
        (n_lo, d_lo), (n_lo, d_hi), (n_hi, d_lo), (n_hi, d_hi),
        (math.sqrt(n_lo * n_hi), math.sqrt(d_lo * d_hi)),
    ]
    candidates = []
    for n0, d0 in starts:
        z0 = np.array([
            min(max(math.log(n0), bounds[0][0]), bounds[0][1]),
            min(max(math.log(d0), bounds[1][0]), bounds[1][1]),
        ])
        result = minimize(
            objective,
            z0,
            method="SLSQP",
            bounds=bounds,
            constraints=[{"type": "ineq", "fun": budget_constraint}],
            options={"ftol": 1e-12, "maxiter": 1000},
        )
        n_b, d_b = math.exp(float(result.x[0])), math.exp(float(result.x[1]))
        candidates.append({
            "success": bool(result.success),
            "message": str(result.message),
            "n_b": n_b,
            "d_b": d_b,
            "loss": loss(n_b, d_b, p),
            "budget_residual_flops": c_flops - feasible_cost(n_b, d_b, lctx),
        })
    feasible = [c for c in candidates if c["budget_residual_flops"] >= -max(1.0, c_flops * 1e-10)]
    if not feasible:
        raise RuntimeError(f"No feasible bounded solution for C={c_flops}, Lctx={lctx}")
    best = min(feasible, key=lambda x: float(x["loss"]))
    return {
        **best,
        "n_starts": len(starts),
        "successful_starts": int(sum(bool(c["success"]) for c in candidates)),
        "unique_objectives": int(len({round(float(c["loss"]), 12) for c in feasible})),
        "support_status": (
            "inside_B1_support"
            if n_lo <= best["n_b"] <= n_hi and d_lo <= best["d_b"] <= d_hi
            else "bounded_to_B1_support"
        ),
    }


def write_yaml(path: Path, data: dict[str, object]) -> None:
    # Small deterministic YAML writer for scalar/list/dict metadata used here.
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for subkey, subvalue in value.items():
                lines.append(f"  {subkey}: {json.dumps(subvalue, ensure_ascii=False)}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RUN_DIR)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)

    params = load_m0()
    support = load_support()
    lctx_values = load_context_values()
    rows = []
    for lctx in lctx_values:
        for budget in BUDGETS:
            relaxed_n, relaxed_d, relaxed_l = relaxed_solution(budget, lctx, params)
            bounded = bounded_solution(budget, lctx, params, support)
            rows.append({
                "budget_flops": budget,
                "Lctx": lctx,
                "eta": ETA,
                "K_product_B2": budget_product(budget, lctx),
                "relaxed_N_B": relaxed_n,
                "relaxed_D_B": relaxed_d,
                "relaxed_loss": relaxed_l,
                "relaxed_within_B1_support": (
                    support["N_min_B"] <= relaxed_n <= support["N_max_B"]
                    and support["D_min_B"] <= relaxed_d <= support["D_max_B"]
                ),
                "bounded_N_B": bounded["n_b"],
                "bounded_D_B": bounded["d_b"],
                "bounded_loss": bounded["loss"],
                "bounded_cost_flops": feasible_cost(float(bounded["n_b"]), float(bounded["d_b"]), lctx),
                "budget_slack_flops": bounded["budget_residual_flops"],
                "bounded_support_status": bounded["support_status"],
                "n_starts": bounded["n_starts"],
                "successful_starts": bounded["successful_starts"],
                "unique_objectives": bounded["unique_objectives"],
            })

    table_path = out / "tables" / "q3_nd_baseline_scenarios.csv"
    with table_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "run_id": RUN_ID,
        "inputs": {
            "m0_metrics": {"path": str(METRICS_SOURCE.relative_to(ROOT)), "sha256": sha256(METRICS_SOURCE)},
            "b1_support": {"path": str(B1_SOURCE.relative_to(ROOT)), "sha256": sha256(B1_SOURCE), "rows": support["B1_rows"]},
            "c7_context_metadata": {"path": str(C7_SOURCE.relative_to(ROOT)), "sha256": sha256(C7_SOURCE), "rows": int(len(pd.read_csv(C7_SOURCE)))},
        },
        "roles": {
            "Q": "fixed at Q0; quality cost is zero",
            "p": "fixed bookkeeping value; not present in B1 objective",
            "B8": "excluded",
            "B9_B10": "excluded from fitting and optimization",
        },
    }
    write_yaml(out / "data_manifest.yaml", manifest)
    config = {
        "run_id": RUN_ID,
        "model": "M0 B1 classical N-D scaling law",
        "objective": "E + A*N_B^(-alpha) + B*D_B^(-beta)",
        "N_D_units": "billions",
        "flops_conversion": "1e18*(6 + eta*Lctx)*N_B*D_B",
        "eta": ETA,
        "budgets_flops": BUDGETS,
        "Lctx_values": lctx_values,
        "bounds": support,
        "solver": "SLSQP on log(N_B), log(D_B), explicit budget inequality, six deterministic starts",
        "status": "exploratory",
    }
    write_yaml(out / "config.yaml", config)
    metrics = {
        "run_id": RUN_ID,
        "status": "EXPLORATORY_Q3_ND_BASELINE",
        "m0_parameters": params,
        "support": support,
        "Lctx_values_from_metadata": lctx_values,
        "budgets_flops": BUDGETS,
        "scenario_count": len(rows),
        "cross_check": "analytic relaxed solution versus bounded explicit-constraint SLSQP",
        "output_sha256": {"q3_nd_baseline_scenarios.csv": sha256(table_path)},
        "limitations": [
            "M0 is B1/Pythia exploratory baseline, not a universal cross-source law",
            "Q and p are fixed; no B6 quality term or A-B row-level bridge is used",
            "relaxed solutions outside B1 support are extrapolation diagnostics",
            "C7 values are observed max_position_embeddings values from architecture metadata",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (out / "environment.txt").write_text(
        f"python={sys.version.split()[0]}\nplatform={platform.platform()}\nnumpy={np.__version__}\npandas={pd.__version__}\nscipy=1.11.1\n",
        encoding="utf-8",
    )
    (out / "command.txt").write_text("python -X utf8 scripts/q3_nd_baseline.py\n", encoding="utf-8")
    readme = f"""# Q3 N-D baseline exploratory run\n\n运行号：`{RUN_ID}`。\n\n本运行固定 `Q=Q0`、`p=p0`，只使用问题二 M0 的 B1 经典 N-D 拟合参数，比较三个算力预算和 C7 架构元数据中观察到的上下文长度。\n\n目标函数为 `E + A*N_B^(-alpha) + B*D_B^(-beta)`；预算约束为 `1e18*(6 + eta*Lctx)*N_B*D_B <= C`。同时输出无边界解析解和 B1 观测支持范围内的显式约束 SLSQP 解。\n\n该运行只验证问题三基线优化流程，不加入质量项、领域配比项或 A-B 逐行桥接。超出 B1 的 `N,D` 范围的解析解仅作外推诊断。\n\n主要结果：`tables/q3_nd_baseline_scenarios.csv`。\n"""
    (out / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
