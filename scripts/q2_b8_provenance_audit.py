"""Read-only provenance and direction audit for the B8 supplementary table."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROOT = ROOT / "data/origin/real_attachments/B_scaling_laws"
MANIFEST = ROOT / "data/origin/real_attachments/source_manifest.json"
NAMES = {
    "B6": "supplementary_NQ_experiment.csv",
    "B7": "supplementary_NQ_experiment_expanded.csv",
    "B8": "supplementary_NQ_experiment_large.csv",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def f(v: str) -> float:
    return float(v)


def monotonicity(rows: list[dict[str, str]]) -> dict:
    groups: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        groups[(r["N_params_B"], r["D_tokens_B"], r.get("data_type", "all"))].append((f(r["Q_score"]), f(r["val_loss"])))
    pos = neg = zero = mixed = 0
    for vals in groups.values():
        vals.sort()
        diffs = [b - a for (_, a), (_, b) in zip(vals, vals[1:])]
        pos += sum(d > 1e-9 for d in diffs)
        neg += sum(d < -1e-9 for d in diffs)
        zero += sum(abs(d) <= 1e-9 for d in diffs)
        mixed += int(any(d > 1e-9 for d in diffs) and any(d < -1e-9 for d in diffs))
    return {"groups": len(groups), "loss_increase_when_q_increases": pos, "loss_decrease_when_q_increases": neg, "zero_steps": zero, "mixed_groups": mixed}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-b8-provenance-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for label, name in NAMES.items():
        path = BROOT / name
        fields, rows = read(path)
        files[label] = {
            "file": name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows": len(rows),
            "fields": fields,
            "data_type_counts": dict(Counter(r.get("data_type", "missing") for r in rows)),
            "q_monotonicity": monotonicity(rows),
            "q_range": [min(f(r["Q_score"]) for r in rows), max(f(r["Q_score"]) for r in rows)],
        }
    manifest_entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_file = {e.get("file"): e for e in manifest_entries if isinstance(e, dict)}
    provenance = {}
    for label, name in NAMES.items():
        e = by_file.get(f"B_scaling_laws/{name}", {})
        provenance[label] = {
            "manifest_entry_present": bool(e),
            "manifest_bytes": e.get("bytes"),
            "manifest_source": e.get("source"),
            "manifest_note": e.get("note"),
            "source_present": bool(e.get("source")),
            "note_present": bool(e.get("note")),
        }
    b6_fields, b6_rows = read(BROOT / NAMES["B6"])
    b7_fields, b7_rows = read(BROOT / NAMES["B7"])
    b6_by_id = {r["experiment_id"]: r for r in b6_rows}
    b7_by_id = {r["experiment_id"]: r for r in b7_rows}
    exact_common = 0
    for key, row in b6_by_id.items():
        if key in b7_by_id and all(b7_by_id[key].get(k) == v for k, v in row.items()):
            exact_common += 1
    b8_rows = read(BROOT / NAMES["B8"])[1]
    metrics = {
        "run_id": "q2-b8-provenance-20250925-r01",
        "status": "BLOCKED_B8_PROVENANCE_AND_DIRECTION",
        "source_manifest_sha256": sha256(MANIFEST),
        "files": files,
        "manifest_provenance": provenance,
        "nested_relation": {
            "b6_rows": len(b6_rows),
            "b7_rows": len(b7_rows),
            "b6_ids_in_b7": sum(k in b7_by_id for k in b6_by_id),
            "b6_rows_exactly_reproduced_in_b7": exact_common,
            "b7_extension_rows": len(b7_rows) - len(b6_rows),
        },
        "blocking_flags": [
            "B7_manifest_has_no_source_or_generation_note",
            "B8_manifest_has_no_source_or_generation_note",
            "B8_Q_direction_conflicts_with_B6_B7",
            "B8_calibrated_and_extrapolated_rows_require_separate_semantics",
        ],
        "required_evidence_to_unlock": [
            "B8 generator or reproducible construction formula and version",
            "quality-score definition and direction for calibrated and extrapolated subsets",
            "data_type split rule and calibration/extrapolation provenance",
            "independent review that does not infer missing metadata from Loss behavior",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# B8 provenance audit\n\n"
        "Read-only audit of B6/B7/B8 hashes, manifest provenance, nested relation, data_type partition, and within-cell Q direction. B8 is not repaired, reversed, filtered, or fitted.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "b6_exact_in_b7": exact_common, "b8_types": files["B8"]["data_type_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
