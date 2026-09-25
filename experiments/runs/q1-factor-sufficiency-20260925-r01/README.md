# Q1 factor sufficiency role-change audit

- Run ID: `q1-factor-sufficiency-20260925-r01`
- Adaptation data: A4/A5, A6/A7 and A8/A9
- Unseen-scale holdout: A10/A11
- Extrapolation diagnostics: A12-A15
- Model: standardized multi-output Ridge
- Scale representation: `log10_scale` and optional squared term
- Composition-derived descriptors: entropy, concentration and active-domain count

This run deliberately changes the roles of A6/A7 and A8/A9. It is a factor-sufficiency audit, not official external validation.

| feature block | leave-one-dataset-out mean R2 | A10 absolute R2 | A10 MAE | A12 MAE | A14 MAE |
|---|---:|---:|---:|---:|---:|
| p only | -2.748 | -465.099 | 2.587 | 3.164 | 3.547 |
| p + linear scale | -2.085 | -17.946 | 0.618 | 0.829 | 0.927 |
| p + scale squared | -2.085 | -16.686 | 0.572 | 0.835 | 1.099 |
| p + scale interaction | -2.063 | -17.159 | 0.542 | 0.790 | 0.945 |
| p + scale + diversity | -1.913 | -19.725 | 0.532 | 0.873 | 1.078 |
| p + scale + diversity interaction | -1.696 | -10.038 | 0.397 | 0.910 | 1.236 |

The richer factor block improves the 1B unseen-scale holdout but degrades the 10B/70B extrapolation diagnostics. This indicates that the current scale relation is not stable across intervals; adding composition-derived descriptors alone does not solve the extrapolation problem.

The result supports a factor-sufficiency limitation: quality score `Q`, target-specific scaling structure, training-process metadata, or a redesigned multi-scale experiment may be required. Entropy, concentration and active-domain count are derived from the mixture and are not independent observations.
