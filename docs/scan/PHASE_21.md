# Phase 21 — pytest Suite Audit

Scope: `tests/conftest.py` (full) + all 56 `tests/test_*.py` files + `tests/CLAUDE.md` +
`.claude/rules/testing.md`. Goal: ground refactor recommendations in what the tests
actually pin down, not what they're named after.

Raw `def test_` count across the 56 files (parametrize-collapsed): **1,441**. This is
consistent with the documented baseline of 1447 passed (parametrized cases expand at
collection time; a handful of files also define module-level `def test_...` outside
classes not caught by the class-scoped grep pass). No pytest run was performed for this
phase (per instructions) — counts are static/grep-derived.

---

## 1. `tests/conftest.py` — fixture hierarchy and DB isolation

Read in full (347 lines). Exact mechanics:

- **Isolation root**: `test_db_path` fixture returns `str(tmp_path / "test_hypertrophy_toolbox.db")` — a fresh file per test function (`tmp_path` is function-scoped in pytest). No test shares a DB file with another unless it explicitly reuses a fixture within the same test.
- **`app` fixture** (function-scoped):
  1. Saves `utils.config.DB_FILE`, reassigns it to `test_db_path` (assignment, not import — matches the documented pattern).
  2. Builds a bare `Flask(__name__, template_folder=..., static_folder=...)` and registers **13 blueprints**: `main_bp, workout_log_bp, weekly_summary_bp, session_summary_bp, exports_bp, filters_bp, workout_plan_bp, progression_plan_bp, user_profile_bp, body_composition_bp, volume_splitter_bp, program_backup_bp, fatigue_bp`. This is one more than the CLAUDE.md table of 11 blueprints (`body_composition_bp` and `fatigue_bp` are present in conftest but not listed in the root CLAUDE.md §2 blueprint table — **[NEW]** doc drift, low severity, not a test defect).
  3. Registers the `safe_media_path` Jinja filter inline (mirrors `app.py`).
  4. Defines a **local** `/erase-data` POST route inline (not imported from `app.py`) that drops backup tables + core tables and calls `_initialize_test_database()`. This is a hand-maintained duplicate of `app.py`'s real `/erase-data` — see §5 finding on `create_auto_backup_before_erase` vs `create_startup_backup` divergence; the conftest local route does **not** call either backup function before dropping tables, unlike production which calls `create_startup_backup()` first (`app.py:176`). Tests that exercise `/erase-data` via `client.post('/erase-data')` are therefore testing a **behaviorally different route** than production for the pre-erase-snapshot step specifically. **[RISK]**
  5. Calls `_initialize_test_database()` inside `app.app_context()` — full schema: `initialize_database(force=True)` + `add_progression_goals_table` + `add_volume_tracking_tables` + `add_user_profile_tables` + `add_body_composition_snapshots_table` + `add_strength_calibration_tables` + `add_fatigue_context_settings_table` + `initialize_exercise_order` + `initialize_backup_tables`.
  6. On teardown: restores `utils.config.DB_FILE`, best-effort deletes the sqlite file + `-wal`/`-shm`/`-journal` sidecars.
- **`client`**: `app.test_client()`, function-scoped, depends on `app`.
- **`db_handler`**: `DatabaseHandler(test_db_path)`, asserts `PRAGMA foreign_keys` is 1 inside a connection block, closes on teardown.
- **`clean_db`**: `DELETE FROM` (not DROP) on 18 named tables in FK-safe child-before-parent order, preserving schema. Notably **does not** include `body_composition_snapshots` in some ordering nuance — it is listed — nor `exercise_isolated_muscles` is listed but only in `clean_db`, not in the local `/erase-data` route's table list (which drops different tables again). Three different "reset everything" code paths exist (`clean_db`, conftest's inline `/erase-data`, and `app.py`'s real `/erase-data`) with three different table lists — a maintenance hazard: adding a new table requires updating all three by hand. **[RISK]**
- **Factories**: `exercise_factory` (INSERT into `exercises` with sane defaults), `workout_plan_factory` (INSERT into `user_selection`, auto-creates an exercise if none given), `workout_log_factory` (INSERT into `workout_log`, auto-creates a plan if none given). All depend on `clean_db`, forming the documented chain `clean_db → exercise_factory → workout_plan_factory → workout_log_factory`.

