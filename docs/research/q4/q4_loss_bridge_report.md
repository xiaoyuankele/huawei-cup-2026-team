# 问题四：Loss–Benchmark 桥接审计

桥接数据必须区分可比性。`High` 组只有 7 个 Pythia 模型，`Medium` 组有 36 个来自不同报告和验证集的模型。结果见 `experiments/runs/q4-frontier-20260926-r01/artifacts/loss_bridge/bridge_regression_summary.csv`。

对 `LB_Average` 做线性描述：

- High：斜率约 −0.88 分/损失单位，留一模型平均绝对误差 0.48；斜率的 bootstrap 95% 区间约 [−4.59, 0.43]，方向并不稳定；
- Medium：斜率约 −14.53，留一平均绝对误差 6.72；该组只能作为敏感性分析，不能与 High 合并当作同一测量关系。

High 组的任务级斜率甚至方向不一致：BBH、MATH、IFEval 主要为负，GPQA 和 MUSR 为正，MMLU-PRO 接近零。这说明用 7 个高可比样本拟合一个统一的 Loss→综合 Benchmark 映射，会把任务噪声和小样本误差直接放大到预测结果。

因此，本轮不把问题二的 loss 缩放律直接转换成问题四的能力前沿。问题四主结果使用 C8 任务分数直接建模；Loss–Benchmark 映射只保留为桥接敏感性，并在最终报告中明确其样本量和区间。若要完成“减缓算力增长”情景，需要新增同验证集、同模型族的 loss–benchmark 配对数据，或把桥接不确定性完整传播到预测区间。

脚本：`scripts/q4/q4_loss_bridge_audit.py`。运行：

```powershell
python scripts/q4/q4_loss_bridge_audit.py
```
