# LaTeX 论文

论文源文件以 `main.tex` 为唯一入口，采用 `template/` 中的用户提供 GMCM2026 模板。当前入口装配问题一的三部分正文：数据质量评价与基础评分、质量冲突消解与综合评价模型、训练配比效应与规模修正。

正文公式每条独占一个居中编号环境，前置简短公式名；图题独立、简短且居中。图形细节与适用边界在正文解释。

## 目录约定

- `main.tex`：唯一编译入口，负责模板参数、队伍信息、摘要和章节装配。
- `sections/q1-quality-evaluation.tex`：第一部分，包含数据预处理、CRITIC--TOPSIS 评分、领域聚合和敏感性分析。
- `sections/q1-conflict-resolution.tex`：第二部分，包含冲突定义、成因分析、有限补偿模型和扩展集结果。
- `sections/q1-mixture-scale.tex`：第三部分，包含配比替代效应、同尺度预测、跨规模修正和校准诊断。
- `sections/references.tex`：三部分正文共用的参考文献列表。
- `sections/drafts/`：保留原始稿件，作为正文来源和审阅追溯。
- `commands.tex`：统一数学符号和项目命令。
- `refs.bib`：项目参考文献库；模板示例参考文献保留在 `template/reference.bib`。
- `template/`：GMCM2026 模板和版式素材。
- `figures/`：论文正文图形；正文引用的 PDF 图形均保留在相应子目录。
- `figures/q1-mixture-scale/`：第三部分的五张正文图和两张补充图。
- `OVERLEAF-PREVIEW.md`：Overleaf 编译预览及已知局限。
- `official-template-checklist.md`：提交前的格式、匿名和材料核对表。

## 编译

从仓库根目录运行：

```powershell
.\scripts\compile_paper.ps1
```

或者从 `paper/` 目录运行：

```powershell
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

提交前请在 `main.tex` 中填写队伍编号、学校和三名成员信息，并根据当届组委会要求复核封面、摘要、页码、篇幅和匿名规则。论文中的数字应能追溯到 `experiments/runs/` 中的 `run_id`。
