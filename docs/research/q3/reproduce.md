# 复现

仓库根目录，Python 3.11，依赖见 `requirements-q3-research.txt`。默认写入被 Git 忽略的 `local/q3-reproduction`，不会覆盖归档。

```sh
python -m pip install -r requirements-q3-research.txt
python scripts/q3_run_experiments.py
python scripts/q3_verify_experiments.py
python scripts/q3_check_reproduction.py
```

可选环境变量：`Q3_OUTPUT_ROOT` 指向独立输出目录；`Q3_RAW_ROOT` 指向受控附件根目录，以额外核验 C7。无需下载原始题目即可重跑数值结果；这不等于重新核验原始采集链。

重跑会校验三份冻结数值输入的 SHA256；不匹配立即失败。脚本不重拟合 Q2，也不会接入新校准候选。数值计算无随机抽样，seed 不适用。实际软件版本写入运行 manifest；环境版本固定见依赖文件。

检查脚本对 7 张 CSV 按原行列顺序比较，rtol/atol 均为 1e-10；独立复核 JSON 比较数值与起点数量；模型预测、预算、配比和无提质收益基线的断言在实验脚本内执行。结果见 [reproduction_verification.json](reproduction_verification.json)。历史 CSV 字节保留，便携脚本修改单独登记哈希。

48 情景共 144 个 SLSQP 起点；138 次成功且可行，6 次不满足这一条件，均未算作通过。每个情景至少有一个成功起点。首次跨 clip 拐点出现误差，后依据收益恒定、成本上升的支配关系缩减求解区间。详细失败限制见结果报告；不是对外部预测有效性的检验。
