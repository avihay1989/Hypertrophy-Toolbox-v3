# Autonomy Model

*How agents run end-to-end in this repo without per-tool-call approval prompts.*

---

## What "autonomous post-planning" means

After the planning gates required by
[QUALITY_GATE.md](QUALITY_GATE.md#plan-stage-routing) are approved, both Claude Code
and Codex CLI can execute the approved scope — file edits, test runs, shell commands
scoped to the repo — without stopping to ask on each tool call. Gate 0 approves the
requirements for large, ambiguous, and new-workflow work; Gate 1 approves the plan.
The human's decision points are those gates, not individual in-scope tool calls.

This only applies within the approved scope. Anything outside that scope (new tables, deletes outside `data/auto_backup/`, changes to `app.py` blueprint registration, pushes to remote) still requires explicit confirmation.

---

## Four layers of defense

| Layer | Artifact | What it protects against |
|---|---|---|
| **1. Requirements + plan approval gates** | Gate 0 `/requirements` → Gate 1 `/council-plan` → [PLAN_REVIEW_TEMPLATE.md](PLAN_REVIEW_TEMPLATE.md) | Wrong scope, calculation-semantics drift, missing tests, API-contract breaks — caught before a line of code is written |
| **2. Workspace-write sandbox** | User-level `C:\Users\<user>\.codex\config.toml`: `sandbox_mode = "workspace-write"`, `approval_policy = "never"`, and `[sandbox_workspace_write] network_access = false` | Writes confined to the workspace; no outbound network |
| **3. Worktree isolation** | `scripts/new-worktree.ps1` + [PARALLEL_WORKFLOW.md](PARALLEL_WORKFLOW.md) | Parallel work that may touch the DB, dev server, or tests gets its own `data/database.db`; SQLite WAL corruption on the main checkout is prevented |
| **4. Post-work review gate** | `/unslop` → `/verify-suite` | AI slop, test regressions, response-contract drift caught after implementation, before any commit lands |

Layers 1 and 4 are process gates (human-approved plan in, human-reviewed diff out). Layers 2 and 3 are technical containment (sandbox + DB isolation). A runaway or mistaken agent can only damage the repo within its worktree, and that damage is reviewed before merging.

---

## Workflow roles

The approved rollout defines these roles; they become active as their charters land in
`.claude/agents/`. Canonical gate and checkout rules remain in these workflow
documents rather than being copied into every charter.

- **`manager`** is the read-only primary router and council orchestrator. It reads
  artifacts, classifies planning size, delegates to allowlisted roles, and enforces
  gates. It never edits files or runs shell-backed skills, and it authors no plan
  content: during `/council-plan` it delegates Plan v1 drafting to `product-manager`
  after Gate 0, spawns the three reviewers in parallel, and synthesizes their proposed
  dispositions, but every council-document write (Plan v1, response matrix, Plan v2) is
  delegated to `product-manager`. It resumes the same delegated agent through
  `SendMessage` using that agent's ID when continuity matters; it does not replace the
  approved artifact with a paraphrased handoff.
- **`product-manager`** owns writes to the **entire** active feature
  `docs/<feature>/PLANNING.md`: Section 0 via `/requirements` (stops at Gate 0), and —
  when the manager delegates them during `/council-plan` — Plan v1, the response
  matrix, and Plan v2 (stops at Gate 1). This is a behavioral write boundary: it writes
  only the active `PLANNING.md`, never application, test, or config files, and it never
  resolves owner-only decisions independently. The manager routes `/requirements` and
  council drafting to this role rather than paraphrasing content.
- **`senior-developer`** is the production-code writer. It reads the approved brief
  and plan directly, implements in the manager session's checkout, and supplies test
  and migration evidence without pushing or merging.
- **`automation-qa`** authors criteria-derived tests before implementation starts and
  is behaviorally limited to `tests/**` and `e2e/**` writes.
- **`manual-qa-reviewer`** is repository-read-only and performs exploratory browser
  testing with reproducible findings.
- Existing plan-time and diff-time reviewers remain independent; developers do not
  approve their own work.

One manager-led feature owns one checkout. Sequential work may use the main checkout;
concurrent work must start in a separate checkout created before its manager session.
See [PARALLEL_WORKFLOW.md](PARALLEL_WORKFLOW.md) for the tracked-DB commit rule.

### Runtime verification versus exploratory QA

This is the single canonical division of labor for the two browser-validation paths:

- **`/verify`** owns scripted end-to-end confirmation of the changed flow. A
  senior-developer launches the current checkout through
  `.claude/skills/run-hypertrophy-toolbox/`, drives the smallest real UI path that
  reaches the change, adds one safe adjacent probe, captures transcript evidence,
  and shuts the app down. It does not substitute tests or imports for the UI.
- **`manual-qa-reviewer`** owns exploratory and regression sweeps beyond the changed
  flow: nearby state transitions, usability, recovery, and reproducible findings. It
  receives an already-running app and never launches processes or edits the checkout.

Both use an isolated, headless Playwright MCP server with `--output-mode stdout` so
browser evidence stays in the transcript rather than creating checkout artifacts.
User-visible runtime changes require `/verify`; manual QA is additive when the plan or
quality gate calls for exploration. Non-runtime changes keep their existing
[QUALITY_GATE.md](QUALITY_GATE.md) evidence and do not invent a browser gate.

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
- [QUALITY_GATE.md](QUALITY_GATE.md) — plan-stage routing plus required gates per change type
- [PLAN_REVIEW_TEMPLATE.md](PLAN_REVIEW_TEMPLATE.md) — council review format
- Root [CLAUDE.md](../../CLAUDE.md) §1 non-goals — local-first invariant that sandbox enforces
