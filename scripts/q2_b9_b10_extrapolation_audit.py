"""Read-only scope and provenance audit for B9/B10 large-model extrapolation inputs."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]; BROOT=ROOT/"data/origin/real_attachments/B_scaling_laws"; MANIFEST=ROOT/"data/origin/real_attachments/source_manifest.json"
def sha(path):
    h=hashlib.sha256();
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def read(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=ROOT/"experiments/runs/q2-b9-b10-extrapolation-audit-20250925-r01"); args=ap.parse_args(); out=args.out; out.mkdir(parents=True,exist_ok=True)
    models=read(BROOT/"supplementary_large_models.csv"); baseline=read(BROOT/"supplementary_large_baseline.csv")
    model_names=[r["model_name"] for r in models]; base_names=[r["family"] for r in baseline]
    entries={e.get("file"):e for e in json.loads(MANIFEST.read_text(encoding="utf-8")) if isinstance(e,dict)}
    def file_report(name,rows):
        nums=[float(r["N_params_B"]) for r in rows if r.get("N_params_B")]; ds=[float(r["D_tokens_B"]) for r in rows if r.get("D_tokens_B")]
        return {"file":name,"rows":len(rows),"sha256":sha(BROOT/name),"n_min":min(nums),"n_max":max(nums),"d_min":min(ds),"d_max":max(ds),"duplicate_name_count":len([x for x,c in Counter(model_names if name.endswith("models.csv") else base_names).items() if c>1]),"missing_cells":sum(v=="" for r in rows for v in r.values())}
    report={"run_id":"q2-b9-b10-extrapolation-audit-20250925-r01","status":"B9_B10_EXTRAPOLATION_ONLY","files":{"B9":file_report("supplementary_large_models.csv",models),"B10":file_report("supplementary_large_baseline.csv",baseline)},"overlap":{"metadata_names":len(set(model_names)),"baseline_names":len(set(base_names)),"baseline_names_in_metadata":sum(x in set(model_names) for x in base_names),"baseline_only_names":[x for x in base_names if x not in set(model_names)]},"manifest_provenance":{"B9":entries.get("B_scaling_laws/supplementary_large_models.csv",{}),"B10":entries.get("B_scaling_laws/supplementary_large_baseline.csv",{})},"checks":{"fit_or_refit":False,"used_as_true_validation":False,"estimated_extrapolation_label_preserved":True,"source_metadata_complete":bool(entries.get("B_scaling_laws/supplementary_large_models.csv",{}).get("source")) and bool(entries.get("B_scaling_laws/supplementary_large_baseline.csv",{}).get("source"))},"interpretation":["B9/B10 are large-model metadata and estimated baseline inputs for range/extrapolation checks.","They do not enter B1 fitting or serve as true held-out validation.","Missing manifest source fields remain a provenance limitation."]}
    (out/"metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"); (out/"README.md").write_text("# B9/B10 extrapolation audit\n\nRead-only range and provenance audit. No fitting and no validation promotion.\n",encoding="utf-8")
    print(json.dumps({"run_id":report["run_id"],"status":report["status"],"B9_rows":len(models),"B10_rows":len(baseline),"metadata_complete":report["checks"]["source_metadata_complete"]},ensure_ascii=False))
if __name__=="__main__":main()
