# Q1 mixture audit run

This run is a read-only audit and baseline, not a final domain model. It reads A4-A15, checks index alignment, composition sums, zero cells, exact duplicate mixture designs and simple support distances, then evaluates a simplex-aware linear baseline fitted only on A4/A5. It reports both absolute metrics and a centered relative diagnostic; the latter removes each scale's target mean only for assessing composition ranking, and is not an absolute Loss forecast.

- Run ID: `q1-mixture-audit-20260924-r01`
- Fit: A4/A5 only
- Validation: A6/A11
- Extrapolation/sensitivity: A12/A15
- Script: `scripts/q1_mixture_audit.py`
- Output: `metrics.json`
- Human review: required before any paper claim
