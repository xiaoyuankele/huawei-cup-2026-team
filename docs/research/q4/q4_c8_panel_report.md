# 问题四：详细 C8 面板模型（统一版）

当前主结果使用 `q4-system-20260926-r01` 的 70/30 月份协议：2024-06 至 2024-12 训练，2025-01 至 2025-03 测试。主目标为详细 C8 六任务等权 q95，官方 `Average` 只作敏感性分析。

70/30 截面 QuantReg 的 q95 结果为：四类模型训练 1167、测试 684，pinball loss=0.559、普通测试 R²=-0.425；pretrained-only 训练 96、测试 41，pinball loss=0.407、普通测试 R²=-1.139。R² 仅作辅助，模型选择依据 pinball loss、覆盖率和时间外稳定性。

完整模型仍采用参数规模、月份和类型三个低复杂度变量。merge 保留在榜单前沿分析中，但由于其可能复用已有权重，不把它单独解释为可观测训练算力轨迹。

早期 `q4-frontier-20260926-r01` 的年度切分结果（1184/691、q95 pinball loss=0.559、覆盖率=96.4%）保留为年度兼容性检查。它与当前 70/30 结果的样本定义不同，不能在同一表中作为重复验证点计数。

脚本和聚合表：`scripts/q4/q4_protocol_experiment.py`、`experiments/runs/q4-system-20260926-r01/metrics/q4_protocol_70_30_model_comparison.csv`。
