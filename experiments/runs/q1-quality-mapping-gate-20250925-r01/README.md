# Q1 quality-score and 17-domain mapping gate

- `run_id`: `q1-quality-mapping-gate-20250925-r01`
- `task_id`: `T-Q1-004`
- `status`: `REVIEW_BLOCKED_FOR_FINAL_ACCEPTANCE`
- `script`: `scripts/q1_quality_mapping_gate.py`
- `metrics`: `metrics.json`
- `mapping_confirmation`: `six_mapping_confirmation.csv`
- `mapping_confirmation_metrics`: `six_mapping_confirmation_metrics.json`
- `inferred_mapping_gap`: `inferred_mapping_gap.csv`
- `acceptance_checklist`: `q1_acceptance_checklist.json`

This is a read-only gate audit. It streams the three quality-score JSONL/XZ
attachments, checks parse errors, duplicate keys, duplicate IDs, non-finite
values, and pairwise ID overlap, then audits the 17-row domain mapping table.
It does not rewrite raw data, score matrices, or mapping rows.

The sample set is present and structurally parseable: A1 has 51,230 rows, A2
17,523, and A3 203,752. There are no parse errors, duplicate JSON keys, or
within-file duplicate IDs. Non-finite values are present in 18 A1 rows and one
A3 row; the Q1 contract retains these rows and reports the affected component
as missing, so they are a review item rather than a silent imputation.

The overlap audit finds 1,419 A1/A2 IDs and 10,000 A1/A3 IDs. Therefore A2/A3
are useful same-family migration checks but cannot be presented as independent
truth. The 17-domain mapping table has 3 direct rows, 3 near-direct rows, and
11 inferred rows with no quality-domain assignment.

The resulting gate is:

- Step 1 can advance to a formal review package, but the final scalar Q is not
  accepted. The preprocessing manifest remains `REVIEW`, the scoring delivery
  remains `LOCAL_RESULT_PENDING_TEAM_REVIEW`, pending indicator directions and
  weights remain unresolved, and the external files are not independent truth.
- Step 2 can advance for confirmation of the six direct/near-direct mappings,
  but full 17-domain mapping remains blocked until the 11 inferred rows have
  domain-specific evidence and validation criteria.

The six supported rows cover 41,230 of the 51,230 A1 records (80.48% of the
available sample rows), while covering only 6 of the 17 mixture domains
(35.29%). Sample support is adequate for a bounded review, but it does not
justify assigning scores to the eleven unmapped mixture domains.

The candidate score also has 21/21 numerical and reproducibility checks passed,
but nine indicator directions remain withheld and the semantic poisoning audit
is still open. The checklist therefore records `CANDIDATE_REVIEW_ONLY`.
