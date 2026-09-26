# 提示词注册与调用规范

`governance/prompts/registry.csv` 是规范提示词目录，`governance/prompts/catalog/` 保存可公开模板，`governance/prompts/runs/` 保存实际调用元数据。

- `prompt_id@version` 代表一个稳定模板；模板不绑定固定 A/B/C 人员。
- 注册表中的 `owner`/`reviewer` 只表示 `work_package_owner` 和 `peer_reviewer` 这类通用责任，不表示具体成员。
- 任务卡必须额外记录 `owner_actor`、`peer_reviewer_actor` 和 `release_integrator_actor`。
- 每次真实调用生成唯一 `prompt_run_id`，并回链 `task_id`、`work_package`、设备、分支、Git commit、输入摘要、输出哈希、`run_id` 和状态。
- Peer Reviewer 只能独立检查；Release Integrator 负责包级证据、接口和 claim ledger 回链；二者都不能代替 Owner 修改结果。
- 题目原文、原始数据、敏感对话、密钥和未公开结果不能进入公开模板或 Prompt Run。

## 目录

```text
governance/prompts/
├── registry.csv
├── catalog/
│   ├── P-*.md
│   └── README.md
└── runs/
    ├── README.md
    └── PR-*.yml
```

## 最低记录

每次调用至少记录：`prompt_run_id`、`prompt_id@version`、`task_id`、`work_package`、Owner/Peer Reviewer/Integrator Actor、设备、日期、AI 工具/模型/提供方、输入摘要、输出用途、代码提交号、输出文件或哈希、`run_id`、Peer Review 决定、Integrator 决定和状态。

运行失败、证据不足、方向争议或模型不一致时，先建立 `feedback_id`，任务进入 `REWORK` 或 `REVIEW_BLOCKED`，不能把聊天窗口的数字直接写入论文。
