# Q1 mixture collinearity audit

- run_id: `q1-mixture-collinearity-20260924-r01`
- task: `T-Q1-003-MIXTURE`
- source: `data/origin/real_attachments/A_data_value/regmix_tables`
- fit reference: A4/A5; A6-A11 validation; A12-A15 extrapolation/sensitivity
- method: closure/rank audit, all-reference sensitivity, standardized SVD condition numbers, VIF, Helmert-ilr zero-replacement sensitivity, quadratic feature rank/conditioning

The source attachments were read only. The structured result is in `metrics.json`; the method is frozen in `config.yaml`.

The most important interpretation is that the 17-column rank loss is structural simplex closure. Reference-coded VIF depends strongly on the omitted component, while Aitchison diagnostics depend on zero replacement. Quadratic Ridge is therefore an exploratory stabilizer, not evidence that the design contains enough information for 152 free second-order effects.
