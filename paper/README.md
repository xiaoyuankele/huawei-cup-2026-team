# LaTeX 论文

论文源文件以 `main.tex` 为唯一入口，采用 `template/` 中的用户提供 GMCM2026 类文件，并叠加 `template/official-format-2026.sty`，按 2026 年 9 月 16 日的论文格式规范排版。当前入口装配问题一的三部分正文：数据质量评价与基础评分、质量冲突消解与综合评价模型、训练配比效应与规模修正。

正文公式每条独占一个居中编号环境，前置简短公式名；图题独立、简短且居中。图形细节与适用边界在正文解释。

## 目录约定

- `main.tex`：唯一编译入口，负责论文题目、摘要和章节装配；不写身份信息。
- `template/official-format-2026.sty`：在保留上游类文件的前提下，落实摘要首页、页码、字体、行距和无页眉要求。
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

摘要页即论文第 1 页，题目、中文摘要及关键词置于该页，正文从下一页开始。论文 PDF 不应出现学校、队员、队号或其他身份标识。提交前核对题目与所选赛题、摘要内容、参考文献引用顺序及上传附件。论文中的数字应能追溯到 `experiments/runs/` 中的 `run_id`。
