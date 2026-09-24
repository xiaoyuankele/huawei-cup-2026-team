# 问题一规模特征表

运行号：`q1-scale-feature-table-20260924-r01`。

本次只读取 A4–A15 的配比输入，未读取 Loss 目标，也没有改变拟合、验证和外推角色。对每行配方先按原始行和归一化：

\[
p'_{r,d}=\frac{p_{r,d}}{\sum_j p_{r,j}},\qquad
N_{r,d}=p'_{r,d}S_r,qquad
x_{s,r}=\log_{10}(S_r).
\]

其中 (S_r) 使用数据契约中的规模标签：1M、60M、1B、10B、70B。`N_{r,d}` 是按比例分配得到的期望域 token 数，可能是小数，不代表独立观测到的整数 token 计数。

输出规模：

- 宽表：1214 行、41 列，每行对应一条配方，包含数据角色、总规模、`log10_scale`、17 个归一化比例列和 17 个期望 token 数列；
- 长表：20638 行、9 列，每行对应一条配方—域组合，便于按规模和域聚合。

原始行和的范围约为 0.996–1.003；归一化后最大绝对偏差小于 (5\times10^{-16})。六个输入文件的 SHA256、派生表 SHA256 和计算公式均写入运行目录的 `metrics.json`。

## 输出文件

- `experiments/runs/q1-scale-feature-table-20260924-r01/q1_scale_features_wide.csv`
- `experiments/runs/q1-scale-feature-table-20260924-r01/q1_scale_features_long.csv`
- `experiments/runs/q1-scale-feature-table-20260924-r01/metrics.json`

这份表可以作为后续规模条件模型的输入特征，但不能据此声称已经获得了实际训练 token 统计；训练步数、去重、重复采样、模型大小等信息仍未由本次运行推断。
