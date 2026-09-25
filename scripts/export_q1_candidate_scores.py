"""Export only the Q1.2 candidate scores from the private per-record results.

The private input contains diagnostic fields that are deliberately excluded from
the public score table. This script validates IDs and score bounds while writing
one deterministic UTF-8 CSV and a provenance manifest.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path


FIELDS = ("id", "dataset", "domain", "Q_candidate", "score_status")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export(source: Path, target: Path, manifest: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    by_dataset: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    minimum, maximum = 100.0, 0.0

    with gzip.open(source, "rt", encoding="utf-8", newline="") as input_stream:
        reader = csv.DictReader(input_stream)
        if not set(FIELDS).issubset(reader.fieldnames or ()):
            raise ValueError("Source is missing required score columns")
        with target.open("w", encoding="utf-8", newline="") as output_stream:
            writer = csv.DictWriter(output_stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            for row in reader:
                record_id = row["id"]
                if not record_id or record_id in seen:
                    raise ValueError("Missing or repeated record ID")
                seen.add(record_id)
                score = float(row["Q_candidate"])
                if not 0 <= score <= 100:
                    raise ValueError(f"Out-of-range score for {record_id}")
                if not row["dataset"] or not row["domain"] or not row["score_status"]:
                    raise ValueError(f"Missing public field for {record_id}")
                writer.writerow({field: row[field] for field in FIELDS})
                by_dataset[row["dataset"]] += 1
                statuses[row["score_status"]] += 1
                minimum = min(minimum, score)
                maximum = max(maximum, score)

    if not seen:
        raise ValueError("Source contains no records")
    metadata = {
        "schema": "q1-candidate-score-export.v1",
        "run_id": "q1-conflict-trial-20260924-r01",
        "source": "private artifacts/sample_results.csv.gz",
        "source_sha256": sha256(source),
        "public_file": target.name,
        "public_sha256": sha256(target),
        "rows": len(seen),
        "columns": list(FIELDS),
        "dataset_counts": dict(sorted(by_dataset.items())),
        "score_status_counts": dict(sorted(statuses.items())),
        "score_min": minimum,
        "score_max": maximum,
        "interpretation": "Exploratory candidate scores; not a validated replacement for Q1.1 scores.",
    }
    manifest.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(export(arguments.source, arguments.output, arguments.manifest), ensure_ascii=False, indent=2))
