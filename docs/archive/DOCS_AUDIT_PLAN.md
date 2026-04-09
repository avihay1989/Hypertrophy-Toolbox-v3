# Documentation & Code Audit — Hardened Execution Plan

**Date:** 2026-04-08  
**Scope:** Review of all 18 files currently in `docs/`, cross-checked against the live codebase and current route/test contracts.  
**Purpose:** Convert the original audit into an execution-safe rollout with explicit go/no-go gates.

---

## Execution Posture

This plan is intentionally conservative.

- **Completed:** Tier 1, Tier 2, Tier 3, Tier 4a, Tier 4b summary/volume closure, all Tier 5 follow-up hardening slices, and the Tier 6 post-rollout re-audit snapshot
- **Still open:** No rollout blockers remain; future maintenance only needs to re-open Tier 6 if new repo drift appears

This is the safest current posture because the medium-risk progression wrapper cutover has already been completed with paired frontend/test updates, the Tier 4b summary/volume wrapper cutover has also been completed with paired frontend/test updates, and Tier 4b closure now has an explicit manual-smoke waiver recorded instead of an unclaimed manual pass. That waiver is backed by a fresh targeted live browser rerun of the summary and volume surfaces plus the already-green full Playwright and full `pytest` evidence. Tier 5 is now fully complete as well: Tier 5a consolidated the shared volume indicator ownership into `styles_volume.css` with browser verification, Tier 5b moved the shared pytest harness onto isolated per-test temp databases, and Tier 5c stabilized the reproduced browser failure cluster. Tier 6 has now also been executed once as a narrow post-rollout snapshot: it refreshed the stale README pointer, reconfirmed the Tier 2 backend logging cleanup, and reconfirmed the Tier 4a progression route contracts without reopening broader rollout work.

---

## Rollout Status Snapshot

**Updated:** 2026-04-09

| Tier | Current rollout state | Date | Notes |
|---|---|---|---|
| **1** | Completed | 2026-04-08 | Archived 5 historical docs, deleted 3 dead CSS files, refreshed Tier 1 docs, grep-based sanity checks completed |
| **2** | Completed | 2026-04-08 | Replaced remaining `print()` sites in `routes/` and `utils/` with structured logger calls |
| **3** | Completed | 2026-04-08 | Migrated the approved DB helper targets, preserved route contracts, and revalidated with targeted tests, browser smoke, and full `pytest` |
| **4a** | Completed | 2026-04-08 | Wrapped the progression endpoints, preserved the non-XHR save redirect fallback, and revalidated with route tests, Playwright API checks, browser smoke, and full `pytest` |
| **4b** | Completed with explicit manual-smoke waiver | 2026-04-09 | Locked Tier 4b scope, hardened callers for compatibility, wrapped the in-scope summary/volume endpoints, re-passed the targeted gate, kept `GET /api/pattern_coverage` plus `POST /api/export_volume_excel` out of scope, and closed the remaining manual-smoke gate via an explicit waiver backed by a fresh `46`-test live browser rerun of the summary/volume surfaces |
| **5** | Completed | 2026-04-09 | Tier 5a live CSS consolidation, Tier 5b test-harness isolation, and Tier 5c non-Tier-4b Playwright stabilization are complete |
| **6** | Completed (post-rollout snapshot) | 2026-04-09 | Executed the Tier 6 re-audit, refreshed the stale README pointer, reconfirmed no backend `print()` drift in `routes/` or `utils/`, and reconfirmed the Tier 4a progression contracts |

### What Is Done Right Now

- **Tier 1 done:** `docs/` now has **13** active top-level docs plus **5** archived docs under `docs/archive/`.
- **Tier 1 done:** The following stale CSS files were removed:
  - `static/css/styles_action_buttons.css`
  - `static/css/styles_chat.css`
  - `static/css/volume_indicators.css`
- **Tier 2 done:** Repo grep confirms no remaining `print()` calls in `routes/` or `utils/`.
- **Tier 3 done:** Migrated `utils/user_selection.py`, the approved volume-splitter persistence endpoints, and `utils/volume_export.py` to `DatabaseHandler`.
- **Tier 3 done:** `utils/database_indexes.py` intentionally keeps `optimize_database()` on the raw connection helper under explicit `_DB_LOCK`, per the documented safety decision for `ANALYZE` and `PRAGMA optimize`.
- **Tier 4a done:** Wrapped `get_exercise_suggestions`, `get_current_value`, `delete_progression_goal`, and `complete_progression_goal` with `success_response(...)` / `error_response(...)`.
- **Tier 4a done:** Preserved the intentional `save_progression_goal` split:
  - wrapped JSON success/error for fetch/XHR callers
  - redirect fallback for non-XHR form submissions
- **Tier 4a done:** Tightened progression route tests and Playwright progression coverage to the final wrapped contract, then revalidated with targeted and full-suite checks.
- **Tier 4b scope locked:** Locked the scope for this phase:
  - keep `GET /api/pattern_coverage` on its current `success` + `data` contract and cover it with regression checks rather than including it in the wrapper cutover
  - keep `POST /api/export_volume_excel` out of wrapper scope
  - preserve HTML rendering for `/session_summary` and `/weekly_summary`
- **Tier 4b cutover done:** Updated the live summary routes to use shared `is_xhr_request()` detection, kept the live summary/volume callers explicitly requesting JSON, and then wrapped the in-scope summary and volume-splitter endpoints with the locked Tier 4b contract.
- **Tier 4b cutover done:** Tightened the route, downstream-normalization, UI-flow, and Playwright API/browser assertions from compatibility mode to the final wrapped contract where appropriate.
- **Tier 4b verification done:** Re-ran the cutover-aware targeted pytest and Playwright gate successfully, and full `pytest` stayed green.
- **Tier 4b verification done:** Full Playwright is now green after the separate Tier 5c stabilization pass.
- **Tier 4b closure done:** Re-ran the live summary-page and volume-splitter browser surfaces on 2026-04-09 with `npx playwright test e2e/summary-pages.spec.ts e2e/volume-splitter.spec.ts --project=chromium --reporter=line` and got `46 passed`.
- **Tier 4b closure done:** Recorded an explicit waiver for the separate manual smoke requirement because no interactive human browser pass was run in this environment; closure rests on the green live browser rerun plus the already-green full Playwright and full `pytest` evidence.
- **Tier 5b done:** `tests/conftest.py` now provisions a unique `tmp_path` SQLite database per test, reinitializes the shared schema for each isolated file, and keeps the fixture names/contracts stable for the rest of the suite.
- **Tier 5b done:** Added lock-focused regression coverage for isolated temp databases and revalidated the shared harness with targeted fixture/route tests plus a green full `pytest tests/ -q` rerun (`981 passed, 1 skipped`).
- **Tier 5a done:** `styles_volume.css` is now the canonical owner for shared volume indicators, badges, classification colors, and legend text, while `session_summary.css` keeps only summary-page-specific table and dark-layout rules.
- **Tier 5a done:** `session_summary.html` now loads `styles_volume.css`, the summary templates use a consistent generic-before-page-specific CSS order, and browser coverage now asserts the shared legend swatch colors on both summary pages.
- **Tier 5a verification done:** Re-ran `npx playwright test e2e/summary-pages.spec.ts e2e/volume-splitter.spec.ts --project=chromium --reporter=line` and got `48 passed`.
- **Tier 5c done:** Stabilized the unrelated workout-plan/superset/validation Playwright failure cluster by resetting workout-plan test state, downgrading handled UI errors from hard console failures to warnings, removing duplicate-test-data assumptions, and refreshing the brittle workout-plan export API setup.
- **Tier 6a done:** Re-grepped the docs and Playwright inventories, confirmed `docs/README.md`, `docs/E2E_TESTING.md`, and `docs/CSS_OWNERSHIP_MAP.md` still match the current repo shape, and refreshed the stale README Tier-reference pointer.
- **Tier 6a done:** Confirmed the deleted CSS files were not reintroduced as live template/static references; the remaining hits are limited to historical docs plus the consolidation comment in `static/css/styles_buttons.css`.
- **Tier 6b done:** Re-grepped `routes/` and `utils/` and reconfirmed there are no raw `print()` calls in the Tier 2 backend scope.
- **Tier 6b done:** Reconfirmed the touched backend modules still centralize logger ownership through `get_logger()` rather than reintroducing ad hoc logger creation in `routes/` or `utils/`.
- **Tier 6c done:** Re-audited `routes/progression_plan.py`, the paired progression tests, and the active frontend callers; the wrapped Tier 4a endpoint inventory is unchanged and the intentional `save_progression_goal` XHR-vs-redirect split remains intact.

### What Is Left To Run

No active rollout work remains. Re-open Tier 6 only if future repo drift stales Tier 1 docs, Tier 2 backend logging, or the Tier 4a progression route contracts again.

---

## Validated Baseline

The following facts were verified directly in the repo on 2026-04-08:

- `docs/` currently contains **18 files**, not 16.
- `e2e/` currently contains **17 Playwright spec files**.
- `DatabaseHandler.fetch_all()` returns **dict rows**, not tuple rows.
- `DatabaseHandler.execute_query()` returns **rowcount**, not a cursor.
- `DatabaseHandler` write-lock detection does **not** currently treat `ANALYZE` or `PRAGMA optimize` as write operations.
- Summary and volume-splitter routes have live frontend consumers, so any response-contract change still requires paired frontend and test updates in the same branch.
- `routes/progression_plan.py` now returns wrapped JSON for fetch/XHR progression callers, while `POST /save_progression_goal` intentionally keeps a non-XHR redirect fallback.
- A targeted route baseline passed:
  - `tests/test_volume_splitter_api.py`
  - `tests/test_session_summary_routes.py`
  - `tests/test_weekly_summary_routes.py`
  - Result: **63 tests passed**

---

## Global Rules For Execution

Apply these rules to every tier:

1. Re-grep the repo before editing anything that depends on counts, file inventories, or route shapes.
2. Do not treat this as a blanket refactor. Several items require code-shape changes, not search-and-replace.
3. Do not change JSON response contracts unless the paired frontend and tests are updated in the same tier.
4. Do not mark manual QA checklists as "done" unless those manual checks were actually run.
5. Keep each tier independently shippable.

---

## Tier 1: Docs Cleanup & Dead File Removal

**Execution status:** Completed on 2026-04-08  
**Risk:** None to application behavior  
**Why approved:** This tier only changes documentation and unlinked CSS artifacts.

### Execution Log

- Completed archive move to `docs/archive/` for:
  - `MISSING_TESTS_CHECKLIST.md`
  - `MISSING_TESTS_PART2.md`
  - `PUPPETEER_TEST_FINDINGS.md`
  - `SUPERSET_FEATURE.md`
  - `PLAN_GENERATOR_IMPLEMENTATION.md`
- Deleted:
  - `static/css/styles_action_buttons.css`
  - `static/css/styles_chat.css`
  - `static/css/volume_indicators.css`
- Refreshed:
  - `docs/README.md`
  - `docs/E2E_TESTING.md`
  - `docs/CSS_OWNERSHIP_MAP.md`
  - `docs/UI_SCENARIOS_GAP_ANALYSIS.md`
  - `docs/program_backups.md`
  - `docs/CLAUDE_MD_AUDIT.md`
  - `docs/CHANGELOG.md` (archived-path reference correction)

### 1a. Archive Completed Feature Docs

Move these historical tracking docs to `docs/archive/`:

- `MISSING_TESTS_CHECKLIST.md`
- `MISSING_TESTS_PART2.md`
- `PUPPETEER_TEST_FINDINGS.md`
- `SUPERSET_FEATURE.md`
- `PLAN_GENERATOR_IMPLEMENTATION.md`

These still have reference value, but they read like active backlog when kept in the top-level docs folder.

### 1b. Delete Dead CSS Files

