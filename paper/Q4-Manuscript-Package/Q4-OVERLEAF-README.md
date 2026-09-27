# 问题四 Overleaf 编译说明

## 编译入口

在 Overleaf 中将 `paper/` 目录作为项目根目录，上传 `q4-overleaf.tex` 及其依赖目录，将 `q4-overleaf.tex` 设为 Main document，并选择 XeLaTeX。也可以直接上传 `Q4-Overleaf-Bundle.zip` 解压后的内容。

## 依赖文件

```text
q4-overleaf.tex
commands.tex
template/gmcmthesis.cls
template/figures/abstract-header2026.pdf
template/figures/cover2026.pdf
template/figures/keywords2026.pdf
sections/drafts/q4-frontier-prediction.tex
figures/q4/FigQ4_01_frontier_validation.pdf
figures/q4/FigQ4_02_12m_scenarios.pdf
figures/q4/FigQ4_03_workflow.pdf
```

完整的 SVG、PNG、TIFF、CSV、图注、figure contract 和 QA 文件保留在 `paper/figures/q4/`，用于编辑、投稿备份和结果复核，不属于最小 LaTeX 编译依赖。

## 提交前检查

- 在 `q4-overleaf.tex` 中填写正式队伍编号、学校和成员姓名。
- 核对主结果运行号 `q4-system-20260926-r01` 与正文数字一致。
- 确认图 Q4-1、Q4-2、Q4-3 的图号和图注与正文引用一致。
- 按 `official-template-checklist.md` 完成 XeLaTeX 编译、页数、匿名和最终 PDF 校验。

