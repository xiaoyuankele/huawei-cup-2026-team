# Q2 M0/M1 exploratory run

M0 fits the classical N-D law on B1 with leave-one-parameter-size-out folds. M1 fits an additive quality sensitivity term on B6 with grouped N-D-cell folds and evaluates the B7 nested extension. B8, B9 and B10 are excluded by the current migration gates. This run is exploratory and not a final paper result.

## Observed diagnostics

- M0 full B1 exploratory fit: `E=1.689798`, `A=0.353980`, `B=1.240306`, `alpha=0.339977`, `beta=0.279878`.
- M0 leave-one-parameter-size-out RMSE ranged from about `0.000102` to `0.000220` within B1. This reflects the highly regular B1 trajectory table and is not an external generalization guarantee.
- M0 external diagnostics: B2 RMSE `1.2431` (`R2=-5.0728`), B4 RMSE `0.2927` (`R2=0.6045`), B5 RMSE `0.1976` (`R2=0.7306`). These sources are not pooled with B1.
- M1 grouped B6 cell-fold RMSE ranged from `0.0512` to `0.0669`; the B7 nested extension RMSE was `0.0416` on 90 additional rows. This is a nested-extension diagnostic, not independent validation.
- M1 fitted `G=0.362247` for the impurity term `(1-Q_score)`, consistent with the negative quality direction observed in B6/B7. It does not validate the A-side quality score or B8.

## Decision

M0 and M1 are reproducible exploratory baselines and may inform the next bridge-interface audit. They do not unlock a joint A--B model. B8 remains excluded, and no result from this run is a final problem-two claim.
