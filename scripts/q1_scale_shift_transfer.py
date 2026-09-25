"""Transfer a paired scale shift learned at 1M->60M to 10B->70B."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/origin/real_attachments/A_data_value/regmix_tables"
RUN_ID = "q1-scale-shift-transfer-20260925-r01"
DEFAULT_OUTPUT = ROOT / "experiments/runs" / RUN_ID
PAIRS = {
    "calibration": ("test_mixture_1m.csv", "test_pile_loss_1m.csv", "test_mixture_60m.csv", "test_pile_loss_60m.csv", 1e6, 60e6),
    "evaluation": ("est_mixture_10b.csv", "est_pile_loss_10b.csv", "est_mixture_70b.csv", "est_pile_loss_70b.csv", 10e9, 70e9),
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


def read_pair(spec: tuple[str, str, str, str, float, float]) -> dict:
    mix_low_name, loss_low_name, mix_high_name, loss_high_name, scale_low, scale_high = spec
    mix_low = pd.read_csv(SOURCE / mix_low_name)
    mix_high = pd.read_csv(SOURCE / mix_high_name)
    loss_low = pd.read_csv(SOURCE / loss_low_name)
    loss_high = pd.read_csv(SOURCE / loss_high_name)
    if not mix_low.equals(mix_high):
        raise ValueError(f"mixture design mismatch: {mix_low_name} vs {mix_high_name}")
    if not loss_low["index"].equals(loss_high["index"]):
        raise ValueError("Loss index mismatch")
    targets = [c for c in loss_low.columns if c != "index"]
    return {
        "mix_low": mix_low,
        "mix_high": mix_high,
        "loss_low": loss_low[targets].to_numpy(dtype=float),
        "loss_high": loss_high[targets].to_numpy(dtype=float),
        "targets": targets,
        "gap": float(np.log10(scale_high) - np.log10(scale_low)),
        "files": (mix_low_name, loss_low_name, mix_high_name, loss_high_name),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    calibration = read_pair(PAIRS["calibration"])
    evaluation = read_pair(PAIRS["evaluation"])
    if calibration["targets"] != evaluation["targets"]:
        raise ValueError("target columns differ")
    calibration_delta = calibration["loss_low"] - calibration["loss_high"]
    evaluation_delta = evaluation["loss_low"] - evaluation["loss_high"]
    transfer_ratio = evaluation["gap"] / calibration["gap"]
    estimated_delta = calibration_delta.mean(axis=0) * transfer_ratio
    predicted_high = evaluation["loss_low"] - estimated_delta.reshape(1, -1)
    residual = evaluation["loss_high"] - predicted_high
    rows = []
    for j, target in enumerate(calibration["targets"]):
        actual = evaluation_delta[:, j]
        estimate = np.full_like(actual, estimated_delta[j])
        rows.append({
            "target": target,
            "calibration_mean_delta_1m_minus_60m": float(calibration_delta[:, j].mean()),
            "calibration_drop_per_log10_scale": float(calibration_delta[:, j].mean() / calibration["gap"]),
            "transferred_mean_delta_10b_minus_70b": float(estimated_delta[j]),
            "actual_mean_delta_10b_minus_70b": float(actual.mean()),
            "transfer_ratio_gap": transfer_ratio,
            "transfer_mae": float(np.mean(np.abs(actual - estimate))),
            "transfer_rmse": float(np.sqrt(np.mean((actual - estimate) ** 2))),
            "actual_minus_transferred_mean": float((actual - estimate).mean()),
        })
    summary = pd.DataFrame(rows)
    prediction_metrics = {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mean_absolute_actual_shift": float(np.mean(np.abs(evaluation_delta))),
        "mean_absolute_transferred_shift_error": float(np.mean(np.abs(evaluation_delta - estimated_delta.reshape(1, -1)))),
        "mean_actual_shift": float(evaluation_delta.mean()),
        "mean_transferred_shift": float(estimated_delta.mean()),
    }
    summary.to_csv(output_dir / "scale_shift_transfer_by_target.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"row": np.arange(len(residual)), "target_mean_absolute_transfer_error": np.mean(np.abs(residual), axis=1)}).to_csv(output_dir / "scale_shift_transfer_by_row.csv", index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.scale-shift-transfer.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "PAIRED_SCALE_DIAGNOSTIC",
        "calibration_pair": {"name": "A6_A8_1m_vs_60m", "gap": calibration["gap"], "rows": len(calibration_delta), "files": {str(p): {"sha256": sha256(SOURCE / p)} for p in calibration["files"]}},
        "evaluation_pair": {"name": "A12_A14_10b_vs_70b", "gap": evaluation["gap"], "rows": len(evaluation_delta), "files": {str(p): {"sha256": sha256(SOURCE / p)} for p in evaluation["files"]}},
        "transfer_ratio": transfer_ratio,
        "prediction_metrics": prediction_metrics,
        "limitations": [
            "The calibration pair supplies one observed scale interval only.",
            "A12/A14 are extrapolation diagnostics and not independent validation.",
            "The transfer is an additive target-level scale-shift diagnostic, not a fitted global scale law.",
            "Quality features are identical within each paired mixture design and cannot explain the paired scale difference.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs/q1-scale-shift-transfer.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text("# Q1 scale shift transfer\n\nA paired scale-shift diagnostic that transfers the target-level 1M->60M mean Loss drop to the 10B->70B duplicate mixture design.\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "transfer_ratio": transfer_ratio, "prediction_metrics": prediction_metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
