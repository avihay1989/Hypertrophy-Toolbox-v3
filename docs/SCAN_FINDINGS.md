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
## Phase 3 — Volume & summary calculations
## Phase 4 — Fatigue, progression, log
## Phase 5 — Estimator core
## Phase 6 — Plan generation & calibration
## Phase 7 — Backup, exports, misc utils
## Phase 8 — Routes: workout_plan + filters
## Phase 9 — Routes: profile / exports / progression
## Phase 10 — Routes: remainder
## Phase 11 — Templates
## Phase 12 — JS: workout-plan cluster
## Phase 13 — JS: profile / muscle-map / media
## Phase 14 — JS: backup / volume-splitter
## Phase 15 — JS: log / filters / dropdowns
## Phase 16 — JS: progression / body-comp / tables / summary
## Phase 17 — JS: app infra & shared
## Phase 18 — CSS part 1
## Phase 19 — CSS part 2
## Phase 20 — CSS part 3
## Phase 21 — Tests: pytest suite
## Phase 22 — E2E specs + build/CI config

---

## Cross-cutting themes (seeds Phase 23 recommendations)
- **Schema-init duplication** — startup (app.py:60-77) and erase_data (204-220) repeat the same 8-call
  block; erase also hardcodes a DROP-table list. WP2.4's registry should own both + a table list. (P1)
- **Response-contract asymmetry** — success_response returns dict, error_response returns tuple. (P1)
- **Doc staleness** — CLAUDE.md §2 startup (6 vs 8), handover SHA pointer (P1). Watch for more.
- **Plan-vs-reality gaps** — WP0.1's "all errors.py handlers live" is already contradicted (P1). The
  grep-based plan needs runtime verification at synthesis; track every CONTRADICTS-PLAN tag.
- **Duplicate helpers** — get_request_id ×2 (P1). Watch for more small dups worth consolidating.
