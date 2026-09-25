"""Q3 exploratory optimization against frozen Q2 v1; never fits synthetic rows.

Run with the scientific Python environment (NumPy, pandas, SciPy).
Frozen public inputs are hash-checked. Outputs default to local/q3-reproduction.
Set Q3_OUTPUT_ROOT to change output; optionally Q3_RAW_ROOT to verify private C7.
"""
from pathlib import Path
import json, hashlib, shutil, sys, platform
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import linprog, brentq, minimize_scalar, minimize

# AI-assisted implementation; numerical checks do not replace independent review.
import os
REPO = Path(__file__).resolve().parents[1]
CONFIG = json.loads((REPO/'configs/q3-frozen-q2-exploration.json').read_text(encoding='utf-8'))
OUT = Path(os.environ.get('Q3_OUTPUT_ROOT', str(REPO/'local/q3-reproduction'))).resolve()
ARCHIVE = (REPO/'experiments/runs/q3-frozen-q2-exploration-20260925-r01').resolve()
if OUT == ARCHIVE or ARCHIVE in OUT.parents:
    raise ValueError('Choose a separate output directory; the reviewed archive is immutable')
OUT.mkdir(parents=True, exist_ok=True)
SOURCES = {name: REPO/record['path'] for name,record in CONFIG['inputs'].items()}
for name,path in SOURCES.items():
    if hashlib.sha256(path.read_bytes()).hexdigest() != CONFIG['inputs'][name]['sha256']:
        raise ValueError('Frozen input hash mismatch: '+name)
if os.environ.get('Q3_RAW_ROOT'):
    raw = Path(os.environ['Q3_RAW_ROOT'])/CONFIG['private_sources']['C7']['relative_path']
    if hashlib.sha256(raw.read_bytes()).hexdigest() != CONFIG['private_sources']['C7']['sha256']:
        raise ValueError('C7 hash mismatch')
    if sorted(pd.read_csv(raw).max_position_embeddings.unique().tolist()) != CONFIG['context_values']:
        raise ValueError('C7 context extract mismatch')
M = json.loads((SOURCES['model_parameters.json']).read_text(encoding='utf-8'))
PARAM = M['scale']['parameters']
E,A,B,AL,BE = [PARAM[k] for k in ('E','A','B','alpha','beta')]
COLS = M['mixture']['columns']; P0 = np.array(M['mixture']['p_reference'])
BRIDGE = pd.read_csv(SOURCES['q1_to_q2_quality_linkage.csv'])
TRAIN = BRIDGE[BRIDGE.dataset=='A4_A5_train_1m'].copy()
P = TRAIN[COLS].to_numpy(float)
assert np.allclose(P.sum(1),1) and np.all(P>=0)
CTX = CONFIG['context_values']
BUDGETS = CONFIG['budgets']
ETA = CONFIG['eta']
COEF = M['quality']['coefficient']
assert M['quality']['form']=='scale_Q' and COEF<0

def transport(q, ax):
    return np.clip(.1+.9*(q-ax['Q_A_train_min'])/(ax['Q_A_train_max']-ax['Q_A_train_min']), .1, 1.)

def components(p, axis):
    ax=M['mixture']['axes'][axis]; q=np.array(ax['domain_quality'])
    qa=np.asarray(p)@q
    r=np.asarray(p)-P0-np.expand_dims(qa-ax['Q_A_reference'],-1)*np.array(ax['p_on_Q_loading'])
    return qa, COEF*(transport(qa,ax)-ax['Q_B_reference']), r@np.array(ax['residual_loss_coefficients'])

def p_opt(axis,lq,lp,mode):
    ax=M['mixture']['axes'][axis]
    if mode=='reference' or (lq==0 and lp==0): return P0.copy(),np.nan
    if mode=='observed_training':
        _,dq,dp=components(P,axis); idx=int(np.argmin(lq*dq+lp*dp))
        return P[idx].copy(),int(TRAIN.iloc[idx]['index'])
    # Clipped affine Q response has three affine regions; solve an LP in each.
    basis=np.eye(17) if mode=='full_simplex' else P
    q=np.array(ax['domain_quality']); w=np.array(ax['residual_loss_coefficients'])
    v=np.array(ax['p_on_Q_loading']); coeff=w-q*(v@w)
    bq=basis@q; bp=basis@coeff; slope=.9/(ax['Q_A_train_max']-ax['Q_A_train_min'])
    best=None
    for low,high,m in [(None,ax['Q_A_train_min'],0),(ax['Q_A_train_min'],ax['Q_A_train_max'],slope),(ax['Q_A_train_max'],None,0)]:
        ub=[]; rhs=[]
        if low is not None: ub.append(-bq); rhs.append(-low)
        if high is not None: ub.append(bq); rhs.append(high)
        fit=linprog(lp*bp+lq*COEF*m*bq,A_ub=np.array(ub),b_ub=rhs,
                    A_eq=np.ones((1,len(basis))),b_eq=[1],bounds=(0,None),method='highs')
        if not fit.success: continue
        p=fit.x@basis
        _,dq,dp=components(p,axis); val=float(lq*dq+lp*dp)
        if best is None or val<best[0]: best=(val,p)
    assert best is not None
    return best[1],np.nan

