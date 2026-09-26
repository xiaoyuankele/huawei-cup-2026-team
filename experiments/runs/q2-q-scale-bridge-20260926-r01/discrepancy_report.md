# 差异报告 / Discrepancy report

- run_id: `q2-q-scale-bridge-20260926-r01`
- 生成时间(UTC): 2026-09-26T02:00:36+00:00

## FEEDBACK_REQUIRED：冻结数组 `M1.fit_B6` 的标签顺序与派发声明不一致

### 事实

`experiments/runs/q2-m0-m1-20260925-r01/metrics.json` 里 `M1.fit_B6` 是裸数组：

```
[1.4892660413046754, 0.5401729882501645, 1.3167948616197847, 0.36224743500545836, 0.27905392394495887, 0.28280291348008263]
```

派发提示词 `P-Q2-001.md` 与 `governance/prompts/dispatching/README.md` 声明其顺序为
`[E, A, B, alpha, beta, G]`。**该声明与生产拟合脚本矛盾。**

唯一权威来源是生成它的脚本 `scripts/q2_m0_m1_explore.py` 第 46 行：

```python
e, a, b, g, alpha, beta = theta   # 顺序为 [E, A, B, G, alpha, beta]
```

### 证据（三重独立核对）

1. 复刻该脚本的 `fit_model(B6, quality=True)`，逐元素最大绝对差 `9.7e-17` 级，确认数组布局为 `[E, A, B, G, alpha, beta]`。
2. 真实顺序下 B6 的 SSR = `1.272273`（RMSE `0.059448`），与 `metrics.json` 自身记录的 `grouped_ND_cell_cv` RMSE `0.0512–0.0669` 量级一致；
   声明顺序下 B6 的 SSR = `5.488376`（RMSE `0.123473`），相差 `4.314` 倍，与自身 CV 记录不符。
3. 真实顺序逐行复刻已提交的 `q2-elasticity-audit-20260925-r01/tables/m1_b6_elasticities.csv`，`epsilon_Q_score` 最大绝对差 `9.7e-17`；声明顺序的最大绝对差为 `3.7e-02`。

### 影响

| 量 | 真实顺序 | 派发声明顺序 |
|---|---|---|
| G（质量项系数） | **0.362247435005** | 0.282802913480 |
| alpha（N 的指数） | 0.279053923945 | 0.362247435005 |
| beta（D 的指数） | 0.282802913480 | 0.279053923945 |

- 声明顺序把质量项系数低估 **21.9%**。
- 由于 M1 的 Loss 对 `G` 严格线性，所有 `ΔLoss` 与 `ε_q` 都按同一比例改变，因此定性结论不变、定量结论必须标明用的是哪一个 G。
- 下游 `scripts/q2_m1_sensitivity_audit.py`、`scripts/q2_q3_interface_sensitivity.py`、`scripts/q3_q_conditional.py` 使用 `["E","A","B","G","alpha","beta"]` 解包（即真实顺序），它们的**数值**是对的，但 `q2-elasticity-audit` 的 `metrics.json` `full_fit_parameters.M1_B6` 把 alpha/beta 两个标签写反了。

### 本 run 的处理

- 未修改 `metrics.json`、未重拟合、未改任何冻结数值；只在本地按真实顺序解释数组。
- 所有主结果使用真实顺序的 `G = 0.36224743500545836`。
- `tables/mapping_effect_G_sensitivity.csv` 同时给出两种 G 下的结果，便于人工核对。
- 建议由上游在修正 `metrics.json` 字段命名后再解除本条 FEEDBACK_REQUIRED。

## BLOCKED_MAPPING_SENSITIVE

候选映射之间 Loss 影响的量级差异超过 2 倍：相对降幅范围 [0.03349744528178779, 0.1218913715558075]，倍数 3.6388

如实报告差异；不得把任何单一映射写成"正确的"换算

## FEEDBACK_REQUIRED

冻结数组 M1.fit_B6 的**标签顺序**与派发声明不一致（数值未变）。真实顺序 [E,A,B,G,alpha,beta] 下 B6 SSR=1.272273，声明顺序 [E,A,B,alpha,beta,G] 下 B6 SSR=5.488376（差 4.314 倍）；真实顺序逐行复刻已提交的 m1_b6_elasticities.csv（最大绝对差 9.7e-17）。因此质量项系数应为 G=0.36224743500545836，而非派发与 README 写的 0.28280291348008263。

写入 discrepancy_report.md；本 run 按真实顺序计算并同时给出两种 G 的敏感性对照表；未修改任何冻结参数文件、未重拟合 M1、未改数据