Delete these files after one final grep confirms they remain unreferenced:

- `static/css/styles_action_buttons.css`
  - Safe because the styles were consolidated into `styles_buttons.css`, which is loaded from `templates/base.html`.
- `static/css/styles_chat.css`
  - Safe because no template, JS module, or stylesheet imports it.
- `static/css/volume_indicators.css`
  - Safe because it is an unlinked duplicate of classes already defined in loaded stylesheets.

### 1c. Refresh Stale Docs

Update these docs, but keep the edits evidence-driven:

- `docs/README.md`
  - Rebuild the index from actual directory contents after the archive move.
  - Add an `archive/` section reference.
- `docs/E2E_TESTING.md`
  - Do not hardcode stale counts.
  - Rebuild the suite inventory from current spec files and current test collection.
  - Phrase counts as current inventory, not as a promise that all suites were rerun clean in this environment unless that rerun actually happens.
- `docs/CSS_OWNERSHIP_MAP.md`
  - Mark the `styles_action_buttons.css` consolidation as complete.
  - Mark per-page CSS loading as complete.
  - Remove references to CSS files deleted in this tier.
  - Keep the wording precise: the display label is "Excessive Volume", but the internal CSS class name is still `ultra-volume`.
- `docs/UI_SCENARIOS_GAP_ANALYSIS.md`
  - Split findings into:
    - fixed
    - intentional/documented behavior
    - accepted/deferred
  - Do not flatten those distinctions into a single "resolved" status.
- `docs/program_backups.md`
  - Do **not** auto-check manual QA boxes.
  - Safer options:
    - convert the section into automated coverage status, or
    - map checklist items to automated tests and leave manual verification explicitly separate

### 1d. Refresh `CLAUDE_MD_AUDIT.md`

Trim resolved findings and keep only live architecture debt.

Important correction:

- Cleanup should focus on stale architecture findings.
- Do **not** assume this file contains a duplicated CSS backlog; that duplication was not confirmed during validation.

### Tier 1 Verification

- Optional: `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- Required: sanity-check file moves, README index, and deleted CSS references with repo grep

**Verification completed on 2026-04-08:**

- Repo grep confirmed no live template/static references to the deleted CSS files.
- `docs/README.md` was rebuilt against the post-move directory structure.
- Optional full pytest was **not** run as part of Tier 1 itself.

### Tier 1 Completion Checklist

Current execution status: completed.

- [x] Archive completed feature docs into `docs/archive/`
- [x] Delete the approved dead CSS files
- [x] Refresh the Tier 1 stale docs
- [x] Trim `CLAUDE_MD_AUDIT.md` to live debt only

---

## Tier 2: Logging Cleanup (`print()` to `logger`)

**Execution status:** Completed on 2026-04-08  
**Risk:** Minimal  
**Why approved:** This tier changes observability only, not business logic or response contracts.

### Execution Log

- Added `get_logger()` usage to the remaining Tier 2 route and utility targets.
- Converted debug-style prints to `logger.debug(...)`.
- Converted startup/CLI visibility messages to `logger.info(...)`.
- Converted failure-path prints to `logger.warning(...)` or `logger.exception(...)`.
- Preserved return values, branching, and response contracts.

### Scope

Replace raw `print()` calls in routes and utils with `get_logger()` calls at the appropriate level.

Execution guardrails:

- Rebuild the inventory with a repo grep before editing. The older per-file counts are already stale.
- Preserve readable error messages.
- Preserve startup visibility in init and maintenance code.
- Do not change return values, branching, or exception handling behavior as part of this tier.

### Confirmed Notes

- `routes/progression_plan.py` has more `print()` calls than the earlier table claimed.
- `routes/session_summary.py` and `routes/weekly_summary.py` are still safe logging-only cleanup targets.
- `utils/volume_export.py`, `utils/user_selection.py`, and related helpers are still appropriate targets here, but only for logging changes in this tier.

### Tier 2 Verification

- Recommended: targeted tests for touched modules plus `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- Required: grep to confirm no intended `print()` cleanup sites were missed

**Verification completed on 2026-04-08:**

- Repo grep found **zero** remaining `print()` calls in `routes/` and `utils/`.
- Targeted verification passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_business_logic.py tests/test_weekly_summary.py tests/test_session_summary.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_workout_plan_routes.py tests/test_exports.py tests/test_workout_log_routes.py tests/test_volume_splitter_api.py tests/test_progression_plan_utils.py -q`
  - Result: **260 passed, 1 skipped**
- Full unit suite also passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - Result: **952 passed, 1 skipped**

### Tier 2 Completion Checklist

Current execution status: completed.

- [x] Replace remaining `print()` calls in `routes/` and `utils/`
- [x] Preserve return values, branching, and response contracts
- [x] Run targeted verification on touched modules
- [x] Run full `pytest tests/ -q`

---

## Tier 3: DatabaseHandler Migration

**Execution status:** Completed on 2026-04-08  
**Risk:** Low, but not "drop-in"  
**Why completed safely:** This tier improved consistency and write safety while preserving the existing JSON and helper contracts relied on by the current frontend.

### Execution Log

- Migrated `utils/user_selection.py` to `DatabaseHandler.fetch_all()`.
- Migrated `routes/volume_splitter.py`:
  - `get_volume_history()`
  - `get_volume_plan()`
  - `delete_volume_plan()`
- Migrated `utils/volume_export.py` to `DatabaseHandler` using `commit=False` for grouped inserts and `db.cursor.lastrowid` for the inserted plan id.
- Preserved the existing top-level JSON response shapes for volume-splitter history, load, save, and delete flows.
- Kept `utils/database_indexes.py -> optimize_database()` on the explicit raw-connection + `_DB_LOCK` strategy already chosen during prerequisite hardening.

### Core Constraints To Respect

- `DatabaseHandler.fetch_all()` returns dict rows.
- `DatabaseHandler.fetch_one()` returns a dict or `None`.
- `DatabaseHandler.execute_query()` returns rowcount.
- `lastrowid` must be read from `db.cursor.lastrowid`, not from the return value of `execute_query()`.
- `ANALYZE` and `PRAGMA optimize` will not automatically hold `_DB_LOCK` with the current helper implementation.

### 95% Confidence Prerequisites

These prerequisites should be completed before Tier 3 is called ready for execution with approximately 95% confidence that existing flows stay intact.

#### P1: Clarify `utils/user_selection.py` runtime status

- Confirm whether the helper is still a live runtime dependency or only a legacy export.
- Current validation result:
  - The live `GET /get_user_selection` route is implemented in `routes/workout_plan.py`, not in `utils/user_selection.py`.
  - `utils/user_selection.py` is still re-exported through `utils.helpers` and `utils.__init__`, so it is not dead code, but it is also not the primary live route path.
- Confidence action:
  - Keep this helper covered with a direct unit test.
  - Do not treat it as the main confidence-building milestone for Tier 3 route safety.

#### P2: Add direct persistence-contract tests for volume-splitter routes

- Add route tests that hit the actual Tier 3 endpoints, not just `/api/calculate_volume`.
- Required coverage:
  - `POST /api/save_volume_plan`
  - `GET /api/volume_history`
  - `GET /api/volume_plan/<id>`
  - `DELETE /api/volume_plan/<id>`
- Frontend safeguard:
  - The volume-history UI should sort returned plans by `created_at`, not rely on top-level object key order after JSON serialization.
- Assert current response shapes exactly:
  - `save_volume_plan` returns top-level `success` and `plan_id`
  - `volume_history` returns grouped top-level plan ids mapping to `training_days`, `created_at`, and `muscles`
  - `volume_plan/<id>` returns top-level `training_days`, `created_at`, and `volumes`
  - delete keeps the current top-level `success` / `error` contract

#### P3: Refresh stale automation before relying on it

- Fix stale API integration coverage that still points at `/calculate_volume_split`.
- Strengthen the weak UI flow test that posts an outdated payload and only checks for HTTP 200.
- Keep the dedicated volume-splitter page E2E coverage, but do not count stale API checks as evidence.

#### P4: Decide the locking strategy for `optimize_database()` before migration

- Current decision for this plan:
  - Keep `optimize_database()` on the raw connection helper for now.
  - Hold `_DB_LOCK` explicitly at the call site while running `ANALYZE` and `PRAGMA optimize`.
- Reason:
  - This avoids depending on `DatabaseHandler` write-operation classification for maintenance statements that are not currently treated as writes.
- Required follow-up:
  - Add tests that confirm the lock is acquired/released and rollback happens on SQLite errors.

#### P5: Lock in `export_volume_plan()` transaction semantics before migration

- The future `DatabaseHandler` migration for this function is only safe if transaction semantics are explicit.
- Required rule:
  - If `commit=False` is used inside a `with DatabaseHandler()` block, either let the database exception escape so `__exit__` rolls back, or explicitly call rollback before returning failure.
- Do not:
  - Catch a DB exception, return `None`, and rely on context exit to infer rollback when no exception escapes.
- Add a regression test that proves a mid-write failure does not leave partial `volume_plans` or `muscle_volumes` rows behind.

### Prerequisite Hardening Status

**Updated:** 2026-04-08

- `utils/user_selection.py` runtime status clarified: legacy export with direct unit coverage, not the live `/get_user_selection` route path
- Added direct route coverage for the Tier 3 volume-splitter persistence endpoints
- Refreshed stale API/UI automation for the current `/api/calculate_volume` contract
- Added dedicated browser smoke coverage for the live volume-splitter persistence flow:
  - save plan
  - verify history update
  - load saved plan back into the UI
  - delete saved plan from history
- Implemented and documented explicit `_DB_LOCK` handling for `optimize_database()`
- Added regression coverage for `export_volume_plan()` rollback behavior on mid-write failure
- Re-ran Tier 3 prechecks:
  - raw DB access inventory still shows the expected remaining Tier 3 targets in `routes/volume_splitter.py`, `utils/volume_export.py`, `utils/database_indexes.py`, and `utils/user_selection.py`
  - orphaned `muscle_volumes` check returned `0`
  - volume-history frontend handling now sorts by `created_at` explicitly instead of relying on object key order
- Verification completed for prerequisite hardening:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_volume_splitter_api.py tests/test_database_indexes.py tests/test_ui_flows.py tests/test_user_selection_helper.py tests/test_priority0_fk_integrity.py -q`
  - Result: `62 passed`
  - `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q`
  - Result: `59 passed`
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - Result: `964 passed, 1 skipped`
- Playwright/API integration specs were refreshed for the current route contract, but not rerun as part of this prerequisite pass
- Dedicated browser smoke rerun completed for the live volume-splitter persistence flow:
  - `npx playwright test e2e/volume-splitter.spec.ts -g "saved plans can be restored and deleted through volume history" --project=chromium`
  - Result: `1 passed`

### Safe Migration Order

#### Step 1: `utils/user_selection.py`

Safe only as a scoped legacy-helper cleanup, not as a primary route-safety milestone.

- Read-only path
- Legacy export path, not the live `/get_user_selection` route implementation
- Keep direct helper tests in place if this file is migrated later
- No response contract changes expected

#### Step 2: `routes/volume_splitter.py` — `get_volume_history()`

Safe if the row-shape change is handled explicitly.

- Convert tuple-style access like `row[0]` to named-key access.
- Keep the returned JSON shape identical.

#### Step 3: `routes/volume_splitter.py` — `get_volume_plan()`

Same guardrails as Step 2.

- Convert tuple-style access to named-key access.
- Keep `training_days`, `created_at`, and `volumes` at the same top-level keys.

#### Step 4: `routes/volume_splitter.py` — `delete_volume_plan()`

Strong correctness win.

- This is currently a write path without the standard lock/rollback helper path.
- Replace with `DatabaseHandler` while preserving the existing success/error JSON shape.

