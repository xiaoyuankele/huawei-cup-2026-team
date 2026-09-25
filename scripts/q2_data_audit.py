"""Read-only audit for problem 2 scaling-law attachments.

This script does not fit a model and never writes to the raw attachment tree.
It records schema, hashes, duplicate keys, basic unit checks, and within-cell
Q monotonicity counts for B6--B8.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median


FILES = [
    "pythia_training_log_existing.csv",
    "cerebras_training_log.csv",
    "scaling_baseline.csv",
    "published_scaling_data.csv",
    "supplementary_NQ_experiment.csv",
    "supplementary_NQ_experiment_expanded.csv",
    "supplementary_NQ_experiment_large.csv",
    "supplementary_large_models.csv",
    "supplementary_large_baseline.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def finite_float(value: str) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    """Small Gaussian elimination helper for the fixed four-term diagnostic."""
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        a[col] = [x / scale for x in a[col]]
        for row in range(n):
            if row == col:
                continue
            scale = a[row][col]
            a[row] = [x - scale * y for x, y in zip(a[row], a[col])]
    return [a[i][-1] for i in range(n)]


def summary(path: Path) -> dict:
    fields, rows = read_csv(path)
    result = {
        "rows": len(rows),
        "fields": fields,
        "sha256": sha256(path),
        "blank_cells": sum(1 for row in rows for value in row.values() if value == ""),
    }

    key = "experiment_id" if "experiment_id" in fields else (
        "model_name" if "model_name" in fields else None
    )
    if key:
        values = [row[key] for row in rows]
        result["duplicate_key_count"] = len(values) - len(set(values))

    if {"N_params_B", "D_tokens_B", "C_FLOPs_1e21"}.issubset(fields):
        errors = []
        for row in rows:
            n = finite_float(row["N_params_B"])
            d = finite_float(row["D_tokens_B"])
            c = finite_float(row["C_FLOPs_1e21"])
            if n is not None and d is not None and c is not None and n * d:
                errors.append((c - 0.006 * n * d) / (0.006 * n * d))
        if errors:
            result["compute_proxy_relative_error"] = {
                "min": min(errors),
                "median": median(errors),
                "max": max(errors),
            }

    if {"ppl", "val_loss", "train_loss"}.issubset(fields):
        ppl_errors = []
        val_minus_train = []
        for row in rows:
            ppl = finite_float(row["ppl"])
            val = finite_float(row["val_loss"])
            train = finite_float(row["train_loss"])
            if ppl and val is not None and ppl > 0:
                ppl_errors.append(math.log(ppl) - val)
            if val is not None and train is not None:
                val_minus_train.append(val - train)
        result["log_ppl_minus_val_loss"] = {
            "min": min(ppl_errors),
            "median": median(ppl_errors),
            "max": max(ppl_errors),
        }
        result["val_minus_train"] = {
            "min": min(val_minus_train),
            "median": median(val_minus_train),
            "max": max(val_minus_train),
            "negative_count": sum(x < 0 for x in val_minus_train),
        }

    if {"N_params_B", "D_tokens_B", "Q_score", "val_loss"}.issubset(fields):
        groups: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
        design: list[list[float]] = []
        target: list[float] = []
        design_by_type: dict[str, list[list[float]]] = defaultdict(list)
        target_by_type: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            n = finite_float(row["N_params_B"])
            d = finite_float(row["D_tokens_B"])
            q = finite_float(row["Q_score"])
            loss = finite_float(row["val_loss"])
            if n is not None and d is not None and q is not None and loss is not None and n > 0 and d > 0:
                data_type = row.get("data_type", "all")
                groups[(row["N_params_B"], row["D_tokens_B"], data_type)].append((q, loss))
                x = [1.0, math.log(n), math.log(d), q]
                design.append(x)
                target.append(loss)
                design_by_type[data_type].append(x)
                target_by_type[data_type].append(loss)
        positive = negative = zero = mixed = 0
        for values in groups.values():
            values.sort()
            diffs = [b - a for (_, a), (_, b) in zip(values, values[1:])]
            positive += sum(x > 1e-9 for x in diffs)
            negative += sum(x < -1e-9 for x in diffs)
            zero += sum(abs(x) <= 1e-9 for x in diffs)
            mixed += int(any(x > 1e-9 for x in diffs) and any(x < -1e-9 for x in diffs))
        result["q_monotonicity"] = {
            "groups": len(groups),
            "loss_increase_when_q_increases": positive,
            "loss_decrease_when_q_increases": negative,
            "zero_steps": zero,
            "mixed_groups": mixed,
        }
        gram = [[sum(x[i] * x[j] for x in design) for j in range(4)] for i in range(4)]
        rhs = [sum(x[i] * y for x, y in zip(design, target)) for i in range(4)]
        coefficients = solve_linear(gram, rhs)
        if coefficients is not None:
            result["conditional_diagnostic"] = {
                "formula": "val_loss ~ 1 + log(N_params_B) + log(D_tokens_B) + Q_score",
                "coefficients": {
                    "intercept": coefficients[0],
                    "log_N": coefficients[1],
                    "log_D": coefficients[2],
                    "Q": coefficients[3],
                },
                "note": "direction diagnostic only; not a final model",
            }
        by_type = {}
        for data_type, typed_design in design_by_type.items():
            typed_gram = [[sum(x[i] * x[j] for x in typed_design) for j in range(4)] for i in range(4)]
            typed_rhs = [sum(x[i] * y for x, y in zip(typed_design, target_by_type[data_type])) for i in range(4)]
            typed_coefficients = solve_linear(typed_gram, typed_rhs)
            if typed_coefficients is not None:
                by_type[data_type] = {
                    "rows": len(typed_design),
                    "Q": typed_coefficients[3],
                }
        if len(by_type) > 1:
            result["conditional_diagnostic_by_data_type"] = by_type

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = {"root": str(args.root), "files": {}, "blocking_flags": []}
    for name in FILES:
        path = args.root / name
        if not path.exists():
            report["files"][name] = {"missing": True}
        else:
            report["files"][name] = summary(path)

    b1 = report["files"].get("pythia_training_log_existing.csv", {})
    if b1.get("compute_proxy_relative_error", {}).get("max", 0) > 0.1:
        report["blocking_flags"].append("B1_compute_proxy_is_not_exact_6ND")

    b6 = report["files"].get("supplementary_NQ_experiment.csv", {}).get("conditional_diagnostic", {})
    b8_by_type = report["files"].get("supplementary_NQ_experiment_large.csv", {}).get("conditional_diagnostic_by_data_type", {})
    b6_q = b6.get("coefficients", {}).get("Q")
    b8_q = [item.get("Q") for item in b8_by_type.values() if item.get("Q") is not None]
    if b6_q is not None and b8_q and b6_q < 0 < min(b8_q):
        report["blocking_flags"].append("B8_Q_direction_conflicts_with_B6")

    manifest = args.root.parent / "source_manifest.json"
    if manifest.exists():
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        by_file = {entry.get("file"): entry for entry in entries if isinstance(entry, dict)}
        for name in ("supplementary_NQ_experiment_expanded.csv", "supplementary_NQ_experiment_large.csv"):
            entry = by_file.get(f"B_scaling_laws/{name}", {})
            if not entry.get("source") or not entry.get("note"):
                report["blocking_flags"].append(f"{name}_provenance_incomplete_in_source_manifest")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
