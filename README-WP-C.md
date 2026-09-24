# WP-C 问题一第二小问本地交付

Owner：ACTOR-3；Peer Reviewer：ACTOR-1；Release Integrator：ACTOR-2。分支`wp/ACTOR-3/WP-C`，对应T-Q1-005～008。本次是本地Git提交，不推送远端，不合并main。

## 文件入口

- [交付目录](docs/tasks/WP-C-final-directory.md)
- [冲突定义、成因与结果](docs/decisions/q1-conflict-analysis.md)
- [候选消解模型建议](docs/decisions/q1-resolution-proposal.md)
- [验证报告](docs/decisions/q1-validation-report.md)
- [角色交接](docs/tasks/WP-C-delivery.json)
- [Markdown和LaTeX草稿](paper/sections/drafts/)
- [中文图表](paper/figures/)

代码、汇总表、配置、图表、文稿和证据记录进入Git。逐样本数据、输入矩阵、案例正文及人工核验清单存放在`experiments/runs/q1-conflict-trial-20260924-r01/artifacts/`，由已有.gitignore忽略。原始附件不复制进Git。

## 核验和复现

```sh
python scripts/verify_q1_conflict_delivery.py
python scripts/q1_conflict_validation.py --self-test
```

有本地内部数据时可复现既有探索性计算：

```sh
python scripts/q1_conflict_analysis.py
python scripts/plot_q1_conflict.py
node scripts/render_q1_conflict_figures.mjs
```

Python依赖见requirements-q1-conflict.txt。绘图使用支持中文的TrueType字体，可通过`--font`指定；Node渲染需要pdfjs-dist和@napi-rs/canvas，或通过WPC_NODE_MODULES指定已有模块目录。绘图脚本输出到运行目录figures，论文图存放paper/figures；更新图后须同步论文副本并重新核验清单。

克隆不含内部数据。如需复原矩阵，运行：

```sh
python scripts/rebuild_q1_conflict_inputs.py --raw-root /path/to/real_attachments --run-dir experiments/runs/q1-conflict-trial-20260924-r01
```

另需从团队内部数据包取得case_selection.csv；case_texts.json是案例证据附件，不参与评分。它们放在该run的artifacts目录。

## 状态与边界

已完成基本探索性冲突计算、候选综合评价、阈值/偏好敏感性、分层汇总、中文图表和章节源码。保留REVIEW_BLOCKED：没有G2通过与独立审核记录，正式bootstrap/权重扰动未执行。脚本已实现并通过合成接口测试。正式验收、模型采纳和论文整合分别依项目角色卡推进，不能把本次提交当成已通过审核。main、WP-A/WP-B原成果和正式claim ledger保持不变。

候选分不覆盖第一问原分，不宣称准确率提高或参数最优。LaTeX未编译，PDF仅为独立图表。完整私有交付包保留于本地工作区，不纳入Git。
