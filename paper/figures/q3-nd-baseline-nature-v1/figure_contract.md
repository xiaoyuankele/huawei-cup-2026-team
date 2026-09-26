# Q3 M0 Nature figure contract

Core conclusion: Under the B1/Pythia conditional baseline, the compute budget moves the optimal N--D allocation along a predictable frontier, while the context overhead and B1 observation bounds determine when the relaxed analytic point reaches an observed-range boundary.

Figure archetype: quantitative grid, two-panel composite.

Backend: Python with Matplotlib only.

Final size: approximately 183 mm wide by 86 mm high; SVG/PDF for editable vector output and 600 dpi TIFF/PNG for raster review.

Panel map:

- a: B1 observation rectangle, equal-budget hyperbolas at the representative context `Lctx=8192`, analytic relaxed points and bounded solutions. Hollow markers identify analytic points; triangles identify relaxed points outside the B1 range; filled markers identify bounded solutions.
- b: bounded `N*` and `D*` across the three compute budgets, grouped by the five observed context values; horizontal lines mark the B1 upper bounds.
- table: all 15 rows from the run CSV, retaining relaxed and bounded coordinates, Loss values, support status and analytic-point role.

Evidence hierarchy:

- hero evidence: panel a separates the B1 observation range from relaxed extrapolation and bounded solutions.
- validation evidence: panel b shows how the bounded frontier changes with budget and context.
- controls/robustness: the table preserves every scenario and its role label.

Statistics needed: 15 deterministic scenarios; B1 row count 1,176; five observed context values; three budgets; no error bars because each row is a deterministic optimization scenario.

Source data: `q3-nd-baseline-20260925-r01/tables/q3_nd_baseline_scenarios.csv` and its run `metrics.json`.

Image-integrity notes: no raster source images, no filtering, no smoothing, no interpolation of observations; only the analytic budget contours and deterministic scenario coordinates are plotted.

Reviewer risk: relaxed points outside the B1 range must remain visibly separated from bounded points and must be described as extrapolation diagnostics.
