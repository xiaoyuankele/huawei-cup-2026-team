# 问题四误差评价（统一版）

## 当前主协议

主协议按月份 70/30 切分，C8 q95 的 h=1 只有 3 个测试点，h=3 只有 1 个测试点：

| 样本 | 方法 | h | MAE | RMSE | R² | 测试点 |
|---|---|---:|---:|---:|---:|---:|
| 全类型 | linear_last_4 | 1 | 0.852 | 0.860 | 0.700 | 3 |
| 全类型 | linear_all | 1 | 1.017 | 1.035 | 0.567 | 3 |
| 全类型 | mean_last_3 | 3 | 5.132 | 5.132 | — | 1 |
| pretrained-only | mean_last_3 | 1 | 9.924 | 11.253 | -0.929 | 3 |

h=3 的单点结果不支持 R² 或显著性结论。普通 R² 是辅助指标，不替代 q95 的 pinball loss 和覆盖率。

## 截面分位数评价

70/30 q95 QuantReg 的全类型测试 pinball loss=0.559、普通测试 R²=-0.425；pretrained-only 的 pinball loss=0.407、普通测试 R²=-1.139。分位数模型可能有正偏差，这是预测条件上分位数的目标特性，不能按普通点预测误差直接判断。

## 旧版兼容性检查

早期年度切分的完整 q95 模型 pinball loss=0.559、覆盖率=96.4%、MAE=10.374、RMSE=12.145。这些结果保留用于检查新协议的量级一致性，不与当前 70/30 结果重复计为独立验证。

## 评价顺序

1. 先看时间外 pinball loss；
2. 再看分位覆盖率；
3. 最后报告 MAE、RMSE、Bias 和 R²；
4. h=3 或更长预测在测试点不足时只作描述性结果。

聚合表：`experiments/runs/q4-system-20260926-r01/metrics/q4_protocol_rolling_horizon_metrics.csv` 和 `q4_protocol_70_30_model_comparison.csv`。
