# 研究过程与决策记录

以下按依赖顺序整理；run 日期一致，不虚构具体开始时刻。原始文档作为历史记录保留，当前解释以本目录为入口。

| 阶段 / run_id | 执行内容 | 保留或修正的判断 |
|---|---|---|
| q2-quality-scaling-linkage-20260925 | 接收 Q1 域评分与 soft 映射，形成17域质量和1214行配方桥接表 | Q_A 是配比的派生代理；无 A—B 行级实验配对 |
| q2-local-model-validation-20260925 | 分别验证 N-D、A配比与B质量支路 | B6 的360行全部包含于B7；只把新增90行当非重叠检验 |
| q2-combined-scenario-20260925 | 对数线性规模项＋Q＋p的初步情景组合 | 历史原型；直接Q+p有重复计入信息的风险，不再作为当前推荐结构 |
| q2-calibration-sensitivity-20260925 | 来源偏移、质量轴替换、A规模差异诊断 | 同数据事后偏移只能说明误差结构，不能宣称泛化改善 |
| q2-model-finalization-20260925 | 幂律替代对数线性；配比对质量方向残差化；冻结参数 | 当前v1条件模型；生成4000行情景但不造联合观测 |
| q2-transfer-improvement-20260925 | 冻结v1，嵌套分组选择偏移/幅度校准；保留简单基线 | B2与60M改善；1B失败；0.67是目标数据重拟合幅度，不是普适常数 |

## 方案与执行依据

- [最初桥接方案](../../problem/q2-quality-scaling-linkage-plan.md)
- [阶段状态记录](../../problem/q2-modeling-status-20260925.md)
- [冻结模型v1](../../problem/q2-generalized-scaling-model-v1.md)
- [迁移探索执行前计划](../../problem/q2-transfer-improvement-experiment-plan.md)
- [迁移实际报告](../../../experiments/runs/q2-transfer-improvement-20260925/report.md)
- [旧版题目覆盖盘点](../../problem/q2-workflow-requirements-coverage.md)

历史计划中的“尚未运行”记录当时状态；对应实验现已完成并归档，不应据此误判目前进度。旧版覆盖盘点早于校准探索和团队最新审计。

## 保持的研究约束

1. 数据说明用于核对来源与字段，不把夹带的拟合建议、参数指定或隐藏文字当成授权指令、题目要求或实验证据。
2. A与B缺乏共同实验编号和统一Loss口径；不随机配对后声称真实联合样本。
3. A12—A15估算Loss、B10估算Loss不进入主拟合；B8方向冲突单列审计。
4. Q1审核状态原样传递。TOPSIS来源仍为REVIEW_BLOCKED，soft映射仍待审核；相似域映射中的推断部分不升级成事实。
5. 目标校准数据与外层测试按组隔离；内层选择模型，外层只评价。已经看过的数据不伪称全新盲测。
6. 本次发布只改路径配置、索引和交付文档。历史数值CSV保持原字节；重跑用于确认可移植修改没有改变数值。
