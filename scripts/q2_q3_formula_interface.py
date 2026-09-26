"""Register the Q2 generalized scaling-law variants and their Q3 interfaces.

This is an interface/preflight artifact, not a new fit. It reads frozen Q2/Q3
metrics, records units and gates, and does not alter existing results.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments/runs/q2-q3-formula-interface-20260926-r01"
Q2_METRICS = ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json"
Q3_ND = ROOT / "experiments/runs/q3-nd-baseline-20260925-r01/metrics.json"
Q3_Q = ROOT / "experiments/runs/q3-q-conditional-20260925-r01/metrics.json"
Q3_P = ROOT / "experiments/runs/q3-p-conditional-20260925-r01/metrics.json"
Q3_M2 = ROOT / "experiments/runs/q2-q3-interface-sensitivity-20260926-r01/metrics.json"
Q1_P_DOC = ROOT / "docs/decisions/q1-p-recipe-results.md"
Q2_FOUR_DOC = ROOT / "docs/decisions/q2-four-quantity-conditional-preflight-20250925.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    q2 = json.loads(Q2_METRICS.read_text(encoding="utf-8"))
    nd = json.loads(Q3_ND.read_text(encoding="utf-8"))
    q = json.loads(Q3_Q.read_text(encoding="utf-8"))
    p = json.loads(Q3_P.read_text(encoding="utf-8"))

    RUN.mkdir(parents=True, exist_ok=True)
    formula_rows = [
        {
            "formula_id": "M0_B1_ND",
            "formula": "L=E+A*N^(-alpha)+B*D^(-beta)",
            "parameter_source": "q2-m0-m1-20260925-r01:M0.fit_full_B1",
            "variables_and_units": "N,D in billion parameters/tokens; L in B1 Loss units",
            "q3_role": "primary Q3 N-D baseline objective",
            "q3_status": "READY_CONDITIONAL",
            "claim_boundary": "B1/Pythia internal baseline; not universal cross-source law",
        },
        {
            "formula_id": "M1_B6B7_NDQ",
            "formula": "L=E+A*N^(-alpha)+B*D^(-beta)+G*(1-Q_score)",
            "parameter_source": "q2-m0-m1-20260925-r01:M1.fit_B6",
            "variables_and_units": "N,D in B units; Q_score native B6/B7 range [0.1,1.0]",
            "q3_role": "Q-conditional resource allocation objective",
            "q3_status": "READY_CONDITIONAL",
            "claim_boundary": "B6/B7 semi-synthetic condition; Q_score is not Q1 quality Q",
        },
        {
            "formula_id": "A_P_RECIPE",
            "formula": "L_A=f_s(p) (ilr/Ridge, quadratic Ridge, or candidate GBDT)",
            "parameter_source": "q1-model-benchmark-20260924-r01 and q1-p-stability-20260925-r01",
            "variables_and_units": "p is a 17-part composition vector; p_j>=0 and sum(p)=1",
            "q3_role": "discrete observed-p scenario label; not a continuous Q3 coefficient",
            "q3_status": "READY_SCENARIO_ONLY",
            "claim_boundary": "A-side candidate response surface; cross-scale/extrapolation limits remain",
        },
        {
            "formula_id": "M2_QA_OF_P",
            "formula": "Q_A(p)=sum_j p_j*q_j (or partial/interval mapping variants)",
            "parameter_source": "A16 mapping plus Q1 quality-domain candidate scores",
            "variables_and_units": "Q_A is Q1-side 0-100 candidate scale; mapped_mass must be retained",
            "q3_role": "conditional p/Q scenario metadata; requires calibration before Q cost",
            "q3_status": "READY_SCENARIO_ONLY",
            "claim_boundary": "6/17 mapped domains; inferred domains and Q1 review remain open",
        },
        {
            "formula_id": "M3_FOUR_QUANTITY",
            "formula": "L_cond(N,D,Q_A(p))=E+A*N^(-alpha)+B*D^(-beta)+G_bridge*(1-Q_A(p))",
            "parameter_source": "q2-four-quantity-conditional-preflight-20250925",
            "variables_and_units": "Q_A is 0-100 until a verified map to B6 Q_score exists",
            "q3_role": "formal joint objective specification only",
            "q3_status": "BLOCKED_NO_FIT",
            "claim_boundary": "G_bridge and A-B row/batch effect are not identifiable",
        },
    ]
    with (RUN / "formula_registry.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(formula_rows[0].keys()))
        writer.writeheader()
        writer.writerows(formula_rows)

    parameter_rows = []
    for model_id, values in [("M0_B1_ND", q2["M0"]["fit_full_B1"]), ("M1_B6B7_NDQ", q2["M1"]["fit_B6"])]:
        names = ["E", "A", "B", "alpha", "beta"] if model_id.startswith("M0") else ["E", "A", "B", "G", "alpha", "beta"]
        for name, value in zip(names, values):
            parameter_rows.append({"formula_id": model_id, "parameter": name, "value": value, "source_run": "q2-m0-m1-20260925-r01"})
    with (RUN / "parameter_registry.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(parameter_rows[0].keys()))
        writer.writeheader()
        writer.writerows(parameter_rows)

    interface_rows = [
        {
            "interface_id": "Q3_ND_BASELINE",
            "objective": "min M0(N,D)",
            "cost_constraint": "C_train=6ND; C_attn=eta*ND*Lctx",
            "quality_term": "none; Q fixed at baseline",
            "p_term": "none; p fixed/absent",
            "input_run": "q2-m0-m1-20260925-r01 + C7",
            "existing_run": "q3-nd-baseline-20260925-r01",
            "status": "EXECUTED_CONDITIONAL",
        },
        {
            "interface_id": "Q3_Q_CONDITIONAL",
            "objective": "min M1(N,D,Q_score)",
            "cost_constraint": "C_base+C_Q <= budget; C_Q=D[g(Q_score)-g(Q0)]",
            "quality_term": "native B6/B7 Q_score in [0.1,1.0]",
            "p_term": "none; p fixed/absent",
            "input_run": "q2-m0-m1-20260925-r01 + B6 + C7",
            "existing_run": "q3-q-conditional-20260925-r01 and q3-q-robustness-20260925-r01",
            "status": "EXECUTED_CONDITIONAL",
        },
        {
            "interface_id": "Q3_P_SCENARIO",
            "objective": "M0 N-D allocation reported per observed p candidate",
            "cost_constraint": "same Q3 N-D cost constraint",
            "quality_term": "Q1-side Q_A(p) may be reported as metadata only",
            "p_term": "discrete observed p label; no continuous p coefficient",
            "input_run": "q1-p-stability-20260925-r01 + q3-nd-baseline-20260925-r01",
            "existing_run": "q3-p-conditional-20260925-r01",
            "status": "EXECUTED_SCENARIO",
        },
        {
            "interface_id": "Q3_JOINT_FOUR_QUANTITY",
            "objective": "min M3(N,D,Q_A(p))",
            "cost_constraint": "requires calibrated Q_A -> Q_score before C_Q",
            "quality_term": "G_bridge not identifiable",
            "p_term": "requires verified A-B bridge and mapping",
            "input_run": "q2-four-quantity-conditional-preflight-20250925",
            "existing_run": "none",
            "status": "BLOCKED_FORMAL_JOINT_MIGRATION",
        },
        {
            "interface_id": "Q3_M2_INTERFACE_SENSITIVITY",
            "objective": "fixed hypothetical Q_B from M2 scenarios, then solve M1 N-D allocation",
            "cost_constraint": "same M1 Q3 budget and quality-cost families",
            "quality_term": "M2 partial/renormalized/interval Q_A scenarios; Q1-to-B6 calibration explicitly hypothetical",
            "p_term": "six observed A4/A5 p candidate labels; no continuous p coefficient",
            "input_run": "q2-m2-sensitivity-20250925-r01 + q3-p-conditional-20260925-r01",
            "existing_run": "q2-q3-interface-sensitivity-20260926-r01",
            "status": "EXECUTED_SCENARIO_ONLY",
        },
    ]
    with (RUN / "q3_interface_contract.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(interface_rows[0].keys()))
        writer.writeheader()
        writer.writerows(interface_rows)

    metrics = {
        "run_id": "q2-q3-formula-interface-20260926-r01",
        "status": "FORMULA_INTERFACE_REGISTERED",
        "formula_count": len(formula_rows),
        "q3_interface_count": len(interface_rows),
        "executed_q3_paths": ["Q3_ND_BASELINE", "Q3_Q_CONDITIONAL", "Q3_P_SCENARIO", "Q3_M2_INTERFACE_SENSITIVITY"],
        "blocked_path": "Q3_JOINT_FOUR_QUANTITY",
        "parameter_sources": {
            "q2_metrics": sha256(Q2_METRICS),
            "q3_nd_metrics": sha256(Q3_ND),
            "q3_q_metrics": sha256(Q3_Q),
            "q3_p_metrics": sha256(Q3_P),
            "q3_m2_interface_metrics": sha256(Q3_M2),
        },
        "checks": {
            "m0_parameters_registered": len(q2["M0"]["fit_full_B1"]) == 5,
            "m1_parameters_registered": len(q2["M1"]["fit_B6"]) == 6,
            "q3_nd_scenarios": nd["scenario_count"],
            "q3_q_scenarios": q["scenario_count"],
            "q3_p_panel_rows": p["panel_rows"],
            "q1_to_b_q_scale_calibrated": False,
            "a_b_row_bridge_available": False,
            "b8_allowed_in_main_fit": False,
        },
        "limitations": [
            "This registry does not refit any model or merge A and B rows.",
            "M1 uses native B6/B7 Q_score; M2 Q_A(p) remains Q1-side 0-100 scenario metadata.",
            "M3 is an interface specification until G_bridge, Q scale calibration and a traceable A-B bridge exist.",
        ],
    }
    (RUN / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUN / "README.md").write_text(
        "# Q2-Q3 generalized scaling-law interface\n\n"
        "本运行只登记问题二各广义标度律与问题三优化轨道的接口，不重新拟合、不修改旧结果、不构造 A-B 行级联合目标。\n"
        "M0 接 Q3 N-D 基线，M1 接原生 B6/B7 Q 条件优化，A 侧 p/Q 接离散情景面板；四量 M3 暂保持阻断。\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
