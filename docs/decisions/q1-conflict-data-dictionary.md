# 逐样本字段说明

`sample_results.csv.gz`为唯一ID表，`record_index.csv.gz`为272505条原文件成员表。A1的split才表示训练/留出；A2/A3的同名值仅是相同ID哈希规则的输出，不能解释为扩展训练集。

| 字段 | 含义和范围 |
|---|---|
| id / dataset / domain | ID；首次保留的来源；领域。完整来源以record_index为准 |
| split | A1 fit或holdout；仅A1用于拟合 |
| Q_original | 第一问16维CRITIC–TOPSIS，0～100 |
| value / expression / cleanliness / no_ads / nonrepetition | 五维分数，0～1 |
| class | conflict / positive_only / negative_only / middle |
| conflict_strength / conflict_breadth | 超阈强度与维度对广度，不是概率 |
| high_dimensions / low_dimensions | 以竖线分隔；空串表示集合为空，不是数值缺失 |
| education_disagreement | 两种教育分一高一低的独立标签 |
| ad_classifier_positive / value_ad_tradeoff | 分类器偏向广告；高内容价值与广告判别并存，均非人工真值 |
| domain_applicability_review | arxiv或github领域适用性待审，不是已确认错判 |
| case_language_review | 两个已查看外语案例的标记，不是全量语言识别 |
| review_required | 任一候选冲突、教育分歧或适用性标记为真 |
| Q_core_mean / Q_core_min | 五维加权平均及最小维度分，均乘100 |
| Q_candidate | lambda=0.25的有限补偿候选分，0～100 |
| delta_vs_core / delta_vs_original | 候选分减五维平均/原TOPSIS；两者含义不同 |
| Q_scenario_low / Q_scenario_high | lambda=0.5/0.1场景分，不是置信区间 |
| Q_applicability_scenario | github暂不考虑表达与整洁度的替代场景，其他域同候选分，不是正式修复 |
| rank_original_pct / rank_candidate_pct | 全量唯一ID中的升序百分位，越高排名越好 |
| rank_shift_pct | 候选百分位减原百分位，正值表示相对上升 |
| score_status | candidate_not_validated，未经标签或下游验证 |

所有汇总rate为0～1；报告表格若标%则已经乘100。数据保留全部唯一ID，没有因冲突剔除行。
