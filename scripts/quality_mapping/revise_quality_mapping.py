from pathlib import Path
import json
import pandas as pd

out=Path(os.environ.get('QUALITY_MAPPING_OUTPUT_DIR', 'quality_mapping_outputs'))
score=pd.read_csv(out/'quality_domain_scores.csv').set_index('quality_domain')['q_score_0_1'].to_dict()
orig=pd.read_csv(out/'A16_domain_mapping_resolved.csv')

# Official mappings remain one-to-one. Inferred rows use transparent semantic mixtures.
soft={
 'dm_mathematics': {'arxiv':0.8,'wikipedia':0.2},
 'freelaw': {'book':0.5,'wikipedia':0.3,'commoncrawl':0.2},
 'nih_exporter': {'arxiv':0.6,'wikipedia':0.2,'commoncrawl':0.2},
 'pubmed_central': {'arxiv':0.7,'wikipedia':0.2,'commoncrawl':0.1},
 'philpapers': {'arxiv':0.6,'book':0.2,'wikipedia':0.2},
 'enron_emails': {'commoncrawl':0.5,'stackexchange':0.3,'wikipedia':0.2},
 'ubuntu_irc': {'commoncrawl':0.5,'stackexchange':0.4,'wikipedia':0.1},
 'europarl': {'wikipedia':0.5,'commoncrawl':0.3,'book':0.2},
 'hackernews': {'commoncrawl':0.5,'stackexchange':0.4,'wikipedia':0.1},
 'pubmed_abstracts': {'arxiv':0.7,'wikipedia':0.2,'commoncrawl':0.1},
 'uspto_backgrounds': {'book':0.4,'arxiv':0.3,'wikipedia':0.2,'commoncrawl':0.1},
}
for _,r in orig.iterrows():
    d=r['mixture_domain']
    if r['mapping_type'] in {'direct','near_direct'}:
        soft[d]={r['proxy_quality_domain']:1.0}

rationale={
 'dm_mathematics':'数学/科学文本，arxiv 为主，wikipedia 作通用参考补充',
 'freelaw':'法律文本缺少同名质量域，采用书籍、百科和网页文本的混合代理',
 'nih_exporter':'生物医学/科学文本，arxiv 为主并保留通用文本成分',
 'pubmed_central':'生物医学全文，arxiv 为主，加入百科和网页文本敏感性',
 'philpapers':'学术论文和哲学论述，使用 arxiv、book、wikipedia 混合',
 'enron_emails':'邮件/通用文本，commoncrawl 为主，stackexchange 表示对话文本',
 'ubuntu_irc':'IRC 对话文本，commoncrawl 与 stackexchange 为主',
 'europarl':'正式议会文本，wikipedia 为主并加入网页和书籍文本',
 'hackernews':'技术社区讨论，commoncrawl 与 stackexchange 为主',
 'pubmed_abstracts':'科学摘要，arxiv 为主并保留通用文本敏感性',
 'uspto_backgrounds':'专利背景文本，book 与 arxiv 为主，其他文本作敏感性补充',
}
rows=[]
for _,r in orig.iterrows():
    d=r['mixture_domain']; mix=soft[d]
    vals=[score[k] for k in mix]
    q=sum(score[k]*w for k,w in mix.items())
    rows.append({
      'mixture_domain':d,
      'mapping_type_A16':r['mapping_type'],
      'official_quality_domain_A16':r['quality_domain'],
      'candidate_quality_domains':';'.join(mix.keys()),
      'candidate_weights':json.dumps(mix,ensure_ascii=False,separators=(',',':')),
      'q_soft_0_1':q,
      'q_semantic_range_low_0_1':min(vals),
      'q_semantic_range_high_0_1':max(vals),
      'q_semantic_range_width':max(vals)-min(vals),
      'mapping_confidence':'official' if r['mapping_type'] in {'direct','near_direct'} else 'inferred_low',
      'rationale': 'A16 official one-to-one mapping' if r['mapping_type'] in {'direct','near_direct'} else rationale[d],
      'note':'range is the min/max of candidate domain scores, not a confidence interval',
    })
m2=pd.DataFrame(rows)
m2.to_csv(out/'A16_domain_mapping_v2_soft.csv',index=False,encoding='utf-8-sig')

