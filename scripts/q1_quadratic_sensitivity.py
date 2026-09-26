"""Coordinate and zero-replacement sensitivity for Q1 quadratic candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from q1_model_benchmark import FEATURE_TABLE, PAIRS, SOURCE, load_data, metrics
from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-quadratic-sensitivity-20260925-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
ALPHAS = [0.1, 1.0, 10.0, 100.0]
SEEDS = [20260924, 20260925, 20260926]


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


def make_model(kind: str, alpha: float):
    if kind == "linear_ridge":
        return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
    if kind == "quadratic_ridge":
        return Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=alpha)),
        ])
    raise ValueError(kind)


def build_representation(p_by_dataset: dict[str, np.ndarray], representation: str, epsilon: float | None) -> dict[str, np.ndarray]:
    if representation == "reference_drop_last":
        return {name: p[:, :-1] for name, p in p_by_dataset.items()}
    basis = helmert_basis(p_by_dataset[next(iter(p_by_dataset))].shape[1])
    return {name: zero_replaced_clr(p, float(epsilon)) @ basis.T for name, p in p_by_dataset.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    p_by_dataset, y_by_dataset, component_names, target_names = load_data()
    rows: list[dict] = []
    candidates = [
        ("reference_drop_last", None),
        ("Helmert-ilr", 1.0e-6),
        ("Helmert-ilr", 1.0e-4),
        ("Helmert-ilr", 1.0e-3),
    ]
    for representation, epsilon in candidates:
        x_by_dataset = build_representation(p_by_dataset, representation, epsilon)
        x_fit = x_by_dataset["A4_A5_train_1m"]
        y_fit = y_by_dataset["A4_A5_train_1m"]
        for kind in ["linear_ridge", "quadratic_ridge"]:
            for alpha in ALPHAS:
                fold_metrics = []
                for seed in SEEDS:
                    splitter = KFold(n_splits=5, shuffle=True, random_state=seed)
                    for train_idx, valid_idx in splitter.split(x_fit):
                        estimator = make_model(kind, alpha)
                        estimator.fit(x_fit[train_idx], y_fit[train_idx])
                        fold_metrics.append(metrics(y_fit[valid_idx], estimator.predict(x_fit[valid_idx])))
                cv_r2 = np.array([m["mean_target_r2"] for m in fold_metrics], dtype=float)
                rows.append({
                    "representation": representation,
                    "epsilon": epsilon,
                    "model": kind,
                    "alpha": alpha,
                    "cv_mean_target_r2": float(cv_r2.mean()),
                    "cv_sd_target_r2": float(cv_r2.std(ddof=1)),
                    "cv_mean_mae": float(np.mean([m["mae"] for m in fold_metrics])),
                })

    summary = pd.DataFrame(rows)
    selected_rows = []
    evaluations = {}
    for (representation, epsilon, kind), group in summary.groupby(["representation", "epsilon", "model"], dropna=False):
        selected = group.sort_values(["cv_mean_target_r2", "cv_mean_mae"], ascending=[False, True]).iloc[0]
        selected_rows.append(selected.to_dict())
        x_by_dataset = build_representation(p_by_dataset, representation, epsilon)
        estimator = make_model(kind, float(selected["alpha"]))
        estimator.fit(x_by_dataset["A4_A5_train_1m"], y_by_dataset["A4_A5_train_1m"])
        for dataset in ["A6_A7_validation_1m", "A8_A9_validation_60m"]:
            evaluations[f"{representation}::{epsilon}::{kind}::{dataset}"] = {
                "representation": representation,
                "epsilon": epsilon,
                "model": kind,
                "alpha": float(selected["alpha"]),
                "dataset": dataset,
                "role": PAIRS[dataset][1],
                **metrics(y_by_dataset[dataset], estimator.predict(x_by_dataset[dataset])),
            }

    # Select the principal candidate using A4/A5 CV only, then estimate an
    # external A6/A7 bootstrap interval with the frozen candidate.
    selected_frame = pd.DataFrame(selected_rows)
    principal = selected_frame.sort_values(["cv_mean_target_r2", "cv_mean_mae"], ascending=[False, True]).iloc[0]
    principal_representation = principal["representation"]
    principal_epsilon = None if pd.isna(principal["epsilon"]) else float(principal["epsilon"])
    principal_kind = principal["model"]
    principal_alpha = float(principal["alpha"])
    principal_x = build_representation(p_by_dataset, principal_representation, principal_epsilon)
    principal_estimator = make_model(principal_kind, principal_alpha)
    principal_x_fit = principal_x["A4_A5_train_1m"]
    principal_y_fit = y_by_dataset["A4_A5_train_1m"]
    bootstrap_rng = np.random.default_rng(20260925)
    bootstrap_values = []
    for _ in range(100):
        indices = bootstrap_rng.integers(0, len(principal_x_fit), size=len(principal_x_fit))
        candidate_estimator = make_model(principal_kind, principal_alpha)
        candidate_estimator.fit(principal_x_fit[indices], principal_y_fit[indices])
        bootstrap_values.append(metrics(
            y_by_dataset["A6_A7_validation_1m"],
            candidate_estimator.predict(principal_x["A6_A7_validation_1m"]),
        )["mean_target_r2"])
    bootstrap_values = np.asarray(bootstrap_values, dtype=float)

    summary.to_csv(output_dir / "candidate_summary.csv", index=False, encoding="utf-8-sig")
    selected_frame.to_csv(output_dir / "selected_summary.csv", index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.quadratic-sensitivity.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "EXPERIMENTAL_REVIEW",
        "fit_rule": "A4/A5 only; repeated three-seed five-fold CV selects alpha",
        "external_validation": "A6/A7",
        "cross_scale_diagnostic": "A8/A9",
        "feature_table": {"path": FEATURE_TABLE.relative_to(ROOT).as_posix(), "sha256": sha256(FEATURE_TABLE)},
        "representations": ["reference_drop_last", "Helmert-ilr epsilon=1e-6/1e-4/1e-3"],
        "evaluations": evaluations,
        "principal_candidate": {
            "representation": principal_representation,
            "epsilon": principal_epsilon,
            "model": principal_kind,
            "alpha": principal_alpha,
            "selection_rule": "maximum repeated A4/A5 CV mean target R2 across representation, model and alpha candidates",
            "A6_bootstrap_mean_target_r2": float(bootstrap_values.mean()),
            "A6_bootstrap_sd": float(bootstrap_values.std(ddof=1)),
            "A6_bootstrap_ci95": [float(np.quantile(bootstrap_values, 0.025)), float(np.quantile(bootstrap_values, 0.975))],
        },
        "outputs": {
            "candidate_summary": (output_dir / "candidate_summary.csv").relative_to(ROOT).as_posix(),
            "selected_summary": (output_dir / "selected_summary.csv").relative_to(ROOT).as_posix(),
        },
        "limitations": [
            "Sensitivity results do not establish a coordinate-invariant interaction mechanism.",
            "A8/A9 remains a cross-scale diagnostic and is not a scale-generalization success test.",
            "No quality score Q, causal effect or optimum mixture is included.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs" / "q1-quadratic-sensitivity.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "selected_rows": len(selected_rows), "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
