# 研究结果与证据边界

所有结果仍待团队独立评审。历史探索和当前验证分开，不以发布动作替代科学验证。

## 当前模型及局部证据

规模项为 L = E + A N^(-α) + B D^(-β)，其中 N、D 均以十亿为单位。质量项以B7参考质量0.55为中心；配比项剔除与 Q_A 线性相关的方向，避免将同一代理信号直接相加两次。具体公式与完整参数见 [v1说明](../../problem/q2-generalized-scaling-model-v1.md) 和 [冻结参数](../../../experiments/runs/q2-model-finalization-20260925/model_parameters.json)。

| 证据 | 数据/协议 | 结果 | 来源 |
|---|---|---|---|
| 规模项 | B1留一N规模，1176行 | MAE 0.000107878，RMSE 0.000151180 | [scale_oof_summary](../../../experiments/runs/q2-model-finalization-20260925/scale_oof_summary.csv) |
| 未校准族外迁移 | B2、B4、B5 | MAE分别1.178442、0.227263、0.170722 | [scale_external](../../../experiments/runs/q2-model-finalization-20260925/scale_external.csv) |
| 质量增量 | B7按N-D分组留出 | 加Q / 不加Q：0.057322 / 0.101965 | [quality_increment_summary](../../../experiments/runs/q2-model-finalization-20260925/quality_increment_summary.csv) |
| 非重叠质量扩展 | B6拟合、B7新增90行检验 | 加Q / 不加Q：0.044603 / 0.057491 | 同上 |
| 配比同规模 | A6/A7测试 | 配比 / 均值：0.180679 / 0.225599 | [mixture_validation](../../../experiments/runs/q2-model-finalization-20260925/mixture_validation.csv) |

## 迁移探索

B2以7条完整轨迹轮流留出，内部再按轨迹选择模型；A按独特配方做外层五折、内层四折。比较原预测、偏移、非负幅度仿射和均值；内层MAE最优值5%以内优先较少参数。种子20260925。

| 任务 | 未校准MAE | 嵌套选择MAE | 相应简单基线MAE | 判定 |
|---|---:|---:|---:|---|
| B2规模迁移（1029行） | 1.178442 | 0.266023 | 0.372331 | 改善；7折均选偏移，但训练进度残差趋势仍强 |
| A60M完整配比（256行） | 1.508086 | 0.146142 | 0.167310 | 改善；4折仿射、1折偏移 |
| A1B完整配比（64行） | 3.190256 | 0.040878 | 0.039563 | 未优于均值；4折选均值 |
| A60M连接，TOPSIS轴 | 1.509793 | 0.144802 | 0.165815 | 优于仅质量基线，仍是A侧局部检验 |
| A1B连接，TOPSIS轴 | 3.180665 | 0.055111 | 0.052475 | 未优于仅质量基线 |
| A60M连接，soft轴 | 1.503859 | 0.157800 | 0.182018 | 局部改善；属于预设敏感性轴 |
| A1B连接，soft轴 | 3.203514 | 0.041079 | 0.038355 | 未优于仅质量基线 |

表源：[完整指标](../../../experiments/runs/q2-transfer-improvement-20260925/performance_summary.csv)、[决策表](../../../experiments/runs/q2-transfer-improvement-20260925/decisions.csv)、[内层选择](../../../experiments/runs/q2-transfer-improvement-20260925/model_selection.csv)。

A60M完整配比的全目标数据重拟合幅度为 **0.67114181**：在该截距＋幅度校准结构中，保留源模型约67%的配比响应幅度；它不是“模型可信度67%”，也不是广义标度律指数。实际外层折估计范围约0.6096—0.7684。质量＋剩余配比连接的对应幅度是0.63883613，两者不可混用。全目标重拟合参数用于部署候选说明，性能必须引用外层预测。见 [full_target_refits](../../../experiments/runs/q2-transfer-improvement-20260925/full_target_refits.csv)。

## 为什么仍不支持完整联合验证

- A60M检验使用A目标规模校准截距，没有验证B1规模项与A的绝对Loss能直接拼接。
- Q_A到B的Q范围映射只是训练范围min-max假设，没有成对质量测量。
- Q_A=qᵀp，A中没有独立于配比的质量干预；残差化不能创造因果可识别性。
- 目标校准需要额外标签，1B并未证明配比结构迁移；不存在已验证的通用幅度系数。
- B2偏移后残差与logD的Spearman仍约0.9961—0.9979，曲线形状问题没有消失。
- 未有统一验证口径下共同测得(N,D,Q,p,Loss)的独立留出集，整体误差和可靠预测区间尚未知。
- 分组交叉验证和小样本重复属于探索性开发证据；重复划分不等于独立重复实验。

因此可表述为“完成条件模型和分层验证，局部迁移可经校准改善”，不能表述为“完整A—B联合模型已经验证”。
