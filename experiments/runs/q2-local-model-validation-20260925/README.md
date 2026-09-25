> 历史研究记录：保留原阶段结论与时态。当前结果、版本关系和交付状态见 [研究总览](../../../docs/research/q2/README.md)。

# Q2 local model validation

Run ID: `q2-local-model-validation-20260925`

This run follows the block-missing validation plan:

- Scale: fit only on real B1 and evaluate leave-one-size-out plus B2/B4/B5.
- Mixture: fit first-order ridge models on real A4/A5 and evaluate A6/A7, A8/A9, A10/A11; A12-A15 remain extrapolation audits.
- Quality: fit additive log-N-D-Q checks between B6 and B7; B8 is a direction-conflict audit.

The outputs are predictive checks for separate components. They are not evidence that a synthetic Cartesian product is an observed joint sample.
