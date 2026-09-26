# Q3 版本边界与交付说明

本文件把已经出现的第三问结果按来源、模型接口和审查状态分开登记。任何引用问题三数值的表格或论文段落都必须同时写出 `run_id`，不得把不同版本合并成一个未命名的“Q3 最优解”。

| 版本标签 | 来源/分支 | 代表运行 | 内容边界 | 状态 |
|---|---|---|---|---|
| `Q3-RESEARCH-HANDOFF-v1.0.0` | 队友交接包，`codex/q3-research-handoff` | `q3-frozen-q2-exploration-20260925-r01` | 冻结 Q2 片段模型上的条件资源情景；已有独立复核接口 | `REVIEW_BLOCKED` |
| `Q3-CONDITIONAL-INTERFACE-v1.0.0` | 本交付分支，`exp/ACTOR-2/q3-conditional-interface-20260926` | `q3-nd-baseline-20260925-r01`、`q3-q-conditional-20260925-r01`、`q3-q-robustness-20260925-r01`、`q3-p-conditional-20260925-r01`、`q3-optimization-robustness-20260926-r01`、`q2-q3-interface-sensitivity-20260926-r01` | B1/B6 条件模型、参数不确定性传播、A 侧 p 情景与 Q2→Q3 假设接口敏感性；不声称正式 M3 联合拟合 | `REVIEW_BLOCKED` |
| `Q3-FINAL-SCENARIO-PACKAGE-LOCAL-20260926-r01` | 队友本地结果，待确认所属分支 | `q3-final-scenario-package-20260926-r01` | 固定预算前沿、代表情景和 claim ledger 的条件打包 | 未纳入本分支 |
| `Q3-P-FIXED-BUDGET-LOCAL-20260926-r01` | 队友本地结果，待确认所属分支 | `q3-p-fixed-budget-panel-20260926-r01` | p 候选与固定预算前沿的条件面板；不做 A-B 行连接 | 未纳入本分支 |
| `Q3-FIXED-BUDGET-LOCAL-20260926-r01` | 队友本地结果，待确认所属分支 | `q3-fixed-budget-frontier-20260926-r01` | 固定预算网格前沿 | 未纳入本分支 |

## 本分支的使用规则

1. `Q3-CONDITIONAL-INTERFACE-v1.0.0` 的 M0 使用 B1，M1 使用 B6/B7 原生 `Q_score`；A 侧 `Q_A(p)` 只作为未校准的接口情景，不进入已拟合的 B 侧损失函数。
2. `q2-q3-interface-sensitivity-20260926-r01` 的 Q1→B6 映射是明确标记的假设校准，只能用于敏感性分析；不能据此宣称质量尺度已经统一，也不能识别 `G_bridge`。
3. 未纳入本分支的队友运行保持原始 `run_id` 和版本标签。后续若要合并，须通过独立 PR，并在比较表中同时保留来源、输入、约束和审查状态。
4. 所有版本均受 B1/B6 观测支持域、预算、上下文和成本函数假设约束；任何“全局最优”“A-B 联合最优”或正式 M3 结论都超出当前证据。

## 可追溯入口

- 任务卡：`docs/tasks/T-Q3-CONDITIONAL-INTERFACE.yml`
- 本分支综合答复：`docs/decisions/q3-answer-package-20260926.md`
- Q2→Q3 敏感性：`docs/decisions/q2-q3-interface-sensitivity-results-20260926.md`
- 运行索引：`experiments/index.csv`
