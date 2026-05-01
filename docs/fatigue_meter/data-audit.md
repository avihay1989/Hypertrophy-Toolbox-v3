---
name: Fatigue Meter — Data Integrity Audit
description: Stage 1.2 audit of the exercise catalog and user data ahead of Phase 1 fatigue meter implementation.
type: project
---

# Fatigue Meter — Data Integrity Audit

**Stage:** PLANNING.md §1.2
**Date:** 2026-05-01
**Audit DB state:** working-tree `data/database.db` (modified vs `f16335d`); `git status` shows `M data/database.db`. Pre-baseline DB still preserved as stash commit `caa457dd5bf81f9dae27b2e49ebd898f0a5fea3b` (shorthand `caa457d`; per §1.1 notes — pinning to the immutable hash because `stash@{0}` would shift if another stash is later pushed). The ~4KB growth since the locked baseline is incidental app activity — not user-content drift — but the audit was run against the live working DB on purpose so that the numbers match what Phase 1 code will see at startup.
**git status --short --branch at audit start:**
```
## main
 M data/database.db
 M docs/CHANGELOG.md
 M docs/fatigue_meter/BRAINSTORM.md
 M docs/muscle_selector.md
 M docs/muscle_selector_vendor.md
 M e2e/workout-plan.spec.ts
 M static/js/modules/muscle-selector.js
 M tests/test_muscle_selector_mapping.py
?? docs/body_muscles_integration/
?? static/bodymaps/
```
Branch: `main` (per PLANNING.md §1.5, `feat/fatigue-meter-phase-1` is intentionally not yet created).

---

## 0. Schema-naming clarification (read this first)

PLANNING.md §1.2 and BRAINSTORM.md refer to "`exercise_database`". The actual table is **`exercises`** (PK = `exercise_name`). The audit uses real column names below:

| PLANNING / BRAINSTORM term | Actual column |
|---|---|
| `exercise_database` | `exercises` table |
| `primary_muscle` | `exercises.primary_muscle_group` |
| movement pattern | `exercises.movement_pattern` (string, lowercase, e.g. `'squat'`, `'hinge'`) |
| reference 1RM | `user_profile_lifts.weight_kg` keyed by `lift_key` (slugged identifier, not full exercise name) |

This terminology drift should be reflected in `utils/fatigue.py` Phase-1 implementation: the module reads from `exercises`, not `exercise_database`.

---

## 1. NULL `primary_muscle_group` count

| Scope | Count | % of scope |
|---|---|---|
| Whole catalog | 633 / 1897 | **33.4%** |
| Strength-eligible only (excl. Recovery/Yoga/Cardio/Stretches) | 295 / 1506 | **19.6%** |

Distribution of NULL-primary-muscle rows by equipment (top): `Recovery` 177, `Yoga` 72, `Bodyweight` 63, `Stretches` 49, `Dumbbells` 46, `Barbell` 41, `Cardio` 40, `Kettlebells` 30, `Medicine_Ball` 25, `Cables` 24.

**Both whole-catalog and strength-only figures exceed the 5% threshold PLANNING.md §1.2 names as a blocking finding.** See §6 below for resolution.

---

## 2. NULL / unset `movement_pattern` count

| Scope | Count | % of scope |
|---|---|---|
| Whole catalog | 454 / 1897 | **23.9%** |
| Strength-eligible only (excl. Recovery/Yoga/Cardio/Stretches) | 158 / 1506 | **10.5%** |

Distribution of populated patterns:
```
upper_isolation: 286    horizontal_pull: 121    core_static:    59
squat:           266    lower_isolation: 102    vertical_pull:  51
hinge:           171    vertical_push:    84    (NULL):        454
horizontal_push: 158    core_dynamic:    145
```

Cross-tab: every row missing `movement_pattern` is also missing `primary_muscle_group` — the 454 NULL-pattern set is a strict subset of the 633 NULL-primary set.

**Strength-only 10.5% still exceeds the 5% threshold.** See §6.

---

## 3. Bodyweight-only exercises

PLANNING.md wording is "weight consistently NULL in log". The log-based count is **unmeasurable** in the current DB:

