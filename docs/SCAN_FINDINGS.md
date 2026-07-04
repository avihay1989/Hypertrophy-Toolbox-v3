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
Full detail: [scan/PHASE_12.md](scan/PHASE_12.md). Highlights:
- **Toast severity bug re-confirmed at app.js:99,111,158,162** (generateStarterPlan paths);
  workout-plan.js/exercises.js themselves clean of the pattern. `[RISK]`
- **TWO full duplicate "Add Exercise" flows** `[NEW]`: exercises.js addExercise/sendExerciseData/
  resetFormFields/validateExerciseValues are dead-but-window-assigned (survives a rule-8 grep!);
  workout-plan.js has the parallel, actually-wired versions with different bodies.
- **WP3.4's 4-leaf split has no home for ~660 lines (~27%)** `[CONTRADICTS-PLAN]`: AMRAP/EMOM
  execution-style picker (~220), swap/replace (~140), Add-Exercise form cluster (~300).
- **table.js/supersets.js not cleanly separable** `[CONTRADICTS-PLAN]`: superset color/adjacency
  logic inlined in updateWorkoutPlanTable row loop + DnD; 4 shared mutable module-state vars cross
  the proposed boundary (selectedExerciseIds, supersetColorMap, allExercisesCache,
  currentRoutineTabFilter) — plan names no shared-state module.
- **Event-listener leak confirmed** `[RISK]`: showExecutionStylePicker (workout-plan.js:383-390) —
  3 of 4 close paths never remove the document outside-click listener.
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
Full detail: [scan/PHASE_15.md](scan/PHASE_15.md). Highlights:
- **Double-submission bug on every scored-value edit** `[RISK]`: workout_log.html inline onchange
  races ui-handlers.js's 500ms-debounced input handler — two identical /update_workout_log POSTs,
  each re-running server calibration recompute + toast.
- **Progression-badge correctness bug from TRIPLICATED logic** `[RISK]`: handleDateChange
  (workout-log.js:801-807) omits the isWeightProgression() assisted-bodyweight special case that the
  other two copies (:388-395, :580-586) apply.
- **~96 lines front-to-back dead** `[NEW]` (workout-log.js:595-690): selectors that don't exist in
  the template; POST to /filter_workout_logs — a route that doesn't exist anywhere.
- **Validation is enforced NOWHERE in the update path** `[RISK]`: client validateScoredValue is
  cosmetic (toggles CSS, never blocks save); server update_workout_log does zero range/type checks.
  Confirms + extends the Phase-8 server-side gap.
- **workout-dropdowns.js _cleanupHandler built but never invoked** `[NEW]` — real per-session
  listener/popover leak on workout_plan. Also: 3rd/4th hand-synced taxonomy lists (muscle names in
  filter-view-mode.js vs constants.py; routine names in routine-cascade.js vs plan_generator.py);
  dead showToast import in routine-cascade.js; no toast legacy-arg misuse in these four files.
