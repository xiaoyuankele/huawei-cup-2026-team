# E4 数据字典

所有表是范围条件情景，不是观测样本。

| 表 | 行数 | 含义 |
|---|---:|---|
| scale_extrapolation_grid.csv | 42 | N×D规模网格；Loss、对数尺度导数、总Loss弹性、B1内外标记 |
| quality_extrapolation_grid.csv | 756 | 两质量轴×3质量案例×3lambda_Q×6N×7D；质量案例区分参考、可行安全路径和形式坐标 |
| exponent_sensitivity.csv | 168 | alpha/beta±10%压力情景；不表示置信区间 |
| b9_b10_coverage.csv | 2 | 只读审计摘要的行数、范围、空单元和来源状态 |
| verification_checks.csv | 6 | 解析/数值实现核验，comparisons不是统计样本量 |

N_params_B和D_tokens_B均为十亿单位。B1支持标记只表示模型拟合边际范围。B9/B10原始逐行Loss未发布，所有情景的observed_joint_row均为false。
