"""Simplex-preserving finite-perturbation stability audit for Q1 mixture models."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from q1_model_benchmark import PAIRS, FEATURE_TABLE, SOURCE, EPSILON, load_data, make_model
from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-effect-stability-20260924-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
DELTA = 0.01
BOOTSTRAP_REPLICATES = 300
SEED = 20260924


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def transform(p: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return zero_replaced_clr(p, EPSILON) @ basis.T


def bootstrap_mean(values: np.ndarray, rng: np.random.Generator, replicates: int) -> tuple[float, float, float]:
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    samples = rng.integers(0, len(values), size=(replicates, len(values)))
    means = values[samples].mean(axis=1)
    return float(values.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    x_by_dataset, y_by_dataset, component_names, target_names = load_data()
    feature_table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in feature_table.columns if column.startswith("p_")]
    p_by_dataset = {}
    for dataset in PAIRS:
        p_by_dataset[dataset] = feature_table[feature_table["dataset"] == dataset].sort_values("index")[p_columns].to_numpy(dtype=float)
    basis = helmert_basis(len(component_names))
    x_transformed = {dataset: transform(p, basis) for dataset, p in p_by_dataset.items()}

    model_specs = {"ilr_ridge": 10.0, "quadratic_ridge": 10.0}
    fitted = {}
    for name, parameter in model_specs.items():
        estimator = make_model(name, parameter)
        estimator.fit(x_transformed["A4_A5_train_1m"], y_by_dataset["A4_A5_train_1m"])
        fitted[name] = estimator

    a4 = p_by_dataset["A4_A5_train_1m"]
    a6 = p_by_dataset["A6_A7_validation_1m"]
    lower = a4.min(axis=0)
    upper = a4.max(axis=0)
    rng = np.random.default_rng(SEED)
    effect_rows: list[dict] = []
    direction_rows: list[dict] = []

    for model_name, estimator in fitted.items():
        for dataset, p_matrix in [("A4_A5_train_1m", a4), ("A6_A7_validation_1m", a6)]:
            for destination in range(len(component_names)):
                for source in range(len(component_names)):
                    if destination == source:
                        continue
                    values_by_target = [[] for _ in target_names]
                    valid_count = 0
                    for p in p_matrix:
                        candidate = p.copy()
                        candidate[destination] += DELTA
                        candidate[source] -= DELTA
                        if candidate.min() < -1e-10:
                            continue
                        candidate[np.abs(candidate) < 1e-12] = 0.0
                        candidate = candidate / candidate.sum()
                        if candidate[source] < lower[source] - 1e-12 or candidate[source] > upper[source] + 1e-12:
                            continue
                        if candidate[destination] < lower[destination] - 1e-12 or candidate[destination] > upper[destination] + 1e-12:
                            continue
                        base_pred = estimator.predict(transform(p[None, :], basis))[0]
                        perturbed_pred = estimator.predict(transform(candidate[None, :], basis))[0]
                        effect = perturbed_pred - base_pred
                        valid_count += 1
                        for target_index, value in enumerate(effect):
                            values_by_target[target_index].append(float(value))
                    for target_index, target in enumerate(target_names):
                        values = np.asarray(values_by_target[target_index], dtype=float)
                        mean_value, ci_low, ci_high = bootstrap_mean(values, rng, BOOTSTRAP_REPLICATES)
                        effect_rows.append({
                            "model": model_name,
                            "dataset": dataset,
                            "destination": component_names[destination],
                            "source": component_names[source],
                            "delta": DELTA,
                            "target": target,
                            "valid_rows": int(valid_count),
                            "mean_effect": mean_value,
                            "bootstrap_ci_low": ci_low,
                            "bootstrap_ci_high": ci_high,
                        })

    effects = pd.DataFrame(effect_rows)
    for dataset in ["A4_A5_train_1m", "A6_A7_validation_1m"]:
        for target in target_names:
            q = effects[(effects["dataset"] == dataset) & (effects["target"] == target)]
            for model_name in model_specs:
                signs = q[q["model"] == model_name]["mean_effect"].to_numpy()
                direction_rows.append({
                    "dataset": dataset,
                    "target": target,
                    "model": model_name,
                    "positive_fraction": float(np.mean(signs > 0)) if len(signs) else float("nan"),
                    "negative_fraction": float(np.mean(signs < 0)) if len(signs) else float("nan"),
                    "near_zero_fraction": float(np.mean(np.isclose(signs, 0.0, atol=1e-6))) if len(signs) else float("nan"),
                })
            left = q[q["model"] == "ilr_ridge"].set_index(["destination", "source"])["mean_effect"]
            right = q[q["model"] == "quadratic_ridge"].set_index(["destination", "source"])["mean_effect"]
            common = left.index.intersection(right.index)
            if len(common):
                direction_rows.append({
                    "dataset": dataset,
                    "target": target,
                    "model": "ridge_vs_quadratic",
                    "sign_agreement_fraction": float(np.mean(np.sign(left.loc[common]) == np.sign(right.loc[common]))),
                    "pair_count": int(len(common)),
                })

    effects.to_csv(output_dir / "finite_effects.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(direction_rows).to_csv(output_dir / "effect_direction_summary.csv", index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.effect-stability.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "EXPERIMENTAL_REVIEW",
        "fit_rule": "models fitted on A4/A5 with fixed selected parameters from q1-model-benchmark-20260924-r01",
        "external_input_check": "A6/A7 predictions only; no refitting",
        "basis": {"name": "Helmert ilr", "zero_replacement": "multiplicative", "epsilon": EPSILON, "component_names": component_names},
        "perturbation": {"definition": "transfer delta from source to destination", "delta": DELTA, "support_guard": "A4 marginal coordinate ranges"},
        "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": SEED},
        "outputs": {
            "finite_effects": {"path": (output_dir / "finite_effects.csv").relative_to(ROOT).as_posix(), "rows": int(len(effects))},
            "effect_direction_summary": {"path": (output_dir / "effect_direction_summary.csv").relative_to(ROOT).as_posix(), "rows": int(len(direction_rows))},
        },
        "limitations": [
            "Finite perturbations are predictive model effects, not causal interventions.",
            "Support guard uses marginal A4 ranges and is not a convex-hull guarantee.",
            "Quadratic interaction interpretation remains exploratory until sign stability and external behavior are reviewed.",
            "Quality score Q is excluded because domain q_i is not frozen.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs" / "q1-effect-stability.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "effects": len(effects), "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
