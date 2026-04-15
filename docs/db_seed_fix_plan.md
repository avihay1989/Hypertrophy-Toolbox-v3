# DB Seed Fix & Dropdown Triage — Consolidated Plan

**Author:** Claude (Opus 4.6), peer-reviewed by Codex
**Date:** 2026-04-11
**Branch:** `spring-cleanup`
**Supersedes:** `docs/db_fix_implementation.md` (removed — wrong scope; architectural rewrite that did not address reported symptoms)
**Confidence:** ≥95% on the active execution path

---

## TL;DR

1. The reported `/workout_plan` dropdown bug is **stale**. User cannot reproduce it on the current branch after Codex's intermediate fix. Fix path is **CLOSED**, retained as a dormant contingency only.
2. A separate, real finding: the seed DB at `data/backup/database.db` is drifted by **14 exercises**, **1595 isolated-muscle rows**, and is missing the entire `movement_pattern` column. Fix in one **catalog-only** commit.
3. Architectural cleanup of the two-DB contract is **deferred** to a future iteration.

**Active work this session:** Phase D (catalog-only seed regen) + Phase E (regression gate).

---

## 1. Evidence Baseline (verified 2026-04-10/11)

### Live DB (`data/database.db`)
- 1897 `exercises`
- 1598 `exercise_isolated_muscles` rows
- `movement_pattern` column present, 1443 populated
- All 12 filter columns populated with real distinct values (range 5–25 distinct)
- User data present: 4 `program_backups`, 8 `program_backup_items`, 1 `progression_goals`

### Seed DB (`data/backup/database.db`)
- 1883 `exercises` (−14 vs live)
- 3 `exercise_isolated_muscles` rows (−1595 vs live)
- `movement_pattern` column: **MISSING**
- Otherwise schema matches

