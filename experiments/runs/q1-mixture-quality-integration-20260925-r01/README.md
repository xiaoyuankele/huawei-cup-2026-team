# Q1 mixture-quality integration

This run aggregates sample-level A1 quality scores by quality domain and joins them to the A4-A15 mixture/scale feature table through the A16 domain mapping. The wide table has one row per mixture sample; the long table preserves domain-level contributions. Unmapped mixture domains remain explicit and are not imputed. The mapped quality is a partial proxy pending team review.
