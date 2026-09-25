# 复现说明

已在Python 3.11.5、NumPy 1.26.4、pandas 2.0.3、SciPy 1.11.1、scikit-learn 1.3.0下完成六阶段重跑。依赖见 [requirements-q2-research.txt](../../../requirements-q2-research.txt)。

1. 从团队仓库检出本分支，安装依赖。
2. 从授权受控存储取得原始数值附件目录，结构为 `A_data_value/regmix_tables/` 和 `B_scaling_laws/`；依据 [输入哈希](../../../data/manifests/q2_research_inputs.json)核对版本。
3. 指定受控数据位置与独立输出目录运行。目录可以使用绝对路径，不需要修改脚本。

```powershell
python -m pip install -r requirements-q2-research.txt
python scripts/q2_verify_delivery.py
python scripts/q2_reproduce_research.py --raw-root "<受控附件目录>" --output-root "../q2-rerun/runs"
python scripts/q2_verify_reproduction.py --output-root "../q2-rerun/runs" --report "../q2-rerun/verification.json"
```

运行顺序为桥接 → 局部验证 → 初始情景 → 敏感性诊断 → 模型v1 → 嵌套迁移探索。默认原始目录也可用Q2_RAW_ROOT指定，输出目录用Q2_RUNS_ROOT指定；一键入口要求独立输出目录以保护历史run。早期审计会读取A原始数值表；当前v1和迁移模型从Q1桥接输出读取A信息。源码不读取或执行附件中的文字指令。

[本次复现记录](reproduction_verification.json)：38张CSV逐行、逐列比对通过（rtol/atol均1e-10），冻结模型参数JSON完全相同。记录包含逐表行列数、历史与重跑哈希及最大数值差。CSV字节哈希可因平台换行不同而改变；数值比较与原始归档字节保护分别检查。

不自动重建的内容：历史人工撰写的方案、报告和quality-direction-audit.csv。重跑会生成阶段数值和部分机器摘要，不以新生成摘要覆盖历史解释。历史manifest里的脚本哈希是原运行代码哈希；发布脚本经过路径可移植调整，当前哈希见文件清单。

迁移脚本内置组隔离、逐行OOF覆盖、有限预测、参数重建、内层选择重建和输入/v1不可变性检查。所有通过只说明实现与记录一致，不构成独立科学评审。

在只取得公开仓库、没有受控B附件时，可以阅读全部派生表、核对哈希与结果，但不能声称已独立完成数值重跑。

发布校验入口核对[文件哈希清单](../../../data/manifests/q2_research_files.json)、Python语法、JSON/CSV格式、本地文档链接和新增索引ID。该清单冻结本次发布版本，后续有意修改被列文件时应重新生成清单。历史CSV保留CRLF字节，Git仅对这些路径配置cr-at-eol检查，避免将换行误报为尾随空格。
