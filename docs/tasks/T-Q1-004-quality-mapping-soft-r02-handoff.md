# T-Q1-004 quality-mapping soft v2 handoff

owner: B
reviewer: A
branch: feature/B/T-Q1-004-quality-mapping-soft-r02
run_id: quality-mapping-20260925-r02-soft-handoff
status: REVIEW
needs_human_review: true

## Scope

Submit the versioned soft mapping and A4-A15 scored handoff tables as an additive run. The teammate's mapping/distribution audit remains separate.

## Acceptance checks

- 17-row A16 v2 mapping table present.
- A4-A15 wide and long tables present with 1,214 and 20,638 rows.
- v1 compatibility tables preserved separately.
- A1-A3/A4-A16 raw inputs referenced only through relative-path manifest and SHA256.
- No raw attachments, private paths, or credentials included.
- Hash list and row-count checks pass.

## Review points

- Confirm inferred semantic weights before using v2 as the primary paper score.
- Keep the existing Q1 run that uses v1 unchanged.
- Treat the soft score as descriptive and deterministic from mixture proportions.
