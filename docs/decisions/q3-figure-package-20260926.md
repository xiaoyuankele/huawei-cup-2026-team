# 问题三单张图候选包整理记录

- 日期：2026-09-26
- 任务：`T-Q3-FIGURES`
- 分支：`feature/B/role-actor-separation`
- 状态：`PEER_REVIEW`
- 范围：Q3 子问题一 M0、子问题二 M1、子问题三 M2/P 的五张中文单坐标图

## 交付内容

图形脚本、数据来源、图形契约、输出格式和 SHA256 均由各图目录的 `figure_manifest.json` 登记。候选包索引见 [`paper/figures/q3-conditional/README.md`](../../paper/figures/q3-conditional/README.md)。

- M0 基线与预算敏感性：`q3-nd-baseline-cn-v1`、`q3-nd-budget-cn-v1`
- M1 原生质量与上下文成本：`q3-m1-qb-cn-v1`、`q3-context-cost-cn-v1`
- M2/P 接口敏感性：`q3-m2p-interface-cn-v1`

所有单图均保留可编辑 PDF/SVG，并输出 600 dpi PNG/TIFF。图中标签使用中文；直接标注用于减少图例与曲线的来回对应。

## 解释边界

- `Q_B` 只指 B6/B7 原生质量变量，不等同于 Q1 的 `Q_A`。
- `L_ctx=30000` 来自成本结构比值 `C_attn/C_train=L_ctx/30000`，是代数临界点，不是模型效果临界点。
- M2/P 图只展示假设映射下的条件资源配置差异；它不识别 `G_bridge`，不构成 A-B 联合 Loss 验证，也不新增观测样本。
- 五张图均未把支持域外点解释为现实中的全局最优。

## 复核记录

已执行：

1. 五个 Python 绘图脚本重新运行并成功导出五种文件格式；
2. 三个新增脚本通过 `python -m py_compile`；
3. 输出清单、文件有限性和源表哈希写入 manifest；
4. 论文主入口保持可编译，正文引用暂不自动替换；
5. 任务卡、实验索引和 claim ledger 已建立回链。

待完成：Peer Reviewer 与 Integrator 对图形语义、数值来源和是否进入正文进行独立审核。审核通过后再在对应 `paper/sections/` 中加入 `figure` 环境并更新发布材料。
