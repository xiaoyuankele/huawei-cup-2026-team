"""E1: analytic sensitivities of frozen Q2 v1, checked against its predictor.

No fitting or raw attachment access. Generated rows are conditional scenarios,
not observations; finite differences verify implementation, not external validity.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy
import sklearn

from q2_finalize_model import predict_scenario
from q2_research_paths import REPO


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def scale_values(n, d, parameters):
    e, a, b, alpha, beta = [parameters[k] for k in ['E', 'A', 'B', 'alpha', 'beta']]
    n, d = np.asarray(n), np.asarray(d)
    nt, dt = a*n**(-alpha), b*d**(-beta)
    loss = e+nt+dt
    dn, dd = -alpha*nt/n, -beta*dt/d
    return dict(N_params_B=n, D_tokens_B=d, predicted_loss=loss, N_term=nt, D_term=dt,
                dL_dN_B=dn, dL_dD_B=dd, N_marginal_benefit=-dn, D_marginal_benefit=-dd,
                d2L_dN_B2=alpha*(alpha+1)*nt/n**2, d2L_dD_B2=beta*(beta+1)*dt/d**2,
                elasticity_N=n*dn/loss, elasticity_D=d*dd/loss,
                dL_dN_individual=dn/1e9, dL_dD_individual=dd/1e9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=REPO/'configs/q2-e1-marginal-elasticity.json')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    out = args.output_dir or REPO/'experiments/runs'/cfg['run_id']
    out.mkdir(parents=True, exist_ok=True)
    inputs = [REPO/cfg[k] for k in ['model','bridge','scale_folds']]
    inputs += [args.config.resolve(), Path(__file__).resolve(), REPO/'scripts/q2_finalize_model.py']
    before = {p.relative_to(REPO).as_posix():fingerprint(p) for p in inputs}
    model = json.loads((REPO/cfg['model']).read_text(encoding='utf-8'))
    assert model['quality']['form']=='scale_Q', 'This E1 derivation requires frozen linear quality v1.'
    bridge = pd.read_csv(REPO/cfg['bridge'])
    train = bridge[bridge.dataset=='A4_A5_train_1m'].copy()
    mix = model['mixture']; cols = mix['columns']; p0 = np.asarray(mix['p_reference'])
    ptrain = train[cols].to_numpy(float)
    assert len(train)==512 and len(cols)==17
    assert np.allclose(ptrain.sum(axis=1),1) and np.all(ptrain>=0)
    assert np.allclose(ptrain.mean(axis=0),p0)
    axes = list(mix['axes']); primary = axes[0]
    par = model['scale']['parameters']; support = model['scale']['support']
    nr, dr = cfg['reference_N_B'], cfg['reference_D_B']
    c = model['quality']['coefficient']
    checks = []

    def check(name, actual, expected, rtol=None, atol=None):
        actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
        assert np.isfinite(actual).all() and np.isfinite(expected).all(), name
        rtol = cfg['first_derivative_rtol'] if rtol is None else rtol
        atol = cfg['first_derivative_atol'] if atol is None else atol
        error = np.abs(actual-expected)
        ratio = error/(atol+rtol*np.abs(expected))
        passed = bool(np.all(ratio<=1))
        checks.append(dict(check=name, comparisons=int(error.size), passed=passed,
                           max_absolute_error=float(error.max(initial=0)), max_tolerance_fraction=float(ratio.max(initial=0))))
        assert passed, checks[-1]

    def predict(n, d, p=p0, axis=primary, lq=1., lp=1.):
        p = np.atleast_2d(p)
        count = max(len(p), np.size(n), np.size(d))
        frame = pd.DataFrame(np.broadcast_to(p,(count,len(cols))),columns=cols)
        frame['N_params_B']=np.broadcast_to(n,count)
        frame['D_tokens_B']=np.broadcast_to(d,count)
        return predict_scenario(frame,model,axis,lambda_q=lq,lambda_p=lp)

    def save(name, frame):
        frame.to_csv(out/name,index=False,encoding='utf-8',lineterminator='\n')

    # Scale grid spans only the marginal bounding box; no empirical joint support claim.
    ns = np.geomspace(*support['N_params_B'],cfg['grid_points_per_dimension'])
    ds = np.geomspace(*support['D_tokens_B'],cfg['grid_points_per_dimension'])
    n,d = np.meshgrid(ns,ds,indexing='ij');n,d=n.ravel(),d.ravel()
    grid = pd.DataFrame(scale_values(n,d,par))
    check('scale_reference_prediction',predict(n,d).predicted_loss_scenario,grid.predicted_loss)
    base = predict(n,d).predicted_loss_scenario.to_numpy()
    for step in cfg['finite_difference_relative_steps']:
        for variable,values in [('N',n),('D',d)]:
            h=values*step
            plus=predict(n+h if variable=='N' else n,d+h if variable=='D' else d).predicted_loss_scenario.to_numpy()
            minus=predict(n-h if variable=='N' else n,d-h if variable=='D' else d).predicted_loss_scenario.to_numpy()
            first=(plus-minus)/(2*h); second=(plus-2*base+minus)/h**2
            check(f'{variable}_first_relative_step_{step}',first,grid[f'dL_d{variable}_B'])
            check(f'{variable}_curvature_relative_step_{step}',second,grid[f'd2L_d{variable}_B2'],cfg['curvature_rtol'],cfg['curvature_atol'])
            if step==cfg['finite_difference_relative_steps'][0]:
                grid[f'fd_dL_d{variable}_B']=first
                grid[f'fd_d2L_d{variable}_B2']=second
    assert (grid[['N_marginal_benefit','D_marginal_benefit','d2L_dN_B2','d2L_dD_B2']]>0).all().all()
    check('N_elasticity_unit_invariance',n*1e9*grid.dL_dN_individual/base,grid.elasticity_N)
    check('D_elasticity_unit_invariance',d*1e9*grid.dL_dD_individual/base,grid.elasticity_D)
    # Curvature and reduction ratios are analytic properties of the frozen equation.
    for variable,exponent in [('N',par['alpha']),('D',par['beta'])]:
        doubled=scale_values(2*n if variable=='N' else n,2*d if variable=='D' else d,par)
        check(variable+'_doubling_marginal_ratio',doubled[f'{variable}_marginal_benefit']/grid[f'{variable}_marginal_benefit'],2**(-exponent-1))
    save('scale_grid.csv',grid)
    an,ad=np.array(list(itertools.product(cfg['anchor_N_B'],cfg['anchor_D_B']))).T
    anchors=pd.DataFrame(scale_values(an,ad,par));save('scale_anchors.csv',anchors)
    curves=[]
    for fixed in cfg['anchor_D_B']:
        f=pd.DataFrame(scale_values(ns,np.full(len(ns),fixed),par));f['varying']='N';curves.append(f)
    for fixed in cfg['anchor_N_B']:
        f=pd.DataFrame(scale_values(np.full(len(ds),fixed),ds,par));f['varying']='D';curves.append(f)
    save('scale_curves.csv',pd.concat(curves,ignore_index=True))
    fold_rows=[]
    for row in pd.read_csv(REPO/cfg['scale_folds']).to_dict('records'):
        f=pd.DataFrame(scale_values(an,ad,row));f['fit']=row['fold'];fold_rows.append(f)
    folds=pd.concat(fold_rows,ignore_index=True);save('scale_fold_sensitivity.csv',folds)

    # Formal QA partial at fixed residual: explicitly not an independent data intervention.
    formal=[];path_checks=[]
    uniform=np.full(len(train),1/len(train)); centered=ptrain-p0
    assert np.linalg.matrix_rank(centered)==len(cols)-1
    for axis in axes:
        a=mix['axes'][axis];q=np.asarray(a['domain_quality']);v=np.asarray(a['p_on_Q_loading'])
        w=np.asarray(a['residual_loss_coefficients']);lo,hi=a['Q_A_train_min'],a['Q_A_train_max'];span=hi-lo
        map_slope=.9/span
        positions=cfg['quality_normalized_positions']
        for lq in cfg['lambda_Q_sensitivity']:
            for t in np.linspace(positions['start'],positions['stop'],positions['count']):
                qa=lo+span*t;z=float(np.clip(.1+.9*t,.1,1))
                lower=bool(np.isclose(t,0,atol=1e-10));upper=bool(np.isclose(t,1,atol=1e-10));kink=lower or upper
                interior=0<t<1 and not kink
                slope=c*lq*map_slope
                left=0. if lower else slope if upper or interior else 0.
                right=0. if upper else slope if lower or interior else 0.
                derivative=(np.nan if kink and lq!=0 else slope if interior else 0.)
                def formal_loss(value):
                    qb=np.clip(.1+.9*(value-lo)/span,.1,1.)
                    return float(scale_values(nr,dr,par)['predicted_loss']+c*lq*(qb-a['Q_B_reference']))
                h=span*1e-5;loss=formal_loss(qa)
                fdleft=(loss-formal_loss(qa-h))/h;fdright=(formal_loss(qa+h)-loss)/h
                check('quality_one_sided_'+axis,[fdleft,fdright],[left,right])
                if np.isfinite(derivative):check('quality_regular_'+axis,(formal_loss(qa+h)-formal_loss(qa-h))/(2*h),derivative)
                formal.append(dict(axis=axis,lambda_Q=lq,normalized_Q_position=float(t),Q_A=float(qa),Q_B_assumed=z,
                    mapping_region='lower_kink' if lower else 'upper_kink' if upper else 'interior' if interior else 'clipped',
                    QA_in_domain_score_hull=bool(q.min()<=qa<=q.max()),independent_Q_intervention_observed=False,
                    predicted_loss_fixed_residual=loss,dL_dQA=derivative,left_dL_dQA=left,right_dL_dQA=right,
                    fd_left=fdleft,fd_right=fdright,
                    elasticity_QA_defined=bool(qa>0 and np.isfinite(derivative) and loss>0),
                    elasticity_QA=qa*derivative/loss if qa>0 and loss>0 else np.nan,
                    formal_dL_dQB=c*lq,formal_elasticity_QB=z*c*lq/loss))
        # The local fixed-residual QA path has an explicit convex-combination witness.
        qc=ptrain@q-a['Q_A_reference'];dw=qc/(qc@qc)
        check('Q_loading_path_'+axis,ptrain.T@dw,v)
        h=min(span*1e-5,cfg['convex_witness_safety_fraction']*np.min(uniform[np.abs(dw)>1e-14]/np.abs(dw[np.abs(dw)>1e-14])))
        pm,pp=p0-h*v,p0+h*v
        check('Q_path_convex_minus_'+axis,(uniform-h*dw)@ptrain,pm)
        check('Q_path_convex_plus_'+axis,(uniform+h*dw)@ptrain,pp)
        assert (uniform-h*dw>=0).all() and (uniform+h*dw>=0).all()
        fdm=predict(nr,dr,pm,axis).predicted_loss_scenario.iloc[0]
        fdp=predict(nr,dr,pp,axis).predicted_loss_scenario.iloc[0]
        analytic=c*map_slope
        check('Q_fixed_residual_predictor_'+axis,(fdp-fdm)/(2*h),analytic)
        residual_plus=pp-p0-(pp@q-a['Q_A_reference'])*v
        check('Q_path_residual_zero_'+axis,residual_plus,np.zeros(len(cols)))
        path_checks.append(dict(axis=axis,QA_step=h,analytic=analytic,finite_difference=(fdp-fdm)/(2*h),
                               min_convex_weight=float(min((uniform-h*dw).min(),(uniform+h*dw).min())),
                               local_path_in_A4_training_convex_hull=True))
    formal=pd.DataFrame(formal);save('quality_piecewise.csv',formal);save('quality_feasible_path_checks.csv',pd.DataFrame(path_checks))

    # All directed simplex moves; endpoints remain in the A4 convex hull by witness.
    directions=[]
    for i,j in itertools.permutations(range(len(cols)),2):
        direction=np.eye(len(cols))[i]-np.eye(len(cols))[j]
        dw=np.linalg.lstsq(centered.T,direction,rcond=1e-12)[0];dw-=dw.mean()
        check('simplex_direction_reconstruction',ptrain.T@dw,direction)
        positive=np.abs(dw)>1e-14
        witness_limit=np.min(uniform[positive]/np.abs(dw[positive]))
        h=min(cfg['mixture_max_step'],cfg['convex_witness_safety_fraction']*witness_limit)
        wm,wp=uniform-h*dw,uniform+h*dw
        assert (wm>=0).all() and (wp>=0).all()
        pm,pp=p0-h*direction,p0+h*direction
        check('simplex_convex_minus',wm@ptrain,pm);check('simplex_convex_plus',wp@ptrain,pp)
        for axis in axes:
            a=mix['axes'][axis];q=np.asarray(a['domain_quality']);v=np.asarray(a['p_on_Q_loading']);w=np.asarray(a['residual_loss_coefficients'])
            assert a['Q_A_train_min']<pm@q<a['Q_A_train_max'] and a['Q_A_train_min']<pp@q<a['Q_A_train_max']
            gradient=c*.9/(a['Q_A_train_max']-a['Q_A_train_min'])*q+w-(w@v)*q
            derivative=float(gradient@direction)
            plus=predict(nr,dr,pp,axis).predicted_loss_scenario.iloc[0]
            minus=predict(nr,dr,pm,axis).predicted_loss_scenario.iloc[0]
            fd=(plus-minus)/(2*h);check('simplex_predictor_'+axis,fd,derivative)
            lref=float(scale_values(nr,dr,par)['predicted_loss'])
            elasticity=derivative/lref/(1/p0[i]+1/p0[j])
            # Log-ratio elasticity is local with the pair sum and other proportions fixed.
            # Smaller step avoids relative truncation near rare components.
            he=h*.01
            ep=predict(nr,dr,p0+he*direction,axis).predicted_loss_scenario.iloc[0]
            em=predict(nr,dr,p0-he*direction,axis).predicted_loss_scenario.iloc[0]
            lr=np.log((p0[i]+he)/(p0[j]-he))-np.log((p0[i]-he)/(p0[j]+he))
            check('pair_logratio_elasticity_'+axis,(np.log(ep)-np.log(em))/lr,elasticity)
            directions.append(dict(axis=axis,to_domain=cols[i][2:],from_domain=cols[j][2:],to_index=i,from_index=j,
                derivative_per_fraction=derivative,loss_change_per_1pp_linearization=derivative*.01,
                pair_logratio_elasticity=elasticity,finite_difference=fd,finite_step=h,
                finite_delta_loss=plus-lref,min_convex_weight=float(min(wm.min(),wp.min())),
                witness_reconstruction_max_error=float(max(abs(wm@ptrain-pm).max(),abs(wp@ptrain-pp).max())),
                finite_endpoints_in_training_convex_hull=True,
                one_percentage_point_support_verified=False))
    directions=pd.DataFrame(directions);save('simplex_directional_derivatives.csv',directions)

    # Full training-feature support for assumption sensitivity, never fit to its Loss.
    scenarios=[]
    refscale=scale_values(nr,dr,par)
    for axis,lq,lp in itertools.product(axes,cfg['lambda_Q_sensitivity'],cfg['lambda_p_sensitivity']):
        pred=predict(nr,dr,ptrain,axis,lq,lp)
        a=mix['axes'][axis];qa=pred.Q_A.to_numpy();lo,hi=a['Q_A_train_min'],a['Q_A_train_max']
        boundary=np.isclose(qa,lo,atol=(hi-lo)*1e-10,rtol=0)|np.isclose(qa,hi,atol=(hi-lo)*1e-10,rtol=0)
        dq=np.where((qa>lo)&(qa<hi),c*lq*.9/(hi-lo),0.)
        dq=np.where(boundary & (lq!=0),np.nan,dq)
        f=pd.DataFrame(dict(axis=axis,lambda_Q=lq,lambda_p=lp,source_recipe_id=train['index'].to_numpy(),
            predicted_loss=pred.predicted_loss_scenario.to_numpy(),Q_A=qa,quality_kink=boundary,
            N_marginal_benefit=refscale['N_marginal_benefit'],D_marginal_benefit=refscale['D_marginal_benefit'],
            elasticity_N=nr*refscale['dL_dN_B']/pred.predicted_loss_scenario.to_numpy(),
            elasticity_D=dr*refscale['dL_dD_B']/pred.predicted_loss_scenario.to_numpy(),dL_dQA_fixed_residual=dq,
            observed_joint_row=False))
        assert (f.predicted_loss>0).all(), 'Undefined log-Loss elasticity: nonpositive scenario prediction.'
        scenarios.append(f)
    scenarios=pd.concat(scenarios,ignore_index=True);save('assumption_sensitivity.csv',scenarios)
    assert scenarios.N_marginal_benefit.nunique()==1 and scenarios.D_marginal_benefit.nunique()==1
    ssummary=scenarios.groupby(['axis','lambda_Q','lambda_p']).agg(rows=('predicted_loss','size'),
        loss_min=('predicted_loss','min'),loss_max=('predicted_loss','max'),
        N_elasticity_min=('elasticity_N','min'),N_elasticity_max=('elasticity_N','max'),
        D_elasticity_min=('elasticity_D','min'),D_elasticity_max=('elasticity_D','max')).reset_index()
    save('assumption_sensitivity_summary.csv',ssummary)
    save('verification_checks.csv',pd.DataFrame(checks))
    # Coordinate origin test: slopes are unchanged by translation, elasticities are not.
    origins=[]
    lref=float(refscale['predicted_loss'])
    for axis in axes:
        a=mix['axes'][axis];slope=c*.9/(a['Q_A_train_max']-a['Q_A_train_min'])
        for shift in [0.,1.]:
            origins.append(dict(axis=axis,QA_coordinate_shift=shift,physical_reference_unchanged=True,
                reference_coordinate=a['Q_A_reference']+shift,dL_d_coordinate=slope,
                quality_elasticity=(a['Q_A_reference']+shift)*slope/lref))
    save('quality_origin_sensitivity.csv',pd.DataFrame(origins))
    assert before=={p.relative_to(REPO).as_posix():fingerprint(p) for p in inputs}
    comparison=directions[directions.to_index<directions.from_index].pivot(index=['to_index','from_index'],columns='axis',values='derivative_per_fraction')
    sign_agreement=float((np.sign(comparison.iloc[:,0])==np.sign(comparison.iloc[:,1])).mean())
    held=folds[folds.fit!='full_fit'].copy();full=anchors.set_index(['N_params_B','D_tokens_B'])
    max_fold_relative={}
    for column in ['N_marginal_benefit','D_marginal_benefit','elasticity_N','elasticity_D']:
        baseline=np.array([full.loc[(r.N_params_B,r.D_tokens_B),column] for r in held.itertuples()])
        max_fold_relative[column]=float(np.max(abs(held[column].to_numpy()/baseline-1)))
    metrics=dict(status='PASS_CONDITIONAL_ANALYSIS',run_id=cfg['run_id'],input_and_model_unchanged=True,
        derivative_check_groups=len(checks),scalar_comparisons=sum(x['comparisons'] for x in checks),all_checks_pass=True,
        scale_grid_rows=len(grid),scale_curve_rows=sum(len(f) for f in curves),quality_rows=len(formal),
        simplex_direction_rows=len(directions),assumption_scenario_rows=len(scenarios),
        reference_N_B=nr,reference_D_B=dr,reference_loss=lref,
        reference_N_marginal_benefit=float(refscale['N_marginal_benefit']),
        reference_D_marginal_benefit=float(refscale['D_marginal_benefit']),
        reference_N_elasticity=float(refscale['elasticity_N']),reference_D_elasticity=float(refscale['elasticity_D']),
        doubling_N_marginal_ratio=2**(-par['alpha']-1),doubling_D_marginal_ratio=2**(-par['beta']-1),
        quality_interior_slopes={a:c*.9/(mix['axes'][a]['Q_A_train_max']-mix['axes'][a]['Q_A_train_min']) for a in axes},
        quality_axis_direction_sign_agreement=sign_agreement,unordered_direction_pairs=len(comparison),
        max_relative_scale_fold_deviation=max_fold_relative,
        max_first_derivative_check_error=max(x['max_absolute_error'] for x in checks if 'first_relative' in x['check']),
        interpretation='Analytic/implementation validation of frozen conditional v1; no new observed performance or causal validation.')
    write_json(out/'metrics.json',metrics)
    write_json(out/'manifest.json',dict(run_id=cfg['run_id'],input_sha256=before,
        config=cfg,environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                                   scipy=scipy.__version__,scikit_learn=sklearn.__version__),
        fit_new_parameters=False,raw_attachments_accessed=False,observed_labels_used=False,
        output_csv_sha256={p.name:fingerprint(p) for p in sorted(out.glob('*.csv'))}))
    print(json.dumps(metrics,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
