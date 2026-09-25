# 问题二 A 到 B 数据迁移与整合计划

状态：`EXECUTED_TO_M3_PREFLIGHT_BLOCKED`

本计划解决问题一 A 数据向问题二 B 数据迁移时的语义、数据血缘、可识别性和验证问题。计划只定义接口、路径、门槛和证据包，不生成最终广义标度律、质量系数、配比系数或弹性结论。

## 1. 迁移目标与当前边界

目标是把问题一形成的质量和配比信息，经过可追溯的域级桥接，作为问题二标度律的候选输入：

\[
A\text{质量信号} \rightarrow q_j\text{域级质量}
\rightarrow p_i\text{域配比}
\rightarrow Q(p)\text{构造性质量指数}
\rightarrow B\text{侧标度律敏感性分析}.
\]

当前已知边界：

- A16 只有 17 个配比域到质量域的人工映射，没有 A 行记录到 B 行记录的连接键；
- B1 没有 `Q` 或 `p`，B6--B8 有 `Q_score` 但没有 `p`；
- A、B 实验独立，不能按行号、模型规模或 Loss 顺序拼接；
- 问题一最终标量 `Q` 和可验收 `p` 接口尚未完成；
- B8 的 `Q` 方向与 B6/B7 相反，且来源和生成规则缺失。

因此，当前正式允许的是接口设计和分层敏感性分析；完整 A--B 联合模型处于阻断状态。

## 2. 总体架构

```text
S0 原始数据隔离与指纹
       ├── A 原始层：A1–A3、A4–A15、A16
       └── B 原始层：B1–B12
                ↓
S1 各自独立的规范化与审计
       ├── Q1-A：质量指标矩阵、域级 q、配比 p
       └── Q2-B：N、D、Loss、family、data_type、证据等级
                ↓
S2 语义桥接层
       ├── A16 域映射表
       ├── mapping_type / coverage / uncertainty
       └── bridge assumptions
                ↓
S3 候选迁移层
       ├── M0：仅 B1 的 N-D 经典基线
       ├── M1：B6/B7 自带 Q 的质量敏感性
       ├── M2：A 域级 q 与 p 构造 Q(p)，只做 A 内或条件分析
       └── M3：有逐行键后的联合 L(N,D,Q,p)（当前不可用）
                ↓
S4 分层验证层
       B1 内部留出 → B2/B3 → B4/B5 → B6/B7 → B8/B9/B10 外推敏感性
                ↓
S5 证据发布层
       run_id、manifest、指标、限制、claim ledger、论文接口
```

## 3. 五层数据契约

### 3.1 A 侧质量契约

A1--A3 只负责产生质量信号和域级质量，不使用 B 的 Loss 反向调整指标方向、权重或阈值。输出至少包含：

| 字段 | 含义 |
|---|---|
| `quality_version` | 质量评分版本和配置哈希 |
| `quality_domain` | A1--A3 的质量域 |
| `q_center` | 域级质量中心值 |
| `q_lower`, `q_upper` | 不确定性或敏感性区间 |
| `n_records` | 用于聚合的有效记录数 |
| `direction_status` | 指标方向是否已核验 |
| `source_role` | A1 fit、A1 holdout、A2/A3 外部迁移 |

在 9 个指标方向仍为 `pending_verification`、质量总分未通过验收前，不能生成正式 `q_center`。

### 3.2 A 侧配比契约

A4--A15 输出 17 维单纯形配比：

| 字段 | 含义 |
|---|---|
| `recipe_id` / `index` | 配方标识 |
| `scale` | 1M、60M、1B、10B、70B 等规模条件 |
| `p_i` | 17 个域的归一化配比 |
| `sum_p` | 原始配比和及归一化记录 |
| `support_flag` | 是否在 A4 观测设计支持范围内 |
| `loss_role` | 拟合、验证或外推角色 |

不能把 A12--A15 的外推 Loss 当作独立真值，也不能把 A6=A8、A12=A14 的重复配比矩阵计作独立配比样本。

### 3.3 A16 域映射契约

A16 作为人工参考表保留四种状态：

- `direct`：可直接对应；
- `near_direct`：语义近似，需要敏感性分析；
- `inferred`：没有直接质量域，不生成确定的质量标签；
- `none`：明确缺失，不允许静默填补。

每次迁移必须保留 `mapping_version`、`mapping_type`、覆盖率和映射不确定性。

### 3.4 B 侧观测契约

B 侧统一为长表，但保留来源和性质：

