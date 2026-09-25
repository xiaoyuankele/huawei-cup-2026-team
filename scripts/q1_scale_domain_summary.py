"""Summarize domain-level expected token counts from the derived scale table."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-scale-domain-summary-20260924-r01"
SOURCE_RUN = "experiments/runs/q1-scale-feature-table-20260924-r01/q1_scale_features_long.csv"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / SOURCE_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(input_path)
    required = {"dataset", "role", "scale_label", "total_scale_tokens", "log10_scale", "index", "domain", "proportion", "expected_tokens"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"derived table missing columns: {sorted(missing)}")
    grouped = (
        frame.groupby(["dataset", "role", "scale_label", "total_scale_tokens", "log10_scale", "domain"], as_index=False)
        .agg(
            records=("index", "size"),
            proportion_mean=("proportion", "mean"),
            proportion_median=("proportion", "median"),
            proportion_p05=("proportion", lambda values: values.quantile(0.05)),
            proportion_p95=("proportion", lambda values: values.quantile(0.95)),
            proportion_zero_fraction=("proportion", lambda values: float((values == 0).mean())),
            expected_tokens_mean=("expected_tokens", "mean"),
            expected_tokens_median=("expected_tokens", "median"),
            expected_tokens_min=("expected_tokens", "min"),
            expected_tokens_max=("expected_tokens", "max"),
        )
    )
    grouped = grouped.sort_values(["total_scale_tokens", "dataset", "domain"]).reset_index(drop=True)
    output_path = output_dir / "q1_scale_domain_summary.csv"
    grouped.to_csv(output_path, index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.scale-domain-summary.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "input": {"path": input_path.relative_to(ROOT).as_posix(), "sha256": sha256(input_path), "rows": int(len(frame))},
        "output": {"path": output_path.relative_to(ROOT).as_posix(), "sha256": sha256(output_path), "rows": int(len(grouped))},
        "grouping": ["dataset", "role", "scale_label", "total_scale_tokens", "log10_scale", "domain"],
        "interpretation_limits": [
            "Expected token counts are derived allocations from proportions and total scale, not independently observed integer counts.",
            "The summary describes input support only and does not use Loss targets or estimate scale effects.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
