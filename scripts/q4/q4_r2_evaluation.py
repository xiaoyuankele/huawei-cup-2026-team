"""Compute pseudo-R2 and ordinary predictive R2 for Q4 quantile models."""
from __future__ import annotations
from pathlib import Path
from q4_paths import DATA_DIR, RUN_DIR, output_dir, q3_optima_file
import numpy as np
import pandas as pd
import statsmodels.api as sm
from q4_c8_panel_quantile_experiment import read_data, design

OUT = output_dir("error"); OUT.mkdir(exist_ok=True)


def r2(y, p, baseline):
    return float(1 - np.sum((y-p)**2) / np.sum((y-baseline)**2))


def main():
    d = read_data(); train = d[d.year == 2024].copy(); test = d[d.year == 2025].copy()
    specs = {"intercept": (False, False, False), "params": (True, False, False),
             "params_type": (True, False, True), "params_time": (True, True, False),
             "full": (True, True, True)}
    rows = []
    for tau in (.90, .95):
        for name, spec in specs.items():
            xtr, xte = design(train, test, spec)
            fit = sm.QuantReg(train.score.to_numpy(float), xtr).fit(q=tau, max_iter=5000, p_tol=1e-8)
            p_tr = np.asarray(fit.predict(xtr), float); p_te = np.asarray(fit.predict(xte), float)
            ytr = train.score.to_numpy(float); yte = test.score.to_numpy(float)
            rows.append({"tau": tau, "model": name, "pseudo_R2_train": float(fit.prsquared),
                         "ordinary_R2_train": r2(ytr, p_tr, ytr.mean()),
                         "ordinary_R2_test_trainmean_baseline": r2(yte, p_te, ytr.mean()),
                         "ordinary_R2_test_testmean_baseline": r2(yte, p_te, yte.mean())})
    out = pd.DataFrame(rows); out.to_csv(OUT / "r2_metrics.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
