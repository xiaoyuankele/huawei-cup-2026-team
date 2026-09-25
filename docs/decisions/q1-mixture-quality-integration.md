# 问题一配比—质量整合表

运行号：`q1-mixture-quality-integration-20260925-r01`
任务：`T-Q1-003-MIXTURE`
状态：`LOCAL_RESULT_PENDING_TEAM_REVIEW`

本运行把样本级质量评分汇总到质量域，再通过 A16 域映射与 A4–A15 配比—规模特征表连接。原始附件和样本级评分文件保持只读。

## 输入

- 配比与规模：`experiments/runs/q1-scale-feature-table-20260924-r01/q1_scale_features_wide.csv`，共 1214 个配比样本，包含 A4/A5、A6/A7、A8/A9、A10/A11、A12/A13、A14/A15 六个数据组。
- 质量评分：六个 20260925 样本级评分表，主模型为 `TOPSIS_CRITIC`，其余五个模型用于评分敏感性。
- 域映射：`data/origin/real_attachments/A_data_value/domain_mapping_guide.csv`。
- 质量汇总口径：A1 全量样本按质量域取 `quality_score` 均值，同时保留样本数、中位数、标准差、P10 和 P90。

## 整合公式

对配比样本 (r)，设 (p_{ri}) 为第 (i) 个配比域的归一化比例，(q_{m(i)}) 为 A16 映射到的质量域评分：

\[
Q_{r,\mathrm{raw}}=\sum_{i\in M}p_{ri}q_{m(i)},
\qquad
C_r=\sum_{i\in M}p_{ri},
\qquad
Q_{r,\mathrm{renorm}}=Q_{r,\mathrm{raw}}/C_r.
\]

其中 (M) 是存在直接或近直接映射的配比域集合。`mapped_mass` 记录 (C_r)，`unmapped_mass=1-C_r`。未映射领域不填充质量分，因此 `mapped_quality_raw_0_100` 是部分映射贡献，`mapped_quality_renorm_0_100` 只是覆盖域条件下的敏感性特征，不能称为完整语料质量总分。

## 输出

- `experiments/runs/q1-mixture-quality-integration-20260925-r01/mixture_quality_integration_wide.csv`：每个配比样本一行，保留比例、规模、主质量特征和六种质量评分模型的敏感性列，并写入 `mapping_version` 与 `quality_score_version`。
- `experiments/runs/q1-mixture-quality-integration-20260925-r01/mixture_quality_contributions_long.csv`：每个配比样本 × 17 个配比域一行，共 20638 行，保留比例、映射类型、质量域、质量贡献、未映射状态和版本标识。
- `experiments/runs/q1-mixture-quality-integration-20260925-r01/quality_domain_reference.csv`：六种评分模型在 A1/A2/A3 质量域上的样本数和分布统计，共 54 行。
- `experiments/runs/q1-mixture-quality-integration-20260925-r01/mapping_audit.csv`：17 个配比域的 A16 映射审计。
- `experiments/runs/q1-mixture-quality-integration-20260925-r01/metrics.json`：输入输出哈希、行数、检查结果和限制。

当前 A16 仅映射 17 个配比域中的 6 个，按域计覆盖率为 6/17。A12–A15 仍然是外推情景，不是独立验证数据。质量评分运行仍处于团队复核状态，因此本表用于候选特征整合和敏感性分析，不支持因果质量效应、完整质量总分或最优配比结论。

重跑命令：

```powershell
python -X utf8 scripts/q1_mixture_quality_integration.py
```
