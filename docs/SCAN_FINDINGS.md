# Codebase Grounding Scan — Findings

Accumulating notes from the line-by-line read. One section per phase. Each file entry
records: what it does, notable coupling, smells/risks, and anything that confirms or
contradicts `docs/REFACTOR_PLAN.md`. Cross-file themes bubble up to the "Cross-cutting"
list at the bottom, which seeds the Phase 23 recommendations.

Convention per finding: `FILE:LINE — observation` · tag `[CONFIRMS-PLAN]`,
`[CONTRADICTS-PLAN]`, `[NEW]`, or `[RISK]`.

---

## Phase 1 — Entry points & cross-cutting
Read: app.py, app_launcher.py, utils/{config,logger,request_id,errors,constants,normalization}.py,
CLAUDE.md, docs/MASTER_HANDOVER.md. (Subsystem rules deferred to their phases; per-dir CLAUDE.md read per phase.)

- **app.py:234,260 + utils/errors.py:166,224 — SHADOWED error handlers.** `[CONTRADICTS-PLAN][RISK]`
  `register_error_handlers(app)` runs at app.py:57, registering `not_found`(404) and
  `handle_unexpected_error`(Exception). Then app.py:234/260 register `handle_404`(404) and
  `handle_exception`(Exception) at module-exec time — **later registration wins in Flask**, so
  errors.py's `not_found` + `handle_unexpected_error` are effectively dead/shadowed. REFACTOR_PLAN
  WP0.1 claims *all* errors.py handlers are "live @app.errorhandler closures — do not touch"; that's
  wrong for these two. `bad_request`(400)/`unprocessable_entity`(422)/`internal_error`(500)/
  `handle_api_error`(APIError) DO remain live. → VERIFY at synthesis with a runtime probe before acting.
- **app.py:60-77 — schema init scattered across 8 calls.** `[CONFIRMS-PLAN]` db_initializer +
  6× `add_*` in database.py + `initialize_exercise_order` (routes/workout_plan) + `init_backup_tables`
  (routes/program_backup). Strongly confirms WP2.4 (single `schema_registry.run_all_initializers`).
- **app.py:204-220 — erase_data duplicates the entire 8-call init block verbatim** from startup 60-77.
  `[NEW]` Plus a hardcoded 16-table DROP list (179-196) that must stay in sync with schema. A
  `run_all_initializers()` would dedupe both; the DROP list wants a schema-owned table registry too.
- **CLAUDE.md §2 startup sequence lists 6 initializers; actual is 8** `[CONFIRMS-PLAN][DOCS]`
  (missing body_composition_snapshots, strength_calibration, fatigue_context_settings). Concrete
  instance of the WP0.5 doc-staleness item.
- **utils/errors.py:22 vs 67 — success/error response shape asymmetry.** `[NEW]` `success_response()`
  returns a **plain dict** (caller must `jsonify` — see app.py:226), while `error_response()` returns
  `(jsonify(...), status_code)`. Inconsistent contract, easy to misuse (forgot-to-jsonify). Candidate
  recommendation: make success_response also return a Flask response tuple, or document loudly.
- **get_request_id() defined twice** — utils/request_id.py:13 AND utils/errors.py:17 (identical). `[NEW]`
- **utils/constants.py:261 ANTAGONIST_PAIRS uses lowercase muscle keys** ('latissimus dorsi',
  'front-shoulder') vs canonical TitleCase MUSCLE_GROUPS ('Latissimus Dorsi'). `[RISK]` Consumers must
  normalize before lookup or superset suggestions silently miss. → verify consumer in Phase 8.
- **constants.py:11,92-93 — open TODO markers** (Front-Shoulder→deltoid collapse; Mid/Upper Back
  grouping). Not acted on; note for taxonomy recommendation.
