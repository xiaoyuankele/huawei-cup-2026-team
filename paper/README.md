# LaTeX 论文

论文源文件以 `main.tex` 为唯一入口，采用从 [Nopon-Knowledge/huawei-cup-modeling-latex](https://github.com/Nopon-Knowledge/huawei-cup-modeling-latex) 导入的 2026 GMCMthesis 模板。模板供应目录是 `template/`，项目自己的章节、命令和参考文献仍独立维护。

## 目录约定

- `main.tex`：唯一编译入口，负责模板参数、队伍信息和章节装配。
- `sections/`：论文正文章节；每个章节只保存正文内容，不重复定义文档环境。
- `commands.tex`：统一数学符号和项目命令。
- `refs.bib`：项目参考文献库；模板示例参考文献保留在 `template/reference.bib`。
- `template/`：上游模板、固定版式素材、官方格式核对资料和维护脚本。
- `official-template-checklist.md`：提交前的格式、匿名和材料核对表。

文献检索、阅读笔记和版权边界见 [docs/literature/README.md](../docs/literature/README.md)。

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

## Q1 质量评价图组

[六张 Nature 风格图、中文图注及 LaTeX 引图片段](figures/q1-critic-topsis/nature-v1/README.md)。图表来源、复现脚本和审核状态均已回链；当前为写作候选素材，正式纳入正文按团队验收流程处理。
