# Q1-S03 mixture–loss figure assets

This directory contains the five figures used by the Q1 third-subquestion manuscript section.

* `Figure3_Q1_S03_core_analysis` separates the paired same-mixture scale contrast from the mixed scale-plus-composition contrast.
* `Figure4_Q1_S03_model_diagnostics` records the provisional quality/proxy diagnostic and is not a model-ranking figure.
* `Figure5_Q1_S03_model_selection_validation` compares the selected composition-only candidates and A6/A7 same-scale validation.
* `Figure6_Q1_S03_aitchison_support` is a descriptive CLR/epsilon support-domain diagnostic; its distances are sensitive to zero replacement.
* `Figure7_Q1_S03_quality_increment` reports quality as an optional deterministic increment. The mapping covers 6 of 17 domains.

PDF is the paper input; SVG is retained for editing and PNG is retained for review. TIFF is intentionally omitted from Git to avoid adding five 40–80 MB raster files.

The figures were generated from the registered experiment outputs listed in the two manifest JSON files. The benchmark and quality-increment sources are marked `EXPERIMENTAL_REVIEW`; A8–A15 were not used for model selection. A10/A11 is a retrospective scale-plus-composition diagnostic, and A12–A15 contain supplied estimates rather than independent observations.

`source_data/` contains the small exported CSVs used to audit the plotted values. It does not contain raw text records.
