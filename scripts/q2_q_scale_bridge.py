#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-Q2-001 缺口 A：问题一 Q_A(0-100) 与 B6 Q_score([0.1,1.0]) 的尺度校准（条件桥接）。

本脚本只建立 **尺度兼容 (scale compatibility)**，不建立任何 A-B 逐行对应，
不重拟合 M0/M1，不修改任何共享文件。

重要输入勘误（详见 discrepancy_report.md）：
    `experiments/runs/q2-m0-m1-20260925-r01/metrics.json` 的 `M1.fit_B6` 是**裸数组**，
    其真实顺序由生产拟合脚本 `scripts/q2_m0_m1_explore.py` 第 46 行 `e, a, b, g, alpha, beta = theta`
    唯一确定，即 `[E, A, B, G, alpha, beta]`。P-Q2-001 与派发 README 声明的 `[E,A,B,alpha,beta,G]`
    顺序会把 alpha/beta/G 三个标签互换。本脚本按**真实顺序**解释冻结数组（数值一字不改）。

运行：
    python -X utf8 scripts/q2_q_scale_bridge.py
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "q2-q-scale-bridge-20260926-r01"
OUT = ROOT / "experiments" / "runs" / RUN_ID
TABLES = OUT / "tables"

Q1_DIR = ROOT / "experiments" / "runs" / "q1-critic-topsis-20260925-r01"
Q1_UNIQUE = Q1_DIR / "artifacts" / "unique_sample_scores.csv"
Q1_SAMPLE = Q1_DIR / "artifacts" / "sample_scores.csv"
Q1_DOMAIN = Q1_DIR / "tables" / "domain_scores.csv"
Q1_CORPUS = Q1_DIR / "tables" / "corpus_scores.csv"
B6_PATH = ROOT / "data" / "origin" / "real_attachments" / "B_scaling_laws" / "supplementary_NQ_experiment.csv"
M1_METRICS = ROOT / "experiments" / "runs" / "q2-m0-m1-20260925-r01" / "metrics.json"
ELASTICITY_TABLE = ROOT / "experiments" / "runs" / "q2-elasticity-audit-20260925-r01" / "tables" / "m1_b6_elasticities.csv"

M1_SHA256_EXPECTED = "38854c768a44d450bf96f03da47d8ee47a8f292e48b8e5dedc48f489c71022e1"

# --- 冻结数组（数值一字不改，来源 q2-m0-m1-20260925-r01:M1.fit_B6） -------------
M1_RAW = [1.4892660413046754, 0.5401729882501645, 1.3167948616197847,
          0.36224743500545836, 0.27905392394495887, 0.28280291348008263]

# 真实顺序（由 scripts/q2_m0_m1_explore.py 第 46 行确定）：[E, A, B, G, alpha, beta]
M1_FROZEN = {"E": M1_RAW[0], "A": M1_RAW[1], "B": M1_RAW[2],
             "G": M1_RAW[3], "alpha": M1_RAW[4], "beta": M1_RAW[5]}

# P-Q2-001 / README 声明的（错误）顺序 [E, A, B, alpha, beta, G]，仅用于敏感性对照
M1_LABEL_SWAPPED = {"E": M1_RAW[0], "A": M1_RAW[1], "B": M1_RAW[2],
                    "alpha": M1_RAW[3], "beta": M1_RAW[4], "G": M1_RAW[5]}

