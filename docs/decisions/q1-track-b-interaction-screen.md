# 轨道 B 规模—配比交互筛查

运行号：`q1-track-b-interaction-screen-20260924-r01`。

对 A6/A8 和 A12/A14 的成对 Loss 差值，分别与同一配方的 16 个 Helmert-ilr 坐标做 Pearson 相关，并用固定种子 20260924、1000 次 bootstrap 计算百分位 95% 区间。该过程不拟合交互模型，也不用于选择轨道 A 特征。

绝对相关最高的候选包括：

| 配对 | 目标 | 坐标 | 相关系数 | bootstrap 95% 区间 |
|---|---|---|---:|---:|
| A12/A14 | uspto_backgrounds | ilr_16 | 0.92 | [0.89, 0.94] |
| A12/A14 | ubuntu_irc | ilr_12 | 0.91 | [0.87, 0.94] |
| A6/A8 | ubuntu_irc | ilr_12 | 0.89 | [0.86, 0.91] |
| A6/A8 | dm_mathematics | ilr_5 | 0.86 | [0.84, 0.89] |
| A6/A8 | pubmed_central | ilr_3 | 0.86 | [0.83, 0.88] |

这些结果支持把低维规模—配比交互列为后续模型候选，而不是只使用统一规模截距。但由于这是在验证/外推目标上做的假设筛查，存在多重比较和角色边界限制；不能直接把这些坐标选入正式模型后再把同一数据当作独立验证。

输出：`experiments/runs/q1-track-b-interaction-screen-20260924-r01/interaction_screen.csv`。
