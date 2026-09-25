# Figure 1: scale-correction audit

## Figure contract

- Core conclusion: a constant correction reduces error in the mean Loss, while domain-specific extrapolation and transfer of the low-scale slope remain imperfect.
- Evidence chain: (a) mean-Loss RMSE; (b) pooled RMSE across all 13 responses; (c) paired scale coefficients and their sampling uncertainty; (d) same-recipe, high-scale change as a direct slope-transfer check.
- Archetype: quantitative grid, with the two error comparisons as primary evidence and the paired-effect panels as interpretation.
- Backend: Python / matplotlib, following the established user preference. No external plotting templates or private materials are incorporated.
- Exports: 180 × 157 mm; editable SVG/PDF text; PNG preview; 600 dpi compressed TIFF. All glyphs at least 6 pt. This is a scientific handoff figure, not a claim of journal acceptance.

## Caption

**Figure 1 | Mean-Loss improvements do not establish accurate domain-wise extrapolation.**
**a,** Root-mean-square error (RMSE) of each recipe's arithmetic mean across 13 Loss responses. B1 uses the composition-derived quality proxy. The two C1 corrections have identical mean predictions, so one C1 curve represents both. **b,** RMSE pooling all recipe–response errors, without averaging responses first. The domain-specific C1 and mixture-conditioned C2 corrections show larger discrepancies than global C1 on the supplied 10B/70B estimates. **c,** Domain-specific slopes per unit increase in log10(scale), fitted from 256 matched A6/A8 recipe pairs; bars are the supplied 95% percentile bootstrap intervals (5,000 resamples of matched recipe rows, with all 13 responses resampled together). The last row is the 13-domain mean. **d,** Mean Loss decrease between the 63 matched 10B and 70B recipes, calculated from the supplied estimates, compared with decreases transferred from the 1M–60M domain slopes. The dotted line is the global-C1 predicted decrease; the final row compares the 13-domain means.

In a and b, 1M/60M each contain 256 rows, 1B contains 64, and 10B/70B each contain 63. Corrected models use both 1M and 60M cohorts for paired calibration. The 1B evaluation is retrospective. The 10B/70B Loss values are supplied estimates, not independent measurements; those recipes also match a subset of A4. Top-row connecting lines guide comparisons across ordered cohorts and do not assert interpolation. Points are fixed-cohort metrics, not seed/fold means; no metric confidence intervals are provided. Panel d uses complete cohort means; no uncertainty interval is supplied or invented. No hypothesis tests or p values are shown. Slope bootstrap intervals quantify paired-row variability only, not uncertainty in the scale-law form.

## Source data and reproduction

Source files, relative to this folder: `../metrics_aggregate.csv`, `../paired_shift_transfer.csv`, `../scale_coefficients.csv`, `../model_parameters.json`. Full model and quality-axis comparisons remain in the CSV files; the figure deliberately fixes the base model to B1_Q_proxy to isolate correction design. All 13 response domains are displayed in c/d; no recipe rows are excluded by this plotting script.

From the repository root:

```bash
python scripts/q1_s03/plot_audit.py --run experiments/runs/q1-s03-handoff-audit-20260925-r01
```

Outputs are `Figure1_scale_correction_audit.{svg,pdf,png,tiff}`. Source checks and rendered-PDF text checks are documented in `QA_notes.md`.
