# 问题二 P1/P3 接口审计结果

运行号：`q2-bridge-interface-20250925-r01`

本次审计只读使用 A16 域映射、A4/A6/A8/A10/A12/A14 混合配方和问题一历史候选域分数。候选分数来自 `q1-critic-topsis-20260924-r01`，其状态仍为 `LOCAL_RESULT_PENDING_TEAM_REVIEW`，因此本结果是条件接口证据，不是正式质量分数，也没有建立 A 到 B 的逐行连接。

## 映射覆盖

| 映射层 | 域数 | 有候选 q 的域数 | 处理 |
|---|---:|---:|---|
| direct | 3 | 3 | 可作为条件敏感性输入 |
| near_direct | 3 | 3 | 保留近似语义，不得当作同域真值 |
| inferred | 11 | 0 | 暂停，不插补 |
| 合计 | 17 | 6 | 候选覆盖率 35.3% |

## 配方级诊断

对每个配方计算了 `mapped_mass`、`unmapped_mass`、`Q_partial_raw` 和仅用于比较的 `Q_partial_renorm`。`Q_partial_raw` 不会把未映射域设为 0 的质量解释成“低质量”；`Q_partial_renorm` 也不用于正式建模，因为它改变了配方权重。

- A4/A5 训练配方平均 `mapped_mass=0.5646`，平均未映射质量权重约 `0.4353`；
- A6/A7 验证配方平均 `mapped_mass=0.5690`，平均未映射质量权重约 `0.4310`；
- A10/A11 的平均映射质量权重为 `0.6224`；
- A12/A13、A14/A15 外推配方平均映射质量权重为 `0.5435`；
- A4/A5 中有配方行的 mapped mass 为 0，说明不能依靠少数域分数给每个配方构造完整 Q；
- `test_mixture_1m.csv` 与 `test_mixture_60m.csv` 的哈希相同，不能把两者视为独立混合设计证据。

完整表格位于运行目录的 `tables/domain_mapping_with_candidate_q.csv` 和 `tables/recipe_partial_q_summary.csv`。

Q1 侧另有角色变更审计 `q1-quality-migration-20260925-r01`，其四种候选质量模型均保留 mapped mass 和未映射域，不改变本接口的 6/17 覆盖结论，也不构成正式 Q。

## 决策

1. P1/P3 接口审计完成，但接口状态为 `BLOCKED_CONDITIONAL_INTERFACE`；
2. M2 只能在补齐 11 个 inferred 域或明确的敏感性边界后做情景分析；
3. 当前不能把 `Q_partial_raw`、`Q_partial_renorm` 或 Q1 候选域分数写入 B 的正式拟合；
4. 继续执行 M0/M1 的 B 侧验证和 B8 来源补证，不解除 A→B 联合迁移阻断。

运行配置、输入哈希、指标和说明见 [q2-bridge-interface-20250925-r01](../../experiments/runs/q2-bridge-interface-20250925-r01/)。
