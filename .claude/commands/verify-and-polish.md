---
description: Documented sequence — full /verify-suite, then code-reviewer, then unslop-reviewer, then handover. Use before declaring a feature complete.
---

This is a **sequence guide**, not a chained skill. Run each step, address findings, re-run if needed.

## Steps
1. **`/verify-suite`** — full pytest + Chromium E2E gate. Must pass (modulo the known current red / historical flake in `e2e/CLAUDE.md` Gotchas) before continuing.
2. **`code-reviewer` agent** — invoke on the staged diff. Cites SQL-injection, response-contract, DB-access, logging, blueprint-registration risks. Address every finding or document why deferred.
3. **`unslop-reviewer` agent** — invoke on the staged diff. Flags AI smells (verbose docstrings, defensive try/except, premature abstractions, restating comments, unrelated churn). Address every finding before commit.
4. **`/handover`** — prepend a session block to `MASTER_HANDOVER.local.md`. If a milestone shipped, edit `docs/MASTER_HANDOVER.md` manually with new test counts and workstream status.

## Failure handling
- Step 1 fail → fix the test, re-run from step 1.
- Step 2 fail → fix the violation, re-run from step 1 if logic changed, else continue from step 3.
- Step 3 fail → fix the smell, re-run from step 3.
- Do not skip to commit on partial success.

## Difference vs `/unslop`
`/unslop` is the **lighter** post-implementation gate — uses targeted tests instead of the full suite. Use `/unslop` for routine work, `/verify-and-polish` for refactors, schema changes, or anything that touches multiple modules.
