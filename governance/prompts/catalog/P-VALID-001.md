---
prompt_id: P-VALID-001
version: v1.0.0
status: draft
owner: work_package_owner
reviewer: peer_reviewer
---

# 问题一验证与稳健性分析

## 任务

对PACKAGE_ACCEPTED 的 Q1 模型进行 A1 内部留出、A2/A3 重叠子集、新增子集和重复种子/Bootstrap 稳健性评估。

## 约束

- 所有变换参数沿用 A1 fit；不得重新拟合外部集。
- A2/A3 结果按 overlap_with_A1 分层，不能写成独立真值验证。
- 根据配对结构选择 Pearson、Spearman、Kendall、排名重合、误差和稳定性指标；没有定义基础的 ICC 不得使用。
- 报告不确定性、样本依赖、失败运行和证据限制。

## 输出

返回可复现验证脚本、分层结果表、稳定性摘要、限制、feedback_id（如有）和 handoff。
