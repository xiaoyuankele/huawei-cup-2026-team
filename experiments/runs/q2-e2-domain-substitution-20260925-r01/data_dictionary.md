# E2 表与证书说明

全部表为确定性派生计算，不是观测Loss数据。

| 表 | 行数 | 内容与读取方式 |
|---|---:|---|
| substitution_support.csv | 272 | to/from索引沿冻结模型17域顺序；hull_limit为LP最优边界；safe为99%边界；pp=配比分数×100 |
| support_weights.csv | 可变稀疏证书 | 每个direction_id的最优凸权重；缺失train_position视为0；source_recipe_id用于核对A4索引 |
| support_duals.csv | 272 | y_0…y_16为17个配方等式对偶变量，y_17为权重和约束；δ上界价格见support表 |
| finite_substitution.csv | 4352 | 5个固定幅度+3个方向安全幅度×272方向×2轴；未通过99%规则的Loss列为空；此空值不是0 |
| assumption_sensitivity.csv | 4896 | 272方向×2轴×9组强度；slope_per_fraction按配比分数计，负值表示条件预测Loss降低 |
| direction_stability.csv | 136 | 保留to_index<from_index方向代表无序域对；符号分类排除λQ=λp=0；相反方向由符号取负得到 |
| interaction_witness_basis.csv | 512 | 各训练配方在17列切向见证基中的系数；d=e_i−e_k对应coef_i−coef_k；与均匀权重相加构造四角 |
| interior_interactions.csv | 4080 | 2040共享供给领域设计×2轴；I=L11−L10−L01+L00；额外组合收益=−I |
| clipping_stress_interactions.csv | 12240 | 纯顶点压力测试，基点全在A4凸包外；不得解释为支持内或经验互补 |
| verification_checks.csv | 13966 | 算术与证书检查；comparisons不是独立样本量 |

train_position 为A4筛选后0起始行号，source_recipe_id沿原CSV的index。凸包支持仅针对A4配方，不涵盖N/D的联合观测。
权重和对偶证书与冻结桥接表的SHA256绑定。预测数值保留全精度，报告为便于阅读而四舍五入。
