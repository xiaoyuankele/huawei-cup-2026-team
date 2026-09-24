# WP-A 预处理修复候选

这里保存既有本地复现使用的七个文件，原始字节不变。它们不替换团队 main 的 WP-A 正式路径、任务卡或交接记录。来源运行：`q1-indicator-normalization-20260924-r02`；反馈：`FB-20260924-B-PREPROCESS-PROVENANCE`。

该运行重建的矩阵与旧 manifest 声明的矩阵哈希一致；历史元数据差异原因仍未解决。是否接受修复由 WP-A Owner 按现有独立审核流程决定。本候选不含质量总分，也不构成 WP-A 验收。

在隔离目录复现旧交付时，`scripts/prepare_q1_review_workspace.py` 将这些文件按原相对路径放入工作副本；源仓库与原始数据均不改写。
