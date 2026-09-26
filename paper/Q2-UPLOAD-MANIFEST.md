# 问题二上传位置清单

本文档记录问题二数据处理、七张新增图件和论文草稿在云端仓库中的建议路径。仓库根目录为 `q4_merge_worktree/`。

## 直接提交到仓库的文件

| 内容 | 仓库路径 | 用途 |
|---|---|---|
| 问题二完整论文段落 | `paper/sections/drafts/q2-complete.tex` | 主文稿候选版本；包含问题二方法、结果、七张新增图和已有补充图引用 |
| Overleaf 编译入口 | `paper/q2-overleaf.tex` | 在 Overleaf 中设置为主文件，编译器选择 XeLaTeX |
| Overleaf 使用说明 | `paper/Q2-OVERLEAF-README.md` | 上传、目录结构和编译说明 |
| 七张新增图的 PDF | `paper/figures/q2-scaling-law/Fig05_E1_marginal_elasticity.pdf` 至 `Fig11_stratified_transfer_diagnostics.pdf` | 论文正文优先使用的矢量图 |
| 七张新增图的 SVG/PNG/TIFF | `paper/figures/q2-scaling-law/Fig05...Fig11.{svg,png,tiff}` | 编辑、预览和投稿格式备用 |
| 图件来源清单 | `paper/figures/q2-scaling-law/q2_gap_figures_manifest.json` | 记录每幅图对应的数据源、脚本和输出文件 |
| 图件质量检查 | `paper/figures/q2-scaling-law/FIGURE-QA.md` | 记录文字重叠、字体、版式和 PDF 导出检查结果 |
| 绘图脚本 | `scripts/plot_q2_gap_figures.py` | 重新生成 Fig05–Fig11 的唯一脚本入口 |

## Overleaf 一次性上传包

如果希望直接导入 Overleaf，上传：

`paper/Q2-Overleaf-Bundle.zip`

该压缩包已经包含 `q2-overleaf.tex`、`commands.tex`、模板类文件、问题二完整段落、Fig01–Fig11 及 FigS01–FigS02 的 PDF、README 和 FIGURE-QA。上传后把 `q2-overleaf.tex` 设为 Main document，并选择 XeLaTeX。

仓库中同时保留了展开目录：

`paper/Q2-Overleaf-Bundle/`

它用于检查压缩包内容和逐文件下载；若追求仓库简洁，提交源文件目录与 ZIP 二选一即可，不需要同时提交展开目录和 ZIP。

## 当前整合边界

`paper/main.tex` 尚未切换到 `q2-complete.tex`。因此本次整理只准备了问题二的可审阅草稿和 Overleaf 编译入口，没有覆盖主文稿入口。完成科学审阅后，再决定是否把 `q2-complete.tex` 接入 `paper/main.tex`。

E4 外推实验的原始运行目录仍在本地交付目录 `q2_e2_delivery/`；本仓库已保存其生成图件及来源记录，但没有把该本地目录整体复制进 `q4_merge_worktree`。

## 建议上传顺序

1. 先上传 `paper/figures/q2-scaling-law/` 和 `scripts/plot_q2_gap_figures.py`。
2. 再上传 `paper/sections/drafts/q2-complete.tex`、`paper/q2-overleaf.tex` 和 `paper/Q2-OVERLEAF-README.md`。
3. 需要给合作者直接编译时，再上传 `paper/Q2-Overleaf-Bundle.zip`。
4. 上传后在云端仓库核对 `q2_gap_figures_manifest.json` 和 `FIGURE-QA.md` 是否一并存在。
