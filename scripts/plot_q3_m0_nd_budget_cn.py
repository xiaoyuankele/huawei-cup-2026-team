"""绘制问题三 M0 的中文预算敏感性单图。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments" / "runs" / "q3-nd-baseline-20260925-r01"
CSV = RUN / "tables" / "q3_nd_baseline_scenarios.csv"
METRICS = RUN / "metrics.json"
OUT = ROOT / "paper" / "figures" / "q3-nd-budget-cn-v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def choose_cn_font() -> FontProperties:
    for path in (
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ):
        if path.exists():
            return FontProperties(fname=str(path))
    return FontProperties(family="sans-serif")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV)
    df["Lctx"] = df["Lctx"].astype(int)
    df = df.sort_values(["Lctx", "budget_flops"])
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    support = metrics["support"]
    budgets = sorted(df["budget_flops"].unique())
    contexts = sorted(df["Lctx"].unique())
    if len(df) != 15 or len(budgets) != 3 or len(contexts) != 5:
        raise ValueError("预算敏感性图需要15行、3个预算和5个上下文长度")
    cn = choose_cn_font()

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans SC", "SimHei", "Arial"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.dpi": 160,
            "savefig.dpi": 600,
        }
    )

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(7.8, 7.3),
        sharex=True,
        gridspec_kw={"height_ratios": [1, 1], "hspace": 0.12},
        constrained_layout=False,
    )
    colors = ["#1E4E79", "#138A8A", "#6B6FAF", "#D08445", "#B34745"]
    context_colors = dict(zip(contexts, colors))
    x = np.asarray(budgets, dtype=float)
    xlabels = [r"$10^{19}$", r"$10^{22}$", r"$10^{24}$"]

    panels = [
        ("bounded_N_B", "参数量 $N^*$（十亿）", support["N_max_B"], "N_{\max}"),
        ("bounded_D_B", "训练数据量 $D^*$（十亿 tokens）", support["D_max_B"], "D_{\max}"),
    ]
    for ax, (column, ylabel, bound, bound_label) in zip(axes, panels):
        ax.set_xscale("log")
        ax.set_xlim(min(budgets) / 1.8, max(budgets) * 1.8)
        ax.grid(True, which="major", color="#D9DEE5", linewidth=0.65, alpha=0.8)
        ax.grid(True, which="minor", color="#EEF1F4", linewidth=0.45, alpha=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.axhline(bound, color="#555555", linewidth=1.05, linestyle=(0, (3, 2)), zorder=1)
        ax.text(
            max(budgets) * 1.42,
            bound * 1.05,
            fr"${bound_label}={bound:.3g}$",
            color="#555555",
            fontsize=9,
            fontproperties=cn,
            ha="right",
            va="bottom",
        )
        for context in contexts:
            sub = df.loc[df["Lctx"] == context].sort_values("budget_flops")
            is_boundary = sub["bounded_support_status"].ne("inside_B1_support").to_numpy()
            ax.plot(
                sub["budget_flops"],
                sub[column],
                color=context_colors[context],
                linewidth=1.65,
                marker="o",
                markersize=5.4,
                markerfacecolor="white",
                markeredgewidth=1.25,
                markeredgecolor=context_colors[context],
                zorder=3,
            )
            if is_boundary.any():
                ax.scatter(
                    sub.loc[is_boundary, "budget_flops"],
                    sub.loc[is_boundary, column],
                    marker="s",
                    s=45,
                    facecolors=context_colors[context],
                    edgecolors="white",
                    linewidths=0.8,
                    zorder=4,
                )
        ax.set_ylabel(ylabel, fontproperties=cn, fontsize=10.5)
        ax.tick_params(axis="both", labelsize=9)

    axes[0].set_ylim(0.1, 15)
    axes[1].set_ylim(0.1, 390)
    axes[1].set_xticks(budgets)
    axes[1].set_xticklabels(xlabels)
    axes[1].set_xlabel("计算预算 $C$（FLOPs，对数刻度）", fontproperties=cn, fontsize=10.5)
    axes[0].set_title(
        "预算变化下 M0 的有界最优配置",
        fontproperties=cn,
        fontsize=13,
        pad=10,
    )
    axes[0].text(
        0.01,
        0.91,
        "（a）最优参数量",
        transform=axes[0].transAxes,
        fontproperties=cn,
        fontsize=9.5,
        color="#333333",
    )
    axes[1].text(
        0.01,
        0.91,
        "（b）最优训练数据量",
        transform=axes[1].transAxes,
        fontproperties=cn,
        fontsize=9.5,
        color="#333333",
    )

    context_handles = [
        Line2D(
            [],
            [],
            color=context_colors[c],
            linewidth=1.8,
            marker="o",
            markerfacecolor="white",
            markeredgecolor=context_colors[c],
            markersize=5.5,
            label=fr"$L_{{\rm ctx}}={c}$",
        )
        for c in contexts
    ]
    context_handles.append(
        Line2D(
            [],
            [],
            color="#555555",
            linewidth=1.0,
            linestyle=(0, (3, 2)),
            label="B1上限",
        )
    )
    context_handles.append(
        Line2D(
            [],
            [],
            color="#555555",
            marker="s",
            linestyle="None",
            markerfacecolor="#555555",
            markeredgecolor="white",
            markersize=6,
            label="支持边界解",
        )
    )
    fig.legend(
        handles=context_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        ncol=4,
        frameon=False,
        prop=cn,
        fontsize=8.8,
        columnspacing=1.0,
        handlelength=2.0,
    )
    fig.subplots_adjust(left=0.14, right=0.98, top=0.92, bottom=0.16)

    stem = OUT / "fig_q3_m0_nd_budget_cn_single_v1"
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)

    manifest = {
        "figure_id": "fig_q3_m0_nd_budget_cn_single_v1",
        "title": "预算变化下 M0 的有界最优配置（中文单图）",
        "source_run": "q3-nd-baseline-20260925-r01",
        "source_csv": str(CSV.relative_to(ROOT)),
        "source_csv_sha256": sha256(CSV),
        "metrics": str(METRICS.relative_to(ROOT)),
        "metrics_sha256": sha256(METRICS),
        "rows": int(len(df)),
        "budgets_flops": [float(v) for v in budgets],
        "contexts": [int(v) for v in contexts],
        "visual_semantics": {
            "open_circle": "bounded solution inside B1 support",
            "filled_square": "bounded solution at B1 support boundary",
            "dashed_horizontal": "B1 observed upper support bound",
        },
        "outputs": [
            stem.with_suffix(".svg").name,
            stem.with_suffix(".pdf").name,
            stem.with_suffix(".png").name,
            stem.with_suffix(".tiff").name,
        ],
    }
    (OUT / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "figure_contract.md").write_text(
        """# Q3 M0 中文预算敏感性单图契约\n\n"
        "图形展示三个预算和五种上下文长度下，M0 在 B1 支持域内的有界最优 `N*` 与 `D*`。\n"
        "虚线为观测支持上限，方形表示被支持上限约束的场景。所有数值直接读取场景 CSV。\n"
        "图形用于条件基线的预算敏感性展示，不扩展为跨来源的普适标度律。\n""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
