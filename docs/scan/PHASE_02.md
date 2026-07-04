# Phase 2 — Data layer & schema

Read in full: `utils/database.py` (762), `utils/db_initializer.py` (655),
`utils/exercise_manager.py` (201), `utils/filter_predicates.py` (193),
`utils/exercise_media.py` (212), `utils/media_path.py` (137), `utils/maintenance.py` (129).
Context read: `.claude/rules/database.md`, `utils/CLAUDE.md`, `docs/REFACTOR_PLAN.md`
(council-reviewed v2), plus targeted peeks outside the phase list where a finding required
confirming a caller/duplicate (`routes/workout_plan.py:1-45`, `routes/filters.py:100-490`,
`app.py` initializer-call grep) — those peeks are cited inline and are not claimed as
full reads.

Convention: `FILE:LINE — observation` · tag `[CONFIRMS-PLAN]`, `[CONTRADICTS-PLAN]`,
`[NEW]`, or `[RISK]`.

---

## utils/database.py (762 lines)

**What it does:** SQLite connection factory (`get_db_connection`), PRAGMA configuration
(`_configure_connection`), corruption-recovery quarantine logic, the `DatabaseHandler`
context-manager (the mandated DB-access API for the whole app), and a long tail of
`add_*_table()` DDL bootstrap functions plus profile/calibration upsert helpers.

Key symbols:
- `_configure_connection` (`database.py:78-102`) — sets `foreign_keys=ON`,
  `busy_timeout=30000`, journal mode (WAL vs DELETE) and synchronous mode keyed off
  `FLASK_DEBUG`/`FLASK_ENV`.
- `_should_attempt_recovery` / `_attempt_database_recovery` (`database.py:105-150`) —
  corruption string-sniffing (`"malformed"`, `"not a database"`, `"encrypted"`) that
  quarantines the file as `*.corrupted_<timestamp>` and lets a fresh DB be created.
- `DatabaseHandler` class (`database.py:185-425`) — `execute_query`, `executemany`,
  `fetch_one`, `fetch_all`, `close`, `__enter__`/`__exit__`.
- `add_progression_goals_table`, `add_volume_tracking_tables`,
  `add_volume_plan_activation_columns`, `add_user_profile_tables`,
  `upsert_user_profile_demographics/_lift/_preference`, `add_strength_calibration_tables`,
  `add_fatigue_context_settings_table`, `add_body_composition_snapshots_table`
  (`database.py:461-763`).

Findings:
- **`database.py:461-763` — six `add_*_table()` bootstrap functions live here, not
  three.** `[CONTRADICTS-PLAN]` WP2.4's problem statement says "three `add_*_table()` in
  `utils/database.py`" and lists `add_fatigue_context_settings_table` separately as if it
  were the 4th outlier. Actual count in this file alone: `add_progression_goals_table`,
  `add_volume_tracking_tables` (which itself calls `add_volume_plan_activation_columns`
  as a second, nested DDL step), `add_user_profile_tables`, `add_strength_calibration_tables`,
  `add_fatigue_context_settings_table`, `add_body_composition_snapshots_table` = 6 top-level
  + 1 nested. Phase 1's finding (`SCAN_FINDINGS.md` Phase 1) already caught this at the
  `app.py` call-site level (8 initializer calls, not 6); this confirms the same drift
  from the file-content side and means WP2.4's "single registry" scope is larger than
  scoped — it should enumerate all 6 (7 incl. the nested column-migration) by name, not
  "three."
- **`database.py:443-464` — `add_progression_goals_table` is defined twice: once as a
  `DatabaseHandler` instance method (`database.py:443`) and once as a module-level
  function of the identical name (`database.py:461`) that just wraps `with
  DatabaseHandler() as db: db.add_progression_goals_table()`.** `[NEW]` No other
  `add_*_table` follows this instance-method + module-wrapper pattern — all the others
  (`add_volume_tracking_tables`, `add_user_profile_tables`, `add_strength_calibration_tables`,
  `add_fatigue_context_settings_table`, `add_body_composition_snapshots_table`) are plain
  module-level functions that open their own `DatabaseHandler`. This one indirection is
  vestigial and inconsistent with the rest of the file; a schema-registry pass (WP2.4)
  should drop the instance method and call the module function directly, or fold it into
  the same shape as its siblings.
