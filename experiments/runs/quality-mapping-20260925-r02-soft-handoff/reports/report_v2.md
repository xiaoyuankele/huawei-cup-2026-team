# A4–A16 质量映射修订版

原始 A16 只明确了 6 个 direct/near_direct 映射，另外 11 个域要求自行建立关联。旧版本将这 11 个域各自硬分到一个代理质量域，确实会掩盖不确定性。本版改为候选质量域组合，并给出语义敏感性范围。

## 修订后的映射

| 配方域 | A16 类型 | 候选质量域 | 候选权重 | 软映射 Q | 语义范围 | 置信级别 |
|---|---|---|---|---:|---:|---|
| arxiv | direct | arxiv | {"arxiv":1.0} | 0.0046 | 0.0046–0.0046 | official |
| github | direct | github | {"github":1.0} | 0.4996 | 0.4996–0.4996 | official |
| stackexchange | direct | stackexchange | {"stackexchange":1.0} | 0.3850 | 0.3850–0.3850 | official |
| wikipedia_en | near_direct | wikipedia | {"wikipedia":1.0} | 0.5077 | 0.5077–0.5077 | official |
| gutenberg_pg_19 | near_direct | book | {"book":1.0} | 0.0029 | 0.0029–0.0029 | official |
| pile_cc | near_direct | commoncrawl | {"commoncrawl":1.0} | 0.1798 | 0.1798–0.1798 | official |
| dm_mathematics | inferred | arxiv;wikipedia | {"arxiv":0.8,"wikipedia":0.2} | 0.1052 | 0.0046–0.5077 | inferred_low |
| freelaw | inferred | book;wikipedia;commoncrawl | {"book":0.5,"wikipedia":0.3,"commoncrawl":0.2} | 0.1897 | 0.0029–0.5077 | inferred_low |
| nih_exporter | inferred | arxiv;wikipedia;commoncrawl | {"arxiv":0.6,"wikipedia":0.2,"commoncrawl":0.2} | 0.1403 | 0.0046–0.5077 | inferred_low |
| pubmed_central | inferred | arxiv;wikipedia;commoncrawl | {"arxiv":0.7,"wikipedia":0.2,"commoncrawl":0.1} | 0.1227 | 0.0046–0.5077 | inferred_low |
| philpapers | inferred | arxiv;book;wikipedia | {"arxiv":0.6,"book":0.2,"wikipedia":0.2} | 0.1049 | 0.0029–0.5077 | inferred_low |
| enron_emails | inferred | commoncrawl;stackexchange;wikipedia | {"commoncrawl":0.5,"stackexchange":0.3,"wikipedia":0.2} | 0.3069 | 0.1798–0.5077 | inferred_low |
| ubuntu_irc | inferred | commoncrawl;stackexchange;wikipedia | {"commoncrawl":0.5,"stackexchange":0.4,"wikipedia":0.1} | 0.2947 | 0.1798–0.5077 | inferred_low |
| europarl | inferred | wikipedia;commoncrawl;book | {"wikipedia":0.5,"commoncrawl":0.3,"book":0.2} | 0.3084 | 0.0029–0.5077 | inferred_low |
| hackernews | inferred | commoncrawl;stackexchange;wikipedia | {"commoncrawl":0.5,"stackexchange":0.4,"wikipedia":0.1} | 0.2947 | 0.1798–0.5077 | inferred_low |
| pubmed_abstracts | inferred | arxiv;wikipedia;commoncrawl | {"arxiv":0.7,"wikipedia":0.2,"commoncrawl":0.1} | 0.1227 | 0.0046–0.5077 | inferred_low |
| uspto_backgrounds | inferred | book;arxiv;wikipedia;commoncrawl | {"book":0.4,"arxiv":0.3,"wikipedia":0.2,"commoncrawl":0.1} | 0.1221 | 0.0029–0.5077 | inferred_low |

`q_soft_0_1` 是候选质量域分数的加权平均；`语义范围` 是候选质量域分数的最小值到最大值，不是统计置信区间。

## 对 A4–A15 的影响

| 数据集 | 行数 | 旧版硬代理均值 | 修订版软代理均值 | 修订版均值范围 | 平均范围宽度 |
|---|---:|---:|---:|---:|---:|
| A10_A11_test_1b | 64 | 0.1536 | 0.2005 | 0.1500–0.3365 | 0.1865 |
| A12_A13_est_10b | 63 | 0.1449 | 0.2035 | 0.1383–0.3634 | 0.2251 |
| A14_A15_est_70b | 63 | 0.1449 | 0.2035 | 0.1383–0.3634 | 0.2251 |
| A4_A5_train_1m | 512 | 0.1678 | 0.2214 | 0.1614–0.3749 | 0.2135 |
| A6_A7_test_1m | 256 | 0.1770 | 0.2281 | 0.1699–0.3809 | 0.2111 |
| A8_A9_test_60m | 256 | 0.1770 | 0.2281 | 0.1699–0.3809 | 0.2111 |

## 建议使用方式

- 正式结果优先使用 `quality_score_mapped_0_1`，只依赖 A16 的 direct/near_direct 映射。
- 需要覆盖全部 17 个配方域时，使用 `quality_score_soft_proxy_0_1`，同时报告 `quality_score_soft_range_width`。
- 不建议再把单个 inferred 域直接写成“对应 arxiv”“对应 book”等确定性结论。
- 如果需要更强的映射证据，下一步应使用 `regmix_domain_sample.jsonl.xz` 的原始文本，与 A1 的质量信号文本做文本相似度或人工抽样复核；当前软权重仍属于可解释的语义先验。

相关文件：

- `A16_domain_mapping_v2_soft.csv`
- `A4_A15_quality_scored_v2_soft.csv`
- `quality_mapping_v1_v2_comparison.csv`
- `A16_mapping_revision_note.md`
