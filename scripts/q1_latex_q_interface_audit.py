"""Audit and freeze the Q interface from the Q1 first-subquestion LaTeX model."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ANCHORS = ["arxiv", "book", "c4", "commoncrawl", "github", "stackexchange", "wikipedia"]
EXPECTED_FULL = {
    "arxiv": 63.862359595226806,
    "book": 56.03252048079162,
    "c4": 66.00211266187863,
    "commoncrawl": 64.33570995356357,
    "github": 51.70140753241471,
    "stackexchange": 61.38787333596658,
    "wikipedia": 61.10090692042493,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    tex_path = root / "paper/sections/drafts/q1-quality-evaluation.tex"
    score_path = root / "experiments/runs/q1-critic-topsis-20260925-r01/tables/domain_scores.csv"
    transfer_metrics_path = root / "experiments/runs/q1-domain-transfer-matrix-20260925-r01/metrics.json"
    tex = tex_path.read_text(encoding="utf-8")
    required_tokens = {
        "sixteen_indicators": "16 个指标" in tex,
        "robust_01_99": "1\\%" in tex and "99\\%" in tex,
        "critic": "CRITIC" in tex,
        "topsis": "TOPSIS" in tex,
        "q_formula": "Q_i=100" in tex and "D_i^{-}" in tex and "D_i^{+}" in tex,
        "domain_mean": "Q_g=" in tex,
    }
    if not all(required_tokens.values()):
        raise RuntimeError(f"LaTeX model token audit failed: {required_tokens}")

    scores = {}
    with score_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["dataset_id"] == "A1" and row["subset"] == "full" and row["domain"] in ANCHORS:
                scores[row["domain"]] = float(row["mean"])
    if set(scores) != set(ANCHORS):
        raise RuntimeError(f"anchor score coverage mismatch: {sorted(scores)}")
    max_abs_error = max(abs(scores[d] - EXPECTED_FULL[d]) for d in ANCHORS)
    if max_abs_error > 1e-10:
        raise RuntimeError(f"domain score mismatch: {max_abs_error}")

    transfer_metrics = json.loads(transfer_metrics_path.read_text(encoding="utf-8"))
    run_id = "q1-latex-q-interface-20260925-r01"
    run_dir = root / "experiments/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "anchor_quality_scores.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["quality_domain", "Q_domain_0_100", "source_model", "source_subset"])
        writer.writeheader()
        for domain in ANCHORS:
            writer.writerow({"quality_domain": domain, "Q_domain_0_100": scores[domain], "source_model": "Q1_CRITIC_TOPSIS_LATEX_FIRST_SUBQUESTION", "source_subset": "A1/full"})

    metrics = {
        "schema_version": "q1.latex.q.interface.v1",
        "run_id": run_id,
        "task_id": "T-Q1-004",
        "status": "Q1_LATEX_Q_INTERFACE_READY_FOR_EXPLORATORY_Q2",
        "source_model": {
            "paper_tex": str(tex_path.relative_to(root)).replace("\\", "/"),
            "paper_tex_sha256": sha256(tex_path),
            "score_table": str(score_path.relative_to(root)).replace("\\", "/"),
            "score_table_sha256": sha256(score_path),
            "model": "16 indicators -> A1 1%/99% robust normalization -> CRITIC weights -> weighted-distance TOPSIS",
            "formula": "Q_i = 100 * D_i_minus / (D_i_plus + D_i_minus)",
            "domain_aggregation": "Q_g = mean_i_in_domain(Q_i)",
        },
        "latex_token_audit": required_tokens,
        "anchor_quality_scores": scores,
        "anchor_score_max_abs_error_vs_frozen_table": max_abs_error,
        "approved_mapping_decision": "q1-domain-conflict-review-decision-20260925-r01",
        "transfer_matrix_run": transfer_metrics["run_id"],
        "transfer_matrix_summary": transfer_metrics["summary"],
        "q2_status": "exploratory_interface_only; formal Q2 fit not started",
        "limitations": [
            "The Q1 score is a composite proxy, not a human-label accuracy estimate.",
            "The 11 inferred domain rows remain semantic priors even after user approval of the main recommendation.",
            "The interface does not join A and B rows by row number; Q/p must enter Q2 through the declared interface.",
        ],
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        "# Q1 first-subquestion LaTeX Q interface\n\n"
        "This run freezes the Q1 first-subquestion CRITIC-TOPSIS model as the quality-score source for the exploratory A4-A15 transfer experiment. It verifies the LaTeX formula and anchor-domain scores, then points to the approved exploratory transfer matrix. It does not start a formal Q2 fit.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": run_id, "status": metrics["status"], "anchor_count": len(scores), "max_abs_error": max_abs_error}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
