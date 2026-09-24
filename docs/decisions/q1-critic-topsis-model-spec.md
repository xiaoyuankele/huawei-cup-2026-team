# B 交付版本：CRITIC–TOPSIS 模型规格

选择依据：用户于 2026-09-24 明确指定 TOPSIS / CRITIC，按此前 TOPSIS_CRITIC 实现落实。规范状态：B 已实现并复核，按 v2 路由至 ACTOR-3 Peer Review 与 ACTOR-1 Integrator；不是 PACKAGE_ACCEPTED 规格。

主模型、归一化、权重、理想点、聚合公式与缺失策略见 q1-quality-evaluation-report.md 第 3–5 节，机器配置见 configs/q1-score-baselines.yaml。主运行 q1-critic-topsis-20260924-r01；PP-GA 不再作为主模型，保留历史诊断。

验收项目：A1/A2/A3 全行有评分；九个未决方向保持空列；A1 fit 独占拟合；A2/A3 重叠和新增分层；全量唯一 ID 聚合；样本分、域分、语料分可互相对账；评分范围 0–100；固定权重下逐指标单调；公开包不含完整样本明细；来源、命令、代码、配置、环境与哈希可复核。

主模型分数不以分组等权或分组 CRITIC 赋权，不使用 GA，不做质量类别聚类。负向指标与 DSIR 的适用性作为显式假设，并提供删除指标组的敏感性结果。
