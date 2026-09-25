import csv, glob, json, lzma, os
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata

ATT = Path(os.environ.get('QUALITY_ATTACHMENTS_ROOT', 'data/origin/real_attachments/A_data_value'))
OUT = Path(os.environ.get('QUALITY_MAPPING_OUTPUT_DIR', 'quality_mapping_outputs'))
OUT.mkdir(parents=True, exist_ok=True)

# A16: official direct / near_direct links plus an explicit, low-confidence proxy for inferred rows.
# The proxy is kept separate from the official mapping_type and is never presented as observed.
proxy = {
    'arxiv': ('arxiv', 'direct', 'official'),
    'github': ('github', 'direct', 'official'),
    'stackexchange': ('stackexchange', 'direct', 'official'),
    'wikipedia_en': ('wikipedia', 'near_direct', 'official'),
    'gutenberg_pg_19': ('book', 'near_direct', 'official'),
    'pile_cc': ('commoncrawl', 'near_direct', 'official'),
    'dm_mathematics': ('arxiv', 'inferred', 'scientific/math proxy'),
    'freelaw': ('book', 'inferred', 'formal/legal prose proxy'),
    'nih_exporter': ('arxiv', 'inferred', 'biomedical/scientific proxy'),
    'pubmed_central': ('arxiv', 'inferred', 'biomedical/scientific proxy'),
    'philpapers': ('arxiv', 'inferred', 'scholarly prose proxy'),
    'enron_emails': ('commoncrawl', 'inferred', 'web/text proxy'),
    'ubuntu_irc': ('commoncrawl', 'inferred', 'web/text proxy'),
    'europarl': ('wikipedia', 'inferred', 'formal encyclopedic proxy'),
    'hackernews': ('commoncrawl', 'inferred', 'web/text proxy'),
    'pubmed_abstracts': ('arxiv', 'inferred', 'biomedical/scientific proxy'),
    'uspto_backgrounds': ('book', 'inferred', 'formal/legal prose proxy'),
}

# Read A1-A3. List-valued signals are reduced to their arithmetic mean as required by the PDF.
quality_files = [ATT/'slimpajama_quality_signal_sample.jsonl.xz'] + sorted((ATT/'slimpajama_quality_extended').glob('*.jsonl.xz'))
rows = []
for f in quality_files:
    forced = 'arxiv' if 'arxiv' in f.name else ('github' if 'github' in f.name else None)
    with lzma.open(f, 'rt', encoding='utf-8') as h:
        for line in h:
            x = json.loads(line)
            domain = forced or x.get('_source_domain')
            y = {'quality_domain': domain}
            for k, v in x.items():
                if k in {'id','content','sub_path','_source_domain','_source_path'}:
                    continue
                if isinstance(v, list):
                    a = [float(z) for z in v if isinstance(z, (int,float)) and np.isfinite(z)]
                    y[k] = float(np.mean(a)) if a else np.nan
                elif isinstance(v, (int,float)):
                    y[k] = float(v) if np.isfinite(v) else np.nan
            rows.append(y)
