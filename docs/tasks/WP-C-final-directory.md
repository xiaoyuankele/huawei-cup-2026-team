# WP-C 本地Git交付目录

分支`wp/ACTOR-3/WP-C`；状态REVIEW_BLOCKED。原始数据不进入Git。

后续公开的逐条候选综合评分表位于`experiments/runs/q1-conflict-trial-20260924-r01/results/q1_candidate_scores.csv`，含261086个唯一ID及`Q_candidate`分数。只公开评分所需五列；导出清单位于同目录的`q1_candidate_scores.manifest.json`，脚本为`scripts/export_q1_candidate_scores.py`。评分状态为`candidate_not_validated`，不代表正式模型采纳。

## 纳入本地提交

```text
README-WP-C.md
configs/q1-conflict-trial.json
data/manifests/q1-conflict-inputs.json
docs/decisions/q1-conflict-analysis.md
docs/decisions/q1-conflict-data-dictionary.md
docs/decisions/q1-conflict-self-check.md
docs/decisions/q1-figure-audit.md
docs/decisions/q1-resolution-proposal.md
docs/decisions/q1-validation-report.md
docs/tasks/G2-record-required-fields.json
docs/tasks/T-Q1-005-local.yml
docs/tasks/T-Q1-005.yml
docs/tasks/T-Q1-006-local.yml
docs/tasks/T-Q1-006.yml
docs/tasks/T-Q1-007-local.yml
docs/tasks/T-Q1-007.yml
docs/tasks/T-Q1-008-local.yml
docs/tasks/T-Q1-008.yml
docs/tasks/WP-C-delivery.json
docs/tasks/验收对照清单.md
experiments/index.csv
experiments/runs/q1-conflict-trial-20260924-r01/command.txt
experiments/runs/q1-conflict-trial-20260924-r01/inputs/config.json
experiments/runs/q1-conflict-trial-20260924-r01/inputs/normalization_stats.json
experiments/runs/q1-conflict-trial-20260924-r01/inputs/q1_domain_scores.csv
experiments/runs/q1-conflict-trial-20260924-r01/inputs/q1_model.json
experiments/runs/q1-conflict-trial-20260924-r01/metrics.json
experiments/runs/q1-conflict-trial-20260924-r01/results/composition_decomposition.json
experiments/runs/q1-conflict-trial-20260924-r01/results/conflict_pairs.csv
experiments/runs/q1-conflict-trial-20260924-r01/results/conflict_summary.csv
experiments/runs/q1-conflict-trial-20260924-r01/results/lambda_sensitivity.csv
experiments/runs/q1-conflict-trial-20260924-r01/results/score_summary.csv
experiments/runs/q1-conflict-trial-20260924-r01/results/threshold_sensitivity.csv
experiments/runs/q1-conflict-trial-20260924-r01/results/thresholds_and_weights.csv
experiments/runs/q1-conflict-trial-20260924-r01/run_manifest.json
experiments/runs/q1-conflict-trial-20260924-r01/validation/checks.json
experiments/runs/q1-conflict-trial-20260924-r01/validation/q1_reproduction.csv
experiments/runs/q1-conflict-trial-20260924-r01/validation/synthetic_validation_tests.json
governance/ai-use-log.csv
governance/feedback/FB-20260924-WPC-G2-001.json
governance/feedback/FB-20260924-WPC-MODEL-002.json
governance/feedback/index.csv
governance/prompts/runs/PR-20260924-WPC-LOCAL-001.json
paper/claim-ledger-candidates.csv
paper/figures/fig1_domain_conflict.pdf
paper/figures/fig1_domain_conflict.png
paper/figures/fig1_domain_conflict.svg
paper/figures/fig2_threshold_sensitivity.pdf
paper/figures/fig2_threshold_sensitivity.png
paper/figures/fig2_threshold_sensitivity.svg
paper/figures/fig3_compensation_sensitivity.pdf
paper/figures/fig3_compensation_sensitivity.png
paper/figures/fig3_compensation_sensitivity.svg
paper/figures/figure_manifest.json
paper/sections/drafts/q1-conflict-results.md
paper/sections/drafts/q1-conflict-results.tex
paper/tables/q1_conflict_coverage.tex
paper/tables/q1_conflict_thresholds.tex
paper/tables/q1_resolution_scores.tex
requirements-q1-conflict.txt
scripts/plot_q1_conflict.py
scripts/q1_conflict_analysis.py
scripts/q1_conflict_validation.py
scripts/rebuild_q1_conflict_inputs.py
scripts/render_q1_conflict_figures.mjs
scripts/verify_q1_conflict_delivery.py
docs/tasks/WP-C-file-manifest.json
docs/tasks/WP-C-final-directory.md
```

## 本地保留但由Git忽略

```text
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/case_scores.csv
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/case_selection.csv
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/case_texts.json
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/normalized_records.csv.gz
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/record_index.csv.gz
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/review_sample_unlabeled.csv
experiments/runs/q1-conflict-trial-20260924-r01/artifacts/sample_results.csv.gz
```
