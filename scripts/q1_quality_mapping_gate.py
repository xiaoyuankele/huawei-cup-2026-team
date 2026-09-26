"""Read-only gate audit for Q1 quality-score samples and the 17-domain bridge table.

The script deliberately does not alter raw attachments, score matrices, or mapping
rows.  It records whether the two requested work packages can advance to review,
and which gates still prevent formal acceptance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import lzma
import math
from collections import Counter
from pathlib import Path
from typing import Any


DATASETS = {
    "A1": "A_data_value/slimpajama_quality_signal_sample.jsonl.xz",
    "A2": "A_data_value/slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz",
    "A3": "A_data_value/slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nonfinite(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, list):
        return any(nonfinite(item) for item in value)
    if isinstance(value, dict):
        return any(nonfinite(item) for item in value.values())
    return False


def scan_jsonl_xz(path: Path) -> dict[str, Any]:
    ids: set[str] = set()
    duplicate_ids = 0
    duplicate_key_records = 0
    parse_errors = 0
    nonfinite_records = 0
    rows = 0
    domains: Counter[str] = Counter()
    fields: set[str] = set()

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        nonlocal duplicate_key_records
        names = [name for name, _ in pairs]
        if len(names) != len(set(names)):
            duplicate_key_records += 1
        return dict(pairs)

    def parse_constant(token: str) -> float:
        return float(token)

    with lzma.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                obj = json.loads(
                    line,
                    object_pairs_hook=pairs_hook,
                    parse_constant=parse_constant,
                )
            except Exception:
                parse_errors += 1
                continue
            rows += 1
            if not isinstance(obj, dict):
                continue
            fields.update(obj)
            record_id = obj.get("id")
            if isinstance(record_id, str):
                if record_id in ids:
                    duplicate_ids += 1
                ids.add(record_id)
            if isinstance(obj.get("_source_domain"), str):
                domains[obj["_source_domain"]] += 1
            if nonfinite(obj):
                nonfinite_records += 1

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "record_count": rows,
        "unique_id_count": len(ids),
        "duplicate_id_count": duplicate_ids,
        "duplicate_key_record_count": duplicate_key_records,
        "parse_error_count": parse_errors,
        "nonfinite_record_count": nonfinite_records,
        "field_count": len(fields),
        "domain_counts": dict(sorted(domains.items())),
        "ids": ids,
    }


def scan_mapping(path: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("mixture_domain"):
                rows.append(row)
    by_type = Counter(row.get("mapping_type", "") for row in rows)
    inferred = [row.get("mixture_domain", "") for row in rows if row.get("mapping_type") == "inferred"]
    unmapped = [row.get("mixture_domain", "") for row in rows if not row.get("quality_domain") or row.get("quality_domain") == "(none)"]
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "row_count": len(rows),
        "mapping_type_counts": dict(sorted(by_type.items())),
        "mapped_row_count": sum(1 for row in rows if row.get("quality_domain") and row.get("quality_domain") != "(none)"),
        "unmapped_row_count": len(unmapped),
        "inferred_domains": inferred,
        "unmapped_domains": unmapped,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out or root / "experiments/runs/q1-quality-mapping-gate-20250925-r01/metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    dataset_results = {}
    for dataset_id, relative in DATASETS.items():
        dataset_results[dataset_id] = scan_jsonl_xz(root / "data/origin/real_attachments" / relative)

    overlaps = {}
    for left, right in (("A1", "A2"), ("A1", "A3"), ("A2", "A3")):
        left_ids = dataset_results[left]["ids"]
        right_ids = dataset_results[right]["ids"]
        overlaps[f"{left}_{right}"] = {
            "intersection_count": len(left_ids & right_ids),
            "left_only_count": len(left_ids - right_ids),
            "right_only_count": len(right_ids - left_ids),
        }

    mapping = scan_mapping(root / "data/origin/real_attachments/A_data_value/domain_mapping_guide.csv")
    scoring_path = root / "data/manifests/q1_scoring_20260925.json"
    scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
    preprocessed_text = (root / "data/manifests/q1_preprocessed_20260925.yaml").read_text(encoding="utf-8")
    preprocessed_status = next((line.split(":", 1)[1].strip() for line in preprocessed_text.splitlines() if line.startswith("status:")), "unknown")
    preprocessed_run = next((line.split(":", 1)[1].strip() for line in preprocessed_text.splitlines() if line.startswith("run_id:")), "unknown")

    sample_complete = all(item["record_count"] > 0 for item in dataset_results.values())
    # Non-finite values are explicitly handled by the Q1 contract as missing
    # components that must be reported. They do not prevent entry to review;
    # parse errors, duplicate keys, or duplicate IDs do.
    raw_structurally_clean = all(
        item["parse_error_count"] == 0
        and item["duplicate_key_record_count"] == 0
        and item["duplicate_id_count"] == 0
        for item in dataset_results.values()
    )
    direct_near = mapping["mapping_type_counts"].get("direct", 0) + mapping["mapping_type_counts"].get("near_direct", 0)
    inferred_count = mapping["mapping_type_counts"].get("inferred", 0)
    metrics = {
        "schema_version": "q1.quality.mapping.gate.v1",
        "run_id": "q1-quality-mapping-gate-20250925-r01",
        "task_id": "T-Q1-004",
        "source_files": {
            "preprocessed_manifest": "data/manifests/q1_preprocessed_20260925.yaml",
            "scoring_manifest": "data/manifests/q1_scoring_20260925.json",
            "mapping_table": "data/origin/real_attachments/A_data_value/domain_mapping_guide.csv",
        },
        "preprocessed": {"status": preprocessed_status, "run_id": preprocessed_run},
        "scoring": {
            "status": scoring.get("status"),
            "primary_model": scoring.get("primary_model"),
            "primary_run_id": scoring.get("primary_run_id"),
            "record_counts": scoring.get("record_counts"),
            "n_unique": scoring.get("n_unique"),
        },
        "datasets": {
            dataset_id: {key: value for key, value in result.items() if key != "ids"}
            for dataset_id, result in dataset_results.items()
        },
        "overlap": overlaps,
        "mapping": mapping,
        "gates": {
            "step1_can_advance_to_review": sample_complete and raw_structurally_clean,
            "step1_final_q_accepted": False,
            "step1_blockers": [
                "preprocessing_manifest_status_REVIEW" if preprocessed_status != "ACCEPTED" else "",
                "scoring_pending_team_review" if scoring.get("status") != "ACCEPTED" else "",
                "pending_indicator_directions_and_no_approved_weights_or_total",
                "A2_A3_are_external_same_family_checks_not_independent_truth",
                "nonfinite_values_reported_as_missing_components",
            ],
            "step2_can_advance_direct_near_direct_review": direct_near == 6,
            "step2_full_17_domain_mapping_accepted": inferred_count == 0 and mapping["row_count"] == 17,
            "step2_blockers": [
                f"{inferred_count}_inferred_domains_without_quality_domain_evidence" if inferred_count else "",
                "mapping_table_notes_are_not_evidence-backed_per_domain",
            ],
        },
    }
    metrics["gates"]["step1_blockers"] = [item for item in metrics["gates"]["step1_blockers"] if item]
    metrics["gates"]["step2_blockers"] = [item for item in metrics["gates"]["step2_blockers"] if item]
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in metrics["gates"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
