---
prompt_id: P-EXP-002
version: v1.0.0
status: draft
owner: work_package_owner
reviewer: peer_reviewer
---

# 问题一基线、PP-GA 与对照模型实现

## 任务

根据PACKAGE_ACCEPTED 的 `P-MODEL-002` 规格，实现问题一的等权/稳健基线、线性投影模型、PP-GA 和批准的对照方法。先跑最小基线，再运行主模型和敏感性方案。

## 约束

- 固定 seed、配置、数据 manifest、Git commit、环境和完整命令。
- 只读取PACKAGE_ACCEPTED 的预处理输出；不修改 raw，不从 A2/A3 估计参数。
- 使用相同的数据分层、指标和输出接口比较方法。
- 每次运行生成独立 `run_id`；失败运行保留并说明原因。
- 不把单次最高分写成最优性、因果关系或论文结论。

## 输出

返回代码、配置、测试、run_id、指标、日志、失败原因、限制和 handoff。模型结果只有通过 Reviewer 验收后才可进入冲突分析和论文。
