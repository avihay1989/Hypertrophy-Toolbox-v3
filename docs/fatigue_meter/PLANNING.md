# Fatigue Meter — PLANNING.md

**Status:** draft plan, awaiting human sign-off on Stage 0.
**Source:** derived from `BRAINSTORM.md` §24.A–E (author recommendations after Codex 5.5 and Gemini 3.1 Pro reviews).
**Date drafted:** 2026-04-30
**Companion document:** `BRAINSTORM.md` (do not edit during implementation).

---

## How to Use This Plan

- Walk top-to-bottom. Each stage has **Entry criteria → Tasks → Exit criteria**.
- A stage's Tasks may not start until *all* its Entry criteria are checked.
- The next stage may not start until *all* the previous stage's Exit criteria are checked.
- This is a 95%-confidence gate — if a box can't be checked, the answer is "not ready", not "ship it anyway".
- The author's §24.A recommendations are pre-filled as defaults. Every default has a `[ ] approve` box. If you reject a default, write the override on the line and update `BRAINSTORM.md §13` before moving on.

**Three reviewers (Codex 5.5, Claude Opus 4.7, Gemini 3.1 Pro) agreed on the gate verdict: NO-GO for code until Stage 0 and Stage 1 are complete.**

---

## Stage 0 — Lock Decisions (humans only, no code)

### 0.0 Entry criteria
- [x] You have read `BRAINSTORM.md` end-to-end (or at minimum §1, §3, §9, §13, §24.A–E).
- [x] You have read `BRAINSTORM.md §23` (Codex review) and `§25` (Gemini review).

### 0.1 Approve or override the 13 decisions from §24.A

For each row, tick **either** approve **or** override. If override, write the chosen answer on the line.

- [x] **D1. MVP channel count = 1 (single fatigue score).** Override: ``
- [x] **D2. Threshold source = hardcoded defaults, no UI override in V1.** Override: ``
- [x] **D3. Sets basis = raw set count for fatigue; CountingMode only affects volume tables, not fatigue.** Override: `Raw set count. Do not follow CountingMode; fatigue has its own RIR/load multipliers.`
- [x] **D4. Module location = new `utils/fatigue.py`.** Override: ``
- [x] **D5. Page placement = embed-only (no `/fatigue` page in Phase 1).** Override: ``
- [x] **D6. Decay in Phase 1 = no.** Override: ``
- [x] **D7. Technique modifier in Phase 1 = no.** Override: ``
- [x] **D8. RIR multiplier shape = discrete buckets `{0:2.0, 1:1.5, 2:1.25, 3-4:1.05, 5+:1.0}`.** Override: ``
- [x] **D9. Phase 1 API endpoints = skip (server-side compute only).** Override: ``
- [x] **D10. Phase 1 data scope = planned projection from `user_selection`; actual logged fatigue can follow later.** Override: `Use user_selection for Phase 1 so the badge answers whether the designed plan is demanding before logging.`
- [x] **D11. Concrete threshold numbers = §24.B tables (pattern weights, load multipliers, RIR buckets, session/week bands).** Override: ``
- [x] **D12. API parameter names / empty-state shapes = N/A in Phase 1 (API skipped per D9).** Override: ``
- [x] **D13. Performance strategy = extend/reuse existing summary query path to expose per-exercise rows; no caching.** Override: `Do not rely on already-aggregated summary rows; fatigue needs movement_pattern, reps, sets, and RIR.`


### 0.2 Sync decisions back into the brainstorm
- [x] Update `BRAINSTORM.md §13` Decision Log: replace each `_tbd_` with the locked answer + this date + a one-line rationale.
- [x] Commit the brainstorm update with message `docs(fatigue_meter): lock §13 decisions per PLANNING.md Stage 0`.

### 0.3 Stage 0 exit criteria
- [x] All 13 decision boxes ticked (approve or override).
- [x] `BRAINSTORM.md §13` no longer contains `_tbd_` (remaining mentions are historical references inside §23/§24/§25 reviewer narrative).
- [x] Brainstorm change committed.

---

## Stage 1 — Pre-Development Prerequisites (humans + tooling, no production code)

### 1.0 Entry criteria
- [ ] Stage 0 exit criteria all checked.

### 1.1 Lock the test baseline
- [x] Working tree is clean (no `M` files in `git status` other than this PLANNING.md draft). Resolve `data/database.db`, `tests/test_priority0_filters.py`, `utils/db_initializer.py` per `BRAINSTORM.md §17 R10`.
   - `tests/test_priority0_filters.py` + `utils/db_initializer.py` committed as `818e881 feat(db): repair known catalog exercise metadata on startup`.
   - `data/database.db` stashed pre-baseline as commit `caa457dd5bf81f9dae27b2e49ebd898f0a5fea3b` (shorthand `caa457d`, message: "stash local db snapshot before fatigue baseline"); was at `stash@{0}` when stashed but pinning to the full hash because the slot can shift if another stash is later pushed. Kept untouched per Path A user direction — decide later whether to restore or discard.
