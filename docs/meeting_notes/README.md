# 会议记录

文件名格式：`YYYYMMDD-topic.md`。

每次记录至少包含：参会人、已决定事项、负责人、截止时间、待解决问题和对应 Issue/commit。

如果会议或语音中口头发布任务，补充以下字段，作为 `announcement_ref`：

```text
problem_id: Q1
subproblem_id: Q1-S03
task_id: T-Q1-S03-001
announced_by_actor: ACTOR-1
owner_actor: ACTOR-2
peer_reviewer_actor: ACTOR-3
objective: <一句话目标>
expected_outputs: <交付物>
acceptance_criteria: <验收条件>
deadline: <时间>
acknowledged_by_actor: ACTOR-2
```

会议记录只保存脱敏摘要；完整语音、题目原文和敏感讨论放在受控本地目录。
