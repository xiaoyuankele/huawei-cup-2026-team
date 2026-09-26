> 历史研究记录：保留原阶段结论与时态。当前结果、版本关系和交付状态见 [研究总览](../../../docs/research/q2/README.md)。

# Q2 quality-scaling linkage audit

- run_id: `q2-quality-scaling-linkage-20260925`
- status: `PLAN / REVIEW_REQUIRED`
- purpose: connect the Q1 quality/mapping handoff to Q2 scaling-law data without a false row-level join
- plan: `docs/problem/q2-quality-scaling-linkage-plan.md`
- audit: `quality-direction-audit.csv`

## Inputs

- Q1 primary score: `experiments/runs/q1-critic-topsis-20260924-r01/tables/domain_scores.csv`
- Q1 soft mapping: `experiments/runs/quality-mapping-20260925-r02-soft-handoff/tables/scored_wide_v2_soft.csv`
- Q2 native quality experiments: B6/B7/B8 under the controlled `real_attachments/B_scaling_laws/` root

## Decision boundary

B1 remains the scale baseline. B6/B7 are the quality-calibration branch. B8 is isolated as a direction-conflict audit because its within-(N,D) quality direction is opposite to B6/B7. No unified quality coefficient is fitted across B6--B8 until the generator/semantic direction is explained.
