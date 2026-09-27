"""绘制上下文注意力成本与训练成本的解析比值。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper" / "sections" / "q3_subproblem2_m1_ndqb.tex"
OUT = ROOT / "paper" / "figures" / "q3-context-cost-cn-v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def chinese_font() -> FontProperties:
    for candidate in (Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"), Path(r"C:\Windows\Fonts\simhei.ttf"), Path(r"C:\Windows\Fonts\simsun.ttc")):
        if candidate.exists():
            return FontProperties(fname=str(candidate))
    return FontProperties(family="sans-serif")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cn = chinese_font()
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "axes.unicode_minus": False, "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 600})
    eta = 2e-4
    x = np.logspace(np.log10(512), np.log10(262144), 600)
    ratio = x / 30000.0
    fig, ax = plt.subplots(figsize=(3.55, 2.75))
    fig.subplots_adjust(left=0.18, right=0.98, bottom=0.22, top=0.80)
    ax.plot(x, ratio, color="#19636B", linewidth=2.0)
    ax.fill_between(x, ratio, 1.0, where=ratio <= 1.0, color="#D8EEF0", alpha=0.65, linewidth=0)
    ax.fill_between(x, ratio, 1.0, where=ratio >= 1.0, color="#F3D8D1", alpha=0.65, linewidth=0)
    ax.axhline(1.0, color="#4C5963", linestyle=(0, (3, 2)), linewidth=0.9)
    ax.axvline(30000, color="#B34745", linestyle=(0, (3, 2)), linewidth=1.0)
    ax.scatter([30000], [1.0], s=26, color="#B34745", zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([2048, 4096, 8192, 32768, 131072])
    ax.set_xticklabels(["2,048", "4,096", "8,192", "32,768", "131,072"], rotation=35, ha="right", fontsize=7)
    ax.set_yticks([0.1, 1.0, 10.0])
    ax.set_yticklabels(["0.1", "1", "10"], fontsize=7)
    ax.set_xlabel("上下文长度 $L_{\\mathrm{ctx}}$", fontproperties=cn, fontsize=8.5)
    ax.set_ylabel(r"$C_{\mathrm{attn}}/C_{\mathrm{train}}$", fontsize=8.5)
    ax.set_title("上下文注意力成本与训练成本的结构比值", fontproperties=cn, fontsize=9.5, fontweight="bold", pad=9)
    ax.text(0.06, 0.16, "比值 < 1", transform=ax.transAxes, ha="left", va="bottom", fontsize=7, fontproperties=cn, color="#19636B")
    ax.annotate("结构临界点\n$L_{\\mathrm{ctx}}=30000$", xy=(30000, 1), xycoords="data", xytext=(0.66, 0.72), textcoords="axes fraction", arrowprops={"arrowstyle": "-", "color": "#B34745", "lw": 0.8}, fontsize=6.5, fontproperties=cn, color="#8F3E37")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="major", color="#E2E7EA", linewidth=0.55)
    stem = OUT / "fig_q3_context_cost_cn_single_v1"
    for suffix, kwargs in (("svg", {}), ("pdf", {}), ("png", {"dpi": 600}), ("tiff", {"dpi": 600})):
        fig.savefig(stem.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)
    plt.close(fig)
    manifest = {"figure_id": "fig_q3_context_cost_cn_single_v1", "title": "上下文成本转移临界点（中文单图）", "source_formula": str(SOURCE.relative_to(ROOT)), "source_sha256": sha256(SOURCE), "eta": eta, "critical_context": 30000, "outputs": [p.name for p in sorted(OUT.glob("fig_q3_context_cost_cn_single_v1.*"))]}
    (OUT / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "figure_contract.md").write_text("""# Q3 上下文成本转移中文单图契约

核心结论：在当前成本函数中，注意力成本与训练成本的结构比值为 $L_{\\mathrm{ctx}}/30000$。

$L_{\\mathrm{ctx}}=30000$ 是成本结构临界点，不是模型效果已经验证的临界点，也不是质量变量的经验转折点。
""", encoding="utf-8")


if __name__ == "__main__":
    main()
