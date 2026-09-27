# Q3 p fixed-budget frontier panel

运行号：`q3-p-fixed-budget-panel-20260926-r01`。

本运行把问题一中实际观测过的 6 个配比候选与固定预算 Q3 `N-D-Q_score` 前沿做笛卡尔情景拼接，共 810 行。A 侧 `Q_A(p)` 和 Loss 与 B 侧原生 `Q_score`、N-D 配置并列保留，不进入同一个损失函数。

这是一张条件策略面板，不是样本级 A-B 连接，也不识别跨来源的 p 或质量系数。
