# E1 仓库规范核对与补正

task_id: T-Q2-E1-MARGINAL

**结论：原提交不完全符合治理规范；本次补登记后仍为 REVIEW_BLOCKED。**
核对范围为 PR #29 的 E1 交付，不构成对已合并 PR #28 或整个仓库的全面审计。
本记录为助手协助的 Owner 侧自查，不是 Peer 或 Integrator 的独立决定。

## 依据与差异

依据：[CONTRIBUTING](../../../CONTRIBUTING.md)、[角色协议 v2](../../../governance/actor-role-policy.md)、[提示词规范](../../../governance/prompts/README.md)、[交接模板](../../../governance/handoff-template.md)、[PR 模板](../../../.github/pull_request_template.md)。
CONTRIBUTING 保留旧分支模式，v2 要求 wp/<actor>/<work-package>；当前 codex 分支不符合两者，不能用本地工具默认命名覆盖团队规范。

| 检查项 | 原状与补正 | 当前判断 |
|---|---|---|
| 推送与评审入口 | 任务分支、draft PR #29；没有直接推 main、强推或自行合并 | 推送方式符合要求 |
| 科学产物与复现 | 配置、环境、冻结参数和输出哈希、11 张表及复现记录已交付 | 文件/数值核验通过，不等于科学验收 |
| 数据边界 | E1 使用已发布派生输入；未新增原始附件、题目或完整敏感对话 | 本轮提交范围符合数据约定 |
| 正式交接 | 原缺符合模板的 handoff，现补任务交接及 run 治理补充记录 | 已补登记，待独立检查 |
| Prompt 与反馈 | 原仅存在 ID，缺注册模板、调用文件和反馈案例 | 现补脱敏重建记录；历史逐次调用无法完整还原 |
| 代码—实验—论文 | 原有 claim ledger，现补未验收论文草稿回链 | 草稿未进入正式论文 |
| 任务状态 | 原 RUN_COMPLETE/REVIEW 混淆计算与验收 | 交付改 REVIEW_BLOCKED；计算仍 RUN_COMPLETE |
| 执行前任务卡 | 原执行后才补任务卡；缺发布人和接收确认记录 | 历史流程偏差不能追溯补成预登记 |
| 分支及工作包路由 | 当前 codex/q2-e1-marginal-elasticity，v2 期望 wp/ACTOR-2/WP-B | 偏差未解决；现有 WP-B Issue #9 为 Q1，Q2 扩展未确认 |
| Gate 与独立评审 | 未提供 G1 通过、Peer 或 Integrator 签署证据 | 不具备 PACKAGE_ACCEPTED 或合并条件 |

## 可复核边界

本次只补治理资料，不重算、不重拟合、不改变冻结输入和数值 CSV。
原实验代码提交保留为 d58e4a1de3f9bac16bbfbc6bf75cfa5c24a322d0；补登记日期使用实际时间，不冒充执行前记录。
模板为事后脱敏重建，不能证明原始逐次调用使用过相同模板。Actor 是待确认的工作包责任路由，不是人工签署。

反馈：[科学质量轴限制](../../../governance/feedback/records/FB-Q2-E1-01.yml)、[结构限制](../../../governance/feedback/records/FB-Q2-E1-02.yml)、[P1 治理缺口](../../../governance/feedback/records/FB-Q2-E1-GOV-20260925.yml)。
P1 保持未关闭，不自行接受例外或代填评审。保留现有 PR 审计历史，等待 Integrator 决定工作包分支归并或明确例外，并由实际成员完成独立复核。

此前反馈未始终以 task_id 开头也属于流程偏差；从本轮起纠正。文件哈希验证器并不验证团队授权和独立性，不能作为完全合规的证明。
