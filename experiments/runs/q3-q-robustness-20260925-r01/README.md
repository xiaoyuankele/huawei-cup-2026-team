# Q3 Q-cost robustness sweep

运行号：`q3-q-robustness-20260925-r01`。本运行以 `q3-q-conditional-20260925-r01` 为父实验，固定 B6 M1 参数，扫描 `Q0=[0.1, 0.3, 0.5]`、附录 B 三种质量成本、C7 五种上下文长度和三档预算，共 135 个情景。

每个情景的 N、D、Q 都限制在 B1/B6 观测支持范围，使用六个确定性起点的显式约束 SLSQP。该运行用于判断前一轮“Q 被推到上界”的结论是否依赖 Q0 或成本函数；它不重新拟合 M1，不构造 A–B 逐行桥接，也不产生正式联合模型。

完整结果见 `tables/q3_q_robustness_scenarios.csv`。
