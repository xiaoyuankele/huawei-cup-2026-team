# 问题一第三问：团队已有数据与模型索引

状态：`SUPPLEMENTAL_DRAFT`，关联 [T-Q1-003-MIXTURE](../tasks/T-Q1-003-MIXTURE.yml)。盘点基于团队 `main` 快照 `57fc793e9692b49a60c33c6d99ec10c17ffd5d76`。本页索引已有证据，不修改模型审核状态、数据契约或论文结论。机器可读模型索引见 [CSV](q1-s03-team-model-inventory.csv)；其中数值直接取自相应运行的 JSON/CSV，空白表示本索引未收录，不表示零。

## 数据与输入定义

| 配方/Loss | 行数 | 给定规模标签 S | 可用内容与角色 |
|---|---:|---:|---|
| A4/A5 | 512 | 1M | 17 域配比与 13 域 Loss；严格路线拟合 |
| A6/A7 | 256 | 1M | 同规模新配方验证；工程路线可另行登记为适配 |
| A8/A9 | 256 | 60M | 与 A6 逐行同配方；可用于配对规模差异 |
| A10/A11 | 64 | 1B | 规模与配方同时变化；多尺度路线的未见规模留出 |
| A12/A13 | 63 | 10B | 估算外推情景，不能当作独立真实实验验证 |
| A14/A15 | 63 | 70B | 与 A12 同配方的估算外推情景 |

六组共 1,214 行，但不能把重复配方计为独立配比设计。A6=A8、A12=A14 指配比矩阵逐行相同；A12/A14 的配方是 A4 配方的子集。给定规模标签 `S` 用于构造 `log10(S)` 或 `log10(S/1M)`，在缺少额外来源证明时，不自动解释成模型参数量或实际训练 token 测量值。域级 `p_i S` 也只是相应规模标签下的派生量。

每行保留原始配比和，再以 `p_i / sum(p)` 归一化，要求非负且和为 1；17 个成分只有 16 个自由度。参考坐标法删除一域；团队主要基线采用乘法零替换（epsilon=1e-4）和 16 维 Helmert-ilr 坐标。13 个 Loss 目标不能与 17 个训练域混为一谈：`nih_exporter`、`enron_emails`、`europarl`、`philpapers` 没有同名 Loss 列。

来源：[数据契约](../decisions/q1-data-contract.md)、[配比建模契约](../decisions/q1-mixture-modeling-contract.md)、[规模特征表](../decisions/q1-scale-feature-table.md)、[结构与指标审计](../decisions/q1-mixture-metrics-summary.md)。原始附件不随本摘要重复上传。

## 质量轴必须按版本分开

| 版本/来源 | 可使用内容 | 解释与兼容边界 |
|---|---|---|
| A16 原始部分映射 / v1 hard 兼容分支 | 3 个 direct、3 个 near_direct，11 个域没有直接质量证据 | 6/17 是域覆盖率，不能称 17 域真实质量已齐全；各运行保留自己的质量评分来源 |
| 团队部分质量整合 | `Q_raw=sum(mapped p_i q_i)`、`mapped_mass`、`Q_renorm=Q_raw/mapped_mass` | 使用 0–100 质量域分数；未知域不填作真实零质量；Q_renorm 只描述已覆盖部分 |
| soft v2 | 6 个直接/近直接映射不变；11 个 inferred 域用候选质量域的语义权重 | 权重是语义先验，不是实测比例或置信概率；min–max 范围不是统计置信区间；保持 `REVIEW` |
| canonical 质量运行 | `q1-critic-topsis-20260924-r01` 的域级聚合与 provenance | 0–100 分值；不能与本地 0–1 Q_proxy/Q_mapped 静默拼接；需核对公式、来源、范围、覆盖率及版本 |

