# Backup Center Implementation Plan

**Scope**: This is the executable plan for the Backup Center phase-3 hardening pass. Each task card below is self-contained and sized for a small-model agent (Sonnet-class, ~15–45 minutes of work per card). An agent can pick up any one card, execute it end-to-end, and confirm success without reading other documents — provided the card's `Depends on` list is complete.

**Companion document**: Product rationale, review history, observations by area, and deferred items live in [BACKUP_CENTER_OBSERVATIONS.md](BACKUP_CENTER_OBSERVATIONS.md). This plan is purely actionable; do not duplicate product reasoning here.

**Branch**: File references below point to the code on `redesign/calm-glass-2026` at the time of writing. Line numbers may drift as earlier cards land; always confirm with a fresh grep before trusting a specific line number.

**Target confidence**: 95%. Any step that depends on a product decision is called out as a prerequisite. If a prerequisite is not locked, stop and escalate rather than guess.

---

## Decisions Locked Before Implementation

These were decided during the cross-review rounds (Codex ↔ Opus, 2026-04-24) and are final unless explicitly reopened:

- **Retention policy**: count-based — keep the latest 10 auto-backups. Age-based pruning deferred.
- **Empty-backup policy**: warn-only in the UI — backend stays lenient. No HTTP 400 block.
- **`restored_count == 0` treatment**: warning state, not success. Distinct copy, no success styling, no auto-dismiss.
- **Duplicate backup names**: allowed — no uniqueness check in create or rename paths.
- **Validation parity**: backend limits must match frontend `maxlength` — name ≤ 100, note ≤ 500. Do not diverge.
- **`workout_log` scope during restore**: keep current CASCADE-driven clear. Documented as intentional in code, not treated as a bug. Log preservation across restore is a future-phase concern (see below).
- **DB plumbing for Stage 1**: no new transaction abstraction. Use existing `execute_query(..., commit=False)` + `connection.commit()`.
- **Stages 1 and 2 ship as separate PRs** but all Stage 2 product decisions above must be locked before Stage 1 opens.

## Deferred To Future Phases

These were considered during planning and explicitly pushed out of the current hardening pass. **Do not expand stage scope to include them.** If a card's work accidentally touches one of these items, stop and escalate.

- **`workout_log` preservation across restore.** Currently the FK `workout_log.workout_plan_id → user_selection.id` is `ON DELETE CASCADE`, so wiping `user_selection` during restore also clears all logged sessions. Preserving history would require either a schema change (nullable FK, historical log archive table) or a soft-delete model. Product decision deferred — revisit only if users explicitly ask for it.
- **Restore modes beyond replace** (merge, append, per-routine restore). Out of scope — would reopen the restore UX entirely.
- **Backup export/import as JSON, pin, duplicate, compare-vs-current** (observation §7). Mature-feature items, not safety items.
- **Age-based auto-backup retention** ("last 30 days"). Current plan is count-only; age can be layered later without migration.
- **Stronger naming discipline** (uniqueness, validation beyond length). Revisit only if duplicate names create real confusion in practice.

## How To Execute A Task Card

Each task below is a self-contained card sized for a small-model agent (Sonnet-class, ~15–45 minutes of work). An agent can execute one card without re-reading the rest of this document, provided:

1. The **Decisions Locked** section above is treated as authoritative — do not reopen those questions.
2. Every task listed in **Depends on** is complete and merged.
3. The agent runs the **Verify** commands and confirms they pass before reporting done.

**Card fields**:
- `File(s)`: path(s) to touch. Line numbers reference the code on `redesign/calm-glass-2026` at the time of writing.
- `Depends on`: task IDs that must be merged first. `—` means no dependencies.
- `Parallel-safe`: `Yes` if this card can run in parallel with other open cards in the same stage; `No` if it mutates shared code another card will also touch.
- `Effort`: `Small` (< 30 min), `Medium` (30–90 min), `Large` (> 90 min — should be split before assigning).
- `Context`: the minimum background an agent needs. No implicit knowledge from other sections.
- `Steps`: sequential instructions. Follow in order.
- `Verify`: exact commands to run. Every one must pass before the card is considered done.
- `Rollback`: how to revert the card's changes locally if verification fails.

**Agent ground rules** (apply to every card):
- Never skip `Verify` commands. If one fails and the root cause is not obvious within 10 minutes, stop and escalate rather than workaround.
- Never introduce a new transaction wrapper, DB helper, or abstraction layer unless the card explicitly tells you to.
- Never broaden scope beyond the card — if you discover adjacent issues, note them in the PR description and leave them for a follow-up card.
- Match existing code style (logger pattern, response helpers, escape helpers). Do not reformat unrelated code.
- If a line number in a card is wrong because an earlier card shifted the file, trust the symbol (function name, element id) over the line number and proceed.

## Progress Snapshot

Completed in the current workspace:

- Stage 1: transactional restore safety
- Stage 2: restore safety copy, save-first flow, inline skipped-results panel, and warning states
- Stage 4: auto-backup retention and collision hardening
- Stage 5: metadata editing
- Stage 6: sorting and empty-save warning
- Stage 7: multi-line note rendering
- Stage 8: implementation cleanup and final verification
- Stage 9: post-implementation review follow-ups (partial-skipped E2E coverage, redundant DB close removal, markup-order verification, final baseline re-check)

Still pending:

- None — all stages from the current hardening pass are complete.

---

## Stage 0 — Baseline (run once before any stage begins)

### S0-T1: Record baseline test counts

- **Type**: Verification
- **Depends on**: —
- **Parallel-safe**: —
- **Effort**: Small
- **Context**: Every later card runs tests and compares against this baseline. If you do not record it now, you cannot confirm later cards did not regress.
- **Steps**:
  - [x] From repo root: `.venv/Scripts/python.exe -m pytest tests/ -q > baseline_pytest.txt 2>&1`
  - [x] From repo root: `npx playwright test --project=chromium --reporter=line > baseline_e2e.txt 2>&1`
  - [x] Copy the final "X passed" line from each file into the Stage 1 PR description.
- **Verify**: Both files exist and end with a "passed" summary. Counts ≥ the numbers in `CLAUDE.md §5` (913 pytest, 314 E2E).
- **Rollback**: `rm baseline_pytest.txt baseline_e2e.txt`

---

## Stage 1 — Transactional Restore Safety

**Status**: Completed in the current workspace.

**Stage goal**: `restore_backup` must succeed atomically or leave `user_selection` and `workout_log` fully intact.

### S1-T1: Wrap `restore_backup` in a single transaction

- **Type**: Backend refactor
- **File(s)**: `utils/program_backup.py`
- **Depends on**: S0-T1
- **Parallel-safe**: No (blocks all S1 test cards and all Stage 2 cards)
- **Effort**: Medium
- **Context**:
  - `DatabaseHandler.execute_query(query, params, *, commit=True)` lives at `utils/database.py:200`. Passing `commit=False` skips the per-statement commit.
  - The handler exposes `db.connection` for explicit `commit()` / `rollback()`.
  - Current flow in `restore_backup` (starting line 281): `DELETE FROM workout_log` (line 334) → `DELETE FROM user_selection` (line 335) → 4-branch per-item `INSERT` loop. Every statement auto-commits today.
  - `sqlite3` is already imported at the top of the file.
