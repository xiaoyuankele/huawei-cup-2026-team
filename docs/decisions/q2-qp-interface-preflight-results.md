# Q2 `Q/p` 接口预检

运行：`q2-qp-interface-preflight-20260925-r01`
状态：`Q2_QP_INTERFACE_PREFLIGHT_EXPLORATORY`

本预检使用问题一第一小问 LaTeX 版 CRITIC--TOPSIS 质量分数，以及用户审核通过的 17 域主映射。它只检查问题二输入接口，不进行标度律拟合，也不把 A、B 按行号连接。

## 检查结果

- 1214 行 A4--A15 配比记录；
- 17 个 `p` 列，行和最大误差 `1.55e-15`；
- `Q` 全部有限且位于 `[0,100]`；
- `Q_low <= Q <= Q_high` 全部成立；
- `(dataset,index)` 重复键为 0；
- 1088 行为已观测 Loss，126 行为 A12--A15 外推/估计角色。

完整指标见 [metrics.json](../../experiments/runs/q2-qp-interface-preflight-20260925-r01/metrics.json)，数据集汇总见 [dataset_summary.csv](../../experiments/runs/q2-qp-interface-preflight-20260925-r01/dataset_summary.csv)。

## 边界

这一步只证明 `Q/p` 表结构可进入后续探索性分析。11 个 inferred 域仍是用户确认的语义先验，A12--A15 仍是外推角色，B8 的质量方向问题仍需单独处理；正式问题二拟合尚未开始。
