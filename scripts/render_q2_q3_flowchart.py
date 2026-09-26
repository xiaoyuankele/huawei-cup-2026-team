"""Render the Q2-Q3 exploratory architecture as a publication-readable PNG."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "experiments" / "q2-q3-exploratory-architecture.png"

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(18, 25), dpi=180)
ax.set_xlim(0, 18)
ax.set_ylim(0, 25)
ax.axis("off")
fig.patch.set_facecolor("white")

COLORS = {
    "data": (0.93, 0.95, 0.97),
    "audit": (1.00, 0.96, 0.84),
    "model": (0.90, 1.00, 0.93),
    "valid": (0.91, 0.95, 1.00),
    "opt": (0.95, 0.91, 1.00),
    "gate": (1.00, 0.91, 0.93),
    "blocked": (1.00, 0.84, 0.85),
}
EDGES = {
    "data": "#4a5568", "audit": "#b7791f", "model": "#2f855a",
    "valid": "#3973b8", "opt": "#805ad5", "gate": "#c53030", "blocked": "#c53030",
}


def group(y, h, title, kind):
    ax.add_patch(Rectangle((0.35, y), 17.3, h, facecolor=COLORS[kind],
                           edgecolor=EDGES[kind], linewidth=1.8, alpha=0.28,
                           zorder=0))
    ax.text(0.62, y + h - 0.36, title, fontsize=15, fontweight="bold",
            color=EDGES[kind], va="top")


def box(x, y, w, h, text, kind, fontsize=10.5, bold=False):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                           facecolor=COLORS[kind], edgecolor=EDGES[kind], linewidth=1.5,
                           zorder=3)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color="#1a202c", fontweight="bold" if bold else "normal",
            linespacing=1.25, zorder=4)
    return (x, y, w, h)


def arrow(a, b, *, dashed=False, color="#4a5568", lw=1.3, bend=0):
    x1, y1 = a
    x2, y2 = b
    style = "--" if dashed else "-"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                linestyle=style, mutation_scale=13,
                                connectionstyle=f"arc3,rad={bend}"), zorder=2)


ax.text(9, 24.55, "问题二—问题三探索性实验架构与流程", ha="center", va="center",
        fontsize=23, fontweight="bold", color="#1a202c")
ax.text(9, 24.12, "只读数据 · 分层验证 · 条件优化 · 投毒隔离", ha="center", va="center",
        fontsize=12.5, color="#4a5568")

start = box(6.0, 22.85, 6.0, 0.78,
            "实验卡冻结\nexperiment_id / run_id / 假设 / 主张边界", "data", 11, True)

group(19.70, 2.55, "只读数据与血缘层", "data")
data = [
    box(0.70, 20.25, 2.15, 1.15, "A1–A3\n质量信号\n域级候选 q", "data"),
    box(2.98, 20.25, 2.15, 1.15, "A4–A15\n17 域配比 p\n与 Loss 配对", "data"),
    box(5.26, 20.25, 2.15, 1.15, "A16\n域映射\ndirect / near / inferred", "data", 9.6),
    box(7.54, 20.25, 2.15, 1.15, "B1–B5\nN–D 标度\n与来源分层", "data"),
    box(9.82, 20.25, 2.15, 1.15, "B6–B8\nQ_score 半合成\n敏感性", "data"),
    box(12.10, 20.25, 2.15, 1.15, "B9–B10\n外推范围\n与来源诊断", "data"),
    box(14.38, 20.25, 2.15, 1.15, "C7\n可行上下文\n长度", "data"),
]

group(17.15, 1.95, "数据与接口审计", "audit")
g0 = box(3.35, 17.68, 4.5, 0.86, "G0 数据门：路径 / 哈希 / 角色 / 投毒隔离", "audit", 10.8, True)
bridge = box(10.15, 17.68, 4.5, 0.86, "A–B 接口审计：真实 join_key？映射覆盖？", "audit", 10.5, True)

group(14.05, 2.55, "隔离模型轨道", "model")
m0 = box(0.80, 14.55, 3.7, 1.12, "M0 B1 经典 N–D\nL = E + A·N^(-alpha) + B·D^(-beta)", "model", 9.5)
m1 = box(4.75, 14.55, 3.7, 1.12, "M1 B6/B7 条件质量\nM0 + G·(1 − Q_score)", "model", 10.5)
ap = box(8.70, 14.55, 3.7, 1.12, "A 侧配比模型\nL_A = f(p)\n组成数据变换", "model", 10.5)
m2 = box(12.65, 14.55, 3.7, 1.12, "M2 Q(p) 情景\nQ_direct / Q_near / Q_range", "model", 10.5)

group(10.90, 2.55, "分层验证层", "valid")
v0 = box(0.65, 11.40, 3.05, 1.12, "B1 分组留出", "valid")
v1 = box(3.90, 11.40, 3.05, 1.12, "B2/B3/B4/B5\n来源或轨迹诊断", "valid")
v2 = box(7.15, 11.40, 3.05, 1.12, "B6 ND 单元留出\nB7 嵌套扩展", "valid")
v3 = box(10.40, 11.40, 3.05, 1.12, "A6–A11 验证\nA12–A15 外推诊断", "valid", 9.9)
v4 = box(13.65, 11.40, 3.05, 1.12, "映射覆盖与不确定性\n不得静默插补", "valid", 9.7)

group(7.70, 2.55, "问题三条件优化层", "opt")
o0 = box(0.80, 8.20, 3.7, 1.12, "Q3–ND 基线\n固定 Q = Q0，p = p0", "opt", 10.5)
o1 = box(4.75, 8.20, 3.7, 1.12, "质量条件情景\n比较 g(Q)", "opt", 10.5)
o2 = box(8.70, 8.20, 3.7, 1.12, "配比条件情景\n只使用 A 侧或 Q(p) 区间", "opt", 9.8)
sens = box(12.65, 8.20, 3.7, 1.12, "预算 / Lctx / 参数\n成本占比与结构转移", "opt", 10.3)

group(4.70, 2.55, "发布门", "gate")
g1 = box(0.55, 5.20, 3.0, 1.12, "G1 模型门\n公式 / 单位 / 切分冻结", "gate", 9.7)
g2 = box(3.78, 5.20, 3.0, 1.12, "G2 验证门\n训练 / 留出 / 外推分离", "gate", 9.7)
g3 = box(7.01, 5.20, 3.0, 1.12, "G3 优化门\n可行性 / 边界 / 多初值", "gate", 9.7)
g4 = box(10.24, 5.20, 3.0, 1.12, "G4 主张门\nclaim ledger / 哈希 / 限制", "gate", 9.4)
release = box(13.47, 5.20, 3.95, 1.12, "探索性 / 条件性结果包\nrun_id + metrics + claim ledger", "gate", 9.5, True)
blocked = box(6.05, 3.10, 5.9, 0.9, "REVIEW_BLOCKED：不得发布正式联合模型", "blocked", 12, True)

# Main vertical flow.
arrow((9.0, 22.85), (9.0, 22.05))
arrow((9.0, 19.70), (5.60, 18.55))
arrow((9.0, 19.70), (12.40, 18.55))
arrow((5.60, 17.68), (2.65, 15.67))
arrow((5.60, 17.68), (6.60, 15.67))
arrow((5.60, 17.68), (10.55, 15.67))
arrow((12.40, 17.68), (14.50, 15.67))
arrow((12.40, 17.68), (9.00, 3.95), dashed=True, color="#c53030", lw=1.5, bend=-0.10)

# Model -> validation.
arrow((2.65, 14.55), (2.15, 12.52))
arrow((2.65, 14.55), (5.40, 12.52))
arrow((6.60, 14.55), (8.65, 12.52))
arrow((10.55, 14.55), (11.90, 12.52))
arrow((14.50, 14.55), (15.20, 12.52))

# Validation convergence and optimization.
for x in (2.15, 5.40, 8.65, 11.90, 15.20):
    arrow((x, 11.40), (9.0, 10.90), color="#3973b8", bend=(x - 9.0) / 70)
arrow((9.0, 10.90), (2.65, 9.32), color="#805ad5", bend=0.12)
arrow((9.0, 10.90), (6.60, 9.32), color="#805ad5", bend=0.05)
arrow((9.0, 10.90), (10.55, 9.32), color="#805ad5", bend=-0.05)
arrow((2.65, 8.20), (14.50, 8.20), color="#805ad5", lw=1.5)
arrow((6.60, 8.20), (14.50, 8.20), color="#805ad5", lw=1.5)
arrow((10.55, 8.20), (14.50, 8.20), color="#805ad5", lw=1.5)
arrow((14.50, 8.20), (9.0, 6.32), color="#805ad5")

# Gate sequence and blocked paths.
arrow((9.0, 6.32), (2.05, 6.32), color="#c53030", bend=0.10)
arrow((2.05, 5.20), (5.28, 5.20), color="#c53030")
arrow((6.78, 5.20), (8.51, 5.20), color="#c53030")
arrow((10.01, 5.20), (11.74, 5.20), color="#c53030")
arrow((13.24, 5.20), (13.47, 5.75), color="#c53030")
arrow((6.78, 5.20), (9.0, 4.00), dashed=True, color="#c53030", bend=-0.15)
arrow((10.01, 5.20), (9.0, 4.00), dashed=True, color="#c53030", bend=0.15)

ax.text(0.65, 2.35, "颜色说明", fontsize=11.5, fontweight="bold", color="#1a202c")
legend = [("#4a5568", "数据/血缘"), ("#b7791f", "审计"), ("#2f855a", "模型"),
          ("#3973b8", "验证"), ("#805ad5", "优化"), ("#c53030", "发布门/阻断")]
for i, (c, label) in enumerate(legend):
    x = 0.70 + (i % 3) * 2.3
    y = 1.75 - (i // 3) * 0.45
    ax.add_patch(FancyBboxPatch((x, y), 0.28, 0.22, boxstyle="round,pad=0.02",
                                facecolor=c, edgecolor=c, zorder=3))
    ax.text(x + 0.40, y + 0.11, label, va="center", fontsize=9.5, color="#4a5568")
ax.text(17.1, 0.55, "注：REVIEW_BLOCKED 表示尚未具备正式 A–B 联合模型的发布条件。",
        ha="right", fontsize=9.5, color="#718096")

fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(OUT)
