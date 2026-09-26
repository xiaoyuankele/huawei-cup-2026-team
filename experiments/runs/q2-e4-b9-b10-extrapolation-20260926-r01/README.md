# E4：B9/B10 百亿以上外推审计

run_id: q2-e4-b9-b10-extrapolation-20260926-r01；结果为范围条件外推，保持 REVIEW_BLOCKED。

报告：report.md；数据字典：data_dictionary.md；配置：../../../configs/q2-e4-b9-b10-extrapolation.json；执行计划：../../../docs/research/q2/E4-plan.md。

复现：python scripts/q2_e4_b9_b10_extrapolation.py --output-dir ../q2-e4-rerun；python scripts/q2_verify_e4.py --rerun-dir ../q2-e4-rerun；python scripts/plot_q2_e4.py --run-dir ../q2-e4-rerun。

B9/B10估算Loss没有加载，不能当独立验证。

发布：[Draft PR #38](https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/41)，分支 wp/ACTOR-2/WP-B。保持 REVIEW_BLOCKED，未合并。
