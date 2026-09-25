"""Plot the E1 frozen-model analysis; all marks are deterministic scenarios.

Figure contract: 180 mm quantitative panels, editable PDF/SVG and 300 dpi PNG.
No statistical CI is implied: there are no new independent experimental units.
Source data: scale_curves.csv, quality_piecewise.csv and
simplex_directional_derivatives.csv. Reverse directions are retained in tables;
the direction comparison shows all 136 unique pairs once. Repeated identical
marginal-benefit curves are represented once with the fixed coordinate stated.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BLUE='#356C91'
TEAL='#43877E'
RUST='#AD6047'
GRAY='#899299'

plt.rcParams.update({
    'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
    'font.size':8,'axes.titlesize':9,'axes.labelsize':8,
    'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':7,
    'svg.fonttype':'none','pdf.fonttype':42,
    'axes.spines.top':False,'axes.spines.right':False,
    'axes.linewidth':.7,'lines.linewidth':1.5,'legend.frameon':False,
    'savefig.facecolor':'white','figure.facecolor':'white',
})


def panel(ax, letter, title):
    ax.set_title(title,loc='left',pad=10)
    ax.text(-.17,1.10,letter,transform=ax.transAxes,fontweight='bold',fontsize=10,va='top')
    ax.tick_params(direction='out',length=3)


def export(fig, stem, records):
    fig.canvas.draw()
    # Catch clipped labels at the declared physical size before export.
    renderer=fig.canvas.get_renderer()
    width,height=fig.canvas.get_width_height()
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text():continue
        box=text.get_window_extent(renderer)
        # Hidden log tick labels can exist outside view; only inspect titles,
        # axis labels, legends and explicitly placed figure annotations here.
        if text in [a.xaxis.label for a in fig.axes]+[a.yaxis.label for a in fig.axes] or text in fig.texts:
            assert box.x0>=-1 and box.y0>=-1 and box.x1<=width+1 and box.y1<=height+1,text.get_text()
    fig.savefig(f'{stem}.svg')
    svg_path=stem.with_suffix('.svg')
    # Keep generated XML portable; newline whitespace is equivalent in SVG paths.
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text(encoding='utf-8').splitlines())+'\n',
                        encoding='utf-8',newline='\n')
    fig.savefig(f'{stem}.pdf')
    fig.savefig(f'{stem}.png',dpi=300)
    records.append(dict(figure=stem.name,width_mm=float(fig.get_figwidth()*25.4),height_mm=float(fig.get_figheight()*25.4),
                        backend='matplotlib',png_dpi=300,editable_vector_text=True,
                        source='deterministic frozen-model scenarios',confidence_intervals=False))
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,default=ROOT/'experiments/runs/q2-e1-marginal-elasticity-20260925-r01')
    args=parser.parse_args();run=args.run_dir;out=run/'figures';out.mkdir(exist_ok=True)
    curves=pd.read_csv(run/'scale_curves.csv')
    assert (curves[['N_params_B','D_tokens_B','N_marginal_benefit','D_marginal_benefit']]>0).all().all()
    records=[]
    fig,axs=plt.subplots(2,2,figsize=(7.0866141732,5.6299212598))
    fig.subplots_adjust(left=.12,right=.97,bottom=.13,top=.90,wspace=.43,hspace=.58)
    fig.suptitle('Scale sensitivities of frozen Q2 v1',fontsize=11,y=.98)
    ncurve=curves[(curves.varying=='N') & (curves.D_tokens_B==100)].sort_values('N_params_B')
    dcurve=curves[(curves.varying=='D') & (curves.N_params_B==1)].sort_values('D_tokens_B')
    a,b,c,d=axs.ravel()
    a.loglog(ncurve.N_params_B,ncurve.N_marginal_benefit,color=BLUE)
    a.set(xlabel='Parameters N (billions)',ylabel='Marginal Loss reduction\n(per billion parameters)')
    panel(a,'a','Parameter marginal benefit')
    b.loglog(dcurve.D_tokens_B,dcurve.D_marginal_benefit,color=TEAL)
    b.set(xlabel='Training tokens D (billions)',ylabel='Marginal Loss reduction\n(per billion tokens)')
    panel(b,'b','Data marginal benefit')
    palette=[GRAY,BLUE,TEAL];styles=[':','--','-']
    for (fixed,part),color,style in zip(curves[curves.varying=='N'].groupby('D_tokens_B'),palette,styles):
        part=part.sort_values('N_params_B')
        c.semilogx(part.N_params_B,part.elasticity_N,color=color,ls=style,label=f'D = {fixed:g} B')
    c.set(xlabel='Parameters N (billions)',ylabel='Elasticity of total Loss to N')
    c.legend(loc='lower right');panel(c,'c','Parameter elasticity depends on D')
    for (fixed,part),color,style in zip(curves[curves.varying=='D'].groupby('N_params_B'),palette,styles):
        part=part.sort_values('D_tokens_B')
        d.semilogx(part.D_tokens_B,part.elasticity_D,color=color,ls=style,label=f'N = {fixed:g} B')
    d.set(xlabel='Training tokens D (billions)',ylabel='Elasticity of total Loss to D')
    d.legend(loc='upper left');panel(d,'d','Data elasticity depends on N')
    fig.text(.12,.035,'Reference mixture; all curves are model implications within the B1 marginal ranges.',fontsize=7)
    export(fig,out/'E1_scale_sensitivity',records)

    quality=pd.read_csv(run/'quality_piecewise.csv')
    directions=pd.read_csv(run/'simplex_directional_derivatives.csv')
    axes=['Q_A_topsis_0_1','quality_score_soft_proxy_0_1']
    fig,axs=plt.subplots(1,2,figsize=(7.0866141732,3.5826771654))
    fig.subplots_adjust(left=.11,right=.97,bottom=.23,top=.80,wspace=.46)
    fig.suptitle('Quality mapping and local mixture sensitivities',fontsize=11,y=.97)
    ax=axs[0]
    for axis,color,label in zip(axes,[BLUE,RUST],['TOPSIS proxy','Soft proxy']):
        part=quality[(quality.axis==axis)&(quality.lambda_Q==1)].sort_values('normalized_Q_position')
        ax.plot(part.normalized_Q_position,part.dL_dQA,color=color,label=label)
        for boundary in ['lower_kink','upper_kink']:
            r=part[part.mapping_region==boundary].iloc[0]
            ax.scatter([r.normalized_Q_position]*2,[r.left_dL_dQA,r.right_dL_dQA],s=22,
                       facecolors='white',edgecolors=color,zorder=4,linewidths=1)
    ax.axvline(0,color=GRAY,lw=.7,ls=':');ax.axvline(1,color=GRAY,lw=.7,ls=':')
    ax.set(xlabel='Position within training quality range',ylabel='dLoss / dQA at fixed residual mixture',xlim=(-.13,1.13))
    ax.legend(loc='center left',fontsize=7);panel(ax,'a','Clipping creates derivative jumps')
    table=directions[directions.to_index<directions.from_index].pivot(index=['to_index','from_index'],columns='axis',values='derivative_per_fraction')
    assert len(table)==136 and table.notna().all().all()
    x,y=table[axes[0]].to_numpy(),table[axes[1]].to_numpy()
    agree=np.sign(x)==np.sign(y)
    ax=axs[1]
    ax.scatter(x[agree],y[agree],s=12,color=BLUE,alpha=.65,label=f'Same sign ({agree.sum()})')
    ax.scatter(x[~agree],y[~agree],s=23,color=RUST,marker='x',label=f'Opposite sign ({(~agree).sum()})')
    extent=float(max(abs(x).max(),abs(y).max())*1.10)
    ax.plot([-extent,extent],[-extent,extent],color=GRAY,lw=.8,ls=':')
    ax.axhline(0,color=GRAY,lw=.6);ax.axvline(0,color=GRAY,lw=.6)
    ax.set(xlabel='Directional derivative: TOPSIS proxy',ylabel='Directional derivative: Soft proxy',
           xlim=(-extent,extent),ylim=(-extent,extent))
    ax.legend(loc='upper left',fontsize=7);panel(ax,'b','Quality-axis choice changes some signs')
    fig.text(.11,.105,'a: Native QA units differ; open circles denote one-sided limits, not a two-sided derivative.',fontsize=7)
    fig.text(.11,.047,'b: All 136 unique domain pairs at the training-mean mixture; local predictions, not interventions.',fontsize=7)
    export(fig,out/'E1_quality_mixture_sensitivity',records)
    (out/'export_manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(records,indent=2))


if __name__=='__main__':
    main()
