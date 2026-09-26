"""Read-only audit of the Q1 quality-score -> Q2 mixture interface.

This script deliberately consumes only the review-blocked Q1 candidate domain
scores.  It never creates an official scalar Q and never imputes scores for
unmapped domains.  The partial/renormalized values are diagnostics only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIXTURES = {
    "A4_A5_train_1m": ("A4", "A_data_value/regmix_tables/train_mixture_1m.csv", "fit"),
    "A6_A7_validation_1m": ("A6", "A_data_value/regmix_tables/test_mixture_1m.csv", "validation"),
    "A8_A9_validation_60m": ("A8", "A_data_value/regmix_tables/test_mixture_60m.csv", "validation"),
    "A10_A11_validation_1b": ("A10", "A_data_value/regmix_tables/test_mixture_1B.csv", "validation"),
    "A12_A13_extrapolation_10b": ("A12", "A_data_value/regmix_tables/est_mixture_10b.csv", "extrapolation"),
    "A14_A15_extrapolation_70b": ("A14", "A_data_value/regmix_tables/est_mixture_70b.csv", "extrapolation"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            text = raw.decode(encoding)
            return list(csv.DictReader(text.splitlines()))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", raw, 0, 1, f"cannot decode {path}")


def fnum(value: str) -> float:
    return float(value.strip()) if value is not None and value.strip() else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-bridge-interface-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    tables = out / "tables"
    tables.mkdir(exist_ok=True)

    mapping_path = ROOT / "data/origin/real_attachments/A_data_value/domain_mapping_guide.csv"
    score_path = ROOT / "experiments/runs/q1-critic-topsis-20260924-r01/tables/domain_scores.csv"
    q1_manifest = ROOT / "experiments/runs/q1-critic-topsis-20260924-r01/run_manifest.json"
    mapping_rows = [r for r in read_csv(mapping_path) if r.get("mixture_domain")]
    score_rows = [r for r in read_csv(score_path) if r.get("dataset_id") == "A1" and r.get("subset") == "full"]
    q_by_domain = {r["domain"]: fnum(r["mean"]) for r in score_rows}

    interface_rows = []
    for r in mapping_rows:
        qdomain = (r.get("quality_domain") or "").strip()
        has_q = qdomain in q_by_domain
        mapping_type = (r.get("mapping_type") or "").strip()
        status = "candidate_available" if has_q else "missing_candidate"
        interface_rows.append(
            {
                "mixture_domain": r["mixture_domain"],
                "quality_domain": qdomain,
                "mapping_type": mapping_type,
                "candidate_q1_mean": f"{q_by_domain[qdomain]:.12g}" if has_q else "",
                "coverage_status": status,
                "note": r.get("note", ""),
            }
        )
    with (tables / "domain_mapping_with_candidate_q.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(interface_rows[0]))
        w.writeheader()
        w.writerows(interface_rows)

    # Use only the explicitly mapped domains.  Keep raw and coverage-normalized
    # diagnostics separate so missing inferred domains are never silently zeroed.
    mapped_domains = {r["mixture_domain"]: q_by_domain[(r.get("quality_domain") or "").strip()]
                      for r in mapping_rows if (r.get("quality_domain") or "").strip() in q_by_domain}
    recipe_summary = []
    recipe_detail_fields = ["recipe", "file", "role", "n_rows", "mean_total_mass", "min_mapped_mass",
                            "mean_mapped_mass", "max_mapped_mass", "mean_unmapped_mass", "mean_q_partial_raw",
                            "mean_q_partial_renorm", "p99_unmapped_mass", "status"]
    for recipe, (dataset_id, rel, role) in MIXTURES.items():
        path = ROOT / "data/origin/real_attachments" / rel
        rows = read_csv(path)
        details = []
        for row in rows:
            total = sum(fnum(v) for k, v in row.items() if k != "index")
            mapped_mass = 0.0
            q_raw = 0.0
            for domain, q in mapped_domains.items():
                col = next((k for k in row if k.endswith("_" + domain)), None)
                if col is not None:
                    p = fnum(row[col])
                    mapped_mass += p
                    q_raw += p * q
            details.append((total, mapped_mass, q_raw))
        details.sort(key=lambda x: x[0] - x[1])
        n = len(details)
        unmapped = [t - m for t, m, _ in details]
        renorm = [q / m if m > 0 else None for _, m, q in details]
        valid_renorm = [x for x in renorm if x is not None]
        mean = lambda xs: sum(xs) / len(xs) if xs else None
        recipe_summary.append({
            "recipe": recipe,
            "file": rel,
            "role": role,
            "n_rows": n,
            "mean_total_mass": mean([x[0] for x in details]),
            "min_mapped_mass": min((x[1] for x in details), default=None),
            "mean_mapped_mass": mean([x[1] for x in details]),
            "max_mapped_mass": max((x[1] for x in details), default=None),
            "mean_unmapped_mass": mean(unmapped),
            "mean_q_partial_raw": mean([x[2] for x in details]),
            "mean_q_partial_renorm": mean(valid_renorm),
            "p99_unmapped_mass": sorted(unmapped)[min(n - 1, int(0.99 * n))] if n else None,
            "status": "diagnostic_only_partial_q",
        })
    with (tables / "recipe_partial_q_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=recipe_detail_fields)
        w.writeheader()
        for row in recipe_summary:
            w.writerow(row)

    direct = sum(r["mapping_type"] == "direct" for r in interface_rows)
    near = sum(r["mapping_type"] == "near_direct" for r in interface_rows)
    inferred = sum(r["mapping_type"] == "inferred" for r in interface_rows)
    score_available = sum(r["coverage_status"] == "candidate_available" for r in interface_rows)
    manifest = json.loads(q1_manifest.read_text(encoding="utf-8"))
    metrics = {
        "run_id": "q2-bridge-interface-20250925-r01",
        "status": "BLOCKED_CONDITIONAL_INTERFACE",
        "purpose": "Audit whether review-blocked Q1 domain candidates can be used as a conditional bridge to Q2 mixtures.",
        "candidate_score_source": "q1-critic-topsis-20260924-r01",
        "candidate_score_status": manifest.get("status"),
        "mapping_counts": {"total": len(interface_rows), "direct": direct, "near_direct": near, "inferred": inferred,
                            "candidate_available": score_available, "candidate_coverage_fraction": score_available / len(interface_rows)},
        "blocking_reasons": [
            "Q1 candidate scalar/domain scores remain pending team review and are not accepted quality truth.",
            "11 inferred mixture domains have no validated quality-domain mapping or candidate score.",
            "Q2 B tables have no row-level join key to A1 records; this is a conditional domain bridge only.",
            "Q2 B8 quality direction conflict remains unresolved; B8 excluded from this interface audit.",
        ],
        "no_imputation": True,
        "no_official_q": True,
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in [mapping_path, score_path, q1_manifest] + [ROOT / "data/origin/real_attachments" / rel for _, rel, _ in MIXTURES.values()]},
        "recipe_summary": recipe_summary,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Q2 bridge interface audit\n\n"
        "This is a read-only, conditional interface audit. It joins A mixture domain names to the review-blocked Q1 A1 domain-score candidate through A16 only. `Q_partial_raw` and `Q_partial_renorm` are diagnostics; they are not an official Q, do not impute the 11 inferred domains, and do not establish an A-to-B row join.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "mapping_counts": metrics["mapping_counts"], "recipes": len(recipe_summary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
