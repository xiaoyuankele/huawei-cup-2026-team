# Q1 unified model benchmark exploratory run

- Run ID: `q1-model-benchmark-20260924-r01`
- Task: `T-Q1-003-MIXTURE`
- Fit role: A4/A5 only; repeated three-seed five-fold cross-validation for model and hyperparameter selection
- External validation: A6/A7 at the same 1M scale
- Cross-scale diagnostics: A8/A9 and A10/A11
- Extrapolation diagnostics: A12-A15
- Feature representation: normalized composition, multiplicative zero replacement with `epsilon=1e-4`, Helmert-ilr (16 predictors)
- Quality score `Q`: excluded because domain-level `q_i` is not frozen

## Compared families

- mean baseline
- ilr OLS
- ilr Ridge
- PLS multi-target regression
- quadratic Ridge
- fixed shallow multi-output gradient boosting reference

## Exploratory selection results

| model | selected parameter | repeated-CV mean target R2 | A6/A7 mean target R2 | A6/A7 MAE |
|---|---:|---:|---:|---:|
| mean baseline | — | -0.0144 | -0.0125 | 0.6193 |
| ilr OLS | — | 0.7309 | 0.7635 | 0.2633 |
| ilr Ridge | 10.0 | 0.7312 | 0.7649 | 0.2626 |
| PLS | 8 components | 0.5985 | 0.6464 | 0.3133 |
| quadratic Ridge | 10.0 | 0.8177 | 0.8661 | 0.2019 |
| shallow GBDT | fixed | 0.7915 | 0.8192 | 0.2307 |

Quadratic Ridge and the shallow GBDT reference improve same-scale predictive metrics relative to linear models in this exploratory protocol. Quadratic Ridge is the strongest candidate in this run, while PLS does not improve over the linear baselines. This is a model-comparison result, not an accepted final model or a causal domain-effect claim.

The quadratic model still has 152 polynomial features and requires coefficient/finite-perturbation stability checks before its interaction terms can be interpreted. A8-A15 remain scale diagnostics and extrapolation scenarios; their absolute errors cannot be presented as scale-invariant success.

## Outputs

- `metrics.json`: run manifest, selected models, evaluations and A6 bootstrap intervals
- `cv_folds.csv`: all repeated-CV fold metrics
- `cv_summary.csv`: candidate-level CV summaries
- `selected_models.csv`: selected candidate per model family
- `predictions.csv`: per-row predictions for all datasets and model families
