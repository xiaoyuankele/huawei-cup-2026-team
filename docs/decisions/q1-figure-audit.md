# WP-C 图表审查

状态：探索性图表，未获独立审核。脚本scripts/plot_q1_conflict.py；输入experiments/runs/q1-conflict-trial-20260924-r01/results；向量后端ReportLab。

| 图 | 源表 | 分层与解释 |
|---|---|---|
| 图1 领域冲突率 | conflict_summary.csv | A1全量七域，标样本数；不附虚构区间 |
| 图2 阈值敏感性 | threshold_sensitivity.csv | A1留出、A2新增、A3新增；A1 fit冻结阈值 |
| 图3 lambda敏感性 | lambda_sensitivity.csv | 同上三分区；是偏好变化，不是准确率变化 |

轴标签、图例、图内说明和领域说明均用中文，英文领域标识仅为数据对应保留。输出PDF与可编辑文字SVG，PDF经pdfjs渲染为300dpi PNG并逐图查看，无截断、重叠和乱码。PDF嵌入中文字体子集，字体文件本身不随包分发。未使用截图替代图源；未删除不利阈值或排序结果。正式论文整合由T-Q1-009接手；本包不编译最终论文PDF。
