# 问题四数据审计（附件 C_efficiency_evolution）

> **运行口径说明：** 早期审计按旧版连接和去重规则报告 1,855 个 C8 模型；当前主运行 `q4-system-20260926-r01` 按模型—月份保留最后记录后得到 1,859 条合并记录、1,850 个模型。两者差异来自去重和日期连接规则，不代表新增原始数据。最终主表以当前运行的数据审计 JSON 为准。

本报告只读审计本地附件 C 数据；复现时放在仓库忽略的 `data/origin/C_efficiency_evolution`，或通过 `--data-dir` 指定。未修改原始数据。

## 文件和样本规模

| 文件 | 行数 | 关键字段 | 备注 |
|---|---:|---|---|
| `leaderboard_cleaned.csv` | 4,576 | Model、Submission Date、#Params (B)、6 个任务、Average | 4,497 个唯一 Model；79 个 Model 重复出现 |
| `leaderboard_enhanced.csv` | 4,576 | 上表 + Epoch_AI_* | Epoch 手工关联字段仅 447/4,576 行有值 |
| `leaderboard_extended_timeseries.csv` | 4,599 | Model、Year、Params_B、Average、6 个任务、Source | 2019--2025；早期年份仅 26 条历史记录 |
| `epoch_all_ai_models.csv` | 3,523 | 训练参数、算力、数据量、可访问性 | 3,518 个唯一 Model；与 Leaderboard Model 无精确交集 |
| `loss_benchmark_bridge.csv` | 43 | Loss 与 Benchmark | 7 条 High、36 条 Medium |
| `loss_benchmark_bridge_expanded.csv` | 75 | Loss 与 Benchmark | 7 条 High、68 条 Medium |
| `model_architecture_metadata.csv` | 45 | Pythia 架构字段 | 主要适合桥接分析 |

另有 `data/train-00000-of-00001.parquet`（4,576 行、36 列）是 C8 的丰富版本，包含 `fullname`、`Base Model`、`Model sha`、Architecture、Generation、MoE、Merged、Precision 等字段。基线实验应优先读取该 parquet；CSV 可作为目标列的交叉核对。

## 时间结构

`leaderboard_extended_timeseries.csv` 的行数按年份为：2019: 1、2020: 1、2021: 2、2022: 7、2023: 13、2024: 2,673、2025: 1,902。按 `Source` 分解，2019--2023 的 26 行全部来自 `Historical (papers/reports)`；2024 有 2,671 条 Open LLM Leaderboard 和 2 条历史记录，2025 有 1,902 条 Open LLM Leaderboard。因此真正可比较的时间横截面主要只有 2024 和 2025，不能把 2019--2023 当作等价的年度样本用于拟合长期趋势。

Open leaderboard 且参数量为正的有效样本为 4,566 行（2024: 2,664，2025: 1,902）。2024 中 2,596 个唯一 Model，2025 中 1,891 个唯一 Model。2024 有 68 个重复 Model 行，2025 有 11 行；重复记录通常代表不同提交时间、评测版本或 Type，不能不加判断地当成独立观测。

## 重复、家族和可交换性

清洗后的 CSV 没有 `family_id`，但 C8 parquet 提供 `Base Model`：4,576 行全部非空，其中 571 行取值为 `Removed`，其余 4,005 行覆盖 3,290 个基础模型族。`Qwen/Qwen2.5-0.5B` 有 114 行、`meta-llama/Meta-Llama-3.1-8B` 有 62 行，家族大小极不均衡。Model 的 namespace（`org/model`）只能作为提交者/组织代理，约有 714 个 namespace，分布同样极不均衡；例如 2024、2025 的 namespace 数分别为 547、283，且少数组织贡献大量派生模型。因此建议：

