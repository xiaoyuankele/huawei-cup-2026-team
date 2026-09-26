"""Scenario-level sensitivity for the exploratory Q1 -> Q2 Q/p interface.

This run keeps each observed mixture proportion vector ``p`` fixed and varies
only the semantic-prior anchor values used to calculate ``Q = p @ q``.  It is
therefore a row-level calculation on the existing A4-A15 interface, not an
A-to-B join and not a Q2 model fit.  The current approved c4 alternatives are
included as separate scenarios so that the baseline matrix remains untouched.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


BRANCHES = {
    "S1_c4_nih_exporter": {"nih_exporter": {"c4": 0.5, "arxiv": 0.4, "wikipedia": 0.1}},
    "S2_c4_pubmed_abstracts": {"pubmed_abstracts": {"c4": 0.5, "arxiv": 0.4, "wikipedia": 0.1}},
    "S3_c4_uspto_backgrounds": {"uspto_backgrounds": {"c4": 0.4, "book": 0.3, "arxiv": 0.2, "wikipedia": 0.1}},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def top_k_overlap(left: pd.Series, right: pd.Series, k: int = 10) -> float:
    k = min(k, len(left))
    if k == 0:
        return float("nan")
    a = set(left.nlargest(k).index)
    b = set(right.nlargest(k).index)
    return len(a & b) / k


def spearman(left: pd.Series, right: pd.Series) -> float:
    value = left.rank(method="average").corr(right.rank(method="average"))
    return float(value) if pd.notna(value) else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/runs/q2-qp-scenario-sensitivity-20260925-r01"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out if args.out.is_absolute() else root / args.out
    out.mkdir(parents=True, exist_ok=True)

    wide_path = root / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/tables/A4_A15_quality_transfer_soft_wide.csv"
    mapping_path = root / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/tables/mapping_v2_soft_current_scores.csv"
    score_path = root / "experiments/runs/q1-critic-topsis-20260925-r01/tables/domain_scores.csv"
    decision_path = root / "experiments/runs/q1-domain-conflict-review-decision-20260925-r01/metrics.json"

    wide = pd.read_csv(wide_path)
    p_cols = sorted(column for column in wide.columns if column.startswith("p_"))
    domains = [column.removeprefix("p_") for column in p_cols]
    if len(domains) != 17:
        raise RuntimeError(f"expected 17 p columns, got {len(domains)}")
    if wide.duplicated(["dataset", "index"]).any():
        raise RuntimeError("duplicate dataset/index in Q/p interface")
    p = wide[p_cols].to_numpy(dtype=float)
    p_sum = p.sum(axis=1)
    if np.max(np.abs(p_sum - 1.0)) > 1e-9:
        raise RuntimeError("p columns do not sum to one")

    with mapping_path.open(encoding="utf-8-sig", newline="") as handle:
        mapping_rows = {row["mixture_domain"]: row for row in csv.DictReader(handle)}
    with score_path.open(encoding="utf-8-sig", newline="") as handle:
        anchor_q = {
            row["domain"]: float(row["mean"])
            for row in csv.DictReader(handle)
            if row.get("dataset_id") == "A1" and row.get("subset") == "full"
        }
    if set(domains) != set(mapping_rows):
        raise RuntimeError("mapping domains and p columns differ")

    # Baseline domain-level Q is the current soft mapping, reconstructed from
    # the frozen candidate-anchor scores.  A mismatch would indicate that the
    # interface table was changed without updating this audit.
    q_domain_baseline: dict[str, float] = {}
    q_domain_low: dict[str, float] = {}
    q_domain_high: dict[str, float] = {}
    for domain in domains:
        row = mapping_rows[domain]
        weights = json.loads(row["candidate_weights"])
        missing = [name for name in weights if name not in anchor_q]
        if missing:
            raise RuntimeError(f"missing anchor score(s) for {domain}: {missing}")
        values = [anchor_q[name] for name in weights]
        q_domain_baseline[domain] = sum(anchor_q[name] * float(weight) for name, weight in weights.items())
        q_domain_low[domain] = min(values)
        q_domain_high[domain] = max(values)

    baseline_recomputed = p @ np.array([q_domain_baseline[d] for d in domains])
    baseline_table = wide["quality_score_soft_proxy_0_100"].to_numpy(dtype=float)
    baseline_error = float(np.max(np.abs(baseline_recomputed - baseline_table)))
    if baseline_error > 1e-8:
        raise RuntimeError(f"baseline Q mismatch: {baseline_error}")

    # Scenarios are all in the Q1 candidate-score scale (0--100).  ``p`` is
    # measured composition and is not perturbed because no uncertainty model
    # for p, and no A-to-B row key, is available.
    scenario_domain_q = {"S0_baseline": q_domain_baseline.copy()}
    scenario_notes = {
        "S0_baseline": "approved soft mapping and current Q1 A1/full anchor scores",
    }
    for name, replacements in BRANCHES.items():
        q_values = q_domain_baseline.copy()
        for domain, weights in replacements.items():
            q_values[domain] = sum(float(weight) * anchor_q.get(anchor, np.nan) for anchor, weight in weights.items() if anchor in anchor_q)
            missing = [anchor for anchor in weights if anchor != "c4" and anchor not in anchor_q]
            if missing:
                raise RuntimeError(f"missing branch anchor(s) for {name}: {missing}")
            # c4 is a frozen A1/full anchor in the current Q1 score table;
            # use that score consistently with q1_domain_transfer_c4_sensitivity.py.
            if "c4" in weights:
                q_values[domain] = sum(
                    float(weight) * (anchor_q[anchor])
                    for anchor, weight in weights.items()
                )
        scenario_domain_q[name] = q_values
        scenario_notes[name] = "approved conflict-domain c4 branch; c4 uses the frozen A1/full Q1 anchor score"
    all_c4 = q_domain_baseline.copy()
    for name, replacements in BRANCHES.items():
        for domain, weights in replacements.items():
            all_c4[domain] = sum(float(weight) * anchor_q[anchor] for anchor, weight in weights.items())
    scenario_domain_q["S4_c4_all_reviewed"] = all_c4
    scenario_notes["S4_c4_all_reviewed"] = "simultaneous application of the three approved c4 branches; sensitivity-only"

    scenario_rows = []
    for scenario, domain_q in scenario_domain_q.items():
        q_values = p @ np.array([domain_q[d] for d in domains])
        scenario_frame = wide[["dataset", "role", "scale", "loss_observed", "index"]].copy()
        scenario_frame["scenario"] = scenario
        scenario_frame["q_0_100"] = q_values
        scenario_frame["delta_from_baseline_0_100"] = q_values - baseline_recomputed
        scenario_frame["baseline_q_0_100"] = baseline_recomputed
        scenario_rows.append(scenario_frame)
    rows = pd.concat(scenario_rows, ignore_index=True)
    rows.to_csv(out / "scenario_q_long.csv", index=False, encoding="utf-8-sig")

    # Keep the semantic envelope from the transfer matrix as a bound, not as a
    # confidence interval or an additional fitted scenario.
    bound_frame = wide[["dataset", "role", "scale", "loss_observed", "index", "quality_score_soft_low_0_100", "quality_score_soft_high_0_100", "quality_score_soft_range_width_0_100"]].copy()
    bound_frame = bound_frame.rename(columns={"quality_score_soft_low_0_100": "q_low_0_100", "quality_score_soft_high_0_100": "q_high_0_100", "quality_score_soft_range_width_0_100": "q_range_width_0_100"})
    bound_frame.to_csv(out / "baseline_semantic_bounds.csv", index=False, encoding="utf-8-sig")

    summaries = []
    baseline_series = pd.Series(baseline_recomputed, index=wide.index)
    for scenario in scenario_domain_q:
        subset_all = rows[rows["scenario"] == scenario].set_index(wide.index.repeat(1) if False else rows[rows["scenario"] == scenario].index)
        q_series = pd.Series(subset_all["q_0_100"].to_numpy(), index=wide.index)
        delta = q_series - baseline_series
        for dataset, group in wide.groupby("dataset", sort=False):
            indices = group.index
            q_group = q_series.loc[indices]
            d_group = delta.loc[indices]
            summaries.append(
                {
                    "scenario": scenario,
                    "dataset": dataset,
                    "role": str(group["role"].iloc[0]),
                    "n_rows": int(len(indices)),
                    "q_mean_0_100": float(q_group.mean()),
                    "q_sd_0_100": float(q_group.std(ddof=0)),
                    "q_min_0_100": float(q_group.min()),
                    "q_max_0_100": float(q_group.max()),
                    "delta_mean_0_100": float(d_group.mean()),
                    "delta_mean_abs_0_100": float(d_group.abs().mean()),
                    "delta_max_abs_0_100": float(d_group.abs().max()),
                    "spearman_vs_baseline": spearman(baseline_series.loc[indices], q_group),
                    "top10_overlap_vs_baseline": top_k_overlap(baseline_series.loc[indices], q_group, 10),
                    "p_sum_max_abs_error": float(np.max(np.abs(p[indices].sum(axis=1) - 1.0))),
                    "q_in_0_100": bool(((q_group >= 0) & (q_group <= 100)).all()),
                }
            )
    pd.DataFrame(summaries).to_csv(out / "scenario_summary.csv", index=False, encoding="utf-8-sig")

    domain_rows = []
    for scenario, q_values in scenario_domain_q.items():
        for domain in domains:
            domain_rows.append({"scenario": scenario, "mixture_domain": domain, "q_domain_0_100": q_values[domain], "baseline_q_domain_0_100": q_domain_baseline[domain], "delta_q_domain_0_100": q_values[domain] - q_domain_baseline[domain]})
    pd.DataFrame(domain_rows).to_csv(out / "scenario_domain_anchors.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "schema_version": "q2.qp.scenario.sensitivity.v1",
        "run_id": "q2-qp-scenario-sensitivity-20260925-r01",
        "task_id": "T-Q2-MIGRATION",
        "status": "Q2_QP_SCENARIO_SENSITIVITY_EXPLORATORY",
        "inputs": {
            "q1_a4_a15_wide": str(wide_path.relative_to(root)).replace("\\", "/"),
            "q1_a4_a15_wide_sha256": sha256(wide_path),
            "q1_mapping": str(mapping_path.relative_to(root)).replace("\\", "/"),
            "q1_mapping_sha256": sha256(mapping_path),
            "q1_anchor_scores": str(score_path.relative_to(root)).replace("\\", "/"),
            "q1_anchor_scores_sha256": sha256(score_path),
            "approved_conflict_decision": str(decision_path.relative_to(root)).replace("\\", "/"),
            "approved_conflict_decision_sha256": sha256(decision_path),
        },
        "scenarios": {name: {"note": scenario_notes[name], "domain_q": values} for name, values in scenario_domain_q.items()},
        "checks": {
            "input_rows": int(len(wide)),
            "p_column_count": int(len(p_cols)),
            "p_sum_max_abs_error": float(np.max(np.abs(p_sum - 1.0))),
            "baseline_reconstruction_max_abs_error": baseline_error,
            "scenario_q_finite": bool(np.isfinite(rows["q_0_100"]).all()),
            "scenario_q_in_0_100": bool(rows["q_0_100"].between(0, 100).all()),
            "duplicate_dataset_index_count": int(wide.duplicated(["dataset", "index"]).sum()),
            "observed_rows": int(wide["loss_observed"].sum()),
            "extrapolation_rows": int((~wide["loss_observed"]).sum()),
            "p_perturbed": False,
            "a_to_b_row_join": False,
            "q2_model_fit": False,
        },
        "scenario_count": len(scenario_domain_q),
        "row_count_per_scenario": int(len(wide)),
        "outputs": {
            "scenario_q_long": "scenario_q_long.csv",
            "scenario_summary": "scenario_summary.csv",
            "scenario_domain_anchors": "scenario_domain_anchors.csv",
            "baseline_semantic_bounds": "baseline_semantic_bounds.csv",
        },
        "interpretation": [
            "This is a Q1 candidate-score interface stress test, not an official Q score.",
            "Measured mixture proportions p are held fixed; no unsupported p uncertainty model is invented.",
            "Q1 0-100 values are not converted to B6's 0-1 Q_score and are not inserted into M0/M1.",
            "The semantic low/high columns are candidate-anchor bounds, not confidence intervals.",
            "B8 remains excluded; no quality-direction or provenance issue is resolved here.",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Q2 Q/p scenario sensitivity\\n\\n"
        "This exploratory run recalculates Q from the frozen A4-A15 p vectors under the approved baseline and c4 mapping scenarios. It preserves p, makes no A-to-B row join, and does not fit a Q2 model. Q remains in the Q1 candidate 0-100 scale.\\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": metrics["run_id"], "status": metrics["status"], "checks": metrics["checks"], "scenario_count": metrics["scenario_count"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
