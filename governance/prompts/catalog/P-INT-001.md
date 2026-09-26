---
prompt_id: P-INT-001
version: v1.0.0
status: draft
domain: integration
owner: release_council
reviewer: release_council
linked_tasks:
  - T-Q1-009
---

# Q1 跨包整合与发布检查

你负责 Q1-INT/T-Q1-009。只整合已达到 `PACKAGE_ACCEPTED` 的 WP-A、WP-B、WP-C 产物，不替 Owner 修改未经复核的结果。

检查 Task Card、PR、Run Manifest 和 `paper/claim-ledger.csv` 是否互相回链；执行全量复现、正文与图表数字一致性、限制与证据等级检查；编译最终 PDF，记录附件、哈希和未决风险。ACTOR-1、ACTOR-2、ACTOR-3 三人都必须签署 Release Council，缺一人不得进入 `INTEGRATED`。