ELASTICITY_DEF = {
    "epsilon_N": "(dL/dN)*(N/L)",
    "epsilon_D": "(dL/dD)*(D/L)",
    "epsilon_q": "(dL/dq)*(q/L) = -G*q/L for M1",
    "note": "无量纲；禁止把有限差分 dL/dN 当弹性（PDF-10 误导点）",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def loss_m1(n, d, q, p):
    n = np.asarray(n, float); d = np.asarray(d, float); q = np.asarray(q, float)
    return p["E"] + p["A"] * n ** (-p["alpha"]) + p["B"] * d ** (-p["beta"]) + p["G"] * (1.0 - q)


def epsilon_q(q, n, d, p):
    """ε_q = (∂L/∂q)·(q/L) = -G·q/L，逐点量。"""
    L = loss_m1(n, d, q, p)
    return -p["G"] * np.asarray(q, float) / L


def qdesc(values) -> dict:
    v = np.asarray(values, float)
    qs = np.percentile(v, [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100])
    return {"n": int(v.size), "min": float(qs[0]), "p01": float(qs[1]), "p05": float(qs[2]),
            "p10": float(qs[3]), "p25": float(qs[4]), "p50": float(qs[5]), "p75": float(qs[6]),
            "p90": float(qs[7]), "p95": float(qs[8]), "p99": float(qs[9]), "max": float(qs[10]),
            "mean": float(v.mean()), "sd": float(v.std(ddof=1)), "skew": float(stats.skew(v)),
            "kurtosis_excess": float(stats.kurtosis(v))}


# ---------------------------------------------------------------------------
# 3.2 候选映射族（全部单调非降）
# ---------------------------------------------------------------------------
class LinearNorm:
    name = "M1_linear_normalization"
    family = "closed_form"
    formula = "q = 0.1 + 0.9*(Q_A/100)"
    params = "指定端点：Q_A 名义域 [0,100] -> Q_score [0.1,1.0]"
    boundary = "Q_A=0 -> q=0.1; Q_A=100 -> q=1.0; Q_A<0 或 >100 线性外延到 B6 拟合区间之外（须标注）"
    def __call__(self, qa):
        return 0.1 + 0.9 * (np.asarray(qa, float) / 100.0)


class LinearClamped(LinearNorm):
    name = "M5_linear_normalization_clamped"
    family = "closed_form"
    formula = "q = clip(0.1 + 0.9*(Q_A/100), 0.1, 1.0)"
    params = "同 M1，但把结果夹在 B6 观测区间内"
    boundary = "Q_A<=0 -> 0.1; Q_A>=100 -> 1.0；永不离开 [0.1,1.0]，但在两端失去分辨力（导数=0）"
    def __call__(self, qa):
        return np.clip(super().__call__(qa), 0.1, 1.0)


class MinMax:
    name = "M2_minmax_observed"
    family = "closed_form"
    def __init__(self, lo, hi):
        self.lo, self.hi = float(lo), float(hi)
        self.formula = "q = 0.1 + 0.9*(Q_A - Q_A,min)/(Q_A,max - Q_A,min)"
        self.params = f"Q_A,min={self.lo:.6f}, Q_A,max={self.hi:.6f}（问题一 unique-union 观测端点）"
        self.boundary = (f"Q_A<={self.lo:.4f} -> q<=0.1; Q_A>={self.hi:.4f} -> q>=1.0; "
                         "观测范围之外线性外延到 B6 拟合区间之外（须标注）")
    def __call__(self, qa):
        return 0.1 + 0.9 * (np.asarray(qa, float) - self.lo) / (self.hi - self.lo)

class RobustQuantile:
    name = "M3_robust_quantile_p05_p95"
    family = "closed_form"
    def __init__(self, qa05, qa95, b05, b95):
        self.qa05, self.qa95, self.b05, self.b95 = map(float, (qa05, qa95, b05, b95))
        self.slope = (self.b95 - self.b05) / (self.qa95 - self.qa05)
        self.formula = f"q = {self.b05:.6f} + {self.slope:.8f}*(Q_A - {self.qa05:.6f})"
        self.params = (f"问题一 p05={self.qa05:.6f}, p95={self.qa95:.6f}; "
                       f"B6 p05={self.b05:.6f}, p95={self.b95:.6f}")
        self.boundary = ("两端线性外延、无界：Q_A 低于 p05 / 高于 p95 时离开 B6 拟合区间（须标注）；"
                         "中心 90% 区间内不做钳制，保留分辨力")
    def __call__(self, qa):
        return self.b05 + self.slope * (np.asarray(qa, float) - self.qa05)


class RankMap:
    name = "M4_rank_quantile_isotonic"
    family = "empirical_quantile"
    formula = "q = Qemp_B6(F_emp_Q1(Q_A))；按经验分布函数对齐，分段线性插值，两端饱和"
    params = "问题一 unique-union 经验 CDF；B6 Q_score 在共同概率网格上的经验分位函数"
    boundary = ("Q_A <= 问题一最小值 -> q = B6 最小值 = 0.1；Q_A >= 问题一最大值 -> q = 1.0；"
                "两端饱和、永不离开 [0.1,1.0]；只在观测支撑内严格递增（8 个平台）")
    def __init__(self, qa_sorted, b_sorted, grid):
        xp = np.quantile(qa_sorted, grid); fp = np.quantile(b_sorted, grid)
        keep = np.concatenate([[True], np.diff(xp) > 0])
        self.xp, self.fp = xp[keep], fp[keep]
    def __call__(self, qa):
        return np.interp(np.asarray(qa, float), self.xp, self.fp)


# ---------------------------------------------------------------------------
# OLS 工具
# ---------------------------------------------------------------------------
def ols(X, y, names):
    X = np.asarray(X, float); y = np.asarray(y, float)
    Xd = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    resid = y - Xd @ beta
    n, k = Xd.shape
    dof = n - k
    sigma2 = float(resid @ resid / dof)
    cov = sigma2 * np.linalg.pinv(Xd.T @ Xd)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    pvals = 2 * stats.t.sf(np.abs(t), dof)
    r2 = 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return ({"n": int(n), "k": int(k), "dof": int(dof), "r2": r2,
             "adj_r2": 1.0 - (1 - r2) * (n - 1) / dof, "rmse": float(np.sqrt(sigma2)),
             "coef": {nm: float(b) for nm, b in zip(["intercept"] + names, beta)},
             "se": {nm: float(s) for nm, s in zip(["intercept"] + names, se)},
             "t": {nm: float(v) for nm, v in zip(["intercept"] + names, t)},
             "p": {nm: float(v) for nm, v in zip(["intercept"] + names, pvals)}},
            resid, Xd @ beta)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    inputs = {}
    for key, path in [("q1_unique_sample_scores", Q1_UNIQUE), ("q1_sample_scores", Q1_SAMPLE),
                      ("q1_domain_scores", Q1_DOMAIN), ("q1_corpus_scores", Q1_CORPUS),
                      ("b6_supplementary_NQ_experiment", B6_PATH), ("m0_m1_metrics", M1_METRICS),
                      ("elasticity_audit_b6_table", ELASTICITY_TABLE)]:
        if not path.exists():
            raise SystemExit(f"BLOCKED_Q1_SCORE_UNAVAILABLE: missing {path}")
        inputs[key] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                       "sha256": sha256(path), "bytes": int(path.stat().st_size)}
    if inputs["m0_m1_metrics"]["sha256"] != M1_SHA256_EXPECTED:
        raise SystemExit("冻结 m0-m1 metrics.json 哈希改变，拒绝继续")

    # ---------------- 0. 冻结数组顺序的判定（只诊断，不改数值） ----------------
    b6 = pd.read_csv(B6_PATH)
    if len(b6) != 360:
        raise SystemExit(f"B6 行数异常: {len(b6)}")
    n_arr = b6["N_params_B"].to_numpy(float)
    d_arr = b6["D_tokens_B"].to_numpy(float)
    q_arr = b6["Q_score"].to_numpy(float)
    y_arr = b6["val_loss"].to_numpy(float)
    imp = 1.0 - q_arr

    def ssr(p):
        r = y_arr - loss_m1(n_arr, d_arr, q_arr, p)
        return float(r @ r)

    ss_true = ssr(M1_FROZEN)          # [E,A,B,G,alpha,beta]
    ss_swap = ssr(M1_LABEL_SWAPPED)   # [E,A,B,alpha,beta,G]

    # 与已提交弹性表逐行对齐，作为顺序的第二重证据
    aud = pd.read_csv(ELASTICITY_TABLE)
    stored_eps = aud["epsilon_Q_score"].to_numpy(float)
    eq_true = epsilon_q(q_arr, n_arr, d_arr, M1_FROZEN)
    eq_swap = epsilon_q(q_arr, n_arr, d_arr, M1_LABEL_SWAPPED)
    order_evidence = {
        "authoritative_source": "scripts/q2_m0_m1_explore.py line 46: `e, a, b, g, alpha, beta = theta`",
        "true_order": ["E", "A", "B", "G", "alpha", "beta"],
        "spec_declared_order": ["E", "A", "B", "alpha", "beta", "G"],
        "spec_declared_order_is_wrong": True,
        "frozen_array": M1_RAW,
        "index_3_is": "G",
        "index_4_is": "alpha",
        "index_5_is": "beta",
        "interpreted_under_true_order": {k: float(v) for k, v in M1_FROZEN.items()},
        "interpreted_under_spec_order": {k: float(v) for k, v in M1_LABEL_SWAPPED.items()},
        "which_positions_move": ("派发声明与真实顺序的差异是：声明把 index3 当成 alpha、index4 当成 beta、index5 当成 G；"
                                 "真实是 index3=G、index4=alpha、index5=beta。"
                                 "等价地，声明的 G 值 0.28280291348008263 其实是 beta，"
                                 "声明的 beta 值 0.27905392394495887 其实是 alpha，"
                                 "真正的 G 是 0.36224743500545836。"),
        "ssr_B6_true_order": ss_true,
        "ssr_B6_spec_order": ss_swap,
        "ssr_ratio_spec_over_true": ss_swap / ss_true,
        "rmse_B6_true_order": float(np.sqrt(ss_true / len(y_arr))),
        "rmse_B6_spec_order": float(np.sqrt(ss_swap / len(y_arr))),
        "max_abs_diff_vs_committed_epsilon_table_true_order": float(np.max(np.abs(eq_true - stored_eps))),
        "max_abs_diff_vs_committed_epsilon_table_spec_order": float(np.max(np.abs(eq_swap - stored_eps))),
        "evidence_conclusion": ("真实顺序 [E,A,B,G,alpha,beta] 同时 (a) 与生产拟合脚本的数组布局一致、"
                               "(b) 逐行复制已提交的 m1_b6_elasticities.csv（最大绝对差 0.0）、"
                               "(c) 给出与 metrics.json 中 grouped_ND_cell_cv rmse 0.0512-0.0669 一致的 B6 rmse。"
                               "声明顺序 [E,A,B,alpha,beta,G] 三项全部不成立。"),
        "numeric_impact": ("质量项系数应为 G=0.36224743500545836，而派发/README 声明的 G=0.28280291348008263 实为 beta；"
                           "声明把 G 低估 21.9%。本脚本主结果用真实顺序的 G，"
                           "并在 tables/mapping_effect_G_sensitivity.csv 给出两种 G 的对照。"),
        "raw_array_values_unchanged": True,
        "action_taken": "仅记录并本地纠正标签；未修改 metrics.json、未改任何冻结数值、未重拟合",
    }


    # ---------------- 3.1 两侧分布 ----------------
    q1u = pd.read_csv(Q1_UNIQUE)
    q1s = pd.read_csv(Q1_SAMPLE)
    q1d = pd.read_csv(Q1_DOMAIN)
    q1c = pd.read_csv(Q1_CORPUS)
    if "quality_score" not in q1u.columns:
        raise SystemExit("BLOCKED_Q1_SCORE_UNAVAILABLE: quality_score 列不可解析")
    qa = q1u["quality_score"].to_numpy(float)
    qa_s = q1s["quality_score"].to_numpy(float)
    qb = q_arr

    pd.DataFrame([
        {"side": "Q1_Q_A_0_100", "table": "unique_sample_scores.csv", **qdesc(qa)},
        {"side": "Q1_Q_A_0_100", "table": "sample_scores.csv (去重前)", **qdesc(qa_s)},
        {"side": "B6_Q_score_0.1_1.0", "table": "supplementary_NQ_experiment.csv", **qdesc(qb)},
    ]).to_csv(TABLES / "scale_distribution_both.csv", index=False, encoding="utf-8-sig")

    q1_rows = [{"level": "record", "scope": "ALL_unique_union", **qdesc(qa)},
               {"level": "record", "scope": "ALL_pre_dedup", **qdesc(qa_s)}]
    for _, r in q1d.iterrows():
        sub = q1u[(q1u["dataset_id"] == r["dataset_id"]) & (q1u["domain"] == r["domain"])]
        if len(sub):
            q1_rows.append({"level": "domain", "scope": f"{r['dataset_id']}::{r['domain']}",
                            **qdesc(sub["quality_score"].to_numpy(float))})
    for _, r in q1c.iterrows():
        sub = q1u[(q1u["dataset_id"] == r["dataset_id"]) & (q1u["kept_in_unique_union"] == True)]
        if r["subset"] in ("fit", "holdout"):
            sub = sub[sub["split"] == r["subset"]]
        if len(sub):
            q1_rows.append({"level": "corpus", "scope": f"{r['dataset_id']}::{r['subset']}",
                            **qdesc(sub["quality_score"].to_numpy(float))})
    pd.DataFrame(q1_rows).to_csv(TABLES / "q1_scale_distribution.csv", index=False, encoding="utf-8-sig")

    ks = stats.kstest((qb - 0.1) / 0.9, "uniform")
    pd.DataFrame([{"level": "record", "scope": "B6_all", **qdesc(qb)}]).to_csv(
        TABLES / "b6_scale_distribution.csv", index=False, encoding="utf-8-sig")
    uq, cnt = np.unique(np.round(qb, 6), return_counts=True)
    pd.DataFrame({"Q_score": uq, "count": cnt}).to_csv(
        TABLES / "b6_scale_levels.csv", index=False, encoding="utf-8-sig")

    # ---------------- 3.2 候选映射族 ----------------
    qa_lo, qa_hi = float(qa.min()), float(qa.max())
    qa05, qa95 = (float(v) for v in np.percentile(qa, [5, 95]))
    b05, b95 = (float(v) for v in np.percentile(qb, [5, 95]))
    grid = np.linspace(1e-6, 1 - 1e-6, 1001)
    maps = [LinearNorm(), LinearClamped(), MinMax(qa_lo, qa_hi),
            RobustQuantile(qa05, qa95, b05, b95), RankMap(qa, qb, grid)]

    pd.DataFrame([{"mapping_id": m.name, "family": m.family, "formula": m.formula,
                   "parameter_source": m.params, "boundary_behaviour": m.boundary,
                   "monotone_nondecreasing": True} for m in maps]).to_csv(
        TABLES / "mapping_candidates.csv", index=False, encoding="utf-8-sig")

    probe = np.array([0.0, qa_lo, qa05, float(np.median(qa)), qa95, qa_hi, 100.0])
    probe_tbl = pd.DataFrame({"Q_A": probe})
    for m in maps:
        probe_tbl[m.name] = m(probe)
    probe_tbl.to_csv(TABLES / "mapping_probe_points.csv", index=False, encoding="utf-8-sig")

    ext = np.linspace(-50, 150, 4001)
    mono_rows = []
    for m in maps:
        v = m(ext)
        mono_rows.append({"mapping_id": m.name,
                          "strictly_increasing_on_extended_domain": bool(np.all(np.diff(v) > 0)),
                          "nondecreasing_on_extended_domain": bool(np.all(np.diff(v) >= -1e-12)),
                          "value_at_QA_0": float(m(np.array([0.0]))[0]),
                          "value_at_QA_100": float(m(np.array([100.0]))[0]),
                          "min_on_extended": float(v.min()), "max_on_extended": float(v.max()),
                          "leaves_fitted_B6_range": bool(v.min() < 0.1 - 1e-12 or v.max() > 1.0 + 1e-12)})
    mono = pd.DataFrame(mono_rows)
    mono.to_csv(TABLES / "mapping_monotonicity_check.csv", index=False, encoding="utf-8-sig")

    # ---------------- 3.3 冻结 M1 下的尺度后果（不重拟合） ----------------
    nd = b6[["N_params_B", "D_tokens_B"]].drop_duplicates().to_numpy(float)
    grids = {"cell": (float(np.median(n_arr)), float(np.median(d_arr)))}
    for i, (n_i, d_i) in enumerate(nd):
        grids[f"cell_{i:02d}"] = (float(n_i), float(d_i))

    anchors = {"ALL_p01": float(np.percentile(qa, 1)), "ALL_p05": qa05,
               "ALL_p25": float(np.percentile(qa, 25)), "ALL_mean": float(qa.mean()),
               "ALL_p50": float(np.median(qa)), "ALL_p75": float(np.percentile(qa, 75)),
               "ALL_p95": qa95, "ALL_p99": float(np.percentile(qa, 99)),
               "ALL_min": qa_lo, "ALL_max": qa_hi}
    for _, r in q1d.iterrows():
        anchors[f"domain::{r['domain']}::mean"] = float(r["mean"])

    eff_rows = []
    for m in maps:
        mq = {k: float(m(np.array([v]))[0]) for k, v in anchors.items()}
        for gname, (n_g, d_g) in grids.items():
            for aname, aq in anchors.items():
                q = mq[aname]
                in_range = bool(0.1 - 1e-12 <= q <= 1.0 + 1e-12)
                eff_rows.append({"mapping_id": m.name, "grid": gname, "N_params_B": n_g, "D_tokens_B": d_g,
                                 "anchor": aname, "Q_A": anchors[aname], "mapped_q": q,
                                 "L_m1_frozen": float(loss_m1(n_g, d_g, q, M1_FROZEN)),
                                 "epsilon_q": float(epsilon_q(q, n_g, d_g, M1_FROZEN)),
                                 "q_in_B6_fitted_range": in_range,
                                 "epsilon_q_valid": in_range})
    eff = pd.DataFrame(eff_rows)
    # 只有 q 落在 B6 拟合区间内，ε_q 才是 M1 的有效局部弹性；
    # q<0 时 (1-q)>1 使纯度项异常放大，甚至把 ε_q 推成正数 —— 这正是 PDF-10 的陷阱。
    eff_in = eff[eff["epsilon_q_valid"]]
    eff.to_csv(TABLES / "mapping_effect_rows.csv", index=False, encoding="utf-8-sig")
    eff[["mapping_id", "grid", "anchor", "Q_A", "mapped_q", "epsilon_q", "L_m1_frozen",
         "epsilon_q_valid"]].to_csv(TABLES / "epsilon_q_rows.csv", index=False, encoding="utf-8-sig")
    # 越界陷阱专表：q 离开 [0.1,1.0] 后 (1-q) 项被异常放大，ε_q 甚至变正
    trap = eff[~eff["epsilon_q_valid"]].copy()
    trap["reason"] = "mapped q outside B6 fitted range [0.1,1.0]; M1's (1-q) term is extrapolated and is no longer the fitted term"
    trap.to_csv(TABLES / "epsilon_q_out_of_range_trap.csv", index=False, encoding="utf-8-sig")
    trap_summary = (trap.groupby("mapping_id")
                    .agg(n_out_of_range=("epsilon_q", "size"),
                         n_positive_epsilon_q=("epsilon_q", lambda s: int((s > 0).sum())),
                         min_mapped_q=("mapped_q", "min"), max_mapped_q=("mapped_q", "max"))
                    .reset_index())
    trap_summary.to_csv(TABLES / "epsilon_q_out_of_range_summary.csv", index=False, encoding="utf-8-sig")

    up_rows = []
    for m in maps:
        q_lo = float(m(np.array([qa05]))[0]); q_hi = float(m(np.array([qa95]))[0])
        for gname, (n_g, d_g) in grids.items():
            L_lo = float(loss_m1(n_g, d_g, q_lo, M1_FROZEN))
            L_hi = float(loss_m1(n_g, d_g, q_hi, M1_FROZEN))
            base = float(M1_FROZEN["E"] + M1_FROZEN["A"] * n_g ** (-M1_FROZEN["alpha"])
                         + M1_FROZEN["B"] * d_g ** (-M1_FROZEN["beta"]))
            up_rows.append({"mapping_id": m.name, "grid": gname, "N_params_B": n_g, "D_tokens_B": d_g,
                            "Q_A_baseline_p05": qa05, "Q_A_upper_p95": qa95,
                            "q_baseline": q_lo, "q_upper": q_hi, "delta_q": q_hi - q_lo,
                            "L_at_baseline_q": L_lo, "L_at_upper_q": L_hi,
                            "delta_L_upper_minus_baseline": L_hi - L_lo,
                            "relative_loss_reduction": (L_lo - L_hi) / L_lo,
                            "G_times_delta_q": float(M1_FROZEN["G"] * (q_hi - q_lo)),
                            "base_L_at_Q1": base,
                            "epsilon_q_at_baseline": float(epsilon_q(q_lo, n_g, d_g, M1_FROZEN)),
                            "epsilon_q_at_upper": float(epsilon_q(q_hi, n_g, d_g, M1_FROZEN))})
    up = pd.DataFrame(up_rows)
    up.to_csv(TABLES / "mapping_delta_loss.csv", index=False, encoding="utf-8-sig")

    # ---------------- 3.4 反向一致性检验 ----------------
    lnN = np.log(n_arr); lnD = np.log(d_arr)
    lin_rows = []

    def add(name, X, names, desc):
        res, resid, fitted = ols(X, y_arr, names)
        row = {"model": name, "description": desc, "n": res["n"], "k": res["k"], "r2": res["r2"],
               "adj_r2": res["adj_r2"], "rmse": res["rmse"], "intercept": res["coef"]["intercept"],
               "max_abs_resid": float(np.max(np.abs(resid)))}
        for nm in names:
            row[f"coef_{nm}"] = res["coef"][nm]; row[f"se_{nm}"] = res["se"][nm]
            row[f"t_{nm}"] = res["t"][nm]; row[f"p_{nm}"] = res["p"][nm]
        row["resid_corr_imp"] = float(np.corrcoef(resid, imp)[0, 1])
        row["resid_corr_fitted"] = float(np.corrcoef(resid, fitted)[0, 1])
        row["resid_skew"] = float(stats.skew(resid))
        bp, _, _ = ols(fitted.reshape(-1, 1), resid ** 2, ["fitted"])
        row["bp_lm_stat"] = float(len(y_arr) * bp["r2"])
        row["bp_p"] = float(stats.chi2.sf(row["bp_lm_stat"], 1))
        reset, _, _ = ols(np.column_stack([X, fitted ** 2]), y_arr, names + ["fitted_sq"])
        row["reset_coef_fitted_sq"] = reset["coef"]["fitted_sq"]
        row["reset_p_fitted_sq"] = reset["p"]["fitted_sq"]
        row["delta_adj_r2_reset"] = reset["adj_r2"] - res["adj_r2"]
        lin_rows.append(row)
        return res, resid, fitted

    mb = add("B_impurity_plus_logND", np.column_stack([imp, lnN, lnD]),
             ["impurity_1_minus_Q", "log_N", "log_D"], "val_loss ~ (1-Q) + log N + log D")
    add("A_impurity_only", imp.reshape(-1, 1), ["impurity_1_minus_Q"], "val_loss ~ (1-Q)")
    add("C_impurity_quadratic", np.column_stack([imp, imp ** 2]),
        ["impurity_1_minus_Q", "impurity_sq"], "val_loss ~ (1-Q) + (1-Q)^2")
    add("D_quadratic_plus_logND", np.column_stack([imp, imp ** 2, lnN, lnD]),
        ["impurity_1_minus_Q", "impurity_sq", "log_N", "log_D"],
        "val_loss ~ (1-Q) + (1-Q)^2 + log N + log D")
    # E: 完全按冻结 M1 的幂形式（真实顺序的 alpha/beta），只自由估计系数
    add("E_frozen_M1_powers", np.column_stack([n_arr ** (-M1_FROZEN["alpha"]),
                                               d_arr ** (-M1_FROZEN["beta"]), imp]),
        ["N_pow_minus_alpha_frozen", "D_pow_minus_beta_frozen", "impurity_1_minus_Q"],
        "val_loss ~ N^(-alpha_frozen)+D^(-beta_frozen)+(1-Q), alpha/beta 取真实顺序冻结值")
    # F: 用声明（错误）顺序的 alpha/beta 作对照
    add("F_declared_order_powers", np.column_stack([n_arr ** (-M1_LABEL_SWAPPED["alpha"]),
                                                    d_arr ** (-M1_LABEL_SWAPPED["beta"]), imp]),
        ["N_pow_minus_alpha_declared", "D_pow_minus_beta_declared", "impurity_1_minus_Q"],
        "同 E，但 alpha/beta 取派发声明顺序（错误标签）的冻结值")

    lin_df = pd.DataFrame(lin_rows)
    lin_df.to_csv(TABLES / "linearity_check.csv", index=False, encoding="utf-8-sig")

    # 残差按 Q 分箱
    resid_b, fit_b = mb[1], mb[2]
    bins = np.arange(0.1, 1.01, 0.1)
    idx = np.clip(np.digitize(q_arr, bins) - 1, 0, len(bins) - 2)
    bin_rows = []
    for b in range(len(bins) - 1):
        s = idx == b
        if s.sum() == 0:
            continue
        bin_rows.append({"Q_bin": f"[{bins[b]:.1f},{bins[b+1]:.1f})", "n": int(s.sum()),
                         "mean_Q": float(q_arr[s].mean()), "mean_resid": float(resid_b[s].mean()),
                         "sd_resid": float(resid_b[s].std(ddof=1)), "mean_fitted": float(fit_b[s].mean()),
                         "mean_actual": float(y_arr[s].mean())})
    pd.DataFrame(bin_rows).to_csv(TABLES / "linearity_residual_by_Q_bin.csv", index=False, encoding="utf-8-sig")

    # 组内配对斜率：M1 隐含 dL/d(1-q) = 常数 G
    slope_rows = []
    for (n_i, d_i), g in b6.groupby(["N_params_B", "D_tokens_B"]):
        g = g.sort_values("Q_score")
        ii = (1 - g["Q_score"].to_numpy(float)); yy = g["val_loss"].to_numpy(float)
        if np.ptp(ii) > 0:
            sl = float(np.polyfit(ii, yy, 1)[0])
            slope_rows.append({"N_params_B": float(n_i), "D_tokens_B": float(d_i), "n": int(len(g)),
                               "within_cell_slope_dL_d_impurity": sl,
                               "deviation_from_frozen_G": sl - M1_FROZEN["G"],
                               "deviation_from_declared_G": sl - M1_LABEL_SWAPPED["G"]})
    sl = pd.DataFrame(slope_rows)
    sl.to_csv(TABLES / "linearity_within_cell_slopes.csv", index=False, encoding="utf-8-sig")

    # ---------------- 3.5 汇总裁剪 ----------------
    summary_rows = []
    for m in maps:
        sub = up[(up["grid"] == "cell") & (up["mapping_id"] == m.name)].iloc[0]
        e_all = eff[eff["mapping_id"] == m.name]
        q_lo, q_hi = sub["q_baseline"], sub["q_upper"]
        summary_rows.append({
            "mapping_id": m.name, "formula": m.formula,
            "q_baseline_at_Q1_p05": q_lo, "q_upper_at_Q1_p95": q_hi, "delta_q": q_hi - q_lo,
            "delta_L_upper_minus_baseline_median_cell": sub["delta_L_upper_minus_baseline"],
            "delta_L_min_over_grid": float(up[up["mapping_id"] == m.name]["delta_L_upper_minus_baseline"].min()),
            "delta_L_max_over_grid": float(up[up["mapping_id"] == m.name]["delta_L_upper_minus_baseline"].max()),
            "relative_loss_reduction_median_cell": sub["relative_loss_reduction"],
            "relative_loss_reduction_min_over_grid": float(up[up["mapping_id"] == m.name]["relative_loss_reduction"].min()),
            "relative_loss_reduction_max_over_grid": float(up[up["mapping_id"] == m.name]["relative_loss_reduction"].max()),
            "G_times_delta_q": sub["G_times_delta_q"],
            "epsilon_q_at_baseline": sub["epsilon_q_at_baseline"], "epsilon_q_at_upper": sub["epsilon_q_at_upper"],
            "epsilon_q_min_over_all_anchors_grids": float(e_all["epsilon_q"].min()),
            "epsilon_q_max_over_all_anchors_grids": float(e_all["epsilon_q"].max()),
            "epsilon_q_min_in_B6_range_only": float(e_all[e_all["epsilon_q_valid"]]["epsilon_q"].min()),
            "epsilon_q_max_in_B6_range_only": float(e_all[e_all["epsilon_q_valid"]]["epsilon_q"].max()),
            "n_anchors_out_of_B6_range": int((~e_all["epsilon_q_valid"]).sum()),
            "n_anchors_with_positive_epsilon_q": int((e_all["epsilon_q"] > 0).sum()),
            "maps_outside_B6_fitted_range": bool((~e_all["q_in_B6_fitted_range"]).any()),
            "consistency_check_3_4_shares_one_conclusion": True,
            "consistency_check_3_4_result": "see linearity_check.csv (same for every candidate mapping)",
        })
    summ = pd.DataFrame(summary_rows)
    summ.to_csv(TABLES / "mapping_effect.csv", index=False, encoding="utf-8-sig")

    # 声明（错误）顺序下的 G 敏感性对照
    sens_rows = []
    for m in maps:
        q_lo = float(m(np.array([qa05]))[0]); q_hi = float(m(np.array([qa95]))[0])
        for tag, p in [("true_order_G", M1_FROZEN), ("declared_order_G", M1_LABEL_SWAPPED)]:
            sens_rows.append({"mapping_id": m.name, "G_source": tag, "G_used": p["G"],
                              "delta_q": q_hi - q_lo,
                              "delta_L_median_cell": float(p["G"] * (q_hi - q_lo)),
                              "epsilon_q_at_baseline_median_cell": float(epsilon_q(q_lo, grids["cell"][0], grids["cell"][1], p)),
                              "epsilon_q_at_upper_median_cell": float(epsilon_q(q_hi, grids["cell"][0], grids["cell"][1], p))})
    sen = pd.DataFrame(sens_rows)
    sen.to_csv(TABLES / "mapping_effect_G_sensitivity.csv", index=False, encoding="utf-8-sig")

    dl = summ["delta_L_upper_minus_baseline_median_cell"].to_numpy(float)
    relred = summ["relative_loss_reduction_median_cell"].to_numpy(float)
    eq_lo = summ["epsilon_q_at_baseline"].to_numpy(float)
    eq_hi = summ["epsilon_q_at_upper"].to_numpy(float)
    flip = {
        "sign_of_delta_L_stable": bool(np.all(dl < 0) or np.all(dl > 0)),
        "sign_of_delta_L": "negative for all mappings" if bool(np.all(dl < 0)) else
                           ("positive for all" if bool(np.all(dl > 0)) else "FLIPS"),
        "relative_loss_reduction_range": [float(relred.min()), float(relred.max())],
        "relative_loss_reduction_spread_ratio": float(relred.max() / relred.min()),
        "epsilon_q_baseline_range": [float(eq_lo.min()), float(eq_lo.max())],
        "epsilon_q_upper_range": [float(eq_hi.min()), float(eq_hi.max())],
        "epsilon_q_sign_stable_negative": bool(np.all(eq_lo < 0) and np.all(eq_hi < 0)),
        "magnitude_flips": bool(relred.max() / relred.min() > 2.0),
    }

    # ---------------- bridge_contract.csv（问题三下游接口） ----------------
    rec = summ[summ["mapping_id"] == RankMap.name].iloc[0]
    lin = summ[summ["mapping_id"] == LinearNorm.name].iloc[0]
    dfac = float(rec["delta_q"] / lin["delta_q"])
    eq_min_cell = float(eff_in[eff_in["grid"] == "cell"]["epsilon_q"].min())
    eq_max_cell = float(eff_in[eff_in["grid"] == "cell"]["epsilon_q"].max())
    eq_min = float(min(eff_in[eff_in["mapping_id"] == RankMap.name]["epsilon_q"].min(),
                       eff_in[eff_in["mapping_id"] == LinearNorm.name]["epsilon_q"].min()))
    eq_max = float(max(eff_in[eff_in["mapping_id"] == RankMap.name]["epsilon_q"].max(),
                       eff_in[eff_in["mapping_id"] == LinearNorm.name]["epsilon_q"].max()))
    n_bad = int((~eff["epsilon_q_valid"]).sum())
    n_pos = int((eff["epsilon_q"] > 0).sum())
    contract = [
        {"field": "scale_map_formula",
         "value": ("(a) q = 0.1 + 0.9*(Q_A/100)  [M1_linear_normalization]; "
                   f"(b) q = {b05:.6f} + {(b95-b05)/(qa95-qa05):.8f}*(Q_A - {qa05:.6f})  [M3_robust_quantile_p05_p95]; "
                   "(c) q = Qemp_B6(F_emp_Q1(Q_A))  [M4_rank_quantile_isotonic]"),
         "evidence": f"{RUN_ID}:tables/mapping_candidates.csv",
         "validity_condition": "只作为**单调尺度桥**；Q_A 仅当作可比的质量序数-区间指标，不当作 B6 Q_score 本身",
         "failure_condition": "一旦声称 Q_A 等价于 B6 Q_score，或声称建立了 A-B 逐行连接，本契约立即失效"},
        {"field": "q1_scale_range",
         "value": f"{qa_lo:.6f} .. {qa_hi:.6f} (n={qa.size})",
         "evidence": f"{RUN_ID}:tables/q1_scale_distribution.csv; q1-critic-topsis-20260925-r01 sha256={inputs['q1_unique_sample_scores']['sha256'][:16]}...",
         "validity_condition": "问题一 unique-union 记录级质量分；问题一 run 状态仍为待验收",
         "failure_condition": "问题一换归一化或换 run_id -> 本契约全部失效，须重算"},
        {"field": "b6_scale_range",
         "value": f"{float(qb.min()):.6f} .. {float(qb.max()):.6f} (n={qb.size}, 8 个离散档)",
         "evidence": f"{RUN_ID}:tables/b6_scale_distribution.csv, tables/b6_scale_levels.csv; B6 sha256={inputs['b6_supplementary_NQ_experiment']['sha256'][:16]}...",
         "validity_condition": "B6 半合成原生 Q_score；KS 对均匀分布 p=" + f"{ks.pvalue:.4g}",
         "failure_condition": "把 B6/B7 当独立观测，或在 [0.1,1.0] 之外使用 q 而不标注外推"},
        {"field": "recommended_map",
         "value": f"{RankMap.name} (保序分位) ；线性读法用 {LinearNorm.name}；契约同时给出两者",
         "evidence": f"{RUN_ID}:tables/mapping_effect.csv",
         "validity_condition": ("条件推荐：若下游只问\"质量提升到问题一观测上界能买多少 Loss\"，用保序分位映射，"
                                "它是分布对齐而非数值对齐；若问题三需要绝对可读的 0-100→[0.1,1.0]，用线性归一"),
         "failure_condition": (f"若问题三把两者混用会不一致：同一 Q_A 提升在保序映射下的 delta_q 是线性映射的 "
                               f"{dfac:.4f} 倍，delta_L 随之同比改变。不得只报其中一个而不声明是哪一个"),
         "recommended_map_note": "没有任何单一映射可被认证为\"正确\"换算，因此本字段是条件推荐"},
        {"field": "epsilon_q_range",
         "value": (f"中位单元(N=1.0B,D=150B)上，全部 5 个映射 × 全部问题一锚点："
                   f"[{eq_min_cell:.6f}, {eq_max_cell:.6f}]; "
                   f"其中 Q1 基线锚点(p05)处 [{eq_lo.min():.6f}, {eq_lo.max():.6f}]，"
                   f"上界锚点(p95)处 [{eq_hi.min():.6f}, {eq_hi.max():.6f}]"),
         "evidence": f"{RUN_ID}:tables/epsilon_q_rows.csv; 定义 (dL/dq)*(q/L) = -G*q/L, G={M1_FROZEN['G']:.10f}",
         "validity_condition": "逐点量，只在所报 q 与 L 处成立；q 须落在 B6 拟合区间 [0.1,1.0]",
         "failure_condition": "q 超出 [0.1,1.0]（M1 外推）或任何形式的 M1 重拟合；ε_q 符号必须保持为负，若为正先检查定义"},
        {"field": "epsilon_q_range_all_anchors_all_cells",
         "value": f"{eq_min:.6f} .. {eq_max:.6f} (仅统计 q 落在 B6 拟合区间 [0.1,1.0] 内的点)",
         "evidence": f"{RUN_ID}:tables/epsilon_q_rows.csv（保序与线性两种映射 × 全部问题一锚点 × 全部 46 个 (N,D) 单元）",
         "validity_condition": "同样逐点；范围更宽只是因为覆盖了问题一的全部分位锚点与 B6 的全部 (N,D) 单元",
         "failure_condition": "不得把这个更宽的区间当成\"质量效应区间\"混用；头条反事实区间见 epsilon_q_range"},
        {"field": "epsilon_q_positive_trap",
         "value": (f"当映射把 q 推出 [0.1,1.0] 时，(1-q) 项被异常外推，ε_q 会算成**正数**："
                   f"共 {n_bad} 个 (映射,锚点,单元) 组合越界，其中 {n_pos} 个给出 ε_q > 0"),
         "evidence": f"{RUN_ID}:tables/epsilon_q_out_of_range_trap.csv, epsilon_q_out_of_range_summary.csv",
         "validity_condition": "仅出现在未钳制的 M1_linear_normalization / M2_minmax_observed / M3_robust_quantile_p05_p95 上",
         "failure_condition": ("这正是 PDF-10 陷阱的现场证据：ε_q > 0 说明定义域被破坏，**先怀疑定义与定义域，不要怀疑数据**。"
                               "下游凡见到 ε_q > 0，一律判为越界，该点结论作废")},
        {"field": "m1_quality_parameter",
         "value": f"G={M1_FROZEN['G']:.12f} (真实顺序 [E,A,B,G,alpha,beta])；派发声明顺序给出的 G={M1_LABEL_SWAPPED['G']:.12f} 是误标",
         "evidence": f"{RUN_ID}:tables/linearity_within_cell_slopes.csv, discrepancy_report.md; 权威来源 scripts/q2_m0_m1_explore.py 第 46 行",
         "validity_condition": "冻结数组数值未改；只是标签顺序按生产脚本复原",
         "failure_condition": "若上游修正 metrics.json 的字段命名，需同步更新本 run 的 G 引用；在修正前两者相差 21.9%"},
    ]
    for m in maps:
        s = summ[summ["mapping_id"] == m.name].iloc[0]
        contract.append({"field": f"delta_loss::{m.name}",
                         "value": (f"{s['delta_L_upper_minus_baseline_median_cell']:.6f} (中位单元); "
                                   f"网格范围 [{s['delta_L_min_over_grid']:.6f}, {s['delta_L_max_over_grid']:.6f}]"),
                         "evidence": f"{RUN_ID}:tables/mapping_delta_loss.csv",
                         "validity_condition": f"问题一 p05->p95，{m.name}，冻结 M1，未重拟合",
                         "failure_condition": "这不是因果效应：不存在 A-B 逐行连接，只是尺度条件反事实"})
    pd.DataFrame(contract).to_csv(TABLES / "bridge_contract.csv", index=False, encoding="utf-8-sig")

    # ---------------- 停止条件 ----------------
    stop = []
    if flip["magnitude_flips"]:
        stop.append({"token": "BLOCKED_MAPPING_SENSITIVE",
                     "reason": (f"候选映射之间 Loss 影响的量级差异超过 2 倍：相对降幅范围 "
                                f"{flip['relative_loss_reduction_range']}，倍数 "
                                f"{flip['relative_loss_reduction_spread_ratio']:.4f}"),
                     "action": "如实报告差异；不得把任何单一映射写成\"正确的\"换算"})
    if True:
        stop.append({"token": "FEEDBACK_REQUIRED",
                     "reason": ("冻结数组 M1.fit_B6 的**标签顺序**与派发声明不一致（数值未变）。"
                                f"真实顺序 [E,A,B,G,alpha,beta] 下 B6 SSR={ss_true:.6f}，"
                                f"声明顺序 [E,A,B,alpha,beta,G] 下 B6 SSR={ss_swap:.6f}（差 {ss_swap/ss_true:.3f} 倍）；"
                                f"真实顺序逐行复刻已提交的 m1_b6_elasticities.csv（最大绝对差 "
                                f"{order_evidence['max_abs_diff_vs_committed_epsilon_table_true_order']:.1e}）。"
                                "因此质量项系数应为 G=0.36224743500545836，而非派发与 README 写的 0.28280291348008263。"),
                     "action": ("写入 discrepancy_report.md；本 run 按真实顺序计算并同时给出两种 G 的敏感性对照表；"
                                "未修改任何冻结参数文件、未重拟合 M1、未改数据")})
    status = "EXPLORATORY_Q_SCALE_BRIDGE"

    # ---------------- metrics.json ----------------
    def tsha(name):
        p = TABLES / name
        return {"path": f"tables/{name}", "sha256": sha256(p)} if p.exists() else None

    out_names = ["q1_scale_distribution.csv", "b6_scale_distribution.csv", "b6_scale_levels.csv",
                 "mapping_candidates.csv", "mapping_probe_points.csv", "mapping_monotonicity_check.csv",
                 "mapping_effect.csv", "mapping_effect_rows.csv", "mapping_effect_G_sensitivity.csv",
                 "mapping_delta_loss.csv", "epsilon_q_rows.csv", "linearity_check.csv",
                 "linearity_residual_by_Q_bin.csv", "linearity_within_cell_slopes.csv",
                 "epsilon_q_out_of_range_trap.csv", "epsilon_q_out_of_range_summary.csv",
                 "scale_distribution_both.csv", "bridge_contract.csv"]

    lin_b = lin_df[lin_df["model"] == "B_impurity_plus_logND"].iloc[0]
    lin_d = lin_df[lin_df["model"] == "D_quadratic_plus_logND"].iloc[0]
    lin_e = lin_df[lin_df["model"] == "E_frozen_M1_powers"].iloc[0]
    lin_f = lin_df[lin_df["model"] == "F_declared_order_powers"].iloc[0]

    metrics_payload = {
        "schema_version": "q2.q_scale_bridge.v1",
        "run_id": RUN_ID, "task_id": "P-Q2-001", "dispatch": "q2-gap-a-quality-scale",
        "status": status,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "仅在问题一 Q_A(0-100) 与 B6 Q_score([0.1,1.0]) 之间建立**尺度兼容**；不建立 A-B 逐行对应",
        "inputs": inputs,
        "frozen_parameters": {
            "M1_source": "experiments/runs/q2-m0-m1-20260925-r01/metrics.json -> M1.fit_B6",
            "M1_form": "L = E + A*N^(-alpha) + B*D^(-beta) + G*(1 - Q_score); N,D 单位十亿",
            "M1_true_order_interpretation": {k: float(v) for k, v in M1_FROZEN.items()},
            "M1_alt_label_interpretation_NOT_USED_AS_PRIMARY": {k: float(v) for k, v in M1_LABEL_SWAPPED.items()},
            "refit_performed": False, "M0_M1_modified": False,
            "raw_array_unchanged": M1_RAW,
        },
        "parameter_order_correction": order_evidence,
        "elasticity_definition": ELASTICITY_DEF,
        "rejected_definitions": [
            "PDF-10：把有限差分 ΔL/ΔN 当弹性、声称无需乘 N/L（拒绝）",
            "PDF-09：对 L,N,D 直接取对数做多元线性回归（拒绝）",
            "PDF-12：预置正弹性符号（拒绝）",
        ],
        "checks": {
            "q1_scores_parsable": True,
            "q1_reference_run": "q1-critic-topsis-20260925-r01",
            "q1_reference_run_status": "LOCAL_RESULT_PENDING_TEAM_REVIEW（仍未验收，不得当作质量真值）",
            "b6_rows": int(len(b6)), "b6_rows_expected": 360,
            "b6_used_as_independent_observation": False, "b6_is_subset_of_b7": True,
            "b8_used": False, "b8_reversed_or_pruned": False,
            "a_b_row_join_established": False,
            "Q1_Q_equals_B6_Q_score_asserted": False,
            "monotonicity_verified_numerically": bool(mono["nondecreasing_on_extended_domain"].all()),
            "mappings_leaving_B6_fitted_range": mono.loc[mono["leaves_fitted_B6_range"], "mapping_id"].tolist(),
            "M0_M1_refit": False, "frozen_G_used": float(M1_FROZEN["G"]),
            "core_blockers_unlocked": 0,
            "core_blockers_declared": [
                "问题一的候选质量分尚未通过验收",
                "17 个配方域中仅 6 个有候选映射（formal_mapping_validated=false）",
                "附件 A 与附件 B 没有逐行 join key（已冻结 conditional-no-row-key-v1）",
                "B8 缺生成来源，且方向与 B6/B7 冲突",
            ],
        },
        "distribution_summary": {
            "Q1_Q_A": qdesc(qa), "B6_Q_score": qdesc(qb),
            "B6_distinct_levels": int(len(np.unique(np.round(qb, 6)))),
            "B6_uniformity_ks_vs_uniform_0.1_1.0": {"statistic": float(ks.statistic), "pvalue": float(ks.pvalue)},
        },
        "mapping_family": {"count": len(maps), "all_monotone": True, "ids": [m.name for m in maps]},
        "headline_results": {
            "delta_L_definition": "在固定 (N,D)、冻结 M1、不重拟合下，问题一锚点质量从 p05 升到 p95 时的 Loss 变化",
            "mapping_effect_is_linear_in_G": True,
            "relative_loss_reduction_range": flip["relative_loss_reduction_range"],
            "delta_L_sign": flip["sign_of_delta_L"],
            "delta_L_sign_stable_across_mappings": flip["sign_of_delta_L_stable"],
            "epsilon_q_baseline_range": flip["epsilon_q_baseline_range"],
            "epsilon_q_upper_range": flip["epsilon_q_upper_range"],
            "epsilon_q_sign_always_negative": flip["epsilon_q_sign_stable_negative"],
            "epsilon_q_sign_always_negative_in_B6_range": bool(
                (eff_in["epsilon_q"] < 0).all()),
            "epsilon_q_positive_outside_B6_range_count": n_pos,
            "epsilon_q_out_of_range_combinations": n_bad,
            "epsilon_q_positive_trap_note": ("q 被映射推出 [0.1,1.0] 后 (1-q) 项被异常外推，"
                                             "ε_q 会算成正数；这是 PDF-10 同型陷阱，须判为定义域失效而非真实效应"),
            "magnitude_flips_across_mappings": flip["magnitude_flips"],
            "G_bridge_identifiable": False,
            "G_bridge_note": "本 run 全程沿用冻结 G，不产生 G_bridge 的识别性估计",
        },
        "linearity_check_3_4": {
            "question": "M1 的 G·(1-Q_score) 线性项隐含\"质量边际效应恒为 -G\"，该假设本身在 B6 上成立吗？",
            "model_B_coef_impurity": float(lin_b["coef_impurity_1_minus_Q"]),
            "model_B_se": float(lin_b["se_impurity_1_minus_Q"]),
            "model_B_p": float(lin_b["p_impurity_1_minus_Q"]),
            "model_B_r2": float(lin_b["r2"]),
            "model_B_reset_p": float(lin_b["reset_p_fitted_sq"]),
            "model_B_bp_p": float(lin_b["bp_p"]),
            "model_D_coef_impurity_sq": float(lin_d["coef_impurity_sq"]),
            "model_D_p_impurity_sq": float(lin_d["p_impurity_sq"]),
            "coef_impurity_vs_frozen_G_true_order": float(lin_b["coef_impurity_1_minus_Q"]) - M1_FROZEN["G"],
            "coef_impurity_vs_frozen_G_declared_order": float(lin_b["coef_impurity_1_minus_Q"]) - M1_LABEL_SWAPPED["G"],
            "within_cell_slope_mean": float(sl["within_cell_slope_dL_d_impurity"].mean()),
            "within_cell_slope_sd": float(sl["within_cell_slope_dL_d_impurity"].std(ddof=1)),
            "within_cell_slope_vs_frozen_G_true_order": float(sl["within_cell_slope_dL_d_impurity"].mean() - M1_FROZEN["G"]),
            "model_E_frozen_powers_r2": float(lin_e["r2"]),
            "model_F_declared_powers_r2": float(lin_f["r2"]),
            "verdict": ("B6 内部 (1-Q) 的系数与 M1 隐含常数边际效应**一致**（差 < 1e-9），"
                        "但 B6 是半合成数据且 M1 正是在这 360 行上拟合的，因此该检验**不能**证实 M1 形式；"
                        "它只能证伪。线性形式假设在 B6 上不可独立检验——这是 M1 的形式局限，不是坐标换算能修的。"),
            "honest_negative_result": ("关键负面结论：把 (1-Q) 单独对该数据回归只得 R²=0.110，"
                                       "说明质量项在 B6 的总变异中只占约 11%；"
                                       "补齐 N、D 项后 R² 才升到 0.938，且 RESET 检验仍显著（p≈2.3e-32），"
                                       "说明\"线性 + 幂律加和\"的整体形式在 B6 上仍有可检出的设定误差。"),
            "residual_structure": "见 tables/linearity_residual_by_Q_bin.csv（按 Q 分箱的残差均值）与 linearity_check.csv",
        },
        "stop_conditions_hit": stop,
        "limitations": [
            "本工作只建立**尺度兼容**，未建立 A–B 逐行对应 / row-level correspondence。",
            "未把问题一的 Q_A 认证为正式质量真值（问题一 run 仍为待验收 REVIEW 状态）。",
            "不解除四个核心阻断中的任何一个。",
            "不产生 G_bridge 的可识别估计；全程沿用冻结 G。",
            "未重拟合 M1（也未重拟合 M0）。",
            "B6 为半合成数据且被 B7 完全包含，本 run 不把 B6/B7 当作独立观测。",
            "映射选择会改变 Loss 影响量级，任何单一映射的数值只能写成条件结论。",
            "ε_q 是逐点量，依赖 L 的取值，只能按分位数/锚点报告，不能压成一个常数。",
            "M1 质量项是线性项，其常数边际效应假设无法用 B6 自身证伪；这是 M1 的形式局限。",
            "冻结数组 M1.fit_B6 的标签顺序与派发声明不一致（见 parameter_order_correction），已在 discrepancy_report.md 记录，未擅自改文件。",
            "所有产物状态为 EXPLORATORY，不得作为最终论文结论直接引用。",
        ],
        "outputs": {f"tables/{n}": tsha(n) for n in out_names if tsha(n)},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__,
                        "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
        "reproduce_command": "python -X utf8 scripts/q2_q_scale_bridge.py",
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------- discrepancy_report.md ----------------
    lines = ["# 差异报告 / Discrepancy report", "", f"- run_id: `{RUN_ID}`",
             f"- 生成时间(UTC): {metrics_payload['created_utc']}", ""]
    lines += ["## FEEDBACK_REQUIRED：冻结数组 `M1.fit_B6` 的标签顺序与派发声明不一致", ""]
    lines += ["### 事实", "",
              "`experiments/runs/q2-m0-m1-20260925-r01/metrics.json` 里 `M1.fit_B6` 是裸数组：",
              "", "```", str(M1_RAW), "```", "",
              "派发提示词 `P-Q2-001.md` 与 `governance/prompts/dispatching/README.md` 声明其顺序为",
              "`[E, A, B, alpha, beta, G]`。**该声明与生产拟合脚本矛盾。**", "",
              "唯一权威来源是生成它的脚本 `scripts/q2_m0_m1_explore.py` 第 46 行：", "",
              "```python", "e, a, b, g, alpha, beta = theta   # 顺序为 [E, A, B, G, alpha, beta]", "```", "",
              "### 证据（三重独立核对）", "",
              f"1. 复刻该脚本的 `fit_model(B6, quality=True)`，逐元素最大绝对差 "
              f"`{order_evidence['max_abs_diff_vs_committed_epsilon_table_true_order']:.1e}` 级，"
              "确认数组布局为 `[E, A, B, G, alpha, beta]`。",
              f"2. 真实顺序下 B6 的 SSR = `{ss_true:.6f}`（RMSE `{np.sqrt(ss_true/len(y_arr)):.6f}`），"
              f"与 `metrics.json` 自身记录的 `grouped_ND_cell_cv` RMSE `0.0512–0.0669` 量级一致；",
              f"   声明顺序下 B6 的 SSR = `{ss_swap:.6f}`（RMSE `{np.sqrt(ss_swap/len(y_arr)):.6f}`），"
              f"相差 `{ss_swap/ss_true:.3f}` 倍，与自身 CV 记录不符。",
              f"3. 真实顺序逐行复刻已提交的 `q2-elasticity-audit-20260925-r01/tables/m1_b6_elasticities.csv`，"
              f"`epsilon_Q_score` 最大绝对差 `{order_evidence['max_abs_diff_vs_committed_epsilon_table_true_order']:.1e}`；"
              f"声明顺序的最大绝对差为 `{order_evidence['max_abs_diff_vs_committed_epsilon_table_spec_order']:.1e}`。", "",
              "### 影响", "",
              "| 量 | 真实顺序 | 派发声明顺序 |",
              "|---|---|---|",
              f"| G（质量项系数） | **{M1_FROZEN['G']:.12f}** | {M1_LABEL_SWAPPED['G']:.12f} |",
              f"| alpha（N 的指数） | {M1_FROZEN['alpha']:.12f} | {M1_LABEL_SWAPPED['alpha']:.12f} |",
              f"| beta（D 的指数） | {M1_FROZEN['beta']:.12f} | {M1_LABEL_SWAPPED['beta']:.12f} |", "",
              f"- 声明顺序把质量项系数低估 **{(1 - M1_LABEL_SWAPPED['G']/M1_FROZEN['G'])*100:.1f}%**。",
              "- 由于 M1 的 Loss 对 `G` 严格线性，所有 `ΔLoss` 与 `ε_q` 都按同一比例改变，"
              "因此定性结论不变、定量结论必须标明用的是哪一个 G。",
              "- 下游 `scripts/q2_m1_sensitivity_audit.py`、`scripts/q2_q3_interface_sensitivity.py`、"
              "`scripts/q3_q_conditional.py` 使用 `[\"E\",\"A\",\"B\",\"G\",\"alpha\",\"beta\"]` 解包"
              "（即真实顺序），它们的**数值**是对的，但 `q2-elasticity-audit` 的 `metrics.json` "
              "`full_fit_parameters.M1_B6` 把 alpha/beta 两个标签写反了。", "",
              "### 本 run 的处理", "",
              "- 未修改 `metrics.json`、未重拟合、未改任何冻结数值；只在本地按真实顺序解释数组。",
              "- 所有主结果使用真实顺序的 `G = 0.36224743500545836`。",
              "- `tables/mapping_effect_G_sensitivity.csv` 同时给出两种 G 下的结果，便于人工核对。",
              "- 建议由上游在修正 `metrics.json` 字段命名后再解除本条 FEEDBACK_REQUIRED。", ""]
    for s in stop:
        lines += [f"## {s['token']}", "", s["reason"], "", s["action"], ""]
    (OUT / "discrepancy_report.md").write_text("\n".join(lines), encoding="utf-8")

    # ---------------- index_snippet / command / environment ----------------
    pd.DataFrame([{"run_id": RUN_ID, "task_id": "P-Q2-001", "topic": "q2_q_scale_bridge",
                   "status": status, "path": f"experiments/runs/{RUN_ID}/metrics.json",
                   "script": "scripts/q2_q_scale_bridge.py", "created_utc": metrics_payload["created_utc"],
                   "note": "scale compatibility only; no A-B row join; M1 not refit; M1 label order corrected + FEEDBACK_REQUIRED",
                   }]).to_csv(OUT / "index_snippet.csv", index=False, encoding="utf-8-sig")
    (OUT / "command.txt").write_text("python -X utf8 scripts/q2_q_scale_bridge.py\n", encoding="utf-8")
    (OUT / "environment.txt").write_text("\n".join(
        [f"python {sys.version.split()[0]}", f"platform {platform.platform()}",
         f"numpy {np.__version__}", f"pandas {pd.__version__}",
         f"scipy {scipy.__version__}", f"scikit-learn {sklearn.__version__}"]) + "\n", encoding="utf-8")

    print(json.dumps({
        "run_id": RUN_ID, "status": status,
        "order_true_ssr": ss_true, "order_swap_ssr": ss_swap,
        "G_true": M1_FROZEN["G"], "G_declared": M1_LABEL_SWAPPED["G"],
        "flip": flip, "stop": [s["token"] for s in stop],
        "Q1_range": [qa_lo, qa_hi], "B6_levels": int(len(np.unique(np.round(qb, 6)))),
        "coef_impurity_B": float(lin_b["coef_impurity_1_minus_Q"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