- **Steps**:
  - [x] Locate `restore_backup` at `utils/program_backup.py:281`.
  - [x] Before the `db.execute_query("DELETE FROM workout_log")` call, open a `try:` block.
  - [x] As the first line inside the try, add `db.execute_query("BEGIN IMMEDIATE", commit=False)`.
  - [x] Add `, commit=False` to each of these calls:
     - `DELETE FROM workout_log` (line 334)
     - `DELETE FROM user_selection` (line 335)
     - Every INSERT in the 4 if/elif/elif/else branches in the restore loop (~line 354 onward)
  - [x] After the `for item in items:` loop ends, add `db.connection.commit()`.
  - [x] Add `except sqlite3.Error: db.connection.rollback(); raise` at the end of the try block.
  - [x] Above the `DELETE FROM workout_log` line, add this single-line comment:
     `# FK CASCADE from user_selection also clears workout_log; explicit DELETE documents intent.`
  - [x] Leave the `skipped` list accumulation unchanged — skipping is not a failure.
- **Verify**:
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` — all existing tests pass.
  - Grep: occurrences of `commit=False` in `utils/program_backup.py` must be ≥ 7 (BEGIN + 2 DELETEs + 4 INSERT branches).
- **Rollback**: `git restore utils/program_backup.py`

### S1-T2: Test — rollback preserves active program on failure

- **Type**: Backend test
- **File(s)**: `tests/test_program_backup.py`
- **Depends on**: S1-T1
- **Parallel-safe**: Yes (does not conflict with S1-T3)
- **Effort**: Medium
- **Context**:
  - S1-T1 made restore atomic; this card proves rollback works.
  - Follow the pattern of the existing `test_restore_backup_replaces_active_program` (around line 116) for fixtures and seed data.
  - Pytest's `monkeypatch` fixture is available on every test.
- **Steps**:
  - [x] In `tests/test_program_backup.py`, add a new test `test_restore_rollback_preserves_active_program_on_failure` in the same class as `test_restore_backup_replaces_active_program`.
  - [x] Seed: create exercises A, B, C, D via `exercise_factory`. Create a backup holding A + B. Then modify the active plan to hold C + D (different from the backup).
  - [x] Monkeypatch `utils.program_backup.DatabaseHandler.execute_query` (or the bound method on the instance used by `restore_backup`) to raise `sqlite3.Error("forced")` on the 3rd call that matches `INSERT INTO user_selection`.
  - [x] Call `restore_backup(backup_id)` and assert it raises `sqlite3.Error`.
  - [x] Assert `user_selection` still contains C + D rows (not A + B, not empty).
  - [x] Assert no partial backup rows were inserted (count matches pre-restore count).
- **Verify**:
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py::TestProgramBackup::test_restore_rollback_preserves_active_program_on_failure -q` passes.
  - Full file still passes: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q`.
- **Rollback**: `git restore tests/test_program_backup.py`

### S1-T3: Test — single commit on success

- **Type**: Backend test
- **File(s)**: `tests/test_program_backup.py`
- **Depends on**: S1-T1
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: Proves the refactor actually batches commits into one call. Without this, a future regression could silently revert to per-statement commits.
- **Steps**:
  - [x] Add a new test `test_restore_commits_once_on_success` in the same class.
  - [x] Seed exercises + create a small backup (3 items).
  - [x] Use `unittest.mock.patch.object` (or monkeypatch) to wrap `sqlite3.Connection.commit` on the handler's connection with a counter.
  - [x] Call `restore_backup(backup_id)` and assert the commit count is exactly 1.
- **Verify**: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py::TestProgramBackup::test_restore_commits_once_on_success -q`.
- **Rollback**: `git restore tests/test_program_backup.py`

---

## Stage 2 — Pre-Restore Safety Flow + Destructive Copy + Skipped Visibility

**Status**: Completed in the current workspace.

**Stage goal**: Ship one PR that covers the restore confirmation copy update, the "save current plan first" option, inline skipped-exercise rendering, and the zero-restored warning state. These share the same confirmation markup — splitting them would require touching the UI twice.

**Stage-level prerequisites** (apply to every card in this stage; do not start any card until all are satisfied):
- Stage 1 (all of S1-T1/T2/T3) merged.
- Locked decisions from the **Decisions Locked** section above are in effect — do not reopen `workout_log` scope, zero-restored treatment, or duplicate-names rules.

### S2-T1: Update restore confirmation copy

- **Type**: Frontend text change
- **File(s)**: `static/js/modules/backup-center.js`
- **Depends on**: —
- **Parallel-safe**: No (other S2 cards also edit `showPendingAction`)
- **Effort**: Small
- **Context**: `showPendingAction` at line 366 sets the confirmation title and body text based on `pendingAction`. Current restore text (line 380) only mentions replacing the workout plan; it should also mention that logged sessions are cleared.
- **Steps**:
  - [x] Open `static/js/modules/backup-center.js`.
  - [x] In `showPendingAction`, find the `if (type === 'restore')` branch (line 378).
  - [x] Replace the existing `textEl.textContent = \`Restore "${selectedBackupDetails.name}" and replace the current workout plan?\`` with:
     `textEl.textContent = \`Restore "${selectedBackupDetails.name}"? The current workout plan and all logged sessions will be cleared.\``
- **Verify**:
  - Grep: `grep -n "Logged sessions\|logged sessions" static/js/modules/backup-center.js` — returns the new copy line.
  - Playwright for existing restore spec still passes: `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line`.
- **Rollback**: `git restore static/js/modules/backup-center.js`

### S2-T2: Add `#backup-restore-save-first` button to the confirmation panel

- **Type**: Template markup
- **File(s)**: `templates/backup.html`
- **Depends on**: —
- **Parallel-safe**: No (S2-T3 edits the same markup region)
- **Effort**: Small
- **Context**: The confirmation panel `#backup-action-confirm` lives at `templates/backup.html:163`. Its `.backup-action-buttons` container (line 168) currently holds Cancel + Confirm. We need a new secondary button that only appears for restore intents.
- **Steps**:
  - [x] Open `templates/backup.html`.
  - [x] Inside `.backup-action-buttons` (line 168), **before** `#backup-action-cancel`, add:
     ```html
     <button type="button" id="backup-restore-save-first" class="btn btn-outline-primary btn-calm-ghost" hidden>
       <i class="fas fa-shield-alt" aria-hidden="true"></i> Save current plan first
     </button>
     ```
  - [x] Leave Cancel and Confirm buttons as-is.
- **Verify**:
  - Grep: `grep -n "backup-restore-save-first" templates/backup.html` — one hit.
  - Page still renders: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py::test_backup_center_page_renders -q`.
- **Rollback**: `git restore templates/backup.html`

### S2-T3: Wire "Save current plan first" handler

- **Type**: Frontend logic
- **File(s)**: `static/js/modules/backup-center.js`
- **Depends on**: S2-T1, S2-T2
- **Parallel-safe**: No
- **Effort**: Medium
- **Context**:
  - `createBackup(name, note)` is already imported from `./program-backup.js` and used in `handleSaveSubmit`.
  - `showPendingAction` shows/hides the confirmation panel.
  - `handleConfirmAction` is the confirm-click handler.
  - The new button from S2-T2 must be shown only when `pendingAction === 'restore'` and hidden for delete.
- **Steps**:
  - [x] In `showPendingAction`, after setting the confirm button classes:
     - If `type === 'restore'`: unhide `#backup-restore-save-first` (`.hidden = false`).
     - Else: hide it (`.hidden = true`).
  - [x] In `clearPendingAction` (line 127), also hide `#backup-restore-save-first`.
  - [x] In `initializeBackupCenter` (line 525), add a handler for `#backup-restore-save-first` click:
     - Disable both the save-first and confirm buttons while running.
     - Build a timestamp: `const stamp = new Date().toISOString().replace('T', ' ').slice(0, 19);`
     - Call `await createBackup(\`Pre-restore snapshot (${stamp})\`, 'Automatic snapshot taken before restore')`.
     - On success: show a success toast ("Current plan saved as …"), re-enable buttons, and call `await refreshBackupCenter({ preserveSelection: true, preferredSelectionId: selectedBackupDetails.id })`.
     - On error: show error toast with the message, re-enable buttons, do **not** dispatch the restore.
