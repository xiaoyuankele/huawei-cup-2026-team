# WP-B：CRITIC–TOPSIS 待审核交付

本提交从个人 fork 的 `wp/ACTOR-2/WP-B` 分支向团队主仓库 `xiaoyuankele/huawei-cup-2026-team` 的 main 发起 PR。状态为 PARTIAL / REVIEW_BLOCKED，G1、Peer Review、Integrator 未完成。真实人员与 Actor 的对应关系由受控分配记录决定，本提交不代签。

## 分类入口

| 内容 | 路径 |
|---|---|
| 质量评价报告与模型规格候选 | docs/decisions/q1-quality-evaluation-report.md；q1-critic-topsis-model-spec.md |
| 评分代码、运行和验证入口 | src/models/q1_scoring.py；scripts/q1_score_models.py；scripts/verify_q1_delivery.py |
| 实验配置与来源清单 | configs/q1-score-baselines.yaml；data/manifests/q1_scoring.json |
| 主实验的领域/语料/A1对照表、权重与图 | experiments/runs/q1-critic-topsis-20260924-r01/tables/ 和 figures/ |
| 六种方案和预处理重建的运行记录 | experiments/runs/；experiments/index.csv |
| 模型方法段候选（未接入主论文） | paper/sections/drafts/q1-critic-topsis-method.md |
| 待审核主张 | paper/claim-ledger.csv |
| 工作包交接和审核路由 | docs/tasks/WP-B-delivery.yml；T-Q1-004-handoff.md |
| WP-A 候选修复及历史来源反馈 | reference/preprocessing_refresh_candidate/；governance/feedback/ |

当前角色分工：WP-B 的 Owner 为 ACTOR-2、Peer Reviewer 为 ACTOR-3、Release Integrator 为 ACTOR-1。原报告/运行中的 B→A 标签是旧架构记录，不能替代本次 v2 审核。历史运行字节和 source commit 不追溯改写；新增 team_handoff.yaml 记录当前路由。

## 复现

模型输入依赖本地预处理修复候选。为保留团队已登记的 WP-A 成果，先从仓库根目录生成隔离工作副本（输出目录必须不存在）：

```text
python -X utf8 scripts/prepare_q1_review_workspace.py --root . --output ../q1-critic-topsis-review
```

将 B 的 `02_完整派生数据包_仅团队内部.zip` 解压到该副本，保持 data/processed 与 experiments/runs 下相对路径。完整数据包仍在本地，未通过本 PR 上传；队员需要通过受控渠道取得。公开表图可直接浏览，无需该包。然后在副本根目录运行：

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/q1_score_models.py --root . --config configs/q1-score-baselines.yaml
python -X utf8 scripts/verify_q1_delivery.py --root .
python -X utf8 scripts/plot_q1_topsis.py --root .
```

若从原始附件重建，在副本中先运行 `python -X utf8 scripts/q1_indicator_preprocess.py --root . --config configs/q1-indicator-normalization.yaml --raw-root <LOCAL_RAW_ROOT>`。原始附件只读，且不会从源仓库复制。Python 3.11 与依赖见 requirements-q1.txt。固定 run_id 用于副本复现；新研究必须另立 run_id。

## 证据与待审事项

既有验证：5 项模型性质测试、23 项数值与来源核对；独立解压复现的 7 份评分和 6 份权重文件字节一致。本次目录迁移另检验候选覆盖、工作副本和公开文件哈希。完整记录 272,505 行、去重 261,086 行，选定 16 项质量信号；另 9 项方向待核验且未入模。

主模型固定理想点 0/1，距离使用一次权重；先算样本分再按唯一 ID 聚合。模型分歧仅用于敏感性分析，不代表完成指标冲突消解。PP-GA 仅保留历史归档，整个 WP-B 尚未完成。

G1 与模型规格待审、WP-A 元数据历史差异未结案，均已登记反馈。正式任务状态和主论文不提升为已接受。delivery_file_manifest.json 保留历史压缩包证据；submission_manifest.json 是本次团队提交路径及哈希清单。

## 数据可见性与交接

质量评分的公开证据已经按运行目录整理：主实验的 `domain_scores.csv`、`corpus_scores.csv`、`full_vs_A1.csv`、`extended_vs_A1.csv`、`model_weights.csv`、`indicator_parameters.csv`、`model_sensitivity.csv` 和跨模型领域对照表位于 `experiments/runs/q1-critic-topsis-20260924-r01/tables/`，运行参数、输入哈希和验证记录位于同一 run 的元数据与 `data/manifests/q1_quality_scores_delivery.yaml`。这些聚合表覆盖 A1=51,230、A2=17,523、A3=203,752 条记录（全量 272,505 行，去重后 261,086 个 ID）。

完整的归一化矩阵和逐样本分数不进入公共 Git。受控团队包 `02_完整派生数据包_仅团队内部.zip` 共 8 个文件、98,499,927 bytes，SHA256 为 `A027356B2354CF6F4D396DE9208DF870FEF3810870534163B50F4B9F55591ED5`，通过团队受控渠道交接；包内文件级哈希记录在 `data/manifests/q1_quality_scores_delivery.yaml`。这一边界遵循 `docs/tasks/WP-B-delivery.yml`、`governance/prompts/catalog/P-DATA-001.md` 和 `docs/architecture.md`，不要使用 `git add -f` 绕过 `.gitignore`。

该受控包的计算来源提交为 `3c7d3512301df6899d293e69a856027c7a4c530b`；本次公开交付以 WP-B 提交 `80b163a16075d4e947b19b400ce1f6515e200c6b` 为基线，随后补充交付文档和图表，二者关系和审核状态均保留在交付清单中。当前状态仍为 `REVIEW_BLOCKED / PARTIAL`，需团队审核后再提升状态。

团队 PR：https://github.com/xiaoyuankele/huawei-cup-2026-team/pull/12
