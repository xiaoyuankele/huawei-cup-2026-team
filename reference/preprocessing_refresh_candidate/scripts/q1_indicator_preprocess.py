"""Build the Q1 indicator catalog, A1-fitted normalization and audits.

The raw JSONL.XZ files are read twice and never written. All learned
parameters are estimated from the deterministic A1 fit partition only. A
direction marked pending_verification is deliberately withheld from the final
higher-is-better matrix; its candidate transformations remain in the
sensitivity table for reviewer decision.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import lzma
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml


SOURCE_CARD = "https://huggingface.co/datasets/opendatalab/SlimPajama-Meta-rater/blob/1b31bb3/README.md"
QURATER_SOURCE = "https://github.com/princeton-nlp/QuRating/blob/main/README.md"
PDF_REF = "problem/数据说明_已清除隐藏误导文字.pdf#page=9"


SPECS: list[dict[str, Any]] = [
    {"id": "I01", "field": "fineweb_edu", "meaning": "FineWeb-Edu educational value", "scale": "single-element model score in list", "unit": "score", "compression": "take element 0", "outputs": [("fineweb_edu", "benefit", "confirmed", "source card calls it educational value")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I02", "field": "fluency_en", "meaning": "English fluency classifier logits", "scale": "[not_fluent_logit, fluent_logit]", "unit": "logit difference", "compression": "fluent_logit - not_fluent_logit", "outputs": [("fluency_en_fluent_margin", "benefit", "confirmed", "class order and fluent label are documented")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I03", "field": "modernbert_cleanliness", "meaning": "PRRC cleanliness rating over levels 0-5", "scale": "six class logits", "unit": "expected level", "compression": "softmax expected level using classes 0..5", "outputs": [("modernbert_cleanliness_expected", "benefit", "confirmed", "cleanliness is a positive formatting/completeness attribute")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I04", "field": "modernbert_readability", "meaning": "PRRC readability rating over levels 0-5", "scale": "six class logits", "unit": "expected level", "compression": "softmax expected level using classes 0..5", "outputs": [("modernbert_readability_expected", "benefit", "confirmed", "readability is defined as clarity and ease of understanding")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I05", "field": "modernbert_reasoning", "meaning": "PRRC reasoning complexity rating over levels 0-5", "scale": "six class logits", "unit": "expected level", "compression": "softmax expected level using classes 0..5", "outputs": [("modernbert_reasoning_expected", "pending_verification", "pending_verification", "higher logical complexity is not intrinsically higher data quality")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I06", "field": "modernbert_professionalism", "meaning": "PRRC professionalism/expertise-related rating over levels 0-5", "scale": "six class logits", "unit": "expected level", "compression": "softmax expected level using classes 0..5", "outputs": [("modernbert_professionalism_expected", "pending_verification", "pending_verification", "source description links this dimension to expertise required; direction for general quality is unresolved")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I07", "field": "dsir_books", "meaning": "DSIR importance relative to Books domain", "scale": "continuous importance score", "unit": "score", "compression": "retain scalar", "outputs": [("dsir_books", "benefit", "confirmed", "higher importance means greater similarity/utility relative to the named target domain; contextual, not universal quality")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I08", "field": "dsir_wiki", "meaning": "DSIR importance relative to Wikipedia domain", "scale": "continuous importance score", "unit": "score", "compression": "retain scalar", "outputs": [("dsir_wiki", "benefit", "confirmed", "same contextual DSIR interpretation")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I09", "field": "dsir_math", "meaning": "DSIR importance relative to AutoMathText domain", "scale": "continuous importance score", "unit": "score", "compression": "retain scalar", "outputs": [("dsir_math", "benefit", "confirmed", "same contextual DSIR interpretation")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I10", "field": "qurater", "meaning": "QuRating multidimensional quality criteria", "scale": "[Writing Style, Required Expertise, Facts and Trivia, Educational Value]", "unit": "criterion score", "compression": "componentwise; never merge criteria with weights", "outputs": [("qurater_writing_style", "benefit", "confirmed", "official QuRating names it a quality criterion"), ("qurater_required_expertise", "pending_verification", "pending_verification", "official repository exposes both high-to-low and low-to-high curricula"), ("qurater_facts_trivia", "benefit", "confirmed", "official QuRating names it a quality criterion"), ("qurater_educational_value", "benefit", "confirmed", "official QuRating names it a quality criterion")], "evidence": [PDF_REF, SOURCE_CARD, QURATER_SOURCE]},
    {"id": "I11", "field": "ad_en", "meaning": "Advertisement detection logits", "scale": "[has_ad_logit, no_ad_logit]", "unit": "logit difference", "compression": "no_ad_logit - has_ad_logit", "outputs": [("ad_en_no_ad_margin", "benefit", "confirmed", "source card documents class order and no-ad label")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I12", "field": "rps_doc_word_count", "meaning": "Number of normalized words in document", "scale": "nonnegative count", "unit": "words", "compression": "retain scalar; no log transform in this contract", "outputs": [("rps_doc_word_count", "pending_verification", "pending_verification", "length alone has no universal quality direction")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I13", "field": "rps_doc_num_sentences", "meaning": "Number of detected sentences", "scale": "nonnegative count", "unit": "sentences", "compression": "retain scalar", "outputs": [("rps_doc_num_sentences", "pending_verification", "pending_verification", "document length/structure is task and domain dependent")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I14", "field": "rps_doc_unigram_entropy", "meaning": "Entropy of the unigram distribution", "scale": "nonnegative continuous", "unit": "entropy", "compression": "retain scalar", "outputs": [("rps_doc_unigram_entropy", "pending_verification", "pending_verification", "higher lexical entropy is not universally better across domains")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I15", "field": "rps_doc_frac_unique_words", "meaning": "Fraction of unique normalized words", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_doc_frac_unique_words", "benefit", "confirmed", "source card identifies it as a degeneracy/diversity measure; more unique words means less repetition under this proxy")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I16", "field": "rps_doc_frac_no_alph_words", "meaning": "Fraction of words without alphabetic characters", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_doc_frac_no_alph_words", "cost", "confirmed", "source card identifies non-alphabetic words as a noise signal")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I17", "field": "rps_doc_frac_chars_top_2gram", "meaning": "Fraction of characters in the most frequent word 2-gram", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_doc_frac_chars_top_2gram", "cost", "confirmed", "higher top n-gram concentration is a repetition proxy")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I18", "field": "rps_doc_frac_chars_top_3gram", "meaning": "Fraction of characters in the most frequent word 3-gram", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_doc_frac_chars_top_3gram", "cost", "confirmed", "higher top n-gram concentration is a repetition proxy")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I19", "field": "rps_lines_uppercase_letter_fraction", "meaning": "Fraction of uppercase letters among characters", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_lines_uppercase_letter_fraction", "pending_verification", "pending_verification", "uppercase usage differs by domain, code and document genre")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I20", "field": "rps_lines_ending_with_terminal_punctution_mark", "meaning": "Fraction of lines ending with terminal punctuation", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_lines_ending_with_terminal_punctution_mark", "benefit", "confirmed", "source card identifies terminal punctuation as a naturalness/structure signal")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I21", "field": "rps_lines_numerical_chars_fraction", "meaning": "Fraction of numerical characters", "scale": "fraction", "unit": "ratio", "compression": "retain scalar", "outputs": [("rps_lines_numerical_chars_fraction", "pending_verification", "pending_verification", "numeric-heavy text can be valid mathematics/code or noise")], "evidence": [PDF_REF, SOURCE_CARD]},
    {"id": "I22", "field": "rps_doc_mean_word_length", "meaning": "Mean normalized word length", "scale": "nonnegative continuous", "unit": "characters per word", "compression": "retain scalar", "outputs": [("rps_doc_mean_word_length", "pending_verification", "pending_verification", "word length is a complexity proxy without a universal quality direction")], "evidence": [PDF_REF, SOURCE_CARD]},
]


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def parse_constant(value: str) -> float:
    return float(value)


def iter_records(path: Path) -> Iterable[dict[str, Any]]:
    with lzma.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line, parse_constant=parse_constant)
            except Exception as exc:
                raise ValueError(f"parse error at {path.as_posix()}:{line_number}:{type(exc).__name__}") from exc
            if not isinstance(record, dict):
                raise TypeError(f"non-object record at {path.as_posix()}:{line_number}")
            yield record


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_split(record_id: str, seed: int) -> str:
    token = hashlib.sha256(f"{seed}|{record_id}".encode("utf-8")).digest()
    bucket = int.from_bytes(token[:8], "big") % 100
    return "fit" if bucket < 80 else "holdout"


def softmax_expected(values: list[Any]) -> float | None:
    if len(values) != 6 or not all(finite(v) for v in values):
        return None
    maximum = max(float(v) for v in values)
    exps = [math.exp(float(v) - maximum) for v in values]
    total = sum(exps)
    return sum(index * value for index, value in enumerate(exps)) / total


def scalarize(record: dict[str, Any]) -> tuple[dict[str, float | None], int, list[str]]:
    values: dict[str, float | None] = {}
    nonfinite_components = 0
    nonfinite_names: list[str] = []

    def get_scalar(name: str, field: str) -> None:
        nonlocal nonfinite_components
        value = record.get(field)
        if finite(value):
            values[name] = float(value)
        else:
            values[name] = None
            nonfinite_components += 1
            nonfinite_names.append(field)

    get_scalar("fineweb_edu", "fineweb_edu") if isinstance(record.get("fineweb_edu"), (int, float)) else None
    if "fineweb_edu" not in values:
        value = record.get("fineweb_edu")
        if isinstance(value, list) and len(value) == 1 and finite(value[0]):
            values["fineweb_edu"] = float(value[0])
        else:
            values["fineweb_edu"] = None
            nonfinite_components += 1
            nonfinite_names.append("fineweb_edu[0]")

    for field, output, left, right in [
        ("ad_en", "ad_en_no_ad_margin", 0, 1),
        ("fluency_en", "fluency_en_fluent_margin", 0, 1),
    ]:
        value = record.get(field)
        if isinstance(value, list) and len(value) == 2 and all(finite(v) for v in value):
            values[output] = float(value[right]) - float(value[left])
        else:
            values[output] = None
            bad = [f"{field}[{i}]" for i in range(2) if not isinstance(value, list) or i >= len(value) or not finite(value[i])]
            nonfinite_components += max(1, len(bad))
            nonfinite_names.extend(bad or [field])

    qurater = record.get("qurater")
    names = ["writing_style", "required_expertise", "facts_trivia", "educational_value"]
    for index, name in enumerate(names):
        output = f"qurater_{name}"
        if isinstance(qurater, list) and len(qurater) == 4 and finite(qurater[index]):
            values[output] = float(qurater[index])
        else:
            values[output] = None
            nonfinite_components += 1
            nonfinite_names.append(f"qurater[{index}]")

    for field in ["modernbert_cleanliness", "modernbert_readability", "modernbert_reasoning", "modernbert_professionalism"]:
        output = f"{field}_expected"
        value = softmax_expected(record.get(field)) if isinstance(record.get(field), list) else None
        values[output] = value
        if value is None:
            nonfinite_components += 1
            nonfinite_names.append(field)

    for field in [
        "dsir_books", "dsir_wiki", "dsir_math", "rps_doc_word_count", "rps_doc_num_sentences",
        "rps_doc_unigram_entropy", "rps_doc_frac_unique_words", "rps_doc_frac_no_alph_words",
        "rps_doc_frac_chars_top_2gram", "rps_doc_frac_chars_top_3gram", "rps_lines_uppercase_letter_fraction",
        "rps_lines_ending_with_terminal_punctution_mark", "rps_lines_numerical_chars_fraction", "rps_doc_mean_word_length",
    ]:
        get_scalar(field, field)
    return values, nonfinite_components, nonfinite_names


def output_specs() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        for output, direction, status, rationale in spec["outputs"]:
            result[output] = {"parent_field": spec["field"], "direction": direction, "direction_status": status, "rationale": rationale}
    return result


def quantile(values: list[float], probability: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def fit_statistics(values: list[float], sign: int) -> dict[str, Any]:
    raw = sorted(values)
    oriented = [sign * value for value in values]
    med = statistics.median(oriented)
    mad = statistics.median([abs(value - med) for value in oriented])
    return {
        "fit_count": len(values),
        "raw_min": min(raw), "raw_max": max(raw),
        "raw_p01": quantile(values, 0.01), "raw_p05": quantile(values, 0.05),
        "raw_median": statistics.median(values), "raw_p95": quantile(values, 0.95), "raw_p99": quantile(values, 0.99),
        "oriented_min": min(oriented), "oriented_max": max(oriented),
        "oriented_p01": quantile(oriented, 0.01), "oriented_p99": quantile(oriented, 0.99),
        "oriented_median": med, "oriented_mad": mad,
        "unique_count": len(set(values)),
    }


def normalize(value: float | None, stats: dict[str, Any], method: str, sign: int, fit_sorted: list[float]) -> float | None:
    if value is None or not finite(value):
        return None
    oriented = sign * float(value)
    if method == "min_max":
        lo, hi = stats["oriented_min"], stats["oriented_max"]
        return 0.5 if hi == lo else max(0.0, min(1.0, (oriented - lo) / (hi - lo)))
    if method == "quantile_01_99":
        lo, hi = stats["oriented_p01"], stats["oriented_p99"]
        return 0.5 if hi == lo else max(0.0, min(1.0, (oriented - lo) / (hi - lo)))
    if method == "rank_ecdf":
        return bisect.bisect_right(fit_sorted, oriented) / (len(fit_sorted) + 1.0)
    if method == "robust_z_logistic":
        scale = 1.4826 * stats["oriented_mad"]
        if scale == 0:
            return 0.5
        z = (oriented - stats["oriented_median"]) / scale
        z = max(-35.0, min(35.0, z))
        return 1.0 / (1.0 + math.exp(-z))
    raise ValueError(method)


def rank_vector(values: list[float | None]) -> list[float | None]:
    pairs = sorted((value, index) for index, value in enumerate(values) if value is not None)
    ranks: list[float | None] = [None] * len(values)
    position = 0
    while position < len(pairs):
        end = position + 1
        while end < len(pairs) and pairs[end][0] == pairs[position][0]:
            end += 1
        rank = (position + 1 + end) / 2.0
        for _, index in pairs[position:end]:
            ranks[index] = rank
        position = end
    return ranks


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 3:
        return float("nan")
    mean_x, mean_y = statistics.fmean(x), statistics.fmean(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    denominator_x = math.sqrt(sum((a - mean_x) ** 2 for a in x))
    denominator_y = math.sqrt(sum((b - mean_y) ** 2 for b in y))
    if denominator_x == 0 or denominator_y == 0:
        return float("nan")
    return numerator / (denominator_x * denominator_y)


def write_catalog(path: Path, config: dict[str, Any]) -> str:
    catalog = {
        "schema_version": "q1.indicator-catalog.v1",
        "task_id": config["task_id"], "run_id": config["run_id"], "prompt_run_id": config["prompt_run_id"],
        "status": "REVIEW", "needs_human_review": True,
        "scope": "22 raw quality fields; list fields may expand to multiple scalar output columns",
        "direction_policy": "Selected proxy directions are assumptions for this experiment, not universal cross-domain monotonic quality laws. Nine pending outputs remain withheld.",
        "direction_qualification": "Non-alphabetic fraction and top word 2/3-gram concentration are treated as costs in the baseline; code, math, tables and legitimate repetition require domain checks. DSIR measures target affinity. confirmed retains the historical operational flag only.",
        "sources": {"problem_pdf": PDF_REF, "quality_data_card": SOURCE_CARD, "qurater_definition": QURATER_SOURCE},
        "normalization": {"fit_dataset": "A1", "fit_partition": "A1 fit only", "primary": "quantile_01_99", "alternatives": ["min_max", "rank_ecdf", "robust_z_logistic"], "reuse": ["A1 holdout", "A2", "A3"]},
        "indicators": [],
    }
    for spec in SPECS:
        catalog["indicators"].append({
            "indicator_id": spec["id"], "raw_field": spec["field"], "meaning": spec["meaning"], "raw_scale": spec["scale"], "unit": spec["unit"],
            "list_compression": spec["compression"], "outputs": [{"name": name, "direction": direction, "direction_status": status, "basis": rationale} for name, direction, status, rationale in spec["outputs"]], "evidence": spec["evidence"],
            "missing_nonfinite": "retain row; set affected output null; report component and row counts; no imputation",
            "outlier_rule": "audit A1 fit p01/p99 and MAD; primary quantile method clips only during derived scaling",
            "license_boundary": "derived local matrix is not a substitute for redistributing raw attachments; raw bytes remain local-only",
        })
    path.write_text(yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return sha256_file(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path, default=Path("configs/q1-indicator-normalization.yaml"))
    parser.add_argument("--raw-root", type=Path, help="Read-only external raw root; never copied")
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw_root = args.raw_root.resolve() if args.raw_root else root / config["raw_root"]
    dataset_paths = {dataset_id: raw_root / relative_path for dataset_id, relative_path in config["datasets"].items()}
    output_specs_map = output_specs()
    output_names = list(output_specs_map)
    directions = {name: (1 if item["direction"] == "benefit" else -1 if item["direction"] == "cost" else 0) for name, item in output_specs_map.items()}
    methods = ["min_max", "quantile_01_99", "rank_ecdf", "robust_z_logistic"]
    output_matrix = root / config["outputs"]["matrix"]
    output_matrix.parent.mkdir(parents=True, exist_ok=True)
    stats_path = root / config["outputs"]["stats"]
    audit_path = root / config["outputs"]["audit"]
    sensitivity_path = root / config["outputs"]["sensitivity"]
    catalog_path = root / config["outputs"]["catalog"]

    raw_hash_before = {dataset_id: sha256_file(path) for dataset_id, path in dataset_paths.items()}
    catalog_hash = write_catalog(catalog_path, config)
    fit_values: dict[str, list[float]] = {name: [] for name in output_names}
    fit_aligned_values: dict[str, list[float | None]] = {name: [] for name in output_names}
    fit_domain_samples: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    all_a1_ids: set[str] = set()
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    nonfinite_components: Counter[str] = Counter()

    for record in iter_records(dataset_paths["A1"]):
        record_id = str(record.get("id", ""))
        all_a1_ids.add(record_id)
        split = stable_split(record_id, int(config["fit"]["seed"]))
        counts["A1"][split] += 1
        values, nonfinite_count, bad_names = scalarize(record)
        for name in bad_names:
            nonfinite_components[name] += 1
        if split == "fit":
            for name in output_names:
                fit_aligned_values[name].append(values.get(name))
            for name, value in values.items():
                if value is not None:
                    fit_values[name].append(value)
                    domain = str(record.get("_source_domain") or "unknown")
                    if len(fit_domain_samples[domain][name]) < 5000:
                        fit_domain_samples[domain][name].append(value)

    stats_by_name: dict[str, dict[str, Any]] = {}
    sorted_oriented: dict[str, list[float]] = {}
    for name in output_names:
        if not fit_values[name]:
            stats_by_name[name] = {"fit_count": 0, "unique_count": 0}
            sorted_oriented[name] = []
        else:
            sign = directions[name] or 1
            stats_by_name[name] = fit_statistics(fit_values[name], sign)
            sorted_oriented[name] = sorted(sign * value for value in fit_values[name])

    matrix_header = ["dataset_id", "record_id", "domain", "split", "overlap_with_A1", "row_status", "nonfinite_component_count", "missing_indicator_count"] + output_names
    dataset_samples: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    output_rows = 0
    with output_matrix.open("w", encoding="utf-8", newline="") as output_handle:
        writer = csv.writer(output_handle)
        writer.writerow(matrix_header)
        for dataset_id in ("A1", "A2", "A3"):
            domain_default = "arxiv" if dataset_id == "A2" else "github" if dataset_id == "A3" else "unknown"
            for record in iter_records(dataset_paths[dataset_id]):
                output_rows += 1
                counts[dataset_id]["records"] += 1
                record_id = str(record.get("id", ""))
                domain = str(record.get("_source_domain") or domain_default)
                overlap = dataset_id != "A1" and record_id in all_a1_ids
                split = stable_split(record_id, int(config["fit"]["seed"])) if dataset_id == "A1" else "external_validation"
                values, nonfinite_count, bad_names = scalarize(record)
                missing_count = sum(value is None for value in values.values())
                row_status = "retained_overlap_with_A1" if record_id in all_a1_ids and dataset_id != "A1" and overlap else "retained_with_missing" if missing_count else "retained"
                row = [dataset_id, record_id, domain, split, str(bool(overlap)).lower(), row_status, nonfinite_count, missing_count]
                for name in output_names:
                    value = values.get(name)
                    direction = directions[name]
                    primary = normalize(value, stats_by_name[name], "quantile_01_99", direction or 1, sorted_oriented[name]) if value is not None and stats_by_name[name].get("fit_count", 0) else None
                    final_value = primary if direction != 0 else None
                    row.append("" if final_value is None else f"{final_value:.12g}")
                    if value is not None and len(dataset_samples[dataset_id][name]) < 5000:
                        dataset_samples[dataset_id][name].append(value)
                writer.writerow(row)

    # Correlation and drift are computed on A1 fit values only; the output row order starts with A1.
    fit_n = counts["A1"]["fit"]
    fit_primary_values: dict[str, list[float | None]] = {}
    for name in output_names:
        sign = directions[name] or 1
        fit_primary_values[name] = [normalize(value, stats_by_name[name], "quantile_01_99", sign, sorted_oriented[name]) for value in fit_aligned_values[name]]
    fit_ranks = {name: rank_vector(values) for name, values in fit_primary_values.items()}
    max_corr: dict[str, float] = {name: float("nan") for name in output_names}
    for index, name in enumerate(output_names):
        candidates: list[float] = []
        for other_index, other in enumerate(output_names):
            if index == other_index:
                continue
            paired = [(x, y) for x, y in zip(fit_ranks[name], fit_ranks[other]) if x is not None and y is not None]
            value = pearson([x for x, _ in paired], [y for _, y in paired]) if paired else float("nan")
            if finite(value):
                candidates.append(abs(value))
        if candidates:
            max_corr[name] = max(candidates)

    def drift(sample: list[float], global_values: list[float]) -> float:
        if not sample or not global_values:
            return float("nan")
        iqr = quantile(global_values, 0.75) - quantile(global_values, 0.25)
        return abs(statistics.median(sample) - statistics.median(global_values)) / (iqr if iqr else 1.0)

    audit_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    for name, item in output_specs_map.items():
        values = fit_values[name]
        stats = stats_by_name[name]
        fit_iqr = quantile(values, 0.75) - quantile(values, 0.25) if values else float("nan")
        domain_shift_values = []
        for domain_map in fit_domain_samples.values():
            sample = domain_map.get(name, [])
            if sample:
                domain_shift_values.append(drift(sample, values))
        max_domain_shift = max(domain_shift_values, default=float("nan"))
        a2_drift = drift(dataset_samples["A2"][name], values)
        a3_drift = drift(dataset_samples["A3"][name], values)
        near_constant = len(set(values)) <= 2 or not finite(fit_iqr) or fit_iqr == 0
        output_method = "withheld_pending_direction" if item["direction_status"] == "pending_verification" else "quantile_01_99"
        audit_rows.append({
            "indicator": name, "parent_field": item["parent_field"], "direction": item["direction"], "direction_status": item["direction_status"],
            "final_matrix_eligible": item["direction_status"] != "pending_verification", "fit_count": len(values), "fit_unique_count": stats.get("unique_count", 0),
            "fit_missing_rate": 1 - (len(values) / fit_n if fit_n else 0), "raw_min": stats.get("raw_min"), "raw_p01": stats.get("raw_p01"), "raw_median": stats.get("raw_median"), "raw_p99": stats.get("raw_p99"), "raw_max": stats.get("raw_max"),
            "fit_iqr": fit_iqr, "near_constant": near_constant, "max_abs_spearman_corr": max_corr[name], "strong_corr_ge_0_9": finite(max_corr[name]) and max_corr[name] >= 0.9,
            "max_domain_median_shift_in_iqr": max_domain_shift, "A2_median_shift_in_iqr": a2_drift, "A3_median_shift_in_iqr": a3_drift, "primary_rule": output_method,
        })
        for method in methods:
            sign = directions[name] or 1
            method_values_fit = [normalize(value, stats, method, sign, sorted_oriented[name]) for value in values]
            candidates = [value for value in method_values_fit if value is not None]
            method_rank = rank_vector(method_values_fit)
            primary_rank = fit_ranks[name]
            paired = [(x, y) for x, y in zip(method_rank, primary_rank) if x is not None and y is not None]
            saturation = sum(value <= 0.0 or value >= 1.0 for value in candidates) / len(candidates) if candidates else float("nan")
            sensitivity_rows.append({"indicator": name, "parent_field": item["parent_field"], "method": method, "direction_status": item["direction_status"], "fit_count": len(candidates), "output_min": min(candidates) if candidates else None, "output_p05": quantile(candidates, 0.05) if candidates else None, "output_median": statistics.median(candidates) if candidates else None, "output_p95": quantile(candidates, 0.95) if candidates else None, "output_max": max(candidates) if candidates else None, "saturation_at_boundary_rate": saturation, "spearman_with_primary": pearson([x for x, _ in paired], [y for _, y in paired]) if paired else None, "selected_primary": method == "quantile_01_99"})

    def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        fields = list(rows[0]) if rows else []
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(audit_path, audit_rows)
    write_csv(sensitivity_path, sensitivity_rows)
    raw_hash_after = {dataset_id: sha256_file(path) for dataset_id, path in dataset_paths.items()}
    stats_payload = {
        "schema_version": "q1.indicator-normalization-stats.v1", "task_id": config["task_id"], "run_id": config["run_id"], "prompt_run_id": config["prompt_run_id"], "needs_human_review": True,
        "config_path": config_path.relative_to(root).as_posix(), "config_sha256": sha256_file(config_path), "catalog_sha256": catalog_hash,
        "raw_hash_before": raw_hash_before, "raw_hash_after": raw_hash_after, "raw_hash_stable": raw_hash_before == raw_hash_after,
        "audit_sampling_note": "Legacy descriptive drift summaries use the first 5000 finite values per dataset/indicator and per A1-fit domain/indicator. Matrix and fit parameters use all eligible rows; full normalized support audits are supplied by q1_score_models.py.",
        "record_counts": {dataset_id: dict(counter) for dataset_id, counter in counts.items()}, "output_rows": output_rows, "output_columns": output_names,
        "nonfinite_component_counts": dict(sorted(nonfinite_components.items())), "pending_direction_outputs": [name for name, item in output_specs_map.items() if item["direction_status"] == "pending_verification"],
        "fit_statistics": stats_by_name, "primary_method": "quantile_01_99", "methods_compared": methods,
        "outputs": {"matrix": output_matrix.relative_to(root).as_posix(), "matrix_sha256": sha256_file(output_matrix), "audit": audit_path.relative_to(root).as_posix(), "audit_sha256": sha256_file(audit_path), "sensitivity": sensitivity_path.relative_to(root).as_posix(), "sensitivity_sha256": sha256_file(sensitivity_path)},
    }
    stats_path.write_text(json.dumps(stats_payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "q1.preprocessed.v1", "task_id": config["task_id"], "run_id": config["run_id"], "prompt_run_id": config["prompt_run_id"], "status": "REVIEW", "needs_human_review": True,
        "raw_root": config["raw_root"], "raw_inputs": [{"dataset_id": dataset_id, "relative_path": config["datasets"][dataset_id], "sha256": raw_hash_after[dataset_id], "role": "A1_fit_and_holdout" if dataset_id == "A1" else "external_validation_only"} for dataset_id in ("A1", "A2", "A3")],
        "fit_rule": config["fit"], "normalization": config["normalization"], "missing": config["missing"], "outputs": {"matrix": output_matrix.relative_to(root).as_posix(), "matrix_sha256": sha256_file(output_matrix), "catalog": catalog_path.relative_to(root).as_posix(), "catalog_sha256": catalog_hash, "stats": stats_path.relative_to(root).as_posix(), "stats_sha256": sha256_file(stats_path), "audit": audit_path.relative_to(root).as_posix(), "audit_sha256": sha256_file(audit_path), "sensitivity": sensitivity_path.relative_to(root).as_posix(), "sensitivity_sha256": sha256_file(sensitivity_path)},
        "limitations": ["pending_verification directions are withheld from final higher-is-better cells", "A2/A3 overlap with A1 is retained as a flag and is not independent-source validation", "no imputation, quality total, weights or model fit is performed"],
    }
    manifest_path = root / "data/manifests/q1_preprocessed.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(json.dumps({"run_id": config["run_id"], "matrix": output_matrix.relative_to(root).as_posix(), "records": output_rows, "fit": counts["A1"]["fit"], "holdout": counts["A1"]["holdout"], "pending_direction_outputs": len(stats_payload["pending_direction_outputs"]), "raw_hash_stable": stats_payload["raw_hash_stable"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
