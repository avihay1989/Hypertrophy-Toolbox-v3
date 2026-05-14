# Autonomy Model

*How agents run end-to-end in this repo without per-tool-call approval prompts.*

---

## What "autonomous post-planning" means

After a plan is approved (via `/council-plan`), both Claude Code and Codex CLI can execute the approved scope — file edits, test runs, shell commands scoped to the repo — without stopping to ask on each tool call. The human's decision point is plan approval, not individual tool execution.

This only applies within the approved scope. Anything outside that scope (new tables, deletes outside `data/auto_backup/`, changes to `app.py` blueprint registration, pushes to remote) still requires explicit confirmation.

---

## Four layers of defense

| Layer | Artifact | What it protects against |
|---|---|---|
| **1. Plan approval gate** | `/council-plan` → [docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md](PLAN_REVIEW_TEMPLATE.md) | Wrong scope, calculation-semantics drift, missing tests, API-contract breaks — caught before a line of code is written |
| **2. Workspace-write sandbox** | User-level `C:\Users\<user>\.codex\config.toml`: `sandbox_mode = "workspace-write"`, `approval_policy = "never"`, and `[sandbox_workspace_write] network_access = false` | Writes confined to the workspace; no outbound network |
| **3. Worktree isolation** | `scripts/new-worktree.ps1` + [PARALLEL_WORKFLOW.md](PARALLEL_WORKFLOW.md) | Parallel work that may touch the DB, dev server, or tests gets its own `data/database.db`; SQLite WAL corruption on the main checkout is prevented |
| **4. Post-work review gate** | `/unslop` → `/verify-suite` | AI slop, test regressions, response-contract drift caught after implementation, before any commit lands |

Layers 1 and 4 are process gates (human-approved plan in, human-reviewed diff out). Layers 2 and 3 are technical containment (sandbox + DB isolation). A runaway or mistaken agent can only damage the repo within its worktree, and that damage is reviewed before merging.

Codex config is separate from Claude Code's permission allowlist; see "Claude Code side" below.

---

## When to drop back to interactive mode

Always pause and confirm before:

- **Schema changes** — anything that adds/alters/drops a column or table (`utils/db_initializer.py`, `utils/database.py`, migration scripts). These touch `data/database.db` and can corrupt the live DB or break the backup/restore flow.
- **Edits to `data/database.db` on the main worktree** — only the app itself or a migration script should touch this file.
- **Deletes outside `data/auto_backup/`** — any `rm`/`Remove-Item` targeting files not in the auto-backup dir.
- **`app.py` blueprint registration** — adding or removing a `register_blueprint` call affects every test in `tests/conftest.py`; a mismatch produces 404s silently.
- **`.github/workflows/ci.yml` changes** — CI is shared state; a broken pipeline blocks everyone.
- **Anything matching `.claude/rules/database.md` scope** — the database rule is the highest-risk surface in this codebase.

---

## Claude Code side (T5.3)

Claude Code's permission allowlist in `.claude/settings.json` (under `permissions.allow`) controls which Bash/MCP calls run without a prompt. Run `/fewer-permission-prompts` after a working session to propose additions. Only land patterns that are unambiguous read-only or scoped-to-repo (e.g. `Bash(git status:*)`, `Bash(npx playwright test:*)`). Avoid `Bash(*)`.

---

## See also

- [PARALLEL_WORKFLOW.md](PARALLEL_WORKFLOW.md) — when to fork a worktree and how to tear it down
- [QUALITY_GATE.md](QUALITY_GATE.md) — required gates per change type
- [PLAN_REVIEW_TEMPLATE.md](PLAN_REVIEW_TEMPLATE.md) — council review format
- Root [CLAUDE.md](../../CLAUDE.md) §1 non-goals — local-first invariant that sandbox enforces