1. 使用 parquet 的 `fullname + Submission Date + Precision + Type` 检查重复；若研究年度前沿，按 `fullname + Year` 聚合，并将聚合规则（最高、均值或最新）预先固定。
2. 回归和 Bootstrap 至少按 `Base Model`（排除/单独标记 `Removed`）聚类；用留一基础家族验证防止同一底模泄漏到训练和测试。
3. `Model sha` 不能单独作为唯一键：99 个重复行分为 76 组，且相同 hash 出现在不同 fullname，组内 Average 差异最大 41.21。
4. `epoch_all_ai_models.csv` 的 `Base model` 仍不能作为全样本训练特征：该字段仅 684/3,523 行非空，且与 Leaderboard Model 没有精确连接。

## 缺失和异常

- `leaderboard_cleaned.csv`：Hub License 缺失 1,753/4,576（38.3%）；Submission Date 缺失 12；#Params 缺失 3，且有 7 行参数量为 0。
- 六个任务分数和 Average 在 Leaderboard 行中没有缺失，取值均非负且没有超过 100。
- parquet 中 `Base Model` 没有空值但有 571 个 `Removed`；Model sha 有 99 个重复行，不能按 hash 盲目去重。
- `epoch_all_ai_models.csv`：Parameters 缺失 1,226、Training compute 缺失 2,133、Training dataset size 缺失 2,123；Open model weights? 非空 2,653（Yes 1,325、No 1,328）。
- Loss bridge：`D_tokens_B` 只有 7 条非缺失，而且都为 299.893B；Medium 组的训练数据量全部缺失，不能在同一模型中把它当作已观测协变量。

处理建议：参数量小于等于 0 设为缺失并剔除出 log 变量；不要用均值填补训练算力/训练数据量；缺失机制和样本筛选要在敏感性分析中报告。

## 目标变量可构造性

对于 Open LLM Leaderboard 行，`Average` 与六个任务列的简单均值几乎一致（差异均值约 -1.7e-5，绝对差最大约 0.005），可直接把 `Average` 作为主目标 `S`。也可以重新计算 `S_eq = mean(IFEval, BBH, MATH_Lvl5, GPQA, MUSR, MMLU_PRO)` 作为核对。

历史 26 行不能采用同一规则：这些行的缺失任务被用 0 表示，`Average` 与六任务均值差异很大（差异均值约 9.04，GPT-3 175B 差异 42.33）。因此主分析应排除历史行，或保留但设置 `historical_incomplete` 标志并只做敏感性分析。

可报告的前沿目标包括每年 `S` 的 90%、95%、99% 分位数。Open leaderboard 参数量为正时：

| 年份 | n | 中位数 | P90 | P95 | P99 | 最大值 |
|---|---:|---:|---:|---:|---:|---:|
| 2024 | 2,664 | 21.12 | 35.095 | 38.544 | 45.629 | 52.08 |
| 2025 | 1,902 | 23.48 | 39.670 | 41.249 | 43.160 | 47.22 |

2024→2025 的 P95 增长约 2.705 分，而 P99 反而下降约 2.469 分，说明极端最大值对重复、模型构成和测量误差非常敏感；建议以 P90/P95 为主，P99/最大值仅作描述。

## Baseline 数据切分建议

建议预先锁定以下主分析集：

```text
Source == "Open LLM Leaderboard"
Params_B > 0
任务分数和 Average 均有效
Year ∈ {2024, 2025}
```

数据验证可以采用“2024 训练、2025 时间留出”；如果进行逐模型预测，必须按 namespace/家族分组留出，避免同一提交者或同一模型族泄漏到训练和测试。由于只有两个可比年份，不能声称完成可靠的长期时间序列外推。前沿预测应使用低自由度模型或简单分位数趋势作为基线，并报告按 namespace 聚类的 bootstrap 区间。

## Loss--Benchmark 桥接

主桥接只使用 7 条 `High (same model, same validation set)` Pythia 记录；将 36/68 条 `Medium` 记录作为扩展敏感性分析。High 样本规模太小，不能支持复杂非线性模型或多变量机器学习；应报告桥接函数的不确定性如何传递到最终前沿区间。
