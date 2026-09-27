# 补充附件草稿

`supplementary-appendix.tex` 是放在 `paper/sections/drafts/` 下的补充附件草稿，覆盖：

1. 数据来源与数据角色；
2. 冻结参数和求解协议；
3. 模型诊断与敏感性结果；
4. 主张、证据与适用边界。

本文件暂不由 `paper/main.tex` 自动 `\input`。仓库当前主入口将问题二、问题三标记为候选或条件结果，
所以应在独立复核完成后再决定是否并入正式答卷。所有数值应回链到 `run_id`、数据 manifest、源文件路径和 SHA256；
不得把 `DRAFT`、`REVIEW` 或 `REVIEW_BLOCKED` 改写成已验证结论。

建议配套提交：

- `Supplementary_Tables.xlsx`：参数、指标和数据来源表；
- `S2_runs.csv`：实验运行索引；
- `S4_claim_evidence_boundary.csv`：主张—证据边界表；
- `supplement_appendix.pdf`：评审版短附录；
- `reproducibility.zip`：不含原始敏感数据的公开 smoke test。

本目录当前已经包含上述附件的仓库副本：

- `supplement_appendix.pdf`
- `Supplementary_Tables.xlsx`
- `S2_runs.csv`
- `S4_claim_evidence_boundary.csv`
- `supplement.zip`
- `reproducibility.zip`
- `supplementary-MANIFEST.sha256`

其中 CSV、工作簿和压缩包只包含公开派生表、索引和元数据，不包含原始文本或受控附件。
