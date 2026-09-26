# Q3 optimization robustness run

运行号：`q3-optimization-robustness-20260926-r01`。

本运行将问题二冻结的 M0/M1 折叠参数逐折传播到问题三优化器，输出支持域内的 N-D、N-D-Q 情景区间，并在固定折叠、上下文长度和质量成本族内标记离散 Pareto 情景。

本运行不重新拟合，不使用 B8，不建立 A-B 行级连接，也不把 Q1 的 `Q_A(p)` 转为 B6 的 `Q_score`。因此输出是参数不确定性和成本假设下的条件稳健性证据，不是正式联合定律或全局最优证明。