团队 `q1-mixture-quality-integration-20260925-r01` 已提供 [整合宽表](../../experiments/runs/q1-mixture-quality-integration-20260925-r01/mixture_quality_integration_wide.csv)、[域贡献长表](../../experiments/runs/q1-mixture-quality-integration-20260925-r01/mixture_quality_contributions_long.csv)、[映射审计](../../experiments/runs/q1-mixture-quality-integration-20260925-r01/mapping_audit.csv) 和 [质量域参考](../../experiments/runs/q1-mixture-quality-integration-20260925-r01/quality_domain_reference.csv)。v2 另见 [交付说明](../tasks/T-Q1-004-quality-mapping-soft-r02-handoff.md) 和 [版本 manifest](../../data/manifests/q1_quality_mapping_v2_soft.json)。

固定质量域分数和映射后，Q 是 p 的确定函数，不是独立测量的因果变量。旧部分映射模型没有因 v2 发布而自动变成 v2 模型。20260924 canonical 与 20260925 重跑的域均分数值相容，也不意味着文件版本、逐样本数据或审核状态相同；见 [质量版本兼容审计](../decisions/q1-quality-version-compatibility.md)。

## 模型族与实际可回答的问题

记 `z=ilr(p)`、`x=log10(S/1M)`，`j` 表示 Loss 目标。

| 模型族 | 广义形式/特征 | 协议与可回答的问题 | 证据 |
|---|---|---|---|
| 均值、ilr-OLS、ilr-Ridge、PLS | 常数或 `a_j+b_j'z` | A4/A5 拟合与内部 CV，A6/A7 验证同尺度配比关联 | [基准报告](../decisions/q1-model-benchmark-results.md)、[脚本](../../scripts/q1_model_benchmark.py) |
| 二阶 Ridge、浅层 GBDT | 二阶 z 特征或树的非线性函数 | 测试非线性/组合预测增量；不能由系数直接认定协同机制 | 同上 |
| 部分质量 Ridge | z 加 Q_raw/覆盖率，或 Q_renorm/覆盖率/可用性 | 测试质量代理的额外预测增量 | [报告](../decisions/q1-mixture-quality-baseline-results.md)、[脚本](../../scripts/q1_mixture_quality_baseline.py) |
| 多尺度 Ridge | `a_j+b_j'z+c_j x+d_j'(z*x)` | A4+A6+A8 适配，A10 留出；A12–A15 情景诊断 | [报告](../decisions/q1-track-c-multiscale-results.md)、[脚本](../../scripts/q1_track_c_multiscale_exploratory.py) |
| 低维交互/多样性/目标级 alpha | 保留部分 z*x、熵/集中度及其交互，或目标分别选 alpha | 判断复杂特征和目标异质性是否改善迁移；协议为角色变更探索 | [低维交互](../decisions/q1-track-c-reduced-interactions-results.md)、[因素充分性](../decisions/q1-factor-sufficiency-results.md)、[目标级模型](../decisions/q1-target-specific-scale-results.md) |
| 中间尺度锚点 | 将 A10/A11 也纳入适配 | 判断额外尺度信息是否改善情景外推；A10 此时不再是留出集 | [报告](../decisions/q1-midscale-anchor-results.md)、[脚本](../../scripts/q1_midscale_anchor.py) |
| 有限配比转移效应 | `f_j(p+0.01 e_to-0.01 e_from)-f_j(p)` | 在单纯形内分析领域替代与组合预测效应的稳定性 | [报告](../decisions/q1-effect-stability-results.md)、[脚本](../../scripts/q1_effect_stability.py) |
| 配对规模差异与区间转移 | 同配方 Loss 差，按对数规模间隔比例转移 | 分离规模变化；检查低规模斜率能否转移至高规模区间 | [报告](../decisions/q1-scale-shift-transfer-results.md)、[脚本](../../scripts/q1_scale_shift_transfer.py) |

## 关键性能：先区分指标口径

团队主表 MAE 是所有样本×13 目标绝对误差的平均；RMSE 是所有样本×13 目标平方误差平均后开根号。团队 `mean_target_r2` 是 13 个逐目标 R² 的平均。

本地“先平均 13 个 Loss，再计算 RMSE/MAE”的指标衡量另一目标，允许域间误差抵消，不能与以下 pooled MAE/RMSE 直接排名。R² 越高越好；RMSE/MAE 越低越好。预测响应、质量版本、数据角色和权重应一致后才比较模型。

以下是已有严格配比基准在 A6/A7 的结果（按原报告精度展示）：

