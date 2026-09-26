# Q3 N-D baseline exploratory run

运行号：`q3-nd-baseline-20260925-r01`。

本运行固定 `Q=Q0`、`p=p0`，只使用问题二 M0 的 B1 经典 N-D 拟合参数，比较三个算力预算和 C7 架构元数据中观察到的上下文长度。

目标函数为 `E + A*N_B^(-alpha) + B*D_B^(-beta)`；预算约束为 `1e18*(6 + eta*Lctx)*N_B*D_B <= C`。同时输出无边界解析解和 B1 观测支持范围内的显式约束 SLSQP 解。

该运行只验证问题三基线优化流程，不加入质量项、领域配比项或 A-B 逐行桥接。超出 B1 的 `N,D` 范围的解析解仅作外推诊断。

主要结果：`tables/q3_nd_baseline_scenarios.csv`。
