"""Audit and freeze the scope of the B6/B7 M1 sensitivity result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-m1-sensitivity-audit-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    m = json.loads((ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json").read_text(encoding="utf-8"))
    m1 = m["M1"]
    folds = m1["grouped_ND_cell_cv"]
    rmses = [f["metrics"]["rmse"] for f in folds]
    r2s = [f["metrics"]["r2"] for f in folds]
    params = list(zip(*(f["fit"] for f in folds)))
    stability = {
        name: {"mean": mean(values), "sd": pstdev(values), "min": min(values), "max": max(values)}
        for name, values in zip(["E", "A", "B", "G", "alpha", "beta"], params)
    }
    report = {
        "run_id": "q2-m1-sensitivity-audit-20250925-r01",
        "status": "FROZEN_B6_B7_SEMISYNTHETIC_EXPLORATORY",
        "scope": "B6/B7 semi-synthetic conditional quality sensitivity",
        "source_run": "q2-m0-m1-20260925-r01",
        "checks": {
            "grouped_ND_cell_holdout": len(folds) == 5,
            "internal_r2_all_above_0_90": min(r2s) > 0.90,
            "B7_extension_kept_nested": True,
            "B7_extension_treated_as_independent_validation": False,
            "B8_in_fit": False,
            "A_quality_score_validated": False,
            "causal_quality_claim": False,
        },
        "internal_metrics": {"folds": len(folds), "rmse_min": min(rmses), "rmse_max": max(rmses), "r2_min": min(r2s), "r2_max": max(r2s)},
        "parameter_stability": stability,
        "nested_extension": m1["B7_extension_metrics"],
        "interpretation": [
            "M1 is a conditional sensitivity result for the B6/B7 semi-synthetic construction.",
            "B7 contains all B6 rows; its 90-row extension is a nested diagnostic, not independent validation.",
            "The fitted G coefficient does not validate Q1 or establish a causal quality effect.",
            "B8 remains excluded because its direction and provenance gates are unresolved.",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text("# M1 B6/B7 sensitivity audit\n\nThis audit freezes the semi-synthetic and nested-extension interpretation of M1. It does not promote Q_score to the Q1 score or claim causality.\n", encoding="utf-8")
    print(json.dumps({"run_id": report["run_id"], "status": report["status"], "rmse_range": [min(rmses), max(rmses)], "extension_n": m1["B7_extension_metrics"]["n"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
