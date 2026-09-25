"""Fit Q2 components, select a scale law, and export a conditional joint model.

Run with the scientific Python environment used for the earlier Q2 scripts.
Bundled Python lacks scipy/sklearn. No estimated Loss or generated scenario is
used for fitting. All quality and mixture transport coefficients are labelled.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GroupKFold

from q2_research_paths import REPO, RAW_ROOT, RUNS, source_ref
RAW = RAW_ROOT / "B_scaling_laws"
OUT = RUNS / 'q2-model-finalization-20260925'
BRIDGE = RUNS / 'q2-quality-scaling-linkage-20260925'
PARAM_NAMES = ['E', 'A', 'B', 'alpha', 'beta']


def score(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    return dict(n=len(y), mae=float(np.mean(abs(pred-y))),
                rmse=float(np.sqrt(np.mean((pred-y)**2))),
                r2=float(1-np.sum((pred-y)**2)/np.sum((y-y.mean())**2)))


def power(p, frame):
    n, d = frame[['N_params_B', 'D_tokens_B']].to_numpy(float).T
    e, a, b, alpha, beta = p
    return e+a*n**(-alpha)+b*d**(-beta)


def fit_power(frame):
    starts = [[1, .5, 1, .3, .3], [.1, 1, 2, .1, .1], [2, .1, .5, .7, .7]]
    fits = [least_squares(lambda p: power(p, frame)-frame.val_loss.to_numpy(), s,
                          bounds=([0, 0, 0, .001, .001], [10, 100, 100, 2, 2]),
                          xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=5000)
            for s in starts]
    fits = [f for f in fits if f.success]
    if not fits:
        raise RuntimeError('No converged power-law fit')
    return min(fits, key=lambda f: np.sum(f.fun**2)).x


def scale_fit(b1):
    rows, params, predictions = [], [], []
    folds = [('full_fit', b1, b1)]
    folds += [(f'leave_N_{n}', b1[b1.N_params_B != n], b1[b1.N_params_B == n])
              for n in sorted(b1.N_params_B.unique())]
    full_p = None
    for fold, train, test in folds:
        p = fit_power(train)
        if fold == 'full_fit':
            full_p = p
        params.append(dict(fold=fold, **dict(zip(PARAM_NAMES, p))))
        log = LinearRegression().fit(np.log(train[['N_params_B', 'D_tokens_B']]), train.val_loss)
        for name, pred in [('power', power(p, test)), ('log_linear', log.predict(np.log(test[['N_params_B', 'D_tokens_B']])) )]:
            rows.append(dict(fold=fold, model=name, **score(test.val_loss, pred)))
            if fold != 'full_fit':
                predictions.extend(dict(fold=fold, model=name, source_row=int(i), actual=float(y), predicted=float(z))
                                   for i, y, z in zip(test.index, test.val_loss, pred))
    pd.DataFrame(rows).to_csv(OUT/'scale_validation.csv', index=False)
    pd.DataFrame(params).to_csv(OUT/'scale_parameters_by_fold.csv', index=False)
    pr = pd.DataFrame(predictions)
    pr.to_csv(OUT/'scale_oof_predictions.csv', index=False)
    summary = [dict(model=name, **score(g.actual, g.predicted)) for name, g in pr.groupby('model')]
    pd.DataFrame(summary).to_csv(OUT/'scale_oof_summary.csv', index=False)
    external = []
    for fname in ['cerebras_training_log.csv', 'scaling_baseline.csv', 'published_scaling_data.csv']:
        df = pd.read_csv(RAW/fname)
        external.append(dict(source=fname, **score(df.val_loss, power(full_p, df))))
    pd.DataFrame(external).to_csv(OUT/'scale_external.csv', index=False)
    return full_p, summary


def quality_fit(b6, b7, p):
    keys = ['N_params_B', 'D_tokens_B', 'Q_score']
    joined = b7.merge(b6[keys].assign(old=True), on=keys, how='left', validate='one_to_one')
    new = joined[joined.old.isna()].drop(columns='old')
    folds = [('B6_to_B7_new', 'nonoverlap', b6, new)]
    for q in sorted(b7.Q_score.unique()):
        folds.append((f'Q_{q}', 'leave_Q', b7[b7.Q_score != q], b7[b7.Q_score == q]))
    groups = b7.groupby(['N_params_B', 'D_tokens_B']).ngroup()
    for k, (tr, te) in enumerate(GroupKFold(5).split(b7, groups=groups)):
        folds.append((f'ND_{k}', 'group_ND', b7.iloc[tr], b7.iloc[te]))

    def features(df, name):
        if name == 'scale_offset':
            return np.zeros((len(df), 1))
        if name == 'scale_Q':
            return (df[['Q_score']].to_numpy()-.55)
        if name == 'scale_logQ':
            return np.log(df[['Q_score']].to_numpy()/.55)
        x = np.log(df[['N_params_B', 'D_tokens_B']].to_numpy())
        return x if name == 'logND' else np.column_stack([x, df.Q_score])

    records, detail = [], []
    for fold, protocol, train, test in folds:
        for name in ['scale_offset', 'scale_Q', 'scale_logQ', 'logND', 'logNDQ']:
            fixed = name.startswith('scale_')
            y = train.val_loss.to_numpy() - (power(p, train) if fixed else 0)
            m = LinearRegression().fit(features(train, name), y)
            pred = m.predict(features(test, name)) + (power(p, test) if fixed else 0)
            records.append(dict(protocol=protocol, fold=fold, model=name, **score(test.val_loss, pred)))
            detail.extend(dict(protocol=protocol, fold=fold, model=name, actual=float(y), predicted=float(z))
                          for y, z in zip(test.val_loss, pred))
    pd.DataFrame(records).to_csv(OUT/'quality_validation_folds.csv', index=False)
    det = pd.DataFrame(detail)
    rows = [dict(protocol=proto, model=name, **score(g.actual, g.predicted))
            for (proto, name), g in det.groupby(['protocol', 'model'])]
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT/'quality_increment_summary.csv', index=False)
    # Select only the quality function from grouped ND validation, not B8.
    options = summary[(summary.protocol == 'group_ND') & summary.model.isin(['scale_Q', 'scale_logQ'])]
    selected = options.sort_values('rmse').iloc[0].model
    m = LinearRegression().fit(features(b7, selected), b7.val_loss-power(p, b7))
    return dict(form=selected, coefficient=float(m.coef_[0]), Q_reference=.55,
                source_offset_B7=float(m.intercept_), source_offset_transferred=False,
                selection='lowest pooled RMSE under 5-fold held-out (N,D) groups',
                evidence='B6/B7 semi-synthetic; not independent real training validation'), summary


def mixture_fit(quality):
    bridge = pd.read_csv(BRIDGE/'q1_to_q2_quality_linkage.csv')
    domain = pd.read_csv(BRIDGE/'q1_domain_quality_for_q2.csv').set_index('mixture_domain')
    cols = [c for c in bridge if c.startswith('p_')]
    train = bridge[bridge.dataset == 'A4_A5_train_1m']
    p0 = train[cols].mean().to_numpy()
    x = train[cols].to_numpy()-p0
    model = Ridge(alpha=1e-5).fit(x, train.loss_mean_13_domains)
    coef = model.coef_-model.coef_.mean()
    frozen = dict(columns=cols, p_reference=p0.tolist(), full_coefficients=coef.tolist(),
                  intercept=float(model.intercept_), ridge_alpha=1e-5, axes={})
    rows, rank_rows, coefficients = [], [], []
    for axis, domain_col in [('Q_A_topsis_0_1', 'q_topsis_domain_0_1'),
                             ('quality_score_soft_proxy_0_1', 'q_soft_0_1')]:
        q = domain.loc[[c[2:] for c in cols], domain_col].to_numpy()
        # Remove the linear component of p explained by Q on TRAINING data.
        # R = (p-p0) - loading*(Q-Q0); R is sample-uncorrelated with Q,
        # sums to zero, and q@R=0. This is a parameterization, not causality.
        qa0 = float(np.dot(p0, q))
        qc = train[axis].to_numpy()-qa0
        loading = (qc@x)/(qc@qc)
        residual = x-qc[:,None]*loading
        assert np.max(abs(qc@residual)) < 1e-10
        assert np.max(abs(residual@q)) < 1e-10
        assert np.max(abs(residual.sum(axis=1))) < 1e-10
        qmin, qmax = float(train[axis].min()), float(train[axis].max())
        assert np.allclose(train[cols].to_numpy()@q, train[axis], atol=1e-10)
        frozen['axes'][axis] = dict(domain_quality=q.tolist(), p_on_Q_loading=loading.tolist(),
            residual_loss_coefficients=coef.tolist(), Q_A_reference=qa0,
            A_quality_slope_removed=float(loading@coef),
            Q_A_train_min=qmin, Q_A_train_max=qmax,
            Q_B_reference=.1+.9*(qa0-qmin)/(qmax-qmin))
        coefficients.extend(dict(axis=axis, domain=c[2:], coefficient_full=float(a),
                                 p_on_Q_loading=float(b), quality_domain=float(v))
                            for c,a,b,v in zip(cols,coef,loading,q))
        qmodel = LinearRegression().fit(train[[axis]], train.loss_mean_13_domains)
        for dataset, test in bridge[bridge.loss_observed == True].groupby('dataset'):
            xp = test[cols].to_numpy()-p0
            y = test.loss_mean_13_domains.to_numpy()
            qa = test[axis].to_numpy()
            rp = xp-(qa-qa0)[:,None]*loading
            qb = np.clip(.1+.9*(qa-qmin)/(qmax-qmin),.1,1.)
            qb0 = frozen['axes'][axis]['Q_B_reference']
            dq = quality['coefficient']*(np.log(qb/qb0) if quality['form']=='scale_logQ' else qb-qb0)
            for name, pred in [('mean', np.full(len(test), model.intercept_)),
                               ('Q_only', qmodel.predict(test[[axis]])),
                               ('full_p', model.intercept_+xp@coef),
                               ('remaining_p_only', model.intercept_+rp@coef),
                               ('replace_Q_from_B', model.intercept_+dq+rp@coef)]:
                rows.append(dict(axis=axis, dataset=dataset, model=name, **score(y, pred),
                                 centered_rmse=float(np.sqrt(np.mean(((pred-pred.mean())-(y-y.mean()))**2))),
                                 spearman=float(spearmanr(y,pred).statistic) if np.std(pred)>1e-10 else None))
        a6 = bridge[bridge.dataset == 'A6_A7_test_1m'].set_index('index')
        a8 = bridge[bridge.dataset == 'A8_A9_test_60m'].set_index('index')
        ids = a6.index.intersection(a8.index)
        assert np.allclose(a6.loc[ids,cols], a8.loc[ids,cols])
        rank_rows.append(dict(axis=axis, matched_rows=len(ids),
                              spearman_A6_A8=float(spearmanr(a6.loc[ids,'loss_mean_13_domains'], a8.loc[ids,'loss_mean_13_domains']).statistic)))
    pd.DataFrame(rows).to_csv(OUT/'mixture_validation.csv', index=False)
    pd.DataFrame(rank_rows).to_csv(OUT/'mixture_transfer.csv', index=False)
    pd.DataFrame(coefficients).to_csv(OUT/'mixture_coefficients.csv', index=False)
    return frozen, bridge


def predict_scenario(frame, model, quality_axis='Q_A_topsis_0_1', lambda_p=1., lambda_q=1.):
    """B1-reference scenario, not a calibrated absolute A/B loss prediction.

    frame must contain N_params_B, D_tokens_B and all 17 p columns.
    lambda_p/q are assumption-based transport strengths, never fit to fake rows.
    """
    mix, qm = model['mixture'], model['quality']
    p = frame[mix['columns']].to_numpy(float)
    nd = frame[['N_params_B','D_tokens_B']].to_numpy(float)
    if not np.isfinite(p).all() or not np.isfinite(nd).all() or (nd <= 0).any():
        raise ValueError('Finite inputs and positive N,D required')
    if (p < 0).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-6):
        raise ValueError('Mixture must be nonnegative and sum to one')
    a = mix['axes'][quality_axis]
    qa = p@np.asarray(a['domain_quality'])
    qraw = .1+.9*(qa-a['Q_A_train_min'])/(a['Q_A_train_max']-a['Q_A_train_min'])
    qb = np.clip(qraw, .1, 1.)
    qref = a['Q_B_reference']
    dq = qm['coefficient']*(np.log(qb/qref) if qm['form']=='scale_logQ' else qb-qref)
    xp = p-np.asarray(mix['p_reference'])
    residual_p = xp-(qa-a['Q_A_reference'])[:,None]*np.asarray(a['p_on_Q_loading'])
    dp = residual_p@np.asarray(a['residual_loss_coefficients'])
    base = power([model['scale']['parameters'][k] for k in PARAM_NAMES], frame)
    out = frame.copy()
    out['quality_axis'] = quality_axis
    out['Q_A'] = qa
    out['Q_B_assumed'] = qb
    out['quality_map_clipped'] = (qraw < .1) | (qraw > 1.)
    out['scale_loss'] = base
    out['delta_Q'] = dq
    out['delta_p_remaining'] = dp
    out['lambda_Q_assumed'], out['lambda_p_assumed'] = lambda_q, lambda_p
    out['predicted_loss_scenario'] = base+lambda_q*dq+lambda_p*dp
    out['observed_joint_row'] = False
    out['status'] = 'CONDITIONAL_SCENARIO_NOT_JOINT_VALIDATION'
    for c in ['N_params_B','D_tokens_B']:
        lo, hi = model['scale']['support'][c]
        out[c+'_outside_B1_range'] = (out[c]<lo) | (out[c]>hi)
    return out


def verify_export(model, result):
    """Check reference normalization and exported prediction decomposition."""
    loaded = json.loads((OUT/'model_parameters.json').read_text(encoding='utf-8'))
    checks = []
    for axis in model['mixture']['axes']:
        ref = dict(zip(model['mixture']['columns'], model['mixture']['p_reference']))
        ref.update(N_params_B=1., D_tokens_B=100.)
        frame = pd.DataFrame([ref])
        baseline = predict_scenario(frame, loaded, axis)
        assert np.allclose(baseline[['delta_Q','delta_p_remaining']],0,atol=1e-12)
        larger = frame.copy()
        larger.N_params_B *= 2
        larger.D_tokens_B *= 2
        assert predict_scenario(larger,loaded,axis).predicted_loss_scenario.iloc[0] < baseline.predicted_loss_scenario.iloc[0]
        # Serialization must preserve the interface, not just parameter text.
        assert np.allclose(predict_scenario(frame,model,axis).predicted_loss_scenario,
                           baseline.predicted_loss_scenario)
        checks.append(dict(axis=axis, reference_centering=True, scale_monotonicity=True,
                           serialization_roundtrip=True))
    recon = result.scale_loss+result.lambda_Q_assumed*result.delta_Q+result.lambda_p_assumed*result.delta_p_remaining
    assert np.allclose(recon,result.predicted_loss_scenario)
    assert np.isfinite(result.predicted_loss_scenario).all()
    saved = pd.read_csv(OUT/'scenario_predictions.csv')
    assert len(saved)==len(result) and not saved.observed_joint_row.any()
    assert np.allclose(saved.predicted_loss_scenario, result.predicted_loss_scenario)
    (OUT/'verification.json').write_text(json.dumps(dict(checks=checks,
        exported_prediction_rows=len(saved), additive_decomposition=True,
        all_predictions_finite=True, generated_rows_never_marked_observed=True),indent=2),encoding='utf-8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b1 = pd.read_csv(RAW/'pythia_training_log_existing.csv')
    b6 = pd.read_csv(RAW/'supplementary_NQ_experiment.csv')
    b7 = pd.read_csv(RAW/'supplementary_NQ_experiment_expanded.csv')
    p, scales = scale_fit(b1)
    print('Scale OOF:', scales, flush=True)
    quality, quality_summary = quality_fit(b6, b7, p)
    print('Quality:', quality, flush=True)
    mixture, bridge = mixture_fit(quality)
    model = dict(status='CONDITIONAL_SCENARIO', scale=dict(parameters=dict(zip(PARAM_NAMES,p)),
        support={c:[float(b1[c].min()),float(b1[c].max())] for c in ['N_params_B','D_tokens_B']},
        units='N and D in billions; natural log; fit source B1'), quality=quality, mixture=mixture,
        assumptions=['Q map fitted on A4/A5 feature support only, clipped outside support',
                     'lambda_Q=1 and lambda_p=1 are transfer assumptions, not identified coefficients',
                     'Training-only regression residualization removes the linear p component explained by Q; no causal effect identified',
                     'B7 offset is not transferred; B1-reference absolute loss only',
                     'B1 near-formula fit is a property of supplied file, not proof of real-world scaling',
                     'TOPSIS REVIEW_BLOCKED and soft REVIEW statuses are inherited'])
    (OUT/'model_parameters.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
    # Ten training mixtures, B1-supported N,D grid; all 17 p columns retained.
    recipes = bridge[bridge.dataset=='A4_A5_train_1m'].sort_values('index').head(10)
    sizes = pd.DataFrame([(n,d) for n in sorted(b1.N_params_B.unique())
                          for d in b1.D_tokens_B.quantile([0,.25,.5,.75,1])],
                         columns=['N_params_B','D_tokens_B'])
    frame = recipes[['index']+mixture['columns']].rename(columns={'index':'A_recipe_index'}).merge(sizes,how='cross')
    variants = []
    for axis in mixture['axes']:
        for name,lq,lp in [('scale_only',0,0),('scale_Q',1,0),('scale_remaining_p',0,1),
                           ('combined',1,1),('combined_half_p',1,.5)]:
            result = predict_scenario(frame,model,axis,lp,lq)
            result['variant'] = name
            variants.append(result)
    result = pd.concat(variants,ignore_index=True)
    result.to_csv(OUT/'scenario_predictions.csv',index=False,encoding='utf-8-sig')
    verify_export(model, result)
    summary = result.groupby(['quality_axis','variant']).predicted_loss_scenario.agg(['size','min','mean','max'])
    summary.to_csv(OUT/'scenario_summary.csv',encoding='utf-8-sig')
    sources = [RAW/n for n in ['pythia_training_log_existing.csv','supplementary_NQ_experiment.csv',
                               'supplementary_NQ_experiment_expanded.csv','cerebras_training_log.csv',
                               'scaling_baseline.csv','published_scaling_data.csv']]
    sources += [BRIDGE/'q1_to_q2_quality_linkage.csv',BRIDGE/'q1_domain_quality_for_q2.csv']
    manifest = dict(raw_source_sha256={source_ref(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    excluded=['A12-A15','B8','B10'], output_scenarios=len(result),
                    note='No generated scenario is used for fitting. Raw source descriptions are not parameter constraints.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(quality_summary.to_string(index=False),flush=True)


if __name__ == '__main__':
    main()
