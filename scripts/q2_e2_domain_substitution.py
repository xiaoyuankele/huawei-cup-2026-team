"""E2: frozen conditional domain substitution and interaction diagnostics.

Only A4 recipe features are read. No observed Loss, fitting or empirical
complementarity claim. Every generated row is a mathematical scenario.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import linprog

from q2_finalize_model import predict_scenario

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/q2-e2-domain-substitution.json')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    out = args.output_dir or ROOT/'experiments/runs'/cfg['run_id']
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    inputs = [ROOT/cfg['model'], ROOT/cfg['bridge'], args.config.resolve(), Path(__file__).resolve(), ROOT/'scripts/q2_finalize_model.py']
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    model = json.loads(inputs[0].read_text(encoding='utf-8'))
    assert model['quality']['form'] == 'scale_Q'
    mix = model['mixture']; cols = mix['columns']; axes = list(mix['axes'])
    # usecols intentionally excludes all observed outcome columns.
    bridge = pd.read_csv(inputs[1], usecols=['dataset', 'index']+cols)
    train = bridge.loc[bridge.dataset == 'A4_A5_train_1m'].reset_index(drop=True)
    p = train[cols].to_numpy(float); ids = train['index'].to_numpy()
    p0 = np.asarray(mix['p_reference']); n, k = p.shape
    assert (n, k) == (512, 17) and len(np.unique(ids)) == n
    assert np.isfinite(p).all() and (p >= 0).all() and np.allclose(p.sum(1), 1)
    assert np.allclose(p.mean(0), p0)
    nr, dr = cfg['reference_N_B'], cfg['reference_D_B']
    checks = []; outputs = []

    def check(name, actual, expected=0., tol=None):
        tol = cfg['prediction_atol'] if tol is None else tol
        err = np.abs(np.asarray(actual)-np.asarray(expected))
        maximum = float(np.max(err, initial=0.))
        ok = bool(np.isfinite(err).all() and maximum <= tol)
        checks.append(dict(check=name, comparisons=int(err.size), max_absolute_error=maximum, tolerance=tol, passed=ok))
        assert ok, checks[-1]

    def save(name, frame):
        frame.to_csv(out/name, index=False, encoding='utf-8', lineterminator='\n')
        outputs.append(name)

    def predict(points, axis, lq=1., lp=1.):
        frame = pd.DataFrame(np.atleast_2d(points), columns=cols)
        frame['N_params_B'] = nr; frame['D_tokens_B'] = dr
        return predict_scenario(frame, model, axis, lambda_q=lq, lambda_p=lp)

    gradients = {}
    for axis in axes:
        a = mix['axes'][axis]; q = np.asarray(a['domain_quality'])
        v = np.asarray(a['p_on_Q_loading']); w = np.asarray(a['residual_loss_coefficients'])
        check('train_quality_min_'+axis, (p@q).min(), a['Q_A_train_min'])
        check('train_quality_max_'+axis, (p@q).max(), a['Q_A_train_max'])
        gq = model['quality']['coefficient']*.9/(a['Q_A_train_max']-a['Q_A_train_min'])*q
        gp = w-(w@v)*q
        gradients[axis] = (gq, gp)

    # Exact ray/hull intersection LP. Dual certificate bounds the optimum.
    uniform = np.full(n, 1/n); eye = np.eye(k)
    ray_rows = []; weight_rows = []; dual_rows = []; endpoints = {}; safe_weights = {}
    for i, j in itertools.permutations(range(k), 2):
        direction = eye[i]-eye[j]; rid = f'{i:02d}_from_{j:02d}'
        ae = np.column_stack([np.vstack([p.T, np.ones(n)]), -np.r_[direction, 0.]])
        be = np.r_[p0, 1.]; cost = np.r_[np.zeros(n), -1.]
        result = linprog(cost, A_eq=ae, b_eq=be, bounds=[(0, None)]*n+[(0, float(p0[j]))],
                         method='highs', options={'primal_feasibility_tolerance':cfg['lp_primal_tolerance'],
                                                   'dual_feasibility_tolerance':cfg['lp_dual_tolerance']})
        if not result.success:
            dump(out/'failure.json', dict(direction_id=rid, solver_status=int(result.status), message=result.message))
            raise RuntimeError('LP failed; failure retained: '+rid)
        weights = result.x[:-1]; limit = float(result.x[-1]); y = result.eqlin.marginals
        upper_price = float(result.upper.marginals[-1])
        dual = float(be@y+p0[j]*upper_price)
        check('LP_primal_'+rid, ae@result.x, be, cfg['witness_atol'])
        check('LP_dual_gap_'+rid, result.fun, dual, cfg['witness_atol'])
        assert weights.min() >= -cfg['lp_primal_tolerance'] and limit > 0
        assert np.max(np.vstack([p.T, np.ones(n)]).T@y) <= cfg['witness_atol']
        assert -1.+direction@y[:k]-upper_price >= -cfg['witness_atol']
        assert upper_price <= cfg['witness_atol']
        safe = cfg['hull_safety_fraction']*limit
        ws = (1-cfg['hull_safety_fraction'])*uniform+cfg['hull_safety_fraction']*weights
        assert ws.min() >= 0
        endpoint = p0+safe*direction
        check('LP_safe_witness_'+rid, ws@p, endpoint, cfg['witness_atol'])
        assert endpoint.min() >= 0
        endpoints[rid] = endpoint; safe_weights[rid] = ws
        ray_rows.append(dict(direction_id=rid,to_index=i,from_index=j,to_domain=cols[i][2:],from_domain=cols[j][2:],
                             simplex_limit=float(p0[j]),hull_limit=limit,safe_hull_limit=safe,safe_hull_limit_pp=100*safe,
                             lp_status=int(result.status),lp_objective=float(result.fun),lp_dual_objective=dual,
                             lp_duality_gap=abs(float(result.fun)-dual),delta_upper_price=upper_price,
                             safe_min_weight=float(ws.min()),observed_joint_support=False))
        for pos in np.flatnonzero(weights != 0):
            weight_rows.append(dict(direction_id=rid,train_position=int(pos),source_recipe_id=int(ids[pos]),weight=float(weights[pos])))
        dual_rows.append(dict(direction_id=rid,**{f'y_{h}':float(y[h]) for h in range(k+1)}))
    rays = pd.DataFrame(ray_rows)
    save('substitution_support.csv',rays); save('support_weights.csv',pd.DataFrame(weight_rows)); save('support_duals.csv',pd.DataFrame(dual_rows))
    print('LP support and dual certificates complete: 272 directions',flush=True)

    finite_rows = []
    for ray in ray_rows:
        i,j,rid = ray['to_index'],ray['from_index'],ray['direction_id']; d = eye[i]-eye[j]
        steps = [('fixed',v) for v in cfg['absolute_swap_fractions']]
        steps += [('fraction_of_safe_limit_'+str(t),ray['safe_hull_limit']*t) for t in cfg['supported_limit_fractions']]
        for axis in axes:
            gq,gp = gradients[axis]; base = predict(p0,axis).iloc[0]
            for kind,delta in steps:
                supported = delta <= ray['safe_hull_limit']*(1+1e-12)
                row = dict(axis=axis,direction_id=rid,to_index=i,from_index=j,to_domain=ray['to_domain'],from_domain=ray['from_domain'],
                           step_kind=kind,swap_fraction=delta,swap_pp=100*delta,simplex_feasible=bool(delta<=p0[j]),
                           training_hull_supported=bool(supported),slope_quality=float(gq@d),slope_residual=float(gp@d),
                           observed_joint_row=False,delta_loss=np.nan,delta_quality=np.nan,delta_residual=np.nan,
                           min_convex_weight=np.nan,status='UNSUPPORTED_AT_REQUESTED_STEP')
                if supported:
                    t=delta/ray['safe_hull_limit']; wnew=(1-t)*uniform+t*safe_weights[rid]
                    pp=p0+delta*d
                    check('finite_hull_'+rid,wnew@p,pp,cfg['witness_atol'])
                    assert wnew.min()>=0
                    pred=predict(pp,axis).iloc[0]
                    dl=float(pred.predicted_loss_scenario-base.predicted_loss_scenario)
                    dq=float(pred.delta_Q-base.delta_Q); dp=float(pred.delta_p_remaining-base.delta_p_remaining)
                    check('finite_decomposition_'+axis,dl,dq+dp)
                    check('finite_gradient_'+axis,dl,delta*((gq+gp)@d))
                    row.update(delta_loss=dl,delta_quality=dq,delta_residual=dp,min_convex_weight=float(wnew.min()),status='SUPPORTED_CONDITIONAL_SCENARIO')
                finite_rows.append(row)
    finite=pd.DataFrame(finite_rows);save('finite_substitution.csv',finite)

    sensitive=[]
    for axis,lq,lp in itertools.product(axes,cfg['lambda_Q'],cfg['lambda_p']):
        gq,gp=gradients[axis];g=lq*gq+lp*gp
        for ray in ray_rows:
            i,j=ray['to_index'],ray['from_index']; slope=float(g[i]-g[j])
            sensitive.append(dict(axis=axis,lambda_Q=lq,lambda_p=lp,direction_id=ray['direction_id'],to_index=i,from_index=j,
                                  slope_per_fraction=slope,sign=int(np.sign(slope)) if abs(slope)>cfg['sign_atol'] else 0,
                                  all_effects_disabled=bool(lq==lp==0)))
    sens=pd.DataFrame(sensitive);save('assumption_sensitivity.csv',sens)
    agreements=[]
    for i,j in itertools.combinations(range(k),2):
        sub=sens[(sens.to_index==i)&(sens.from_index==j)&~sens.all_effects_disabled]
        signs=set(sub.sign);nonzero=signs-{0}; nominal=sub[(sub.lambda_Q==1)&(sub.lambda_p==1)].sort_values('axis')
        agreements.append(dict(to_index=i,from_index=j,to_domain=cols[i][2:],from_domain=cols[j][2:],
                               active_scenarios=len(sub),sign_flips=len(nonzero)>1,neutral_present=0 in signs,
                               robust_nonzero_direction=len(signs)==1 and 0 not in signs,
                               nominal_axes_agree=nominal.sign.nunique()==1,
                               min_slope=float(sub.slope_per_fraction.min()),max_slope=float(sub.slope_per_fraction.max())))
    agreement=pd.DataFrame(agreements);save('direction_stability.csv',agreement)

    # Reusable dense 512 x 17 coefficient witness basis; no observed labels.
    centered=p-p0;basis=np.linalg.pinv(centered.T,rcond=1e-12);basis-=basis.mean(axis=0)
    bf=pd.DataFrame(basis,columns=[f'coef_{i}' for i in range(k)])
    bf.insert(0,'source_recipe_id',ids);bf.insert(0,'train_position',np.arange(n))
    save('interaction_witness_basis.csv',bf)
    designs=[];points=[[],[],[],[]]
    for donor in range(k):
        for i,j in itertools.combinations([x for x in range(k) if x!=donor],2):
            d1=eye[i]-eye[donor];d2=eye[j]-eye[donor]
            b1=basis[:,i]-basis[:,donor];b2=basis[:,j]-basis[:,donor]
            denom=abs(b1)+abs(b2);mask=denom>1e-14
            h=min(cfg['interaction_max_step'],cfg['interaction_witness_safety']*float(np.min(uniform[mask]/denom[mask])))
            ps=[p0,p0+h*d1,p0+h*d2,p0+h*(d1+d2)]
            ws=[uniform,uniform+h*b1,uniform+h*b2,uniform+h*(b1+b2)]
            check('four_corner_witness',np.asarray(ws)@p,np.asarray(ps),cfg['witness_atol'])
            assert np.min(ws)>=0 and np.min(ps)>=0
            designs.append(dict(donor_index=donor,to1_index=i,to2_index=j,step=h,minimum_corner_weight=float(np.min(ws))))
            for container,point in zip(points,ps):container.append(point)
    interaction=[]
    for axis in axes:
        pred=[predict(np.asarray(ps),axis) for ps in points]
        losses=[x.predicted_loss_scenario.to_numpy() for x in pred]
        gap=losses[3]-losses[1]-losses[2]+losses[0]
        check('interior_four_corner_'+axis,gap,0,cfg['interaction_zero_atol'])
        for f in pred: assert not f.quality_map_clipped.any()
        for t,design in enumerate(designs):
            interaction.append(dict(axis=axis,**design,loss00=float(losses[0][t]),loss10=float(losses[1][t]),loss01=float(losses[2][t]),loss11=float(losses[3][t]),
                                    interaction_loss=float(gap[t]),complementarity_benefit=-float(gap[t]),all_corners_training_hull_supported=True,
                                    is_empirical_complementarity_evidence=False))
    interior=pd.DataFrame(interaction);save('interior_interactions.csv',interior)

    # All pure-vertex stress designs: outside-training baselines must be explicit.
    stress=[];stresspoints=[[],[],[],[]];stressdesign=[]
    for design in designs:
        donor,i,j=design['donor_index'],design['to1_index'],design['to2_index']
        for h in cfg['stress_swap_fractions']:
            ps=[eye[donor],eye[donor]+h*(eye[i]-eye[donor]),eye[donor]+h*(eye[j]-eye[donor]),eye[donor]+h*(eye[i]+eye[j]-2*eye[donor])]
            assert np.min(ps)>=0
            outside=bool(p[:,donor].max()<1-cfg['witness_atol'])
            stressdesign.append(dict(donor_index=donor,to1_index=i,to2_index=j,step=h,pure_baseline_outside_training_hull=outside,
                                     baseline_training_domain_max=float(p[:,donor].max())))
            for container,point in zip(stresspoints,ps):container.append(point)
    for axis in axes:
        pred=[predict(np.asarray(ps),axis) for ps in stresspoints]
        losses=[x.predicted_loss_scenario.to_numpy() for x in pred]
        qs=[x.Q_B_assumed.to_numpy() for x in pred]
        residual=[x.delta_p_remaining.to_numpy() for x in pred]
        gap=losses[3]-losses[1]-losses[2]+losses[0]
        clip=model['quality']['coefficient']*(qs[3]-qs[1]-qs[2]+qs[0])
        check('stress_clip_explains_gap_'+axis,gap,clip)
        check('stress_residual_interaction_'+axis,residual[3]-residual[1]-residual[2]+residual[0],0)
        anyclip=np.logical_or.reduce([x.quality_map_clipped.to_numpy() for x in pred])
        for t,design in enumerate(stressdesign):
            stress.append(dict(axis=axis,**design,any_corner_clipped=bool(anyclip[t]),interaction_loss=float(gap[t]),
                               clip_only_interaction=float(clip[t]),nonzero_interaction=bool(abs(gap[t])>cfg['interaction_zero_atol']),
                               observed_joint_row=False,is_empirical_complementarity_evidence=False))
    stress=pd.DataFrame(stress);save('clipping_stress_interactions.csv',stress)
    save('verification_checks.csv',pd.DataFrame(checks))
    fixed=finite[(finite.axis==axes[0])&(finite.step_kind=='fixed')]
    metrics=dict(status='CONDITIONAL_ANALYSIS_COMPLETE_REVIEW_BLOCKED',directed_swaps=len(rays),unordered_domain_pairs=len(agreement),
                 reference_N_B=nr,reference_D_B=dr,training_recipes=n,quality_axes=len(axes),
                 safe_support_pp_min=float(rays.safe_hull_limit_pp.min()),safe_support_pp_median=float(rays.safe_hull_limit_pp.median()),safe_support_pp_max=float(rays.safe_hull_limit_pp.max()),
                 supported_directed_counts_by_swap_pp={str(float(v)):int(g.training_hull_supported.sum()) for v,g in fixed.groupby('swap_pp')},
                 nominal_axis_disagreements=int((~agreement.nominal_axes_agree).sum()),active_assumption_sign_flips=int(agreement.sign_flips.sum()),
                 active_assumption_robust_pairs=int(agreement.robust_nonzero_direction.sum()),
                 interior_four_corner_rows=len(interior),interior_max_abs_interaction=float(interior.interaction_loss.abs().max()),
                 stress_rows=len(stress),stress_nonzero_rows=int(stress.nonzero_interaction.sum()),stress_max_abs_interaction=float(stress.interaction_loss.abs().max()),
                 stress_all_baselines_outside_training_hull=bool(stress.pure_baseline_outside_training_hull.all()),
                 max_clip_explanation_error=float((stress.interaction_loss-stress.clip_only_interaction).abs().max()),
                 check_groups=len(checks),scalar_checks=sum(x['comparisons'] for x in checks),
                 new_observed_experiments=0,new_fitted_parameters=0,empirical_complementarity_identified=False)
    dump(out/'metrics.json',metrics)
    after={p.relative_to(ROOT).as_posix():sha(p) for p in inputs};assert before==after
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dump(out/'manifest.json',dict(run_id=cfg['run_id'],task_id=cfg['task_id'],prompt_run_id='PR-Q2-E2-20260925',
         status='REVIEW_BLOCKED',execution_status='RUN_COMPLETE',git_commit=commit,git_commit_role='code commit at execution',started_at=started,
         completed_at=datetime.now(timezone.utc).isoformat(),input_sha256=before,output_csv_sha256={name:sha(out/name) for name in outputs},
         metrics_sha256=sha(out/'metrics.json'),config=cfg,seed=None,deterministic=True,
         environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__),
         training_filter='A4_A5_train_1m',read_columns=['dataset','index']+cols,observed_outcome_columns_read=False,
         evidence='Conditional frozen-model scenarios; A-recipe hull is not joint A-B observation support',
         command='python scripts/q2_e2_domain_substitution.py',peer_decision='PENDING',integrator_decision='PENDING'))
    dump(out/'input_unchanged.json',dict(passed=before==after,input_sha256=after))
    print(json.dumps(metrics,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    main()
