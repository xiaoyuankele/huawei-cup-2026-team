# Quality mapping run: quality-mapping-20260925-r02-soft-handoff

Status: `REVIEW` / `needs_human_review: true`

This run is the soft-mapping track and is kept separate from the teammate's mapping/distribution audit. It does not overwrite or replace the legacy v1 tables.

## Outputs

- `tables/mapping_v2_soft.csv`: 17 A16 mixture domains with candidate quality domains and semantic-prior weights.
- `tables/scored_wide_v2_soft.csv`: 1,214 A4-A15 mixture/Loss rows with v2 scores and ranges.
- `tables/scored_long_v2_soft.csv`: 20,638 row-domain contributions.
- `tables/mapping_v1_hard.csv`, `tables/scored_wide_v1_hard.csv`, `tables/scored_long_v1_hard.csv`: compatibility outputs only.
- `tables/quality_domain_scores.csv`: 7 quality-domain scores from A1-A3.
- `tables/v1_v2_comparison.csv`: dataset-level version comparison.
- `reports/mapping_soft_flow.md`: process architecture for handoff and paper use.

## Interpretation

The six direct/near-direct A16 mappings remain one-to-one. Eleven inferred mappings use candidate-domain mixtures; weights are semantic priors, not observed proportions or confidence probabilities. The soft range is the minimum-to-maximum candidate-domain score, not a statistical confidence interval.

The score is deterministic from the mixture proportions and fixed domain scores. It is a descriptive quality axis and must not be interpreted as an independent causal variable when all 17 proportions are already included in a model. A12-A15 remain scale-extrapolation data and are not tuning inputs.

## Reproduction

Use `config.yaml` and `command.txt`. The scripts accept `QUALITY_ATTACHMENTS_ROOT` and `QUALITY_MAPPING_OUTPUT_DIR`; raw attachment files are referenced through the repository's existing `data/manifests/q1_raw.yaml` contract but are not committed.
