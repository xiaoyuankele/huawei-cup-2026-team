"""Read-only external diagnostic for B3 interpolated Pythia trajectories."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
BROOT = ROOT / "data/origin/real_attachments/B_scaling_laws"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def metric(y, pred):
    ybar = mean(y); err = [a-b for a,b in zip(y,pred)]
    denom = sum((v-ybar)**2 for v in y)
    return {"n": len(y), "mae": mean(abs(e) for e in err), "rmse": math.sqrt(mean(e*e for e in err)), "r2": 1-sum(e*e for e in err)/denom if denom else None}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-b3-trajectory-audit-20250925-r01"); args = ap.parse_args()
    out = args.out; out.mkdir(parents=True, exist_ok=True)
    m0 = json.loads((ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json").read_text(encoding="utf-8"))["M0"]["fit_full_B1"]
    E,A,B,alpha,beta = m0
    file_reports=[]; all_y=[]; all_pred=[]
    for path in sorted((BROOT/"training_trajectories").glob("*.csv")):
        rows=read(path); y=[]; pred=[]; keys=set(); dup=0
        for r in rows:
            n,d=float(r["N_params_B"]),float(r["D_tokens_B"]); y.append(float(r["val_loss"])); pred.append(E+A*n**(-alpha)+B*d**(-beta)); key=(r["N_params_B"],r["D_tokens_B"],r.get("step","")); dup += int(key in keys); keys.add(key)
        all_y += y; all_pred += pred
        file_reports.append({"file":path.name,"sha256":sha256(path),"rows":len(rows),"n_unique_N":len({r["N_params_B"] for r in rows}),"interpolated_count":sum(r.get("interpolated")=="1" for r in rows),"duplicate_key_count":dup,**metric(y,pred)})
    report={"run_id":"q2-b3-trajectory-audit-20250925-r01","status":"B3_EXTERNAL_TRAJECTORY_DIAGNOSTIC","source_model_run":"q2-m0-m1-20260925-r01","model_parameters":{"E":E,"A":A,"B":B,"alpha":alpha,"beta":beta},"files":file_reports,"overall":metric(all_y,all_pred),"checks":{"all_rows_interpolated":all(x["interpolated_count"]==x["rows"] for x in file_reports),"duplicate_keys_absent":all(x["duplicate_key_count"]==0 for x in file_reports),"refit_on_B3":False,"B3_used_to_select_M0":False},"interpretation":["B3 is a same-family Pythia interpolated-trajectory diagnostic, not an independent source truth.","Predictions use frozen B1 M0 parameters; no B3 refit or model selection was performed.","The diagnostic does not establish cross-family generalization or a universal scaling law."]}
    (out/"metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"); (out/"README.md").write_text("# B3 trajectory audit\n\nRead-only diagnostic using frozen B1 M0 parameters.\n",encoding="utf-8")
    print(json.dumps({"run_id":report["run_id"],"status":report["status"],"overall":report["overall"]},ensure_ascii=False))

if __name__ == "__main__": main()
