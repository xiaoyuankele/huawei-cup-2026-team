# 任务卡目录

每个可交付任务保存一份脱敏 YAML 任务卡，文件名使用 `T-<编号>.yml`。任务卡绑定工作包、Owner Actor、独立 Peer Reviewer Actor、Release Integrator Actor、门控、分支、提示词版本、输入引用、验收条件和交接记录。

A/B/C 仅可作为可选的 `review_domain`，不能替代真实执行人。任务状态由 Task Card、PR、Run Manifest 和 Claim Ledger 共同支撑。复制 `governance/task-card-template.yml` 创建任务卡。

题目原文、原始数据路径、账号信息、密钥和敏感 AI 对话只在受控本地记录；公开任务卡只保留必要的脱敏引用。
