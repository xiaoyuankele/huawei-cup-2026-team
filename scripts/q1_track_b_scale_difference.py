"""Run Track B: paired scale-difference analysis on duplicate mixture designs.

No model is fitted.  The analysis verifies duplicate mixture inputs and
describes paired Loss differences across scales only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-track-b-scale-difference-20260924-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID

PAIRS = {
    "A6_A8_1m_vs_60m": {
        "mixture_low": "test_mixture_1m.csv",
        "loss_low": "test_pile_loss_1m.csv",
        "scale_low": "1M",
        "mixture_high": "test_mixture_60m.csv",
        "loss_high": "test_pile_loss_60m.csv",
        "scale_high": "60M",
        "role": "validation",
    },
    "A12_A14_10b_vs_70b": {
        "mixture_low": "est_mixture_10b.csv",
        "loss_low": "est_pile_loss_10b.csv",
        "scale_low": "10B",
        "mixture_high": "est_mixture_70b.csv",
        "loss_high": "est_pile_loss_70b.csv",
        "scale_high": "70B",
        "role": "extrapolation",
    },
}

SCALE_TOKENS = {"1M": 1e6, "60M": 60e6, "10B": 10e9, "70B": 70e9}


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


def read_pair(metadata: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mixture_low = pd.read_csv(SOURCE / metadata["mixture_low"])
    loss_low = pd.read_csv(SOURCE / metadata["loss_low"])
    mixture_high = pd.read_csv(SOURCE / metadata["mixture_high"])
    loss_high = pd.read_csv(SOURCE / metadata["loss_high"])
    for mixture, loss in [(mixture_low, loss_low), (mixture_high, loss_high)]:
        if not mixture["index"].equals(loss["index"]):
            raise ValueError("mixture/Loss index mismatch")
    if not mixture_low.equals(mixture_high):
        raise ValueError("paired designs are not exact duplicates")
    if not loss_low["index"].equals(loss_high["index"]):
        raise ValueError("paired target index mismatch")
    return mixture_low, loss_low, mixture_high, loss_high


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    difference_rows = []
    source_records = {}
    for pair_name, metadata in PAIRS.items():
        mixture_low, loss_low, mixture_high, loss_high = read_pair(metadata)
        target_names = [column for column in loss_low.columns if column != "index"]
        low = loss_low[target_names].to_numpy(dtype=float)
        high = loss_high[target_names].to_numpy(dtype=float)
        delta = low - high
        log_scale_gap = float(np.log10(SCALE_TOKENS[metadata["scale_high"]]) - np.log10(SCALE_TOKENS[metadata["scale_low"]]))
        mixture = mixture_low.drop(columns="index").astype(float)
        mixture = mixture.div(mixture.sum(axis=1), axis=0).to_numpy()
        ilr = zero_replaced_clr(mixture, 1e-4) @ helmert_basis(mixture.shape[1]).T
        source_records[pair_name] = {
            "mixture_low": {"path": (SOURCE / metadata["mixture_low"]).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / metadata["mixture_low"])},
            "mixture_high": {"path": (SOURCE / metadata["mixture_high"]).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / metadata["mixture_high"])},
            "loss_low": {"path": (SOURCE / metadata["loss_low"]).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / metadata["loss_low"])},
            "loss_high": {"path": (SOURCE / metadata["loss_high"]).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / metadata["loss_high"])},
            "rows": int(len(delta)),
            "target_count": int(delta.shape[1]),
        }
        for target_index, target in enumerate(target_names):
            values = delta[:, target_index]
            summary_rows.append({
                "pair": pair_name,
                "role": metadata["role"],
                "scale_low": metadata["scale_low"],
                "scale_high": metadata["scale_high"],
                "log10_scale_gap": log_scale_gap,
                "target": target,
                "mean_delta_low_minus_high": float(values.mean()),
                "mean_loss_drop_per_log10_scale": float(values.mean() / log_scale_gap),
                "delta_cv": float(values.std(ddof=1) / max(abs(values.mean()), 1e-15)),
                "max_absolute_corr_with_ilr": float(max(abs(np.corrcoef(ilr[:, coordinate], values)[0, 1]) for coordinate in range(ilr.shape[1]))),
                "median_delta_low_minus_high": float(np.median(values)),
                "sd_delta": float(values.std(ddof=1)),
                "min_delta": float(values.min()),
                "max_delta": float(values.max()),
                "positive_fraction": float(np.mean(values > 0)),
                "mean_absolute_delta": float(np.abs(values).mean()),
                "shared_prediction_mae_lower_bound": float(np.abs(values).mean() / 2.0),
                "shared_prediction_rmse_lower_bound": float(np.sqrt(np.mean(values ** 2) / 4.0)),
            })
        for row_index, index_value in enumerate(loss_low["index"]):
            for target_index, target in enumerate(target_names):
                difference_rows.append({
                    "pair": pair_name,
                    "role": metadata["role"],
                    "scale_low": metadata["scale_low"],
                    "scale_high": metadata["scale_high"],
                    "log10_scale_gap": log_scale_gap,
                    "index": index_value,
                    "target": target,
                    "loss_low": float(low[row_index, target_index]),
                    "loss_high": float(high[row_index, target_index]),
                    "delta_low_minus_high": float(delta[row_index, target_index]),
                })
    summary = pd.DataFrame(summary_rows)
    differences = pd.DataFrame(difference_rows)
    summary_path = output_dir / "scale_difference_summary.csv"
    difference_path = output_dir / "scale_differences_long.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    differences.to_csv(difference_path, index=False, encoding="utf-8-sig")
    interval_table = summary.pivot(index="target", columns="pair", values="mean_loss_drop_per_log10_scale")
    interval_consistency = {}
    if {"A6_A8_1m_vs_60m", "A12_A14_10b_vs_70b"}.issubset(interval_table.columns):
        low_interval = interval_table["A6_A8_1m_vs_60m"].to_numpy()
        high_interval = interval_table["A12_A14_10b_vs_70b"].to_numpy()
        interval_consistency = {
            "target_slope_pearson_correlation": float(np.corrcoef(low_interval, high_interval)[0, 1]),
            "mean_high_interval_to_low_interval_ratio": float(np.mean(high_interval / low_interval)),
            "low_interval_slope_min": float(np.min(low_interval)),
            "low_interval_slope_max": float(np.max(low_interval)),
            "high_interval_slope_min": float(np.min(high_interval)),
            "high_interval_slope_max": float(np.max(high_interval)),
        }
    output = {
        "schema_version": "q1.track-b-scale-difference.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "analysis": "paired low-scale minus high-scale Loss differences for exact duplicate mixture designs",
        "source_records": source_records,
        "outputs": {
            "summary": {"path": summary_path.relative_to(ROOT).as_posix(), "sha256": sha256(summary_path), "rows": int(len(summary))},
            "differences_long": {"path": difference_path.relative_to(ROOT).as_posix(), "sha256": sha256(difference_path), "rows": int(len(differences))},
        },
        "overall": {
            pair: {
                "mean_delta_low_minus_high": float(group["mean_delta_low_minus_high"].mean()),
                "mean_loss_drop_per_log10_scale": float(group["mean_loss_drop_per_log10_scale"].mean()),
                "mean_delta_cv": float(group["delta_cv"].mean()),
                "mean_max_absolute_corr_with_ilr": float(group["max_absolute_corr_with_ilr"].mean()),
                "mean_positive_fraction": float(group["positive_fraction"].mean()),
                "mean_shared_prediction_mae_lower_bound": float(group["shared_prediction_mae_lower_bound"].mean()),
                "mean_shared_prediction_rmse_lower_bound": float(group["shared_prediction_rmse_lower_bound"].mean()),
            }
            for pair, group in summary.groupby("pair")
        },
        "interval_consistency": interval_consistency,
        "limitations": [
            "No Loss model is fitted; paired differences are descriptive scale evidence only.",
            "A12/A14 are extrapolation sensitivity data, not independent validation.",
            "A positive low-minus-high difference indicates lower Loss at the higher scale for that paired target row.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