This matches `tests/CLAUDE.md` and `.claude/rules/testing.md` almost exactly; the one gap is the blueprint-count/table drift noted above.

---

## 2. Per-plan-question findings

### Q1 — `effective_sets.py:349-575` "second pipeline" — production-dead but unit-tested

**[CONFIRMS-PLAN].** Grepped `aggregate_session_volumes`, `aggregate_weekly_volumes`,
`format_volume_summary`, `calculate_training_frequency`, `calculate_volume_distribution`
across the whole repo (`*.py`): every call site outside `utils/effective_sets.py` itself
is in `tests/test_effective_sets.py`. Zero references from `routes/` or any other
`utils/` module. Production weekly/session aggregation instead goes through
`utils/weekly_summary.py::calculate_weekly_summary` and
`utils/session_summary.py::calculate_session_summary`, which have their own independent
aggregation logic (per CLAUDE.md §5 "not duplicates" note) and do **not** call into this
second pipeline.

**Tests that would be touched by deleting `effective_sets.py:349-576`** (`tests/test_effective_sets.py`):
| Class | Tests |
|---|---|
| `TestTrainingFrequency` | 3 |
| `TestVolumeDistribution` | 4 |
| `TestAggregateSessionVolumes` | 7 |
| `TestAggregateWeeklyVolumes` | 8 |
| `TestFormatVolumeSummary` | 4 |
| **Total** | **26** |

These are clean, well-named behavioral tests (no brittle string matching) — if this code
is ever removed, it's a one-shot deletion of exactly these 26 tests plus the 5 imports at
the top of the file, not a risky partial-refactor.

### Q2 — Five "zero frontend caller" route endpoints — all are pytest-pinned

**[CONFIRMS-PLAN, but adds nuance]**: the endpoints have no *frontend JS* callers per the
Wave-1 scan, but they are **not test-orphaned** — pytest exercises all five directly:

| Endpoint | Test file : test(s) |
|---|---|
| `GET /get_routine_options` | `test_workout_plan_routes.py::TestGetRoutineOptions::test_get_routine_options` |
| `GET /get_user_selection` | `test_workout_plan_routes.py::TestGetUserSelection` (2 tests: empty, with_data) |
| `GET /get_exercise_details/<id>` | `test_workout_plan_routes.py::TestGetExerciseDetails` (2); also `test_priority0_api_contract.py::test_not_found_error_format`, `test_downstream_normalization.py::test_get_exercise_details_returns_normalized_fields` |
| `POST /get_filtered_exercises` | `test_priority0_filters.py::TestGetFilteredExercisesWhitelist` (2 tests) |
| `GET /get_unique_values/<table>/<column>` | `test_priority0_filters.py::TestGetUniqueValuesWhitelist` (5 tests: valid, invalid table, invalid column, 2× SQL-injection); `test_priority0_api_contract.py` (2); `test_downstream_normalization.py` (2) |

Net: deleting any of these five routes would break real, currently-green pytest
coverage (roughly 16 test functions total), even though no browser-side JS calls them.
Any WP that removes "dead" routes must delete/rewrite these tests in the same PR, or the
plan's own dead-code rule ("test references count as references," global rule 8) blocks
the deletion outright.

### Q3 — `advanced_to_basic` is test-fixture-only

