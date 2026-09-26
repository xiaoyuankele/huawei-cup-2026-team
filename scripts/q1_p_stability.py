"""Restricted stability audit for the A-side 17-domain mixture model.

The audit fits only on A4/A5, screens only observed A4/A5 compositions, and
uses finite donor-to-receiver perturbations around the best observed row.  It
does not produce an unconstrained optimum mixture.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from q1_mixture_collinearity import helmert_basis, zero_replaced_clr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "origin" / "real_attachments" / "A_data_value" / "regmix_tables"
FEATURE_TABLE = ROOT / "experiments" / "runs" / "q1-scale-feature-table-20260924-r01" / "q1_scale_features_wide.csv"
RUN_ID = "q1-p-stability-20260925-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
EPSILONS = [1e-6, 1e-4, 1e-3]
DELTA = 0.01
TARGET_FILE = "train_pile_loss_1m.csv"
VALIDATION_FILE = "test_pile_loss_1m.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def load_pair(filename: str) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    table = pd.read_csv(FEATURE_TABLE)
    p_cols = [c for c in table.columns if c.startswith("p_")]
    subset = table[table["dataset"] == ("A4_A5_train_1m" if "train" in filename else "A6_A7_validation_1m")].sort_values("index")
    loss = pd.read_csv(SOURCE / filename).sort_values("index")
    if not np.array_equal(subset["index"].to_numpy(), loss["index"].to_numpy()):
        raise ValueError(f"index mismatch for {filename}")
    return subset, loss.drop(columns="index").to_numpy(float), p_cols


def design(p: np.ndarray, epsilon: float) -> np.ndarray:
    return zero_replaced_clr(p, epsilon) @ helmert_basis(p.shape[1]).T


def make_model(kind: str) -> object:
    if kind == "ilr_ridge":
        return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=10.0))])
    if kind == "quadratic_ridge":
        return Pipeline([("poly", PolynomialFeatures(degree=2, include_bias=False)),
                         ("scale", StandardScaler()), ("ridge", Ridge(alpha=10.0))])
    if kind == "shallow_gbdt":
        base = GradientBoostingRegressor(n_estimators=100, learning_rate=0.03,
                                         max_depth=2, min_samples_leaf=10,
                                         random_state=20260924)
        return MultiOutputRegressor(base)
    raise ValueError(kind)


def score_matrix(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = y.mean(axis=0)
    sd = y.std(axis=0, ddof=1)
    sd[sd == 0] = 1.0
    return mean, sd


def scalar_score(y: np.ndarray, mean: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return ((y - mean) / sd).mean(axis=1)


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    train, y_train, p_cols = load_pair(TARGET_FILE)
    valid, y_valid, valid_cols = load_pair(VALIDATION_FILE)
    if p_cols != valid_cols:
        raise ValueError("composition columns differ")
    p_train = train[p_cols].to_numpy(float)
    p_valid = valid[p_cols].to_numpy(float)
    if not np.allclose(p_train.sum(axis=1), 1.0, atol=1e-8):
        raise ValueError("A4/A5 composition rows are not normalized")
    y_mean, y_sd = score_matrix(y_train)
    empirical_idx = int(np.argmin(scalar_score(y_train, y_mean, y_sd)))

    candidate_rows = []
    perturb_rows = []
    model_cache: dict[tuple[str, float], object] = {}
    pred_cache: dict[tuple[str, float], np.ndarray] = {}
    for epsilon in EPSILONS:
        for kind in ("ilr_ridge", "quadratic_ridge"):
            model = make_model(kind)
            model.fit(design(p_train, epsilon), y_train)
            model_cache[(kind, epsilon)] = model
            pred = model.predict(design(p_train, epsilon))
            pred_valid = model.predict(design(p_valid, epsilon))
            pred_cache[(kind, epsilon)] = pred
            pred_scalar = scalar_score(pred, y_mean, y_sd)
            best = int(np.argmin(pred_scalar))
            candidate_rows.append({
                "model": kind, "epsilon": epsilon,
                "observed_best_index": int(train.iloc[empirical_idx]["index"]),
                "observed_best_score_z": float(scalar_score(y_train, y_mean, y_sd)[empirical_idx]),
                "predicted_best_index": int(train.iloc[best]["index"]),
                "predicted_best_score_z": float(pred_scalar[best]),
                "predicted_best_observed_score_z": float(scalar_score(y_train, y_mean, y_sd)[best]),
                "predicted_best_is_observed_row": True,
                "a6_a7_mean_predicted_loss_overall": float(pred_valid.mean()),
            })

            p0 = p_train[empirical_idx].copy()
            for donor in range(len(p_cols)):
                if p0[donor] < DELTA:
                    continue
                for receiver in range(len(p_cols)):
                    if receiver == donor:
                        continue
                    p1 = p0.copy()
                    p1[donor] -= DELTA
                    p1[receiver] += DELTA
                    delta = scalar_score(model.predict(design(p1[None, :], epsilon)), y_mean, y_sd)[0] - scalar_score(model.predict(design(p0[None, :], epsilon)), y_mean, y_sd)[0]
                    perturb_rows.append({
                        "model": kind, "epsilon": epsilon,
                        "donor": p_cols[donor][2:], "receiver": p_cols[receiver][2:],
                        "delta_mass": DELTA, "delta_scalar_loss_z": float(delta),
                        "direction": "improves" if delta < 0 else "worsens" if delta > 0 else "flat",
                    })

    candidate = pd.DataFrame(candidate_rows)
    perturb = pd.DataFrame(perturb_rows)
    grouped = perturb.groupby(["donor", "receiver"], as_index=False).agg(
        model_epsilon_count=("delta_scalar_loss_z", "size"),
        median_delta_scalar_loss_z=("delta_scalar_loss_z", "median"),
        min_delta_scalar_loss_z=("delta_scalar_loss_z", "min"),
        max_delta_scalar_loss_z=("delta_scalar_loss_z", "max"),
        improving_fraction=("direction", lambda x: float((x == "improves").mean())),
    )
    grouped["sign_consistent"] = (grouped["improving_fraction"].eq(0.0) | grouped["improving_fraction"].eq(1.0))

    candidate.to_csv(RUN_DIR / "candidate_summary.csv", index=False, encoding="utf-8-sig")
    perturb.to_csv(RUN_DIR / "finite_perturbations.csv", index=False, encoding="utf-8-sig")
    grouped.to_csv(RUN_DIR / "pair_stability_summary.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "run_id": RUN_ID, "status": "EXPERIMENTAL_REVIEW",
        "fit_rule": "A4/A5 only; fixed selected alpha=10 configurations",
        "validation": "A6/A7 predictions are diagnostics; no model selection on validation",
        "representations": {"epsilon_values": EPSILONS, "basis": "Helmert ilr", "delta": DELTA},
        "train_rows": int(len(train)), "validation_rows": int(len(valid)),
        "target_count": int(y_train.shape[1]), "domain_count": int(p_train.shape[1]),
        "empirical_best_index": int(train.iloc[empirical_idx]["index"]),
        "candidate_model_count": int(len(candidate)),
        "finite_perturbation_count": int(len(perturb)),
        "pair_count": int(len(grouped)),
        "pair_sign_consistent_fraction": float(grouped["sign_consistent"].mean()),
        "candidate_unique_predicted_indices": sorted(candidate["predicted_best_index"].unique().tolist()),
        "candidate_model_epsilon_table": candidate[["model", "epsilon", "predicted_best_index", "predicted_best_score_z", "a6_a7_mean_predicted_loss_overall"]].to_dict(orient="records"),
        "inputs": {
            "feature_table": {"path": str(FEATURE_TABLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(FEATURE_TABLE)},
            "train_loss": {"path": str((SOURCE / TARGET_FILE).relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(SOURCE / TARGET_FILE)},
            "validation_loss": {"path": str((SOURCE / VALIDATION_FILE).relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(SOURCE / VALIDATION_FILE)},
        },
        "outputs": {
            "candidate_summary": "candidate_summary.csv",
            "finite_perturbations": "finite_perturbations.csv",
            "pair_stability_summary": "pair_stability_summary.csv",
        },
        "limitations": [
            "The candidate screen is restricted to observed A4/A5 rows; no unconstrained optimum is produced.",
            "Finite perturbations are local diagnostics and do not establish causal domain effects.",
            "A8-A15 cross-scale behavior is not used for model selection.",
            "Quality Q and any A-B bridge are excluded.",
        ],
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(f"python={sys.version.split()[0]}\nplatform={platform.platform()}\npandas={pd.__version__}\n", encoding="utf-8")
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q1_p_stability.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q1 P stability audit

运行号：`{RUN_ID}`。只用 A4/A5 拟合固定配置的 ilr Ridge 与二阶 Ridge，在 `epsilon={EPSILONS}` 下比较模型筛选出的最佳观测配比，并围绕 A4/A5 观测中标准化平均 Loss 最低的行做 `delta={DELTA}` 的供体—受体有限扰动。A6/A7 只做预测诊断。

本运行只筛选观测配比，不搜索连续单纯形外的点；结果不能解释为因果领域效应或全局最优配方。
""", encoding="utf-8")
    print(RUN_DIR)


if __name__ == "__main__":
    main()