#### Step 5: `utils/volume_export.py` — `export_volume_plan()`

Safe only with explicit transaction handling details.

- Use `DatabaseHandler`.
- Use `commit=False` for the grouped inserts only if rollback semantics are explicit.
- If a DB write fails:
  - either let the exception escape the `with DatabaseHandler()` block so `__exit__` rolls back
  - or call rollback explicitly before returning failure
- Read the inserted plan id from `db.cursor.lastrowid`.

Required pre-check before migrating this path:

```sql
SELECT COUNT(*) FROM muscle_volumes
WHERE plan_id NOT IN (SELECT id FROM volume_plans);
```

If orphaned `muscle_volumes` rows exist, clean them up before relying on stricter foreign-key enforcement for this path.

#### Step 6: `utils/database_indexes.py` — `optimize_database()`

Do not treat this as automatically safe just because it uses `DatabaseHandler`.

- `ANALYZE` and `PRAGMA optimize` are not currently included in the helper's write-lock detection.
- Either extend the helper deliberately or document and manage locking explicitly at the call site.
- Add a docstring or comment noting the blocking characteristics of this maintenance operation.

### Tier 3 Next Actions

Current execution status: completed.

- [x] Complete Tier 3 prerequisite hardening for 95%-confidence execution:
  - [x] clarify `utils/user_selection.py` runtime status and add direct helper coverage
  - [x] add direct route-contract tests for `save_volume_plan`, `volume_history`, `volume_plan/<id>`, and delete
  - [x] refresh stale `/api/calculate_volume` API/UI automation
  - [x] decide and implement the `optimize_database()` locking strategy with tests
  - [x] add rollback regression coverage for `export_volume_plan()`
- [x] Re-run Tier 3 prechecks:
  - raw DB access grep
  - orphaned `muscle_volumes` check
  - route/frontend shape sanity check for volume-splitter endpoints
- [x] Migrate `utils/user_selection.py`
- [x] Migrate `routes/volume_splitter.py` -> `get_volume_history()`
- [x] Migrate `routes/volume_splitter.py` -> `get_volume_plan()`
- [x] Migrate `routes/volume_splitter.py` -> `delete_volume_plan()`
- [x] Migrate `utils/volume_export.py` using `commit=False` for grouped inserts and `db.cursor.lastrowid`
- [x] Decide and implement/document the locking strategy for `utils/database_indexes.py` -> `optimize_database()`
- [x] Run the required targeted tests
- [x] Run full `pytest tests/ -q` before calling Tier 3 complete

### Tier 3 Verification

At minimum:

- `.\.venv\Scripts\python.exe -m pytest tests/test_volume_splitter_api.py tests/test_database_indexes.py tests/test_ui_flows.py tests/test_user_selection_helper.py tests/test_priority0_fk_integrity.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q`
- Keep the dedicated `e2e/volume-splitter.spec.ts` suite current if the page contract changes

Recommended before shipping:

- `.\.venv\Scripts\python.exe -m pytest tests/ -q`

**Verification completed on 2026-04-08:**

- Raw DB access grep now shows only:
  - `utils/database.py`
  - `utils/database_indexes.py` for the intentionally retained locked maintenance path
- Targeted Tier 3 verification passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_volume_splitter_api.py tests/test_database_indexes.py tests/test_ui_flows.py tests/test_user_selection_helper.py tests/test_priority0_fk_integrity.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q`
  - Result: `121 passed`
- Dedicated browser persistence smoke passed after the migration:
  - `npx playwright test e2e/volume-splitter.spec.ts -g "saved plans can be restored and deleted through volume history" --project=chromium`
  - Result: `1 passed`
- Full unit suite passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - Result: `964 passed, 1 skipped`

---

## Tier 4: Response Wrapper Migration (`jsonify` to `success_response` / `error_response`)

**Execution status:** Tier 4a completed on 2026-04-08; Tier 4b completed on 2026-04-09 with an explicit manual-smoke waiver recorded  
**Risk:** Medium to High  
**Why this stayed controlled:** Tier 4a changed API contracts only with paired frontend/test updates in the same branch state, and Tier 4b only proceeded once those live summary/volume consumers were hardened, the cutover gate passed, and the remaining manual-smoke closure step was resolved explicitly rather than implied.

### Default Rule

Do **not** execute Tier 4 as routine cleanup. Tier 4a and Tier 4b only proceeded once the paired frontend, template JS, and test updates were included in the same change set; keep using that rule if future Tier 4-surface contract work is ever reconsidered.

### 4a. Progression Routes

**Status:** Completed on 2026-04-08

Endpoints in scope:

- `POST /get_exercise_suggestions`
- `DELETE /delete_progression_goal/<id>`
- `POST /complete_progression_goal/<id>`
- `POST /get_current_value`

Important additional decision:

- `POST /save_progression_goal` had to be called out explicitly.
- The final decision was:
  - wrapped JSON success/error for fetch/XHR callers
  - redirect fallback for non-XHR form submissions
- Standardizing that split was reasonable, but the contract change needed to be intentional.

### Execution Log

- Wrapped `POST /get_exercise_suggestions` to return `jsonify(success_response(data=[...]))` and standardized validation/internal errors with `error_response(...)`.
- Wrapped `POST /get_current_value` to return `jsonify(success_response(data={"current_value": value}))`, preserving `"N/A"` for unsupported goal types inside the wrapped `data` payload.
- Wrapped `DELETE /delete_progression_goal/<id>` and `POST /complete_progression_goal/<id>` to use standardized success/error envelopes, including `NOT_FOUND` responses.
- Preserved `POST /save_progression_goal` as:
  - wrapped JSON success/error for fetch/XHR callers
  - redirect fallback for non-XHR form submissions
- Tightened:
  - `tests/test_progression_plan_routes.py`
  - `e2e/api-integration.spec.ts`
  - `e2e/progression.spec.ts`
- Verification completed in the same branch state:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_progression_plan_routes.py tests/test_progression_plan_utils.py -q` -> `56 passed`
  - `npx playwright test e2e/api-integration.spec.ts -g "Double Progression API|Progression Plan API" --project=chromium` -> `10 passed`
  - `npx playwright test e2e/progression.spec.ts -g "goal can be saved and completed through the progression page" --project=chromium` -> `1 passed`
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `977 passed, 1 skipped`

Why this was not initially "safe by default":

- The progression page JS is mostly wrapper-tolerant.
- The API integration test asserted a bare array for `/get_exercise_suggestions`.
- A redirect-returning fetch endpoint should not be silently standardized without deciding the desired client contract first.

### 95% Confidence Prerequisites For Tier 4a

These should be completed before Tier 4a is treated as execution-ready with approximately 95% confidence that progression flows continue to work after the response-wrapper migration.

#### P1: Lock the intended contract for every affected progression endpoint

- Decide the post-migration response shape for:
  - `POST /get_exercise_suggestions`
  - `POST /get_current_value`
  - `DELETE /delete_progression_goal/<id>`
  - `POST /complete_progression_goal/<id>`
  - `POST /save_progression_goal`
- Recommended decision:
  - use wrapped JSON for all fetch-facing progression endpoints
  - keep redirect behavior only as an explicit non-XHR fallback for `save_progression_goal`, if needed
- Document the exact success and error payloads before editing routes.

#### P2: Make fetch/XHR intent explicit for non-`/api/` progression routes

- The current `fetch-wrapper` sends `Content-Type` and `X-Request-ID`, but Tier 4a safety improves if progression fetches also unambiguously request JSON.
- Before migration, either:
  - add `Accept: application/json` and/or `X-Requested-With: XMLHttpRequest` to the shared fetch wrapper, or
  - move the Tier 4a endpoints under an `/api/` namespace as part of the same contract decision
- Goal:
  - ensure `error_response(...)` behavior is deterministic for these fetch calls, not inferred indirectly from route path or browser defaults.

#### P3: Add dedicated route-contract tests for progression endpoints

- Add a focused route test file for the Tier 4a endpoints.
- Required coverage:
  - `POST /get_exercise_suggestions`
  - `POST /get_current_value`
  - `POST /save_progression_goal`
  - `DELETE /delete_progression_goal/<id>`
  - `POST /complete_progression_goal/<id>`
- Assert exact wrapped payload shapes and status codes for:
  - success cases
  - validation failures
  - not-found cases
  - internal-error cases where practical
- Include DB side-effect assertions:
  - goal row created
  - goal row deleted
  - `completed` flag updated

#### P4: Refresh stale API integration coverage to the live progression routes

- Remove or replace stale progression API checks that still point at old or nonexistent endpoints.
- Update the Playwright API integration expectations so they match the intended wrapped contract, not the current bare-array or redirect behavior.
- Do not count the current stale progression API checks as confidence evidence until they target the real live routes.

#### P5: Harden the progression frontend against the wrapped contract before switching the backend

- Verify `static/js/modules/progression-plan.js` explicitly handles wrapped responses for:
  - suggestions
  - current value lookup
  - save goal
  - delete goal
  - complete goal
- The suggestions/current-value paths are already partially wrapper-tolerant; save/delete/complete should be made equally explicit so the route migration is not relying on incidental compatibility.
- Preserve:
  - current toast behavior
  - modal close behavior
  - page reload behavior after save
  - row removal/update behavior after delete/complete

#### P6: Add one browser-level progression goal lifecycle smoke

- Add a dedicated browser smoke that exercises the real user flow:
  - open progression page
  - select an exercise
  - load suggestions
  - open the goal modal
  - save a goal
  - verify the goal appears after reload
  - complete or delete the goal
- This should be treated as the frontend confidence gate for Tier 4a, similar to the browser smoke added for Tier 3 volume-splitter persistence.

#### P7: Define the pre-execution verification gate for Tier 4a

