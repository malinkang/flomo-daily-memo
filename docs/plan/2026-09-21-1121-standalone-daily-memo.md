---
id: 1
title: Extract the daily flomo memo workflow into a public repository
status: completed
created_at: 2026-09-21T11:21:07+08:00
updated_at: 2026-09-21T11:33:57+08:00
completed_at: 2026-09-21T11:33:57+08:00
---

## Objective

Create the public GitHub repository `malinkang/flomo-daily-memo` with a self-contained version of the daily memo workflow and its Python entry point. Preserve the existing UTC+8 diary content and date behavior.

## Scope and steps

1. Extract the memo request and signature behavior into standalone Python modules, using only `requests` and `python-dotenv`.
2. Keep the daily 16:00 UTC schedule and optional manual date; add a no-write preview and pass workflow input through environment variables.
3. Require account-specific credentials through environment variables or GitHub Secrets, exclude local configuration, and return sanitized failures.
4. Document setup, scheduling, local use, and the transition from an existing schedule. Add an MIT license and offline CI.
5. Validate Python compilation, date/signature/request/error behavior, workflow syntax, and the publication contents. Mark this plan completed and commit the implementation.
6. Publish the verified commits to the new public repository and verify remote visibility, CI, and a manual no-write preview run.
7. Remove the daily workflow and standalone creation script from the original repository, link to the new repository in its README, and update the NotionHub submodule reference after the source change passes validation and is published.

## Acceptance criteria

- The repository runs independently without flomo2notion, Notion, or NotionHub runtime dependencies.
- The default content is `#日记 YYYY-MM-DD`, with created_at at midnight UTC+8. A valid explicit date overrides today's date.
- Invalid configuration, invalid dates, upstream failures, and malformed responses return nonzero exit status without logging credentials or upstream response bodies.
- Preview works without credentials or network access. CI tests run without Secrets.
- The repository contains no account token, personal device ID, local environment, log files, or source-repository history.
- The published repository is public and both CI and the manual preview succeed.
- The original repository no longer contains the daily creation script or workflow; its shared signing module and Notion synchronization code remain intact. The NotionHub submodule reference records the published removal. No Notion sync run is required because the removed entry point only creates flomo memos.

## Change Log

- 2026-09-21T11:21:07+08:00: Created a bounded extraction plan for the requested standalone public repository.
- 2026-09-21T11:24:10+08:00: Began standalone extraction using the current source implementation; require a user-provided device ID instead of inheriting an account-specific default.
- 2026-09-21T11:26:23+08:00: Expanded the migration scope at the user’s request to remove the original daily creation workflow and script, retaining the shared sync dependencies and updating the root gitlink.
- 2026-09-21T11:33:57+08:00: Completed extraction and migration. Twenty offline tests, Python compilation, actionlint, and the publication scan passed. Public GitHub CI passed on Python 3.10 and 3.12; manual preview passed without credentials or writes. Removed the original entry points through the source PR and updated the root gitlink, then fast-forwarded the local checkouts while preserving unrelated changes.

## Verification and handoff

- Public repository: https://github.com/malinkang/flomo-daily-memo (default branch `main`).
- Public CI: https://github.com/malinkang/flomo-daily-memo/actions/runs/35557624274 — success on Python 3.10 and 3.12.
- Manual preview: https://github.com/malinkang/flomo-daily-memo/actions/runs/35557625873 — success; no flomo write was sent.
- Source removal: https://github.com/malinkang/flomo2notion/pull/3 — merged as `d335ecc030b0493a0489b01565a9d9d9facf749a`; complete Python compilation and five existing sync tests passed locally.
- Root gitlink: https://github.com/malinkang/notionhub/pull/42 — merged as `714e931e158b67379ede6138ba4000d6cabad295`; verified that every formal submodule path is a gitlink and that the flomo target exists on remote `main`.
- The two private repositories' hosted CI jobs did not start because GitHub reported an account payment/spending-limit restriction. This infrastructure limitation remains; their local checks above passed.
- GitHub cannot read back the original repository's encrypted Secrets. The new repository contains no credentials; configure `FLOMO_TOKEN` and `FLOMO_DEVICE_ID` before actual memo creation. Scheduled runs skip until configuration exists. Actual authenticated creation was not tested.
- No Notion sync was triggered: the extracted and removed entry point creates memos in flomo and does not participate in Notion synchronization.