### Code-path verification
- [routes/workout_plan.py:18-99](routes/workout_plan.py#L18-L99) `fetch_unique_values()` queries live DB directly, no cache, no limit.
- [utils/db_initializer.py:344](utils/db_initializer.py#L344) seed-copy path early-returns when `exercises >= MIN_EXERCISE_ROWS (100)`. With 1897 rows it never fires. Also skipped entirely when `TESTING=1` ([utils/db_initializer.py:333](utils/db_initializer.py#L333)).
- [utils/database.py:152-157](utils/database.py#L152-L157) recovery path only runs on SQLite corruption markers (`"malformed"`, `"not a database"`, `"encrypted"`). Copies the seed **wholesale** → this is why Phase D **must** be catalog-only.

### Independent browser verification (Codex)
- `/workout_plan` in Chromium: 1898 exercise options (1897 + JS placeholder), all filters populated, no console/pageerror.
- XHR observed: `/get_workout_plan`, `/get_all_exercises`.

### User reproduction
- Original report: Edge 146, **before** Codex's intermediate fix.
- Current status: **cannot reproduce** on `spring-cleanup`.
- Both simple and advanced filter modes were tested in the original report.

**Conclusion:** Dropdown bug report is stale. Seed drift is real.

---

## 2. Root Cause Analysis

### Dropdown bug — CLOSED
- Not caused by DB (live DB has all data).
- Not caused by bootstrap (seed path doesn't run when `exercises >= 100`).
- Not caused by recovery (no corruption).
- Most likely caused by an intermediate state on the user's local branch that Codex has since patched.
- Cannot reproduce → no code change to ship on this axis.

### Seed drift — OPEN, Phase D target
- Seed file is stale and schema-incomplete vs live DB.
- Recovery path in [utils/database.py:152](utils/database.py#L152) copies this seed wholesale on SQLite corruption, silently degrading the user's catalog and discarding the `movement_pattern` column.
- Fix: regenerate seed with **catalog-only** content (`exercises` + `exercise_isolated_muscles`), matching current live DB, excluding all user-data tables.

### Two-DB architectural smell — DEFERRED (Phase F)
- `SEED_DB_PATH` duplicated in [utils/db_initializer.py:16](utils/db_initializer.py#L16) and [utils/database.py:30](utils/database.py#L30).
- Bootstrap and recovery both read the same untracked sidecar file.
- Both fail soft (warn + continue) when the seed is missing.
- Real but latent; does not cause current symptoms. Scheduled for future iteration, not this one.

---

## 3. Execution Rules for LLM Handoffs

Designed to survive context-window loss and token budgets.

- Execute **one phase at a time**. Never combine phases.
- Each action has an explicit exit artifact. Do not mark complete without it.
- Max files touched per code action: **2**. Max lines touched per code action: **30**. Read/verify actions are unlimited.
- Token budget per action: **≤15k input tokens**. Scope file reads to specific line ranges where possible.
- Never combine in one action: schema changes, catalog data generation, runtime loader logic, recovery behavior, documentation cleanup.
- If an action reveals unexpected state, **stop** and record a note in §10 before continuing.
- A fresh LLM session must be able to continue by reading only:
  1. This file (self-contained).
  2. The referenced files in the active action (listed explicitly per action).
  3. The exit artifact from the previous action.

---

## 4. Phase D — Catalog-Only Seed Regeneration (ACTIVE)

**Goal:** replace `data/backup/database.db` with a catalog-only seed that matches live DB row counts, with zero user-data leakage.
**Blast radius:** one file (`data/backup/database.db`).
**Reversibility:** 100% — `.pre-regen.bak` saved before any destructive action.
**Files referenced across this phase:** [utils/db_initializer.py:34-165](utils/db_initializer.py#L34-L165), [utils/database.py:108-166](utils/database.py#L108-L166), `data/database.db`.

### D0 — Pre-flight snapshot
**Exit artifact:** `debug/D0_preflight.md`

- [x] Record live DB row counts for all 9 tables: `exercises`, `exercise_isolated_muscles`, `program_backups`, `program_backup_items`, `progression_goals`, `user_selection`, `workout_log`, `volume_plans`, `muscle_volumes`.
- [x] Record current seed DB row counts + `PRAGMA table_info(exercises)` output.
- [x] Copy `data/backup/database.db` → `data/backup/database.db.pre-regen.bak`.
- [x] Verify `.bak` exists and is byte-identical (`sha256sum` match).

### D1 — Build the new seed in a staging file
**Exit artifact:** `debug/D1_build.md` + `data/backup/database.db.new`

- [x] Create `data/backup/database.db.new` as a fresh empty SQLite file.
- [x] Apply the `exercises` DDL from [utils/db_initializer.py:34-68](utils/db_initializer.py#L34-L68) including `movement_pattern` and `movement_subpattern` columns and the `idx_exercise_name_nocase` index.
- [x] Apply the `exercise_isolated_muscles` DDL: composite PK `(exercise_name, muscle)` with `FK → exercises` `ON DELETE CASCADE`.
- [x] `ATTACH DATABASE 'data/database.db' AS live`.
- [x] `INSERT INTO exercises SELECT ... FROM live.exercises` — explicit column list, all 15 columns.
- [x] `INSERT INTO exercise_isolated_muscles SELECT exercise_name, muscle FROM live.exercise_isolated_muscles`.
- [x] `DETACH DATABASE live`.

### D2 — Verify catalog parity
**Exit artifact:** `debug/D2_parity.md`

- [x] Confirm `exercises` row count == **1897** (hard fail otherwise).
- [x] Confirm `exercise_isolated_muscles` row count == **1598** (hard fail otherwise).
- [x] Confirm `movement_pattern` column present via `PRAGMA table_info`.
- [x] Confirm `movement_pattern` populated count == **1443**.
- [x] Per-column `SELECT COUNT(DISTINCT col)` for all 12 filter columns; must match live DB exactly (use §1 numbers as oracle).

### D3 — Verify isolation (no user data)
**Exit artifact:** `debug/D3_isolation.md`

- [x] `SELECT name FROM sqlite_master WHERE type='table'` — allowed set: `{exercises, exercise_isolated_muscles, sqlite_sequence?}`. Hard fail if anything else exists.
- [x] Explicit absence check (each must return `no such table`): `program_backups`, `program_backup_items`, `progression_goals`, `user_selection`, `workout_log`, `volume_plans`, `muscle_volumes`.
- [x] Record full `.schema` output.

### D4 — Simulated corruption recovery test
**Exit artifact:** `debug/D4_recovery_sim.md`

- [x] Create temp dir; copy `database.db.new` into it as `live.db`.
- [x] Corrupt `live.db`: overwrite first 512 bytes with `\x00`.
- [x] Monkeypatch `utils.config.DB_FILE` and `utils.db_initializer.SEED_DB_PATH` + `utils.database.SEED_DB_PATH` to temp paths.
- [x] Call `get_db_connection()` → should trigger `_attempt_database_recovery` and restore from seed.
- [x] Assert restored DB has exactly 2 tables (`exercises`, `exercise_isolated_muscles`) with 1897 + 1598 rows.
- [x] Assert **none** of the 7 user-data tables exist in the restored DB.

### D5 — Atomic replace + fresh-install sanity
**Exit artifact:** `debug/D5_install.md`

- [x] Atomic replace: `mv data/backup/database.db.new data/backup/database.db`.
- [x] Temp-dir fresh-install scenario: empty live DB, run `initialize_database()`, expect 1897 exercises + 1598 isolated-muscle rows + `movement_pattern` column present.
- [x] Confirm no warnings about "Seed database missing" in the log output.

### D6 — Test suite gate
**Exit artifact:** `debug/D6_pytest.txt`

- [x] Run `.venv/Scripts/python.exe -m pytest tests/ -q`.
- [x] Expected baseline: **930 passed, 1 skipped** (per CLAUDE.md §8).
- [x] On any regression: **STOP**, restore `.pre-regen.bak`, investigate before proceeding. Do not patch forward.

### D7 — Commit
**Exit artifact:** `debug/D7_commit.txt` (commit hash)

- [x] `git add data/backup/database.db`
- [x] Commit message:
  ```
  chore(seed): regenerate catalog-only seed DB from live data

  Replaces a drifted 1883-row seed (missing movement_pattern column,
  only 3 exercise_isolated_muscles rows) with a catalog-only rebuild
  from data/database.db: 1897 exercises, 1598 isolated muscle rows,
  movement_pattern column populated. User-data tables are explicitly
  excluded to prevent contamination of the corruption-recovery path
  in utils/database.py:152.
  ```
- [x] Do **NOT** commit `data/backup/database.db.pre-regen.bak` (untracked; retained in working tree for 24h as rollback).

### D8 — Exit condition
- [x] All D0–D7 artifacts present.
- [x] Test suite baseline matched.
- [x] Commit hash recorded.
- [x] Rollback file present and untracked.

---

## 5. Phase E — Regression Gate (runs immediately after D)

**Goal:** prove Phase D has zero behavioral impact on the running app.

### E1 — Full pytest
**Exit artifact:** `debug/E1_pytest.txt`

- [x] `.venv/Scripts/python.exe -m pytest tests/ -q`
- [x] Pass count ≥ 930 (+ 1 skipped).

### E2 — Targeted Playwright specs
**Exit artifact:** `debug/E2_e2e.txt`

- [x] `npx playwright test e2e/workout-plan.spec.ts --project=chromium --reporter=line`
- [x] `npx playwright test e2e/api-integration.spec.ts --project=chromium --reporter=line`
- [x] Both green.

### E3 — Manual Edge smoke (user's actual browser)
**Exit artifact:** `debug/E3_edge_smoke.md`

- [x] Start dev server: `.venv/Scripts/python.exe app.py`.
- [x] Open `/workout_plan` in actual installed Edge incognito (Edge 147.0.3912.60; original report was Edge 146).
- [x] Visually confirm every filter dropdown shows options.
- [x] Visually confirm exercise dropdown has ≥1897 options (scroll or search-filter to verify).
- [x] Toggle Simple ↔ Advanced filter mode; confirm both render.
- [x] Capture Edge console/page errors; confirm zero errors on load.
- [x] If any of the above fails → activate Contingency §6.

### E4 — Exit
- [x] All three gates green.
- [x] Phase D + E confirmed safe to retain on `spring-cleanup`.

---

## 6. Contingency Plan (DORMANT — activate only on E3 failure)

IF the Edge smoke in E3 reveals the original dropdown bug still present, re-open the following track. Do **not** run any item below unless E3 explicitly fails.

### Contingency A — Reproduction & evidence capture
**Exit artifact:** `debug/CA_repro.md`

- [ ] Capture `/workout_plan` in Edge incognito with DevTools open.
- [ ] Record which specific dropdowns are empty (names + expected vs actual `.wpdd-option` counts).
- [ ] Capture console + pageerror output.
- [ ] Capture Network tab — list every XHR with status and response size.

### Contingency B — Targeted inspection
(Only if CA reproduces.)
**Exit artifact:** `debug/CB_candidates.md`

- [ ] Read [templates/workout_plan.html](templates/workout_plan.html) in full — audit `{% for %}` loops over `filters` and `exercises`.
- [ ] Read [static/js/modules/workout-dropdowns.js](static/js/modules/workout-dropdowns.js) `buildOptions()` around line 392 and native-select-hide wrapping around line 72.
- [ ] Read [static/js/modules/filter-view-mode.js](static/js/modules/filter-view-mode.js) `getMuscleFilterOptions()` around line 413, plus audit the double-load between [templates/workout_plan.html:516](templates/workout_plan.html#L516) and `templates/base.html:290`.
- [ ] Cross-check [routes/filters.py](routes/filters.py) `ALLOWED_COLUMNS` against the 12 columns requested in [routes/workout_plan.py:104-117](routes/workout_plan.py#L104-L117).
- [ ] Name exactly **one** file + line range as the failure site at ≥95% confidence. If not reachable, stop and re-plan.

### Contingency C — Minimal fix (mode-aware, wpdd-aware)
(Only if CB identifies a site.)
**Exit artifact:** `debug/CC_fix.md` + commit hash

- [ ] Create branch `fix/workout-plan-dropdowns` from `spring-cleanup`.
- [ ] Write **failing** Playwright spec `e2e/workout-plan-dropdown-regression.spec.ts` asserting:
  1. Exercise dropdown `.wpdd-option` count ≥ 1897 (accept 1898 if placeholder present).
  2. Non-muscle filters (`force`, `equipment`, `mechanic`, `difficulty`, `utility`, `grips`, `stabilizers`, `synergists`): `.wpdd-option` count ≥ 1 and matches native `<select>` option count.
  3. Muscle filters (`primary`, `secondary`, `tertiary`, `advanced_isolated`): in simple mode, `.wpdd-option` count == `Object.keys(SIMPLE_MUSCLES).length`; in advanced mode, `.wpdd-option` count == `Object.keys(ADVANCED_MUSCLES).length`. **Parametrize by mode**, not by raw DB distinct.
  4. Zero `pageerror` and zero console error-level messages across load.
- [ ] Confirm the spec is **red** on the current code.
- [ ] Apply the targeted fix (≤2 files, ≤30 lines, no drive-by edits).
- [ ] Spec green; plus regression specs: `e2e/workout-plan.spec.ts`, `e2e/api-integration.spec.ts`, `e2e/exercise-interactions.spec.ts`, `e2e/superset-edge-cases.spec.ts`.
- [ ] Commit; message names root cause file and oracle (`.wpdd-option`, mode-aware).

---

## 7. Phase F — Deferred Architectural Cleanup

Executed 2026-04-15 with scope F1 + F2 + F4. F3 became moot once the seed contract was retired (empty DB is now the valid initial state, not an error).

- [x] **F1** — Retired `SEED_DB_PATH` contract entirely. Deleted `data/backup/database.db`, removed `_seed_exercises_from_backup_if_needed()` from `utils/db_initializer.py`, and simplified `_attempt_database_recovery()` in `utils/database.py` to quarantine-only (next init creates a fresh empty DB). User keeps their own `data/database.db` backups offline (`C:\Users\aviha\OneDrive\מסמכים\backup database`).
- [x] **F2** — Removed duplicate `SEED_DB_PATH` constant from `utils/database.py`; subsumed by F1.
- [ ] **F3** — Superseded by F1. Empty DB is no longer an error condition.
- [x] **F4** — Removed duplicate `filter-view-mode.js` script tag from `templates/workout_plan.html`; the load now lives only in `templates/base.html`.

---

## 8. Confidence Statement

| Component | Confidence | Justification |
|---|---|---|
| Phase D will not break any existing test | **≥98%** | Seed is only read when `exercises < 100` AND `TESTING != 1`. Tests set `TESTING=1` ([conftest.py](tests/conftest.py)); live app has 1897 rows >> 100. Seed path is dead code for both. |
| Phase D removes user-data contamination from recovery | **100%** | Catalog-only by construction; D3 asserts absence of 7 user-data tables explicitly. |
| Phase D resolves the drift (14 exercises / 1595 isolated / missing column) | **100%** | D2 hard-fails on any row-count mismatch against live. |
| Phase D is reversible | **100%** | D0 saves `.pre-regen.bak` before any destructive action. Rollback is `mv` + single-file restore. |
| Dropdown bug is closed (unconditional) | **~92%** | Codex Chromium verification + user's inability to reproduce + SQL verification of live DB integrity. Remaining 8% is Edge-specific. |
| Dropdown bug is closed (after E3 Edge smoke) | **≥99%** | Adds user's actual browser to the evidence set. |
| Overall execution path causes zero data loss | **100%** | All destructive actions gated and reversible. |
| **Overall plan confidence** | **≥95%** | All components at or above the bar. |

---

## 9. Rules for Updating This File During Execution

- After each completed action, mark its checkbox immediately.
- Add one short note under §10 with action ID, what changed, what was validated, any surprises.
- If a step is deferred, record why + what prerequisite is missing.
- Do not keep progress in chat only — this file is the source of truth.

---

## 10. Execution Notes

### 2026-04-11

- Plan created after Codex peer-review of the prior `docs/db_fix_implementation.md` (now removed as wrong scope: it targeted an architectural rewrite that did not address the user-reported symptoms).
- **A0 reproduction gate resolved as "cannot reproduce on current branch"** — the user confirmed the dropdown report was from Edge 146 **before** Codex's intermediate fix, and is not reproducible on `spring-cleanup` now.
- Phases A/B/C dropped from active plan; replaced by dormant Contingency track (§6), activated only if E3 Edge smoke fails.
- **Phase D rewritten from scratch** per Codex's data-safety finding: a full `.dump` of the live DB would bake `program_backups` (4 rows), `program_backup_items` (8 rows), and `progression_goals` (1 row) into the seed. Because recovery copies the seed **wholesale**, that would contaminate the recovery path. Catalog-only is the only safe shape.
- **Phase D is the only active work item this session.** Phase E runs immediately after. Phase F is deferred.
- **D0 completed:** wrote `debug/D0_preflight.md`, recorded live/seed table counts and seed `PRAGMA table_info(exercises)`, copied `data/backup/database.db` to `data/backup/database.db.pre-regen.bak`, and verified both files are byte-identical by SHA256 (`DF52EF7AE0C319717CB59168F74623E30CB5D073B0C45E6366583067A5D7EA08`). Surprise noted: the seed DB contains stale `user_selection` rows (31) and a `progression_goals` table (0 rows), reinforcing the catalog-only D1/D3 isolation checks.
- **D1 completed:** wrote `debug/D1_build.md` and created `data/backup/database.db.new` as a fresh catalog-only SQLite file with `exercises` + `exercise_isolated_muscles`, the no-case exercise-name index, and the isolated-muscle index. Copied 1897 exercises via explicit 15-column list and 1598 isolated-muscle mappings from `data/database.db`; `PRAGMA integrity_check` returned `ok`; staging DB SHA256 is `4F9654AFEEF807E813B01ACB0EAF2F2B7883400255FD1FDF527878ECB3EFDAC2`. Initial build attempt hit `database live is locked` on `DETACH` inside the transaction; reran cleanly after committing before detach.
- **D2 completed:** wrote `debug/D2_parity.md`; staging `data/backup/database.db.new` matches live DB on 1897 exercises, 1598 isolated-muscle mappings, `movement_pattern`/`movement_subpattern` presence, 1443 populated `movement_pattern` rows, `PRAGMA integrity_check=ok`, and populated/distinct counts for all 12 filter columns.
- **D3 completed:** wrote `debug/D3_isolation.md`; staging `data/backup/database.db.new` contains only `exercises` and `exercise_isolated_muscles`, `PRAGMA integrity_check=ok`, and explicit probes for `program_backups`, `program_backup_items`, `progression_goals`, `user_selection`, `workout_log`, `volume_plans`, and `muscle_volumes` all returned `no such table`. Full schema recorded in the artifact.
- **D4 completed:** wrote `debug/D4_recovery_sim.md`; temp `live.db` was corrupted by overwriting its first 512 bytes, `utils.config.DB_FILE`, `utils.database.SEED_DB_PATH`, and `utils.db_initializer.SEED_DB_PATH` were monkeypatched to temp paths, and `get_db_connection()` triggered `_attempt_database_recovery`. The corrupted DB was quarantined, restored `live.db` is byte-identical to the temp catalog-only seed, restored counts are 1897 exercises + 1598 isolated-muscle rows, `PRAGMA integrity_check=ok`, and all 7 user-data table probes returned `no such table`.
- **D5 completed:** wrote `debug/D5_install.md`; atomically replaced `data/backup/database.db.new` into `data/backup/database.db` using `.NET File.Replace` after an initial null-backup argument attempt failed without changing files. The active seed now has SHA256 `4F9654AFEEF807E813B01ACB0EAF2F2B7883400255FD1FDF527878ECB3EFDAC2`, `.new` is gone, and rollback `data/backup/database.db.pre-regen.bak` remains intact at SHA256 `DF52EF7AE0C319717CB59168F74623E30CB5D073B0C45E6366583067A5D7EA08`. Fresh temp install via `initialize_database(force=True)` produced 1897 exercises, 1598 isolated-muscle rows, `movement_pattern` column present with 1443 populated rows, `PRAGMA integrity_check=ok`, and no `Seed database missing` warning.
- **D6 completed:** wrote `debug/D6_pytest.txt`; `.venv/Scripts/python.exe -m pytest tests/ -q` passed with **934 passed, 1 skipped** in 110.80s, exceeding the 930 passed + 1 skipped baseline. No rollback needed.
- **D7 completed:** committed only `data/backup/database.db` with commit `0e0ca3b51cc35539d7676b890e939da57cadb223` (`chore(seed): regenerate catalog-only seed DB from live data`) and wrote `debug/D7_commit.txt`. The rollback file `data/backup/database.db.pre-regen.bak` remains untracked/ignored and was not committed.
- **D8 completed:** verified all D0-D7 artifacts exist, `debug/D6_pytest.txt` records **934 passed, 1 skipped**, `debug/D7_commit.txt` records commit `0e0ca3b51cc35539d7676b890e939da57cadb223` matching `HEAD`, and `data/backup/database.db.pre-regen.bak` exists while `git ls-files --error-unmatch` confirms it is not tracked.
- **E1 completed:** wrote `debug/E1_pytest.txt`; `.venv/Scripts/python.exe -m pytest tests/ -q` passed with **934 passed, 1 skipped** in 106.31s, satisfying the Phase E1 gate of at least 930 passed plus 1 skipped.
- **E2 completed:** wrote `debug/E2_e2e.txt`; `npx playwright test e2e/workout-plan.spec.ts --project=chromium --reporter=line` passed with **17 passed** in 21.4s and `npx playwright test e2e/api-integration.spec.ts --project=chromium --reporter=line` passed with **58 passed** in 3.8s. Both commands exited 0, satisfying the targeted Playwright gate.
- **E3 completed:** wrote `debug/E3_edge_smoke.md`; started `.venv/Scripts/python.exe app.py`, opened `/workout_plan` in a fresh private Edge context using the actual installed Edge **147.0.3912.60** (original report was Edge 146), and stopped the server afterward. All 12 filter dropdowns opened with options, the exercise dropdown opened with **1898** options, Simple -> Advanced -> Simple mode toggling rendered correctly via pointer-clicks at a 1920x1080 desktop viewport, and captured Edge console/page errors were both zero. Initial probe notes: WPDD popovers live under `document.body`, not inside `.wpdd`, and the navbar toggle sits outside a 1440px viewport; neither reproduced the original dropdown bug.
- **E4 completed:** E1, E2, and E3 are all green, so Phase D + E are confirmed safe to retain on `spring-cleanup`; Contingency §6 remains dormant.
