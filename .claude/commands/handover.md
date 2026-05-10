---
description: Update local handover scratch with current session state; optionally edit committed handover.
---

Update the handover layers per `.claude/SHARED_PLAN.md` Appendix A1.1.

## Steps
1. Capture current state:
   - Run `git status --short --branch` and `git log -1 --oneline`.
   - Note the current TodoWrite list (if any) and the file/line you are mid-edit on.
2. **Prepend** a new dated block to `MASTER_HANDOVER.local.md` (do not overwrite or delete prior blocks). Block template:

   ```markdown
   ## YYYY-MM-DDTHH:MM
   - git status: <one-line summary>
   - last commit: <sha> — <subject>
   - in-progress edit: <file:line>
   - open todos: <list>
   - next step: <action>
   ```
3. Ask the user: "Update committed `docs/MASTER_HANDOVER.md` too? (y/N)" — default no.
4. If yes, open `docs/MASTER_HANDOVER.md` for manual edit; never auto-write to it. The committed handover is curated, not appended.
5. No Stop hook is wired — `/handover` stays manual until it proves low-noise.
