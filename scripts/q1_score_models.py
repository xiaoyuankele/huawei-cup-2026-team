"""Run the selected CRITIC-TOPSIS model and controls from the repository root.

python -X utf8 scripts/q1_score_models.py --root . --config configs/q1-score-baselines.yaml
Raw files are read by the separate preprocessing command. No external cohort fits weights.
"""
import os
for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
    os.environ[key] = '1'
import argparse, hashlib, json, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.stats import spearmanr, rankdata
import yaml
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.models.q1_scoring import critic_weights, topsis, weighted_sum


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1048576),b''): h.update(block)
    return h.hexdigest()


def dump(p, obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def csv(df,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,encoding='utf-8-sig',float_format='%.17g')


def views(df):
    masks={}
    for ds in ('A1','A2','A3'):
        mask=df.dataset_id.eq(ds).to_numpy()
        masks[(ds,'full')]=mask
        if ds=='A1':
            for split in ('fit','holdout'): masks[(ds,split)]=mask & df.split.eq(split).to_numpy()
        else:
            for name, ov in [('overlap_A1',True),('new_only',False)]: masks[(ds,name)]=mask & df.overlap_with_A1.eq(ov).to_numpy()
    masks[('A1+A2+A3','unique_union')]=df.kept_in_unique_union.to_numpy()
    masks[('A1+A2+A3','all_file_rows_diagnostic')]=np.ones(len(df),dtype=bool)
    return masks


def aggregate(df, scores, masks):
    rows=[]
    for (ds,subset),mask in masks.items():
        for domain in ['ALL']+sorted(df.loc[mask,'domain'].unique()):
            m=mask if domain=='ALL' else mask & df.domain.eq(domain).to_numpy()
            s=scores[m]
            rows.append(dict(dataset_id=ds,subset=subset,domain=domain,n_records=len(s),n_unique_ids=int(df.loc[m,'record_id'].nunique()),mean=float(s.mean()),median=float(np.median(s)),sd=float(s.std(ddof=1)) if len(s)>1 else 0.,p10=float(np.quantile(s,.1)),p90=float(np.quantile(s,.9))))
    t=pd.DataFrame(rows)
    t['domain_rank']=np.nan
    m=t.domain.ne('ALL')
    t.loc[m,'domain_rank']=t.loc[m].groupby(['dataset_id','subset'])['mean'].rank(method='min',ascending=False)
    return t


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--config',type=Path,default=Path('configs/q1-score-baselines.yaml'))
    args=ap.parse_args(); root=args.root.resolve(); t0=time.monotonic()
    cfgpath=args.config if args.config.is_absolute() else root/args.config
    cfg=yaml.safe_load(cfgpath.read_text(encoding='utf-8'))
    manifest=yaml.safe_load((root/cfg['preprocessing_manifest']).read_text(encoding='utf-8'))
    for key in ('matrix','catalog','stats','audit','sensitivity'):
        if sha(root/manifest['outputs'][key])!=manifest['outputs'][key+'_sha256']: raise ValueError('Preprocessing hash mismatch: '+key)
    if {i['dataset_id']:i['sha256'] for i in manifest['raw_inputs']}!={i['dataset_id']:i['sha256'] for i in cfg['raw_inputs']}: raise ValueError('Raw source manifest changed')
    matrix=root/cfg['matrix'];df=pd.read_csv(matrix,dtype={'record_id':str},float_precision='round_trip')
    names=cfg['indicators'];x=df[names].to_numpy(float)
    if not df.overlap_with_A1.dtype==bool: df['overlap_with_A1']=df.overlap_with_A1.astype(str).str.lower().eq('true')
    if df.record_id.isna().any() or df.record_id.eq('').any():raise ValueError('Missing ID')
    if df.duplicated(['dataset_id','record_id']).any():raise ValueError('Within-file duplicate ID requires review')
    if df.groupby('record_id').domain.nunique().max()!=1:raise ValueError('Duplicate domain differs')
    df['kept_in_unique_union']=~df.duplicated('record_id',keep='first')
    first=df.reset_index().drop_duplicates('record_id').set_index('record_id')['index']
    representative=df.record_id.map(first).to_numpy(int)
    if not np.array_equal(x,x[representative]):raise ValueError('Duplicate normalized signals differ')
    counts=df.dataset_id.value_counts().to_dict()
    if counts!=cfg['expected_counts']:raise ValueError('Record counts changed')
    a1=df.dataset_id.eq('A1').to_numpy();fit=a1 & df.split.eq('fit').to_numpy()
    if fit.sum()!=cfg['expected_fit'] or (a1 & ~fit).sum()!=cfg['expected_holdout']:raise ValueError('Split changed')
    if df.kept_in_unique_union.sum()!=cfg['expected_unique']:raise ValueError('Unique count changed')
    if not np.isfinite(x).all():raise ValueError('Selected features contain missing values; no rows dropped')
    w,sd,corr,information=critic_weights(x[fit]);p=len(names)
    masks=views(df)
    weight_map={'TOPSIS_CRITIC':w,'CRITIC_SUM':w,'EQUAL_SUM':np.ones(p)/p}
    for model,mask in [('TOPSIS_NO_3_COST',np.array([n not in ('rps_doc_frac_no_alph_words','rps_doc_frac_chars_top_2gram','rps_doc_frac_chars_top_3gram') for n in names])),('TOPSIS_NO_DSIR',np.array([not n.startswith('dsir_') for n in names]))]:
        ww=w*mask;weight_map[model]=ww/ww.sum()
    weight_map['TOPSIS_WEIGHT_SQUARED']=w*w/(w*w).sum()
    primary=cfg['run_ids']['TOPSIS_CRITIC'];primarydir=root/'experiments/runs'/primary
    scores={};summaries={};run_manifests={}
    meta=df[['dataset_id','record_id','domain','split','overlap_with_A1','kept_in_unique_union']].copy()
    for model,ww in weight_map.items():
        run=cfg['run_ids'][model];rd=root/'experiments/runs'/run
        for folder in ['tables','artifacts','validation']: (rd/folder).mkdir(parents=True,exist_ok=True)
        if model.endswith('_SUM'):
            s=weighted_sum(x,ww);dp=dm=None
        else:s,dp,dm=topsis(x,ww)
        scores[model]=s;summaries[model]=aggregate(df,s,masks)
        output=meta.copy();output['quality_score']=s
        if dp is not None:output['distance_to_positive']=dp;output['distance_to_negative']=dm
        csv(output,rd/'artifacts/sample_scores.csv')
        csv(summaries[model].query("domain != 'ALL'"),rd/'tables/domain_scores.csv')
        csv(summaries[model].query("domain == 'ALL'"),rd/'tables/corpus_scores.csv')
        csv(pd.DataFrame({'indicator':names,'distance_or_sum_weight':ww}),rd/'tables/model_weights.csv')
        dump(rd/'model_parameters.json',{'model':model,'run_id':run,'fit_records':int(fit.sum()),'weights':dict(zip(names,ww.tolist())),'positive_ideal':1.,'negative_ideal':0.,'weight_convention':cfg['topsis'] if model.startswith('TOPSIS') else '100*sum(w*x)','note':'TOPSIS_WEIGHT_SQUARED uses normalized squared original CRITIC weights; sensitivity only' if model=='TOPSIS_WEIGHT_SQUARED' else 'Main and controls use the same frozen normalized matrix'})
        (rd/'config.yaml').write_text(yaml.safe_dump(dict(cfg,executed_model=model,executed_run_id=run),allow_unicode=True,sort_keys=False),encoding='utf-8')
        (rd/'command.txt').write_text('python -X utf8 scripts/q1_score_models.py --root . --config configs/q1-score-baselines.yaml\n# This command produces each separately identified model run from one common input.\n',encoding='utf-8')
        (rd/'git_commit.txt').write_text(cfg['source_repository_commit']+'\n# Base repository commit; new delivery code is uncommitted and identified by SHA256.\n',encoding='utf-8')
        dump(rd/'environment.json',{'python':platform.python_version(),'platform':platform.system(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'PyYAML':yaml.__version__,'threads':1})
        dump(rd/'data_manifest.json',manifest)
        run_manifests[model]={'run_id':run,'model':model,'task_id':'T-Q1-004','status':'LOCAL_RESULT_PENDING_TEAM_REVIEW','needs_human_review':True,'primary_model':model=='TOPSIS_CRITIC','preprocessing_run_id':manifest['run_id'],'raw_sha256':{i['dataset_id']:i['sha256'] for i in manifest['raw_inputs']},'normalized_matrix_sha256':sha(matrix),'config_sha256':sha(cfgpath),'source_commit':cfg['source_repository_commit'],'code_sha256':{n:sha(root/n) for n in ['scripts/q1_score_models.py','src/models/q1_scoring.py','scripts/q1_indicator_preprocess.py']},'n_file_records':len(df),'n_unique_records':int(df.kept_in_unique_union.sum()),'n_fit':int(fit.sum()),'counts':counts,'scope':'Every A1/A2/A3 row scored; same-ID cross-file duplicates removed only in unique-union aggregation; no raw text output'}
        print(model,run,'complete',flush=True)
    full=masks[('A1+A2+A3','unique_union')];sp=scores['TOPSIS_CRITIC']
    csv(meta.loc[full].assign(quality_score=sp[full]),primarydir/'artifacts/unique_sample_scores.csv')
    tb=summaries['TOPSIS_CRITIC'];rows=[]
    for domain in sorted(df.domain.unique()):
        a=tb[(tb.dataset_id=='A1')&(tb.subset=='full')&(tb.domain==domain)].iloc[0]
        b=tb[(tb.subset=='unique_union')&(tb.domain==domain)].iloc[0]
        rows.append({'domain':domain,'n_A1':int(a.n_records),'A1_mean':a['mean'],'n_full_unique':int(b.n_records),'full_mean':b['mean'],'difference_points':b['mean']-a['mean'],'A1_rank':int(a.domain_rank),'full_rank':int(b.domain_rank)})
    compare=pd.DataFrame(rows);csv(compare,primarydir/'tables/full_vs_A1.csv')
    rows=[]
    for ds,domain in [('A2','arxiv'),('A3','github')]:
        a=compare.set_index('domain').loc[domain]
        for subset in ['full','new_only','overlap_A1']:
            b=tb[(tb.dataset_id==ds)&(tb.subset==subset)&(tb.domain==domain)].iloc[0]
            rows.append({'dataset_id':ds,'domain':domain,'subset':subset,'n_records':int(b.n_records),'A1_mean':a.A1_mean,'extended_mean':b['mean'],'difference_points':b['mean']-a.A1_mean})
    csv(pd.DataFrame(rows),primarydir/'tables/extended_vs_A1.csv')
    stats=json.loads((root/'normalization_stats.json').read_text(encoding='utf-8'))
    csv(pd.DataFrame({'indicator':names,'raw_direction':['cost' if n in ('rps_doc_frac_no_alph_words','rps_doc_frac_chars_top_2gram','rps_doc_frac_chars_top_3gram') else 'benefit' for n in names],'critic_weight':w,'fit_normalized_sd':sd,'information':information,'oriented_p01':[stats['fit_statistics'][n]['oriented_p01'] for n in names],'oriented_p99':[stats['fit_statistics'][n]['oriented_p99'] for n in names]}),primarydir/'tables/indicator_parameters.csv')
    csv(pd.DataFrame(corr,index=names,columns=names).reset_index(names='indicator'),primarydir/'tables/fit_pearson_correlation.csv')
    boundary=[]
    for (ds,subset),m in masks.items():
        if subset=='all_file_rows_diagnostic':continue
        for j,n in enumerate(names):boundary.append({'dataset_id':ds,'subset':subset,'indicator':n,'n_records':int(m.sum()),'zero_rate':float(np.mean(x[m,j]==0)),'one_rate':float(np.mean(x[m,j]==1)),'normalized_mean':float(x[m,j].mean())})
    csv(pd.DataFrame(boundary),primarydir/'tables/full_record_normalization_support.csv')
    contrasts=[];primary_rank=100*(rankdata(sp[full],method='average')-.5)/int(full.sum())
    for model,s in scores.items():
        r=100*(rankdata(s[full],method='average')-.5)/int(full.sum())
        contrasts.append({'model':model,'run_id':cfg['run_ids'][model],'scope':'unique_union','n':int(full.sum()),'mean':float(s[full].mean()),'spearman_with_primary':float(spearmanr(sp[full],s[full]).statistic),'mean_abs_score_difference':float(np.abs(s[full]-sp[full]).mean()),'mean_abs_rank_gap_pp':float(np.abs(r-primary_rank).mean()),'rank_gap_ge20pp_rate':float(np.mean(np.abs(r-primary_rank)>=20))})
    csv(pd.DataFrame(contrasts),primarydir/'tables/model_sensitivity.csv')
    all_domains=pd.concat([t.assign(model=m,run_id=cfg['run_ids'][m]) for m,t in summaries.items()],ignore_index=True)
    csv(all_domains,primarydir/'tables/all_models_cohort_domain.csv')
    a1mean=float(sp[a1].mean());fullmean=float(sp[full].mean())
    adjusted=float(np.average(compare.full_mean,weights=compare.n_A1))
    metrics={'primary_model':'TOPSIS_CRITIC','A1_mean':a1mean,'full_unique_mean':fullmean,'full_minus_A1':fullmean-a1mean,'A1_share_standardized_full_mean':adjusted,'within_domain_component':adjusted-a1mean,'composition_component':fullmean-adjusted,'macro_domain_mean':float(compare.full_mean.mean()),'n_file_rows':len(df),'n_unique':int(full.sum()),'overlap_removed':len(df)-int(full.sum()),'n_fit':int(fit.sum()),'n_holdout':int((a1&~fit).sum()),'total_seconds':time.monotonic()-t0}
    dump(primarydir/'metrics.json',metrics)
    for model,rm in run_manifests.items():
        rd=root/'experiments/runs'/cfg['run_ids'][model]
        if model!='TOPSIS_CRITIC':dump(rd/'metrics.json',{'model':model,'full_unique_mean':float(scores[model][full].mean()),'A1_mean':float(scores[model][a1].mean())})
        produced=['artifacts/sample_scores.csv','tables/domain_scores.csv','tables/corpus_scores.csv','tables/model_weights.csv','model_parameters.json','config.yaml','command.txt','git_commit.txt','environment.json','data_manifest.json','metrics.json']
        if model=='TOPSIS_CRITIC':
            produced+=['artifacts/unique_sample_scores.csv']+['tables/'+n for n in ['full_vs_A1.csv','extended_vs_A1.csv','indicator_parameters.csv','fit_pearson_correlation.csv','full_record_normalization_support.csv','model_sensitivity.csv','all_models_cohort_domain.csv']]
        # Reports, validation and plots observe this run. They are covered by the
        # delivery manifest, not self-referential model-output checksums.
        rm['output_sha256']={p:sha(rd/p) for p in produced}
        dump(rd/'run_manifest.json',rm)
    scoring_manifest={'schema_version':'q1.scoring.delivery.v1','task_id':'T-Q1-004','status':'LOCAL_RESULT_PENDING_TEAM_REVIEW','needs_human_review':True,'primary_model':'TOPSIS_CRITIC','primary_run_id':primary,'preprocessing_manifest':cfg['preprocessing_manifest'],'preprocessing_run_id':manifest['run_id'],'models':cfg['run_ids'],'complete_data_files':{'matrix':cfg['matrix'],'all_record_scores':f'experiments/runs/{primary}/artifacts/sample_scores.csv','unique_sample_scores':f'experiments/runs/{primary}/artifacts/unique_sample_scores.csv'},'record_counts':counts,'n_unique':int(full.sum())}
    dump(root/'data/manifests/q1_scoring.json',scoring_manifest)
    print(json.dumps(metrics,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
