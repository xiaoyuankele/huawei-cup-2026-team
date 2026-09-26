# Q1 纵向工作包分发 v2

本文件是三个人的实际执行入口。A/B/C 不再作为固定人员身份；每个工作包明确 `Owner`、`Peer Reviewer` 和 `Release Integrator`，三人各自负责一段代码、实验和论文。

## 分配表

| 工作包 | Issue | Owner | 代码交付 | 实验交付 | 论文交付 | Peer Reviewer | Release Integrator | 正式实验门 |
|---|---|---|---|---|---|---|---|---|
| WP-A 数据与证据 | [#8](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/8) | ACTOR-1 | 审计、预处理、manifest、指标目录 | 数据角色、A1 fit/holdout、重叠、缺失、漂移和泄漏 | 数据方法、预处理和限制段 | ACTOR-2 | ACTOR-3 | G0 |
| WP-B 模型与优化 | [#9](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/9) | ACTOR-2 | 统一评分接口、基线、线性投影、PP-GA、对照 | 分层模型比较、敏感性、失败运行 | 模型定义、目标函数、实验协议 | ACTOR-3 | ACTOR-1 | G1 |
| WP-C 验证与结果 | [#10](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/10) | ACTOR-3 | 冲突、验证、稳健性、图表和结果表脚本 | rank reversal、bootstrap、重复 seed、域分层 | 结果、冲突解释、图表和限制段 | ACTOR-1 | ACTOR-2 | G2 |
| Q1-INT/T-Q1-009 | [#11](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/11) | ACTOR-1（协调） | claim-ledger、整合脚本、复现检查 | 全量复现、论文数字一致性、发布清单 | 三段合并、主张审查和最终稿 | 三人共同 | 三人共同 | G3 |

## 发给 ACTOR-1：WP-A（Issue [#8](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/8)）

```text
你是 WP-A Owner。交付必须同时包含代码、实验和论文段。

代码：维护只读审计、q1_indicator_preprocess.py、指标目录、manifest 和审计输出，不修改 data/origin/。
实验：记录 A1 fit/holdout、A2/A3 overlap、新增子集、NaN、漂移、泄漏和 pending_verification 方向；不得建立未经批准的质量总分或 PP-GA 权重。
论文：起草数据角色、A1 fit-only、缺失/非有限值、同源重叠、代理信号和限制段；所有数字回链 run_id。

先经过 ACTOR-2 Peer Review，再由 ACTOR-3 作为 Release Integrator 检查接口、manifest、claim ledger 和 handoff。状态依次写入 RUN_COMPLETE、PEER_REVIEW、PACKAGE_ACCEPTED。
```

## 发给 ACTOR-2：WP-B（Issue [#9](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/9)）

```text
你是 WP-B Owner。交付必须同时包含代码、实验和论文段。

代码：实现统一评分接口、等权/稳健基线、线性投影模型、PP-GA 和批准的对照方法。
实验：先做 smoke test；G1 后为每种方法建立独立 run_id，固定 seed、数据分层和 A1 fit 变换，保留失败运行。
论文：起草变量、目标函数、约束、评价指标、PP-GA 边界和实验协议，不把单次高分写成最优性或因果结论。

ACTOR-3 负责 Peer Review，ACTOR-1 负责 Release Integrator 检查。未通过 G1 只能准备接口，不能写正式模型结论。
```

## 发给 ACTOR-3：WP-C（Issue [#10](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/10)）

```text
你是 WP-C Owner。交付必须同时包含代码、实验和论文段。

G0 后即可准备冲突诊断、验证、图表和论文骨架；G2 前只能使用模拟/接口数据，不能写正式结果。
代码：实现冲突分类、rank reversal、权重扰动、bootstrap/重复 seed、域分层、图表和结果表脚本。
实验：G2 后区分语义、测量、尺度/方向、缺失、同源重复、域漂移和优化不稳定；A2/A3 不称为独立真值。
论文：起草冲突、验证、稳健性、图表说明、结果解释和限制段。

ACTOR-1 负责 Peer Review，ACTOR-2 负责 Release Integrator 检查。T-Q1-008 只交付结果段，不独占最终论文整合。
```

## Q1-INT/T-Q1-009（Issue [#11](https://github.com/xiaoyuankele/huawei-cup-2026-team/issues/11)）

```text
你负责跨包整合，不得替任何 Owner 重写未经复核的结果。

检查 WP-A/B/C 是否都有 code、run_id、paper_section、PR、Peer Review、Integrator 结论和 handoff；逐项核对 paper/claim-ledger.csv、图表、正文数字和 PACKAGE_ACCEPTED 状态；执行全量复现和发布清单。

ACTOR-1、ACTOR-2、ACTOR-3 三人分别签署自己的工作包和最终 Release Council。任何一个人未签署，状态保持 REVIEW_BLOCKED 或未进入 INTEGRATED。
```

## 统一交付格式

```text
work_package: WP-A | WP-B | WP-C | Q1-INT
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
code_outputs:
run_id_and_metrics:
paper_outputs:
claim_refs:
changed_files:
command:
output_hashes:
status: DRAFT | SPEC_READY | CODE_READY | RUNNING | RUN_COMPLETE | PEER_REVIEW | PACKAGE_ACCEPTED | INTEGRATED | REWORK | REVIEW_BLOCKED
feedback_id:
reviewer_decision:
integrator_decision:
release_council_decision:
limitations:
next_action:
```

缺少代码、实验或论文段只能标记为 `PARTIAL`，不能进入 `PACKAGE_ACCEPTED`。
