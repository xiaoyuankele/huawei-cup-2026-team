"""Nature-style plots and table for the Q3 M0 N-D baseline.

All plotted scenario values are read directly from the frozen run CSV. The
analytic budget contours are derived from the same budget and context fields.
No re-fitting or smoothing is performed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd


# Mandatory Nature-style editable-text settings before any figure is created.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 8
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["legend.frameon"] = False
plt.rcParams["xtick.major.width"] = 0.7
plt.rcParams["ytick.major.width"] = 0.7


COLORS = {
    "navy": "#0F4D92",
    "blue": "#3775BA",
    "teal": "#42949E",
    "violet": "#9A4D8E",
    "red": "#B64342",
    "grey": "#767676",
    "light_grey": "#D8D8D8",
    "dark": "#272727",
    "support": "#E8EEF7",
}

CONTEXT_COLORS = {
    2048: "#0F4D92",
    4096: "#3775BA",
    8192: "#42949E",
    32768: "#9A4D8E",
    131072: "#B64342",
}
MARKERS = {1e19: "o", 1e22: "s", 1e24: "D"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def budget_label(value: float) -> str:
    exponent = int(round(np.log10(value)))
    return rf"$10^{{{exponent}}}$"


def style_axis(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3, width=0.7, pad=2)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontsize=10,
            fontweight="bold", ha="left", va="bottom", color=COLORS["dark"])


def save_figure(fig: plt.Figure, stem: Path) -> list[str]:
    fig.tight_layout(pad=1.2, w_pad=2.2)
    outputs: list[str] = []
    for suffix, kwargs in [
        ("svg", {"bbox_inches": "tight"}),
        ("pdf", {"bbox_inches": "tight"}),
        ("png", {"dpi": 600, "bbox_inches": "tight"}),
        ("tiff", {"dpi": 600, "bbox_inches": "tight"}),
    ]:
        target = stem.with_suffix(f".{suffix}")
        fig.savefig(target, **kwargs)
        outputs.append(str(target))
    plt.close(fig)
    return outputs


def draw_frontier_figure(frame: pd.DataFrame, output_stem: Path,
                         support: dict[str, float], eta: float) -> list[str]:
    fig, (ax_a, ax_b_left) = plt.subplots(1, 2, figsize=(7.2, 3.35),
                                           gridspec_kw={"width_ratios": [1.05, 1.20]})
    style_axis(ax_a)
    style_axis(ax_b_left)
    add_panel_label(ax_a, "a")
    add_panel_label(ax_b_left, "b")

    # Panel a: broad log-log view so extrapolated analytic points remain visible.
    n_min, n_max = support["N_min_B"], support["N_max_B"]
    d_min, d_max = support["D_min_B"], support["D_max_B"]
    ax_a.add_patch(Rectangle((n_min, d_min), n_max - n_min, d_max - d_min,
                             facecolor=COLORS["support"], edgecolor=COLORS["navy"],
                             linewidth=1.0, linestyle="--", zorder=0))
    n_grid = np.logspace(np.log10(0.05), np.log10(70), 500)
    contour_context = 8192
    budget_colors = {1e19: COLORS["navy"], 1e22: COLORS["teal"], 1e24: COLORS["red"]}
    for budget, group in frame.groupby("budget_flops", sort=True):
        k = float(group.iloc[0]["K_product_B2"])
        d_curve = k / n_grid
        visible = (d_curve >= 0.08) & (d_curve <= 6000)
        ax_a.plot(n_grid[visible], d_curve[visible], color=budget_colors[float(budget)],
                  linewidth=1.0, alpha=0.60, linestyle="-", zorder=1)
        label_x = np.sqrt(n_min * n_max)
        label_y = k / label_x
        if 0.08 <= label_y <= 6000:
            ax_a.text(label_x * 1.04, label_y * 1.04,
                      f"{budget_label(float(budget))}", fontsize=7,
                      color=COLORS["dark"], rotation=-28, ha="left", va="bottom")

    for _, row in frame.sort_values(["budget_flops", "Lctx"]).iterrows():
        budget = float(row["budget_flops"])
        color = {1e19: COLORS["navy"], 1e22: COLORS["teal"], 1e24: COLORS["red"]}[budget]
        relaxed_inside = bool(row["relaxed_within_B1_support"])
        bounded_at_edge = row["bounded_support_status"] == "bounded_to_B1_support"
        ax_a.scatter(row["relaxed_N_B"], row["relaxed_D_B"],
                     marker="o" if relaxed_inside else "^", s=34,
                     facecolors="white", edgecolors=color, linewidths=1.0,
                     zorder=4)
        ax_a.scatter(row["bounded_N_B"], row["bounded_D_B"],
                     marker="s" if bounded_at_edge else "o", s=28,
                     facecolors=color, edgecolors="white", linewidths=0.45,
                     zorder=5)

    ax_a.set_xscale("log")
    ax_a.set_yscale("log")
    ax_a.set_xlim(0.05, 70)
    ax_a.set_ylim(0.08, 6000)
    ax_a.set_xlabel(r"Model size, $N$ (billion parameters)")
    ax_a.set_ylabel(r"Training data, $D$ (billion tokens)")
    ax_a.text(0.06, 0.94, "B1 observation range", transform=ax_a.transAxes,
              fontsize=7, color=COLORS["navy"], ha="left", va="top")
    ax_a.text(0.06, 0.89, rf"budget contours at $L_{{\rm ctx}}={contour_context}$",
              transform=ax_a.transAxes, fontsize=6.7, color=COLORS["grey"],
              ha="left", va="top")
    role_handles = [
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor="white",
               markeredgecolor=COLORS["dark"], markersize=5, label="Analytic inside B1"),
        Line2D([0], [0], marker="^", linestyle="None", markerfacecolor="white",
               markeredgecolor=COLORS["dark"], markersize=5, label="Analytic extrapolation"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=COLORS["teal"],
               markeredgecolor="white", markersize=5, label="Bounded solution"),
        Line2D([0], [0], marker="s", linestyle="None", markerfacecolor=COLORS["red"],
               markeredgecolor="white", markersize=5, label="B1 boundary solution"),
    ]
    budget_handles = [
        Line2D([0], [0], color=COLORS["navy"], lw=2, label=r"$10^{19}$ FLOPs"),
        Line2D([0], [0], color=COLORS["teal"], lw=2, label=r"$10^{22}$ FLOPs"),
        Line2D([0], [0], color=COLORS["red"], lw=2, label=r"$10^{24}$ FLOPs"),
    ]
    legend_1 = ax_a.legend(handles=role_handles, loc="lower left", fontsize=6.2,
                           handletextpad=0.4, borderpad=0.2, labelspacing=0.25)
    ax_a.add_artist(legend_1)
    ax_a.legend(handles=budget_handles, loc="upper right", fontsize=6.2,
                handletextpad=0.4, borderpad=0.2, labelspacing=0.25)

    # Panel b: bounded N and D frontiers by context.
    ax_b_right = ax_b_left.twinx()
    ax_b_right.spines["top"].set_visible(False)
    ax_b_right.spines["right"].set_visible(False)
    ax_b_right.tick_params(direction="out", length=3, width=0.7, pad=2,
                           colors=COLORS["grey"])
    budgets = sorted(frame["budget_flops"].unique())
    contexts = sorted(frame["Lctx"].unique())
    x = np.arange(len(budgets))
    for context in contexts:
        subset = frame[frame["Lctx"] == context].sort_values("budget_flops")
        color = CONTEXT_COLORS[int(context)]
        ax_b_left.plot(x, subset["bounded_N_B"], color=color, marker="o",
                       markersize=4.2, linewidth=1.25, label=rf"$L_{{\rm ctx}}={int(context)}$")
        ax_b_right.plot(x, subset["bounded_D_B"], color=color, marker="o",
                        markersize=4.2, linewidth=1.25, linestyle="--", alpha=0.75)
    ax_b_left.axhline(n_max, color=COLORS["navy"], linestyle=":", linewidth=0.9, alpha=0.8)
    ax_b_right.axhline(d_max, color=COLORS["grey"], linestyle=":", linewidth=0.9, alpha=0.8)
    ax_b_left.text(0.98, n_max, r"$N_{\max}$", transform=ax_b_left.get_yaxis_transform(),
                   ha="right", va="bottom", fontsize=6.5, color=COLORS["navy"])
    ax_b_right.text(0.98, d_max, r"$D_{\max}$", transform=ax_b_right.get_yaxis_transform(),
                    ha="right", va="bottom", fontsize=6.5, color=COLORS["grey"])
    ax_b_left.set_xticks(x, [budget_label(b) for b in budgets])
    ax_b_left.set_yscale("log")
    ax_b_right.set_yscale("log")
    ax_b_left.set_xlabel("Compute budget")
    ax_b_left.set_ylabel(r"Bounded $N^*$ (billion parameters)", color=COLORS["navy"])
    ax_b_right.set_ylabel(r"Bounded $D^*$ (billion tokens)", color=COLORS["grey"])
    ax_b_left.tick_params(axis="y", colors=COLORS["navy"])
    ax_b_left.set_ylim(0.06, 20)
    ax_b_right.set_ylim(0.1, 500)
    ax_b_left.legend(loc="upper left", bbox_to_anchor=(0.0, -0.13), fontsize=6.2,
                     ncol=3, handletextpad=0.35, columnspacing=0.8,
                     borderpad=0.2, labelspacing=0.25)
    style_axis(ax_b_left)
    ax_b_right.spines["right"].set_visible(False)
    ax_b_left.text(0.02, 0.04, "solid: $N^*$; dashed: $D^*$",
                   transform=ax_b_left.transAxes, fontsize=6.7, color=COLORS["grey"])
    return save_figure(fig, output_stem)


def write_latex_table(frame: pd.DataFrame, output_path: Path) -> None:
    rows: list[str] = []
    for _, row in frame.sort_values(["budget_flops", "Lctx"]).iterrows():
        budget = f"$10^{{{int(round(np.log10(row['budget_flops'])))} }}$".replace(" ", "")
        lctx = int(row["Lctx"])
        relaxed = f"({row['relaxed_N_B']:.3f}, {row['relaxed_D_B']:.3f})"
        bounded = f"({row['bounded_N_B']:.3f}, {row['bounded_D_B']:.3f})"
        relaxed_role = "域内解析点" if bool(row["relaxed_within_B1_support"]) else "外推解析点"
        status = "B1范围内" if row["bounded_support_status"] == "inside_B1_support" else "边界约束"
        rows.append(
            f"{budget} & {lctx} & {relaxed} & {row['relaxed_loss']:.4f} & "
            f"{bounded} & {row['bounded_loss']:.4f} & {status} & {relaxed_role} \\\\"  # noqa: W605
        )
    content = """% Generated directly from q3-nd-baseline-20260925-r01/tables/q3_nd_baseline_scenarios.csv
