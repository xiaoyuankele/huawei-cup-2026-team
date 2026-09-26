# 问题一规模—域级输入汇总

运行号：`q1-scale-domain-summary-20260924-r01`。本表读取 `q1-scale-feature-table-20260924-r01` 的长格式派生表，不读取 Loss 目标。

输出 102 行，覆盖 6 个数据集 × 17 个训练域。每行给出比例均值、中位数、5%/95%分位数、零比例，以及按总规模换算的期望 token 数均值、中位数、最小值和最大值。

按配方平均的最小域级期望 token 数来自 `train_the_pile_enron_emails`：

| 规模 | 最小域 | 平均期望 token 数 |
|---:|---|---:|
| 1M | enron_emails | 2,211 |
| 60M | enron_emails | 141,329 |
| 1B | enron_emails | 156,250 |
| 10B | enron_emails | 10,636,194 |
| 70B | enron_emails | 74,453,356 |

最大平均域随规模表中的配方分布变化：1M/60M 为 `github`，1B 为 `pile_cc`，10B/70B 为 `freelaw`。这些数字描述的是配方输入支持，不是实测训练语料计数，也不能单独证明某域在训练过程中的实际有效样本量。

输出文件：

- `experiments/runs/q1-scale-domain-summary-20260924-r01/q1_scale_domain_summary.csv`
- `experiments/runs/q1-scale-domain-summary-20260924-r01/metrics.json`

后续若使用 `expected_tokens_*` 作为模型特征，应同时保留原始比例 `p_*` 和总规模 `S`，避免把比例效应、规模效应和数据处理过程混为一个变量。
