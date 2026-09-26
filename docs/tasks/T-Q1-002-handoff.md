# [HANDOFF] 问题一指标语义与归一化

```text
[HANDOFF]
task_id: T-Q1-002
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
branch: feature/B/T-Q1-002
branch_owner_actor: ACTOR-1
prompt_id: P-DATA-001@v1.0.0
prompt_run_id: PR-20260923-003
run_id: q1-indicator-normalization-20260923-r01
input_refs: data/manifests/q1_raw.yaml; docs/decisions/q1-data-contract.md; problem/数据说明_已清除隐藏误导文字.pdf; problem/隐藏文字检查报告.md
commit: 7db9a5d
pr: https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/4
changed_files: indicator_catalog.yaml; configs/q1-indicator-normalization.yaml; scripts/q1_indicator_preprocess.py; data/manifests/q1_preprocessed.yaml; normalization_stats.json; indicator_audit.csv; normalization_sensitivity.csv; docs/decisions/q1-preprocessing-contract.md; docs/tasks/T-Q1-002.yml; governance/prompts/runs/PR-20260923-003.yml; experiments/index.csv; governance/ai-use-log.csv
command: python -X utf8 scripts/q1_indicator_preprocess.py --root . --config configs/q1-indicator-normalization.yaml
outputs: indicator_catalog.yaml; data/processed/q1_X_norm_v1.csv; normalization_stats.json; indicator_audit.csv; normalization_sensitivity.csv; data/manifests/q1_preprocessed.yaml
status: PEER_REVIEW
acceptance_result: PASS_WITH_WARNINGS
limitations: 22 个原始字段展开为 25 个派生标量列；16 个方向有证据并进入 higher-is-better 矩阵，9 个方向待核验并留空；A1 fit 估计 quantile_01_99 参数后复用于 A1 holdout/A2/A3；A2/A3 与 A1 存在同源 ID 重叠。
review_request: 复核每个字段的语义和方向依据，确认列表压缩、A1 fit 参数冻结、强相关/域漂移解释及 pending_verification 处理。
next_action: ACTOR-2 完成 Peer Review；通过后由 ACTOR-3 检查包级接口、证据回链和 handoff，或登记 feedback_id 并触发 REWORK。
[/HANDOFF]
```

本交接单只包含脱敏元数据和相对路径，不包含原始数据、题目正文或完整 AI 对话。
