# Q3 新增正文图 QA

本文件记录 Fig06–Fig13 的生成和导出检查。图件由 `plot_q3_missing_figures.py` 使用仓库冻结的 Q3 条件实验表生成，未重新拟合模型。

## 源码检查

命令：

```powershell
python C:/Users/29717/.codex/skills/nature-figure/scripts/validate_figure.py --json paper/figures/q3/plot_q3_missing_figures.py
```

结果：19 PASS、1 WARN、0 FAIL，`ready=true`。WARN 为静态检查器对数学上标 `$Q^*$` 可能缩小字形的保守提示；PDF 字体审计没有发现低于 5 pt 的实际文本运行。

## PDF 字体检查

```powershell
python C:/Users/29717/.codex/skills/nature-figure/scripts/audit_pdf_text.py --min-pt 5.0 <figure>.pdf
```

| 图件 | 最小实际字级 | 低于 5 pt | 结果 |
|---|---:|---:|---|
| Fig06_M0_budget_context | 6.20 pt | 0 | PASS |
| Fig07_M1_quality_tradeoff | 5.11 pt | 0 | PASS |
| Fig08_Q0_cost_robustness | 5.11 pt | 0 | PASS |
| Fig09_parameter_uncertainty | 5.11 pt | 0 | PASS |
| Fig10_discrete_pareto | 6.20 pt | 0 | PASS |
| Fig11_p_candidate_panel | 6.00 pt | 0 | PASS |
| Fig12_M2_interface_heatmap | 5.04 pt | 0 | PASS |
| Fig13_identifiability_interface | 6.20 pt | 0 | PASS |

## 版式检查

- 画布按 183 mm 正文宽度导出。
- PDF 和 SVG 保留可编辑文字；PNG 为 500 dpi，TIFF 为 600 dpi、LZW 压缩。
- 所有图使用仓库 Q1/Q2/Q3 既有的白底、深灰文字、蓝绿色主色和暖橙色对照色。
- 已逐张检查标题、坐标、图例、热图标签、分面标签和底部说明，没有发现文字与数据或相邻小图重叠。
- Fig09 的阴影表示折叠参数传播范围，不写作置信区间。
- Fig11 的 A 侧配比评价与 B 侧资源配置分面展示，不合并为联合 Loss。
- Fig12 的 Q1→B6 映射明确标注为未经验证的接口情景。
- Fig13 仅表示模型接口和可识别性边界，不表示 M3 已完成参数估计。

## 复现

```powershell
python paper/figures/q3/plot_q3_missing_figures.py
```

输入文件哈希和每幅图的行数记录在 `figure_manifest_missing.json`。
