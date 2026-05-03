# Fatigue Meter — Feature Brainstorm

**Status:** brainstorm / pre-plan. Multi-LLM review document.
**Date drafted:** 2026-04-30
**Source inspiration:** Stimulus-to-Fatigue Ratio discussion, YouTube `3vX2hAitKyQ` (Gemini summary in user prompt).
**Author goal:** add a "fatigue meter" view per session and per week so the user can see how demanding a designed plan is.

This document is a brainstorm, not a plan. It deliberately presents alternatives, gaps, and open questions for IDE-LLM review. **No code is to be written until a chosen approach is locked in via a follow-up PLANNING.md.**

---

## 1. Goal & Scope

### What the user wants
A "fatigue meter" that:
1. Reports total fatigue per session and per week.
2. Surfaces in `/session_summary` and `/weekly_summary`, possibly also as a dedicated tab.
3. Helps the user see whether a *planned* program is too demanding before logging it.
4. Reflects what was actually performed once logged.

### What this is NOT (non-goals)
- Not a coach. Effective-sets logic is informational per `utils/effective_sets.py:6-7`. Fatigue must follow the same rule: **never block, never auto-adjust, never gate user actions**. Surface signals only.
- Not a 1:1 import of the Gemini formula — see Section 3 critique.
- Not a CNS-fatigue lab simulator. Hypertrophy-relevant fatigue only.
- Not requiring new daily user input loops (soreness questionnaires every morning, etc.) unless explicitly opted in. The minimum-viable model uses only data we already capture.

### Success criteria
- A user looking at `/session_summary` for a brutal day and a deload day can tell which is which from the fatigue widget alone.
- A user designing a routine can see a projected fatigue score *before* training (using planned reps/sets/RIR) and adjust if it crosses a threshold.
- The model gives sensible answers on the edge cases listed in Section 10.

---

## 2. Existing Infrastructure — What We Can Reuse

The codebase already does most of the input-side work. The fatigue feature should be an **alternative aggregation** of the same inputs that drive effective sets, not a parallel data pipeline.

| Existing piece | Location | Reusable for fatigue? |
|---|---|---|
| RIR → effort factor buckets | `utils/effective_sets.py:64-69` (`EFFORT_FACTOR_BUCKETS`) | Yes — but fatigue uses a *different* curve (exponential near failure). |
| Rep-range buckets | `utils/effective_sets.py:75-81` | Yes — but fatigue weights *low* rep ranges higher (joint/CNS cost), inverse of the hypertrophy curve. |
| Muscle contribution weights | `utils/effective_sets.py:84-88` | Yes — for per-muscle local fatigue. |
| Weekly volume thresholds | `utils/effective_sets.py:91-96` | Reusable as a baseline, but fatigue needs its own thresholds (per-muscle MRV-style, plus systemic budget). |
| Movement-pattern taxonomy | `utils/movement_patterns.py` | Yes — to assign systemic/joint-stress weights per pattern. |
| `aggregate_session_volumes` / `aggregate_weekly_volumes` | `utils/effective_sets.py:402,454` | Pattern to copy: per-session result → weekly aggregation. |
| User profile reference lifts | `routes/user_profile.py` + `utils/profile_estimator.py` | Yes — to compute `%1RM` for a load multiplier when a reference lift exists. Falls back to rep-range proxy otherwise. |
| Workout log data | `workout_log` table | Provides actual reps/weight/RIR/scored reps per set. |
| User selection data | `user_selection` table | Provides planned reps/sets/RIR for *projected* fatigue. |

**Implication:** the fatigue module is mostly a `utils/fatigue.py` that reads the same inputs, applies a different weighting function, and aggregates.

---

## 3. Critique of the Gemini Formula

The Gemini summary captures the right *intuitions* but is too coarse and partly redundant with what we already compute. Issues:

### 3.1 "Base Exercise Score" — too coarse
A binary High (1.5) / Low (1.0) split throws away most of the information. We have movement_patterns + primary/secondary/tertiary muscles per exercise; we can derive a continuous "systemic load weight" instead of a 2-bucket flag.

**Replacement proposal:** per-pattern weights, e.g.
- `SQUAT`, `HINGE` (deadlift sub-pattern especially): 1.5–1.7
- `HORIZONTAL_PUSH` (compound: bench, dip), `HORIZONTAL_PULL` (row), `VERTICAL_PUSH` (OHP), `VERTICAL_PULL` (chin-up): 1.2–1.3
- `UPPER_ISOLATION`, `LOWER_ISOLATION`: 0.8–1.0
- Core static/dynamic: 0.7–0.9

Or, derived rather than hardcoded: count of muscles touched (primary + secondary + tertiary) × stability flag.

### 3.2 "Load Multiplier" — uses rep range as a load proxy, but we have actual loads
For exercises with a reference 1RM in `user_profile`, we can compute %1RM directly. Joint stress at 90% 1RM × 6 reps is materially different from 60% 1RM × 6 reps even though the rep range is identical.

**Replacement proposal:**
- If %1RM is available: use a piecewise multiplier (e.g., `<60%`: 0.9, `60–75%`: 1.0, `75–85%`: 1.15, `>85%`: 1.3).
- Else: fall back to a rep-range proxy (lower reps ⇒ higher multiplier), but flag the result as "estimated".

### 3.3 "Intensity Multiplier" — directionally right, refine the curve
Gemini's RIR=0 → 2.0×, RIR=1–2 → 1.2×, RIR=3+ → 1.0× is reasonable but jumps abruptly. Fatigue research suggests fatigue accumulates *exponentially* in the last 2–3 reps before failure. A smoother curve avoids cliff effects between RIR=2 and RIR=3.

**Replacement proposal:** continuous function with discrete-bucket fallback for tests.
- `intensity_factor(RIR) = 1.0 + 1.2 * exp(-0.7 * RIR)`
  - RIR=0 → 2.2
  - RIR=1 → ~1.60
  - RIR=2 → ~1.30
  - RIR=3 → ~1.15
  - RIR=5 → ~1.04
- Or buckets if simpler: `{0: 2.0, 1: 1.5, 2: 1.25, 3-4: 1.05, 5+: 1.0}`. Keep buckets for parity with `EFFORT_FACTOR_BUCKETS`.

### 3.4 "Technique Modifier" — we don't capture this
We don't currently log range of motion or eccentric tempo. Adding a per-set "technique" field is a meaningful UX cost (one more input per set) and likely won't be filled in honestly.

**Decision tree:**
- Phase 1: drop this multiplier entirely. Don't pretend to model what we don't measure.
- Phase 2 (optional): add an *optional* per-exercise default ("partial ROM" / "full ROM") at the routine level, not per set, so the user sets it once.
- Phase 3 (optional): a session-level "form was rough today" toggle that applies a global × 1.1.

### 3.5 What Gemini omits entirely
1. **Recovery decay between sessions.** A heavy back day Monday and another Wednesday is more fatiguing than the same load split Mon/Sat. Cumulative weekly fatigue without decay over-counts.
2. **Per-muscle fatigue.** Total fatigue is less actionable than "your hamstrings are at 95% of capacity, your chest is at 40%."
3. **Frequency cost.** Hitting a muscle 4× / week at moderate sets is different from 2× / week at high sets, even at equal weekly volume.
4. **Stimulus-to-Fatigue Ratio (SFR).** The whole point of the source video is the *ratio*, not raw fatigue. Two programs with identical fatigue but different stimulus are not equally good.

These omissions are the most important corrections.

---

## 4. Proposed Model — Layered, Reuses Existing Inputs

Three independent fatigue channels, each computed per set and aggregated per session and per week.

### 4.1 Per-set fatigue (the unit)
```
set_fatigue = base_pattern_weight
            × load_multiplier      (from %1RM if available, else rep-range proxy)
            × intensity_multiplier (from RIR, exponential near failure)
            × duration_multiplier  (optional Phase 2 — drop sets, supersets, etc.)
```

This is the atomic unit. From here, three *channels* aggregate the same set with different weights:

### 4.2 Channel A — Local (per-muscle) fatigue
- Sum `set_fatigue × muscle_contribution_weight` across sets, grouped by muscle.
- Exposes: "biceps fatigue this week = 14.2 (high)", per the muscle's own threshold.
- Per-muscle thresholds inspired by RP-style volume landmarks: MEV / MAV / MRV. Stored as a constants table keyed by muscle, not hardcoded inline. *(See Section 5 for landmarks discussion.)*

### 4.3 Channel B — Systemic fatigue
- Sum `set_fatigue × pattern_systemic_weight` across all sets in a session/week.
- `pattern_systemic_weight` is high for big compounds (squat/hinge/heavy compound press), near zero for isolation (curls, lateral raises).
- Exposes: "session systemic load = 18.4 / 25 budget".
- Budget is a single per-user number, with a default and an option to recalibrate from history (see Section 6).

