# QA notes

- Backend: Python/matplotlib/seaborn only.
- Outputs: editable SVG and PDF, 600 dpi TIFF, 300 dpi PNG.
- Main data counts: 1,214 A4-A15 scored rows; M1 prediction source has 1,214 rows; domain increment table is retained in full.
- Extrapolation: A12-A15 are shaded or explicitly labeled as supplied estimates.
- Paired evidence: A6/A7 → A8/A9 scale effect is plotted with the supplied bootstrap intervals.
- Composition: A10/A11 is labeled as scale + composition migration.
- Quality: soft Q_proxy is presented as an optional deterministic covariate, not a causal quality measure.
- No simulated data, no hidden row filtering, and no rasterized source tables. Scatter marks are rasterized only inside the vector figure to keep the file size manageable.
- Visual review: inspect both PNG previews at final physical size; all panels use the repository palette, editable text settings, and ≥5 pt intended text sizes.
