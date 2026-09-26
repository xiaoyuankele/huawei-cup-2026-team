"""E3 deterministic conditional figures; no empirical uncertainty implied."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from q2_e3_quality_substitution import ROOT, sha, dump

WIDTH_IN = 180/25.4
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':7,'axes.labelsize':7,
                     'axes.titlesize':8,'xtick.labelsize':7,'ytick.labelsize':7,
                     'legend.fontsize':7,'pdf.fonttype':42,'ps.fonttype':42,
                     'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
AXES = [('Q_A_topsis_0_1','TOPSIS'),('quality_score_soft_proxy_0_1','Soft proxy')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir',type=Path,default=ROOT/'experiments/runs/q2-e3-quality-parameter-substitution-20260925-r01')
    args = ap.parse_args(); r = args.run_dir; out=r/'figures';out.mkdir(exist_ok=True)
    curves=pd.read_csv(r/'quality_path_curves.csv');cap=pd.read_csv(r/'quality_capacity.csv')
    recipes=pd.read_csv(r/'recipe_substitution.csv')
    exports=[]
    def export(fig,name):
        for suffix in ['.svg','.pdf','.png']:
            p=out/(name+suffix);fig.savefig(p,dpi=300)
            if suffix=='.svg':
                p.write_text('\n'.join(x.rstrip() for x in p.read_text(encoding='utf-8').splitlines())+'\n',
                             encoding='utf-8',newline='\n')
            exports.append(p)
        plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(WIDTH_IN,145/25.4),layout='constrained')
    for j,(axis,label) in enumerate(AXES):
        ax=axs[0,j];sub=curves[(curves.axis==axis)&(curves.N0_B==1)]
        for lq,color,style in [(0,'#777777',':'),(.5,'#D55E00','--'),(1,'#0072B2','-')]:
            s=sub[sub.lambda_Q==lq]
            ax.plot(s.delta_QB,s.N_required_ratio,color=color,ls=style,label=f'lambda Q = {lq}')
        ax.set(xlabel='Mapped quality increment (QB)',ylabel='Required N / baseline N',
               title=f'{"ab"[j]}  {label}: feasible path')
        ax.legend(frameon=False)
        ax=axs[1,j];s=cap[(cap.axis==axis)&(cap.N0_B==1)&(cap.lambda_Q==1)]
        vals=[s[s.kind==k].N_scale_ratio.iloc[0] for k in ['feasible_fixed_residual','formal_quality_coordinate']]
        bars=ax.bar(['Feasible path','Formal coordinate'],vals,color=['#0072B2','#999999'],width=.55)
        for bar,val in zip(bars,vals):
            ax.text(bar.get_x()+bar.get_width()/2,val+.05,f'{val:.2f}x',ha='center')
        ax.set(ylim=(0,max(vals)*1.22),ylabel='Equivalent scale expansion',
               title=f'{"cd"[j]}  {label}: capacity at lambda Q = 1')
    fig.suptitle('Conditional equal-loss substitution | N0 = 1B, D = 100B',fontsize=9)
    export(fig,'E3_quality_scale_tradeoff')
    fig,axs=plt.subplots(1,2,figsize=(WIDTH_IN,85/25.4),layout='constrained')
    for ax,(axis,label),panel in zip(axs,AXES,'ab'):
        s=recipes[(recipes.axis==axis)&(recipes.N0_B==1)&(recipes.lambda_Q==1)&(recipes.lambda_p==1)]
        bad=s.quality_up_loss_not_improved
        ax.scatter(s.loc[~bad,'delta_QA'],s.loc[~bad,'gain_total'],s=10,c='#0072B2',alpha=.5,label='Other recipes')
        ax.scatter(s.loc[bad,'delta_QA'],s.loc[bad,'gain_total'],s=14,c='#D55E00',marker='x',
                   label=f'Quality up, gain <= 0 (n={bad.sum()})')
        ax.axhline(0,color='#777777',lw=.6);ax.axvline(0,color='#777777',lw=.6)
        ax.set(xlabel='Recipe quality change (QA)',ylabel='Total predicted Loss reduction',
               title=f'{panel}  {label} | all 512 recipes')
        ax.legend(frameon=False,loc='upper left',fontsize=7)
    fig.suptitle('Conditional recipe changes | lambda Q = lambda p = 1',fontsize=9)
    export(fig,'E3_recipe_counterexamples')
    dump(out/'export_manifest.json',dict(source_script_sha256=sha(Path(__file__)),
         source_csvs={p:sha(r/p) for p in ['quality_path_curves.csv','quality_capacity.csv','recipe_substitution.csv']},
         exports={p.name:sha(p) for p in exports},status='SELF_CHECK_NOT_PEER_REVIEW'))


if __name__=='__main__':
    main()
