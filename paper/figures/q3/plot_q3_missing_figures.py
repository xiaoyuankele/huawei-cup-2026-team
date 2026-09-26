"""Create the manuscript-ready figures for the Q3 analyses not covered by the
original exploratory draft.

All values are read from frozen experiment tables.  The plots are conditional
scenario summaries, not new fits or independent validation experiments.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "figures"
WIDTH_MM = 183

INK = "#29363D"
TEAL_DARK = "#315F6A"
TEAL = "#527F88"
TEAL_LIGHT = "#C8DEDF"
WARM = "#C17855"
WARM_LIGHT = "#E9C7B7"
GREY = "#738087"
PALE = "#EDF0F1"
WHITE = "#FFFFFF"
BLUE = "#668CA3"

CONTEXTS = [2048, 4096, 8192, 32768, 131072]
CONTEXT_COLORS = ["#315F6A", "#527F88", "#6E9AA0", "#9ABABD", "#C8DEDF"]
COSTS = ["exponential", "power", "logarithmic"]
COST_LABELS = {"exponential": "指数", "power": "幂函数", "logarithmic": "对数"}
MAPPING_ORDER = [
    "M2_partial_raw",
    "M2_partial_renorm",
    "M2_interval_low",
    "M2_interval_mid",
    "M2_interval_high",
]
MAPPING_LABELS = {
    "M2_partial_raw": "部分映射\n原值",
    "M2_partial_renorm": "部分映射\n重归一化",
    "M2_interval_low": "区间低值",
    "M2_interval_mid": "区间中值",
    "M2_interval_high": "区间高值",
}


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
            "font.size": 7.2,
            "axes.titlesize": 8.2,
            "axes.labelsize": 7.3,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.2,
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


def axis_style(ax, grid: str | None = "y") -> None:
    ax.spines["left"].set_color(GREY)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(color=GREY, labelcolor=INK, width=0.65, length=2.6, pad=2)
    if grid:
        ax.grid(axis=grid, color=PALE, lw=0.7, zorder=0)
        ax.set_axisbelow(True)


def panel_label(ax, label: str) -> None:
    ax.text(-0.10, 1.05, label, transform=ax.transAxes, color=INK,
            fontsize=9, fontweight="bold", ha="right", va="bottom")


def read_run(relative: str, expected: int | None = None) -> pd.DataFrame:
    path = REPO / relative
    frame = pd.read_csv(path)
    if expected is not None:
        assert len(frame) == expected, (relative, len(frame), expected)
    return frame


def log_budget(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    assert np.all(values > 0), "budgets must be strictly positive"
    return np.log10(values)


def save(fig: plt.Figure, stem: str) -> None:
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


def title(fig: plt.Figure, main: str, sub: str, foot: str) -> None:
    fig.text(0.04, 0.965, main, fontsize=10, fontweight="bold", color=INK,
             ha="left", va="top")
    fig.text(0.04, 0.925, sub, fontsize=6.8, color=GREY,
             ha="left", va="top")
    fig.text(0.04, 0.045, foot, fontsize=6.2, color=GREY,
             ha="left", va="bottom")


def fig06_m0_budget_context() -> dict:
    d = read_run("experiments/runs/q3-nd-baseline-20260925-r01/tables/q3_nd_baseline_scenarios.csv", 15)
    d = d.sort_values(["Lctx", "budget_flops"])
    assert set(d.Lctx) == set(CONTEXTS)
    assert d.budget_flops.nunique() == 3
    fig, axs = plt.subplots(2, 2, figsize=(WIDTH_MM / 25.4, 112 / 25.4))
    axs = axs.ravel()
    xs = log_budget(sorted(d.budget_flops.unique()))
    for ctx, col in zip(CONTEXTS, CONTEXT_COLORS):
        p = d.loc[d.Lctx.eq(ctx)].sort_values("budget_flops")
        x = log_budget(p.budget_flops)
        for ax, relaxed, bounded, label in [
            (axs[0], "relaxed_N_B", "bounded_N_B", "N (B)"),
            (axs[1], "relaxed_D_B", "bounded_D_B", "D (B)"),
        ]:
            ax.plot(x, p[relaxed], color=col, lw=1.0, ls="--", alpha=0.8)
            ax.plot(x, p[bounded], color=col, lw=1.8, marker="o", ms=3.1,
                    label=f"Lctx={ctx:,}")
            ax.set_ylabel(label)
            ax.set_xticks(xs, ["1e19", "1e22", "1e24"])
            ax.set_xlabel("预算 FLOPs")
            axis_style(ax)
        ax = axs[2]
        ax.plot(x, p.relaxed_loss, color=col, lw=1.0, ls="--", alpha=0.8)
        ax.plot(x, p.bounded_loss, color=col, lw=1.8, marker="o", ms=3.1)
        ax.set_ylabel("预测 Loss")
        ax.set_xlabel("预算 FLOPs")
        ax.set_xticks(xs, ["1e19", "1e22", "1e24"])
        axis_style(ax)
        ax = axs[3]
        util = p.bounded_cost_flops / p.budget_flops
        ax.plot(x, util, color=col, lw=1.8, marker="o", ms=3.1)
        ax.set_ylabel("受限解预算利用率")
        ax.set_xlabel("预算 FLOPs")
        ax.set_xticks(xs, ["1e19", "1e22", "1e24"])
        ax.set_ylim(0, 1.08)
        axis_style(ax)
    axs[0].axhspan(0.070542, 11.965825, color=TEAL_LIGHT, alpha=0.20, zorder=0)
    axs[1].axhspan(0.134, 299.893, color=TEAL_LIGHT, alpha=0.20, zorder=0)
    axs[0].text(0.02, 0.08, "B1 支持域", transform=axs[0].transAxes, color=TEAL_DARK, fontsize=6.2)
    axs[1].text(0.02, 0.08, "B1 支持域", transform=axs[1].transAxes, color=TEAL_DARK, fontsize=6.2)
    axs[0].legend(loc="upper center", bbox_to_anchor=(1.08, 1.31), ncol=3,
                  frameon=False, handlelength=2.2, columnspacing=1.0)
    panel_label(axs[0], "a")
    panel_label(axs[1], "b")
    panel_label(axs[2], "c")
    panel_label(axs[3], "d")
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.19, top=0.78,
                        wspace=0.35, hspace=0.75)
    title(fig, "M0 预算下的参数量–训练 token 配置",
          "实线为 B1 支持域约束解，虚线为放松支持域的解析解；颜色表示上下文长度。",
          "阴影为 B1 观测支持范围；超出支持域的放松解仅作外推诊断，不表示实证最优。")
    save(fig, "Fig06_M0_budget_context")
    return {"rows": len(d), "contexts": CONTEXTS, "budgets": xs.tolist()}


def fig07_m1_quality_tradeoff() -> dict:
    d = read_run("experiments/runs/q3-q-conditional-20260925-r01/tables/q3_q_conditional_scenarios.csv", 45)
    assert set(d.cost_family) == set(COSTS)
    assert set(d.Lctx) == set(CONTEXTS)
    fig, axs = plt.subplots(2, 3, figsize=(WIDTH_MM / 25.4, 112 / 25.4), sharex=True)
    xs = log_budget(sorted(d.budget_flops.unique()))
    for j, cost in enumerate(COSTS):
        for ctx, col in zip(CONTEXTS, CONTEXT_COLORS):
            p = d.loc[d.cost_family.eq(cost) & d.Lctx.eq(ctx)].sort_values("budget_flops")
            x = log_budget(p.budget_flops)
            axs[0, j].plot(x, p.Q, color=col, lw=1.45, marker="o", ms=2.9)
            axs[1, j].plot(x, p.quality_cost_flops / p.total_cost_flops,
                           color=col, lw=1.45, marker="o", ms=2.9)
        for ax in axs[:, j]:
            ax.set_xticks(xs, ["1e19", "1e22", "1e24"])
            ax.set_xlabel("预算 FLOPs")
            axis_style(ax)
        axs[0, j].set_title(COST_LABELS[cost], color=INK, pad=5)
        axs[0, j].set_ylim(0.07, 1.04)
        axs[1, j].set_ylim(0, 0.96)
    axs[0, 0].set_ylabel("最优质量 $Q^*$")
    axs[1, 0].set_ylabel("质量成本占比")
    axs[0, 0].axhspan(0.1, 1.0, color=TEAL_LIGHT, alpha=0.15, zorder=0)
    handles = [plt.Line2D([0], [0], color=c, lw=2, marker="o", ms=3, label=f"Lctx={ctx:,}")
               for ctx, c in zip(CONTEXTS, CONTEXT_COLORS)]
    axs[0, 1].legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.47),
                      ncol=5, frameon=False, handlelength=1.5, columnspacing=0.75)
    panel_label(axs[0, 0], "a")
    panel_label(axs[0, 1], "b")
    panel_label(axs[0, 2], "c")
    panel_label(axs[1, 0], "d")
    panel_label(axs[1, 1], "e")
    panel_label(axs[1, 2], "f")
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.20, top=0.74,
                        wspace=0.36, hspace=0.85)
    title(fig, "M1 原生质量条件下的质量投入与资源替代",
          "三列为附录 B 的成本族；颜色表示 C7 上下文长度，所有点为确定性条件情景。",
          "Q 为 B6/B7 原生质量分数；该图不把 Q 解释为 Q1 质量分，也不构成 A–B 联合验证。")
    save(fig, "Fig07_M1_quality_tradeoff")
    return {"rows": len(d), "cost_families": COSTS, "contexts": CONTEXTS}


def _heat(ax, mat, rows, cols, title_text, cmap, vmin=None, vmax=None, fmt=".2f"):
    im = ax.imshow(mat, aspect="auto", interpolation="nearest", cmap=cmap,
                   vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(cols)), cols)
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0, pad=3)
    ax.set_title(title_text, fontsize=7.2, pad=5, color=INK)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isfinite(mat[i, j]):
                txt_color = WHITE if (mat[i, j] - np.nanmin(mat)) / max(np.nanmax(mat) - np.nanmin(mat), 1e-9) > 0.60 else INK
                ax.text(j, i, format(mat[i, j], fmt), ha="center", va="center", fontsize=6.0, color=txt_color)
    axis_style(ax, None)
    return im


def fig08_q0_cost_robustness() -> dict:
    d = read_run("experiments/runs/q3-q-robustness-20260925-r01/tables/q3_q_robustness_scenarios.csv", 135)
    # Aggregate over the five contexts to isolate the Q0/cost/budget sensitivity.
    q = d.groupby(["budget_flops", "Q0", "cost_family"], as_index=False).agg(
        Q=("Q", "median"), at_bound=("Q_at_bound", "mean")
    )
    fig, axs = plt.subplots(2, 2, figsize=(WIDTH_MM / 25.4, 102 / 25.4))
    axs = axs.ravel()
    q0s = sorted(q.Q0.unique())
    costs = COSTS
    qmatrices = []
    for budget in sorted(q.budget_flops.unique()):
        p = q.loc[q.budget_flops.eq(budget)].set_index(["Q0", "cost_family"])
        mat = np.array([[p.loc[(q0, cost), "Q"] for cost in costs] for q0 in q0s])
        qmatrices.append(mat)
    cmap = mcolors.LinearSegmentedColormap.from_list("q3_q", ["#EDF0F1", TEAL_LIGHT, TEAL_DARK])
    for ax, mat, budget, letter in zip(axs[:3], qmatrices, sorted(q.budget_flops.unique()), ["a", "b", "c"]):
        im = _heat(ax, mat, [str(v) for v in q0s], [COST_LABELS[c] for c in costs],
                   f"预算 {budget:.0e}", cmap, 0.1, 1.0, ".2f")
        ax.set_xlabel("成本函数")
        ax.set_ylabel("初始质量 $Q_0$")
        panel_label(ax, letter)
    p = q.copy()
    p["at_bound_pct"] = 100 * p.at_bound
    mat = p.groupby(["Q0", "cost_family"]).at_bound_pct.mean().unstack().reindex(index=q0s, columns=costs).to_numpy()
    im = _heat(axs[3], mat, [str(v) for v in q0s], [COST_LABELS[c] for c in costs],
               "达到质量上界的情景比例（%）", plt.get_cmap("Oranges"), 0, 100, ".0f")
    axs[3].set_xlabel("成本函数")
    axs[3].set_ylabel("初始质量 $Q_0$")
    panel_label(axs[3], "d")
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.21, top=0.77,
                        wspace=0.54, hspace=0.92)
    title(fig, "M1 质量最优解对初始质量和成本函数的稳健性",
          "每个单元格为五个上下文情景的中位数；右下角显示达到质量上界的情景比例。",
          "该图是 Q0 与成本族的参数敏感性，不是重新拟合或独立验证；质量上界为 B6 支持范围内的条件边界。")
    save(fig, "Fig08_Q0_cost_robustness")
    return {"rows": len(d), "q0_values": q0s, "budgets": [float(x) for x in sorted(q.budget_flops.unique())]}


def fig09_parameter_uncertainty() -> dict:
    m0 = read_run("experiments/runs/q3-optimization-robustness-20260926-r01/tables/m0_uncertainty_summary.csv", 15)
    m1 = read_run("experiments/runs/q3-optimization-robustness-20260926-r01/tables/m1_uncertainty_summary.csv", 45)
    fig, axs = plt.subplots(2, 2, figsize=(WIDTH_MM / 25.4, 112 / 25.4))
    axs = axs.ravel()
    xs = log_budget(sorted(m0.budget_flops.unique()))
    for ctx, col in zip(CONTEXTS, CONTEXT_COLORS):
        p = m0.loc[m0.Lctx.eq(ctx)].sort_values("budget_flops")
        x = log_budget(p.budget_flops)
        axs[0].fill_between(x, p.bounded_N_B_p05, p.bounded_N_B_p95, color=col, alpha=0.12)
        axs[0].plot(x, p.bounded_N_B_median, color=col, lw=1.5, marker="o", ms=2.7)
        axs[1].fill_between(x, p.bounded_D_B_p05, p.bounded_D_B_p95, color=col, alpha=0.12)
        axs[1].plot(x, p.bounded_D_B_median, color=col, lw=1.5, marker="o", ms=2.7)
    axs[0].axhspan(0.070542, 11.965825, color=TEAL_LIGHT, alpha=0.14)
    axs[1].axhspan(0.134, 299.893, color=TEAL_LIGHT, alpha=0.14)
    axs[0].set_ylabel("M0 受限 $N^*$ (B)")
    axs[1].set_ylabel("M0 受限 $D^*$ (B tokens)")
    for ax in axs[:2]:
        ax.set_xlabel("预算 FLOPs")
        ax.set_xticks(xs, ["1e19", "1e22", "1e24"])
        axis_style(ax)
    p = m1.loc[m1.cost_family.eq("exponential") & m1.Lctx.eq(2048)].sort_values("budget_flops")
    x = log_budget(p.budget_flops)
    axs[2].fill_between(x, p.Q_p05, p.Q_p95, color=WARM_LIGHT, alpha=0.50)
    axs[2].plot(x, p.Q_median, color=WARM, lw=1.8, marker="o", ms=3.0)
    axs[2].set_ylabel("M1 $Q^*$")
    axs[2].set_xlabel("预算 FLOPs")
    axs[3].fill_between(x, p.loss_p05, p.loss_p95, color=TEAL_LIGHT, alpha=0.65)
    axs[3].plot(x, p.loss_median, color=TEAL_DARK, lw=1.8, marker="o", ms=3.0)
    axs[3].set_ylabel("M1 预测 Loss")
    axs[3].set_xlabel("预算 FLOPs")
    for ax in axs[2:]:
        ax.set_xticks(xs, ["1e19", "1e22", "1e24"])
        axis_style(ax)
    handles = [plt.Line2D([0], [0], color=c, lw=2, marker="o", ms=3, label=f"Lctx={ctx:,}")
               for ctx, c in zip(CONTEXTS, CONTEXT_COLORS)]
    axs[0].legend(handles=handles, loc="upper center", bbox_to_anchor=(1.08, 1.34),
                  ncol=5, frameon=False, handlelength=1.4, columnspacing=0.75)
    panel_label(axs[0], "a")
    panel_label(axs[1], "b")
    panel_label(axs[2], "c")
    panel_label(axs[3], "d")
    fig.subplots_adjust(left=0.09, right=0.99, bottom=0.20, top=0.75,
                        wspace=0.42, hspace=0.82)
    title(fig, "Q2 参数折叠传播到 Q3 优化结果的范围",
          "阴影为 5%–95% 折叠参数传播范围，实线为中位数；仅展示参数不确定性，不是独立实验置信区间。",
          "M0 阴影带同时标示 B1 支持域；M1 下排固定指数成本与 Lctx=2048。")
    save(fig, "Fig09_parameter_uncertainty")
    return {"m0_rows": len(m0), "m1_rows": len(m1), "m1_slice": "exponential, Lctx=2048"}


def fig10_discrete_pareto() -> dict:
    m0 = read_run("experiments/runs/q3-optimization-robustness-20260926-r01/tables/m0_discrete_frontier.csv", 120)
    m1 = read_run("experiments/runs/q3-optimization-robustness-20260926-r01/tables/m1_discrete_frontier.csv", 225)
    m0 = m0.loc[m0.Lctx.eq(2048)].copy()
    m1 = m1.loc[m1.Lctx.eq(2048)].copy()
    fig, ax = plt.subplots(figsize=(WIDTH_MM / 25.4, 78 / 25.4))
    ax.scatter(log_budget(m0.bounded_cost_flops), m0.bounded_loss, s=24, color=TEAL,
               alpha=0.28, label="M0 情景", zorder=2)
    ax.scatter(log_budget(m1.total_cost_flops), m1.loss, s=28, color=WARM,
               alpha=0.24, label="M1 情景", zorder=2)
    p0 = m0.loc[m0.pareto_flag]
    p1 = m1.loc[m1.pareto_flag]
    ax.scatter(log_budget(p0.bounded_cost_flops), p0.bounded_loss, s=42, color=TEAL_DARK,
               marker="D", edgecolor=WHITE, linewidth=0.5, label="M0 离散前沿", zorder=4)
    ax.scatter(log_budget(p1.total_cost_flops), p1.loss, s=44, color=WARM,
               marker="D", edgecolor=WHITE, linewidth=0.5, label="M1 离散前沿", zorder=4)
    ax.set_xlabel("log10(实际计算成本 FLOPs)")
    ax.set_ylabel("预测 Loss")
    ax.legend(loc="upper right", frameon=False, ncol=2, columnspacing=1.0)
    axis_style(ax)
    panel_label(ax, "a")
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.27, top=0.73)
    title(fig, "M0/M1 的离散成本–Loss 前沿",
          "固定上下文 Lctx=2048；点为折叠参数传播后的确定性情景，菱形为组内离散非支配点。",
          "离散前沿用于比较条件情景的成本–Loss 关系，不是连续优化的全局最优边界。")
    save(fig, "Fig10_discrete_pareto")
    return {"m0_rows_lctx2048": len(m0), "m1_rows_lctx2048": len(m1), "m0_pareto": int(p0.pareto_flag.sum()), "m1_pareto": int(p1.pareto_flag.sum())}


def fig11_p_candidate_panel() -> dict:
    s = read_run("experiments/runs/q3-p-conditional-20260925-r01/tables/p_candidate_summary.csv", 6)
    d = read_run("experiments/runs/q3-p-conditional-20260925-r01/tables/p_candidate_q3_nd_panel.csv", 90)
    candidates = s.sort_values("predicted_policy_rank").candidate_index.astype(int).tolist()
    labels = [f"p{c}" for c in candidates]
    fig, axs = plt.subplots(1, 2, figsize=(WIDTH_MM / 25.4, 82 / 25.4), gridspec_kw={"wspace": 0.46})
    s = s.set_index("candidate_index").loc[candidates].reset_index()
    y = np.arange(len(s))
    axs[0].hlines(y, s.predicted_scalar_loss_z_min, s.predicted_scalar_loss_z_max, color=TEAL_LIGHT, lw=4)
    axs[0].scatter(s.observed_scalar_loss_z, y, color=WARM, s=35, marker="o", label="A 侧观测")
    axs[0].scatter(s.predicted_scalar_loss_z_mean, y, color=TEAL_DARK, s=35, marker="D", label="A 侧预测均值")
    axs[0].set_yticks(y, labels)
    axs[0].set_xlabel("标准化 scalar Loss")
    axs[0].set_ylabel("候选配比（按预测策略排序）")
    axs[0].legend(loc="lower left", frameon=False, fontsize=6.0)
    axis_style(axs[0], "x")
    axs[0].invert_yaxis()
    p = d.loc[d.Lctx.eq(2048) & d.budget_flops.eq(1e22)].set_index("candidate_index").loc[candidates].reset_index()
    x = np.arange(len(p))
    axs[1].plot(x, p.bounded_N_B, color=TEAL_DARK, lw=1.8, marker="o", ms=4, label="N* (B)")
    axs[1].plot(x, p.bounded_D_B / 20, color=WARM, lw=1.8, marker="s", ms=4, label="D*/20 (B tokens)")
    axs[1].set_xticks(x, labels)
    axs[1].set_ylabel("条件配置（D 缩放为 1/20）")
    axs[1].set_xlabel("候选配比")
    axs[1].legend(loc="upper right", frameon=False, fontsize=6.0)
    axis_style(axs[1])
    panel_label(axs[0], "a")
    panel_label(axs[1], "b")
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.25, top=0.72)
    title(fig, "已观测配比候选的 A 侧表现与 Q3 条件配置",
          "a，A 侧观测/预测 scalar Loss；b，指数成本、Lctx=2048、预算 1e22 FLOPs 下的条件配置。",
          "A 侧配比评价与 B 侧资源配置分开呈现；两者不相加为未经验证的联合 Loss。")
    save(fig, "Fig11_p_candidate_panel")
    return {"summary_rows": len(s), "panel_rows": len(d), "candidate_order": candidates}


def fig12_m2_interface_heatmap() -> dict:
    d = read_run("experiments/runs/q2-q3-interface-sensitivity-20260926-r01/tables/m2_q3_fixed_q_scenarios.csv", 1350)
    p = d.loc[d.cost_family.eq("exponential") & d.Lctx.eq(2048) & d.budget_flops.eq(1e22)].copy()
    assert len(p) == 30
    candidates = sorted(p.candidate_index.unique())
    p["mapping_scenario"] = pd.Categorical(p.mapping_scenario, categories=MAPPING_ORDER, ordered=True)
    p = p.sort_values(["candidate_index", "mapping_scenario"])
    def mat(col):
        return p.pivot(index="candidate_index", columns="mapping_scenario", values=col).reindex(index=candidates, columns=MAPPING_ORDER).to_numpy()
    fig, axs = plt.subplots(1, 3, figsize=(WIDTH_MM / 25.4, 82 / 25.4))
    qmat = mat("Q_B_hypothetical_0_1")
    lmat = mat("loss")
    cmat = 100 * mat("quality_cost_share")
    short_labels = ["原值", "重归一化", "低", "中", "高"]
    im1 = _heat(axs[0], qmat, [f"p{x}" for x in candidates], short_labels, "假设 $Q_B$", mcolors.LinearSegmentedColormap.from_list("q3q", ["#EDF0F1", TEAL_LIGHT, TEAL_DARK]), 0.1, 1.0, ".2f")
    im2 = _heat(axs[1], lmat, [f"p{x}" for x in candidates], short_labels, "预测 Loss", mcolors.LinearSegmentedColormap.from_list("q3loss", [WARM_LIGHT, "#F3E7E1", WHITE]), float(np.nanmin(lmat)), float(np.nanmax(lmat)), ".2f")
    im3 = _heat(axs[2], cmat, [f"p{x}" for x in candidates], short_labels, "质量成本占比（%）", plt.get_cmap("Blues"), 0, max(1.0, float(np.nanmax(cmat))), ".1f")
    for ax in axs:
        ax.set_xlabel("Q1→B6 接口情景")
        ax.set_ylabel("候选配比")
    panel_label(axs[0], "a")
    panel_label(axs[1], "b")
    panel_label(axs[2], "c")
    fig.subplots_adjust(left=0.09, right=0.99, bottom=0.30, top=0.72,
                        wspace=0.65)
    title(fig, "Q1 配比质量到 B6 质量接口的情景敏感性",
          "固定指数成本、Lctx=2048、预算 1e22 FLOPs；每个单元格对应一个条件优化情景。",
          "Q1→B6 的仿射映射未经验证；热图展示接口假设如何改变 Q、Loss 和质量成本占比，不代表质量尺度已校准。")
    save(fig, "Fig12_M2_interface_heatmap")
    return {"rows": len(d), "slice_rows": len(p), "slice": "exponential, Lctx=2048, budget=1e22"}


def fig13_identifiability_interface() -> dict:
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, 92 / 25.4), facecolor=WHITE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = [
        (0.04, 0.64, 0.20, 0.17, "B1\n规模与 token\n1176 行", TEAL_LIGHT, TEAL_DARK),
        (0.04, 0.34, 0.20, 0.17, "B6/B7\n原生质量 Q\n360 行", TEAL_LIGHT, TEAL_DARK),
        (0.04, 0.13, 0.20, 0.17, "A4/A5\n已观测配比候选\n6 行", WARM_LIGHT, WARM),
        (0.40, 0.68, 0.20, 0.17, "M0\nN–D 基线优化", TEAL_LIGHT, TEAL_DARK),
        (0.40, 0.38, 0.20, 0.17, "M1\nN–D–Q 条件优化", TEAL_LIGHT, TEAL_DARK),
        (0.40, 0.15, 0.20, 0.17, "P / M2\n配比与接口情景", WARM_LIGHT, WARM),
        (0.76, 0.39, 0.20, 0.22, "M3\nN–D–Q–p 联合模型\n暂不识别", "#F3E7E1", WARM),
    ]
    for x, y, w, h, text_value, fill, edge in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.012",
                                    facecolor=fill, edgecolor=edge, lw=1.0))
        ax.text(x + w / 2, y + h / 2, text_value, ha="center", va="center",
                fontsize=8.0, color=INK, linespacing=1.35)
    arrows = [
        ((0.24, 0.725), (0.40, 0.765), TEAL_DARK, "可识别"),
        ((0.24, 0.425), (0.40, 0.465), TEAL_DARK, "可识别"),
        ((0.24, 0.215), (0.40, 0.235), WARM, "离散情景"),
        ((0.60, 0.765), (0.76, 0.52), TEAL_DARK, "待桥接"),
        ((0.60, 0.465), (0.76, 0.49), TEAL_DARK, "待桥接"),
        ((0.60, 0.235), (0.76, 0.48), WARM, "假设接口"),
    ]
    for start, end, color, label in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                                     lw=1.2, color=color, connectionstyle="arc3,rad=0.02"))
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mx, my + 0.035, label, fontsize=6.5, color=color, ha="center", va="center")
    ax.text(0.76, 0.31, "缺少 A–B 行级连接键\nQ1 与 B6 质量尺度未校准\nG_bridge 未识别",
            ha="center", va="center", fontsize=6.8, color=WARM)
    title(fig, "问题三模型接口与可识别性边界",
          "M0、M1 可以分别给出条件资源配置；P/M2 保留为配比或尺度接口情景。",
          "该图是方法结构示意，不表示 M3 联合模型已经完成参数估计。")
    save(fig, "Fig13_identifiability_interface")
    return {"blocks": len(boxes), "status": "M3 blocked pending A-B bridge and Q-scale calibration"}


def main() -> None:
    style()
    results = {
        "Fig06_M0_budget_context": fig06_m0_budget_context(),
        "Fig07_M1_quality_tradeoff": fig07_m1_quality_tradeoff(),
        "Fig08_Q0_cost_robustness": fig08_q0_cost_robustness(),
        "Fig09_parameter_uncertainty": fig09_parameter_uncertainty(),
        "Fig10_discrete_pareto": fig10_discrete_pareto(),
        "Fig11_p_candidate_panel": fig11_p_candidate_panel(),
        "Fig12_M2_interface_heatmap": fig12_m2_interface_heatmap(),
        "Fig13_identifiability_interface": fig13_identifiability_interface(),
    }
    input_paths = [
        "experiments/runs/q3-nd-baseline-20260925-r01/tables/q3_nd_baseline_scenarios.csv",
        "experiments/runs/q3-q-conditional-20260925-r01/tables/q3_q_conditional_scenarios.csv",
        "experiments/runs/q3-q-robustness-20260925-r01/tables/q3_q_robustness_scenarios.csv",
        "experiments/runs/q3-p-conditional-20260925-r01/tables/p_candidate_summary.csv",
        "experiments/runs/q3-p-conditional-20260925-r01/tables/p_candidate_q3_nd_panel.csv",
        "experiments/runs/q3-optimization-robustness-20260926-r01/tables/m0_uncertainty_summary.csv",
        "experiments/runs/q3-optimization-robustness-20260926-r01/tables/m1_uncertainty_summary.csv",
        "experiments/runs/q3-optimization-robustness-20260926-r01/tables/m0_discrete_frontier.csv",
        "experiments/runs/q3-optimization-robustness-20260926-r01/tables/m1_discrete_frontier.csv",
        "experiments/runs/q2-q3-interface-sensitivity-20260926-r01/tables/m2_q3_fixed_q_scenarios.csv",
    ]
    manifest = {
        "backend": "Python/matplotlib",
        "style_inheritance": "Q3 existing Nature-style figures: white background, charcoal ink, teal primary, warm orange contrast",
        "status": "conditional_scenario_figures_for_manuscript",
        "input_sha256": {},
        "figures": results,
    }
    for rel in input_paths:
        digest = hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
        manifest["input_sha256"][rel] = digest
    (HERE / "figure_manifest_missing.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
