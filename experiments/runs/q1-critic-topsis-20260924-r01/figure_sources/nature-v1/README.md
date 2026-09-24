# Nature 风格六图：来源与复现

本目录附属于 `q1-critic-topsis-20260924-r01`，是已有评分运行的可视化派生产物，不是新的模型实验。

- [写作图组与预览](../../../../../paper/figures/q1-critic-topsis/nature-v1/README.md)
- `tables/`：描述统计、KDE 曲线、领域指标均值、A1 对照和分解、权重、方案敏感性；不含样本 ID。
- `validation/`：来源文件哈希、计数检查、制图规范、源代码预检、PDF 字号和视觉审阅。历史本地导出清单包含 TIFF；本次实际入库文件见 `upload_manifest.json`。
- `upload_manifest.json`：本次新增和修改文件的 SHA-256 与 Git blob SHA。

## 从完整派生数据复现

在已有完整本地派生数据的仓库根目录运行（公开 Git 不包含样本明细，需团队受控数据包）：

```text
python scripts/plot_q1_domain_distribution_nature.py --input experiments/runs/q1-critic-topsis-20260924-r01/artifacts/unique_sample_scores.csv --reference-domain-table experiments/runs/q1-critic-topsis-20260924-r01/tables/domain_scores.csv --output local/q1-nature-reproduction/figure01
python scripts/plot_q1_figures_02_06_nature.py --repository . --output local/q1-nature-reproduction/figures02_06
```

环境：Python 3.11.5、numpy 1.26.4、pandas 2.0.3、scipy 1.11.1、matplotlib 3.7.2，Arial 与 Microsoft YaHei 字体。脚本验证输入哈希，版本不同需先核对。

## 核对结果

全量质量信号 272,505 条，11,419 条跨集重复；重复 ID 的 16 项指标及领域一致，唯一 ID 与评分表完全匹配。所有 261,086 个唯一样本参与统计。图 3 差值及图 4 分解与原运行指标一致。CRITIC 权重合计 1；图 6 比例与百分点单位核对通过。图 1 描述统计与原图字节相同。

图 1 和图 2–6 的源码预检各 20 PASS / 0 WARN / 0 FAIL；实际 PDF 最小字体均为 7 pt，人工检查六图标签和布局。没有新增显著性结论、置信区间、模拟数据或指标冲突诊断。

审核状态仍为 DRAFT / 待团队独立复核，详见 `docs/tasks/WP-B-figures-handoff.yml`。本次不修改主论文入口、既有数值配置或运行结果。
