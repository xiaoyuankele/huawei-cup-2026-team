"""Run c4-only sensitivity branches for the three reviewed conflict domains."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


BRANCHES = {
    "nih_exporter_c4": {"domain": "nih_exporter", "weights": {"c4": 0.5, "arxiv": 0.4, "wikipedia": 0.1}},
    "pubmed_abstracts_c4": {"domain": "pubmed_abstracts", "weights": {"c4": 0.5, "arxiv": 0.4, "wikipedia": 0.1}},
    "uspto_backgrounds_c4": {"domain": "uspto_backgrounds", "weights": {"c4": 0.4, "book": 0.3, "arxiv": 0.2, "wikipedia": 0.1}},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def q_from_weights(weights: dict[str, float], q_anchor: dict[str, float]) -> float:
    return sum(weights[name] * q_anchor[name] for name in weights)


def rank_corr(left: pd.Series, right: pd.Series) -> float:
    return float(left.rank(method="average").corr(right.rank(method="average")))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    wide_path = root / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/tables/A4_A15_quality_transfer_soft_wide.csv"
    mapping_path = root / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/tables/mapping_v2_soft_current_scores.csv"
    score_path = root / "experiments/runs/q1-critic-topsis-20260925-r01/tables/domain_scores.csv"
    wide = pd.read_csv(wide_path)
    mapping = {row["mixture_domain"]: row for row in csv.DictReader(mapping_path.open(encoding="utf-8-sig"))}
    q_anchor = {
        row["domain"]: float(row["mean"])
        for row in csv.DictReader(score_path.open(encoding="utf-8-sig"))
        if row["dataset_id"] == "A1" and row["subset"] == "full"
    }
    run_id = "q1-domain-transfer-c4-sensitivity-20260925-r01"
    run_dir = root / "experiments/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    branch_rows = []
    output_tables = []
    for branch_id, spec in BRANCHES.items():
        domain = spec["domain"]
        base_weights = json.loads(mapping[domain]["candidate_weights"])
        base_q = q_from_weights(base_weights, q_anchor)
        alt_q = q_from_weights(spec["weights"], q_anchor)
        base_low = min(q_anchor[name] for name in base_weights)
        base_high = max(q_anchor[name] for name in base_weights)
        alt_low = min(q_anchor[name] for name in spec["weights"])
        alt_high = max(q_anchor[name] for name in spec["weights"])
        column = f"p_{domain}"
        if column not in wide:
            raise RuntimeError(f"missing mixture column {column}")
        out = wide[["dataset", "role", "scale", "loss_observed", "index", column, "quality_score_soft_proxy_0_100", "quality_score_soft_low_0_100", "quality_score_soft_high_0_100"]].copy()
        out = out.rename(columns={column: "target_domain_proportion", "quality_score_soft_proxy_0_100": "baseline_q_soft_0_100", "quality_score_soft_low_0_100": "baseline_q_low_0_100", "quality_score_soft_high_0_100": "baseline_q_high_0_100"})
        out["branch_id"] = branch_id
        out["target_domain"] = domain
        out["base_domain_q_0_100"] = base_q
        out["c4_branch_domain_q_0_100"] = alt_q
        out["c4_branch_q_soft_0_100"] = out["baseline_q_soft_0_100"] + out["target_domain_proportion"] * (alt_q - base_q)
        out["delta_q_soft_0_100"] = out["c4_branch_q_soft_0_100"] - out["baseline_q_soft_0_100"]
        out["c4_branch_q_low_0_100"] = out["baseline_q_low_0_100"] + out["target_domain_proportion"] * (alt_low - base_low)
        out["c4_branch_q_high_0_100"] = out["baseline_q_high_0_100"] + out["target_domain_proportion"] * (alt_high - base_high)
        out["c4_branch_range_width_0_100"] = out["c4_branch_q_high_0_100"] - out["c4_branch_q_low_0_100"]
        out["sensitivity_status"] = "C4_SENSITIVITY_ONLY"
        output_tables.append(out)
        branch_rows.append(
            {
                "branch_id": branch_id,
                "target_domain": domain,
                "baseline_weights": json.dumps(base_weights, ensure_ascii=False, separators=(",", ":")),
                "c4_branch_weights": json.dumps(spec["weights"], ensure_ascii=False, separators=(",", ":")),
                "baseline_domain_q_0_100": base_q,
                "c4_branch_domain_q_0_100": alt_q,
                "domain_q_delta_0_100": alt_q - base_q,
                "baseline_range_low_0_100": base_low,
                "baseline_range_high_0_100": base_high,
                "c4_branch_range_low_0_100": alt_low,
                "c4_branch_range_high_0_100": alt_high,
                "wide_row_count": len(out),
                "mean_delta_q_soft_0_100": float(out["delta_q_soft_0_100"].mean()),
                "max_abs_delta_q_soft_0_100": float(out["delta_q_soft_0_100"].abs().max()),
                "mean_abs_delta_q_soft_0_100": float(out["delta_q_soft_0_100"].abs().mean()),
                "spearman_baseline_vs_branch": rank_corr(out["baseline_q_soft_0_100"], out["c4_branch_q_soft_0_100"]),
                "formal_mapping_change": "NO",
                "formal_q2_fit": "NO",
            }
        )

    all_output = pd.concat(output_tables, ignore_index=True)
    all_output.to_csv(run_dir / "c4_sensitivity_wide.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(branch_rows).to_csv(run_dir / "branch_summary.csv", index=False, encoding="utf-8-sig")
    metrics = {
        "schema_version": "q1.domain.transfer.c4.sensitivity.v1",
        "run_id": run_id,
        "task_id": "T-Q1-004",
        "status": "EXPLORATORY_C4_SENSITIVITY",
        "inputs": {
            "baseline_wide": str(wide_path.relative_to(root)).replace("\\", "/"),
            "baseline_wide_sha256": sha256(wide_path),
            "baseline_mapping": str(mapping_path.relative_to(root)).replace("\\", "/"),
            "anchor_quality_scores": str(score_path.relative_to(root)).replace("\\", "/"),
        },
        "branches": branch_rows,
        "summary": {
            "branch_count": len(branch_rows),
            "total_branch_rows": len(all_output),
            "max_abs_delta_across_branches_0_100": float(all_output["delta_q_soft_0_100"].abs().max()),
            "mean_abs_delta_across_branches_0_100": float(all_output["delta_q_soft_0_100"].abs().mean()),
        },
        "decision_boundary": "c4 alternatives are sensitivity-only; baseline mapping and Q1 scores are unchanged; no formal Q2 fit is performed",
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        "# c4 sensitivity branches\n\n"
        "This run compares the user-approved baseline transfer matrix with three c4 alternatives for `nih_exporter`, `pubmed_abstracts`, and `uspto_backgrounds`. It changes only the target domain's semantic-prior anchor mixture, stores results separately, and does not alter A16 or start Q2 fitting.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": run_id, "status": metrics["status"], "branch_count": len(branch_rows), "summary": metrics["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
