# [HANDOFF] 任务交接

交接内容必须让另一台设备在不依赖聊天上下文的情况下复核或重跑。任务完成后由 Owner 填写，Peer Reviewer 和 Release Integrator 分别补充决定。

```text
[HANDOFF]
task_id: T-Q1-001
problem_id: Q1
subproblem_id: Q1-S00
work_package: WP-A
owner_actor: ACTOR-1
peer_reviewer_actor: ACTOR-2
release_integrator_actor: ACTOR-3
release_approver_actors: ACTOR-1; ACTOR-2; ACTOR-3
independence_check: PASS | FAIL | REVIEW_BLOCKED
peer_decision: PENDING | PASS | PASS_WITH_WARNINGS | FAIL
integrator_decision: PENDING | PASS | PASS_WITH_WARNINGS | FAIL
release_council_decision: PENDING | ACCEPTED | REWORK | BLOCKED
device_id: DEVICE-B-01
branch: wp/ACTOR-1/WP-A
prompt_id: P-EXP-001@v1.0.0
prompt_run_id: PR-20260923-001
run_id: R-Q1-001-20260923
gate: G0
input_refs: data/manifests/example.yaml; <其他 commit 或产物>
commit: <git sha>
changed_files: <相对路径列表>
command: <完整可复制命令>
outputs: <指标、日志、图表和文件路径>
status: RUN_COMPLETE | PEER_REVIEW | PACKAGE_ACCEPTED | REWORK | REVIEW_BLOCKED
feedback_id: <feedback_id 或 NONE>
feedback_status: NONE | CAPTURED | RESPONDED | CLOSED | BLOCKED
feedback_summary: <脱敏一句话>
evidence_ref: <run、PR 或文件>
limitations: <已知限制、失败实验或未验证假设>
next_action: <下一步动作>
[/HANDOFF]
```

完整的敏感输入和 AI 原始输出不放入公开仓库；公开记录保留脱敏摘要、引用关系和必要哈希。
