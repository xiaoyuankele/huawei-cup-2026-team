# 问题二 LaTeX 候选正文

状态：`DRAFT / REVIEW_BLOCKED`。正文在 `q2-current-stage.tex`，使用已有六张 `paper/figures/q2-scaling-law/` 矢量 PDF 图。`q2-current-stage-standalone.tex` 是审阅入口；正式主论文仍由 `paper/main.tex` 控制，待团队独立科学评审后再决定是否接入。

从仓库 `paper/` 目录运行 `xelatex sections/drafts/q2-current-stage-standalone.tex`，再次运行以解析交叉引用。本机没有安装 XeLaTeX，因此这次完成了源码静态核查，尚无 PDF 编译验收。

## 数值与主张来源

| 正文内容 | 仓库内依据 |
|---|---|
| 式 (3-1)–(3-4)、冻结参数及训练支持范围 | `docs/problem/q2-generalized-scaling-model-v1.md`；`experiments/runs/q2-model-finalization-20260925/model_parameters.json` |
| B1 留一规模、B6/B7 质量增量、A 同规模配比误差 | `experiments/runs/q2-model-finalization-20260925/` 内的 `scale_oof_summary.csv`、`quality_increment_summary.csv`、`mixture_validation.csv` |
| B2/A 60M/A 1B 嵌套迁移误差 | `experiments/runs/q2-transfer-improvement-20260925/performance_summary.csv` |
| 边际效用、弹性与质量轴导数 | `experiments/runs/q2-e1-marginal-elasticity-20260925-r01/report.md` |
| 领域转移支持、假设翻转与四角交互 | `experiments/runs/q2-e2-domain-substitution-20260925-r01/report.md` |
| 六张图的绘制协议与限制 | `paper/figures/q2-scaling-law/README.md` 及 `figure_manifest.json` |

质量轴提高 0.1 对应的参数等效值是根据冻结公式新推导的**条件情景**：TOPSIS 参考配方的映射值约为 0.7494，增至 0.8494 仍在映射内部；在 $N=1$ 十亿、$\lambda_Q=1$ 时，等效规模为约 1.3734 十亿。此数值未接受独立的四变量联合实验检验。

## 接入前必须核对

- 论文 Owner 与独立 Reviewer 核对 B1、B6/B7、A 侧来源属性及图注后，再将正文接入 `paper/main.tex`。
- 用仓库 GMCM 模板的 XeLaTeX 编译完整论文，检查分页、浮动体和中文断行；`ctexart` 独立入口只用于段落审阅。
- 保留 B8 方向冲突、B9/B10 非实测 Loss、A 1B 迁移失败，以及缺少联合观测的证据限制。
