---
id: 2
title: Support inclusive date ranges for daily flomo memos
status: completed
created_at: 2026-09-21T11:41:47+08:00
updated_at: 2026-09-21T11:44:58+08:00
completed_at: 2026-09-21T11:44:58+08:00
---

## Objective

Extend the standalone CLI and GitHub Action to create one daily diary memo for each day in an inclusive date range while preserving single-date and scheduled usage.

## Implementation

1. Add start/end date arguments and workflow inputs; an omitted end date defaults to today in UTC+8.
2. Reject invalid or reversed ranges and conflicting single-date/range inputs before any write.
3. Create days sequentially with a short delay between writes, stopping on the first failure and reporting completed dates/counts. Keep previews free of credentials and network requests.
4. Document manual and local range usage and safe recovery after partial completion; add offline regression tests.

## Acceptance criteria

- Inclusive ranges handle month/year boundaries, leap days, a single-day range, and UTC+8 today correctly.
- Existing single-date and no-argument usage remain compatible.
- Invalid input sends no requests, previews send no requests, and failures stop later writes without automatic retries.
- Python compilation, offline tests, workflow actionlint, and the 2026-09-04 through 2026-09-21 preview pass.
- Changed files contain no credentials; workflow parameters are passed through environment variables.

## Delivery validation

After the implementation commit is published and hosted CI passes, use the GitHub Action to create the user-authorized 2026-09-04 through 2026-09-21 range (18 dates). Inspect its terminal state and per-date outcomes; report any partial completion before deciding which remaining dates to run. This operation does not trigger Notion synchronization.

## Change Log

- 2026-09-21T11:41:47+08:00: Created the bounded date-range implementation plan and recorded the requested hosted backfill verification.
- 2026-09-21T11:43:03+08:00: Implemented inclusive CLI/workflow ranges, fail-fast sequential writes, progress reporting, and credential-free previews; validating before publication.
- 2026-09-21T11:44:58+08:00: Implementation verified: 33 offline tests, Python compilation, actionlint, and the inclusive 18-day dry-run passed. Ready for hosted CI and the user-authorized actual Action run.
