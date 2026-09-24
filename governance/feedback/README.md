# 失败、阻塞与不确定性反馈

失败的 AI 输出、不可复现实验、数据矛盾、证据不足和暂时无法解决的问题都是科研过程的一部分。它们使用 `feedback_id` 单独记录，不通过删除聊天或覆盖旧结论来处理。

## 口头发布与题目分解

任务可以在会议、语音或面对面交流中口头发布。口头发布只是启动方式，不能替代仓库记录。执行前，协调人或任务 Owner 必须在 `docs/tasks/` 创建任务卡，并填写 `problem_id`、`subproblem_id`、Owner、Reviewer、交付物、验收条件和 `announcement_ref`。接收任务的队友确认后，其他设备只依据任务卡执行。

任务按题目树划分：

```text
problem_id: Q1
└── subproblem_id: Q1-S03
    └── task_id: T-Q1-S03-001
```

工作包、分支和 AI 工具属于执行细节，不能代替题目或子问题编号。新任务建议使用 `T-Q1-S03-001`；已有 `T-Q1-003` 等编号继续有效。

## 回馈提交规则

每次回馈的第一行必须写 `task_id`。如果内容涉及失败、风险、阻塞、返工、证据不足或无法判断，必须同时创建 `feedback_id`，并填写 `problem_id`、`subproblem_id`、提交人、证据、响应负责人和下一步。没有 `task_id` 的口头回馈只能作为通知，不能作为验收依据。

最小回馈格式：

```text
task_id: T-Q1-S03-001
feedback_id: FB-20260924-Q1-S03-001 | NONE
status: CAPTURED | RESPONDED | CLOSED | BLOCKED
summary: <脱敏的一句话反馈>
evidence_ref: <run_id、PR、日志或文件>
next_action: <下一步动作>
```

## 公开边界

本仓库是公开仓库。公开案例只能包含脱敏摘要、错误类型、状态、必要的输入引用和哈希。完整 AI 对话、未公开题目、原始数据片段、账号信息和内部上下文放在本地加密目录，例如 `local/ai-transcripts/`；`local/` 已加入 `.gitignore`，只保留说明文件。

高敏感案例只在公开索引中保留 `private_ref` 或 `transcript_sha256`，不在 GitHub Issue 或 PR 评论中展开。

## 类型与状态

反馈类型使用固定值：

- `no_solution`：没有生成满足输出契约的方案；
- `execution_failure`：代码、命令、环境或资源失败；
- `quality_failure`：输出违反格式、接口或验收要求；
- `evidence_gap`：资料不足，不能支持结论；
- `contradiction`：同一上下文出现互相冲突的结果；
- `security_privacy`：发现泄露、提示注入或越权风险；
- `human_disagreement`：队员无法认可输出或解释。

状态流程为：

```text
captured → triaged → reproducing
                    ├→ resolved
                    ├→ needs_input
                    ├→ accepted_uncertainty
                    └→ escalated
                         ↓
                       closed
```

`duplicate` 和 `superseded` 是旁支终态。每次状态变化都应写入案例的 `events`，包括时间、操作者、原因和证据引用。

## “无解”的判定

`UNKNOWN` 或 `accepted_uncertainty` 表示证据不足，不能写成“问题无解”。只有在理论约束下确实不可行，或至少两种独立方案在固定协议下均失败，并由 A 审核后，才可以使用 `not_feasible`。

`wont_fix` 表示项目决定停止投入，原因可能是范围、时间或成本；它不等于数学上的不可行。

## 严重等级与处理

| 等级 | 例子 | 处理 |
|---|---|---|
| P0 | 泄露、关键结论错误、污染最终 PDF | 立即暂停相关实验和合并，由 A 处理 |
| P1 | 数据契约、指标、核心代码或实验设计错误 | 阻塞 PR，修复并重跑 |
| P2 | 局部质量或解释问题 | 下一迭代修复 |
| P3 | 格式、措辞和非关键改进 | 可批量处理 |

P0/P1 的公开记录可以只保留脱敏 stub，详细材料放私有记录。`accepted_uncertainty` 关闭时，必须写清楚“目前不能声称什么”和需要什么证据。

## 与现有对象的关系

- `task_id` 表示要完成的工作；
- `prompt_run_id` 表示一次 AI 调用；
- `run_id` 表示真实代码或数据实验；
- `feedback_id` 表示对输出、实验或证据的反馈案例。

一个任务可以有多个提示词调用和实验，一个反馈案例可以关联多个重试 `run_id`。反馈记录不能替代实验的配置、数据 manifest、Git commit、环境和指标。

## 关闭条件

关闭案例时必须记录：处理决定、修复的 prompt 或代码版本、复现命令、证据引用、Reviewer 和后续动作。已关闭的 `no_solution`、`quality_failure` 和 `contradiction` 应加入提示词回归测试集；`evidence_gap` 和 `accepted_uncertainty` 必须阻止未经证据的论文表述。
