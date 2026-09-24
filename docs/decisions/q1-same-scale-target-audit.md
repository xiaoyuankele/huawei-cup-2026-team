# 轨道 A：A6 同尺度逐目标审计

候选协议：Helmert-ilr、乘法零替换 \(\epsilon=10^{-4}\)、线性多响应 Ridge，`alpha` 由 A4/A5 五折交叉验证选择。A6/A7 是 1M 同尺度外部验证。

| 目标 | A6 R² | A6 Spearman |
|---|---:|---:|
| arxiv | 0.754 | 0.916 |
| freelaw | 0.832 | 0.918 |
| pubmed_central | 0.859 | 0.940 |
| wikipedia_en | 0.797 | 0.904 |
| dm_mathematics | 0.848 | 0.902 |
| github | 0.741 | 0.886 |
| stackexchange | 0.701 | 0.884 |
| gutenberg_pg_19 | 0.715 | 0.876 |
| pile_cc | 0.683 | 0.849 |
| ubuntu_irc | 0.820 | 0.874 |
| hackernews | 0.678 | 0.849 |
| pubmed_abstracts | 0.693 | 0.870 |
| uspto_backgrounds | 0.821 | 0.899 |

A6 的目标级 R² 全部为正，范围为 0.678–0.859；目标级 Spearman 范围为 0.849–0.940。这说明在同一 1M 尺度内，候选配比模型对目标排序和相对变化有一致的信号，但目标间解释程度不同，不能只报告平均值。

该结果仍受零替换和坐标基敏感性影响，也不能外推到 A8 的 60M 绝对 Loss。正式报告必须同时给出目标级表、零替换敏感性和规模边界。
