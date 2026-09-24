"""Independent numerical and provenance checks; optional historical result comparison."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--historical-scores',type=Path);args=ap.parse_args()
    root=args.root.resolve();cfg=yaml.safe_load((root/'configs/q1-score-baselines.yaml').read_text(encoding='utf-8'))
    primary=root/'experiments/runs'/cfg['run_ids']['TOPSIS_CRITIC']
    df=pd.read_csv(root/cfg['matrix'],dtype={'record_id':str},float_precision='round_trip');names=cfg['indicators'];x=df[names].to_numpy(float)
    checks=[]
    def check(name,ok,detail=None):
        checks.append(dict(check=name,passed=bool(ok),detail=detail));
        if not ok:raise AssertionError(name)
    fit=(df.dataset_id.eq('A1')&df.split.eq('fit')).to_numpy()
    z=x[fit];center=z-z.mean(axis=0);cov=center.T@center/(len(z)-1);sd=np.sqrt(np.diag(cov));corr=cov/np.outer(sd,sd);info=sd*np.sum(1-corr,axis=1);w=info/info.sum()
    params=json.loads((primary/'model_parameters.json').read_text(encoding='utf-8'))
    modelw=np.array([params['weights'][n] for n in names])
    check('CRITIC weights independently recomputed from covariance',np.allclose(w,modelw,atol=1e-12,rtol=0),float(np.max(abs(w-modelw))))
    plus2=sum(modelw[j]*(1-x[:,j])**2 for j in range(len(names)));minus2=sum(modelw[j]*x[:,j]**2 for j in range(len(names)))
    expected=100*np.sqrt(minus2)/(np.sqrt(minus2)+np.sqrt(plus2))
    out=pd.read_csv(primary/'artifacts/sample_scores.csv',dtype={'record_id':str},float_precision='round_trip')
    check('All records and keys retained in source order',len(out)==272505 and out[['dataset_id','record_id']].equals(df[['dataset_id','record_id']]))
    error=float(abs(expected-out.quality_score.to_numpy()).max());check('Every TOPSIS score independently recomputed',error<1e-10,error)
    check('All selected values and scores finite and bounded',np.isfinite(x).all() and np.isfinite(expected).all() and expected.min()>=0 and expected.max()<=100)
    check('Fit contains A1 fit only',fit.sum()==40919 and (df.dataset_id.eq('A1')&~df.split.eq('fit')).sum()==10311)
    check('Nine withheld directions stay empty',len([n for n in df.columns if n not in names and n not in ['dataset_id','record_id','domain','split','overlap_with_A1','row_status','nonfinite_component_count','missing_indicator_count'] and df[n].isna().all()])==9)
    unique=out.drop_duplicates('record_id');check('Unique sample coverage',len(unique)==261086 and len(out)-len(unique)==11419)
    check('Duplicate sample scores equal',out.groupby('record_id').quality_score.nunique().max()==1)
    domain=pd.read_csv(primary/'tables/domain_scores.csv');domain=domain.query("subset=='unique_union'")
    check('Domain sample counts reconcile',domain.n_records.sum()==len(unique))
    calculated=unique.groupby('domain').quality_score.mean();check('Domain means match unique samples',np.allclose(domain.set_index('domain')['mean'].sort_index(),calculated.sort_index(),atol=1e-10))
    weighted=float(np.average(domain['mean'],weights=domain.n_records));check('Corpus equals sample-count-weighted domain means',abs(weighted-unique.quality_score.mean())<1e-10)
    metrics=json.loads((primary/'metrics.json').read_text(encoding='utf-8'));check('Composition decomposition reconciles',abs(metrics['within_domain_component']+metrics['composition_component']-metrics['full_minus_A1'])<1e-10)
    m=yaml.safe_load((root/cfg['preprocessing_manifest']).read_text(encoding='utf-8'))
    check('All refreshed preprocessing outputs match manifest',all(sha(root/m['outputs'][k])==m['outputs'][k+'_sha256'] for k in ['matrix','catalog','stats','audit','sensitivity']))
    stats=json.loads((root/'normalization_stats.json').read_text(encoding='utf-8'));check('Raw files unchanged during preprocessing',stats['raw_hash_stable'] and stats['raw_hash_before']==stats['raw_hash_after'])
    old=json.loads((root/'reference/preprocessing_before_refresh/normalization_stats.json').read_text(encoding='utf-8'))
    check('Rebuilt selected p01/p99 reproduce historical fit parameters',all(abs(stats['fit_statistics'][n][k]-old['fit_statistics'][n][k])<1e-10 for n in names for k in ['oriented_p01','oriented_p99']))
    for model,run in cfg['run_ids'].items():
        rd=root/'experiments/runs'/run;rm=json.loads((rd/'run_manifest.json').read_text(encoding='utf-8'))
        check(model+' recorded output hashes match',all(sha(rd/p)==v for p,v in rm['output_sha256'].items()))
    if args.historical_scores:
        h=pd.read_csv(args.historical_scores,usecols=['dataset_id','record_id','TOPSIS_CRITIC'],dtype={'record_id':str},float_precision='round_trip')
        check('Historical TOPSIS record alignment',h[['dataset_id','record_id']].equals(out[['dataset_id','record_id']]))
        err=float(np.max(abs(h.TOPSIS_CRITIC.to_numpy()-expected)))
        check('Rebuilt main scores agree with existing TOPSIS_CRITIC',err<2e-8,{'max_absolute_difference':err,'reason_for_small_difference':'Old normalized export used 10 significant digits; refreshed preprocessing exports 12.'})
    result={'passed':all(c['passed'] for c in checks),'checks':checks,'count':len(checks),'scope':'numerical and reproducibility checks, not quality-label validation'}
    (primary/'validation/independent_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
