"""Nature-style figures for the unified Q4 results.

The script reads only the local Attachment C directory and public aggregate
metrics from the Q4 run. It writes publication exports plus compact source
tables under paper/figures/q4/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

# Required Nature-figure editable-text settings.
# Keep the canonical declarations in this file for source-level QA:
# svg.fonttype='none'; pdf.fonttype=42
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

PALETTE = {
    "teal_dark": "#56808A",
    "teal_mid": "#82A8AD",
    "teal_light": "#C9DCDD",
    "slate": "#687B84",
    "ink": "#26343B",
    "warm": "#C47B52",
    "warm_light": "#E6B79D",
    "grey": "#AEB8BC",
    "grid": "#DDE5E7",
    "green": "#6B9E7B",
}


def style(font_size: float = 8.0) -> None:
    mpl.rcParams.update({
        "font.size": font_size,
        "axes.titlesize": font_size + 1,
        "axes.labelsize": font_size,
        "xtick.labelsize": font_size - 0.4,
        "ytick.labelsize": font_size - 0.4,
        "legend.fontsize": font_size - 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.75,
        "xtick.color": PALETTE["slate"],
        "ytick.color": PALETTE["slate"],
        "axes.labelcolor": PALETTE["ink"],
        "text.color": PALETTE["ink"],
        "axes.edgecolor": PALETTE["slate"],
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def panel_label(ax, label: str) -> None:
    ax.text(-0.09, 1.05, label, transform=ax.transAxes, fontsize=10,
            fontweight="bold", ha="left", va="bottom", color=PALETTE["ink"])


def light_grid(ax) -> None:
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax.set_axisbelow(True)


def save_pub(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / f"{stem}.tiff", dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def load_q4(base: Path, run: Path) -> dict[str, pd.DataFrame]:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "q4"))
    from q4_baseline_experiment import load_c8_scores

    lb = pd.read_csv(base / "leaderboard_cleaned.csv", parse_dates=["Submission Date"])
    c8 = load_c8_scores(base / "detailed_results")
    joined = lb.merge(c8[["Model", "c8_score"]], on="Model", how="inner")
    n_before = len(joined)
    joined = joined.dropna(subset=["Submission Date", "c8_score"]).copy()
    n_after = len(joined)
    joined["month"] = joined["Submission Date"].dt.to_period("M").dt.to_timestamp()
    joined = joined[(joined.month >= "2024-06-01") & (joined.month <= "2025-03-01")]
    type_map = {
        "pretrained": "pretrained",
        "chat": "chat",
        "fine-tuned": "fine-tuned",
        "merge": "merge",
    }
    def cat(x: object) -> str:
        s = str(x or "").lower()
        if "pretrained" in s:
            return "pretrained"
        if "chat" in s:
            return "chat"
        if "fine-tuned" in s or "fine tuned" in s:
            return "fine-tuned"
        if "merge" in s or "moerge" in s:
            return "merge"
        return "other"
    joined["type_clean"] = joined["Type"].map(cat)
    months = pd.period_range("2024-06", "2025-03", freq="M").to_timestamp()
    monthly_c8 = joined.groupby("month")["c8_score"].agg(q95=lambda z: z.quantile(.95), n="size").reindex(months).rename_axis("month").reset_index()
    monthly_c8["month_label"] = monthly_c8["month"].dt.strftime("%y-%m")
    avg_before = len(lb)
    avg = lb.dropna(subset=["Submission Date", "Average ⬆️"]).copy()
    avg_after = len(avg)
    avg["month"] = avg["Submission Date"].dt.to_period("M").dt.to_timestamp()
    avg = avg[(avg.month >= "2024-06-01") & (avg.month <= "2025-03-01")]
    monthly_avg = avg.groupby("month")["Average ⬆️"].agg(q95=lambda z: z.quantile(.95)).reindex(months).rename_axis("month").reset_index()
    monthly_avg["month_label"] = monthly_avg["month"].dt.strftime("%y-%m")
    boot_path = run / "artifacts" / "robustness" / "c8_equal_task_frontier_bootstrap.csv"
    if not boot_path.exists():
        raise FileNotFoundError(
            f"Expected observed-score bootstrap artifact is missing: {boot_path}. "
            "Regenerate the Q4 robustness artifact before plotting."
        )
    boot = pd.read_csv(boot_path, parse_dates=["month"])
    boot = boot[boot.month.isin(months)].sort_values("month")
    task = pd.read_csv(run / "metrics" / "task_frontiers.csv")
    task = task[task.target.isin(["IFEval", "BBH", "MATH", "GPQA", "MUSR", "MMLU_PRO"])].copy()
    rolling = pd.read_csv(run / "metrics" / "q4_protocol_rolling_horizon_metrics.csv")
    scenarios = pd.read_csv(run / "metrics" / "q4_protocol_12m_platform_trend_scenarios.csv")
    composition = joined[joined.type_clean.isin(["pretrained", "chat", "fine-tuned", "merge"])]
    composition = composition.groupby(["month", "type_clean"]).size().unstack(fill_value=0).reindex(months, fill_value=0)
    composition = composition.div(composition.sum(axis=1), axis=0).rename_axis("month").reset_index()
    composition["month_label"] = composition["month"].dt.strftime("%y-%m")
    exclusions = pd.DataFrame([
        {"table": "leaderboard × C8", "n_before": n_before, "n_after": n_after, "n_excluded": n_before - n_after},
        {"table": "leaderboard Average", "n_before": avg_before, "n_after": avg_after, "n_excluded": avg_before - avg_after},
    ])
    return {"joined": joined, "monthly_c8": monthly_c8, "monthly_avg": monthly_avg,
            "boot": boot, "task": task, "rolling": rolling,
            "scenarios": scenarios, "composition": composition, "exclusions": exclusions}


def write_sources(data: dict[str, pd.DataFrame], out_dir: Path) -> None:
    src = out_dir / "source_data"
    src.mkdir(parents=True, exist_ok=True)
    for key in ["monthly_c8", "monthly_avg", "boot", "task", "rolling", "scenarios", "composition", "exclusions"]:
        data[key].to_csv(src / f"q4_{key}.csv", index=False)


def figure_frontier(data: dict[str, pd.DataFrame], out_dir: Path) -> None:
    style(8.0)
    fig = plt.figure(figsize=(7.2, 5.1))
    gs = fig.add_gridspec(2, 2, hspace=0.48, wspace=0.32, left=0.08, right=0.98, top=0.90, bottom=0.13)
    months = data["monthly_c8"]["month"]
    x = np.arange(len(months))

    ax = fig.add_subplot(gs[0, 0]); panel_label(ax, "a")
    boot = data["boot"].sort_values("month")
    ax.fill_between(np.arange(len(boot)), boot.q95_boot_lo, boot.q95_boot_hi,
                    color=PALETTE["teal_light"], alpha=0.9, linewidth=0)
    ax.plot(np.arange(len(boot)), boot.q95, color=PALETTE["teal_dark"], marker="o", markersize=3.8, linewidth=2, label="C8 q95")
    avg = data["monthly_avg"]
    ax.plot(x, avg.q95, color=PALETTE["slate"], linestyle=(0, (3, 2)), marker="s", markersize=2.8, linewidth=1.15, label="Average q95")
    ax.axvspan(-0.4, 6.5, color=PALETTE["teal_light"], alpha=0.16, zorder=-2)
    ax.axvspan(6.5, 9.4, color=PALETTE["warm_light"], alpha=0.12, zorder=-2)
    ax.axvline(6.5, color=PALETTE["warm"], linewidth=0.85, linestyle="--")
    ax.text(2.9, 58.7, "训练期", ha="center", va="top", color=PALETTE["teal_dark"], fontsize=7)
    ax.text(8.0, 58.7, "测试期", ha="center", va="top", color=PALETTE["warm"], fontsize=7)
    ax.set_ylabel("月度前沿 q95")
    ax.set_xticks(x); ax.set_xticklabels(data["monthly_c8"]["month_label"], rotation=45, rotation_mode="anchor", ha="right")
    ax.set_ylim(38, 61); light_grid(ax)
    ax.legend(loc="lower right", handlelength=1.8, frameon=False)
    ax.set_title("C8 前沿沿时间上升，但评分口径不同", loc="left", pad=8, fontweight="bold")

    ax = fig.add_subplot(gs[0, 1]); panel_label(ax, "b")
    task = data["task"].sort_values("change_last_minus_first", ascending=True)
    colors = [PALETTE["warm"] if t == "MATH" else PALETTE["teal_dark"] for t in task.target]
    y = np.arange(len(task))
    ax.barh(y, task.change_last_minus_first, color=colors, height=0.58)
    ax.set_yticks(y); ax.set_yticklabels(task.target)
    ax.set_xlabel("首末月 q95 变化（分）")
    ax.axvline(0, color=PALETTE["slate"], linewidth=0.75)
    for yi, val in zip(y, task.change_last_minus_first):
        ax.text(val + 0.45, yi, f"{val:.1f}", va="center", fontsize=7, color=PALETTE["ink"])
    ax.set_xlim(0, 31); light_grid(ax)
    ax.set_title("MATH 放大趋势，其他任务仍同向", loc="left", pad=8, fontweight="bold")

    ax = fig.add_subplot(gs[1, 0]); panel_label(ax, "c")
    comp = data["composition"].set_index("month").reindex(months)
    bottom = np.zeros(len(comp))
    type_colors = {"pretrained": PALETTE["teal_dark"], "chat": PALETTE["teal_mid"],
                   "fine-tuned": PALETTE["warm"], "merge": PALETTE["slate"]}
    for typ in ["pretrained", "chat", "fine-tuned", "merge"]:
        values = comp[typ].to_numpy(float)
        ax.fill_between(x, bottom, bottom + values, step="mid", color=type_colors[typ], alpha=0.92, linewidth=0)
        bottom += values
    ax.set_ylim(0, 1); ax.set_ylabel("模型类型比例")
    ax.set_xticks(x); ax.set_xticklabels(data["composition"]["month_label"], rotation=45, rotation_mode="anchor", ha="right")
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0))
    ax.legend(["pretrained", "chat", "fine-tuned", "merge"], loc="upper left", ncol=2, handlelength=1.2, columnspacing=0.8)
    light_grid(ax); ax.set_title("前沿样本构成持续变化", loc="left", pad=8, fontweight="bold")

    ax = fig.add_subplot(gs[1, 1]); panel_label(ax, "d")
    r = data["rolling"][(data["rolling"].score == "c8_q95") & (data["rolling"].horizon_months == 1)].copy()
    r["cohort_label"] = r["cohort"].map({"all_four_types": "四类全量", "pretrained_only": "Pretrained-only"})
    method_labels = {"linear_last_4": "最近四点线性", "linear_all": "扩展线性", "mean_last_3": "近三月均值", "naive_last": "最近值"}
    for cohort, marker, color in [("all_four_types", "o", PALETTE["teal_dark"]), ("pretrained_only", "^", PALETTE["warm"])]:
        sub = r[r.cohort == cohort]
        for _, row in sub.iterrows():
            ax.scatter(row.MAE, row.R2, s=32, marker=marker, color=color, edgecolor="white", linewidth=0.5, zorder=3)
            if cohort == "all_four_types" or row.method == "mean_last_3":
                ax.annotate(method_labels[row.method], (row.MAE, row.R2), xytext=(4, 4), textcoords="offset points", fontsize=6.4)
    ax.axhline(0, color=PALETTE["slate"], linewidth=0.75)
    ax.set_xlabel("h=1 MAE（分）"); ax.set_ylabel("普通测试 R²")
    ax.set_xlim(-0.2, 15); ax.set_ylim(-2.2, 0.9); light_grid(ax)
    ax.scatter([], [], marker="o", color=PALETTE["teal_dark"], label="四类全量")
    ax.scatter([], [], marker="^", color=PALETTE["warm"], label="Pretrained-only")
    ax.legend(loc="lower left", handletextpad=0.4)
    ax.set_title("pretrained-only 短期误差更不稳定", loc="left", pad=8, fontweight="bold")
    fig.suptitle("问题四：数据趋势、构成变化与短期验证", x=0.08, ha="left", y=0.975, fontsize=12, fontweight="bold", color=PALETTE["ink"])
    fig.text(0.08, 0.035, "阴影为月度横截面 bootstrap 95% 区间；h=1 测试点数 n=3，h=3 仅 1 个起点。", color=PALETTE["slate"], fontsize=6.6)
    save_pub(fig, out_dir, "FigQ4_01_frontier_validation")


def figure_scenarios(data: dict[str, pd.DataFrame], out_dir: Path) -> None:
    style(8.2)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw={"wspace": 0.38, "left": 0.09, "right": 0.98, "top": 0.83, "bottom": 0.23})
    ax = axes[0]; panel_label(ax, "a")
    s = data["scenarios"]
    mult_order = [1.0, 1.5, 2.3, 4.0, 5.0]
    base = s[s.type_shift == "baseline"].copy()
    base["compute_multiplier"] = pd.Categorical(base.compute_multiplier, categories=mult_order, ordered=True)
    for form, label, color, marker in [("platform", "平台型", PALETTE["teal_dark"], "o"), ("trend", "趋势型", PALETTE["warm"], "s")]:
        sub = base[base.forecast_form == form].sort_values("compute_multiplier")
        ax.plot(sub.compute_multiplier.astype(float), sub.q95_point, color=color, marker=marker, linewidth=2, markersize=4.5, label=label)
        for _, row in sub.iterrows():
            if row.compute_multiplier in [1.0, 2.3, 5.0]:
                ax.annotate(f"{row.q95_point:.1f}", (float(row.compute_multiplier), row.q95_point), xytext=(0, 7 if form == "trend" else -13), textcoords="offset points", ha="center", fontsize=6.5, color=color)
    ax.set_xlabel("年算力倍率"); ax.set_ylabel("12 个月 C8 q95")
    ax.set_xticks(mult_order); ax.set_xticklabels(["1.0×", "1.5×", "2.3×", "4.0×", "5.0×"])
    ax.set_ylim(55, 79); light_grid(ax); ax.legend(loc="upper left")
    ax.set_title("时间项设定的影响大于算力倍率", loc="left", pad=8, fontweight="bold")

    ax = axes[1]; panel_label(ax, "b")
    sens = s[(s.compute_multiplier == 2.3) & (s.type_shift.isin(["baseline", "pretrained_plus_10pp", "pretrained_minus_10pp", "chat_plus_10pp", "chat_minus_10pp"]))]
    labels = {"baseline": "基准", "pretrained_plus_10pp": "pretrained +10pp", "pretrained_minus_10pp": "pretrained −10pp", "chat_plus_10pp": "chat +10pp", "chat_minus_10pp": "chat −10pp"}
    order = ["baseline", "pretrained_plus_10pp", "pretrained_minus_10pp", "chat_plus_10pp", "chat_minus_10pp"]
    xpos = np.arange(len(order)); width = 0.36
    for offset, form, color, label in [(-width / 2, "platform", PALETTE["teal_dark"], "平台型"), (width / 2, "trend", PALETTE["warm"], "趋势型")]:
        vals = [float(sens[(sens.type_shift == k) & (sens.forecast_form == form)].weighted_mean.iloc[0]) for k in order]
        ax.bar(xpos + offset, vals, width=width, color=color, label=label)
    ax.set_xticks(xpos); ax.set_xticklabels([labels[k] for k in order], rotation=35, rotation_mode="anchor", ha="right")
    ax.set_ylabel("2.3×情景的加权平均分")
    ax.set_ylim(48, 66); light_grid(ax); ax.legend(loc="upper left")
    ax.set_title("类型比例扰动是次级敏感性", loc="left", pad=8, fontweight="bold")
    fig.suptitle("问题四：未来 12 个月的算力—时间情景", x=0.09, ha="left", y=0.965, fontsize=12, fontweight="bold", color=PALETTE["ink"])
    fig.text(0.09, 0.045, "算力倍率由问题三规模弹性外生给出；profile range 不等同于时间预测置信区间。", color=PALETTE["slate"], fontsize=6.7)
    save_pub(fig, out_dir, "FigQ4_02_12m_scenarios")


def figure_workflow(out_dir: Path) -> None:
    style(8.4)
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    boxes = [
        (0.04, 0.54, 0.16, 0.24, "附件 C\n数据审计与投毒隔离", PALETTE["teal_light"], PALETTE["teal_dark"]),
        (0.24, 0.54, 0.16, 0.24, "C8 六任务\n等权分数与月度 q95", "#DCE8E7", PALETTE["teal_dark"]),
        (0.44, 0.54, 0.16, 0.24, "70/30 时间外验证\nh=1 / h=3", "#E7EDF0", PALETTE["slate"]),
        (0.64, 0.54, 0.16, 0.24, "面板分位数模型\n参数 + 时间 + 类型", "#F0E1D8", PALETTE["warm"]),
        (0.84, 0.54, 0.12, 0.24, "12 个月\n情景", "#E7E4EA", "#7C6C8A"),
    ]
    for x, y, w, h, label, face, edge in boxes:
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.1, facecolor=face, edgecolor=edge)
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=8, color=PALETTE["ink"], linespacing=1.35)
    for (x1, y1, w1, h1, *_), (x2, y2, w2, h2, *_) in zip(boxes[:-1], boxes[1:]):
        arr = FancyArrowPatch((x1 + w1 + 0.008, y1 + h1 / 2), (x2 - 0.008, y2 + h2 / 2), arrowstyle="-|>", mutation_scale=12, linewidth=1.1, color=PALETTE["slate"])
        ax.add_patch(arr)
    # External Q2/Q3 input enters only at the scenario layer.
    ext = FancyBboxPatch((0.36, 0.12), 0.28, 0.20, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.0, facecolor="#F3EEE5", edgecolor=PALETTE["warm"])
    ax.add_patch(ext)
    ax.text(0.50, 0.22, "问题二/三外生输入\nN*(C)、D*(C) 与算力倍率", ha="center", va="center", fontsize=7.7, color=PALETTE["ink"], linespacing=1.35)
    arr = FancyArrowPatch((0.64, 0.32), (0.72, 0.53), connectionstyle="arc3,rad=0.15", arrowstyle="-|>", mutation_scale=12, linewidth=1.0, color=PALETTE["warm"])
    ax.add_patch(arr)
    ax.text(0.50, 0.91, "问题四的直接预测独立于前三问；前三问只进入未来情景层", ha="center", va="center", fontsize=10, fontweight="bold", color=PALETTE["ink"])
    ax.text(0.50, 0.03, "主结果：C8 前沿预测 · 平台型 / 趋势型 / 算力约束型", ha="center", va="center", fontsize=7.2, color=PALETTE["slate"])
    save_pub(fig, out_dir, "FigQ4_03_workflow")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path.cwd() / "data/origin/C_efficiency_evolution")
    ap.add_argument("--run-dir", type=Path, default=Path("experiments/runs/q4-system-20260926-r01"))
    ap.add_argument("--out-dir", type=Path, default=Path("paper/figures/q4"))
    args = ap.parse_args()
    data = load_q4(args.data_dir, args.run_dir)
    write_sources(data, args.out_dir)
    figure_frontier(data, args.out_dir)
    figure_scenarios(data, args.out_dir)
    figure_workflow(args.out_dir)
    print(f"Wrote Q4 figures to {args.out_dir}")


if __name__ == "__main__":
    main()
