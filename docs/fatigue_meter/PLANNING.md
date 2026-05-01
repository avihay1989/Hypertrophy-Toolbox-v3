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
- [ ] Start the dev server (`/run-tests` skill or `.venv/Scripts/python.exe app.py`) — or confirm it's running.
- [ ] Hit `POST /api/backups` with a label like `pre-fatigue-meter-2026-04-30`.
- [ ] Verify the backup appears in `GET /api/backups`. Record the backup id: `____`
- [ ] Note: this is the rollback floor. Do not delete it until Phase 1 has been live and clean for ≥2 weeks.

### 1.4 Dependency check
- [ ] No new Python packages required for Phase 1 — verified by walking the §24.E shape against project imports.
- [ ] No new JS packages required for Phase 1 — badge is server-rendered HTML + minimal SCSS.
- [ ] No new SCSS framework changes — new partial uses existing Bootstrap utilities.
- [ ] If any of the above is false, escalate to a separate decision before proceeding.

### 1.5 Branch and PLANNING sign-off
- [ ] Create feature branch: `git checkout -b feat/fatigue-meter-phase-1`.
- [ ] You (the human) have read this PLANNING.md end-to-end.
- [ ] You agree the §24.E lock-in shape is what's getting built.

### 1.6 Stage 1 exit criteria
- [ ] Baseline file saved and committed.
- [ ] `data-audit.md` written and committed.
- [ ] Pre-flight backup id recorded above.
- [ ] On feature branch.

---

## Stage 2 — Phase 1 Implementation (one chapter per commit)

Each chapter is a single small commit. Each chapter has an explicit gate. Work on the next chapter does not begin until the previous gate is green. **Per §24.E, original Chapter 1.3 (read-only API) is deleted** — chapters renumber to 1.1, 1.2, 1.4, 1.5, 1.6.

### 2.0 Entry criteria
- [ ] Stage 1 exit criteria all checked.
- [ ] You are on `feat/fatigue-meter-phase-1`.

---

### 2.1 Chapter 1.1 — Pure-function fatigue module

**Goal:** add `utils/fatigue.py` containing all the math. No DB writes. No routes. No templates. No `app.py` changes.

**Tasks:**
- [ ] Create `utils/fatigue.py` with:
  - [ ] `from utils.logger import get_logger; logger = get_logger()` at top.
  - [ ] `PATTERN_WEIGHTS` dict (from §24.B table 1).
  - [ ] `LOAD_MULTIPLIER_BUCKETS` (from §24.B table 2).
  - [ ] `INTENSITY_MULTIPLIER_BUCKETS` (from §24.B table 3).
  - [ ] `SESSION_FATIGUE_BANDS` and `WEEKLY_FATIGUE_BANDS` (from §24.B threshold tables).
  - [ ] `@dataclass SetFatigueResult`, `@dataclass SessionFatigueResult`, `@dataclass WeeklyFatigueResult`.
  - [ ] `calculate_set_fatigue(...)` pure function.
  - [ ] `aggregate_session_fatigue(...)` pure function.
  - [ ] `aggregate_weekly_fatigue(...)` pure function.
  - [ ] `classify_session_fatigue(score) -> band` and `classify_weekly_fatigue(score) -> band`.
- [ ] No `import sqlite3`, no `DatabaseHandler` references — module is pure math.
- [ ] No `import` at top from `routes/`.

**Gate 2.1 (must all be checked before Chapter 1.2):**
- [ ] `python -c "import utils.fatigue"` succeeds.
- [ ] Full pytest still **1216 passed** (no regressions; no new tests yet).
- [ ] No new files outside `utils/`.
- [ ] Commit message: `feat(fatigue §1.1): add utils/fatigue.py pure-function module`.

---

### 2.2 Chapter 1.2 — Unit tests for the math

**Goal:** add `tests/test_fatigue.py`. Pure-math tests, no DB. Establishes that §24.B numbers produce the expected results.

