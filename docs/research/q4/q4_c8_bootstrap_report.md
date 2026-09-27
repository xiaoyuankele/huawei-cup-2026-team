# 详细 C8 主模型的 cluster bootstrap

> **结果定位：历史不确定性量级检查。** 本文的 100 次发布方代理 bootstrap 仍可作为参考，但其年度训练样本和趋势情景不替代当前 70/30 主协议。

对 2024 年训练样本按模型发布方前缀（`Model` 中斜杠前字符串）做 100 次 cluster bootstrap，并重拟合完整 95% 分位模型。该前缀是组织/发布方代理，不是经过验证的模型家族，因此结果用于不确定性量级评估。

结果见 `experiments/runs/q4-frontier-20260926-r01/artifacts/c8_bootstrap/cluster_bootstrap_summary.csv`：

- 时间系数中位数约 1.04 分/月，bootstrap 95% 区间约 [0.69, 1.29]；
- 12 个月趋势型前沿中位数约 67.36，区间约 [60.73, 71.43]；
- 24 个月趋势型前沿中位数约 79.94，区间约 [69.07, 86.77]。

这些区间只覆盖发布方聚类重采样和模型估计不确定性，没有覆盖评测规则变化、数据源漂移、未来模型类型构成变化以及 Loss–Benchmark 桥接误差。因此最终结果仍应报告平台型与趋势型两类情景，而不能把趋势型区间当作唯一预测区间。

脚本：`scripts/q4/q4_c8_cluster_bootstrap.py`。运行：

```powershell
python scripts/q4/q4_c8_cluster_bootstrap.py
```
