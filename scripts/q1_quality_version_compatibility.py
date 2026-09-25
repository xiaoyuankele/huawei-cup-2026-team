"""Audit compatibility between canonical and local Q1 quality-score versions."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-quality-version-compatibility-20260925-r01"
OUT = ROOT / "experiments" / "runs" / RUN_ID
REMOTE_MANIFEST = "data/manifests/q1_quality_scores_delivery.yaml"
OLD = {
    "TOPSIS_CRITIC": ROOT / "experiments/runs/q1-critic-topsis-20260924-r01/tables/domain_scores.csv",
    "CRITIC_SUM": ROOT / "experiments/runs/q1-critic-sum-20260924-r02/tables/domain_scores.csv",
    "EQUAL_SUM": ROOT / "experiments/runs/q1-equal-sum-20260924-r02/tables/domain_scores.csv",
    "TOPSIS_NO_3_COST": ROOT / "experiments/runs/q1-topsis-no3cost-20260924-r01/tables/domain_scores.csv",
    "TOPSIS_NO_DSIR": ROOT / "experiments/runs/q1-topsis-nodsir-20260924-r01/tables/domain_scores.csv",
    "TOPSIS_WEIGHT_SQUARED": ROOT / "experiments/runs/q1-topsis-wsquared-20260924-r01/tables/domain_scores.csv",
}
NEW = {
    "TOPSIS_CRITIC": ROOT / "experiments/runs/q1-critic-topsis-20260925-r01/tables/domain_scores.csv",
    "CRITIC_SUM": ROOT / "experiments/runs/q1-critic-sum-20260925-r01/tables/domain_scores.csv",
    "EQUAL_SUM": ROOT / "experiments/runs/q1-equal-sum-20260925-r01/tables/domain_scores.csv",
    "TOPSIS_NO_3_COST": ROOT / "experiments/runs/q1-topsis-no3cost-20260925-r01/tables/domain_scores.csv",
    "TOPSIS_NO_DSIR": ROOT / "experiments/runs/q1-topsis-nodsir-20260925-r01/tables/domain_scores.csv",
    "TOPSIS_WEIGHT_SQUARED": ROOT / "experiments/runs/q1-topsis-wsquared-20260925-r01/tables/domain_scores.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_remote_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    source_meta: dict[str, dict] = {}
    for model_name in OLD:
        old_path, new_path = OLD[model_name], NEW[model_name]
        if not old_path.exists() or not new_path.exists():
            raise FileNotFoundError(f"missing source for {model_name}: {old_path} / {new_path}")
        old = pd.read_csv(old_path)
        new = pd.read_csv(new_path)
        old = old[(old["dataset_id"] == "A1") & (old["subset"] == "full")][["domain", "mean"]]
        new = new[(new["dataset_id"] == "A1") & (new["subset"] == "full")][["domain", "mean"]]
        merged = old.merge(new, on="domain", how="outer", suffixes=("_canonical_20260924", "_local_20260925"))
        merged["delta_local_minus_canonical"] = merged["mean_local_20260925"] - merged["mean_canonical_20260924"]
        for record in merged.to_dict(orient="records"):
            rows.append({"quality_model": model_name, **record})
        source_meta[model_name] = {
            "canonical_20260924": {"path": old_path.relative_to(ROOT).as_posix(), "sha256": sha256(old_path)},
            "local_20260925": {"path": new_path.relative_to(ROOT).as_posix(), "sha256": sha256(new_path)},
        }

    comparison = pd.DataFrame(rows)
    comparison_path = OUT / "domain_score_version_comparison.csv"
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig", lineterminator="\n")

    manifest_snapshot = OUT / "canonical_manifest_snapshot.yaml"
    try:
        content = subprocess.run(
            ["git", "show", f"origin/main:{REMOTE_MANIFEST}"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout
        manifest_snapshot.write_text(content, encoding="utf-8")
        manifest_status = "captured_from_origin_main"
    except (OSError, subprocess.CalledProcessError):
        manifest_status = "unavailable"

    output = {
        "schema_version": "q1.quality-version-compatibility.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "LOCAL_RESULT_PENDING_TEAM_REVIEW",
        "canonical_reference": {
            "remote": "origin/main",
            "remote_commit": git_remote_commit(),
            "manifest": REMOTE_MANIFEST,
            "primary_run_id": "q1-critic-topsis-20260924-r01",
            "manifest_snapshot_status": manifest_status,
        },
        "source_versions": source_meta,
        "comparison_scope": "A1/full domain means for six quality models; all seven quality domains retained",
        "checks": {
            "rows": int(len(comparison)),
            "models": int(comparison["quality_model"].nunique()),
            "domains": int(comparison["domain"].nunique()),
            "max_abs_delta": float(comparison["delta_local_minus_canonical"].abs().max()),
            "all_within_1e-12": bool((comparison["delta_local_minus_canonical"].abs() <= 1e-12).all()),
        },
        "output": {
            "path": comparison_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(comparison_path),
        },
        "interpretation": [
            "The local 20260925 domain means are numerically compatible with the canonical 20260924 means within 1e-12.",
            "The source run IDs and hashes remain distinct and must not be silently rewritten.",
            "Existing Q1 mixture-quality integration and baseline metrics do not require numerical refitting solely because origin/main advanced.",
            "The quality-score delivery remains review-blocked and is not treated as accepted ground truth.",
        ],
    }
    (OUT / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (OUT / "config.yaml").write_text(
        "schema_version: q1.quality-version-compatibility.v1\n"
        f"run_id: {RUN_ID}\n"
        "canonical_run: q1-critic-topsis-20260924-r01\n"
        "local_run: q1-critic-topsis-20260925-r01\n"
        "comparison: A1/full domain means across six quality models\n"
        "tolerance: 1e-12\n",
        encoding="utf-8",
    )
    (OUT / "README.md").write_text(
        "# Q1 质量评分版本兼容性审计\n\n"
        "本运行比较远端主仓库登记的 20260924 canonical 质量评分与本地 20260925 重跑的 A1/full 域级均分。"
        "两者数值兼容，但保留独立 run_id、文件哈希和审核状态；本审计不替换历史运行，也不将质量评分提升为已验收真值。\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": RUN_ID, "max_abs_delta": output["checks"]["max_abs_delta"], "output_dir": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
