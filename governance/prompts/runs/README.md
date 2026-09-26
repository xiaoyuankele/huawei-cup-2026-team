# Prompt Run 记录

每一次实际 AI 调用在本目录或受控本地目录生成一个 `PR-<日期>-<序号>.yml`。公开仓库中的记录必须脱敏，并绑定工作包的 Owner、Peer Reviewer 和 Release Integrator。

```yaml
prompt_run_id: PR-20260923-001
task_id: T-Q1-001
work_package: WP-A
prompt_id: P-EXP-001
prompt_version: v1.0.0
owner_actor: ACTOR-1
peer_reviewer_actor: ACTOR-2
release_integrator_actor: ACTOR-3
device_id: DEVICE-B-01
date: 2026-09-23
tool: ""
model: ""
provider: ""
input_summary: "不包含题目原文、原始数据或密钥"
output_ref: ""
output_sha256: ""
git_commit: ""
run_id: ""
needs_human_review: true
peer_decision: PENDING | PASS | PASS_WITH_WARNINGS | FAIL
integrator_decision: PENDING | PASS | PASS_WITH_WARNINGS | FAIL
release_council_decision: PENDING | ACCEPTED | REWORK | BLOCKED
status: TRIAL | RUN_COMPLETE | PEER_REVIEW | PACKAGE_ACCEPTED | REJECTED
failure_or_limitations: ""
next_action: ""
```

多个 `prompt_run_id` 可以服务同一个实验 `run_id`；一个 `prompt_run_id` 不能替代实验配置和运行记录。旧记录如果仍使用 `reviewer_actor` 或 `final_authority_actor`，必须迁移到本格式并保留历史 commit。