- Before starting Tier 4a, require all of the following to pass in the same branch state:
  - the new progression route-contract tests
  - `tests/test_progression_plan_utils.py`
  - refreshed progression-related Playwright API checks
  - the progression browser lifecycle smoke
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- Recorded pass on 2026-04-08:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_progression_plan_routes.py tests/test_progression_plan_utils.py -q` -> `56 passed`
  - `npx playwright test e2e/api-integration.spec.ts -g "Double Progression API|Progression Plan API" --project=chromium` -> `10 passed`
  - `npx playwright test e2e/progression.spec.ts -g "goal can be saved and completed through the progression page" --project=chromium` -> `1 passed`
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `977 passed, 1 skipped`

#### Locked Contract Assumption For Prerequisite Work

Unless explicitly re-decided, Tier 4a prerequisite work should assume the following end-state contract:

| Endpoint | Intended success payload | Intended error payload | Notes |
|---|---|---|---|
| `POST /get_exercise_suggestions` | `jsonify(success_response(data=[...]))` | `error_response(...)` | Suggestions move from bare array to wrapped `data` array |
| `POST /get_current_value` | `jsonify(success_response(data={"current_value": value}))` | `error_response(...)` | `current_value` stays the same field name inside `data` |
| `POST /save_progression_goal` | `jsonify(success_response(data={"goal_id": id}, message="Goal saved successfully"))` | `error_response(...)` | Keep redirect fallback only for non-XHR/non-JSON callers if still needed |
| `DELETE /delete_progression_goal/<id>` | `jsonify(success_response(message="Goal deleted successfully"))` | `error_response(...)` | No extra `data` required on success |
| `POST /complete_progression_goal/<id>` | `jsonify(success_response(message="Goal marked as completed"))` | `error_response(...)` | No extra `data` required on success |

This contract is now implemented for the Tier 4a progression endpoints.

#### Working Checklist For The Current Repo State

Use this as the practical go/no-go checklist for the Tier 4a gaps still visible in the repo as of 2026-04-08.

Priority order is top to bottom.

1. [x] Lock the final contract for all five progression endpoints and record the exact wrapped success/error payloads.
2. [x] Make the `POST /save_progression_goal` decision explicit and stop relying on redirect/HTML success behavior for fetch callers.
3. [x] Make progression fetch intent unambiguous by sending `Accept: application/json` and optionally `X-Requested-With: XMLHttpRequest`.
4. [x] Add or tighten route-level validation for missing/invalid JSON and required goal fields before calling `save_progression_goal()`, so validation failures are intentional 4xx responses instead of incidental 500s from missing keys.
5. [x] Add `tests/test_progression_plan_routes.py` with exact payload/status assertions plus DB side-effect checks for save/delete/complete/current-value/suggestions flows.
6. [x] Replace stale progression API integration checks that still target old or nonexistent routes such as `/get_progression_goals`, `/add_progression_goal`, or `POST /delete_progression_goal` without `<id>`.
7. [x] Upgrade progression browser coverage from page-structure checks to one real lifecycle smoke and fix any selector drift before counting browser automation as confidence evidence.
8. [x] Run and record the full Tier 4a verification gate in one branch state before calling the tier execution-ready.

### Recommended Execution Order For Tier 4a Prep

Use this order to keep Tier 4a controlled and to avoid changing backend contracts before the paired frontend/tests are ready.

1. Lock the endpoint contract first.
   - Finalize the intended wrapped success/error shape for every Tier 4a endpoint.
   - Make the `save_progression_goal` decision explicit before touching code.

2. Make JSON/XHR intent explicit next.
   - Update the fetch path so progression requests clearly ask for JSON responses.
   - This removes ambiguity for non-`/api/` progression routes before wrapper work begins.

3. Refresh stale progression API coverage to the live route inventory.
   - Replace outdated API integration references with the real active endpoints.
   - At this stage, focus on route inventory and endpoint targeting, not final wrapped assertions yet.

4. Harden the progression frontend for the wrapped contract.
   - Make `static/js/modules/progression-plan.js` explicitly consume wrapped responses for save/delete/complete in addition to suggestions/current-value.
   - Preserve the current UX behaviors so the backend migration becomes a contract swap, not a UI rewrite.

5. Add the new progression route-contract tests and browser lifecycle smoke in the same working branch as the backend wrapper change.
   - If these tests assert the final wrapped payloads, they should land together with the route migration, not earlier in a passing mainline state.
   - Goal:
     - avoid a long period where tests are knowingly red against the old contract
     - keep the migration, frontend handling, and verification tightly paired

6. Execute the Tier 4a route wrapping.
   - Wrap only the approved progression endpoints.
   - Apply the already-decided `save_progression_goal` behavior instead of improvising during implementation.

7. Run the Tier 4a verification gate before calling the tier safe or complete.
   - progression route-contract tests
   - `tests/test_progression_plan_utils.py`
   - refreshed progression-related Playwright API checks
   - progression browser lifecycle smoke
   - full `pytest tests/ -q`

### Practical Start Point

If Tier 4a is approved later, the recommended first concrete task is:

1. decide and document the final contract for all five progression endpoints
2. update the fetch/XHR JSON signaling
3. then start the paired frontend/test/backend migration in one branch
   - route tests
   - browser smoke
   - route wrappers
   - final verification

### Concrete Tier 4a Prep Todo List

Use this as the implementation-oriented checklist for prerequisite work before the Tier 4a wrapper migration itself.

#### Step 1: Lock the final endpoint contracts in writing

Files to touch:

- `docs/archive/DOCS_AUDIT_PLAN.md`
- `routes/progression_plan.py`
- `utils/errors.py` (reference against the existing wrapper shape; only edit if the contract helper itself must change)

What to do:

- Document the intended success and error shape for:
  - `POST /get_exercise_suggestions`
  - `POST /get_current_value`
  - `POST /save_progression_goal`
  - `DELETE /delete_progression_goal/<id>`
  - `POST /complete_progression_goal/<id>`
- Make an explicit decision for `save_progression_goal`:
  - JSON only, or
  - JSON for fetch/XHR plus redirect fallback for non-XHR
- Confirm whether `get_exercise_suggestions` should become:
  - wrapped `data: [...]`, or
  - intentionally remain a bare array
- Do not start route edits until this contract table is settled.

#### Step 2: Make fetch/XHR JSON intent explicit

Files to touch:

- `static/js/modules/fetch-wrapper.js`
- `static/js/modules/progression-plan.js`
- `utils/errors.py` (only if request-type detection needs coordinated support)

What to do:

- Ensure progression fetches clearly request JSON responses:
  - add `Accept: application/json`
  - optionally add `X-Requested-With: XMLHttpRequest`
- Verify the progression page still behaves correctly after the header change:
  - suggestions fetch
  - current-value fetch
  - save goal
  - delete goal
  - complete goal
- Keep this step focused on signaling and compatibility, not wrapper migration yet.

#### Step 3: Add dedicated progression route-contract tests

Files to touch:

- `tests/test_progression_plan_routes.py` (new)
- `tests/conftest.py` (only if new fixtures are needed)
- `routes/progression_plan.py` (only for minor validation fixes discovered while writing tests)

What to do:

- Add direct route tests for:
  - `POST /get_exercise_suggestions`
  - `POST /get_current_value`
  - `POST /save_progression_goal`
  - `DELETE /delete_progression_goal/<id>`
  - `POST /complete_progression_goal/<id>`
- Assert:
  - exact payload shape
  - status code
  - goal create/delete/complete side effects
  - validation and not-found cases
- Keep utility logic tests in `tests/test_progression_plan_utils.py` as-is; this new file should cover route contracts specifically.

#### Step 4: Refresh stale progression API integration coverage

Files to touch:

- `e2e/api-integration.spec.ts`
- `e2e/fixtures.ts` (only if new helpers/constants improve clarity)

What to do:

- Replace stale progression API checks that still point at old or nonexistent endpoints.
- Align the progression API tests with the real live route inventory.
- Once the final contract is chosen, assert the intended wrapped shapes instead of the old bare-array / legacy assumptions.

#### Step 5: Harden the progression page JS for wrapped responses

Files to touch:

- `static/js/modules/progression-plan.js`
- `static/js/modules/fetch-wrapper.js` (if response extraction helpers should be centralized)
- `templates/progression_plan.html` (only if stable selectors or small testability hooks are needed)

What to do:

- Make response handling explicit for:
  - `get_exercise_suggestions`
  - `get_current_value`
  - `save_progression_goal`
  - `delete_progression_goal`
  - `complete_progression_goal`
- Prefer one consistent extraction pattern:
  - wrapped responses read from `response.data`
  - success messages read from `response.message` when relevant
- Preserve existing UX:
  - modal closes after save
  - save still reloads the page
  - delete still removes the row
  - complete still updates the row status
  - toasts still show the right message

#### Step 6: Add one browser-level progression goal lifecycle smoke

Files to touch:

- `e2e/progression.spec.ts`
- `e2e/fixtures.ts` (only if helper selectors/utilities are useful)
- `templates/progression_plan.html` (only if selector stability needs a small markup hook)

What to do:

- Add one real lifecycle smoke that:
  - opens `/progression`
  - selects an exercise
  - waits for suggestions
  - opens the goal modal
  - saves a goal
  - verifies the goal appears after reload
  - completes or deletes the goal
- Keep it self-cleaning where possible so reruns do not accumulate state.

#### Step 7: Define the exact verification command set

Files to touch:

- `docs/archive/DOCS_AUDIT_PLAN.md`
- optional: `docs/code_cleanup_plan.md` if that file should mirror the same gate later

What to do:

- Record the exact commands that must pass before Tier 4a begins:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_progression_plan_routes.py tests/test_progression_plan_utils.py -q`
  - refreshed progression-focused Playwright API tests
  - progression lifecycle smoke
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- Make clear which checks are prerequisite hardening and which belong to the actual Tier 4a migration branch.

Required paired work if Tier 4a proceeds:

1. Wrap the selected progression endpoints.
2. Decide whether `/save_progression_goal` stays redirect-based or becomes a JSON API.
3. Update the API integration expectations.
4. Run progression route tests and the relevant E2E/API tests.

### Tier 4a Next Actions

Current execution status: completed on 2026-04-08.

- [x] Complete Tier 4a prerequisite hardening for 95%-confidence execution
- [x] Decide the intended client contract for `POST /save_progression_goal`
- [x] Wrap the selected progression endpoints
- [x] Update frontend handling that consumes the wrapped progression responses
- [x] Update API integration expectations for progression endpoints
- [x] Run progression route tests
- [x] Run the relevant progression/API/E2E coverage before marking Tier 4a complete

### 4b. Summary + Volume Splitter Routes

**Status:** Completed on 2026-04-09; backend wrapper cutover implemented on 2026-04-08, automated verification closure completed on 2026-04-09, and the separate manual-smoke gate was explicitly waived on 2026-04-09 after a fresh targeted live browser rerun

This was the highest-risk area because the live summary and volume consumers had to be made wrapper-safe before the backend cutover could happen safely.

### Scope Decisions Locked For This Phase

- `GET /api/pattern_coverage` is explicitly **deferred from the wrapper cutover** for this phase.
  - Its current `success` + `data` contract remains unchanged.
  - It stays covered by refreshed API and browser regression checks.
- `POST /api/export_volume_excel` remains **out of wrapper scope** because it is a file download.
- Non-XHR HTML rendering for `GET /session_summary` and `GET /weekly_summary` remains unchanged.

### Execution Log

- During prerequisite hardening, updated `routes/session_summary.py` and `routes/weekly_summary.py` to use shared `is_xhr_request()` detection while preserving the then-current JSON shapes.
- Updated `templates/session_summary.html` and `templates/weekly_summary.html` so the live inline fetch consumers:
  - send explicit JSON/XHR headers
  - accept both current top-level payloads and future wrapped `data` payloads
  - preserve loading rows, empty-state rows, tooltip setup, formula text updates, and filter-view-mode transforms
- Updated `templates/weekly_summary.html` pattern-coverage handling to keep working against the current `success` + `data` contract while remaining compatible with a future wrapped payload if scope changes later.
- Updated `static/js/modules/volume-splitter.js` with explicit JSON request headers, local unwrap/error helpers, and dual-shape handling for calculate/save/history/load/delete flows while leaving Excel export behavior unchanged.
- Extended the summary route tests to verify JSON/XHR detection via `X-Requested-With: XMLHttpRequest`.
- Refreshed `e2e/api-integration.spec.ts` to target the live `/weekly_summary`, `/session_summary`, and volume persistence routes instead of stale `/get_weekly_summary` and `/get_session_summary` paths.
- Upgraded `e2e/summary-pages.spec.ts` with real fetch-backed weekly-summary/session-summary browser smokes plus a live pattern-coverage browser smoke.
- Kept the existing volume-splitter save/load/delete browser smoke in the gate and updated it to treat the explicit empty-history placeholder row as intentional behavior.
- Wrapped the XHR/API success and error paths for `GET /session_summary` and `GET /weekly_summary` with `success_response(...)` / `error_response(...)` while preserving the non-XHR HTML render path.
- Wrapped the in-scope volume-splitter endpoints:
  - `POST /api/calculate_volume`
  - `GET /api/volume_history`
  - `POST /api/save_volume_plan`
  - `GET /api/volume_plan/<id>`
  - `DELETE /api/volume_plan/<id>`
- Left `GET /api/pattern_coverage` on its existing `success` + `data` contract and left `POST /api/export_volume_excel` unwrapped because it remains a file-download flow.
- Tightened `tests/test_session_summary_routes.py`, `tests/test_weekly_summary_routes.py`, `tests/test_volume_splitter_api.py`, `tests/test_downstream_normalization.py`, `tests/test_ui_flows.py`, `e2e/api-integration.spec.ts`, and `e2e/summary-pages.spec.ts` to the final wrapped contract where those checks are meant to validate the cutover itself.
- Updated the volume-splitter persistence smoke to match the standardized delete success copy returned by the wrapped API flow.

