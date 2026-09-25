"""Build the versioned Q1-to-Q2 quality linkage table.

This is a model-input bridge, not a row-level join between Q1 and Q2.  It
combines the Q1 A4-A15 mixture rows with the Q1 domain-score handoff and keeps
the v2 soft score as a separately labelled sensitivity input.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

import pandas as pd
from q2_research_paths import RUNS


def parse_weights(value: str) -> dict[str, float]:
    try:
        result = json.loads(value)
    except json.JSONDecodeError:
        result = ast.literal_eval(value)
    return {str(k): float(v) for k, v in result.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    run = repo / "experiments" / "runs" / "quality-mapping-20260925-r02-soft-handoff"
    q1_score = repo / "experiments" / "runs" / "q1-critic-topsis-20260924-r01" / "tables" / "domain_scores.csv"
    out = args.output_dir or RUNS / "q2-quality-scaling-linkage-20260925"
    out.mkdir(parents=True, exist_ok=True)

    wide = pd.read_csv(run / "tables" / "scored_wide_v2_soft.csv")
    mapping = pd.read_csv(run / "tables" / "mapping_v2_soft.csv")
    domain = pd.read_csv(q1_score)
    domain = domain[(domain["dataset_id"] == "A1") & (domain["subset"] == "full")]
    domain_scores = (domain.set_index("domain")["mean"] / 100.0).to_dict()

    q_map = {}
    for row in mapping.itertuples(index=False):
        weights = parse_weights(row.candidate_weights)
        missing = sorted(set(weights) - set(domain_scores))
        if missing:
            raise KeyError(f"Q1 primary domain scores missing: {missing}")
        q_map[row.mixture_domain] = sum(weights[k] * domain_scores[k] for k in weights)

    p_cols = [c for c in wide.columns if c.startswith("p_")]
    p_domains = [c[2:] for c in p_cols]
    missing = sorted(set(p_domains) - set(q_map))
    if missing:
        raise KeyError(f"A16 mapping missing mixture domains: {missing}")

    linked = wide.copy()
    linked["Q_A_topsis_0_1"] = sum(linked[f"p_{d}"].fillna(0.0) * q_map[d] for d in p_domains)
    linked["Q_A_source"] = "q1-critic-topsis-20260924-r01+A16-v2-candidate-weights"
    linked["Q_A_soft_source"] = "quality-mapping-20260925-r02-soft-handoff"
    linked["quality_provenance"] = linked["mapped_share_direct_near_direct"].map(
        lambda x: "official_only" if x >= 0.999999 else ("mixed_inferred" if x > 0 else "inferred_only")
    )

    keep = [
        "dataset", "role", "scale", "loss_observed", "index",
        "Q_A_topsis_0_1", "quality_score_soft_proxy_0_1",
        "quality_score_soft_low_0_1", "quality_score_soft_high_0_1",
        "quality_score_soft_range_width", "mapped_share_direct_near_direct",
        "quality_provenance", "Q_A_source", "Q_A_soft_source",
        "loss_mean_13_domains",
    ] + p_cols
    linked[keep].to_csv(out / "q1_to_q2_quality_linkage.csv", index=False, encoding="utf-8-sig")

    qmap = mapping[[
        "mixture_domain", "mapping_type_A16", "candidate_quality_domains",
        "candidate_weights", "q_soft_0_1", "q_semantic_range_low_0_1",
        "q_semantic_range_high_0_1", "q_semantic_range_width",
        "mapping_confidence",
    ]].copy()
    qmap["q_topsis_domain_0_1"] = qmap["mixture_domain"].map(q_map)
    qmap["q_topsis_source"] = "q1-critic-topsis-20260924-r01/domain_scores.csv"
    qmap.to_csv(out / "q1_domain_quality_for_q2.csv", index=False, encoding="utf-8-sig")

    summary = {
        "run_id": "q2-quality-scaling-linkage-20260925",
        "status": "PLAN / REVIEW_REQUIRED",
        "row_count": int(len(linked)),
        "q1_topsis_domain_range": [float(min(q_map.values())), float(max(q_map.values()))],
        "q1_topsis_row_range": [float(linked["Q_A_topsis_0_1"].min()), float(linked["Q_A_topsis_0_1"].max())],
        "soft_v2_row_range": [float(linked["quality_score_soft_proxy_0_1"].min()), float(linked["quality_score_soft_proxy_0_1"].max())],
        "q1_topsis_vs_soft_v2_corr": float(linked[["Q_A_topsis_0_1", "quality_score_soft_proxy_0_1"]].corr().iloc[0, 1]),
        "q1_primary_source": "experiments/runs/q1-critic-topsis-20260924-r01/tables/domain_scores.csv",
        "q1_soft_source": "experiments/runs/quality-mapping-20260925-r02-soft-handoff/tables/scored_wide_v2_soft.csv",
        "note": "This table is a feature bridge; it does not claim an observed Q1-Q2 row-level join.",
    }
    (out / "linkage_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
