# 问题一规模条件候选设计表

运行号：`q1-scale-model-design-20260924-r01`。

该表从 `q1-scale-feature-table-20260924-r01` 生成候选规模条件输入矩阵，使用 Helmert-ilr（乘法零替换 \(\epsilon=10^{-4}\)）并加入：

- 16 个 ilr 配比坐标；
- 1 个 `log10_scale` 主效应；
- 16 个 `ilr × log10_scale` 交互项。

合计 33 个预测变量，包含元数据后共 38 列，1214 行；含截距设计矩阵秩为 34，标准化条件数为 17.05。

该文件只是候选输入设计，不读取任何 Loss 目标，也不改变 A4/A5 拟合、A6–A11 验证和 A12–A15 外推的数据角色。由于 A4/A5 只有 1M 一个规模，规模主效应和交互项仍不能从当前拟合集单独估计。

输出：`experiments/runs/q1-scale-model-design-20260924-r01/q1_scale_model_design_epsilon_1e-4.csv`。