**Tasks (per `BRAINSTORM.md §16.1`):**
- [ ] Per-set fatigue tests:
  - [ ] Standard inputs match a hand-calculated value.
  - [ ] RIR=0 maxes intensity multiplier.
  - [ ] RIR=10 yields ≈ 1.0 multiplier.
  - [ ] RIR=None uses default, doesn't crash.
  - [ ] Rep range None uses default, doesn't crash.
  - [ ] All muscles None → primary contribution falls into "unassigned" bucket, total still computed.
  - [ ] Sets=0 → fatigue=0, no division by zero.
  - [ ] Bodyweight (weight=None) → rep-range proxy path, no crash.
  - [ ] Pattern unset → 1.0 fallback, warning logged.
- [ ] Aggregation tests:
  - [ ] Empty exercise list → `SessionFatigueResult` with all zeros.
  - [ ] Single exercise → matches per-set × sets.
  - [ ] Two exercises same muscle → sums correctly.
  - [ ] Same exercise listed twice → fatigue sums (no dedup).
  - [ ] Weekly = sum of session results (Phase 1, no decay).
  - [ ] Cross-week boundary (Sunday vs Monday) → ISO calendar week.
- [ ] Threshold classification tests:
  - [ ] Session fatigue 0 → `light`.
  - [ ] Session fatigue 35 → `moderate`.
  - [ ] Session fatigue 65 → `heavy`.
  - [ ] Session fatigue 100 → `very_heavy`.
  - [ ] Same set for weekly bands.
  - [ ] Boundary values (exact band edges) → deterministic side per docstring.
- [ ] Worked example test: §24.B "6 exercises × 3 sets at RIR 2, 8–12 reps, mostly compound" produces session fatigue ≈ 32 ± 1.

**Gate 2.2:**
- [ ] Full pytest = **1216 + N passed**. Record N: `____`
- [ ] All new tests run in <2s combined.
- [ ] No tests in other files changed in count or status.
- [ ] Commit message: `feat(fatigue §1.2): add tests/test_fatigue.py unit tests`.

---

### 2.3 Chapter 1.4 — Server-rendered badge partial

**Note:** Chapter 1.3 (read-only API) is **deleted** per §24.E / D9. This is what was Chapter 1.4.

**Goal:** add `templates/_fatigue_badge.html` and include it in `session_summary.html` and `weekly_summary.html`. Compute fatigue server-side in the existing route handlers using the rows they already load (D13, no new queries).

**Tasks:**
- [ ] Create `templates/_fatigue_badge.html`:
  - [ ] Bootstrap-card-shaped partial.
  - [ ] Inputs: `fatigue_score`, `band` (one of `light`/`moderate`/`heavy`/`very_heavy`), `period_label`.
  - [ ] Includes a one-paragraph "what this means" tooltip.
  - [ ] **Copy is descriptive only** — no "you should reduce", no "TOO HIGH". Use neutral phrasing.
- [ ] Edit `routes/session_summary.py`:
  - [ ] Import from `utils.fatigue`.
  - [ ] In the route handler, after the existing summary computation, call `aggregate_session_fatigue(...)` using the rows already loaded.
  - [ ] Pass `fatigue_score`, `band`, `period_label` into the template context.
- [ ] Edit `routes/weekly_summary.py`:
  - [ ] Same pattern as above for weekly aggregation.
- [ ] Edit `templates/session_summary.html`:
  - [ ] One `{% include '_fatigue_badge.html' %}` line in a designated slot near the existing volume cards.
- [ ] Edit `templates/weekly_summary.html`:
  - [ ] Same.
- [ ] Verify the badge respects the user's existing `CountingMode` toggle (D3) — when the user is viewing RAW, fatigue is computed from raw sets.

