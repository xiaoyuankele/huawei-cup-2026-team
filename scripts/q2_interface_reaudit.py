"""Read-only re-audit of the current A--B interface evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q2-interface-reaudit-20260925-r01"
RUN_DIR = ROOT / "experiments" / "runs" / RUN_ID
A_ROOT = ROOT / "data" / "origin" / "real_attachments" / "A_data_value"
B_ROOT = ROOT / "data" / "origin" / "real_attachments" / "B_scaling_laws"
Q1_RUN = ROOT / "experiments" / "runs" / "q1-critic-topsis-20260925-r01"
MAPPING = A_ROOT / "domain_mapping_guide.csv"
DOMAIN_SCORES = Q1_RUN / "tables" / "domain_scores.csv"
Q1_MANIFEST = Q1_RUN / "run_manifest.json"
SOURCE_MANIFEST = ROOT / "data" / "origin" / "real_attachments" / "source_manifest.json"
B_FILES = {
    "B6": B_ROOT / "supplementary_NQ_experiment.csv",
    "B7": B_ROOT / "supplementary_NQ_experiment_expanded.csv",
    "B8": B_ROOT / "supplementary_NQ_experiment_large.csv",
}
A_MIXTURE_FILES = {
    "A4_A5_train_1m": A_ROOT / "regmix_tables" / "train_mixture_1m.csv",
    "A6_A7_validation_1m": A_ROOT / "regmix_tables" / "test_mixture_1m.csv",
    "A8_A9_validation_60m": A_ROOT / "regmix_tables" / "test_mixture_60m.csv",
    "A10_A11_validation_1b": A_ROOT / "regmix_tables" / "test_mixture_1B.csv",
    "A12_A13_extrapolation_10b": A_ROOT / "regmix_tables" / "est_mixture_10b.csv",
    "A14_A15_extrapolation_70b": A_ROOT / "regmix_tables" / "est_mixture_70b.csv",
}


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


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            reader = csv.DictReader(raw.decode(encoding).splitlines())
            return list(reader.fieldnames or []), list(reader)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {path}")


def fnum(value: str | None) -> float:
    return float(value) if value not in (None, "") else 0.0


def monotonicity(rows: list[dict[str, str]]) -> dict[str, int]:
    groups: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        groups[(row.get("N_params_B", ""), row.get("D_tokens_B", ""), row.get("data_type", "all"))].append(
            (fnum(row.get("Q_score")), fnum(row.get("val_loss")))
        )
    increase = decrease = zero = mixed = 0
    for values in groups.values():
        values.sort()
        diffs = [b - a for (_, a), (_, b) in zip(values, values[1:])]
        increase += sum(d > 1e-9 for d in diffs)
        decrease += sum(d < -1e-9 for d in diffs)
        zero += sum(abs(d) <= 1e-9 for d in diffs)
        mixed += int(any(d > 1e-9 for d in diffs) and any(d < -1e-9 for d in diffs))
    return {"groups": len(groups), "loss_increase_when_q_increases": increase,
            "loss_decrease_when_q_increases": decrease, "zero_steps": zero,
            "mixed_groups": mixed}


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "tables").mkdir(exist_ok=True)

    mapping_fields, mapping_rows = read_csv(MAPPING)
    mapping_rows = [row for row in mapping_rows if (row.get("mixture_domain") or "").strip()]
    score_frame = pd.read_csv(DOMAIN_SCORES)
    score_frame = score_frame[(score_frame["dataset_id"] == "A1") & (score_frame["subset"] == "full")]
    q_by_domain = {str(row.domain): float(row["mean"]) for _, row in score_frame.iterrows()}
    mapping_audit = []
    for row in mapping_rows:
        mix = (row.get("mixture_domain") or "").strip()
        qdom = (row.get("quality_domain") or "").strip()
        mapping_audit.append({
            "mixture_domain": mix, "quality_domain": qdom,
            "mapping_type": row.get("mapping_type", ""),
            "quality_score_available": qdom in q_by_domain,
            "quality_score_0_100": q_by_domain.get(qdom),
        })
    mapping_df = pd.DataFrame(mapping_audit)
    mapped = mapping_df[mapping_df["quality_score_available"]]

    recipe_rows = []
    a_field_sets = {}
    for label, path in A_MIXTURE_FILES.items():
        fields, rows = read_csv(path)
        a_field_sets[label] = set(fields)
        mixture_cols = [f for f in fields if f != "index"]
        masses = []
        for row in rows:
            masses.append(sum(fnum(row.get(col)) for col in mixture_cols))
        recipe_rows.append({
            "recipe": label, "rows": len(rows), "fields": len(fields),
            "index_present": "index" in fields,
            "mean_mixture_sum": sum(masses) / len(masses),
            "min_mixture_sum": min(masses), "max_mixture_sum": max(masses),
        })
    recipe_df = pd.DataFrame(recipe_rows)

    b_audit = []
    b_rows = {}
    b_fields = {}
    for label, path in B_FILES.items():
        fields, rows = read_csv(path)
        b_fields[label] = set(fields)
        b_rows[label] = rows
        b_audit.append({
            "file": label, "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "rows": len(rows), "fields": len(fields),
            "has_experiment_id": "experiment_id" in fields,
            "has_N_params_B": "N_params_B" in fields,
            "has_D_tokens_B": "D_tokens_B" in fields,
            "has_Q_score": "Q_score" in fields,
            "has_val_loss": "val_loss" in fields,
            "q_min": min(fnum(r.get("Q_score")) for r in rows),
            "q_max": max(fnum(r.get("Q_score")) for r in rows),
            "q_monotonicity": json.dumps(monotonicity(rows), ensure_ascii=False),
        })
    b6_ids = {row.get("experiment_id") for row in b_rows["B6"]}
    b7_by_id = {row.get("experiment_id"): row for row in b_rows["B7"]}
    b6_exact_in_b7 = sum(1 for row in b_rows["B6"] if row.get("experiment_id") in b7_by_id and all(b7_by_id[row["experiment_id"]].get(k) == v for k, v in row.items()))

    a_fields_union = set().union(*a_field_sets.values())
    b6_intersection = sorted(a_fields_union & b_fields["B6"])
    possible_join = [field for field in b6_intersection if field in {"index", "record_id", "dataset_id", "experiment_id"}]

    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    manifest_by_file = {entry.get("file"): entry for entry in source_manifest if isinstance(entry, dict)}
    provenance_rows = []
    for label, path in B_FILES.items():
        entry = manifest_by_file.get(f"B_scaling_laws/{path.name}", {})
        provenance_rows.append({
            "file": label, "manifest_entry_present": bool(entry),
            "source_present": bool(entry.get("source")), "note_present": bool(entry.get("note")),
        })
    provenance_df = pd.DataFrame(provenance_rows)

    q1_manifest = json.loads(Q1_MANIFEST.read_text(encoding="utf-8"))
    checks = {
        "q1_score_accepted": q1_manifest.get("status") == "ACCEPTED",
        "all_17_mixture_domains_have_quality_score": len(mapped) == 17,
        "a_b_row_level_join_key_available": bool(possible_join),
        "b8_manifest_has_source_and_note": bool(provenance_df.loc[provenance_df.file.eq("B8"), "source_present"].iloc[0] and provenance_df.loc[provenance_df.file.eq("B8"), "note_present"].iloc[0]),
        "b8_direction_consistent_with_b6_b7": monotonicity(b_rows["B8"])["loss_increase_when_q_increases"] == 0,
        "mixture_rows_have_finite_sums": bool(np.isfinite(recipe_df[["mean_mixture_sum", "min_mixture_sum", "max_mixture_sum"]].to_numpy()).all()),
    }
    blockers = []
    if not checks["q1_score_accepted"]:
        blockers.append("Current Q1 TOPSIS-CRITIC run remains LOCAL_RESULT_PENDING_TEAM_REVIEW.")
    if not checks["all_17_mixture_domains_have_quality_score"]:
        blockers.append(f"Only {len(mapped)}/17 mixture domains have current A1 domain-score mappings.")
    if not checks["a_b_row_level_join_key_available"]:
        blockers.append(f"A mixture fields and B6 fields intersect only at non-key fields: {b6_intersection}; no row-level join key is available.")
    if not checks["b8_manifest_has_source_and_note"]:
        blockers.append("B8 manifest lacks complete source/generation provenance.")
    if not checks["b8_direction_consistent_with_b6_b7"]:
        blockers.append("B8 Q direction is inconsistent with the B6/B7 within-cell direction.")

    mapping_df.to_csv(RUN_DIR / "tables/mapping_audit.csv", index=False, encoding="utf-8-sig")
    recipe_df.to_csv(RUN_DIR / "tables/recipe_interface_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(b_audit).to_csv(RUN_DIR / "tables/b_file_audit.csv", index=False, encoding="utf-8-sig")
    provenance_df.to_csv(RUN_DIR / "tables/b_provenance_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"check": k, "passed": v} for k, v in checks.items()]).to_csv(RUN_DIR / "tables/gate_checks.csv", index=False, encoding="utf-8-sig")

    metrics = {
        "run_id": RUN_ID, "status": "BLOCKED_FORMAL_JOINT_MIGRATION",
        "purpose": "Read-only re-audit using the current Q1 score run and current A/B attachments.",
        "q1_score_run": {"run_id": q1_manifest.get("run_id"), "status": q1_manifest.get("status"), "sha256": sha256(Q1_MANIFEST)},
        "mapping": {"total_mixture_domains": len(mapping_df), "mapped_candidate_domains": int(len(mapped)), "coverage_fraction": float(len(mapped) / len(mapping_df)), "mapping_type_counts": mapping_df["mapping_type"].value_counts(dropna=False).to_dict()},
        "a_b_field_intersection": {"all_intersection": b6_intersection, "possible_key_intersection": possible_join},
        "b6_b7_nested": {"b6_rows": len(b_rows["B6"]), "b7_rows": len(b_rows["B7"]), "b6_exact_rows_in_b7": b6_exact_in_b7},
        "checks": checks, "blockers": blockers,
        "source_sha256": {"domain_mapping_guide.csv": sha256(MAPPING), "domain_scores.csv": sha256(DOMAIN_SCORES), "source_manifest.json": sha256(SOURCE_MANIFEST), **{label: sha256(path) for label, path in B_FILES.items()}},
        "no_raw_mutation": True, "no_model_fit": True, "no_q_conversion_to_b6_scale": True,
    }
    (RUN_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (RUN_DIR / "environment.txt").write_text(f"python={sys.version.split()[0]}\nplatform={platform.platform()}\npandas={pd.__version__}\n", encoding="utf-8")
    (RUN_DIR / "command.txt").write_text("python -X utf8 scripts/q2_interface_reaudit.py\n", encoding="utf-8")
    (RUN_DIR / "README.md").write_text(
        f"""# Q2 A-B interface re-audit

运行号：`{RUN_ID}`。本运行只读复核当前 Q1 TOPSIS-CRITIC 结果、A16 映射、A4–A15 配比表、B6–B8 字段/嵌套关系和 B8 来源与方向证据。它不拟合模型，不把 Q1 候选分转换为 B6 的 `Q_score`，也不修改原始附件。

当前状态为 `BLOCKED_FORMAL_JOINT_MIGRATION`，详细门检查见 `tables/gate_checks.csv`。
""", encoding="utf-8")
    print(json.dumps({"run_id": RUN_ID, "status": metrics["status"], "blockers": len(blockers)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
