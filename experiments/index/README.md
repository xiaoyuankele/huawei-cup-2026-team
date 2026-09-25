# 实验索引版本登记

本目录保存按交付包拆分的实验索引版本。交付分支新增实验记录时，创建一个独立的 CSV 版本文件，并在本文件登记来源、范围、哈希和审核状态；不要在交付分支直接追加共享的 `experiments/index.csv`。

## 版本规则

- 文件名：`<run_id>-v<版本号>.csv`。
- 每个版本文件保留完整表头，包含该交付包的索引记录；修订同一交付包时递增版本号，旧版本不覆盖。
- `experiments/index.csv` 是集成后的聚合快照，只在主分支的集成提交中更新。这样不同交付分支不会同时修改同一个 CSV 尾部。
- 版本文件中的 `run_id` 必须唯一；`git_commit`、`data_manifest`、`metrics` 和 PR 字段用于追溯，不能用新版本静默替换旧版本。

## 已登记版本

| version_id | table | source_commit | run_id | rows | status | PR | sha256 |
|---|---|---|---|---:|---|---|---|
| `q1-quality-mapping-soft-r02-v1` | [`versions/q1-quality-mapping-soft-r02-v1.csv`](versions/q1-quality-mapping-soft-r02-v1.csv) | `f5de761254973eeed30b13b887700ce62a966dbb` | `quality-mapping-20260925-r02-soft-handoff` | 1 | `REVIEW` | [#24](https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/24) | `ace6b70e48211182134e69fbd589b2eeb26fcb323d4cb876755f50fa763fc8a1` |

## PR #24 的集成说明

PR #24 的数据交付记录已经从共享聚合表拆出，独立保存在上面的 v1 版本中。合并时应保留当前 `main` 的 `experiments/index.csv`，再由主分支集成提交按本登记表追加或重新生成该记录；不要使用整文件 `ours` 或 `theirs` 覆盖另一侧。
