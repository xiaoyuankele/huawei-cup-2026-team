# Q4 figure QA report

## 已执行检查

运行 `nature-figure` Python backend 的源代码检查：

```powershell
python C:\Users\29717\.codex\skills\nature-figure\scripts\validate_figure.py scripts/plot_q4_figures.py --json
```

结果：`ready=true`，20 项 PASS，0 项 WARN，0 项 FAIL。检查覆盖字体、字号、颜色映射、可编辑文本、矢量/栅格导出、600 dpi、数据抽样、缺失值计数、旋转锚点和后端独占性。

逐个 PDF 运行 `audit_pdf_text.py --min-pt 5 --json`：

| PDF | 文本运行数 | 最小字号 | 低于 5 pt |
|---|---:|---:|---:|
| `FigQ4_01_frontier_validation.pdf` | 94 | 6.4 pt | 0 |
| `FigQ4_02_12m_scenarios.pdf` | 41 | 6.5 pt | 0 |
| `FigQ4_03_workflow.pdf` | 14 | 7.2 pt | 0 |

## 视觉复核

三幅 PNG 已按最终导出尺寸检查：面板标签、图例、中文标题和旋转刻度均在画布内；面板 a 的 bootstrap 阴影、面板 b 的任务差异、面板 d 的分组标记和图 Q4-2 的两类情景均可辨识。图 Q4-3 的流程箭头与边界说明完整。

