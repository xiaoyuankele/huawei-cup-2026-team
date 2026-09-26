# 纯配比与规模修正的受控回顾性消融

`run_id: q1-mixture-scale-ablation-20260925-r01` · `task_id: T-Q1-S03-ABLATION` · 状态：待团队复核

本次将纯配比 ilr-Ridge、二阶 Ridge 接入已经审计的 C1/C2 尺度修正，另以完全相同的 512 行拟合数据比较追加 Q_proxy 的增量。保留 Q-only 为辅助压缩对照。研究主线不依赖质量分数。

## 运行前固定的协议

[配置](../../../configs/q1-mixture-scale-ablation.json) 记录本次受控比较。模型族及参数均在本次计算前固定，但来源于已开展的历史研究，不称事前注册或新盲测。

| 项目 | 设置 |
|---|---|
| 基模型 | ilr-Ridge、二阶 ilr-Ridge、二者各追加一个 Q_proxy 列、Q-only OLS |
| 共同拟合行 | A4/A5 全部 512 行；质量代理完整，无删行 |
| 配比处理 | 17 域非负归一化；乘法零替换 ε=10⁻⁴；16 维 Helmert-ilr |
| 二阶特征 | 16 个一阶项、136 个平方/交互项，共 152 项；Q 在变换后追加，无 Q 交互 |
| 回归 | 特征标准化只在拟合数据上估计；Ridge α=10，截距不惩罚；Q-only 为 OLS |
| 修正 | C0 无修正；C1-global 单一斜率；C1-domain 13 域斜率；C2 配方条件差值，α=10 |
| 尺度标定 | A6/A8 的 256 个完全相同配方对；`x=log10(S/1M)`；完整配对差乘 `x/log10(60)` |
| 额外诊断 | 五折校准 OOF，仅重新估计训练折统计量；α来自历史选择，故非独立/嵌套验证 |
| 主指标 | 全样本×13响应 pooled RMSE/MAE；平均响应、逐域与 R²另列 |
| 差值区间 | 固定预测、配方行为重采样单位、13响应整组保留；5,000次配对 bootstrap，seed=20260925（按表加序号） |

Q_proxy 是 p 的确定函数；新增列测试的是特征表示及正则化的增量，不是独立质量因果信息。追加质量模型没有另外调参；不能将其结果推广为所有质量评分或充分优化后的质量模型无用。

## 数据角色和结果入口

A6 是同规模回顾评价；在修正方案中同时参与尺度差标定。A8 修正后性能属于校准内，条件 OOF 独立列在 `metrics_calibration_oof.csv`。A10 是校准外回顾评价，不是从未查看的确认性检验。A12/A14 配方为训练表子集，Loss 为题目给定估算值；它们只支持估算表一致性审计。

论文方法、完整解释和中文 Results 草稿见 [结果文档](../../../docs/decisions/q1-mixture-scale-ablation-results.md)。

| 文件 | 内容 |
|---|---|
| `metrics_aggregate.csv` | 5基模型×4修正×6表 = 120行，所有组合完整保留 |
| `metrics_by_domain.csv` | 1,560行逐响应指标 |
| `metrics_calibration_oof.csv` | 20行条件校准OOF指标 |
| `paired_error_comparisons.csv` | 135个尺度、质量、二阶/一阶比较；差值为候选减参照，负值表示改善 |
| `table_pure_mixture_scale.csv` | 40行纯配比主表 |
| `table_optional_quality.csv` | 40行可选质量增量及区间 |
| `table_scale_transfer.tex` | 纯配比1B/10B/70B表格片段，直接 `\input`，需中文LaTeX环境 |
| `table_quality_increment.tex` | 固定C1-global的质量增量展示片段；其他修正完整保留于CSV |
| `high_scale_shift.csv` | 同配方10B→70B差值审计，对全部基模型相同 |
| `model_parameters.json` | 基变换、特征次序、回归系数、归一化、尺度参数 |
| `audit.json` / `validation.json` / `verification.json` | 运行环境、限制、历史复现、科学不变量测试与内部独立验数 |
| `run_manifest.json` | 输入、源代码和所有运行产物的字节哈希 |
| `figures/` | PNG/PDF/SVG/TIFF、绘图源数据、中文图注与QA |

## 复现

在仓库根目录、Python 3.11 环境执行：

```bash
python -m pip install -r requirements-q1-mixture-scale-ablation.txt
python -m unittest discover -s tests -p test_q1_mixture_scale_ablation.py -v
python -m unittest discover -s tests -p test_q1_s03.py -v
python scripts/q1_s03/mixture_scale_ablation.py
python scripts/q1_s03/plot_mixture_scale_ablation.py --run experiments/runs/q1-mixture-scale-ablation-20260925-r01
python scripts/q1_s03/package_mixture_scale_ablation.py
```

计算脚本也支持 `--output` 写到独立目录。发布图形依赖操作系统字体与 matplotlib 版本；数值复现以 CSV 和参数为准。LaTeX 表格是可编辑片段，未在本包内编译成完整论文。

直接计算新配方：按 `p_columns` 排序和归一化、按 ε处理零后乘保存的 ilr 基；二阶按 `polynomial_powers` 构造；可选 Q 最后追加；用保存的均值/标准差归一化后计算 `X @ coefficients_targets_by_features.T + intercept_targets`；按登记公式再加尺度项。S 必须与1M使用统一单位。

本包复用既有派生表，没有上传原始附件、逐行目标/预测副本或新的训练权重。内部自动与AI检查不替代团队人工复核。
