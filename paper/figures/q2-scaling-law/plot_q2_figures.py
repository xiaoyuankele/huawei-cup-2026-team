"""Q2 evidence figures from frozen repository outputs.

Only visual conventions are inherited from the repository's Q1 figures.
No model is fitted or experimental value synthesized here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INK = "#29363D"
TEAL = "#527F88"
TEAL_LIGHT = "#C8DEDF"
WARM = "#C17855"
GREY = "#738087"
PALE = "#EDF0F1"
WHITE = "#FFFFFF"
FIG_WIDTH_MM = 183


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Hiragino Sans GB", "Arial", "DejaVu Sans"],
            "font.size": 8,
            "axes.titlesize": 8.5,
            "axes.labelsize": 8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
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


def source_path(repo: Path, relative: str) -> Path:
    path = repo / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def read_csv(repo: Path, relative: str, expected_rows: int | None = None) -> pd.DataFrame:
    frame = pd.read_csv(source_path(repo, relative))
    if expected_rows is not None and len(frame) != expected_rows:
        raise ValueError(f"Unexpected rows in {relative}: {len(frame)} != {expected_rows}")
    return frame


def make_canvas(height: float = 3.7):
    fig = plt.figure(figsize=(7.2047244094, height), facecolor=WHITE)
    return fig


def clean_axis(ax, grid_axis="x") -> None:
    ax.spines["left"].set_color(GREY)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(color=GREY, labelcolor=INK, width=0.65, length=3)
    ax.grid(axis=grid_axis, color=PALE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)


def save_figure(fig, output: Path, stem: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    common = {"bbox_inches": "tight", "pad_inches": 0.06, "facecolor": WHITE}
    svg_path = output / f"{stem}.svg"
    fig.savefig(svg_path, **common)
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n")
    fig.savefig(output / f"{stem}.pdf", **common)
    fig.savefig(output / f"{stem}.png", dpi=600, **common)
    fig.savefig(output / f"{stem}.tiff", dpi=600, pil_kwargs={"compression": "tiff_lzw"}, **common)
    plt.close(fig)


def figure_01_scale(repo: Path, output: Path) -> dict:
    rel = "experiments/runs/q2-model-finalization-20260925/scale_validation.csv"
    frame = read_csv(repo, rel, 18)
    frame = frame[frame.fold.str.startswith("leave_N_")].copy()
    frame["N"] = frame.fold.str.removeprefix("leave_N_").astype(float)
    assert len(frame) == 16 and set(frame.model) == {"power", "log_linear"}
    assert frame.mae.gt(0).all() and frame.N.gt(0).all()
    pivot = frame.pivot(index="N", columns="model", values="mae").sort_index()
    assert pivot.shape == (8, 2)
    if np.any(pivot.index.to_numpy() <= 0) or np.any(pivot.to_numpy() <= 0):
        raise ValueError("Log axes require strictly positive N and MAE")

    fig = make_canvas(3.45)
    ax = fig.add_axes([0.13, 0.25, 0.82, 0.67])
    ax.scatter(pivot.index, pivot.log_linear, s=35, color=GREY, marker="o", label="对数线性", zorder=3)
    ax.scatter(pivot.index, pivot.power, s=37, color=TEAL, marker="D", label="经典幂律", zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.055, 15)
    ax.set_ylim(4e-5, 0.4)
    ax.set_xticks(pivot.index)
    ax.set_xticklabels([f"{v:.2g}" for v in pivot.index], rotation=25, ha="right", rotation_mode="anchor")
    ax.set_yticks([0.0001, 0.001, 0.01, 0.1], ["0.0001", "0.001", "0.01", "0.1"])
    ax.set_xlabel("留出的参数规模 N（十亿参数）", labelpad=8, color=INK)
    ax.set_ylabel("留出 MAE（Loss）", labelpad=7, color=INK)
    clean_axis(ax, "y")
    ax.legend(loc="upper right", frameon=False, ncol=2)
    save_figure(fig, output, "Fig01_B1_leave_size")
    return {"figure": "Fig01_B1_leave_size", "source": rel, "rows_used": 16, "unit": "held-out N size"}


def figure_02_quality(repo: Path, output: Path) -> dict:
    base = "experiments/runs/q2-model-finalization-20260925/"
    summary = read_csv(repo, base + "quality_increment_summary.csv", 15)
    folds = read_csv(repo, base + "quality_validation_folds.csv", 80)
    keep = {"scale_offset", "scale_Q"}
    s = summary[summary.model.isin(keep)]
    f = folds[folds.model.isin(keep)]
    pair_s = s.pivot(index="protocol", columns="model", values="mae")
    pair_f = f.pivot(index=["protocol", "fold"], columns="model", values="mae")
    assert pair_s.shape == (3, 2) and pair_f.shape == (16, 2)
    assert pair_s.notna().all().all() and pair_f.notna().all().all()
    pair_f["gain"] = pair_f.scale_offset - pair_f.scale_Q
    label = {"group_ND": "留出 (N,D) 组合", "leave_Q": "留出 Q 水平", "nonoverlap": "B6 → B7"}
    order = ["group_ND", "leave_Q", "nonoverlap"]

    fig = make_canvas(3.45)
    ax1 = fig.add_axes([0.17, 0.23, 0.35, 0.61])
    ax2 = fig.add_axes([0.66, 0.23, 0.29, 0.61])
    y = np.arange(3)[::-1]
    for yy, key in zip(y, order):
        b, q = pair_s.loc[key, ["scale_offset", "scale_Q"]]
        ax1.plot([q, b], [yy, yy], color=GREY, lw=0.7, zorder=1)
        ax1.scatter(b, yy, s=36, facecolors=WHITE, edgecolors=GREY, linewidths=1.1, zorder=3)
        ax1.scatter(q, yy, s=36, color=TEAL, edgecolors=WHITE, linewidths=0.5, zorder=4)
    ax1.set_yticks(y, [label[k] for k in order])
    ax1.set_xlim(0.025, 0.13)
    ax1.set_xlabel("汇总 MAE（Loss）", color=INK)
    ax1.set_title("a", loc="left", weight="bold", color=INK, pad=6)
    clean_axis(ax1)
    ax1.scatter([], [], s=42, facecolors=WHITE, edgecolors=GREY, label="不加 Q")
    ax1.scatter([], [], s=42, color=TEAL, label="加入 Q")
    fig.legend(*ax1.get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.42, 0.99),
               ncol=2, frameon=False, handletextpad=0.4, columnspacing=0.9)

    ax2.axvline(0, color=GREY, lw=0.65)
    for yy, key in zip(y, order):
        values = pair_f.loc[key, "gain"].to_numpy(dtype=float)
        offsets = np.linspace(-0.17, 0.17, len(values)) if len(values) > 1 else np.array([0.0])
        ax2.scatter(values, yy + offsets, s=26, facecolors=TEAL_LIGHT, edgecolors=TEAL, lw=0.6, zorder=3)
    ax2.set_yticks(y, ["", "", ""])
    ax2.set_xlim(-0.006, 0.15)
    ax2.set_xlabel("同折 MAE 改善量（Loss）", color=INK)
    ax2.set_title("b", loc="left", weight="bold", color=INK, pad=6)
    clean_axis(ax2)
    save_figure(fig, output, "Fig02_quality_increment")
    return {"figure": "Fig02_quality_increment", "sources": [base + "quality_increment_summary.csv", base + "quality_validation_folds.csv"], "rows_used": {"summary": 6, "fold": 32}, "unit": "validation fold"}


def figure_03_transfer(repo: Path, output: Path) -> dict:
    base = "experiments/runs/q2-transfer-improvement-20260925/"
    perf = read_csv(repo, base + "performance_summary.csv", 35)
    fold = read_csv(repo, base + "outer_fold_metrics.csv", 185)
    spec = [("B2", "scale", "none", "B2"),
            ("A60M", "full_mixture", "none", "A 60M"),
            ("A1B", "full_mixture", "none", "A 1B")]
    models = [("raw", "原模型", GREY, "o"), ("mean", "均值基线", WARM, "s"), ("selected", "嵌套选择", TEAL, "D")]

    fig = make_canvas(4.15)
    axs = [fig.add_axes([0.18, 0.68 - i * 0.25, 0.76, 0.17]) for i in range(3)]
    used_perf = 0
    used_fold = 0
    for panel, (ax, (task, branch, axis, title)) in enumerate(zip(axs, spec)):
        sub = perf[(perf.task == task) & (perf.branch == branch) & (perf.axis == axis)]
        folds = fold[(fold.task == task) & (fold.branch == branch) & (fold.axis == axis)]
        assert set(sub.model) == {"raw", "mean", "selected", "offset", "affine"}
        if np.any(sub.mae.to_numpy() <= 0):
            raise ValueError("Log MAE axis requires strictly positive values")
        used_perf += 3
        for pos, (model, display, color, marker) in enumerate(models):
            row = sub[sub.model == model].iloc[0]
            values = folds[folds.model == model].sort_values("fold").mae.to_numpy(dtype=float)
            assert len(values) == (7 if task == "B2" else 5)
            assert np.isfinite(values).all() and np.all(values > 0)
            used_fold += len(values)
            jitter = np.linspace(-0.11, 0.11, len(values))
            ax.scatter(values, pos + jitter, s=13, facecolors=WHITE, edgecolors=color, lw=0.65, alpha=0.65, zorder=2)
            ax.scatter(row.mae, pos, s=40, marker=marker, color=color, edgecolors=WHITE, lw=0.5, zorder=4)
        ax.set_xscale("log")
        ax.set_xlim(0.025, 4.5)
        ax.set_xticks([0.03, 0.1, 0.3, 1, 3], ["0.03", "0.1", "0.3", "1", "3"])
        ax.set_ylim(2.4, -0.4)
        ax.set_yticks(range(3), [m[1] for m in models])
        ax.set_title(f"{chr(97 + panel)}  {title}", loc="left", color=INK, fontsize=8, weight="bold", pad=3)
        clean_axis(ax)
        if ax is not axs[-1]:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("外层 MAE（Loss，对数坐标）", color=INK, labelpad=5)
    save_figure(fig, output, "Fig03_transfer_calibration")
    return {"figure": "Fig03_transfer_calibration", "sources": [base + "performance_summary.csv", base + "outer_fold_metrics.csv"], "rows_used": {"summary": used_perf, "fold": used_fold}, "unit": "held-out trajectory or recipe fold"}


def figure_04_mixture(repo: Path, output: Path) -> dict:
    rel = "experiments/runs/q2-model-finalization-20260925/mixture_validation.csv"
    frame = read_csv(repo, rel, 40)
    use = frame[(frame.axis == "Q_A_topsis_0_1") & frame.model.isin(["mean", "full_p"]) &
                frame.dataset.isin(["A6_A7_test_1m", "A8_A9_test_60m", "A10_A11_test_1b"])].copy()
    assert len(use) == 6
    dataset_order = ["A6_A7_test_1m", "A8_A9_test_60m", "A10_A11_test_1b"]
    names = ["1M", "60M", "1B"]
    fig = make_canvas(3.35)
    ax = fig.add_axes([0.13, 0.23, 0.82, 0.68])
    for pos, key in enumerate(dataset_order):
        part = use[use.dataset == key].set_index("model")
        b = float(part.loc["mean", "centered_rmse"])
        p = float(part.loc["full_p", "centered_rmse"])
        ax.scatter(pos - 0.09, b, s=48, facecolors=WHITE, edgecolors=GREY, lw=1.1, zorder=3)
        ax.scatter(pos + 0.09, p, s=48, color=TEAL, edgecolors=WHITE, lw=0.5, zorder=4)
    ax.set_xticks(range(3), names)
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(0, 0.315)
    ax.set_ylabel("中心化 RMSE（Loss）", labelpad=7, color=INK)
    clean_axis(ax, "y")
    ax.scatter([], [], s=60, facecolors=WHITE, edgecolors=GREY, label="均值基线")
    ax.scatter([], [], s=60, color=TEAL, label="完整配比")
    ax.legend(loc="upper right", ncol=2, frameon=False)
    save_figure(fig, output, "Fig04_mixture_scale")
    return {"figure": "Fig04_mixture_scale", "source": rel, "rows_used": 6, "unit": "held-out recipe row"}


def figure_05_b8(repo: Path, output: Path) -> dict:
    rel = "experiments/runs/q2-quality-scaling-linkage-20260925/quality-direction-audit.csv"
    frame = read_csv(repo, rel, 3)
    order = ["supplementary_NQ_experiment.csv", "supplementary_NQ_experiment_expanded.csv", "supplementary_NQ_experiment_large.csv"]
    names = ["B6", "B7", "B8"]
    frame = frame.set_index("dataset").loc[order]
    fig = make_canvas(3.1)
    ax = fig.add_axes([0.13, 0.25, 0.82, 0.64])
    ax.axvline(0, color=GREY, lw=0.7, zorder=1)
    y = np.arange(3)[::-1]
    for pos, name, (_, row) in zip(y, names, frame.iterrows()):
        x = float(row.median_within_ND_spearman)
        color = WARM if name == "B8" else TEAL
        ax.scatter(x, pos, color=color, s=44, edgecolors=WHITE, lw=0.6, zorder=3)
    ax.set_yticks(y, names)
    ax.set_xlim(-1.1, 1.1)
    ax.set_xlabel("组内 Spearman 相关系数的中位数", labelpad=7, color=INK)
    clean_axis(ax)
    save_figure(fig, output, "FigS01_B8_quality_direction")
    return {"figure": "FigS01_B8_quality_direction", "source": rel, "rows_used": 3, "unit": "N-D group"}


def figure_06_extrapolation(repo: Path, output: Path) -> dict:
    rel = "experiments/runs/q2-b9-b10-extrapolation-audit-20250925-r01/metrics.json"
    metrics = json.loads(source_path(repo, rel).read_text(encoding="utf-8"))
    params_rel = "experiments/runs/q2-model-finalization-20260925/model_parameters.json"
    params = json.loads(source_path(repo, params_rel).read_text(encoding="utf-8"))
    # The B1 support bounds are frozen in the model report; they are checked against
    # the parameter JSON before use instead of inferred from B9/B10.
    def find_n_bounds(obj):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key.lower() in {"n_params_b", "n_range", "n_b_range"} and isinstance(val, (list, tuple)) and len(val) == 2:
                    return float(val[0]), float(val[1])
                result = find_n_bounds(val)
                if result:
                    return result
        return None

    b1 = find_n_bounds(params)
    if b1 is None:
        b1 = (0.070542, 11.965825)
        serial = json.dumps(params)
        assert "11.965825" in serial and "0.070542" in serial, "B1 support changed"
    assert b1[0] > 0 and b1[1] > b1[0]
    rows = [("B1 主拟合", b1[0], b1[1], TEAL, "观测范围"),
            ("B9 大模型元数据", metrics["files"]["B9"]["n_min"], metrics["files"]["B9"]["n_max"], GREY, "非 Loss 验证"),
            ("B10 大模型基线", metrics["files"]["B10"]["n_min"], metrics["files"]["B10"]["n_max"], WARM, "估算 Loss")]
    assert all(low > 0 and high > low for _, low, high, _, _ in rows)
    if np.any(np.asarray([(low, high) for _, low, high, _, _ in rows]) <= 0):
        raise ValueError("Log N axis requires strictly positive range endpoints")
    fig = make_canvas(3.2)
    ax = fig.add_axes([0.14, 0.25, 0.81, 0.64])
    ax.axvline(b1[1], ls="--", color=GREY, lw=0.75, zorder=1)
    y = np.arange(3)[::-1]
    for pos, (name, low, high, color, role) in zip(y, rows):
        ax.plot([low, high], [pos, pos], color=color, lw=2.2, solid_capstyle="butt", zorder=3)
        ax.vlines([low, high], pos - 0.09, pos + 0.09, colors=color, lw=0.9, zorder=4)
    ax.set_xscale("log")
    ax.set_xlim(0.04, 20000)
    ax.set_xticks([0.1, 1, 10, 100, 1000, 10000], ["0.1", "1", "10", "100", "1,000", "10,000"])
    ax.set_ylim(-0.45, 2.5)
    ax.set_yticks(y, ["B1", "B9", "B10"])
    ax.set_xlabel("参数规模 N（十亿参数，对数坐标）", labelpad=7, color=INK)
    clean_axis(ax)
    save_figure(fig, output, "FigS02_large_model_range")
    return {"figure": "FigS02_large_model_range", "sources": [rel, params_rel], "rows_used": {"B9": metrics["files"]["B9"]["rows"], "B10": metrics["files"]["B10"]["rows"]}, "unit": "model record"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.out.resolve()
    setup_style()
    records = [fn(repo, output) for fn in (figure_01_scale, figure_02_quality, figure_03_transfer,
                                            figure_04_mixture, figure_05_b8, figure_06_extrapolation)]
    sources = sorted({rel for rec in records for rel in (rec.get("sources") or [rec.get("source")])})
    for rec in records:
        for ext in ("svg", "pdf", "png", "tiff"):
            assert (output / f"{rec['figure']}.{ext}").is_file()
    manifest = {"figures": records, "sources": {rel: hashlib.sha256(source_path(repo, rel).read_bytes()).hexdigest()
                                                    for rel in sources}, "backend": "Python/matplotlib",
                "style_reuse": "style only"}
    (output / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"figures": [r["figure"] for r in records], "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
