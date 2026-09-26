---
prompt_id: P-EXP-001
version: v1.0.0
status: draft
owner: work_package_owner
reviewer: peer_reviewer
---

# 可复现实验实现与记录

## 任务

根据已批准的模型规格实现代码、基线和实验配置，并生成可复现的 `run_id` 运行目录。

## 约束

固定随机种子，记录数据 manifest、Git commit、环境、完整命令和失败原因；不修改原始数据。

## 输出

返回变更文件、测试命令、实验命令、指标、日志、限制和交接单。