\\begin{table}[htbp]
  \\centering
  \\caption{M0 支持域内点与解析外推点的资源配置情景对比。}
  \\label{tab:q3-m0-nd-scenarios}
  \\scriptsize
  \\begin{tabular}{r r c r c r l l}
    \\toprule
    $C$ (FLOPs) & $L_{\\rm ctx}$ & $(N,D)_{\\rm relaxed}$ & $L_{\\rm relaxed}$ & $(N,D)_{\\rm bounded}$ & $L_{\\rm bounded}$ & 状态 & 解析点角色 \\\\
    \\midrule
""" + "\n".join(rows) + """
    \\bottomrule
  \\end{tabular}
  \\begin{flushleft}
  \\footnotesize
  注：解析点由放松后的预算约束得到；当其超出 B1 观测范围时，标记为外推解析点。
  有界点在 B1 观测范围内求解，并保留边界状态。两类 Loss 分别对应各自的数学情景。
  \\end{flushleft}
\\end{table}
"""
    output_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    run_dir = root / "experiments" / "runs" / "q3-nd-baseline-20260925-r01"
    source_csv = run_dir / "tables" / "q3_nd_baseline_scenarios.csv"
    metrics_path = run_dir / "metrics.json"
    out_dir = root / "paper" / "figures" / "q3-nd-baseline-nature-v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    table_path = root / "paper" / "tables" / "q3_m0_nd_scenarios.tex"
    table_path.parent.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(source_csv)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    support = metrics["support"]
    eta = float(frame["eta"].iloc[0])
    if len(frame) != 15:
        raise ValueError(f"Expected 15 scenarios, found {len(frame)}")
    if set(frame["bounded_support_status"]) != {"inside_B1_support", "bounded_to_B1_support"}:
        raise ValueError("Unexpected bounded support status")
    if frame["relaxed_loss"].isna().any() or frame["bounded_loss"].isna().any():
        raise ValueError("Loss columns contain missing values")

    output_stem = out_dir / "fig_q3_m0_nd_frontier_nature_v1"
    outputs = draw_frontier_figure(frame, output_stem, support, eta)
    write_latex_table(frame, table_path)

    manifest = {
        "figure_id": "fig_q3_m0_nd_frontier_nature_v1",
        "run_id": metrics["run_id"],
        "backend": "python-matplotlib",
        "source_csv": str(source_csv.relative_to(root)).replace("\\", "/"),
        "source_csv_sha256": sha256(source_csv),
        "metrics_json": str(metrics_path.relative_to(root)).replace("\\", "/"),
        "metrics_json_sha256": sha256(metrics_path),
        "scenario_count": int(len(frame)),
        "support": support,
        "contexts": sorted(int(v) for v in frame["Lctx"].unique()),
        "budgets_flops": sorted(float(v) for v in frame["budget_flops"].unique()),
        "contour_context": 8192,
        "outputs": [str(Path(p).relative_to(root)).replace("\\", "/") for p in outputs],
        "table": str(table_path.relative_to(root)).replace("\\", "/"),
        "table_sha256": sha256(table_path),
        "roles": {
            "relaxed_inside": "analytic point inside B1 observed range",
            "relaxed_outside": "analytic extrapolation diagnostic",
            "bounded": "explicitly constrained solution within B1 observed range",
        },
    }
    (out_dir / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
