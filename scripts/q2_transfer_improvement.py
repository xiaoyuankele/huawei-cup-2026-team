"""Preplanned nested-group transfer experiments; v1 is read-only.

Outputs are calibration development evidence, not new independent joint data.
All target-label operations are restricted to the corresponding calibration
fold. Small-sample repeats are descriptive, not independent experiments.
"""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from scipy.stats import spearmanr
from sklearn.model_selection import KFold

from q2_research_paths import REPO as ROOT, RAW_ROOT, RUNS, source_ref
OUT = RUNS/'q2-transfer-improvement-20260925'
MODEL = RUNS/'q2-model-finalization-20260925/model_parameters.json'
BRIDGE = RUNS/'q2-quality-scaling-linkage-20260925/q1_to_q2_quality_linkage.csv'
B2 = RAW_ROOT/"B_scaling_laws/cerebras_training_log.csv"
PLAN = ROOT/'docs/problem/q2-transfer-improvement-experiment-plan.md'
SEED = 20260925
KINDS = ['raw', 'offset', 'affine', 'mean']
FREE = dict(raw=0, offset=1, affine=2, mean=1)


def fingerprint(f):
    return hashlib.sha256(f.read_bytes()).hexdigest()


def metrics(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    residual = pred-y
    den = np.sum((y-y.mean())**2)
    return dict(n=len(y), mae=float(np.mean(abs(residual))),
                rmse=float(np.sqrt(np.mean(residual**2))),
                r2=float(1-np.sum(residual**2)/den) if den > 0 else None,
                signed_error=float(residual.mean()),
                spearman=float(spearmanr(y,pred).statistic) if np.std(pred)>1e-12 else None)


def fit_calibration(train, kind, raw_intercept):
    x = train.x.to_numpy()
    response = (train.y-train.q).to_numpy()
    if kind == 'raw':
        return float(raw_intercept), 1.
    if kind == 'mean':
        return float(response.mean()), 0.
    if kind == 'offset':
        return float(np.mean(response-x)), 1.
    dx, dy = x-x.mean(), response-response.mean()
    slope = max(0., float(dx@dy/(dx@dx))) if dx@dx > 1e-20 else 0.
    return float(response.mean()-slope*x.mean()), slope


def predict(frame, coef):
    a, c = coef
    return frame.q.to_numpy()+a+c*frame.x.to_numpy()


def select(inner_scores, candidates):
    means = inner_scores[inner_scores.model.isin(candidates)].groupby('model').mae.mean().to_dict()
    best = min(means.values())
    eligible = [m for m,v in means.items() if v <= best*1.05+1e-14]
    return min(eligible, key=lambda m:(FREE[m], means[m], m))


def split_groups(groups, n_splits, seed):
    unique = np.array(sorted(set(groups)),dtype=object)
    mapping = {}
    for fold, (_, test) in enumerate(KFold(n_splits,shuffle=True,random_state=seed).split(unique)):
        mapping.update({g:fold for g in unique[test]})
    return mapping


def nested(frame, task, branch, axis, raw_intercept, b_mode=False):
    meta = dict(task=task, branch=branch, axis=axis)
    candidates = ['mean','offset','affine'] if branch=='connection' else KINDS
    preds, coefs, inners, splits, choices = [], [], [], [], []
    folds = sorted(frame.fold.unique())
    for fold in folds:
        train, test = frame[frame.fold!=fold].copy(), frame[frame.fold==fold].copy()
        assert set(train.group).isdisjoint(test.group)
        # Fix inner folds from group IDs only, without looking at target Loss.
        igroups = sorted(train.group.unique())
        imap = {g:i for i,g in enumerate(igroups)} if b_mode else split_groups(igroups,4,SEED+int(fold)+1)
        train['inner_fold'] = train.group.map(imap)
        fold_scores = []
        for inner in sorted(train.inner_fold.unique()):
            fit = train[train.inner_fold!=inner]
            val = train[train.inner_fold==inner]
            assert set(fit.group).isdisjoint(val.group)
            for kind in candidates:
                coef = fit_calibration(fit,kind,raw_intercept)
                # Each B validation fold is a complete trajectory. A folds
                # contain recipe groups, never rows split within a recipe.
                row = dict(**meta, outer_fold=int(fold), inner_fold=int(inner),
                           model=kind, **metrics(val.y,predict(val,coef)))
                fold_scores.append(row)
                inners.append(row)
        chosen = select(pd.DataFrame(fold_scores),candidates)
        choices.append(dict(**meta,fold=int(fold),selected=chosen))
        for _, row in train.iterrows():
            splits.append(dict(**meta,outer_fold=int(fold),source_id=row.source_id,
                               group=row.group,role='calibration',inner_fold=int(row.inner_fold)))
        for _, row in test.iterrows():
            splits.append(dict(**meta,outer_fold=int(fold),source_id=row.source_id,
                               group=row.group,role='test',inner_fold=-1))
        for kind in KINDS+['selected']:
            actual_kind = chosen if kind=='selected' else kind
            coef = fit_calibration(train,actual_kind,raw_intercept)
            coefs.append(dict(**meta,fold=int(fold),model=kind,actual_model=actual_kind,
                              intercept=coef[0],slope=coef[1],n_calibration=len(train),
                              n_calibration_groups=train.group.nunique(),n_test=len(test)))
            for (_, r), pred in zip(test.iterrows(),predict(test,coef)):
                preds.append(dict(**meta,fold=int(fold),model=kind,actual_model=actual_kind,
                                  source_id=r.source_id,group=r.group,actual=float(r.y),
                                  predicted=float(pred),x_frozen=float(r.x),q_frozen=float(r.q),
                                  coordinate_1=float(r.coordinate_1),coordinate_2=float(r.coordinate_2)))
    return [pd.DataFrame(r) for r in [preds,coefs,inners,splits,choices]]


def small_sample(frame, task, branch, axis, raw_intercept, b_mode=False):
    rows = []
    for fold in sorted(frame.fold.unique()):
        train, test = frame[frame.fold!=fold],frame[frame.fold==fold]
        groups = sorted(train.group.unique())
        for size in ([1,2,4] if b_mode else [8,16,32]):
            if b_mode:
                sets = list(combinations(groups,size))
            else:
                sets = [np.random.default_rng(SEED+i).choice(groups,size,replace=False).tolist() for i in range(5)]
            for repetition, subset in enumerate(sets):
                cal = train[train.group.isin(subset)]
                assert set(cal.group).isdisjoint(test.group)
                for kind in KINDS:
                    coef = fit_calibration(cal,kind,raw_intercept)
                    rows.append(dict(task=task,branch=branch,axis=axis,fold=int(fold),
                                     n_calibration_groups=size,n_calibration_rows=len(cal),
                                     repetition=repetition,calibration_groups=';'.join(subset),
                                     model=kind,intercept=coef[0],slope=coef[1],
                                     **metrics(test.y,predict(test,coef))))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources = [MODEL,BRIDGE,B2,PLAN]
    before = {source_ref(f):fingerprint(f) for f in sources}
    frozen = json.loads(MODEL.read_text(encoding='utf-8'))
    b = pd.read_csv(B2)
    p = frozen['scale']['parameters']
    b['x'] = p['E']+p['A']*b.N_params_B**(-p['alpha'])+p['B']*b.D_tokens_B**(-p['beta'])
    b['q'],b['y'],b['group'] = 0., b.val_loss,b.run_id
    b['source_id'] = ['B2_row_'+str(i) for i in b.index]
    order = b.groupby('group').N_params_B.first().sort_values().index.tolist()
    b['fold'] = b.group.map({g:i for i,g in enumerate(order)})
    b['coordinate_1'],b['coordinate_2'] = b.N_params_B,b.D_tokens_B
    assert b.group.nunique()==7
    jobs = [(b,'B2','scale','none',0.,True)]

    bridge = pd.read_csv(BRIDGE)
    obs = bridge[bridge.loss_observed==True].copy()
    mix = frozen['mixture']
    cols = mix['columns']
    matrix = obs[cols].to_numpy()
    assert np.isfinite(matrix).all() and (matrix>=0).all() and np.allclose(matrix.sum(axis=1),1)
    obs['group'] = ['recipe_'+hashlib.sha256(np.asarray(row,dtype='<f8').tobytes()).hexdigest()[:16]
                    for row in np.round(matrix,10)]
    distinct = obs.drop_duplicates('group')[cols].to_numpy()
    minimum_distance = float(pdist(distinct,metric='chebyshev').min())
    assert minimum_distance > 1e-8, 'Near duplicate recipe groups require a merged split'
    train = obs[obs.dataset=='A4_A5_train_1m']
    assert set(train.group).isdisjoint(obs[obs.dataset!='A4_A5_train_1m'].group)
    obs['x'] = (matrix-np.asarray(mix['p_reference']))@np.asarray(mix['full_coefficients'])
    obs['q'],obs['y'] = 0.,obs.loss_mean_13_domains
    obs['source_id'] = obs.dataset+'_'+obs['index'].astype(str)
    obs['coordinate_1'],obs['coordinate_2'] = obs['index'].astype(float),0.
    assigned = []
    for label,dataset in [('A60M','A8_A9_test_60m'),('A1B','A10_A11_test_1b')]:
        a = obs[obs.dataset==dataset].copy()
        mapping = split_groups(a.group,5,SEED)
        a['fold'] = a.group.map(mapping)
        jobs.append((a,label,'full_mixture','none',mix['intercept'],False))
        assignment = a[['dataset','source_id','group','fold']].copy()
        assigned.append(assignment)
        if label=='A60M':
            paired = obs[obs.dataset=='A6_A7_test_1m'].copy()
            assert set(paired.group)==set(a.group)
            paired['fold'] = paired.group.map(mapping)
            assigned.append(paired[['dataset','source_id','group','fold']])
        xp = a[cols].to_numpy()-np.asarray(mix['p_reference'])
        for axis,am in mix['axes'].items():
            qa = a[cols].to_numpy()@np.asarray(am['domain_quality'])
            assert np.allclose(qa,a[axis])
            qb = np.clip(.1+.9*(qa-am['Q_A_train_min'])/(am['Q_A_train_max']-am['Q_A_train_min']),.1,1.)
            gm = frozen['quality']
            dq = gm['coefficient']*(qb-am['Q_B_reference'] if gm['form']=='scale_Q' else np.log(qb/am['Q_B_reference']))
            residual = xp-(qa-am['Q_A_reference'])[:,None]*np.asarray(am['p_on_Q_loading'])
            conn = a.copy()
            conn['x'] = residual@np.asarray(am['residual_loss_coefficients'])
            conn['q'] = dq
            jobs.append((conn,label,'connection',axis,mix['intercept'],False))
    pd.concat(assigned).to_csv(OUT/'A_recipe_fold_assignments.csv',index=False)

    parts = [[] for _ in range(5)]
    for job in jobs:
        for bucket, frame in zip(parts,nested(*job)):
            bucket.append(frame)
    pred,coef,inner,splits,choice = [pd.concat(bucket,ignore_index=True) for bucket in parts]
    for df,name in zip([pred,coef,inner,splits,choice],['outer_predictions','calibration_coefficients','inner_validation','split_manifest','model_selection']):
        df.to_csv(OUT/(name+'.csv'),index=False,encoding='utf-8-sig')
    keys = ['task','branch','axis']
    foldrows = []
    for key,g in pred.groupby(keys+['model','fold']):
        foldrows.append(dict(zip(keys+['model','fold'],key),**metrics(g.actual,g.predicted)))
    foldmetrics = pd.DataFrame(foldrows)
    foldmetrics.to_csv(OUT/'outer_fold_metrics.csv',index=False)
    rows = []
    for key,g in pred.groupby(keys+['model']):
        local = foldmetrics
        for col,val in zip(keys+['model'],key):
            local = local[local[col]==val]
        rows.append(dict(zip(keys+['model'],key),**metrics(g.actual,g.predicted),
                         macro_fold_mae=float(local.mae.mean()),macro_fold_rmse=float(local.rmse.mean()),
                         worst_fold_mae=float(local.mae.max())))
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT/'performance_summary.csv',index=False)
    decisions = []
    for key,g in summary.groupby(keys):
        indexed = g.set_index('model')
        raw,sel,mean = [indexed.loc[m] for m in ['raw','selected','mean']]
        folds = foldmetrics
        for col,val in zip(keys,key):
            folds=folds[folds[col]==val]
        pivot=folds.pivot(index='fold',columns='model',values='mae')
        improved=int((pivot.selected<pivot.raw).sum())
        base_mae=raw.macro_fold_mae if key[0]=='B2' else raw.mae
        sel_mae=sel.macro_fold_mae if key[0]=='B2' else sel.mae
        gain=float(1-sel_mae/base_mae)
        practical=bool(gain>=.1 and sel.rmse<=raw.rmse and improved >= (5 if key[0]=='B2' else 4))
        extra=bool(sel.mae<mean.mae and sel.rmse<=mean.rmse)
        decisions.append(dict(zip(keys,key),mae_reduction_vs_raw=gain,improved_folds=improved,
                              practical_calibration_pass=practical,beats_mean_or_quality_only=extra,
                              mae_reduction_vs_mean_or_quality_only=float(1-sel.mae/mean.mae),
                              interpretation=('calibration_and_shape_supported' if practical and extra else
                                              'calibration_only' if practical else 'predefined_gate_not_met')))
    decisions=pd.DataFrame(decisions)
    decisions.to_csv(OUT/'decisions.csv',index=False)
    refits=[]
    for frame,task,branch,axis,mu,bmode in jobs:
        decision=decisions[(decisions.task==task)&(decisions.branch==branch)&(decisions.axis==axis)].iloc[0]
        for kind in KINDS:
            ac=fit_calibration(frame,kind,mu)
            refits.append(dict(task=task,branch=branch,axis=axis,model=kind,
                               intercept=ac[0],slope=ac[1],n_target_labels=len(frame),
                               interpretation='full_target_refit_not_validation',
                               branch_supported_beyond_simple_baseline=bool(decision.beats_mean_or_quality_only),
                               v1_updated=False))
    pd.DataFrame(refits).to_csv(OUT/'full_target_refits.csv',index=False)
    print(summary[['task','branch','axis','model','mae','rmse','r2']].to_string(index=False),flush=True)
    print(decisions.to_string(index=False),flush=True)

    # Secondary sensitivity is run only where main calibration and shape
    # both improve; it does not alter main candidate selection or gates.
    small=[]
    for job in jobs:
        frame,task,branch,axis,mu,bmode=job
        decision=decisions[(decisions.task==task)&(decisions.branch==branch)&(decisions.axis==axis)].iloc[0]
        if branch!='connection' and decision.practical_calibration_pass and decision.beats_mean_or_quality_only:
            small.append(small_sample(*job))
    if small:
        small=pd.concat(small,ignore_index=True)
        small.to_csv(OUT/'small_sample_detail.csv',index=False)
        small.groupby(keys+['n_calibration_groups','model']).agg(
            evaluations=('mae','size'),mae_mean=('mae','mean'),mae_median=('mae','median'),
            mae_min=('mae','min'),mae_max=('mae','max'),rmse_mean=('rmse','mean')).to_csv(OUT/'small_sample_summary.csv')

    # Descriptive residual trend check; never used for tuning this run.
    diag=[]
    for (model,group),g in pred[pred.task=='B2'].groupby(['model','group']):
        diag.append(dict(model=model,trajectory=group,
            residual_logD_spearman=float(spearmanr(g.predicted-g.actual,np.log(g.coordinate_2)).statistic),
            residual_mean=float((g.predicted-g.actual).mean())))
    pd.DataFrame(diag).to_csv(OUT/'B2_residual_diagnostics.csv',index=False)

    # Verification: disjointness, all-row OOF coverage, reconstruction and
    # selection using inner data, plus immutable source/parameter files.
    assert not pred.duplicated(keys+['model','source_id']).any()
    assert np.isfinite(pred[['actual','predicted']]).all().all()
    # Check that the stored selected label can be recovered from inner-only
    # evidence, and selected predictions equal their chosen candidate.
    for _,r in choice.iterrows():
        evidence=inner[(inner.task==r.task)&(inner.branch==r.branch)&(inner.axis==r.axis)&(inner.outer_fold==r.fold)]
        candidates=['mean','offset','affine'] if r.branch=='connection' else KINDS
        assert select(evidence,candidates)==r.selected
        sample=pred[(pred.task==r.task)&(pred.branch==r.branch)&(pred.axis==r.axis)&(pred.fold==r.fold)]
        chosen_pred=sample[sample.model==r.selected].set_index('source_id').predicted.sort_index()
        selected_pred=sample[sample.model=='selected'].set_index('source_id').predicted.sort_index()
        assert np.allclose(chosen_pred,selected_pred)
    merged=pred.merge(coef,on=keys+['fold','model','actual_model'],validate='many_to_one')
    assert np.allclose(merged.predicted,merged.q_frozen+merged.intercept+merged.slope*merged.x_frozen)
    for job in jobs:
        frame,task,branch,axis,mu,bmode=job
        g=pred[(pred.task==task)&(pred.branch==branch)&(pred.axis==axis)]
        assert g.groupby('model').size().eq(len(frame)).all()
    after={source_ref(f):fingerprint(f) for f in sources}
    assert before==after
    manifest=dict(status='EXPLORATORY_NESTED_GROUP_VALIDATION',seed=SEED,input_sha256=before,
        script_sha256=fingerprint(Path(__file__)),minimum_distinct_recipe_chebyshev_distance=minimum_distance,
        selected_model_rule='inner macro MAE; within 5 percent select fewer free parameters',
        candidates=KINDS,nonnegative_slopes=True,
        sensitivity_repeats_are_independent_experiments=False,
        limitation='Previously examined data, not a pristine final test; B2 is semi-synthetic; no joint A-B validation',
        checks=dict(input_and_v1_unchanged=True,group_disjoint=True,all_rows_have_one_oof_prediction_per_model=True,
                    parameter_prediction_reconstruction=True,finite_predictions=True,
                    selection_recovered_from_inner_evidence=True),
        outer_prediction_rows=len(pred))
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