qdf = pd.DataFrame(rows)
features = [c for c in qdf.columns if c != 'quality_domain']
# Fill the few missing values with the global feature median.
Xraw = qdf[features].copy()
Xraw = Xraw.fillna(Xraw.median(numeric_only=True))
# Rank-percentile transforms reduce the effect of very heavy-tailed DSIR/count signals.
X = np.column_stack([rankdata(Xraw[c].to_numpy(), method='average') / (len(Xraw)+1.0) for c in features])
anchor_names = ['fineweb_edu','fluency_en','modernbert_cleanliness','modernbert_readability','modernbert_reasoning','modernbert_professionalism','qurater','ad_en']
anchor = X[:, [features.index(c) for c in anchor_names]].mean(axis=1)
# Small, deterministic NumPy K-means implementation.  It avoids depending on
# BLAS thread-control libraries while still fitting on a representative sample.
rng = np.random.default_rng(42)
fit_idx = rng.choice(len(X), size=min(50000, len(X)), replace=False)
Xfit = X[fit_idx]
centers = Xfit[rng.choice(len(Xfit), size=3, replace=False)].copy()
for _ in range(60):
    d = ((Xfit[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    lab_fit = d.argmin(axis=1)
    new_centers = np.vstack([Xfit[lab_fit == k].mean(axis=0) if np.any(lab_fit == k) else centers[k] for k in range(3)])
    if np.max(np.abs(new_centers - centers)) < 1e-7:
        centers = new_centers
        break
    centers = new_centers
labels = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
cluster_anchor = {int(k): float(anchor[labels == k].mean()) for k in range(3)}
ordered = sorted(cluster_anchor, key=cluster_anchor.get)
cluster_q = {int(k): float(i/2) for i,k in enumerate(ordered)}
qdf['cluster'] = labels
qdf['cluster_q'] = qdf['cluster'].map(cluster_q)
qdf['anchor_rank'] = anchor
# Domain-level quality profile.
prof = []
for dom, g in qdf.groupby('quality_domain', sort=True):
    prof.append({
        'quality_domain': dom,
        'n_records': int(len(g)),
        'q_score_0_1': float(g['cluster_q'].mean()),
        'low_share': float((g['cluster_q'] == 0.0).mean()),
        'middle_share': float((g['cluster_q'] == 0.5).mean()),
        'high_share': float((g['cluster_q'] == 1.0).mean()),
        'anchor_rank_mean': float(g['anchor_rank'].mean()),
    })
profdf = pd.DataFrame(prof)
score_by_domain = profdf.set_index('quality_domain')['q_score_0_1'].to_dict()

# Resolve A16 into an auditable table.
mapdf = pd.read_csv(ATT/'domain_mapping_guide.csv')
mapdf['proxy_quality_domain'] = mapdf['mixture_domain'].map(lambda d: proxy[d][0])
mapdf['proxy_mapping_type'] = mapdf['mixture_domain'].map(lambda d: proxy[d][1])
mapdf['proxy_confidence_note'] = mapdf['mixture_domain'].map(lambda d: proxy[d][2])
mapdf['quality_q_score_0_1'] = mapdf['proxy_quality_domain'].map(score_by_domain)
mapdf['source_for_score'] = 'A1-A3: domain-level cluster-Q; list signals reduced by mean; rank-percentile + KMeans(3)'
mapdf.to_csv(OUT/'A16_domain_mapping_resolved.csv', index=False, encoding='utf-8-sig')
profdf.to_csv(OUT/'quality_domain_scores.csv', index=False, encoding='utf-8-sig')

# Read and join every A4-A15 mixture/Loss pair.
pairs = [
    ('A4_A5_train_1m','train_mixture_1m.csv','train_pile_loss_1m.csv','train','1m',True),
    ('A6_A7_test_1m','test_mixture_1m.csv','test_pile_loss_1m.csv','test','1m',True),
    ('A8_A9_test_60m','test_mixture_60m.csv','test_pile_loss_60m.csv','test','60m',True),
    ('A10_A11_test_1b','test_mixture_1B.csv','test_pile_loss_1B.csv','test','1b',True),
    ('A12_A13_est_10b','est_mixture_10b.csv','est_pile_loss_10b.csv','estimate','10b',False),
    ('A14_A15_est_70b','est_mixture_70b.csv','est_pile_loss_70b.csv','estimate','70b',False),
]
all_wide=[]
all_long=[]
mixture_cols=None
loss_cols=None
map_type = mapdf.set_index('mixture_domain')['mapping_type'].to_dict()
proxy_dom = mapdf.set_index('mixture_domain')['proxy_quality_domain'].to_dict()
for ds, mixfile, lossfile, role, scale, observed in pairs:
    mix = pd.read_csv(ATT/'regmix_tables'/mixfile)
    loss = pd.read_csv(ATT/'regmix_tables'/lossfile)
    if set(mix['index']) != set(loss['index']):
        raise ValueError(f'index mismatch {ds}')
    df = mix.merge(loss, on='index', how='inner', validate='one_to_one')
    if mixture_cols is None:
        mixture_cols = [c for c in mix.columns if c != 'index']
        loss_cols = [c for c in loss.columns if c != 'index']
    # Normalize row sums to remove the documented per-mille rounding error.
    raw_p = df[mixture_cols].astype(float)
    row_sum = raw_p.sum(axis=1)
    p = raw_p.div(row_sum.replace(0, np.nan), axis=0)
    direct_cols = [c for c in mixture_cols if map_type[c.replace('train_the_pile_','')] in {'direct','near_direct'}]
    direct_domains = [c.replace('train_the_pile_','') for c in direct_cols]
    mapped_share = p[direct_cols].sum(axis=1)
    q_proxy = np.zeros(len(df), dtype=float)
    q_mapped_num = np.zeros(len(df), dtype=float)
    high_proxy = np.zeros(len(df), dtype=float)
    mid_proxy = np.zeros(len(df), dtype=float)
    low_proxy = np.zeros(len(df), dtype=float)
    for c in mixture_cols:
        md = c.replace('train_the_pile_','')
        qd = proxy_dom[md]
        qv = score_by_domain[qd]
        q_proxy += p[c].to_numpy() * qv
        qg = profdf.loc[profdf.quality_domain == qd].iloc[0]
        low_proxy += p[c].to_numpy() * qg['low_share']
        mid_proxy += p[c].to_numpy() * qg['middle_share']
        high_proxy += p[c].to_numpy() * qg['high_share']
        if map_type[md] in {'direct','near_direct'}:
            q_mapped_num += p[c].to_numpy() * qv
    q_mapped = np.divide(q_mapped_num, mapped_share.to_numpy(), out=np.full(len(df), np.nan), where=mapped_share.to_numpy()>0)
    out = pd.DataFrame({
        'dataset': ds, 'role': role, 'scale': scale, 'loss_observed': observed,
        'index': df['index'].astype(int),
        'mixture_sum_raw': row_sum,
        'mapped_share_direct_near_direct': mapped_share,
        'quality_score_mapped_0_1': q_mapped,
        'quality_score_proxy_0_1': q_proxy,
        'proxy_low_share': low_proxy,
        'proxy_middle_share': mid_proxy,
        'proxy_high_share': high_proxy,
        'loss_mean_13_domains': df[loss_cols].astype(float).mean(axis=1),
    })
    # Keep normalized mixture and all loss columns in the wide deliverable.
    for c in mixture_cols:
        out[c.replace('train_the_pile_','p_')] = p[c]
    for c in loss_cols:
        out[c] = df[c]
    all_wide.append(out)
    for c in mixture_cols:
        md = c.replace('train_the_pile_','')
        qd = proxy_dom[md]
        g = profdf.loc[profdf.quality_domain == qd].iloc[0]
        all_long.append(pd.DataFrame({
            'dataset': ds, 'role': role, 'scale': scale, 'loss_observed': observed,
            'index': df['index'].astype(int), 'mixture_domain': md,
            'proportion_raw': raw_p[c], 'proportion_normalized': p[c],
            'mapping_type_A16': map_type[md], 'quality_domain_proxy': qd,
            'mapping_confidence': 'official' if map_type[md] in {'direct','near_direct'} else 'inferred_proxy',
            'domain_quality_score_0_1': g['q_score_0_1'],
            'weighted_quality_contribution': p[c] * g['q_score_0_1'],
        }))
wide = pd.concat(all_wide, ignore_index=True)
long = pd.concat(all_long, ignore_index=True)
wide.to_csv(OUT/'A4_A15_quality_scored.csv', index=False, encoding='utf-8-sig')
long.to_csv(OUT/'A4_A15_quality_scored_long.csv', index=False, encoding='utf-8-sig')

meta = {
    'quality_records': int(len(qdf)),
    'quality_domains': sorted(score_by_domain),
    'cluster_anchor_centers': cluster_anchor,
    'cluster_q_mapping': cluster_q,
    'list_reduction': 'arithmetic mean of numeric list elements',
    'normalization': 'rank percentile per feature over A1-A3 records; KMeans n_clusters=3 random_state=42',
    'anchor_features': anchor_names,
    'official_mapping': 'A16 direct/near_direct only',
    'inferred_proxy_mapping': 'included in quality_score_proxy_0_1 and marked inferred_proxy',
    'datasets': [{'dataset': ds, 'n': int((wide.dataset==ds).sum())} for ds, *_ in pairs],
    'output_files': [p.name for p in OUT.iterdir() if p.is_file()],
}
(OUT/'quality_score_method.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

# Basic audit printout for reproducibility.
print('quality records:', len(qdf))
print('domain scores:')
print(profdf[['quality_domain','n_records','q_score_0_1','low_share','middle_share','high_share']].to_string(index=False))
print('wide rows:', len(wide), 'long rows:', len(long))
print('row sum max abs error after normalization:', float((wide.filter(regex='^p_').sum(axis=1)-1).abs().max()))
print('dataset summary:')
print(wide.groupby(['dataset','role','scale'], as_index=False).agg(n=('index','size'), q_proxy_mean=('quality_score_proxy_0_1','mean'), q_proxy_sd=('quality_score_proxy_0_1','std'), mapped_share_mean=('mapped_share_direct_near_direct','mean'), loss_mean=('loss_mean_13_domains','mean')).to_string(index=False))