- **Verify**:
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` still passes.
  - Grep: `grep -n "Pre-restore snapshot" static/js/modules/backup-center.js` — one hit.
- **Rollback**: `git restore static/js/modules/backup-center.js`

### S2-T4: Add `#backup-restore-result` inline panel

- **Type**: Template markup
- **File(s)**: `templates/backup.html`
- **Depends on**: —
- **Parallel-safe**: No (S2-T5 populates this element)
- **Effort**: Small
- **Context**: We need a dedicated element in the detail panel where skipped-exercise names and zero-restored warnings will render. It must be hidden by default.
- **Steps**:
  - [x] Open `templates/backup.html`.
  - [x] **After** the `#backup-action-confirm` block (closes at line 172) and **before** `.backup-detail-table-wrap` (line 174), insert:
     ```html
     <div id="backup-restore-result" class="backup-restore-result" role="status" hidden>
       <p id="backup-restore-result-title" class="backup-restore-result-title"></p>
       <ul id="backup-restore-result-list" class="backup-restore-result-list"></ul>
     </div>
     ```
- **Verify**:
  - Grep: `grep -n "backup-restore-result" templates/backup.html` — 4 hits (container id + title id + list id + class).
  - Page renders test still green.
- **Rollback**: `git restore templates/backup.html`

### S2-T5: Render skipped names + zero-restored warning after restore

- **Type**: Frontend logic
- **File(s)**: `static/js/modules/backup-center.js`
- **Depends on**: S2-T4, S2-T1, S2-T3
- **Parallel-safe**: No
- **Effort**: Medium
- **Context**:
  - `handleConfirmAction` (line 446) currently consumes `result` from `restoreBackup` and shows a toast. We want it to also populate `#backup-restore-result`.
  - `result` shape: `{ restored_count, skipped: [name, ...], backup_name, backup_id }`.
  - Zero-restored = warning state (distinct copy, no success styling, toast uses `warning` level).
  - `renderBackupDetails` (line 242) currently calls `clearPendingAction()` — this must also clear the restore-result panel on selection change.
- **Steps**:
  - [x] In `handleConfirmAction`, after `const result = await restoreBackup(...)`, extract a helper `renderRestoreResult(result)` that:
     - Gets `#backup-restore-result`, `#backup-restore-result-title`, `#backup-restore-result-list`.
     - If `result.restored_count === 0`:
       - Title: `"Nothing was restored — every exercise is missing from the catalog."`
       - List: render each skipped name as `<li>`.
       - Add class `is-warning` to `#backup-restore-result`.
     - Else if `result.skipped.length > 0`:
       - Title: `"${result.restored_count} exercises restored. ${result.skipped.length} skipped because they are no longer in the catalog:"`
       - List: render each skipped name as `<li>` (escape with `escapeHtml`).
       - Remove `is-warning` class (use success styling).
     - Else:
       - Title: `"Restored ${result.restored_count} exercises from \"${result.backup_name}\"."`
       - Clear the list.
       - Remove `is-warning` class.
     - Unhide the panel.
  - [x] Call `renderRestoreResult(result)` inside `handleConfirmAction` right before the toast.
  - [x] Change the toast level: use `showToast('warning', message)` when `result.restored_count === 0`; keep `success` for the other two cases.
  - [x] In `renderBackupDetails` (line 242) and `renderEmptyDetail` (line 197), hide `#backup-restore-result` (`.hidden = true`, remove `is-warning`, clear list) so switching selection clears the stale result.
- **Verify**:
  - Grep: `grep -n "renderRestoreResult\|is-warning" static/js/modules/backup-center.js` — at least 3 hits.
  - Existing test passes: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q`.
- **Rollback**: `git restore static/js/modules/backup-center.js`

### S2-T6: Style the restore-result panel

- **Type**: CSS
- **File(s)**: `static/css/pages-backup.css`
- **Depends on**: S2-T4
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: The panel needs a subtle background and clear warning state. Follow existing `frame-calm-*` conventions in the file; do not add new color tokens.
- **Steps**:
  - [x] Open `static/css/pages-backup.css`.
  - [x] Add rules at the end:
     - `.backup-restore-result` — block spacing, border-radius, neutral background (reuse existing tokens).
     - `.backup-restore-result.is-warning` — warning-tone background + icon accent.
     - `.backup-restore-result-title` — readable text size, margin-bottom.
     - `.backup-restore-result-list` — bulleted, tight line-height, no horizontal scroll.
  - [x] Keep total additions under ~40 lines; do not introduce new imports.
- **Verify**:
  - Visual check in browser at `/backup` — panel renders when triggered via console `document.getElementById('backup-restore-result').hidden = false`.
  - `npm run build:css` if the CSS goes through the Bootstrap build; otherwise skip.
- **Rollback**: `git restore static/css/pages-backup.css`

### S2-T7: Playwright — pre-restore save creates snapshot

- **Type**: E2E test
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S2-T3
- **Parallel-safe**: Yes (separate test)
- **Effort**: Medium
- **Context**: Follow the patterns in the existing file (restore + delete test at line 87). Use the API setup helpers already in the spec.
- **Steps**:
  - [x] Add `test('pre-restore save option creates a snapshot before restoring')` in the "Backup Center Page" describe block.
  - [x] Seed via the API: create exercise, add to active plan, create a backup "A".
  - [x] Navigate to `/backup`, select backup A, click Restore, then click `#backup-restore-save-first`.
  - [x] Wait for the success toast.
  - [x] Assert via `request.get('/api/backups')` that a backup whose name starts with `Pre-restore snapshot` exists.
- **Verify**: `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line` passes.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

### S2-T8: Playwright — skipped names + zero-restored + warning copy

- **Type**: E2E test
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S2-T5
- **Parallel-safe**: Yes
- **Effort**: Medium
- **Context**: One card covering the three restore-result assertions so the seed setup can be shared.
- **Steps**:
  - [x] Add `test('restore confirmation copy mentions logged sessions')` — open confirm panel, assert `#backup-action-text` contains `"logged sessions"`.
  - [x] Add `test('restore with missing exercises shows skipped names inline')` — seed exercises X, Y; create backup with both; delete X via `DELETE /api/exercises/X` (or direct DB); run restore; assert `#backup-restore-result` visible and `#backup-restore-result-list` contains an `<li>` with text `X`.
  - [x] Add `test('zero-restored restore shows warning state')` — seed backup whose exercises are all removed before restore; run restore; assert `#backup-restore-result` has class `is-warning` and title includes "every exercise is missing".
- **Verify**: `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line` passes.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

---

## Stage 4 — Auto-Backup Retention + Collision Hardening

**Status**: Completed in the current workspace.

**Stage goal**: Auto-backups cannot collide on same-second creation, and they are capped at the latest 10. Manual backups are never pruned.

