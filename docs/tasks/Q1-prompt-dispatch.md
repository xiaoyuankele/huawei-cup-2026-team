# Q1 细分任务与提示词分发 v2

本文件是三个人和多个 Codex 对话的复制入口。实际分工见 [`Q1-work-packages.md`](Q1-work-packages.md)，架构规则见 [`docs/architecture.md`](../architecture.md)。执行身份只使用 Owner、Peer Reviewer、Release Integrator；A/B/C 不能代替真实 Actor。

## 当前分发

| 工作包 | Owner | Peer Reviewer | Release Integrator | 代码 | 实验 | 论文 |
|---|---|---|---|---|---|---|
| WP-A | ACTOR-1 | ACTOR-2 | ACTOR-3 | 数据审计和预处理 | 数据角色、归一化、泄漏和漂移 | 数据方法与限制段 |
| WP-B | ACTOR-2 | ACTOR-3 | ACTOR-1 | 评分接口、基线、PP-GA | 分层模型比较和敏感性 | 模型与实验协议段 |
| WP-C | ACTOR-3 | ACTOR-1 | ACTOR-2 | 冲突、验证、图表 | bootstrap、重复 seed、域分层 | 结果、解释和限制段 |
| Q1-INT | 三人共同 | 三人共同 | 三人共同 | claim ledger、整合和复现 | 全量复现与发布检查 | 三段合并和最终稿 |

## 通用执行协议

1. 先读对应 Task Card、canonical prompt、manifest 和 handoff 模板。
2. 执行前生成唯一 `prompt_run_id`；结束时写入 Prompt Run、AI 使用日志和 handoff。
3. 所有实验必须有 `run_id`、配置、seed、命令、commit、环境、输入引用、输出哈希和失败原因。
4. Owner 只在自己的工作分支修改；Peer Reviewer 只通过 PR/handoff 提意见；Integrator 只在证据齐全后推动包级合并。
5. 论文只能引用 `PACKAGE_ACCEPTED` 的 run_id；不能把 A2/A3 全量写成独立真值。

## 复制给 ACTOR-1：WP-A Owner

```text
执行 WP-A/T-Q1-001/002。完成数据审计、只读预处理、指标目录、manifest、归一化和泄漏审计；记录 A1 fit/holdout、A2/A3 overlap、新增子集、缺失、漂移和 pending_verification。同步交付代码、run_id 和数据方法段。

G0 后可执行。ACTOR-2 做 Peer Review，ACTOR-3 做 Release Integrator。未完成三者检查不得 PACKAGE_ACCEPTED。
```

## 复制给 ACTOR-2：WP-B Owner

```text
执行 WP-B/T-Q1-003/004。先冻结统一评分接口、等权/稳健基线、线性投影、PP-GA、对照方法和评价指标；G1 后再做正式实验。每种方法独立 run_id，保留失败运行，并交付模型协议和实验段。

ACTOR-3 做 Peer Review，ACTOR-1 做 Release Integrator。单次最高分不能写成最优性或因果结论。
```

## 复制给 ACTOR-3：WP-C Owner

```text
执行 WP-C/T-Q1-005/006/007/008。G0 后可准备冲突诊断、验证、图表、表结构和论文骨架；G2 后再写正式数字。交付冲突分类、rank reversal、bootstrap/重复 seed、域分层、图表源文件、结果段和限制段。

ACTOR-1 做 Peer Review，ACTOR-2 做 Release Integrator。T-Q1-008 只负责 WP-C 结果段，跨包整合由 T-Q1-009 完成。
```

## 复制给 Q1-INT 对话

```text
执行 Q1-INT/T-Q1-009。检查 WP-A/B/C 的 code、run_id、paper_section、PR、Peer Review、Integrator 结论、handoff 和 claim-ledger；执行全量复现、正文/图表数字一致性、PDF、附件和哈希检查。

三人必须分别签署自己的工作包和最终 Release Council。任何一人未签署，状态保持 REVIEW_BLOCKED 或未进入 INTEGRATED。
```

## 回收格式

```text
work_package:
task_ids:
owner_actor:
peer_reviewer_actor:
release_integrator_actor:
release_approver_actors:
gate:
prompt_id@version:
prompt_run_id:
branch:
commit:
run_id:
changed_files:
outputs_and_hashes:
claim_refs:
status:
feedback_id:
peer_decision:
integrator_decision:
release_council_decision:
limitations:
next_action:
```
