"""Q3 conditional experiment: optimize N, D and Q under three Appendix-B costs.

This is an exploratory conditional calculation.  It uses the B6 M1 fit only
and treats Q as the B6/B7 semi-synthetic score.  It does not promote the score
to the Q1 quality output or create an A--B row-level bridge.
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
RUN_ID = "q3-q-conditional-20260925-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
M1_SOURCE = ROOT / "experiments" / "runs" / "q2-m0-m1-20260925-r01" / "metrics.json"
B1_SOURCE = ROOT / "data" / "origin" / "real_attachments" / "B_scaling_laws" / "pythia_training_log_existing.csv"
B6_SOURCE = ROOT / "data" / "origin" / "real_attachments" / "B_scaling_laws" / "supplementary_NQ_experiment.csv"
C7_SOURCE = ROOT / "data" / "origin" / "real_attachments" / "C_efficiency_evolution" / "model_architecture_metadata.csv"
ETA = 2e-4
FLOPS_PER_BILLION_PAIR = 1e18
TOKENS_PER_BILLION = 1e9
Q0 = 0.1
BUDGETS = [1e19, 1e22, 1e24]

COSTS = {
    "exponential": {"gamma": 1e7, "lambda": 6.0},
    "power": {"gamma": 5e9, "lambda": 4.0},
    "logarithmic": {"gamma": 2e9, "lambda": 10.0},
}


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


def load_m1() -> dict[str, float]:
    payload = json.loads(M1_SOURCE.read_text(encoding="utf-8"))
    values = payload["M1"]["fit_B6"]
    return {name: float(value) for name, value in
            zip(("E", "A", "B", "G", "alpha", "beta"), values)}


def load_support() -> dict[str, float]:
    frame = pd.read_csv(B1_SOURCE)
    return {"N_min_B": float(frame["N_params_B"].min()),
            "N_max_B": float(frame["N_params_B"].max()),
            "D_min_B": float(frame["D_tokens_B"].min()),
            "D_max_B": float(frame["D_tokens_B"].max()),
            "B1_rows": int(len(frame))}


def load_q_bounds() -> dict[str, float]:
    frame = pd.read_csv(B6_SOURCE)
    return {"Q_min": float(frame["Q_score"].min()),
            "Q_max": float(frame["Q_score"].max()),
            "B6_rows": int(len(frame))}


def load_context_values() -> list[int]:
    frame = pd.read_csv(C7_SOURCE)
    values = sorted({int(v) for v in frame["max_position_embeddings"].dropna()})
    if not values:
        raise ValueError("No context values found in C7 metadata")
    return values


def g_value(q: float, kind: str) -> float:
    spec = COSTS[kind]
    if kind == "exponential":
        return spec["gamma"] * math.exp(spec["lambda"] * q)
    if kind == "power":
        return spec["gamma"] * q ** spec["lambda"]
    return spec["gamma"] * math.log1p(spec["lambda"] * q)


def quality_cost(d_b: float, q: float, kind: str, q0: float = Q0) -> float:
    return d_b * TOKENS_PER_BILLION * (g_value(q, kind) - g_value(q0, kind))


def base_cost(n_b: float, d_b: float, lctx: int) -> float:
    return FLOPS_PER_BILLION_PAIR * n_b * d_b * (6.0 + ETA * lctx)


def total_cost(n_b: float, d_b: float, q: float, lctx: int, kind: str,
               q0: float = Q0) -> float:
    return base_cost(n_b, d_b, lctx) + quality_cost(d_b, q, kind, q0)


def loss(n_b: float, d_b: float, q: float, p: dict[str, float]) -> float:
    return (p["E"] + p["A"] * n_b ** (-p["alpha"])
            + p["B"] * d_b ** (-p["beta"]) + p["G"] * (1.0 - q))


def solve_one(budget: float, lctx: int, kind: str, p: dict[str, float],
              support: dict[str, float], q_bounds: dict[str, float],
              q0: float = Q0) -> dict[str, object]:
    n_lo, n_hi = support["N_min_B"], support["N_max_B"]
    d_lo, d_hi = support["D_min_B"], support["D_max_B"]
    q_lo, q_hi = q_bounds["Q_min"], q_bounds["Q_max"]
    bounds = [(math.log(n_lo), math.log(n_hi)),
              (math.log(d_lo), math.log(d_hi)), (q_lo, q_hi)]

    def unpack(z: np.ndarray) -> tuple[float, float, float]:
        return math.exp(float(z[0])), math.exp(float(z[1])), float(z[2])

    def objective(z: np.ndarray) -> float:
        n_b, d_b, q = unpack(z)
        return loss(n_b, d_b, q, p)

    def budget_constraint(z: np.ndarray) -> float:
        n_b, d_b, q = unpack(z)
        # Scale the inequality to order one; raw FLOP magnitudes make SLSQP's
        # finite-difference stopping test unnecessarily ill-conditioned.
        return (budget - total_cost(n_b, d_b, q, lctx, kind, q0)) / budget

    n_mid = math.sqrt(n_lo * n_hi)
    d_mid = math.sqrt(d_lo * d_hi)
    starts = [(n_lo, d_lo, q_lo), (n_mid, d_mid, q_lo),
              (n_mid, d_mid, (q_lo + q_hi) / 2.0), (n_hi, d_hi, q_lo),
              (n_lo, d_hi, q_hi), (n_hi, d_lo, q_hi)]
    candidates = []
    for n0, d0, q_start in starts:
        z0 = np.array([min(max(math.log(n0), bounds[0][0]), bounds[0][1]),
                       min(max(math.log(d0), bounds[1][0]), bounds[1][1]),
                       min(max(q_start, q_lo), q_hi)])
        result = minimize(objective, z0, method="SLSQP", bounds=bounds,
                          constraints=[{"type": "ineq", "fun": budget_constraint}],
                          options={"ftol": 1e-12, "maxiter": 2000})
        n_b, d_b, q = unpack(result.x)
        c = total_cost(n_b, d_b, q, lctx, kind, q0)
        candidates.append({"success": bool(result.success), "message": str(result.message),
                           "N_B": n_b, "D_B": d_b, "Q": q,
                           "loss": loss(n_b, d_b, q, p), "total_cost_flops": c,
                           "budget_slack_flops": budget - c,
                           "base_train_attn_cost_flops": base_cost(n_b, d_b, lctx),
                           "quality_cost_flops": quality_cost(d_b, q, kind, q0)})
    feasible = [c for c in candidates if float(c["budget_slack_flops"]) >= -max(1.0, budget * 1e-9)]
    if not feasible:
        raise RuntimeError(f"No feasible solution for budget={budget}, Lctx={lctx}, kind={kind}")
    feasible_success = [c for c in feasible if bool(c["success"])]
    # Prefer optimizer-converged candidates; retain a fallback only when all
    # starts fail, and expose that fact in the output rather than hiding it.
    selected_pool = feasible_success if feasible_success else feasible
    best = min(selected_pool, key=lambda c: float(c["loss"]))
    n_b, d_b, q = float(best["N_B"]), float(best["D_B"]), float(best["Q"])
    return {**best, "budget_flops": budget, "Lctx": lctx, "cost_family": kind,
            "Q0": q0, "support_status": "inside_B1_B6_support",
            "n_starts": len(starts),
            "successful_starts": int(sum(bool(c["success"]) for c in candidates)),
            "unique_objectives": int(len({round(float(c["loss"]), 12) for c in feasible})),
            "selected_from_successful_start": bool(best["success"]),
            "N_at_bound": bool(abs(n_b - n_lo) < 1e-8 or abs(n_b - n_hi) < 1e-8),
            "D_at_bound": bool(abs(d_b - d_lo) < 1e-8 or abs(d_b - d_hi) < 1e-8),
            "Q_at_bound": bool(abs(q - q_lo) < 1e-8 or abs(q - q_hi) < 1e-8)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RUN_DIR)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)
    p, support, q_bounds = load_m1(), load_support(), load_q_bounds()
    contexts = load_context_values()
    rows = [solve_one(budget, lctx, kind, p, support, q_bounds)
            for kind in COSTS for lctx in contexts for budget in BUDGETS]
    table = out / "tables" / "q3_q_conditional_scenarios.csv"
    with table.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    metrics = {
        "run_id": RUN_ID, "status": "EXPLORATORY_Q3_Q_CONDITIONAL",
        "m1_parameters": p, "support": support, "q_bounds": q_bounds,
        "Q0": Q0, "cost_families": COSTS, "budgets_flops": BUDGETS,
        "Lctx_values_from_metadata": contexts, "scenario_count": len(rows),
        "output_sha256": {"q3_q_conditional_scenarios.csv": sha256(table)},
        "limitations": [
            "M1 is a B6/B7 semi-synthetic conditional sensitivity, not a universal law",
            "Q is the B6 score and is not the Q1 A-side quality score",
            "p is fixed and the A-B row-level bridge is not used",
            "N,D,Q are bounded to observed B1/B6 ranges; no unbounded optimum is claimed",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (out / "environment.txt").write_text(f"python={sys.version.split()[0]}\nplatform={platform.platform()}\nnumpy={np.__version__}\npandas={pd.__version__}\nscipy=1.11.1\n", encoding="utf-8")
    (out / "command.txt").write_text("python -X utf8 scripts/q3_q_conditional.py\n", encoding="utf-8")
    readme = f"""# Q3 Q conditional exploratory run

运行号：`{RUN_ID}`。本运行在 B6/B7 M1 半合成敏感性模型上，把 `Q` 作为决策变量，分别比较附录 B 的指数、幂函数和对数渐进质量成本。`Q0=0.1`，Q 上界取 B6 观测上界 0.9；N、D 限制在 B1 支持范围，`Lctx` 取 C7 观测值。

总成本为 `1e18*(6+eta*Lctx)*N_B*D_B + 1e9*D_B*(g(Q)-g(Q0))`，目标为 M1 的 `E+A*N_B^(-alpha)+B*D_B^(-beta)+G*(1-Q)`。每个场景用六个确定性起点的显式约束 SLSQP 求解，并记录质量成本、训练/注意力成本和边界状态。

结果仅用于检查质量投入是否挤占 N、D 预算，不把 B6 Q 解释为已验证的 Q1 质量分，也不产生最优配比或 A--B 联合结论。
"""
    (out / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
