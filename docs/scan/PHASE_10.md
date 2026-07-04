# Phase 10 — Routes: remainder

Read line-by-line: `routes/body_composition.py` (336), `routes/volume_splitter.py` (313),
`routes/workout_log.py` (250), `routes/program_backup.py` (234), `routes/weekly_summary.py`
(159), `routes/session_summary.py` (146), `routes/fatigue.py` (29), `routes/main.py` (8).
Also read `.claude/rules/routes.md`, `routes/CLAUDE.md`, and (for plan context, since
`docs/REFACTOR_PLAN.md` does not exist in this worktree — it's an untracked file that
only exists in the sibling `Hypertrophy-Toolbox-v3-main` checkout) the plan body from
that sibling path.

Convention: `FILE:LINE — observation` · tag `[CONFIRMS-PLAN]` / `[CONTRADICTS-PLAN]` /
`[NEW]` / `[RISK]`.

---

## routes/main.py (8 lines)

- **main.py:1-8 — as thin as a route can get.** One blueprint, one route, one
  `render_template` call, zero logic, zero error handling (nothing to fail). `[CONFIRMS-PLAN]`
  Textbook example of the target shape for every other file in this phase.

## routes/fatigue.py (29 lines)

- **fatigue.py:19-29 — thin, correct shape.** `fatigue_page()` does
  `request.args.get('period')` → `build_fatigue_page_context(period)` (utils call) →
  `render_template`. No DB, no business logic in the route. `[CONFIRMS-PLAN]`
- **fatigue.py:26 — `is_xhr_request(request)` called with a positional argument the
  function does not accept.** `[RISK][NEW]` `utils/errors.py:47` defines
  `def is_xhr_request() -> bool:` — **zero parameters**, it reads Flask's global `request`
  proxy internally. Every other caller (`weekly_summary.py:98,127`, `session_summary.py:115,144`,
  `progression_plan.py:231`) calls it as `is_xhr_request()`. `fatigue.py:26` is the sole
  caller passing an argument. This raises `TypeError: is_xhr_request() takes 0 positional
  arguments but 1 was given` — but only on the already-exceptional path (inside the
  `except Exception:` block after `build_fatigue_page_context` fails), so it masks the
  real error: an XHR client hitting a broken `/fatigue` page gets an unhandled 500
  crash-in-the-handler instead of the intended `error_response("INTERNAL_ERROR", ...)`.
  Low traffic surface (only fires when the page is already broken) but a genuine bug —
  one-line fix (`is_xhr_request()`).

## routes/body_composition.py (336 lines)

- **body_composition.py:1-8 — docstring explicitly scopes the module as "HTTP plumbing,
  validation, and DB I/O"**, math delegated to `utils/body_fat.py`. `[NEW]` This is a
  *documented* deliberate exception to `routes/CLAUDE.md:4`'s "no direct DB access" rule,
  not an oversight — but it still contradicts the stated architecture rule literally.
  Every route in the file (`body_composition`, `create_snapshot`, `list_snapshots`,
  `delete_snapshot`) opens `DatabaseHandler()` and runs a raw SQL string in the handler
  (lines 171-181, 250-284/276-284, 299-308, 319-331). `[CONTRADICTS-PLAN]` — worth a
  named WP (`utils/body_composition.py` CRUD layer) if the plan's "no DB in routes" rule
  is meant literally; currently the file is internally consistent and well-organized, just
  not compliant with the stated rule.
