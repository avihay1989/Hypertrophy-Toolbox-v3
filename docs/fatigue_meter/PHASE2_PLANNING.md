# Fatigue Meter — Phase 2 PLANNING

**Status:** **Stage 2 SHIPPED 2026-05-23 to `main` via PR #35 (squash d5b80bf); Stage 3 verify-suite gate CLOSED 2026-05-24; Stage 4 calibration window OPEN 2026-05-24.** (Path 1 — 8 chapters: per-muscle accumulator, period selector, dedicated `/fatigue` route, dual planned + logged bars, two SFR cards, nav link, badge → page link). pytest 1351 → 1442 (+91 new Stage-2 cases); `e2e/fatigue.spec.ts` 8/8 Chromium green. Stage 3 verify-suite on `main`: pytest 1442 passed, full Playwright Chromium 449 passed / 13 failed / 17 did-not-run — the 13 + 17 reds match the CLAUDE.md §5 documented pre-existing baseline exactly with zero new Stage-2 reds.
**Date extracted:** 2026-05-23
**Stage 0 closed:** 2026-05-23
**Stage 1 closed:** 2026-05-23
**Stage 2 implementation completed:** 2026-05-23 (merged to `main` 2026-05-23 via PR #35, squash d5b80bf)
**Stage 3 closed:** 2026-05-24 (verify-suite gate green on `main`; pre-merge restore point: backup id 5, label `pre-fatigue-meter-phase-2-stage-2-merge-2026-05-23`)
**Stage 4 opened:** 2026-05-24 (≥2 weeks of real use before any per-muscle threshold tweaks)
**Source:** split out of [`PLANNING.md`](PLANNING.md) Stage 5/6 and [`BRAINSTORM.md`](BRAINSTORM.md) (§4–§9, §11, §13, §20 Phase 2 matrix).
**Predecessor state:** Phase 1 shipped 2026-05-03 (PR #7, single global server-rendered badge). [Stage 4 closed 2026-05-20](calibration-notes.md) by owner-approved felt-label review (4 of 5 anchors agreed; no threshold changes). The Phase 1 surface (`calculate_set_fatigue`, `aggregate_session_fatigue`, `aggregate_weekly_fatigue`, `classify_*`, `*_FATIGUE_BANDS`, `PATTERN_WEIGHTS`, `LOAD_MULTIPLIER_BUCKETS`, `INTENSITY_MULTIPLIER_BUCKETS` in `utils/fatigue.py`, plus `tests/test_fatigue.py` Phase-1 classes, plus `scripts/fatigue_calibration_report.py::SCENARIOS`) was preserved byte-identical across Stage 2.

This document mirrors the shape of `PLANNING.md` (entry / tasks / exit per stage). Stage 0 (lock D2.x decisions) closed 2026-05-23 via owner decision walk; Stage 1 prerequisites closed 2026-05-23 on branch `feat/fatigue-meter-phase-2` with pytest 1351 passed, backup id 5 (`pre-fatigue-meter-phase-2-2026-05-23`), and catalog `primary_muscle_group` NULLs eliminated. Stage 2 shipped to `main` 2026-05-23 via PR #35 (squash commit `d5b80bf`); Stage 3 verify-suite gate closed 2026-05-24 on `main`; Stage 4 calibration window opened 2026-05-24.

---

## 1. Why Phase 2 — Problem statement (beyond the Phase 1 badge)

Phase 1 ships a single global descriptive score on `/session_summary` and `/weekly_summary`. It answers the question *"is this plan heavy?"* and nothing else.

Three concrete questions Phase 1 cannot answer:

1. **What is heavy?** A 165 weekly score gives no signal about whether the load is biased toward one muscle group, one movement pattern, or one joint system. Two programs with identical global scores can be radically different in distribution.
2. **Is the heaviness worth it?** Phase 1 reports fatigue with no reference to stimulus. A high-fatigue / low-stimulus program (junk volume) reads the same as a high-fatigue / high-stimulus program. The Stimulus-to-Fatigue Ratio (SFR) discussion in `BRAINSTORM.md §4.6` exists exactly to surface this distinction.
3. **Where is the headroom?** Without a per-muscle breakdown there is no signal for "biceps are at typical-recoverable; quads have room" — the per-muscle question is the one most likely to change a routine design decision.

Stage 4's calibration close confirmed the §24.B thresholds are sane against one real logged week + four synthetic anchors. That removes recalibration as the next investment and frees the next investment for **resolution** (channel split + drill-down + ratio).

---

## 2. Locked Phase 2 scope (Path 1 — Stage 0 close 2026-05-23)

Owner-selected scope after Stage 0 walk. Larger than the original "MVP" draft — adds the planned+logged side-by-side view and the period selector on day one. Still purely additive, still no schema, still no API.

- **(a) Local-channel split.** Per-muscle fatigue accumulator (`BRAINSTORM.md §4.2` — Channel A only). Sum `set_fatigue × muscle_contribution_weight` grouped by muscle, surfaced as a per-muscle bar list.
- **(b) Dedicated `/fatigue` route + page.** New blueprint, new template. Houses the per-muscle breakdown and the SFR card(s). The existing badge on `/session_summary` and `/weekly_summary` stays as-is and gains a "View per-muscle breakdown →" link (`BRAINSTORM.md §7` Option C).
- **(c) Per-muscle MEV/MAV/MRV defaults.** Hardcoded constants per `BRAINSTORM.md §5` table. No UI override (carry forward Phase 1's D2 stance: defaults only in V2).
- **(d) Stimulus-to-Fatigue Ratio (SFR) card(s).** Reuses `effective_sets` output as the stimulus proxy; divides by the Phase-1 fatigue score. Two cards rendered side-by-side (one for planned, one for logged) per (e). Display with a sentinel for the `fatigue == 0` case (per `BRAINSTORM.md §16.1` SFR test row).
- **(e) Planned + Logged side-by-side rendering (EXPANSION vs original draft).** Every per-muscle bar shows two stacked sub-bars: one from `user_selection` (planned), one from `workout_log` (logged for the selected window). SFR also renders twice. Owner-locked at Stage 0; original doc had this as Phase 3 (D2.5 carry-forward). Doubles Stage 2 UI surface area — see chapter table in §5.
- **(f) Period selector on day one (EXPANSION vs original draft).** A dropdown at the top of `/fatigue` toggles aggregation window: **this session**, **this week**, **last 4 weeks**. Owner-locked at Stage 0; original doc had this as a §4 stretch decision. Requires new 4-week aggregation code (does not exist anywhere else in the app) — see chapter table in §5.
- **(g) Bar sort order.** Bars sorted by **% of MRV, highest first** (most stressed muscle floats to the top). Owner-locked at Stage 0; original doc had this as §4 stretch.

Seven concrete additions, all additive, no schema change, no API.

---

## 3. Deferred to Phase 3 or later

Explicitly out of Phase 2 Path 1 scope, kept on file:

- **Systemic + Joint channels** (`BRAINSTORM.md §4.3` Channel B, §4.4 Channel C). Local-first ships the largest single piece of user value; the other two channels can layer in once the per-muscle UX is validated.
- **Decay model** (`BRAINSTORM.md §4.5`). Cheap to add later (one function with τ per channel); expensive to debug if shipped wrong. Phase 1's D6 lock applies forward.
- **%1RM path** (`BRAINSTORM.md §3.2`). Requires populated `user_profile` reference lifts — `data-audit.md` recorded zero usable rows at Phase 1 baseline; the data does not yet exist.
- **Technique modifier** (`BRAINSTORM.md §3.4`). Phase 1's D7 lock applies forward — we still don't capture the data.
- **Calibration table** (`user_fatigue_thresholds`). **First schema change in the feature** — belongs to Phase 3 and triggers the `BRAINSTORM.md §18` rollback escalation.
- **`/api/fatigue/*` endpoints.** Phase 1's D9 lock applies forward. Revisit only when a client genuinely needs JSON (e.g. a future mobile companion or an external integration).
- **Per-muscle SFR** (D2.6 stretch). Page-level SFR ships in Path 1; per-muscle SFR card-per-muscle stays deferred — feasibility check moves into Stage 1 dependency review.
- **Catalog cleanup of `movement_pattern` NULLs** (454/1897 rows). Movement pattern is not used by per-muscle math, so Phase 2 ships without these cleaned. Track as a separate data-quality task.
- **Plan-projection mode in a dedicated route** (`BRAINSTORM.md §9` Phase 3). Subsumed by the Phase-1 D10 override; planned + logged side-by-side (now in Path 1) is the modern equivalent and removes the need for a separate projection toggle.

**Moved INTO Phase 2 Path 1** (were previously deferred in the draft): logged-data path (D2.5), period selector (was §4 stretch).

---

## 4. Decisions — Stage 0 LOCKED 2026-05-23

Same shape as `PLANNING.md §0.1` and `BRAINSTORM.md §13` / §24.A. **All D2 rows locked by owner walk on 2026-05-23.** Sync back to `BRAINSTORM.md §13` shipped with PR #33 as the new `§13.1 Phase 2 Decision Log` block (Phase 1 D1–D13 rows untouched) — no further Stage 1 work required on the sync.

| # | Decision | Locked choice | Notes |
|---|---|---|---|
| **D2.1** | Channel split for Phase 2 | ✅ **Local-only (Channel A)** | §2(a). Systemic + Joint stay deferred to Phase 3. |
| **D2.2** | Page placement | ✅ **Dedicated `/fatigue` + keep existing badge with a link** (Option C from `BRAINSTORM.md §7`) | Embed-only would crowd the summary cards; dedicated-only would orphan the badge. |
| **D2.3** | Threshold source | ✅ **Hardcoded `BRAINSTORM.md §5` defaults; no UI override in V2** | Carries forward Phase 1's D2 stance. Calibration table is Phase 3. |
| **D2.4** | Sets basis for per-muscle channel | ✅ **Raw sets** (carry forward Phase 1 D3 override) | Per-muscle channel needs to be CountingMode-invariant for the same reason the global badge is — fatigue has its own multipliers and shouldn't double-count effort. |
| **D2.5** | Data scope | ✅ **Planned + Logged side-by-side** (EXPANSION vs draft recommendation of planned-only) | Owner picked richer view on day one. Doubles UI surface area + Stage 2 chapter count — see §5. |
| **D2.6** | SFR denominator | ✅ **Global fatigue (Phase 1 score) for the page-level SFR card(s); per-muscle SFR remains deferred** | Two SFR cards (planned + logged) on the page per D2.5. Per-muscle SFR card-per-muscle is Phase 3 unless Stage 1 dependency review surfaces a cheap path. |
| **D2.7** | Ship `/api/fatigue/*` in Phase 2? | ✅ **Skip** (carry forward Phase 1 D9) | Page is server-rendered; no client needs JSON. SQL-injection surface stays at zero. |
| **D2.8** | Any schema touch in Phase 2? | ✅ **No** — additive only | First schema change is Phase 3 territory by design. If a Phase 2 chapter wants a table, that chapter does not belong in Phase 2. |
| **D2.9** | Where does per-muscle data come from? | ✅ **Reuse `effective_sets`-style per-muscle aggregation** — query both `user_selection` (planned) and `workout_log` (logged) with the fatigue-relevant columns | Avoids forking a parallel pipeline; honors D13 (don't reuse aggregated rows — re-query). Two queries now (planned + logged), one per data source. |
| **D2.10** | Copy boundaries | ✅ **Same as Phase 1** — descriptive, no "MRV"/"MEV" in user-facing copy; bands stay neutral ("above the typical recoverable range") | `BRAINSTORM.md §11 Q7` + Phase 1 §3.3 verified non-prescriptive copy as a hard gate. |

Stretch decisions also locked at Stage 0:
- ✅ Per-muscle bar sort: **by % of MRV, highest first** (most stressed surfaces first).
- ✅ Period selector: **ship on day one** — dropdown with this-session / this-week / last-4-weeks (EXPANSION vs draft recommendation of single-period MVP).
- ⏳ Per-muscle empty-state UX (all-zero bars vs collapsed empty-state copy): deferred to Stage 2.4 implementation choice — non-blocking, owner can decide at template draft time.

**New decision surfaced at Stage 0 (not in original draft):**
- ✅ **Catalog data-quality re-scope** — hybrid approach. Clean only the **633 `primary_muscle_group` NULLs** (Stage 1 prerequisite) since per-muscle math depends on them. Defer cleanup of the 454 `movement_pattern` NULLs since per-muscle math does not use that column. Surfaced by Codex review 2026-05-23.

**Stage 1 cleanup design (locked at execution time 2026-05-23):**
- Inference rule: tokenize `exercise_name`, match against `utils.constants.MUSCLE_ALIAS` ∪ `MUSCLE_GROUPS` (longest-alias-first, word-boundary regex). 132 of 633 rows resolved to a real muscle this way (Gluteus Maximus 45, Hamstrings 16, Chest 13, Latissimus Dorsi 10, Lower Back 8, Neck 8, Trapezius 6, Biceps 5, Quadriceps 4, Forearms 4, Rectus Abdominis 4, Calves 4, Triceps 3, External Obliques 2).
- Remaining 501 unmatched rows assigned the sentinel value **`"Unassigned"`**. All 501 are dormant catalog entries (zero appear in `user_selection` at cleanup time — verified by joined-NULL audit).
- `"Unassigned"` added to `utils/volume_taxonomy.COARSE_TO_BASIC` → `"Abdominals"` and `COARSE_TO_REPRESENTATIVE_ADVANCED` → `"upper-abdominals"` so volume-rollup invariants stay satisfied. Comments inline mark both as Stage 1 placeholders. **Stage 2 fatigue per-muscle math should treat `"Unassigned"` the same as a NULL bucket** (display in its own bar, no rollup into a real muscle's MEV/MAV/MRV).
- Reproducer script: `scripts/fatigue_stage1_cleanup.py` (idempotent — a second run touches zero rows). Dry-run twin: `scripts/fatigue_stage1_cleanup_dryrun.py`.
- Regression test: `tests/test_catalog_invariants.py::test_catalog_primary_muscle_group_has_no_nulls`.

---

## 5. Proposed staged implementation plan

Mirrors `PLANNING.md`'s stage shape. No tasks are pre-checked; this is a forecast, not a commitment.

### Stage 0 — Lock D2.x decisions (humans only, no code) — ✅ CLOSED 2026-05-23
- Walked D2.1–D2.10 + stretch decisions + catalog re-scope. Every row ticked — see §4.
- **Stage 0 → Stage 1 handoff complete:** Sync of locked decisions into `BRAINSTORM.md §13.1 Phase 2 Decision Log` shipped with PR #33 (2026-05-23). Phase 1 D1–D13 rows preserved untouched.

### Stage 1 — Pre-development prerequisites (no app code; one DB write for catalog cleanup) — ✅ CLOSED 2026-05-23
All prerequisites complete on local branch `feat/fatigue-meter-phase-2` (Stage 1 close commit not yet pushed). Stage 2 implementation remains gated on an explicit owner "start Stage 2" greenlight.
- ✅ **Re-verified post-Phase-1 baseline** at Stage 1 entry on `main` @ 24c6f46: pytest 1350 passed (~2m 53s). Delta from the 2026-05-21 1374 baseline is the `tests/test_filter_cache.py` removal in commit 6d87284 (KI-001 dormant code) partially offset by `test_profile_estimator.py` / `test_user_profile_routes.py` / `test_workout_log_routes.py` additions across PR #17/#18 + body-composition follow-ups. See `CLAUDE.md §5`.
- ✅ **Data audit refresh** — re-count confirmed 633 `primary_muscle_group` NULLs and 454 `movement_pattern` NULLs in the catalog at Stage 1 entry (matches the 2026-05-23 Stage 0 close numbers). `user_selection` join-NULL audit recorded zero overlap with the unmatched 501 sentinel rows.
- ✅ **Catalog cleanup pass — 633 `primary_muscle_group` NULLs eliminated.** Inference rule (longest-alias-first, word-boundary regex against `utils.constants.MUSCLE_ALIAS` ∪ `MUSCLE_GROUPS`) resolved 132 of 633 rows to real muscles per the §4 distribution table; the remaining 501 dormant catalog rows received the sentinel value `"Unassigned"`. `movement_pattern` cleanup remains deferred per §4 catalog row. **Pre-flight backup was taken first** (see next item). Regression test `tests/test_catalog_invariants.py::test_catalog_primary_muscle_group_has_no_nulls` added and green; post-cleanup pytest 1351 passed (~2m 55s).
- ✅ **Pre-flight backup** captured via `POST /api/backups` — backup id **5**, label `pre-fatigue-meter-phase-2-2026-05-23`.
- ✅ **Dependency check** — confirmed Phase 2 needs no new Python deps. Chart strategy: inline SVG bars (matches `volume_splitter` precedent and `BRAINSTORM.md §11 Q6` — no new chart library).
- ~~**Sync Stage 0 decisions into `BRAINSTORM.md §13`** as a new Phase-2 block.~~ ✅ Already shipped with PR #33 (commit 24c6f46) as `§13.1 Phase 2 Decision Log`. No Stage 1 action required.
- ✅ **Feature branch** `feat/fatigue-meter-phase-2` created and now holds the Stage 1 close commit.
- ✅ **Exit recorded:** baseline (1350 → 1351) + data-audit numbers + catalog cleanup commit + backup id 5 + branch `feat/fatigue-meter-phase-2` all on record above. BRAINSTORM sync was already out of scope (PR #33). **Stage 2 implementation must not begin until owner says "start Stage 2."** Stage 2 fatigue per-muscle math must continue to treat `"Unassigned"` as its own bucket — do not fold it into Abdominals MEV/MAV/MRV (see §4 Stage 1 cleanup design note).

### Stage 2 — Implementation chapters (Path 1 — 8 chapters)
Each chapter is a single small commit with its own gate, matching Phase 1's pattern. Path 1 expansion of D2.5 (planned+logged) and the period selector push chapter count from the original 6 to 8.

| Chapter | Goal | Net new files | Net edited files |
|---|---|---|---|
| 2.1 | Extend `utils/fatigue.py` with **per-muscle planned-side accumulator** (pure functions; no DB). | — | `utils/fatigue.py` |
| 2.2 | Add **logged-side per-muscle accumulator + multi-window aggregation** (this-session / this-week / last-4-weeks) to `utils/fatigue.py`. Pure functions; no DB. The 4-week aggregator is genuinely new — no other module computes it. | — | `utils/fatigue.py` |
| 2.3 | Unit tests for per-muscle math, logged-side math, and all three period windows (extend `tests/test_fatigue.py`). | — | `tests/test_fatigue.py` |
| 2.4 | Add `routes/fatigue.py` blueprint + `templates/fatigue.html` skeleton + period-selector query-param handling. Register in `app.py` AND `tests/conftest.py` (the #1 testing pitfall — Phase 1 R1). Use `success_response()` for any JSON the template inlines via a route helper; no `/api/*` route. Route handler queries both `user_selection` (planned) and `workout_log` (logged) per D2.9. | `routes/fatigue.py`, `templates/fatigue.html` | `app.py`, `tests/conftest.py` |
| 2.5 | Per-muscle bar partial rendering **planned + logged side-by-side sub-bars** (D2.5) sorted by % of MRV (locked stretch). SCSS color/state additions for bars including dual-bar layout. | `templates/_fatigue_muscle_bar.html`, possibly `static/js/modules/fatigue.js` if a real chart lib is in play (otherwise inline SVG) | `scss/_fatigue.scss`, `scss/custom-bootstrap.scss` (extend `@import` block), `templates/fatigue.html` |
| 2.6 | **Two SFR cards** (planned + logged) at top of page, matching D2.5 dual rendering. Handle `fatigue == 0` sentinel for both. | — | `templates/fatigue.html`, `scss/_fatigue.scss` |
| 2.7 | **Period selector frontend** — dropdown + state management (query param round-trip). Wire to backend query parameter from 2.4. Empty-state handling per period (e.g. "no logged sessions yet this week"). | — | `templates/fatigue.html`, `static/js/modules/fatigue.js` (if created) |
| 2.8 | Nav link + dark-mode parity + copy review + "View per-muscle breakdown →" link from the existing summary badges back to `/fatigue`. Docs + CHANGELOG + test counts + flip this `PHASE2_PLANNING.md` status banner to SHIPPED. | — | `templates/base.html`, `templates/_fatigue_badge.html` (link), `CLAUDE.md §5`, `docs/CHANGELOG.md`, `docs/fatigue_meter/PHASE2_PLANNING.md`, run `/build-css` |

Per-chapter gates follow Phase 1 §2.X exactly: pytest delta documented, targeted E2E spec green, no test-count regression in unrelated files, code-reviewer pass on diff before merge.

### Stage 3 — Verification & merge gate (95% confidence checkpoint) — ✅ CLOSED 2026-05-24
Same shape as `PLANNING.md §3`. Adds two Phase-2-specific items:
- **Per-muscle data-fidelity sanity check.** Per-muscle scores for a known routine match a hand-calculated value across at least 3 muscles. ✅ Verified during Stage 2 implementation (`tests/test_fatigue.py` + `tests/test_fatigue_routes.py`, 91 new cases).
- **Link reciprocity.** Badge → `/fatigue` and `/fatigue` → summary pages both load without console errors. ✅ Verified by `e2e/fatigue.spec.ts` (8/8 Chromium green).

**Verify-suite result on `main` @ d5b80bf:**
- **pytest**: 1442 passed (~2m 55s) — full suite green, matches Stage 2 baseline.
- **Playwright Chromium full suite**: 449 passed / 13 failed / 17 did-not-run (~12.5m). The 13 + 17 reds match the `CLAUDE.md §5` documented pre-existing baseline exactly (2 `workout-plan.spec.ts` `#muscleModeToggle` off-viewport at 1280; 10 sub-pixel `visual.spec.ts` desktop drifts on welcome/workout-plan/workout-log/progression/volume-splitter with zero Stage-2 surface; 1 `visual-baseline-thumbnails.spec.ts` plan thumbnail; 17 `visual-baseline-thumbnails.spec.ts` cases needing the seed-DB preflight from `e2e/scripts/prepare_visual_db.py`). **Zero new Stage-2 reds.** The 12 weekly-summary + session-summary visual baselines re-snapshotted during Stage 2 implementation are now passing (`449 = 437 + 12`).

Pre-merge restore point retained: backup id 5, label `pre-fatigue-meter-phase-2-stage-2-merge-2026-05-23`, created 2026-05-23T23:39:09.502079.

### Stage 4 — Post-merge calibration window — ⏳ OPEN 2026-05-24
≥2 weeks of real use before any per-muscle threshold tweaks. Same "no tuning without ≥2 disagreements" bar as Phase 1 §4.2. Earliest close date: **2026-06-07**.

---

## 6. Files likely touched

Phase 2 MVP is **purely additive** — no existing route handler logic changes, no schema, no `utils/effective_sets.py` edit.

### ADD
| File | Purpose |
|---|---|
| `routes/fatigue.py` | New blueprint; one route (`GET /fatigue`); no `/api/*`. |
| `templates/fatigue.html` | Per-muscle breakdown + SFR card. Extends `base.html`. |
| `templates/_fatigue_muscle_bar.html` | One row per muscle. Reused inside the page; possibly inlined depending on the SCSS pattern. |
| `static/js/modules/fatigue.js` | **Only if a real chart lib is reused** from elsewhere in the project. Otherwise inline SVG bars and skip this file (matches `BRAINSTORM.md §8` "inline SVG to avoid new deps"). |
| `e2e/fatigue.spec.ts` | Page-load, per-muscle bars, SFR card, empty-state, dark mode. |

### EDIT
| File | Why |
|---|---|
| `utils/fatigue.py` | Per-muscle accumulator functions (pure; no DB). |
| `tests/test_fatigue.py` | Per-muscle math + SFR tests. |
| `app.py` | Register `fatigue_bp`. |
| `tests/conftest.py` | Register `fatigue_bp` in the test app fixture. **Phase 1 R1 — missing this = silent 404s.** |
| `templates/base.html` | Nav link to `/fatigue`. |
| `templates/_fatigue_badge.html` | Add "View per-muscle breakdown →" link to the new page. |
| `scss/_fatigue.scss` | Per-muscle bar color states, dark-mode aware. |
| `scss/custom-bootstrap.scss` | If a new partial is split out, add `@import`. |
| `static/css/bootstrap.custom.min.css` | Rebuilt by `/build-css`. |
| `CLAUDE.md §5` | Test count line update + date. |
| `docs/CHANGELOG.md` | Phase 2 entry. |
| `docs/fatigue_meter/PHASE2_PLANNING.md` | Flip status banner at Stage 2.6. |

### NOT touched in Phase 2 (regression flag if any of these change)
`utils/effective_sets.py`, `utils/session_summary.py`, `utils/weekly_summary.py`, `utils/database.py`, `utils/db_initializer.py`, `utils/program_backup.py`, `utils/auto_backup.py`, `data/database.db` (schema), `scripts/fatigue_calibration_report.py::SCENARIOS`.

---

## 7. Test plan

Builds on Phase 1's `tests/test_fatigue.py` and Phase 1's E2E baselines (`CLAUDE.md §5`).

### Unit tests (extend `tests/test_fatigue.py`, pure-math, no DB)
- Per-muscle accumulator (**planned side** — `user_selection`):
  - Single exercise with one primary muscle → that muscle's score = per-set × sets; all other muscles = 0.
  - Two exercises hitting overlapping muscles → per-muscle scores sum correctly.
  - Exercise with NULL `primary_muscle` → contribution falls into `unassigned` bucket; per-muscle total still computed; warning logged.
  - Secondary / tertiary muscle weighting matches `effective_sets.py` contribution constants.
- Per-muscle accumulator (**logged side** — `workout_log`, NEW per D2.5):
  - Single logged session with one exercise → per-muscle scores match the planned-side math for the same rows.
  - Mixed completed + skipped sets → only scored sets contribute; per-muscle total reflects actual completion.
  - Empty `workout_log` for selected period → all muscles return 0; route still renders empty-state.
- Period aggregation (NEW per period selector):
  - `this_session` window → only rows with the latest session date are counted.
  - `this_week` window → rows from Mon–Sun of the current ISO week.
  - `last_4_weeks` window → rolling 28-day count, boundary day inclusive.
  - Boundary tests: midnight rollovers, week-start day, daylight-saving day if applicable.
- SFR (×2 cards — planned + logged):
  - `fatigue == 0` → SFR returns sentinel (`None` or documented marker), not crash, not `inf`.
  - `fatigue > 0, stimulus = 0` → SFR returns `0`.
  - Both positive → ratio matches expected to 3 decimal places on a hand-calculated example.
  - Planned and logged SFR computed independently from each side's accumulator output.
- Threshold classification (per-muscle bands):
  - Muscle below MEV → `light`.
  - Muscle in MAV → `moderate`.
  - Muscle above MRV → `very_heavy`.
  - Boundary values deterministic per docstring.
  - Sort assertion: bars returned in descending `% of MRV` order (locked stretch).

### Integration (route handler returns correct template context)
- `GET /fatigue` against seeded `user_selection` + `workout_log` → 200, template context contains `muscles_planned`, `muscles_logged`, `sfr_planned`, `sfr_logged`, `period`, `period_label`, and the canonical `fatigue_*` keys.
- `GET /fatigue?period=session` / `?period=week` / `?period=4week` → 200 each, aggregation matches the requested window.
- `GET /fatigue?period=invalid` → 400 via `error_response()` OR silent fallback to `week` (decide at Stage 2.4 — pick whichever matches existing route conventions).
- `GET /fatigue` against empty `user_selection` AND empty `workout_log` → 200, empty-state copy rendered for both sides, no crash.
- `GET /fatigue` with planned populated but empty logged → 200, planned bars render, logged side shows "no logged sessions in this window".

### E2E (`e2e/fatigue.spec.ts`)
- Page loads with no console errors.
- Per-muscle bars render as **side-by-side planned + logged pairs** and are sorted by % of MRV.
- **Period selector dropdown** changes window; bars re-render; URL query param updates.
- Two SFR cards visible (planned + logged) with label, ratio, explanation copy.
- Empty-state paths:
  - Brand-new DB → page does not crash, bars area shows "No planned exercises yet" + "No logged sessions yet".
  - Planned-only DB (no logs) → planned side renders, logged side shows empty-state copy.
- Dark-mode parity across all bands and both sub-bars.
- Link from `/session_summary` badge → `/fatigue` works (and vice-versa).

### Targeted regression sweep (Phase 1 §16.4 + new spec)
- `e2e/summary-pages.spec.ts` — touched indirectly via the new "View per-muscle breakdown" link in the badge partial.
- `e2e/workout-plan.spec.ts`, `e2e/workout-log.spec.ts` — sibling pages.
- `e2e/accessibility.spec.ts` — new DOM means new ARIA assumptions.
- `e2e/fatigue.spec.ts` — the new spec itself.

### Manual smoke (browser walk, Phase 1 §3.5 pattern)
- All navbar routes load without console errors (now 10 with `/fatigue`).
- Add exercise → badge + per-muscle bars update consistently.
- Restore the pre-Phase-2 backup → every page loads.
- 375px viewport: per-muscle bars wrap cleanly; no horizontal overflow.
- Dark mode: bar fills + thresholds readable across all bands.

---

## 8. Rollback & safety

### Phase 2 MVP rollback
Phase 2 MVP is purely additive (no schema change). Rollback path matches Phase 1:
- `git revert <merge-commit>` per chapter or per merge. Because each chapter has a green gate, partial rollback is safe.
- `static/css/bootstrap.custom.min.css` rebuilds from SCSS — revert SCSS + rerun `/build-css` to undo Chapter 2.4 / 2.5.
- No DB migrations to undo (no schema changes in Phase 2 MVP).

### Pre-flight backup
Take a fresh manual backup via `POST /api/backups` at Stage 1 (label `pre-fatigue-meter-phase-2-YYYY-MM-DD`). **Phase 1's backup id `5` is not sufficient** — it predates the body-composition + workout-cool work that landed between Phase 1 merge and Phase 2 start; restoring it would discard substantial unrelated user state.

### Schema-creep guardrail
If a Phase 2 chapter discovers it wants a table (e.g. a per-muscle override row, an SFR snapshot), **stop and escalate to Phase 3 framing**. Phase 2's "purely additive, no schema" stance is the entire reason rollback is cheap. The first schema change ships in Phase 3 with `BRAINSTORM.md §18` becoming load-bearing (document down SQL inline, audit `utils/program_backup.py` for new-table inclusion, manual backup before merge).

### Emergency rollback path
- Restore the pre-Phase-2 labeled backup via `POST /api/backups/<id>/restore`.
- `git revert <merge-commit>` on `main`.
- Investigate offline.

---

## 9. Explicit non-goals (Phase 2)

Carry-forward from `BRAINSTORM.md §1` and §22, plus Phase-2-specific items:

- **Never blocks a user action.** Per-muscle bars and SFR are descriptive only.
- **No auto-deload, no auto-adjust, no prescriptive copy.** "Above MRV" stays out of user-facing copy; use "above the typical recoverable range" or color + number with no verb.
- **No modal interrupts.** No popups for "you're over MRV"; soft inline only.
- **No HRV / soreness / readiness integrations** (would need wearables or daily opt-in inputs).
- **No multi-user comparisons** (single-user app).
- **No predicting injury risk** (medical claim).
- **No notifications / push reminders.**
- **No sharing / exporting fatigue charts** to external services.
- **Phase 2 does not retire the Phase 1 badge.** Both coexist — the badge stays on the summary pages and gains a link to the new page.
- **No schema change in Phase 2.** First schema change is Phase 3. Path 1's planned+logged side-by-side is achieved by querying existing tables (`user_selection` + `workout_log`), not by adding a new one.
- **No `/api/fatigue/*` endpoints in Phase 2** (carry forward D9).
- **No %1RM path in Phase 2** (Phase 3 — requires populated `user_profile` reference lifts).
- **No decay model in Phase 2** (Phase 3).
- **No technique modifier in Phase 2** (`BRAINSTORM.md §3.4` Phase 4 / opt-in only).
- **No per-muscle SFR cards in Phase 2** (D2.6 — page-level SFR only, two cards per D2.5 dual rendering).
- **No catalog `movement_pattern` cleanup in Phase 2** — Stage 1 cleans `primary_muscle_group` only.
- **Per-muscle bars are not a coaching prescription.** They describe distribution; they do not recommend a rebalance.

---

## 10. Open follow-ups / parking lot

Tracked here so they don't get lost during Stage 1 / Stage 2 / Stage 3:
- **Phase 3 — per-muscle MEV / MAV / MRV defaults for the six unranked labels.** Stage 2 shipped BRAINSTORM §5 verbatim (12 muscles), per owner Stage 0 decision. Six canonical catalog labels still render at the bottom with neutral state and "—" for the % column: **Front-Shoulder, Rear-Shoulder, Lower Back, Hip-Adductors, Middle-Traps, Neck** (plus the `Unassigned` sentinel which is intentional and not a threshold gap). Resolution path: owner supplies vetted MEV / MAV / MRV per muscle, then either (a) extend `MUSCLE_VOLUME_LANDMARKS` in `utils/fatigue.py` directly, or (b) introduce the `user_fatigue_thresholds` Phase-3 calibration table per `BRAINSTORM.md §6 Option 3`. Per Stage 0 policy, do not invent thresholds without a fresh owner override.
- Per-muscle SFR (D2.6) — page-level SFR shipped in Stage 2; per-muscle SFR card-per-muscle stays deferred. Feasibility hinges on `effective_sets.py` exposing per-muscle stimulus in a shape the SFR card can consume without a parallel pipeline.
- "View per-muscle breakdown →" link copy — descriptive only, never "View MRV breakdown" (D2.10).
- Recovery of the deferred `BRAINSTORM.md §10` partial-week handling for the per-muscle view ("X / N expected for this point in week"). Phase 3 polish item.
- Catalog `movement_pattern` cleanup (454 NULLs) — not blocking Phase 2 but worth scheduling as a separate data-quality task before any future feature that depends on movement pattern.
- ~~BRAINSTORM.md §13 sync — locked Stage 0 decisions must be propagated as a new Phase-2 block (Stage 1 prerequisite per §5).~~ ✅ Shipped with PR #33 (commit 24c6f46) — see `BRAINSTORM.md §13.1`.

---

## 11. Companion file references

| File | Relation |
|---|---|
| [`PLANNING.md`](PLANNING.md) | Phase 1 source-of-action; Stage 5/6 now point here. |
| [`BRAINSTORM.md`](BRAINSTORM.md) | Source-of-thought; full historical context for §4/§5/§7/§9/§11/§13/§20 Phase 2 matrix. |
| [`calibration-notes.md`](calibration-notes.md) | Stage 4 close 2026-05-20 — why thresholds are stable enough to invest in resolution next. |
| [`STAGE4_PARKED_HANDOFF.md`](STAGE4_PARKED_HANDOFF.md) | Superseded by the 2026-05-20 owner-approved Stage 4 close; preserved for history. |
| [`../LEFTOVERS_BY_PRIORITY.md`](../LEFTOVERS_BY_PRIORITY.md) row #15 | Tracks Phase 2 as owner-gated; points back here. |

---

*End of PHASE2_PLANNING.md. Stage 0 + Stage 1 closed 2026-05-23. Stage 2 implementation completed 2026-05-23 on branch `feat/fatigue-meter-phase-2-stage-2`, merged to `main` 2026-05-23 via PR #35 (squash commit `d5b80bf`). Stage 3 verify-suite gate closed 2026-05-24 on `main` (pytest 1442 passed; Playwright Chromium 449 passed / 13 failed / 17 did-not-run — reds match documented pre-existing baseline exactly, zero new Stage-2 reds). Stage 4 calibration window opened 2026-05-24; earliest close 2026-06-07. Path 1 ships dedicated `/fatigue` route, dual planned + logged per-muscle bars sorted by % MRV, two SFR cards with `fatigue == 0 → "—"` sentinel, period selector (`this session` / `this week` / `last 4 weeks`), nav link in Analyze dropdown, badge "View per-muscle breakdown →" link. Phase 1 surface preserved byte-identical. Phase-3 follow-up: vetted MEV / MAV / MRV defaults for the six unranked labels (Front-Shoulder, Rear-Shoulder, Lower Back, Hip-Adductors, Middle-Traps, Neck) — see §10.*
