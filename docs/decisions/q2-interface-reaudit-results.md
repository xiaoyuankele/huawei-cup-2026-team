# Q2 A–B 接口再审计结果

运行号：`q2-interface-reaudit-20260925-r01`。

本运行使用当前的 Q1 TOPSIS–CRITIC 评分、A16 映射文件、A4–A15 配比表和 B6–B8 附件做只读审计，不重新拟合模型、不修改原始数据，也不把 Q1 分数转换为 B6 的 `Q_score`。

## 审计结果

| 检查项 | 结果 |
|---|---|
| 当前 Q1 评分状态 | `LOCAL_RESULT_PENDING_TEAM_REVIEW` |
| A16 可用映射 | 6/17，覆盖率 0.3529 |
| A 与 B6 字段交集 | 空集 |
| A–B 逐行连接键 | 不存在 |
| B6—B7 嵌套关系 | B6 的 360 行全部在 B7 中，B7 共 450 行 |
| B7 来源/生成说明 | 缺失 |
| B8 来源/生成说明 | 缺失 |
| B8 Q—Loss 方向 | 与 B6/B7 不一致 |

B6 的 45 个 `(N,D)` 单元中有 43 个呈现混合方向；B7 的 90 个单元中有 43 个混合方向。B8 则有 150 个单元，其中 Q 增大时 Loss 增大的步数为 1311，下降仅 2 步，且来源和生成过程没有完整记录。因此 B8 不能直接并入当前 M1 或联合优化。

## 结论

当前仍不能拟合或发布正式的 A–B 联合模型。可以继续保留：

- B1 的 N–D 基线；
- B6/B7 的条件性质量敏感性；
- A 侧配比候选的离散情景；
- A16 不完整映射下的区间敏感性。

不能把这些结果合并成一个已验证的 `L(N,D,Q,p)`，也不能把 B6 的半合成 `Q_score` 当作 Q1 的真实质量分。

完整门检查见 [gate_checks.csv](../../experiments/runs/q2-interface-reaudit-20260925-r01/tables/gate_checks.csv)，映射审计见 [mapping_audit.csv](../../experiments/runs/q2-interface-reaudit-20260925-r01/tables/mapping_audit.csv)，B 文件审计见 [b_file_audit.csv](../../experiments/runs/q2-interface-reaudit-20260925-r01/tables/b_file_audit.csv)。
