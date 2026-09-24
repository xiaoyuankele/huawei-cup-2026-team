# 协作规范

## 分支

- `main` 是可复现的稳定集成分支，禁止直接推送。
- 任务分支格式：`feature/<成员>/<主题>`、`exp/<成员>/<run-id>`、`paper/<成员>/<章节>`。
- 发布分支：`release/huawei-cup-2026`。
- 禁止 force-push。合并前至少由一名非 Owner 队员复核。

## 提交信息

使用 `data:`、`model:`、`exp:`、`paper:`、`fix:`、`docs:`、`chore:` 前缀，并说明目的。例如：

```text
exp: add baseline seed sweep for model-01
paper: revise sensitivity analysis section
```

## 角色与任务流程

- A 负责架构、算法、数据角色、评价协议和 P0 技术结论。
- B 负责数据处理、实现、基线和批量实验。
- C 负责实现协作、结果分析、图表和 LaTeX 论文。
- 每个任务必须有 `task_id`、Owner、Reviewer、分支、提示词版本和验收条件，模板见 `governance/task-card-template.yml`。
- 跨设备交接使用 `governance/handoff-template.md`；提示词调用使用 `prompt_id@version` 和 `prompt_run_id`。
- AI 生成内容必须由 Owner 测试和人工复核，论文只引用已接受的 `run_id`。
- 无解、失败、阻塞和证据不足的问题必须登记 `feedback_id`；P0/P1 反馈未关闭前不得合并相关 PR。

## 任务流程

1. 负责人可以在会议或语音中口头发布任务，但执行前必须在 `docs/tasks/` 创建任务卡，填写题目/子问题编号和 `announcement_ref`。
2. 任务按 `problem_id → subproblem_id` 划分，例如 `Q1 → Q1-S03`；工作包和设备只表示执行方式。
3. 接收任务的队友确认任务卡后创建任务分支，所有路径使用相对路径。
4. 运行最小验证或实验，并保存 `run_id`、配置、数据版本和环境信息。
5. 回馈第一行必须包含 `task_id`；失败、风险、阻塞或证据不足必须同时登记 `feedback_id`。
6. 提交 Pull Request，由另一名成员复核。
7. 合并后更新决策记录、实验索引和 `paper/claim-ledger.csv`（如涉及论文主张）。

## 数据与密钥

原始数据和大型模型不直接进入 Git。密钥、个人信息、竞赛账号信息和未公开题目不得提交仓库。
