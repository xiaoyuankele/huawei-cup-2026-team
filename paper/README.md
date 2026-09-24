# LaTeX 论文管理规范

本目录采用“题目顺序论文 + 工作包执行”的双层架构。论文最终阅读顺序由题目中的问题编号决定；`WP-A/WP-B/WP-C` 只用于后台分配数据、模型、验证和图表任务，不直接决定章节顺序。

## 论文入口与章节装配

- `main.tex`：唯一编译入口。
- `sections/introduction.tex`：研究背景和总体问题说明。
- `sections/assumptions.tex`：跨问题共用的假设和符号。
- `sections/problem-order.tex`：按题目编号装配问题正文。
- `sections/problems/problem-XX.tex`：一道题对应一个正文文件。
- `sections/drafts/legacy-*.tex`：迁移前的跨题目占位稿，不被 `main.tex` 编译。
- `sections/conclusion.tex`：综合结论、贡献和局限。
- `commands.tex`：统一数学符号和项目命令。
- `refs.bib`：项目唯一正式参考文献库。

每个问题文件内部使用固定顺序：

```text
问题分析与输入输出
→ 模型建立
→ 算法与求解
→ 结果与检验
→ 不确定性与局限
```

题目数量确定后，在 `sections/problems/` 新增 `problem-01.tex`、`problem-02.tex` 等文件。 `problem-order.tex` 已预留编号入口，并按编号装配；不要把正文重新拆成跨题目的“模型”“实验”“结果”章节。

## 研发结果如何进入论文

论文不是实验事实源，而是已验收证据的组织层。每一个正式数字或结论都要能沿以下链路回溯：

```text
problem_id / subproblem_id
→ task_id
→ run_id
→ data_manifest
→ git_commit
→ figure/table
→ claim_id
→ sections/problems/problem-XX.tex
```

问题之间有数据或参数依赖时，必须同时记录上游问题的输出文件、输入 manifest 和依赖关系。没有 `run_id`、独立复核或证据边界说明的内容只能保留在草稿中。

## 主张状态

`paper/claim-ledger.csv` 是论文主张台账。建议使用以下状态：

| 状态 | 说明 | 可否进入正式正文 |
|---|---|---|
| `DRAFT` | 草稿或候选图表 | 否 |
| `LOCAL_COMPUTATION_PENDING_TEAM_REVIEW` | 已本地运行，等待独立复核 | 否 |
| `PACKAGE_ACCEPTED` | 运行、图表、解释和复核均完成 | 可以 |
| `INTEGRATED` | 已合入论文集成分支并完成编译检查 | 可以 |
| `REWORK` | 需要返工 | 否 |
| `REVIEW_BLOCKED` | 证据不足、冲突或无法判断 | 否 |

当前台账中的 Q1 内容仍有草稿和待复核记录，不应直接视为最终结论。

## 图表、数据和文献

图表按问题归档：

```text
paper/figures/q1/<version>/
paper/figures/q2/<version>/
```

每组图表保留源脚本、源表、图注、导出文件、manifest 和审核状态。论文引用只从 `paper/refs.bib` 读取；检索式和阅读笔记放在 `docs/literature/`，受版权限制的 PDF 和个人批注保留在本地。

## 修改与审核

论文修改必须绑定 `task_id`、`problem_id` 和 `section_id`，通过短分支和 PR 提交。提交前至少完成：

1. 章节顺序仍与题目顺序一致；
2. 正文数字和图表均可回链 `run_id`、manifest 和 `claim_id`；
3. 题目之间的数据依赖已经写明；
4. Peer Reviewer 独立检查公式、数据边界、图表和结论；
5. Release Integrator 检查跨问题一致性、引用和编译结果。

从仓库根目录编译：

```powershell
.\scripts\compile_paper.ps1
```

提交前还需依据 `paper/official-template-checklist.md` 和 `governance/release-checklist.md` 检查封面、匿名、页码、图表、参考文献和最终 PDF 哈希。