**[CONFIRMS-PLAN]** — already dispositioned in the plan's own council response matrix
(#2: "accept... moved to explicit do-not-delete list"). Verified independently: grep for
`advanced_to_basic` across `*.py` finds exactly:
- Definition: `utils/volume_taxonomy.py:318`
- Import + one direct call: `tests/test_volume_taxonomy.py:24,175` (`test_design_calls_documented`)

No caller in `routes/` or any other `utils/` module. `utils/volume_taxonomy.py` is
otherwise heavily used (via `aggregate_planned_sets`, `canonical_pst`, etc. — see
`test_volume_progress.py`), so this one function is a true dead leaf inside an otherwise
live module, kept alive only by the test file's direct-call assertion.

### Q4 — `exercise_manager` falsy-check bug (weight==0 rejected) — TESTED and enshrined

**[CONFIRMS-PLAN] + [RISK].** `tests/test_exercise_manager.py::TestAddExercise::test_add_exercise_missing_weight`
explicitly asserts `weight=0` is treated as missing:
```python
result = ExerciseManager.add_exercise(..., weight=0)  # comment: "Missing/zero"
assert "Error" in result
```
So the falsy-check behavior is not an accidental untested bug — it is pinned by a named
test that documents the intent as "weight 0 == missing." This is a real product-risk
inconsistency worth flagging even though it's outside this phase's job to fix: elsewhere
in the same suite, `scored_weight = 0.0` is a **legitimate** value for assisted-bodyweight
exercises (`test_workout_log_routes.py::test_workout_log_page_renders_zero_assistance_as_entered_value`,
`test_workout_log_utils.py::test_assisted_indicator_treats_zero_assistance_as_improved`).
Any refactor of `ExerciseManager.add_exercise`'s validation must either keep the
0-is-missing rule for the *planning* path while continuing to allow 0 as a real value on
the *logging* path, or explicitly change both together with sign-off — the two code
paths currently disagree on what `weight/scored_weight == 0` means.

### Q5 — `update_exercise` has no server-side validation — untested permissiveness

**[CONFIRMS-PLAN].** `tests/test_workout_plan_routes.py::TestUpdateExercise` has exactly
three tests: `test_update_exercise_sets` (valid update), `test_update_exercise_no_data`
(400), `test_update_exercise_missing_id` (400). None assert what happens for negative
sets, negative/zero weight, inverted rep ranges, or out-of-range RIR/RPE on `/update_exercise`.
Grepped the whole `tests/` tree for negative-value assertions against
`update_exercise`/`update_workout_log` — no hits. The only place negative/zero/decimal
boundary behavior is asserted at all is `e2e/validation-boundary.spec.ts` (Playwright,
23 tests per `.claude/rules/testing.md`'s E2E map) — which is browser-level and does not
prove the *server* rejects bad input; it can pass purely off client-side form
constraints. **No pytest test proves the server validates or rejects invalid
`/update_exercise` payloads.** This is a genuine coverage gap, not just an untested
permissiveness — the plan's premise is confirmed as-is.

### Q6 — body_fat JS↔Python parity — pytest has none, confirmed Playwright-only

**[CONFIRMS-PLAN].** Grepped `tests/` for `parity`, `body-composition.js`, `bodyFat`,
`body_fat.js` — the only hit is an unrelated string in `test_fatigue_context.py`
(false positive, unrelated fatigue-context field name, not a parity check). The Python
formula itself (`utils/body_fat.py`: `compute_navy`, `compute_bmi`, `ace_category`,
`jackson_pollock_ideal`) is thoroughly unit-tested in `tests/test_body_fat.py` (24 tests,
table-anchor + interpolation + clamp + domain-violation cases) and the route layer in
`tests/test_body_composition_routes.py` (20 tests: snapshot CRUD, validation, date
parsing). But there is **no pytest test that cross-checks the client-side JS
implementation's output against `utils/body_fat.py`'s output** — that comparison exists
only in `e2e/body-composition.spec.ts:100-125` per the sibling scan's finding. If the two
implementations drift (e.g., a refactor changes rounding in one but not the other),
pytest's full green run gives zero signal; only the Playwright suite would catch it, and
only if that specific spec is run (it is not in every CI job — full E2E Chromium
baselines the parity spec but WP gates using "full pytest == baseline" alone would miss a
regression here). **[RISK]** for any WP touching `utils/body_fat.py` or its JS twin.

### Q7 — `create_auto_backup_before_erase` tested-but-uncalled

**[CONFIRMS-PLAN], with an added nuance the plan doesn't mention.** Grep confirms
`utils/program_backup.py::create_auto_backup_before_erase` (defined line 604) is called
only from `tests/test_program_backup.py` (7 call sites across 7 tests):
`test_auto_backup_created_before_erase`, `test_auto_backup_skipped_when_program_empty`,
`test_two_auto_backups_same_second_both_succeed`, `test_auto_backup_retention_keeps_latest_n`,
`test_auto_backup_retention_ignores_manual`, `test_auto_backup_prune_cascades_items`,
`test_create_plus_prune_atomic_on_failure`. Zero references from `routes/` or `app.py`.

**Added nuance**: production's real `/erase-data` (`app.py:165-176`) calls a
*different, similarly-named* function — `create_startup_backup()` from
`utils/auto_backup.py` — not `create_auto_backup_before_erase()` from
`utils/program_backup.py`. The two modules (`utils/auto_backup.py` and
`utils/program_backup.py`) each independently implement a "snapshot before wiping data"
concept with near-identical purposes and confusingly similar names. Worse: **`utils/auto_backup.py`
(the one actually wired into production startup and `/erase-data`) has zero test
coverage of its own** — no test file imports it or calls `create_startup_backup`
directly (confirmed by grep). So the coverage picture is inverted from what a
"most-used code has the most tests" heuristic would predict: the *unused* twin has 7
tests and the *live* twin has 0. **[NEW] [RISK]** — flag `utils/auto_backup.py` as a
coverage gap independent of the plan's original question.

---

## 3. Coverage matrix — `utils/` (35 modules)

| Module | Test file(s) | Approx. tests | Notes |
|---|---|---|---|
| `config.py` | `test_config.py` | 21 | Full — paths, env overrides, dir creation |
| `errors.py` | `test_errors_utils.py` (+ `test_priority7_error_handling.py` partial) | 30+ | Full |
| `logger.py` | `test_logger.py` | 14 | Mock-heavy (RotatingFileHandler mocked) |
| `volume_ai.py` | `test_volume_ai.py` | 26 | Full, pure-function |
| `effective_sets.py` | `test_effective_sets.py` | 68 | Heaviest single unit-test file; includes the 26 dead-pipeline tests (Q1) |
| `exercise_manager.py` | `test_exercise_manager.py` | 36 | Full CRUD + duplicate-prevention + isolated-muscle sync |
| `filter_predicates.py` | `test_filter_predicates.py` | 39 | Full, SQL-injection-focused |
| `maintenance.py` | `test_maintenance.py` | 19 | **All DB access mocked** (`MagicMock`) — no real-DB integration test of `normalize_and_rebuild_eim` end to end |
| `normalization.py` | `test_normalization.py` (6) + `test_downstream_normalization.py` (6, integration) | 12 | Thin unit file but backed by solid route-level integration |
| `session_summary.py` | `test_session_summary.py` | 30 | Full |
| `volume_classifier.py` | `test_volume_classifier.py` | 43 | Full, boundary-heavy |
| `weekly_summary.py` | `test_weekly_summary.py` | 4 | **Thin** — only 4 top-level tests for a calculation module CLAUDE.md calls out as protected; relies on `test_weekly_summary_routes.py` (mock-based, not real calc) for the rest |
| `auto_backup.py` | **none** | 0 | **[RISK]** — see Q7. Production startup + `/erase-data` snapshot path is completely untested at the utils layer |
| `program_backup.py` | `test_program_backup.py` | 41 | Very heavy — commit-count assertions, rollback, retention/pruning, row-for-row restore integrity |
| `volume_export.py` | via `test_volume_splitter_api.py` + `test_volume_progress.py` (`export_volume_plan` calls) | ~10 indirect | No dedicated `test_volume_export.py`; covered as a dependency, including one rollback-on-failure test |
| `volume_progress.py` | `test_volume_progress.py` | 31 | Full |
| `media_path.py` | `test_free_exercise_db_mapping.py` (`TestMediaPathShapeValidator`, `TestMediaPathResolves`, `TestSafeMediaPathJinjaFilter`) | ~15 | Full |
| `workout_log.py` | `test_workout_log_utils.py` | 25 | Full — all 5 progression conditions, NULL handling, assisted-bodyweight semantics |
| `body_fat.py` | `test_body_fat.py` | 24 | Full Python-side; **no JS parity** (Q6) |
| `fatigue.py` | `test_fatigue.py` | 72 | Heaviest file overall; 17 classes covering set/session/weekly aggregation, classification, Unassigned-bucket invariant, period windows |
| `progression_plan.py` | `test_progression_plan_utils.py` (43) + `test_double_progression.py` (25, overlapping) | ~50 unique | Two files test largely the same functions (`_calculate_weight_increment`, `_check_acceptable_effort`, `_get_progression_status`, `generate_progression_suggestions`) — see smells §4 |
| `lift_matching.py` | **none direct** | 0 direct | Only reached indirectly through `test_strength_calibration.py` / `test_calibration_integration.py` / `test_profile_estimator.py` exercising the higher-level functions that call into it; no unit test targets `lift_matching` functions by name |
| `strength_calibration.py` | `test_strength_calibration.py` (36) + `test_calibration_integration.py` (28) + `test_workout_log_calibration_route.py` (7) | 71 | Full, layered (pure logic → DB lifecycle → route hooks → integration) |
| `fatigue_context.py` | `test_fatigue_context.py` | 29 | Full |
| `fatigue_data.py` | `test_fatigue_routes.py` (`build_fatigue_page_context` used directly + via route) | ~12 | Adequate, route-level only (no isolated unit-test file) |
| `database.py` | Distributed: `test_db_migration.py`, `test_database_user_profile.py`, `test_priority0_fk_integrity.py`, implicit via every fixture | many (indirect) | No single `test_database.py`; `DatabaseHandler` core behavior (context manager, journal mode) has no dedicated isolated test beyond FK-enabled checks |
| `request_id.py` | `test_priority7_error_handling.py` (`test_request_id_format`, middleware tests) | ~6 | Adequate but thin for a cross-cutting concern |
| `volume_taxonomy.py` | `test_volume_taxonomy.py` | 8 | Small count but each test is a broad "every value in the *live* DB must map" invariant — see §4 for the live-DB dependency smell |
| `db_initializer.py` | `test_priority0_filters.py` (trim/repair tests) | ~6 | Partial — `initialize_database` itself only tested via its side effects (whitespace trim, equipment repair), not directly unit-tested |
| `export_utils.py` | `test_exports.py` (`TestFilenameSanitization`, `TestContentDisposition`, `TestTimestampedFilename`, `TestExportSizeEstimation`) | ~20 | Full |
| `profile_estimator.py` | `test_profile_estimator.py` | 64 | Second-heaviest file; extremely thorough (tier classification, Epley formula, rounding, load-basis conversion, cold-start, cohort ranges, bodymap coverage, trace/telemetry) |
| `__init__.py` | none | 0 | Expected — deprecated facade per CLAUDE.md, not authoritative for new code |
| `movement_patterns.py` | `test_plan_generator.py` (`TestMovementPatternClassification`, `TestSessionBlueprints`, `TestPrescriptionRules`) | ~20 | Full |
| `constants.py` | `test_constants.py` | 45 (many trivial `isinstance` checks) | Full but low-value — see smells §4 |
| `plan_generator.py` | `test_plan_generator.py` (37) + `test_phase3_features.py` (20, Phase-3 execution styles/merge/time-budget/superset-suggestion) + `test_superset.py` (2, generator-superset interaction) | ~59 | Full, two generations of features |
| `exercise_media.py` | **none direct** — only indirect via `test_workout_plan_routes.py` media-path-fallback tests hitting `/get_workout_plan` | 0 direct | Route-level only; no isolated unit test of the mapping/fallback functions themselves |

## 4. Coverage matrix — `routes/` (13 modules)

| Route module | Test file(s) | Notes |
|---|---|---|
| `main.py` | none dedicated | Only incidentally exercised (`client.get('/')` inside `test_priority7_error_handling.py`'s request-ID tests); no assertions on home-page content/behavior itself |
| `workout_log.py` | `test_workout_log_routes.py` (38) | Full |
| `weekly_summary.py` | `test_weekly_summary_routes.py` (30) | Route layer is **fully mock-isolated** — every test patches `calculate_weekly_summary`/`calculate_exercise_categories`/`calculate_isolated_muscles_stats`; builds its own bare Flask app + blueprint instead of using the shared conftest `app`/`client` fixtures (see smells) |
| `session_summary.py` | `test_session_summary_routes.py` (31) | Same pattern as weekly_summary — own local app fixture, full mocking |
| `exports.py` | `test_exports.py` (39, shared with `export_utils.py`) | Full |
| `filters.py` | `test_priority0_filters.py` (23) + `test_priority0_api_contract.py` | Full, security-focused |
| `workout_plan.py` | `test_workout_plan_routes.py` (36) + `test_replace_exercise.py` (10) + `test_superset.py` (14) | Full |
| `progression_plan.py` | `test_progression_plan_routes.py` (18) | Full |
| `user_profile.py` | `test_user_profile_routes.py` (30) | Full, includes render-content assertions (brittle — see smells) |
| `body_composition.py` | `test_body_composition_routes.py` (20) | Full |
| `volume_splitter.py` | `test_volume_splitter_api.py` (10) + `test_volume_progress.py` (route half) | Full |
| `program_backup.py` | `test_program_backup.py` (`TestProgramBackupAPI`, `TestEraseDataDeletesBackups`) | Full |
| `fatigue.py` | `test_fatigue_routes.py` (12) | Adequate |

---

## 5. Test smells

1. **Route tests that bypass the shared conftest app/client entirely.** `test_weekly_summary_routes.py` and `test_session_summary_routes.py` each define their *own* local `app`/`client` fixtures (bare `Flask(__name__)` + single blueprint), overriding the module-scoped conftest fixtures of the same name. This works because pytest fixture resolution is file-local, but it means these two files test the route in total isolation from the rest of the app (no DB, no other blueprints, no middleware) and via heavy `unittest.mock.patch` of the calculation functions. That's a deliberate, reasonable choice for a route-contract test, but it means **the actual calculation numbers are never asserted here** — correctness of `calculate_weekly_summary`/`calculate_session_summary` output is entirely the job of `test_weekly_summary.py` (4 tests) and `test_session_summary.py` (30 tests) respectively. `test_weekly_summary.py`'s thinness (4 tests for a CLAUDE.md-protected calculation module) is therefore a real coverage gap, not compensated for by the route file.

2. **Brittle full-string / exact-HTML assertions in `test_user_profile_routes.py`.** Many tests assert exact rendered strings, e.g. `'value="100.0"' in html`, `'class="reference-lift-group-title">Chest<' in html`, `">Barbell Back Squat</li>" in html`. These will break on *any* template markup change (adding a wrapper `<div>`, changing a class name, reformatting whitespace) even when the underlying behavior is unchanged — a pure-refactor risk multiplier for `templates/user_profile.html`. 30 tests in this file, a large fraction of which are this shape. Any WP touching that template must expect to update dozens of exact-string assertions even for cosmetic changes.

3. **Two test files independently re-testing the same pure functions.** `test_progression_plan_utils.py` and `test_double_progression.py` both import and directly test `_calculate_weight_increment`, `_check_acceptable_effort`, `_get_progression_status`, `_analyze_consistency`, and `generate_progression_suggestions` from `utils/progression_plan.py`, with overlapping (not identical) case coverage. Not harmful, but a merge/rename of any of these functions requires touching two files instead of one, and a reviewer skimming just one file will underestimate real coverage.

4. **Live-database-dependent tests (`data/database.db`, not the fixture DB).** `test_volume_taxonomy.py` and `test_catalog_invariants.py` explicitly `sqlite3.connect(data/database.db)` — the real shipped catalog — bypassing the `clean_db`/`app` isolation entirely. This is deliberate and documented in both files' docstrings ("Phase 0 gates on the real catalog taxonomy, not seeded fixtures"), but it means: (a) these tests can fail in an environment where `data/database.db` is missing, stale, or has been legitimately edited for an unrelated reason (git status at session start shows `M data/database.db`, i.e., it's currently modified in the working tree); (b) "full pytest == baseline" as a refactor gate is silently coupled to the *content* of the live DB, not just code — a schema-preserving but content-changing edit to `data/database.db` could flip these tests red with zero code change. **[RISK]** for any WP gate that assumes pytest is purely a function of source code.

5. **Low-value tautological tests in `test_constants.py`.** A meaningful fraction of its 45 tests are `isinstance(X, dict)` / `isinstance(value, str)` checks with no behavioral content (e.g. `test_force_is_dict`, `test_mechanic_values_are_strings`, all of `TestConstantsConsistency`). These pad the count without adding refactor protection — they'd pass against almost any non-empty dict. Genuinely useful subset: the specific synonym/alias assertions (`test_dumbbell_synonyms`, `test_normalize_muscle_aliases`-adjacent checks).

6. **`test_maintenance.py` is 100% mock-based.** Every test in the file uses `MagicMock()` for `DatabaseHandler`/db objects — there is no test that runs `normalize_and_rebuild_eim()` against a real (even fixture) SQLite DB and checks the resulting rows in `exercise_isolated_muscles`. The SQL strings themselves are checked for substring presence (`"DELETE FROM exercise_isolated_muscles" in combined`) rather than executed. A refactor that changes the SQL's *behavior* while keeping matching substrings would pass this file undetected.

7. **`test_exports.py` fixtures directly mutate the shared DB without full isolation guarantees for parallel runs.** Fixtures like `large_workout_log` insert 1000 rows and clean up in a `yield`/finally-less `DELETE` after the test — acceptable under the current serial pytest execution model, but fragile if the suite is ever parallelized (pytest-xdist), since these fixtures assume no other test is touching `workout_log` concurrently. Not a bug today, but a latent constraint on any future CI speed-up work.

8. **Response-shape tests double as behavior tests without separating the two concerns.** Several files (`test_priority0_api_contract.py`, `test_weekly_summary_routes.py`) assert both the wrapper envelope (`ok`/`status`/`error.code`) and business content in the same test function. This is fine for now but means a WP that only touches the envelope helper (`utils/errors.py`) risks needing to re-verify content-bearing tests it didn't intend to touch, and vice versa.

**What's *not* a smell — genuinely resilient tests worth calling out:** `test_effective_sets.py`, `test_fatigue.py`, `test_profile_estimator.py`, `test_strength_calibration.py`, and `test_volume_progress.py` are consistently behavior-focused: they assert computed values (`pytest.approx`) and named outcome fields, not implementation shape. These are the files most safe to refactor *underneath* — they'll only break if the actual math or the field names visible to callers change, exactly the CLAUDE.md refactor invariant they're meant to protect.

---

## 6. Cross-cutting seeds

- **Backup-function naming collision is a standalone refactor candidate.** `utils/auto_backup.py::create_startup_backup` (live, zero tests) and `utils/program_backup.py::create_auto_backup_before_erase` (dead in production, 7 tests) do overlapping jobs under confusingly similar names. A future WP should either (a) add a pytest test for `create_startup_backup` before touching either module, or (b) fold the two backup-before-erase concepts into one function and delete the loser, updating both test files. Do this as its own WP, not a drive-by inside a bigger one — the two modules currently have completely disjoint test authorship assumptions.
- **`update_exercise`/`update_workout_log` validation gap (Q5) plus the `weight==0` inconsistency (Q4) are related**: both concern what counts as a "valid" numeric value across the plan-vs-log boundary. A single WP proposing consistent numeric validation across `ExerciseManager.add_exercise`, `/update_exercise`, and `/update_workout_log` would resolve two separate audit findings at once — but per the plan's global rule 1 ("behavior-preserving only"), that WP needs explicit product-risk sign-off since it changes validation *behavior*, not just code shape.
- **The live-DB test dependency (`test_volume_taxonomy.py`, `test_catalog_invariants.py`) should be called out explicitly in any WP's gate description** — "full pytest == baseline" is not purely hermetic today. Worth a one-line addendum to `.claude/rules/testing.md` documenting that these two files require `data/database.db` to exist and be schema-current, independent of the tmp-DB fixtures every other file uses.
- **`utils/lift_matching.py` and `utils/exercise_media.py`** have no direct unit-test file (only reached transitively through higher-level callers' tests). Any WP that refactors either module's internals — even behavior-preservingly — has weaker regression protection than the "full pytest == baseline" gate implies; consider a smaller, targeted pytest addition as a low-risk pre-step before restructuring either module, independent of the larger refactor plan.
- **Body-fat JS/Python parity (Q6) has no pytest coverage at all.** If any WP in the CSS/JS cleanup phases (Phase 3/4 per `docs/REFACTOR_PLAN.md`) touches `static/js/modules/body-composition.js` or `utils/body_fat.py`, the gate must explicitly include `e2e/body-composition.spec.ts`, not just pytest — "full pytest == baseline" would pass through a parity regression silently.
