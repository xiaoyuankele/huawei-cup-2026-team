"""绘制 Q3 M1 原生 Q_B 情景图（Python / Nature 风格）。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments" / "runs" / "q3-q-conditional-20260925-r01"
CSV = RUN / "tables" / "q3_q_conditional_scenarios.csv"
OUT = ROOT / "paper" / "figures" / "q3-m1-qb-cn-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def chinese_font() -> FontProperties:
    for candidate in (
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ):
        if candidate.exists():
            return FontProperties(fname=str(candidate))
    return FontProperties(family="sans-serif")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV)
    expected = {"exponential", "power", "logarithmic"}
    if set(df["cost_family"]) != expected or len(df) != 45:
        raise ValueError("M1 情景表应包含 45 行和三类质量成本")

    cn = chinese_font()
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 600,
        }
    )

    contexts = [2048, 4096, 8192, 32768, 131072]
    budgets = [1e19]
    families = ["exponential", "power", "logarithmic"]
    family_cn = {"exponential": "指数型", "power": "幂函数型", "logarithmic": "对数渐进型"}
    colors = {"exponential": "#19636B", "power": "#7B6FA8", "logarithmic": "#B34745"}
    linestyles = {"exponential": "-", "power": (0, (4, 2)), "logarithmic": (0, (1, 1))}

    fig, ax = plt.subplots(figsize=(4.9, 3.45))
    fig.subplots_adjust(left=0.17, right=0.97, bottom=0.20, top=0.78)
    for family in families:
        sub = df.loc[(df["cost_family"] == family) & (df["budget_flops"] == 1e19)].sort_values("Lctx")
        ax.plot(sub["Lctx"], sub["Q"], color=colors[family], linestyle=linestyles[family], linewidth=1.8, marker="o", markersize=4.8, label=family_cn[family])
        row = sub.tail(1).iloc[0]
        ax.annotate(f"{float(row['Q']):.3f}", xy=(row["Lctx"], row["Q"]), xytext=(5, 2), textcoords="offset points", fontsize=6.7, color=colors[family])
    ax.set_xscale("log")
    ax.set_xlim(1700, 170000)
    ax.set_ylim(0.1, 1.04)
    ax.set_xticks(contexts)
    ax.set_xticklabels(["2,048", "4,096", "8,192", "32,768", "131,072"], rotation=35, ha="right", fontsize=7)
    ax.set_yticks([0.1, 0.4, 0.7, 1.0])
    ax.tick_params(axis="y", labelsize=7, length=2)
    ax.set_xlabel("上下文长度 $L_{\\mathrm{ctx}}$", fontproperties=cn, fontsize=8.7)
    ax.set_ylabel("最优原生质量 $Q_B^*$", fontproperties=cn, fontsize=8.7)
    ax.set_title("M1 原生质量条件下的最优 $Q_B^*$（$C=10^{19}$ FLOPs）", fontproperties=cn, fontsize=10.2, fontweight="bold", pad=10)
    ax.legend(frameon=False, prop=cn, fontsize=6.8, loc="lower right", title="质量成本", title_fontproperties=cn)
    ax.grid(True, axis="both", color="#E2E7EA", linewidth=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    stem = OUT / "fig_q3_m1_qb_cn_single_v2"
    for suffix, kwargs in (("svg", {}), ("pdf", {}), ("png", {"dpi": 600}), ("tiff", {"dpi": 600})):
        fig.savefig(stem.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)
    plt.close(fig)

    manifest = {
        "figure_id": "fig_q3_m1_qb_cn_single_v2",
        "title": "M1 原生质量条件下的最优 Q_B（中文单张图）",
        "source_run": str(RUN.relative_to(ROOT)),
        "source_csv": str(CSV.relative_to(ROOT)),
        "source_csv_sha256": sha256(CSV),
        "rows": 15,
        "filter": {"cost_family": families, "budget_flops": budgets, "Lctx": contexts},
        "marker_semantics": {"triangle": "Q_B 触及 B6/B7 支持上界 1.0"},
        "outputs": [p.name for p in sorted(OUT.glob("fig_q3_m1_qb_cn_single_v2.*"))],
    }
    (OUT / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "figure_contract.md").write_text(
        """# Q3 M1 原生 Q_B 中文单张图契约

核心结论：在冻结的 B1、B6/B7 支持域和三类质量成本假设下，预算与上下文共同改变最优原生质量变量 $Q_B^*$。

图形选取低预算代表性情景 $C=10^{19}$ FLOPs，展示五档上下文下三类质量成本的 $Q_B^*$ 曲线；完整 45 行情景仍以表格为准。
$Q_B$ 是 B6/B7 原生变量，不是 Q1 的 $Q_A$；曲线不代表真实训练质量已经饱和。
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
