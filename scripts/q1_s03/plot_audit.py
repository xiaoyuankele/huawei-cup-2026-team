"""Plot audited Q1.3 outputs using Python only; no fitting or data filtering.

Run from the repository root with --run experiments/runs/<run-name>.
Top-row metrics are fixed-cohort values, not stochastic repeated-run means.
Paired slope uncertainty comes directly from scale_coefficients.csv.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7,
    "axes.titlesize": 7.5,
    "axes.labelsize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "legend.frameon": False,
    "savefig.facecolor": "white",
})

DATASETS = ["A6_A7_test_1m", "A8_A9_test_60m", "A10_A11_test_1b",
            "A12_A13_est_10b", "A14_A15_est_70b"]
LABELS = ["1M", "60M", "1B", "10B", "70B"]
STYLE = {
    "C0_none": ("#777777", "o", "--", "C0: None"),
    "C1_global": ("#277DA8", "o", "-", "C1: Global"),
    "C1_domain": ("#86559D", "s", "-", "C1: Domain"),
    "C2_mixture_conditioned": ("#BD7439", "^", ":", "C2: Mixture"),
}
DOMAIN_NAMES = {
    "arxiv": "ArXiv", "freelaw": "FreeLaw", "pubmed_central": "PubMed Central",
    "wikipedia_en": "Wikipedia (en)", "dm_mathematics": "DM Mathematics",
    "github": "GitHub", "stackexchange": "StackExchange",
    "gutenberg_pg_19": "Gutenberg", "pile_cc": "Pile-CC", "ubuntu_irc": "Ubuntu IRC",
    "hackernews": "HackerNews", "pubmed_abstracts": "PubMed abstracts",
    "uspto_backgrounds": "USPTO", "loss_mean_13_domains": "13-domain mean",
}


def display_domain(name):
    if name == "loss_mean_13_domains":
        return DOMAIN_NAMES[name]
    return DOMAIN_NAMES[name.removeprefix("metric/the_pile_").removesuffix("_val_loss")]


def panel_label(ax, letter, x=-0.17, y=1.07):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=9, fontweight="bold")


def read_sources(run):
    metrics = pd.read_csv(run / "metrics_aggregate.csv")
    paired = pd.read_csv(run / "paired_shift_transfer.csv")
    coeffs = pd.read_csv(run / "scale_coefficients.csv")
    parameters = json.loads((run / "model_parameters.json").read_text(encoding="utf-8"))
    if len(coeffs) != 14 or coeffs.domain.duplicated().any():
        raise ValueError("Expected all 13 domains and the 13-domain mean exactly once")
    base = metrics[metrics.base_model.eq("B1_Q_proxy")]
    selected = base[base.dataset.isin(DATASETS)]
    if len(selected) != 20 or selected[["correction", "dataset"]].duplicated().any():
        raise ValueError("Expected four corrections across five complete evaluation cohorts")
    if not np.isfinite(selected[["rmse_mean_loss", "rmse_pooled_all_domains"]]).all().all():
        raise ValueError("Metrics must be finite")
    global_mean = selected[selected.correction.eq("C1_global")].set_index("dataset").loc[DATASETS]
    domain_mean = selected[selected.correction.eq("C1_domain")].set_index("dataset").loc[DATASETS]
    if not np.allclose(global_mean.rmse_mean_loss, domain_mean.rmse_mean_loss, atol=1e-12):
        raise ValueError("C1 global/domain mean RMSE is not identical; revise panel a")
    shift = paired[paired.left_dataset.eq("A12_A13_est_10b") & paired.correction.eq("C1_domain")]
    shift = shift.set_index("domain").loc[coeffs.domain]
    if len(shift) != 14 or not shift.n.eq(63).all():
        raise ValueError("High-scale shift requires 63 pairs and all 13 domains plus mean")
    return selected, coeffs, shift, parameters


def metrics_panel(ax, metrics, column, include_domain):
    # Ordered cohorts, not a continuous scale axis; connecting lines are guides.
    xx = np.arange(len(DATASETS))
    for corr, (color, marker, line, label) in STYLE.items():
        if corr == "C1_domain" and not include_domain:
            continue
        series = metrics[metrics.correction.eq(corr)].set_index("dataset").loc[DATASETS]
        ax.plot(xx, series[column], color=color, marker=marker, linestyle=line,
                linewidth=1.15, markersize=3, label=label)
    ax.set_xticks(xx, LABELS)
    ax.set_xlim(-0.2, 4.2)
    ax.set_ylim(0, 4.2)
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_ylabel("RMSE (Loss units)")
    ax.grid(axis="y", color="#EAEAEA", linewidth=0.5)
    ax.set_axisbelow(True)
    for x, text in [(0.5, "Paired calibration"), (2, "Retrospective"), (3.5, "Table estimates")]:
        ax.text(x, -0.255, text, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=6)
    ax.plot([-0.1, 1.1], [-0.21, -0.21], transform=ax.get_xaxis_transform(),
            color="#777777", linewidth=0.55, clip_on=False)
    ax.plot([2.9, 4.1], [-0.21, -0.21], transform=ax.get_xaxis_transform(),
            color="#777777", linewidth=0.55, clip_on=False)


def make_figure(run):
    metrics, coeffs, shift, parameters = read_sources(run)
    out = run / "figures"
    out.mkdir(parents=True, exist_ok=True)
    # Physical canvas is exactly 180 × 157 mm; fixed axes preserve its dimensions.
    fig = plt.figure(figsize=(7.0866141732, 6.1811023622))
    axes = [fig.add_axes(bounds) for bounds in [
        (0.095, 0.635, 0.38, 0.25), (0.60, 0.635, 0.38, 0.25),
        (0.18, 0.10, 0.295, 0.36), (0.60, 0.10, 0.38, 0.36),
    ]]
    a, b, c, d = axes
    metrics_panel(a, metrics, "rmse_mean_loss", include_domain=False)
    metrics_panel(b, metrics, "rmse_pooled_all_domains", include_domain=True)
    a.set_title("Error in 13-domain mean Loss", loc="left", pad=10)
    b.set_title("Error across all 13 responses", loc="left", pad=10)
    a.text(0.02, 0.90, "C1 global = C1 domain", transform=a.transAxes, fontsize=6.2)
    a.text(0.02, 0.80, "Response averaging can cancel errors", transform=a.transAxes, fontsize=6.2)
    for ax, letter in [(a, "a"), (b, "b")]:
        panel_label(ax, letter)
    handles = [Line2D([0], [0], color=s[0], marker=s[1], linestyle=s[2],
                      linewidth=1.15, markersize=3, label=s[3]) for s in STYLE.values()]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.53, 0.985),
               ncol=4, columnspacing=1.8, handlelength=2.1)

    yy = np.arange(14)
    val = coeffs.slope_per_log10_scale.to_numpy()
    lo, hi = coeffs.bootstrap_ci95_low.to_numpy(), coeffs.bootstrap_ci95_high.to_numpy()
    if not ((lo <= val).all() and (hi >= val).all()):
        raise ValueError("Bootstrap intervals do not bracket their supplied point estimates")
    c.errorbar(val[:-1], yy[:-1], xerr=np.vstack([val[:-1]-lo[:-1], hi[:-1]-val[:-1]]),
               fmt="s", color=STYLE["C1_domain"][0], markersize=3,
               elinewidth=0.8, capsize=1.7)
    c.errorbar(val[-1:], yy[-1:], xerr=np.vstack([val[-1:]-lo[-1:], hi[-1:]-val[-1:]]),
               fmt="D", color=STYLE["C1_global"][0], markersize=4,
               elinewidth=0.9, capsize=1.7)
    c.axvline(val[-1], color=STYLE["C1_global"][0], linestyle=":", linewidth=0.8)
    c.set_yticks(yy, [display_domain(x) for x in coeffs.domain])
    c.set_xlim(-1.48, -0.46)
    c.set_xticks([-1.4, -1.1, -0.8, -0.5])
    c.set_xlabel("Loss change per decade of scale", labelpad=6)
    c.set_title("Paired scale slopes with 95% CI", loc="left", pad=27)
    c.text(0, 1.05, "1M → 60M; 256 matched recipes", transform=c.transAxes, fontsize=6.3)
    panel_label(c, "c", x=-0.48, y=1.15)

    reference = -shift.reference_delta_mean.to_numpy()
    transferred = -shift.predicted_delta_mean.to_numpy()
    if not (np.isfinite(reference).all() and np.isfinite(transferred).all()):
        raise ValueError("Nonfinite paired shifts")
    for row, (ref, pred) in enumerate(zip(reference, transferred)):
        d.plot([ref, pred], [row, row], color="#D8D8D8", linewidth=0.8, zorder=1)
    d.scatter(reference, yy, marker="o", color="#666666", s=13,
              label="Table-estimated decrease", zorder=3)
    d.scatter(transferred[:-1], yy[:-1], marker="s", color=STYLE["C1_domain"][0], s=13,
              label="Transferred C1 domain", zorder=3)
    d.scatter(transferred[-1], yy[-1], marker="D", color=STYLE["C1_global"][0], s=20, zorder=3)
    d.axvline(transferred[-1], color=STYLE["C1_global"][0], linestyle=":", linewidth=0.8)
    d.set_yticks(yy, [""]*14)
    d.tick_params(axis="y", length=0)
    d.spines["left"].set_visible(False)
    d.set_xlim(0.2, 1.23)
    d.set_xticks([0.3, 0.6, 0.9, 1.2])
    d.set_xlabel("Loss decrease from 10B to 70B", labelpad=6)
    d.set_title("Transfer of low-scale slopes", loc="left", pad=27)
    d.text(0, 1.05, "63 matched recipes; estimates only", transform=d.transAxes, fontsize=6.3)
    d.legend(loc="lower right", bbox_to_anchor=(1.025, 1.105), fontsize=6,
             handlelength=1.1, borderaxespad=0, labelspacing=0.3)
    panel_label(d, "d", y=1.15)
    for ax in (c, d):
        ax.set_ylim(13.65, -0.65)
        ax.axhline(12.5, color="#CCCCCC", linewidth=0.6)
    fig.text(0.095, 0.017,
             "A6/A8 fit the corrections. A12–A15 provide estimated Loss; they are not independent observations.",
             fontsize=6.3)

    stem = out / "Figure1_scale_correction_audit"
    fig.savefig(stem.with_suffix(".svg"))
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)
    metadata = {
        "backend": "python", "width_mm": 180, "height_mm": 157,
        "sources": ["metrics_aggregate.csv", "paired_shift_transfer.csv", "scale_coefficients.csv"],
        "base_model": "B1_Q_proxy", "metrics_rows_displayed": len(metrics),
        "slope_rows": len(coeffs), "paired_shift_rows": len(shift),
        "bootstrap": parameters.get("bootstrap", {}),
        "exclusions": "Base-model sensitivity omitted from figure only; all source rows retained in CSV. No recipe exclusion.",
        "mean_C1_curves": "Global and domain-specific values checked equal; one curve shown in panel a.",
    }
    (out / "figure_manifest.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote figure exports to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Run directory containing audited CSV outputs")
    make_figure(parser.parse_args().run)