- **body_composition.py:36-117 — six private validation helpers** (`_get_json_payload`,
  `_nullable_text`, `_required_float`, `_nullable_float`, `_required_int`,
  `_parse_captured_at`) are exactly the routes-level bound-checking pattern
  `.claude/rules/routes.md:60-61` calls out as correct route-layer work (cf.
  `workout_plan.py`'s sets/reps/weight/RIR bounds). `[CONFIRMS-PLAN]` These are NOT
  business logic — they're input parsing/validation, appropriately placed.
- **body_composition.py:139-165 — `_profile_demographics` reads and validates
  `user_profile` fields (gender/age/height/weight) needed for BFP calculation.**
  Borderline: it's demographic *validation* (route-appropriate) but it also encodes a
  business rule (which four fields are required to save a snapshot). `[NEW]` minor —
  not urgent, but if `utils/body_fat.py` ever needs to validate the same precondition
  from a second caller, this would need to move.
- **body_composition.py:216-224 — Navy-method completeness rule lives in the route**
  (`any_tape`/`required_tape`/`all_required_tape` gender-conditional logic deciding
  whether to compute `bfp_navy` at all). `[NEW]` This is domain logic (which
  measurements the Navy formula needs per gender), arguably belongs next to
  `compute_navy` in `utils/body_fat.py` rather than in the route.
- **body_composition.py:192 — `render_template("error.html", message=...)`.** `[RISK][NEW]`
  See cross-cutting section below — `error.html` doesn't have a `message` variable.
- Otherwise: consistent `error_response`/`success_response`(`jsonify`-wrapped) usage,
  consistent try/except-then-log shape across all 4 routes. `[CONFIRMS-PLAN]` on response
  contract.

## routes/volume_splitter.py (313 lines)

- **volume_splitter.py:16-57 — four module-level helper functions
  (`get_muscle_list_for_mode`, `build_default_ranges`, `sanitize_range_value`,
  `parse_requested_ranges`) contain domain logic (basic vs advanced muscle-group
  selection, default 12-20 set range, per-muscle range sanitization/clamping) sitting
  directly in the routes file, not in a `utils` module.** `[NEW]` — extends the fat-route
  pattern the plan documents for `workout_plan.py`/`user_profile.py`/`exports.py`
  (WP1.1-1.3 + the post-1.3 audit note) to a **fourth file the plan doesn't mention**.
- **volume_splitter.py:74-133 `calculate_volume` — the per-muscle status classification
  (`optimal`/`low`/`high`/`excessive` against min/max ranges, `sets_per_session > 10`
  override) is computed inline in the route (lines 97-122), not via a utils function.**
  `[NEW][RISK]` This is a *different* classification scheme from
  `utils/volume_classifier.py`'s tier-based `get_volume_class`/`get_volume_label` (fixed
  30/20/10/0 raw-set thresholds used on weekly/session summary pages) — not a duplicate
  of existing logic, but a second, undocumented volume-classification algorithm that
  lives only in this route. A refactor should either name and move it to
  `utils/volume_classifier.py` (or a new `utils/volume_splitter_calc.py`) for
  testability, or explicitly document why it's route-local.
