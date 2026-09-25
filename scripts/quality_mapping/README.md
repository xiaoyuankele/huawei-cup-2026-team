# Quality mapping scripts

Set `QUALITY_ATTACHMENTS_ROOT` to the local controlled `A_data_value` attachment directory and `QUALITY_MAPPING_OUTPUT_DIR` to a run output directory. Raw attachments are not committed to the public repository.

```powershell
$env:QUALITY_ATTACHMENTS_ROOT = "data/origin/real_attachments/A_data_value"
$env:QUALITY_MAPPING_OUTPUT_DIR = "experiments/runs/quality-mapping-20260925-r02-soft-handoff/tables"
python scripts/quality_mapping/build_quality_mapping.py
python scripts/quality_mapping/revise_quality_mapping.py
```
