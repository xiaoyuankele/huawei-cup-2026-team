# 问题一任务分发图 v2

任务卡只描述范围、依赖和证据门；实际执行人由 `owner_actor`、`peer_reviewer_actor` 和 `release_integrator_actor` 决定。A/B/C 不再作为人员身份。正式状态使用 `DRAFT → SPEC_READY → CODE_READY → RUNNING → RUN_COMPLETE → PEER_REVIEW → PACKAGE_ACCEPTED → INTEGRATED`。

| 顺序 | task_id | 任务 | 工作包 | Owner | Peer Reviewer | Release Integrator | Prompt | 状态 | 前置门 |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | T-Q1-001 | 原始数据契约与实验边界 | WP-A | ACTOR-1 | ACTOR-2 | ACTOR-3 | P-EXP-001@v1.0.0 | PEER_REVIEW | G0 |
| 2 | T-Q1-002 | 指标语义、方向、归一化和泄漏审计 | WP-A | ACTOR-1 | ACTOR-2 | ACTOR-3 | P-DATA-001@v1.0.0 | PEER_REVIEW | T-Q1-001 / G0 |
| 3 | T-Q1-003 | 综合评价模型规格与评价协议 | WP-B | ACTOR-2 | ACTOR-3 | ACTOR-1 | P-MODEL-002@v1.0.0 | DRAFT | G0，可与 WP-C 脚手架并行 |
| 4 | T-Q1-004 | 基线、PP-GA 和对照模型实现 | WP-B | ACTOR-2 | ACTOR-3 | ACTOR-1 | P-EXP-002@v1.0.0 | DRAFT | G1 / T-Q1-003 PACKAGE_ACCEPTED |
| 5 | T-Q1-005 | 指标冲突、权重敏感性和解释 | WP-C | ACTOR-3 | ACTOR-1 | ACTOR-2 | P-CONFLICT-001@v1.0.0 | DRAFT | G2 / T-Q1-004 PACKAGE_ACCEPTED |
| 6 | T-Q1-006 | 内部/外部验证与稳健性分析 | WP-C | ACTOR-3 | ACTOR-1 | ACTOR-2 | P-VALID-001@v1.0.0 | DRAFT | G2 / T-Q1-004、005 |
| 7 | T-Q1-007 | Q1 图表与结果表 | WP-C | ACTOR-3 | ACTOR-1 | ACTOR-2 | P-FIG-001@v1.0.0 | DRAFT | G2 / T-Q1-005、006 |
| 8 | T-Q1-008 | WP-C 结果论文段与主张登记 | WP-C | ACTOR-3 | ACTOR-1 | ACTOR-2 | P-PAPER-001@v1.0.0 | DRAFT | T-Q1-006、007 |
| 9 | T-Q1-009 | Q1 跨包整合与发布检查 | Q1-INT | ACTOR-1（协调） | ACTOR-2/3 | ACTOR-1/2/3 | P-INT-001@v1.0.0 | DRAFT | WP-A/B/C PACKAGE_ACCEPTED |

## 并行规则

1. WP-A 在 G0 后执行数据契约和预处理；9 个 `pending_verification` 方向不能进入主评分矩阵。
2. T-Q1-003 的模型规格和 WP-C 的诊断/图表/论文脚手架可以并行准备；没有 G1/G2 时不得写正式结果。
3. T-Q1-004 通过 G1 后先跑等权/稳健基线，再跑 PP-GA 和对照方法；每个方法独立 `run_id`。
4. T-Q1-005/006/007/008 共享已接受模型 run_id，但 WP-C 可提前准备代码和空表结构。
5. T-Q1-009 只做跨包整合，不替 Owner 重写结果；三人 Release Council 全部签署后才进入 `INTEGRATED`。

## 四个事实源

- Task Card：范围、门控和验收条件。
- Pull Request：代码审阅、Peer Review 和 Integrator 决定。
- Run Manifest：配置、seed、输入、指标、失败原因和输出哈希。
- `paper/claim-ledger.csv`：每个论文主张、图表和数字的证据链。

缺少任一事实源、独立复核、Integrator 结论或论文段时，任务只能是 `PARTIAL`、`REWORK` 或 `REVIEW_BLOCKED`。
