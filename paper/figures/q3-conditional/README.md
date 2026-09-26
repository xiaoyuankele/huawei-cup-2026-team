# 问题三中文单张图候选包

本目录登记问题三的五张中文单坐标图。每张图只承载一个主要关系，提供 PDF、SVG、600 dpi PNG 和 TIFF；图形数据、脚本、哈希和限制写入各自目录的 `figure_manifest.json` 与 `figure_contract.md`。

## 图形清单

| 图形 | 主要用途 | 数据来源 | 证据边界 |
|---|---|---|---|
| [`q3-nd-baseline-cn-v1`](../q3-nd-baseline-cn-v1/) | M0 在 B1 支持域内的 N-D 基线配置 | `q3-nd-baseline-20260925-r01` | 条件基线，不外推为普适标度律 |
| [`q3-nd-budget-cn-v1`](../q3-nd-budget-cn-v1/) | M0 在预算和上下文变化下的 N-D 配置 | `q3-nd-baseline-20260925-r01` | 预算敏感性，不替代完整场景表 |
| [`q3-m1-qb-cn-v1`](../q3-m1-qb-cn-v1/) | M1 原生质量变量 $Q_B^*$ 随上下文和成本形状的变化 | `q3-q-conditional-20260925-r01` | $Q_B$ 是 B6/B7 原生变量，不是 Q1 的 $Q_A$；图取低预算代表性切片，完整 45 行仍以表格为准 |
| [`q3-context-cost-cn-v1`](../q3-context-cost-cn-v1/) | $C_{\mathrm{attn}}/C_{\mathrm{train}}=L_{\mathrm{ctx}}/30000$ 的结构关系 | `q3-q-conditional-20260925-r01` | $L_{\mathrm{ctx}}=30000$ 是成本结构临界点，不是模型效果验证的临界点 |
| [`q3-m2p-interface-cn-v1`](../q3-m2p-interface-cn-v1/) | M2/P 假设映射造成的条件 N-D 配置变化 | `q2-q3-interface-sensitivity-20260926-r01` | 条件情景敏感性；不识别 $G_{\mathrm{bridge}}$，不产生新增观测样本 |

[图注与阅读说明](captions.md)。

## 说明和使用规则

1. 五张图均为候选素材，当前任务状态为 `PEER_REVIEW`；独立复核完成前不把图形状态写成正式论文结论。
2. M1 图对应 3 类质量成本、5 档上下文和 3 档预算的 45 个原生情景；单图只显示低预算代表性切片，不能替代情景表。
3. M2/P 图使用 $Q_A(p)$ 作为 A 侧条件标签。若通过假设接口传入 Q3，必须明确这是反事实条件情景，不是 $Q_A$ 与 $Q_B$ 的实证标定。
4. 图注不得声称 A-B 联合 Loss 已验证、存在唯一最优配比，或支持域外结果是现实中的全局最优。
5. 正文引入需经过 Peer Reviewer 和 Integrator 独立审核；本次提交只登记素材、来源和解释，不自动替换正文引用。

## 复现入口

```powershell
python -X utf8 scripts/plot_q3_m0_nd_cn.py
python -X utf8 scripts/plot_q3_m0_nd_budget_cn.py
python -X utf8 scripts/plot_q3_m1_qb_cn.py
python -X utf8 scripts/plot_q3_context_cost_cn.py
python -X utf8 scripts/plot_q3_m2p_interface_cn.py
```



