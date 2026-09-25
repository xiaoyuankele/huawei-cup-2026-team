# Q1-S02 冲突诊断与有限补偿配图

任务 `T-Q1-007`、`T-Q1-008`；工作包 `WP-C`；来源运行 `q1-conflict-trial-20260924-r01`。**状态：REVIEW_BLOCKED，供论文写作和人工审核使用。** 本目录的提交不提升运行证据等级，也不代表候选分数已被采纳。正式纳入 `paper/main.tex` 前，须完成既有 G2、Peer Review 和集成检查。

独立 LaTeX 审阅稿位于 [`paper/sections/drafts/q1-conflict-resolution-standalone.tex`](../../sections/drafts/q1-conflict-resolution-standalone.tex)。`paper/main.tex` 仍是正式论文的唯一入口。

| 图 | 内容 | 预览 | 插图 PDF | 可编辑 SVG |
| --- | --- | --- | --- | --- |
| 3-1 | 三分区高低分信号有向配对 | [PNG](fig3_1_conflict_pair_heatmap.png) | [PDF](fig3_1_conflict_pair_heatmap.pdf) | [SVG](fig3_1_conflict_pair_heatmap.svg) |
| 3-2 | A1 七域候选冲突率 | [PNG](fig3_2_domain_conflict.png) | [PDF](fig3_2_domain_conflict.pdf) | [SVG](fig3_2_domain_conflict.svg) |
| 3-3 | 阈值敏感性 | [PNG](fig3_3_threshold_sensitivity.png) | [PDF](fig3_3_threshold_sensitivity.pdf) | [SVG](fig3_3_threshold_sensitivity.svg) |
| 3-4 | 有限补偿参数敏感性 | [PNG](fig3_4_compensation_sensitivity.png) | [PDF](fig3_4_compensation_sensitivity.pdf) | [SVG](fig3_4_compensation_sensitivity.svg) |

图组沿用仓库已有 CRITIC–TOPSIS 图的 183 mm 宽、白底、深灰文字、青灰主色和陶土橙强调色。新图展示第二小问数据，不能将配对比例相加，也不能把冲突率或均分变化解释为准确率。PNG 为 600 dpi；PDF 与 SVG 保留可编辑文本。更详细的纳入范围和检查结果见 [figure_qa.md](figure_qa.md)。

从仓库根目录复现：

```sh
python paper/figures/q1-conflict-resolution/plot_q1_2_repo_style.py
```

从 `paper/` 编译独立审阅稿：

```sh
xelatex sections/drafts/q1-conflict-resolution-standalone.tex
```

复现依赖运行目录中已有的汇总 CSV，绘图不读取原始文本或逐条私有记录。当前提交没有修改主论文、正式 claim ledger 或既有候选实验结果。
