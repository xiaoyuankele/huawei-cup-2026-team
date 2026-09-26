# 问题一第三问：数据与模型协作交接

`task_id: T-Q1-S03-HANDOFF` · `parent: T-Q1-003-MIXTURE` · 状态：待团队复核

本包汇总当前协作仓库的配比—Loss 研究资产。**第三问的主线是配比模型，质量是可选增量；补充校准审计中的 Q-only B1 不充当第三问的主基线。**目标仓库为 **xiaoyuankele/huawei-cup-2026-team**；基于 main 提交 `57fc793e9692b49a60c33c6d99ec10c17ffd5d76`。本包不替换团队既有模型、数据契约或正式论文结论。

## 回答题目的模型顺序

1. 以均值预测作简单参照，以 **纯配比 ilr-Ridge** 作主要基线，建立 `L_j=f_j(p)`；二阶 Ridge 和浅层 GBDT 是已有非线性候选。
2. 跨规模评价使用 `L_j=f_j(p)+g_j(p,log10(S/1M))`，明确规模项的拟合数据与评价角色。规模修正不以质量分数为前提。
3. 在相同数据角色、样本和评价口径下比较 `p` 与 `p+Q`，只有质量增量证据充分时才保留 Q。
4. 本包的 B1/M1+C0/C1/C2 是前期质量与规模实验的**补充复核**，不是“先有质量才可建模配比”的研究顺序。其系数和指标不可直接移作纯配比模型的结果；主线已有证据见模型索引。

## 从哪里开始

| 需要的内容 | 入口 |
|---|---|
| 数据角色、17 域/13 响应、公式、架构、指标口径 | [数据与模型指南](docs/problem/q1-s03-data-model-guide.md) |
| 已有团队模型、实验、组合效应与对应证据 | [团队模型索引](docs/problem/q1-s03-team-model-inventory.md) · [CSV](docs/problem/q1-s03-team-model-inventory.csv) |
| 补充质量模型的校准复核、RMSE/MAE 与外推限制 | [新运行报告](experiments/runs/q1-s03-handoff-audit-20260925-r01/README.md) |
| 所有汇总指标／逐域指标 | [汇总表](experiments/runs/q1-s03-handoff-audit-20260925-r01/metrics_aggregate.csv) · [逐域表](experiments/runs/q1-s03-handoff-audit-20260925-r01/metrics_by_domain.csv) |
| 可计算参数、规模系数及区间 | [参数 JSON](experiments/runs/q1-s03-handoff-audit-20260925-r01/model_parameters.json) · [系数表](experiments/runs/q1-s03-handoff-audit-20260925-r01/scale_coefficients.csv) |
| 可直接复用的输入 | [已有 v1 hard 组合表](experiments/runs/quality-mapping-20260925-r02-soft-handoff/tables/scored_wide_v1_hard.csv) |
| 数据清单及字段定义 | [数据清单](experiments/runs/q1-s03-handoff-audit-20260925-r01/data_inventory.csv) · [字段字典](experiments/runs/q1-s03-handoff-audit-20260925-r01/field_dictionary.csv) |
| 数值复现／作图 | [计算脚本](scripts/q1_s03/reproduce.py) · [图形脚本](scripts/q1_s03/plot_audit.py) |
| 交接与修正记录 | [handoff](docs/tasks/T-Q1-S03-HANDOFF.md) · [反馈记录](governance/feedback/records/FB-Q1-S03-20260925-CALIBRATION.yml) |

## 这次交付明确了什么

1. 配方和响应共 1,214 行。A4/A5 拟合基模型，A6/A8 完全同配方可估计规模差；A10 是规模与配方同时变化；A12/A14 是训练配方子集，其 Loss 为提供的估算值。
2. 简单规模修正确实复现了平均 Loss 的 RMSE/MAE 大幅下降，但这是相对于不具备可识别规模项的本地基线。不能据此宣布全团队模型最优。
3. 现在同时报告 mean-response、pooled、target-macro 与逐域误差。较小的平均 Loss RMSE 可能包含正负域误差抵消，单个总体数字不够。
4. 发布前修复 C2 的尺度单位和折内标准化；旧“C2 外推失败”的判断不再沿用。C3 的历史混合调参有问题，本包不复现旧结论。
5. 固定对数斜率在 10B→70B 高规模区间高估降幅。A10 是校准外回顾性评价，A12–A15 是估算表审计；均不写成新盲测或真实大模型验证。

## 复现命令

从仓库根目录执行，Python 3.11 环境：

```bash
python -m pip install -r requirements-q1-s03-handoff.txt
python -m unittest discover -s tests -p test_q1_s03.py -v
python scripts/q1_s03/reproduce.py --input experiments/runs/quality-mapping-20260925-r02-soft-handoff/tables/scored_wide_v1_hard.csv --output data/processed/q1-s03-reproduction --bootstrap 5000 --seed 20260925
python scripts/q1_s03/plot_audit.py --run experiments/runs/q1-s03-handoff-audit-20260925-r01
```

计算脚本默认只导出参数和聚合结果；如确需逐行预测，`--export-predictions` 必须输出到团队受控目录。本次提交复用已登记的派生输入，不增加原始附件、个人配置或原始对话。

对新配方计算：按 `model_parameters.json` 的字段顺序构造特征，使用其均值/标准差与标准化回归系数得到基预测；再按 C1/C2 公式加规模项。完整逐域计算与指标实现以脚本为准。S 必须使用统一规模单位，不能将 `1B` 数字 1 直接代入 `log10(S/1M)`。

既有团队成果仍各自保留输入版本、拟合角色与审核状态；需要人工复核后，才决定正式论文引用与主模型选型。
