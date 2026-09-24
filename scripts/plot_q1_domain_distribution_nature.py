"""Figure 1: full-union CRITIC-TOPSIS score distributions (no sampling).

Nature-inspired revision: half-density plus compact boxplot; same observed scores.
Plot implementation and quantitative calculations are original for this dataset.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

EXPECTED_SHA = 'f7148769aac33e8e4e70662e6468f2fb7e05b85dc69901c4b2e33d2ad2b75c22'
EXPECTED_COUNTS = {'arxiv': 17523, 'book': 171, 'c4': 10000,
                   'commoncrawl': 9640, 'github': 203752,
                   'stackexchange': 10000, 'wikipedia': 10000}
LABELS = {'arxiv': 'arXiv', 'book': 'Book', 'c4': 'C4',
          'commoncrawl': 'CommonCrawl', 'github': 'GitHub',
          'stackexchange': 'StackExchange', 'wikipedia': 'Wikipedia'}

def make_figure(source, output, reference=None):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA, 'Unexpected source version'
    frame = pd.read_csv(source, dtype={'record_id': str})
    assert len(frame) == 261086 and frame.record_id.is_unique
    assert frame.domain.notna().all()
    assert frame.groupby('domain').size().to_dict() == EXPECTED_COUNTS
    assert np.isfinite(frame.quality_score).all()
    assert frame.quality_score.between(0, 100).all()
    assert frame.kept_in_unique_union.all()

    summaries, data = [], {}
    for domain, group in frame.groupby('domain'):
        values = group.quality_score.to_numpy()
        data[domain] = values
        p10, q1, median, q3, p90 = np.quantile(values, [.1, .25, .5, .75, .9])
        iqr = q3-q1
        inside = values[(values >= q1-1.5*iqr) & (values <= q3+1.5*iqr)]
        outliers = (values < q1-1.5*iqr) | (values > q3+1.5*iqr)
        summaries.append(dict(domain=domain, n=len(values), mean=float(values.mean()),
                              median=median, q1=q1, q3=q3, iqr=iqr,
                              sd=float(values.std(ddof=1)), min=float(values.min()),
                              max=float(values.max()), p10=p10, p90=p90,
                              whisker_low=float(inside.min()), whisker_high=float(inside.max()),
                              outside_1_5_iqr_count=int(outliers.sum())))
    summary = pd.DataFrame(summaries).sort_values('median', ascending=False)
    summary.to_csv(output/'domain_distribution_summary.csv', index=False, float_format='%.12g')
    if reference:
        ref = pd.read_csv(reference)
        # The recorded full-union domain table is identified by dataset/subset labels.
        candidates = ref.loc[(ref.n_records == ref.domain.map(EXPECTED_COUNTS))]
        for _, row in summary.iterrows():
            matches = candidates.loc[candidates.domain == row.domain]
            assert any(np.isclose(matches['mean'],row['mean'],atol=1e-9,rtol=0))
            assert any(np.isclose(matches['median'],row['median'],atol=1e-9,rtol=0))

    from scipy.stats import gaussian_kde
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['svg.fonttype'] = 'none'
    plt.rcParams.update({'font.size':8,'axes.labelsize':8.5,'xtick.labelsize':8,
                         'ytick.labelsize':8,'legend.fontsize':7.3,'pdf.fonttype':42,'svg.fonttype':'none',
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.linewidth':.6,'axes.unicode_minus':False,
                         'figure.facecolor':'white','axes.facecolor':'white'})
    ink, teal, fill, warm, grey = '#29363D','#527F88','#C8DEDF','#C17855','#738087'
    fig=plt.figure(figsize=(7.2047244094,4.4881889764))  # 183 by 114 mm
    ax=fig.add_axes([.197,.203,.668,.621])
    order=summary.domain.tolist();positions=np.arange(7,0,-1,dtype=float)
    density_records=[]
    for domain,pos in zip(order,positions):
        values=data[domain]
        grid=np.linspace(values.min(),values.max(),400)
        assert np.all(np.diff(grid)>0)
        bandwidth=1.2
        density=gaussian_kde(values,bw_method=bandwidth/values.std(ddof=1))(grid)
        baseline=pos+.06
        contour=baseline+.36*density/density.max()
        ax.fill_between(grid,baseline,contour,facecolor=fill,edgecolor=teal,linewidth=.6,zorder=2)
        density_records.extend({'domain':domain,'quality_score':float(x),'density':float(y)}
                               for x,y in zip(grid,density))
    bp=ax.boxplot([data[d] for d in order],positions=positions-.10,vert=False,widths=.16,
                  whis=1.5,showfliers=True,showmeans=True,patch_artist=True,
                  boxprops={'facecolor':'white','edgecolor':teal,'linewidth':.8},
                  medianprops={'color':ink,'linewidth':1.2},
                  whiskerprops={'color':teal,'linewidth':.65},
                  capprops={'color':teal,'linewidth':.65},
                  flierprops={'marker':'o','markersize':1.3,'markerfacecolor':'none',
                              'markeredgecolor':grey,'markeredgewidth':.3,'alpha':.25},
                  meanprops={'marker':'D','markersize':3.3,'markerfacecolor':warm,
                             'markeredgecolor':'white','markeredgewidth':.35})
    for i,(_,row) in enumerate(summary.iterrows()):
        bp['fliers'][i].set_rasterized(True)
        assert len(bp['fliers'][i].get_xdata())==row.outside_1_5_iqr_count
        assert np.isclose(bp['medians'][i].get_xdata()[0],row['median'],atol=1e-10)
    ax.set_xlim(0,100);ax.set_xticks(np.arange(0,101,20));ax.set_ylim(.45,7.62)
    ax.set_yticks([]);ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#7F8A90')
    ax.tick_params(axis='x',width=.6,length=3,color='#7F8A90',labelcolor=ink)
    ax.grid(axis='x',color='#EDF0F1',linewidth=.55,zorder=0);ax.set_axisbelow(True)
    ax.set_xlabel('质量评分（0–100，越高越好）',labelpad=7,color=ink)
    for pos,(_,row) in zip(positions,summary.iterrows()):
        ax.text(-.045,pos+.06,LABELS[row.domain],transform=ax.get_yaxis_transform(),
                ha='right',va='center',fontsize=8.4,color=ink,clip_on=False)
        ax.text(-.045,pos-.22,f'n = {int(row.n):,}',transform=ax.get_yaxis_transform(),
                ha='right',va='center',fontsize=7,color=grey,clip_on=False)
        ax.text(1.115,pos+.015,f'{row["median"]:.2f}',transform=ax.get_yaxis_transform(),
                ha='center',va='center',fontsize=8.4,color=ink,clip_on=False)
    fig.text(.035,.962,'各领域样本质量评分分布',fontsize=10.5,weight='bold',color=ink,va='top')
    fig.text(.975,.960,'CRITIC–TOPSIS',fontsize=8,color=grey,ha='right',va='top')
    fig.text(.035,.900,'A1 + A2 + A3  /  全量去重  /  N = 261,086',fontsize=7.7,color=grey)
    fig.text(.940,.837,'中位数',fontsize=7.3,ha='center',color=grey)
    handles=[Patch(facecolor=fill,edgecolor=teal,linewidth=.6,label='分布密度'),
             Patch(facecolor='white',edgecolor=teal,linewidth=.8,label='25%–75% 分位'),
             Line2D([0],[0],marker='|',markersize=6,linestyle='none',color=ink,label='中位数'),
             Line2D([0],[0],marker='D',markersize=3.5,linestyle='none',color=warm,label='均值')]
    legend=fig.legend(handles=handles,loc='center',bbox_to_anchor=(.51,.865),ncol=4,
                      frameon=False,handlelength=1.2,columnspacing=1.5,handletextpad=.55)
    fig.text(.197,.067,'密度形状按域归一化；曲线高度不代表样本量。',fontsize=7,color=grey)
    fig.text(.197,.027,'箱须：1.5 × IQR；空心点：范围外观测。全部样本参与计算，未抽样。',fontsize=7,color=grey)
    # Explicit CJK fallback keeps sans-serif Chinese labels and Latin glyphs editable.
    for text_artist in fig.findobj(matplotlib.text.Text):
        text_artist.set_fontfamily(['Arial','Microsoft YaHei'])
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    assert not ax.xaxis.label.get_window_extent(renderer).overlaps(legend.get_window_extent(renderer))
    bad=[]
    for text_artist in fig.findobj(matplotlib.text.Text):
        if not text_artist.get_visible() or not text_artist.get_text():continue
        box=text_artist.get_window_extent(renderer=renderer)
        if box.x0<-.5 or box.y0<-.5 or box.x1>fig.bbox.width+.5 or box.y1>fig.bbox.height+.5:
            bad.append(text_artist.get_text())
    assert not bad,f'Clipped labels: {bad}'
    stem=output/'figure01_domain_distribution_nature'
    for ext in ['png','pdf','svg','tiff']:
        options={'pil_kwargs':{'compression':'tiff_lzw'}} if ext=='tiff' else {}
        fig.savefig(stem.with_suffix('.'+ext),dpi=600,facecolor='white',**options)
    plt.close(fig)
    pd.DataFrame(density_records).to_csv(output/'density_curves.csv',index=False,float_format='%.12g')
    manifest={'figure_id':'Q1-FIG-01-NATURE-V2','run_id':'q1-critic-topsis-20260924-r01',
              'model':'TOPSIS_CRITIC','input_sha256':digest,'unique_records':len(frame),
              'dropped_by_plot':0,'domain_counts':EXPECTED_COUNTS,'order':order,
              'descriptive_statistics':'Unchanged from original figure',
              'density_method':'Full-data Gaussian KDE; absolute bandwidth 1.2 score units; 400 points within observed range; each domain peak normalized',
              'box_definition':'Q1-Q3, median, mean diamond, 1.5-IQR observed whiskers, every flier',
              'outside_1_5_iqr_total':int(summary.outside_1_5_iqr_count.sum()),
              'size_mm':[183,114],'minimum_source_font_pt':7,'dpi':600,
              'clipped_labels':bad,'backend':'Python / matplotlib / scipy',
              'inference':'Descriptive only; no significance, confidence intervals or intrinsic-quality claim'}
    manifest['outputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in output.iterdir() if p.suffix in ['.png','.pdf','.svg','.tiff','.csv']}
    (output/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'records':len(frame),'domains':len(summary),'clipped_labels':bad}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True)
    parser.add_argument('--output',default=str(Path(__file__).resolve().parent))
    parser.add_argument('--reference-domain-table')
    args=parser.parse_args();make_figure(args.input,args.output,args.reference_domain_table)
