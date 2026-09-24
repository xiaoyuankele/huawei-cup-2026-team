# WP-C 验证报告

状态：REVIEW_BLOCKED。实际完成的探索性检查与正式未运行事项分开记录。

## 已完成

- 第一问复算与七域均分核对，最大绝对差 6.89e-13。
- 272505条全量覆盖、261086唯一ID、重复指标和领域一致性。
- A1 fit/holdout、A2/A3 overlap/new以及全量去重分层。
- 五维阈值和lambda敏感性，方法间Spearman与10个百分点排名位移。
- 有限补偿模型的范围、单调性、五顶点闭式解检查。
- 83条人工核验待标注清单；15个定向案例的原文解释，不作为随机准确率验证。
- 正式验证脚本的合成接口测试通过；未据此填写真实数据区间。

## G2 后执行

`scripts/q1_conflict_validation.py`要求已接受WP-B运行记录，输出conditional_bootstrap.csv、weight_perturbation.csv、method_rank_reversal.csv。三seed为20260923/24/25；每seed bootstrap 200次；相对权重半径0.1/0.2，各20次。bootstrap固定分层计数并冻结参数；区间不代表已知目标总体，也不覆盖拟合误差。排名反转只在同一批配对文本对上定义，不能用ICC替代。

源包未提供G2通过的事实证据，故这些正式数据实验未执行。任务卡要求的完整验收尚未满足，不能标RUN_COMPLETE或PACKAGE_ACCEPTED。

## 未决边界

没有人工质量真值或下游Loss验证；lambda=0.25为展示场景而非最优解；高低分位只是相对评价；领域/语言适用性尚需标注；非有限值仅对已选16项核查；确定性模型不涉及随机优化不稳定性。LaTeX仅生成章节源码，当前环境无TeX引擎，未声称完成论文编译。

证据：experiments/runs/q1-conflict-trial-20260924-r01/validation/checks.json、synthetic_validation_tests.json及results下对应CSV。