**Stage-level prerequisites**: Stage 1 (all cards) merged. Locked decisions in effect (retention = count-based, keep = 10).

### S4-T1: Add optional `db` parameter to `create_backup`

- **Type**: Backend refactor (signature-compatible)
- **File(s)**: `utils/program_backup.py`
- **Depends on**: —
- **Parallel-safe**: No (S4-T3 and S4-T4 depend on this)
- **Effort**: Medium
- **Context**:
  - `create_backup` (line 109) currently opens its own `DatabaseHandler` via `with DatabaseHandler() as db:` (line 134).
  - For atomic create+prune (S4-T4), the caller needs to share a handler.
  - `initialize_backup_tables` (line 22) already accepts an optional `db` — follow that pattern exactly.
- **Steps**:
  - [x] Change the signature from `def create_backup(name, note=None, backup_type="manual")` to `def create_backup(name, note=None, backup_type="manual", db: Optional[DatabaseHandler] = None)`.
  - [x] Apply the same `should_close` pattern used in `initialize_backup_tables`:
     ```python
     should_close = False
     if db is None:
         db = DatabaseHandler()
         db.__enter__()
         should_close = True
     try:
         # existing body — reuse `db` instead of `with DatabaseHandler() as db:`
         ...
     finally:
         if should_close:
             db.__exit__(None, None, None)
     ```
  - [x] Keep the INSERTs committed as-is (no `commit=False` here — that happens in S4-T4 for the atomic flow).
  - [x] Confirm `Optional` is imported from `typing` (already is — line 11).
- **Verify**:
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` — all existing tests pass unchanged.
  - Grep: `grep -n "def create_backup" utils/program_backup.py` shows the new signature with `db:` param.
- **Rollback**: `git restore utils/program_backup.py`

### S4-T2: Sub-second precision on auto-backup names

- **Type**: Backend fix
- **File(s)**: `utils/program_backup.py`
- **Depends on**: —
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: `UNIQUE(name, created_at)` on `program_backups` (line 45) collides if two auto-backups are created in the same second. `created_at` is also second-resolution in SQLite's default timestamp, but the safer fix is to make the *name* unique per call.
- **Steps**:
  - [x] In `create_auto_backup_before_erase` (line 494), change the timestamp format from `"%Y-%m-%d %H:%M:%S"` to `"%Y-%m-%d %H:%M:%S.%f"`.
  - [x] No other change needed — the name template already includes the timestamp.
- **Verify**:
  - Grep: `grep -n "%H:%M:%S.%f" utils/program_backup.py` — one hit.
  - Existing tests still pass.
- **Rollback**: `git restore utils/program_backup.py`

### S4-T3: Add `prune_auto_backups` function

- **Type**: Backend addition
- **File(s)**: `utils/program_backup.py`
- **Depends on**: S4-T1
- **Parallel-safe**: Yes
- **Effort**: Medium
- **Context**:
  - Deletes auto-backups beyond the most recent `keep_count`. FK `ON DELETE CASCADE` on `program_backup_items` (line 64) removes child rows automatically.
  - Must accept an optional shared `db` handler (same pattern as S4-T1).
- **Steps**:
  - [x] Add this function near `get_latest_auto_backup`:
     ```python
     def prune_auto_backups(keep_count: int = 10, db: Optional[DatabaseHandler] = None) -> int:
         """Delete auto-backups beyond the latest `keep_count`. Manual backups are never touched.

         Returns the number of rows deleted.
         """
         should_close = False
         if db is None:
             db = DatabaseHandler()
             db.__enter__()
             should_close = True
         try:
             rowcount = db.execute_query(
                 """
                 DELETE FROM program_backups
                  WHERE backup_type = 'auto'
                    AND id NOT IN (
                          SELECT id FROM program_backups
                           WHERE backup_type = 'auto'
                           ORDER BY created_at DESC
                           LIMIT ?
                        )
                 """,
                 (keep_count,),
             )
             logger.info("Pruned auto-backups", extra={'kept': keep_count, 'deleted': rowcount})
             return rowcount
         finally:
             if should_close:
                 db.__exit__(None, None, None)
     ```
  - [x] Do not call it yet — S4-T4 wires it up atomically.
- **Verify**:
  - Grep: `grep -n "def prune_auto_backups" utils/program_backup.py` — one hit.
  - Existing tests pass.
- **Rollback**: `git restore utils/program_backup.py`

### S4-T4: Atomic create+prune in `create_auto_backup_before_erase`

- **Type**: Backend refactor
- **File(s)**: `utils/program_backup.py`
- **Depends on**: S4-T1, S4-T2, S4-T3
- **Parallel-safe**: No
- **Effort**: Medium
- **Context**: Create + prune must succeed as one transaction. If prune fails, the newly created auto-backup should not linger.
- **Steps**:
  - [x] In `create_auto_backup_before_erase` (line 494), replace the single `return create_backup(...)` call at the end with:
     ```python
     with DatabaseHandler() as db:
         db.execute_query("BEGIN IMMEDIATE", commit=False)
         try:
             backup = create_backup(
                 name=backup_name,
                 note="Automatically created before erase/reset operation",
                 backup_type="auto",
                 db=db,
             )
             prune_auto_backups(keep_count=10, db=db)
             db.connection.commit()
             return backup
         except sqlite3.Error:
             db.connection.rollback()
             raise
     ```
  - [x] Make sure the empty-plan early-return at the top of the function stays unchanged.
- **Verify**:
  - Manual smoke: from a Python REPL with the app env, call `create_auto_backup_before_erase()` twice rapidly — both succeed.
  - All existing tests pass: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q`.
- **Rollback**: `git restore utils/program_backup.py`

### S4-T5: Tests — collision, retention, cascade, atomic

- **Type**: Backend tests
- **File(s)**: `tests/test_program_backup.py`
- **Depends on**: S4-T4
- **Parallel-safe**: Yes (one card with several tests — they share fixtures)
- **Effort**: Medium
- **Context**: Follow the existing `create_auto_backup` tests (around line 240) for fixture usage.
- **Steps**:
  - [x] Add `test_two_auto_backups_same_second_both_succeed` — monkeypatch `datetime.datetime.now` (or `datetime.now` depending on import) to return a fixed second across two calls; call `create_auto_backup_before_erase()` twice; assert both backups exist and have distinct names.
  - [x] Add `test_auto_backup_retention_keeps_latest_n` — seed an active plan; call `create_auto_backup_before_erase()` 12 times (advance mocked time microseconds per call); assert `list_backups()` returns exactly 10 auto-backups.
  - [x] Add `test_auto_backup_retention_ignores_manual` — create 12 manual backups and then trigger 3 auto-backup creations; assert all 12 manual backups remain.
  - [x] Add `test_auto_backup_prune_cascades_items` — after retention runs, assert `SELECT COUNT(*) FROM program_backup_items WHERE backup_id NOT IN (SELECT id FROM program_backups)` returns 0 (no orphan items).
  - [x] Add `test_create_plus_prune_atomic_on_failure` — monkeypatch `prune_auto_backups` to raise `sqlite3.Error`; call `create_auto_backup_before_erase()`; expect the error to propagate and assert `list_backups()` count is unchanged (new backup was rolled back).
