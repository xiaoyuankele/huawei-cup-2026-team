# Figure QA record

This audit covers the supplied quantitative outputs and their presentation. Passing these checks is not evidence of statistical validity or journal acceptance.

## Automated checks

- Source validator: **20 PASS, 0 WARN, 0 FAIL**; see `source_validation.json`.
- PDF text audit: **71 text runs; minimum 6.0 pt; zero below 6 pt**; see `pdf_text_audit.json`.
- Final canvas: **180 × 157 mm**, preserved without tight-crop resizing.
- Editable SVG text and embedded TrueType PDF fonts configured.
- PNG preview: 300 dpi. TIFF: 4,251 × 3,708 pixels at 600 dpi; LZW compressed, 1,138,880 bytes at this export.
- Numerical assertions verify complete metrics (four corrections × five cohorts), all 13 domains plus their mean, finite values, valid coefficient intervals, 63 high-scale recipe pairs, and equality of C1 global/domain mean-Loss RMSE.

## Panel-by-panel visual audit

| Panel | Unique claim | Summary / interval | Unit | Label and collision review | Result |
|---|---|---|---|---|---|
| a | Correction reduces mean-Loss error | Fixed-cohort RMSE; no uncertainty supplied | Recipe, averaged across 13 responses before squared error | C1 equality labelled; curves and annotations separated; calibration/retrospective/estimate labels shown | Pass |
| b | Averaging responses can conceal larger domain-level errors | Pooled recipe–response RMSE; no uncertainty supplied | All recipe × response cells, equal weight | Matches a's scales, colors and cohort order; all four methods distinguishable by markers/linestyles | Pass |
| c | Paired slopes differ across domains | Point estimate with 95% paired-row bootstrap interval | 256 matched recipes; all 13 responses resampled jointly | All 13 named domains and mean displayed; labels and intervals do not collide | Pass |
| d | Low-scale slopes overpredict the supplied high-scale decrease | Complete-cohort mean differences; no uncertainty supplied | 63 matched recipes | Same domain order as c; table estimates distinguished from transferred slopes; global mean reference explained in caption | Pass |

The complete rendered figure and each panel were inspected. There are no cropped labels, obscured points, line/annotation collisions or missing domain rows. The shared method legend is outside the plots. Method identity uses marker shapes and line styles as well as color. The bottom panels share aligned rows, and the separation above the mean is visible.

## Data and interpretation safeguards

No rows were subsampled. The source metric table includes additional base-model and quality-axis sensitivities; the figure uses B1_Q_proxy only to isolate the correction choice. All 13 domains are included in the bottom panels. The script reads only the aggregate CSV outputs and does not refit any model.

A8 is not independent validation for corrected models. A10 was previously inspected and is labelled retrospective. A12–A15 provide estimated Loss values and cannot establish independent observed performance. The low mean-Loss error at 70B must be read alongside pooled domain error and the high-scale paired-change check. The small coefficient bootstrap intervals quantify paired-row variability, not scale-law uncertainty. No p values, causal effects or new confidence intervals are inferred.

## Reproduction

Run `python scripts/q1_s03/plot_audit.py --run experiments/runs/q1-s03-handoff-audit-20260925-r01` from the repository root. Matplotlib, NumPy and pandas are required. Optional source/PDF audit tools belong to the nature-figure skill and are not required to regenerate the figure. Their machine-readable reports are retained with this export for review.
