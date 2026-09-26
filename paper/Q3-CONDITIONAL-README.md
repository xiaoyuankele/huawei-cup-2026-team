# 问题三条件资源配置论文包

版本：`Q3-CONDITIONAL-INTERFACE-v1.0.0`
任务：`T-Q3-CONDITIONAL-INTERFACE`
分支：`exp/ACTOR-2/q3-conditional-interface-20260926`
状态：`DRAFT / REVIEW_REQUIRED`（任务卡状态：`REVIEW_BLOCKED`）

本目录保存问题三当前的独立审阅稿。稿件把 B1 的 `N-D` 基线、B6/B7 原生 `Q_B` 条件优化和 A 侧配比的 Q2→Q3 假设接口分开写入。A、B 数据没有共同连接键，`Q_A` 与 `Q_B` 也没有完成统一标度，因此本稿不接入 `paper/main.tex`，不宣称正式四量联合拟合或全局最优。

## 文件说明

- `sections/drafts/q3-conditional-resource.tex`：问题三 6.1–6.3 候选正文，覆盖问题分析、变量、M0、M1、M2/P 接口和结果边界。
- `sections/drafts/q3-conditional-resource-standalone.tex`：主候选正文的独立 XeLaTeX 编译入口。
- `sections/drafts/q3-subproblem2-m1-ndqb-draft-20260926.tex`：子问题二 M1 的 `N-D-Q_B` 条件优化稿；对应说明见同名 `.md`。
- `sections/drafts/q3-subproblem3-m2p-interface-draft-20260926.tex`：子问题三 M2/P 配比接口稿；对应说明见同名 `.md`。
- `sections/drafts/q3-subproblem23-standalone-20260926.tex`：子问题二、三合并的独立审阅入口。
- `sections/drafts/q3-m0-nd-figure-snippet.tex`：M0 图表插入片段，当前不由主候选正文自动引入。`q3-subproblem23-standalone-20260926.tex`：子问题二、三合并独立编译入口。
- `tables/q3_m0_nd_scenarios.tex`：M0 15 个预算—上下文情景表。
- `figures/q3-nd-baseline-nature-v1/`：M0 图件、图件契约和来源清单。
- `outline-q1-q4-20260926.md`：全文结构草案；`sections/drafts/q3-conditional-resource-outline-20260926.md`：问题三章节结构说明。
- `sections/drafts/q3-exploratory-results.md`：早期探索结果及证据边界，仅作背景，不替代本版本稿件。

## 编译

在本目录 (`paper/`) 下执行。先创建隔离构建目录，避免把 `.aux`、`.log`、`.toc` 等产物写入源文件目录：

```powershell
New-Item -ItemType Directory -Force build\q3-conditional-resource | Out-Null
xelatex -interaction=nonstopmode -halt-on-error `
  -output-directory=build\q3-conditional-resource `
  sections\drafts\q3-conditional-resource-standalone.tex
```

审阅子问题二、三合并稿时：

```powershell
New-Item -ItemType Directory -Force build\q3-subproblem23 | Out-Null
Push-Location sections\drafts
xelatex -interaction=nonstopmode -halt-on-error `
  -output-directory=../../build/q3-subproblem23 `
  q3-subproblem23-standalone-20260926.tex
Pop-Location
```

如果本机没有 `xelatex`，请使用 TeX Live、MiKTeX 或 Overleaf 等 XeLaTeX 环境；本次提交不纳入生成的 PDF 或临时构建包。编译前仍需按任务卡完成 Peer Review 和 Integrator 审查。

## 复核边界

- 编译入口均为独立审阅稿，不修改 `paper/main.tex`。
- 所有数值应回链到 `experiments/runs/` 中的 `run_id` 和 `docs/research/q3/` 的版本说明。
- 不按行号建立 A–B 连接，不把假设 `Q_A -> Q_B` 映射写成实证标定。
- `.aux`、`.log`、`.out`、`.toc`、`.pdf` 和临时构建记录属于生成物，不纳入本次提交。