- **Verify**: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` — all old + 5 new tests pass.
- **Rollback**: `git restore tests/test_program_backup.py`

---

## Stage 5 — Backup Metadata Editing (Rename + Note)

**Status**: Completed in the current workspace.

**Stage goal**: Users can rename a backup and edit its note inline from the detail panel. Duplicate names allowed.

**Stage-level prerequisites**: Locked decisions in effect (duplicates allowed, validation parity).

### S5-T1: Add `update_backup_metadata` util

- **Type**: Backend addition
- **File(s)**: `utils/program_backup.py`
- **Depends on**: —
- **Parallel-safe**: Yes
- **Effort**: Medium
- **Context**: A single function that updates `name` and/or `note` while preserving `id`, `created_at`, and `backup_type`. Returns the updated row.
- **Steps**:
  - [x] Add this function after `delete_backup`:
     ```python
     def update_backup_metadata(
         backup_id: int,
         name: Optional[str] = None,
         note: Optional[str] = None,
     ) -> Optional[Dict[str, Any]]:
         """Update name and/or note on a backup. Returns the updated row or None if not found."""
         if name is None and note is None:
             raise ValueError("At least one of 'name' or 'note' must be provided")
         if name is not None:
             name = name.strip()
             if not name:
                 raise ValueError("Backup name cannot be empty")
             if len(name) > 100:
                 raise ValueError("Backup name must be 100 characters or fewer")
         if note is not None and len(note) > 500:
             raise ValueError("Backup note must be 500 characters or fewer")

         with DatabaseHandler() as db:
             existing = db.fetch_one(
                 "SELECT id, name, note FROM program_backups WHERE id = ?",
                 (backup_id,),
             )
             if not existing:
                 return None

             updates = []
             params: list = []
             if name is not None:
                 updates.append("name = ?")
                 params.append(name)
             if note is not None:
                 updates.append("note = ?")
                 params.append(note)
             params.append(backup_id)

             db.execute_query(
                 f"UPDATE program_backups SET {', '.join(updates)} WHERE id = ?",
                 tuple(params),
             )

             logger.info(
                 "Backup metadata updated",
                 extra={
                     'backup_id': backup_id,
                     'old_name': existing['name'],
                     'new_name': name if name is not None else existing['name'],
                     'note_changed': note is not None,
                 },
             )

             row = db.fetch_one(
                 """
                 SELECT id, name, note, backup_type, schema_version, item_count, created_at
                   FROM program_backups WHERE id = ?
                 """,
                 (backup_id,),
             )
             return dict(row) if row else None
     ```
- **Verify**:
  - Grep: `grep -n "def update_backup_metadata" utils/program_backup.py` — one hit.
  - Existing tests pass.
- **Rollback**: `git restore utils/program_backup.py`

### S5-T2: Add `PATCH /api/backups/<id>` route

- **Type**: Backend route
- **File(s)**: `routes/program_backup.py`
- **Depends on**: S5-T1
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**:
  - Route must use `success_response` / `error_response` helpers (see `.claude/rules/routes.md`).
  - Validation limits **must match** `templates/backup.html:76,86` (`maxlength="100"` for name, `maxlength="500"` for note).
- **Steps**:
  - [x] At the top of `routes/program_backup.py`, add `update_backup_metadata` to the imports from `utils.program_backup`.
  - [x] Add this route after `api_delete_backup`:
     ```python
     @program_backup_bp.route('/api/backups/<int:backup_id>', methods=['PATCH'])
     def api_update_backup(backup_id: int):
         try:
             data = request.get_json() or {}
             if 'name' not in data and 'note' not in data:
                 return error_response("VALIDATION_ERROR", "At least one of 'name' or 'note' must be provided", 400)

             name = data.get('name')
             note = data.get('note')

             try:
                 updated = update_backup_metadata(backup_id, name=name, note=note)
             except ValueError as e:
                 return error_response("VALIDATION_ERROR", str(e), 400)

             if updated is None:
                 return error_response("NOT_FOUND", f"Backup with id {backup_id} not found", 404)

             return jsonify(success_response(data=updated, message="Backup updated"))
         except Exception:
             logger.exception(f"Error updating backup {backup_id}")
             return error_response("INTERNAL_ERROR", "Failed to update backup", 500)
     ```
- **Verify**:
  - Page still loads (no import errors): `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py::test_backup_center_page_renders -q`.
  - Grep: `grep -n "methods=\['PATCH'\]" routes/program_backup.py` — one hit.
- **Rollback**: `git restore routes/program_backup.py`

### S5-T3: Unit tests for PATCH endpoint

- **Type**: Backend tests
- **File(s)**: `tests/test_program_backup.py`
- **Depends on**: S5-T2
- **Parallel-safe**: Yes
- **Effort**: Medium
- **Context**: Follow the existing API test patterns (`test_api_delete_backup` at line 405).
- **Steps**:
  - [x] Add `test_api_patch_backup_updates_name` — create backup, PATCH with `{'name': 'new name'}`, assert 200 and name changed on refetch.
  - [x] Add `test_api_patch_backup_updates_note` — PATCH with `{'note': 'new note'}`, assert 200 and note changed.
  - [x] Add `test_api_patch_backup_rejects_empty_name` — PATCH with `{'name': ''}`, expect 400 and `VALIDATION_ERROR`.
  - [x] Add `test_api_patch_backup_rejects_oversized_name` — PATCH with 101-char name, expect 400.
  - [x] Add `test_api_patch_backup_rejects_oversized_note` — PATCH with 501-char note, expect 400.
  - [x] Add `test_api_patch_backup_not_found` — PATCH on nonexistent id, expect 404.
  - [x] Add `test_api_patch_preserves_created_at_and_id` — PATCH name; assert `id`, `created_at`, `backup_type` unchanged.
- **Verify**: `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` — all existing + 7 new tests pass.
- **Rollback**: `git restore tests/test_program_backup.py`

### S5-T4: Add `updateBackupMetadata` JS helper

- **Type**: Frontend addition
- **File(s)**: `static/js/modules/program-backup.js`
- **Depends on**: S5-T2
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: Follow the pattern of `createBackup` (line 42) exactly. `api` is imported from `./fetch-wrapper.js`; `api.patch` may not exist — check by grepping `api.patch\|api\.` in `static/js/modules/fetch-wrapper.js` first and add a `patch` method there if missing (mirror `post`).
- **Steps**:
  - [x] If `fetch-wrapper.js` lacks `api.patch`, add it (copy `post`, change method to `PATCH`).
  - [x] Add to `program-backup.js`:
     ```javascript
     export async function updateBackupMetadata(backupId, { name, note }) {
         const payload = {};
         if (name !== undefined) payload.name = name;
         if (note !== undefined) payload.note = note;
         try {
             const data = await api.patch(`/api/backups/${backupId}`, payload, { showErrorToast: false });
             return data.data !== undefined ? data.data : data;
         } catch (error) {
             console.error('Error updating backup metadata:', error);
             throw error;
         }
     }
     ```
- **Verify**: Manual import check in browser devtools on `/backup` — `import('/static/js/modules/program-backup.js').then(m => typeof m.updateBackupMetadata)` returns `"function"`.
- **Rollback**: `git restore static/js/modules/program-backup.js static/js/modules/fetch-wrapper.js`

### S5-T5: Inline edit UI for name + note

- **Type**: Frontend + template
- **File(s)**: `templates/backup.html`, `static/js/modules/backup-center.js`, `static/css/pages-backup.css`
- **Depends on**: S5-T4
- **Parallel-safe**: No (touches multiple files; ship as one card)
- **Effort**: Medium
- **Context**: Must not introduce a modal. Optimistic update: update local cache + UI immediately, revert on error.
- **Steps**:
  - [x] In `templates/backup.html`, add edit pencil buttons next to `#backup-detail-name` and after `#backup-detail-note`:
     ```html
     <button type="button" id="backup-detail-edit-name" class="btn btn-sm btn-calm-ghost" aria-label="Rename backup">
       <i class="fas fa-pen" aria-hidden="true"></i>
     </button>
     ```
     (same pattern for `#backup-detail-edit-note`).
  - [x] In `backup-center.js`, import `updateBackupMetadata`.
  - [x] Add handler functions:
     - `enterEditMode(field)`: replace target element with `<input maxlength="100">` or `<textarea maxlength="500">` pre-filled with current value; show Save / Cancel buttons.
     - `commitEdit(field, newValue)`: call `updateBackupMetadata(selectedBackupDetails.id, { [field]: newValue })`; on success update `backupsCache` entry + `selectedBackupDetails` + call `renderBackupDetails(selectedBackupDetails)` and `renderBackupList()`; on failure show toast and exit edit mode without changes.
  - [x] Wire edit buttons in `initializeBackupCenter`.
  - [x] Add minimal CSS in `pages-backup.css` for the edit buttons (inline-align with heading, hover tint).