w=pd.read_csv(out/'A4_A15_quality_scored.csv')
qsoft=dict(zip(m2.mixture_domain,m2.q_soft_0_1))
qlow=dict(zip(m2.mixture_domain,m2.q_semantic_range_low_0_1))
qhigh=dict(zip(m2.mixture_domain,m2.q_semantic_range_high_0_1))
pcols=[c for c in w.columns if c.startswith('p_')]
qv=[]; lo=[]; hi=[]
for _,row in w.iterrows():
    qv.append(sum(row['p_'+d]*qsoft[d] for d in qsoft))
    lo.append(sum(row['p_'+d]*qlow[d] for d in qsoft))
    hi.append(sum(row['p_'+d]*qhigh[d] for d in qsoft))
w['quality_score_soft_proxy_0_1']=qv
w['quality_score_soft_low_0_1']=lo
w['quality_score_soft_high_0_1']=hi
w['quality_score_soft_range_width']=w['quality_score_soft_high_0_1']-w['quality_score_soft_low_0_1']
w.to_csv(out/'A4_A15_quality_scored_v2_soft.csv',index=False,encoding='utf-8-sig')

# Long-form v2 table: one row per mixture row x mixture domain.
long_v1=pd.read_csv(out/'A4_A15_quality_scored_long.csv')
long_v2=long_v1[['dataset','role','scale','loss_observed','index','mixture_domain','proportion_raw','proportion_normalized']].copy()
long_v2=long_v2.merge(m2[['mixture_domain','mapping_type_A16','official_quality_domain_A16','candidate_quality_domains','candidate_weights','q_soft_0_1','q_semantic_range_low_0_1','q_semantic_range_high_0_1','q_semantic_range_width','mapping_confidence','rationale']], on='mixture_domain', how='left', validate='many_to_one')
long_v2['weighted_soft_quality_contribution']=long_v2['proportion_normalized']*long_v2['q_soft_0_1']
long_v2['weighted_soft_low_contribution']=long_v2['proportion_normalized']*long_v2['q_semantic_range_low_0_1']
long_v2['weighted_soft_high_contribution']=long_v2['proportion_normalized']*long_v2['q_semantic_range_high_0_1']
long_v2.to_csv(out/'A4_A15_quality_scored_long_v2_soft.csv',index=False,encoding='utf-8-sig')

# Summary comparing the prior hard-proxy and revised soft-proxy scores.
comp=w.groupby(['dataset','role','scale'],as_index=False).agg(
 n=('index','size'), hard_proxy_mean=('quality_score_proxy_0_1','mean'),
 soft_proxy_mean=('quality_score_soft_proxy_0_1','mean'),
 soft_low_mean=('quality_score_soft_low_0_1','mean'),
 soft_high_mean=('quality_score_soft_high_0_1','mean'),
 soft_range_mean=('quality_score_soft_range_width','mean'))
comp['mean_change_soft_minus_hard']=comp['soft_proxy_mean']-comp['hard_proxy_mean']
comp.to_csv(out/'quality_mapping_v1_v2_comparison.csv',index=False,encoding='utf-8-sig')

# Short revision note.
md=['# A16 映射修订说明','',
'原版本将 11 个 `inferred` 域各自硬映射到一个质量域，作为快速可运行版本。该做法会把语义不确定性隐藏起来。修订版保留 6 个 `direct/near_direct` 一对一映射，对 11 个 inferred 域使用候选质量域组合。', '',
'修订版的 `q_soft_0_1` 是候选域质量分的加权平均；`q_semantic_range_low/high_0_1` 是候选域分数的最小/最大值，用来表示语义代理敏感性，不是统计置信区间。', '',
'建议：正式分析优先报告 direct/near_direct 覆盖的 `quality_score_mapped_0_1`；如果必须覆盖 17 个配方域，使用 `quality_score_soft_proxy_0_1`，同时报告 `quality_score_soft_range_width`。', '',
'## 主要修订',
'- `freelaw`、`uspto_backgrounds`：不再只使用 `book`，增加 `wikipedia`、`arxiv` 或 `commoncrawl` 的敏感性成分。',
'- `enron_emails`、`ubuntu_irc`、`hackernews`：不再只使用 `commoncrawl`，加入 `stackexchange` 以反映对话/技术社区属性。',
'- `europarl`：使用 `wikipedia`、`commoncrawl`、`book` 混合，不再视为单一百科文本。',
'- 生物医学和学术域：仍以 `arxiv` 为主，但保留通用文本域作为不确定性范围。',
]
(out/'A16_mapping_revision_note.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print('wrote v2 outputs')
print(comp.to_string(index=False))
