"""Conditional M2 sensitivity for unmapped A mixture domains.

The available Q1 domain scores are review-blocked.  This script therefore
reports a scenario envelope in the Q1 candidate-score scale only.  It never
maps the result to B6's 0--1 Q_score scale and never fits B data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIXTURES = {
    "A4_A5_train_1m": ("A_data_value/regmix_tables/train_mixture_1m.csv", "fit"),
    "A6_A7_validation_1m": ("A_data_value/regmix_tables/test_mixture_1m.csv", "validation"),
    "A8_A9_validation_60m": ("A_data_value/regmix_tables/test_mixture_60m.csv", "validation"),
    "A10_A11_validation_1b": ("A_data_value/regmix_tables/test_mixture_1B.csv", "validation"),
    "A12_A13_extrapolation_10b": ("A_data_value/regmix_tables/est_mixture_10b.csv", "extrapolation"),
    "A14_A15_extrapolation_70b": ("A_data_value/regmix_tables/est_mixture_70b.csv", "extrapolation"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            return list(csv.DictReader(raw.decode(enc).splitlines()))
        except UnicodeDecodeError:
            pass
    raise ValueError(f"cannot decode {path}")


def fnum(v: str) -> float:
    return float(v) if v and v.strip() else 0.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-m2-sensitivity-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    tables = out / "tables"
    tables.mkdir(exist_ok=True)
    mapping_path = ROOT / "data/origin/real_attachments/A_data_value/domain_mapping_guide.csv"
    score_path = ROOT / "experiments/runs/q1-critic-topsis-20260924-r01/tables/domain_scores.csv"
    mapping = [r for r in read_csv(mapping_path) if r.get("mixture_domain")]
    scores = [r for r in read_csv(score_path) if r.get("dataset_id") == "A1" and r.get("subset") == "full"]
    q_by_quality = {r["domain"]: fnum(r["mean"]) for r in scores}
    q_available = [q_by_quality[(r.get("quality_domain") or "").strip()] for r in mapping if (r.get("quality_domain") or "").strip() in q_by_quality]
    q_low, q_high = min(q_available), max(q_available)
    q_mid = sorted(q_available)[len(q_available) // 2]
    mapped = {r["mixture_domain"]: q_by_quality[(r.get("quality_domain") or "").strip()]
              for r in mapping if (r.get("quality_domain") or "").strip() in q_by_quality}
    rows_out = []
    for recipe, (rel, role) in MIXTURES.items():
        path = ROOT / "data/origin/real_attachments" / rel
        for row in read_csv(path):
            mapped_mass = 0.0
            q_raw = 0.0
            total = sum(fnum(v) for k, v in row.items() if k != "index")
            for domain, q in mapped.items():
                col = next((k for k in row if k.endswith("_" + domain)), None)
                if col:
                    p = fnum(row[col])
                    mapped_mass += p
                    q_raw += p * q
            unmapped_mass = max(0.0, total - mapped_mass)
            rows_out.append({
                "recipe": recipe,
                "role": role,
                "index": row.get("index", ""),
                "mapped_mass": mapped_mass,
                "unmapped_mass": unmapped_mass,
                "q_partial_raw": q_raw,
                "q_scenario_low": q_raw + unmapped_mass * q_low,
                "q_scenario_mid": q_raw + unmapped_mass * q_mid,
                "q_scenario_high": q_raw + unmapped_mass * q_high,
                "status": "conditional_scenario_only",
            })
    fields = list(rows_out[0])
    with (tables / "recipe_q_scenarios.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    summary = []
    for recipe, (_, role) in MIXTURES.items():
        rr = [r for r in rows_out if r["recipe"] == recipe]
        mean = lambda key: sum(float(r[key]) for r in rr) / len(rr)
        summary.append({
            "recipe": recipe,
            "role": role,
            "n_rows": len(rr),
            "mean_unmapped_mass": mean("unmapped_mass"),
            "mean_q_partial_raw": mean("q_partial_raw"),
            "mean_q_low": mean("q_scenario_low"),
            "mean_q_mid": mean("q_scenario_mid"),
            "mean_q_high": mean("q_scenario_high"),
            "mean_interval_width": mean("q_scenario_high") - mean("q_scenario_low"),
        })
    with (tables / "recipe_q_scenario_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    metrics = {
        "run_id": "q2-m2-sensitivity-20250925-r01",
        "status": "CONDITIONAL_SCENARIO_ONLY",
        "candidate_score_source": "q1-critic-topsis-20260924-r01",
        "candidate_score_status": "LOCAL_RESULT_PENDING_TEAM_REVIEW",
        "q1_candidate_range_used_only_for_sensitivity": {"low": q_low, "mid": q_mid, "high": q_high},
        "mapped_domain_count": len(mapped),
        "unmapped_domain_count": 17 - len(mapped),
        "no_b_q_scale_conversion": True,
        "no_b_model_fit": True,
        "no_official_q": True,
        "source_sha256": {
            "domain_mapping_guide.csv": sha256(mapping_path),
            "q1_domain_scores.csv": sha256(score_path),
            **{name + ".mixture.csv": sha256(ROOT / "data/origin/real_attachments" / rel) for name, (rel, _) in MIXTURES.items()},
        },
        "summary": summary,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Q2 M2 conditional bridge sensitivity\n\n"
        "The low/mid/high scenarios assign the observed review-blocked Q1 candidate range to unmapped mixture mass. They are an uncertainty envelope in the candidate Q1 score scale, not an imputed quality score, and are not converted to B6's Q_score or used in a B fit.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "range": metrics["q1_candidate_range_used_only_for_sensitivity"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
