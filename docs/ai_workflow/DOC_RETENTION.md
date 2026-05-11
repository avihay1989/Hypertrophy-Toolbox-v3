# Documentation Retention

*Rules for keeping the docs surface useful without losing historical context.*

## Purpose

Keep active docs focused on current project truth. Archive completed plans when they stop helping daily work, and delete local/debug artifacts that should never become project memory.

## Retention Classes

| Class | Examples | Rule |
|---|---|---|
| Always active | `CLAUDE.md`, `docs/MASTER_HANDOVER.md`, `docs/ai_workflow/**`, `docs/DECISIONS.md`, `docs/CHANGELOG.md` | Keep in the active tree. Update when the workflow or durable project truth changes. |
| Active workstream | `docs/<feature>/PLANNING.md`, `docs/<feature>/EXECUTION_LOG.md`, feature research notes | Keep while the workstream is active, paused, or referenced from `docs/MASTER_HANDOVER.md`. |
| Archive | Completed feature plans, old audits, superseded implementation notes | Move to `docs/archive/<year>/<feature>/` after all archive criteria are met. |
| Delete | `debug/*`, `*.local.md`, generated scratch notes, local command output | Do not archive. These are local-only or transient artifacts. |

## Archive Criteria

Archive a document only when all of these are true:

1. The feature, audit, or migration shipped or was explicitly abandoned.
2. The document has had no meaningful edits for at least 6 months.
3. No open follow-up in `docs/MASTER_HANDOVER.md` points at it.
4. The active docs index or feature folder has a better current source of truth.

## Archive Procedure

1. Create `docs/archive/<year>/<feature>/` if it does not already exist.
2. Move the stale document there with its filename preserved unless the old name is misleading.
3. Update links in `docs/README.md`, `docs/ai_workflow/INDEX.md`, and any affected feature docs.
4. Add a short changelog or handover note if the archived document was previously part of an active workstream.

## Keep Active Procedure

When a document stays active after a milestone, trim it to what future work needs:

- Replace completed checklist noise with a short shipped summary.
- Move durable choices into `docs/DECISIONS.md` as an ADR when they affect future implementation.
- Keep command names, file paths, and current verification status concrete.
- Remove stale speculation once the source code, changelog, or tests carry the truth.

## Delete Procedure

Delete transient artifacts instead of archiving them:

- Files under `debug/`, which are gitignored session scratch.
- `*.local.md`, including `MASTER_HANDOVER.local.md`.
- Generated command output, screenshots, or test logs unless a committed doc explicitly needs a small excerpt.
- Duplicated plans whose useful decisions have already moved into active docs.
