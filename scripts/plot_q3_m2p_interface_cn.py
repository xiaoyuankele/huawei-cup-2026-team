"""绘制 M2/P 接口映射造成的条件资源配置变化（Python / Nature 风格）。"""

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


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments" / "runs" / "q2-q3-interface-sensitivity-20260926-r01"
CSV = RUN / "tables" / "m2_q3_interface_summary.csv"
OUT = ROOT / "paper" / "figures" / "q3-m2p-interface-cn-v1"


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
    df = pd.read_csv(CSV)
    sub = df.loc[(df["cost_family"] == "exponential") & (df["Lctx"] == 2048) & (df["budget_flops"] == 1e22)].copy()
    if len(sub) != 5:
        raise ValueError("代表性接口情景应包含五种映射")
    order = ["M2_partial_raw", "M2_interval_low", "M2_interval_mid", "M2_partial_renorm", "M2_interval_high"]
    labels = ["原始", "低", "中", "重归一", "高"]
    sub["order"] = pd.Categorical(sub["mapping_scenario"], categories=order, ordered=True)
    sub = sub.sort_values("order")
    cn = chinese_font()
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"], "axes.unicode_minus": False, "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 600})
    fig, ax = plt.subplots(figsize=(4.9, 3.55))
    fig.subplots_adjust(left=0.16, right=0.86, bottom=0.19, top=0.78)
    x = sub["N_B_median"].to_numpy(float)
    y = sub["D_B_median"].to_numpy(float)
    q = sub["Q_B_median"].to_numpy(float)
    for i in range(len(sub) - 1):
        ax.annotate("", xy=(x[i + 1], y[i + 1]), xytext=(x[i], y[i]), arrowprops={"arrowstyle": "->", "color": "#AAB5BC", "lw": 0.9})
    scatter = ax.scatter(x, y, c=q, cmap=mpl.colors.LinearSegmentedColormap.from_list("qteal", ["#D8EEF0", "#19636B"]), vmin=0.1, vmax=1.0, s=95, edgecolors="white", linewidths=0.9, zorder=3)
    offsets = [(4, 5), (4, 5), (4, 5), (4, 5), (-58, 5)]
    for xi, yi, qi, label, offset in zip(x, y, q, labels, offsets):
        ax.annotate(f"{label}  $Q_B={qi:.3f}$", xy=(xi, yi), xytext=offset, textcoords="offset points", fontsize=6.6, fontproperties=cn, color="#17343B")
    ax.set_xlim(8.02, 8.75)
    ax.set_ylim(168, 196)
    ax.set_xlabel("最优参数量 $N^*$（十亿参数）", fontproperties=cn, fontsize=8.7)
    ax.set_ylabel("最优训练数据量 $D^*$（十亿 tokens）", fontproperties=cn, fontsize=8.7)
    ax.set_title("M2/P 接口映射造成的条件资源配置变化", fontproperties=cn, fontsize=10.5, fontweight="bold", pad=10)
    cbar = fig.colorbar(scatter, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("假设 $Q_B$", fontproperties=cn, fontsize=8.0)
    cbar.ax.tick_params(labelsize=7, length=2)
    ax.grid(color="#E2E7EA", linewidth=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    stem = OUT / "fig_q3_m2p_interface_cn_single_v2"
    for suffix, kwargs in (("svg", {}), ("pdf", {}), ("png", {"dpi": 600}), ("tiff", {"dpi": 600})):
        fig.savefig(stem.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)
    plt.close(fig)
    manifest = {"figure_id": "fig_q3_m2p_interface_cn_single_v2", "title": "M2/P 接口映射造成的条件资源配置变化（中文单张图）", "source_run": str(RUN.relative_to(ROOT)), "source_csv": str(CSV.relative_to(ROOT)), "source_csv_sha256": sha256(CSV), "filter": {"cost_family": "exponential", "Lctx": 2048, "budget_flops": 1e22, "candidate_count": 6}, "mapping_scenarios": order, "outputs": [p.name for p in sorted(OUT.glob("fig_q3_m2p_interface_cn_single_v2.*"))]}
    (OUT / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "figure_contract.md").write_text("""# Q3 M2/P 接口中文单张图契约

核心结论：在代表性预算和上下文下，不同的假设接口映射会改变 $Q_B^*$、$N^*$、$D^*$ 与质量成本占比。

图中以 $N^*-D^*$ 平面展示条件资源配置变化，并用颜色标记假设 $Q_B$。$Q_A(p)$ 只作为 A 侧标签；映射不构成 $Q_A$ 与 $Q_B$ 的实证关系，不能识别 $G_{\\mathrm{bridge}}$，也不产生新增观测样本。
""", encoding="utf-8")


if __name__ == "__main__":
    main()
