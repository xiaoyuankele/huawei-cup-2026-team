# 问题四：时间标签安慰剂检验

对 10 个月的 q95 序列进行 100,000 次月份标签置换，重新计算线性斜率。结果见 `experiments/runs/q4-frontier-20260926-r01/artifacts/time_placebo/monthly_slope_placebo.csv`。这里的 exceedance fraction 只是小样本安慰剂诊断，不作为因果显著性结论。

- 综合指标排除 MATH 后，观察斜率为 0.460 分/月；置换斜率绝对值超过它的比例约 5.6%，单侧超过比例约 2.7%；
- MATH 单任务斜率为 3.194 分/月，置换单侧超过比例约 0.007%，是最强的时间结构来源；
- BBH、GPQA、MMLU-PRO 的单侧超过比例分别约 4.0%、0.1%、0.25%；
- IFEval 约 11.6%，MUSR 约 5.6%，这两项单独不足以支持稳定的单调上升。

因此，时间排序中确实包含超出随机重排的结构，但它集中在 MATH 和部分任务，不能把所有任务视为同一条同步技术进步曲线。最终模型应报告任务级斜率和留一任务敏感性，并把“技术进步项”解释为条件关联。

脚本：`scripts/q4/q4_time_placebo_test.py`。运行：

```powershell
python scripts/q4/q4_time_placebo_test.py
```