| 字段 | 含义 |
|---|---|
| `source_id` | B1--B12 文件标识 |
| `family` | 模型族或文献来源 |
| `N_params_B`, `D_tokens_B` | 参数和 token，单位固定为十亿 |
| `val_loss` | 验证交叉熵损失 |
| `Q_score` | 仅 B6--B8 的半合成质量字段 |
| `data_type` | B8 的 calibrated/extrapolated |
| `evidence_role` | 主拟合、轨迹、族外、文献、半合成、估算 |
| `provenance_status` | 完整、部分、缺失 |

B1--B5、B6/B7、B8、B9/B10 必须分层保存，不能先合并再补标签。

### 3.5 桥接契约

任何 A→B 迁移都必须形成一条桥接记录：

| 字段 | 含义 |
|---|---|
| `bridge_id` | 桥接方案标识 |
| `source_A` | A 侧输入版本 |
| `source_B` | B 侧输入版本 |
| `assumption` | 可检验的传输假设 |
| `join_key` | 真实连接键；当前通常为空 |
| `mapping_scope` | 域级、配方级、模型级或逐行 |
| `identifiability` | 可识别、条件可识别、不可识别 |
| `validation` | 支持该桥接的验证结果 |
| `status` | proposed、review、accepted、rejected |

没有 `join_key` 时，`mapping_scope` 不得填写为逐行。

## 4. 迁移模式与准入规则

### M0：B1 经典基线

只使用 B1 的 `N,D,Loss`，不引入 A 的任何结果。用途是建立问题二的最小基线和分组验证协议。该模式当前可执行。

### M1：B6/B7 自带质量敏感性

只使用 B6/B7 的 `N,D,Q_score,Loss`，并明确标注半合成。B6 是 B7 的嵌套子集，不能同时等权计数。该模式可以估计“该半合成构造中的 Q 敏感性”，不能直接证明问题一 `Q` 已成功迁移。

### M2：A 域质量到配方质量的构造性迁移

在 A16 映射和问题一质量域分数通过审查后，可构造：

\[
Q(p)=\sum_{i=1}^{17}p_i q_i.
\]

但必须同时输出：

- 仅 `direct` 映射的 (Q_{direct}(p))；
- `direct + near_direct` 的 (Q_{near}(p))；
- 对 `inferred` 域不确定或区间化的 (Q_{range}(p))。

M2 只能用于 A 内配方分析、桥接敏感性或条件情景，不能把它伪装成 B1 的逐行观测质量。

### M3：逐行联合迁移

只有在获得 A 配方、质量、B 训练记录之间的真实连接键，且验证了相同 Loss 口径、训练数据语义和实验单位后，才允许估计完整的 (L(N,D,Q,p))。当前数据不满足 M3 条件，应保持 `REVIEW_BLOCKED`。

## 5. 推荐的模型整合顺序

### 阶段 P0：冻结来源

输入：原始 A/B 附件、清理后的题目文件、现有 manifest。

动作：计算 SHA256，建立只读快照，登记文件性质、许可证、来源和隐藏文字隔离状态。

验收：所有原始文件只读；A/B 每个文件有唯一版本；B7/B8 的来源缺口单独列为阻断项。

### 阶段 P1：完成 Q1 输出接口

输入：A1--A3、A4--A16。

动作：完成质量方向核验、指标聚合、域级 `q`、配比 `p`、A16 映射敏感性。

验收：质量总分和配比输出达到 `PACKAGE_ACCEPTED`；每个 `q_i` 可回链到指标、样本范围和配置；不得用 A4--A15 Loss 反推质量标签。

### 阶段 P2：建立独立 B 基线

输入：B1--B5。

动作：B1 做分组留出；B2/B3 做族外和轨迹验证；B4/B5 按 family/source 分层。

验收：主拟合、验证、外推不能混组；报告 MAE、RMSE、相对误差、残差和不确定性；不以训练集 R² 作为唯一结论。

### 阶段 P3：质量桥接审计

输入：P1 的 `q_i,p_i` 和 B6--B8。

动作：比较 `Q_A`、`Q(p)` 和 `Q_score_B` 的范围、方向、基准和可比性；B6/B7 单独分析；B8 隔离。

验收：明确哪些量可比较、哪些只能敏感性分析；若没有跨附件校准锚点，不得写 `Q_A=Q_B`。

### 阶段 P4：候选模型族比较

候选结构至少包括：

