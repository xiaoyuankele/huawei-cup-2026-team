"""Role-change audit for whether scale and composition-derived factors are sufficient."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from q1_model_benchmark import FEATURE_TABLE, PAIRS, SOURCE, load_data, metrics
from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-factor-sufficiency-20260925-r01"
DEFAULT_OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
EPSILON = 1e-4
ALPHAS = [0.1, 1.0, 10.0, 100.0]
ADAPTATION = ["A4_A5_train_1m", "A6_A7_validation_1m", "A8_A9_validation_60m"]
HOLDOUT = ["A10_A11_validation_1b"]
DIAGNOSTIC = ["A12_A13_extrapolation_10b", "A14_A15_extrapolation_70b"]


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


def feature_blocks(table: pd.DataFrame, p_by_dataset: dict[str, np.ndarray]) -> dict[str, dict[str, np.ndarray]]:
    p_columns = [column for column in table.columns if column.startswith("p_")]
    basis = helmert_basis(len(p_columns))
    blocks: dict[str, dict[str, np.ndarray]] = {name: {} for name in [
        "p_only", "p_scale_linear", "p_scale_quadratic", "p_scale_interaction",
        "p_scale_diversity", "p_scale_diversity_interaction"
    ]}
    for dataset, p in p_by_dataset.items():
        subset = table[table["dataset"] == dataset].sort_values("index")
        z = zero_replaced_clr(p, EPSILON) @ basis.T
        scale = subset["log10_scale"].to_numpy(dtype=float).reshape(-1, 1)
        entropy = (-np.sum(np.where(p > 0, p * np.log(np.where(p > 0, p, 1.0)), 0.0), axis=1)).reshape(-1, 1)
        concentration = np.sum(p ** 2, axis=1).reshape(-1, 1)
        active_count = np.sum(p > 0, axis=1).reshape(-1, 1)
        scale_squared = scale ** 2
        blocks["p_only"][dataset] = z
        blocks["p_scale_linear"][dataset] = np.c_[z, scale]
        blocks["p_scale_quadratic"][dataset] = np.c_[z, scale, scale_squared]
        blocks["p_scale_interaction"][dataset] = np.c_[z, scale, z * scale]
        blocks["p_scale_diversity"][dataset] = np.c_[z, scale, scale_squared, entropy, concentration, active_count]
        blocks["p_scale_diversity_interaction"][dataset] = np.c_[
            z, scale, scale_squared, z * scale, entropy, concentration, active_count,
            entropy * scale, concentration * scale,
        ]
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    x_by_dataset, y_by_dataset, component_names, target_names = load_data()
    table = pd.read_csv(FEATURE_TABLE)
    p_columns = [column for column in table.columns if column.startswith("p_")]
    p_by_dataset = {dataset: table[table["dataset"] == dataset].sort_values("index")[p_columns].to_numpy(dtype=float) for dataset in PAIRS}
    blocks = feature_blocks(table, p_by_dataset)
    x_adapt_groups = np.concatenate([np.full(len(y_by_dataset[d]), d) for d in ADAPTATION])
    y_adapt = np.vstack([y_by_dataset[d] for d in ADAPTATION])
    rows = []
    evaluations = {}

    for block_name, x_by in blocks.items():
        x_adapt = np.vstack([x_by[d] for d in ADAPTATION])
        candidates = []
        for alpha in ALPHAS:
            fold_r2 = []
            logo = LeaveOneGroupOut()
            for train_idx, valid_idx in logo.split(x_adapt, y_adapt, groups=x_adapt_groups):
                model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
                model.fit(x_adapt[train_idx], y_adapt[train_idx])
                fold_r2.append(metrics(y_adapt[valid_idx], model.predict(x_adapt[valid_idx]))["mean_target_r2"])
            candidates.append({"alpha": alpha, "logo_mean_target_r2": float(np.mean(fold_r2)), "logo_sd_target_r2": float(np.std(fold_r2, ddof=1)), "fold_r2": fold_r2})
        selected = max(candidates, key=lambda item: (item["logo_mean_target_r2"], -item["logo_sd_target_r2"]))
        model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=selected["alpha"]))]).fit(x_adapt, y_adapt)
        rows.append({"block": block_name, "selected_alpha": selected["alpha"], "logo_mean_target_r2": selected["logo_mean_target_r2"], "logo_sd_target_r2": selected["logo_sd_target_r2"], "logo_fold_r2": selected["fold_r2"], "feature_count": int(x_adapt.shape[1])})
        for dataset in HOLDOUT + DIAGNOSTIC:
            evaluations[f"{block_name}::{dataset}"] = {"block": block_name, "alpha": selected["alpha"], "dataset": dataset, "role": "unseen_scale_holdout" if dataset in HOLDOUT else "extrapolation_diagnostic", **metrics(y_by_dataset[dataset], model.predict(x_by[dataset]))}

    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir / "factor_block_summary.csv", index=False, encoding="utf-8-sig")
    output = {
        "schema_version": "q1.factor-sufficiency.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "ROLE_CHANGE_EXPLORATORY",
        "role_change": "A6/A7 and A8/A9 are adaptation data; A10/A11 is unseen-scale holdout",
        "feature_table": {"path": FEATURE_TABLE.relative_to(ROOT).as_posix(), "sha256": sha256(FEATURE_TABLE)},
        "adaptation": ADAPTATION,
        "holdout": HOLDOUT,
        "diagnostic": DIAGNOSTIC,
        "feature_blocks": summary.to_dict(orient="records"),
        "evaluations": evaluations,
        "limitations": [
            "This is a role-change factor sufficiency audit, not official A6-A11 validation.",
            "Entropy, concentration and active-domain count are composition-derived descriptors, not independent observations.",
            "Quality q_i and data-processing variables are not included because they are not frozen.",
            "A12-A15 remain extrapolation diagnostics.",
        ],
    }
    (output_dir / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "config.yaml").write_text((ROOT / "configs" / "q1-factor-sufficiency.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "blocks": len(rows), "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
