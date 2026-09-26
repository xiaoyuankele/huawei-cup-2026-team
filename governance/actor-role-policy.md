# 角色与执行人解耦协议 v2

角色描述工作阶段或复核视角，Actor 描述真实执行人。当前任务卡不再使用固定的 A/B/C Owner 或“全部由 A 最终签字”模式。每个任务必须记录实际的 `owner_actor`、`peer_reviewer_actor` 和 `release_integrator_actor`。

## 当前三人工作包

| Actor | 纵向工作包 | 代码—实验—论文闭环 | 交叉职责 |
|---|---|---|---|
| ACTOR-1 | WP-A 数据与证据 | 审计/预处理代码；数据边界与归一化实验；数据方法段 | 复核 WP-C，集成 WP-B，参与发布签署 |
| ACTOR-2 | WP-B 模型与优化 | 评分接口/基线/PP-GA 代码；分层模型实验；模型协议段 | 复核 WP-A，集成 WP-C，参与发布签署 |
| ACTOR-3 | WP-C 验证与结果 | 冲突/验证/图表代码；稳健性与域分层实验；结果限制段 | 复核 WP-B，集成 WP-A，参与发布签署 |

真实姓名或 GitHub 用户名只写入受控分配记录；公开仓库使用稳定 Actor ID。

## 约束

1. `owner_actor`、`peer_reviewer_actor`、`release_integrator_actor` 必须互不相同。
2. Peer Reviewer 必须独立检查，不得直接修改 Owner 的结果；发现问题必须建立 `feedback_id`。
3. Integrator 检查接口、manifest、run_id、claim ledger 和限制是否齐全，不代替 Peer Review。
4. 缺少 Peer Review 时只能是 `REVIEW_BLOCKED`；缺少 Integrator 检查时不能是 `PACKAGE_ACCEPTED`。
5. 三人各自的工作包必须同时交付代码、实验和论文段；缺少任何一类只能是 `PARTIAL`。
6. Q1-INT/T-Q1-009 的发布决定需要三人 Release Council 共同签署；ACTOR-1 的协调身份不能替代其他两人的签署。
7. 任务状态必须由 Task Card、PR、Run Manifest 和 Claim Ledger 共同支撑，不能只凭聊天记录更新。

## 环形分配

| 工作包 | Owner Actor | Peer Reviewer | Release Integrator | 允许正式实验的门 |
|---|---|---|---|---|
| WP-A | ACTOR-1 | ACTOR-2 | ACTOR-3 | G0 |
| WP-B | ACTOR-2 | ACTOR-3 | ACTOR-1 | G1 |
| WP-C | ACTOR-3 | ACTOR-1 | ACTOR-2 | G2 |
| Q1-INT | ACTOR-1（协调） | 三人共同 | 三人共同 | G3 |

## 状态机

```text
DRAFT → SPEC_READY → CODE_READY → RUNNING → RUN_COMPLETE
      → PEER_REVIEW → PACKAGE_ACCEPTED → INTEGRATED
                         └→ REWORK / REVIEW_BLOCKED
```

角色视角可以写入可选字段 `review_domain`，但不能覆盖 Actor 独立性判断。分支使用 `wp/<actor>/<work-package>`，跨包整合使用 `integration/<actor>/Q1-INT`。
