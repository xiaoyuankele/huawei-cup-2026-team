# Q1 finite perturbation effect stability exploratory run

- Run ID: `q1-effect-stability-20260924-r01`
- Fit models: ilr Ridge (`alpha=10`) and quadratic Ridge (`alpha=10`), selected by `q1-model-benchmark-20260924-r01`
- Fit data: A4/A5 only
- External input check: A6/A7 predictions without refitting
- Perturbation: transfer `delta=0.01` from source domain to destination domain
- Support guard: perturbed coordinates remain within A4 marginal ranges
- Uncertainty: 300 row-bootstrap replicates for each destination-source-target effect

The quadratic Ridge model is the strongest predictive candidate in the benchmark, but its finite-perturbation directions agree with linear Ridge only about 0.69–0.71 of the time across targets and datasets. This means predictive improvement does not yet establish stable, interpretable domain-combination effects.

These are model-based finite perturbations, not causal interventions. The marginal-range guard is not a convex-hull guarantee, and no optimum mixture is produced.

## Outputs

- `finite_effects.csv`: destination-source-target effects and bootstrap intervals
- `effect_direction_summary.csv`: direction proportions and model sign agreement
- `metrics.json`: protocol and claim limitations