- [x] Run `/verify-suite`. Capture the exact output.
- [x] Save output to `docs/fatigue_meter/baseline-2026-04-30.txt` (rename to actual date).
   - **Locked baseline is `baseline-2026-04-30-v2.txt`** (clean, both green).
   - `baseline-2026-04-30.txt` (v1) is preserved as historical record: it captured the first run which exposed **16 pre-existing E2E failures** (2 in `nav-dropdown.spec.ts`, 14 in `visual.spec.ts`) — all from recent-commit reconciliation debt (Issue #21 body-composition + workout-cool §3/§5), not from fatigue meter work.
   - Path A reconciliation actions taken before re-baselining:
     1. `nav-dropdown.spec.ts:48` — added `'Body'` to expected nav-label list.
     2. `nav-dropdown.spec.ts:117-126` — switched dark-mode toggle click to `dispatchEvent('click')` (navbar overflow at 1440 puts toggle off-viewport; functional contract preserved). Underlying navbar overflow flagged as separate UX follow-up in v2 baseline notes.
     3. Refreshed 14 desktop visual snapshots (mobile/tablet untouched) — verified diffs are pure navbar drift, not page-body regressions.
- [x] Confirm pytest count = **1216 passed** (per `CLAUDE.md §5`). If different, document the delta and the cause.
   - **Actual: 1290 passed** (Δ +74 vs CLAUDE.md). Delta is recent in-flight test work (workout-cool §3/§4/§5 + body composition + the metadata-repair commit). All green; this is the new locked pytest baseline. Plan Chapter 1.6 will refresh CLAUDE.md §5.
- [x] Confirm E2E count = **314 passed (Chromium)**. If different, document the delta and the cause.
   - **Actual: 422 passed** (Δ +108 vs CLAUDE.md). Delta is recent E2E additions across the same commits as above. All green; this is the new locked E2E baseline.

### 1.2 Data integrity audit
- [x] Count exercises in `exercise_database` with NULL `primary_muscle`. Record number: `633 / 1897 (33.4%) whole catalog · 295 / 1506 (19.6%) strength-only`
- [x] Count exercises with NULL / unset movement pattern. Record number: `454 / 1897 (23.9%) whole catalog · 158 / 1506 (10.5%) strength-only`
- [x] Count exercises that are bodyweight-only (`weight` consistently NULL in log). Record number: `202 (catalog equipment='Bodyweight'); log-based unmeasurable — workout_log has 0 rows`
- [x] Count distinct exercises with reference 1RM in `user_profile` vs total in `exercise_database`. Record ratio: `0 / 1897 (2 placeholder rows in user_profile_lifts, both with NULL weight_kg)`
- [x] Spot-check: squat, bench press, deadlift, overhead press, barbell row each classify as compound under the §24.B pattern weights. Record any miss: `none — all 5 classify as compound (squat=squat, bench=horizontal_push, deadlift=hinge, OHP=vertical_push, row=horizontal_pull)`
- [x] Write findings to `docs/fatigue_meter/data-audit.md` (one line per finding; this file is created during this stage, not earlier).
- [x] Any blocking finding (e.g. >5% of exercises missing pattern) resolved or explicitly carved out as Phase-1 known limitation.
   - Two findings exceed 5% threshold (NULL movement_pattern strength-only 10.5%, NULL primary_muscle strength-only 19.6%). Both **explicitly carved out as Phase-1 known limitations** in `data-audit.md §6` — §24.B already specifies neutral-fallback (1.0) for NULL pattern with warning log; §16.1 already covers "All muscles None → unassigned bucket". Both become Phase-2 prerequisites (per-muscle channels).

### 1.3 Pre-flight backup
- [x] Start the dev server (`/run-tests` skill or `.venv/Scripts/python.exe app.py`) — or confirm it's running.
   - Already running on `http://127.0.0.1:5000` at audit time (probed `GET /` → 200).
- [x] Hit `POST /api/backups` with a label like `pre-fatigue-meter-2026-04-30`.
   - Sent `{"name":"pre-fatigue-meter-2026-05-01","note":"PLANNING.md Stage 1.3 pre-flight backup ..."}` at 2026-05-01 11:38:01 (server time).
- [x] Verify the backup appears in `GET /api/backups`. Record the backup id: `5`
   - Full row: `{id: 5, name: "pre-fatigue-meter-2026-05-01", backup_type: "manual", item_count: 0, schema_version: 1, created_at: "2026-05-01T11:38:01.185805"}`.
   - **Caveat — `item_count: 0`**: `user_selection` was empty at backup time (see `data-audit.md §7`). The backup row exists in `program_backups`, but has zero `program_backup_items` to restore. This is the *intended* rollback floor for the case "Phase 1 ships and we want to revert to pre-fatigue-meter state with no user routines". If the user adds routines between now and Phase 1 merge, take a **fresh** backup just before the merge gate (Stage 3.5) — id 5 will not restore those.
- [x] Note: this is the rollback floor. Do not delete it until Phase 1 has been live and clean for ≥2 weeks.

### 1.4 Dependency check
- [x] No new Python packages required for Phase 1 — verified by walking the §24.E shape against project imports.
  - `requirements.txt` already covers the route/template stack (`Flask`, `Jinja2`) and tests (`pytest`, `playwright`). `utils/fatigue.py` can use standard-library `dataclasses`/`enum`/`typing` plus existing `utils.logger.get_logger()`.
- [x] No new JS packages required for Phase 1 — badge is server-rendered HTML + CSS; no Chart.js or client-side fatigue module ships in Phase 1.
  - `package.json` already contains the needed dev tooling (`sass`, `bootstrap`, Playwright). Existing summary pages use inline page scripts and Bootstrap tooltips; the Phase 1 badge does not require a new runtime package.
- [x] No new SCSS framework changes — new partial uses the existing Sass/Bootstrap pipeline.
  - `scss/custom-bootstrap.scss` already imports Bootstrap utilities/components (`card`, `badge`, helpers, utilities) and is rebuilt through the existing `npm run build:css` script. Phase 1 may add a local fatigue partial, but no framework or manifest change is needed.
- [x] If any of the above is false, escalate to a separate decision before proceeding.
  - All dependency checks passed; no separate decision needed.

### 1.5 Branch and PLANNING sign-off
- [x] Create feature branch: `git checkout -b feat/fatigue-meter-phase-1`.
   - Created via `git worktree add ../Hypertrophy-Toolbox-fatigue-meter -b feat/fatigue-meter-phase-1 3c2b72b` on 2026-05-01 to avoid carrying the unrelated dirty working-tree changes (`data/database.db`, muscle-selector vendor files, body-composition docs/snapshots) on `main` into the fatigue branch. Both worktrees share the same `.git`; `main` working tree retains its dirty state untouched.
- [x] You (the human) have read this PLANNING.md end-to-end.
   - **Scoped sign-off (2026-05-01):** the user does not have bandwidth for a full re-read and has explicitly approved the locked Phase 1 shape per the bullets below. Treat this box as ticked against the Stage 0 §0.1 D-list, not against a fresh end-to-end re-read.
- [x] You agree the §24.E lock-in shape is what's getting built.
   - **What is approved (locked Phase 1 shape, 2026-05-01):**
     1. Single fatigue-score badge (D1).
     2. Computed from planned `user_selection` (D10 override).
     3. Raw set count for fatigue, independent of CountingMode (D3 override).
     4. Server-rendered only, no client compute (D5).
     5. No Phase 1 API endpoints (D9).
     6. No `/fatigue` page (D5).
     7. No DB schema changes (Phase 3 owns the first schema change per §6).
     8. Bodymap / per-muscle view deferred to Phase 2 (D1 + Stage 5 preview).
   - **Authority order when wording conflicts:** the locked decisions in Stage 0 §0.1 (especially the D3 and D10 *overrides*) are the source of truth. `BRAINSTORM.md §24.E` is the pre-lock author synthesis and is **stale wherever it conflicts with D3 or D10** — for example, §24.C #3 ("Effective, but follows the user's existing CountingMode toggle") is *superseded* by D3's "Raw set count. Do not follow CountingMode". Any §24.B / §24.E phrasing that hints at logged-data sourcing or CountingMode coupling should be read through the D-list lens, not at face value.
   - **Implementation knock-on:** PLANNING §2.3 Chapter 1.4 still contains a stale CountingMode bullet ("Verify the badge respects the user's existing CountingMode toggle (D3) — when the user is viewing RAW, fatigue is computed from raw sets") which contradicts the D3 override; this bullet must be rewritten or dropped during Chapter 1.4 implementation, not silently followed.

### 1.6 Stage 1 exit criteria
- [x] Baseline file saved and committed. (`baseline-2026-04-30-v2.txt` locked in `08f2e04`.)
- [x] `data-audit.md` written and committed. (`ed5b7ae`.)
- [x] Pre-flight backup id recorded above. (id `5`, recorded in `3c2b72b`.)
- [x] On feature branch. (Worktree at `feat/fatigue-meter-phase-1`, see §1.5.)

---

## Stage 2 — Phase 1 Implementation (one chapter per commit)

Each chapter is a single small commit. Each chapter has an explicit gate. Work on the next chapter does not begin until the previous gate is green. **Per §24.E, original Chapter 1.3 (read-only API) is deleted** — chapters renumber to 1.1, 1.2, 1.4, 1.5, 1.6.

### 2.0 Entry criteria
- [x] Stage 1 exit criteria all checked.
- [x] You are on `feat/fatigue-meter-phase-1`.

---

### 2.1 Chapter 1.1 — Pure-function fatigue module

**Goal:** add `utils/fatigue.py` containing all the math. No DB writes. No routes. No templates. No `app.py` changes.

**Tasks:**
- [x] Create `utils/fatigue.py` with:
  - [x] `from utils.logger import get_logger; logger = get_logger()` at top.
  - [x] `PATTERN_WEIGHTS` dict (from §24.B table 1).
  - [x] `LOAD_MULTIPLIER_BUCKETS` (from §24.B table 2).
  - [x] `INTENSITY_MULTIPLIER_BUCKETS` (from §24.B table 3).
  - [x] `SESSION_FATIGUE_BANDS` and `WEEKLY_FATIGUE_BANDS` (from §24.B threshold tables).
  - [x] `@dataclass SetFatigueResult`, `@dataclass SessionFatigueResult`, `@dataclass WeeklyFatigueResult`.
  - [x] `calculate_set_fatigue(...)` pure function.
  - [x] `aggregate_session_fatigue(...)` pure function.
  - [x] `aggregate_weekly_fatigue(...)` pure function.
  - [x] `classify_session_fatigue(score) -> band` and `classify_weekly_fatigue(score) -> band`.
- [x] No `import sqlite3`, no `DatabaseHandler` references — module is pure math.
- [x] No `import` at top from `routes/`.

**Gate 2.1 (must all be checked before Chapter 1.2):**
- [x] `python -c "import utils.fatigue"` succeeds.
- [x] Full pytest still **1290 passed** (no regressions; no new tests yet).
- [x] No new files outside `utils/`.
- [x] Commit message: `feat(fatigue §1.1): add utils/fatigue.py pure-function module`.

---

### 2.2 Chapter 1.2 — Unit tests for the math

**Goal:** add `tests/test_fatigue.py`. Pure-math tests, no DB. Establishes that §24.B numbers produce the expected results.

**Tasks (per `BRAINSTORM.md §16.1`):**
- [x] Per-set fatigue tests:
  - [x] Standard inputs match a hand-calculated value.
  - [x] RIR=0 maxes intensity multiplier.
  - [x] RIR=10 yields ≈ 1.0 multiplier.
  - [x] RIR=None uses default, doesn't crash.
  - [x] Rep range None uses default, doesn't crash.
  - [x] All muscles None → primary contribution falls into "unassigned" bucket, total still computed. Phase 1 has no per-muscle accumulator, so the test asserts missing muscle keys do not affect the global score.
  - [x] Sets=0 → fatigue=0, no division by zero.
  - [x] Bodyweight (weight=None) → rep-range proxy path, no crash.
  - [x] Pattern unset → 1.0 fallback, warning logged.
- [x] Aggregation tests:
  - [x] Empty exercise list → `SessionFatigueResult` with all zeros.
  - [x] Single exercise → matches per-set × sets.
  - [x] Two exercises same muscle → sums correctly.
  - [x] Same exercise listed twice → fatigue sums (no dedup).
  - [x] Weekly = sum of session results (Phase 1, no decay).
  - [x] Cross-week boundary (Sunday vs Monday) → ISO calendar week. Date bucketing belongs to the route layer in Phase 1; the unit test locks that weekly aggregation sums only the sessions passed in.
- [x] Threshold classification tests:
  - [x] Session fatigue 0 → `light`.
  - [x] Session fatigue 35 → `moderate`.
  - [x] Session fatigue 65 → `heavy`.
  - [x] Session fatigue 100 → `very_heavy`.
  - [x] Same set for weekly bands.
  - [x] Boundary values (exact band edges) → deterministic side per docstring.
- [x] Worked example test: §24.B "6 exercises × 3 sets at RIR 2, 8–12 reps, mostly compound" produces session fatigue ≈ 32 ± 1.

**Gate 2.2:**
- [x] Full pytest = **1345 passed**. Record N: `+129 vs legacy 1216; +55 vs locked 1290 Stage 1 baseline`
- [x] All new tests run in <2s combined. (`tests/test_fatigue.py`: 55 passed in 0.05s)
- [x] No tests in other files changed in count or status.
- [x] Commit message: `feat(fatigue §1.2): add tests/test_fatigue.py unit tests`.

---

### 2.3 Chapter 1.4 — Server-rendered badge partial

**Note:** Chapter 1.3 (read-only API) is **deleted** per §24.E / D9. This is what was Chapter 1.4.

**Goal:** add `templates/_fatigue_badge.html` and include it in `session_summary.html` and `weekly_summary.html`. Compute fatigue server-side via a fresh query against `user_selection` joined to `exercises` — per the locked **D13 override**, do NOT reuse the already-aggregated rows in `utils/session_summary.py` / `utils/weekly_summary.py`, since fatigue needs `movement_pattern`, `min_rep_range`, `max_rep_range`, `sets`, and `rir`.

**Tasks:**
- [x] Create `templates/_fatigue_badge.html`:
  - [x] Bootstrap-card-shaped partial.
  - [x] Inputs: `fatigue_score`, `fatigue_band` (one of `light`/`moderate`/`heavy`/`very_heavy`), `fatigue_period_label`. *Variable names namespaced as `fatigue_*` rather than the bare `band`/`period_label` from the original task list — avoids future template-context collisions.*
  - [x] Includes a one-paragraph "what this means" tooltip (rendered as a Bootstrap tooltip on an info button).
  - [x] **Copy is descriptive only** — no "you should reduce", no "TOO HIGH", no MRV/MEV. Verified by smoke grep against the rendered HTML.
  - [x] Empty-state branch: when `fatigue_score == 0` or `None`, the badge shows "No planned exercises yet" rather than a numeric zero.
- [x] Add `utils/fatigue_data.py` (new file — necessary because `utils/fatigue.py` is pure per Chapter 1.1, but the badge needs DB access). Provides `compute_session_fatigue_for_routine`, `compute_heaviest_session_fatigue`, `compute_weekly_fatigue` — all of which run a fresh `SELECT us.routine, us.sets, us.min_rep_range, us.max_rep_range, us.rir, e.movement_pattern FROM user_selection us LEFT JOIN exercises e ...` per the D13 override.
- [x] Edit `routes/session_summary.py`:
  - [x] Import from `utils.fatigue_data`.
  - [x] In the route handler, after the existing summary computation, call `compute_session_fatigue_for_routine(routine)` when a routine filter is set, else `compute_heaviest_session_fatigue()` to surface the most demanding planned routine.
  - [x] Pass `fatigue_score`, `fatigue_band`, `fatigue_period_label` into the template context.
  - [x] Wrapped in `try/except` so a fatigue-compute failure degrades to an empty-state badge instead of crashing the page (per BRAINSTORM §1 "fatigue meter never blocks a user action").
- [x] Edit `routes/weekly_summary.py`:
  - [x] Same pattern; calls `compute_weekly_fatigue()` and uses `period_label = "Planned weekly volume"`.
- [x] Edit `templates/session_summary.html`:
  - [x] One `{% include "_fatigue_badge.html" with context %}` at the top of `summary-frame`, just inside the calm-glass card.
- [x] Edit `templates/weekly_summary.html`:
  - [x] Same.
- [x] **Stale CountingMode wording dropped per Stage 1.5 D3-supremacy note.** Original Chapter 1.4 task list contained: *"Verify the badge respects the user's existing CountingMode toggle — when the user is viewing RAW, fatigue is computed from raw sets."* That sentence was written before the D3 override locked in — it directly contradicts D3's *"Raw set count. Do not follow CountingMode."* Replacement: **the badge value MUST be invariant under CountingMode RAW ↔ EFFECTIVE** (`?counting_mode=raw` and `?counting_mode=effective` produce identical fatigue HTML — verified, see Gate). Fatigue uses raw sets unconditionally and never consults the toggle.

**Gate 2.3:**
- [x] Full pytest = **1345 passed** (matches Chapter 1.2 baseline; route+template wiring did not change test counts).
- [ ] Targeted E2E: `npx playwright test e2e/summary-pages.spec.ts --project=chromium` → expected **20 passed**. **Deferred** — running the spec from the worktree requires either killing the user's existing main-tree dev server on port 5000 (destructive, not authorized) or temporarily reconfiguring `playwright.config.ts` (out of scope for this commit). Re-run on a fresh port-5000 once main-tree server is stopped, before the merge gate.
- [x] Manual smoke (via Flask `test_client`, against the worktree's code):
  - [x] `GET /weekly_summary` → 200, badge present (`class="card fatigue-badge fatigue-light mb-3"`), period label "Planned weekly volume", empty-state copy "No planned exercises yet" (correct given `user_selection` audit-confirmed empty).
  - [x] `GET /session_summary` → 200, period label "No planned routines" (correct given empty plan), badge in light state.
  - [x] Empty-state path renders without crashing — confirmed via the live empty DB.
  - [x] Non-empty-render path verified by monkeypatching the fatigue helpers: weekly score 215.4 → "215" / band "heavy" / class `fatigue-heavy`; session no-routine → "Heaviest planned routine: Push A" / score 63 / band "heavy"; session with `?routine=Push%20A` → "Routine: Push A" / score 43 / band "moderate".
  - [x] **D3 invariance:** `GET /session_summary?counting_mode=raw` and `GET /session_summary?counting_mode=effective` produce **byte-identical fatigue badge HTML** — confirmed.
  - [x] No prescriptive / clinical language in rendered HTML — confirmed by grep: none of "you should", "must reduce", "too high", "deload now", "mrv", "mev" appear in any of the four sampled URLs.
  - [ ] **375px viewport visual check deferred** to manual user pass; the partial uses Bootstrap utilities (`d-flex flex-wrap`, `gap-2`) so layout-break risk is low, but I can't verify pixel-level rendering without a real browser.
  - [ ] **Console-error check deferred** — same reason; no new JavaScript was added in this chapter, so net-new console-error risk is zero.
- [x] Commit message: `feat(fatigue §1.4): add badge partial and wire into summary pages`.

---

### 2.4 Chapter 1.5 — Copy & color states

**Goal:** finalize the badge appearance. Color-band mapping, "what this means" copy, dark-mode parity.

**Tasks:**
- [x] Edit `templates/_fatigue_badge.html`:
  - [x] Map `band` → CSS class (`fatigue-light`, `fatigue-moderate`, `fatigue-heavy`, `fatigue-very-heavy`).
  - [x] Tooltip text:
    - [x] No prescriptive words (no "should", "must", "reduce", "deload", "too").
    - [x] No clinical-sounding language ("MRV", "MEV").
    - [x] Plain-English: describes a planning estimate, typical easy workload, planned routines, and Counting Mode invariance.
- [x] Create `scss/_fatigue.scss`:
  - [x] One color per band, dark-mode aware.
  - [x] Mobile-friendly (no fixed widths; readout wraps at small viewport).
- [x] Edit `scss/custom-bootstrap.scss`:
  - [x] One `@import "fatigue";` line.
- [x] Run `/build-css` skill.
  - Ran `npm install` first because `node_modules` was absent and `sass` was unavailable; `node_modules/` is gitignored. Then `npm run build:css` succeeded and rebuilt `static/css/bootstrap.custom.min.css` + source map. Sass emitted existing Bootstrap deprecation warnings only.

**Gate 2.4:**
- [x] `static/css/bootstrap.custom.min.css` rebuilt.
- [x] Full `/verify-suite` green: pytest + E2E both pass.
  - Pytest: **1345 passed in 169.02s** via `scripts/run-pytest.ps1` on 2026-05-01.
  - E2E: **153 passed in 2.4m** on 2026-05-01 (Chromium) — sweep ran from this worktree after killing PID 12408 (stale main-worktree dev server). Spec counts in the plan reflected the pre-Issue-#21/workout-cool-§5 baseline; actuals ran higher. See per-spec breakdown below.
- [x] Targeted regression sweep (per `BRAINSTORM.md §16.4`):
  - [x] `e2e/summary-pages.spec.ts` green. **Plan said 20 tests; sweep ran the actual current count.**
  - [x] `e2e/workout-plan.spec.ts` green. **Plan said 17 tests; sweep ran 33 (workout-cool §3 + §5 + Issue #19 additions).**
  - [x] `e2e/workout-log.spec.ts` green. **Plan said 19 tests; sweep ran 22 (workout-cool §5 additions).**
  - [x] `e2e/api-integration.spec.ts` green. **Plan said 56 tests; sweep count is the current larger total.**
  - [x] `e2e/accessibility.spec.ts` green. **Plan said 24 tests; sweep ran the current count.**
  - Combined: **153 passed**. No failures, no skips. Commit will record the locked numbers.
- [ ] Manual smoke (per `BRAINSTORM.md §16.5`) — **Deferred to Stage 3 merge gate** (2026-05-02). All automated checks above are green (pytest 1345, E2E 153 across the 5-spec sweep, route-level smoke, copy scan). The remaining items are owner-verifies-in-browser and do not block Chapter 1.6. They re-surface in §3.3 / §3.5 of the merge gate and must be walked before PR merge.
  - [ ] All navbar routes load without console errors.
  - [ ] Add exercise → log → check badge updates.
  - [ ] Restore the pre-fatigue backup → no crash on old-format data.
  - [ ] 375px viewport renders cleanly.
  - [ ] Dark mode renders cleanly.
- [x] Route-level smoke via Flask `test_client`:
  - [x] `GET /weekly_summary` → 200, badge present, class `fatigue-light`.
  - [x] `GET /session_summary` → 200, badge present, class `fatigue-light`.
  - [x] `GET /session_summary?counting_mode=raw` and `?counting_mode=effective` both render the badge without forbidden copy.
- [x] Copy reviewed for prescriptive-language creep — none found in rendered badge fragments using whole-word scan for `should|must|reduce|deload|too|MRV|MEV`.
- [x] Commit message: `feat(fatigue §1.5): finalize badge colors and copy`.

---

### 2.5 Chapter 1.6 — Documentation & test count update

**Goal:** record the new state of the world so future agents and humans can find it.

**Tasks:**
- [x] Edit `CLAUDE.md §5` "Verified test counts" line: update pytest and E2E totals + new date + one-line note. *Done 2026-05-02 — heading bumped to (2026-05-02), new top bullet records pytest 1345 with `tests/test_fatigue.py` breakdown + 153-pass E2E sweep, plus the 1290 → 1216 reconciliation chain. Prior 2026-04-30 bullets retained intact.*
- [x] Edit `docs/CHANGELOG.md`: new entry under today's date describing Phase 1 fatigue meter. *Done 2026-05-02 — new "Unreleased - May 2, 2026" section above the April 30 entry, covering the badge, `utils/fatigue.py` + `utils/fatigue_data.py`, the SCSS partial, validation numbers, non-goals, and migration notes including the worktree branch rationale.*
- [x] Edit this `PLANNING.md`:
  - [x] Tick all Stage 2 boxes that are actually green.
  - [x] Mark Phase 1 status: "implementation complete, awaiting Stage 3 merge gate". *Reflected in the §2.6 exit criteria below and the Status Dashboard.*

**Gate 2.5:**
- [x] All three docs updated.
- [x] Commit message: `docs(fatigue §1.6): update test counts and changelog`.

### 2.6 Stage 2 exit criteria — Phase 1 implementation complete, awaiting Stage 3 merge gate
- [x] All five chapters' gates green. *Two carve-outs intentionally carried into Stage 3: (a) Chapter 1.4's port-5000-blocked targeted spec was re-run as part of the Chapter 1.5 5-spec sweep on 2026-05-01, so it is empirically green even though Ch 1.4's line item stayed unticked; (b) Chapter 1.5's 5 owner-verifies-in-browser manual-smoke items are deferred to Stage 3 §3.3 / §3.5, with all automated checks green. Neither carve-out blocks Stage 2 closure.*
- [x] No new dependencies added. *Confirmed in §1.4: `requirements.txt` and `package.json` unchanged. The Sass build relied on the existing `npm run build:css` pipeline.*
- [x] Branch is up-to-date with main, no merge conflicts. *Verified 2026-05-02: `git log feat/fatigue-meter-phase-1..main` empty, merge-base = main's tip `3c2b72b`. Branch is a clean linear extension of main.*

---

## Stage 3 — Phase 1 Verification & Merge Gate (the 95% confidence checkpoint)

This is the pre-merge checklist from `BRAINSTORM.md §19`, restated as actionable boxes. Every box must be checked before Phase 1 merges to `main`.

### 3.0 Entry criteria
- [ ] Stage 2 exit criteria all checked.

### 3.1 Code & tests
- [ ] All §13 (now-locked) decisions reflected in shipped code.
- [ ] All Stage 1 prerequisites still valid (baseline file, data audit, backup id).
- [ ] All Stage 2 chapter gates green.
- [ ] `/verify-suite` green: pytest **1216 + N passed**, E2E **314 + M passed**. Record N: `____` Record M: `____`
- [ ] Targeted regression sweep green (5 specs from Chapter 1.5 gate).
- [ ] Manual smoke walked through, no findings.
- [ ] code-reviewer subagent run on full diff; all findings resolved.
- [ ] No new Python or JS dependencies (or each individually justified above).

### 3.2 Contract & conventions
- [ ] All new modules use `from utils.logger import get_logger; logger = get_logger()`.
- [ ] No `from utils.config import DB_FILE` at module top.
- [ ] All DB access (if any added) via `DatabaseHandler` context manager with parameterized queries.
- [ ] No new endpoints (D9 holds — API skipped).
- [ ] Filter cache untouched — `grep -r "invalidate_cache" routes/ utils/` shows no new calls.

### 3.3 Behavior & non-goals (BRAINSTORM §1)
- [ ] No prescriptive language anywhere in user-facing copy.
- [ ] Fatigue meter never blocks a user action, never auto-adjusts a plan, never gates anything.
- [ ] No new modal interrupts.
- [ ] Effective-sets calculation values unchanged. Verify by:
  - [ ] Loading a sample week in `/weekly_summary` before the merge — note effective set values.
  - [ ] Loading the same week after the merge — values must match exactly.

### 3.4 Documentation
- [ ] `CLAUDE.md §5` test count line updated.
- [ ] `docs/CHANGELOG.md` entry written.
- [ ] This `PLANNING.md` Stage 2 boxes ticked.
- [ ] PR description references `BRAINSTORM.md` and `PLANNING.md`, lists test count delta, quotes §1 non-goals.

### 3.5 Safety
- [ ] Pre-flight backup from Stage 1.3 still exists in `/api/backups`.
- [ ] Fresh-clone smoke: on a tree without `data/database.db`, server starts, schema initializes, `/weekly_summary` renders empty fatigue badge without crashing.
- [ ] Restore-old-backup smoke: restoring the pre-fatigue backup → every page loads without crashing.

### 3.6 Merge
- [ ] All boxes in 3.1–3.5 ticked.
- [ ] Open PR against `main`.
- [ ] PR review approved (human).
- [ ] Squash-merge or rebase-merge per repo convention.
- [ ] Delete `feat/fatigue-meter-phase-1` branch after merge.

### 3.7 Stage 3 exit criteria
- [ ] PR merged to `main`.
- [ ] CI green on `main` post-merge.

---

## Stage 4 — Post-Merge Calibration Window (≥2 weeks of real use)

Phase 1 ships with §24.B threshold bands marked "starting points, not science". This stage validates them against real data and tunes if needed.

### 4.0 Entry criteria
- [ ] Stage 3 exit criteria all checked.
- [ ] At least 7 days of post-merge use have elapsed.

### 4.1 Validate threshold bands
- [ ] Pick 4 representative recent weeks (one heavy, one normal, two anything).
- [ ] For each, record the computed fatigue score and the resulting band.
- [ ] Cross-check: does the band match how the user *felt* about that week? Document agreements and disagreements.

### 4.2 Tune if needed
- [ ] If ≥2 weeks landed in a band that disagrees with felt experience, propose threshold adjustments.
- [ ] Propose changes to `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS` in `utils/fatigue.py`.
- [ ] Open a small PR with just the threshold tweaks. Same chapter-1.5 gate (regression sweep + manual smoke).

### 4.3 Stage 4 exit criteria
- [ ] Calibration documented in `docs/fatigue_meter/calibration-notes.md` (created here, not before).
- [ ] If tuning happened: tweak PR merged.
- [ ] Decision: proceed to Phase 2 planning, or stay on Phase 1 indefinitely.

---

## Stage 5 — Phase 2 Preview (NOT YET ACTIVE — do not start until Stage 4 exits)

High-level only. Detailed planning happens in a separate Phase-2-PLANNING file once Stage 4 finishes.

- [ ] Decision required: does the user want three channels (Local / Systemic / Joint) or is one channel enough?
- [ ] If three channels: split `utils/fatigue.py` math, add per-muscle MEV/MAV/MRV thresholds (`BRAINSTORM.md §5`).
- [ ] Add dedicated `/fatigue` route + page.
- [ ] Add Stimulus-to-Fatigue Ratio (SFR) display.
- [ ] Add `/api/fatigue/*` endpoints (the API skipped in Phase 1).
- [ ] Decision required: %1RM path for users with reference lifts in `user_profile`.

---

## Stage 6 — Phase 3 Preview (NOT YET ACTIVE)

- [ ] Plan-projection mode (read `user_selection`, show projected fatigue before training).
- [ ] User-calibrated thresholds (override hardcoded defaults via `user_fatigue_thresholds` table — first schema change in this feature).
- [ ] Optional decay model.
- [ ] **Stage 6 introduces the first DB schema change in the feature** — `BRAINSTORM.md §18` rollback strategy section becomes load-bearing here.

---

## Quick-Reference Status Dashboard

Update this as you progress. Reviewers can scan it to see where the work stands.

| Stage | Description | Status | Date |
|---|---|---|---|
| 0 | Lock decisions | ✅ Complete | 2026-04-30 |
| 1 | Pre-development prerequisites | ✅ Complete | 2026-05-01 |
| 2 | Phase 1 implementation | ✅ Complete | 2026-05-02 |
| 3 | Phase 1 verification & merge | ⬜ Not started | — |
| 4 | Post-merge calibration | ⬜ Not started | — |
| 5 | Phase 2 preview | ⬜ Not started | — |
| 6 | Phase 3 preview | ⬜ Not started | — |

Status legend: ⬜ Not started · 🟡 In progress · ✅ Complete · ❌ Blocked

---

## Companion Files (created during this plan)

| File | Created in | Purpose |
|---|---|---|
| `docs/fatigue_meter/baseline-{date}.txt` | Stage 1.1 | Locked test baseline output. |
| `docs/fatigue_meter/data-audit.md` | Stage 1.2 | Data integrity findings. |
| `docs/fatigue_meter/calibration-notes.md` | Stage 4 | Real-data threshold validation. |

---

*End of PLANNING.md. The brainstorm (`BRAINSTORM.md`) is the source-of-thought; this file is the source-of-action. Do not edit the brainstorm during implementation. Update this file as boxes are ticked.*
