# 提交 WP-B 的冲突消解模型建议

状态：MODEL_PROPOSAL / 未采用。Owner为WP-C ACTOR-3；拟请ACTOR-2在模型规格中审议。

## 冲突消解的综合评价候选模型

消解的对象是综合决策中的补偿规则，不是强行抹平真实差异。原分 \(Q_i^{(0)}\) 与冲突证据均保留。对组内评分器分歧不擅自判定谁正确；对语言/领域适用性疑点输出复核标记。对真实属性权衡，提出偏好权重不确定集合下的有限补偿模型，作为提交给WP-B的候选，不覆盖既有评分接口。

令 \(\Delta_5=\{p:p_g\ge0,\sum_gp_g=1\}\)，构造

\[
\mathcal W_\lambda=\{(1-\lambda)v+\lambda p:p\in\Delta_5\},\quad
Q_i^{\mathrm{cand}}(\lambda)=100\min_{a\in\mathcal W_\lambda}\sum_ga_gz_{ig},\quad0\le\lambda\le1.\tag{4}
\]

由于线性目标在单纯形上将不确定权重放到最小维度，得到

\[
M_i=\sum_gv_gz_{ig},\quad m_i=\min_gz_{ig},\quad
Q_i^{\mathrm{cand}}(\lambda)=100[(1-\lambda)M_i+\lambda m_i].\tag{5}
\]

因此

\[
100m_i\le Q_i^{\mathrm{cand}}(\lambda)\le100M_i,\qquad
Q_i^{\mathrm{cand}}-100M_i=-100\lambda(M_i-m_i).\tag{6}
\]

\(\lambda\)表示对维度偏好不确定性的保守程度，不是由人工标签估计的最优参数。取0.25仅作为展示点，比较0、0.1、0.25、0.5。固定非负权重时，每个维度上升都不会降低M和m，故候选分单调；其范围为0～100，各维度同为c时得分100c。闭式解已与五个顶点枚举核对。这种方法对所有样本连续应用，不依据离散冲突标签突然扣分，也不因为某个优点变强、冲突强度上升而降低总分。

与原16维TOPSIS的分差混合了指标集合、聚合方式及保守程度三个变化，不能全部称为“消解效果”。因此单列五维加权平均基线，只有式(6)可归因于有限补偿参数。得分变低不证明质量评价更准确。本模型仍继承指标适用性问题，正式采用前须原文标注或下游效果验证。



对应结果：experiments/runs/q1-conflict-trial-20260924-r01/results/score_summary.csv。该建议与原第一问16维TOPSIS不同，不自动覆盖其接口。
