
# Execution log — User Profile feature

> ⚠️ **Frozen — v1 shipped 2026-04-26. Archived 2026-04-29.** This file
> is the historical execution journal for the v1 build. Post-v1 work
> (Issues #1–#24) is tracked in
> [`../development_issues.md`](../development_issues.md), not here.
> Append-only contract no longer applies — file is closed.

> Living journal kept by each implementing agent. **Do not retroactively rewrite entries.** Append-only.

> Companion to [PLANNING.md](PLANNING.md). Each phase ticks its checkboxes in PLANNING.md only after the matching entry is appended here.

---

## How to use this file

Each agent that picks up a slice (A, B, C1, C2, D, E, F, G, H — see PLANNING.md "Agent-sized task slicing") appends one entry under the matching heading below. Format:

```
### YYYY-MM-DD — Slice-X — <agent label / model>

**Files changed:**
- path/to/file.py — brief description
- path/to/other.html — brief description

**Decisions / guesses (call out anything not pinned in PLANNING.md or DESIGN.md):**
- e.g. "Used 2.5 kg rounding for trapbar despite plan saying 1.25 kg — reasoning: ..."

**Tests:**
- pytest: 968 → 978 (+10) passing
- e2e (chromium, relevant specs): 62 → 64 (+2) passing

**Open issues / follow-ups:**
- e.g. "Lateral raise estimate looked too heavy in manual test — flagged for retune in v2"
```

Keep entries terse. Link to commit SHAs when available.

---

## Phase 0 — Scaffolding

### 2026-04-26 — Slice-0 — opus-4-7 (planning agent)

**Files changed:**
- `docs/user_profile/PLANNING.md` — created (mirror of plan-mode plan file)
- `docs/user_profile/EXECUTION_LOG.md` — created (this file, stub)

**Decisions:**
- Two-doc layout chosen per user request: planning + execution as siblings under `docs/user_profile/`.
- `DESIGN.md` deferred to Slice-A (it captures Phase-A constants in code-ready form).
- `README.md` deferred to Slice-H (Phase-H §H.2).

**Tests:** none (docs only).

**Open issues:** awaiting plan approval before Slice-A starts.

---

## Phase A — Design constants

### 2026-04-26 — Slice-A — opus-4-7

**Files changed:**
- `docs/user_profile/DESIGN.md` — created. Pinned 14 questionnaire slugs, tier rules, Epley formula, tier ratios (1.0/0.7/0.4), three rep-range presets, weight-rounding table, muscle→key-lift mapping with cross-fallback factor 0.6, estimation precedence, route validation ranges.

**Decisions / guesses:**
- Set `CROSS_FALLBACK_FACTOR = 0.6` to apply when the chosen reference lift is not the first in a muscle's chain (e.g., triceps → bench press fallback). Approximation; flagged in §10 for v2 retune.
- Default sets = 3 across all profile-derived estimates. Could be tier-specific later.
- `bodyweight_pullups` and `bodyweight_dips` slugs accept `weight_kg = 0` and use reps directly; bodyweight-plus-bodyweight math deferred to v2.
- `Hip-Adductors`, `Calves`, `Forearms`, `Rectus Abdominis`, `Neck`, `External Obliques` have empty key-lift chains → estimator returns None → caller falls back to hardcoded defaults.

**Tests:** none (docs only).

**Open issues:** §10 in DESIGN.md tracks v2 follow-ups.

---

## Pre-Execution Review

### 2026-04-26 — Plan Review — Opus (Claude Opus 4.6 Thinking)

**Scope:** Full review of PLANNING.md, DESIGN.md, EXECUTION_LOG.md cross-referenced against live codebase.

**Overall confidence: ~88%** — 9 blocking items identified. Once resolved → ≥95%.

**Blocking issues found (comments injected into PLANNING.md and DESIGN.md):**

| # | File | Section | Issue |
|---|------|---------|-------|
| 1 | PLANNING.md | Phase B.4 | Missing `erase-data` route and `clean_db` fixture updates for 3 new tables |
| 2 | PLANNING.md | Phase C.2 | `_lookup_last_logged` JOIN to `user_selection` is unnecessary; need `scored_*` vs `planned_*` clarification via COALESCE |
| 3 | PLANNING.md | Phase E.1 | CSS strategy ("no new bundle") conflicts with `.claude/rules/frontend.md` route-scope rules — create `pages-user-profile.css` |
| 4 | PLANNING.md | Phase E.1 | `apiCall` export doesn't exist in `fetch-wrapper.js`; real exports are `apiFetch` / `api.post()` |
| 5 | PLANNING.md | Phase F | `resetFormFields()` uses different defaults (`weight=100, sets=1`) than HTML (`weight=25, sets=3`) — two conflicting default sets |
| 6 | DESIGN.md | §2.3 | `"clean"` keyword in COMPLEX_ALLOWLIST may cause false substring matches |
| 7 | DESIGN.md | §7 | Cross-fallback from `weighted_pullups` → Biceps produces ~4 kg estimates (bodyweight not counted in added weight) |
| 8 | DESIGN.md | §6 | No minimum weight floor for dumbbell estimates |
| 9 | — | — | `workout_log.created_at` column existence needs verification for ORDER BY |

**What's strong:**
- Phase ordering (B→C→D→E→F→G→H) has correct dependency chain
- 9-slice decomposition is well-scoped for small agents (<30k token context each)
- Worked examples (EZ Bar Preacher Curl ≈ 11 kg, Bench Press ≈ 99 kg) are mathematically verified correct
- Blueprint registration pattern matches existing codebase perfectly
- Response contract uses correct `success_response`/`error_response` from `utils/errors.py`
- Tier classification rules are sound and well-aligned with `utils/movement_patterns.py`

**Corrections already applied to PLANNING.md:**
- B.4: Added 3 missing checklist items (erase-data DROP, clean_db DELETE, erase-data reinit)
- C.2: Corrected `_lookup_last_logged` to query `workout_log` directly (no JOIN), added COALESCE column mapping
- E.1: Changed CSS strategy to create new `pages-user-profile.css` route bundle
- E.1/E.2/F.1: Corrected `apiCall` → `apiFetch` / `api.post()` throughout
- E.3: Made nav insertion point explicit (between `muscleModeToggle` and `darkModeToggle`)
- F.1: Documented the `resetFormFields` discrepancy with recommendation
- Utilities list: Corrected `apiCall` → `apiFetch`
- All 9 slice contexts: Updated to reflect corrections

**Corrections noted in DESIGN.md (as review comments, not yet applied to code):**
- §2.3: `"clean"` keyword false positive risk
- §6: Dumbbell minimum weight floor suggestion
- §7: `weighted_pullups` → Biceps fallback chain removal recommendation
- §8: Confirmed no JOIN needed for last-logged-set lookup

**Open issues / follow-ups:**
- ~~Opus 4.7 should review the injected comments and decide on each recommendation before starting Slice-B~~ → resolved below
- ~~The `resetFormFields` decision (BLOCKING #5) needs explicit sign-off: recommend option (a) — re-fetch estimate after add~~ → resolved below

### 2026-04-26 — Plan Review Sign-off — Opus 4.7

**Verdict on Opus 4.6's 9 items:**

| # | Item | Decision |
|---|---|---|
| 1 | erase-data + clean_db wiring (B.4) | ✅ Approved as-applied. Real bug — would have leaked profile data across tests and survived `/erase-data`. |
| 2 | Drop `user_selection` JOIN in `_lookup_last_logged` (C.2) | ✅ Approved as-applied. `workout_log` is denormalized; JOIN was redundant cost. |
| 3 | New `pages-user-profile.css` bundle (E.1) | ✅ Approved as-applied. Stuffing into `pages-workout-plan.css` violates route-scope. Bundle count 7→8 is fine. |
| 4 | `apiCall` → `apiFetch` (E.1, E.2, F.1, utilities) | ✅ Approved as-applied. Real bug — `apiCall` was never an export. |
| 5 | `resetFormFields` discrepancy (F.2) | ✅ **Signed off** with explicit Slice-F directives now in PLANNING.md F.2. Legacy `weight=100, sets=1, rir=0, min_rep=3, max_rep=5, rpe=''` reset values are deleted; post-add path re-runs the estimate handler. |
| 6 | `"clean"` keyword false positives (DESIGN §2.3) | ✅ **Applied.** Replaced bare `clean` with `power clean` + `hang clean`. `snatch` retained — only common false positive ("Snatch Grip Deadlift") is itself a complex lift. |
| 7 | `weighted_pullups` → Biceps cross-fallback (DESIGN §7) | ✅ **Applied.** Removed `weighted_pullups` from `Biceps` chain. Falls through to defaults if `barbell_bicep_curl` missing. Kept as primary for `Latissimus Dorsi` (no cross-fallback factor on primary entry). |
| 8 | Dumbbell weight floor (DESIGN §6) | ✅ **Applied at 1 kg, not 2 kg.** Most commercial gym dumbbell sets start at 1 kg; 2 kg over-corrects. Also added explicit floor column for all equipment classes (free-weight floor = 20 kg empty bar). |
| 9 | `workout_log.created_at` ordering (PLANNING C.2) | ✅ **Pinned to `id DESC LIMIT 1`.** Verified `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` exists at `utils/db_initializer.py:250`, but `id` is strictly monotonic AUTOINCREMENT and tie-free. |

**Confidence after these resolutions:** ~96%. Plan is ready for Slice-B execution once the user gives a final go.

**Files touched in this sign-off pass:**
- `docs/user_profile/DESIGN.md` — applied #6, #7, #8 corrections (replaced bare `clean` keyword, removed `weighted_pullups` from Biceps chain, added explicit floor column with 1 kg dumbbell floor).
- `docs/user_profile/PLANNING.md` — pinned C.2 ordering to `id DESC` (#9), added explicit Slice-F directive for #5.

**Tests:** none (docs only).

### 2026-04-26 — Follow-up correction — Opus 4.6

**Files touched:**
- `docs/user_profile/DESIGN.md` §8 line 235 — replaced leftover "matching `user_selection` row" wording with `id DESC LIMIT 1, no JOIN` + `COALESCE(scored_*, planned_*)` to align with the PLANNING.md C.2 directive. No semantic change to the agreed approach; this was an internal-consistency fix.

**Acknowledged by Opus 4.7:** Verified the §8 wording now matches PLANNING.md C.2's COALESCE mapping. No further edits needed.

### 2026-04-26 — Plan Review — codex-5.5

**Scope:** Reviewed `PLANNING.md`, `DESIGN.md`, and `EXECUTION_LOG.md` against the current repo state, especially `workout-plan.js`, `exercises.js`, `fetch-wrapper.js`, `templates/workout_plan.html`, `templates/base.html`, `app.py`, `tests/conftest.py`, and the live exercise metadata for the worked preacher-curl example.

**Verdict:**
- *** codex 5.5*** Confidence is close, but not quite 95% until the Phase-F ownership mismatch and the barbell/EZ-bar weight-floor conflict are resolved in the plan. After those are corrected, I would treat the plan as execution-ready.

**Comments injected:**
- *** codex 5.5*** `PLANNING.md` Phase B now has comments recommending DB-level enforcement for the one-row profile table and conflict-update upserts instead of `INSERT OR REPLACE`.
- *** codex 5.5*** `PLANNING.md` Phase E now notes that `.claude/rules/frontend.md` still contains stale `apiCall` guidance in more than one section, so Slice-E should update those lines too.
- *** codex 5.5*** `PLANNING.md` Phase F now flags that `workout-plan.js` already has an active `handleExerciseSelection()` change handler and an active Add Exercise reset path; smaller agents should modify that path, not add a duplicate listener or focus on the legacy `exercises.js` flow first.
- *** codex 5.5*** `DESIGN.md` now flags the `Barbell` 20 kg floor conflict: live `EZ Bar Preacher Curl` is stored as `equipment = 'Barbell'`, so the current floor would break the documented ~11 kg example.
- *** codex 5.5*** `DESIGN.md` now notes that demographics are mostly unused in v1 and should not silently turn into unreviewed age/gender/bodyweight formulas during implementation.

**Open issues / follow-ups:**
- *** codex 5.5*** Before Slice-C starts, decide the final `round_weight()` floor rule for isolated barbell/EZ-bar exercises.
- *** codex 5.5*** Before Slice-F starts, update its task brief so `static/js/modules/workout-plan.js` is the primary owner and `static/js/modules/exercises.js` is secondary/legacy context.
- *** codex 5.5*** Add one regression test proving post-add reset reuses the selected exercise estimate.

### 2026-04-26 — codex 5.5 review sign-off — Opus 4.7

**Scope:** Reviewed all 12 codex 5.5 comments across `DESIGN.md` and `PLANNING.md`. All accepted; plan adjusted accordingly.

**Decisions on each codex 5.5 item:**

| # | Where | Item | Decision |
|---|---|---|---|
| 1 | DESIGN §1 | UI copy must say "recent hard set", not "1RM" | ✅ **Applied.** Added Resolved block under §1 with explicit copy directive for Slice-E (per-row helper text + section header forbidden from saying "1RM"). |
| 2 | DESIGN §6 | `Barbell` 20 kg floor breaks the EZ-bar preacher curl example | ✅ **Applied.** Floor is now tier-aware: 20 kg empty-bar floor only for **complex** tier; **accessory/isolated** with `equipment='Barbell'` floor at 1.25 kg. Added a separate row to the rounding table. `round_weight()` signature changes to `(weight, equipment, tier)` — flagged as a Slice-C implementation note. Worked example (`~11 kg` preacher curl) preserved. |
| 3 | DESIGN §8 | Add stable `reason` field to response contract | ✅ **Applied.** `reason` adopted as a required key on every estimator return. Stable enum: `log`, `profile`, `profile_cross`, `default_excluded`, `default_no_reference`, `default_missing`. `source` keeps driving UI; `reason` is the contract surface for tests and logs. |
| 4 | DESIGN §10 | Demographics unused in v1 — make it explicit | ✅ **Applied.** Hard constraint pinned: `_estimate_from_profile` MUST NOT read demographic columns in v1. Function signature does not even take them as inputs. Implementation that violates this must be rejected at review. |
| 5 | PLANNING B.1 | DB-level `CHECK (id = 1)` for `user_profile` | ✅ **Applied.** Schema updated to `id INTEGER PRIMARY KEY CHECK (id = 1)`. Upserts must write `id = 1` literally. |
| 6 | PLANNING B.2/B.3 | Prefer `ON CONFLICT DO UPDATE` over `INSERT OR REPLACE` | ✅ **Applied.** All three upserts (lifts, preferences, demographics — added new B.3a) now use `ON CONFLICT DO UPDATE SET ... = excluded....`. `INSERT OR REPLACE` explicitly forbidden. |
| 7 | PLANNING E.1 | `frontend.md` has stale `apiCall` references in multiple sections | ✅ **Applied.** New checklist item lists all sections needing `apiCall → apiFetch`/`api.post()` replacement, plus a verification grep. |
| 8 | PLANNING F.1 | Subsection stale — `handleExerciseSelection()` already exists | ✅ **Applied.** F.1 rewritten: must modify the existing handler, must NOT add a second listener, must preserve the existing `updateExerciseDetails()` call. |
| 9 | PLANNING F.1 | One shared `applyUserProfileEstimateForSelectedExercise()` helper | ✅ **Applied.** Helper named, scoped to `workout-plan.js`, called from both the change handler and the post-add reset path. |
| 10 | PLANNING F.2 | `workout-plan.js` is primary; `exercises.js` is legacy | ✅ **Applied.** F.2 rewritten with explicit primary/secondary split. `exercises.js:resetFormFields` only edited if Playwright proves a legacy caller still hits it. Slice-F context line in the slicing list also rewritten with the same ownership model. |
| 11 | PLANNING G.2 | Regression test for post-add reset reusing the estimate | ✅ **Applied.** New G.2 bullet pins the exact assertion: select → fields populated → click Add → fields **still show estimate** (not legacy `weight=100, sets=1` reset, not blank). Test seeds `user_profile_lifts` via the API for deterministic weight. |
| 12 | PLANNING Slice-F | Update slice brief to reflect ownership | ✅ **Applied.** Slice-F context block in the slicing list now says "Primary owner: workout-plan.js / Secondary: exercises.js (legacy)" with the three-bullet directive. |

**Confidence after these resolutions:** ≥95% (per codex 5.5's threshold). Plan is execution-ready for Slice-B onward.

**Cross-impacts to be aware of for downstream slices:**
- **Slice-C:** `round_weight()` signature changed — now takes `(weight, equipment, tier)`. `_estimate_from_profile` already has `tier` from `classify_tier()`, so plumbing is local.
- **Slice-C:** Every return from `estimate_for_exercise` includes a `reason` field. Tests must assert on `reason`, not `source`.
- **Slice-C:** Estimator MUST NOT read demographic columns. Signature: `estimate_for_exercise(exercise_name, *, db)` — no demographic params.
- **Slice-D:** `/api/user_profile/estimate` response includes the new `reason` key (under `success_response`'s `data`).
- **Slice-E:** UI copy for the lift questionnaire forbidden from using "1RM". Helper text per row says "your recent hard set".
- **Slice-F:** Modify existing `handleExerciseSelection()`; do not add a second listener. New helper name: `applyUserProfileEstimateForSelectedExercise()`.

**Files touched in this sign-off pass:**
- `docs/user_profile/DESIGN.md` — added Resolved blocks under §1, §6, §8, §10. Tier-aware floor row added to §6 rounding table.
- `docs/user_profile/PLANNING.md` — B.1 CHECK constraint; B.2/B.3 ON CONFLICT; new B.3a; E.1 expanded apiCall directive; F.1 fully rewritten with shared helper; F.2 fully rewritten with primary/secondary split; G.2 regression test added; Slice-F context line rewritten.

**Tests:** none (docs only).

---

## Phase B — Data layer

### 2026-04-26 — Slice-B — codex-5.5

**Files changed:**
- `utils/database.py` — added `add_user_profile_tables()` plus non-`REPLACE` upsert helpers for demographics, reference lifts, and tier preferences.
- `app.py` — wired user-profile table creation into startup and `/erase-data` reinitialization; profile tables now drop during full reset.
- `tests/conftest.py` — wired the test initializer, test `/erase-data`, and `clean_db` cleanup for the three new tables.
- `tests/test_database_user_profile.py` — added schema, constraint, and erase-data recreation tests.

**Decisions / guesses:**
- Used SQLite `CHECK` constraints exactly as planned: `user_profile.id = 1`, valid preference tiers, and valid rep-range keys.
- Kept the test-only `/erase-data` fixture route's existing no-confirm behavior so existing tests continue to exercise reset without request-body churn; production `app.py` still requires `confirm=ERASE_ALL_DATA`.

**Tests:**
- `python -m pytest tests/test_database_user_profile.py -q`: 4 passed.
- `python -m pytest tests/test_volume_progress.py::test_migration_called_via_add_volume_tracking_tables tests/test_program_backup.py::TestEraseDataDeletesBackups::test_erase_data_reinitializes_tables -q`: 2 passed.

**Open issues / follow-ups:**
- Slice-D can reuse the data-layer upsert helpers after adding request validation and route responses.

---

## Phase C — Estimation utility

### 2026-04-26 — Slice-C1/C2 — codex-5.5

**Files changed:**
- `utils/profile_estimator.py` — added constants, tier classification, Epley/rounding helpers, last-log lookup, profile estimation, and safe default fallback contract.
- `tests/test_profile_estimator.py` — added focused unit coverage for constants, tiering, Epley clamp, rounding floors, log/profile/default precedence, cross fallback, and bodyweight references.

**Decisions / guesses:**
- Implemented bodyweight reference behavior as `weight=0` and `min_rep=max_rep=<stored reps>`, while still carrying the selected tier preset's RIR/RPE.
- Empty exercise names return the default struct with `reason='default_missing'`, matching the planned client flow for a cleared exercise selector.

**Tests:**
- `python -m pytest tests/test_profile_estimator.py -q`: 14 passed.
- `python -m pytest tests/test_database_user_profile.py -q`: 4 passed.

**Open issues / follow-ups:**
- Slice-D should expose `estimate_for_exercise()` through `/api/user_profile/estimate` and preserve the `reason` field in the response data.

---

## Phase D — Backend routes

### 2026-04-26 — Slice-D — codex-5.5

**Files changed:**
- `routes/user_profile.py` — added blueprint, page route, demographics/lifts/preferences save APIs, and estimate API.
- `app.py` — registered `user_profile_bp`.
- `tests/conftest.py` — registered `user_profile_bp` in the test app.
- `tests/test_user_profile_routes.py` — added route contract tests for page render, validation, persistence, and estimate precedence.

**Decisions / guesses:**
- Lift saves accept either the planned list body or `{lifts: [...]}` for ergonomic JS callers.
- Empty estimate query returns `source='default', reason='default_missing'`.

**Tests:**
- `python -m pytest tests/test_user_profile_routes.py -q`: 10 passed.

**Open issues / follow-ups:** none.

---

## Phase E — Frontend: profile page

### 2026-04-26 — Slice-E — codex-5.5

**Files changed:**
- `templates/user_profile.html` — added three saveable sections for demographics, reference lifts, and rep-range preferences.
- `static/js/modules/user-profile.js` — added no-reload section saves through `api.post()`.
- `static/css/pages-user-profile.css` — added route-scoped profile page styling.
- `templates/base.html` — added right-side Profile nav link.
- `.claude/rules/frontend.md` — updated route bundle count/list and replaced stale `apiCall` guidance.
- `e2e/fixtures.ts` — added User Profile route/selectors.

**Decisions / guesses:**
- Used compact segmented radio controls for rep ranges and per-row "your recent hard set" helper text per DESIGN.md.

**Tests:**
- `rg -i "apiCall" .claude/rules/frontend.md`: zero matches.
- `node --check static/js/modules/user-profile.js`: passed.
- `python -m pytest tests/test_user_profile_routes.py -q`: 10 passed.

**Open issues / follow-ups:** none.

---

## Phase F — Workout-plan integration

### 2026-04-26 — Slice-F — codex-5.5

**Files changed:**
- `static/js/modules/workout-plan.js` — added `applyUserProfileEstimateForSelectedExercise()`, called it from the existing exercise-change handler, and routed post-add reset through the same helper.
- `templates/workout_plan.html` — added provenance caption under Workout Controls.
- `static/css/pages-workout-plan.css` — styled the provenance caption.

**Decisions / guesses:**
- Network failures during estimate fetch locally fall back to the HTML defaults and caption `default values`.
- Left legacy `static/js/modules/exercises.js` untouched because the active template path uses `workout-plan.js`.

**Tests:**
- `node --check static/js/modules/workout-plan.js`: passed.
- `python -m pytest tests/test_user_profile_routes.py tests/test_profile_estimator.py tests/test_database_user_profile.py -q`: 28 passed.

**Open issues / follow-ups:** none.

---

## Phase G — Tests / verification

### 2026-04-26 — Slice-G — codex-5.5

**Files changed:**
- `e2e/user-profile.spec.ts` — added profile-save E2E and workout-plan post-add estimate regression.
- `e2e/fixtures.ts` — added User Profile route/selectors.

**Decisions / guesses:**
- Seeded deterministic reference lifts via the User Profile API rather than mutating SQLite directly from Playwright.

**Tests:**
- `python -m pytest tests/test_user_profile_routes.py tests/test_profile_estimator.py tests/test_database_user_profile.py -q`: 28 passed.
- `npx playwright test e2e/user-profile.spec.ts --project=chromium`: 2 passed.
- `npx playwright test e2e/workout-plan.spec.ts --project=chromium`: 19 passed.
- `npx playwright test e2e/volume-progress.spec.ts --project=chromium`: 16 passed.

**Open issues / follow-ups:**
- Full pytest and full relevant E2E gate were not run in this slice.

---

## Phase H — Documentation closeout

### 2026-04-26 — Slice-H — codex-5.5

**Files changed:**
- `docs/user_profile/README.md` — added short feature note linking planning, design constants, execution log, route, and estimator ownership.
- `CLAUDE.md` — added User Profile workflow/blueprint/startup references and targeted verification counts.
- `docs/user_profile/PLANNING.md` — checked off completed D-H items.
- `docs/user_profile/EXECUTION_LOG.md` — appended Slice-B through Slice-H entries.

**Decisions / guesses:**
- Kept CLAUDE.md's historical full-suite counts intact because this pass ran targeted verification, not a new full baseline.

**Tests:**
- Documentation-only changes after the final verification commands above.

**Open issues / follow-ups:**
- Run the full verification gate before treating the historical CLAUDE.md baseline counts as refreshed.

---

## Phase G — Verification gate closeout

### 2026-04-26 — Slice-G3 — codex-5.5

**Files changed:**
- `docs/user_profile/PLANNING.md` — checked off the full pytest and relevant Chromium Playwright verification gate.
- `CLAUDE.md` — refreshed verified test counts for the User Profile feature gate.
- `docs/user_profile/EXECUTION_LOG.md` — appended this closeout entry.

**Decisions / guesses:**
- Treated the planned `/verify-suite` item as satisfied by equivalent direct commands because the local skill was not available in this session.
- Kept the older full E2E baseline line unchanged; this pass ran the relevant Chromium specs named in G.3, not the entire Playwright suite.

**Tests:**
- `python -m pytest -q`: 996 passed.
- `npx playwright test e2e/user-profile.spec.ts e2e/workout-plan.spec.ts e2e/volume-progress.spec.ts e2e/volume-splitter.spec.ts --project=chromium`: 64 passed.

**Open issues / follow-ups:**
- Manual visual/click-through confirmation checklist remains available in `PLANNING.md` for a human pass.

---

## Phase — Manual/API verification pass

### 2026-04-26 — Manual verification — claude-sonnet-4-6

**Scope:** Worked through every remaining unchecked item in `PLANNING.md §Verification`.

**Verification method:** Started Flask app (`python app.py`) and used `curl` + direct DB queries to exercise all API paths. Browser-side toast/UI rendering not verified (no browser), but all backend contract points confirmed.

**Results:**

| Checklist item | Result |
|---|---|
| App boots, logs "Adding user profile tables..." | ✅ Confirmed in `app.py` stdout and `logs/app.log` |
| `/user_profile` page loads | ✅ HTTP 200 |
| Demographics save + persist | ✅ `POST /api/user_profile` → `ok:true`; row visible in `user_profile` table with `id=1` |
| Reference lifts save + persist | ✅ `POST /api/user_profile/lifts` → `ok:true`; 4 lifts confirmed in `user_profile_lifts` |
| Preferences save | ✅ `POST /api/user_profile/preferences` → complex=heavy, accessory=moderate, isolated=light confirmed |
| EZ Bar Preacher Curl estimate ≈ 11 kg | ✅ Returned `weight=11.25, min_rep=10, max_rep=15, rir=2, rpe=7.5, source=profile` |
| Barbell Bench Press estimate ≈ 99 kg | ✅ Returned `weight=98.75, min_rep=4, max_rep=6, rir=1, rpe=9.0, source=profile` |
| Last-logged-set precedence | ✅ After inserting a `workout_log` row (102.5 kg), estimate returned `source=log, weight=102.5` |
| TRX Pushup → defaults | ✅ `source=default, reason=default_excluded, weight=25, sets=3` |
| Bosu Ball Curl → defaults | ✅ `source=default, reason=default_excluded, weight=25, sets=3` |
| All main pages HTTP 200 | ✅ `/workout_plan`, `/workout_log`, `/weekly_summary`, `/session_summary`, `/progression`, `/volume_splitter`, `/api/backups` all 200 |

**Files changed:**
- `docs/user_profile/PLANNING.md` — checked off all remaining manual checklist items.
- `docs/user_profile/EXECUTION_LOG.md` — appended this entry.

**Decisions / guesses:**
- Test lift slugs: used `barbell_back_squat`, `barbell_bench_press`, `romanian_deadlift`, `barbell_bicep_curl` (not `conventional_deadlift` — not in `KEY_LIFTS`).
- Inserted one `workout_log` row directly into SQLite to verify last-log precedence; removed it immediately after.

**Tests:** No new automated tests. All prior counts unchanged (996 pytest, 64 relevant Chromium E2E).

**Open issues / follow-ups:**
- Browser-based visual verification (toasts, provenance caption rendering, form field autofill on exercise select) is the one remaining human step.
