# 问题四基线实验报告

> **结果定位：历史探索。** 本文结果来自早期运行 `q4-frontier-20260926-r01`，保留用于方法开发和兼容性检查。当前主结果请参见 `q4_c8_main_results.md` 与 `q4_results_reconciliation.md`，统一采用 70/30 月份切分和 12 个月情景。

## 实验范围

本轮实验使用 `leaderboard_cleaned.csv`，按 `Submission Date` 聚合到月份，并按模型名在同一月份去重。主目标是从 C8 逐任务详细 JSON 中提取 IFEval、BBH、MATH、GPQA、MUSR、MMLU-PRO 六个任务组的主指标，要求六项均存在后取等权均值并转换到 0--100 分；共连接到 1,855 个模型。Leaderboard 的 `Average` 作为敏感性目标。

可比的 Open LLM Leaderboard 月份为 2024-06 至 2025-03，共 10 个时间点。验证从至少 3 个月训练开始，进行 7 次滚动一步预测。

## 基线模型

1. `naive_last`：下一月前沿等于上一月前沿；
2. `mean_last_3`：下一月前沿等于最近三个月前沿均值；
3. `linear_trend`：用截至当前月份的全部前沿点拟合线性时间趋势。

## 结果

### C8 六任务组等权分数（主基线）

| 方法 | 预测次数 | MAE | RMSE | 平均偏差 |
|---|---:|---:|---:|---:|
| `linear_trend` | 7 | 0.857 | 0.959 | 0.236 |
| `naive_last` | 7 | 0.999 | 1.328 | -0.767 |
| `mean_last_3` | 7 | 1.994 | 2.108 | -1.994 |

在这 7 个滚动测试点上，线性趋势的误差最小，但样本点极少，不能据此宣称线性趋势具有稳定优势。

### Leaderboard `Average`（敏感性基线）

| 方法 | 预测次数 | MAE | RMSE | 平均偏差 |
|---|---:|---:|---:|---:|
| `mean_last_3` | 7 | 1.638 | 2.147 | -1.535 |
| `naive_last` | 7 | 1.712 | 1.890 | -0.186 |
| `linear_trend` | 7 | 3.172 | 3.921 | 3.094 |

两种目标的模型排序不同，说明目标构造和评测口径会影响结论，后续必须把任务级目标作为主分析并报告敏感性。

## 12/24 个月外推（仅作基线情景）

以 C8 等权分数为目标，2025-03 的 P95 为 54.164：

| 方法 | 12 个月 | 24 个月 |
|---|---:|---:|
| `naive_last` | 54.164 | 54.164 |
| `mean_last_3` | 52.535 | 52.535 |
| `linear_trend` | 66.661 | 78.714 |

线性趋势的远期结果明显高于持平基线，说明其外推对短窗口趋势非常敏感。现阶段不能把 66.661 或 78.714 当作正式预测，只能作为趋势上界敏感性情景。

## 统计解释

- 7 个滚动测试点不足以支持显著性检验或复杂模型选择；
- 2019--2023 历史数据与 2024--2025 Leaderboard 存在数据源断点，不能混合拟合长期趋势；
- 前沿 P95 比最大值更稳定，P99 和最大值只作描述；
- 基线实验支持后续使用低自由度、带时间留出的面板分位数模型，但不支持 ARIMA 或高阶趋势外推；
- 后续必须增加留一组织/模型家族、任务留出、年份置换和 cluster bootstrap。

生成文件：

- `scripts/q4/q4_baseline_experiment.py`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/baseline_metrics.csv`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/baseline_projections.csv`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/leaderboard_average_rolling_predictions.csv`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/c8_equal_task_rolling_predictions.csv`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/monthly_average_frontier.csv`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/monthly_c8_frontier.csv`
- `experiments/runs/q4-frontier-20260926-r01/artifacts/baseline/c8_model_scores.csv`
- `q4_data_audit.md`