def nd_opt(C,ctx,b=0.,scope='unrestricted'):
    """Exact conditional ND optimum; N,D in billions, b=g_increment/1e9."""
    c=C/1e18; a=6+ETA*ctx
    if b==0: n=(AL*A*c**BE/(BE*B*a**BE))**(1/(AL+BE))
    else:
        def eq(logn):
            return np.log(BE*B*a/(AL*A))-BE*np.log(c)+(1+AL)*logn+(BE-1)*np.logaddexp(np.log(a)+logn,np.log(b))
        n=np.exp(brentq(eq,-60,60,xtol=1e-12))
    if scope=='B1_rectangle':
        nmin,nmax=M['scale']['support']['N_params_B']; dmin,dmax=M['scale']['support']['D_tokens_B']
        hi=min(nmax,(c/dmin-b)/a)
        if hi<nmin: return None
        n=np.clip(max(n,(c/dmax-b)/a),nmin,hi)
        d=min(dmax,c/(a*n+b))
    else: d=c/(a*n+b)
    loss=E+A*n**(-AL)+B*d**(-BE)
    return float(n),float(d),float(loss)

def cost(q,kind):
    if kind=='exponential': return 1e7*np.exp(6*q)
    if kind=='power': return 5e9*q**4
    if kind=='logarithmic': return 2e9*np.log1p(10*q)
    raise ValueError(kind)

def record_nd(n,d,C,ctx,b):
    tr=6*n*d*1e18; at=ETA*ctx*n*d*1e18; qu=d*1e9*(b*1e9)
    nr=M['scale']['support']['N_params_B']; dr=M['scale']['support']['D_tokens_B']
    return dict(N_B=n,D_B=d,train_share=tr/C,attention_share=at/C,quality_share=qu/C,
                utilization=(tr+at+qu)/C,N_outside_B1=not(nr[0]-1e-8<=n<=nr[1]+1e-8),
                D_outside_B1=not(dr[0]-1e-8<=d<=dr[1]+1e-8))

def process_opt(C,ctx,axis,kind,p,scope='unrestricted',lq=1.,coord='Q_A',grid_size=65):
    """Hypothesis only: treatment raises Q at fixed p; residual p is frozen.
    Q2 itself has no such independently identified intervention.
    """
    ax=M['mixture']['axes'][axis]; qa0,dq0,dp=components(p,axis)
    qb0=float(transport(qa0,ax))
    if coord=='Q_A': q0=float(qa0); qtop=max(q0,ax['Q_A_train_max'])
    else: q0=qb0; qtop=1.
    def objective(q,detail=False):
        b=max(float(cost(q,kind)-cost(q0,kind)),0)/1e9
        nd=nd_opt(C,ctx,b,scope)
        if nd is None: return np.inf
        n,d,base=nd; qb=float(transport(q,ax)) if coord=='Q_A' else q
        pred=base+lq*COEF*(qb-ax['Q_B_reference'])+float(dp)
        return (pred,nd,b,qb) if detail else pred
    grid=np.linspace(q0,qtop,grid_size); vals=np.array([objective(q) for q in grid])
    candidates=[(vals[0],q0),(vals[-1],qtop)]
    for i in range(1,len(grid)-1):
        if vals[i]<=vals[i-1] and vals[i]<=vals[i+1]:
            sol=minimize_scalar(objective,bounds=(grid[i-1],grid[i+1]),method='bounded',options={'xatol':1e-12})
            candidates.append((sol.fun,sol.x))
    val,q=min(candidates)
    pred,(n,d,base),b,qb=objective(q,True)
    zero=objective(q0)
    return dict(budget=C,context=int(ctx),axis=axis,cost=kind,scope=scope,lambda_q=lq,cost_coordinate=coord,
                Q0=q0,Q_star=float(q),Q_B_star=qb,Q_upper=qtop,
                regime='no_processing' if abs(q-q0)<1e-6 else (('map_saturation' if coord=='Q_A' else 'quality_upper') if abs(q-qtop)<1e-6 else 'interior'),
                predicted_loss=pred,scale_loss=base,remaining_p=float(dp),benefit_vs_same_recipe_no_processing=zero-pred,
                **record_nd(n,d,C,ctx,b))