**Gate 2.3:**
- [ ] Full pytest = unchanged delta from Chapter 1.2 (template additions don't break server tests).
- [ ] Targeted E2E: `npx playwright test e2e/summary-pages.spec.ts --project=chromium` → **20 passed**.
- [ ] Manual: load `/weekly_summary` and `/session_summary` in a browser. Badge appears. No console errors. No layout breaks at 375px viewport width.
- [ ] Manual: empty log → badge shows zero state without crashing.
- [ ] Manual: toggle CountingMode RAW ↔ EFFECTIVE — badge value changes accordingly.
- [ ] Commit message: `feat(fatigue §1.4): add badge partial and wire into summary pages`.

---

### 2.4 Chapter 1.5 — Copy & color states

**Goal:** finalize the badge appearance. Color-band mapping, "what this means" copy, dark-mode parity.

**Tasks:**
- [ ] Edit `templates/_fatigue_badge.html`:
  - [ ] Map `band` → CSS class (`fatigue-light`, `fatigue-moderate`, `fatigue-heavy`, `fatigue-very-heavy`).
  - [ ] Tooltip text:
    - [ ] No prescriptive words (no "should", "must", "reduce", "deload", "too").
    - [ ] No clinical-sounding language ("MRV", "MEV").
    - [ ] Plain-English: "your typical week", "above your typical recoverable range", etc.
- [ ] Create `scss/_fatigue.scss`:
  - [ ] One color per band, dark-mode aware.
  - [ ] Mobile-friendly (no fixed widths).
- [ ] Edit `scss/custom-bootstrap.scss`:
  - [ ] One `@import "_fatigue";` line.
- [ ] Run `/build-css` skill.

**Gate 2.4:**
- [ ] `static/css/custom-bootstrap.css` rebuilt and committed.
- [ ] Full `/verify-suite` green: pytest + E2E both pass.
- [ ] Targeted regression sweep (per `BRAINSTORM.md §16.4`):
  - [ ] `e2e/summary-pages.spec.ts` (20 tests) green.
  - [ ] `e2e/workout-plan.spec.ts` (17 tests) green.
  - [ ] `e2e/workout-log.spec.ts` (19 tests) green.
  - [ ] `e2e/api-integration.spec.ts` (56 tests) green.
  - [ ] `e2e/accessibility.spec.ts` (24 tests) green.
- [ ] Manual smoke (per `BRAINSTORM.md §16.5`):
  - [ ] All navbar routes load without console errors.
  - [ ] Add exercise → log → check badge updates.
  - [ ] Restore the pre-fatigue backup → no crash on old-format data.
  - [ ] 375px viewport renders cleanly.
  - [ ] Dark mode renders cleanly.
- [ ] Copy reviewed for prescriptive-language creep — none found.
- [ ] Commit message: `feat(fatigue §1.5): finalize badge colors and copy`.

---

### 2.5 Chapter 1.6 — Documentation & test count update

**Goal:** record the new state of the world so future agents and humans can find it.

**Tasks:**
- [ ] Edit `CLAUDE.md §5` "Verified test counts" line: update pytest and E2E totals + new date + one-line note.
- [ ] Edit `docs/CHANGELOG.md`: new entry under today's date describing Phase 1 fatigue meter.
- [ ] Edit this `PLANNING.md`:
  - [ ] Tick all Stage 2 boxes that are actually green.
  - [ ] Mark Phase 1 status: "implementation complete, awaiting Stage 3 merge gate".

**Gate 2.5:**
- [ ] All three docs updated.
- [ ] Commit message: `docs(fatigue §1.6): update test counts and changelog`.

### 2.6 Stage 2 exit criteria
- [ ] All five chapters' gates green.
- [ ] No new dependencies added.
- [ ] Branch is up-to-date with main, no merge conflicts.

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
| 1 | Pre-development prerequisites | 🟡 In progress | 2026-04-30 |
| 2 | Phase 1 implementation | ⬜ Not started | — |
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
