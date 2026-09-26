# 问题四：任务级与留一任务前沿审计

结果见 `experiments/runs/q4-frontier-20260926-r01/artifacts/task_frontier/task_frontier_summary.csv`。月度前沿仍使用 C8 逐任务结果、2024-06 至 2025-03 的同一榜单时段。

六个单任务 q95 的首末月变化如下：

- IFEval：+5.54 分；
- BBH：+3.35 分；
- MATH：+27.30 分；
- GPQA：+2.55 分；
- MUSR：约 +0.01 分；
- MMLU-PRO：+4.86 分。

MATH 的变化远大于其他任务，综合分的增长不能被解释成所有能力维度同步改善。另一方面，留一任务后的综合 q95 仍然全部上升：排除 MATH 后为 +4.21 分，排除其他任务时约为 +7.45 至 +9.31 分。因此“趋势完全由 MATH 造成”也不成立；更准确的结论是，MATH 放大了综合趋势，而其他任务提供了较弱但方向一致的支持，MUSR 几乎没有变化。

这项审计带来两个建模约束：

1. 主结果必须同时报告综合前沿和六个任务前沿，不能只报一个平均分；
2. 任务权重改变会显著改变趋势斜率，应把等权、留一任务和可能的稳健权重作为敏感性分析。

脚本：`scripts/q4/q4_task_frontier_audit.py`。运行：

```powershell
python scripts/q4/q4_task_frontier_audit.py
```