- **Verify**:
  - Page still renders, existing tests pass.
  - Manual smoke in browser: click edit on a backup name, change it, save — value updates without page reload.
- **Rollback**: `git restore templates/backup.html static/js/modules/backup-center.js static/css/pages-backup.css`

### S5-T6: Playwright — rename persists on reload

- **Type**: E2E test
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S5-T5
- **Parallel-safe**: Yes
- **Effort**: Small
- **Steps**:
  - [x] Add `test('rename backup from detail panel persists on reload')` in the Backup Center describe block.
  - [x] Seed a backup named "Before".
  - [x] Navigate to `/backup`, select it, click edit-name, type "After", click Save.
  - [x] Reload page, assert the backup in the library renders as "After".
- **Verify**: `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line` passes.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

---

## Stage 6 — Sort Controls + Empty-Backup Warning

**Status**: Completed in the current workspace.

**Stage goal**: Library sortable by Newest / Oldest / Name A–Z / Name Z–A with preference persisted. Empty saves require explicit re-confirm in the UI.

**Stage-level prerequisites**: Locked decisions (empty-backup = warn-only, backend stays lenient).

### S6-T1: Sort dropdown markup + JS sort logic + localStorage

- **Type**: Frontend
- **File(s)**: `templates/backup.html`, `static/js/modules/backup-center.js`
- **Depends on**: —
- **Parallel-safe**: No (same JS file as other stages; check for rebase conflicts)
- **Effort**: Medium
- **Context**:
  - `getVisibleBackups` (line 64) currently filters but does not sort — the DOM order relies on `backupsCache` coming in newest-first from the API.
  - `localStorage` is available globally.
  - `pages-backup.css` already has `.backup-library-controls` styling.
- **Steps**:
  - [x] In `templates/backup.html`, add a sort `<select>` inside `.backup-library-controls` (line 106) before the filter group:
     ```html
     <label class="visually-hidden" for="backup-sort">Sort backups</label>
     <select id="backup-sort" class="form-select input-calm-inset backup-sort-select">
       <option value="newest">Newest first</option>
       <option value="oldest">Oldest first</option>
       <option value="name-asc">Name A–Z</option>
       <option value="name-desc">Name Z–A</option>
     </select>
     ```
  - [x] In `backup-center.js`:
     - Add constant `const SORT_PREF_KEY = 'backupCenter.sortPreference';`
     - At the top of `initializeBackupCenter`, restore the preference: read localStorage, set `#backup-sort.value`.
     - In `getVisibleBackups`, after filtering, read the current select value and sort accordingly.
     - Add a `change` listener on `#backup-sort` that saves to localStorage and calls `renderBackupList()`.
  - [x] Default to `"newest"` when no preference is stored.
- **Verify**:
  - Grep: `grep -n "backupCenter.sortPreference" static/js/modules/backup-center.js` — one hit.
  - Existing pytest + playwright all pass.
- **Rollback**: `git restore templates/backup.html static/js/modules/backup-center.js`

### S6-T2: Empty-backup inline warning in save flow

- **Type**: Frontend
- **File(s)**: `templates/backup.html`, `static/js/modules/backup-center.js`
- **Depends on**: —
- **Parallel-safe**: No
- **Effort**: Small
- **Context**: Backend stays lenient per locked decisions. Warning is a two-click gate.
- **Steps**:
  - [x] In `templates/backup.html`, inside `#backup-save-panel` after the form actions (line 95), add:
     ```html
     <div id="backup-save-empty-warning" class="backup-save-warning" role="alert" hidden>
       Your active plan is empty. Saving now will create an empty snapshot. Click Save again to confirm.
     </div>
     ```
  - [x] In `backup-center.js` / `handleSaveSubmit` (line 393):
     - Before `createBackup`, read `#backup-active-count` text content.
     - If the count parses to `0` and a module-level flag `emptyWarningShown` is `false`, set the flag, unhide the warning, re-enable the submit button, and `return` (do not dispatch the create).
     - If the flag is `true`, proceed with `createBackup` and reset the flag + hide the warning after the request resolves (success or error).
     - On a successful save, hide the warning and reset the flag regardless.
  - [x] Add minimal CSS in `pages-backup.css` for `.backup-save-warning` (warning-tone background, padding).
- **Verify**:
  - Grep: `grep -n "backup-save-empty-warning" static/js/modules/backup-center.js templates/backup.html` — at least two hits.
  - Existing tests pass.
- **Rollback**: `git restore templates/backup.html static/js/modules/backup-center.js static/css/pages-backup.css`

### S6-T3: Playwright — sort tests

- **Type**: E2E tests
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S6-T1
- **Parallel-safe**: Yes
- **Effort**: Medium
- **Steps**:
  - [x] Add `test('sort by Name A-Z reorders library')` — seed backups named "Zebra", "Apple", "Mango". Select "Name A–Z". Assert DOM order is Apple, Mango, Zebra.
  - [x] Add `test('sort preference persists across reload')` — select "Oldest first", reload page, assert `#backup-sort` value is `"oldest"` after reload.
- **Verify**: `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line` passes.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

### S6-T4: Playwright — empty-backup warning

- **Type**: E2E test
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S6-T2
- **Parallel-safe**: Yes
- **Effort**: Small
- **Steps**:
  - [x] Add `test('saving with zero active exercises shows warning and requires re-confirm')`.
  - [x] Clear the active plan via API/DB so `active_program_count == 0`.
  - [x] Navigate to `/backup`, fill the save form, click Save.
  - [x] Assert `#backup-save-empty-warning` is visible; assert no new backup was created.
  - [x] Click Save again; assert warning hidden and a new (empty) backup exists.
- **Verify**: Spec passes.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

---

## Stage 7 — Multi-Line Note Rendering

**Status**: Completed in the current workspace.

**Stage goal**: Note newlines preserved visually without reintroducing an `innerHTML` path.

### S7-T1: Switch `innerHTML` → `textContent` + add `white-space: pre-wrap`