### 4.4 Channel C — Joint / CNS stress
- Sum `set_fatigue × joint_stress_weight × heavy_load_kicker` where the kicker only fires above ~80% 1RM (or low rep proxy).
- `joint_stress_weight` is highest for high-load compounds with long lever arms (deadlift, squat, OHP, bench) and lowest for machine isolation work.
- Exposes the "this week is heavy on joints" signal independent of total volume.

Three channels avoids the trap of one composite number that hides which dimension is overloaded.

### 4.5 Weekly aggregation with decay (Phase 2)
Fatigue from earlier in the week shouldn't count 1:1 against today. A simple model:
```
weekly_fatigue(t) = Σ session_fatigue(s) * exp(-(t - s) / τ)
```
where τ depends on channel:
- Local: τ ≈ 72 h (muscle protein turnover)
- Systemic: τ ≈ 48 h
- Joint/CNS: τ ≈ 96 h

Phase 1 can skip decay entirely (just sum). The decision: ship the simpler model first, add decay only if users find weekly numbers too inflated mid-week.

### 4.6 Stimulus-to-Fatigue Ratio (SFR)
We already compute effective sets (= stimulus proxy). The ratio
```
SFR = effective_sets / fatigue_score
```
is a single number that says "is this efficient programming?" Show it alongside the fatigue meter. A program with high fatigue *and* high stimulus is fine; high fatigue + low stimulus is junk volume.

This is arguably the most useful number in the whole feature, and it falls out for free.

---

## 5. Volume Landmarks (per-muscle thresholds)

For the local-fatigue channel to mean anything, we need per-muscle thresholds. The literature anchor is Renaissance Periodization-style landmarks:

- **MV** Maintenance Volume (sets/week)
- **MEV** Minimum Effective Volume
- **MAV** Maximum Adaptive Volume (sweet spot)
- **MRV** Maximum Recoverable Volume (where fatigue starts cratering progress)

Approximate set ranges (these are debated; treat as defaults with user override):

| Muscle | MEV | MAV | MRV |
|---|---|---|---|
| Chest | 8 | 12–16 | 22 |
| Back | 10 | 14–22 | 25 |
| Shoulders (side delt) | 8 | 16–22 | 26 |
| Biceps | 8 | 14–20 | 26 |
| Triceps | 6 | 10–14 | 18 |
| Quads | 8 | 12–18 | 20 |
| Hamstrings | 6 | 10–14 | 20 |
| Glutes | 0 | 4–12 | 16 |
| Calves | 8 | 12–16 | 22 |
| Abs | 0 | 6–25 | 25 |
| Traps | 0 | 8–14 | 26 |
| Forearms | 0 | 6–12 | 16 |

These are weekly **set** counts (raw or effective — design choice). Two reasonable interpretations:
1. **Apply to raw sets** — simpler, matches RP convention.
2. **Apply to effective sets** — internally consistent with the rest of the codebase. Probably the right call.

A user who blows past their MRV repeatedly should see a soft warning. Never blocking. Wording matters: "you're at 26 effective sets for hamstrings this week — above the typical recoverable range of 20" is informational; "TOO HIGH" is not.

---

## 6. Calibration — Per-User Budgets

Hardcoded thresholds will work for ~70% of users and badly mislead the rest. Three calibration options:

### Option 1 — Ship hardcoded defaults, let user edit
Default values per Section 5, exposed in `/user_profile`. Lowest implementation cost, biggest UX cost (user has to know what to put).

### Option 2 — Calibrate from history
After N weeks of logged data, compute the user's typical session/week fatigue and call that their baseline. Thresholds become "120% of your average week" rather than absolute numbers. Easier on the user, but requires N weeks before the meter is meaningful and gives wrong answers for users in a planned overreach phase.

### Option 3 — Both
Hardcode defaults; once 4+ weeks of data exists, offer a "calibrate from my history" button that overrides them. This is probably the right call for V2.

V1 should ship with Option 1 only.

---

## 7. UI / Placement Options

### Option A — Embed in existing summaries
Add a "Fatigue" card to `/session_summary` and `/weekly_summary` next to the existing volume blocks.

**Pros:** zero new navigation, immediate context next to volume. **Cons:** crowded pages get more crowded; mobile rendering already tight; mixes two metrics that need separate explanation.

### Option B — Dedicated `/fatigue` route
New blueprint, new tab, full page for the meter with all three channels and per-muscle breakdown.

**Pros:** room to explain the model, room for charts, separate concerns. **Cons:** another tab; users have to think to look there.

### Option C — Both (recommended)
Compact "fatigue badge" embedded in `/session_summary` and `/weekly_summary` (one number + color, click-through), full breakdown lives at `/fatigue`. Mirrors how the volume splitter works alongside summaries.

The badge should answer one question at a glance: "is this session/week heavier than my baseline?" Everything else lives on the dedicated page.

### Component sketch (recommended)
```
[ /weekly_summary ]
  ├─ existing volume cards
  ├─ NEW: Fatigue badge
  │       ├─ Total: 142 (typical week: 110)  [yellow]
  │       ├─ Systemic: 38/50  ▓▓▓▓▓▓▓░░░
  │       ├─ Joint:    22/30  ▓▓▓▓▓▓▓▓░░
  │       └─ "View per-muscle breakdown →" → /fatigue?period=week
  └─ ...

[ /fatigue ]
  ├─ Period selector (this session / this week / 4-week)
  ├─ Three channel meters (Local / Systemic / Joint)
  ├─ Per-muscle bar chart vs MEV/MAV/MRV
  ├─ Stimulus-to-Fatigue Ratio (single number, with explanation)
  └─ Per-session contribution table (which days drove fatigue)
```

---

## 8. Data Pipeline

### Inputs (read)
- `workout_log` — actual logged sets (for "what happened" mode)
- `user_selection` — planned sets (for "what's projected" mode, before logging)
- `exercise_database` — muscle assignments and pattern classification
- `user_profile` reference lifts — for %1RM derivation when present

### New persistence (write) — minimal
- **Phase 1:** No new tables. Compute on the fly per request, cache the result keyed by week.
- **Phase 2 (calibration):** A `user_fatigue_thresholds` table for per-user MRV overrides + per-channel budgets. One row per user (single user app, so effectively one row total).
- **Phase 3 (history):** A `fatigue_snapshots` table if we want trend charts over time, e.g. "your weekly systemic fatigue trended up 25% over the last 8 weeks". Optional.

### Module layout (proposed)
```
utils/fatigue.py              ← pure calculation, mirrors effective_sets.py shape
                                  (constants, dataclasses, per-set fn, aggregators)
routes/fatigue.py             ← /fatigue page + /api/fatigue/{session,week}
templates/fatigue.html        ← main page
templates/_fatigue_badge.html ← partial included by session/weekly summary templates
static/js/modules/fatigue.js  ← chart rendering (reuse Chart.js if already in use,
                                  otherwise inline SVG bars to avoid new deps)
tests/test_fatigue.py         ← per-set math, aggregations, edge cases
e2e/fatigue.spec.ts           ← landing, period switch, per-muscle drilldown
```

---

## 9. Phasing / MVP

### Phase 1 — MVP (the smallest shippable version)
- Single-channel "total fatigue" number per session and per week.
- Computed from existing `workout_log` data only.
- Surfaced as a badge in `/session_summary` and `/weekly_summary`.
- Hardcoded default thresholds; no calibration, no decay.
- 1 paragraph of "what this means" copy on each page.

This alone delivers ~60% of the user value at maybe 20% of the effort.

### Phase 2 — Three channels + dedicated page
- Local / Systemic / Joint split per Section 4.
- New `/fatigue` route with per-muscle breakdown.
- Per-muscle MEV/MAV/MRV thresholds via the constants table from Section 5.
- Stimulus-to-Fatigue Ratio shown alongside.

### Phase 3 — Projection mode + calibration
- Same model, but applied to `user_selection` (planned) so a user designing a routine sees projected fatigue *before* training it.
- "Calibrate from my last 4 weeks" button.
- Optional decay model.

