# A16 映射修订说明

原版本将 11 个 `inferred` 域各自硬映射到一个质量域，作为快速可运行版本。该做法会把语义不确定性隐藏起来。修订版保留 6 个 `direct/near_direct` 一对一映射，对 11 个 inferred 域使用候选质量域组合。

修订版的 `q_soft_0_1` 是候选域质量分的加权平均；`q_semantic_range_low/high_0_1` 是候选域分数的最小/最大值，用来表示语义代理敏感性，不是统计置信区间。

建议：正式分析优先报告 direct/near_direct 覆盖的 `quality_score_mapped_0_1`；如果必须覆盖 17 个配方域，使用 `quality_score_soft_proxy_0_1`，同时报告 `quality_score_soft_range_width`。

## 主要修订
- `freelaw`、`uspto_backgrounds`：不再只使用 `book`，增加 `wikipedia`、`arxiv` 或 `commoncrawl` 的敏感性成分。
- `enron_emails`、`ubuntu_irc`、`hackernews`：不再只使用 `commoncrawl`，加入 `stackexchange` 以反映对话/技术社区属性。
- `europarl`：使用 `wikipedia`、`commoncrawl`、`book` 混合，不再视为单一百科文本。
- 生物医学和学术域：仍以 `arxiv` 为主，但保留通用文本域作为不确定性范围。
