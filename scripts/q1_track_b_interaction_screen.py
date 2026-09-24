"""Exploratory screen for scale-difference versus ilr-coordinate associations."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
RUN_ID = "q1-track-b-interaction-screen-20260924-r01"
OUTPUT_DIR = ROOT / "experiments" / "runs" / RUN_ID
BOOTSTRAP_REPS = 1000
SEED = 20260924
EPSILON = 1e-4

PAIRS = {
    "A6_A8_1m_vs_60m": ("test_mixture_1m.csv", "test_pile_loss_1m.csv", "test_pile_loss_60m.csv", "validation"),
    "A12_A14_10b_vs_70b": ("est_mixture_10b.csv", "est_pile_loss_10b.csv", "est_pile_loss_70b.csv", "extrapolation"),
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


def corr(x: np.ndarray, y: np.ndarray) -> float:
    if np.std(x) <= 1e-15 or np.std(y) <= 1e-15:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def bootstrap_corr(x: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    indices = rng.integers(0, len(y), size=(BOOTSTRAP_REPS, len(y)))
    xb = x[indices]
    yb = y[indices]
    xb = xb - xb.mean(axis=1, keepdims=True)
    yb = yb - yb.mean(axis=1, keepdims=True)
    numerator = np.sum(xb * yb, axis=1)
    denominator = np.sqrt(np.sum(xb * xb, axis=1) * np.sum(yb * yb, axis=1))
    return numerator / np.where(denominator > 1e-15, denominator, np.nan)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []
    source_records = {}
    for pair, (mixture_file, low_file, high_file, role) in PAIRS.items():
        mixture = pd.read_csv(SOURCE / mixture_file)
        low = pd.read_csv(SOURCE / low_file)
        high = pd.read_csv(SOURCE / high_file)
        if not mixture["index"].equals(low["index"]) or not low["index"].equals(high["index"]):
            raise ValueError(f"index mismatch: {pair}")
        mixture_values = mixture.drop(columns="index").astype(float)
        mixture_values = mixture_values.div(mixture_values.sum(axis=1), axis=0).to_numpy()
        ilr = zero_replaced_clr(mixture_values, EPSILON) @ helmert_basis(mixture_values.shape[1]).T
        targets = [column for column in low.columns if column != "index"]
        delta = low[targets].to_numpy(dtype=float) - high[targets].to_numpy(dtype=float)
        source_records[pair] = {
            "mixture": {"path": (SOURCE / mixture_file).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / mixture_file)},
            "low_target": {"path": (SOURCE / low_file).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / low_file)},
            "high_target": {"path": (SOURCE / high_file).relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE / high_file)},
            "rows": int(len(delta)),
        }
        for target_index, target in enumerate(targets):
            y = delta[:, target_index]
            for coordinate in range(ilr.shape[1]):
                x = ilr[:, coordinate]
                point = corr(x, y)
                sample_size = len(y)
                finite_boot = bootstrap_corr(x, y, rng)
                finite_boot = finite_boot[np.isfinite(finite_boot)]
                rows.append({
                    "pair": pair,
                    "role": role,
                    "target": target,
                    "ilr_coordinate": f"ilr_{coordinate + 1}",
                    "pearson_r": point,
                    "absolute_r": abs(point) if np.isfinite(point) else np.nan,
                    "bootstrap_ci95_low": float(np.quantile(finite_boot, 0.025)) if len(finite_boot) else np.nan,
                    "bootstrap_ci95_high": float(np.quantile(finite_boot, 0.975)) if len(finite_boot) else np.nan,
                    "bootstrap_reps": BOOTSTRAP_REPS,
                })
    result = pd.DataFrame(rows)
    output_path = OUTPUT_DIR / "interaction_screen.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    top = result.sort_values("absolute_r", ascending=False).head(20)
    output = {
        "schema_version": "q1.track-b-interaction-screen.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "zero_replacement": {"method": "multiplicative", "epsilon": EPSILON},
        "bootstrap": {"reps": BOOTSTRAP_REPS, "seed": SEED, "interval": "percentile_95"},
        "source_records": source_records,
        "output": {"path": output_path.relative_to(ROOT).as_posix(), "sha256": sha256(output_path), "rows": int(len(result))},
        "top_absolute_correlations": top.to_dict(orient="records"),
        "limitations": [
            "This is a descriptive hypothesis screen; no interaction model is fitted.",
            "The maximum over many target-coordinate pairs is selection-sensitive; bootstrap intervals are not multiplicity-adjusted.",
            "A12/A14 remain extrapolation sensitivity data and cannot be treated as independent validation.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