### Prerequisite Verification Completed On 2026-04-08

- Targeted route gate:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_volume_splitter_api.py -q`
  - Result: `73 passed`
- Refreshed summary/volume Playwright API checks:
  - `npx playwright test e2e/api-integration.spec.ts -g "Weekly Summary API|Session Summary API|Volume Splitter API|GET /api/pattern_coverage returns movement pattern analysis" --project=chromium`
  - Result: `10 passed`
- Summary-page browser smokes:
  - `npx playwright test e2e/summary-pages.spec.ts -g "fetch-backed weekly summary updates use explicit JSON intent|fetch-backed session summary updates use explicit JSON intent|weekly summary page renders pattern coverage from the live fetch" --project=chromium`
  - Result: `3 passed`
- Volume-splitter persistence smoke:
  - `npx playwright test e2e/volume-splitter.spec.ts -g "saved plans can be restored and deleted through volume history" --project=chromium`
  - Result: `1 passed`
- Full unit suite:
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - Result: `979 passed, 1 skipped`

### Post-Cutover Verification Completed On 2026-04-08

- Cutover-aware Python verification slice:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_volume_splitter_api.py tests/test_downstream_normalization.py tests/test_ui_flows.py -q`
  - Result: `96 passed`
- Refreshed summary/volume Playwright API checks after the wrapper swap:
  - `npx playwright test e2e/api-integration.spec.ts -g "Weekly Summary API|Session Summary API|Volume Splitter API|GET /api/pattern_coverage returns movement pattern analysis" --project=chromium`
  - Result: `10 passed`
- Summary-page browser smokes after the wrapper swap:
  - `npx playwright test e2e/summary-pages.spec.ts -g "fetch-backed weekly summary updates use explicit JSON intent|fetch-backed session summary updates use explicit JSON intent|weekly summary page renders pattern coverage from the live fetch" --project=chromium`
  - Result: `3 passed`
- Volume-splitter persistence smoke after the wrapper swap:
  - `npx playwright test e2e/volume-splitter.spec.ts -g "saved plans can be restored and deleted through volume history" --project=chromium`
  - Result: `1 passed`
- Full unit suite after the wrapper swap:
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - Result: `979 passed, 1 skipped`
- Full Playwright suite:
  - `npx playwright test`
  - Result: `268 passed, 45 failed`
  - Current failures are concentrated in non-Tier-4b surfaces:
    - empty workout-log import messaging
    - duplicate-submit / double-click prevention
    - progression display
    - superset edge cases
    - validation-boundary form flows
    - workout-log editing flows
    - workout-plan click-action flow
- Failure triage rerun on 2026-04-09:
  - `npx playwright test --last-failed --reporter=json > playwright-last-failed.json`
  - Result: `32` failures reproduced; `13` of the original failures did not reproduce on the immediate rerun
  - Reproduced failures by area:
    - `22` in `e2e/validation-boundary.spec.ts`
    - `6` in `e2e/superset-edge-cases.spec.ts`
    - `2` in `e2e/error-handling.spec.ts`
    - `1` in `e2e/empty-states.spec.ts`
    - `1` in `e2e/workout-plan.spec.ts`
  - Dominant reproduced root cause:
    - `26` failures surface `Exercise already exists in this routine.` as a console-detected API validation error
    - `1` failure surfaces a duplicate-insert DB `UNIQUE constraint failed ...` error during rapid double-click submission
    - the remaining reproduced failures are handled non-Tier-4b validation/no-data messages being treated as console-test failures
  - Original full-run failures that did not reproduce immediately:
    - `1` progression display failure
    - `5` workout-log editing/progression-indicator failures
    - `6` superset interaction/persistence failures
    - `1` validation-boundary failure
  - Tier 4b classification from this rerun:
    - no reproduced failures touched `session_summary`, `weekly_summary`, `volume_splitter`, or the Tier 4b browser/API confidence slices
    - this points to broader E2E isolation / state-pollution / console-error-harness issues rather than a Tier 4b wrapper-cutover regression
- Closure evidence on 2026-04-09:
  - `npx playwright test e2e/summary-pages.spec.ts e2e/volume-splitter.spec.ts --project=chromium --reporter=line`
  - Result: `46 passed`
- Manual summary-page and volume-splitter browser smoke:
  - Not run in a separate interactive human pass during this cutover turn
  - Explicit waiver recorded instead, backed by the green live browser rerun above plus the already-green full Playwright and full `pytest` evidence

### Historical Baseline Before Prerequisite Hardening

- `templates/session_summary.html` has inline `updateSessionSummary()` fetch logic that:
  - calls `GET /session_summary` with `Accept: application/json`
  - reads top-level `data.session_summary`
  - reads top-level `data.categories`
  - reads top-level `data.isolated_muscles`
- `templates/weekly_summary.html` has inline `updateWeeklySummary()` fetch logic that:
  - calls `GET /weekly_summary` with `Accept: application/json`
  - reads top-level `data.weekly_summary`
  - reads top-level `data.categories`
  - reads top-level `data.isolated_muscles`
- `templates/weekly_summary.html` also has inline `updatePatternCoverage()` logic that:
  - calls `GET /api/pattern_coverage`
  - reads `result.success`
  - reads `result.data`
- `static/js/modules/volume-splitter.js` reads:
  - `payload.results`
  - `payload.suggestions`
  - `payload.ranges`
  - `Object.entries(history)`
  - `result.success`
  - `result.error`
  - `plan.training_days`
  - `plan.volumes`
- `static/js/modules/summary.js` is wrapper-tolerant, but it is not the critical live consumer on the current summary pages
- `static/js/modules/summary.js` is currently bypassed on the live summary pages because `pageHasOwnUpdater()` short-circuits when `#counting-mode` exists
- `routes/session_summary.py` and `routes/weekly_summary.py` only switch to JSON when `Accept` equals exactly `application/json`, rather than using shared XHR/API detection
- `static/js/modules/volume-splitter.js` uses raw `fetch(...)` rather than `api` / `fetch-wrapper`, so it does not yet get shared error normalization or request-ID handling
- Route tests still assert top-level keys like `session_summary` and `weekly_summary`
- `tests/test_volume_splitter_api.py` still asserts the current top-level `results`, `success`, `training_days`, and grouped-history contracts
- `e2e/api-integration.spec.ts` still points summary checks at stale `/get_weekly_summary` and `/get_session_summary` endpoints and does not yet cover the volume save/load/delete contract shapes
- `e2e/summary-pages.spec.ts` is primarily page-structure and toggle coverage, not route-contract confidence evidence
- `e2e/volume-splitter.spec.ts` already has a valuable browser save/load/delete smoke, but it is not yet asserting the final wrapped API contract

Important corrections to the earlier draft:

- `/weekly_summary` must be treated as part of this high-risk scope.
- `/api/calculate_volume` is a `POST` endpoint, not `GET`.
- `GET /api/pattern_coverage` needs an explicit scope decision for Tier 4b instead of being treated as invisible collateral inside `routes/weekly_summary.py`.

Important scope decisions before Tier 4b:

- Decide whether `GET /api/pattern_coverage` joins the Tier 4b wrapper migration.
  - Recommended safe default: defer it unless there is a concrete reason to standardize it in the same branch.
  - Reason: the current weekly summary page already consumes its existing `success` + `data` shape, so leaving it alone keeps Tier 4b narrower while the higher-risk summary and volume consumers are hardened first.
- Keep `POST /api/export_volume_excel` out of wrapper scope.
  - Reason: it returns a file download, not a JSON payload.
- Preserve the non-XHR HTML rendering behavior for:
  - `GET /session_summary`
  - `GET /weekly_summary`

### Recommended Safe Execution Posture

Treat Tier 4b as a compatibility-first rollout, not a backend-first refactor.

- First make the live callers and stale tests tolerant of both:
  - the current top-level JSON payloads
  - the future wrapped `data` payloads
- Keep the current backend contracts in place while that prerequisite work lands.
- Only perform the backend wrapper cutover after the paired frontend and confidence checks are already green in the same branch state.

In simple terms:

- make the app bilingual first
- switch the backend contract second

### 95% Confidence Prerequisites For Tier 4b

These should be completed before Tier 4b is treated as execution-ready with approximately 95% confidence that summary and volume-splitter flows continue to work after the wrapper migration.

#### P1: Lock the exact Tier 4b scope and contract boundaries

- Decide the in-scope JSON endpoints explicitly:
  - `GET /session_summary` JSON branch only
  - `GET /weekly_summary` JSON branch only
  - `GET /api/pattern_coverage` if approved into scope
  - `POST /api/calculate_volume`
  - `GET /api/volume_history`
  - `POST /api/save_volume_plan`
  - `GET /api/volume_plan/<id>`
  - `DELETE /api/volume_plan/<id>`
- Decide the out-of-scope endpoints explicitly:
  - `POST /api/export_volume_excel`
  - HTML rendering for `/session_summary` and `/weekly_summary`
- Record the intended wrapped success and error payloads before editing route code.
- Keep the migration conservative:
  - wrap existing payloads under `data`
  - avoid changing inner field names unless there is a strong reason
  - preserve existing sorting, empty-state, and alias behavior inside the wrapped payloads

#### P2: Make JSON/XHR intent deterministic before changing the summary contracts

- Current risk:
  - `routes/session_summary.py` and `routes/weekly_summary.py` return JSON only when `Accept` is exactly `application/json`
  - this is more brittle than the shared `is_xhr_request()` helper already used elsewhere
- Before Tier 4b route wrapping, choose one path:
  - update the summary routes to use shared XHR/API detection, or
  - add dedicated `/api/` aliases for summary JSON fetches and migrate the page scripts to those aliases
- Keep the existing HTML page render behavior intact for normal browser navigation.
- For any frontend callers that remain on direct `fetch(...)`, make JSON intent explicit:
  - `Accept: application/json`
  - `X-Requested-With: XMLHttpRequest`

#### P3: Refresh stale API integration coverage to the live route inventory

- Replace stale summary API checks that still point at:
  - `/get_weekly_summary`
  - `/get_session_summary`
- Move those checks to the real live routes:
  - `/weekly_summary` with JSON intent
  - `/session_summary` with JSON intent
- Add missing API integration coverage for the live volume persistence routes:
  - `POST /api/save_volume_plan`
  - `GET /api/volume_history`
  - `GET /api/volume_plan/<id>`
  - `DELETE /api/volume_plan/<id>`
- If `GET /api/pattern_coverage` is included in Tier 4b scope, add exact contract checks there too.
- Do not count the current stale summary API checks as confidence evidence until they target the real live routes.

#### P4: Add exact route-contract coverage for the Tier 4b routes

- Extend the existing route test files rather than relying only on browser coverage:
  - `tests/test_session_summary_routes.py`
  - `tests/test_weekly_summary_routes.py`
  - `tests/test_volume_splitter_api.py`
- Required assertions for summary routes:
  - exact wrapped JSON success payload for XHR/API callers
  - exact wrapped JSON error payload for XHR/API callers
  - unchanged HTML rendering behavior for non-XHR requests
  - continued presence of expected inner fields such as:
    - `session_summary`
    - `weekly_summary`
    - `categories`
    - `isolated_muscles`
    - `modes`
- Required assertions for volume routes:
  - `calculate_volume` preserves inner `results`, `suggestions`, and `ranges`
  - `save_volume_plan` still returns the inserted `plan_id`
  - `volume_history` still preserves grouped plan history and ordering semantics
  - `volume_plan/<id>` still preserves `training_days`, `created_at`, and `volumes`
  - delete still removes both the parent plan and dependent `muscle_volumes` rows
  - not-found and internal-error cases use the agreed wrapped error shape
