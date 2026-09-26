"""Reproduce Q1.2 from the bundled normalized records; no source execution/network.
Usage: python code/run_analysis.py [--root PATH]
All rates are fractions, scores are on 0..100, rank changes are percentile fractions.
"""
from pathlib import Path
import argparse, hashlib, json, platform, sys
import numpy as np
import pandas as pd

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def robust_score(z,v,lam):
    return 100*((1-lam)*(z@v)+lam*z.min(axis=1))

def main(root):
    inp=root/'inputs'; out=root/'results'; val=root/'validation'
    out.mkdir(exist_ok=True);val.mkdir(exist_ok=True);(root/'artifacts').mkdir(exist_ok=True)
    cfg=json.loads((inp/'config.json').read_text()); pm=json.loads((inp/'q1_model.json').read_text()); stats=json.loads((inp/'normalization_stats.json').read_text())
    w=pd.Series(pm['weights']); cols=list(w.index);groups=cfg['groups'];gn=list(groups);p=cfg['tail_probability'];lam=cfg['lambda_reference']
    d=pd.read_csv(root/'artifacts/normalized_records.csv.gz',dtype={'id':str},float_precision='round_trip')
    X=d[cols].to_numpy(); assert np.isfinite(X).all() and X.min()>=0 and X.max()<=1
    a1=d.dataset.eq('A1').to_numpy();fit=a1&d.split.eq('fit').to_numpy();unique=~d.id.duplicated().to_numpy();new=~d.id.isin(set(d.loc[a1,'id'])).to_numpy()
    assert (len(d),int(unique.sum()),int(fit.sum()))==(272505,261086,40919)
    repeated=d[d.id.duplicated(False)]
    assert repeated.groupby('id')[cols].nunique().max().max()==1
    assert repeated.groupby('id').domain.nunique().max()==1
    dm=np.sqrt((X**2)@w.to_numpy());dp=np.sqrt(((1-X)**2)@w.to_numpy());d['Q_original']=100*dm/(dm+dp)
    checks=[]; orig=pd.read_csv(inp/'q1_domain_scores.csv')
    for r in orig[(orig.dataset_id=='A1')&(orig.subset=='full')].itertuples():
        q=d.loc[a1&d.domain.eq(r.domain),'Q_original'].mean()
        checks.append({'domain':r.domain,'reported':r.mean,'reproduced':q,'abs_error':abs(q-r.mean)})
    assert max(x['abs_error'] for x in checks)<1e-8
    pd.DataFrame(checks).to_csv(val/'q1_reproduction.csv',index=False)
    v=np.array([w[cs].sum() for cs in groups.values()]);v=v/v.sum()
    for g,cs in groups.items():d[g]=d[cs].to_numpy()@(w[cs]/w[cs].sum()).to_numpy()
    Z=d[gn].to_numpy();lo=np.quantile(Z[fit],p,axis=0);hi=np.quantile(Z[fit],1-p,axis=0)
    H=Z>hi;L=Z<lo;c=H.any(1)&L.any(1)
    d['class']=np.select([c,H.any(1),L.any(1)],['conflict','positive_only','negative_only'],default='middle')
    u=np.maximum(0,(Z-hi)/(1-hi));b=np.maximum(0,(lo-Z)/lo)
    d['conflict_strength']=u.max(1)*b.max(1)
    d['conflict_breadth']=H.sum(1)*L.sum(1)/10
    d['high_dimensions']=['|'.join(np.array(gn)[r]) for r in H]
    d['low_dimensions']=['|'.join(np.array(gn)[r]) for r in L]
    E=d[['fineweb_edu','qurater_educational_value']].to_numpy();el=np.quantile(E[fit],p,axis=0);eh=np.quantile(E[fit],1-p,axis=0)
    ec=((E[:,0]>eh[0])&(E[:,1]<el[1]))|((E[:,1]>eh[1])&(E[:,0]<el[0]))
    d['education_disagreement']=ec
    ads=stats['fit_statistics']['ad_en_no_ad_margin'];ad0=(0-ads['oriented_p01'])/(ads['oriented_p99']-ads['oriented_p01'])
    d['ad_classifier_positive']=d.ad_en_no_ad_margin.lt(ad0)
    d['value_ad_tradeoff']=H[:,gn.index('value')]&d.ad_classifier_positive.to_numpy()
    # Diagnosis flags do not assert a causal explanation or independently verified defect.
    d['domain_applicability_review']=d.domain.isin(['arxiv','github'])
    d['case_language_review']=d.id.isin(['BkiUbJ_xK6mkyCfOAMU9','BkiUeR_xK6nrxqmo0hda'])
    d['review_required']=c|ec|d.domain_applicability_review|d.case_language_review
    d['Q_core_mean']=100*(Z@v);d['Q_core_min']=100*Z.min(1)
    d['Q_candidate']=robust_score(Z,v,lam)
    d['delta_vs_core']=d.Q_candidate-d.Q_core_mean
    d['delta_vs_original']=d.Q_candidate-d.Q_original
    d['score_status']='candidate_not_validated'
    # The scenario interval expresses preference uncertainty, not a confidence interval.
    d['Q_scenario_low']=robust_score(Z,v,.5);d['Q_scenario_high']=robust_score(Z,v,.1)
    d['Q_applicability_scenario']=d.Q_candidate.copy()
    code=d.domain.eq('github').to_numpy();keep=[i for i,g in enumerate(gn) if g not in ['expression','cleanliness']]
    d.loc[code,'Q_applicability_scenario']=robust_score(Z[code][:,keep],v[keep]/v[keep].sum(),lam)
    parts={'A1_full':a1,'A1_fit':fit,'A1_holdout':a1&~fit,'A2_full':d.dataset.eq('A2').to_numpy(),'A2_overlap':d.dataset.eq('A2').to_numpy()&~new,'A2_new':d.dataset.eq('A2').to_numpy()&new,'A3_full':d.dataset.eq('A3').to_numpy(),'A3_overlap':d.dataset.eq('A3').to_numpy()&~new,'A3_new':d.dataset.eq('A3').to_numpy()&new,'union_unique':unique}
    rates=[];summ=[];pair=[];models=[];sen=[]
    for part,m in parts.items():
        for dom in ['ALL']+sorted(d.loc[m,'domain'].unique()):
            mask=m if dom=='ALL' else m&d.domain.eq(dom).to_numpy()
            row={'partition':part,'domain':dom,'n':int(mask.sum()),'n_conflict':int(c[mask].sum()),'conflict_rate':float(c[mask].mean()),'education_disagreement_n':int(ec[mask].sum()),'education_disagreement_rate':float(ec[mask].mean()),'value_ad_tradeoff_n':int(d.loc[mask,'value_ad_tradeoff'].sum())}
            row.update({k:int(d.loc[mask,'class'].eq(k).sum()) for k in ['positive_only','negative_only','middle']});rates.append(row)
            ss={'partition':part,'domain':dom,'n':int(mask.sum())}
            for col in ['Q_original','Q_core_mean','Q_core_min','Q_candidate','delta_vs_core','delta_vs_original','Q_applicability_scenario']:
                ss[col+'_mean']=float(d.loc[mask,col].mean())
            ss['Q_candidate_p10']=float(d.loc[mask,'Q_candidate'].quantile(.1));ss['Q_candidate_p90']=float(d.loc[mask,'Q_candidate'].quantile(.9));summ.append(ss)
        for g in range(5):
            for k in range(5):
                if g!=k:
                    hit=H[:,g]&L[:,k];pair.append({'partition':part,'high':gn[g],'low':gn[k],'n':int(hit[m].sum()),'rate':float(hit[m].mean())})
        r0=d.loc[m,'Q_original'].rank(pct=True);rc=d.loc[m,'Q_core_mean'].rank(pct=True)
        for la in cfg['lambda_sensitivity']:
            qs=robust_score(Z[m],v,la);rr=pd.Series(qs,index=r0.index).rank(pct=True)
            models.append({'partition':part,'lambda':la,'mean':float(qs.mean()),'p10':float(np.quantile(qs,.1)),'p90':float(np.quantile(qs,.9)),'delta_vs_core_mean':float((qs-d.loc[m,'Q_core_mean'].to_numpy()).mean()),'rank_correlation_original':float(rr.corr(r0)),'rank_correlation_core':float(rr.corr(rc)),'rank_shift_ge_10pp_vs_core':float(((rr-rc).abs()>=cfg['rank_shift_cutoff']).mean())})
    for name,cs in {'all16':cols,'without_DSIR13':[c for c in cols if not c.startswith('dsir_')],'core11':sum(groups.values(),[]),'groups5':gn}.items():
        A=d[cs].to_numpy()
        for tail in cfg['tail_sensitivity']:
            ll=np.quantile(A[fit],tail,axis=0);hh=np.quantile(A[fit],1-tail,axis=0);hit=(A<ll).any(1)&(A>hh).any(1)
            for part,m in parts.items():sen.append({'features':name,'tail_probability':tail,'partition':part,'n_conflict':int(hit[m].sum()),'rate':float(hit[m].mean())})
    thresholds=pd.DataFrame({'dimension':gn,'low':lo,'high':hi,'group_weight':v})
    thresholds.to_csv(out/'thresholds_and_weights.csv',index=False)
    for fn,rows in [('conflict_summary.csv',rates),('score_summary.csv',summ),('conflict_pairs.csv',pair),('lambda_sensitivity.csv',models),('threshold_sensitivity.csv',sen)]:pd.DataFrame(rows).to_csv(out/fn,index=False)
    # Domain composition decomposition with a specified, reproducible order.
    rt=pd.DataFrame(rates); aa=rt[(rt.partition=='A1_full')&(rt.domain!='ALL')].set_index('domain');uu=rt[(rt.partition=='union_unique')&(rt.domain!='ALL')].set_index('domain')
    a_rate=float(c[a1].mean());u_rate=float(c[unique].mean());standardized=float(((aa.n/aa.n.sum())*uu.conflict_rate).sum())
    (out/'composition_decomposition.json').write_text(json.dumps({'A1_rate':a_rate,'union_rate':u_rate,'union_reweighted_to_A1':standardized,'within_domain_change':standardized-a_rate,'composition_change':u_rate-standardized},indent=2))
    d['rank_original_pct']=np.nan;d['rank_candidate_pct']=np.nan
    d.loc[unique,'rank_original_pct']=d.loc[unique,'Q_original'].rank(pct=True);d.loc[unique,'rank_candidate_pct']=d.loc[unique,'Q_candidate'].rank(pct=True)
    d['rank_shift_pct']=d.rank_candidate_pct-d.rank_original_pct
    drop=cols
    export=d.loc[unique].drop(columns=drop)
    export.to_csv(root/'artifacts/sample_results.csv.gz',index=False,compression={'method':'gzip','mtime':0},float_format='%.10g')
    d[['dataset','id','domain','split']].to_csv(root/'artifacts/record_index.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    selection=pd.read_csv(root/'artifacts/case_selection.csv',dtype={'id':str})[['case_type','id']]
    selection.merge(export,on='id',validate='many_to_one').to_csv(root/'artifacts/case_scores.csv',index=False)
    # A deterministic review sample, NOT an annotated accuracy test.
    pool=export[export.dataset.eq('A1')].copy();pool['sample_hash']=pool.id.map(lambda x:hashlib.sha256(('review|'+x).encode()).hexdigest())
    review=pool.sort_values('sample_hash').groupby(['domain','class'],group_keys=False).head(3).drop(columns='sample_hash').copy()
    for col in ['human_conflict','cause_category','indicator_applicable','review_note','reviewer']:review[col]=''
    review.to_csv(root/'artifacts/review_sample_unlabeled.csv',index=False)
    # Mathematics checks: every vertex of the weight uncertainty simplex gives the closed form.
    rng=np.random.default_rng(cfg['seed']);t=rng.random((1000,5));up=np.minimum(1,t+rng.random(t.shape)*.05)
    q=robust_score(t,v,lam);vertices=100*((1-lam)*(t@v)[:,None]+lam*t)
    assert np.allclose(q,vertices.min(1))
    assert np.all(robust_score(up,v,lam)>=q-1e-12)
    assert np.all(q<=100*(t@v)+1e-12) and np.all(q>=100*t.min(1)-1e-12)
    assert np.isclose(robust_score(np.ones((1,5)),v,lam)[0],100)
    assert np.isclose(robust_score(np.zeros((1,5)),v,lam)[0],0)
    for r in rates:assert r['n']==sum(r[k] for k in ['n_conflict','positive_only','negative_only','middle'])
    assert np.isfinite(export.select_dtypes('number')).all().all()
    validation={'n_records':len(d),'n_unique':len(export),'A1_fit_n':int(fit.sum()),'max_q1_mean_error':max(x['abs_error'] for x in checks),'duplicate_metrics_consistent':True,'four_classes_partition':True,'robust_vertex_solution_checked':True,'monotonicity_checked':True,'range_and_bounds_checked':True,'manual_accuracy_test_performed':False,'review_sample_n':len(review),'review_sample_unlabeled':True,'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'platform':platform.platform(),'inputs_sha256':{p.name:digest(p) for p in inp.iterdir() if p.is_file()}}
    (val/'checks.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2))
    print(pd.DataFrame(summ).query('domain=="ALL"')[['partition','n','Q_original_mean','Q_core_mean_mean','Q_candidate_mean','delta_vs_core_mean']].to_string(index=False))
    print('validation passed; unlabeled review rows',len(review))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'experiments/runs/q1-conflict-trial-20260924-r01');args=ap.parse_args();main(args.root)
