# 问题一质量评分版本兼容性审计

运行号：`q1-quality-version-compatibility-20260925-r01`
任务：`T-Q1-003-MIXTURE`
状态：`LOCAL_RESULT_PENDING_TEAM_REVIEW`

## 仓库更新

远端 `origin/main` 已前进到 `aab095b`，新增了 WP-B 质量评分公开交付清单、质量评分可见性 manifest、Q1.1 论文段落和公开候选评分表。该更新没有改变 A4–A15 配比或 Loss 文件，也没有改变 A16 域映射表。

远端主仓库登记的质量评分 canonical 运行是 `q1-critic-topsis-20260924-r01`；当前配比—质量整合使用的是本地重跑 `q1-critic-topsis-20260925-r01`。两者不能因为数值一致就合并成同一个版本。

## 数值兼容性

对六个质量评分方案的 A1/full 域均分进行逐域比较，共 6 个方案 × 7 个质量域 = 42 行：

- 最大绝对差：`2.842170943040401e-14`；
- 全部差异均小于 `1e-12`；
- 主模型 TOPSIS_CRITIC 的六个可映射质量域也完全一致到机器精度。

因此，`q1-mixture-quality-integration-20260925-r01` 和 `q1-mixture-quality-baseline-20260925-r01` 不需要仅因 `origin/main` 更新而重新拟合。它们的数值结果可以与 canonical 质量域均分兼容，但仍必须保留各自的输入哈希、运行号和审核状态。

## 版本与公开边界

远端新增的 `data/manifests/q1_quality_scores_delivery.yaml` 明确了公开 Git 只保存聚合评分和 provenance，逐样本评分与归一化矩阵属于受控团队数据。当前配比—质量实验使用的逐样本评分文件仍是本地受控输入，因此不能把本地实验目录直接表述为公开数据交付。

本审计只证明两个版本在域级质量均值上的数值兼容，不证明逐样本分数、文件字节或计算环境完全相同，也不改变质量评分的 `REVIEW_BLOCKED` / `LOCAL_RESULT_PENDING_TEAM_REVIEW` 状态。

## 证据

- `experiments/runs/q1-quality-version-compatibility-20260925-r01/domain_score_version_comparison.csv`
- `experiments/runs/q1-quality-version-compatibility-20260925-r01/metrics.json`
- `experiments/runs/q1-quality-version-compatibility-20260925-r01/canonical_manifest_snapshot.yaml`
- 远端清单：`data/manifests/q1_quality_scores_delivery.yaml`