| Source | Count |
|---|---|
| `workout_log` rows total | **0** |
| Distinct exercises ever logged | 0 |
| `exercises.equipment = 'Bodyweight'` | **202** |
| `exercises.equipment IN ('Bodyweight', NULL/empty)` | 202 |

Because there is no logged history to derive "consistently NULL weight" from, the audit falls back on the catalog's `equipment` column. **202 / 1897 exercises (10.7%) are explicitly catalogued as `Bodyweight`.**

Implication for Phase 1: §24.B's load-multiplier table uses rep range as the load proxy, not weight, so NULL `weight` in `user_selection` (D10's input source) is not a blocker. But §16.1's "Bodyweight (weight=None) → rep-range proxy path, no crash" unit test is now load-bearing — without real logs, this edge case is exercised only by the unit test.

---

## 4. Reference 1RM coverage

| Quantity | Value |
|---|---|
| Distinct `lift_key` rows in `user_profile_lifts` | 2 (`barbell_bench_press`, `barbell_bicep_curl`) |
| Of those, with a non-NULL non-zero `weight_kg` | **0** |
| Total exercises in `exercises` | 1897 |
| **Effective coverage ratio** | **0 / 1897** |

Both rows are placeholders with NULL `weight_kg` and NULL `reps`. The user has not yet entered any reference 1RM data.

Implication for Phase 1: §24.B's load multiplier is rep-range-based, not %1RM-based, so 1RM coverage does not gate Phase 1. **It does gate Phase 2** (§24.B says "%1RM is Phase 2"). Carry this forward as a Phase-2 prerequisite, not a Phase-1 blocker.

Note: `lift_key` is a slugged lift identifier, not an `exercises.exercise_name`. A direct ratio of "distinct lift_keys ÷ exercises" mixes units; the meaningful Phase-2 question is "how many of the canonical compounds (squat / bench / deadlift / OHP / row) have a reference 1RM" — currently zero.

---

## 5. Compound spot-check (§24.B pattern weights)

Compound = `movement_pattern` ∈ {`hinge`, `squat`, `vertical_push`, `horizontal_push`, `horizontal_pull`, `vertical_pull`} (all weights ≥ 1.2 in §24.B). Up to 5 representative rows per lift:

| Lift | Match | `movement_pattern` | `movement_subpattern` | Verdict |
|---|---|---|---|---|
| Squat | `Squat` | `squat` | `squat` | ✓ COMPOUND |
| Squat | `Barbell Full Squat - quadriceps focused` | `squat` | `bilateral_squat` | ✓ COMPOUND |
| Squat | `Barbell Front/High-Bar/Low-Bar Squat` (3 rows) | `squat` | `bilateral_squat` | ✓ COMPOUND |
| Bench Press | `Bench Press`, `Barbell Bench Press` | `horizontal_push` | `press` | ✓ COMPOUND |
| Bench Press | `Barbell Incline / High-Incline / Close-Grip Bench Press` | `horizontal_push` | `press` | ✓ COMPOUND |
| Deadlift | `Barbell Deadlift`, `Barbell Sumo Deadlift` | `hinge` | `deadlift` | ✓ COMPOUND |
| Deadlift | `Barbell Coan / Staggered / Single Leg Deadlift` | `hinge` | `deadlift` | ✓ COMPOUND |
| Overhead Press | `Overhead Press`, `Barbell Overhead Press`, `Barbell Military Press`, `Barbell Seated Military Press` | `vertical_push` | `press` | ✓ COMPOUND |
| Barbell Row | `Barbell Row`, `Barbell Bent Over Row`, `Barbell Pronated/Supinated Pendlay Row`, `Barbell Underhand Bent over Row` | `horizontal_pull` | `row` | ✓ COMPOUND |

**No misses.** All five canonical compound lifts classify correctly under §24.B's pattern weights.

Notable cross-check: `Barbell Coan Deadlift` has `primary_muscle_group = 'Quadriceps'` — almost certainly a catalog mistake (it should be hamstrings/glutes), but it doesn't affect the §24.B compound classification because the pattern is `hinge`. Tracked under §6 as a known catalog defect, not a Phase-1 blocker.

---

## 6. Blocking-findings resolution

