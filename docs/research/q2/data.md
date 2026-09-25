# 研究数据、字典与来源

[文件级CSV目录](file_inventory.csv)列出所有发布表的行列数与SHA256；[逐列字典](column_dictionary.csv)列出各CSV的列名、读取类型、缺失数和用途提示；[输入清单](../../../data/manifests/q2_research_inputs.json)记录受控原始数值文件及Q1依赖的哈希。原始文件不随公开包上传。

## 数据身份

| 数据块 | 内容与本包用途 | 不能作出的推断 |
|---|---|---|
| Q1输出 | A配方17域比例、质量代理、13验证域平均Loss及来源标签 | 不等同于B的质量测量；不补出A真实D |
| A4/A5、A6/A7、A8/A9、A10/A11 | 1M训练/测试、60M测试、1B测试的配比与原表Loss | A的13域均值不是自动与B同定义的验证Loss |
| A12—A15 | 10B/70B估算配方结果，桥接表保留标签 | 不作为真实Loss主拟合或独立验证 |
| B1 | N、D、附件Loss；规模拟合和留一规模 | 附件拟合精度不代表所有实际训练任务 |
| B2 | 1029行、7条轨迹；半合成族外/校准探索 | 一条147点轨迹不是147个独立模型；校准不是零样本迁移 |
| B4/B5 | 附件的跨族/文献数值对照 | 总体指标不能替代按评估口径分层 |
| B6/B7 | N、D、Q、半合成Loss；360/450行 | B6全部包含于B7，新增仅90行 |
| B8 | 1704行，质量方向冲突诊断 | 不并入主质量拟合；冲突不自动证明投毒 |
| 情景表 | 明示假设下组合N、D、Q、p，输出预测Loss | 4000行不是4000个真实联合实验 |
| 校准预测表 | 各候选模型与选择模型的外层预测、actual和分组 | 9945条预测记录包含重复评价同一来源行，不能当独立样本数 |

B3、B9/B10等团队审计入口见 [PR #23](https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/23)。本包没有复制原始题目或数据说明中的指令文本。

## 主要字段

- `N_params_B`：参数量，十亿参数；`D_tokens_B`：训练token量，十亿token。
- `p_*`：17域归一化配比，处于单纯形；增加一个域须减少其他域。
- `Q_A_topsis_0_1`：Q1域TOPSIS分经映射与配比加权的代理，无量纲。
- `quality_score_soft_proxy_0_1`：另一套soft质量代理，无量纲；与TOPSIS定义、排序不同，不可直接互换。
- `Q_score`：B半合成实验的质量控制分数，无量纲；不是已校准的Q_A同尺度测量。
- `quality_provenance`、`mapped_share_direct_near_direct`：映射来源和直接/近直接覆盖份额，不是统计置信度。
- `loss_observed`：A原表Loss的观测/估算身份；`loss_mean_13_domains`是其13验证域均值。
- `dataset, role, scale, index`：来源及来源内标识；不能跨A/B直接使用index连接。
- `actual, predicted`：验证表中的来源目标值和模型预测；半合成来源的actual仍为半合成值。
- `source_id, group, fold`：来源行、分组、外层折；应与task/branch/axis/model组合识别，不能只按source_id去重。
- `q_frozen, x_frozen, intercept, slope`：冻结的质量与形状输入、折内校准参数，支持预测重建。
- `selected`：由内层证据选择的预测；`full_target_refits`是全部目标数据重拟合，不用于报告留出性能。
- `observed_joint_row`及情景标签：防止将预测当观测使用；以实际表字段为准。

## 数据版本约束

本包Q1输入与main同名文件数值一致；soft的两张表在旧工作区与main存在换行差异。旧run manifest保留历史输入/脚本哈希，发布清单记录移植后的脚本哈希，二者用途不同。源文件来自旧工作树（基于f5de761），不声称当时这些研究文件已经提交到该commit。

研究表按字节保留；38张表通过数值重跑对比。历史quality-direction-audit.csv为早期独立诊断，未在一键脚本重建，相关方向结论同时由局部模型审计支撑。不得把缺失的A训练量、配对编号或B配比补成“实测字段”。
