"""Four descriptive Q1.2 data figures in the manuscript's established style."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.font_manager import FontProperties, fontManager


HERE = Path(__file__).resolve().parent
DATA = (HERE.parents[2] / "experiments" / "runs"
        / "q1-conflict-trial-20260924-r01" / "results")
CHINESE_FONT = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
if CHINESE_FONT.exists():
    fontManager.addfont(str(CHINESE_FONT))
HEADING_FONT = Path("/System/Library/Fonts/STHeiti Medium.ttc")
TITLE_FONT = (FontProperties(fname=str(HEADING_FONT)) if HEADING_FONT.exists()
              else FontProperties(family="Microsoft YaHei", weight="bold"))

INK = "#29363D"
TEAL = "#527F88"
PALE = "#C8DEDF"
WARM = "#C17855"
GREY = "#738087"
GRID = "#EDF0F1"
SOFT = "#D1D8DB"
SERIES = (
    ("A1_holdout", "A1 内部留出", GREY, "-", "o"),
    ("A2_new", "A2 新增论文", WARM, "--", "D"),
    ("A3_new", "A3 新增代码", TEAL, "-.", "s"),
)
DIMENSIONS = ("value", "expression", "cleanliness", "no_ads", "nonrepetition")
DIM_LABELS = ("价值", "表达", "整洁", "无广告", "非重复")
DOMAIN_LABELS = {
    "arxiv": "arXiv", "book": "Book", "c4": "C4",
    "commoncrawl": "CommonCrawl", "github": "GitHub",
    "stackexchange": "StackExchange", "wikipedia": "Wikipedia",
}

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial Unicode MS", "Microsoft YaHei", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.3,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": GREY,
    "ytick.color": INK,
    "legend.frameon": False,
})


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def base(height: float, title: str, subtitle: str, footnote: str):
    fig = plt.figure(figsize=(7.2047244094, height))
    fig.text(.035, .965, title, fontsize=10.5, fontproperties=TITLE_FONT, va="top")
    fig.text(.975, .96, "质量冲突 · 有限补偿", fontsize=8, color=GREY,
             ha="right", va="top")
    fig.text(.035, .905, subtitle, fontsize=7.7, color=GREY, va="top")
    fig.text(.035, .045, footnote, fontsize=7, color=GREY, va="bottom")
    return fig


def axis_style(ax, grid_axis="y"):
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#7F8A90")
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", width=.6, length=3)
    ax.grid(axis=grid_axis, color=GRID, linewidth=.55)
    ax.set_axisbelow(True)


def export(fig, stem: str):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    outside = []
    for artist in fig.findobj(mpl.text.Text):
        if not artist.get_visible() or not artist.get_text():
            continue
        if artist.axes is not None and artist.get_clip_on():
            continue
        bounds = artist.get_window_extent(renderer)
        if (bounds.x0 < -.6 or bounds.y0 < -.6 or
                bounds.x1 > fig.bbox.width + .6 or bounds.y1 > fig.bbox.height + .6):
            outside.append(artist.get_text())
    if outside:
        raise ValueError(f"{stem}: labels outside canvas: {outside}")
    fig.savefig(HERE / f"{stem}.svg", facecolor="white")
    fig.savefig(HERE / f"{stem}.pdf", facecolor="white")
    fig.savefig(HERE / f"{stem}.png", dpi=600, facecolor="white")
    fig.savefig(HERE / f"{stem}.tiff", dpi=600, facecolor="white",
                pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


def figure31_pairs(summary):
    counts = {r["partition"]: int(r["n"]) for r in summary if r["domain"] == "ALL"}
    pairs = read("conflict_pairs.csv")
    selected = {part: [r for r in pairs if r["partition"] == part]
                for part, *_ in SERIES}
    expected = {(a, b) for a in DIMENSIONS for b in DIMENSIONS if a != b}
    for part, rows in selected.items():
        if len(rows) != 20 or {(r["high"], r["low"]) for r in rows} != expected:
            raise ValueError(f"Incomplete directed pairs for {part}")
        if not all(0 <= float(r["rate"]) <= 1 for r in rows):
            raise ValueError(f"Invalid rate for {part}")

    fig = base(4.02, "高分与低分信号的冲突组合如何变化？",
               "行：高分维度  /  列：低分维度  /  单元格为分区内记录的占比（%）",
               "一条记录可满足多个配对，单元格不能相加；对角线无定义。阈值由 A1 拟合集冻结。")
    cmap = LinearSegmentedColormap.from_list(
        "repo_teal", ["#F5F8F7", "#D5E5E3", "#8BB3B7", TEAL, "#234954"])
    from matplotlib.colors import Normalize
    norm = Normalize(0, 60)
    for i, (part, label, _, _, _) in enumerate(SERIES):
        ax = fig.add_axes([.16 + i * .278, .205, .235, .49])
        values = {(r["high"], r["low"]): 100 * float(r["rate"])
                  for r in selected[part]}
        matrix = [[values.get((a, b), float("nan")) for b in DIMENSIONS]
                  for a in DIMENSIONS]
        ax.imshow(matrix, cmap=cmap, norm=norm, aspect="equal", interpolation="nearest")
        ax.set_xticks(range(5), DIM_LABELS, fontsize=7.0)
        ax.set_yticks(range(5), DIM_LABELS if i == 0 else [""] * 5, fontsize=7.0)
        ax.tick_params(length=0, pad=3)
        ax.set_xticks([j - .5 for j in range(6)], minor=True)
        ax.set_yticks([j - .5 for j in range(6)], minor=True)
        ax.grid(which="minor", color="white", linewidth=.8)
        ax.tick_params(which="minor", length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for row in range(5):
            for col in range(5):
                val = matrix[row][col]
                if row == col:
                    ax.text(col, row, "—", ha="center", va="center", fontsize=8,
                            color=SOFT)
                else:
                    ax.text(col, row, f"{val:.1f}", ha="center", va="center",
                            fontsize=7.0, color="white" if val >= 34 else INK)
        fig.text(.16 + i * .278, .745, f"{chr(97+i)}  {label}", fontsize=8.4,
                 fontproperties=TITLE_FONT)
        fig.text(.16 + i * .278, .711, f"n = {counts[part]:,}", fontsize=7.1,
                 color=GREY)
    cax = fig.add_axes([.37, .115, .32, .016])
    cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, orientation="horizontal",
                                   ticks=[0, 20, 40, 60])
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2, labelsize=7)
    export(fig, "fig3_1_conflict_pair_heatmap")


def figure32_domains(summary):
    rows = [r for r in summary if r["partition"] == "A1_full" and r["domain"] != "ALL"]
    if len(rows) != 7 or {r["domain"] for r in rows} != set(DOMAIN_LABELS):
        raise ValueError("Expected seven A1 domains")
    if sum(int(r["n"]) for r in rows) != 51230:
        raise ValueError("A1 domain counts do not reconcile")
    overall = next(r for r in summary if r["partition"] == "A1_full" and r["domain"] == "ALL")
    rows.sort(key=lambda r: float(r["conflict_rate"]), reverse=True)
    fig = base(4.35, "A1 各领域的候选冲突率差异",
               "A1 全量 n = 51,230  /  五组质量信号  /  低、高分位阈值分别为 20% 与 80%",
               "领域比例为描述统计；Book 样本量仅 171。虚线是 A1 总体冲突率，并非显著性界限。")
    ax = fig.add_axes([.25, .18, .68, .61])
    rates = [100 * float(r["conflict_rate"]) for r in rows]
    y = list(range(7))
    ax.barh(y, rates, height=.56, color=TEAL)
    ax.invert_yaxis()
    ax.set_xlim(0, 67)
    ax.set_xticks([0, 20, 40, 60])
    ax.set_xlabel("候选冲突率（%）", labelpad=7)
    ax.set_yticks([])
    axis_style(ax, "x")
    line = 100 * float(overall["conflict_rate"])
    ax.axvline(line, color=WARM, linestyle=(0, (3, 3)), linewidth=1.1)
    fig.text(.686, .825, f"A1 总体 {line:.2f}%", color=WARM,
             fontsize=7.2, ha="center")
    for yy, r, rate in zip(y, rows, rates):
        ax.text(-.022, yy - .09, DOMAIN_LABELS[r["domain"]],
                transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=8.2, clip_on=False)
        ax.text(-.022, yy + .20, f'n = {int(r["n"]):,}',
                transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=7, color=GREY, clip_on=False)
        near_reference = rate < line and abs(rate - line) < 4
        ax.text(rate - .65 if near_reference else rate + .75, yy,
                f"{rate:.2f}%", ha="right" if near_reference else "left",
                va="center", fontsize=7.7,
                color="white" if near_reference else INK)
    export(fig, "fig3_2_domain_conflict")


def line_data(filename, key, value, feature=None):
    rows = read(filename)
    names = {s[0] for s in SERIES}
    selected = [r for r in rows if r["partition"] in names and
                (feature is None or r.get("features") == feature)]
    if len(selected) != 12:
        raise ValueError(f"Expected 12 selected rows in {filename}")
    grouped = {}
    for part in names:
        one = sorted((r for r in selected if r["partition"] == part),
                     key=lambda r: float(r[key]))
        if len(one) != 4 or len({r[key] for r in one}) != 4:
            raise ValueError(f"Incomplete four-point series: {part}")
        grouped[part] = one
    return grouped


def line_chart(grouped, summary, *, stem, title, subtitle, footnote,
               xkey, ykey, xfactor, yfactor, xlim, ylim, xticks, yticks,
               xlabel, ylabel, height=4.0):
    counts = {r["partition"]: int(r["n"]) for r in summary if r["domain"] == "ALL"}
    fig = base(height, title, subtitle, footnote)
    ax = fig.add_axes([.115, .23, .82, .57])
    for part, label, color, style, marker in SERIES:
        rows = grouped[part]
        x = [float(r[xkey]) * xfactor for r in rows]
        values = [float(r[ykey]) * yfactor for r in rows]
        if not all(0 <= v <= 100 for v in values):
            raise ValueError("Outside score/rate scale")
        ax.plot(x, values, color=color, linestyle=style, linewidth=1.45,
                marker=marker, markersize=4.2, markeredgewidth=.9,
                markerfacecolor="white", label=f"{label}  n = {counts[part]:,}")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.set_xlabel(xlabel, labelpad=7)
    ax.set_ylabel(ylabel, labelpad=7)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#7F8A90")
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", width=.6, length=3)
    ax.grid(axis="y", color=GRID, linewidth=.55)
    ax.set_axisbelow(True)
    fig.legend(loc="upper center", bbox_to_anchor=(.5, .858), ncol=3,
               handlelength=2.0, columnspacing=1.2, frameon=False)
    export(fig, stem)


def main():
    summary = read("conflict_summary.csv")
    figure31_pairs(summary)
    figure32_domains(summary)
    threshold = line_data("threshold_sensitivity.csv", "tail_probability", "rate",
                          feature="groups5")
    line_chart(threshold, summary, stem="fig3_3_threshold_sensitivity",
               title="分位阈值上调，候选冲突率如何变化？",
               subtitle="A1 拟合参照冻结  /  三个互不重叠分区  /  五组质量信号",
               footnote="展示全部四个已计算阈值；连线仅辅助追踪离散参数点。候选冲突率不是识别准确率。",
               xkey="tail_probability", ykey="rate", xfactor=100, yfactor=100,
               xlim=(9.6, 25.4), ylim=(0, 85), xticks=[10, 15, 20, 25],
               yticks=[0, 20, 40, 60, 80], xlabel="低分位阈值 p（%）；高分位为 100−p",
               ylabel="候选冲突率（%）")
    sensitivity = line_data("lambda_sensitivity.csv", "lambda", "mean")
    line_chart(sensitivity, summary, stem="fig3_4_compensation_sensitivity",
               title="有限补偿增强，各分区候选均分如何变化？",
               subtitle="同一五组质量信号  /  四个 λ 设定  /  评分范围 0–100 分",
               footnote="均分为描述统计；随 λ 下降是模型定义的保守折减，不表示预测准确率改善。",
               xkey="lambda", ykey="mean", xfactor=1, yfactor=1,
               xlim=(-.015, .515), ylim=(28, 80), xticks=[0, .1, .25, .5],
               yticks=[30, 40, 50, 60, 70, 80], xlabel="偏好保守程度参数 λ",
               ylabel="候选质量评分均值（0–100 分）")


if __name__ == "__main__":
    main()
