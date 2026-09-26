"""Frozen E3 conditional equal-loss analysis. No observed outcomes are loaded."""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from scipy.optimize import linprog, brentq
from q2_finalize_model import predict_scenario

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n',
                    encoding='utf-8', newline='\n')


def inverse(S, gain, A, alpha, match_improvement=False):
    """Return a finite positive inverse or explicit asymptotic status."""
    term = S-gain if match_improvement else S+gain
    if term <= 0:
        return np.nan, 'INFINITE_LIMIT_ONLY' if term == 0 else 'BELOW_ASYMPTOTIC_FLOOR'
    value = float(np.exp(-np.log(term/A)/alpha))
    return value, 'FINITE'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, default=ROOT/'configs/q2-e3-quality-parameter-substitution.json')
    ap.add_argument('--output-dir', type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    out = args.output_dir or ROOT/'experiments/runs'/cfg['run_id']
    out.mkdir(parents=True, exist_ok=True)
    inputs = [ROOT/cfg['model'], ROOT/cfg['bridge'], args.config.resolve(),
              Path(__file__).resolve(), ROOT/'scripts/q2_finalize_model.py']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    model = json.loads(inputs[0].read_text(encoding='utf-8'))
    mix = model['mixture']; cols = mix['columns']
    train = pd.read_csv(inputs[1], usecols=['dataset', 'index']+cols)
    train = train[train.dataset == 'A4_A5_train_1m'].reset_index(drop=True)
    P = train[cols].to_numpy(float); p0 = np.asarray(mix['p_reference'])
    n, k = P.shape
    assert (n, k) == (512, 17)
    assert np.allclose(P.mean(0), p0) and np.all(P >= 0) and np.allclose(P.sum(1), 1)
    A = model['scale']['parameters']['A']; alpha = model['scale']['parameters']['alpha']
    c = model['quality']['coefficient']
    assert c < 0 and model['quality']['form'] == 'scale_Q'
    nlo, nhi = model['scale']['support']['N_params_B']
    checks = []; files = []

    def check(name, actual, expected=0., tol=None):
        err = np.abs(np.asarray(actual)-np.asarray(expected))
        maximum = float(np.max(err, initial=0))
        tol = cfg['equality_atol'] if tol is None else tol
        ok = bool(np.isfinite(err).all() and maximum <= tol)
        checks.append(dict(check=name, comparisons=int(err.size), max_absolute_error=maximum,
                           tolerance=tol, passed=ok))
        assert ok, checks[-1]

    def save(name, rows):
        df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        df.to_csv(out/name, index=False, lineterminator='\n')
        files.append(name)
        return df

    def predict(points, axis, N=1., D=None, lq=1., lp=1.):
        f = pd.DataFrame(np.atleast_2d(points), columns=cols)
        f['N_params_B'] = N
        f['D_tokens_B'] = cfg['D_reference_B'] if D is None else D
        return predict_scenario(f, model, axis, lambda_q=lq, lambda_p=lp)

    def outcome(N, G):
        S = A*N**(-alpha)
        small, ss = inverse(S, G, A, alpha)
        large, ls = inverse(S, G, A, alpha, True)
        if G == 0:
            small = large = float(N)
        return dict(N_required_B=small, required_status=ss, N_required_ratio=small/N,
                    required_in_B1=bool(nlo <= small <= nhi),
                    N_scale_equivalent_B=large, scale_status=ls, N_scale_ratio=large/N,
                    scale_is_expansion=bool(G > cfg['sign_atol']),
                    scale_in_B1=bool(nlo <= large <= nhi),
                    quality_cost_ceiling_FLOPs=cfg['compute_coefficient_kappa']*
                    cfg['D_reference_B']*(N-small)*1e18,
                    quality_cost_ceiling_per_token=cfg['compute_coefficient_kappa']*(N-small)*1e9)

    supports = []; weights = []; duals = []; curves = []; capacities = []; targets = []; recipes = []
    uniform = np.full(n, 1/n)
    for axis, ax in mix['axes'].items():
        q = np.asarray(ax['domain_quality']); v = np.asarray(ax['p_on_Q_loading'])
        w = np.asarray(ax['residual_loss_coefficients'])
        qa0 = ax['Q_A_reference']; qb0 = ax['Q_B_reference']
        slope = .9/(ax['Q_A_train_max']-ax['Q_A_train_min'])
        check('q_dot_v_'+axis, q@v, 1.)
        check('sum_v_'+axis, v.sum())
        qa = P@q
        check('quality_reference_'+axis, p0@q, qa0)
        check('mapping_reference_'+axis, .1+slope*(qa0-ax['Q_A_train_min']), qb0)
        upper = ax['Q_A_train_max']-qa0
        ae = np.column_stack([np.vstack([P.T, np.ones(n)]), -np.r_[v, 0.]])
        be = np.r_[p0, 1.]
        lp = linprog(np.r_[np.zeros(n), -1.], A_eq=ae, b_eq=be,
                     bounds=[(0, None)]*n+[(0, upper)], method='highs',
                     options={'primal_feasibility_tolerance':cfg['lp_tolerance'],
                              'dual_feasibility_tolerance':cfg['lp_tolerance']})
        assert lp.success, lp.message
        a = lp.x[:-1]; tmax = float(lp.x[-1]); safe = cfg['hull_safety_fraction']*tmax
        y = lp.eqlin.marginals; up = float(lp.upper.marginals[-1])
        dual = float(be@y+upper*up)
        check('lp_primal_'+axis, ae@lp.x, be, cfg['witness_atol'])
        check('lp_dual_gap_'+axis, lp.fun, dual, cfg['witness_atol'])
        assert a.min() >= -cfg['lp_tolerance'] and tmax > 0 and up <= cfg['witness_atol']
        assert np.max(np.vstack([P.T, np.ones(n)]).T@y) <= cfg['witness_atol']
        assert -1+v@y[:k]-up >= -cfg['witness_atol']
        ws = (1-cfg['hull_safety_fraction'])*uniform+cfg['hull_safety_fraction']*a
        check('safe_witness_'+axis, ws@P, p0+safe*v, cfg['witness_atol'])
        supports.append(dict(axis=axis, Q_A_reference=qa0, Q_B_reference=qb0,
                             t_hull_max=tmax, t_safe=safe, delta_QB_safe=slope*safe,
                             delta_QB_formal=1-qb0, lp_objective=float(lp.fun),
                             dual_objective=dual, t_upper_price=up, observed_joint_support=False))
        for i in np.flatnonzero(a != 0):
            weights.append(dict(axis=axis, train_position=int(i), source_recipe_id=int(train['index'].iloc[i]),
                                weight=float(a[i])))
        duals.append(dict(axis=axis, **{f'y_{j}':float(y[j]) for j in range(k+1)}))
        tt = np.linspace(0, safe, cfg['path_points'])
        points = p0+tt[:, None]*v
        pred = predict(points, axis)
        check('fixed_residual_'+axis, pred.delta_p_remaining)
        check('path_quality_'+axis, pred.Q_A, qa0+tt)
        check('path_gain_'+axis, -pred.delta_Q, -c*slope*tt)
        # Feasible symmetric derivative check using an explicit convex witness.
        centered = qa-qa0; dw = centered/(centered@centered)
        check('derivative_witness_'+axis, P.T@dw, v, cfg['witness_atol'])
        h = min(safe*1e-4, .1*np.min(uniform[np.abs(dw)>0]/np.abs(dw[np.abs(dw)>0])))
        assert np.min(uniform+h*dw) >= 0 and np.min(uniform-h*dw) >= 0
        for lq, N in itertools.product(cfg['lambda_Q'], cfg['N_anchors_B']):
            S = A*N**(-alpha)
            gain = -c*lq*slope*tt
            rows = [outcome(N, float(g)) for g in gain]
            small = np.array([r['N_required_B'] for r in rows])
            base = float(predict(p0, axis, N=N, lq=lq).predicted_loss_scenario.iloc[0])
            check('equal_loss_path_'+axis+str((lq,N)),
                  predict(points, axis, N=small, lq=lq).predicted_loss_scenario, base)
            check('D_invariance_'+axis+str((lq,N)),
                  predict(points, axis, N=small, D=cfg['D_invariance_check_B'], lq=lq).predicted_loss_scenario,
                  float(predict(p0, axis, N=N, D=cfg['D_invariance_check_B'], lq=lq).predicted_loss_scenario.iloc[0]))
            roots = np.exp([brentq(lambda z: A*np.exp(-alpha*z)-g-S, np.log(N)-30,
                                  np.log(N)+30, xtol=cfg['root_xtol']) for g in gain])
            check('brent_relative_'+axis+str((lq,N)), roots/small, 1., 2e-10)
            fm = inverse(S, -c*lq*slope*(-h), A, alpha)[0]
            fp = inverse(S, -c*lq*slope*h, A, alpha)[0]
            derivative = c*lq*slope*N**(alpha+1)/(alpha*A)
            check('derivative_'+axis+str((lq,N)), (fp-fm)/(2*h), derivative,
                  max(2e-6, abs(derivative)*2e-6))
            assert np.max(np.diff(small)) <= cfg['equality_atol']
            for t, g, r in zip(tt, gain, rows):
                curves.append(dict(axis=axis, N0_B=N, D_B=cfg['D_reference_B'], lambda_Q=lq,
                                   t_QA=float(t), delta_QB=float(slope*t), gain=float(g),
                                   observed_joint_row=False, **r))
            for kind, delta in [('feasible_fixed_residual',slope*safe), ('formal_quality_coordinate',1-qb0)]:
                capacities.append(dict(axis=axis, N0_B=N, lambda_Q=lq, kind=kind,
                                       delta_QB=delta, gain=-c*lq*delta, **outcome(N,-c*lq*delta)))
            for mult in cfg['target_N_multipliers']:
                required = S*(1-mult**(-alpha))
                dq = required/(-c*lq) if lq else np.nan
                targets.append(dict(axis=axis,N0_B=N,lambda_Q=lq,target_multiplier=mult,
                                    target_N_B=N*mult,target_in_B1=bool(nlo<=N*mult<=nhi),
                                    required_gain=required,required_delta_QB=dq,required_t_QA=dq/slope,
                                    feasible_path=bool(lq and dq<=slope*safe),
                                    formal_coordinate=bool(lq and dq<=1-qb0),
                                    status='CONDITIONAL' if lq else 'NO_QUALITY_EFFECT'))
        nominal = predict(P, axis)
        for lq, lpres, N in itertools.product(cfg['lambda_Q'],cfg['lambda_p'],cfg['N_anchors_B']):
            gq = -lq*nominal.delta_Q.to_numpy()
            gp = -lpres*nominal.delta_p_remaining.to_numpy()
            gain = gq+gp; rows = [outcome(N,float(g)) for g in gain]
            small = np.array([r['N_required_B'] for r in rows]); mask = np.isfinite(small)
            base = float(predict(p0,axis,N=N,lq=lq,lp=lpres).predicted_loss_scenario.iloc[0])
            check('recipe_backsub_'+axis+str((lq,lpres,N)),
                  predict(P[mask],axis,N=small[mask],lq=lq,lp=lpres).predicted_loss_scenario,base)
            large = np.array([r['N_scale_equivalent_B'] for r in rows]); mask = np.isfinite(large)
            improved = predict(P,axis,N=N,lq=lq,lp=lpres).predicted_loss_scenario.to_numpy()
            check('scale_backsub_'+axis+str((lq,lpres,N)),
                  predict(np.repeat(p0[None,:],mask.sum(),axis=0),axis,N=large[mask],lq=lq,lp=lpres).predicted_loss_scenario,
                  improved[mask])
            for i,r in enumerate(rows):
                recipes.append(dict(axis=axis,source_recipe_id=int(train['index'].iloc[i]),
                                    N0_B=N,lambda_Q=lq,lambda_p=lpres,delta_QA=float(qa[i]-qa0),
                                    gain_quality=float(gq[i]),gain_residual=float(gp[i]),gain_total=float(gain[i]),
                                    quality_up_loss_not_improved=bool(qa[i]>qa0+cfg['sign_atol'] and gain[i]<=cfg['sign_atol']),
                                    observed_joint_row=False,**r))
    for g, expected in [(A,'INFINITE_LIMIT_ONLY'),(2*A,'BELOW_ASYMPTOTIC_FLOOR')]:
        assert inverse(A,g,A,alpha,True)[1] == expected
        assert inverse(A,-g,A,alpha)[1] == expected
    check('cost_D_ratio',cfg['D_reference_B']/cfg['D_invariance_check_B'],10.)
    save('quality_path_support.csv',supports); save('support_weights.csv',weights); save('support_duals.csv',duals)
    save('quality_path_curves.csv',curves); save('quality_capacity.csv',capacities)
    target = save('expansion_targets.csv',targets); rec = save('recipe_substitution.csv',recipes)
    summary = rec.groupby(['axis','N0_B','lambda_Q','lambda_p']).agg(
        recipe_count=('source_recipe_id','size'),quality_up_loss_not_improved=('quality_up_loss_not_improved','sum'),
        positive_gain=('gain_total',lambda x:int((x>cfg['sign_atol']).sum())),
        required_in_B1=('required_in_B1','sum'),scale_in_B1=('scale_in_B1','sum')).reset_index()
    save('recipe_summary.csv',summary); save('verification_checks.csv',checks)
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    metrics = dict(status='RUN_COMPLETE_CONDITIONAL',path_rows=len(curves),recipe_rows=len(rec),
                   target_rows=len(target),capacity_rows=len(capacities),checks=len(checks),
                   numerical_comparisons=sum(x['comparisons'] for x in checks),
                   feasible_target_rows=int(target.feasible_path.sum()),
                   formal_target_rows=int(target.formal_coordinate.sum()),
                   observed_outcomes_loaded=False,new_parameters_fit=False,inputs_unchanged=True,
                   support=supports,
                   nominal_recipe_summary=summary[(summary.N0_B==1)&(summary.lambda_Q==1)&(summary.lambda_p==1)].to_dict('records'))
    dump(out/'metrics.json',metrics)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dump(out/'manifest.json',dict(task_id='T-Q2-E3',run_id=cfg['run_id'],git_commit=commit,
         created_at=datetime.now(timezone.utc).isoformat(),inputs=hashes,
         outputs={f:sha(out/f) for f in files},metrics_sha256=sha(out/'metrics.json'),
         inference_status='CONDITIONAL_SCENARIO_NOT_JOINT_VALIDATION',cost_status='ASSUMPTION_ONLY'))
    print(json.dumps(metrics,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
