# 问题一配比—质量映射审计

审计对象：A4–A15 配比域到 A1 样本级质量评分域的桥接。
审计状态：映射逻辑可复现，但语义证据不足以形成完整质量真值。
本审计不修改题目附件中的 A16 映射文件。

## 版本区分

| 层级 | 文件或运行 | 映射来源 | 质量评分来源 | 状态 |
|---|---|---|---|---|
| 原始映射 | `data/origin/real_attachments/A_data_value/domain_mapping_guide.csv` | SHA256 `0ae884c0...8401e7` | 无 | 题目附件参考映射 |
| 本次整合 | `q1-mixture-quality-integration-20260925-r01` | 同一 A16 SHA256 | 六个 20260925 样本级评分表，主模型 `TOPSIS_CRITIC` | `LOCAL_RESULT_PENDING_TEAM_REVIEW` |
| 队友桥接 | `q2-bridge-interface-20250925-r01/tables/domain_mapping_with_candidate_q.csv` | 同一 A16 SHA256 | `q1-critic-topsis-20260924-r01/tables/domain_scores.csv` | `BLOCKED_CONDITIONAL_INTERFACE` |
| 未映射压力测试 | `q1-quality-mapping-stress-20260925-r01` | 同一 A16 SHA256 | `TOPSIS_CRITIC` | 仅情景敏感性，不是映射表 |

因此目前没有发现两套不同的 A16 映射规则。区别在于评分来源、输出用途和是否对未映射域设置情景值。后续比较必须至少以 `(mapping_source_sha256, quality_source_sha256, run_id)` 三元组区分版本。

## 映射推导规则

1. 以 A4–A15 配比表的 17 个 `train_the_pile_*` 域名为配比域全集。
2. 以 A1 样本级评分中的 `_source_domain`/`domain` 为质量域全集。当前质量样本实际出现 `arxiv`、`book`、`c4`、`commoncrawl`、`github`、`stackexchange`、`wikipedia`。
3. 使用 A16 的 `quality_domain` 和 `mapping_type`，不从 Loss 反推映射。
4. `direct` 只表示域名标签一致，保留为候选域级映射，不表示两个附件来自同一语料源。
5. `near_direct` 保留为近似语义映射，不升级为直接映射。
6. `quality_domain` 为空或为 `(none)` 的 `inferred` 行保持未映射，不填充质量分。
7. 对有映射的域，先在 A1/full 样本级评分上按质量域计算均值，再按配比计算部分质量贡献和映射覆盖率：

\[
Q_{\mathrm{partial}}=\sum_{i\in M}p_iq_{m(i)},
\qquad
C=\sum_{i\in M}p_i,
\qquad
Q_{\mathrm{renorm}}=Q_{\mathrm{partial}}/C.
\]

`Q_partial` 和 `Q_renorm` 都不是完整语料质量真值，`C` 必须作为独立特征保留。

## 语义核对

### 同名候选域

- `arxiv → arxiv`
- `github → github`
- `stackexchange → stackexchange`

这三项在标签层面一致，但配比数据来自 RegMix/The Pile 域，质量评分来自 SlimPajama 质量信号样本。因此它们最多支持“同域名的跨来源质量代理”，不能解释为同一语料记录或完全相同的分布。

### 近似候选域

- `wikipedia_en → wikipedia`：质量样本路径确认是 `wikipedia`，但当前质量域字段没有独立证明其语言范围与 `wikipedia_en` 完全一致。
- `gutenberg_pg_19 → book`：PG-19 是书籍子域，`book` 是更宽的类别，存在粒度差异。
- `pile_cc → commoncrawl`：Pile-CC 是 Common Crawl 衍生子域，质量样本的 `commoncrawl` 是更宽的来源类别，存在来源和抽样差异。

这三项保留 `near_direct` 是合理的，但不能在正式模型里当成无误差标签。

### 当前不能建立的 11 项

`freelaw`、`nih_exporter`、`pubmed_central`、`dm_mathematics`、`philpapers`、`enron_emails`、`ubuntu_irc`、`europarl`、`hackernews`、`pubmed_abstracts`、`uspto_backgrounds` 在 A16 中没有质量域候选。当前不应把它们强行映射到 `arxiv`、`book`、`commoncrawl` 或其他相近领域。压力测试中的 low/mean/high 只是边界情景，不是语义映射。

## 与队友表的关系

队友表 `domain_mapping_with_candidate_q.csv` 与本次 `mapping_audit.csv` 的 17 行映射分类一致，都是 3 个 `direct`、3 个 `near_direct`、11 个 `inferred`。队友表使用 20260924 评分运行，本次整合使用 20260925 样本级评分运行。当前 6 个 A1 域均值数值相同到机器精度附近，但两者 SHA256 和 run_id 不同，不能删除版本标识或直接覆盖。

后续如果队友提供新的语义映射候选，应先新增独立的 `mapping_version` 和候选文件，分别记录证据类型、源语料关系、语言范围、粒度和允许的使用场景，再通过映射敏感性实验比较，不能直接替换 A16 或合并到当前主表。

## 结论

当前整合脚本的计算逻辑与 A16 文件一致，且没有把 11 个未映射域伪造成有质量分。逻辑层面没有发现“把空映射当成真实映射”的错误。真正的语义限制是：即使 `direct` 标签相同，配比和质量数据仍来自不同语料体系，当前结果只能称为跨来源的域级质量代理。若论文需要完整质量评分或独立质量效应，必须先补充 11 个域的语义证据，或明确采用情景包络而不是单一质量分。
