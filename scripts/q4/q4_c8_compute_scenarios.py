"""Compute-growth scenarios on the detailed C8 score scale."""
from __future__ import annotations
import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
import statsmodels.api as sm
from q4_c8_panel_quantile_experiment import read_data, design

OUT = output_dir("c8_compute"); OUT.mkdir(exist_ok=True)


def main():
    d = read_data(); train = d[d.year == 2024].copy(); profile = d[d.year == 2025].copy()
    q3 = pd.read_csv(q3_optima_file()); q3 = q3[q3.L_ctx == 4096]
    kN = float(np.polyfit(np.log(q3.budget_FLOPs), np.log(q3.N_B), 1)[0])
    kD = float(np.polyfit(np.log(q3.budget_FLOPs), np.log(q3.D_B), 1)[0])
    specs = {"params_type_no_time": (True, False, True), "full_time_type": (True, True, True)}
    fits = {}
    for name, spec in specs.items():
        xtr, _ = design(train, profile, spec)
        fits[name] = sm.QuantReg(train.score.to_numpy(float), xtr).fit(q=.95, max_iter=5000, p_tol=1e-8)
    rows = []
    for growth in (0.0, .25, .50):
        for h in (12, 24):
            nscale = (1 + growth) ** (kN * h / 12); dscale = (1 + growth) ** (kD * h / 12)
            future = profile.copy(); future["params"] *= nscale; future["log_params"] = np.log1p(future.params); future["time_month"] = 9 + h
            for name, spec in specs.items():
                _, xf = design(train, future, spec); p = np.asarray(fits[name].predict(xf), float)
                rows.append({"annual_compute_growth": growth, "horizon_months": h, "model": name,
                    "N_scale": nscale, "D_scale": dscale, "frontier_q95_conditional": np.quantile(p,.95),
                    "median_conditional": np.median(p), "mean_conditional": np.mean(p), "max_conditional": np.max(p)})
    out = pd.DataFrame(rows); out.to_csv(OUT / "compute_constrained_forecasts.csv", index=False)
    (OUT / "run_metadata.json").write_text(json.dumps({"kN": kN, "kD": kD, "score": "detailed C8 six-task equal-weight", "warning": "External Q3 elasticity scenario; not causal."}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out.sort_values(["model", "horizon_months", "annual_compute_growth"]).to_string(index=False))


if __name__ == "__main__":
    main()
