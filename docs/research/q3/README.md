# 问题三阶段性研究交付

task_id: T-Q3-RESEARCH-HANDOFF · run_id: `q3-frozen-q2-exploration-20260925-r01` · 状态：**REVIEW_BLOCKED / EXPLORATION_ONLY**。

冻结问题二 v1 后完成 1,200 个原模型情景和 3,492 个额外提质情景。数值求解可复核，但配比边界、质量成本坐标和跨规模迁移尚未支持最终资源推荐。

- [结果及完整限制](results.md)：正结果、负 Loss、回溯 regret、成本转折与给 Q2 的反馈。
- [实验架构](process.md)：两层实验、求解流程及题目覆盖。
- [输入和字段](data.md)：上游版本、成本坐标、原始数据边界。
- [复现](reproduce.md)：独立目录重跑及结果比较。
- [交接](handoff.md)：评审接口和未闭环事项。
- [候选论文段](../../../paper/sections/drafts/q3-exploratory-results.md)：DRAFT，未接入正式论文。

核心证据：4,000 行 Q2 预测最大重建差 8.88e-16；48 个代表情景多起点全变量复核，最优值最大差 5.23e-12。数值正确不等于目标模型在推荐点可信。所有情景均不作为拟合标签。
