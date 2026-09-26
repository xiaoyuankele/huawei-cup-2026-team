"""Permutation placebo for monthly frontier slopes (descriptive, n=10)."""
from __future__ import annotations
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd

OUT = output_dir("time_placebo")
OUT.mkdir(exist_ok=True)
BASE = output_dir("task_frontier")


def main():
    records = []
    files = [BASE / "loo_exclude_MATH_monthly_frontier.csv"]
    files += [BASE / f"{t}_monthly_frontier.csv" for t in ["IFEval", "BBH", "MATH", "GPQA", "MUSR", "MMLU_PRO"]]
    rng = np.random.default_rng(20260925)
    B = 100000
    for fn in files:
        f = pd.read_csv(fn)
        y = f["q95"].to_numpy(float) * 100.0
        x = np.arange(len(y), dtype=float)
        obs = float(np.polyfit(x, y, 1)[0])
        perm = np.empty(B)
        for i in range(B):
            perm[i] = np.polyfit(x, rng.permutation(y), 1)[0]
        records.append({"target": fn.stem.replace("_monthly_frontier", ""),
                        "n_months": len(y), "observed_slope_per_month": obs,
                        "perm_mean": float(perm.mean()), "perm_sd": float(perm.std(ddof=1)),
                        "one_sided_exceedance": float(np.mean(perm >= obs)),
                        "two_sided_exceedance": float(np.mean(np.abs(perm) >= abs(obs))),
                        "perm_q025": float(np.quantile(perm, .025)),
                        "perm_q975": float(np.quantile(perm, .975))})
    out = pd.DataFrame(records)
    out.to_csv(OUT / "monthly_slope_placebo.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
