"""Five manuscript figures from the archived Q2-E2 and Q3 result tables.

Style-only inheritance from the repository's Q1/Q2 manuscript figures.
All plotted values are read from frozen source tables; no model is refitted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import NullFormatter
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "source_data"
OUT = ROOT / "figures"
INK = "#29363D"
TEAL = "#527F88"
TEAL_DARK = "#315F6A"
TEAL_LIGHT = "#C8DEDF"
WARM = "#C17855"
GREY = "#738087"
PALE = "#EDF0F1"
WHITE = "#FFFFFF"
WIDTH_MM = 183


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Hiragino Sans GB", "Arial", "DejaVu Sans"],
            "font.size": 7.2,
            "axes.titlesize": 8.3,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.65,
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "figure.facecolor": WHITE,
            "axes.facecolor": WHITE,
            "savefig.facecolor": WHITE,
        }
    )


def read(name: str, expected: int) -> pd.DataFrame:
    frame = pd.read_csv(DATA / name)
    assert len(frame) == expected, (name, len(frame), expected)
    return frame


def canvas(height_mm: float):
    return plt.figure(figsize=(WIDTH_MM / 25.4, height_mm / 25.4), facecolor=WHITE)


def axis_style(ax, grid: str | None = "y") -> None:
    ax.spines["left"].set_color(GREY)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(color=GREY, labelcolor=INK, width=0.65, length=2.6)
    if grid:
        ax.grid(axis=grid, color=PALE, lw=0.7, zorder=0)
        ax.set_axisbelow(True)


def panel_label(ax, letter: str) -> None:
    ax.text(-0.10, 1.05, letter, transform=ax.transAxes, color=INK,
            fontsize=9, fontweight="bold", ha="right", va="bottom")


def save(fig, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    opts = {"bbox_inches": "tight", "pad_inches": 0.05, "facecolor": WHITE}
    svg_path = OUT / f"{stem}.svg"
    fig.savefig(svg_path, **opts)
    svg = svg_path.read_text(encoding="utf-8")
    svg_path.write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n",
                        encoding="utf-8")
    fig.savefig(OUT / f"{stem}.pdf", **opts)
    fig.savefig(OUT / f"{stem}.png", dpi=500, **opts)
    fig.savefig(OUT / f"{stem}.tiff", dpi=600,
                pil_kwargs={"compression": "tiff_lzw"}, **opts)
    plt.close(fig)


def fig01_support() -> dict:
    d = read("e2_substitution_support.csv", 272)
    assert d[["to_index", "from_index"]].drop_duplicates().shape[0] == 272
    assert d.safe_hull_limit_pp.gt(0).all()
    thresholds = [0.1, 1.0, 5.0]
    counts = [int(d.safe_hull_limit_pp.ge(v).sum()) for v in thresholds]
    assert counts == [272, 224, 117]
    labels = [str(d.loc[d.to_index.eq(i), "to_domain"].iloc[0]).replace("_", " ")
              for i in range(17)]
    mat = d.pivot(index="to_index", columns="from_index",
                  values="safe_hull_limit_pp").reindex(index=range(17), columns=range(17)).to_numpy()
    assert np.isfinite(mat).sum() == 272
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "q3_teal", [WHITE, TEAL_LIGHT, TEAL, TEAL_DARK]
    ).copy()
    cmap.set_bad(PALE)
    fig = canvas(142)
    ax = fig.add_axes([0.22, 0.23, 0.49, 0.63])
    im = ax.imshow(mat, interpolation="nearest", aspect="equal", cmap=cmap,
                   vmin=0, vmax=12)
    ax.set_xticks(range(17), labels, rotation=90, rotation_mode="anchor", ha="right")
    ax.set_yticks(range(17), labels)
    ax.tick_params(length=0, labelsize=5.4, pad=1.5)
    ax.set_xlabel("减少的领域", labelpad=4)
    ax.set_ylabel("增加的领域", labelpad=4)
    ax.text(-0.10, 1.00, "a", transform=ax.transAxes, color=INK,
            fontsize=9, fontweight="bold", ha="right", va="bottom")
    cax = fig.add_axes([0.79, 0.83, 0.17, 0.013])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal", ticks=[0, 6, 12])
    cb.ax.tick_params(labelsize=6, length=2)
    fig.text(0.79, 0.87, "替代上限（百分点）", fontsize=6.4, color=GREY)

    bx = fig.add_axes([0.79, 0.36, 0.18, 0.41])
    yy = np.arange(3)
    bx.barh(yy, counts, color=[TEAL_DARK, TEAL, TEAL_LIGHT], height=0.48)
    bx.set_yticks(yy, ["≥0.1", "≥1", "≥5"])
    bx.invert_yaxis()
    bx.set_xlim(0, 290)
    bx.set_xticks([0, 136, 272])
    bx.set_xlabel("支持方向数 / 272")
    bx.set_ylabel("替代幅度（百分点）")
    axis_style(bx, "x")
    panel_label(bx, "b")
    for y, n in zip(yy, counts):
        bx.text(n + 4, y, str(n), va="center", color=INK, fontsize=6.5)
    fig.text(0.04, 0.95, "配方凸包内的有限领域替代支持域", fontsize=10,
             fontweight="bold", color=INK)
    fig.text(0.04, 0.91, "Q2-E2 特征支持诊断 · 272 个有向替代 · 99% 安全余量",
             fontsize=6.8, color=GREY)
    save(fig, "Fig01_recipe_support")
    return {"rows": len(d), "threshold_counts": dict(zip(map(str, thresholds), counts))}


def fig02_failure() -> dict:
    recipe = read("recipe_optima.csv", 40)
    optima = read("frozen_v1_optima.csv", 1200)
    r = recipe.loc[recipe.variant.eq("v1")].copy()
    assert len(r) == 8
    full = optima.loc[optima.variant.eq("v1") & optima["mode"].eq("full_simplex")].copy()
    assert len(full) == 60 and full.predicted_loss.lt(0).all()
    modes = ["reference", "observed_training", "training_hull", "full_simplex"]
    names = ["参考配方", "已有训练配方", "训练凸包", "完整单纯形"]
    axes = ["Q_A_topsis_0_1", "quality_score_soft_proxy_0_1"]
    colors = [TEAL, WARM]
    fig = canvas(101)
    ax = fig.add_axes([0.08, 0.30, 0.43, 0.50])
    x = np.arange(4)
    for j, (quality_axis, color, label) in enumerate(zip(axes, colors, ["TOPSIS 轴", "soft 轴"])):
        vals = [float(r.loc[r.axis.eq(quality_axis) & r["mode"].eq(m),
                            "total_correction"].iloc[0]) for m in modes]
        ax.scatter(x + (j - 0.5) * 0.16, vals, s=27, color=color,
                   marker="o" if j == 0 else "s", label=label, zorder=3)
    ax.axhline(0, color=GREY, lw=0.7)
    ax.set_xticks(x, names)
    ax.set_ylabel("模型总修正（Loss）")
    ax.set_ylim(-4.85, 0.4)
    axis_style(ax)
    ax.legend(loc="lower left", ncol=2, bbox_to_anchor=(0.00, 1.00), frameon=False)
    panel_label(ax, "a")
    ax.annotate("纯 Enron", xy=(3, -4.37), xytext=(2.35, -3.20), fontsize=6.8,
                color=WARM, arrowprops={"arrowstyle": "-", "color": WARM, "lw": 0.8})

    bx = fig.add_axes([0.60, 0.30, 0.37, 0.50])
    jitter = np.linspace(-0.08, 0.08, len(full))
    for i, (_, row) in enumerate(full.iterrows()):
        marker = "o" if row.scope == "unrestricted" else "s"
        color = TEAL if row.axis == axes[0] else WARM
        bx.scatter(np.log10(row.budget) + jitter[i], row.predicted_loss,
                   s=14, marker=marker, facecolors="none", edgecolors=color,
                   linewidths=0.8, alpha=0.8, zorder=3)
    bx.axhline(0, color=INK, lw=0.9, ls="--")
    bx.set_xticks([19, 22, 24], ["1e19", "1e22", "1e24"])
    bx.set_xlabel("预算 FLOPs")
    bx.set_ylabel("完整单纯形预测 Loss")
    bx.set_xlim(18.6, 24.4)
    axis_style(bx)
    panel_label(bx, "b")
    bx.text(0.04, 0.06, "60/60 个情景 < 0", transform=bx.transAxes,
            color=WARM, fontsize=7.2, fontweight="bold")
    fig.text(0.04, 0.95, "配比放开导致冻结模型在最优点失效", fontsize=10,
             fontweight="bold", color=INK)
    fig.text(0.04, 0.91,
             "Enron 占比：训练配方最高 2.6026% → 完整单纯形解 100%",
             fontsize=7.0, color=WARM)
    fig.text(0.04, 0.08,
             "点为确定性情景结果；不同预算、上下文、规模边界及质量轴不是独立训练重复。",
             fontsize=6.7, color=GREY)
    save(fig, "Fig02_recipe_failure")
    return {"recipe_rows": len(r), "negative_rows": len(full),
            "negative_loss_range": [float(full.predicted_loss.min()),
                                    float(full.predicted_loss.max())]}


def fig03_quality_cost() -> dict:
    d = read("processing_scenarios.csv", 3492)
    q = d.loc[
        d.cost.eq("exponential") & d.context.eq(2048)
        & d.recipe.eq("reference") & d.scope.eq("unrestricted")
        & d.lambda_q.eq(1)
    ].copy()
    assert len(q) == 204
    assert q.groupby(["axis", "cost_coordinate"]).size().eq(51).all()
    fig = canvas(122)
    lefts = [0.10, 0.55]
    bottoms = [0.57, 0.16]
    axes = ["Q_A_topsis_0_1", "quality_score_soft_proxy_0_1"]
    for i, quality_axis in enumerate(axes):
        for j, coordinate in enumerate(["Q_A", "Q_B"]):
            part = q.loc[q.axis.eq(quality_axis) & q.cost_coordinate.eq(coordinate)].sort_values("budget")
            ax = fig.add_axes([lefts[j], bottoms[i], 0.36, 0.25])
            xx = np.log10(part.budget.to_numpy())
            yy = part.Q_star.to_numpy()
            assert np.all(np.diff(xx) > 0)
            ax.plot(xx, yy, color=TEAL if j == 0 else WARM, lw=1.8,
                    zorder=3)
            ax.axhline(float(part.Q0.iloc[0]), color=GREY, lw=0.7, ls="--")
            ax.set_xlim(18.9, 24.1)
            ax.set_ylim(0.18 if i == 1 and j == 0 else 0.58, 1.025)
            ax.set_xticks([19, 20, 21, 22, 23, 24],
                          ["19", "20", "21", "22", "23", "24"])
            ax.set_xlabel("log10(预算 FLOPs)")
            ax.set_ylabel("最优质量 Q*")
            axis_style(ax)
            panel_label(ax, "abcd"[i * 2 + j])
            label = ("TOPSIS" if i == 0 else "soft") + (" · 按 QA 计价" if j == 0 else " · 按 QB 计价")
            ax.set_title(label, loc="left", color=INK, pad=6)
            if j == 1:
                interior = part.loc[part.regime.eq("interior")]
                if not interior.empty:
                    ax.axvspan(np.log10(interior.budget.min()),
                               np.log10(interior.budget.max()),
                               color=WARM, alpha=0.08, zorder=0)
                for regime, marker in [("no_processing", "o"), ("interior", "s"),
                                       ("quality_upper", "^")]:
                    pp = part.loc[part.regime.eq(regime)]
                    if not pp.empty:
                        edges = pp.iloc[[0, -1]].drop_duplicates(subset="budget")
                        ax.scatter(np.log10(edges.budget), edges.Q_star, marker=marker,
                                   s=20, facecolors=WARM if regime == "interior" else WHITE,
                                   edgecolors=WARM, linewidths=0.8, zorder=4)
    fig.text(0.04, 0.95, "质量成本口径改变最优处理状态", fontsize=10,
             fontweight="bold", color=INK)
    fig.text(0.04, 0.91,
             "指数成本 · 上下文 2048 · 参考配方 · 无规模上限 · 冻结效应强度 1",
             fontsize=6.8, color=GREY)
    fig.text(0.04, 0.06,
             "虚线为各口径初始质量；两种计价是不同模型假设，非等价换元。转折点只由 0.1 log10 步长定位。",
             fontsize=6.5, color=GREY)
    save(fig, "Fig03_quality_cost")
    counts = q.groupby(["axis", "cost_coordinate", "regime"]).size()
    return {"rows": len(q), "regime_counts": {"|".join(key): int(value)
                                                 for key, value in counts.items()}}


def fig04_budget_nd() -> dict:
    d = read("frozen_v1_optima.csv", 1200)
    q = d.loc[d.axis.eq("Q_A_topsis_0_1") & d.variant.eq("v1")
              & d["mode"].eq("reference") & d.context.eq(2048)].copy()
    assert len(q) == 6 and set(q.scope) == {"unrestricted", "B1_rectangle"}
    fig = canvas(91)
    for j, (field, upper, ylabel) in enumerate([
        ("N_B", 11.965825, "参数量 N*（十亿）"),
        ("D_B", 299.893, "训练 token D*（十亿）"),
    ]):
        ax = fig.add_axes([0.10 + j * 0.45, 0.27, 0.35, 0.53])
        for scope, color, marker, label in [
            ("unrestricted", WARM, "o", "无规模约束"),
            ("B1_rectangle", TEAL, "s", "B1 矩形边界"),
        ]:
            part = q.loc[q.scope.eq(scope)].sort_values("budget")
            ax.plot(np.log10(part.budget), part[field], color=color, marker=marker,
                    markersize=4.5, lw=1.0, ls="--", label=label, zorder=3)
            if scope == "unrestricted":
                bad = part.loc[part[field].gt(upper + 1e-9)]
                ax.scatter(np.log10(bad.budget), bad[field], s=56,
                           facecolors="none", edgecolors=WARM, linewidths=1.0, zorder=4)
        ax.axhline(upper, color=GREY, lw=0.9, ls="--")
        ax.set_yscale("log")
        ticks = [0.1, 1, 10, 100] if field == "N_B" else [1, 10, 100, 1000, 10000]
        ax.set_yticks(ticks, [str(x) for x in ticks])
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks([19, 22, 24], ["1e19", "1e22", "1e24"])
        ax.set_xlabel("预算 FLOPs")
        ax.set_ylabel(ylabel)
        axis_style(ax)
        panel_label(ax, "ab"[j])
        if j == 0:
            ax.legend(loc="upper left", frameon=False)
        ax.text(0.97, 0.52, "B1 上限", transform=ax.transAxes, ha="right",
                color=GREY, fontsize=6.5)
    fig.text(0.04, 0.95, "高预算条件解越过 B1 规模支持范围", fontsize=10,
             fontweight="bold", color=INK)
    fig.text(0.04, 0.91,
             "TOPSIS 质量轴 · v1 · 参考配方 · 上下文 2048 · 预算仅含三个离散情景",
             fontsize=6.8, color=GREY)
    fig.text(0.04, 0.075,
             "空心圈标出无约束解超出 B1 上限；1e24 预算下受限解利用率为 2.30%，不代表现实算力上限。",
             fontsize=6.5, color=GREY)
    save(fig, "Fig04_budget_ND")
    return {"rows": len(q), "budgets": sorted(map(float, q.budget.unique()))}


def fig05_regret() -> dict:
    d = read("retrospective_decision_regret.csv", 24)
    q = d.loc[d.variant.eq("v1")].copy()
    assert len(q) == 6
    # The two axes choose the same recipe at each scale. Show one copy; verify equality.
    check = q.groupby("dataset").agg(
        same_recipe=("selected_recipe", lambda x: x.nunique() == 1),
        same_loss=("selected_observed_loss", lambda x: x.nunique() == 1),
    )
    assert check.all().all()
    q = q.loc[q.axis.eq("Q_A_topsis_0_1")].copy()
    labels = [("A6_A7_test_1m", "1M"), ("A8_A9_test_60m", "60M"),
              ("A10_A11_test_1b", "1B")]
    fig = canvas(105)
    for i, (dataset, title) in enumerate(labels):
        row = q.loc[q.dataset.eq(dataset)].iloc[0]
        ax = fig.add_axes([0.11 + i * 0.295, 0.26, 0.24, 0.47])
        vals = [row.best_available_observed_loss,
                row.candidate_mean_observed_loss,
                row.selected_observed_loss]
        yy = np.arange(3)
        ax.scatter(vals, yy, s=[34, 34, 45], color=[GREY, TEAL, WARM], zorder=3)
        ax.set_yticks(yy, ["候选最佳", "候选均值", "模型选中"])
        ax.invert_yaxis()
        span = max(vals) - min(vals)
        ax.set_xlim(min(vals) - span * 0.14, max(vals) + span * 0.16)
        ax.set_xlabel("实测平均 Loss")
        ax.set_title(f"{title} · {int(row.n_candidates)} 候选", loc="left", pad=7)
        axis_style(ax, "x")
        panel_label(ax, "abc"[i])
        ax.text(0.00, 1.19, f"regret {row.regret:.3f}", transform=ax.transAxes,
                color=WARM, fontsize=6.9)
        ax.text(0.00, -0.33,
                f"实际排名 {int(row.selected_actual_rank)}/{int(row.n_candidates)}",
                transform=ax.transAxes, color=GREY, fontsize=6.4)
    fig.text(0.04, 0.95, "回溯选优显示模型均值误差之外的决策风险", fontsize=10,
             fontweight="bold", color=INK)
    fig.text(0.04, 0.91,
             "冻结 v1 模型 · 两质量轴选中相同配方 · 在各自候选集合内比较",
             fontsize=6.8, color=GREY)
    fig.text(0.04, 0.075,
             "相关标签已用于 Q2 研究；本图是回溯诊断，不是新的独立盲测。1M 与 60M 配方匹配，不视为独立重复。",
             fontsize=6.5, color=GREY)
    save(fig, "Fig05_decision_regret")
    return {"rows_from_table": len(q),
            "regret": {title: float(q.loc[q.dataset.eq(dataset), "regret"].iloc[0])
                       for dataset, title in labels}}


def main() -> None:
    style()
    info = {
        "source_commit": "f36afef332ed160146c548551d6cf09488cfd312",
        "backend": "Python/matplotlib",
        "style_reuse": "style only: repository Q1/Q2 palette, typography and spacing",
        "figures": {
            "Fig01_recipe_support": fig01_support(),
            "Fig02_recipe_failure": fig02_failure(),
            "Fig03_quality_cost": fig03_quality_cost(),
            "Fig04_budget_ND": fig04_budget_nd(),
            "Fig05_decision_regret": fig05_regret(),
        },
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(DATA.glob("*.csv"))},
    }
    (ROOT / "figure_manifest.json").write_text(json.dumps(info, ensure_ascii=False,
                                         indent=2, default=str) + "\n", encoding="utf-8")
    print("Created five Q3 manuscript figures")


if __name__ == "__main__":
    main()
