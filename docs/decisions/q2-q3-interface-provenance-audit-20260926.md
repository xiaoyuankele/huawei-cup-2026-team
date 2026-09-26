# Q2→Q3 接口运行 provenance 审计

审计日期：2026-09-26
涉及版本：`q2-q3-interface-20260926-v1.csv` → `q2-q3-interface-20260926-v2.csv`

## 审计发现

接口索引 v1 将以下三个运行的 `git_commit` 都写为 `d3f92c9acf68c625aa00fcad0f04b9fce4c0b168`：

- `q2-q-scale-bridge-20260926-r01`
- `q2-q3-formula-interface-20260926-r01`
- `q2-q3-interface-sensitivity-20260926-r01`

只读验证表明，`d3f92c9` 是合并提交，提交树中不存在
`scripts/q2_q_scale_bridge.py`；该脚本及对应运行产物首次进入当前 Git 历史的是打包提交
`6cb89e8`。因此 `d3f92c9` 不能证明这些运行的执行时脚本版本。

运行目录的元数据也不一致：Q2 scale bridge 没有 `git_commit.txt`；formula interface 的文件明确写着
“generated from local working tree before delivery packaging; not a reproducibility claim”；sensitivity
运行虽有同一哈希文件，但没有独立执行时证明。这里不能把打包提交倒填为执行提交。

## 处理决定

1. 保留 v1 不变，避免改写已经合并的历史索引。
2. 新增 v2：清空不可验证的 `git_commit` 字段，并在 `conclusion` 中显式标记
   `execution commit unavailable`。
3. 不修改任何结果表、指标数值、原始数据或运行状态。
4. 若要解除该元数据阻断，必须从当前可追溯提交重新运行接口实验，并在运行目录中同时保存
   `command.txt`、`environment.txt`、`git_commit.txt`、输入 manifest 和 `metrics.json`。

## 证据边界

该问题只影响运行可复现性与 lineage 证明，不推翻接口实验已经报告的数值，也不解除 A-B 无唯一键、
Q1/B6 尺度未校准和 B8 来源不足等科学阻断。v2 仍属于 `REVIEW_BLOCKED` 的审计修订，不代表正式联合拟合已验收。