- **utils/normalization.py — clean, well-factored** (canonical-key lookups, precomputed maps). No smell.
- **app_launcher.py — PyInstaller frozen-exe wrapper**; app.py:40-48 has the matching frozen branch.
  Packaging/distribution path exists (relevant if any refactor touches import-time side effects).
- **docs/MASTER_HANDOVER.md:67 — stale "current tip" pointer** says `284dca4`; actual `main` is
  `b5e837d` (PRs #87/#88 landed after). Changelog body mentions #87/#88, but the SHA anchor drifted. `[NEW]`

## Phase 2 — Data layer & schema
Full detail: [scan/PHASE_02.md](scan/PHASE_02.md). Highlights:
- **Schema init even more scattered than WP2.4 says** `[CONTRADICTS-PLAN]`: SIX `add_*_table()` in
  database.py:461-763 (plan says "three"), plus duplicate instance-method/module-function for
  add_progression_goals_table (database.py:443 vs 461).
- **maintenance.py:111-118 creates exercise_isolated_muscles with a DRIFTED schema** `[RISK]` —
  surrogate id PK, no FK/CASCADE vs db_initializer.py:141-150's composite-PK+CASCADE. Masked only
  because initialize_database() always runs first.
- **"Fetch unique values" has FOUR implementations** `[CONTRADICTS-PLAN]` (WP1.1 tracks two):
  ExerciseManager.fetch_unique_values (unguarded f-string, but zero external-input reachability),
  routes/workout_plan.fetch_unique_values (guarded), routes/filters.py:356 get_unique_values
  (own ALLOWED_TABLES/COLUMNS, inline SQL).
- **Filter query building duplicated 3 ways, two hand-synced allowlists** `[NEW][RISK]`:
  FilterPredicates.VALID_FILTER_FIELDS vs routes/filters ALLOWED_COLUMNS; raw-SQL builder
  filter_exercises_with_expanded_muscles (routes/filters.py:269-344) bypasses filter_predicates.
- **DatabaseHandler write-lock detection misses CTE-prefixed writes** `[RISK]` (database.py:216,292 —
  first token "WITH"); one live instance: maintenance.py REBUILD_EIM_SQL runs unlocked.

## Phase 3 — Volume & summary calculations
Full detail: [scan/PHASE_03.md](scan/PHASE_03.md). Highlights:
- **effective_sets.py:349-575 — entire second aggregation pipeline DEAD in production** `[NEW]`
  (aggregate_session_volumes, aggregate_weekly_volumes, calculate_training_frequency,
  calculate_volume_distribution, format_volume_summary) — only its own unit tests call it;
  weekly/session_summary hand-roll equivalents.
- **WP2.3 monster functions confirmed** `[CONFIRMS-PLAN]`: calculate_weekly_summary 179 lines,
  calculate_pattern_coverage 172; session_summary's helper-decomposed structure is a ready template.
- **Movement-pattern classification FORK** `[RISK]`: PatternMapping.MUSCLE_GROUP_PATTERNS (23 entries)
  vs calculate_pattern_coverage's inline 7-substring elif fallback — drift independently.
- **Null-routine semantic divergence** `[RISK]`: session_summary buckets null routine as "Unassigned";
  weekly_summary silently drops null-routine rows from frequency counting.
- **Dead code confirmed**: advanced_to_basic (test-fixture-only, matches plan), weekly_summary.STATUS_MAP,
  MovementCategory enum, HOME_BASIC_EQUIPMENT `[CONFIRMS-PLAN]`.
## Phase 4 — Fatigue, progression, log
Full detail: [scan/PHASE_04.md](scan/PHASE_04.md) (agent-read, verified). Highlights:
- **utils/fatigue.py — four concerns behind banner comments** (Phase-1 core / per-muscle / period-window /
  SFR). `[NEW]` Strong move-only split candidate, same shape as WP2.1/WP2.3, but absent from REFACTOR_PLAN.
- **Duplicated logic across fatigue.py ↔ fatigue_data.py** `[NEW]`: the "is this logged row scored" skip
  rule (adapt_logged_row vs _stimulus_from_rows) and the muscle-bar sort tie-break tuple
  (summarize_muscle_bars vs _merge_muscle_rows). Not plan-tracked.
- **progression_plan.py:39 _calculate_weight_increment** — `<20kg` branch returns 2.5 regardless of
  `is_novice` → the novice check in that branch is a no-op. `[RISK]` Protected zone: owner-decision item,
  do not touch silently.
- **body_fat.py ↔ body-composition.js manual-sync contract** with no automated parity test. `[RISK]`
  (Note: handover says PR #32 added a JS↔Python parity test — reconcile at Phase 21 when reading tests.)
- **Hardcoded catalog-adjacent lists that silently go stale** `[RISK]`: workout_log.py
  ASSISTED_BODYWEIGHT_EXERCISES (6 literal names); 6 muscle labels missing from MUSCLE_VOLUME_LANDMARKS.
- Verified live (not dead): decide_progression_target shared with strength_calibration (import at line 38);
  both fatigue_data query shapes serve different routes.
## Phase 5 — Estimator core
Full detail: [scan/PHASE_05.md](scan/PHASE_05.md). Highlights:
- **WP2.1's cohort.py grouping is wrong** `[CONTRADICTS-PLAN]`: cohort_ranges (2045) belongs with
  cohort_bars/coverage_donut (2214/2281); muscle_coverage_state (2327) is an unrelated bodymap-SVG
  concern with its own JS drift-guard test.
- **Plan's 3-module split omits two real clusters** `[NEW]`: ~740-line constants/lookup block (22-740)
  and an accuracy/coverage-guidance cluster (accuracy_band, next_high_impact_lifts, 1772-1968) — both
  would silently bloat core.py.
- **Circular-import guard verified exactly** `[CONFIRMS-PLAN]`: strength_calibration.py:30 top-level;
  profile_estimator lazy imports only at 1298 (_lookup_related_learned_calibration) and 1364
  (_lookup_learned_calibration).
- **Mid-file lift_matching re-export confirmed at 589-598** incl. underscore alias _match_direct_lift_key
  used by internal call sites — must survive the __init__ export list. `[CONFIRMS-PLAN]`
- **Cross-module duplication** `[RISK]`: strength_calibration._promotion_basis_factor (523) duplicates
  profile_estimator._load_basis_factor (1176) arithmetic exactly; linked only by docstring.

## Phase 6 — Plan generation & calibration
Full detail: [scan/PHASE_06.md](scan/PHASE_06.md). Highlights:
- **All four WP2.2 targets verified with exact spans** `[CONFIRMS-PLAN]`: _score_exercise 495-585,
  _apply_priority_muscle_boost 847-955, persist 1248-1347, generate_starter_plan 1350-1441 (thin under
  big docstring). Clean order-preserving extract-method decompositions exist.
- **persist()'s two-tier exception handling (1260-1345) must survive any split byte-identically** `[RISK]`
  — inner per-row swallow/log/continue vs outer re-raise. Should be an explicit WP2.2 no-drift item.
- **get_related_calibration_candidate (strength_calibration.py:278-384, 107 lines)** — >100-line Phase-2A
  calibration math on no WP's radar; if ever decomposed needs product-risk-reviewer gate. `[NEW]`
- **Trivial dead code for WP2.2**: _score_exercise's unused `routine` param (499); persist's unused
  loop var `i` (1270). `[NEW]`
- lift_matching keyword-ordering invariant has no dedicated test (only indirect via
  test_profile_estimator). generate_starter_plan_route confirmed thin `[CONFIRMS-PLAN]` but duplicates
  GeneratorConfig.__post_init__ validation.

## Phase 7 — Backup, exports, misc utils
Full detail: [scan/PHASE_07.md](scan/PHASE_07.md). Highlights:
- **create_backup() not atomic on the main user-facing path** `[RISK]` (program_backup.py:146-219):
  N+1 separate commits (header + each item); crash mid-loop leaves header overstating item_count.
  restore_backup 200 lines away does it right (single transaction).
- **create_auto_backup_before_erase() tested but never called in production** `[NEW]` (604) —
  /erase-data uses file-copy create_startup_backup() by design (erase drops program_backups right
  after). Documented trap for WP2.4: do not "fix."
- **Export streaming threshold is decorative** `[NEW]`: STREAMING_THRESHOLD/should_use_streaming/
  estimate_export_size/EXPORT_BATCH_SIZE implemented + unit-tested but never consulted by any route;
  client `type` param chooses the path.
- **WP0.3 re-verified: zero code importers of utils/__init__ facade** `[CONFIRMS-PLAN]`.
- **WP2.4 wiring evidence** `[CONFIRMS-PLAN]`: conftest already calls utils initialize_backup_tables
  directly; e2e/scripts/prepare_visual_db.py is the one outlier on the routes wrapper.
- Stray debug: unconditional time.sleep(0.5) in create_excel_workbook cleanup — +500ms per Excel export.
## Phase 8 — Routes: workout_plan + filters
Full detail: [scan/PHASE_08.md](scan/PHASE_08.md). Highlights:
- **WP1.1 strongly confirmed** `[CONFIRMS-PLAN]`: fetch_unique_values (workout_plan.py:20-101) and
  get_unique_values (filters.py:356-442) are near-duplicate ~80-line whitelist lookups; plus
  workout_plan.py:12 imports ALLOWED_COLUMNS/validate_column_name cross-blueprint from routes.filters
  (routes→routes boundary violation).
- **WP1.2/1.3 are mechanical moves** `[CONFIRMS-PLAN]`: replace/superset logic already lives in
  module-level helpers (_fetch_current_exercise_details, _apply_superset_link, _find_antagonist_pairings…)
  — wrong file, direct DatabaseHandler SQL, but extractable as-is.
- **Validation gap, not just doc drift** `[NEW][RISK]`: routes.md's claimed "sets 1-20, reps 1-100,
  weight ≥0, RIR 0-10" bounds DO NOT EXIST in the route; add_exercise enforces narrower/different rules,
  update_exercise enforces NONE (negative weight/RIR, inverted rep ranges accepted).
- **Falsy-check bug family** `[RISK]`: exercise_manager.py:32 `if not all([...weight])` rejects
  weight==0 (bodyweight exercises); same pattern rejects order=0 in remove_exercise/update_exercise_order.
- **5 route candidates with zero frontend callers** `[NEW]`: /get_routine_options, /get_user_selection,
  /get_exercise_details/<id>, /get_filtered_exercises, /get_unique_values/<table>/<column> — tested but
  superseded. Dead-code candidates for a Phase-0-style WP.
- **ANTAGONIST_PAIRS casing watch item CLOSED — no bug** (lowercased canonical values verified end-to-end).
## Phase 9 — Routes: profile / exports / progression
Full detail: [scan/PHASE_09.md](scan/PHASE_09.md). Highlights:
- **exports.py is the real fat-route file** `[CONFIRMS-PLAN]`: DB_TO_ADVANCED_MUSCLE/WORKOUT_PLAN_COLUMNS/
  transform_muscle_value/reorder_and_rename_columns (22-227), _build_export_query (276-326),
  _fetch_all_sheets (329-400) — business logic with no home in export_utils (which is purely mechanical).
- **exports.py:233,278 imports column_exists/table_exists from routes.workout_plan** — exact WP2.4
  cross-route coupling, call sites pinned. `[CONFIRMS-PLAN]`
- **export_to_workout_log (473-541)** `[NEW][RISK]`: zero utils delegation, per-row N+1 dupe-check+insert
  loop; _recalculate_exercise_order mutates user_selection as a side effect of a nominally read-only GET.
- **user_profile.py handlers are actually thin** `[CONTRADICTS-PLAN, narrow]` — fatness is ~230 lines of
  pre-route static data + one view-model builder, not fat handlers. Plan's "audit for extraction" may
  find little to extract.
- **Fatigue-context advisory guarantee verified end-to-end** at both attach points (user_profile.py:574-588,
  progression_plan.py:136-200): estimate first, sibling key only, exception-swallowed. `[CONFIRMS design]`

## Phase 10 — Routes: remainder
Full detail: [scan/PHASE_10.md](scan/PHASE_10.md). Highlights:
- **error.html contract bug at 6 of 7 call sites** `[NEW][RISK]`: routes pass message= but template reads
  error_message/error_title/error_code → real 500s render near-blank. Only fatigue.py:28 is correct.
- **DB-work-in-routes is a 3-file pattern the plan misses** `[CONTRADICTS-PLAN]`: body_composition.py
  (full CRUD), volume_splitter.py (history/get/delete), workout_log.py (all mutations) — Phase-1
  slim-down names only workout_plan/filters (+user_profile/exports audits).
- **routes/fatigue.py:26 calls is_xhr_request(request) but it takes zero args** `[RISK]` — real TypeError,
  fires only on the already-broken exception path.
- **volume_splitter.py holds domain logic** `[NEW]`: muscle-range defaults/sanitization, a second
  undocumented volume-classification scheme, hand-rolled Excel export duplicating create_excel_workbook.
- **WP2.4 wrapper confirmed**: program_backup.py:226-234 pure wrapper; caller map pinned (prepare_visual_db
  → routes wrapper; conftest → utils direct). `[CONFIRMS-PLAN]`
## Phase 11 — Templates
Full detail: [scan/PHASE_11.md](scan/PHASE_11.md) (complete; agent killed pre-summary). Highlights:
- **`<main>` landmark inconsistent across all templates** `[NEW][RISK]`: base.html:219 uses a plain div;
  5 templates nest their own `<main>`; 7 pages have NO main landmark → real a11y gap, unscoped by any WP.
- **Three coexisting "server data → JS" conventions** `[NEW]`: JSON script tag (user_profile.html:280),
  plain data-* attrs (body_composition.html:10-15), tojson-in-data-* (volume_splitter.html:25-29).
- Query-string cache-buster on static assets noted as a cheap perf win (replace with content hash).
## Phase 12 — JS: workout-plan cluster
## Phase 13 — JS: profile / muscle-map / media
Full detail: [scan/PHASE_13.md](scan/PHASE_13.md) (complete). Highlights:
- **PR #87 MuscleMap unification verified clean at JS level** `[CONFIRMS-PLAN]`: no dead workout-cool/
  react-body-highlighter code in muscle-selector.js/bodymap-svg.js; leftovers are comment/test-docstring
  only (test_muscle_selector_mapping.py:151 stale "workout-cool" naming — cosmetic).
- **muscle-selector region→leaf decision table is Python-ported in tests** (good drift-guard practice,
  TestRegionVisualState) — pattern worth replicating for body_fat↔body-composition.js.
- **user-profile.js:1100-1154 vs 1187-1234 — duplicated optimistic-update pattern** `[NEW]` for
  settings toggles; fold into any future user-profile.js split.

## Phase 14 — JS: backup / volume-splitter
Full detail: [scan/PHASE_14.md](scan/PHASE_14.md) (complete). Highlights:
- **WP3.5 fetch counts exactly right (7 + 2)** `[CONFIRMS-PLAN]` — BUT volume-splitter.js:16-90 is a
  ~50-line parallel reimplementation of apiFetch's envelope/error logic that should be deleted wholesale,
  not call-site-swapped. Amend WP3.5 scope. `[CONTRADICTS-PLAN, scope]`
- **program-backup.js:104-162 showAutoBackupBanner — fully-built orphaned feature** `[NEW]`: defined,
  imported into app.js, window-assigned, ZERO call sites; welcome.html erase flow never calls it.
  Wire it up or delete (~60 lines + wiring).
- **Silent failure in volume-splitter's highest-frequency call** `[RISK]`; backup-center.js vs
  program-backup.js refresh interplay dismisses in-flight restore confirmations (UX regression noted).
## Phase 15 — JS: log / filters / dropdowns
## Phase 16 — JS: progression / body-comp / tables / summary
## Phase 17 — JS: app infra & shared
Full detail: [scan/PHASE_17.md](scan/PHASE_17.md) (complete). Highlights:
- **app.js:99,111,158,162 — toast severity bug, reachable in production** `[NEW][RISK]`: four call
  sites pass 'warning'/'error' as toast.js's legacy boolean 2nd arg (toast.js:17 coerces non-boolean
  → false) so warnings AND errors render as green success toasts. Behavior-changing fix → standalone
  bug ticket, not a refactor WP.
- **fetch-wrapper.js has ZERO blob/binary support** `[CONFIRMS-PLAN]` — confirms WP3.5's carve-out:
  export/download raw fetches MUST stay raw (or the wrapper needs a blob mode first).
- toast.js dual API (legacy positional + object-style) is the root enabler of the severity bug;
  full export-surface documentation gap noted for any Phase-3 work.
## Phase 18 — CSS part 1
## Phase 19 — CSS part 2
## Phase 20 — CSS part 3
## Phase 21 — Tests: pytest suite
## Phase 22 — E2E specs + build/CI config

---

## Cross-cutting themes (seeds Phase 23 recommendations)
- **Schema-init duplication** — startup (app.py:60-77) and erase_data (204-220) repeat the same 8-call
  block; erase also hardcodes a DROP-table list; SIX add_* fns not three (P2); maintenance.py carries a
  drifted duplicate table definition (P2). WP2.4's registry should own all of it + a table list. (P1,P2)
- **Duplicated business logic across module pairs** — fatigue.py↔fatigue_data.py (scored-row rule,
  tie-break) (P4); _promotion_basis_factor↔_load_basis_factor exact arithmetic (P5,P6);
  weekly_summary↔session_summary hand-rolled aggregation + dead effective_sets pipeline that was meant
  to unify them (P3); 4× fetch-unique-values (P2,P8); volume_splitter hand-rolled Excel export (P10).
- **Validation is inconsistent and partially absent** — routes.md's documented bounds don't exist;
  update_exercise validates nothing; falsy-check rejects weight==0/order==0 (P8). error.html contract
  broken at 6/7 call sites (P10). is_xhr_request(request) TypeError (P10).
- **Dead code clusters** — effective_sets second pipeline (P3), 5 unreferenced route endpoints (P8),
  create_auto_backup_before_erase (P7, by-design trap), STATUS_MAP/MovementCategory/HOME_BASIC_EQUIPMENT
  (P3, confirms WP0.2), decorative streaming threshold (P7).
- **Classification forks that drift** — movement-pattern mapping vs inline elif fallback (P3);
  null-routine semantics diverge weekly vs session (P3); two hand-synced filter allowlists (P2).
- **Reliability** — create_backup non-atomic N+1 commits (P7); CTE writes bypass write-lock detection
  (P2); export GET mutates exercise_order (P9); sleep(0.5) in every Excel export (P7).
- **Plan-vs-reality gaps** — WP0.1 shadowed handlers (P1); WP2.1 cohort grouping wrong + 2 omitted
  clusters (P5); DB-in-routes is 3 files beyond plan scope (P10); user_profile handlers already thin (P9).
- **Response-contract asymmetry** — success_response returns dict, error_response returns tuple (P1).
- **Doc staleness** — CLAUDE.md startup 6 vs 8 (P1); handover SHA pointer (P1); routes.md validation
  claims (P8); REFACTOR_PLAN.md untracked → invisible in worktrees (P10, now copied in).
- **Duplicate helpers** — get_request_id ×2 (P1).
