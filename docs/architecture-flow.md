# 全流程架构图 v2

本图描述题目/子问题拆分、口头发布、三条纵向工作包、反馈回链、证据门和最终 Release Council。图源保存在 `architecture-flow.mmd`。

```mermaid
flowchart TB
    subgraph TEAM[三人执行入口]
        P1[ACTOR-1\nWP-A Owner\nWP-B Integrator]
        P2[ACTOR-2\nWP-B Owner\nWP-C Integrator]
        P3[ACTOR-3\nWP-C Owner\nWP-A Integrator]
        COORD[协调对话\n任务图/门控/决策]
    end

    subgraph PROBLEM_TREE[题目分解与发布]
        PROBLEM[Problem Qn]
        SUBPROBLEM[Subproblem Qn-Sxx]
        ANNOUNCE[口头/会议发布\nannouncement_ref]
    end

    subgraph WPS[纵向工作包]
        WPA[WP-A 数据与证据\n代码 + run_id + 数据论文段]
        WPB[WP-B 模型与优化\n代码 + run_id + 模型论文段]
        WPC[WP-C 验证与结果\n代码 + run_id + 结果论文段]
        INT[Q1-INT / T-Q1-009\nclaim ledger + 论文整合 + 发布检查]
    end

    subgraph GATES[证据门]
        G0[G0 范围/数据边界]
        G1[G1 数据契约与模型接口]
        G2[G2 已接受模型 run_id]
        G3[G3 三个包 PACKAGE_ACCEPTED]
        G4[G4 Release Council 三人签署]
    end

    subgraph SOURCES[事实源]
        TASK[Task Card\ntask_id + 题目/子问题]
        PR[Pull Request]
        RUN[Run Manifest]
        FEEDBACK[Feedback Case\nfeedback_id + 证据/响应]
        CLAIM[Claim Ledger]
    end

    P1 --> WPA
    P2 --> WPB
    P3 --> WPC
    P1 --> COORD
    P2 --> COORD
    P3 --> COORD
    COORD --> TASK
    PROBLEM --> SUBPROBLEM
    SUBPROBLEM --> ANNOUNCE
    ANNOUNCE --> TASK
    TASK --> G0
    G0 --> WPA
    G0 --> WPB
    G0 --> WPC
    WPA --> G1
    WPB --> G1
    G1 --> WPB
    WPB --> G2
    G2 --> WPC
    WPA --> G3
    WPB --> G3
    WPC --> G3
    G3 --> INT
    INT --> G4
    TASK -.-> PR
    PR -.-> RUN
    RUN -.-> CLAIM
    RUN -.-> FEEDBACK
    FEEDBACK -.-> TASK
    FEEDBACK -.-> PR
    CLAIM -.-> INT
    G4 --> RELEASE[集成分支/最终 PDF/附件]
```

## 阅读顺序

先看 Owner—Peer Reviewer—Integrator 的环形分工，再看 G0–G4 门控。WP-B 的模型规格和 WP-C 的脚手架可以在 G0 后并行准备；正式分析结果必须等待 G2。只有三个工作包全部 `PACKAGE_ACCEPTED`，Q1-INT 才能整合 claim ledger 和最终论文。