- **`database.py:216,292` — write-detection is a hardcoded verb allowlist
  (`INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/REPLACE` for `execute_query`;
  `INSERT/UPDATE/DELETE/REPLACE` for `executemany`) parsed from
  `query.strip().split()[0].upper()`.** `[RISK]` A query opening with a comment, a CTE
  (`WITH ... INSERT`), or leading whitespace/newline before the verb would misclassify as
  a read and skip the `_DB_LOCK` acquisition — currently no caller in this codebase does
  that (verified by grep across `utils/`/`routes/` call sites read so far), but it's a
  latent trap for any future query author, especially the CTE pattern already used
  elsewhere in this phase's files (see `maintenance.py` `REBUILD_EIM_SQL` recursive CTE,
  which happens to start with `WITH` then `INSERT`, i.e. `.split()[0]` would yield `"WITH"`
  → **not** classified as a write → runs unlocked). Confirmed real: `maintenance.py:36-56`.
- **`_DB_LOCK` is a single process-global `threading.RLock` serializing every write
  across every `DatabaseHandler` instance regardless of which table is touched**
  (`database.py:23`, acquired at `database.py:220-222` and `:296-297`). `[RISK]` Matches
  the single-user local-first non-goal (CLAUDE.md §1) so this is a deliberate, reasonable
  trade — noting it because any refactor that parallelizes background jobs (e.g. batch
  media-path backfills) would silently serialize through this lock.
- **`DatabaseHandler.__exit__` commits/rolls back unconditionally on top of per-call
  auto-commit** (`database.py:417-425`) — every `execute_query`/`executemany` call
  defaults to `commit=True` already, so `__exit__`'s commit is a no-op in the common case
  and only matters for the explicit `commit=False` batching pattern used in
  `db_initializer._trim_exercise_name_whitespace` and `maintenance._exec_many`. Not a bug,
  just worth flagging as coupling: the `commit=False` contract is implicit (relies on the
  caller remembering to call `db.connection.commit()`/`rollback()` itself, since `__exit__`
  only fires at `with` block exit) — both current call sites do this correctly, but
  there's no assertion/guard against a caller leaving a `commit=False` transaction open
  without a manual commit outside a `with DatabaseHandler()` block.
- **Corruption recovery matches on English substrings of `sqlite3.DatabaseError.args`**
  (`database.py:110-114`: `"malformed"`, `"not a database"`, `"encrypted"`) — fragile if
  the underlying SQLite build's error text changes, but this is vendored CPython
  `sqlite3`/`libsqlite3` wording, low churn risk. `[NEW]` (minor, not escalating).
- Matches `.claude/rules/database.md`'s documented `DatabaseHandler` pattern exactly —
  `[CONFIRMS-PLAN]` no drift between the rule doc and the actual API surface for
  `execute_query`/`fetch_one`/`fetch_all`.
- No dead code found in this file — every `add_*`/`upsert_*` function is called from
  `app.py` (verified via grep: all 6 `add_*_table` names appear in `app.py`'s import list
  and are invoked twice — once at module-load startup, once inside the `/erase-data`
  re-init block, matching Phase 1's finding of a duplicated 8-call init block).

---

## utils/db_initializer.py (655 lines)

**What it does:** `initialize_database()` — the schema-creation-and-repair entry point
called once per process (guarded by `_INITIALIZATION_LOCK` + `_INITIALIZATION_COMPLETE`),
covering `exercises`, `exercise_isolated_muscles`, `user_selection`, `workout_log`, plus a
sequence of one-time data-hygiene passes (FK backfill, equipment/muscle normalization,
exercise-name whitespace trim, known-metadata repair, movement-pattern population).

Key symbols:
- `_initialize_exercises_table` / `_initialize_isolated_muscles_table` /
  `_initialize_user_selection_table` / `_initialize_workout_log_table`
  (`db_initializer.py:69-276`) — each does a **schema-shape self-check** (queries
  `PRAGMA table_info`/`PRAGMA foreign_key_list`, and for `exercises` also
  `sqlite_master` for the PK column) and `DROP TABLE IF EXISTS` + recreate if the live
  table doesn't match the expected shape (missing FK, wrong PK, wrong CASCADE, or under
  `TESTING=1` unconditionally for `user_selection`/`workout_log`).
