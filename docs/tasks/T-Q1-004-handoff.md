# WP-B 模型交付（团队架构 v2）

角色来自团队任务卡，仅用于路由职责；不据旧 B 标签断言提交人的受控 Actor 身份，不代替本人签署。

当前交付为 `PARTIAL / REVIEW_BLOCKED`。任务正式状态仍为 DRAFT；Peer Review、Integrator 和 G1 均未完成。原本地数值核对通过不等于团队签署。

- 完整交接：[WP-B-delivery.yml](WP-B-delivery.yml)
- 代码：`src/models/q1_scoring.py`；入口：`scripts/q1_score_models.py`
- 配置：`configs/q1-score-baselines.yaml`
- 主运行：`experiments/runs/q1-critic-topsis-20260924-r01/`
- 方法草稿：`paper/sections/drafts/q1-critic-topsis-method.md`
- 复现与分类：根目录 `README-delivery.md`
- PR：https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/12

复核顺序：ACTOR-3 检查模型公式、方向假设、重叠去重及适用性；ACTOR-1 检查输入接口、manifest 和主张回链。未正式验收前不将结果写入主论文。
