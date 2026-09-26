# LaTeX 论文

论文源文件以 `main.tex` 为唯一入口，采用 `template/` 中的用户提供 GMCM2026 模板。当前入口装配问题一的质量评价与冲突消解正文，并接入问题三资源配置的探索性候选章节。问题三运行 `q3-frozen-q2-exploration-20260925-r01` 仍为 `REVIEW_BLOCKED / EXPLORATION_ONLY`；接入是排版和协作审阅，不表示模型已通过独立验证或可以给出最终训练建议。问题二的候选章节仍在 `sections/drafts/`，尚未作为正式正文装配。

## 目录约定

- `main.tex`：唯一编译入口，负责模板参数、队伍信息、摘要和章节装配。
- `sections/q1-quality-evaluation.tex`：第一部分，包含数据预处理、CRITIC--TOPSIS 评分、领域聚合和敏感性分析。
- `sections/q1-conflict-resolution.tex`：第二部分，包含冲突定义、成因分析、有限补偿模型和扩展集结果。
- `sections/drafts/q3-resource-optimization.tex`：第三问的条件资源优化、五图一表和适用边界；由 `main.tex` 引入供排版审阅。
- `sections/drafts/`：保留原始稿件，作为正文来源和审阅追溯。
- `commands.tex`：统一数学符号和项目命令。
- `refs.bib`：项目参考文献库；模板示例参考文献保留在 `template/reference.bib`。
- `template/`：GMCM2026 模板和版式素材。
- `figures/`：论文正文图形；正文引用的 PDF 图形均保留在相应子目录。
- `figures/q3/figures/`：问题三五张正文图的 PDF 及其他格式，源表和绘图脚本在 `figures/q3/`。
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