1. 经典 `N-D` 基线；
2. 显式质量修正；
3. 有效数据量修正 `D_eff=D*q(Q,p)`；
4. 配比摘要或交互项的条件模型。

每个候选模型都要满足基准归一化、参数可识别、训练/验证分层和退化条件。不能用 B8 反向关系决定质量方向。

### 阶段 P5：弹性与替代分析

只有模型在 B1--B5 和允许的半合成敏感性集上通过验证后，才计算：

\[
\varepsilon_N=\frac{\partial L}{\partial N}\frac{N}{L},\qquad
\varepsilon_Q=\frac{\partial L}{\partial Q}\frac{Q}{L}.
\]

质量提升等价参数增加必须固定 `D,p,L`，并报告局部近似、有限区间解和不确定性。配比效应用单纯形上的替代方向或 log-ratio 坐标，不把普通偏导直接解释成自由增减。

### 阶段 P6：论文与证据封装

每条正式主张必须关联：数据 manifest、桥接记录、run_id、配置、指标、图表、限制和证据等级。B6/B7 只能写半合成补充证据；B8、B9、B10 的外推性质必须在图表和文字中显式标注。

## 6. 验证矩阵

| 问题 | 主数据 | 验证数据 | 不可做的解释 |
|---|---|---|---|
| 经典 N-D 标度律 | B1 | B2/B3、B4/B5 | 不能把跨族结果写成 B1 同源真值 |
| 半合成 Q 效应 | B6/B7 | 分层留出和敏感性 | 不能写成真实受控实验 |
| B8 质量效应 | 暂不进入主模型 | 仅来源核验后再决定 | 不能反转 Q 或静默删点 |
| A 域级质量 | A1--A3 | A2/A3 域迁移 | 不能视为独立真值或直接映射 B |
| A 配方质量 | A4--A16 | A 内尺度条件验证 | 不能直接当作 B 行级 p |
| 百亿参数外推 | B9/B10 | 范围、敏感性、来源检查 | 不能当真实验证集 |

## 7. 污染和泄漏防护

- 题目 PDF 的近白隐藏文字只进入隔离清单，不进入模型输入、先验和结论；
- 原始 A/B 文件只读，所有派生表带父文件 SHA256；
- A1 的质量预处理参数不能由 A2/A3 或 B 数据估计；
- Q1 的质量权重不能用 B Loss 反调；B Loss 模型不能用未来验证结果调参；
- B6 是 B7 的嵌套子集，避免重复加权；
- B8 的 calibrated/extrapolated 必须分开；
- B9/B10 不能参与 B1 主模型参数估计；
- 随机划分不能拆散同一模型训练轨迹、同一来源或同一模型族；
- 任何 `Q` 方向改变、零替换、近似映射和尺度转换都必须记录为独立 bridge version。

## 8. 交付物结构

建议按以下目录保存，不覆盖原始附件：

```text
data/manifests/
  q1_quality_interface_v1.yaml
  q1_recipe_interface_v1.yaml
  q2_bridge_manifest_v1.yaml
data/processed/q2_bridge/
  domain_mapping_a16_v1.csv
  domain_quality_direct_v1.csv
  domain_quality_sensitivity_v1.csv
  recipe_quality_qp_v1.csv
  bridge_assumptions_v1.yaml
experiments/runs/
  q2-b-baseline-<date>-r01/
  q2-quality-bridge-<date>-r01/
  q2-b8-provenance-audit-<date>-r01/
paper/claim-ledger.csv
  每条 Q/p 迁移主张回链到 bridge_id 和 run_id
```

## 9. 解锁判据

只有以下条件全部满足，才可把状态从 `PLAN_ONLY/REVIEW_BLOCKED` 改为正式拟合：

1. 问题一的标量 `Q`、域级 `q_i` 和配比 `p` 通过独立复核；
2. A16 的 direct、near_direct、inferred 映射已分层量化不确定性；
3. B1 分组留出、B2/B3、B4/B5 验证协议已冻结；
4. B6/B7 嵌套关系已处理；
5. B8 的来源、质量语义和生成公式已补齐，或明确从主结论永久排除；
6. 真实 `join_key` 不存在时，论文明确采用条件迁移而非逐行联合模型；
7. 所有模型结果、弹性和外推值都有脚本、配置、哈希和独立验证记录。

当前建议的可执行路径是：保留 M0/M1 探索结果，完成 P1/P3 的接口复核，并用 M2 条件情景包络量化未映射域影响；在补齐 inferred 域和 Q1 验收前，M2 不进入 B 拟合，M3 暂停。
