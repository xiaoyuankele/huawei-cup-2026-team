> 历史研究记录：保留原阶段结论与时态。当前结果、版本关系和交付状态见 [研究总览](../../../docs/research/q2/README.md)。

# Q2 calibration and sensitivity audit

This run quantifies source offsets and quality-axis uncertainty without treating post-hoc offsets as new observations.

## B source offsets

The B1 log-N-D baseline has substantial source shifts on B2/B4/B5. The raw signed-error offsets are approximately -1.368 (B2), -0.475 (B4), and -0.199 (B5), so a post-hoc additive correction would be about +1.368, +0.475, and +0.199 respectively. Median or mean offset correction is reported only as a diagnostic. It cannot be applied to an unseen source without a bridge observation.

## A scale shift

The common A6/A8 mixtures provide a direct within-A scale comparison. The observed A8 minus A6 mean shift across 13 domains is -1.4594; the negative share is 1.000. This supports a scale shift, but does not recover B's token-count coordinate.

## Q-axis sensitivity

The Q1 TOPSIS and soft axes have correlation -0.6516. Their differences are propagated through the scenario model in `Q_axis_sensitivity.csv`. This is a mapping sensitivity result, not an empirical calibration.

For the four hundred paired scenario rows, the two Q-axis choices change `scale_plus_Q` by a median absolute amount of about 0.121 Loss units (range 0.032–0.203). `scale_only` and `scale_plus_p` are unchanged because they do not use the selected Q axis.
