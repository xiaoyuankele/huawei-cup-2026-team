# E1 条件分析草稿（未验收）

task_id: T-Q2-E1-MARGINAL；状态 DRAFT / REVIEW_BLOCKED。
不得作为已接受实验进入正式论文。对应 Q2-E1-SCALE、QUALITY、DIRECTION、STRUCTURE 四条候选主张。

冻结模型为
\[
L=E+AN^{-\alpha}+BD^{-\beta}+c\lambda_Q[T(Q_A)-T(Q_{A0})]+\lambda_p w^\top r,
\quad Q_A=q^\top p,\quad r=p-p_0-v(Q_A-Q_{A0}).
\]
在保持其他输入不变时，规模边际收益为
\(U_N=\alpha AN^{-\alpha-1}\)、\(U_D=\beta BD^{-\beta-1}\)，
完整 Loss 弹性为 \(\varepsilon_N=-\alpha AN^{-\alpha}/L\)、\(\varepsilon_D=-\beta BD^{-\beta}/L\)。
这些是冻结函数的条件导数。N、D 的单位分别为十亿参数和十亿 token。

参考 N=1、D=100、训练平均配方时，预测 Loss 为 2.385578，N/D 弹性为 −0.050447/−0.040100。
11 张数值表已独立重跑得到相同字节；数值核验不提供新的训练观测。
质量截断点采用单侧导数；非正质量坐标或不可微点的对数弹性不定义。
136 个无序领域对中，12 个方向随质量评分轴改变；这属于局部模型敏感性，不是领域替代/互补的实证结论。
9216 个预设情景中，N/D 原始边际收益相同，反映可加结构未表达质量、配比与规模的交互效应。

联合观测缺口、质量代理量的量纲/原点依赖、局部方向支持和外推风险均未因此消失。
推导与原始结果见[实验报告](../../../experiments/runs/q2-e1-marginal-elasticity-20260925-r01/report.md)，
图见[规模敏感性](../../../experiments/runs/q2-e1-marginal-elasticity-20260925-r01/figures/E1_scale_sensitivity.pdf)和[质量/配比敏感性](../../../experiments/runs/q2-e1-marginal-elasticity-20260925-r01/figures/E1_quality_mixture_sensitivity.pdf)。
证据索引见[claim ledger](../../claim-ledger.csv)；合规限制见[审计记录](../../../docs/research/q2/E1-governance-audit.md)。