- `_backfill_workout_log_plan_ids` (`db_initializer.py:279-345`) — matches legacy
  `workout_log` rows lacking `workout_plan_id` to a `user_selection` row via a
  COALESCE-guarded all-fields match, only when exactly one candidate exists.
- `_normalize_equipment_values` / `_normalize_muscle_group_values`
  (`db_initializer.py:347-435`) — re-run `normalize_equipment`/`normalize_muscle` from
  `utils/normalization.py` against live catalogue data on every boot.
- `_trim_exercise_name_whitespace` (`db_initializer.py:437-527`) — the most delicate
  function in the file: trims `exercises.exercise_name` PK whitespace, cascading the same
  rename across `exercise_isolated_muscles`, `user_selection`, and the **un-FKed**
  `workout_log.exercise` text column, using `PRAGMA defer_foreign_keys=ON` +
  `commit=False` batching so the four-table rename is atomic. Explicitly checks for a
  case-insensitive name collision before renaming and skips with a warning if found.
- `_repair_known_exercise_metadata` (`db_initializer.py:530-555`) — applies
  `KNOWN_EXERCISE_METADATA_FIXES` (hardcoded dict, `db_initializer.py:17-66`) only when
  the target column is NULL/blank, never overwrites populated data.
- `initialize_database` (`db_initializer.py:557-594`) — orchestrator; note the guard is
  **bypassed entirely under `TESTING=1`** (`db_initializer.py:569,575`: the skip
  condition is `_INITIALIZATION_COMPLETE and not force and os.getenv("TESTING") != "1"`),
  meaning every test-suite call to `initialize_database()` re-runs the **entire**
  drop/recreate + normalization + backfill pipeline, and `_initialize_user_selection_table`
  / `_initialize_workout_log_table` additionally **unconditionally drop** those two tables
  under `TESTING=1` regardless of shape (`db_initializer.py:160-161`, `:231-232`) —
  by design, for test isolation, but worth flagging because it means these two tables are
  never shape-checked under test the way `exercises`/`exercise_isolated_muscles` are.
- `_populate_movement_patterns` (`db_initializer.py:597-655`) — lazy-imports
  `utils.movement_patterns.classify_exercise` inside the function (not module top) to
  avoid a hard dependency/import-order issue; swallows `ImportError` with a warning.

Findings:
- **Column-name f-string interpolation in `_normalize_muscle_group_values` and
  `_repair_known_exercise_metadata`** (`db_initializer.py:393-394,415`,
  `:537-542`) builds `f"... {column} ..."` / `f"SET {column} = ?"` SQL — **but** in both
  cases `column`/`fields.items()` iterate over a hardcoded tuple
  (`muscle_columns = ("primary_muscle_group", ...)`) or a hardcoded dict
  (`KNOWN_EXERCISE_METADATA_FIXES`), never external input. `[NEW]` Not an injection
  vector today, but it's the same *pattern* (raw f-string column interpolation with no
  runtime whitelist check) that IS unguarded and reachable with real column names
  elsewhere (see `exercise_manager.py:172-178` below) — worth naming as a repo-wide
  pattern in a lint/convention note even though this specific instance is safe.
