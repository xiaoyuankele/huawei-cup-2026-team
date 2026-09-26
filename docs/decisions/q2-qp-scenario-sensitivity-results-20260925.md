# 问题二 Q/p 场景敏感性结果

状态：`Q2_QP_SCENARIO_SENSITIVITY_EXPLORATORY`。

本轮只使用问题一 A4--A15 的 1214 行 Q/p 接口，保持每一行的 17 域配比 `p` 不变，按已批准的三条 c4 语义分支重新计算 Q。基线由冻结的 A1/full 域分数重构，最大误差为 `8.53e-14`；17 个 p 列的和误差为 `1.55e-15`。Q 全部有限并保持在 0--100，重复的 dataset/index 数为 0。1088 行是有观测 Loss 的角色，126 行是 estimate/外推角色。

场景包括基线、分别替换 `nih_exporter`、`pubmed_abstracts`、`uspto_backgrounds` 的 c4 分支，以及同时应用三条分支。域级 Q 的变化分别为约 `+1.25`、`+1.30` 和 `+1.87`；在行级混合后，最大绝对 Q 变化约 `1.30`，同时应用三条分支时各数据集的秩相关仍约为 `0.98--0.99`。这些结果说明当前批准的 c4 替代对接口有可量化但有限的影响，不能把它解释为质量干预效果。

本实验没有修改 A16 映射原文件，没有把 Q1 的 0--100 分数转换成 B6/B7 的 `Q_score`，没有连接 B 的 Loss，也没有拟合问题二模型。B8 的方向和来源阻断保持不变。输出见 `experiments/runs/q2-qp-scenario-sensitivity-20260925-r01/`，其中 `scenario_summary.csv` 按数据集和角色提供分层结果，`baseline_semantic_bounds.csv` 保留候选锚点上下界；上下界不是置信区间。
