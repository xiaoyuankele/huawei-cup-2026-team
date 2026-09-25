# 模板正文编译预览

- GitHub 基线：`32f58f9`（2026-09-25 同步的 `origin/main`）。
- Overleaf 项目：https://www.overleaf.com/project/6ab60403133c25eb2c98b0d2
- 编译器：XeLaTeX；TeX Live 2026；入口：`main.tex`。
- 结果：24 页；问题一三部分正文，第三部分使用五张正文图和两张补充图；0 个编译错误，无缺失引用或重复标签。
- 公式均以单个居中编号环境排版，前置简短公式名；每张正文图和补充图各有简短、居中的图名，解释保留在正文。长公式已拆分，编译日志未报告超宽盒。
- 模板资源沿用云端 GMCM2026；修正第一章标题层级、图注与图形不匹配、跨章浮动、参考文献被图片打断和编号不重置。
- 表 1.1 的全量占比按已提交 `experiments/runs/q1-critic-topsis-20260924-r01/figure_sources/nature-v1/tables/figure03_04_domain_comparison_and_shares.csv` 校正：book 0.07%、c4 3.83%、commoncrawl 3.69%、stackexchange 3.83%、wikipedia 3.83%。其他模型数值未重算。
- 仍有 19 条非阻断警告；模板在 Linux 环境以楷书替代隶书。参考文献有两处行距提示，无编译中断或超宽盒提示。
- 当前仅为已提交正文的排版预览，不代表完整竞赛终稿。学校、队号、队员尚为占位内容；摘要尚缺量化结果，其他题目章节、完整论文结构与人工验证结果未补造。
- 本地提交分支：`codex/q1-s03-paper-20260925`。
