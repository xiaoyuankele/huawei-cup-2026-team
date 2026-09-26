"""Build a separated exploratory soft domain-transfer matrix for Q1 -> A4-A15.

This run is intentionally separate from A16 and from the new-repository v2
handoff. It reuses only the proposed semantic-prior weights and recalculates
all quality-domain values from the current workspace's 2025-09-25 TOPSIS run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


SOFT_PRIORS = {
    "dm_mathematics": {"arxiv": 0.8, "wikipedia": 0.2},
    "freelaw": {"book": 0.5, "wikipedia": 0.3, "commoncrawl": 0.2},
    "nih_exporter": {"arxiv": 0.6, "wikipedia": 0.2, "commoncrawl": 0.2},
    "pubmed_central": {"arxiv": 0.7, "wikipedia": 0.2, "commoncrawl": 0.1},
    "philpapers": {"arxiv": 0.6, "book": 0.2, "wikipedia": 0.2},
    "enron_emails": {"commoncrawl": 0.5, "stackexchange": 0.3, "wikipedia": 0.2},
    "ubuntu_irc": {"commoncrawl": 0.5, "stackexchange": 0.4, "wikipedia": 0.1},
    "europarl": {"wikipedia": 0.5, "commoncrawl": 0.3, "book": 0.2},
    "hackernews": {"commoncrawl": 0.5, "stackexchange": 0.4, "wikipedia": 0.1},
    "pubmed_abstracts": {"arxiv": 0.7, "wikipedia": 0.2, "commoncrawl": 0.1},
    "uspto_backgrounds": {"book": 0.4, "arxiv": 0.3, "wikipedia": 0.2, "commoncrawl": 0.1},
}

PAIRS = [
    ("A4_A5_train_1m", "train_mixture_1m.csv", "train_pile_loss_1m.csv", "train", "1m", True),
    ("A6_A7_test_1m", "test_mixture_1m.csv", "test_pile_loss_1m.csv", "test", "1m", True),
    ("A8_A9_test_60m", "test_mixture_60m.csv", "test_pile_loss_60m.csv", "test", "60m", True),
    ("A10_A11_test_1b", "test_mixture_1B.csv", "test_pile_loss_1B.csv", "test", "1b", True),
    ("A12_A13_est_10b", "est_mixture_10b.csv", "est_pile_loss_10b.csv", "estimate", "10b", False),
    ("A14_A15_est_70b", "est_mixture_70b.csv", "est_pile_loss_70b.csv", "estimate", "70b", False),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def current_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    run_id = "q1-domain-transfer-matrix-20260925-r01"
    run_dir = root / "experiments/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    tables = run_dir / "tables"
    tables.mkdir(exist_ok=True)

    mapping_path = root / "data/origin/real_attachments/A_data_value/domain_mapping_guide.csv"
    score_path = root / "experiments/runs/q1-critic-topsis-20260925-r01/tables/domain_scores.csv"
    score_rows = read_csv(score_path)
    q_by_domain = {
        row["domain"]: float(row["mean"])
        for row in score_rows
        if row.get("dataset_id") == "A1" and row.get("subset") == "full"
    }
    mapping_rows = [row for row in read_csv(mapping_path) if row.get("mixture_domain")]
    if len(mapping_rows) != 17:
        raise ValueError(f"expected 17 mapping rows, got {len(mapping_rows)}")

    soft_rows = []
    matrix_rows = []
    for row in mapping_rows:
        domain = row["mixture_domain"]
        if row.get("mapping_type") in {"direct", "near_direct"}:
            qdomain = row.get("quality_domain", "").strip()
            weights = {qdomain: 1.0}
            status = "official_candidate"
        else:
            weights = SOFT_PRIORS[domain]
            status = "semantic_prior_exploratory"
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ValueError(f"weights do not sum to one for {domain}")
        values = [q_by_domain[name] for name in weights]
        q_soft = sum(q_by_domain[name] * weight for name, weight in weights.items())
        soft_rows.append(
            {
                "mixture_domain": domain,
                "mapping_type_A16": row.get("mapping_type", ""),
                "official_quality_domain_A16": row.get("quality_domain", ""),
                "candidate_quality_domains": ";".join(weights),
                "candidate_weights": json.dumps(weights, ensure_ascii=False, separators=(",", ":")),
                "q_soft_0_100": q_soft,
                "q_semantic_range_low_0_100": min(values),
                "q_semantic_range_high_0_100": max(values),
                "q_semantic_range_width_0_100": max(values) - min(values),
                "mapping_status": status,
                "note": "range is candidate-domain min/max, not a statistical confidence interval",
            }
        )
        matrix_row = {"mixture_domain": domain, "mapping_type_A16": row.get("mapping_type", ""), "mapping_status": status}
        for name in sorted(q_by_domain):
            matrix_row[f"w_{name}"] = weights.get(name, 0.0)
        matrix_rows.append(matrix_row)

    pd.DataFrame(soft_rows).to_csv(tables / "mapping_v2_soft_current_scores.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(matrix_rows).to_csv(tables / "domain_transfer_matrix_W.csv", index=False, encoding="utf-8-sig")

    wide_parts = []
    long_parts = []
    q_soft = {row["mixture_domain"]: row["q_soft_0_100"] for row in soft_rows}
    q_low = {row["mixture_domain"]: row["q_semantic_range_low_0_100"] for row in soft_rows}
    q_high = {row["mixture_domain"]: row["q_semantic_range_high_0_100"] for row in soft_rows}
    mapping_type = {row["mixture_domain"]: row["mapping_type_A16"] for row in soft_rows}
    mapping_status = {row["mixture_domain"]: row["mapping_status"] for row in soft_rows}

    for dataset, mixture_file, loss_file, role, scale, observed in PAIRS:
        mixture_path = root / "data/origin/real_attachments/A_data_value/regmix_tables" / mixture_file
        loss_path = root / "data/origin/real_attachments/A_data_value/regmix_tables" / loss_file
        mixture = pd.read_csv(mixture_path)
        loss = pd.read_csv(loss_path)
        if set(mixture["index"]) != set(loss["index"]):
            raise ValueError(f"index mismatch in {dataset}")
        merged = mixture.merge(loss, on="index", how="inner", validate="one_to_one")
        mixture_cols = [column for column in mixture.columns if column != "index"]
        loss_cols = [column for column in loss.columns if column != "index"]
        raw_p = merged[mixture_cols].astype(float)
        normalized_p = raw_p.div(raw_p.sum(axis=1).replace(0, pd.NA), axis=0).astype(float)
        q_value = sum(normalized_p[f"train_the_pile_{domain}"].to_numpy() * q_soft[domain] for domain in q_soft)
        q_lower = sum(normalized_p[f"train_the_pile_{domain}"].to_numpy() * q_low[domain] for domain in q_low)
        q_upper = sum(normalized_p[f"train_the_pile_{domain}"].to_numpy() * q_high[domain] for domain in q_high)
        official_mass = sum(
            normalized_p[f"train_the_pile_{domain}"].to_numpy()
            for domain in q_soft
            if mapping_type[domain] in {"direct", "near_direct"}
        )
        out = pd.DataFrame(
            {
                "dataset": dataset,
                "role": role,
                "scale": scale,
                "loss_observed": observed,
                "index": merged["index"].astype(int),
                "mixture_sum_raw": raw_p.sum(axis=1),
                "official_mapped_mass": official_mass,
                "quality_score_soft_proxy_0_100": q_value,
                "quality_score_soft_low_0_100": q_lower,
                "quality_score_soft_high_0_100": q_upper,
                "quality_score_soft_range_width_0_100": q_upper - q_lower,
                "quality_transfer_status": "EXPLORATORY_SEMANTIC_PRIOR",
            }
        )
        for column in mixture_cols:
            out[column.replace("train_the_pile_", "p_")] = normalized_p[column]
        for column in loss_cols:
            out[column] = merged[column]
        wide_parts.append(out)
        for column in mixture_cols:
            domain = column.replace("train_the_pile_", "")
            long_parts.append(
                pd.DataFrame(
                    {
                        "dataset": dataset,
                        "role": role,
                        "scale": scale,
                        "loss_observed": observed,
                        "index": merged["index"].astype(int),
                        "mixture_domain": domain,
                        "proportion_raw": raw_p[column],
                        "proportion_normalized": normalized_p[column],
                        "mapping_type_A16": mapping_type[domain],
                        "mapping_status": mapping_status[domain],
                        "q_soft_0_100": q_soft[domain],
                        "q_low_0_100": q_low[domain],
                        "q_high_0_100": q_high[domain],
                        "weighted_soft_contribution_0_100": normalized_p[column] * q_soft[domain],
                    }
                )
            )

    wide = pd.concat(wide_parts, ignore_index=True)
    long = pd.concat(long_parts, ignore_index=True)
    wide.to_csv(tables / "A4_A15_quality_transfer_soft_wide.csv", index=False, encoding="utf-8-sig")
    long.to_csv(tables / "A4_A15_quality_transfer_soft_long.csv", index=False, encoding="utf-8-sig")

    mapping_counts = pd.Series([row["mapping_type_A16"] for row in soft_rows]).value_counts().to_dict()
    metrics = {
        "schema_version": "q1.domain.transfer.matrix.v1",
        "run_id": run_id,
        "task_id": "T-Q1-004",
        "status": "EXPLORATORY_TRANSFER_MATRIX_REVIEW",
        "current_workspace_commit": current_commit(root),
        "source_repo_reference": {
            "path": "E:/huaweicup/2026project-pr24-update",
            "branch": "codex/pr24-versioned-index",
            "commit": "ef339a9230805b940aa8046b306bc7470cd4d520",
            "source_run_id": "quality-mapping-20260925-r02-soft-handoff",
            "source_method_sha256": "c75269d027c783efa29aff5a5ce0d6dbc90640ad2b55793c96b19955bd846123",
            "source_mapping_v2_sha256": "8a1ec05476e d ecf915217f89d51337e5aed4905e9726fce8cd0e00eee5724c02".replace(" ", ""),
            "use": "reference_only_soft_prior_weights",
        },
        "current_sources": {
            "mapping_guide": {"path": str(mapping_path.relative_to(root)).replace("\\", "/"), "sha256": sha256(mapping_path)},
            "quality_domain_scores": {"path": str(score_path.relative_to(root)).replace("\\", "/"), "sha256": sha256(score_path), "run_id": "q1-critic-topsis-20260925-r01", "subset": "A1/full"},
        },
        "mapping_counts": mapping_counts,
        "matrix": {"rows": len(soft_rows), "quality_anchor_count": len(q_by_domain), "all_rows_sum_to_one": True},
        "datasets": {dataset: int((wide["dataset"] == dataset).sum()) for dataset, *_ in PAIRS},
        "outputs": {
            "mapping": "tables/mapping_v2_soft_current_scores.csv",
            "matrix": "tables/domain_transfer_matrix_W.csv",
            "wide": "tables/A4_A15_quality_transfer_soft_wide.csv",
            "long": "tables/A4_A15_quality_transfer_soft_long.csv",
        },
        "summary": {
            "wide_rows": len(wide),
            "long_rows": len(long),
            "soft_q_mean_0_100": float(wide["quality_score_soft_proxy_0_100"].mean()),
            "soft_range_width_mean_0_100": float(wide["quality_score_soft_range_width_0_100"].mean()),
            "official_mapped_mass_mean": float(wide["official_mapped_mass"].mean()),
        },
        "limitations": [
            "11 inferred rows use semantic-prior weights referenced from the new repository; they are not validated mappings.",
            "This run recalculates q values from the current workspace TOPSIS candidate domain scores and must not be mixed with the new repository v2 scores.",
            "Semantic min/max is a scenario range, not a statistical confidence interval.",
            "No formal Q2 fit is performed and no official A16 file is modified.",
        ],
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "config.yaml").write_text(
        """schema_version: q1.domain.transfer.matrix.v1\nrun_id: q1-domain-transfer-matrix-20260925-r01\nstatus: EXPLORATORY_TRANSFER_MATRIX_REVIEW\nquality_score_source: q1-critic-topsis-20260925-r01\nsoft_prior_source: quality-mapping-20260925-r02-soft-handoff (reference only)\nformal_q2_fit: false\nraw_policy: raw attachments remain read-only and local-only\n""",
        encoding="utf-8",
    )
    (run_dir / "README.md").write_text(
        """# Q1 to A4-A15 soft domain-transfer matrix\n\nThis is a separated exploratory run. It uses the new repository's v2 semantic-prior weights as a reference, but recalculates all quality-domain scores from the current workspace's `q1-critic-topsis-20260925-r01` A1/full candidate run. It does not modify A16, the official Q1 score, or any Q2 fit.\n\nThe 17-by-7 matrix `W` keeps the six A16 direct/near-direct rows as one-hot rows and gives the eleven inferred rows candidate anchor mixtures. `quality_score_soft_proxy_0_100` is a projected proxy; the low/high columns are the candidate-anchor min/max scenario range, not confidence intervals.\n\nStatus: `EXPLORATORY_TRANSFER_MATRIX_REVIEW`.\n""",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": run_id, "status": metrics["status"], "summary": metrics["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
