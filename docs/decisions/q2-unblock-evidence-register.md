# 问题二迁移解锁证据登记表

当前总状态：`BLOCKED_FORMAL_JOINT_MIGRATION`

| blocker_id | 当前状态 | 需要的证据 | 通过标准 | 未通过时的处理 |
|---|---|---|---|---|
| Q1-SCORE | `OPEN` | Q1 `q_i`、权重、方向和归一化的独立复核 | run 状态为 `ACCEPTED`，指标方向和缺失处理有签字记录 | 只能使用候选分数做桥接敏感性 |
| DOMAIN-MAP | `OPEN` | 17 个混合域的版本化映射、近似误差和 inferred 域边界 | 每个实际使用域都有 direct/near_direct 或明确区间 | 保留未映射质量权重，不做零填充 |
| AB-JOIN | `OPEN` | A 与 B 的共享记录键，或条件迁移的研究声明 | 能证明逐行连接，或在协议中排除逐行因果解释 | 不建立联合逐行模型 |
| B8-PROV | `OPEN` | B8 生成脚本/公式、版本、质量定义、分层规则 | calibrated/extrapolated 语义可重现且方向可解释 | B8 永久隔离出主模型 |
| VALIDATION | `CLOSED_CONDITIONAL` | M0/M1 分组留出和外部诊断 | 角色不变、随机拆分禁用、嵌套扩展单独报告 | 保持探索性报告 |
| POISONING | `CLOSED` | 隐藏文字隔离报告和原始文件哈希 | 隐藏先验不进入参数、映射和结论 | 发现新污染时回滚派生结果 |

登记表只描述解锁条件，不代表任何 blocker 已被外部证据关闭。每次补证必须新建版本化 run，不能覆盖现有 `REVIEW_BLOCKED` 结果。
