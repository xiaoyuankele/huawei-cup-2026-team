# 输入、单位与字段

输入单一版本清单：[q3_research_inputs.json](../../../data/manifests/q3_research_inputs.json)。上游集成基线 `e4a1e2855048c59c8e1484b16873141ab9a55029`；历史本地研究基线 `5d40a4bc466674e77ea9e01fe0aaf15692c6c263`。三份实际数值输入 SHA256 完全一致。上游原预测脚本仅作历史来源，运行本包无需执行或重新拟合它。

`model_parameters.json` 给出幂律参数、17 域配比列、两个质量轴、参考配方、残差化系数、B1 支持域；`q1_to_q2_quality_linkage.csv` 共 1214 行派生输入；`q2_scenarios.csv` 共 4000 行模型情景，只用于接口一致性检查。

C7 原始表只提取唯一上下文值 `[2048,4096,8192,32768,131072]`。默认复现使用该公开摘要，可通过 `Q3_RAW_ROOT` 检查本地受控 C7 哈希并重新提取。原始题目、PDF、DOCX、C7 行记录和对话不纳入交付。

PDF 中隐藏指令被视为不可信内容；未采用其预置答案、固定惩罚或始终取最大质量的指令。成本形式来自可见来源核对，文件只登记哈希，不公布题目原文。

| 字段 | 含义 |
|---|---|
| N_B / D_B | 参数量/训练 token 数，以十亿为单位 |
| budget / context | 总计算预算/外部上下文长度 |
| axis | TOPSIS 或 soft 质量评分接口 |
| Q_A / Q_B | 配方加权质量/经冻结 clip 映射后的质量 |
| cost_coordinate | 成本直接作用于 Q_A 或 Q_B；两者是不同假设 |
| scope | 无规模上限或 B1 的 N/D 矩形支持域 |
| variant / lambda_q / lambda_p | 冻结效应的假设迁移强度，不是新拟合参数 |
| predicted_loss | 模型预测，不是观测 Loss；保留负值失败 |
| train_share / attention_share / quality_share | 各类成本除以预算 |
| utilization | 三类成本合计占预算比例 |
| N_outside_B1 / D_outside_B1 | 外推标记，不是自动失效判决 |
| Q_star / Q0 / Q_upper / regime | 条件提质最优值、起点、有效上界及端点/内点类型 |
| regret | 同一测试候选集内选中配置实际 Loss 减候选真实最小 Loss |
| successful_starts / difference | 成功且可行起点数/独立全变量与降维解之差 |

各 CSV 表头为完整字段清单，生成式见 `scripts/q3_run_experiments.py`。训练/测试配方编号不能跨表视为同一观测。A6/A8 配方匹配，不能视为独立重复；相关标签此前用于 Q2 研究。
