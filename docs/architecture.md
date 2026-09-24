# 三人协作架构 v2

状态：ACTIVE（Q1 任务分发与后续研发统一采用本架构）。

本项目不再把 A/B/C 当作三个人的固定身份。A/B/C 只能作为题目中的专业视角；实际协作使用三种可轮换身份：

- **Owner**：对一个工作包的代码、实验和论文段负责，拥有修改权和结果解释责任。
- **Peer Reviewer**：独立检查 Owner 的代码、运行证据和主张，不代替 Owner 修改结果。
- **Release Integrator**：检查工作包是否满足接口、证据和论文回链要求，负责把已通过内容接入集成分支。

Owner、Peer Reviewer 和 Release Integrator 必须是三个不同的 Actor。项目发布由三人 Release Council 共同签署，任何一个人都不能单独给全项目盖章。ACTOR-1 可以担任协调人，但协调权不等于全部任务的最终技术签署权。

## 三条纵向交付链

| 工作包 | Owner | 代码 | 实验 | 论文 | Peer Reviewer | Release Integrator |
|---|---|---|---|---|---|---|
| WP-A 数据与证据 | ACTOR-1 | 原始数据审计、预处理、manifest、指标目录 | 数据角色、A1 fit/holdout、重叠、缺失、漂移和泄漏审计 | 数据方法、预处理和证据限制段 | ACTOR-2 | ACTOR-3 |
| WP-B 模型与优化 | ACTOR-2 | 统一评分接口、基线、线性投影、PP-GA 和对照方法 | 分层模型比较、敏感性和失败运行记录 | 模型定义、目标函数和实验协议段 | ACTOR-3 | ACTOR-1 |
| WP-C 验证与结果 | ACTOR-3 | 冲突诊断、验证、稳健性、图表和结果表脚本 | rank reversal、bootstrap、重复 seed、域分层和稳健性 | 结果、冲突解释、图表和限制段 | ACTOR-1 | ACTOR-2 |

每个工作包都必须形成 `code → run_id → paper_section` 闭环。T-Q1-008 不再由 WP-C 独占最终论文整合；它只负责结果段，跨包论文整合和发布检查由新增的 Q1-INT/T-Q1-009 完成。

## 任务拓扑与并行边界

```text
G0 题目/数据边界冻结
 ├─ WP-A 数据代码与预处理实验
 ├─ WP-B 模型规格、接口和基线脚手架（可与 WP-C 准备并行）
 └─ WP-C 冲突/验证/图表脚手架和论文骨架（只能准备，不写正式结果）

G1 数据契约与模型接口冻结
 └─ WP-B 正式模型实验

G2 已接受模型 run_id
 └─ WP-C 正式冲突、验证和稳健性实验

G3 三个工作包 PACKAGE_ACCEPTED
 └─ Q1-INT/T-Q1-009：claim-ledger、论文整合、全量复现和发布检查

G4 三人 Release Council 签署
 └─ 集成分支、最终 PDF 和提交附件
```

因此，WP-C 可以提前写诊断脚本、图表模板、表结构和论文骨架；只有正式数字和技术主张受 G2 门控。WP-B 先完成规格和 smoke test，正式结果受 G1 门控。

## 题目优先的任务划分与口头发布

任务不按电脑、编程语言或个人习惯拆分，而按题目树拆分。统一使用：

```text
problem_id → subproblem_id → task_id → work_package → run_id / PR → feedback_id
Q1         → Q1-S03       → T-Q1-S03-001
```

负责人可以通过会议、语音或面对面交流口头发布任务。口头发布后，执行前必须在 `docs/tasks/` 创建任务卡，并写入 `announcement.mode`、发布人、时间、脱敏摘要和 `announcement_ref`。队友确认任务卡后才开始执行；没有任务卡 ID 的内容只属于通知，不属于可验收交付物。

回馈时必须携带对应的 `task_id`。如果是失败、阻塞、风险、返工、证据不足或无法判断，还必须创建 `feedback_id`，回链题目/子问题、证据、响应负责人和下一步。反馈未关闭时，任务只能停留在 `REWORK` 或 `REVIEW_BLOCKED`，不能进入 `PACKAGE_ACCEPTED`。

## 五个事实源

1. **Task Card**：题目/子问题、口头发布留痕、范围、Owner、依赖、门控和验收条件。
2. **Pull Request**：代码和文档变更、Peer Review 和 Integrator 决定。
3. **Run Manifest**：配置、seed、输入 manifest、环境、指标、失败原因和输出哈希。
4. **Feedback Case**：反馈、失败、阻塞、不确定性、证据和处理决定。
5. **Claim Ledger**：论文主张、图表、数字、run_id、证据等级和限制。

五个事实源都能互相回链，工作包才能从 `RUN_COMPLETE` 进入 `PACKAGE_ACCEPTED`；聊天消息只负责通知。

## 状态机

```text
DRAFT → SPEC_READY → CODE_READY → RUNNING → RUN_COMPLETE
      → PEER_REVIEW → PACKAGE_ACCEPTED → INTEGRATED
                         └→ REWORK / REVIEW_BLOCKED
```

缺少代码、实验、论文段、handoff 或独立复核时只能保持 `PARTIAL`、`REWORK` 或 `REVIEW_BLOCKED`。正式论文只能引用 `PACKAGE_ACCEPTED` 的 run_id。

## GitHub 与对话组织

- 每个工作包使用一个 GitHub Issue 和一个主 PR；T-Q1-001…008 作为 Issue/PR 内的 checklist，不再为每个微任务强制创建 Issue。
- 未来分支使用 `wp/ACTOR-1/WP-A`、`wp/ACTOR-2/WP-B`、`wp/ACTOR-3/WP-C`；跨包整合使用 `integration/ACTOR-1/Q1-INT`。
- 每个执行对话只处理一个工作包；独立 Reviewer 只能通过 PR 和 handoff 提意见，不能直接改 Owner 的结果。
- 一个协调对话只维护任务图、门控、决策日志和 Release Council，不代替三个执行对话跑实验。

公开仓库只保存脱敏任务卡、代码、配置、manifest、运行元数据、图表源文件和论文源文件；原始数据、未公开题目、密钥和敏感对话保留在受控本地目录。
