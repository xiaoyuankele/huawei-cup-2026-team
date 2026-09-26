# LaTeX 论文

论文源文件以 `main.tex` 为唯一入口，采用 `template/` 中的用户提供 GMCM2026 模板。当前入口装配两份已经形成正文的内容：数据质量评价与基础评分、质量冲突消解与综合评价模型。

## 目录约定

- `main.tex`：唯一编译入口，负责模板参数、队伍信息、摘要和章节装配。
- `q4-overleaf.tex`：问题四独立编译入口；可在 `paper/` 目录作为 Overleaf 项目根目录编译。
- `Q4-OVERLEAF-README.md`：问题四 Overleaf 依赖和提交前核对说明。
- `Q4-Manuscript-Package.zip`：问题四正文、图件、源数据、QA 记录和最小模板依赖的归档包。
- `sections/q1-quality-evaluation.tex`：第一部分，包含数据预处理、CRITIC--TOPSIS 评分、领域聚合和敏感性分析。
- `sections/q1-conflict-resolution.tex`：第二部分，包含冲突定义、成因分析、有限补偿模型和扩展集结果。
- `sections/drafts/q4-frontier-prediction.tex`：问题四正式章节，按最新大纲接入数据审计、短期验证、分位数模型、任务级证伪和十二个月情景。
- `sections/drafts/`：保留原始稿件，作为正文来源和审阅追溯。
- `commands.tex`：统一数学符号和项目命令。
- `refs.bib`：项目参考文献库；模板示例参考文献保留在 `template/reference.bib`。
- `template/`：GMCM2026 模板和版式素材。
- `figures/`：论文正文图形；正文引用的 PDF 图形均保留在相应子目录。
- `figures/q4/`：问题四三幅正式图件、图注、源数据和 QA/完整性清单。
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