| 模型 | 平均逐目标 R² | pooled MAE |
|---|---:|---:|
| 均值基线 | -0.0125 | 0.6193 |
| ilr-OLS | 0.7635 | 0.2633 |
| ilr-Ridge | 0.7649 | 0.2626 |
| PLS | 0.6464 | 0.3133 |
| 二阶 Ridge | 0.8661 | 0.2019 |
| 浅层 GBDT | 0.8192 | 0.2307 |

来源：[q1-model-benchmark-20260924-r01](../../experiments/runs/q1-model-benchmark-20260924-r01/metrics.json)。二阶 Ridge 为该候选集同尺度预测最优；不据此认定跨尺度最优。

同尺度质量增量来自另一独立运行，不能直接拼成跨版本总排名：

| 特征块 | A6/A7 pooled MAE | A6/A7 pooled RMSE |
|---|---:|---:|
| p_only | 0.262645 | 0.346443 |
| p + Q_raw + coverage | 0.253634 | 0.337611 |
| p + Q_renorm + coverage | 0.252254 | 0.335993 |

来源：[evaluation_summary.csv](../../experiments/runs/q1-mixture-quality-baseline-20260925-r01/evaluation_summary.csv)。完整精度与其他尺度结果收录于本页配套 CSV；逐目标结果保留在原运行。

多尺度适配的关键 pooled MAE（原报告精度）：

| 模型/协议 | A10/A11 | A12/A13 情景 | A14/A15 情景 |
|---|---:|---:|---:|
| ilr + x；A4+A6+A8 适配 | 0.6182 | 0.8291 | 0.9271 |
| ilr + x + 全量交互；同上 | 0.5559 | 0.7967 | 0.9504 |
| 质量迁移/共享 alpha；同上 | 0.389 | 0.925 | 1.273 |
| 质量迁移/目标级 alpha；同上 | 0.437 | 0.903 | 1.190 |
| 质量迁移 + 1B 锚点；A10 也适配 | 不再留出 | 0.647 | 1.324 |

这些模型没有在三个尺度同时占优。证据分别在 [低维交互指标](../../experiments/runs/q1-track-c-reduced-interactions-20260924-r01/reduced_interaction_metrics.csv)、[目标级指标](../../experiments/runs/q1-target-specific-scale-20260925-r01/target_specific_summary.csv) 和 [锚点指标](../../experiments/runs/q1-midscale-anchor-20260925-r01/midscale_anchor_summary.csv)。A10 已经用于多次探索比较，不能再把当前选择后的表现称为从未查看过的确认性前瞻检验。

## 与本地规模修正方案的关系

本地 `B1/M1 + c_j log10(S/1M)` 可作为新增工程校准路线，明确 B1/M1 的质量轴版本、基础响应和 A6/A8 的校准用途。它可以检验规模均值偏差是否减少，但不覆盖团队已有二阶模型、组合效应与 pooled 逐目标评价。

团队已有直接的区间转移诊断：用 1M→60M 同配方下降量转移到 10B→70B，预测平均下降 **0.6935919500**，而题目给定估算情景下降为 **0.3829130647**；转移 pooled MAE **0.3106801847**，RMSE **0.3639253737**，13 个目标全部高估高规模区间的下降。见 [原始指标记录](../../experiments/runs/q1-scale-shift-transfer-20260925-r01/metrics.json)。因此“修正后绝对误差减少”与“恒定对数斜率不具备全区间稳定性”可以同时成立，应共同报告。

该运行记录的 A12 输入字节哈希与数据契约登记值不同；本页保留原运行 provenance，不宣称所有历史运行使用相同文件字节。报告确认配比矩阵逐行相同，但字节哈希差异仍应在需要完全复现时核对。

本次增补适合交付：模型/数据索引、可复现修正脚本、独立运行配置与哈希、两种指标聚合口径、逐目标与尺度区间诊断。保持既有官方契约、canonical 质量文件、实验版本和任务审核状态不变。公开上传遵循 [质量交付可见性清单](../../data/manifests/q1_quality_scores_delivery.yaml)：聚合证据与 provenance 可引用，原始附件与受控逐样本质量矩阵不随摘要打包。