def main():
    recipes=[]; results=[]
    variants=[('scale_only',0,0),('quality_only',1,0),('v1',1,1),('half_p',1,.5),('low_p',1,.05)]
    for axis in M['mixture']['axes']:
        for variant,lq,lp in variants:
            for mode in ['reference','observed_training','training_hull','full_simplex']:
                p,idx=p_opt(axis,lq,lp,mode); qa,dq,dp=components(p,axis)
                row=dict(axis=axis,variant=variant,mode=mode,recipe_index=idx,Q_A=float(qa),
                         Q_B=float(transport(qa,M['mixture']['axes'][axis])),delta_Q=float(dq),delta_p=float(dp),
                         total_correction=float(lq*dq+lp*dp),max_share=float(max(p)),dominant_domain=COLS[int(np.argmax(p))],
                         min_distance_to_training_L1=float(np.min(abs(P-p).sum(1))),**dict(zip(COLS,p)))
                recipes.append(row)
                for scope in ['unrestricted','B1_rectangle']:
                    for C in BUDGETS:
                        for ctx in CTX:
                            n,d,base=nd_opt(C,ctx,scope=scope)
                            results.append({k:row[k] for k in ['axis','variant','mode','total_correction','dominant_domain','max_share']} |
                                dict(scope=scope,budget=C,context=int(ctx),predicted_loss=base+row['total_correction'],scale_loss=base,
                                     **record_nd(n,d,C,ctx,0.)))
    rec=pd.DataFrame(recipes); res=pd.DataFrame(results)
    rec.to_csv(OUT/'recipe_optima.csv',index=False); res.to_csv(OUT/'frozen_v1_optima.csv',index=False)
    print('Frozen v1 scenarios:',len(res),flush=True)
    treatments=[]
    for axis in M['mixture']['axes']:
        for kind in ['exponential','power','logarithmic']:
            for ctx in CTX:
                for C in np.logspace(19,24,51):
                    for coord in ['Q_A','Q_B']:
                        treatments.append(process_opt(C,ctx,axis,kind,P0,coord=coord)|dict(recipe='reference'))
    print('Processing main sweep:',len(treatments),flush=True)
    # Targeted comparisons: quality transfer, recipe choice, cost coordinate, support.
    for axis in M['mixture']['axes']:
        best,_=p_opt(axis,1,1,'observed_training')
        for kind in ['exponential','power','logarithmic']:
            for C in BUDGETS:
                for ctx in [2048,32768,131072]:
                    for label,p in [('reference',P0),('best_observed',best)]:
                        for scope,lq,coord in [('B1_rectangle',1,'Q_A'),('unrestricted',.5,'Q_A'),
                                               ('unrestricted',0,'Q_A'),('unrestricted',1,'Q_B'),('unrestricted',1,'Q_A')]:
                            treatments.append(process_opt(C,ctx,axis,kind,p,scope,lq,coord)|dict(recipe=label))
    pro=pd.DataFrame(treatments).drop_duplicates(subset=['axis','cost','budget','context','recipe','scope','lambda_q','cost_coordinate'])
    pro.to_csv(OUT/'processing_scenarios.csv',index=False)
    transitions=[]
    main=pro[(pro.recipe=='reference')&(pro.scope=='unrestricted')&(pro.lambda_q==1)]
    for keys,g in main.groupby(['axis','cost','context','cost_coordinate']):
        rows=g.sort_values('budget').to_dict('records')
        for prev,next_ in zip(rows,rows[1:]):
            if prev['regime']!=next_['regime']:
                transitions.append(dict(zip(['axis','cost','context','cost_coordinate'],keys))|dict(budget_lo=prev['budget'],budget_hi=next_['budget'],
                    from_regime=prev['regime'],to_regime=next_['regime'],Q_before=prev['Q_star'],Q_after=next_['Q_star']))
    pd.DataFrame(transitions).to_csv(OUT/'transition_brackets.csv',index=False)
    # Decision regret within existing test candidate sets. Previously seen Q2 data;
    # exploratory retrospective evidence, not new independent validation.
    regrets=[]
    for axis in M['mixture']['axes']:
        for variant,lq,lp in variants:
            if variant=='scale_only': continue
            for dataset,g in BRIDGE[(BRIDGE.loss_observed==True)&(BRIDGE.role!='train')].groupby('dataset'):
                _,dq,dp=components(g[COLS].to_numpy(),axis)
                prediction=lq*dq+lp*dp; y=g.loss_mean_13_domains.to_numpy()
                selected=int(np.argmin(prediction)); top5=np.argsort(prediction)[:5]
                regrets.append(dict(axis=axis,variant=variant,dataset=dataset,n_candidates=len(g),
                    selected_recipe=int(g.iloc[selected]['index']),selected_observed_loss=float(y[selected]),
                    best_available_observed_loss=float(y.min()),candidate_mean_observed_loss=float(y.mean()),
                    regret=float(y[selected]-y.min()),improvement_vs_candidate_mean=float(y.mean()-y[selected]),
                    selected_actual_rank=int(1+(y<y[selected]).sum()),top5_mean_loss=float(y[top5].mean())))
    pd.DataFrame(regrets).to_csv(OUT/'retrospective_decision_regret.csv',index=False)
    # Independent raw N,D,Q constrained optimization, endpoints and grid refinement.
    checks=[]
    for axis in M['mixture']['axes']:
        for kind in ['exponential','power','logarithmic']:
            for C,ctx in [(1e19,2048),(1e22,32768),(1e24,131072)]:
                r=process_opt(C,ctx,axis,kind,P0)
                fine=process_opt(C,ctx,axis,kind,P0,grid_size=513)
                assert abs(r['predicted_loss']-fine['predicted_loss'])<1e-7
                ax=M['mixture']['axes'][axis]; q0=r['Q0']; qbref=ax['Q_B_reference']
                def obj(x):
                    n,d=np.exp(x[:2]); return E+A*n**(-AL)+B*d**(-BE)+COEF*(float(transport(x[2],ax))-qbref)
                def constraint(x):
                    n,d=np.exp(x[:2]); b=(cost(x[2],kind)-cost(q0,kind))/1e9
                    return 1-d*((6+ETA*ctx)*n+b)/(C/1e18)
                initial=[np.log(r['N_B']),np.log(r['D_B']),r['Q_star']]
                sl=minimize(obj,initial,method='SLSQP',bounds=[(-30,30),(-30,30),(q0,1)],
                            constraints=[{'type':'ineq','fun':constraint}],options={'ftol':1e-11,'maxiter':500})
                assert sl.success and abs(sl.fun-r['predicted_loss'])<1e-7
                assert constraint(sl.x)>-1e-7
                checks.append(dict(axis=axis,cost=kind,budget=C,context=ctx,dense_grid_difference=fine['predicted_loss']-r['predicted_loss'],
                                   full_NDQ_difference=sl.fun-r['predicted_loss'],constraint_slack=constraint(sl.x)))
    assert (pro.utilization<=1+1e-8).all() and (pro.benefit_vs_same_recipe_no_processing>=-1e-9).all()
    assert np.allclose(rec[COLS].sum(1),1) and (rec[COLS].min().min()>=-1e-9)
    assert (pro[pro.lambda_q==0].Q_star==pro[pro.lambda_q==0].Q0).all()
    # Exact comparison with frozen Q2's exported scenario predictions, without importing its fitting script.
    original=pd.read_csv(SOURCES['q2_scenarios.csv'])
    maxdiff=0.
    for axis,g in original.groupby('quality_axis'):
        _,dq,dp=components(g[COLS].to_numpy(),axis)
        n=g.N_params_B.to_numpy();d=g.D_tokens_B.to_numpy()
        pred=E+A*n**(-AL)+B*d**(-BE)+g.lambda_Q_assumed*dq+g.lambda_p_assumed*dp
        maxdiff=max(maxdiff,float(np.max(abs(pred-g.predicted_loss_scenario))))
    assert maxdiff<1e-10
    pd.DataFrame(checks).to_csv(OUT/'solver_crosschecks.csv',index=False)
    manifest=dict(status='EXPLORATION_ONLY',model_status=M['status'],source_repo_commit=CONFIG['historical_source_commit'], upstream_commit=CONFIG['upstream_commit'], run_id=CONFIG['run_id'],
        input_sha256={name:hashlib.sha256(SOURCES[name].read_bytes()).hexdigest() for name in SOURCES},
        source_paths={name:CONFIG['inputs'][name]['path'] for name in SOURCES},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=sys.version,platform=platform.platform(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,
        no_refitting=True,outputs_are_not_observations=True,quality_intervention_is_extra_assumption=True,
        frozen_prediction_max_difference=maxdiff,full_variable_crosschecks=len(checks),
        count_frozen=len(res),count_processing=len(pro),count_transition_brackets=len(transitions),
        costs={'exponential':'1e7 exp(6Q)','power':'5e9 Q^4','logarithmic':'2e9 log(1+10Q)'},
        critical_context=6/ETA,context_values=[int(c) for c in CTX],
        external_validation_not_performed=True,
        retrospective_candidate_set_evaluation='Q2 previously inspected A6/A8/A10 labels, no new blind validation',
        quality_cost_parameters_source='User DOCX appendix B, paragraphs 55-58',
        problem_docx_sha256=CONFIG['private_sources']['problem_document']['sha256'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
