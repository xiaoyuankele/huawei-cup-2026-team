# Figure 1 · Nature-inspired revision

- Claim: Seven domains differ in score location and within-domain spread, with overlapping observed ranges; the plot does not establish intrinsic domain quality or significance.
- Evidence: One dominant quantitative panel. Upper half densities describe distribution shape, lower conventional boxes show Q1–Q3, median, mean and 1.5-IQR observed whiskers. All outside-whisker observations remain visible.
- Data: Same 261086 unique records and SHA256 as the original figure; no sampling, deletion, parameter refitting or score change. The original summary CSV must match exactly.
- Density: Gaussian KDE uses every record with shared absolute bandwidth 1.2 score units and 400 grid points per domain, restricted to observed min–max. Each density is peak-normalized for equal maximum height; height does not represent sample size. n is directly labeled.
- Archetype: quantitative grid with a single hero panel. Structural adaptation of the existing figure, replacing the page-like header/table composition with compact distribution rows. No external figure assets are copied.
- Backend: saved Python preference; matplotlib and scipy only for visualization.
- Style: white background, restrained teal, charcoal rules, a muted warm accent for means; sans-serif labels including Chinese; compact annotations, one shared key, no redundant title at the bottom.
- Export: 183 × 114 mm; PNG and TIFF 600 dpi; editable PDF/SVG text. Full caption and statistical notes saved separately. Minimum text 7 pt. This is a Nature-inspired presentation for the user's mathematical-modeling report, not a claim of journal acceptance or formal submission compliance.
- QA: input SHA256, all seven counts and unique IDs; exact original descriptive-statistic equality; outlier count and marker integrity; all labels within canvas; explicit no-overlap checks for key/axis title; source preflight, PDF text audit, visual inspection of each row and whole figure.
