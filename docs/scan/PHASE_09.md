# Phase 9 — Routes: profile / exports / progression

Line-by-line read of `routes/user_profile.py` (877), `routes/exports.py` (673),
`routes/progression_plan.py` (393), plus `.claude/rules/routes.md` and
`routes/CLAUDE.md` for context. Cross-checked against `docs/REFACTOR_PLAN.md`
v2 (council-reviewed), specifically the Phase-1 routes slim-down WPs and the
instruction: *"After WP1.3, audit `routes/user_profile.py` and
`routes/exports.py` for the same pattern; if violations are found, file one
follow-up WP each."* This phase is that audit.

---

## routes/user_profile.py (877 lines)

**Verdict: route *handlers* are thin; the file is fat because of ~230 lines of
module-level static data + view-model assembly helpers sitting ahead of the
first route.**

- Lines 68–230: `REFERENCE_LIFT_GROUPS` (13 muscle groups × lift tuples, ~90
  lines), `REFERENCE_LIFT_LABELS` (derived dict), `REFERENCE_LIFT_IMAGE_PATHS`
  (~65-entry dict mapping lift_key → static image path). This is presentation
  data, not routing logic, and has no dependency on Flask (`request`,
  `jsonify`, etc.). It naturally belongs beside `KEY_LIFTS` /
  `DUMBBELL_LIFT_KEYS` in `utils/profile_estimator.py`, which the route already
  imports from. **[NEW]** — low urgency; `REFERENCE_LIFT_LABELS` is on the
  plan's WP0.2 do-NOT-delete "real refs" list, so it's alive and this is a
  pure-move candidate only, not a correctness issue.
