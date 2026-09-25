"""Stratified B4/B5 diagnostics using frozen B1 M0 parameters."""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
BROOT = ROOT / "data/origin/real_attachments/B_scaling_laws"

def read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def metric(rows, params):
    E,A,B,alpha,beta=params; y=[]; pred=[]
    for r in rows:
        n,d=float(r["N_params_B"]),float(r["D_tokens_B"]); y.append(float(r["val_loss"])); pred.append(E+A*n**(-alpha)+B*d**(-beta))
    ybar=mean(y); err=[a-b for a,b in zip(y,pred)]; denom=sum((v-ybar)**2 for v in y)
    return {"n":len(y),"mae":mean(abs(e) for e in err),"rmse":math.sqrt(mean(e*e for e in err)),"r2":1-sum(e*e for e in err)/denom if denom else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=ROOT/"experiments/runs/q2-b4-b5-stratified-audit-20250925-r01"); args=ap.parse_args()
    out=args.out; out.mkdir(parents=True,exist_ok=True)
    m0=json.loads((ROOT/"experiments/runs/q2-m0-m1-20260925-r01/metrics.json").read_text(encoding="utf-8"))["M0"]["fit_full_B1"]
    report={"run_id":"q2-b4-b5-stratified-audit-20250925-r01","status":"B4_B5_STRATIFIED_EXTERNAL_DIAGNOSTIC","source_model_run":"q2-m0-m1-20260925-r01","datasets":{},"checks":{"refit_by_family_or_source":False,"pooled_external_fit":False,"small_groups_flagged":True}}
    for label, name, group_key in [("B4","scaling_baseline.csv","family"),("B5","published_scaling_data.csv","source")]:
        rows=read(BROOT/name); groups={}
        for r in rows: groups.setdefault(r.get(group_key,"(missing)"),[]).append(r)
        report["datasets"][label]={"file":name,"group_key":group_key,"rows":len(rows),"groups":{k:{**metric(v,m0),"small_group":len(v)<5} for k,v in sorted(groups.items())}}
    (out/"metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"README.md").write_text("# B4/B5 stratified audit\n\nFrozen B1 M0 parameters are evaluated by family/source. No pooled external fit is performed.\n",encoding="utf-8")
    print(json.dumps({"run_id":report["run_id"],"status":report["status"],"groups":{"B4":len(report["datasets"]["B4"]["groups"]),"B5":len(report["datasets"]["B5"]["groups"])}},ensure_ascii=False))

if __name__=="__main__": main()
