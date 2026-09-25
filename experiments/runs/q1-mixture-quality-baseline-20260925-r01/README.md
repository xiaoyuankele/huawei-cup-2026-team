# Q1 配比—质量基线模型

运行号：`q1-mixture-quality-baseline-20260925-r01`。A4/A5 仅用于拟合和五折选择 alpha，A6/A7 为同尺度外部验证，A8–A11 为跨尺度诊断，A12–A15 为外推情景诊断。模型比较 p-only、p + Q_raw + mapped_mass，以及 Q_raw/mapped_mass 敏感性分支。未映射领域保留在配比向量中，不填充质量零值。

该运行是候选基线，状态为 LOCAL_RESULT_PENDING_TEAM_REVIEW，不支持因果质量效应、通用跨规模定律或最优配比结论。Q_renorm 对 mapped_mass=0 的行使用训练行中位数并带有可用性指示，不是质量为零的填充。`paper_comparison_summary.csv` 给出联合指标差值，`paper_comparison_target_summary.csv` 给出逐目标误差差值。

重跑命令：`python -X utf8 scripts/q1_mixture_quality_baseline.py`
