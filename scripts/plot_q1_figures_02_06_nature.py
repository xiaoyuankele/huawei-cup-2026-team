"""Reproducible Q1 figures 2–6, using the frozen CRITIC–TOPSIS results.

Usage: python plot_figures_02_06.py --repository PATH --output PATH
All sample records contribute; exports of source data are aggregated only.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_pdf import PdfPages

INK, TEAL, PALE, WARM, GREY, GRID = '#29363D', '#527F88', '#C8DEDF', '#C17855', '#738087', '#EDF0F1'
ORDER = ['c4', 'commoncrawl', 'arxiv', 'stackexchange', 'wikipedia', 'book', 'github']
DOMAINS = dict(zip(ORDER, ['C4', 'CommonCrawl', 'arXiv', 'StackExchange', 'Wikipedia', 'Book', 'GitHub']))
COUNTS = dict(zip(ORDER, [10000, 9640, 17523, 10000, 10000, 171, 203752]))
INDICATORS = {
    'fineweb_edu': '教育价值 · FineWeb',
    'fluency_en_fluent_margin': '流畅性',
    'modernbert_cleanliness_expected': '整洁度',
    'modernbert_readability_expected': '可读性',
    'dsir_books': '目标亲和度 · Books',
    'dsir_wiki': '目标亲和度 · Wikipedia',
    'dsir_math': '目标亲和度 · Math',
    'qurater_writing_style': '写作风格 · QuRating',
    'qurater_facts_trivia': '事实常识 · QuRating',
    'qurater_educational_value': '教育价值 · QuRating',
    'ad_en_no_ad_margin': '无广告倾向',
    'rps_doc_frac_unique_words': '独特词比例',
    'rps_doc_frac_no_alph_words': '无字母词比例（逆向）',
    'rps_doc_frac_chars_top_2gram': '高频二元组占比（逆向）',
    'rps_doc_frac_chars_top_3gram': '高频三元组占比（逆向）',
    'rps_lines_ending_with_terminal_punctution_mark': '句末标点行比例',
}


def setup_style():
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Microsoft YaHei', 'DejaVu Sans'],
        'font.size': 8, 'axes.labelsize': 8, 'xtick.labelsize': 7.5, 'ytick.labelsize': 8,
        'legend.fontsize': 7.3, 'pdf.fonttype': 42, 'svg.fonttype': 'none',
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': .6,
        'axes.unicode_minus': False, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'text.color': INK, 'axes.labelcolor': INK, 'xtick.color': GREY, 'ytick.color': INK,
    })


def header(fig, title, subtitle):
    fig.text(.035, .966, title, fontsize=10.5, weight='bold', va='top')
    fig.text(.975, .962, 'CRITIC–TOPSIS', fontsize=8, color=GREY, ha='right', va='top')
    fig.text(.035, .909, subtitle, fontsize=7.7, color=GREY)


def axis_style(ax, grid='x'):
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#7F8A90')
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', width=.6, length=3)
    ax.grid(axis=grid, color=GRID, linewidth=.55)
    ax.set_axisbelow(True)


def panel(ax, letter, title):
    ax.text(-.015, 1.055, letter, transform=ax.transAxes, weight='bold', fontsize=10)
    ax.annotate(title, (-.015, 1.055), xycoords='axes fraction', xytext=(14, 0),
                textcoords='offset points', fontsize=8.3, annotation_clip=False)


def save_figure(fig, stem, output, pdf_pages, records):
    for t in fig.findobj(matplotlib.text.Text):
        t.set_fontfamily(['Arial', 'Microsoft YaHei'])
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    outside, minimum = [], 100
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text():
            continue
        # Hidden tick labels outside fixed limits do not belong to the rendered figure.
        if t.axes is not None and t.get_clip_on():
            continue
        box = t.get_window_extent(renderer)
        minimum = min(minimum, t.get_fontsize())
        if box.x0 < -.6 or box.y0 < -.6 or box.x1 > fig.bbox.width+.6 or box.y1 > fig.bbox.height+.6:
            outside.append(t.get_text())
    assert not outside, f'{stem}: clipped text {outside}'
    assert minimum >= 7
    for ext in ['png', 'pdf', 'svg', 'tiff']:
        extra = {'pil_kwargs': {'compression': 'tiff_lzw'}} if ext == 'tiff' else {}
        fig.savefig(output / f'{stem}.{ext}', dpi=600, facecolor='white', **extra)
    pdf_pages.savefig(fig, dpi=600, facecolor='white')
    page = re.search(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',
                     (output / f'{stem}.pdf').read_bytes())
    bounds = np.array([float(x) for x in page.groups()])
    size = (bounds[2:] - bounds[:2]) * 25.4 / 72
    np.testing.assert_allclose(size, fig.get_size_inches()*25.4, atol=1e-6)
    records.append({'file_stem': stem, 'size_mm': size.tolist(), 'minimum_font_pt': minimum,
                    'clipped_labels': outside, 'dpi': 600})
    plt.close(fig)
    print(f'Exported {stem}', flush=True)


def load_and_check(repository, output):
    run = repository / 'experiments/runs/q1-critic-topsis-20260924-r01'
    paths = {
        'scores': run / 'artifacts/unique_sample_scores.csv',
        'normalized': repository / 'data/processed/q1_X_norm_v2.csv',
        'comparison': run / 'tables/full_vs_A1.csv',
        'weights': run / 'tables/model_weights.csv',
        'sensitivity': run / 'tables/model_sensitivity.csv',
        'metrics': run / 'metrics.json',
    }
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    assert hashes['scores'] == 'f7148769aac33e8e4e70662e6468f2fb7e05b85dc69901c4b2e33d2ad2b75c22'
    assert hashes['normalized'] == '0c61e680e0ea086976334670166cbccbdf9520541a9eb80aaf3b098a5cfb465a'
    scores = pd.read_csv(paths['scores'], dtype={'record_id': str})
    assert len(scores) == 261086 and scores.record_id.is_unique
    assert scores.groupby('domain').size().to_dict() == COUNTS
    assert scores.kept_in_unique_union.all()
    assert np.isfinite(scores.quality_score).all() and scores.quality_score.between(0, 100).all()
    features = list(INDICATORS)
    matrix = pd.read_csv(paths['normalized'], usecols=['record_id', 'domain']+features,
                         dtype={'record_id': str})
    assert len(matrix) == 272505
    values = matrix[features].to_numpy()
    assert np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all()
    # Compare every duplicated ID's oriented values and domain before keeping one instance.
    repeated = matrix.loc[matrix.record_id.duplicated(keep=False)]
    assert repeated.groupby('record_id')[['domain']+features].nunique(dropna=False).eq(1).all().all()
    unique = matrix.drop_duplicates('record_id').set_index('record_id')
    assert len(unique) == 261086 and set(unique.index) == set(scores.record_id)
    assert (unique.loc[scores.record_id, 'domain'].to_numpy() == scores.domain.to_numpy()).all()
    heat = unique.groupby('domain')[features].mean().loc[ORDER].T
    heat.index.name = 'indicator'
    heat.to_csv(output / 'figure02_domain_indicator_means.csv', float_format='%.12g')
    comp = pd.read_csv(paths['comparison']).set_index('domain').loc[ORDER].copy()
    np.testing.assert_allclose(comp.full_mean, scores.groupby('domain').quality_score.mean().loc[ORDER], atol=1e-10)
    np.testing.assert_allclose(comp.difference_points, comp.full_mean-comp.A1_mean, atol=1e-10)
    assert comp.n_full_unique.to_dict() == COUNTS and comp.n_A1.sum() == 51230
    assert (comp.loc[comp.n_A1 == comp.n_full_unique, 'difference_points'] == 0).all()
    comp['A1_share'] = comp.n_A1 / comp.n_A1.sum()
    comp['full_share'] = comp.n_full_unique / comp.n_full_unique.sum()
    comp['within_component'] = comp.A1_share * (comp.full_mean-comp.A1_mean)
    comp['composition_component'] = (comp.full_share-comp.A1_share) * comp.full_mean
    comp.to_csv(output / 'figure03_04_domain_comparison_and_shares.csv', float_format='%.12g')
    decomposition = {
        'A1_mean': float((comp.A1_share*comp.A1_mean).sum()),
        'standardized_full_mean': float((comp.A1_share*comp.full_mean).sum()),
        'within_domain_component': float(comp.within_component.sum()),
        'composition_component': float(comp.composition_component.sum()),
        'full_mean': float((comp.full_share*comp.full_mean).sum()),
    }
    metrics = json.loads(paths['metrics'].read_text(encoding='utf-8'))
    for key, source_key in [('A1_mean', 'A1_mean'), ('standardized_full_mean', 'A1_share_standardized_full_mean'),
                            ('within_domain_component', 'within_domain_component'),
                            ('composition_component', 'composition_component'), ('full_mean', 'full_unique_mean')]:
        np.testing.assert_allclose(decomposition[key], metrics[source_key], atol=1e-10)
    np.testing.assert_allclose(decomposition['A1_mean']+decomposition['within_domain_component']+
                               decomposition['composition_component'], decomposition['full_mean'], atol=1e-10)
    pd.DataFrame([decomposition]).to_csv(output / 'figure04_decomposition.csv', index=False, float_format='%.12g')
    weights = pd.read_csv(paths['weights']).set_index('indicator').loc[features]
    assert len(weights) == 16 and (weights.distance_or_sum_weight >= 0).all()
    np.testing.assert_allclose(weights.distance_or_sum_weight.sum(), 1, atol=1e-12)
    weights['label'] = weights.index.map(INDICATORS)
    weights['weight_percent'] = weights.distance_or_sum_weight*100
    weights = weights.sort_values('weight_percent', ascending=False)
    weights.to_csv(output / 'figure05_weights.csv', float_format='%.12g')
    sens = pd.read_csv(paths['sensitivity'])
    assert len(sens) == 6 and (sens.n == 261086).all() and (sens.scope == 'unique_union').all()
    baseline = sens.loc[sens.model == 'TOPSIS_CRITIC']
    np.testing.assert_allclose(baseline[['spearman_with_primary', 'mean_abs_rank_gap_pp', 'rank_gap_ge20pp_rate']], [[1, 0, 0]])
    sens = sens.loc[sens.model != 'TOPSIS_CRITIC'].sort_values('mean_abs_rank_gap_pp').copy()
    assert len(sens) == 5 and sens.model.is_unique
    assert sens.spearman_with_primary.between(-1, 1).all() and sens.rank_gap_ge20pp_rate.between(0, 1).all()
    sens['rank_gap_ge20pp_percent'] = 100*sens.rank_gap_ge20pp_rate
    sens.to_csv(output / 'figure06_sensitivity.csv', index=False, float_format='%.12g')
    integrity = {'input_sha256': hashes, 'source_paths': {k: str(v.relative_to(repository)) for k,v in paths.items()},
                 'file_records': len(matrix), 'unique_records': len(unique), 'duplicate_records_removed': len(matrix)-len(unique),
                 'duplicate_values_agree': True, 'unique_ids_and_domains_match_scores': True,
                 'finite_normalized_0_to_1': True, 'domain_counts': COUNTS, 'no_sampling': True,
                 'model_refitted': False, 'decomposition_matches_saved_metrics': True,
                 'self_comparison_omitted_from_figure06_only': 'TOPSIS_CRITIC (1, 0, 0)', 'fit_n': 40919}
    return heat, comp, decomposition, weights, sens, integrity


def figure02(heat):
    fig = plt.figure(figsize=(7.2047244094, 5.9842519685))  # 183 x 152 mm
    header(fig, '各领域的质量指标画像', '16 项指标  /  全量去重 N = 261,086  /  统一为“越高越好”')
    ax = fig.add_axes([.335, .212, .605, .646])
    cmap = LinearSegmentedColormap.from_list('quality_teal', ['#F5F8F7', '#D5E5E3', '#8BB3B7', '#527F88', '#234954'])
    im = ax.imshow(heat.to_numpy(), cmap=cmap, vmin=0, vmax=1, aspect='auto', interpolation='nearest')
    ax.set_yticks(np.arange(16), [INDICATORS[k] for k in heat.index], fontsize=8)
    ax.set_xticks(np.arange(7), ['C4', 'Common\nCrawl', 'arXiv', 'Stack\nExchange', 'Wikipedia', 'Book', 'GitHub'], fontsize=7.5)
    ax.tick_params(axis='both', length=0, pad=6)
    ax.set_xticks(np.arange(-.5, 7, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 16, 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=.7)
    ax.tick_params(which='minor', length=0)
    for spine in ax.spines.values(): spine.set_visible(False)
    for (i,j), value in np.ndenumerate(heat.to_numpy()):
        ax.text(j, i, f'{value:.2f}', ha='center', va='center', fontsize=7.4,
                color='white' if value >= .65 else INK)
    cax = fig.add_axes([.46, .105, .355, .016])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal', ticks=[0, .25, .5, .75, 1])
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2, labelsize=7)
    cb.set_label('方向统一、归一化后的指标均值', fontsize=7.5, labelpad=3)
    fig.text(.035, .025, '全图共用 0–1 色标；负向指标已逆向。颜色不表示指标对 TOPSIS 总分的可加贡献。', fontsize=7, color=GREY)
    return fig


def figure03(comp):
    fig = plt.figure(figsize=(7.2047244094, 4.6456692913))  # 183 x 118 mm
    header(fig, '扩展前后，各领域评分变化多大？', 'A1：51,230 条  →  全量去重：261,086 条  /  同一套 A1 拟合参数')
    left = fig.add_axes([.245, .215, .415, .575])
    right = fig.add_axes([.775, .215, .18, .575])
    ys = np.arange(7)[::-1]
    for y, (domain, r) in zip(ys, comp.iterrows()):
        left.plot([r.A1_mean, r.full_mean], [y, y], color=GREY, linewidth=1)
        left.plot(r.A1_mean, y, 'o', mfc='white', mec=GREY, ms=6, mew=1, zorder=3)
        left.plot(r.full_mean, y, 'D', mfc=TEAL, mec='white', ms=3.5, mew=.35, zorder=4)
        left.text(r.full_mean+1.05, y, f'{r.full_mean:.2f}', va='center', fontsize=8)
        left.text(-.055, y+.09, DOMAINS[domain], transform=left.get_yaxis_transform(), ha='right', va='center', fontsize=8.4)
        left.text(-.055, y-.22, f'{int(r.n_A1):,} → {int(r.n_full_unique):,}', transform=left.get_yaxis_transform(), ha='right', va='center', fontsize=7, color=GREY)
        colour = WARM if r.difference_points < -1e-10 else GREY
        right.hlines(y, min(0, r.difference_points), max(0, r.difference_points), color=colour, linewidth=1)
        right.plot(r.difference_points, y, 'o', color=colour, ms=4)
        right.annotate(f'{r.difference_points:+.3f}' if abs(r.difference_points)>1e-10 else '0.000',
                       (r.difference_points, y), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=7.4, color=colour)
    for ax in [left, right]:
        axis_style(ax); ax.set_ylim(-.6, 6.6); ax.set_yticks([])
    left.set_xlim(45, 75); left.set_xticks([45, 55, 65, 75]); left.set_xlabel('领域平均质量评分（0–100）', labelpad=7)
    right.set_xlim(-.45, .10); right.set_xticks([-.4, -.2, 0]); right.axvline(0, color='#ABB4B8', lw=.7)
    right.set_xlabel('全量 − A1（分）', labelpad=7)
    panel(left, 'a', '均分与样本量'); panel(right, 'b', '精确差值')
    handles = [Line2D([0],[0], marker='o', mfc='white', mec=GREY, ms=5, ls='none', label='A1'),
               Line2D([0],[0], marker='D', color=TEAL, ms=3.5, ls='none', label='全量去重')]
    fig.legend(handles=handles, loc='center', bbox_to_anchor=(.47, .859), ncol=2, frameon=False, handletextpad=.45)
    fig.text(.035, .078, '仅 arXiv 与 GitHub 增加记录；其余 5 个领域的样本未扩充，因此分数相同。', fontsize=7, color=GREY)
    fig.text(.035, .035, '均分保留两位小数，差值保留三位；未四舍五入的数据见配套 CSV。', fontsize=7, color=GREY)
    return fig


def figure04(comp, d):
    fig = plt.figure(figsize=(7.2047244094, 4.9212598425))  # 183 x 125 mm
    header(fig, '总体均分下降，主要来自领域构成变化', 'A1 → 全量去重  /  样本加权均分下降 6.715 分  /  描述性分解')
    left = fig.add_axes([.173, .263, .342, .527])
    right = fig.add_axes([.635, .263, .33, .527])
    ys = np.arange(7)[::-1]
    left.barh(ys+.14, comp.A1_share*100, height=.23, color='#CDD3D5', edgecolor='none')
    left.barh(ys-.14, comp.full_share*100, height=.23, color=TEAL, edgecolor='none')
    for y, (_, r) in zip(ys, comp.iterrows()):
        left.text(r.A1_share*100+1.3, y+.14, f'{r.A1_share*100:.2f}', fontsize=7, va='center', color=GREY)
        left.text(r.full_share*100+1.3, y-.14, f'{r.full_share*100:.2f}', fontsize=7, va='center', color=TEAL)
    left.set_yticks(ys, [DOMAINS[k] for k in comp.index], fontsize=7.8)
    left.set_xlim(0, 99); left.set_xticks([0,20,40,60,80]); left.set_ylim(-.6, 6.6)
    left.set_xlabel('样本占比（%）', labelpad=7); axis_style(left)
    panel(left, 'a', '各领域的样本占比')
    fig.legend(handles=[Patch(facecolor='#CDD3D5', label='A1'), Patch(facecolor=TEAL, label='全量去重')],
               loc='center', bbox_to_anchor=(.32, .861), ncol=2, frameon=False, handlelength=1)
    a, mid, end = d['A1_mean'], d['standardized_full_mean'], d['full_mean']
    right.bar(0, a, width=.53, color='#CDD3D5')
    right.bar(1, a-mid, bottom=mid, width=.53, color=WARM, linewidth=.8, edgecolor=WARM)
    right.bar(2, mid-end, bottom=end, width=.53, color=WARM)
    right.bar(3, end, width=.53, color=TEAL)
    for i, height in enumerate([a, mid, end]):
        right.plot([i+.27, i+.73], [height,height], color=GREY, lw=.6, ls='--')
    right.text(0, a+2.5, f'{a:.3f}', ha='center', fontsize=7.5)
    right.annotate(f'{d["within_domain_component"]:.3f}', (1, mid), xytext=(1, 71), textcoords='data',
                   ha='center', fontsize=7.5, color=WARM, arrowprops={'arrowstyle':'-', 'color':WARM, 'lw':.6})
    right.text(2, mid+2.5, f'{d["composition_component"]:.3f}', ha='center', fontsize=7.5, color=WARM)
    right.text(3, end+2.5, f'{end:.3f}', ha='center', fontsize=7.5, color=TEAL)
    right.set_xticks(range(4), ['A1\n均分', '域内\n变化', '构成\n变化', '全量\n均分'], fontsize=7.5)
    right.set_xlim(-.6, 3.6); right.set_ylim(0, 78); right.set_yticks([0,20,40,60])
    right.set_ylabel('质量评分（分）', labelpad=5); axis_style(right, grid='y')
    panel(right, 'b', '总体均分的变化分解')
    fig.text(.173, .158, 'GitHub 占比：19.52% → 78.04%', fontsize=8, color=TEAL)
    fig.text(.035, .090, '分解顺序：先固定 A1 领域占比、替换领域均分，再替换为全量领域占比。', fontsize=7, color=GREY)
    fig.text(.035, .044, '域内项 = Σ pA1(μ全量 − μA1)；构成项 = Σ(p全量 − pA1)μ全量。此分解不代表因果效应。', fontsize=7, color=GREY)
    return fig


def figure05(weights):
    fig = plt.figure(figsize=(7.2047244094, 5.6299212598))  # 183 x 143 mm
    header(fig, '16 项质量指标的 CRITIC 权重', '仅以 A1 拟合集估计  /  n = 40,919  /  权重合计 100%')
    ax = fig.add_axes([.343, .185, .59, .668])
    ys = np.arange(16)[::-1]
    ax.barh(ys, weights.weight_percent, height=.55, color=TEAL)
    for y, v in zip(ys, weights.weight_percent):
        ax.text(v+.14, y, f'{v:.2f}%', va='center', fontsize=7.6, zorder=4,
                bbox={'facecolor':'white', 'edgecolor':'none', 'pad':.5})
    ax.set_yticks(ys, weights.label, fontsize=8)
    ax.set_ylim(-.65, 15.65); ax.set_xlim(0, 10); ax.set_xticks([0,2,4,6,8,10])
    axis_style(ax); ax.set_xlabel('CRITIC 权重（%）', labelpad=7)
    ax.axvline(6.25, color=WARM, ls=(0,(3,3)), lw=.85)
    ax.text(6.25, 15.95, '等权参考 6.25%', color=WARM, fontsize=7.3, ha='center')
    fig.text(.035, .077, 'CRITIC 结合拟合样本的指标离散程度与相关结构；图中为 TOPSIS 距离中使用的权重。', fontsize=7, color=GREY)
    fig.text(.035, .035, '权重不等于因果重要性，也不能直接解释为各指标对总分的可加贡献。', fontsize=7, color=GREY)
    return fig


def figure06(sens):
    fig = plt.figure(figsize=(7.2047244094, 4.7244094488))  # 183 x 120 mm
    header(fig, '评价方案变化对样本排序的影响', '5 种变体均与主模型比较  /  全量去重 N = 261,086  /  描述性敏感性分析')
    labels = {'CRITIC_SUM': 'CRITIC 加权和', 'TOPSIS_WEIGHT_SQUARED': 'TOPSIS 权重平方',
              'EQUAL_SUM': '等权加和', 'TOPSIS_NO_DSIR': 'TOPSIS 去除 DSIR', 'TOPSIS_NO_3_COST': 'TOPSIS 去除 3 项负向指标'}
    axes = [fig.add_axes([.295,.265,.183,.495]), fig.add_axes([.54,.265,.183,.495]), fig.add_axes([.787,.265,.183,.495])]
    keys = ['spearman_with_primary', 'mean_abs_rank_gap_pp', 'rank_gap_ge20pp_percent']
    limits = [(.96,1.0015), (0,5.8), (0,3.4)]
    ticks = [[.96,.98,1.00],[0,2,4],[0,1,2,3]]
    titles = ['排序相关性', '平均排名变动', '大幅变动占比']
    xlabels = ['Spearman ρ', '百分点', '样本占比（%）']
    ys = np.arange(5)[::-1]
    for j, ax in enumerate(axes):
        panel(ax, chr(97+j), titles[j])
        for y, (_, row) in zip(ys, sens.iterrows()):
            value = row[keys[j]]
            colour = WARM if row.model == 'TOPSIS_NO_3_COST' else TEAL
            # Correlation uses points on an explicitly restricted axis; change panels start at zero.
            if j > 0: ax.hlines(y, 0, value, color=PALE if colour == TEAL else '#E5CBBB', lw=1.6)
            ax.plot(value, y, 'o', ms=4.3, color=colour)
            fmt = f'{value:.4f}' if j==0 else f'{value:.2f}'
            align = 'right' if (j==0 and value>.99) else ('left' if j==0 else 'center')
            ax.annotate(fmt, (value,y), xytext=(0,8), textcoords='offset points', fontsize=7.3, ha=align, color=colour)
        ax.set_ylim(-.5, 4.65); ax.set_xlim(*limits[j]); ax.set_xticks(ticks[j]); ax.set_yticks([])
        ax.set_xlabel(xlabels[j], labelpad=8); axis_style(ax)
    for y, (_,row) in zip(ys, sens.iterrows()):
        axes[0].text(-.11, y, labels[row.model], transform=axes[0].get_yaxis_transform(), ha='right', va='center', fontsize=7.7,
                     color=WARM if row.model=='TOPSIS_NO_3_COST' else INK)
    fig.text(.295,.140,'“大幅变动”：百分位排名的绝对变化 ≥ 20 个百分点。',fontsize=7,color=GREY)
    fig.text(.035,.095,'主模型：CRITIC 加权距离 TOPSIS；自身对照恒为 1 / 0 / 0，未重复绘制。',fontsize=7,color=GREY)
    fig.text(.035,.046,'模型间差异用于敏感性检验，不代表准确率，也不等同于质量指标之间的冲突。',fontsize=7,color=GREY)
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    setup_style()
    heat, comp, decomposition, weights, sensitivity, integrity = load_and_check(args.repository, args.output)
    records = []
    with PdfPages(args.output / 'figures02_06_nature.pdf') as pages:
        for stem, figure in [
            ('figure02_indicator_heatmap_nature', lambda: figure02(heat)),
            ('figure03_A1_full_comparison_nature', lambda: figure03(comp)),
            ('figure04_composition_decomposition_nature', lambda: figure04(comp, decomposition)),
            ('figure05_critic_weights_nature', lambda: figure05(weights)),
            ('figure06_model_sensitivity_nature', lambda: figure06(sensitivity)),
        ]:
            save_figure(figure(), stem, args.output, pages, records)
    integrity['figures'] = records
    integrity['outputs_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir()
                                   if p.suffix in ['.png','.pdf','.svg','.tiff','.csv']}
    (args.output / 'figure_manifest.json').write_text(json.dumps(integrity, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Completed: all five figures, source tables, PDF collection, and manifest.', flush=True)


if __name__ == '__main__':
    main()
