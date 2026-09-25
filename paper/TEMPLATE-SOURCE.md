# LaTeX 模板来源

本目录的 `gmcmthesis.cls` 等上游文件同步自用户提供的 GMCM2026 模板压缩包 `GMCM2026.zip`。项目另增 `official-format-2026.sty`，按 2026 年 9 月 16 日的论文格式规范覆盖上游类文件中与当届要求冲突的封面和行距设置；上游类文件保留原样。

- 源文件 SHA256：`C0940E53E830BD8FC6B465E91CBF5CC31A248B786643B16D84969E4E04560120`
- 模板文件清单：29 个文件，包括 `gmcmthesis.cls`、`gmcm.bst`、官方示例、参考文献样式以及 `figures/` 下的版式素材。
- 同步策略：上游 29 个文件保持原样；适配层是本项目增量文件，不属于源压缩包。
- 论文入口：`paper/main.tex` 使用 `template/gmcmthesis.cls` 和 `template/official-format-2026.sty`，正文图形仍从 `paper/figures/` 引用。
- 记录日期：2026-09-25。

规范来源：用户提供的《“华为杯”第二十三届中国研究生数学建模竞赛论文格式规范》，落款 2026 年 9 月 16 日。提交前仍应复核赛题要求及最终材料。
