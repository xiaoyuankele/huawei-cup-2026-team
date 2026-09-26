# Q1 to A4-A15 soft domain-transfer matrix

This is a separated exploratory run. It uses the new repository's v2 semantic-prior weights as a reference, but recalculates all quality-domain scores from the current workspace's `q1-critic-topsis-20260925-r01` A1/full candidate run. It does not modify A16, the official Q1 score, or any Q2 fit.

The 17-by-7 matrix `W` keeps the six A16 direct/near-direct rows as one-hot rows and gives the eleven inferred rows candidate anchor mixtures. `quality_score_soft_proxy_0_100` is a projected proxy; the low/high columns are the candidate-anchor min/max scenario range, not confidence intervals.

Status: `EXPLORATORY_TRANSFER_MATRIX_REVIEW`.