- If `GET /api/pattern_coverage` is in scope, extend `tests/test_weekly_summary_routes.py` or add a dedicated route test for it.

#### P5: Harden the live summary page JS against the wrapped contract before switching the backend

- Current risk:
  - the live summary pages do not rely on `static/js/modules/summary.js`
  - they use inline template scripts that read the current top-level JSON keys directly
- Required hardening targets:
  - `templates/session_summary.html`
  - `templates/weekly_summary.html`
- Make the inline fetch consumers explicitly wrapper-tolerant for:
  - summary arrays
  - categories
  - isolated muscles
  - modes
  - pattern coverage if it joins Tier 4b
- Preserve the current UX:
  - loading spinners
  - empty-state rows
  - formula text updates when counting mode changes
  - tooltip initialization
  - filter-view-mode display transforms
  - inline error rows when fetches fail

#### P6: Harden the volume-splitter frontend against the wrapped contract before switching the backend

- Current risk:
  - `static/js/modules/volume-splitter.js` still uses raw `fetch(...)`
  - it reads the current top-level payloads directly
- Required hardening targets:
  - `static/js/modules/volume-splitter.js`
  - optional: `static/js/modules/fetch-wrapper.js` if response extraction should be centralized
- Preferred direction:
  - migrate the JSON endpoints in this module to the shared `api` wrapper, or
  - add explicit local unwrap helpers and consistent error handling if full migration would be too disruptive
- Make response handling explicit for:
  - `POST /api/calculate_volume`
  - `GET /api/volume_history`
  - `POST /api/save_volume_plan`
  - `GET /api/volume_plan/<id>`
  - `DELETE /api/volume_plan/<id>`
- Preserve the current UX:
  - result-table rendering
  - AI suggestions rendering
  - history sorting by `created_at`
  - mode switching and restored plan detection
  - save/load/delete toasts
  - export-to-Excel behavior remaining untouched

#### P7: Add browser-level confidence coverage for the live summary and volume flows

- `e2e/summary-pages.spec.ts` should be upgraded from mostly structure coverage to real fetch-backed smoke coverage.
- Add or tighten one weekly-summary browser smoke that:
  - opens `/weekly_summary`
  - waits for the initial fetch-backed table render or empty-state row
  - switches counting mode
  - switches contribution mode
  - confirms the table updates without console errors
  - confirms pattern coverage still renders if that route is in scope
- Add or tighten one session-summary browser smoke that:
  - opens `/session_summary`
  - waits for the initial fetch-backed table render or empty-state row
  - switches counting mode
  - switches contribution mode
  - confirms the table updates without console errors
- Keep the existing volume-splitter save/load/delete smoke as a prerequisite confidence gate.
- If the wrapped contract changes the volume-splitter fetch path materially, extend that smoke to assert the live wrapped behavior rather than only successful responses.

#### P8: Define the exact pre-execution verification gate for Tier 4b

- Before starting the Tier 4b backend wrapper migration, require all of the following to pass in the same branch state:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_volume_splitter_api.py -q`
  - refreshed summary/volume-focused Playwright API checks
  - summary page browser smokes
  - volume-splitter persistence browser smoke
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- Keep the gate branch-specific:
  - do not rely on historical pass counts
  - re-run the exact checks in the same branch state that is considered execution-ready

#### Recommended Contract Assumption For Tier 4b Prerequisite Work

Unless explicitly re-decided, the safest end-state contract assumption is:

| Endpoint | Recommended success payload | Recommended error payload | Notes |
|---|---|---|---|
| `GET /session_summary` (XHR/API) | `jsonify(success_response(data={"session_summary": [...], "categories": [...], "isolated_muscles": ..., "modes": {...}}))` | `error_response(...)` | HTML render path stays unchanged for non-XHR requests |
| `GET /weekly_summary` (XHR/API) | `jsonify(success_response(data={"weekly_summary": [...], "categories": [...], "isolated_muscles": ..., "modes": {...}}))` | `error_response(...)` | HTML render path stays unchanged for non-XHR requests |
| `GET /api/pattern_coverage` | `jsonify(success_response(data=coverage))` | `error_response(...)` | Include only if approved into Tier 4b scope |
| `POST /api/calculate_volume` | `jsonify(success_response(data={"results": ..., "suggestions": ..., "ranges": ...}))` | `error_response(...)` | Preserve current range-sanitization behavior |
| `GET /api/volume_history` | `jsonify(success_response(data=history))` | `error_response(...)` | Preserve grouped plan-history inner shape unless explicitly redesigned |
| `POST /api/save_volume_plan` | `jsonify(success_response(data={"plan_id": id}, message="Volume plan saved successfully"))` | `error_response(...)` | Preserve DB side effects and inserted id visibility |
| `GET /api/volume_plan/<id>` | `jsonify(success_response(data=plan))` | `error_response(...)` | Preserve `training_days`, `created_at`, and `volumes` inside the wrapped `data` |
| `DELETE /api/volume_plan/<id>` | `jsonify(success_response(message="Volume plan deleted successfully"))` | `error_response(...)` | No extra `data` required on success |

#### Working Checklist For The Prerequisite-Hardening Repo State

Use this as the practical execution checklist that was completed for the Tier 4b prerequisite phase on 2026-04-08.

This is intentionally written in the safest application order rather than in a generic backlog order.

1. [x] Lock the Tier 4b scope first.
2. [x] Explicitly defer `GET /api/pattern_coverage` from the Tier 4b wrapper cutover unless a concrete reason is recorded to include it.
3. [x] Keep the current `GET /api/pattern_coverage` `success` + `data` contract unchanged during prerequisite hardening.
4. [x] Lock the exact wrapped contract for every remaining in-scope Tier 4b endpoint.
5. [x] Decide how summary JSON callers will be identified reliably:
   - shared `is_xhr_request()` detection, or
   - dedicated `/api/` summary aliases
6. [x] Make summary-page fetches and any remaining raw volume-splitter fetches explicitly request JSON.
7. [x] Harden the inline summary page scripts so they can consume both the current top-level payloads and the future wrapped payloads without changing current UX.
8. [x] Harden `static/js/modules/volume-splitter.js` so it can consume both the current top-level payloads and the future wrapped payloads without changing current UX.
9. [x] Replace stale API integration checks that still target `/get_weekly_summary` and `/get_session_summary`.
10. [x] Add missing API integration coverage for volume save/load/delete/history.
11. [x] Keep `GET /api/pattern_coverage` covered by API and weekly-summary browser regression checks while it remains deferred.
12. [x] Add browser-level summary smokes that exercise real fetch-backed updates, not just static structure.
13. [x] Re-run the targeted Tier 4b prerequisite gate in one branch state and record the exact results.

#### Backend Cutover Checklist For The Paired Post-Prerequisite Branch

Use this as the separate follow-on checklist for the backend wrapper swap itself, after the prerequisite gate is already green in the same branch state.

14. [x] Only after steps 1-13 pass, wrap the selected backend endpoints in one paired cutover branch.
15. [x] Land exact final wrapped route-contract assertions in that same cutover branch if they are not written to be dual-shape tolerant during prerequisite hardening.

### Recommended Execution Order For Tier 4b Prep

Use this order to keep Tier 4b controlled and to avoid changing backend contracts before the paired frontend and tests are ready.

1. Lock scope and contract first.
   - Decide whether `pattern_coverage` is deferred or included.
   - Recommended safe default: defer it.
   - Keep its current `success` + `data` contract unchanged while the rest of Tier 4b is hardened.
   - Lock the final wrapped payload shape for each remaining in-scope endpoint before route edits begin.

2. Make JSON intent deterministic next.
   - Resolve the brittle summary-route JSON detection.
   - Ensure the frontend callers clearly request JSON responses.

3. Harden the live frontend consumers before backend cutover.
   - Update the summary page inline scripts.
   - Update `static/js/modules/volume-splitter.js`.
   - Preserve current UX behavior while making response handling dual-shape tolerant.

4. Refresh the stale API and browser confidence layer against the live route inventory.
   - Remove `/get_weekly_summary` and `/get_session_summary`.
   - Add the missing live volume persistence route coverage.
   - Keep `pattern_coverage` covered by regression checks while it remains deferred.
   - Add real fetch-backed summary browser smokes.

5. Run the Tier 4b prerequisite gate.
   - Only treat Tier 4b as execution-ready once the targeted tests and browser checks pass together in the same branch state.

6. Perform the backend wrapper cutover last, in one paired branch.
   - Wrap the selected routes.
   - Land any exact final wrapped-contract assertions that are not already dual-shape tolerant.
   - Re-run the targeted gate before calling the migration safe.

### Practical Start Point For Tier 4b Prep

If Tier 4b prerequisite work begins next, the recommended first concrete tasks are:

1. decide whether `GET /api/pattern_coverage` is explicitly deferred or intentionally included
2. if deferred, explicitly record that its current `success` + `data` contract stays unchanged for this phase
3. make summary JSON intent deterministic and explicit
4. then harden the live summary templates and `static/js/modules/volume-splitter.js` to consume both current and wrapped responses without changing backend contracts yet
5. after that, refresh the stale `/get_weekly_summary` and `/get_session_summary` API checks to the real live routes

### Concrete Tier 4b Prep Todo List

Use this as the implementation-oriented checklist for prerequisite work before the Tier 4b wrapper migration itself.

This section is ordered to match the recommended safe rollout.

#### Step 1: Lock the final endpoint contracts in writing

Files to touch:

- `docs/archive/DOCS_AUDIT_PLAN.md`
- `routes/session_summary.py`
- `routes/weekly_summary.py`
- `routes/volume_splitter.py`
- `utils/errors.py` (reference only unless the shared contract helper itself must change)

What to do:

- Document the intended success and error shape for every in-scope Tier 4b endpoint.
- Decide whether `GET /api/pattern_coverage` is included or explicitly deferred.
- If deferred, explicitly record that its current `success` + `data` contract remains unchanged in this phase and is protected by regression coverage rather than wrapper migration.
- Explicitly record that `POST /api/export_volume_excel` stays outside this wrapper migration.
- Confirm that HTML rendering for `/session_summary` and `/weekly_summary` is preserved.

#### Step 2: Make JSON/XHR intent explicit and stable

Files to touch:

- `templates/session_summary.html`
- `templates/weekly_summary.html`
- `static/js/modules/volume-splitter.js`
- optional: `static/js/modules/fetch-wrapper.js`
- optional: `routes/session_summary.py`
- optional: `routes/weekly_summary.py`

What to do:

- Ensure summary-page fetches clearly request JSON and are routed through stable JSON detection.
- Ensure any remaining volume-splitter raw fetches clearly request JSON.
- Keep this step focused on signaling and compatibility, not backend wrapper changes yet.

#### Step 3: Harden the live summary pages for dual-shape compatibility

Files to touch:

- `templates/session_summary.html`
- `templates/weekly_summary.html`
- optional: `static/js/modules/summary.js` if shared helpers improve clarity without changing ownership

What to do:

- Add explicit wrapper-aware response extraction in the inline page scripts.
- Make the summary pages tolerant of both:
  - the current top-level JSON payloads
  - the future wrapped `data` payloads
- Keep the current summary-table, categories-table, and isolated-muscles rendering behavior unchanged.
- Preserve:
  - loading state
  - empty-state rows
  - tooltip setup
  - view-mode transforms
  - formula text updates
  - fetch-failure fallback rows

#### Step 4: Harden the volume-splitter page for dual-shape compatibility

Files to touch:

- `static/js/modules/volume-splitter.js`
- optional: `static/js/modules/fetch-wrapper.js`
- `templates/volume_splitter.html` only if small testability hooks or stable selectors are needed

What to do:

- Make response handling explicit for calculate/save/history/load/delete flows.
- Make the page tolerant of both:
  - the current top-level JSON payloads
  - the future wrapped `data` payloads
- Preserve:
  - result rendering
  - suggestions rendering
  - save/load/delete toasts
  - history sorting
  - restored plan loading behavior
  - mode switching
- Leave file-download export behavior unchanged.

#### Step 5: Refresh stale Playwright API coverage

Files to touch:

- `e2e/api-integration.spec.ts`
- optional: `e2e/fixtures.ts`

What to do:

- Replace stale summary API checks with the live `/weekly_summary` and `/session_summary` routes.
- Add live API integration checks for:
  - `POST /api/save_volume_plan`
  - `GET /api/volume_history`
  - `GET /api/volume_plan/<id>`
  - `DELETE /api/volume_plan/<id>`
- If `GET /api/pattern_coverage` remains deferred, keep explicit regression checks for its current `success` + `data` contract.
- Add wrapped-contract checks for `GET /api/pattern_coverage` only if that endpoint joins Tier 4b.

#### Step 6: Upgrade browser confidence coverage

Files to touch:

- `e2e/summary-pages.spec.ts`
- `e2e/volume-splitter.spec.ts`
- optional: `e2e/fixtures.ts`

What to do:

- Add real weekly-summary and session-summary fetch-backed smokes.
- Keep `GET /api/pattern_coverage` covered by the weekly-summary browser confidence layer while it remains deferred.
- Keep the existing volume-splitter save/load/delete smoke as part of the gate.
- Extend browser assertions only as far as needed to prove the wrapped contract did not break the live UX.

#### Step 7: Define and run the exact Tier 4b prerequisite gate

Files to touch:

- `docs/archive/DOCS_AUDIT_PLAN.md`
- optional: `docs/code_cleanup_plan.md` if it should mirror the same gate later

What to do:

- Record the exact commands that must pass before the backend wrapper change begins:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_volume_splitter_api.py -q`
  - refreshed summary/volume Playwright API checks
  - summary page browser smokes
  - volume-splitter persistence smoke
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- Distinguish clearly between:
  - prerequisite hardening that can land before the backend wrapper swap
  - exact final wrapped assertions that should land in the same branch as the backend cutover if needed