## Phase 16 — JS: progression / body-comp / tables / summary
Full detail: [scan/PHASE_16.md](scan/PHASE_16.md). Highlights:
- **charts.js fully dead in production** `[NEW]`: reachable via initializeCharts() but no template
  creates [data-chart] and Chart.js is never loaded (Chart global doesn't exist).
- **summary.js exports are permanent no-ops** `[NEW]`: self-guard pageHasOwnUpdater() is always true
  (templates define their own window-scoped updaters). The ~395 inline JS lines WP3.2 targets are the
  ONLY live implementation, not a duplicate — extraction is a move, not a merge.
- **Body-comp parity gap quantified** `[RISK]`: e2e parity test covers only compute_navy, male, one
  input; compute_bmi/ace_category/jackson_pollock_ideal have ZERO parity assertions (4 functions
  mandated byte-identical by body_fat.py docstring — currently verified identical by read).
- **progression-plan.js:523-573 dead AND broken** `[NEW]`: createSuggestionCard/openGoalModal no
  callers; openGoalModal calls getCurrentValue() which doesn't exist anywhere in the repo.
- **filters.js: exactly 1 raw fetch (line 222)** `[CONFIRMS-PLAN]`. table-responsiveness.js has ~3
  runtime-unreachable exports — a JS dead-code category (call-graph-reachable, runtime-unreachable)
  that Phase 0 (Python-only) doesn't cover.
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
Full detail: [scan/PHASE_18.md](scan/PHASE_18.md). Highlights:
- **@layer cascade trap** `[RISK]`: no explicit @layer order statement anywhere; components.css and
  pages-workout-plan.css both open `@layer workout {}` (silently merged by load order); ~100% of
  in-layer rules carry !important — a workaround for losing to unlayered rules. Removing !important
  without first declaring layer order reintroduces cascade bugs. WP4.2 prerequisite.
- **~600 lines of MISFILED page content in pages-workout-plan.css** `[NEW]`: .workout-log-frame
  (~155, belongs to Log) + .summary-* families (~440, belongs to Summaries), both ALSO duplicated in
  components.css. WP4.3 needs a "relocate" step, not just "hoist shared".
- **Bimodal token adoption** `[NEW]`: new sections (superset, fatigue-context, Calm Glass) tokenized;
  ~70% older code hardcodes literals even where a same-file token exists.
- **Two overlapping spacing-token vocabularies in tokens.css itself** (--space-* legacy vs --s-* Calm
  Glass, same values) `[RISK]` — WP4.1 merge hazard, resolve first.
- **Dead**: .legend-mode-badge, ADVANCED MODE grouped-legend block, .view-toggle-group (~60 lines).

## Phase 20 — CSS part 3 (+ SCSS pipeline)
Full detail: [scan/PHASE_20.md](scan/PHASE_20.md). Highlights:
- **bootstrap.custom.min.css is NOT pure Bootstrap** `[RISK]`: silently bundles compiled .fatigue-*
  and .vp-*/.volume-active-summary from SCSS — invisible to static/css-only audits; name-collides
  with unrelated .volume-* in pages-volume-splitter.css.
- **navbar.css = three overlapping live redesign generations** `[CONTRADICTS-PLAN]` (token @layer +
  hardcoded !important legacy + newer :where() Calm Glass) — much harder than generic WP4.2 treatment.
- **theme-dark.css needs per-rule triage, not bulk deletion** `[CONTRADICTS-PLAN]`: legacy hex layer
  (incl. a pastel duplicate whose light twin lives in another file) + newer variable-remap layer that
  only partially supersedes it.
- **Four template-verified dead blocks** `[NEW]`: volume-splitter 3-col layout; progression's ~75-line
  dropdown section that targets workout_plan.html elements; base.css .loading-spinner/.fade-enter*;
  base.css .skeleton fully shadowed by motion.css.
- **Six siloed local token namespaces** (--wl-*, --nav-*, --bc-*, --backup-*, --volume-*, --fatigue-*)
  none referencing tokens.css `[NEW]` — the real duplication is one level above hardcoded colors;
  WP4.1's framing undercounts it.
## Phase 19 — CSS part 2
Full detail: [scan/PHASE_19.md](scan/PHASE_19.md). Highlights:
- **weekly-summary ↔ session-summary CSS 99.1% byte-identical (diff-confirmed)** `[NEW]`; the same
  ~1350-line frame block is copy-pasted into pages-workout-log.css (3rd copy) and
  pages-workout-plan.css (4th). WP4.3's dedupe payoff is far larger than the plan sized.
- **base.html loads tokens.css AFTER layout/components/navbar/a11y/route CSS** `[CONTRADICTS-PLAN]`
  (frontend.md states the opposite order) — latent cascade-inversion risk for token overrides.
- **pages-workout-log.css is the debt champion** `[RISK]`: 375 !important, 351 raw rgba(), 217
  dark-mode blocks with genuinely DIFFERENT per-theme RGB values (not swappable) — WP4.2 undersizes it.
- **pages-user-profile.css is the proven target end-state** `[NEW]`: 0 !important, 144 color-mix(),
  ~1:1 token ratio, dark mode as single-property token swaps. Use as the WP4.2 template.
- **Dead CSS ready for deletion** (zero refs): #isolated_muscles_filter, tooltipFadeIn keyframe
  (declared 3×, used 0×), layout.css .tbl-show-*/.tbl-hide-sm helpers.
## Phase 20 — CSS part 3
## Phase 21 — Tests: pytest suite
Full detail: [scan/PHASE_21.md](scan/PHASE_21.md) (incl. full coverage matrix). Highlights:
- **effective_sets second pipeline: deletion touches exactly 26 tests in test_effective_sets.py**
  `[CONFIRMS P3]` — clean one-shot removal.
- **Backup coverage is INVERTED** `[NEW][RISK]`: create_auto_backup_before_erase (dead) has 7 tests;
  create_startup_backup (live in /erase-data + startup) has ZERO tests.
- **update_exercise permissiveness is untested-by-pytest** `[CONFIRMS P8]`: only Playwright
  validation-boundary.spec.ts touches it — and (per P22) those assertions are largely vacuous.
- **weight==0 bug is ENSHRINED** `[RISK]`: test_add_exercise_missing_weight asserts the rejection;
  conflicts with logging-side tests that treat scored_weight=0.0 as legit assisted-bodyweight.
  Plan-vs-log semantic inconsistency, owner decision needed.
- **Two test files read the LIVE data/database.db** `[RISK]`: test_volume_taxonomy.py,
  test_catalog_invariants.py bypass fixture isolation — "full pytest == baseline" is not hermetic.
- lift_matching + exercise_media have no direct unit tests (transitive only); body-fat parity has
  zero pytest coverage (Playwright-only) — gates for WPs touching those must include the e2e spec.

## Phase 22 — E2E specs + build/CI config
Full detail: [scan/PHASE_22.md](scan/PHASE_22.md). Highlights:
- **WP0.4 misclassification** `[CONTRADICTS-PLAN]`: scripts/seed_visual_baseline.py is on the
  "must stay" list but has ZERO code/CI/e2e refs (doc mentions only) — fails the plan's own archive
  standard; distinct from e2e/scripts/build_visual_seed.py.
- **Tier-1 CSS-cleanup fragility** `[RISK]`: e2e/visual-helpers.ts prepareForScreenshot() hardcodes
  ~25 class names in an override stylesheet shared by ALL visual specs (66 screenshots) — Phase-4
  renames won't error, they'll silently pollute every pixel diff.
- **Exact-RGB assertions in REQUIRED CI specs** `[RISK]`: nav-dropdown.spec.ts (nav icon colors),
  summary-pages.spec.ts (legend swatches) hard-fail on token consolidation — but Phase 4's stated
  gates don't include these functional specs.
- **Vacuous assertions inflate the safety net** `[RISK]`: expect(true).toBeTruthy() / `x || true`
  patterns across validation-boundary, empty-states, exercise-interactions, superset-edge-cases —
  ~half the documented input-validation E2E coverage cannot fail.
- **fatigue-context.spec.ts (327 lines, real 2D-A coverage) runs in NO CI path** `[NEW]` — absent
  from required shards and from e2e/CLAUDE.md's inclusion table; deep-gate only, undocumented.
- testing.md spec ledger stale (17/315 vs actual 28) `[CONFIRMS-PLAN item #10]`; body-comp parity
  spec verified exactly as P16 described.

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

### Wave-2 additions (frontend/tests/CI):
- **JS dead code is a first-class category the plan lacks** — charts.js + summary.js no-ops (P16),
  exercises.js duplicate Add-Exercise flow (P12), workout-log.js 96 dead lines incl. a POST to a
  nonexistent route (P15), showAutoBackupBanner orphan (P14), progression legacy calling a
  nonexistent function (P16), dropdown _cleanupHandler never invoked (P15). "Window-assigned but
  never called" defeats the plan's rule-8 grep.
- **Triplicated/duplicated client logic with drift already realized** — progression-badge logic ×3
  with one copy missing the assisted-bodyweight case (P15); apiFetch reimplemented in
  volume-splitter.js (P14); 3rd/4th hand-synced taxonomy lists in JS (P15).
- **Validation void spans the full stack** — server: none on update paths (P8); client: cosmetic
  only (P15); pytest: gap confirmed (P21); E2E: vacuous assertions (P22). The app effectively has
  no enforced input validation on updates anywhere.
- **CSS: the plan's WP4.x are right in direction but mis-sized** — 4× copy-pasted ~1350-line frame
  block (P19); @layer/!important trap needs an order statement first (P18); six siloed token
  namespaces + duplicate spacing vocabularies (P18,P20); theme-dark + navbar need triage not bulk
  treatment (P20); tokens.css loads after its consumers (P19); misfiled page content (P18).
- **Test safety net weaker than counts suggest** — inverted backup coverage (P21), non-hermetic
  live-DB tests (P21), vacuous E2E assertions (P22), fatigue-context spec in no CI path (P22),
  exact-RGB assertions primed to fail Phase 4 (P22), visual-helpers hardcoding ~25 class names (P22).
- **UI event-handling races/leaks** — double-submit on scored edits (P15), execution-picker listener
  leak (P12), popover leak (P15), toast severity bug (P17/P12).
