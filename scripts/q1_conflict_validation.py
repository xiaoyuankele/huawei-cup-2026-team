"""WP-C validation runner. Real-data validation requires a recorded G2 acceptance.
--self-test uses synthetic interface data only; it is NOT empirical validation.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd

SEEDS=[20260923,20260924,20260925]
def topsis(x,w):
    a=np.sqrt((x*x)@w);b=np.sqrt(((1-x)**2)@w);return 100*a/(a+b)
def ranks(x):return pd.Series(x).rank(pct=True).to_numpy()
def rank_stats(a,b,rng,pairs=100000):
    ra,rb=ranks(a),ranks(b);n=len(a)
    i=rng.integers(n,size=pairs);j=rng.integers(n,size=pairs)
    da=np.sign(a[i]-a[j]);db=np.sign(b[i]-b[j]);ok=(i!=j)&(da!=0)&(db!=0)
    return {'pearson':float(np.corrcoef(a,b)[0,1]),'spearman':float(np.corrcoef(ra,rb)[0,1]),'rank_shift_ge_10pp':float((abs(ra-rb)>=.1).mean()),'sampled_pair_reversal':float((da[ok]!=db[ok]).mean()),'comparable_sampled_pairs':int(ok.sum())}
def bootstrap_fixed(rows,strata,seeds=SEEDS,reps=200):
    # Conditional row bootstrap: freeze fitted weights, thresholds and observed stratum counts.
    # Does not quantify fit uncertainty, source clustering or external population bias.
    labels=np.unique(strata);ixs=[np.flatnonzero(strata==g) for g in labels];result=[]
    for seed in seeds:
        rng=np.random.default_rng(seed);samples=[]
        for _ in range(reps):
            idx=np.concatenate([rng.choice(ix,len(ix),replace=True) for ix in ixs])
            samples.append(rows[idx].mean(0))
        b=np.array(samples)
        for j in range(rows.shape[1]):result.append({'seed':seed,'metric_index':j,'estimate':float(rows[:,j].mean()),'lower025':float(np.quantile(b[:,j],.025)),'upper975':float(np.quantile(b[:,j],.975)),'bootstrap_reps':reps})
    return result
def self_test(out):
    rng=np.random.default_rng(20260923);x=rng.uniform(.1,.9,(300,16));w=np.ones(16)/16;q=topsis(x,w)
    r=rank_stats(q,q,np.random.default_rng(1),10000)
    assert r['sampled_pair_reversal']==0 and np.isclose(r['spearman'],1)
    assert np.all(topsis(np.minimum(x+.01,1),w)>=q)
    tests=bootstrap_fixed(np.c_[q,np.ones(len(q))],np.repeat([0,1,2],100),reps=20)
    for t in tests:
        if t['metric_index']==1:assert t['lower025']==t['upper975']==1
    assert np.array_equal(topsis(x,w),topsis(x,w))
    out.mkdir(parents=True,exist_ok=True)
    (out/'synthetic_validation_tests.json').write_text(json.dumps({'passed':True,'input_kind':'synthetic_interface_only','n':300,'seeds':SEEDS,'tests':['identity_rank_reversal_zero','identity_spearman_one','topsis_monotonicity','bootstrap_constant_interval','deterministic_score_repeatability'],'real_data_bootstrap_performed':False},indent=2))
    print('Synthetic interface tests passed; no real-data validation was run.')
def main(root,gate):
    if gate is None or not gate.exists():raise SystemExit('G2 evidence missing. Run --self-test or supply --gate-record after team acceptance.')
    g=json.loads(gate.read_text())
    required={'gate':'G2','model_status':'PACKAGE_ACCEPTED','peer_reviewer_actor':'ACTOR-3','release_integrator_actor':'ACTOR-1','upstream_run_id':'q1-critic-topsis-20260924-r01'}
    if any(g.get(k)!=v for k,v in required.items()) or not g.get('peer_review_evidence') or not g.get('integrator_evidence'):
        raise SystemExit('Gate record incomplete: require accepted WP-B run and distinct reviewer/integrator evidence.')
    # This guard checks record completeness, not authenticity; reviewers verify linked evidence.
    d=pd.read_csv(root/'artifacts/normalized_records.csv.gz',float_precision='round_trip');pm=json.loads((root/'inputs/q1_model.json').read_text());cols=list(pm['weights']);w=np.array(list(pm['weights'].values()));X=d[cols].to_numpy();q=topsis(X,w)
    result=pd.read_csv(root/'artifacts/sample_results.csv.gz');d=d.merge(result[['id','class','Q_candidate','Q_core_mean']],on='id',validate='many_to_one')
    a1=d.dataset.eq('A1').to_numpy();new=~d.id.isin(set(d.loc[a1,'id'])).to_numpy()
    parts={'A1_fit':a1&d.split.eq('fit').to_numpy(),'A1_holdout':a1&d.split.eq('holdout').to_numpy(),'A2_overlap':d.dataset.eq('A2').to_numpy()&~new,'A2_new':d.dataset.eq('A2').to_numpy()&new,'A3_overlap':d.dataset.eq('A3').to_numpy()&~new,'A3_new':d.dataset.eq('A3').to_numpy()&new,'union_unique':~d.id.duplicated().to_numpy()}
    dest=root/'validation/formal_after_G2';dest.mkdir(parents=True,exist_ok=True);ci=[];sens=[];comparisons=[]
    for part,m in parts.items():
        n=int(m.sum());z=X[m];base=q[m]
        metrics=np.c_[base,d.loc[m,'Q_candidate'],d.loc[m,'class'].eq('conflict').to_numpy().astype(float)]
        for row in bootstrap_fixed(metrics,d.loc[m,'domain'].to_numpy()):ci.append({'partition':part,'n':n,'metric':['Q_original_mean','Q_candidate_mean','conflict_rate'][row.pop('metric_index')],**row})
        for name,other in [('CRITIC_SUM',100*(z@w)),('EQUAL_SUM',100*z.mean(1)),('Q_candidate',d.loc[m,'Q_candidate'].to_numpy())]:
            comparisons.append({'partition':part,'method':name,**rank_stats(base,other,np.random.default_rng(20260923))})
        for seed in SEEDS:
            rng=np.random.default_rng(seed)
            for epsilon in [.1,.2]:
                for draw in range(20):
                    ww=w*(1+rng.uniform(-epsilon,epsilon,len(w)));ww/=ww.sum();other=topsis(z,ww)
                    sens.append({'partition':part,'seed':seed,'draw':draw,'relative_weight_radius':epsilon,'n':n,**rank_stats(base,other,rng,20000)})
        print('validated',part,flush=True)
    pd.DataFrame(ci).to_csv(dest/'conditional_bootstrap.csv',index=False);pd.DataFrame(sens).to_csv(dest/'weight_perturbation.csv',index=False);pd.DataFrame(comparisons).to_csv(dest/'method_rank_reversal.csv',index=False)
    (dest/'gate_record_used.json').write_text(json.dumps(g,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'experiments/runs/q1-conflict-trial-20260924-r01');ap.add_argument('--gate-record',type=Path);ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
    self_test(a.root/'validation') if a.self_test else main(a.root,a.gate_record)