- `_load_latest_body_composition()` (`user_profile.py:286-322`): runs a raw
  SQL query, then applies Navy-over-BMI selection + `ace_category()`
  band-lookup business logic directly in the route file. 37 lines. **[NEW]**
  — candidate for `utils/body_composition.py` (Phase 10 territory; flagging
  here since it's read in this phase and blocks a clean "thin route" claim).
- `_load_profile_context()` (`user_profile.py:325-384`, 60 lines) and
  `_build_profile_insights()` (`user_profile.py:408-458`, 51 lines): these are
  view-model builders that assemble reference-lift groups, insights, cohort
  bars, coverage donuts, etc. They call plenty of `utils.profile_estimator`
  functions correctly (no calculation logic duplicated here — confirmed by
  spot-checking `accuracy_band`, `cohort_ranges`, `cohort_bars`,
  `coverage_donut`, `muscle_coverage_state`, `next_high_impact_lifts`,
  `replaced_anchor_lifts`, `cold_start_anchor_lifts` are all imported, not
  reimplemented). The violation is architectural placement, not duplicated
  math: this is "build the template context" logic, which per `routes/
  CLAUDE.md` should be a thin call into a utils function returning a ready
  context dict. **[NEW]** — extraction candidate (e.g.
  `utils/profile_estimator.build_profile_page_context(db)`), but it is a
  single-consumer function (only `GET /user_profile` calls it), so the ROI is
  lower than the exports.py findings below.
- `_classify_experience_label()` (387-405): pure function, no DB/Flask
  coupling — trivially movable to utils but harmless where it sits.
- **Route handlers themselves are thin** (`user_profile.py:461-877`, 14
  routes). Each one: parses/validates input via the small `_nullable_*`
  helpers, opens `DatabaseHandler`, delegates to `utils.strength_calibration`
  / `utils.fatigue_context` / `utils.profile_estimator` / `utils.database`,
  and returns via `success_response()`/`error_response()`. No SQL, no
  calculation logic in any handler body. This matches the routes-layer
  contract in `routes/CLAUDE.md` ("HTTP layer... no business logic, no direct
  DB access"). **[CONTRADICTS-PLAN]** in the narrow sense that the plan
  frames `user_profile.py` as a fat-route audit target on the same footing as
  `workout_plan.py`'s `replace_exercise`/superset functions — it isn't. The
  actual fat surface is pre-route static data + one view-model builder, not
  oversized/logic-heavy handlers. No function in the file exceeds 100 lines.
- `GET /api/user_profile/estimate` (`user_profile.py:574-588`): **[CONFIRMS
  design]** — matches the documented Phase 2D-A/2D-B advisory-layer contract
  exactly. `estimate_for_exercise(exercise, db=db)` runs first and its return
  value is what gets passed to `jsonify(success_response(data=estimate))`;
  `attach_fatigue_context(estimate, exercise, db=db)` runs *after* and mutates
  `estimate` in place, only ever adding a `fatigue_context` key (verified in
  `utils/fatigue_context.py:368-389`: the function wraps
  `build_fatigue_context()` in its own try/except, swallows all exceptions,
  and only sets `estimate["fatigue_context"] = block` when `block is not
  None`). It cannot change `estimate`'s existing keys (number/source/reason/
  trace) and cannot raise. This is exactly the "additive, default-off,
  never touch the estimate" guarantee described in the docstring and in
  `docs/REFACTOR_PLAN.md` protected-zone rule 2 ("locked 2D-A advisory copy").
  **Do not disturb this call ordering in any future refactor of this route.**

## routes/exports.py (673 lines)

**Verdict: this is the real fat-route file in this phase — misplaced
business logic, raw SQL embedded directly in handlers, and a live
route-to-route import that the plan already knows about (WP2.4).**

- `column_exists` / `table_exists` cross-import (`exports.py:233`, `278`:
  `from routes.workout_plan import column_exists`): `routes/exports.py`
  imports helpers *from another route module*, not from `utils`. This breaks
  the stated module-boundary rule in root `CLAUDE.md` §2 ("Routes import from
  utils; utils never import from routes") in spirit — routes importing routes
  is the same class of coupling, just not literally the forbidden direction.
  **[CONFIRMS-PLAN]** — this is precisely what `docs/REFACTOR_PLAN.md` WP2.4
  already targets: *"Move `initialize_exercise_order` AND its helpers
  `column_exists` / `table_exists` into utils; keep deprecation re-exports in
  `routes/workout_plan.py` (helpers are imported by `routes/exports.py`,
  `tests/test_exports.py`, `tests/test_program_backup.py`)."* Confirmed by
  reading both sides: `routes/workout_plan.py:620` defines `column_exists`,
  `:626` defines `table_exists`; `routes/exports.py` uses both at
  `:233-234`, `:247-249`, `:278-280`. No new finding needed — just a direct
  confirmation with exact call sites for whoever executes WP2.4.
- `DB_TO_ADVANCED_MUSCLE` (`exports.py:22-77`, 56-entry dict),
  `WORKOUT_PLAN_COLUMNS` (`exports.py:84-157`, column order + two display-name
  maps), `transform_muscle_value()` (`170-187`) and
  `reorder_and_rename_columns()` (`190-227`, 38 lines): this is genuine
  export-formatting business logic — column reordering, display-name
  remapping, and a simple-to-advanced muscle-name vocabulary translation.
  Checked `utils/export_utils.py` (458 lines) for contrast: it only contains
  generic, content-agnostic mechanics — `sanitize_filename()`,
  `generate_timestamped_filename()`, `create_excel_workbook()`,
  `stream_excel_response()`, `MAX_EXPORT_ROWS`. None of it knows about
  `primary_muscle_group` or workout-plan column names. So the
  domain-specific transform logic in `exports.py` has no analog anywhere in
  utils — it was never extracted. **[CONFIRMS-PLAN]** (matches the "audit
  exports.py for the same pattern" instruction; this is the clearest hit).
  Candidate home: a new `utils/export_transforms.py` or add to
  `utils/export_utils.py` directly — either keeps `routes/exports.py` to
  request handling + wiring.
- `_recalculate_exercise_order(db)` (`exports.py:231-273`, 43 lines): DB
  read-then-batch-write business logic (detects degenerate `exercise_order`
  state, rebuilds it) that duplicates a purpose overlapping
  `initialize_exercise_order()` in `routes/workout_plan.py`. This runs on
  *every* `GET /export_to_excel` call, not just at startup — a repeated,
  non-trivial write path hidden inside an export route. **[RISK]** — this is
  side-effecting (mutates `user_selection.exercise_order`) as a side effect of
  what looks like a read-only export action; worth flagging for whoever picks
  up WP2.4 or a follow-up, since consolidating schema/order initialization
  (per WP2.4) should also ask whether an export request is the right trigger
  for a data-repair pass.
- `_build_export_query(db)` (`exports.py:276-326`, 51 lines): builds one of
  three hand-written multi-line SQL strings (with a CTE) depending on which
  optional columns exist. Real query-construction logic living in the route
  file. **[CONFIRMS-PLAN]** — same "business logic belongs in utils" pattern.
- `_fetch_all_sheets(db, view_mode)` (`exports.py:329-400`, 72 lines):
  orchestrates 7 sheets (Workout Plan, Workout Log, Weekly Summary, Session
  Summary, Progression Goals, Categories, Isolated Muscles), 3 of which are
  raw inline SQL (`workout_log`, session-summary join, `progression_goals`)
  right in the route module rather than being pulled from `utils/database.py`
  or a dedicated query module. Not over 100 lines, but it's the densest
  concentration of DB-query logic in a route file across this phase.
  **[CONFIRMS-PLAN]**.
- `export_to_workout_log()` (`exports.py:473-541`, 68 lines): **no
  delegation to utils at all** — defines its own `query`/`insert_query`
  strings, opens `DatabaseHandler`, and loops row-by-row doing a per-row
  `SELECT` duplicate-check followed by a per-row `INSERT` (lines 505-521,
  classic N+1: one dupe-check query + one insert query per plan row, not
  batched). Contrast with `_recalculate_exercise_order`'s explicit comment
  (`exports.py:259-260`) about a prior N+1→batch fix elsewhere in the same
  file — this handler was not given the same treatment. **[NEW / RISK]** —
  functionally correct today, but it's both a performance smell (N+1 against
  `workout_log`) and the single most "fat" individual handler in the phase:
  100% inline business logic, zero utils delegation.
- `export_large_dataset()` (`exports.py:594-673`, 80 lines): nested
  `data_generator()` closure containing three more raw SQL blocks
  (workout_log, session_summary, weekly/categories), plus a
  `type in ['all', 'workout_log']` branch. Same pattern as `_fetch_all_sheets`
  but for the streaming path. **[CONFIRMS-PLAN]** with a caveat: the task
  brief anticipated "the export streaming/blob path may legitimately keep raw
  handling" — that caveat applies to the *response transport* (generator +
  `stream_excel_response`, which is correctly using `utils/export_utils.py`),
  not to the SQL query bodies feeding it. The streaming mechanics are clean;
  the query content inside the generator is the same misplaced-logic pattern
  as everywhere else in this file.
- `export_to_excel()` (`exports.py:403-471`, 68 lines) has a nested
  try/except (`438-462`) whose only job is to log then re-raise
  (`except Exception as create_error: logger.exception(...); raise`) before
  being caught again by the outer handler's `except Exception as e` two lines
  later. **[NEW]** — harmless but redundant; the outer handler already logs
  via `logger.exception(f"Error exporting to Excel: {e}")`, so the inner
  block produces a duplicate log line for the same exception. Minor,
  unslop-tier cleanup, not worth its own WP.
- Dead comment: `exports.py:229` — `# Removed verbose before_request logging
  - using logger only` — a stray comment about code that no longer exists,
  with nothing left to describe. **[NEW]** — trivial, bundle into any future
  touch of this file.
- **Response-contract consistency**: `export_to_workout_log()` (`:525-527`,
  `:531-533`) and `export_summary()` return `success_response(...)` bare,
  without `jsonify()`. Checked `utils/errors.py:22-44` — `success_response()`
  returns a plain `dict`, not a Flask response; Flask auto-JSONifies dicts
  returned from a view function, so this works, but it's inconsistent with
  every success path in `user_profile.py` and `progression_plan.py`, which
  always wrap with `jsonify(success_response(...))`. `error_response()` is
  correctly never re-wrapped anywhere (it already returns
  `(jsonify(...), status_code)` per `utils/errors.py:117`). **[NEW]** —
  cosmetic/consistency only, not a contract violation (`routes/routes.md`'s
  response-contract shapes are identical either way), but worth normalizing
  if `exports.py` gets touched for the WP1-style extraction above.
- `export_to_excel()` / `export_summary()` correctly return the raw
  `create_excel_workbook()` / `stream_excel_response()` Flask `Response`
  objects rather than routing them through `success_response()` — this is the
  legitimate exception called out in the task brief and matches
  `routes/routes.md`'s silence on binary/streaming payloads. No finding here.

## routes/progression_plan.py (393 lines)

**Verdict: thin and clean — the best-behaved file of the three.**

- Small local validation helpers (`_get_json_payload`, `_require_text_field`,
  `_normalize_is_novice`, `_parse_numeric_goal_value`,
  `_normalize_progression_goal_payload`) are all pure, small (≤32 lines each),
  and stay in the route file appropriately per `routes/routes.md`'s "Routes
  validate bounds before calling utils" convention — comparable in spirit to
  `routes/workout_plan.py`'s inline sets/reps/weight/RIR bounds pattern
  referenced in `.claude/rules/routes.md:61`.
- All actual progression math (`get_exercise_history`,
  `get_exercise_plan_defaults`, `generate_progression_suggestions`,
  `generate_plan_based_progression_suggestions`, `save_progression_goal`)
  lives in `utils/progression_plan.py` and is only ever called, never
  reimplemented, from this route file. No SQL string is hand-built for
  progression logic itself (the raw SQL in `progression_plan.py:109-114`,
  `118-123`, `266-267`, `273-274`, `289-290`, `296-297` are simple
  single-table `SELECT`/`UPDATE`/`DELETE` by primary key or a two-column
  `DISTINCT` — not business logic, just direct CRUD, consistent with how
  `routes/workout_log.py`-style routes are expected to look per
  `routes/CLAUDE.md`).
- `get_current_value()` (`progression_plan.py:306-393`, 88 lines) is the
  largest function in the file and the closest thing to a borderline case:
  it branches on `goal_type` to pick one of three hand-written SQL strings,
  then falls back to `get_exercise_plan_defaults()` if the DB value is
  `None`. It's under 100 lines and every branch is a simple parameterized
  query, but the three near-identical `SELECT ... WHERE exercise = ?`
  strings plus the fallback-key mapping (`plan_value_keys` dict,
  `:360-364`) could reasonably become a single
  `utils.progression_plan.get_current_tracked_value(exercise, goal_type,
  db=db)` for symmetry with the other four progression functions that are
  already in utils. **[NEW]** — mild, optional; not a violation, just an
  inconsistency (four of five progression queries are behind a utils
  function, this one isn't).
- `POST /get_exercise_suggestions` (`progression_plan.py:136-200`): **matches
  the Phase 2D-B advisory contract precisely.** `suggestions` is computed
  first (from `generate_progression_suggestions` or
  `generate_plan_based_progression_suggestions`, chosen by whether
  `get_exercise_history(exercise)` is empty) and placed into
  `payload = success_response(data=suggestions)` — `data` never becomes
  anything but the suggestions list. The fatigue-context attach
  (`:173-184`) runs afterward in its own try/except, calls
  `build_fatigue_context_batch([exercise], db=db)` (verified in
  `utils/fatigue_context.py:296-365`: settings-gated, returns `{}` when the
  advisory toggle is off, per-exercise blocks are the same shape as
  `attach_fatigue_context`'s single-exercise path via the shared
  `_block_from_page`/`_neutral_block` builders), and only ever does
  `payload["fatigue_context"] = block` as a **sibling top-level key**, never
  touching `payload["data"]`. Confirms the "byte-for-byte unchanged when
  disabled, additive only when enabled" guarantee. **[CONFIRMS-PLAN]**
  (protected-zone rule 2 in `docs/REFACTOR_PLAN.md`).
- **[NEW / minor inconsistency]**: this route wraps its own
  try/except around the batch fatigue-context call
  (`progression_plan.py:173-183`), duplicating the same
  catch-log-and-continue guard that `attach_fatigue_context()` already
  provides internally for the single-exercise case used by
  `routes/user_profile.py`. There's no bug — `build_fatigue_context_batch`
  has no equivalent "safe" wrapper of its own, so the route-level try/except
  is the only guard for it today — but it means the "advisory layer can
  never break the caller" guarantee is enforced two different ways
  (wrapper function vs. inline try/except at the call site) depending on
  which route you're in. Worth a one-line note if `fatigue_context.py` is
  ever touched: consider a `build_fatigue_context_batch`-safe wrapper for
  symmetry, not urgent.
- `save_goal()` (`progression_plan.py:203-258`) branches on
  `request.is_json` vs. form POST and on `is_xhr_request()` for the response
  shape (JSON vs. redirect) — this is legitimate content-negotiation, not
  business logic, and mirrors the documented `is_xhr_request()` helper usage
  pattern from `utils/errors.py:47-64`.
- No function in this file exceeds 100 lines. No dead code found. No
  route-to-route imports. No SQL-injection surface (all queries are
  parameterized `?` placeholders per `.claude/rules/routes.md`'s prevention
  layer, though none of these queries interpolate a caller-supplied column
  name, so the `validate_column_name()` guard doesn't apply here).

---

## Cross-cutting seeds

1. **exports.py is the confirmed follow-up-WP target; user_profile.py mostly
   isn't.** The plan's blanket "audit user_profile.py and exports.py for the
   same [fat-route] pattern" turns out asymmetric: `exports.py` has five
   separate misplaced-logic sites (column/muscle-name transform data, query
   builders, `_fetch_all_sheets`, `export_to_workout_log`'s inline N+1,
   `export_large_dataset`'s inline SQL) that all belong in
   utils — a real "WP1.4-style" extraction candidate
   (`utils/export_transforms.py` for the display/column logic +
   folding query-building into `utils/export_utils.py` or a new
   `utils/export_data.py`). `user_profile.py`'s handlers are already thin;
   its only extraction candidates are pre-route static data and one
   single-consumer view-model builder, both lower priority.
2. **WP2.4's `column_exists`/`table_exists` migration is independently
   confirmed** with exact call sites in `routes/exports.py:233-234,
   247-249, 278-280` — no new investigation needed when that WP is executed,
   just wire the re-export as planned.
3. **Duplicate JSON-payload-parsing helpers across route files.** This
   phase's `user_profile.py:233-238` (`_get_json_payload`) and
   `progression_plan.py:22-27` (`_get_json_payload`) are near-identical
   (`request.get_json(silent=True)` → `None`/non-dict → `ValueError`), and a
   third near-twin exists in `routes/body_composition.py:36`
   (Phase 10, confirmed by grep, not fully read this phase). None of the
   three route files import a shared helper — each hand-rolls its own. Not
   in the current plan's WP list; worth a small dedicated WP
   (`utils/route_helpers.py` or similar) if Phase 1 gets a follow-up round,
   scoped across whichever route files actually have it once Phase 10 is
   also read.
4. **The Phase 2D-A/2D-B advisory-layer contract is followed correctly and
   consistently at both of its attachment points** (`user_profile.py`'s
   single-exercise `attach_fatigue_context` and `progression_plan.py`'s
   batch `build_fatigue_context_batch`) — verified by reading
   `utils/fatigue_context.py` in full, not just trusting the route-level
   comments. Both call sites run the estimate/suggestion computation first,
   attach the advisory block as a strictly additive, exception-swallowed,
   sibling key second, and never touch the primary payload. Safe to treat
   as settled/protected in any future refactor of these two files.
5. **No function in any of the three files exceeds 100 lines.** The
   "functions >100 lines" watch item from the task brief did not surface a
   hit in this phase — the biggest is `_fetch_all_sheets` at 72 lines and
   `export_large_dataset` at 80. Fatness in this phase is about logic
   *placement* (routes doing utils' job) and *data volume* (large static
   dicts/lists at module scope), not oversized functions.