#### Step 8: Backend cutover branch only

This is not prerequisite hardening. It begins only after Step 7 is green in the same branch state.

Files to touch:

- `routes/session_summary.py`
- `routes/weekly_summary.py`
- `routes/volume_splitter.py`
- `tests/test_session_summary_routes.py`
- `tests/test_weekly_summary_routes.py`
- `tests/test_volume_splitter_api.py`

What to do:

- Wrap the selected in-scope endpoints with the locked Tier 4b contract.
- Land exact final wrapped route-contract assertions if they were not made dual-shape tolerant earlier.
- Re-run the targeted Tier 4b gate before calling the cutover safe.

### Tier 4b Next Actions

Current execution status: Tier 4b is fully closed. The backend wrapper cutover completed on 2026-04-08, the targeted gate is green, full `pytest` is green, the full Playwright suite is green after the 2026-04-09 Tier 5c stabilization pass, and the remaining manual-smoke gate was resolved on 2026-04-09 via an explicit waiver backed by a fresh live browser rerun of the summary and volume surfaces.

- [x] Complete Tier 4b prerequisite hardening for 95%-confidence execution in this order
  - [x] lock the exact Tier 4b scope and endpoint contracts
  - [x] decide whether `GET /api/pattern_coverage` is explicitly deferred or intentionally included
  - [x] if deferred, record that its current `success` + `data` contract remains unchanged in this phase
  - [x] make summary JSON/XHR intent deterministic
  - [x] harden the live summary page scripts for dual-shape compatibility
  - [x] harden `static/js/modules/volume-splitter.js` for dual-shape compatibility
  - [x] refresh stale summary API integration coverage to the live route inventory
  - [x] add missing volume persistence API integration coverage
  - [x] keep `GET /api/pattern_coverage` covered by API and browser regression checks while deferred
  - [x] add real summary-page browser smokes
  - [x] define and pass the Tier 4b prerequisite verification gate
- [x] After the prerequisite gate passes, execute the backend wrapper cutover in one paired branch
  - [x] wrap the selected summary and volume-splitter endpoints
  - [x] land exact final wrapped route-contract assertions if not already dual-shape tolerant
  - [x] re-run the targeted Tier 4b gate before calling the migration safe
- [x] After the migration itself, close the broader verification loop:
  - [x] full `pytest tests/ -q`
  - [x] full Playwright suite
  - [ ] manual summary-page and volume-splitter smoke verification
  - [x] explicit waiver recorded for the separate manual summary-page and volume-splitter smoke requirement
  - [x] decide whether the current non-Tier-4b Playwright failures are triaged, fixed, or explicitly waived for Tier 4b closure

Decision:

- The selected summary and volume-splitter endpoints are now wrapped with the locked Tier 4b contract.
- Do not treat Tier 4b as routine cleanup.
- `GET /api/pattern_coverage` remains intentionally deferred on its current `success` + `data` contract.
- `POST /api/export_volume_excel` remains intentionally outside the wrapper scope.
- The 2026-04-09 last-failed Playwright triage did not identify any reproduced failure that requires reopening the Tier 4b summary/volume cutover itself.
- The unrelated full-Playwright stabilization work belonged under Tier 5c rather than Tier 4b and has now been executed there.
- The Tier 5c stabilization pass re-ran the reproduced browser-failure cluster cleanly (`80 passed`) and returned the full Playwright suite to green.
- The 2026-04-09 live browser rerun of `e2e/summary-pages.spec.ts` plus `e2e/volume-splitter.spec.ts` passed cleanly (`46 passed`) and provided fresh summary/volume surface evidence on the same post-cutover repo state.
- No interactive human browser smoke was run in this environment, so the separate manual-smoke requirement was explicitly waived rather than silently assumed complete.
- Tier 4b can now be treated as fully closed unless new evidence reaches the summary/volume surfaces.

---

## Tier 5: Follow-Up Hardening

**Execution status:** Completed on 2026-04-09  
**Risk:** Medium overall  
**Why this was safe to complete:** Each Tier 5 slice was kept narrow and verified on its real regression surface: Tier 5a on live summary/volume browser checks, Tier 5b on the shared pytest harness plus full unit rerun, and Tier 5c on the reproduced Playwright/browser failure cluster.

Tier 5 now contains three completed slices:

- **5a:** completed live CSS consolidation for overlapping summary/volume indicator styles
- **5b:** completed test harness isolation to reduce temp-DB locking risk
- **5c:** completed non-Tier-4b Playwright stabilization for workout-plan/superset/validation state isolation and console-error handling

### 5a. Live CSS Consolidation

**Status:** Completed on 2026-04-09  
**Risk:** Medium  
**Why this proceeded:** Consolidating live loaded CSS can change selector ownership, specificity, and load-order behavior, so it only proceeded once the summary/volume browser surface was already green and could be revalidated immediately after the selector cutover.

Current state:

- `static/css/styles_volume.css` now owns the shared `.volume-indicator`, `.volume-badge`, classification colors, and shared legend text rules.
- `static/css/session_summary.css` now keeps the summary-page-specific scroll, table, and summary dark-mode rules without redefining the shared volume tokens.
- `templates/session_summary.html` now loads `styles_volume.css`, and both summary templates now load the shared volume styles before `session_summary.css` so generic tokens land before page-specific overrides.
- `docs/CSS_OWNERSHIP_MAP.md` now reflects that `styles_volume.css` is the canonical owner for shared volume indicators, badges, classification colors, and legend text.
- `e2e/summary-pages.spec.ts` now includes explicit shared legend swatch color assertions on both summary pages.

Execution posture for this slice:

- Treat this slice as complete unless a future CSS refactor reintroduces duplicated ownership for the shared volume tokens.
- Keep `styles_volume.css` as the canonical owner for shared summary/splitter volume status tokens.
- Continue using the summary-page plus volume-splitter browser suite as the primary regression surface for future changes in this area.

Verification:

- `npx playwright test e2e/summary-pages.spec.ts e2e/volume-splitter.spec.ts --project=chromium --reporter=line`
  - Result: **48 passed**

Tier 5a checklist:

- [x] Inventory overlapping volume-indicator selectors in `static/css/session_summary.css` and `static/css/styles_volume.css`
- [x] Choose a canonical owner for the shared volume-indicator styles and document the intended ownership
- [x] Confirm template load order and specificity dependencies on session summary, weekly summary, and volume-splitter pages
- [x] Add or refresh visual regression coverage for the affected pages before changing shared selectors
- [x] Consolidate duplicated selectors without changing rendered labels, status colors, or page-specific overrides
- [x] Run summary-page and volume-splitter smoke verification after the consolidation

### 5b. Test Harness Lock Fix

**Status:** Completed on 2026-04-09  
**Risk:** Medium  
**Why this proceeded:** This slice improves long-term reliability, and once the main route/frontend rollout stabilized it became safe to execute as a bounded shared-infrastructure cutover with explicit regression coverage plus full-suite verification.

Current state:

