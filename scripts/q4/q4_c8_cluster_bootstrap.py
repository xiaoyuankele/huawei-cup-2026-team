"""Cluster bootstrap for detailed-C8 panel quantile coefficients and scenarios."""
from __future__ import annotations
import json
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
import statsmodels.api as sm
from q4_c8_panel_quantile_experiment import read_data, design

OUT = output_dir("c8_bootstrap"); OUT.mkdir(exist_ok=True)


def main(B=100, seed=20260925):
    d = read_data(); train = d[d.year == 2024].copy(); profile = d[d.year == 2025].copy()
    train["cluster"] = train["Model"].astype(str).str.split("/").str[0]
    clusters = train.cluster.dropna().unique(); rng = np.random.default_rng(seed)
    rows = []
    spec = (True, True, True)
    for b in range(B):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        pieces = []
        for j, c in enumerate(sampled):
            q = train[train.cluster == c].copy(); q["_draw_cluster"] = j; pieces.append(q)
        boot = pd.concat(pieces, ignore_index=True)
        try:
            xtr, _ = design(boot, profile, spec)
            fit = sm.QuantReg(boot.score.to_numpy(float), xtr).fit(q=.95, max_iter=3000, p_tol=1e-7)
            future_rows = []
            for h in (12, 24):
                f = profile.copy(); f["time_month"] = 9 + h
                _, xf = design(boot, f, spec)
                p = np.asarray(fit.predict(xf), float)
                future_rows.append((h, np.quantile(p, .95)))
            row = {"replicate": b, "n_boot_rows": len(boot), "n_clusters": len(sampled),
                   "const": float(fit.params.get("const", np.nan)),
                   "log_params": float(fit.params.get("log_params", np.nan)),
                   "time_month": float(fit.params.get("time_month", np.nan))}
            for h, v in future_rows: row[f"frontier_q95_h{h}"] = v
            rows.append(row)
        except Exception:
            continue
    out = pd.DataFrame(rows); out.to_csv(OUT / "cluster_bootstrap_draws.csv", index=False)
    summary = []
    for col in ["const", "log_params", "time_month", "frontier_q95_h12", "frontier_q95_h24"]:
        x = out[col].dropna().to_numpy(float)
        summary.append({"quantity": col, "n_boot": len(x), "median": np.median(x),
                        "q025": np.quantile(x, .025), "q975": np.quantile(x, .975),
                        "sd": np.std(x, ddof=1)})
    pd.DataFrame(summary).to_csv(OUT / "cluster_bootstrap_summary.csv", index=False)
    (OUT / "run_metadata.json").write_text(json.dumps({"B_requested": B, "B_success": len(out), "cluster_definition": "Model prefix before slash", "warning": "Cluster is a release/organization proxy, not a verified model family."}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
