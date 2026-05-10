# Workstream Ownership

*Advisory path-claim rules for parallel Claude instances. Solo dev — claims are coordination hints, not enforced. Implements [`.claude/SHARED_PLAN.md`](../../.claude/SHARED_PLAN.md) Appendix A2.1.*

## Where live claims go

**Do not put live claims in this file.** This committed doc is rules + template only; live ownership rows would create merge churn on every claim/release.

Put live claims in one of:
- `MASTER_HANDOVER.local.md` — append a claim block under the current session entry (gitignored).
- `WORKSTREAM_OWNERSHIP.local.md` — gitignored sibling of this file, dedicated to claims (see [`.gitignore`](../../.gitignore)).

## Active claims (template)

Copy this block into your local file, fill in the rows, delete rows when done.

```markdown
## Active claims
| Path glob | Workstream | Owner instance | Worktree | Started |
|---|---|---|---|---|
| `routes/workout_plan.py`, `templates/workout_plan.html` | fatigue badge slot | claude-A | Hypertrophy-Toolbox-v3-fatigue-badge | 2026-05-11 14:00 |
```

## Rules

1. Before editing files matching a claimed glob, check the local claim file in the worktree(s) you know about.
2. If you must edit a claimed path, note it in `MASTER_HANDOVER.local.md` and coordinate — rebase, pair, or wait.
3. Release a claim by deleting the row from the local file (nothing to commit).
4. **Never-claimed shared paths** (coordinate per-edit, not via claims):
   - `app.py`
   - root [`CLAUDE.md`](../../CLAUDE.md) and any folder-level `CLAUDE.md`
   - [`.claude/settings.json`](../../.claude/settings.json), [`.claude/SHARED_PLAN.md`](../../.claude/SHARED_PLAN.md)
   - [`docs/MASTER_HANDOVER.md`](../MASTER_HANDOVER.md)
   - [`.gitignore`](../../.gitignore)
5. **Per-worktree, never shared** (do not claim — they are isolated by construction):
   - `data/database.db` and its `-wal` / `-shm` sidecars
   - `data/auto_backup/`
   - `MASTER_HANDOVER.local.md`
   - `.venv/`

## Claim granularity

- Prefer file globs over folder-level claims. `routes/workout_plan.py` is a claim; `routes/**` is a foot-gun.
- A single workstream can hold multiple claims — list them as separate rows.
- Reviewer-only edits (proofreading, comments) don't need a claim; coordinate verbally.

## See also

- [PARALLEL_WORKFLOW.md](PARALLEL_WORKFLOW.md) — when to fork, DB isolation rule.
- [`.claude/commands/worktree.md`](../../.claude/commands/worktree.md) — how to fork.
- `MASTER_HANDOVER.local.md` — preferred home for live claims.