### Phase 4 — Optional inputs
- Per-exercise technique flag (full ROM / partial), set once per exercise.
- Per-session "form was rough" toggle.
- Soreness / readiness check-in (opt-in; doesn't change calculations, just annotates the chart).

---

## 10. Edge Cases & Gotchas

- **Bodyweight exercises with no `weight` value.** %1RM is undefined. Fall back to rep-range proxy and flag as estimated.
- **No RIR logged.** Most legacy data lacks RIR. Default the intensity multiplier to 1.0 (treat as moderate) and flag the row in the contribution table.
- **Cardio / conditioning entries.** If they exist in `workout_log`, exclude — this model is resistance-training-only.
- **Drop sets / rest-pause / supersets.** These multiply effective work in a single "set" entry. Phase 1 ignores. Phase 2 should at least apply a `× 1.3` for sets flagged as drop-set/rest-pause if such a flag exists; otherwise punt.
- **Supersets** (`user_selection.superset_group`) — biomechanically antagonistic supersets reduce systemic fatigue per unit time, but don't reduce per-set fatigue meaningfully. Probably ignore.
- **Partial-week views.** If today is Tuesday, "weekly fatigue" should not be compared to a full-week MRV. Always show "X / N expected for this point in week" or scope visualizations to "last 7 days" rather than calendar week.
- **Exercise with primary muscle = `null` or junk.** Already a known data-cleanliness issue in places. Fatigue contribution falls back to "unassigned" bucket; warn if total > 5% of session.
- **Plan-projection vs logged divergence.** If the user logs *very* differently from the plan, surfacing both numbers (planned 110 vs actual 145) is more useful than blending them.
- **Long sessions where user took half the day off.** Fatigue per session assumes one continuous session. We don't track session duration, so we can't detect this. Out of scope.

---

## 11. Open Questions for Review

1. **Channels — three or one?** Three (local/systemic/joint) is the right model; one is the right MVP. Where do we draw the Phase 1 line?
2. **Thresholds — RP-style fixed vs user-calibrated?** Section 6 leans Option 3, but a simpler "always calibrate from user data after 4 weeks" might be the right answer if we accept a 4-week empty state.
3. **Effective vs raw sets as the basis?** Section 5 leans effective for internal consistency. Confirm.
4. **`utils/effective_sets.py` constants — reuse or fork?** The fatigue module needs *different* curves (especially RIR → multiplier). Do we (a) extend `effective_sets.py` with parallel constants, (b) put fatigue constants in `utils/fatigue.py`, or (c) factor a shared `utils/training_factors.py`? Leaning (b) for now to avoid coupling.
5. **Where does pattern_systemic_weight live?** Add to `MovementPattern` enum metadata, or a separate dict in `utils/fatigue.py`? Leaning the latter — keeps `movement_patterns.py` framework-clean.
6. **UI: Chart.js or hand-rolled SVG?** What do `weekly_summary` / `volume_splitter` already use? Match that.
7. **Does "fatigue" leak prescriptive language?** The non-goals (Section 1) commit to descriptive-only. Wording like "above MRV" verges on prescriptive — vet copy carefully.
8. **Phase-1 acceptance test.** What concrete user-visible behavior is the MVP done bar? Suggest: "given a sample logged week, the fatigue badge shows the same number across two reloads, and the badge color matches the threshold band."
9. **Performance.** `/weekly_summary` already hits the DB nontrivially. Adding fatigue = another aggregation across the same rows. Compute once per request and reuse, or cache keyed by `(user, week_start, log_max_id)`?
10. **Backup contract.** Per CLAUDE.md §1, any change to core workflow behavior (analyze/etc.) requires backup-format consideration. Fatigue is computed, not stored, so backups are unaffected — *unless* we add `user_fatigue_thresholds`. Confirm before Phase 2.

---

## 12. What Reviewers Should Push Back On

The author's biases that should be questioned:

- **The three-channel model may be over-engineered for a single-user app.** A simpler "one number, one threshold" version might be enough.
- **MRV-style thresholds rely on debated literature.** Some reviewers will object that MEV/MAV/MRV are not crisply defined. That's fair; the defaults are starting points, not science.
- **The exponential intensity curve is a stylistic choice.** Buckets parallel to the existing effort factor would be more consistent and easier to test. Probably the right call.
- **"Don't add a technique modifier" is a usability call, not a correctness call.** A reviewer arguing we *should* add it (set-level or exercise-level) has a defensible position.
- **A dedicated `/fatigue` page may be redundant** with `/weekly_summary` if we keep the badge model rich enough. Could be solved with a collapsible section instead of a new route.

---

## 13. Decision Log (locked 2026-04-30 per PLANNING.md Stage 0)

| # | Decision | Options | Chosen | Rationale | Date |
|---|---|---|---|---|---|
| D1 | MVP channel count | 1 vs 3 | **1 (single fatigue score)** | Author §24.A default approved — single score keeps Phase 1 small and testable; three-channel split deferred to Phase 2. | 2026-04-30 |
| D2 | Threshold source | hardcoded / user-calibrated / both | **Hardcoded defaults; no UI override in V1** | Author §24.A default approved — calibration table is a Phase 3 schema change. | 2026-04-30 |
| D3 | Sets basis | raw / effective | **Raw set count; CountingMode ignored for fatigue** | OVERRIDE of author default. Fatigue has its own RIR/load multipliers — coupling it to CountingMode would double-count effort. | 2026-04-30 |
| D4 | Module location | extend `effective_sets.py` / new `utils/fatigue.py` / shared `training_factors.py` | **New `utils/fatigue.py`** | Author §24.A default approved — keeps fatigue math isolated from effective-sets invariants. | 2026-04-30 |
| D5 | Page placement | embed only / dedicated only / both | **Embed-only (no `/fatigue` page in Phase 1)** | Author §24.A default approved — dedicated page is Phase 2. | 2026-04-30 |
| D6 | Decay in Phase 1 | yes / no | **No** | Author §24.A default approved — decay model is Phase 3. | 2026-04-30 |
| D7 | Technique modifier in Phase 1 | yes / no | **No** | Author §24.A default approved — technique modifier deferred. | 2026-04-30 |
| D8 | RIR multiplier shape | exponential curve / discrete buckets | **Discrete buckets `{0:2.0, 1:1.5, 2:1.25, 3-4:1.05, 5+:1.0}`** | Author §24.A default approved (per §23 Codex) — parity with `EFFORT_FACTOR_BUCKETS`, easier to test. | 2026-04-30 |
| D9 | Phase 1 API endpoints | ship `/api/fatigue/*` / server-side only / both | **Skip API (server-side compute only)** | Author §24.A default approved — badge is server-rendered, no client needs the JSON in Phase 1. | 2026-04-30 |
| D10 | Phase 1 data scope | logged only / logged + projected / projected only | **Planned projection from `user_selection`** | OVERRIDE rationale: badge should answer "is the designed plan demanding?" before logging. Logged-data path can follow later. | 2026-04-30 |
| D11 | Phase 1 concrete threshold numbers | per §5 ranges | **§24.B tables (pattern weights, load multipliers, RIR buckets, session/week bands)** | Author §24.A default approved — concrete numbers picked before tests, marked "starting points" for Stage 4 calibration. | 2026-04-30 |
| D12 | API parameter names & empty-state shape (if API ships) | spec'd in PLANNING.md | **N/A in Phase 1 (API skipped per D9)** | Deferred until Phase 2 API work. | 2026-04-30 |
| D13 | Performance strategy | re-query DB / reuse loaded summary rows / cache by `(week, log_max_id)` | **Extend/reuse existing summary query path to expose per-exercise rows; no caching** | OVERRIDE: do not rely on already-aggregated summary rows — fatigue needs `movement_pattern`, `reps`, `sets`, and `RIR`. No cache in Phase 1. | 2026-04-30 |

---

## 14. Prerequisites — Before Any Code Is Written

The 95%-confidence bar starts here. None of these are optional. All happen *after* §13 is filled in and *before* the first commit on a fatigue-meter branch.

### 14.1 Lock the baseline
- [ ] Run `/verify-suite`. Capture the exact pytest count, E2E count, and durations. Fatigue work cannot start until this is green.
- [ ] Per CLAUDE.md §5 the current baseline is **pytest 1216 passed** and **E2E 314 passed (Chromium)**. Confirm nothing has shifted in the user's working tree since (note: at draft time `data/database.db`, `tests/test_priority0_filters.py`, `utils/db_initializer.py` all show as modified — flush or commit those before baseline).
- [ ] Save the verification log to `docs/fatigue_meter/baseline-{date}.txt` for reference. Any test count change later must be explained against this file.

### 14.2 Data integrity audit
The fatigue model multiplies several inputs. If any input is silently NULL/wrong for a swath of exercises, fatigue numbers will look fine but be lies.
- [ ] Count exercises with NULL `primary_muscle` (should be ~0; confirm).
- [ ] Count exercises with NULL `movement_pattern` / no pattern classification.
- [ ] Count exercises that are bodyweight-only (`weight` always NULL in the log) — these will drive the rep-range fallback path and need explicit test coverage.
- [ ] Count distinct exercises in `user_profile` reference lifts vs total exercises in `exercise_database`. The ratio tells us whether the %1RM path is the common case or the rare case (probably rare — plan accordingly).
- [ ] Spot-check 5 high-volume exercises (squat, bench, deadlift, OHP, row) to confirm they classify as compound under whatever pattern_systemic_weight scheme we choose.

Each finding gets one line in `docs/fatigue_meter/data-audit.md` (a sibling doc, not part of this brainstorm). Findings that block development must be resolved or explicitly carved out before Phase 1 starts.

### 14.3 Pre-flight backup
- [ ] Create a manual backup via `POST /api/backups` *before* any code lands. Auto-backup at startup (`utils/auto_backup.py`) covers daily snapshots, but a labeled "pre-fatigue-meter" snapshot is the rollback floor.

### 14.4 Decision lock
- [ ] §13 fully filled in. Specifically these three blockers must be resolved before §15 chapters can start:
  - MVP channel count (1 vs 3) — drives the entire Phase 1 surface area.
  - Sets basis (raw vs effective) — drives test fixtures and threshold values.
  - Module location — drives every import line.
- [ ] PLANNING.md drafted from this brainstorm with the decisions baked in. The brainstorm stays as historical record; PLANNING.md is what the implementation tracks against.

### 14.5 Dependency check
- [ ] No new Python packages required. Confirm by walking the model — pure stdlib + existing project imports should suffice.
- [ ] No new JS packages required for Phase 1 (badge is server-rendered HTML + minimal SCSS). Phase 2 dedicated page may use the existing chart library — identify which library `weekly_summary` / `volume_splitter` already uses and reuse it. **Adding a new front-end dep needs explicit approval.**
- [ ] No new SCSS framework changes; new partial uses existing Bootstrap utility classes.

---

## 15. Implementation Chapters — Phase 1 (with Validation Gates)

Each chapter is a single small commit. Each chapter has an explicit **gate** — work on the next chapter does not begin until the previous gate is green. This is the key mechanism for not breaking anything.

### Chapter 1.1 — Pure-function fatigue module
**Files added:** `utils/fatigue.py` (constants + dataclasses + per-set function + session/weekly aggregators).
**Files edited:** none.
**No DB writes. No routes. No templates. No app.py changes.**

**Gate 1.1:**
- [ ] `python -c "import utils.fatigue"` succeeds.
- [ ] Full pytest still **1216 passed** (no test count delta — we haven't added tests yet, but we've also added no regressions).
- [ ] No new files in `routes/`, `templates/`, or `static/`.

### Chapter 1.2 — Unit tests for the math
**Files added:** `tests/test_fatigue.py` (~30–50 tests, see §16.1).
**Files edited:** none.

**Gate 1.2:**
- [ ] Full pytest = **1216 + N passed** where N is the count of new tests. Document N.
- [ ] All new tests run in <2s combined (pure-math, no DB access yet).
- [ ] No tests in other files changed in count or status.

### Chapter 1.3 — Read-only API
**Files added:** `routes/fatigue.py` with two endpoints:
- `GET /api/fatigue/session?routine=<name>&date=<iso>` → session fatigue payload.
- `GET /api/fatigue/week?week=<iso-week>` → weekly fatigue payload.

Both return via `success_response()` / `error_response()` per CLAUDE.md §3 conventions. Both use `DatabaseHandler` context manager for reads. No writes.

**Files edited:**
- `app.py` — register `fatigue_bp` in the blueprint list.
- `tests/conftest.py` — register `fatigue_bp` in the test app fixture (per testing rule §"Adding a new blueprint — don't forget the test app").

**Gate 1.3:**
- [ ] Full pytest = **1216 + N + M passed** where M is the count of new API tests.
- [ ] Manual curl: `GET /api/fatigue/session` against a seeded DB returns valid JSON conforming to `success_response` shape.
- [ ] `GET /api/fatigue/week` with no data → returns `{success: true, data: {fatigue: 0, ...}}`, *not* 500.
- [ ] code-reviewer subagent run on staged diff; flags resolved (especially response-contract drift and SQL-injection risk on the `routine` / `date` / `week` parameters — these MUST be parameterized).

### Chapter 1.4 — Server-rendered badge partial
**Files added:** `templates/_fatigue_badge.html` (a Bootstrap card-shaped partial that takes `fatigue`, `baseline`, `state` color enum).

**Files edited:**
- `templates/session_summary.html` — `{% include '_fatigue_badge.html' %}` in a designated slot.
- `templates/weekly_summary.html` — same.
- `routes/session_summary.py` and `routes/weekly_summary.py` — pass fatigue numbers into template context (computed via `utils.fatigue` functions, no API hop).

**Gate 1.4:**
- [ ] Full pytest = unchanged delta from Chapter 1.3 (template additions don't break server tests).
- [ ] **Targeted E2E:** `npx playwright test e2e/summary-pages.spec.ts --project=chromium` → expected 20 passed (per testing rule). Any regression here means the badge insertion broke a selector or layout.
- [ ] Manual: load `/weekly_summary` and `/session_summary` in a browser. Badge appears, no console errors, no broken layouts on mobile-width viewport.

### Chapter 1.5 — Copy & color states
**Files edited:**
- `templates/_fatigue_badge.html` — add color-state CSS classes and one-paragraph "what this means" tooltip.
- `scss/_fatigue.scss` (new) and `scss/custom-bootstrap.scss` — import the new partial.
- Run the `/build-css` skill.

**Gate 1.5:**
- [ ] `static/css/custom-bootstrap.css` rebuilt and committed.
- [ ] Full `/verify-suite`: pytest + E2E both green.
- [ ] **Manual smoke (in browser, all routes):** `/`, `/workout_plan`, `/workout_log`, `/weekly_summary`, `/session_summary`, `/progression`, `/volume_splitter`, `/user_profile`, `/body_composition`. Confirm no regressions in unrelated pages, no console errors, no broken navbar.
- [ ] Copy reviewed for prescriptive-language creep (Section 1 non-goals).

### Chapter 1.6 — Documentation & test count update
**Files edited:**
- `CLAUDE.md` §5 "Verified test counts" line — update to new totals with date and explanation.
- `docs/CHANGELOG.md` — fatigue meter Phase 1 entry.
- `docs/fatigue_meter/PLANNING.md` (created earlier in §14.4) — mark Phase 1 chapters complete.

**Gate 1.6 (final Phase 1 merge gate):** see §19 pre-merge checklist.

---

## 16. Test Plan

### 16.1 Unit tests (`tests/test_fatigue.py`)
Pure-math, no DB. These are the cheap defenders.

**Per-set fatigue:**
- Standard inputs (sets=3, RIR=2, rep range 8–12, primary muscle set) → matches expected hand-calculated value.
- RIR=0 → intensity multiplier maxed.
- RIR=10 → intensity multiplier ≈ 1.0.
- RIR=None → uses default multiplier, does not crash.
- Rep range None → uses default load multiplier, does not crash.
- All muscles None → primary contribution falls into "unassigned" bucket, total still computed.
- Sets=0 → fatigue=0, no division by zero anywhere.
- Bodyweight (weight=None) → falls back to rep-range proxy, no crash.
- %1RM available (reference lift exists) → uses %1RM path.
- %1RM unavailable → falls back to rep-range proxy, returns same shape.

**Aggregation:**
- Empty exercise list → SessionFatigueResult with all zeros.
- Single exercise → matches per-set × sets.
- Two exercises same muscle → muscle fatigue sums correctly.
- Same exercise listed twice → fatigue sums (no dedup).
- Weekly = sum of session results (Phase 1 — no decay).
- Cross-week boundary: a Sunday session and a Monday session land in different weeks per ISO calendar.

**Stimulus-to-Fatigue Ratio:**
- Fatigue = 0 → SFR returns `None` (or sentinel), not `inf` or crash.
- Fatigue > 0, stimulus = 0 → SFR = 0.
- Both > 0 → ratio matches expected.

**Threshold classification:**
- Fatigue below MEV → "low" state.
- Fatigue between MAV and MRV → "high" state.
- Fatigue > MRV → "excessive" state.
- Boundary values (exact MEV, exact MAV, exact MRV) → deterministic side per docstring.

### 16.2 Integration tests (route + DB, in `tests/test_fatigue.py` or a sibling)
- `GET /api/fatigue/session` with seeded plan + log → correct payload, 200, `success_response` shape.
- `GET /api/fatigue/session?routine=<missing>` → empty payload, 200, *not* 404 (non-existent routine is a valid empty case).
- `GET /api/fatigue/week?week=invalid` → 400 with `error_response` shape.
- SQL parameterization: pass a `routine` containing `' OR 1=1 --` → returns empty result, no crash, no rows leaked from other routines. (Critical: this is exactly the kind of injection vector code-reviewer will flag.)
- DB patching pattern verified: `utils.config.DB_FILE = test_db_path` correctly redirects fatigue queries to the test DB.

### 16.3 E2E (`e2e/fatigue.spec.ts` — added Phase 2; in Phase 1 we extend `summary-pages.spec.ts`)
**Phase 1 (extend `summary-pages.spec.ts`):**
- Badge renders on `/weekly_summary`.
- Badge renders on `/session_summary`.
- Badge renders even when log is empty (shows zero / "no data" state, not crash).
- No new console errors introduced on either page.

**Phase 2 (new `e2e/fatigue.spec.ts`):**
- `/fatigue` page loads, no console errors.
- Period selector switches between session / week / 4-week views.
- Per-muscle bars render and are sorted descending by fatigue.
- SFR card shows ratio + explanation copy.
- Empty-state: brand-new DB → all zeros, page does not crash.

### 16.4 Targeted regression sweep (must pass before merge)
Per CLAUDE.md §4B Refactor playbook:
- `e2e/summary-pages.spec.ts` (20 tests) — touched directly.
- `e2e/workout-plan.spec.ts` (17 tests) — sibling page, sanity check.
- `e2e/workout-log.spec.ts` (19 tests) — sibling page, sanity check.
- `e2e/api-integration.spec.ts` (56 tests) — new API endpoint added.
- `e2e/accessibility.spec.ts` (24 tests) — badge added new DOM, may break ARIA assumptions.

If any of these regress, fix before adding the next chapter's code.

### 16.5 Manual smoke (the human-eyes gate)
Before the merge gate, a human walks through:
1. Load every navbar route: `/`, `/workout_plan`, `/workout_log`, `/weekly_summary`, `/session_summary`, `/progression`, `/volume_splitter`, `/user_profile`, `/body_composition`. No console errors. No broken layouts.
2. Add an exercise to a routine, log it, view weekly summary. Badge updates as expected.
3. Restore a backup. Badge does not crash on pre-fatigue-format data.
4. Resize to mobile width (375px). Badge does not push other content off-screen.
5. Toggle dark mode. Badge colors readable in both modes.

---

## 17. Risk Register

Concrete risks specific to this codebase, each with mitigation. Reviewers should add risks I've missed.

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Blueprint not registered in `tests/conftest.py` → 404s in tests | Medium (it's the #1 testing pitfall per the testing rule) | High (silent broken tests) | Chapter 1.3 explicitly requires conftest update; PR template adds a checkbox. |
| R2 | SQL injection via `routine` / `date` / `week` query params | Medium | Critical | All DB calls via `DatabaseHandler` parameterized; code-reviewer agent run on staged diff. |
| R3 | Response contract drift (ad-hoc JSON instead of `success_response`) | Medium (per §"Known response-contract exceptions" in CLAUDE.md, this has happened before) | Medium | Lint-style check during review; explicit chapter gate. |
| R4 | Filter cache stale due to a fatigue route mistakenly invalidating it | Low | Medium | Fatigue routes never call `invalidate_cache()`. Verified by grep before merge. |
| R5 | Division by zero in SFR when fatigue = 0 | Medium | Low (crash, but easy to repro) | Explicit unit test (§16.1). Guard returns `None` sentinel. |
| R6 | Date / ISO-week boundary off-by-one | Medium | Medium (numbers wrong but plausible) | Explicit unit test for Sunday/Monday boundary. Use `datetime.date.isocalendar()`. |
| R7 | Performance regression on `/weekly_summary` | Low | Medium | Compute fatigue from the same query results that already power volume; do not re-query. Time before/after with a 100-week test fixture. |
| R8 | Prescriptive language creeps into copy ("you should reduce volume") | Medium | Low (UX), High (project-philosophy) | Copy review checkbox in §19. Section 1 non-goals quoted in PR description. |
| R9 | Phase 1 ships a number nobody understands | Medium | Medium | One-paragraph "what this means" tooltip on the badge. Beta-test on user before claiming done. |
| R10 | Tests in `tests/test_priority0_filters.py` (currently modified per `git status`) interfere with baseline | Already present | High (baseline lockdown depends on this) | Resolve the working-tree state in §14.1 before starting. |
| R11 | DB backup format silently grows new tables that backups don't include | Low | High | Phase 1 has no schema changes. If Phase 3 adds tables, audit `utils/program_backup.py` first. |
| R12 | `volume_splitter` page logic depends on summary data shape; fatigue computation alters the shared DB query path | Low | High | Phase 1 does NOT modify `weekly_summary.py` query — only consumes its results. Confirmed by code review. |

---

## 18. Rollback Strategy

Phase 1 is **purely additive**: no schema changes, no rewrites of existing functions, no behavioral changes to existing routes.

### Rollback for Phase 1
- `git revert <chapter-1.x>` walks each chapter back independently. Because gates ensure a green state at each chapter boundary, partial rollback is safe.
- No DB migrations to undo (no schema changes in Phase 1).
- `static/css/custom-bootstrap.css` rebuilds from SCSS, so reverting scss + rerunning `/build-css` is sufficient to undo Chapter 1.5.

### Rollback for Phase 2
Same as Phase 1 (no schema changes; new templates and JS module are additive).

### Rollback for Phase 3
**This is where rollback gets harder** — adds `user_fatigue_thresholds` table. Mitigation:
- Migration must include a documented `down` SQL (the project doesn't have a migration framework; record the down SQL inline in the migration function's docstring).
- `utils/program_backup.py` must include the new table in backup format, or the table must be schema-rebuildable from defaults.
- Manual backup taken before merging Phase 3.

### Emergency rollback path
If something goes wrong post-merge:
1. `POST /api/backups/<pre-fatigue-snapshot-id>/restore` to restore the labeled backup from §14.3.
2. `git revert <merge-commit>` on `main`.
3. Investigate offline.

---

## 19. Pre-Merge Checklist (the 95% confidence gate)

Every box must be checked before Phase 1 merges to `main`. Reviewers refuse to approve until all are checked.

### Code & tests
- [ ] All §13 decisions filled.
- [ ] §14 prerequisites done (baseline locked, data audit complete, pre-flight backup taken, dependency check passed).
- [ ] All Phase 1 chapter gates in §15 passed.
- [ ] `/verify-suite` green: pytest **1216 + N passed**, E2E **314 + M passed**.
- [ ] Targeted regression sweep (§16.4) green.
- [ ] Manual smoke (§16.5) walked through, no findings.
- [ ] code-reviewer subagent run on full diff; all findings resolved.
- [ ] No new Python or JS dependencies (or each new dep individually justified).

### Contract & conventions
- [ ] All new JSON returns use `success_response` / `error_response`.
- [ ] All new DB access via `DatabaseHandler` context manager with parameterized queries.
- [ ] All new modules use `from utils.logger import get_logger; logger = get_logger()`.
- [ ] No `import DB_FILE` at module top — only `import utils.config` then `utils.config.DB_FILE`.
- [ ] New blueprint registered in BOTH `app.py` AND `tests/conftest.py`.
- [ ] Filter cache untouched — verified by grep for `invalidate_cache` (should be no new calls).

### Behavior & non-goals
- [ ] No prescriptive language in user-facing copy.
- [ ] Fatigue meter never blocks a user action, never auto-adjusts a plan, never gates anything.
- [ ] No new modal interrupts (no popups for "you're over MRV"; soft inline warnings only).
- [ ] Effective-sets calculation values unchanged (verify by diffing a sample week's output before vs after).

### Documentation
- [ ] `CLAUDE.md` §5 verified test count line updated with new totals + date.
- [ ] `docs/CHANGELOG.md` entry written.
- [ ] `docs/fatigue_meter/PLANNING.md` Phase 1 marked complete.
- [ ] PR description references this brainstorm and the PLANNING.md, lists the test count delta, and quotes Section 1 non-goals.

### Safety
- [ ] Pre-flight backup from §14.3 still exists in `/api/backups`.
- [ ] On a fresh clone (no `data/database.db`), startup creates a healthy DB and `/weekly_summary` renders the empty fatigue badge without crashing.
- [ ] On a backup-restored DB from before fatigue meter existed, every page loads without crashing.

If any box can't be checked, the answer is "not ready", not "ship it anyway".

---

## 20. Files-Touched Matrix

### Phase 1 (additive only)
| File | Action | Notes |
|---|---|---|
| `utils/fatigue.py` | ADD | All math, mirrors `effective_sets.py` shape. |
| `routes/fatigue.py` | ADD | Two read-only endpoints. |
| `templates/_fatigue_badge.html` | ADD | Reusable partial. |
| `scss/_fatigue.scss` | ADD | Color states. |
| `tests/test_fatigue.py` | ADD | Unit + integration tests. |
| `app.py` | EDIT | Register `fatigue_bp` (one line in blueprint list). |
| `tests/conftest.py` | EDIT | Register `fatigue_bp` in test app fixture. |
| `templates/session_summary.html` | EDIT | Single `{% include %}` line. |
| `templates/weekly_summary.html` | EDIT | Single `{% include %}` line. |
| `routes/session_summary.py` | EDIT | Pass fatigue context to template. |
| `routes/weekly_summary.py` | EDIT | Pass fatigue context to template. |
| `scss/custom-bootstrap.scss` | EDIT | One `@import` line. |
| `static/css/custom-bootstrap.css` | EDIT | Rebuilt by `/build-css`. |
| `e2e/summary-pages.spec.ts` | EDIT | Add badge-presence assertions. |
| `CLAUDE.md` | EDIT | Test count line in §5. |
| `docs/CHANGELOG.md` | EDIT | New entry. |
| `docs/fatigue_meter/PLANNING.md` | EDIT | Mark Phase 1 complete. |

**Files NOT touched in Phase 1** (and a regression there is a red flag):
- `utils/effective_sets.py`, `utils/weekly_summary.py`, `utils/session_summary.py`, `utils/database.py`, `utils/db_initializer.py`, `data/database.db` schema, `utils/program_backup.py`, `utils/auto_backup.py`, all other routes.

### Phase 2 additions (preview)
| File | Action | Notes |
|---|---|---|
| `templates/fatigue.html` | ADD | Dedicated page. |
| `static/js/modules/fatigue.js` | ADD | Chart rendering. |
| `e2e/fatigue.spec.ts` | ADD | Dedicated E2E spec. |
| `templates/base.html` | EDIT | Nav link. |
| `app.py` | EDIT | Add `/fatigue` route registration if not via existing blueprint. |

### Phase 3 additions (preview)
| File | Action | Notes |
|---|---|---|
| `utils/database.py` | EDIT | New `add_fatigue_threshold_tables()` function. |
| `app.py` | EDIT | Call new migration at startup. |
| `tests/conftest.py` | EDIT | Call new migration in `_initialize_test_database`. |
| `utils/program_backup.py` | EDIT (likely) | Include new table in backup format. |

---

## 21. Codebase-Specific Pitfalls (read before writing code)

These have bitten the project before per CLAUDE.md / `.claude/rules/testing.md`. Don't repeat them.

1. **Bare `from utils.config import DB_FILE` does not work in tests.** Tests patch `utils.config.DB_FILE` at runtime. Always reference `utils.config.DB_FILE` lazily inside functions.
2. **New blueprint must be registered in `tests/conftest.py` AND `app.py`.** Missing the conftest one = silent 404s in tests.
3. **`success_response` / `error_response` are mandatory for new endpoints.** Per CLAUDE.md §5 there are existing exceptions in `routes/weekly_summary.py:133,139` and `routes/workout_plan.py:1079-1125` — those are tech debt, not patterns to copy.
4. **`DatabaseHandler` context manager only.** Never open `sqlite3.connect()` directly, never bypass it — FK enforcement and journal mode depend on it.
5. **Logger via `get_logger()` only.** Don't `logging.getLogger(__name__)` — the project standardizes on the named `'hypertrophy_toolbox'` logger.
6. **Filter cache TTL is 3600s and invalidation is currently never called.** Don't call `invalidate_cache()` from fatigue code; it has nothing to do with filter data.
7. **Test count is the canary.** A drop in test count (vs an addition) almost always means a test was renamed/removed accidentally. Document any negative delta explicitly.
8. **CSS must be rebuilt.** `static/css/custom-bootstrap.css` is committed but generated. Use the `/build-css` skill — don't edit the CSS by hand.
9. **The `data/database.db` file is the user's data.** Do not commit changes to it as part of feature development. The current `M data/database.db` in `git status` is a working-tree artifact, not a code change.
10. **`utils/__init__.py` is no longer the authoritative facade.** Per CLAUDE.md §2, prefer concrete `utils.fatigue` imports, not `from utils import fatigue` via `__init__`.

---

## 22. Out-of-Scope (record so it doesn't creep)

- HRV / readiness integrations (would need wearables).
- Sleep tracking.
- Nutrition / macros.
- Multi-user comparisons (single-user app).
- Predicting injury risk from fatigue (medical claim, hard no).
- Auto-deload recommendations (prescriptive, violates Section 1 non-goals).
- Auto-adjusting RIR or weight in the plan based on fatigue (violates Section 1 non-goals).
- Notifications / push reminders.
- Sharing / exporting fatigue charts to social media.

---

## 23. *** codex 5.5 *** Review - 95% Confidence Readiness Gate

**Verdict:** Not ready for development at the 95% confidence gate.

This document is strong as a brainstorm and review artifact, but it is not yet a development plan. I am more than 95% confident the correct gate result is **NO-GO for coding** and **GO for converting this into a locked `PLANNING.md`**.

### Blocking findings

1. **The document explicitly says it is pre-plan.** The header marks the status as `brainstorm / pre-plan`, and the intro says no code should be written until a chosen approach is locked in via a follow-up `PLANNING.md`.
2. **Core decisions are still unresolved.** Section 13 still has `_tbd_` entries for MVP channel count, threshold source, raw vs effective basis, module location, page placement, decay, and technique modifier. These choices affect function signatures, tests, endpoint payloads, and UI scope.
3. **Pre-development prerequisites are unchecked.** Section 14 requires baseline verification, data audit, pre-flight backup, decision lock, and dependency check before any implementation starts.
4. **Current working tree is not baseline-clean.** Review-time `git status --short` showed modified `data/database.db`, `tests/test_priority0_filters.py`, `utils/db_initializer.py`, plus untracked `docs/fatigue_meter/`. This must be resolved or deliberately recorded before the fatigue branch baseline is locked.
5. **MVP scope conflicts with stated user value.** The goals include projected fatigue before training, but Phase 1 says it only uses `workout_log`. That can be acceptable for Phase 1, but only if the team explicitly accepts "logged-only fatigue" as a partial MVP.
6. **API/date semantics need to be locked.** Proposed endpoints use `date` and `week`, while the existing summary routes are shaped around `routine`, `start_date`, `end_date`, or current plan aggregation. Decide exact query parameters and empty-state behavior before route work.
7. **Threshold meaning is under-specified.** The doc discusses RP-style landmarks and effective-set consistency, but Phase 1 hardcoded threshold values are not concretely defined. This will make tests and badge colors arbitrary unless locked first.
8. **Performance strategy is not chosen.** The brainstorm correctly flags `/weekly_summary` DB cost, but the implementation strategy is still open: reuse existing query results, re-query, or cache by week/log version. Choose before coding.

### Required changes before development

- Fill Section 13 completely, with rationale and date for every decision.
- Create `docs/fatigue_meter/PLANNING.md` from this brainstorm and make it the implementation source of truth.
- Run the full verification baseline and save it as `docs/fatigue_meter/baseline-{date}.txt`.
- Create `docs/fatigue_meter/data-audit.md` with the Section 14.2 findings.
- Create the pre-flight backup and record its backup id/name in the planning doc.
- Decide whether Phase 1 is logged-only or must include planned/projection mode from `user_selection`.
- Define Phase 1 fatigue thresholds numerically before writing tests.
- Define exact API payloads, parameter names, and empty-state responses.
- Decide whether Phase 1 computes from fresh DB queries or receives already-loaded summary rows.
- Confirm no new Python or JavaScript dependencies for Phase 1.

### Suggested locked Phase 1 shape

- One total fatigue score only.
- Logged data only, unless projection is elevated to a hard MVP requirement.
- New `utils/fatigue.py` for pure math and constants.
- No schema changes.
- Optional read-only API only if the badge or tests need it; otherwise compute server-side in the summary routes.
- Badge in `/session_summary` and `/weekly_summary`.
- No dedicated `/fatigue` page until Phase 2.
- Bucketed RIR multiplier rather than exponential curve for easier tests and consistency with `utils/effective_sets.py`.
- User-facing copy must stay descriptive and non-prescriptive.

### Gate conclusion

Do not start coding from this file as-is. The next correct step is planning: lock decisions, audit the data, verify the baseline, then implement Phase 1 chapter by chapter.

---

## 24. Author Response to §23 (Codex 5.5) Review

**Reviewed:** 2026-04-30. Recording the dialogue inline so subsequent LLM reviewers see both voices, not two competing artifacts.

### Verdict: agree
NO-GO for coding from this brainstorm as-is. GO for graduating to `PLANNING.md`. That was always the design — the brainstorm header (line 8) and footer say so explicitly.

### Codex findings — author classification

**Genuinely additive (folded into §13 as new decision rows):**

- **Phase 1 API may be unnecessary.** Strong catch. If Phase 1 is server-rendered badge only, `/api/fatigue/*` endpoints in §15 Chapter 1.3 are speculative complexity. New §13 row: "Phase 1 API endpoints — ship / skip / both". If skipped, §15 collapses Chapter 1.3 into 1.4 and the SQL-injection surface in §17 R2 reduces.
- **Concrete threshold numbers, not ranges.** §5 currently gives "Chest MEV 8 / MAV 12–16 / MRV 22". Tests need a single number per band. New §13 row added.
- **Logged-only vs. logged+projection scope tension.** §1 success criterion #2 references projection from `user_selection`. §9 Phase 1 says logged-only. That tension must be resolved before coding. New §13 row added.
- **API parameter names + empty-state shapes.** Lock exact semantics in PLANNING.md before route code. New §13 row added.
- **Performance strategy.** Already in §17 R7 mitigation but not in §13. Promoted to a decision row.
- **Bucketed RIR vs exponential curve.** §3.3 offered both; §12 explicitly invited reviewer pushback on the exponential. Codex pushed. New §13 row to formalize the choice.

**Tautological (correct but already in the doc):**

- "Document is pre-plan" → header line 3, footer line 762.
- "§13 has _tbd_ entries" → that's the call-to-action.
- "§14 prerequisites unchecked" → that's the prerequisite checklist.
- "Working tree not baseline-clean" → §17 R10 already flags this.

These four findings restate the doc's own framing. Recording for completeness, but they don't change anything.

**Codex's "Suggested locked Phase 1 shape" — author position:**

Codex's suggested shape is sensible and largely matches §9 Phase 1, with two additive simplifications:
1. Skip the API in Phase 1 (compute server-side only). Author agrees; subject to §13 decision.
2. Buckets over exponential RIR curve. Author agrees; subject to §13 decision.

Author does **not** treat Codex's suggested shape as locked — it must still pass through §13 by an explicit human decision, not adopted by inference from a review.

### Where Codex under-weighted

For balance, recording what Codex chose not to engage:

- **Three-channels-vs-one.** Codex accepted "one channel for Phase 1" without engaging §11 Q1 or §12 bullet 1. The author's bias is also "one channel for Phase 1" — but reviewers should not accept this by default. A reviewer who argues "skip channels entirely, just ship a single descriptive number forever" has a defensible position.
- **MEV/MAV/MRV reliance.** §12 bullet 2 explicitly invited pushback on the literature. Codex did not push. Threshold defaults remain debated; reviewers should still pressure-test §5.
- **Per-pattern weight scheme (§3.1).** Codex did not engage hardcoded-table vs derived-from-muscle-count. This is a real design question that affects how many exercises need manual classification before Phase 2.

These open questions remain open for the next reviewer.

### Net effect on the document

- §13 grew from 7 rows to 13 rows — six decisions Codex surfaced or sharpened.
- §15 Chapter 1.3 (API) becomes conditional on the new §13 "Phase 1 API endpoints" decision; if skipped, fold its work into Chapter 1.4 and reduce §17 R2 weight accordingly.
- §14.4 implicit requirement made explicit: PLANNING.md must include concrete numeric thresholds, not just §5 ranges.
- No content removed. Brainstorm character preserved. PLANNING.md (downstream) is where decisions become commitments.

### 24.A Author's Recommended Answers to §13 Decisions

These are author positions, not locked decisions. They exist so the next reviewer (Codex or otherwise) has a concrete target to agree or disagree with — much harder to push back on `_tbd_`. The Decision Log itself stays in §13 with `_tbd_` until the human signs off.

| # | Decision | Author recommendation | Reasoning |
|---|---|---|---|
| 1 | MVP channel count | **1 (single fatigue score)** | Three-channel model is the right *long-term* shape but over-engineered for MVP. Ship one number first; validate the user understands it; then split. |
| 2 | Threshold source | **Hardcoded defaults, no UI override in V1** | UI override needs a settings page that doesn't exist; calibration needs N weeks of data the user may not have. Defaults + a comment "your numbers may differ" is honest. |
| 3 | Sets basis | **Effective sets** | Internal consistency. Critically: **follow the user's active CountingMode toggle on the page** so the badge tracks what the user is already looking at. RAW mode → fatigue computed on raw sets; EFFECTIVE mode → on effective sets. |
| 4 | Module location | **New `utils/fatigue.py`** | Keeps `effective_sets.py` framework-clean. Shared `training_factors.py` only when a third consumer appears. YAGNI on premature factoring. |
| 5 | Page placement | **Embed-only (Phase 1)** | Dedicated `/fatigue` page is Phase 2. No new route, no nav link, no new template — just a partial included by `session_summary.html` and `weekly_summary.html`. |
| 6 | Decay in Phase 1 | **No** | Add if users complain weekly numbers feel inflated mid-week. Cheap to add later (one function), expensive to debug if shipped wrong. |
| 7 | Technique modifier in Phase 1 | **No** | We don't capture the data. Pretending to model it = false precision. Phase 4 *maybe*, opt-in per-exercise default only. |
| 8 | RIR multiplier shape | **Discrete buckets: `{0: 2.0, 1: 1.5, 2: 1.25, 3-4: 1.05, 5+: 1.0}`** | Parity with existing `EFFORT_FACTOR_BUCKETS` shape, deterministic tests, no transcendental functions in the hot path. Codex's recommendation accepted. |
| 9 | Phase 1 API endpoints | **Skip — server-side compute only** | Badge is server-rendered HTML. API is speculative until Phase 2's dedicated page needs it. Skipping reduces SQL-injection surface (§17 R2) to zero, deletes Chapter 1.3 entirely, and removes ~20 integration tests we don't yet need. Codex's recommendation accepted. |
| 10 | Phase 1 data scope | **Logged only (`workout_log`)** | "What happened" first, "what's projected" second. Validates the model against real data before extending it to plans. The §1 projection success criterion moves to Phase 3 explicitly. |
| 11 | Concrete threshold numbers | **See §24.B below** | Numbers depend on the multiplier scheme; expressed there with explicit caveat that PLANNING.md re-validates them against the user's last 4 weeks of logged data before shipping. |
| 12 | API parameters / empty state | **N/A in Phase 1** (API skipped per #9). Locks deferred to Phase 2 PLANNING. | |
| 13 | Performance strategy | **Reuse loaded summary rows; no new DB queries; no caching** | `/weekly_summary` and `/session_summary` route handlers already load all the rows fatigue needs. Compute fatigue from the same in-memory result. If profiling later shows a regression, add caching keyed by `(period_start, max_log_id)`. Don't pre-optimize. |

### 24.B Concrete Phase 1 Multiplier Scheme & Threshold Numbers

Without picking actual numbers, the Phase 1 tests are non-deterministic and the badge colors are arbitrary. Here is a defensible starting point. **PLANNING.md must re-validate these against ≥4 weeks of the user's logged data before Phase 1 ships.** If a typical week comes out >2× a deload week and a leg-day session comes out >1.5× a pull-day session, the scheme is calibrated correctly. If not, tune.

#### Per-set fatigue formula (Phase 1)
```
set_fatigue = pattern_weight × load_multiplier × intensity_multiplier
session_fatigue = Σ set_fatigue across all sets in the session
weekly_fatigue = Σ session_fatigue across the ISO week
```
No decay, no per-muscle split, no joint-stress channel — those are Phase 2.

#### Pattern weight (`utils/fatigue.py` constants)
| Movement pattern | Weight |
|---|---|
| `HINGE` (especially `DEADLIFT` sub-pattern) | 1.7 |
| `SQUAT` | 1.6 |
| `VERTICAL_PUSH` (OHP, military press) | 1.3 |
| `HORIZONTAL_PUSH` (bench, dip — compound) | 1.2 |
| `HORIZONTAL_PULL` (row), `VERTICAL_PULL` (pulldown, pullup) | 1.2 |
| `LOWER_ISOLATION` (leg ext, leg curl, calf raise) | 0.9 |
| `UPPER_ISOLATION` (curl, tricep ext, lateral raise) | 0.8 |
| `CORE_DYNAMIC` (crunch, leg raise, rotation) | 0.8 |
| `CORE_STATIC` (plank, hollow, pallof) | 0.7 |
| Pattern unset / NULL | 1.0 (neutral fallback, logged as a warning) |

#### Load multiplier (rep-range proxy in Phase 1; %1RM is Phase 2)
| Avg of (min_reps, max_reps) | Multiplier |
|---|---|
| 1–5 | 1.3 |
| 6–10 | 1.1 |
| 11–15 | 1.0 |
| 16–20 | 0.95 |
| 21+ | 0.9 |
| Unknown | 1.0 |

#### Intensity multiplier (RIR buckets)
| RIR | Multiplier |
|---|---|
| 0 | 2.0 |
| 1 | 1.5 |
| 2 | 1.25 |
| 3–4 | 1.05 |
| 5+ | 1.0 |
| Unknown / NULL | 1.0 (logged as a warning row in the contribution table) |

#### Provisional threshold bands

Worked example: 6 exercises × 3 sets = 18 sets, mostly 8–12 reps at RIR 2, mostly compound work. Per-set ≈ 1.3 × 1.1 × 1.25 ≈ 1.79. Session ≈ 32. A 4-day week ≈ 128. These bands flow from that:

**Per session:**
| Band | Range | Color |
|---|---|---|
| Light | < 20 | green |
| Moderate | 20–50 | green |
| Heavy | 50–80 | yellow |
| Very heavy | > 80 | red |

**Per week:**
| Band | Range | Color |
|---|---|---|
| Light | < 80 | green |
| Moderate | 80–200 | green |
| Heavy | 200–320 | yellow |
| Very heavy | > 320 | red |

These are starting points, **not science**. PLANNING.md must spot-check them against the user's actual logged weeks. If a normal week consistently lands in "Very heavy", either the user is genuinely overreaching (rare) or the bands are wrong (common). Tune the bands, not the user.

### 24.C Author's Answers to §11 Open Questions

| # | Question | Author answer |
|---|---|---|
| 1 | Channels — three or one? | **One for Phase 1, three for Phase 2.** Single number ships fast; user learns to read it; then we split. |
| 2 | Thresholds — fixed vs calibrated? | **Fixed defaults V1, calibration Phase 3.** Calibration after-the-fact is easy to bolt on; users without 4 weeks of data don't get a broken empty state. |
| 3 | Effective vs raw sets? | **Effective, but follows the user's existing CountingMode toggle.** If they're looking at raw, fatigue is computed from raw. Don't fight the user's view choice. |
| 4 | Reuse or fork `effective_sets.py` constants? | **Fork — new `utils/fatigue.py` with its own constants.** Different curves (RIR 0 → 2.0 here vs effort 1.0 there are not the same physical meaning). Shared module only with three consumers. |
| 5 | Where do pattern weights live? | **Dict in `utils/fatigue.py`, not in the `MovementPattern` enum.** Keeps `movement_patterns.py` framework-clean. |
| 6 | Chart.js vs hand-rolled? | **Phase 1 needs no charts** — badge is text + a color band. Decision deferred to Phase 2; whatever `volume_splitter` already uses wins by default. |
| 7 | "Above MRV" prescriptive? | **Yes, replace with neutral phrasing.** "Above the typical recoverable range" or just color + number with no verb. The badge state name in code is `very_heavy`, not `excessive` or `above_mrv`. |
| 8 | Phase 1 acceptance test? | **"Fatigue score is deterministic across two reloads on identical data; color band matches the documented thresholds; badge does not crash on an empty log."** Concrete and falsifiable. |
| 9 | Performance? | **Reuse loaded summary rows.** No new query, no cache. If profiling shows a problem, then cache. |
| 10 | Backup contract? | **Unaffected in Phase 1** (no schema changes). Phase 3 must audit `utils/program_backup.py` if it adds tables. |

### 24.D Author's Responses to §12 Push-Back-On-Me Items

§12 invited reviewers to challenge the author. Author responses, for the record:

- **"Three-channel model over-engineered for single-user app."** *Conceded for MVP.* Phase 1 ships a single channel. If users find one number sufficient through Phase 2, the three-channel split may be permanently shelved.
- **"MRV/MAV/MEV literature debated."** *Conceded.* Phase 1 doesn't use them — the §24.B threshold bands are derived from the multiplier scheme and a worked example, not from the literature table in §5. The literature table moves to Phase 2 with a "defaults, your values may differ" caveat in copy.
- **"Exponential intensity curve is stylistic."** *Conceded.* §24.B uses buckets. Codex pushed in the same direction.
- **"Don't add a technique modifier is a usability call, not a correctness call."** *Stand firm.* Modeling what we don't measure is worse than not modeling it. A reviewer who wants the modifier needs to first specify how the data is captured *honestly*, not just where it multiplies in.
- **"A dedicated `/fatigue` page may be redundant."** *Partially conceded.* Phase 1 has no dedicated page (badge embed only). Phase 2 will be re-evaluated: if a rich badge plus a collapsible per-muscle section in `/weekly_summary` is enough, the dedicated page is dropped.

### 24.E Recommended Phase 1 Lock-In (Synthesis)

If the human signs off on §13 with the answers in §24.A, Phase 1 collapses to this shape:

- **Scope:** single fatigue score per session and per week, computed from logged data only.
- **Math:** `pattern_weight × load_multiplier × intensity_multiplier` per set, summed. All buckets, all hardcoded.
- **Sets basis:** effective, follows the user's CountingMode toggle.
- **Surface:** server-rendered badge included in `session_summary.html` and `weekly_summary.html`. No API. No `/fatigue` page. No JS module beyond what's already on those pages.
- **DB:** no schema changes, no new tables, no new columns.
- **Tests:** unit (per-set math, aggregations, edge cases), integration (route handlers pass fatigue context to template), E2E (badge renders on both pages, survives empty log). Numbers locked per §24.B.
- **Files touched:** §20 Phase 1 matrix, *minus* `routes/fatigue.py` (skipped), *minus* the API portions of `tests/test_fatigue.py`.
- **Chapters:** §15 Chapter 1.3 (API) is deleted; 1.1 → 1.2 → 1.4 → 1.5 → 1.6 with renumbering.
- **Risk register:** §17 R2 (SQL injection on API params) drops out entirely. R7 (perf) downgrades to "Low/Low" because we share the existing query path.

This is the shape that maximizes value × confidence × ship-speed. Reviewers should disagree if they think it ships too little or hides too much.

### Standing invitation to the next reviewer

If you are the third LLM reviewing this file: please add §25 with your own findings rather than editing §23 or §24. Keep the dialogue stack visible. Disagree with the author or with Codex explicitly — the file is more useful when reviewers contradict each other than when they agree.

## 25. *** gemini 3.1 pro *** Review - 95% Confidence Readiness Gate

**Verdict:** Not ready for development at the 95% confidence gate (NO-GO for coding, GO for PLANNING.md).

### Summary
The document is a highly detailed and well-thought-out brainstorm for the Fatigue Meter feature. It correctly identifies the goals, non-goals, existing infrastructure, and critiques the initial formula. It proposes a phased implementation plan, identifies edge cases, and provides a comprehensive risk register and rollback strategy. The author has also responded to the previous review (Codex 5.5) and provided solid, actionable recommendations for Phase 1.

### Review
I agree with both Codex 5.5 and the Author: this document is a brainstorm artifact, not a locked implementation plan. At a 95% confidence gate, we cannot begin development because:
1. **Human Sign-off is Missing:** The decisions in Section 13 are still `_tbd_`. While the author provided strong recommendations in Section 24.A, a human must explicitly approve these before they become locked constraints.
2. **Prerequisites are Incomplete:** Section 14 requires a baseline lock, data integrity audit (`data-audit.md`), and a pre-flight backup. These must be executed before writing any code.
3. **PLANNING.md is Missing:** As stated throughout the document, the actual development must be driven by a `PLANNING.md` file, which translates the locked decisions into concrete, unchangeable tasks.

### What to Change / Next Steps
Before development can begin, the following steps must be completed:
1. **Lock Decisions:** A human reviewer needs to review the Author's recommendations in Section 24.A and formally lock them in the Decision Log (Section 13).
2. **Execute Prerequisites (Section 14):**
   - Run the test suite and lock the baseline.
   - Perform the data integrity audit and document findings in `docs/fatigue_meter/data-audit.md`.
   - Take a pre-flight backup.
3. **Create `PLANNING.md`:** Draft the final implementation plan using the locked decisions, concrete threshold numbers (Section 24.B), and the synthesized Phase 1 shape (Section 24.E).
4. **Preserve this Document:** Do not modify this brainstorm file further once `PLANNING.md` is created. Keep it as historical context.

---

*End of brainstorm. Reviewers: please leave inline comments and fill the decision log in §13. Once §13 is complete, this document graduates to a sibling `PLANNING.md` (concrete tasks per chapter) plus `data-audit.md` (§14.2 findings). The brainstorm itself stays as historical context — do not overwrite it during implementation.*