- **Type**: Frontend bugfix
- **File(s)**: `static/js/modules/backup-center.js`, `static/css/pages-backup.css`
- **Depends on**: —
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: Line 264 currently uses `noteEl.innerHTML = escapeHtml(backup.note)` which is XSS-safe but collapses newlines in HTML. Switching to `textContent` preserves `\n` and is still XSS-safe.
- **Steps**:
  - [x] In `backup-center.js:264`, replace `noteEl.innerHTML = escapeHtml(backup.note);` with `noteEl.textContent = backup.note;`
  - [x] If any other path renders notes via `innerHTML` (grep `note.*innerHTML`), apply the same change.
  - [x] In `pages-backup.css`, find `.backup-detail-note` (or add it) and include `white-space: pre-wrap;`.
- **Verify**:
  - Grep: `grep -n "noteEl.innerHTML\|innerHTML.*note" static/js/modules/backup-center.js` — zero hits after the change.
  - Grep: `grep -n "white-space: pre-wrap" static/css/pages-backup.css` — at least one hit.
  - Existing tests pass.
- **Rollback**: `git restore static/js/modules/backup-center.js static/css/pages-backup.css`

### S7-T2: Playwright — multi-line note renders

- **Type**: E2E test
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S7-T1
- **Parallel-safe**: Yes
- **Effort**: Small
- **Steps**:
  - [x] Add `test('multi-line note renders with preserved line breaks')`.
  - [x] Create a backup via API with note `"Line 1\nLine 2"`.
  - [x] Navigate to `/backup`, select it, assert `#backup-detail-note.textContent` contains `"\n"` and its rendered height is greater than the single-line height.
- **Verify**: Spec passes.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

---

## Stage 8 — Implementation Cleanup

**Status**: Completed in the current workspace.

**Stage goal**: Remove dead code paths and redundant init work identified during review.

**Stage-level prerequisites**: Stages 1–7 merged. `schema_version` decision locked (choose option (a) *stop writing* or (b) *keep + add TODO*) before starting S8-T3.

### S8-T1: Remove dead `IntegrityError` branch in restore loop

- **Type**: Backend cleanup
- **File(s)**: `utils/program_backup.py`
- **Depends on**: Stage 1 merged
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: Lines 423–428 catch `sqlite3.IntegrityError` and add a `"(duplicate)"` entry to `skipped`. `user_selection` has no UNIQUE constraint beyond `id`, so this branch is unreachable under normal conditions. Confirmed by grep: `grep -n "UNIQUE\|CREATE UNIQUE" utils/db_initializer.py` — no UNIQUE on `user_selection`.
- **Steps**:
  - [x] Delete the `except sqlite3.IntegrityError` block in the restore loop.
  - [x] Keep the outer try/except from S1-T1 (the transaction rollback path).
  - [x] Remove any test that only covers this branch. Expected: none, since it is unreachable.
- **Verify**:
  - Grep: `grep -n "(duplicate)" utils/program_backup.py tests/test_program_backup.py` — zero hits.
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` passes unchanged.
- **Rollback**: `git restore utils/program_backup.py`

### S8-T2: Remove redundant `initialize_backup_tables` calls

- **Type**: Backend cleanup
- **File(s)**: `utils/program_backup.py`
- **Depends on**: —
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**: `init_backup_tables()` in `routes/program_backup.py:201` is called at app startup. The in-function calls at lines 136 (`create_backup`) and 234 (`list_backups`) are redundant.
- **Steps**:
  - [x] Delete `initialize_backup_tables(db)` inside `create_backup` (line 136).
  - [x] Delete `initialize_backup_tables(db)` inside `list_backups` (line 234).
  - [x] Delete `initialize_backup_tables(db)` inside `get_latest_auto_backup` if present (line 538).
  - [x] Leave the definition of `initialize_backup_tables` untouched — it is still called from startup.
- **Verify**:
  - Full suite: `.venv/Scripts/python.exe -m pytest tests/ -q`.
  - `conftest.py` should already call `initialize_backup_tables` in test setup — confirm by grep.
- **Rollback**: `git restore utils/program_backup.py`

### S8-T3: Apply `schema_version` decision

- **Type**: Backend cleanup
- **File(s)**: `utils/program_backup.py`
- **Depends on**: Schema version decision locked (prerequisite).
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**:
  - `BACKUP_SCHEMA_VERSION = 1` is written on create (line 172) and read on list/get, but never consumed by any migration logic.
  - Decision options: (a) stop writing it and remove the column from reads, (b) keep it and add a TODO comment naming the expected first consumer.
- **Steps (option a — stop writing)**:
  - [ ] Remove the `schema_version` column from the CREATE TABLE (line 37) — but only if the column can be dropped without breaking existing DBs. Otherwise, keep the column but stop referencing it in Python.
  - [ ] Remove `schema_version` from all INSERT and SELECT column lists in this file.
  - [ ] Remove `BACKUP_SCHEMA_VERSION` constant.
  - [ ] Update `renderBackupDetails` in `backup-center.js` to stop showing the schema value.
- **Steps (option b — keep + TODO)**:
  - [x] Above `BACKUP_SCHEMA_VERSION = 1` (line 19), add:
     ```python
     # TODO: schema_version is written but not yet consumed. First consumer should
     # read it in restore_backup to trigger field migration. Until then it is purely
     # informational.
     ```
  - [x] Leave all other code as-is.
- **Verify**: Full suite passes.
- **Rollback**: `git restore utils/program_backup.py static/js/modules/backup-center.js`

### S8-T4: Verify baseline — final suite check

- **Type**: Verification
- **File(s)**: — (commands only)
- **Depends on**: S8-T1, S8-T2, S8-T3
- **Parallel-safe**: No
- **Effort**: Small
- **Steps**:
  - [x] Run `.venv/Scripts/python.exe -m pytest tests/ -q` and `npx playwright test --project=chromium --reporter=line`.
  - [x] Compare pass counts against `baseline_pytest.txt` and `baseline_e2e.txt` from S0-T1.
  - [x] Pytest passed with 924 tests.
  - [x] Visual spec now restores the committed visual seed database before screenshots, preventing cross-test DB drift from earlier E2E specs.
  - [x] Playwright passed with 367 tests.
  - [x] Counts match or exceed the baseline and the browser suite is green.
- **Verify**: Both suites green; counts ≥ baseline.
- **Rollback**: — (verification only)

---

## Stage 9 — Post-Implementation Review Follow-ups

**Status**: Completed in the current workspace. Discovered during the 2026-04-24 post-implementation review by Opus. None of these are correctness blockers — they are polish items — but they close out the review cleanly.

**Stage goal**: Close the three gaps identified after Stage 8 landed: one missing E2E coverage case, one redundant DB close, and one minor plan-vs-markup divergence.

**Stage-level prerequisites**: Stages 1–8 merged. Locked decisions still in effect.

### S9-T1: Add missing E2E test for partial-skipped restore (success + skipped list)

- **Type**: E2E test
- **File(s)**: `e2e/program-backup.spec.ts`
- **Depends on**: S2-T5 (already merged)
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**:
  - S2-T8 originally called for three Playwright tests. Only two shipped:
    - `restore confirmation mentions logged sessions and offers a save-first snapshot` (covers the copy + save-first button).
    - `restore renders a warning inline result panel when nothing can be restored` (covers `restored_count === 0`, the `is-warning` branch).
  - The third — **partial-skipped success** — was never added. That is the path where `restored_count > 0` *and* `skipped.length > 0`. The JS handles it at `renderRestoreResult` in `static/js/modules/backup-center.js` around the `else if (skipped.length > 0)` branch, but no E2E asserts the DOM.
  - The plan card called this one `restore with missing exercises shows skipped names inline`. Use that title to stay consistent.
  - Reuse the `page.route('**/api/backups/*/restore', ...)` mocking pattern that the existing zero-restored test uses — do NOT try to delete exercises out of the catalog mid-flight; mocking is simpler and more deterministic.
- **Steps**:
  - [x] Open `e2e/program-backup.spec.ts` and find the existing `restore renders a warning inline result panel when nothing can be restored` test (around line 166).
  - [x] Below it, add a new test `restore with missing exercises shows skipped names inline`:
    - [x] Seed a backup via the save form (same pattern as the existing tests — fill `#backup-center-name`, click submit, wait for toast).
    - [x] Select the backup in the list, click `#backup-detail-restore`.
    - [x] Use `page.route('**/api/backups/*/restore', ...)` to fulfill with a mocked JSON response where `restored_count` is e.g. `3` and `skipped` is `['Missing Exercise A', 'Missing Exercise B']`. Keep `ok: true, status: 'success'`.
    - [x] Click `#backup-action-confirm-btn`.
    - [x] Assert `#backup-restore-result` is visible.
    - [x] Assert `#backup-restore-result` does **NOT** have class `is-warning` (this is the success styling, not warning).
    - [x] Assert `#backup-restore-result-title` text contains both `3 exercises restored` and `2 skipped`.
    - [x] Assert `#backup-restore-result-list li` has count `2`.
    - [x] Assert one `<li>` contains `Missing Exercise A` and another contains `Missing Exercise B`.
