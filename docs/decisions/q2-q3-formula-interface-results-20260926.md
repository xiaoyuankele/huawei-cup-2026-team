# 问题二多套广义标度律与问题三接口

运行号：`q2-q3-formula-interface-20260926-r01`  
状态：`FORMULA_INTERFACE_REGISTERED`

问题二目前不是只有一个公式。它们对应不同的数据角色，不能把所有参数直接拼成一个统一公式。

## 1. 公式梳理

### M0：B1 经典 N–D 标度律

\[
\widehat L_{M0}(N,D)=E+A N^{-\alpha}+B D^{-\beta}.
\]

参数来自 B1/Pythia：

\[
E=1.689798,\quad A=0.353980,\quad B=1.240306,
\quad \alpha=0.339977,\quad \beta=0.279878.
\]

这是问题三的主基线。它只描述 (N,D) 对 B1 Loss 的响应，不能自动推广到其他数据源。

### M1：B6/B7 条件质量标度律

\[
\widehat L_{M1}(N,D,Q_B)=E+A N^{-\alpha}+B D^{-\beta}+G(1-Q_B).
\]

参数来自 B6：

\[
E=1.489266,\ A=0.540173,\ B=1.316795,
\quad G=0.362247,\quad \alpha=0.279054,\quad \beta=0.282803.
\]

其中 (Q_B) 是 B6/B7 原生 `Q_score`，支持范围为 `[0.1,1.0]`。它可以进入问题三的质量条件优化，但不能改名为问题一的质量分数。

### A 侧配比响应面

问题一还给出了：

\[
\widehat L_A=f_s(p),
\]

其中 (p) 是 17 维组成向量，候选模型包括 ilr-OLS、ilr-Ridge、二阶 Ridge 和浅层 GBDT。它描述 A 侧配比与 A 侧 Loss 的关系，不是 B 侧的 (L(N,D)) 公式。

问题三目前只能把已观测 (p) 作为离散策略标签，逐个配比报告对应的 (N,D) 资源分配，不能把 (p) 的系数直接写入 M0 或 M1。

### M2：配比到质量的条件接口

\[
Q_A(p)=\sum_{j=1}^{17}p_jq_j.
\]

当前还要保留 `mapped_mass`、未映射区间和软映射区间。(Q_A) 是 Q1 侧 `0–100` 候选尺度，不等于 M1 的 B6 `Q_score`。

### M3：四量条件公式

\[
\widehat L_{M3}(N,D,Q_A(p))
=E+A N^{-\alpha}+B D^{-\beta}
+G_{\mathrm{bridge}}[1-Q_A(p)].
\]

它是题意要求的四量接口规格，但 (G_{\mathrm{bridge}}) 目前不可识别，且 Q1 与 B6 的尺度尚未校准，A 与 B 也没有逐行或批次级连接键。因此 M3 不能作为正式问题三目标函数启动。

## 2. 与问题三的实际连接

问题三的成本约束为：

\[
C_{\mathrm{base}}=10^{18}ND(6+\eta L_{ctx}),
\]

其中 (η=2\times10^{-4})，(L_{ctx}) 来自 C7。若采用 B6 质量条件，还增加：

\[
C_Q=D\times10^9[g(Q_B)-g(Q_0)].
\]

因此当前可以执行三条接口路径：

| Q3 路径 | 目标函数 | 接入的 Q2 公式 | 状态 |
|---|---|---|---|
| Q3-ND | 最小化 (M0(N,D)) | M0 | 已执行 |
| Q3-Q | 最小化 (M1(N,D,Q_B)) | M1 | 已执行 |
| Q3-P | 对观测 (p) 逐个运行 N-D 资源分配 | (f_s(p))、(Q_A(p)) 作为情景信息 | 已执行 |
| Q3-M2-sensitivity | 固定 M2 假设质量值后运行 M1 的 N-D 分配 | 部分映射、重归一化、区间情景 | 已执行，条件情景 |
| Q3-Joint | 最小化 (M3(N,D,Q_A(p))) | M3 | 阻断 |

已有 Q3 结果对应：

- Q3-ND：15 个 N-D 场景；
- Q3-Q：45 个质量条件场景；
- Q3-P：90 个离散配比—N-D 面板行。
- Q3-M2-sensitivity：1,350 个配比—接口—预算情景行；其中 Q1 到 B6 的尺度变换仍是假设。

## 3. 当前不应做的连接

- 不能把 M0 和 M1 的参数平均或拼接成一套新参数；
- 不能把 Q1 的 `0–100` 分数直接代入 B6 的 `[0.1,1.0]` 质量成本；
- 不能把 A 侧 (f_s(p)) 与 B1 Loss 相加后声称得到联合 Loss；
- 不能用 (N,D) 数值相同代替 A-B 行级连接键；
- 不能把 B8 的反向质量方向并入 M1；
- 不能把 M3 的 (G_{\mathrm{bridge}}) 当成已拟合参数。

## 4. 下一步接口实验

下一步不是直接拟合 M3，而是先做一个**接口敏感性矩阵**：

1. M0 固定基线；
2. M1 使用 B6 原生 (Q_B)；
3. M2 使用 A 侧 (Q_A(p)) 的部分映射、重归一化和区间情景；
4. 对每种情景比较 (N^*,D^*,Q^*)、质量成本占比和预算活跃边界；
5. 只在 Q1–B6 的尺度校准和 A-B 桥接证据补齐后，再考虑 M3。

接口登记表见 [formula_registry.csv](../../experiments/runs/q2-q3-formula-interface-20260926-r01/formula_registry.csv)、[parameter_registry.csv](../../experiments/runs/q2-q3-formula-interface-20260926-r01/parameter_registry.csv) 和 [q3_interface_contract.csv](../../experiments/runs/q2-q3-formula-interface-20260926-r01/q3_interface_contract.csv)。

该敏感性矩阵已执行，结果见 [q2-q3-interface-sensitivity-results-20260926.md](q2-q3-interface-sensitivity-results-20260926.md)。其中 Q1 `0–100` 到 B6 `[0.1,1.0]` 的换算只作为显式的未经验证情景，不改变 M0/M1 原生结果，也不解除 M3 阻断。
