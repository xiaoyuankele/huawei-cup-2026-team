"""Build a traceable mixture-quality integration table for Q1.

The script reads the derived scale-feature table and sample-level quality
scores, aggregates A1/full scores by quality domain, applies the A16 mapping,
and emits wide and long tables without changing any source file.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q1-mixture-quality-integration-20260925-r01"
OUTPUT = ROOT / "experiments" / "runs" / RUN_ID
MIXTURE_SOURCE = ROOT / "experiments/runs/q1-scale-feature-table-20260924-r01/q1_scale_features_wide.csv"
MAPPING_SOURCE = ROOT / "data/origin/real_attachments/A_data_value/domain_mapping_guide.csv"
QUALITY_SOURCES = {
    "TOPSIS_CRITIC": ROOT / "experiments/runs/q1-critic-topsis-20260925-r01/artifacts/sample_scores.csv",
    "CRITIC_SUM": ROOT / "experiments/runs/q1-critic-sum-20260925-r01/artifacts/sample_scores.csv",
    "EQUAL_SUM": ROOT / "experiments/runs/q1-equal-sum-20260925-r01/artifacts/sample_scores.csv",
    "TOPSIS_NO_3_COST": ROOT / "experiments/runs/q1-topsis-no3cost-20260925-r01/artifacts/sample_scores.csv",
    "TOPSIS_NO_DSIR": ROOT / "experiments/runs/q1-topsis-nodsir-20260925-r01/artifacts/sample_scores.csv",
    "TOPSIS_WEIGHT_SQUARED": ROOT / "experiments/runs/q1-topsis-wsquared-20260925-r01/artifacts/sample_scores.csv",
}
PRIMARY_MODEL = "TOPSIS_CRITIC"
QUALITY_SCORE_VERSION = "q1-scoring-20260925-r01"
EXPECTED_DATASETS = {
    "A4_A5_train_1m": "fit",
    "A6_A7_validation_1m": "external_validation",
    "A8_A9_validation_60m": "external_validation",
    "A10_A11_validation_1b": "external_validation",
    "A12_A13_extrapolation_10b": "extrapolation",
    "A14_A15_extrapolation_70b": "extrapolation",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def read_mapping() -> pd.DataFrame:
    for encoding in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            mapping = pd.read_csv(MAPPING_SOURCE, encoding=encoding)
            break
        except UnicodeDecodeError:
            mapping = None
    if mapping is None:
        raise RuntimeError(f"Unable to decode {MAPPING_SOURCE}")
    mapping = mapping.loc[:, ["mixture_domain", "quality_domain", "mapping_type"]].copy()
    mapping["mixture_domain"] = mapping["mixture_domain"].fillna("").astype(str).str.strip()
    mapping["quality_domain"] = mapping["quality_domain"].fillna("").astype(str).str.strip()
    mapping["mapping_type"] = mapping["mapping_type"].fillna("").astype(str).str.strip()
    mapping.loc[mapping["quality_domain"].isin(["", "(none)"]), "quality_domain"] = pd.NA
    mapping = mapping[mapping["mixture_domain"].ne("")].drop_duplicates("mixture_domain", keep="first")
    return mapping


def read_quality_reference() -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    reference_rows: list[dict[str, object]] = []
    full_means: dict[str, dict[str, float]] = {}
    for model, path in QUALITY_SOURCES.items():
        frame = pd.read_csv(
            path,
            usecols=["dataset_id", "domain", "split", "quality_score"],
            dtype={"dataset_id": "string", "domain": "string", "split": "string"},
        )
        frame["quality_score"] = pd.to_numeric(frame["quality_score"], errors="coerce")
        if frame["quality_score"].isna().any():
            raise ValueError(f"Non-finite quality score in {path}")
        for dataset_id, dataset_frame in frame.groupby("dataset_id", sort=True):
            for domain, domain_frame in dataset_frame.groupby("domain", sort=True):
                for subset, subset_frame in (("full", domain_frame),):
                    values = subset_frame["quality_score"].to_numpy(dtype=float)
                    reference_rows.append(
                        {
                            "quality_model": model,
                            "dataset_id": str(dataset_id),
                            "subset": subset,
                            "quality_domain": str(domain),
                            "n_records": int(values.size),
                            "mean_quality_score_0_100": float(np.mean(values)),
                            "median_quality_score_0_100": float(np.median(values)),
                            "sd_quality_score_0_100": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
                            "p10_quality_score_0_100": float(np.quantile(values, 0.10)),
                            "p90_quality_score_0_100": float(np.quantile(values, 0.90)),
                        }
                    )
        a1 = frame[frame["dataset_id"].eq("A1")]
        full_means[model] = {
            str(domain): float(domain_frame["quality_score"].mean())
            for domain, domain_frame in a1.groupby("domain", sort=True)
        }
    return pd.DataFrame(reference_rows), full_means


def build_tables() -> dict[str, object]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mixture = pd.read_csv(MIXTURE_SOURCE)
    mixture_source_columns = list(mixture.columns)
    p_columns = [column for column in mixture.columns if column.startswith("p_train_the_pile_")]
    if len(p_columns) != 17:
        raise ValueError(f"Expected 17 mixture columns, found {len(p_columns)}")
    if set(mixture["dataset"].unique()) != set(EXPECTED_DATASETS):
        raise ValueError(f"Unexpected dataset groups: {sorted(mixture['dataset'].unique())}")
    if mixture.duplicated(["dataset", "index"]).any():
        raise ValueError("index is not unique within a dataset in the scale feature table")
    mixture["p_sum_normalized"] = mixture[p_columns].sum(axis=1)
    if float(np.max(np.abs(mixture["p_sum_normalized"] - 1.0))) > 1e-8:
        raise ValueError("normalized mixture proportions do not sum to one")

    mapping = read_mapping()
    mapping_version = f"A16-domain_mapping_guide@{sha256(MAPPING_SOURCE)[:12]}"
    mapping_by_domain = mapping.set_index("mixture_domain").to_dict("index")
    quality_reference, full_means = read_quality_reference()
    mixture_domains = [column.removeprefix("p_train_the_pile_") for column in p_columns]

    mapping_rows: list[dict[str, object]] = []
    for mixture_domain in mixture_domains:
        info = mapping_by_domain.get(mixture_domain, {})
        q_domain = info.get("quality_domain")
        mapping_rows.append(
            {
                "mixture_domain": mixture_domain,
                "quality_domain": q_domain if pd.notna(q_domain) else "",
                "mapping_type": info.get("mapping_type", "unlisted"),
                "mapped": bool(pd.notna(q_domain) and str(q_domain).strip()),
                "primary_quality_score_0_100": full_means[PRIMARY_MODEL].get(str(q_domain)) if pd.notna(q_domain) else np.nan,
            }
        )
    mapping_audit = pd.DataFrame(mapping_rows)

    wide = mixture.copy()
    wide["mapping_version"] = mapping_version
    wide["quality_score_version"] = QUALITY_SCORE_VERSION
    for model in QUALITY_SOURCES:
        raw_values: list[float] = []
        mass_values: list[float] = []
        renorm_values: list[float] = []
        for row in wide.itertuples(index=False):
            raw = 0.0
            mass = 0.0
            for column in p_columns:
                mixture_domain = column.removeprefix("p_train_the_pile_")
                info = mapping_by_domain.get(mixture_domain, {})
                q_domain = info.get("quality_domain")
                if pd.notna(q_domain) and str(q_domain).strip() in full_means[model]:
                    proportion = float(getattr(row, column))
                    raw += proportion * full_means[model][str(q_domain)]
                    mass += proportion
            raw_values.append(raw)
            mass_values.append(mass)
            renorm_values.append(raw / mass if mass > 0 else np.nan)
        slug = model.lower()
        wide[f"quality_{slug}_mapped_raw_0_100"] = raw_values
        wide[f"quality_{slug}_mapped_mass"] = mass_values
        wide[f"quality_{slug}_mapped_renorm_0_100"] = renorm_values
    wide["quality_score_model_primary"] = PRIMARY_MODEL
    wide["quality_mapped_raw_0_100"] = wide["quality_topsis_critic_mapped_raw_0_100"]
    wide["quality_mapped_mass"] = wide["quality_topsis_critic_mapped_mass"]
    wide["quality_mapped_renorm_0_100"] = wide["quality_topsis_critic_mapped_renorm_0_100"]
    wide["quality_unmapped_mass"] = 1.0 - wide["quality_mapped_mass"]
    wide["quality_feature_status"] = np.where(
        wide["quality_mapped_mass"] > 0,
        "partial_mapped_proxy",
        "no_mapped_quality",
    )

    long_rows: list[dict[str, object]] = []
    for row in mixture.itertuples(index=False):
        for column in p_columns:
            mixture_domain = column.removeprefix("p_train_the_pile_")
            info = mapping_by_domain.get(mixture_domain, {})
            q_domain = info.get("quality_domain")
            mapped = bool(pd.notna(q_domain) and str(q_domain).strip() in full_means[PRIMARY_MODEL])
            proportion = float(getattr(row, column))
            q_score = full_means[PRIMARY_MODEL].get(str(q_domain)) if mapped else np.nan
            long_rows.append(
                {
                    "mapping_version": mapping_version,
                    "quality_score_version": QUALITY_SCORE_VERSION,
                    "dataset": row.dataset,
                    "role": row.role,
                    "scale_label": row.scale_label,
                    "total_scale_tokens": row.total_scale_tokens,
                    "log10_scale": row.log10_scale,
                    "index": row.index,
                    "mixture_domain": mixture_domain,
                    "proportion": proportion,
                    "quality_domain": str(q_domain) if pd.notna(q_domain) else "",
                    "mapping_type": info.get("mapping_type", "unlisted"),
                    "mapped": mapped,
                    "quality_model": PRIMARY_MODEL,
                    "quality_score_0_100": q_score,
                    "quality_contribution_0_100": proportion * q_score if mapped else np.nan,
                    "quality_contribution_status": "observed_mapping" if mapped else "unmapped_domain",
                }
            )
    long = pd.DataFrame(long_rows)

    wide_path = OUTPUT / "mixture_quality_integration_wide.csv"
    long_path = OUTPUT / "mixture_quality_contributions_long.csv"
    reference_path = OUTPUT / "quality_domain_reference.csv"
    mapping_path = OUTPUT / "mapping_audit.csv"
    wide.to_csv(wide_path, index=False, encoding="utf-8-sig")
    long.to_csv(long_path, index=False, encoding="utf-8-sig")
    quality_reference.to_csv(reference_path, index=False, encoding="utf-8-sig")
    mapping_audit.to_csv(mapping_path, index=False, encoding="utf-8-sig")

    config_path = ROOT / "configs/q1-mixture-quality-integration.yaml"
    (OUTPUT / "config.yaml").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    (OUTPUT / "git_commit.txt").write_text(git_commit() + "\n", encoding="utf-8")
    (OUTPUT / "README.md").write_text(
        "# Q1 mixture-quality integration\n\n"
        "This run aggregates sample-level A1 quality scores by quality domain and joins them to the A4-A15 mixture/scale feature table through the A16 domain mapping. The wide table has one row per mixture sample; the long table preserves domain-level contributions. Unmapped mixture domains remain explicit and are not imputed. The mapped quality is a partial proxy pending team review.\n",
        encoding="utf-8",
    )

    outputs = {
        "wide": {"path": str(wide_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(wide_path), "rows": int(len(wide)), "columns": list(wide.columns)},
        "long": {"path": str(long_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(long_path), "rows": int(len(long)), "columns": list(long.columns)},
        "quality_reference": {"path": str(reference_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(reference_path), "rows": int(len(quality_reference))},
        "mapping_audit": {"path": str(mapping_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(mapping_path), "rows": int(len(mapping_audit))},
    }
    manifest = {
        "schema_version": "q1.mixture-quality-integration.v1",
        "run_id": RUN_ID,
        "task_id": "T-Q1-003-MIXTURE",
        "git_commit": git_commit(),
        "status": "LOCAL_RESULT_PENDING_TEAM_REVIEW",
        "inputs": {
            "mixture_feature_table": {"path": str(MIXTURE_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(MIXTURE_SOURCE), "rows": int(len(mixture)), "columns": mixture_source_columns},
            "mapping_source": {"path": str(MAPPING_SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(MAPPING_SOURCE)},
            "quality_sources": {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)} for name, path in QUALITY_SOURCES.items()},
        },
        "quality_source": {"dataset": "A1", "subset": "full", "aggregation": "mean sample quality_score grouped by domain"},
        "mapping_version": mapping_version,
        "quality_score_version": QUALITY_SCORE_VERSION,
        "mapping": {"total_mixture_domains": int(len(mapping_audit)), "mapped_domains": mapping_audit.loc[mapping_audit["mapped"], "mixture_domain"].tolist(), "mapped_count": int(mapping_audit["mapped"].sum()), "coverage_fraction_by_domain": float(mapping_audit["mapped"].mean()), "unmapped_domains": mapping_audit.loc[~mapping_audit["mapped"], "mixture_domain"].tolist()},
        "dataset_rows": {dataset: int((mixture["dataset"] == dataset).sum()) for dataset in EXPECTED_DATASETS},
        "outputs": outputs,
        "checks": {
            "normalized_mixture_row_sum_max_abs_error": float(np.max(np.abs(mixture["p_sum_normalized"] - 1.0))),
            "long_rows_equal_wide_rows_times_domains": bool(len(long) == len(wide) * len(p_columns)),
            "wide_index_unique_within_dataset": bool(not wide.duplicated(["dataset", "index"]).any()),
            "primary_quality_score_range": [float(quality_reference.loc[quality_reference["quality_model"].eq(PRIMARY_MODEL), "mean_quality_score_0_100"].min()), float(quality_reference.loc[quality_reference["quality_model"].eq(PRIMARY_MODEL), "mean_quality_score_0_100"].max())],
        },
        "limitations": [
            "The integrated quality is a partial mapped proxy because only six of seventeen mixture domains have direct or near-direct A16 mappings.",
            "Unmapped domains are not imputed and mapped_quality_renorm is a sensitivity feature, not a full corpus quality score.",
            "Quality score runs are local candidates pending team review; no causal quality effect or optimal mixture is claimed.",
            "A12-A15 remain extrapolation scenarios and are not independent validation samples.",
        ],
    }
    (OUTPUT / "metrics.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build_tables(), ensure_ascii=False, indent=2))
