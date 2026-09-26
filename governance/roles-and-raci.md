# 三人执行、复核与发布架构

本项目的执行单位是三个真实 Actor，不能用 A/B/C 角色名代替。A/B/C 只作为题目中的责任视角；任务卡以 `owner_actor`、`peer_reviewer_actor` 和 `release_integrator_actor` 为准。

## 三种可轮换身份

| 身份 | 权限 | 禁止事项 |
|---|---|---|
| Owner | 修改本工作包代码、配置、实验和论文段；解释自己的结果 | 不能审核自己的结果，不能把聊天输出当作证据 |
| Peer Reviewer | 独立检查代码、run manifest、统计边界和主张；登记 feedback | 不能代替 Owner 修改结果，不能绕过失败运行 |
| Release Integrator | 检查接口、证据回链、claim ledger 和包状态；决定是否进入集成分支 | 不能替代 Peer Review，不能把缺证据结果并入论文 |

当前采用环形分配：

| 工作包 | Owner | Peer Reviewer | Release Integrator |
|---|---|---|---|
| WP-A 数据与证据 | ACTOR-1 | ACTOR-2 | ACTOR-3 |
| WP-B 模型与优化 | ACTOR-2 | ACTOR-3 | ACTOR-1 |
| WP-C 验证与结果 | ACTOR-3 | ACTOR-1 | ACTOR-2 |

Q1-INT/T-Q1-009 是跨包发布任务。ACTOR-1 可以承担协调和集成分支维护，但最终发布必须由 ACTOR-1、ACTOR-2、ACTOR-3 三人共同签署。

## RACI

| 工作项 | ACTOR-1 | ACTOR-2 | ACTOR-3 |
|---|---|---|---|
| WP-A 数据代码、预处理实验、数据论文段 | R | C/Peer | C/Integrator |
| WP-B 模型代码、基线实验、模型论文段 | C/Integrator | R | C/Peer |
| WP-C 冲突验证代码、稳健性实验、结果论文段 | C/Peer | C/Integrator | R |
| Q1-INT claim ledger、论文整合和发布检查 | C/Coordinator | C | C |
| 最终提交 | Release Council | Release Council | Release Council |

`R` 是执行责任，`C/Peer` 是独立复核，`C/Integrator` 是包级集成检查。协调人不拥有单独的最终否决或签署权。

## 证据门

- **G0：范围门**——数据角色、题意解释、保密边界和任务卡冻结。
- **G1：接口门**——预处理 manifest、指标方向、模型输入输出和评价指标冻结。
- **G2：运行门**——模型正式 run 通过配置、seed、分层和失败记录检查。
- **G3：论文门**——三个工作包都完成 code、run_id、paper section、handoff 和 Peer Review。
- **G4：发布门**——claim ledger、PDF、附件、哈希和提交材料由三人共同检查。

没有独立 Peer Review 时状态只能是 `REVIEW_BLOCKED`；没有 Integrator 检查时不能进入 `PACKAGE_ACCEPTED`；没有三人 Release Council 签署时不能进入 `INTEGRATED`。

## 任务状态

统一状态为：

```text
DRAFT → SPEC_READY → CODE_READY → RUNNING → RUN_COMPLETE
      → PEER_REVIEW → PACKAGE_ACCEPTED → INTEGRATED
                         └→ REWORK / REVIEW_BLOCKED
```

`Task Card` 管范围和依赖，`PR` 管代码审阅，`Run Manifest` 管实验事实，`paper/claim-ledger.csv` 管论文主张。四者缺一不可。

## 对话与 GitHub 规则

每个 Actor 使用一个工作包对话；协调对话只维护任务图、门控和决策日志。每个工作包原则上一个 Issue、一个主 PR，微任务作为 checklist。Reviewer 通过 PR/handoff 留意见，Owner 在自己的分支修订；Integrator 只在包级证据齐全后推动合并。

分支命名使用 `wp/ACTOR-1/WP-A`、`wp/ACTOR-2/WP-B`、`wp/ACTOR-3/WP-C`；跨包整合使用 `integration/ACTOR-1/Q1-INT`。原始数据、未公开题目、密钥和敏感对话不进入 GitHub。
