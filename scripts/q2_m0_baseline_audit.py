"""Audit and freeze the scope of the B1 M0 baseline without refitting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-m0-baseline-audit-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    m = json.loads((ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json").read_text(encoding="utf-8"))
    m0 = m["M0"]
    folds = m0["leave_one_parameter_size_out"]
    rmses = [f["metrics"]["rmse"] for f in folds]
    r2s = [f["metrics"]["r2"] for f in folds]
    params = list(zip(*(f["fit"] for f in folds)))
    parameter_stability = {
        name: {"mean": mean(values), "sd": pstdev(values), "min": min(values), "max": max(values)}
        for name, values in zip(["E", "A", "B", "alpha", "beta"], params)
    }
    external = m0["external_diagnostics"]
    report = {
        "run_id": "q2-m0-baseline-audit-20250925-r01",
        "status": "FROZEN_B1_BASELINE_EXPLORATORY",
        "scope": "B1 internal scaling baseline only",
        "source_run": "q2-m0-m1-20260925-r01",
        "checks": {
            "grouped_leave_one_N_size_out": len(folds) == 8,
            "internal_r2_all_above_0_99": min(r2s) > 0.99,
            "external_diagnostics_kept_separate": True,
            "cross_source_universal_law_claim": False,
            "B1_compute_proxy_exact_6ND": False,
            "random_row_split_used": False,
        },
        "internal_metrics": {"folds": len(folds), "rmse_min": min(rmses), "rmse_max": max(rmses), "r2_min": min(r2s), "r2_max": max(r2s)},
        "parameter_stability": parameter_stability,
        "external_diagnostics": external,
        "frozen_interpretation": [
            "M0 is a descriptive B1 baseline with parameter-size grouped holdout.",
            "B2/B4/B5 are external diagnostics and do not select or refit M0.",
            "The baseline is not a universal cross-source scaling law.",
            "The C_FLOPs_1e21 column is retained as a proxy and is not assumed to equal exact 6ND.",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text("# M0 B1 baseline audit\n\nThis audit freezes the interpretation of the already-run M0 fit. It does not refit the model or promote it to a universal law.\n", encoding="utf-8")
    print(json.dumps({"run_id": report["run_id"], "status": report["status"], "rmse_range": [min(rmses), max(rmses)], "min_external_r2": min(v["r2"] for v in external.values())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
