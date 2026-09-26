# Q3 云端仓库上传清单

目标仓库：`https://github.com/xiaoyuankele/huawei-cup-2026-team.git`

目标分支：当前工作树分支 `q4-merge-fix-20260926`（如团队规定使用其他集成分支，只替换分支名，不改变下面的目录）。

## 应上传到仓库的路径

```text
paper/figures/q3/README.md
paper/figures/q3/Q3-MISSING-FIGURE-QA.md
paper/figures/q3/Q3-CLOUD-UPLOAD-MANIFEST.md
paper/figures/q3/Q3_figures_bundle.zip
paper/figures/q3/figure_manifest_missing.json
paper/figures/q3/plot_q3_missing_figures.py
paper/figures/q3/figures/Fig06_M0_budget_context.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig07_M1_quality_tradeoff.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig08_Q0_cost_robustness.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig09_parameter_uncertainty.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig10_discrete_pareto.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig11_p_candidate_panel.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig12_M2_interface_heatmap.{pdf,svg,png,tiff}
paper/figures/q3/figures/Fig13_identifiability_interface.{pdf,svg,png,tiff}

# 问题三论文写作入口与 Overleaf 包
paper/sections/drafts/q3-conditional-results.tex
paper/q3-overleaf.tex
paper/Q3-OVERLEAF-README.md
paper/Q3-Overleaf-Bundle.zip
paper/Q3-WRITING-STATUS.md
```

## 建议提交命令

在能够访问 GitHub 的环境中，从 `q4_merge_worktree` 根目录执行：

```powershell
git add paper/figures/q3/README.md `
  paper/figures/q3/Q3-MISSING-FIGURE-QA.md `
  paper/figures/q3/Q3-CLOUD-UPLOAD-MANIFEST.md `
  paper/figures/q3/Q3_figures_bundle.zip `
  paper/figures/q3/figure_manifest_missing.json `
  paper/figures/q3/plot_q3_missing_figures.py `
  paper/figures/q3/figures/Fig06_M0_budget_context.* `
  paper/figures/q3/figures/Fig07_M1_quality_tradeoff.* `
  paper/figures/q3/figures/Fig08_Q0_cost_robustness.* `
  paper/figures/q3/figures/Fig09_parameter_uncertainty.* `
  paper/figures/q3/figures/Fig10_discrete_pareto.* `
  paper/figures/q3/figures/Fig11_p_candidate_panel.* `
  paper/figures/q3/figures/Fig12_M2_interface_heatmap.* `
  paper/figures/q3/figures/Fig13_identifiability_interface.*
git commit -m "feat(q3): add manuscript-ready conditional analysis figures"
git push team-upstream HEAD:q4-merge-fix-20260926
```

论文稿与独立编译包可用下面的命令一并提交：

```powershell
git add paper/sections/drafts/q3-conditional-results.tex `
  paper/q3-overleaf.tex `
  paper/Q3-OVERLEAF-README.md `
  paper/Q3-Overleaf-Bundle.zip `
  paper/Q3-WRITING-STATUS.md
git commit -m "docs(q3): add conditional resource configuration manuscript"
git push team-upstream HEAD:q4-merge-fix-20260926
```

本次图件包不修改 `paper/main.tex`，也不把 M3 联合模型写成已识别结果；正文接入应在科学审阅后另行提交。
