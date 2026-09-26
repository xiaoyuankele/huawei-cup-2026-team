# Q1 quality score and mapping gate decision

**Run:** `q1-quality-mapping-gate-20250925-r01`
**Evidence:** [metrics](../../experiments/runs/q1-quality-mapping-gate-20250925-r01/metrics.json), [six-domain confirmation table](../../experiments/runs/q1-quality-mapping-gate-20250925-r01/six_mapping_confirmation.csv), [acceptance checklist](../../experiments/runs/q1-quality-mapping-gate-20250925-r01/q1_acceptance_checklist.json), [audit script](../../scripts/q1_quality_mapping_gate.py)

## Decision

顺序 1 和顺序 2 都可以继续推进，但推进层级不同：

1. **顺序 1（Q1 质量评分）**进入“正式验收审查包”阶段；不能标记为最终质量分已验收。
2. **顺序 2（17 域映射）**进入“6 个直接/近直接映射的确认”阶段；不能标记为 17 域映射已完成。

## Evidence

- A1/A2/A3 评分样本分别为 51,230、17,523、203,752 条；三份文件均无解析错误、重复 JSON 键或文件内重复 `id`。
- 非有限值出现在 A1 的 18 条和 A3 的 1 条记录中。它们已按现有契约作为受影响指标缺失项报告，不能被静默填补。
- A1/A2 有 1,419 个重叠 ID，A1/A3 有 10,000 个重叠 ID。A2/A3 因而只能作为同族迁移检查，不能作为独立人工真值。
- 评分交付状态为 `LOCAL_RESULT_PENDING_TEAM_REVIEW`，预处理状态为 `REVIEW`；尚无正式批准的单一总分、权重和完整方向集合。
- 映射表共 17 行：direct 3、near_direct 3、inferred 11；后 11 行仍为 `(none)`，目前只有语义猜测，没有逐域质量证据。
- 6 个已支持域在 A1 中覆盖 41,230/51,230 条记录（80.48% 的样本行），但只覆盖问题二的 6/17 个 mixture 域（35.29%）；样本覆盖率不能替代域映射覆盖率。
- 候选分数的 21 项数值与复现检查全部通过，但仍有 9 个指标方向被保留为 pending，内容语义投毒审计也尚未关闭，因此当前状态仍是 `CANDIDATE_REVIEW_ONLY`。
- 11 个 inferred 域在当前 A1 质量样本中都没有对应的源域样本；缺口表已明确要求“逐域质量样本或经过验证的迁移规则”，当前动作统一为保留未映射、不插补。

## Required next gates

- 顺序 1：完成非有限值影响清单、9 个待核方向的语义审查、权重/总分的团队评审，并将 A1 留出和 A2/A3 迁移结果作为分层证据，不把它们写成独立真值。
- 顺序 2：先锁定 6 个直接/近直接映射；对 11 个 inferred 域逐域补齐来源、可比性依据、样本覆盖和验证规则。补齐前，问题二只能使用已映射质量域或显式保留未映射质量分量。
- “注意投毒”边界：本门禁覆盖结构性异常、重叠和来源角色，尚未完成内容语义投毒/恶意样本识别；在问题二正式联合拟合前仍需保留该独立审计门。
