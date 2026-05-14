# AGENTS.md

This repo's canonical operating guide is **[CLAUDE.md](CLAUDE.md)** — read it first.

Codex CLI follows the same conventions as Claude Code: module boundaries, DatabaseHandler pattern, response-contract shapes, logger pattern, and test/E2E gates all apply equally. There is no separate Codex-specific guide; a single source of truth avoids drift.

Codex-specific notes (when they differ from the above):
- Codex autonomy settings live in user-level `C:\Users\<user>\.codex\config.toml`, not in this repo.
- Intended settings are `approval_policy = "never"`, `sandbox_mode = "workspace-write"`, and `[sandbox_workspace_write] network_access = false` — see `docs/ai_workflow/AUTONOMY.md` for the four-layer safety model.
- Before parallel work that may touch the DB, dev server, or tests, read `docs/ai_workflow/PARALLEL_WORKFLOW.md` and use `scripts/new-worktree.ps1` to isolate `data/database.db`.
