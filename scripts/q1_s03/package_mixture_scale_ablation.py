"""Build paper table fragments and hash manifest from the frozen ablation."""
from pathlib import Path
import hashlib
import json

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/"experiments/runs/q1-mixture-scale-ablation-20260925-r01"


def table(path, caption, columns, headings, rows, label):
    lines=[r"\begin{table}[htbp]",r"\centering",r"\small",
           r"\caption{"+caption+"}",r"\label{"+label+"}",
           r"\begin{tabular}{"+columns+"}",r"\hline",
           " & ".join(headings)+r" \\",r"\hline"]
    lines.extend(" & ".join(row)+r" \\" for row in rows)
    lines.extend([r"\hline",r"\end{tabular}",r"\end{table}"])
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    metrics=pd.read_csv(RUN/"metrics_aggregate.csv")
    comparisons=pd.read_csv(RUN/"paired_error_comparisons.csv")
    correction_labels={"C0_none":"C0","C1_global":"C1-global","C1_domain":"C1-domain","C2_mixture_conditioned":"C2"}
    models={"ilr_ridge":"ilr-Ridge","quadratic_ridge":"Quadratic"}
    rows=[]
    for model,label in models.items():
        for correction,clabel in correction_labels.items():
            values=[]
            for dataset in ["A10_A11_test_1b","A12_A13_est_10b","A14_A15_est_70b"]:
                r=metrics.query("base_model==@model and correction==@correction and dataset==@dataset").iloc[0]
                values.extend([f"{r.rmse_pooled_all_domains:.4f}",f"{r.mae_domain_macro:.4f}"])
            rows.append([label,clabel]+values)
    table(RUN/"table_scale_transfer.tex",
          "纯配比模型的尺度迁移误差。指标在所有样本及13个响应上合并计算；1B为回顾性评价，10B和70B为题目提供的估算目标。",
          "llrrrrrr",["模型","修正","1B RMSE","1B MAE","10B RMSE","10B MAE","70B RMSE","70B MAE"],rows,"tab:q1-mixture-scale")
    rows=[]
    datasets={"A6_A7_test_1m":"1M","A8_A9_test_60m":"60M","A10_A11_test_1b":"1B","A12_A13_est_10b":"10B*","A14_A15_est_70b":"70B*"}
    for model,label in models.items():
        for dataset,ds in datasets.items():
            r=comparisons.query("comparison=='optional_quality' and reference_base_model==@model and dataset==@dataset and candidate_correction=='C1_global'").iloc[0]
            rows.append([label,ds,f"{r.rmse_difference:+.4f}",f"[{r.rmse_ci95_low:+.4f}, {r.rmse_ci95_high:+.4f}]",f"{r.mae_difference:+.4f}",f"[{r.mae_ci95_low:+.4f}, {r.mae_ci95_high:+.4f}]"])
    table(RUN/"table_quality_increment.tex",
          "固定C1-global后的可选质量增量。差值为加入Q后的误差减去纯配比误差，负值表示改善。区间为5000次配方行配对bootstrap的描述性95\\%区间，不含拟合或选模不确定性；星号为估算表。60M属于校准内评价。",
          "llrrrr",["模型","规模",r"$\Delta$RMSE","95\\%区间",r"$\Delta$MAE","95\\%区间"],rows,"tab:q1-optional-quality")
    source_paths=["configs/q1-mixture-scale-ablation.json","scripts/q1_s03/mixture_scale_ablation.py",
        "scripts/q1_s03/plot_mixture_scale_ablation.py","scripts/q1_s03/package_mixture_scale_ablation.py",
        "scripts/q1_s03/reproduce.py","scripts/q1_mixture_collinearity.py","tests/test_q1_mixture_scale_ablation.py",
        "requirements-q1-mixture-scale-ablation.txt","docs/decisions/q1-mixture-scale-ablation-results.md"]
    def info(p):
        return {"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    config=json.loads((ROOT/source_paths[0]).read_text(encoding="utf-8"))
    manifest={"run_id":config["run_id"],"task_id":"T-Q1-S03-ABLATION","status":"PEER_REVIEW",
        "team_base_commit":"33d1a0cb4f289102c58ac4066e3847243e0bf4ee","repository":"xiaoyuankele/huawei-cup-2026-team",
        "input":info(ROOT/config["input"]),"sources":[info(ROOT/p) for p in source_paths],
        "outputs":[info(p) for p in sorted(RUN.rglob('*')) if p.is_file() and p.name!='run_manifest.json' and '__pycache__' not in p.parts],
        "reproduce":["python scripts/q1_s03/mixture_scale_ablation.py","python scripts/q1_s03/plot_mixture_scale_ablation.py --run experiments/runs/q1-mixture-scale-ablation-20260925-r01","python scripts/q1_s03/package_mixture_scale_ablation.py"],
        "human_review":"PENDING; internal automated/AI checks do not replace team review"}
    (RUN/"run_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"outputs":len(manifest['outputs']),"source_files":len(source_paths)}))


if __name__=="__main__":
    main()
