# 问题三执行架构图

状态：`REVIEW_BLOCKED`。本图描述当前可执行、可复核的条件解答路径；理论四量接口保留在图中，但不会绕过数据识别闸门进入正式联合拟合。

```mermaid
flowchart TB
    Q3["问题三目标<br/>在预算 C 与上下文 Lctx 下配置 N、D、Q、p"]

    subgraph G0["G0：数据、投毒与版本审计"]
        R["冻结数据角色、来源哈希和 run_id"]
        V["版本路由<br/>队友交接版 / 本条件接口版 / 队友本地前沿版"]
        EX["排除项<br/>B8 不进主拟合；C8 四个截断 JSON 不进 Q3"]
    end
    Q3 --> R --> V
    R --> EX

    subgraph DATA["输入证据"]
        B1["B1：1,176 行<br/>N、D → M0"]
        B6["B6：360 行<br/>N、D、原生 Q_score → M1"]
        B7["B7：B6 嵌套扩展<br/>只作条件核验"]
        C7["C7：5 个上下文值<br/>Lctx = 2048…131072"]
        P["A4/A5：6 个观测 p 候选<br/>Q_A(p) 为 Q1 侧候选尺度"]
    end
    R --> B1
    R --> B6
    R --> B7
    R --> C7
    R --> P

    subgraph MODEL["可识别模型层"]
        M0["M0：规模基线<br/>L = E + A N^-α + B D^-β"]
        M1["M1：原生质量条件<br/>L = M0 + G(1 − Q_B)"]
        M2["M2/P：配比离散情景<br/>Q_A(p) = Σ p_j q_j"]
        MH["M3-H：理论四量接口<br/>ilr(p) → 有效数据效率 M_p<br/>只做敏感性/反事实"]
    end
    B1 --> M0
    B6 --> M1
    B7 --> M1
    P --> M2
    P -.-> MH

    BLOCK["识别闸门：A/B 没有行或批次连接键；<br/>Q1 与 B6 质量尺度未校准；G_bridge 不可识别"]
    M2 -.-> BLOCK
    MH -.-> BLOCK

    subgraph OPT["约束与求解层"]
        COST["成本约束<br/>C_base = 10^18 N_B D_B(6 + ηLctx)<br/>M1 另加 C_Q"]
        BOUND["支持域与边界<br/>N、D ∈ B1 支持域；Q_B ∈ [0.1,1.0]<br/>预算、上下文、有限性"]
        S0["M0 求解<br/>解析预算解 + 有界多起点 SLSQP"]
        S1["M1 求解<br/>对数参数化 + 多起点 SLSQP"]
        CAL["假设校准<br/>Q_A(0–100) → Q_B(0.1–1.0)<br/>仅用于接口敏感性"]
        S2["M2 求解<br/>固定假设 Q_B，复用 M1 求解器"]
        ALG["智能算法当前不启用<br/>维度低、目标光滑、约束明确；<br/>离散/非凸/整数扩展时再评估"]
    end
    M0 --> S0
    M1 --> S1
    M2 --> CAL --> S2
    COST --> S0
    COST --> S1
    COST --> S2
    BOUND --> S0
    BOUND --> S1
    BOUND --> S2
    ALG -.-> S0
    ALG -.-> S1
    ALG -.-> S2

    subgraph VAL["验证与审查层"]
        F["数值检查<br/>有限性、输出哈希、预算相对误差"]
        U["稳健性<br/>参数折叠、成本族、Q0、上下文、预算"]
        L["边界检查<br/>支持域、外推标记、边界触达"]
        N["主张闸门<br/>不按行拼接、不把假设标定写成实证<br/>不声称正式 M3 或全局最优"]
    end
    S0 --> F
    S1 --> F
    S2 --> F
    F --> U --> L --> N

    subgraph OUT["可交付输出"]
        O0["Q3_ND：15 个 M0 情景"]
        O1["Q3_Q_native：45 个原生 Q 情景"]
        O2["Q3_P_panel：90 行 p 条件面板"]
        O3["Q3_M2_interface：1,350 行接口敏感性"]
        O4["条件结论、限制、版本表<br/>任务卡与 experiments/index.csv<br/>保持 REVIEW_BLOCKED"]
    end
    N --> O0
    N --> O1
    N --> O2
    N --> O3
    O0 --> O4
    O1 --> O4
    O2 --> O4
    O3 --> O4

    classDef input fill:#EAF3FF,stroke:#2F5597,color:#17365D;
    classDef model fill:#EAF7EA,stroke:#38761D,color:#1F4D1F;
    classDef opt fill:#FFF2CC,stroke:#BF9000,color:#5B4300;
    classDef gate fill:#FCE4D6,stroke:#C65911,color:#7F2F00;
    classDef output fill:#E4DFEC,stroke:#674EA7,color:#351C75;
    class B1,B6,B7,C7,P input;
    class M0,M1,M2,MH model;
    class COST,BOUND,S0,S1,CAL,S2,ALG opt;
    class R,V,EX,BLOCK,F,U,L,N gate;
    class O0,O1,O2,O3,O4 output;
```

## 执行顺序

| 阶段 | 执行动作 | 形成的证据 | 停止条件 |
|---|---|---|---|
| G0 审计 | 冻结数据角色、剔除投毒/截断输入、登记版本 | 数据角色、哈希、run_id、版本表 | 发现来源或尺度不清时停止联合建模 |
| M0 | 用 B1 拟合 `N-D` 标度律并做预算优化 | 15 个 N-D 条件情景 | 超出支持域必须标记外推 |
| M1 | 用 B6 原生 `Q_score` 加入质量成本 | 45 个 Q 条件情景 | 不得把 `Q_score` 当成 Q1 `Q_A(p)` |
| M2/P | 对 6 个观测配比候选做离散面板 | 90 行 p 面板 | p 只作 A 侧条件标签 |
| Q2→Q3 接口 | 对 5 种映射、3 类成本、5 个上下文、3 个预算做敏感性 | 1,350 行接口矩阵 | 假设校准不能升级为实证标定 |
| 验证 | 检查有限性、哈希、预算误差、边界和参数传播 | metrics、表格哈希、稳健性摘要 | 任何失败都保持 `REVIEW_BLOCKED` |
| 封包 | 写入答案、任务卡、版本表和运行索引 | 可审查 Q3 条件解答 | Peer/Integrator 未确认前不进入正式论文结论 |

## 当前回答的范围

- 已经可以回答：规模 `N-D` 分配、原生 `Q_score` 的条件影响、预算/上下文/成本族敏感性、观测配比的条件面板。
- 可以作为理论补充：通过 `ilr(p)` 改变有效数据效率的 M3-H 形式，以及 Q2→Q3 接口的反事实敏感性。
- 仍然不能声称：A-B 跨来源联合 Loss、唯一最优配比、已经标定的 `G_bridge`、支持域外的实证全局最优。

## 回链

- 综合答复：`docs/decisions/q3-answer-package-20260926.md`
- 退阶策略：`docs/decisions/q3-fallback-solution-strategy-20260926.md`
- 版本边界：`docs/research/q3/conditional-interface-version-20260926.md`
- 任务卡：`docs/tasks/T-Q3-CONDITIONAL-INTERFACE.yml`
