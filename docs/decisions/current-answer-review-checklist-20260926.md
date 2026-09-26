# 当前问题回答检查清单

用途：供团队逐项核对当前问题一、问题二、问题三的模型、数据、证据和结论边界。

## 一、总状态

| 问题 | 当前状态 | 可以报告的内容 | 主要阻断项 |
|---|---|---|---|
| 问题一 | `REVIEW / CONDITIONAL` | 指标预处理、质量候选分数、17 域配比建模、离散配比候选 | 质量映射仍有 inferred 域；Q1 评分尚未升级为跨来源真值 |
| 问题二 | `CONDITIONAL_COMPLETE` | M0、M1、弹性、验证、外推和 B8 排除证据 | A-B 无逐行键；M3 的桥接系数不可识别 |
| 问题三 | `CONDITIONAL_ANSWER_PACKAGE_REVIEW` | N-D 基线、原生 Q 条件优化、p 情景、M2 接口敏感性 | 正式四量联合模型和跨域最优配比不可识别 |
| C8 截断处理 | `RESOLVED_FOR_CURRENT_Q3` | 4 个截断 JSON 已审计并剔除 | 若将来用于问题四，需使用有效子集并单独说明缺失 |

## 二、问题一目前回答了什么

### 已完成

- 构造了 17 维配比向量 (p)，并检查单纯形约束：(p_j\ge0)、(sum_jp_j=1)；
- 比较了 ilr/Ridge、二阶 Ridge 等配比响应模型；
- 形成了 Q1 侧候选质量分数 (Q_A(p))；
- 对域映射、c4 分支、部分映射和区间映射做了敏感性分析；
- 选出 6 个已观测配比候选：`46, 97, 170, 186, 270, 323`。

### 当前可报告

- A 侧不同配比候选的相对 Loss 情景；
- 配比模型表示和零替换参数变化下的排序稳定性；
- (Q_A(p)) 的部分映射、重归一化和区间范围。

### 当前不可报告

- 17 个域全部已经获得真实质量标签；
- Q1 分数就是 B6 `Q_score`；
- 某一个配比是跨 A-B 的全局最优配方；
- 配比对 B 侧 Loss 的独立因果效应。

主要文件：

- `docs/decisions/q1-p-recipe-results.md`
- `docs/decisions/q1-p-stability-results.md`
- `docs/decisions/q1-quality-mapping-gate.md`
- `experiments/runs/q3-p-conditional-20260925-r01/tables/p_candidate_summary.csv`

## 三、问题二目前回答了什么

### M0：B1 主标度律

```text
L_M0(N,D) = E + A*N^(-alpha) + B*D^(-beta)
```

参数：

```text
E     = 1.68979756
A     = 0.35398032
B     = 1.24030558
alpha = 0.33997658
beta  = 0.27987813
```

作用：回答 B1 数据内部的模型规模、训练数据量与 Loss 的关系，并作为问题三 N-D 基线。

### M1：B6/B7 条件质量标度律

```text
L_M1(N,D,Q_B) = E + A*N^(-alpha) + B*D^(-beta) + G*(1-Q_B)
```

参数：

```text
E     = 1.48926604
A     = 0.54017299
B     = 1.31679486
G     = 0.36224744
alpha = 0.27905392
beta  = 0.28280291
```

作用：回答 B6/B7 半合成条件下质量分数与规模变量的关系，并作为问题三 Q 条件优化目标。

### 已完成的验证与诊断

- M0 分组留出 (R^2\) 约 `0.9999992--0.9999998`；
- M1 分组 N-D 验证 (R^2\) 约 `0.9526--0.9705`；
- B2/B3、B4/B5 保留为族外、跨族和文献诊断，不直接混入 M0/M1 主拟合；
- B8 完成来源、方向和嵌套关系审计，排除主拟合；
- B9/B10 只用于大规模外推边界讨论。

主要文件：

- `docs/decisions/q2-m0-m1-results.md`
- `docs/decisions/q2-claim-boundaries.md`
- `docs/decisions/q2-b8-provenance-results.md`
- `experiments/runs/q2-m0-m1-20260925-r01/metrics.json`

## 四、问题三目前回答了什么

### 1. N-D 基线优化

目标：

```text
min L_M0(N,D)
subject to 1e18*(6 + eta*Lctx)*N*D <= C
```

其中：

```text
eta = 2e-4
C   = 1e19, 1e22, 1e24 FLOPs
Lctx = 2048, 4096, 8192, 32768, 131072
```

已回答：预算和上下文长度如何改变最优 (N,D)，以及何时触及 B1 支持边界。

### 2. 原生 Q 条件优化

目标：

```text
min L_M1(N,D,Q_B)
subject to C_ND + C_Q <= C
```

已比较：指数、幂函数、对数渐进三类质量成本，以及不同 (Q_0) 情景。

已回答：质量投入如何与模型规模、训练数据量竞争预算。

### 3. p 条件情景

将 6 个观测配比候选与 15 个 N-D 预算—上下文场景并列组合，共 90 行。

已回答：不同已观测配比策略可以和哪些资源配置情景并列比较。

没有回答：跨 A-B 的最优配比。

### 4. M2 接口敏感性

将部分映射、重归一化和区间低/中/高情景传入 Q3，共 1,350 行。

已回答：质量接口假设变化是否会改变 (N^*,D^*)、Loss 和质量成本占比。

限制：Q1 `0--100` 到 B6 `[0.1,1.0]` 的转换是情景假设，不是观测校准。

主要文件：

- `docs/decisions/q3-answer-package-20260926.md`
- `docs/decisions/q2-q3-interface-sensitivity-results-20260926.md`
- `experiments/runs/q3-nd-baseline-20260925-r01/tables/q3_nd_baseline_scenarios.csv`
- `experiments/runs/q3-q-conditional-20260925-r01/tables/q3_q_conditional_scenarios.csv`
- `experiments/runs/q2-q3-interface-sensitivity-20260926-r01/tables/m2_q3_fixed_q_scenarios.csv`

## 五、理论 M3 当前状态

提出了可退化到 M0/M1 的假设模型：

```text
z(p)   = ilr(p)
M_p(p) = exp(theta^T*(z(p)-z(p0)))
L_H    = E + A*N^(-alpha) + B*(D*M_p(p))^(-beta) + G*(1-Q)
```

当前用途：

- 说明配比可以被解释为有效数据效率；
- 设计后续联合实验；
- 做假设参数和尺度转换敏感性。

当前不能做：

- 不能将 (G)、(	heta) 写成正式拟合参数；
- 不能识别 Q1 与 B6 的共同质量尺度；
- 不能声称得到正式跨 A-B 四量联合最优解。

主要文件：

- `docs/decisions/q2-q3-hypothetical-m3-theory-model-20260926.md`
- `docs/decisions/q3-fallback-solution-strategy-20260926.md`

## 六、你检查时建议优先核对的项目

1. M0/M1 参数是否与 `metrics.json` 完全一致；
2. B1、B6、C7 的数据角色和样本量是否写清楚；
3. `Q_B` 是否始终与 Q1 的 (Q_A(p)) 区分；
4. 所有 M2 结果是否标注为假设情景；
5. 高预算下的支持域边界是否被误写成全局最优；
6. (L_{ctx}^{crit}=30000) 是否覆盖 8192 与 32768 两侧；
7. p 是否被错误地加入 B1/B6 的连续目标函数；
8. B8、C8 截断文件和投毒文本是否被错误写入主结论；
9. M3 是否被写成“拟合完成”，而不是“理论接口/条件模型”；
10. 最终正文中的每个数值是否能回链到脚本和运行记录。
