# [HANDOFF] 问题一数据契约

```text
[HANDOFF]
task_id: T-Q1-001
work_package: WP-A
owner_actor: ACTOR-1
peer_reviewer_actor: ACTOR-2
release_integrator_actor: ACTOR-3
release_approver_actors: ACTOR-1; ACTOR-2; ACTOR-3
independence_check: PASS
peer_decision: PENDING
integrator_decision: PENDING
release_council_decision: PENDING
device_id: DEVICE-LOCAL-CODEX
branch: feature/B/T-Q1-001
branch_owner_actor: ACTOR-1
prompt_id: P-EXP-001@v1.0.0
prompt_run_id: PR-20260923-002
run_id: q1-raw-contract-20260923-r01
input_refs: data/manifests/q1_raw.yaml; governance/prompts/catalog/P-EXP-001.md
commit: a8fd1399da10012edb28a6746f2619bc8e562543
pr: https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/3
changed_files: data/manifests/q1_raw.yaml; docs/decisions/q1-data-contract.md; schema_snapshot.csv; scripts/q1_audit_raw.py; docs/tasks/T-Q1-001.yml; docs/tasks/T-Q1-001-handoff.md; governance/prompts/registry.csv; experiments/index.csv; governance/ai-use-log.csv; governance/prompts/runs/PR-20260923-002.yml
command: python -X utf8 scripts/q1_audit_raw.py
outputs: data/manifests/q1_raw.yaml; docs/decisions/q1-data-contract.md; schema_snapshot.csv; scripts/q1_audit_raw.py
status: PEER_REVIEW
acceptance_result: PASS_WITH_WARNINGS
limitations: A1/A3 含 NaN 非有限值；A2/A3 与 A1 同属上游质量信号族；上游许可条款未记录。
review_request: 复核 A1/A2/A3 的拟合、内部验证和外部验证边界，确认 A4-A15 的外部验证/外推分层及原始数据只读规则。
next_action: ACTOR-2 完成 Peer Review；通过后由 ACTOR-3 检查包级接口、证据回链和 handoff，再将任务卡和 Prompt Run 更新为 PACKAGE_ACCEPTED。
[/HANDOFF]
```

本交接单只包含脱敏元数据和相对路径，不包含原始数据、题目正文或完整 AI 对话。
