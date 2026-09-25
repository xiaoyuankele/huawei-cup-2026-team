> 历史研究记录：保留原阶段结论与时态。当前结果、版本关系和交付状态见 [研究总览](../../../docs/research/q2/README.md)。

# Q2 generalized scaling model v1

Status: CONDITIONAL_SCENARIO. B1 power law + B7 linear quality response + A4/A5 mixture residual after training-only regression on Q1 quality.

Read [the model report](../../../docs/problem/q2-generalized-scaling-model-v1.md) for equations, parameters, validation and limitations.

Reproduce from repository root: `python scripts/q2_finalize_model.py`.

The scenario table retains N, D, Q and all 17 mixture columns. Its Loss is a prediction, never an observed training target. Quality mappings and cross-source transfer strengths remain assumptions. Prior Q1 review statuses are inherited. No raw files are modified.