PLANNING.md §1.2 last bullet: *"Any blocking finding (e.g. >5% of exercises missing pattern) resolved or explicitly carved out as Phase-1 known limitation."*

Two findings exceed the 5% threshold:

| Finding | Whole-catalog | Strength-only | Resolution |
|---|---|---|---|
| NULL `movement_pattern` | 23.9% | 10.5% | **Carved out as Phase-1 known limitation.** §24.B already specifies the fallback: `Pattern unset / NULL → 1.0 (neutral fallback, logged as a warning)`. §16.1 unit-test list already includes `Pattern unset → 1.0 fallback, warning logged`. Phase 1 will not crash on NULL patterns; it will silently degrade to neutral weight and emit a `logger.warning(...)` row per affected exercise. |
| NULL `primary_muscle_group` | 33.4% | 19.6% | **Carved out as Phase-1 known limitation.** §16.1 already covers `All muscles None → primary contribution falls into "unassigned" bucket, total still computed`. For Phase 1's single-channel score this is benign — the global fatigue total is unaffected. **It will become a real problem in Phase 2** (per-muscle channels), so the catalog backfill is a Phase-2 prerequisite, not a Phase-1 prerequisite. |

### Why this is acceptable for Phase 1 (and not for Phase 2)

- Phase 1 ships a **single global fatigue score**. Missing pattern weights degrade to 1.0 (neutral) — a row with NULL pattern still contributes its load × intensity multiplier. The score remains directionally informative.
- D10 says Phase 1 reads `user_selection`, not `workout_log`. `user_selection` currently has 0 rows (see §7), so the badge will render its empty state on first load. The user must add at least one routine before NULL-pattern exposure becomes possible.
- Phase 2 splits to per-muscle channels and will surface "unassigned" as its own bucket — the catalog gap becomes user-visible there. Stage 4 calibration is the natural moment to plan a backfill.

### Recommended follow-ups (NOT blocking Phase 1)

- **Stage 4 add-on:** during the calibration window, audit which catalog NULLs the user actually selects in `user_selection`, and prioritize backfill by user-touched coverage rather than catalog completeness.
- **Phase 2 prerequisite:** before per-muscle channels ship, restore strength-only `primary_muscle_group` coverage to ≥ 95%. Catalog defects like `Barbell Coan Deadlift = Quadriceps` should be fixed in the same pass.
- **Phase 2 prerequisite:** before %1RM load multipliers ship (replacing rep-range proxy), populate at least the five canonical compounds in `user_profile_lifts` with real weights — currently zero.

---

## 7. Additional context (out of PLANNING scope, useful for §16 test design)

- `user_selection` rows: **0**. Phase 1's badge will be exercised first against its empty state. Worth ensuring the §16.1 test "Empty exercise list → `SessionFatigueResult` with all zeros" + a route-handler integration test that the badge renders (rather than crashes) on an empty selection.
- `workout_log` rows: **0**. Stage 4 calibration explicitly walks "≥7 days of post-merge use" and "4 representative recent weeks" — these will only become available *after* the user starts logging. Calibration may need to extend its 2-week window if logging adoption is slow.
- `user_profile_lifts` rows: 2 placeholders, 0 with real data.
- Empty `user_selection` + empty `workout_log` together mean Phase 1's manual smoke (PLANNING §2.3 / §2.4 gates) is shaped like *"add an exercise → observe badge updates from zero"* rather than *"open existing log and confirm badge"* — bake this into the manual checklist.

---

## 8. Audit verdict

- ✅ Five canonical compounds classify correctly.
- ✅ Bodyweight catalog count established (log-based count unavailable but Phase 1's rep-range proxy renders that moot).
- ✅ 1RM coverage established as 0/1897 — Phase-2 prerequisite, not Phase-1 blocker.
- ⚠️ NULL `movement_pattern` and NULL `primary_muscle_group` both exceed PLANNING's 5% threshold. **Both explicitly carved out as Phase-1 known limitations** with the §24.B / §16.1 fallback paths cited. Phase 2 inherits both as prerequisites.

**Phase 1 is not blocked by data integrity.** Proceed to PLANNING §1.3 (pre-flight backup).
