# Q2 figure layout QA

The seven added figures were regenerated with the repository palette and a shared white-background style. Plot legends were moved outside data regions or replaced by dedicated explanatory text bands; rotated domain labels in Fig06 were placed below the heatmap; subplot spacing was increased before export.

Automated checks:

- Nature figure source validation: 20 PASS, 0 WARN, 0 FAIL.
- PDF text audit: Fig05--Fig11 all auditable; minimum text size 5.7--6.5 pt; no below-threshold text runs.
- Vector exports: SVG and PDF for every figure.
- Raster exports: 600 dpi PNG and TIFF for every figure.

The figures remain deterministic frozen-model diagnostics and do not add confidence intervals or imply joint experimental validation.