- `tests/conftest.py` now uses a unique `tmp_path` database file per test instead of a single session-wide temp DB path.
- The shared Flask test app fixture now initializes the schema against that per-test path, while `client`, `db_handler`, and `clean_db` continue to use the same fixture names and semantics.
- Added `tests/test_harness_isolation.py` to pin the no-argument `DatabaseHandler()` path wiring and to verify that isolated temp databases do not share SQLite file locks.
- Targeted verification passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_harness_isolation.py tests/test_priority0_fk_integrity.py tests/test_volume_splitter_api.py tests/test_program_backup.py tests/test_workout_plan_routes.py -q`
  - Result: **76 passed, 1 skipped**
- Full unit verification passed:
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - Result: **981 passed, 1 skipped**

Execution posture for this slice:

- Treat this slice as complete unless a later test-infrastructure change reintroduces shared-path assumptions.
- Keep future harness edits on the same standard: isolated DB paths plus full-suite verification.
- Revalidate Playwright/API setup only if a future harness change affects end-to-end initialization; this Tier 5b cutover did not.

Tier 5b checklist:

- [x] Audit `tests/conftest.py` DB setup/teardown flow and identify where a shared temp DB path is still assumed
- [x] Move the test harness to unique per-test or per-worker temp DB paths
- [x] Confirm schema initialization and seed/setup helpers still work with isolated temp DB paths
- [x] Add or refresh regression coverage for lock-sensitive and concurrent DB test scenarios
- [x] Re-run the full unit suite after the harness change
- [x] Re-evaluate Playwright/API coverage needs and record that no rerun was required because end-to-end setup was unchanged

### 5c. Non-Tier-4b Playwright Stabilization

**Status:** Completed on 2026-04-09  
**Risk:** Medium  
**Why this proceeded:** The reproduced failures were outside the Tier 4b summary/volume cutover, but they were concrete current failures in the shared Playwright/browser layer. That made Tier 5c the correct follow-up reliability slice to execute without reopening Tier 4b.

Current state:

- The 2026-04-09 `npx playwright test --last-failed` rerun reproduced `32` failures and did not reproduce `13` of the original full-run failures, confirming the hot cluster was concentrated outside Tier 4b.
- The reproduced cluster was concentrated in `e2e/validation-boundary.spec.ts` (`22`), `e2e/superset-edge-cases.spec.ts` (`6`), `e2e/error-handling.spec.ts` (`2`), `e2e/empty-states.spec.ts` (`1`), and `e2e/workout-plan.spec.ts` (`1`).
- The dominant reproduced signal was duplicate exercise state pollution (`Exercise already exists in this routine.`) plus handled validation/no-data errors being promoted into console-test failures.
- No reproduced failure touched `session_summary`, `weekly_summary`, `volume_splitter`, or the Tier 4b browser/API confidence slices.

Work completed:

- Added shared handled-error helpers in `static/js/modules/fetch-wrapper.js` so validation, no-data, and not-found API failures can be logged as expected warnings instead of hard console errors.
- Updated `static/js/modules/workout-plan.js`, `static/js/modules/exports.js`, and `static/js/modules/workout-log.js` to use the shared handled-error helpers and keep expected UI-handled API failures from tripping the Playwright console harness.
- Hardened workout-plan exercise submission in `static/js/modules/workout-plan.js` with pending-state guarding and button disable/loading behavior to prevent duplicate rapid-submit flows.
- Added shared workout-plan reset coverage in `e2e/fixtures.ts` and applied it to the reproduced failure cluster in `e2e/validation-boundary.spec.ts`, `e2e/superset-edge-cases.spec.ts`, `e2e/error-handling.spec.ts`, `e2e/empty-states.spec.ts`, and `e2e/workout-plan.spec.ts`.
- Removed duplicate-test-data assumptions in `e2e/superset-edge-cases.spec.ts` by selecting unused exercises and tightening the persisted-superset assertion to row-level elements.
- Refreshed `e2e/api-integration.spec.ts` to seed workout-plan add/export coverage from the live exercise inventory before asserting the API responses.

Verification:

- `npx playwright test e2e/validation-boundary.spec.ts e2e/superset-edge-cases.spec.ts e2e/error-handling.spec.ts e2e/empty-states.spec.ts e2e/workout-plan.spec.ts --project=chromium --reporter=line` -> `80 passed`
- `npx playwright test e2e/api-integration.spec.ts -g "POST /add_exercise with valid data succeeds|POST /export_to_workout_log exports data" --project=chromium --reporter=line` -> `2 passed`
- Full `npx playwright test --project=chromium --reporter=line` rerun completed green; `test-results/.last-run.json` now reports `"status": "passed"` with no failed tests.

Execution posture after completion:

- Treat this slice as complete unless a new non-Tier-4b browser failure cluster appears.
- Do not reopen Tier 4b unless new evidence reaches the summary/volume surfaces.
- Treat Tier 5a as complete; if future shared volume-selector work is needed, keep it isolated from unrelated browser stabilization changes.

Tier 5c checklist:

- [x] Define which handled API errors should remain console-test failures and which should be treated as expected UI-handled outcomes
- [x] Audit `e2e/fixtures.ts` console collection policy against the reproduced error cases and narrow any overly broad failures
- [x] Isolate or reset workout-plan routine/exercise state in the reproduced validation, superset, and workout-plan specs
- [x] Remove duplicate-test-data assumptions in the reproduced specs by using unique setup data or explicit cleanup
- [x] Re-run `npx playwright test --last-failed` after the harness/state-isolation changes
- [x] Re-run the full `npx playwright test` suite only after the reproduced cluster is stable

## Tier 6: Post-Rollout Re-Audit Triggers

**Execution status:** Completed on 2026-04-09 as a post-rollout snapshot re-audit  
**Risk:** Low overall  
**Why executed now:** Later rollout completion left a stale Tier-reference in `docs/README.md`, and that made it worthwhile to run the maintenance triggers once, capture a fresh repo-state snapshot, and confirm that the backend logging and progression-contract tiers still match their completed rollout state.

Tier 6 contains three post-rollout slices:

- **6a:** Tier 1 documentation and inventory drift re-audit
- **6b:** Tier 2 logging regression and logger-tuning re-audit
- **6c:** Tier 4a progression contract drift re-audit

### 6a. Tier 1 Docs Drift Re-Audit

**Status:** Completed on 2026-04-09; future-trigger slice remains available  
**Risk:** Low  
**Why executed:** Later tier completion made the README pointer stale, so this slice was reopened narrowly to verify the current repo inventories and update only the affected documentation.

Current state:

- `docs/` still contains **18** files: **13** active top-level docs plus **5** archived docs under `docs/archive/`.
- `e2e/` still contains **17** Playwright spec files, so `docs/E2E_TESTING.md` inventory remains accurate.
- The deleted CSS files were not reintroduced as live references; the remaining grep hits are limited to historical docs plus the consolidation note in `static/css/styles_buttons.css`.
- `docs/CSS_OWNERSHIP_MAP.md` still matches the live template-loading model and current shared volume-style ownership.
- `docs/README.md` was refreshed so its quick pointer now reflects the completed rollout and follow-up maintenance posture.

Execution posture for this slice:

- Treat future reopens as conditional maintenance rather than as blocking rollout work.
- Re-open this slice only when a concrete repo change invalidates a Tier 1 artifact.
- Keep future responses scoped to the stale artifact instead of re-running all of Tier 1 by default.

Tier 6a checklist for the 2026-04-09 snapshot:

- [x] Re-audit `docs/` inventory against `docs/README.md`
- [x] Re-audit Playwright inventory against `docs/E2E_TESTING.md`
- [x] Re-grep the repo for live references to the deleted CSS files
- [x] Reconfirm the live CSS loading model against `docs/CSS_OWNERSHIP_MAP.md`

### 6b. Tier 2 Logging Re-Audit

**Status:** Completed on 2026-04-09; future-trigger slice remains available  
**Risk:** Low  
**Why executed:** Tier 6 is the right place to confirm that the later Tier 3 through Tier 5 backend edits did not quietly reintroduce raw `print()` calls or drift away from the shared logger pattern.

Current state:

- Repo grep still finds **zero** raw `print()` calls in `routes/` and `utils/`.
- The touched backend modules in `routes/` and `utils/` still use `get_logger()` for shared logger ownership.
- No repo-only evidence from this snapshot suggests further backend logger-level tuning is needed right now.

Execution posture for this slice:

- Treat future reopens as observability maintenance rather than as active feature work.
- Re-open this slice only when a concrete regression or tuning need is observed.
- Prefer targeted fixes and targeted verification over broad rework.

Tier 6b checklist for the 2026-04-09 snapshot:

- [x] Re-grep `routes/` and `utils/` for raw `print()` drift
- [x] Reconfirm shared backend logger ownership in touched `routes/` and `utils/` modules
- [x] Record that no repo-only logger-tuning follow-up was identified in this snapshot

### 6c. Tier 4a Progression Contract Re-Audit

**Status:** Completed on 2026-04-09; future-trigger slice remains available  
**Risk:** Low  
**Why executed:** The Tier 4a progression routes were touched again during later rollout work, so Tier 6 is the right place to confirm that the wrapped contract inventory and the intentional `save_progression_goal` split still match the completed Tier 4a decision.

Current state:

- `routes/progression_plan.py` still exposes the same wrapped Tier 4a progression endpoint set:
  - `POST /get_exercise_suggestions`
  - `POST /get_current_value`
  - `POST /save_progression_goal`
  - `DELETE /delete_progression_goal/<id>`
  - `POST /complete_progression_goal/<id>`
- The wrapped JSON envelopes remain in place for the fetch/XHR callers, and `POST /save_progression_goal` still keeps the intentional non-XHR redirect fallback to `/progression`.
- The paired progression contract coverage in `tests/test_progression_plan_routes.py`, the Playwright API checks, and the live frontend caller in `static/js/modules/progression-plan.js` still target that same route inventory.

Execution posture for this slice:

- Treat future reopens as contract-maintenance work rather than active rollout work.
- Re-open this slice only when progression route behavior or route inventory actually changes.
- Keep future responses scoped to the affected progression endpoint set rather than re-running unrelated Tier 4 work by default.

Tier 6c checklist for the 2026-04-09 snapshot:

- [x] Re-audit the live progression route inventory for new bare-array or bare-object endpoints
- [x] Reconfirm the `save_progression_goal` redirect-vs-JSON split
- [x] Reconfirm that the paired tests and frontend callers still match the wrapped Tier 4a contract

---

## Verification Strategy

Use tier-specific verification instead of one blanket command for every tier.

### After Tier 1

- Repo grep for moved docs, deleted CSS references, and README index accuracy
- Optional: `.\.venv\Scripts\python.exe -m pytest tests/ -q`

### After Tier 2

- Targeted tests for touched modules
- Recommended: `.\.venv\Scripts\python.exe -m pytest tests/ -q`

### After Tier 3

- Required:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_volume_splitter_api.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q`
- Recommended:
  - `.\.venv\Scripts\python.exe -m pytest tests/ -q`

### After Tier 4a

- Progression route tests
- Relevant API integration tests
- Any progression page smoke coverage needed for the changed contract

### Before Tier 4b Execution

- `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_volume_splitter_api.py -q`
- Refreshed summary/volume Playwright API checks against the live route inventory
- Summary-page browser smokes
- Volume-splitter persistence browser smoke
- `.\.venv\Scripts\python.exe -m pytest tests/ -q`

### After Tier 4b

- Full Playwright suite
- Manual summary-page and volume-splitter smoke verification, or an explicit waiver recorded against fresh live browser evidence if no interactive human pass is performed

### After Tier 5

- For Tier 5a:
  - visual regression verification or equivalent browser smoke coverage on summary and volume-splitter pages
  - summary-page and volume-splitter smoke verification after selector consolidation
- For Tier 5b:
  - full `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - refreshed API/Playwright coverage if the harness change alters end-to-end setup behavior
- For Tier 5c:
  - `npx playwright test --last-failed`
  - full `npx playwright test` after the reproduced failure cluster is stable
  - targeted verification of the touched workout-plan, superset, validation, or export flows if the stabilization work changes shared fixture behavior

### After Tier 6

- For Tier 6a:
  - repo grep and doc sanity checks for the specific Tier 1 artifact that became stale
  - refresh only the affected docs inventory, CSS reference, or ownership-map documentation
- For Tier 6b:
  - repo grep for `print()` drift in `routes/` and `utils/`
  - targeted verification for any touched logging modules
  - full `.\.venv\Scripts\python.exe -m pytest tests/ -q` only if the re-audit touches broad shared logging behavior
- For Tier 6c:
  - progression route inventory grep for newly added bare-array or bare-object responses
  - targeted progression route/API/browser verification for the changed progression endpoints
  - full `.\.venv\Scripts\python.exe -m pytest tests/ -q` only if the progression contract re-audit broadens beyond the touched route set

Avoid promising hard pass-count baselines unless the full suites are rerun clean in the same environment after the change.

---

## Final Rollout Summary

| Tier | Status | Risk | Decision |
|---|---|---|---|
| **1** | Completed | None | Done on 2026-04-08 |
| **2** | Completed | Minimal | Done on 2026-04-08 |
| **3** | Completed | Low | Done on 2026-04-08 |
| **4a** | Completed | Medium | Done on 2026-04-08 with paired contract/frontend/test updates |
| **4b** | Completed with explicit manual-smoke waiver | High | The paired cutover work is done, the unrelated Playwright failures were stabilized under Tier 5c, and closure was finalized on 2026-04-09 via an explicit waiver backed by a fresh `46`-test live browser rerun of the summary/volume surfaces |
| **5** | Completed | Medium | Tier 5a, Tier 5b, and Tier 5c are complete with browser and full-suite verification on their respective regression surfaces |
| **6** | Completed post-rollout snapshot | Low | Executed on 2026-04-09 to refresh stale Tier references, reconfirm backend logging cleanup, and reconfirm the Tier 4a progression contracts; re-open only if future drift appears |

## Practical Recommendation

For a 95%-confidence rollout that does not disturb existing features or flows:

1. Tier 1 is already complete.
2. Tier 2 is already complete.
3. Tier 3 is complete.
4. Treat Tier 4b as fully closed; if future summary/volume changes land, require either a real manual smoke pass or another explicit waiver backed by fresh live browser evidence.
5. Treat Tier 5 as fully complete.
6. Treat Tier 6 as complete for the current repo snapshot and re-open it only if later changes stale the completed docs, backend logging, or progression contracts again.
