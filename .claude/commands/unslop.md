---
description: Quality gate — diff → targeted tests → code-reviewer → unslop-reviewer → handover update.
---

Run the post-implementation polish gate per `.claude/SHARED_PLAN.md` Appendix A1.2.

## Steps
1. **Capture changed files**. Include staged, unstaged, and untracked files:
   - `git diff --name-only HEAD`
   - `git diff --name-only --cached`
   - `git ls-files --others --exclude-standard`
   - If a feature branch has an upstream/base, also include `git diff --name-only <merge-base>...HEAD`.
   - De-duplicate the list. If it is empty, stop.
2. **Targeted tests** — derive from the diff using `docs/ai_workflow/QUALITY_GATE.md`:
   - `routes/X.py` → try `tests/test_X_routes.py`, then `tests/test_X.py`; also `rg` tests for imports/blueprint names.
   - `utils/X.py` → try `tests/test_X.py`; also `rg` tests for imports.
   - `templates/X.html` or `static/js/**/X*` → normalize `_` to `-` and use the feature-to-spec map in `QUALITY_GATE.md`.
   - Run via `/run-tests <files>` and `/run-e2e <specs>`. If the union is empty or the diff is cross-cutting, fall back to `/verify-suite`.
3. **`code-reviewer` agent**: invoke on the staged diff. Address every finding or document why deferred.
4. **`unslop-reviewer` agent**: invoke on the staged diff. Address every finding before commit; AI smells are not "preferences".
5. **`/handover`**: prepend a session block to `MASTER_HANDOVER.local.md` capturing what shipped + new test counts.

## When to use
- Before declaring a non-trivial change complete.
- Before opening a PR.
- Not for product-docs-only or comment-only changes — those go straight to `/handover`.
- For `.claude/**`, `CLAUDE.md`, folder `CLAUDE.md`, and `docs/ai_workflow/**`, do the manual dry-run/self-review from `QUALITY_GATE.md`; these files change agent behavior even though they are Markdown.

## When NOT to chain
- If targeted tests fail in step 2, stop and fix; do not let `code-reviewer`/`unslop-reviewer` review broken code.
- If the diff is purely product docs, skip steps 2–4; jump to step 5.
