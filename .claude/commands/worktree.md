---
description: Create a new git worktree with isolated SQLite DB for parallel agent work.
---

Use this to fork a workstream onto its own checkout so parallel Claude instances don't corrupt each other's `data/database.db`. SQLite WAL is not safe across concurrent writers from independent processes pointing at the same file — this is why [CLAUDE.md](../../CLAUDE.md) §3 keeps `FLASK_USE_RELOADER=0` by default.

## Quick start

```powershell
.\scripts\new-worktree.ps1 -Task <slug> [-Seed visual|empty|copy-current] [-OpenTerminal]
```

Creates `..\Hypertrophy-Toolbox-v3-<slug>` from HEAD on branch `wt/<slug>`, ensures `data/` and `data/auto_backup/` exist, seeds `data/database.db` per the mode, and (with `-OpenTerminal`) opens a new Windows Terminal tab in the new worktree.

## When to fork

- Two or more agents will edit the working tree at once.
- A long experiment will pollute `data/database.db` and you want the main checkout clean.
- You need to compare two implementations side-by-side.

If only one agent is active, stay in the main checkout — worktrees are overhead.

## Seed modes

| Mode | What it does | Use when |
|---|---|---|
| `visual` (default) | Copies `e2e/fixtures/database.visual.seed.db` into `data/database.db`. If the fixture is missing, warns and leaves the DB absent so `app.py` initializes fresh on launch. | E2E or template work that expects the fixture dataset. |
| `empty` | Leaves `data/database.db` absent. `app.py` will run `initialize_database()` on first launch. | Fresh dev / unit-test work. |
| `copy-current` | Copies the main checkout's `data/database.db` if it exists. Warns about WAL/SHM sidecars; stop the source app first. | Reproducing a bug against your live local data. |

The script always checks the source exists before copying — missing source warns and skips rather than failing the worktree creation.

## Per-worktree, never shared

- `data/database.db` (and `-wal` / `-shm` sidecars)
- `data/auto_backup/`
- `.venv/` — recreate with `python -m venv .venv` or symlink the main checkout's venv with `New-Item -ItemType SymbolicLink`
- `MASTER_HANDOVER.local.md`
- Live workstream claims — see [docs/ai_workflow/WORKSTREAM_OWNERSHIP.md](../../docs/ai_workflow/WORKSTREAM_OWNERSHIP.md); put the active row in `MASTER_HANDOVER.local.md` or a local `WORKSTREAM_OWNERSHIP.local.md`, not the committed table.

## Tearing down

```powershell
git worktree remove ..\Hypertrophy-Toolbox-v3-<slug>
git branch -d wt/<slug>   # or -D if abandoned
```

`git worktree remove` refuses if the worktree has uncommitted changes. Investigate before forcing.

## See also

- [docs/ai_workflow/PARALLEL_WORKFLOW.md](../../docs/ai_workflow/PARALLEL_WORKFLOW.md) — when to fork, DB isolation rule, conflict avoidance.
- [docs/ai_workflow/WORKSTREAM_OWNERSHIP.md](../../docs/ai_workflow/WORKSTREAM_OWNERSHIP.md) — path-claim rules.
