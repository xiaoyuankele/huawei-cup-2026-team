# q4-system-20260926-r01

状态：`REVIEW`。本运行按问题四冻结协议执行：详细 C8 六任务等权均值为主评价指标，按月份做 70/30 时间外切分（2024-06—2024-12 训练，2025-01—2025-03 测试），并保留 `Leaderboard Average` 作为敏感性指标。

## 已执行内容

- 运行原有 Q4 基线、稳健性、分位数、任务级前沿、安慰剂、R²、bootstrap 与算力情景脚本。
- 新增 `scripts/q4/q4_protocol_experiment.py`：全四类模型和 `pretrained-only` 敏感性、h=1/3 月滚动验证、截面 QuantReg 对比、12 个月平台型/趋势型情景。
- 算力情景使用 1.0×、1.5×、2.3×、4.0×、5.0×；类型比例以末月分布为基准，对 pretrained/chat 分别做 ±10 个百分点扰动并重新归一化。
- 当前 C8 数据只有参数量、提交时间和类型；训练数据量、训练算力、评测版本不可用，模型族仅由 namespace 前缀派生。缺失字段没有均值填补。

## 主要结果

主 C8 月度 q95 的 70/30 滚动验证中，h=1 的 `linear_last_4` 最好（MAE 0.852、RMSE 0.860、R² 0.700，3 个测试点）；h=3 只有 1 个测试点，R² 不可估。`pretrained-only` 的 h=1 MAE 为 9.924–13.503，明显不稳定，因此只作为敏感性分析。

截面 QuantReg 的 q95 测试 R² 为全四类型 -0.425、pretrained-only -1.139；该结果用于证伪过拟合式解释，不用于宣称预测有效。12 个月输出是情景投影，表中的 profile range 不是时间预测区间。

## 运行

从仓库根目录执行：

```powershell
$env:Q4_DATA_DIR='D:\F题\real_attachments\C_efficiency_evolution'
$env:Q4_RUN_DIR='experiments/runs/q4-system-20260926-r01'
$env:Q4_Q3_OPTIMA_FILE='experiments/runs/q4-system-20260926-r01/q3_baseline_ND_optima.csv'
python scripts/q4/run_all.py --data-dir $env:Q4_DATA_DIR --run-dir $env:Q4_RUN_DIR
python scripts/q4/q4_protocol_experiment.py --base $env:Q4_DATA_DIR --run-dir $env:Q4_RUN_DIR --q3-optima $env:Q4_Q3_OPTIMA_FILE
```

公开提交只包含聚合表、配置、运行日志和可复现实验代码；原始附件 C 不进入 Git。
