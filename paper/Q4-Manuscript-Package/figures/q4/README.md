# 问题四图件包

本目录保存问题四当前统一结果的 Nature 风格图件、可编辑矢量文件和逐图源数据。图件采用 Python/matplotlib 生成，使用与仓库已有问题一至问题三图件一致的低饱和青灰—暖橙配色。

## 图件与论文位置

| 文件 | 建议放置位置 | 主要结论 |
|---|---|---|
| `FigQ4_01_frontier_validation` | 结果：数据审计与短期验证 | C8 等权 q95 的月度前沿、任务变化、类型构成，以及 70/30 短期验证的误差稳定性 |
| `FigQ4_02_12m_scenarios` | 结果：未来 12 个月情景 | 平台型/趋势型时间项和算力倍率的相对影响，以及类型比例扰动的敏感性 |
| `FigQ4_03_workflow` | 方法或结果开头 | 从投毒隔离到 C8 评分、滚动验证、分位数模型和 12 个月情景的流程边界 |

每个图件同时导出 SVG、PDF、600 dpi PNG 和 600 dpi TIFF。SVG/PDF 保留可编辑文本。`source_data/` 中的 CSV 与各面板一一对应，可用于复核或重绘。

`manifest.json` 记录本图件包 24 个文件的大小和 SHA-256 校验值，可用于投稿打包或跨机器传输后的完整性核对。

## 重现命令

在仓库根目录运行：

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/plot_q4_figures.py `
  --data-dir 'D:\F题\real_attachments\C_efficiency_evolution' `
  --run-dir 'experiments/runs/q4-system-20260926-r01' `
  --out-dir 'paper/figures/q4'
```

脚本只使用 Attachment C 的清洗榜单、详细任务分数和已保存的 Q4 实验产物；月度 bootstrap 直接读取 `q4-system-20260926-r01/artifacts/robustness/c8_equal_task_frontier_bootstrap.csv`，缺失时会显式报错，不会生成演示数据。