- **Verify**:
  - `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line` — new test passes, existing 21 tests still pass.
  - Grep: `grep -n "shows skipped names inline" e2e/program-backup.spec.ts` — one hit.
- **Rollback**: `git restore e2e/program-backup.spec.ts`

### S9-T2: Remove redundant `db.close()` inside `restore_backup`'s `with` block

- **Type**: Backend cleanup
- **File(s)**: `utils/program_backup.py`
- **Depends on**: Stage 1 merged
- **Parallel-safe**: Yes
- **Effort**: Small
- **Context**:
  - `restore_backup` opens the handler with `with DatabaseHandler() as db:` (around line 395) AND explicitly calls `db.close()` inside a `finally` clause (around line 540) that is nested *inside* the `with` block.
  - The explicit close is redundant — `__exit__` on the context manager already closes the connection. `close()` is idempotent (`utils/database.py:400-412` checks `if getattr(self, "connection", None)` and nulls the attribute), so it is not a bug, just dead work and a confusing pattern.
  - It also makes the control flow harder to reason about: the outer `with` will try to `commit()` on a nulled connection and silently do nothing on the success path, which is fine but surprising.
  - Keep the `try / except sqlite3.Error: rollback; raise` structure — only the `finally: db.close()` line needs to go.
- **Steps**:
  - [x] Open `utils/program_backup.py` and locate the `try` block inside `restore_backup` (starts around line 426 with `db.execute_query("BEGIN IMMEDIATE", commit=False)`).
  - [x] Find the `finally: db.close()` (around line 539-540).
  - [x] Delete the `finally` clause entirely so the structure becomes `try: ... db.connection.commit() ... except sqlite3.Error: db.connection.rollback(); raise` — with no `finally` at the end.
  - [x] Do NOT touch the outer `with DatabaseHandler() as db:` — it stays and handles cleanup.
  - [x] Do NOT change any `commit=False` calls or the explicit `db.connection.commit()` on the success path.
  - [x] Follow-up: `test_restore_commits_once_on_success` previously relied on the inner `db.close()` nulling `self.connection` before `DatabaseHandler.__exit__` re-committed. With the inner close gone, `__exit__` runs one additional idempotent commit. The counting wrapper in `tests/test_program_backup.py` now gates on `self._connection.in_transaction`, so only the explicit transaction-closing commit is counted — preserving the test's regression-detection intent (any revert to per-statement commits still inflates the count).
- **Verify**:
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py -q` — all backup tests still green, especially `test_restore_rollback_preserves_active_program_on_failure` and `test_restore_commits_once_on_success`.
  - Grep: `grep -n "db.close()" utils/program_backup.py` — the occurrence inside `restore_backup` should be gone; other unrelated `close()` calls (if any) stay.
- **Rollback**: `git restore utils/program_backup.py`

### S9-T3: Move `#backup-restore-result` panel to the planned position

- **Type**: Template cleanup
- **File(s)**: `templates/backup.html`
- **Depends on**: —
- **Parallel-safe**: Yes (no other card edits this block)
- **Effort**: Small
- **Context**:
  - S2-T4 instructed to insert `#backup-restore-result` *after* `#backup-action-confirm` and *before* `.backup-detail-table-wrap`.
  - In the current markup the panel landed after `.backup-detail-actions` **and** after `#backup-action-confirm` but the plan's literal ordering has the result panel immediately adjacent to the confirm panel — the intent being: confirm → result (swap visibility) → table.
  - Functionally the current placement works; this is purely a markup-order fix so the DOM matches the plan. No CSS or JS needs to change.
  - Before moving, confirm nothing else was added between the two elements that would depend on their current order (e.g., scroll anchors). If anything was added, stop and escalate rather than guess.
- **Steps**:
  - [x] Open `templates/backup.html` and locate `#backup-action-confirm` (closes around line 199) and `#backup-restore-result` (around line 201).
  - [x] Verify `#backup-restore-result` sits directly between the closing `</div>` of `#backup-action-confirm` and the opening `<div class="backup-detail-table-wrap ...">`. Confirmed — the panel already matches the planned ordering, so no markup move was required.
  - [x] If anything else (e.g., `.backup-detail-actions`) sits between them, move `#backup-restore-result` to directly follow the closing `</div>` of `#backup-action-confirm` so it precedes the table wrap.
  - [x] Do NOT touch any other markup; do NOT rename ids or classes.
- **Verify**:
  - `.venv/Scripts/python.exe -m pytest tests/test_program_backup.py::TestProgramBackupAPI::test_backup_center_page_renders -q` — page still renders.
  - `npx playwright test e2e/program-backup.spec.ts --project=chromium --reporter=line` — all 22 tests pass (21 existing + S9-T1 if merged first).
  - Manual smoke: load `/backup`, select a backup, click Restore → the confirm panel and (after confirm) the result panel should both appear in the detail column above the exercise table.
- **Rollback**: `git restore templates/backup.html`

### S9-T4: Final baseline re-check

- **Type**: Verification
- **File(s)**: — (commands only)
- **Depends on**: S9-T1, S9-T2, S9-T3
- **Parallel-safe**: No
- **Effort**: Small
- **Context**: Mirror of S8-T4 — confirms the follow-ups did not regress either suite.
- **Steps**:
  - [x] Run `.venv/Scripts/python.exe -m pytest tests/ -q` — 929 passed in 119.94s.
  - [x] Run `npx playwright test --project=chromium --reporter=line` — 368 passed in 8.8m.
  - [x] Confirm pytest count ≥ Stage 8 final (924) — S9 adds zero unit tests; 929 ≥ 924 (unrelated tests accumulated since).
  - [x] Confirm Playwright count = Stage 8 final + 1 (368, after S9-T1) — 368 matches exactly.
  - [x] If either suite regresses, stop and escalate — do not bypass.
- **Verify**: Both suites green; counts match expectations above.
- **Rollback**: — (verification only)
