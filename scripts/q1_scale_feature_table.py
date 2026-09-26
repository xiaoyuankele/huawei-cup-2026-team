"""Create auditable scale and per-domain token-count tables for Q1 A4-A15.

The source mixture attachments are read only.  The derived token counts are
expected counts (total scale multiplied by the normalized domain proportion),
so they may be fractional when the input proportions are fractional.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-scale-feature-table-20260924-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID

DATASETS = {
    "A4_A5_train_1m": {"file": "train_mixture_1m.csv", "role": "fit", "scale_label": "1M", "scale_tokens": 1_000_000},
    "A6_A7_validation_1m": {"file": "test_mixture_1m.csv", "role": "validation", "scale_label": "1M", "scale_tokens": 1_000_000},
    "A8_A9_validation_60m": {"file": "test_mixture_60m.csv", "role": "validation", "scale_label": "60M", "scale_tokens": 60_000_000},
    "A10_A11_validation_1b": {"file": "test_mixture_1B.csv", "role": "validation", "scale_label": "1B", "scale_tokens": 1_000_000_000},
    "A12_A13_extrapolation_10b": {"file": "est_mixture_10b.csv", "role": "extrapolation", "scale_label": "10B", "scale_tokens": 10_000_000_000},
    "A14_A15_extrapolation_70b": {"file": "est_mixture_70b.csv", "role": "extrapolation", "scale_label": "70B", "scale_tokens": 70_000_000_000},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    wide_rows: list[dict] = []
    long_rows: list[dict] = []
    source_records: dict = {}
    component_names: list[str] | None = None
    for dataset, metadata in DATASETS.items():
        source_path = SOURCE / metadata["file"]
        frame = pd.read_csv(source_path)
        if "index" not in frame.columns:
            raise ValueError(f"missing index column: {source_path}")
        components = [column for column in frame.columns if column != "index"]
        if component_names is None:
            component_names = components
        elif components != component_names:
            raise ValueError(f"component columns differ: {source_path}")
        p_raw = frame[components].astype(float)
        row_sums = p_raw.sum(axis=1)
        if (row_sums <= 0).any():
            raise ValueError(f"non-positive mixture sum: {source_path}")
        p = p_raw.div(row_sums, axis=0)
        scale_tokens = int(metadata["scale_tokens"])
        log10_scale = math.log10(scale_tokens)
        token_counts = p * scale_tokens
        for row_index, index_value in enumerate(frame["index"]):
            wide = {
                "dataset": dataset,
                "role": metadata["role"],
                "scale_label": metadata["scale_label"],
                "total_scale_tokens": scale_tokens,
                "log10_scale": log10_scale,
                "index": index_value,
                "original_mixture_sum": float(row_sums.iloc[row_index]),
            }
            for component in components:
                wide[f"p_{component}"] = float(p.iloc[row_index][component])
                wide[f"tokens_{component}"] = float(token_counts.iloc[row_index][component])
                long_rows.append({
                    "dataset": dataset,
                    "role": metadata["role"],
                    "scale_label": metadata["scale_label"],
                    "total_scale_tokens": scale_tokens,
                    "log10_scale": log10_scale,
                    "index": index_value,
                    "domain": component,
                    "proportion": float(p.iloc[row_index][component]),
                    "expected_tokens": float(token_counts.iloc[row_index][component]),
                })
            wide_rows.append(wide)
        source_records[dataset] = {
            "relative_path": source_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(source_path),
            "rows": int(len(frame)),
            "original_sum_min": float(row_sums.min()),
            "original_sum_max": float(row_sums.max()),
            "normalized_sum_max_abs_deviation": float((p.sum(axis=1) - 1.0).abs().max()),
            "scale_label": metadata["scale_label"],
            "scale_tokens": scale_tokens,
        }
    wide = pd.DataFrame(wide_rows)
    long = pd.DataFrame(long_rows)
    return wide, long, {"component_names": component_names, "source_records": source_records}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    wide, long, metadata = build_tables()
    wide_path = output_dir / "q1_scale_features_wide.csv"
    long_path = output_dir / "q1_scale_features_long.csv"
    wide.to_csv(wide_path, index=False, encoding="utf-8-sig")
    long.to_csv(long_path, index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.scale-feature-table.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "source_root": "data/origin/real_attachments/A_data_value/regmix_tables",
        "derived_outputs": {
            "wide_table": wide_path.relative_to(ROOT).as_posix(),
            "long_table": long_path.relative_to(ROOT).as_posix(),
            "wide_sha256": sha256(wide_path),
            "long_sha256": sha256(long_path),
        },
        "rows": {"wide": int(len(wide)), "long": int(len(long))},
        "domains": metadata["component_names"],
        "scale_levels": sorted({metadata["scale_label"] for metadata in DATASETS.values()}, key=lambda value: math.log10(next(item["scale_tokens"] for item in DATASETS.values() if item["scale_label"] == value))),
        "source_records": metadata["source_records"],
        "calculation": "p_normalized = p_raw / row_sum; expected_tokens_domain = p_normalized_domain * total_scale_tokens; log10_scale = log10(total_scale_tokens)",
        "interpretation_limits": [
            "Per-domain token counts are expected allocations, not independently observed integer token counts.",
            "Scale labels are fixed from the Q1 data contract; this run does not infer or validate training-process metadata such as epochs, steps, deduplication, or model size.",
            "The derived table is an input feature artifact and does not fit a Loss model or change A4-A15 data roles.",
            "Original attachments remain read-only and are not copied into the run directory.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
