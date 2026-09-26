---
prompt_id: P-CONFLICT-001
version: v1.0.0
status: draft
owner: work_package_owner
reviewer: peer_reviewer
---

# 问题一冲突诊断与解释

## 任务

利用PACKAGE_ACCEPTED 的模型运行结果、指标审计和验证分层，解释指标方向冲突、尺度差异、域漂移、缺失模式、权重扰动和模型 rank reversal。

## 约束

- 区分语义冲突、测量冲突、数据漂移、同源重复和优化不稳定。
- 不能把冲突自动当噪声删除，也不能在没有证据时加入惩罚项。
- 每个解释必须回链输入文件、方法、run_id 和证据等级。
- A2/A3 的全量结果不能表述为独立来源真值。

## 输出

返回冲突分类表、影响度/敏感性指标、域分层解释、未决问题和可写入论文的证据边界。
