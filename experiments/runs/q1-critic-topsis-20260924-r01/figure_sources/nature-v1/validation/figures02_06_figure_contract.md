# Q1 figures 2–6 · Nature-style figure contract

All figures inherit the approved figure 1: Python/matplotlib, white canvas, Arial + Microsoft YaHei, restrained teal and charcoal, warm accent only for changes or a specific sensitivity result. All figures are 183 mm wide; heights vary to preserve readable 7 pt or larger labels. Export PNG/TIFF at 600 dpi and PDF/SVG with editable text. This is a local review set, not an automatic GitHub or manuscript update.

## Data contract

Use A1+A2+A3, all 272505 file records and 261086 unique IDs; reject missing/nonfinite selected features, verify repeated IDs agree on domain and all 16 oriented values, and match unique IDs to the existing scoring run. No aesthetic sampling or additional exclusions. Source model, parameters, direction rules and score definitions remain unchanged. Histories and raw files remain read-only. Source-data exports contain aggregates, not sample IDs.

## Figure-specific contracts

| Figure | Claim/question | Evidence and archetype | Statistical boundary |
|---|---|---|---|
| 2 | How do the 16 indicator profiles differ by domain? | Single heatmap, 16 rows × 7 domains, oriented normalized means, common 0–1 scale, every cell annotated. Quantitative grid. | No per-row rescaling; no interpretation as additive TOPSIS contribution or indicator-conflict diagnosis. |
| 3 | How much do domain scores change from A1 to the full union? | Paired domain means plus an aligned difference panel; all seven domains and n before/after. Quantitative comparison. | Descriptive means, not confidence intervals; five domains have no new records. Replaces the previous figure 3 in style, not calculations. |
| 4 | Why is the overall full-union score lower? | Domain proportions plus a waterfall decomposing A1 mean → full-domain means at A1 proportions → actual full-union mean. Quantitative composite. | Sequence-specific descriptive decomposition. Within-domain = sum(p_A1 * (mean_full−mean_A1)); composition = sum((p_full−p_A1) * mean_full). Not a causal attribution. |
| 5 | How are the 16 indicator weights allocated? | Sorted horizontal bars with exact percentages and an equal-weight 6.25% reference. Single quantitative panel. | CRITIC fit only on A1 fit n=40919; weights are neither causal importance nor a validated universal quality ranking. |
| 6 | How sensitive are rankings to method and indicator choices? | Five variants compared with the primary model: Spearman correlation, mean absolute percentile-rank change, and rate with change ≥20 percentage points. Aligned three-panel grid. | Full union n=261086; reference self-comparison is identically 1/0/0 and is omitted explicitly. Descriptive sensitivity, not accuracy or indicator-conflict resolution. |

## Validation

Assert input versions, counts, unique IDs, duplicate-value agreement, and all-domain coverage. Independently recompute figure 3 deltas and figure 4 weights/decomposition against the saved metrics. Assert weights nonnegative and sum to one. Verify figure 6 row counts/ranges, retain all five variants, and label its threshold as descriptive. Check each panel, label/annotation and entire canvas visually; run source preflight and PDF font audit, independently verify PDF sizes. No fabricated p-values, uncertainty intervals, quality tiers or review acceptance.
