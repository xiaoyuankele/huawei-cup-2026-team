"""E2 quantitative grid: finite support, directional sensitivity, clipping artifacts.

Every record is a deterministic conditional-model calculation; no empirical
replicates, p values or confidence intervals. All domains/pairs are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'experiments/runs/q2-e2-domain-substitution-20260925-r01'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
    'font.size':7,'axes.labelsize':8,'axes.titlesize':9,'xtick.labelsize':7,'ytick.labelsize':7,
    'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,
    'legend.frameon':False,'figure.facecolor':'white'})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run-dir',type=Path,default=DEFAULT);args=ap.parse_args()
    r=args.run_dir;out=r/'figures';out.mkdir(exist_ok=True)
    support=pd.read_csv(r/'substitution_support.csv');sens=pd.read_csv(r/'assumption_sensitivity.csv')
    inter=pd.read_csv(r/'interior_interactions.csv');stress=pd.read_csv(r/'clipping_stress_interactions.csv')
    stability=pd.read_csv(r/'direction_stability.csv');metadata=[]
    def export(fig,name,width,height,sources):
        fig.set_size_inches(width/25.4,height/25.4)
        for extension in ['svg','pdf','png']:
            fig.savefig(out/(name+'.'+extension),dpi=300)
            if extension == 'svg':
                path = out/(name+'.svg')
                path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',
                                encoding='utf-8',newline='\n')
        metadata.append(dict(figure=name,width_mm=width,height_mm=height,source_csvs=sources,
                             independent_replicates=0,uncertainty='Not estimated; conditional deterministic calculations'))
        plt.close(fig)
    # Matrix is to-domain x from-domain. Only diagonal has no defined transfer.
    labels=[support.loc[support.to_index==i,'to_domain'].iloc[0].replace('_',' ') for i in range(17)]
    matrix=support.pivot(index='to_index',columns='from_index',values='safe_hull_limit_pp').reindex(index=range(17),columns=range(17)).to_numpy()
    assert np.isfinite(matrix).sum()==272
    fig,ax=plt.subplots(figsize=(180/25.4,160/25.4))
    fig.subplots_adjust(left=.24,right=.86,bottom=.26,top=.87)
    cmap=plt.get_cmap('Blues').copy();cmap.set_bad('#EEEEEE')
    im=ax.imshow(matrix,cmap=cmap,vmin=0,vmax=float(np.nanmax(matrix)),interpolation='nearest',aspect='equal')
    ax.set_xticks(range(17),labels,rotation=90);ax.set_yticks(range(17),labels)
    ax.set_xlabel('Removed from domain',labelpad=8);ax.set_ylabel('Added to domain',labelpad=8)
    ax.tick_params(length=0);ax.set_title('Supported finite substitution at the reference recipe',pad=12)
    cax=fig.add_axes([.9,.3,.02,.49]);cb=fig.colorbar(im,cax=cax);cb.set_label('99% of hull limit (percentage points)',labelpad=7)
    fig.text(.24,.95,'A4 recipe convex hull; 272 directed transfers',fontsize=9)
    fig.text(.24,.92,'Feature support only; no observed joint A-B experiment',fontsize=7,color='#555555')
    export(fig,'E2_substitution_support',180,160,['substitution_support.csv'])
    # Two panels use all 136 unordered pairs and all interaction diagnostics.
    fig,axs=plt.subplots(1,2,figsize=(180/25.4,92/25.4));fig.subplots_adjust(left=.10,right=.98,bottom=.23,top=.77,wspace=.43)
    nominal=sens.query('lambda_Q == 1 and lambda_p == 1 and to_index < from_index')
    paired=nominal.pivot(index=['to_index','from_index'],columns='axis',values='slope_per_fraction')
    x=paired['Q_A_topsis_0_1'].to_numpy();y=paired['quality_score_soft_proxy_0_1'].to_numpy();agree=x*y>0
    assert len(x)==136
    ax=axs[0];ax.axhline(0,color='#BBBBBB',lw=.6);ax.axvline(0,color='#BBBBBB',lw=.6)
    ax.scatter(x[agree],y[agree],s=11,color='#42678E',alpha=.65,label=f'Same direction ({agree.sum()})')
    ax.scatter(x[~agree],y[~agree],s=20,color='#B87235',marker='x',label=f'Opposite ({(~agree).sum()})')
    lim=max(np.max(abs(x)),np.max(abs(y)))*1.08
    ax.set_xlim(-lim,lim);ax.set_ylim(-lim,lim);ax.set_xlabel('TOPSIS-axis Loss slope / fraction');ax.set_ylabel('Soft-axis Loss slope / fraction')
    ax.set_title('Quality-axis sensitivity',pad=8);ax.legend(loc='upper left',bbox_to_anchor=(0,1.02),fontsize=7,markerscale=1)
    ax.text(-.19,1.19,'a',transform=ax.transAxes,weight='bold',fontsize=10)
    ax=axs[1]
    threshold=1e-10
    # Signed finite four-corner gap; threshold defines numerical zero, not significance.
    interior_counts=[int((inter.interaction_loss<-threshold).sum()),int((inter.interaction_loss.abs()<=threshold).sum()),int((inter.interaction_loss>threshold).sum())]
    stress_counts=[int((stress.interaction_loss<-threshold).sum()),int((stress.interaction_loss.abs()<=threshold).sum()),int((stress.interaction_loss>threshold).sum())]
    xx=np.arange(3);width=.35
    a=ax.bar(xx-width/2,np.array(interior_counts)/len(inter)*100,width,color='#42678E',label='Training hull (4080)')
    b=ax.bar(xx+width/2,np.array(stress_counts)/len(stress)*100,width,color='#B87235',label='Vertex stress (12240)')
    ax.set_xticks(xx,['Negative','Numerical\nzero','Positive']);ax.set_ylim(0,125);ax.set_yticks([0,25,50,75,100]);ax.set_ylabel('Share of calculated four-corner designs (%)')
    ax.set_title('Interaction or mapping artifact?',pad=8)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,1.04),fontsize=7)
    for bars,counts in [(a,interior_counts),(b,stress_counts)]:
        for bar,count in zip(bars,counts):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,str(count),ha='center',fontsize=7)
    ax.text(-.19,1.19,'b',transform=ax.transAxes,weight='bold',fontsize=10)
    fig.text(.10,.95,'Frozen-model diagnostics, not empirical complementarity tests',fontsize=9)
    fig.text(.10,.06,f'Across active strength assumptions: {int(stability.sign_flips.sum())}/136 pairs reverse; '+
             f'{int(stability.robust_nonzero_direction.sum())}/136 retain a strict direction.',fontsize=7)
    fig.text(.10,.02,'Every nonzero vertex-stress interaction is explained by quality clipping; zero tolerance = 1e-10 Loss.',fontsize=7)
    export(fig,'E2_direction_interaction',180,92,['assumption_sensitivity.csv','direction_stability.csv','interior_interactions.csv','clipping_stress_interactions.csv'])
    data=dict(backend='Python/matplotlib',matplotlib=matplotlib.__version__,figures=metadata,
              plot_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              file_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.suffix in ['.svg','.pdf','.png']})
    (out/'export_manifest.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Exported two E2 figures as SVG/PDF/PNG')


if __name__=='__main__':main()
