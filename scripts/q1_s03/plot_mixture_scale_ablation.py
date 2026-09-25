"""Plot full-mixture scale calibration from audited aggregate metrics.

Python-only, deterministic source-data plot. No simulated observations or
resampling. This figure contains only the two pure-mixture models; quality
ablations remain available in the complete experiment tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


MODELS = [("ilr_ridge", "ilr-Ridge"), ("quadratic_ridge", "Quadratic Ridge")]
DATASETS = [
    "A6_A7_test_1m",
    "A8_A9_test_60m",
    "A10_A11_test_1b",
    "A12_A13_est_10b",
    "A14_A15_est_70b",
]
DISPLAY = [
    "A6/A7\n1M\nSame scale",
    "A8/A9\n60M\nCalibration",
    "A10/A11\n1B\nRetrospective",
    "A12/A13\n10B\nEstimated",
    "A14/A15\n70B\nEstimated",
]
CORRECTIONS = [
    ("C0_none", "C0: No scale term", "#777777", "s"),
    ("C1_global", "C1: Global log-scale", "#187B8D", "o"),
    ("C1_domain", "C1: Domain log-scale", "#8D6CA7", "D"),
    ("C2_mixture_conditioned", "C2: Mixture-conditioned", "#C67C3A", "^"),
]
METRIC = "rmse_pooled_all_domains"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path,
                        default=Path("experiments/runs/q1-mixture-scale-ablation-20260925-r01"))
    args = parser.parse_args()
    run = args.run.resolve()
    source = run / "metrics_aggregate.csv"
    out = run / "figures"
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(source)
    required = {"base_model", "correction", "dataset", "n", "role", METRIC}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    subset = frame[
        frame["base_model"].isin([name for name, _ in MODELS])
        & frame["correction"].isin([row[0] for row in CORRECTIONS])
        & frame["dataset"].isin(DATASETS)
    ].copy()
    keys = ["base_model", "correction", "dataset"]
    if subset.duplicated(keys).any() or len(subset) != 40:
        raise ValueError("Figure requires exactly 40 unique model/correction/dataset rows.")
    indexed = subset.set_index(keys)
    expected = pd.MultiIndex.from_product(
        [[name for name, _ in MODELS], [row[0] for row in CORRECTIONS], DATASETS],
        names=keys,
    )
    if len(expected.difference(indexed.index)):
        raise ValueError("Incomplete figure source grid.")
    values = indexed.reindex(expected)[METRIC].to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("RMSE values must all be finite and positive.")
    for dataset in DATASETS:
        rows = subset[subset["dataset"] == dataset]
        if rows["n"].nunique() != 1:
            raise ValueError(f"Inconsistent sample counts: {dataset}")
    subset = indexed.reindex(expected).reset_index()
    source_columns = keys + ["n", "role", METRIC]
    subset[source_columns].to_csv(out / "source_data.csv", index=False)

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7,
        "axes.titlesize": 8,
        "axes.labelsize": 7,
        "xtick.labelsize": 6,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
    })
    # 183 mm x 100 mm, expressed in inches for matplotlib and source auditing.
    fig, axes = plt.subplots(1, 2, figsize=(7.2047244094, 3.9370078740), sharey=True)
    fig.subplots_adjust(left=0.083, right=0.982, bottom=0.305, top=0.845, wspace=0.18)
    x = np.arange(len(DATASETS), dtype=float)
    offsets = np.linspace(-0.24, 0.24, len(CORRECTIONS))
    log_y = float(values.max() / values.min()) > 20
    for panel, (ax, (model, display_model)) in enumerate(zip(axes, MODELS)):
        ax.axvspan(2.5, 4.5, color="#F1F1F1", zorder=0)
        ax.axvline(2.5, color="#D1D1D1", linewidth=0.6, zorder=0)
        for offset, (correction, label, color, marker) in zip(offsets, CORRECTIONS):
            points = np.array([indexed.loc[(model, correction, dataset), METRIC]
                               for dataset in DATASETS], dtype=float)
            ax.scatter(x + offset, points, s=22, marker=marker, c=color,
                       edgecolors="white", linewidths=0.35, zorder=3,
                       label=label)
        ax.set_xticks(x, DISPLAY)
        ax.tick_params(axis="x", length=0, pad=5)
        ax.tick_params(axis="y", length=3, width=0.7)
        ax.set_xlim(-0.55, 4.55)
        if log_y:
            ax.set_yscale("log")
            ax.set_ylim(values.min() / 1.3, values.max() * 1.35)
        else:
            ax.set_ylim(0, values.max() * 1.12)
        ax.yaxis.grid(True, which="major", color="#DEDEDE", linewidth=0.45, zorder=0)
        ax.set_axisbelow(True)
        ax.set_title(display_model + " (pure mixture)", pad=17, loc="left")
        ax.text(-0.08, 1.18, chr(ord("a") + panel), transform=ax.transAxes,
                fontsize=8, fontweight="bold", va="top", ha="left")
    axes[0].set_ylabel("Pooled RMSE across 13 Loss responses" + (" (log scale)" if log_y else ""))
    legend = [Line2D([], [], linestyle="None", marker=marker, color=color,
                     markeredgecolor="white", markeredgewidth=0.35, markersize=5,
                     label=label)
              for _, label, color, marker in CORRECTIONS]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.52, 0.015),
               ncol=2, frameon=False, handletextpad=0.45, columnspacing=2.6,
               labelspacing=0.9)
    fig.text(0.532, 0.164, "Dataset categories; scale spacing is not represented",
             ha="center", va="center", fontsize=6, color="#555555")
    stem = out / "Figure1_full_mixture_scale_ablation"
    fig.savefig(stem.with_suffix(".svg"))
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)
    outputs = [stem.with_suffix(suffix) for suffix in [".svg", ".pdf", ".png", ".tiff"]]
    outputs.append(out / "source_data.csv")
    write_json(out / "figure_manifest.json", {
        "figure": "Figure1_full_mixture_scale_ablation",
        "backend": "python/matplotlib",
        "matplotlib_version": matplotlib.__version__,
        "source": "../metrics_aggregate.csv",
        "source_sha256": sha256(source),
        "script": "../../../../scripts/q1_s03/plot_mixture_scale_ablation.py",
        "script_sha256": sha256(Path(__file__)),
        "source_rows_before_selection": len(frame),
        "source_rows_after_selection": len(subset),
        "selection": "Two pure-mixture models; all four corrections; all five non-training tables.",
        "metric": METRIC,
        "x_axis": "Ordered dataset categories; not proportional to scale.",
        "y_axis": "logarithmic" if log_y else "linear; starts at zero",
        "point_definition": "Deterministic whole-table pooled RMSE over all 13 response domains.",
        "uncertainty": "None; no replicate-run or sampling-uncertainty intervals supplied.",
        "width_mm": 183,
        "height_mm": 100,
        "raster_dpi": 600,
        "minimum_declared_font_pt": 6,
        "data_table_counts": {dataset: int(subset.loc[subset["dataset"] == dataset, "n"].iloc[0])
                              for dataset in DATASETS},
        "outputs": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
                    for path in outputs],
    })
    print(json.dumps({"figure": stem.name, "rows": len(subset), "log_y": log_y}))


if __name__ == "__main__":
    main()
