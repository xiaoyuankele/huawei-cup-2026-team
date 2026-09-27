# 问题三 Overleaf 编译说明

## 编译入口

在 Overleaf 中把 `paper/` 目录作为项目根目录，上传 `q3-overleaf.tex` 及其依赖目录，将 `q3-overleaf.tex` 设置为 Main document，并选择 XeLaTeX。

## 依赖文件

```text
q3-overleaf.tex
commands.tex
template/gmcmthesis.cls
template/figures/*
sections/drafts/q3-conditional-results.tex
figures/q3/figures/Fig06_M0_budget_context.pdf
figures/q3/figures/Fig07_M1_quality_tradeoff.pdf
figures/q3/figures/Fig08_Q0_cost_robustness.pdf
figures/q3/figures/Fig09_parameter_uncertainty.pdf
figures/q3/figures/Fig10_discrete_pareto.pdf
figures/q3/figures/Fig11_p_candidate_panel.pdf
figures/q3/figures/Fig12_M2_interface_heatmap.pdf
figures/q3/figures/Fig13_identifiability_interface.pdf
```

如果只编译问题三正文，上传 PDF 图即可；SVG、PNG 和 TIFF 用于编辑、预览和投稿备份。数据表、绘图脚本、manifest 和 QA 文件保留在仓库中用于复现，不是 LaTeX 编译依赖。

## 写作边界

正文明确区分 M0、M1、P/M2 条件结果和暂不识别的 M3 联合模型。支持域外解、质量上界和 Q1→B6 映射均按条件情景描述，不应改写成已完成的独立验证或唯一最优训练建议。
