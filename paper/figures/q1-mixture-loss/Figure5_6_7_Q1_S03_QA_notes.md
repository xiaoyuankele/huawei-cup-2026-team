# QA notes

- Backend: Python/matplotlib/seaborn only.
- Outputs: editable SVG/PDF, 600 dpi TIFF, 300 dpi PNG.
- Figure 5 uses the selected hyperparameter for each model family across the 15 A4/A5 fold-seed replicates and point estimates from A6/A7 external validation; no uncertainty was fabricated for A6/A7 RMSE/MAE.
- Figure 6 uses multiplicative zero replacement with epsilon=1e-4 for the primary CLR map and exports epsilon sensitivity at 1e-6, 1e-5 and 1e-4. A12/A14 exact recipe overlap is retained.
- Figure 7 keeps all 13 target domains and both quality variants. Negative Δ means lower error relative to p_only.
- A8-A15 are not used to select the benchmark model. A10/A11 remains retrospective, and A12-A15 are supplied-estimate audits.
- Source rows are retained in accompanying CSVs; only declared cohorts/models are selected for each panel.
