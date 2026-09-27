"""Compute-growth scenarios for Q4 using Q3 optimum elasticities as exogenous constraints."""
from __future__ import annotations
import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
import statsmodels.api as sm

from q4_nested_quantile_experiment import read_data, design

OUT = output_dir("compute_scenario")
OUT.mkdir(exist_ok=True)


def main():
    d = read_data()
    train = d[d.year == 2024].copy()
    profile = d[d.year == 2025].copy()
    q3 = pd.read_csv(q3_optima_file())
    q3 = q3[q3.L_ctx == 4096].sort_values("budget_FLOPs")
    kN = float(np.polyfit(np.log(q3.budget_FLOPs), np.log(q3.N_B), 1)[0])
    kD = float(np.polyfit(np.log(q3.budget_FLOPs), np.log(q3.D_B), 1)[0])

    specs = {"params_type_no_time": (True, False, True), "full_time_type": (True, True, True)}
    fits = {}
    for name, spec in specs.items():
        xtr, _ = design(train, profile, spec)
        fits[name] = sm.QuantReg(train.score.to_numpy(float), xtr).fit(q=.95, max_iter=5000, p_tol=1e-8)

    rows = []
    for growth in (0.00, 0.25, 0.50):
        for horizon in (12, 24):
            scale_N = (1 + growth) ** (kN * horizon / 12)
            scale_D = (1 + growth) ** (kD * horizon / 12)
            future = profile.copy()
            future["params"] = future["params"] * scale_N
            future["log_params"] = np.log1p(future["params"])
            future["time_month"] = 9 + horizon
            for model, spec in specs.items():
                _, xf = design(train, future, spec)
                pred = np.asarray(fits[model].predict(xf), float)
                rows.append({
                    "annual_compute_growth": growth, "horizon_months": horizon,
                    "model": model, "n_profile": len(pred),
                    "N_scale": scale_N, "D_scale": scale_D,
                    "conditional_frontier_q95": np.quantile(pred, .95),
                    "conditional_median": np.median(pred),
                    "conditional_mean": np.mean(pred),
                    "conditional_max": np.max(pred),
                })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "compute_constrained_forecasts.csv", index=False)
    meta = {"q3_context_length": 4096, "kN": kN, "kD": kD,
            "growth_scenarios": [0.0, 0.25, 0.5], "horizons_months": [12, 24],
            "profile": "observed 2025 parameter/type composition scaled by Q3 N*(C) elasticity",
            "warning": "Scenario bridge; Q3 optimum elasticities are treated as external assumptions and do not establish causality."}
    (OUT / "run_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out.sort_values(["model", "horizon_months", "annual_compute_growth"]).to_string(index=False))


if __name__ == "__main__":
    main()