- **Self-healing schema-shape checks are hand-rolled per table** (four near-identical
  `PRAGMA table_info`/`PRAGMA foreign_key_list` + drop-if-mismatched blocks,
  `db_initializer.py:69-276`) with no shared helper — each of the four
  `_initialize_*_table` functions reimplements "read columns, read FK list, compare,
  maybe DROP." `[NEW]` A shared `_table_matches_shape(db, table, expected_columns,
  expected_fk)` helper would collapse ~120 lines of near-duplicate PRAGMA-introspection
  code. Candidate for WP2.4 or a small follow-up — moving this logic doesn't touch
  calculation semantics, only DDL bootstrapping, so it's low-risk under global rule 2.
- **This file plus the six `database.py` `add_*_table` functions plus
  `initialize_exercise_order`/`column_exists`/`table_exists` in
  `routes/workout_plan.py` (not read this phase, confirmed via `.claude/rules/database.md`
  line references and the WP2.4 text) plus backup-table init in
  `utils/program_backup.py` — schema setup genuinely is scattered across (at least) 4
  files and >10 functions.** `[CONFIRMS-PLAN]` Directly substantiates WP2.4's premise;
  see the `add_*` undercount correction above for the one place the plan's inventory is
  off.
- No dead code: every `_initialize_*`/`_normalize_*`/`_backfill_*`/`_repair_*`/
  `_populate_*` helper is called from `initialize_database` in one straight-line
  sequence (`db_initializer.py:582-591`). Nothing orphaned.

---

## utils/exercise_manager.py (201 lines)

**What it does:** `ExerciseManager` — CRUD-ish facade over `user_selection` (plan rows)
and `exercises` (catalogue), plus module-level "shortcut" functions re-exporting each
static method for callers that don't want the class ceremony.

Key symbols:
- `add_exercise` (`exercise_manager.py:20-104`) — validates required fields, rep-range
  ordering, non-negative RIR, weight bounds (`0 <= weight <= 1000`), duplicate
  routine+exercise rejection, then inserts with or without `exercise_order` depending on
  whether the column exists yet (legacy-schema fallback via `PRAGMA table_info` check
  inline, `exercise_manager.py:74-75` — a **third** ad hoc column-existence check pattern
  in this phase, alongside `db_initializer.py`'s four and `database.py`'s one in
  `add_volume_plan_activation_columns`).
- `delete_exercise`, `remove_exercise_by_name` (`exercise_manager.py:106-111,164-170`).
- `save_exercise` (`exercise_manager.py:114-162`) — normalizes via
  `normalize_exercise_row`, does a case-insensitive collision check
  (`WHERE exercise_name = ? COLLATE NOCASE`) before an `INSERT ... ON CONFLICT DO UPDATE`
  built from a **hardcoded** `columns` list (`exercise_manager.py:122-136`) — safe, no
  interpolated user input, but note this hardcoded column list must be kept in sync by
  hand with the `exercises` table DDL in `db_initializer.py:81-99` (e.g. it omits `force`,
  wait — `force` IS in the list; it omits `movement_pattern`, `movement_subpattern`,
  `youtube_video_id`, `media_path` — those columns are simply never touched by
  `save_exercise`, which appears intentional since they're populated by separate
  pipelines, but there is no enforcement/test tying the two lists together).
- **`fetch_unique_values(table, column)` (`exercise_manager.py:172-178`) — the
  unguarded f-string this scan's brief specifically asked about:**
  ```python
  query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column} ASC"
  ```
  No whitelist, no `validate_column_name`/`validate_table_name` call, both `table` and
  `column` interpolated directly. `[CONFIRMS-PLAN][RISK]` This is exactly the function
  the council response-matrix finding #4 names ("ExerciseManager's unguarded f-string").
  **Verified caller surface (grep, this session):** only `tests/test_exercise_manager.py`
  calls it, always with hardcoded literal args (`"exercises"`, `"equipment"`,
  `"tertiary_muscle_group"`, `"primary_muscle_group"`) — **no route or other utils module
  calls `ExerciseManager.fetch_unique_values` with any value that could originate from a
  request.** The plan's disposition (leave it untouched, don't merge with the guarded
  routes-level version) is correct as stated, but the plan should explicitly note this
  function has **zero external-input reachability today** — it's latent risk (a future
  caller could pass a request-derived column name straight through with no compiler/type
  signal to stop them) rather than an active vulnerability. Worth a one-line docstring
  warning on the function itself as a cheap mitigation independent of any larger refactor.
- Module-level shortcuts (`exercise_manager.py:196-201`) mirror every static method 1:1;
  `utils/__init__.py:17,58` re-exports `fetch_unique_values` again through the facade
  — a second layer of indirection on top of the shortcut, both pointing at the same
  unguarded function. `[CONFIRMS-PLAN]` (WP0.3 emptying `utils/__init__.py` removes one
  of these two redundant re-export hops, not the underlying risk.)

---

## utils/filter_predicates.py (193 lines)

**What it does:** `FilterPredicates` — "consolidated" (per its own docstring) exercise
filter-query builder: `VALID_FILTER_FIELDS` allowlist, `PARTIAL_MATCH_FIELDS` (LIKE vs
exact), `build_filter_query`, `filter_exercises`/`get_exercises`, `sanitize_filters`.

Findings:
- **Column names are only ever interpolated into SQL after an allowlist membership
  check** (`filter_predicates.py:74`: `if field not in cls.VALID_FILTER_FIELDS: continue`)
  — this module's own SQL-building (`build_filter_query`, `filter_predicates.py:63-104`)
  is safe; the guard-then-interpolate pattern here is the right shape and the one the
  plan's WP1.1 wants replicated for the relocated `fetch_filter_values`.
- **This module's docstring claims to be the "single source of truth" for exercise
  filtering** (`filter_predicates.py:2-3,15-16`), but it is not: `routes/filters.py`
  maintains **its own, separate** filter allowlist (`ALLOWED_COLUMNS`,
  `filters.py:115-141`) and **its own, separate** inline SQL query builder
  (`filter_exercises_with_expanded_muscles`, `routes/filters.py:269-344`, confirmed by a
  targeted peek outside this phase's file list) used whenever a multi-value muscle filter
  is present. `[NEW][RISK]` — beyond what WP1.1 scopes. Concretely there are now **three**
  independent "build a WHERE clause for exercise filtering" implementations in the
  codebase: (1) `FilterPredicates.build_filter_query` (`VALID_FILTER_FIELDS`, this file),
  (2) `routes/filters.py`'s single-value path which calls back into
  `FilterPredicates.get_exercises` after its own `ALLOWED_COLUMNS`-based sanitization, and
  (3) `routes/filters.py:filter_exercises_with_expanded_muscles`, a fully separate
  raw-SQL builder for the OR-logic multi-value muscle case that does **not** go through
  `FilterPredicates` at all and lives in the routes layer, directly violating the
  "routes call utils, routes hold no raw SQL" boundary from root `CLAUDE.md` §2. Two
  different allowlists (`VALID_FILTER_FIELDS` vs `ALLOWED_COLUMNS`) must be kept in sync
  by hand for filtering to behave consistently across the two entry points. WP1.1 as
  written only relocates `ALLOWED_COLUMNS`/`validate_column_name` and the
  distinct-values `fetch_unique_values`; it does not touch this deeper
  filter-query-builder duplication or the routes-layer raw-SQL boundary violation. Worth
  a follow-up WP (or an expansion of WP1.1's scope) once the council/owner sees this.
- **A fourth "fetch unique values" implementation exists**, beyond the two the plan
  already tracks (`routes/workout_plan.py:fetch_unique_values` and
  `ExerciseManager.fetch_unique_values`): the route handler
  `routes/filters.py:get_unique_values` (`filters.py:356-`, confirmed by targeted peek)
  guards with its own `ALLOWED_TABLES`/`ALLOWED_COLUMNS` pair and builds the query
  inline in the route rather than delegating to either utils implementation. `[NEW]`
  Same family of risk as the filter-builder duplication above — not flagged in WP1.1's
  "no merge" disposition because the plan's authors evidently weren't aware of this third
  code path when writing the disposition (finding #4 in the response matrix only discusses
  two).
- `sanitize_filters`/`validate_filter_field` (`filter_predicates.py:146-174`) are real,
  live helpers — `validate_filter_field` is explicitly named in WP0.2's "do NOT delete
  (real refs)" list, confirmed still present and exported at module level
  (`filter_predicates.py:178-193` convenience wrappers). `[CONFIRMS-PLAN]`
- No dead code in this file — every method/function is reachable from
  `routes/filters.py` or `utils/exercise_manager.py`.

---

## utils/exercise_media.py (212 lines)

**What it does:** Resolves a safe `media_path` (thumbnail/preview image) for a given
exercise name, in priority order: (1) an existing valid DB `media_path` value, (2) a
hand-curated `MANUAL_EXERCISE_MEDIA_OVERRIDES` dict, (3) the bundled
`free_exercise_db_mapping.csv` (rows marked `confirmed`/`manual`/`auto`), (4) the vendored
`free-exercise-db` catalogue JSON via exact key match, (5) fuzzy token-overlap scoring
against the same catalogue (`_resolve_fuzzy_media_path`, threshold `MIN_FUZZY_SCORE=0.72`).

Key symbols: `_normalize_exercise_name`/`_tokens_for_match`/`_match_key`
(`exercise_media.py:78-98`) — casefold + phrase/singular-token normalization pipeline;
`_load_catalog_media_entries`/`_load_fallback_media_map` (both `@lru_cache`,
`exercise_media.py:101-160`) — one-time-per-process catalogue/CSV loads;
`_score_candidate` (`exercise_media.py:163-177`) — weighted coverage/Jaccard/SequenceMatcher
blend; `resolve_exercise_media_path` (`exercise_media.py:197-212`) — public entry point.

Findings:
- **No DB access in this file at all** — it's pure filesystem/CSV/JSON + string matching,
  correctly living in `utils/` per the module-boundary rule even though it has zero
  `DatabaseHandler` usage. `[NEW]` (positive note, not a smell.)
- Delegates all path-safety validation to `utils/media_path.py`
  (`is_valid_media_path_shape`, `media_path_resolves`) rather than reimplementing it —
  good separation, no duplicated validation logic. `[CONFIRMS-PLAN]`-adjacent (matches
  the "single source of truth per concern" spirit the plan wants elsewhere).
  `MANUAL_EXERCISE_MEDIA_OVERRIDES` and `DEFAULT_MAPPING_CSV`/catalogue-JSON entries are
  all independently checked against `media_path_resolves` before being trusted
  (`exercise_media.py:130,154`), so a stale override/CSV row degrades to "no image"
  rather than a broken path.
- `lru_cache(maxsize=2048)` on `_resolve_fuzzy_media_path` (`exercise_media.py:180`) is
  keyed on the raw exercise name string — fine for this app's small, static catalogue
  size, but note it's a **process-lifetime** cache with no invalidation hook; if
  `exercises.json`/the mapping CSV is edited on disk while the app is running (e.g. via
  one of the `apply_*` maintenance scripts noted in the refactor plan), the cache will
  keep serving stale answers until process restart. `[RISK]` (minor — matches this app's
  "restart to pick up catalogue changes" operational model, not a bug.)
- No dead code — `resolve_exercise_media_path` is the only public entry point and is
  called from `routes/workout_plan.py:10,resolve_exercise_media_path` usage (grep-verified
  presence in that file's import list) — full reachability review deferred to Phase 8.

---

## utils/media_path.py (137 lines)

**What it does:** Pure, filesystem-free path-shape validator for `exercises.media_path`
(`is_valid_media_path_shape`), a companion diagnostic (`explain_media_path_shape_failure`),
and a filesystem-touching existence check re-rooted under a vendor base dir
(`media_path_resolves`).

Findings:
- **Defense-in-depth path-traversal guard done right:** `is_valid_media_path_shape`
  rejects `..`/`.` segments, backslashes, `:`  (Windows drive prefixes), leading
  slash/backslash, and empty segments (`media_path.py:44-62`) — and
  `media_path_resolves` *additionally* re-derives the resolved candidate path and asserts
  `candidate.relative_to(base_resolved)` before touching the filesystem
  (`media_path.py:117-127`), so even a shape-validator bug can't escape the vendor
  directory. `[NEW]` (clean, well-factored security-relevant code — no smell.)
- File docstring explicitly states the JS mirror (`resolveExerciseMediaSrc()`) must match
  these rules "exactly" (`media_path.py:7-8`) — a cross-language duplication-by-necessity
  (client can't call into Python) rather than an accidental one; worth flagging only so
  a future refactor doesn't "fix" the JS copy into calling this module (it can't) or drop
  the comment noting the coupling. `[NEW]` (informational only.)
- No SQL, no `DatabaseHandler` — correctly scoped as a pure validation module.
  `__all__` (`media_path.py:130-137`) is a deliberate public-surface declaration; every
  name in it is used by `exercise_media.py` and (per docstring) the JS mirror. No dead
  code.

---

## utils/maintenance.py (129 lines)

**What it does:** A standalone CLI maintenance script
(`python -m utils.maintenance normalize_and_rebuild_eim`) that normalizes legacy
semicolon-delimited `advanced_isolated_muscles` CSV values on the `exercises` table, then
fully rebuilds `exercise_isolated_muscles` from that column via a recursive CTE split.

Key symbols: `NORMALIZE_SQL` (3 `REPLACE()` passes collapsing `; ` / `;` variants to `,`,
`maintenance.py:18-31`), `REBUILD_EIM_SQL` (`maintenance.py:33-61`, a `WITH RECURSIVE`
comma-splitter feeding an `INSERT`), `_exec_many` (retry-with-backoff wrapper for
`"database is locked"` up to 5 attempts, `maintenance.py:65-82`),
`_normalize_existing_rows` (Python-side normalization via
`normalize_advanced_muscles`, `maintenance.py:85-102`), `normalize_and_rebuild_eim`
(orchestrator, `maintenance.py:105-119`).

Findings:
- **`normalize_and_rebuild_eim` creates `exercise_isolated_muscles` with a schema that
  has drifted from the canonical one in `db_initializer.py`.** `[RISK]` This file's DDL
  (`maintenance.py:111-118`):
  ```sql
  CREATE TABLE IF NOT EXISTS exercise_isolated_muscles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_name TEXT NOT NULL,
    muscle TEXT NOT NULL
  );
  ```
  vs. the canonical DDL in `db_initializer.py:141-150`:
  ```sql
  CREATE TABLE IF NOT EXISTS exercise_isolated_muscles (
    exercise_name TEXT NOT NULL,
    muscle TEXT NOT NULL,
    PRIMARY KEY (exercise_name, muscle),
    FOREIGN KEY (exercise_name) REFERENCES exercises(exercise_name) ON DELETE CASCADE
  )
  ```
  Different PK shape (surrogate `id` vs. composite `(exercise_name, muscle)`), and **no
  FK / CASCADE to `exercises` at all**. Because both use `CREATE TABLE IF NOT EXISTS`,
  this is silent and inert as long as `db_initializer.initialize_database()` always runs
  first in every real code path (it does — `app.py` startup, confirmed Phase 1) — the
  table already exists with the canonical shape by the time anyone could invoke this CLI
  script. But if this script were ever run against a genuinely fresh/empty DB file
  (bypassing `app.py`, e.g. a disaster-recovery scenario, a docs-recommended one-liner, or
  a future CI/tooling script), it would silently create the child table **without the
  CASCADE delete** that `exercise_isolated_muscles` depends on everywhere else, and orphan
  rows would survive `DELETE FROM exercises`. Not currently reachable from any route or
  app-startup path (confirmed via grep: only this file's own `tests/test_maintenance.py`,
  fully mocked, and the `__main__` CLI block reference it) — flagging as latent-but-real
  schema-drift, not an active bug.
- **This file is not in the REFACTOR_PLAN.md audit at all** (not named in WP0.4's
  archive-candidate or must-stay lists, despite that WP explicitly auditing "root-level
  one-off scripts"). `[CONTRADICTS-PLAN]`-adjacent gap: `utils/maintenance.py` is a
  `utils/`-housed one-off CLI tool with the same "who runs this and when" ambiguity as the
  scripts WP0.4 does audit, but it lives under `utils/` rather than repo-root `scripts/`
  so WP0.4's grep sweep (scoped to root-level scripts per its own text) would miss it
  entirely. Recommend folding it into WP0.4's scope or filing a companion WP.
- `_exec_many`'s lock-retry loop (`maintenance.py:69-78`) duplicates the *intent* of
  `DatabaseHandler`'s own `_DB_LOCK` serialization in `database.py`, but operates via
  `sqlite3.OperationalError` string-matching (`"locked" in str(exc).lower()`) rather than
  the app's lock primitive — this script opens its own `DatabaseHandler` (which itself
  acquires `_DB_LOCK` per-statement in `execute_query`), so the retry loop is a second,
  redundant safety net against *external* (e.g., another process) lock contention rather
  than in-process contention. `[NEW]` Not wrong, just an extra layer worth knowing about
  if `_DB_LOCK`'s scope ever changes.
- Try/except import fallback at module top (`maintenance.py:8-15`, package-relative vs.
  bare) supports `python -m utils.maintenance` direct invocation outside the Flask app
  context — consistent with this being a standalone CLI tool, not dead code.

---

## Cross-cutting seeds (for synthesis)

1. **Schema-init sprawl is worse than WP2.4's own inventory states.** Confirmed from the
   file-content side (not just the `app.py` call-site side Phase 1 already found): 6
   `add_*_table` functions in `database.py` (not 3) + `db_initializer.initialize_database`
   (4 tables + a data-hygiene pipeline) + `routes/workout_plan.py`'s
   `initialize_exercise_order`/`column_exists`/`table_exists` + `program_backup`'s init +
   `utils/maintenance.py`'s **out-of-sync** DDL for a table `db_initializer.py` already
   owns. A `schema_registry.py` (WP2.4) needs a corrected, complete function inventory
   before it can claim to be the single source of truth — and should probably absorb or
   explicitly exclude `maintenance.py`'s DDL with a comment explaining why it's allowed
   to diverge (it isn't, currently — that divergence should be fixed, not preserved).
2. **"Fetch unique values for a column" exists in (at least) four independent
   implementations** with three different validation strategies (unguarded f-string,
   `ALLOWED_COLUMNS`+enum-map, `ALLOWED_TABLES`+`ALLOWED_COLUMNS` inline in a route) and
   two different signatures (`(column)` vs `(table, column)`). WP1.1 only accounts for
   two of the four. Recommend the synthesis phase re-scope WP1.1 (or add a WP1.1b) once
   all four are confirmed against the routes-phase read.
3. **Exercise-filter query building exists in (at least) three independent
   implementations** (`FilterPredicates.build_filter_query`, `routes/filters.py`'s
   `ALLOWED_COLUMNS`-based single-value path, and
   `filter_exercises_with_expanded_muscles`'s fully separate raw-SQL builder for
   multi-value muscle filters) with two allowlists that must be hand-synced
   (`VALID_FILTER_FIELDS` vs `ALLOWED_COLUMNS`). This is a materially bigger duplication
   than WP1.1 scopes and includes an active routes-layer raw-SQL boundary violation
   against CLAUDE.md §2's module-boundary rule.
4. **Column-existence checks (`PRAGMA table_info` + membership test) are hand-rolled at
   least 6 times across this phase's files alone** (four in `db_initializer.py`'s
   `_initialize_*_table` functions, one in `database.py:add_volume_plan_activation_columns`,
   one in `exercise_manager.py:add_exercise`'s legacy-schema fallback) — a shared
   `column_exists(db, table, column)` helper (which WP2.4 already plans to centralize
   from `routes/workout_plan.py`) should absorb all of these, not just the one it
   currently names.
5. **`query.strip().split()[0].upper()` write-detection in `DatabaseHandler` doesn't
   recognize CTE-prefixed writes (`WITH ... INSERT`)** — confirmed one real instance of
   this exact shape already in the codebase (`maintenance.py`'s `REBUILD_EIM_SQL`),
   meaning that statement currently executes without acquiring `_DB_LOCK`. Low current
   blast radius (single-user local app, that script isn't invoked from any route) but
   worth a one-line fix (check for `INSERT/UPDATE/DELETE` anywhere in the first N tokens,
   or require callers of CTE writes to pass an explicit `is_write` override) independent
   of any larger refactor.
