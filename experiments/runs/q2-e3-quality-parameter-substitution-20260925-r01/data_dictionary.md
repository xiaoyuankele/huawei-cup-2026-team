# E3 数据字典

所有新增行均为数学情景，不是新观测训练样本。N0_B、N_required_B、N_scale_equivalent_B以十亿参数计；D_B以十亿token计。QA/QB为无量纲但定义不同的评分；gain为Loss下降量。

| 文件 | 行数 | 内容 |
|---|---:|---|
| quality_path_support.csv | 2 | 每轴的LP边界、安全QA/QB增量、形式坐标余量、上界对偶价格 |
| support_weights.csv | 稀疏 | LP最优凸权重；未列train_position视为0；安全权重=0.01/512+0.99×最优权重 |
| support_duals.csv | 2 | y_0…y_16对应17配比等式，y_17对应权重和约束 |
| quality_path_curves.csv | 918 | 两轴×3N×3λQ×51个安全路径点，λp=1但残差为0 |
| quality_capacity.csv | 36 | 两轴×3N×3λQ×可行/形式两类上限 |
| expansion_targets.csv | 72 | 替代1.25/1.5/2/4倍扩参所需质量、可行性和N范围 |
| recipe_substitution.csv | 27648 | 512配方×2轴×9组λQ/λp×3N；分项和总收益、双向逆解、成本阈值 |
| recipe_summary.csv | 54 | 每轴、N、λQ、λp组的512配方描述性计数 |
| verification_checks.csv | 203 | 程序核验组；comparisons不是科研样本量 |

N_required_ratio=N_required/N0，N_scale_ratio=N_equivalent/N0；两者不是倒数。FINITE仅指有限数学解；in_B1仅指N落在B1边际区间，不是联合验证。scale_is_expansion要求正收益，负收益仍保留数学缩参解。
无有限解时N和成本留空；INFINITE_LIMIT_ONLY是仅无限N的渐近极限，BELOW_ASYMPTOTIC_FLOOR是目标低于相应Loss下界。λQ=0的目标行NO_QUALITY_EFFECT，所需质量留空。
quality_cost_ceiling_FLOPs是κ=6、D=100B假设下的允许额外成本上限；负值无非负成本空间。两个轴分开统计，计数非概率。
