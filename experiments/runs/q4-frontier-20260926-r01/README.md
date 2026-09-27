# q4-frontier-20260926-r01

状态：`REVIEW`，等待 Owner 和 Reviewer A 对数据角色、模型口径和外推结论进行人工复核。此运行包含问题四已完成的探索性基线、条件分位数、任务级、安慰剂、Loss 桥接及算力情景实验。

从仓库根目录按 `command.txt` 运行。附件 C 放在被 Git 忽略的 `data/origin/C_efficiency_evolution`，或使用 `--data-dir` 指定本地位置。`scripts/q4/hash_inputs.py` 用于核对 `data/manifests/q4_attachment_c.yaml`；逐模型输出写入被忽略的 `artifacts/`。公开仓库只保留 `metrics/` 下的聚合指标和脱敏运行日志。

主要结果：详细 C8 95% 分位完整模型在 2024→2025 时间外测试的 pinball loss 为 0.559、经验覆盖率为 96.4%；月度 C8 前沿只有 7 个滚动测试点。12/24 个月输出是平台型与延续趋势型情景，尚无可验证的长期预测误差。算力弹性来自问题三探索性输出，训练数据量和训练算力在当前 C8 主模型中不可用。

`docs/research/q4/` 保存完整研究说明。模型级结果、原始附件、题面和详细逐任务 JSON 不进入 Git。分位数模型的普通 R² 只作辅助，主比较使用 pinball loss 与覆盖率。
