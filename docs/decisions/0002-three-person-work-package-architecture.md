# 决策 0002：采用三条纵向工作包与三人发布委员会

日期：2026-09-24
状态：提议在架构 v2 分支合并后生效

## 决定

三名真实 Actor 分别负责 WP-A 数据与证据、WP-B 模型与优化、WP-C 验证与结果。每个工作包必须由 Owner 同时交付代码、实验和论文段，并由另一名 Actor Peer Review、第三名 Actor 作为 Release Integrator 检查包级证据。

跨包论文整合、claim ledger、全量复现和发布检查单独作为 Q1-INT/T-Q1-009。最终发布由三人 Release Council 共同签署；ACTOR-1 可以维护协调分支，但不再作为所有任务的单一最终技术签署人。

## 原因

旧架构把静态 A/B/C 角色、真实执行人和最终签署人混在一起，导致 ACTOR-1 成为所有任务的单点瓶颈；WP-C 又同时承担分析、图表和整篇论文整合。新架构把执行责任、独立复核和包级集成分开，并允许模型规格、分析脚手架和论文骨架并行准备。

## 证据门

G0 范围/数据边界，G1 数据契约与模型接口，G2 已接受模型 run_id，G3 三个工作包 PACKAGE_ACCEPTED，G4 三人发布签署。状态只能按照 `DRAFT → SPEC_READY → CODE_READY → RUNNING → RUN_COMPLETE → PEER_REVIEW → PACKAGE_ACCEPTED → INTEGRATED` 推进。

## 代价

需要维护每个工作包的独立 PR、run manifest、handoff 和 claim ledger；发布前三人都必须完成检查，不能由单个人快速代签。