- **volume_splitter.py:76-86 — nested try/except structure is confusing but not
  buggy on inspection:** outer try parses `mode`/`training_days` (lines 77-80); a
  `TypeError`/`ValueError` from `int(...)` falls back to `training_days = 3` silently
  (no validation error surfaced to the client — an invalid `training_days` never causes
  a 400, it's just coerced); any other exception logs and returns 500. `mode` is always
  assigned before the exception-prone `int()` call, so no `UnboundLocalError`. `[NEW]`
  minor: silently-coerced invalid input is a design choice, not obviously wrong, but note
  it uses `logger.exception('...: %s', e)` redundantly (both `%s` and `.exception()`
  already logs the traceback) — repeated at lines 84, 132, 167, 194, 228, 239, 250, 266
  (8 occurrences in this file alone). `[NEW]` cosmetic/logging-hygiene, low priority.
- **volume_splitter.py:135-267 — `get_volume_history`, `get_volume_plan`,
  `delete_volume_plan` run raw SQL directly in the route via `DatabaseHandler`**
  (JOIN queries at 139-146, 201-206; DELETE at 261), while `save_volume_plan`,
  `activate_saved_volume_plan`, `deactivate_saved_volume_plan` correctly delegate to
  `utils.volume_export.export_volume_plan` / `utils.volume_progress.activate_volume_plan`
  / `deactivate_volume_plan`. `[CONTRADICTS-PLAN]` — inconsistent within the same file:
  some CRUD paths for the same `volume_plans`/`muscle_volumes` tables go through utils,
  others don't. A `utils/volume_plans.py` (or extend `volume_progress.py`) read/delete
  layer would unify this.
- **volume_splitter.py:269-313 `export_volume_excel` — Excel-building logic (openpyxl
  workbook construction, column widths, sheet naming) lives entirely in the route.**
  `[NEW]` Compare to `workout_log.py`/`exports.py` which delegate Excel generation to
  `utils/export_utils.create_excel_workbook`. This route hand-rolls its own workbook
  instead of reusing that utility — both a fat-route violation and a missed
  reuse opportunity (worth checking export_utils.py's capability at synthesis).
  Also note: no error handling at all in this endpoint (no try/except) — if
  `volumes[muscle]/training_days` throws (e.g. non-numeric `weekly_sets` from a
  malformed payload), it's an unhandled 500 via Flask's generic handler rather than the
  app's `error_response` contract. `[RISK]`

## routes/workout_log.py (250 lines)

- **workout_log.py:38-95 `update_workout_log`, 97-130 `delete_workout_log`,
  132-157 `update_progression_date`, 226-250 `clear_workout_log` — all four build and
  execute raw SQL (UPDATE/DELETE) directly in the route via `DatabaseHandler`.**
  `[CONTRADICTS-PLAN]` `utils/workout_log.py` exists (read this phase, 154 lines) but
  contains only read/derive helpers (`get_workout_logs`, `check_progression`,
  `get_weight_progression_indicator`, `is_assisted_bodyweight_exercise`,
  `is_weight_progression`) — **no write path**. All log mutation logic lives in the
  routes file. This is the clearest "DB work directly in a route instead of via utils"
  instance in this phase — a third file (after body_composition.py, volume_splitter.py)
  making the same violation, i.e. a *pattern*, not an isolated case.
- **workout_log.py:59-61 — dynamic `SET` clause built from a whitelist
  (`valid_fields` set at line 49-52) via `f"{k} = ?"` join.** `[NEW]` Not a SQL-injection
  risk (keys are pre-filtered against a fixed literal set, values are parameterized) but
  it is dynamic SQL construction in a route with no equivalent to `filters.py`'s
  `validate_column_name()` guard — works today only because `valid_fields` is a closed,
  hardcoded set literal at the call site. If someone adds a field to `valid_fields`
  without checking it's a real column, the failure mode is a SQL error, not a security
  hole — low risk but worth noting as the kind of pattern that should route through a
  utils helper with the same guard rails as `filters.py`.
- **workout_log.py:74-86, 116-123 — calibration recompute deliberately swallows its own
  exceptions** ("Guarded so a calibration failure never rolls back the user's log
  write" — comment at line 75-78). `[CONFIRMS-PLAN]` This is intentional, documented,
  and consistent with the non-goal that effective-sets/calibration info must never block
  user actions (root CLAUDE.md §1 Non-goals). Correctly implemented, not a smell.
- **workout_log.py:83, 120 — bare `except Exception:` inside the `with DatabaseHandler()`
  block for calibration only** — the outer log write (`db.execute_query`) is NOT inside
  this guarded try, so a DB failure on the actual UPDATE/DELETE still propagates to the
  outer handler correctly. Ordering is right. No risk.
- Otherwise thin: validation → whitelist → DB check-exists → mutate → respond. Response
  contract consistent (`success_response`/`error_response`). `[CONFIRMS-PLAN]` on
  contract; `[CONTRADICTS-PLAN]` on "no direct DB access" as noted above.

## routes/program_backup.py (234 lines)

- **program_backup.py:1-234 — the cleanest file in this phase.** Every route
  (`backup_center`, `api_list_backups`, `api_create_backup`, `api_get_backup`,
  `api_restore_backup`, `api_delete_backup`, `api_update_backup`) is validate → call one
  of `create_backup`/`list_backups`/`get_backup_details`/`restore_backup`/
  `delete_backup`/`update_backup_metadata` (all from `utils.program_backup`) → respond.
  Zero raw SQL in the routes file. `[CONFIRMS-PLAN]` — this is the file the other three
  in this phase should look like.
- **program_backup.py:226-234 `init_backup_tables()` — exactly the thin wrapper the
  refactor plan's WP2.4 describes:** a routes-layer function whose entire body is
  `initialize_backup_tables()` (imported from `utils.program_backup` at line 18) wrapped
  in try/except-log. `[CONFIRMS-PLAN]` Confirms WP2.4's premise precisely. Traced the
  callers: `app.py:25` imports `init_backup_tables` from `routes.program_backup`;
  `app.py:77` calls it at startup; `app.py:220` calls it again inside `/erase-data`'s
  duplicated init block (consistent with the Phase-1 finding that erase_data repeats the
  whole 8-call startup sequence). A third call site, `e2e/scripts/prepare_visual_db.py:86,100`,
  also imports and calls the **routes** wrapper (not the utils function directly) — this
  is a caller WP2.4 must account for that the plan's caller list doesn't explicitly name
  by this exact reference (it does list `e2e/scripts/prepare_visual_db.py` generally).
  Meanwhile `tests/conftest.py:31,51` and `tests/test_harness_isolation.py:8,19` already
  import `initialize_backup_tables` straight from `utils.program_backup`, bypassing the
  routes wrapper entirely — i.e. the test suite already treats the routes wrapper as
  optional, supporting WP2.4's plan to have `schema_registry.run_all_initializers()` call
  the utils function directly and leave the routes wrapper as a deprecated re-export only
  used by `prepare_visual_db.py` until that script is updated too.
- **program_backup.py:44 — `render_template("error.html", message=...)`.** `[RISK][NEW]`
  Same template-variable bug as body_composition.py — see cross-cutting section.
- Response codes: `api_restore_backup` (line 169) returns `error_response("NOT_FOUND",
  str(e), 404)` for a `ValueError` from `restore_backup` — using the exception message
  directly as the user-facing string. `[NEW]` Fine as long as `utils.program_backup`
  never puts anything internal/sensitive in that `ValueError` message (single-user local
  app, no PII risk today, just a coupling to watch if error messages are refactored).

## routes/weekly_summary.py (159 lines)

- **weekly_summary.py:29-36 `_parse_counting_mode` / 34-36 `_parse_contribution_mode` —
  thin compatibility wrappers that just call the shared parser from
  `utils.effective_sets`.** `[NEW]` Duplicated verbatim in `session_summary.py:31-38`
  (identical bodies, identical docstrings). Trivial (4 lines × 2), but a clean example of
  a small cross-file duplication a refactor could dedupe into one shared routes-level
  helper (or just call `shared_parse_counting_mode` directly at both call sites and drop
  the wrapper — the docstrings suggest they were added as a compatibility shim that
  never got removed).
- **weekly_summary.py:56-78 — the route builds a 19-field-per-muscle response dict**
  inline (legacy aliasing: `total_weight` = alias of `total_volume`, `total_sets` = alias
  of `weekly_sets`, defensive `.get(..., fallback)` for effective/raw variants).
  `[NEW]` This is response-shaping, not calculation — the actual math is in
  `calculate_weekly_summary` (utils). Borderline whether this belongs in the route or a
  utils-level formatter; it's mechanical enough (no business decisions, just field
  renaming/aliasing) that leaving it in the route is defensible, but it's ~25 lines of
  the ~90-line route, i.e. plurality of the function is response reshaping. Compare to
  `session_summary.py:60-89` which does the identical pattern.
- **weekly_summary.py:83-97, `session_summary.py:93-113` — fatigue-badge computation
  wrapped in its own try/except that degrades gracefully to an empty-state badge.**
  `[CONFIRMS-PLAN]` Matches root CLAUDE.md §1 non-goal ("effective sets... never
  auto-adjust or block user actions") extended correctly to the fatigue badge; comment
  explicitly cites "BRAINSTORM §1 non-goal." Well-documented, intentional.
  Note: this is the *same* pattern as `workout_log.py`'s calibration-swallow — a
  recurring, consistent "advisory computation must never break the page" idiom across
  three unrelated route files. Worth naming as a codebase convention if not already
  documented somewhere central (it currently lives only as repeated inline comments).
- **weekly_summary.py:98-107, 127-128 — dual response mode via `is_xhr_request()`**
  (JSON for XHR, `render_template` for full page load), both success and error paths.
  `[CONFIRMS-PLAN]` clean, consistent with `.claude/rules/routes.md`'s XHR-detection
  description; correctly uses the zero-arg `is_xhr_request()` (unlike `fatigue.py`).
- **weekly_summary.py:129 — `render_template("error.html", message=...)` on the
  non-XHR error path.** `[RISK][NEW]` Same bug, see cross-cutting.
- **weekly_summary.py:132-159 `get_pattern_coverage` — genuinely thin**: one call to
  `calculate_pattern_coverage()`, `success_response`, `error_response`. Good docstring
  describing the shape (`per_routine`/`total`/`warnings`/`sets_per_routine`/
  `ideal_sets_range`). `[CONFIRMS-PLAN]` — this endpoint (named in the task prompt as one
  to watch) is not fat; all its complexity is correctly in
  `utils/weekly_summary.py::calculate_pattern_coverage` (WP2.3 targets that function for
  decomposition, not the route — consistent with what's actually here).

## routes/session_summary.py (146 lines)

- Structurally near-identical to `weekly_summary.py`: same duplicated mode-parser
  wrappers (29-38 mirrors weekly_summary.py:29-36), same response-dict reshaping pattern
  (60-89, 21 fields per muscle — even more fields than weekly_summary's, includes
  session-state and volume-warning flags), same fatigue-badge try/except-degrade
  (93-113), same dual XHR/render_template response mode (115-141), same
  `render_template("error.html", message=...)` bug (146). `[NEW]`/`[RISK]` — same notes
  as weekly_summary.py apply; flagging here to avoid re-deriving, not duplicating detail.
- **session_summary.py:100-108 — routine-vs-heaviest fatigue branching
  (`compute_session_fatigue_for_routine` vs `compute_heaviest_session_fatigue`) lives in
  the route**, choosing the period label text based on which path was taken. `[NEW]`
  Borderline: it's presentation logic (which label to show) driven by a business decision
  (which routine's fatigue to display when none is specified) — small enough that
  extracting it wouldn't meaningfully thin the route, but it's one of the only places in
  this file with a real conditional business decision rather than pure reshaping.
- No unique issues beyond what's mirrored from weekly_summary.py.

---

## Cross-cutting seeds

- **`error.html` template contract violated by 6 of ~8 route files that use it
  fallback-render it.** `[RISK][NEW]` **This is the single highest-value finding in this
  phase.** `templates/error.html` (read this phase) expects `error_title`, `error_code`,
  `error_message` (and optionally `error_detail_code`, `request_id`). Grepped every
  `render_template("error.html", ...)` call site in the repo:
  `weekly_summary.py:129`, `user_profile.py:469`, `program_backup.py:44`,
  `session_summary.py:146`, `progression_plan.py:133`, `body_composition.py:192` **all
  pass `message=...`** — a variable the template never reads — while
  `error_title`/`error_code`/`error_message` are left undefined (Jinja silently renders
  undefined vars as empty strings, no exception). **Only `routes/fatigue.py:28` passes
  the correct `error_message=...` key** (and even that omits `error_title`/`error_code`).
  Net effect: on the exception path of 6 major pages (weekly/session summary, user
  profile, backup center, progression plan, body composition), the fallback error page
  renders with a blank title, blank status code, and blank message — just the "Return to
  Home"/"Go Back" buttons and layout chrome. Users hitting a genuine 500 on any of these
  pages get a near-blank error page instead of a helpful one. Not covered by
  `docs/REFACTOR_PLAN.md` at all (no WP mentions `error.html` or these render calls) —
  **new finding, not a plan validation**. Fix is mechanical (rename `message=` →
  `error_message=`, add `error_title=`/`error_code=` at each of the 6 sites) but touches
  2 files outside this phase's scope (`user_profile.py`, `progression_plan.py` — Phase 9)
  so a fix WP should cover all 6 together.
- **DB-work-in-routes is a 3-file pattern, not an isolated case.**
  `[CONTRADICTS-PLAN][NEW]` `body_composition.py` (full CRUD), `volume_splitter.py`
  (partial — history/get/delete raw SQL, save/activate/deactivate delegate correctly),
  and `workout_log.py` (all 4 mutation routes) all run `DatabaseHandler` queries directly
  in route handlers, contradicting `routes/CLAUDE.md:4`'s explicit "no direct DB access"
  rule. `docs/REFACTOR_PLAN.md` Phase 1 (routes slim-down) only targets
  `workout_plan.py`/`filters.py` (WP1.1-1.3) and says to *audit* `user_profile.py` /
  `exports.py` afterward — it does not mention `body_composition.py`,
  `volume_splitter.py`, or `workout_log.py` at all. If Phase 1's thin-route goal is meant
  to generalize, these three are concrete follow-up candidates; `program_backup.py`
  (this phase) and `main.py`/`fatigue.py` (this phase) are the counter-examples proving
  the pattern is achievable and already the norm elsewhere in the codebase.
- **Volume-domain logic scattered across 2+ locations with 2 different
  classification schemes.** `[NEW]` `utils/volume_classifier.py`'s tier-based
  `get_volume_class`/`get_volume_label` (fixed 30/20/10/0 raw-set thresholds, used by
  weekly/session summary) is a *different* algorithm from the inline
  optimal/low/high/excessive-against-custom-range logic in
  `routes/volume_splitter.py:97-122` (used only by the volume splitter page). Both are
  legitimately separate features (global volume tiers vs. user-tunable per-muscle
  target ranges), so this isn't a duplication bug — but the second one currently has
  zero unit-test surface of its own (it's inline in a route, only reachable via an
  integration test through the endpoint), unlike the first which lives in a testable
  utils module. A refactor extracting it to utils would also make it independently
  testable.
- **Advisory-computation-must-not-break-the-page is a real, repeated, undocumented-as-a-
  pattern idiom.** `[CONFIRMS-PLAN]`/`[NEW]` Appears 3× in this phase alone:
  `workout_log.py`'s calibration recompute (lines 74-86, 118-123), `weekly_summary.py`'s
  fatigue badge (83-97), `session_summary.py`'s fatigue badge (93-113) — all wrap an
  advisory/secondary computation in its own try/except that degrades to a safe default
  rather than failing the request. This directly implements root CLAUDE.md §1's
  "Effective sets are informational only — never auto-adjust or block user actions,"
  extended in practice to calibration and fatigue too. Worth promoting from "convention
  repeated in comments" to an actual documented pattern (e.g. a short note in
  `routes/CLAUDE.md`) so future advisory features (any Stage-4/2D-D work) follow it by
  default rather than by copying the nearest example.
- **`logger.exception(msg, e)` redundancy is widespread**, not just in
  `volume_splitter.py` (8 occurrences) — worth a repo-wide grep at synthesis time to see
  if it's worth a lint rule; `.exception()` already includes the traceback, passing `e`
  as a format arg is harmless but redundant everywhere it appears.
- **`docs/REFACTOR_PLAN.md` does not exist in this worktree** (`scan/codebase-grounding`
  branch) — it is an untracked file only present in the sibling
  `Hypertrophy-Toolbox-v3-main` working copy. Every `[CONFIRMS-PLAN]`/`[CONTRADICTS-PLAN]`
  tag in this phase was checked against that sibling-repo copy since the worktree has no
  local copy to grep. Flagging so synthesis knows the plan file needs to be copied/synced
  into this worktree (or referenced by absolute path) before Phase 23.
