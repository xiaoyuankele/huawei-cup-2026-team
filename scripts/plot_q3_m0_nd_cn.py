"""绘制问题三 M0 的中文单图：B1 支持域与 N-D 预算前沿。

图形直接读取 q3-nd-baseline-20260925-r01 的场景 CSV；不重新拟合参数，
并明确区分无边界解析点、支持域内有界点和支持域外解析外推点。
"""

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
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments" / "runs" / "q3-nd-baseline-20260925-r01"
CSV = RUN / "tables" / "q3_nd_baseline_scenarios.csv"
METRICS = RUN / "metrics.json"
OUT = ROOT / "paper" / "figures" / "q3-nd-baseline-cn-v1"
ETA = 2e-4
LCTX = 8192


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def choose_cn_font() -> FontProperties:
    candidates = [
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return FontProperties(fname=str(path))
    return FontProperties(family="sans-serif")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV)
    df = df.loc[df["Lctx"].astype(int) == LCTX].copy()
    if len(df) != 3:
        raise ValueError(f"Lctx={LCTX} 应有3个预算场景，实际为 {len(df)}")
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    support = metrics["support"]
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

    fig, ax = plt.subplots(figsize=(7.8, 6.35), constrained_layout=False)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.05, 70)
    ax.set_ylim(0.08, 7000)
    ax.grid(True, which="major", color="#D9DEE5", linewidth=0.65, alpha=0.75)
    ax.grid(True, which="minor", color="#EEF1F4", linewidth=0.45, alpha=0.75)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # B1 的观测支持矩形。
    rect = Rectangle(
        (support["N_min_B"], support["D_min_B"]),
        support["N_max_B"] - support["N_min_B"],
        support["D_max_B"] - support["D_min_B"],
        facecolor="#DCEAF4",
        edgecolor="#326A8A",
        linewidth=1.25,
        alpha=0.48,
        zorder=1,
        label="B1观测支持域",
    )
    ax.add_patch(rect)

    palette = {1e19: "#1E4E79", 1e22: "#138A8A", 1e24: "#B34745"}
    labels = {1e19: r"10^{19}", 1e22: r"10^{22}", 1e24: r"10^{24}"}
    n_grid = np.logspace(np.log10(0.05), np.log10(70), 600)

    # 在代表性上下文长度 Lctx=8192 下绘制三条预算双曲线。
    for _, row in df.sort_values("budget_flops").iterrows():
        budget = float(row["budget_flops"])
        k = budget / (1e18 * (6.0 + ETA * LCTX))
        d_grid = k / n_grid
        ax.plot(
            n_grid,
            d_grid,
            color=palette[budget],
            linewidth=1.65,
            alpha=0.92,
            label=fr"预算 $C={labels[budget]}$ FLOPs",
            zorder=2,
        )

        relaxed_n = float(row["relaxed_N_B"])
        relaxed_d = float(row["relaxed_D_B"])
        bounded_n = float(row["bounded_N_B"])
        bounded_d = float(row["bounded_D_B"])
        relaxed_inside = bool(row["relaxed_within_B1_support"])
        bounded_on_boundary = row["bounded_support_status"] != "inside_B1_support"

        # 空心点表示无边界解析解；三角形表示其落在 B1 支持域之外。
        ax.scatter(
            [relaxed_n],
            [relaxed_d],
            s=112,
            marker="o" if relaxed_inside else "^",
            facecolors="white",
            edgecolors=palette[budget],
            linewidths=1.55,
            zorder=5,
        )
        # 有界解覆盖在解析点上；边界解用方形标记。
        ax.scatter(
            [bounded_n],
            [bounded_d],
            s=45,
            marker="s" if bounded_on_boundary else "o",
            facecolors=palette[budget],
            edgecolors="white",
            linewidths=0.8,
            zorder=6,
        )
        if bounded_on_boundary:
            ax.plot(
                [relaxed_n, bounded_n],
                [relaxed_d, bounded_d],
                linestyle=(0, (2, 2)),
                color=palette[budget],
                linewidth=0.85,
                alpha=0.7,
                zorder=3,
            )

    ax.text(
        support["N_min_B"] * 1.10,
        support["D_max_B"] / 1.45,
        "B1观测支持域",
        color="#275B77",
        fontsize=9.5,
        fontproperties=cn,
        zorder=7,
    )
    ax.set_xlabel("参数量 $N$（十亿）", fontproperties=cn, fontsize=11)
    ax.set_ylabel("训练数据量 $D$（十亿 tokens）", fontproperties=cn, fontsize=11)
    ax.set_title(
        "M0模型在预算约束下的N–D最优配置（上下文长度 $L_{\\rm ctx}=8192$）",
        fontproperties=cn,
        fontsize=13,
        pad=10,
    )

    # 两组标记的解释，预算颜色由曲线图例给出。
    handles, labels_ = ax.get_legend_handles_labels()
    handles.extend(
        [
            plt.Line2D([], [], marker="o", linestyle="None", markerfacecolor="white", markeredgecolor="#333333", markersize=8, label="解析解（支持域内）"),
            plt.Line2D([], [], marker="^", linestyle="None", markerfacecolor="white", markeredgecolor="#333333", markersize=8, label="解析外推点"),
            plt.Line2D([], [], marker="o", linestyle="None", markerfacecolor="#555555", markeredgecolor="white", markersize=6, label="有界解"),
            plt.Line2D([], [], marker="s", linestyle="None", markerfacecolor="#555555", markeredgecolor="white", markersize=6, label="支持边界解"),
        ]
    )
    labels_.extend(["解析解（支持域内）", "解析外推点", "有界解", "支持边界解"])
    legend = ax.legend(
        handles,
        labels_,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        frameon=False,
        prop=cn,
        fontsize=8.5,
        handlelength=2.0,
        borderaxespad=0.2,
        ncol=3,
        columnspacing=1.1,
    )
    legend._legend_box.align = "left"

    fig.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.27)

    stem = OUT / "fig_q3_m0_nd_cn_single_v1"
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)

    manifest = {
        "figure_id": "fig_q3_m0_nd_cn_single_v1",
        "title": "M0模型在预算约束下的N-D最优配置（中文单图）",
        "source_run": "q3-nd-baseline-20260925-r01",
        "source_csv": str(CSV.relative_to(ROOT)),
        "source_csv_sha256": sha256(CSV),
        "metrics": str(METRICS.relative_to(ROOT)),
        "metrics_sha256": sha256(METRICS),
        "filter": {"Lctx": LCTX, "rows": int(len(df))},
        "outputs": [
            stem.with_suffix(".svg").name,
            stem.with_suffix(".pdf").name,
            stem.with_suffix(".png").name,
            stem.with_suffix(".tiff").name,
        ],
        "encoding": "N,D in billions; budget C in FLOPs; Q and p fixed per M0 run",
        "visual_semantics": {
            "hollow_circle": "relaxed analytic solution within B1 support",
            "hollow_triangle": "relaxed analytic extrapolation outside B1 support",
            "filled_circle": "bounded solution inside B1 support",
            "filled_square": "bounded solution at B1 support boundary",
        },
    }
    (OUT / "figure_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "figure_contract.md").write_text(
        """# Q3 M0 中文单图契约\n\n"
        "图形展示 B1/Pythia 条件基线在 `Lctx=8192` 下的 N-D 预算前沿。\n"
        "预算双曲线、解析点和有界点均由 `q3_nd_baseline_scenarios.csv` 直接绘制。\n"
        "空心三角形仅表示支持域外的解析外推；实心方形表示支持域边界上的有界解。\n"
        "该图用于说明 M0 的条件配置关系，不作为跨来源标度律或 Q、p 独立作用的证据。\n""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
