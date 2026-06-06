# Learned Calibration Plan

## Status

MVP + Phase 2A learned calibration are shipped on `main`:

- PR #37 / `fd2e2f5`: exact-exercise learned calibration backend, settings, estimator integration, Profile controls, Workout Controls source UI/actions, workout-log notifications, tests, and E2E.
- PR #39 / `62db541`: separate profile-estimator dumbbell/total-load reference fix.
- PR #53 / `0f8b4b7`: Phase 2A read-only, ratio-gated related-exercise transfer — `utils/lift_matching.py`, additive `exercise_transfer_ratios` + `ignored_calibration_transfers` tables, `allow_related_exercise_learning` settings flag (default `0`), estimator priority (exact learned → exact log → related learned → Profile → cold-start → default), Profile toggle, Workout Controls related-source badge/trace/ignore. Ships with **zero** seeded ratios, so no behavior change until learned mode + related mode + a ratio row all exist.

**Phase 2A is complete.** The next implementation slice is **Phase 2B** (review and control surface) — see §"Phase 2B Review and Control Surface" below. This document remains the planning source for Phases 2B–2D; 2C (promote to Profile) and 2D (fatigue/volume-aware) still need design review before coding.

## Goal

Add a learned calibration layer so Workout Controls suggestions can improve from the user's logged performance, not only from Profile reference lifts, demographics, or static defaults.

Example target behavior:

- Profile suggests `Barbell Full Squat - quadriceps focused` at `81.5 kg`.
- User logs `120 kg x 6-8 @ 2 RIR`.
- After learned calibration is enabled, the same squat variation produces a better next Workout Controls suggestion.
- The app explains why the suggestion changed and lets the user keep, apply, reset, or disable learned calibration.

## Current Behavior

The shipped estimate flow prioritizes:

1. Exact exercise learned calibration, when settings mode is `suggest` and confidence is usable.
2. Last logged set for the exact exercise.
3. Profile reference lifts.
4. Cold-start demographics.
5. Static default.

Exact exercises now adapt from recent valid scored logs instead of only mirroring the latest row. Similar exercises still do not learn from logs. Cross-exercise propagation exists only through Profile reference lifts, and workout logs do not write back to those reference lifts.

## Desired Result

Workout Controls should become a smarter suggestion engine with visible source attribution:

- Exact exercise suggestions should use recent valid logged performance.
- Suggestions should use the existing double-progression rules instead of simply mirroring the last row.
- Profile values should remain the user's declared baseline unless the user explicitly promotes learned data.
- The user should always be able to see why a number was suggested.

## Non-Goals

- Do not silently overwrite Profile reference lifts.
- Do not silently rewrite existing planned program rows in `user_selection`.
- Do not auto-change historical workout logs.
- Do not treat one unusual set as permanent truth.
- Do not add related-exercise transfer in MVP.
- Do not introduce a second app-wide strength formula.
- Do not learn from incomplete logs that lack usable weight and rep data.
- Do not calibrate excluded equipment or unsupported edge cases.

## MVP Scope

The MVP should include:

- Exact exercise learned calibration only.
- Workout Controls estimator integration.
- User-visible source and explanation trace.
- Settings with two modes:
  - `off`
  - `suggest`
- Reset learned calibration per exercise.
- Backend tests for calibration logic, estimator priority, settings behavior, and database cleanup.

The MVP should not include:

- Related exercise learning.
- Auto-apply mode.
- Automatic edits to `user_selection`.
- Fatigue-aware set changes.
- Profile dashboard.
- Promote-to-Profile workflow.
- Persisting `Apply suggestion` to `user_selection`.

## Phase 2 Scope

Phase 2 can add:

- Related exercise calibration.
- Dedicated exercise-to-exercise transfer ratio table.
- Calibration event/audit history.
- Profile calibration dashboard.
- Manual `Promote to Profile reference lift` action.
- Fatigue-aware and volume-aware set suggestions.
- E2E coverage for the full related-learning UI flow.

### Phase 2 Scope Split

Phase 2 should be split into reviewable stages:

1. **Phase 2A - related-exercise suggestions only.** Add read-only transfer from one exercise's learned calibration to a related target exercise. No Profile writes, no plan-row writes, no dashboard, no auto-apply.
2. **Phase 2B - review and control surface.** Add an audit/dashboard view, ignored-transfer controls, and bulk reset only after 2A behavior is stable.
3. **Phase 2C - promote to Profile.** Add manual promote-to-Profile as its own explicit action with route tests, response-contract tests, and clear copy that it changes the user's declared baseline.
4. **Phase 2D - fatigue/volume-aware suggestions.** Keep this separate from strength transfer so fatigue logic does not become a hidden modifier inside Workout Controls.

Phase 2A is shipped (PR #53). **Phase 2B is the next implementation slice** — see below.

## Phase 2B Review and Control Surface

### Goal

Give the user a Profile surface to *inspect* learned calibration state and *manage* ignored related transfers, **without changing estimator math**. This is a read/control layer over the rows Phase 2A already writes — it does not promote to Profile, write reference lifts, write plan rows, auto-apply, add fatigue/volume awareness, change estimator priority, or seed transfer ratios.

### Locked decisions (Opus review, 2026-06-06)

1. **Placement** — a new section on `/user_profile`, beside the existing Learned Calibration settings. No new route/page/nav entry.
2. **No `calibration_events` table** — deferred until a real audit-history consumer exists (plan §"Data Model"). 2B reads live state only.
3. **Transfer-ratio rows stay internal** — the surface shows learned calibrations + ignored pairs only. Curated ratios are not user-visible (there are zero seeded today).
4. **Bulk reset requires UI confirmation** — destructive actions (reset all learned, clear all ignored) prompt before firing.
5. **Clear ignored transfers: per-pair + global** — each ignored pair has an un-ignore (remove) control, plus a bulk "clear all ignored" control.

### Surface contents

- **Learned calibrations** (read-only list): exercise name, confidence, sample count, estimated 1RM, suggested weight + rep range, last observed date.
- **Ignored related transfers** (list with per-row remove): source exercise, target exercise, created date.
- **Bulk controls**: "Reset all learned calibration" and "Clear all ignored transfers", both confirmed.
- Existing per-exercise reset (Plan page) and per-pair ignore (Workout Controls) are unchanged.

### Backend (additive, no schema change)

New helpers in `utils/strength_calibration.py` (all reuse the caller's `DatabaseHandler`):

- `list_learned_calibrations(*, db)` — all rows, most-recently-observed first.
- `list_ignored_transfers(*, db)` — all ignored source→target pairs.
- `unignore_calibration_transfer(source, target, *, db)` — delete one pair.
- `clear_ignored_transfers(*, db)` — delete all ignored pairs.
- `reset_all_calibrations(*, db)` — delete all learned-calibration rows (does not touch settings or transfer ratios).

New routes in `routes/user_profile.py` (all `success_response()` / `error_response()`):

- `GET  /api/user_profile/calibration/dashboard` — `{learned: [...], ignored_transfers: [...]}`.
- `POST /api/user_profile/calibration/unignore_transfer` — `{source_exercise, target_exercise}`.
- `POST /api/user_profile/calibration/clear_ignored_transfers`.
- `POST /api/user_profile/calibration/reset_all`.

### Acceptance criteria

- The dashboard route returns learned rows + ignored pairs and never mutates state.
- Un-ignore removes exactly one pair and leaves the source's exact learned calibration intact (restoring related fallback for that target).
- Clear-ignored removes all ignored pairs only.
- Reset-all clears all learned-calibration rows but leaves `user_calibration_settings` and `exercise_transfer_ratios` untouched.
- Estimator output is byte-for-byte unchanged by adding this surface (no priority/math change).
- All new responses use the standard contract; bulk actions confirm in the UI.

### Out of scope for 2B

Promote-to-Profile (2C), Profile/plan-row writes, auto-apply, fatigue/volume-aware suggestions (2D), user-visible/seeded transfer ratios, and `calibration_events` history.

## Phase 2A Related-Exercise Transfer Plan

### Product Principle

Related transfer should be conservative and explainable:

- Use related logs only when the target exercise has no usable exact learned calibration and no exact last-log fallback.
- Keep the existing Profile reference chain as the fallback if related evidence is weak, stale, or hard to explain.
- Never silently overwrite Profile lifts, planned program rows, or historical logs.
- Show that a suggestion is transferred, not exact: e.g. `Related: learned from Barbell Bench Press`.
- Allow the user to reset/ignore a transferred source without deleting the source exercise's exact calibration.

### Priority

Phase 2A estimator priority should be:

1. Exact exercise learned calibration.
2. Exact last-log fallback.
3. Related exercise learned calibration.
4. Profile reference lifts.
5. Cold-start demographics.
6. Static default.

This keeps exact user evidence above transferred evidence. It also means a single target-exercise log immediately suppresses related transfer for that target.

### Settings

Use the existing reserved settings fields before adding new user-facing modes:

- `user_calibration_settings.mode`: remains `off` / `suggest`.
- `user_calibration_settings.allow_related_exercise_learning`: must default to `0`.
- No settings row must still behave as fully off.
- Related transfer can only run when `mode == 'suggest'` and `allow_related_exercise_learning == 1`.

Do not add `auto_apply` in Phase 2A.

### Transfer Eligibility

A source calibration may transfer to a target exercise only when all are true:

- Source has usable confidence (`medium` or `high`) and at least `MIN_RELATED_LOGS` valid source logs.
- Source is not stale by exact-calibration rules.
- Source and target are not the same exact exercise.
- Target has no usable exact learned calibration and no exact last-log fallback.
- Target is not excluded by `classify_tier()`.
- Source and target pass a deterministic relationship rule.
- The relationship has an explainable transfer ratio.
- The user has not ignored this source-target pair.

### Relationship Rules

Start with a deterministic, testable relationship score. Do not use fuzzy text similarity as the primary signal.

Inputs available today:

- `lift_key` from `utils.lift_matching.match_direct_lift_key()`.
- `primary_muscle_group`.
- `movement_pattern`.
- `equipment`.
- `mechanic`.
- Existing per-hand vs total-load handling via `_load_basis_factor()`.

Initial allowed relations:

1. **Same direct lift key**: e.g. barbell bench variants that map to the same key-lift vocabulary.
2. **Same primary muscle + same movement pattern + compatible mechanic**: e.g. horizontal push to horizontal push, squat to squat.
3. **Equipment-compatible pairs only**: barbell/machine/cable/dumbbell/bodyweight compatibility must be explicit, not inferred from names.

Initial blocked relations:

- Different primary muscle.
- Different movement pattern, unless manually whitelisted.
- Unilateral vs bilateral transfers until a ratio is explicitly defined.
- Bodyweight exercises where external load is not the main performance variable.
- Exercises classified as `excluded`.
- Any pair whose load basis cannot be explained as total-load or per-hand.

### Transfer Ratios

Do not hard-code one universal ratio for all related exercises.

Recommended first slice:

- Add a small `exercise_transfer_ratios` table for curated source-target pairs.
- Store directional ratios (`source_exercise_name`, `target_exercise_name`, `ratio`, `basis`, `confidence`, `notes`).
- Seed only a tiny safe set after review, or allow the table to start empty and prove the plumbing first.
- Direction matters: `bench -> incline dumbbell press` is not necessarily the same as `incline dumbbell press -> bench`.

If an MVP-without-seed is preferred, Phase 2A can first compute candidates but never return them until ratios exist. That gives tests and dashboard/audit visibility without changing Workout Controls behavior.

### Suggested Schema

Additive, idempotent tables:

#### `exercise_transfer_ratios`

- `id`
- `source_exercise_name`
- `target_exercise_name`
- `source_lift_key`
- `target_lift_key`
- `ratio`
- `load_basis`: `total_to_total`, `total_to_per_hand`, `per_hand_to_total`, `per_hand_to_per_hand`
- `relationship_type`: `same_lift_key`, `same_pattern`, `manual`
- `confidence`: `low`, `medium`, `high`
- `notes`
- `created_at`
- `updated_at`

#### `ignored_calibration_transfers`

- `id`
- `source_exercise_name`
- `target_exercise_name`
- `created_at`

Optional later table for Phase 2B:

#### `calibration_events`

- `id`
- `event_type`
- `exercise_name`
- `related_source_exercise_name`
- `payload_json`
- `created_at`

### Algorithm Sketch

When estimating a target exercise:

1. Run the shipped exact learned lookup.
2. Run the shipped exact last-log lookup.
3. If both miss, and related learning is enabled, query candidate source calibrations.
4. Join candidate source rows to explicit transfer ratios for the target.
5. Discard ignored source-target pairs.
6. Discard low-confidence, stale, excluded, or unsupported-basis candidates.
7. Convert source `estimated_1rm` through the directional ratio and load-basis factor to produce target `estimated_1rm`.
8. Use the target exercise's rep goals and the existing progression helper to derive target `suggested_weight` where possible.
9. Pick the highest-confidence candidate; tie-break by most recent `last_observed_at`, then largest sample count.
10. Return `source: "related_learned"`, `reason: "related_calibration"`, and a trace that names the source exercise and ratio.

### Trace Requirements

Workout Controls trace must show:

- Source exercise.
- Source confidence and sample count.
- Source observed top set / e1RM.
- Relationship type.
- Transfer ratio and load-basis conversion.
- Final progression decision.
- Why exact learned/log data did not apply.

Example:

```text
Source: Related learned calibration
Learned from: Barbell Bench Press, 4 recent logs, confidence high
Transfer: Bench Press -> Incline Dumbbell Press, ratio 0.72, total-load to per-hand
Estimated strength: 92 kg source e1RM -> 33 kg/hand target
Progression: maintain and build reps
```

### User Controls

Phase 2A controls:

- Enable/disable related learned suggestions in Profile.
- Reset learned data for the target exercise (already exists for exact rows).
- Ignore this related source for this target.
- Keep current.
- Apply suggestion client-side only.

Do not add promote-to-Profile or auto-apply in Phase 2A.

### Data Lifecycle

- `/erase-data` must clear transfer ratios only if they are user-generated. If curated app-default ratios are shipped, they should be recreated by startup/seed logic rather than deleted permanently.
- Deleting a source workout log should recompute the exact source calibration; related suggestions should derive from the new exact row at read time instead of storing copied related rows.
- Deleting a target log should not delete source calibration.
- Backup/restore must be safe with old snapshots missing Phase 2 tables.
- The workout-log write path must continue reusing the open `DatabaseHandler`.

### Open Decisions For Opus Review

1. Should Phase 2A ship with zero default transfer ratios first, proving plumbing without behavior change?
2. Which first 10-20 source-target pairs are safe enough to seed?
3. Should related transfer use source `suggested_weight` or source `estimated_1rm` as the ratio input?
4. Should exact last-log fallback always beat related learned evidence, or should stale/low-quality exact logs fall below high-confidence related evidence?
5. Should unilateral/bilateral pairs be blocked for the whole first slice?
6. Should machine/cable exercises require manual ratios only?
7. Is a per-exercise ignore enough, or do we need ignore-by-source-target pair from the start?
8. How should bodyweight-loaded movements be represented, or should they remain blocked?

### Phase 2A Acceptance Criteria

- With related learning disabled, estimate endpoint output is byte-for-byte equivalent to shipped MVP behavior.
- With related learning enabled but no transfer ratios, output is still unchanged.
- The first Phase 2A implementation slice ships with zero seeded transfer ratios.
- With one valid curated transfer ratio, target uses related calibration only after exact learned and exact log miss.
- Exact target log immediately suppresses related transfer.
- Low/stale source confidence does not override Profile reference lifts.
- Trace clearly names source exercise, relationship, ratio, confidence, and fallback reason.
- Reset/ignore controls do not delete the source exercise's exact learned calibration.

## Strength Formula

Learned calibration must use the existing canonical app formula:

```python
epley_1rm(weight, reps)
```

That function currently caps reps at 12:

```text
estimated_1rm = weight * (1 + min(reps, 12) / 30)
```

RIR should not be added to reps for e1RM in MVP. RIR/RPE should be used for set-quality and progression decisions, not for defining a second strength formula.

Example:

```text
120 kg x 8 @ 2 RIR
canonical e1RM = 120 * (1 + 8 / 30) = 152 kg
```

If the product later wants an RIR-adjusted e1RM, it should be changed deliberately app-wide, routed through one shared helper, documented with worked examples, and covered by re-baselined tests.

## Progression Engine

Learned calibration should not create a duplicate next-weight engine.

The estimator should delegate next-target decisions to the existing progression logic in `utils/progression_plan.py`, especially:

- effort window: RIR 1-3 or RPE 7-9
- increase weight after reaching the top of the rep range with acceptable effort
- maintain weight while building reps
- reduce weight after repeated below-range performance
- existing increment rules

Implementation should extract a public reusable helper from `utils/progression_plan.py` if needed. Do not call private progression helpers from the estimator, and do not duplicate progression rules in `utils/strength_calibration.py`.

## Settings Default

No settings row should behave as `off`.

This preserves existing behavior and protects current estimator tests. Turning learned suggestions on should be an explicit user action from the Profile settings UI.

Required regression guard:

- With no `user_calibration_settings` row, the estimate endpoint must produce the same output as the current estimator chain for existing Profile/log scenarios.

## Estimate Priority

### MVP Priority

1. Exact exercise learned calibration, only when settings mode is `suggest` and confidence is usable.
2. Exact last-log fallback.
3. Profile reference lifts.
4. Cold-start demographics.
5. Static default.

### Phase 2 Priority

1. Exact exercise learned calibration.
2. Exact last-log fallback.
3. Related exercise learned calibration.
4. Profile reference lifts.
5. Cold-start demographics.
6. Static default.

Exact-exercise evidence must always beat related-exercise transfer.

## Confidence Constants

Confidence must be numeric enough to test. Start with named constants in `utils/strength_calibration.py`:

```python
MIN_EXACT_LOGS_MEDIUM = 1
MIN_EXACT_LOGS_HIGH = 3
MAX_RECENT_DAYS = 90
STALE_AFTER_DAYS = 180
MAX_E1RM_VARIANCE_PCT_HIGH = 10
# Phase 2 reserved constants:
MIN_RELATED_LOGS = 3
MIN_RELATED_CONFIDENCE = "medium"
```

Initial confidence rules:

- `high`: at least 3 valid exact logs, latest valid log within 90 days, and e1RM variance within 10%.
- `medium`: at least 1 valid exact log within 180 days.
- `low`: valid but stale, sparse, missing effort data, or inconsistent.
- `none`: invalid, incomplete, unsupported, or settings disabled.

RIR/RPE presence can raise the quality score, but missing RIR/RPE should not invalidate a log that has plausible weight and reps.

## User Experience

Workout Controls should show a compact source line when learned suggestions are enabled:

```text
120 kg x 6-8, 2 RIR
Learned from 3 recent squat logs - confidence: high
```

Expandable details should show:

- Last valid top set.
- Canonical e1RM.
- Progression decision.
- Rounding logic.
- Confidence reason.

Example:

```text
Source: Learned calibration
Last valid top set: 120 kg x 8 @ 2 RIR
Estimated strength: ~152 kg e1RM
Progression: maintain 120 kg and aim for the top of the rep range
Confidence: high
```

## Notifications

After a meaningful scored log update:

```text
Calibration updated for Barbell Full Squat.
```

If confidence is low:

```text
Logged set saved. More data needed before learned calibration changes this exercise.
```

If calibration is disabled:

```text
Logged set saved. Learned calibration is currently off.
```

Do not notify about related exercises in MVP.

## User Actions

MVP actions:

- `Enable learned suggestions`
- `Disable learned suggestions`
- `Apply suggestion`
- `Keep current`
- `Reset learned data for this exercise`

For MVP, `Apply suggestion` is client-side only. It should populate the current Workout Controls inputs with the suggested weight/reps/RIR/RPE and should not persist to `user_selection` or call a new plan-row update endpoint. Persisting suggested values into planned program rows can be considered later as an explicit user action with its own endpoint, response-contract tests, and migration notes.

Phase 2 actions:

- `Reset all learned calibration`
- `Promote to Profile reference lift`
- `Ignore related calibration`

## Data Model

Shipped MVP tables:

### `learned_strength_calibrations`

- `id`
- `exercise_name`
- `lift_key`
- `primary_muscle`
- `estimated_1rm`
- `suggested_weight`
- `suggested_min_reps`
- `suggested_max_reps`
- `suggested_rir`
- `suggested_rpe`
- `confidence`
- `sample_count`
- `last_log_id`
- `last_observed_at`
- `source`
- `created_at`
- `updated_at`

Normalize before persisting:

- `primary_muscle` must use `normalize_muscle()`.
- `lift_key` must reuse the existing key-lift vocabulary from `utils/profile_estimator.py`.

### `user_calibration_settings`

- `id INTEGER PRIMARY KEY CHECK (id = 1)`
- `mode`: `off`, `suggest`
- `allow_related_exercise_learning`, reserved for Phase 2 and default `0`
- `min_sessions_for_related`, reserved for Phase 2
- `updated_at`

Phase 2A should add `exercise_transfer_ratios` and `ignored_calibration_transfers` only if related transfer is enabled. Phase 2B can add `calibration_events` when the Profile dashboard or audit history has a real consumer.

## Data Lifecycle

Add all calibration tables to:

- app startup table creation
- `tests/conftest.py` app setup
- `tests/conftest.py` erase/cleanup table lists
- production `/erase-data` route in `app.py`

Handle stale calibration references:

- On `/delete_workout_log`, either invalidate affected calibration rows or recompute calibration for the deleted exercise.
- On `/erase-data`, delete all calibration rows.
- Prefer recompute-on-write and invalidate-on-delete for MVP.

Backup and restore should remain safe for old snapshots. These tables are additive and idempotent; restoring a pre-calibration backup should leave learned calibration empty, with settings behaving as `off`.

## DatabaseHandler Requirement

The workout-log hook must reuse the open `DatabaseHandler`.

When `/update_workout_log` updates a row, call calibration with `db=db` inside the same handler block. Do not open a nested `DatabaseHandler` while the write path is active.

## Shipped MVP Tasks

1. Create `utils/strength_calibration.py`.
2. Add numeric confidence constants.
3. Add calibration tables in `utils/database.py`.
4. Register table creation during app startup and tests.
5. Register table cleanup in test fixtures and production erase-data flow.
6. Implement exact-exercise calibration from recent logs.
7. Use existing `epley_1rm()` for strength estimates.
8. Extract or expose a public progression helper and delegate next-target decisions to it.
9. Add calibration update after successful `/update_workout_log`, reusing the existing DB handler.
10. Invalidate or recompute calibration on `/delete_workout_log`.
11. Extend `utils/profile_estimator.py` with learned calibration only when settings mode is `suggest`.
12. Add trace fields for learned calibration.
13. Add settings and per-exercise reset endpoints.
14. Add Profile UI controls for calibration settings.
15. Add Workout Controls source badges and explanation details.
16. Add migration notes because estimator priority changes product behavior.

## Phase 2A Development Tasks

1. Lock the transfer model after Opus/product review.
2. Add additive Phase 2A tables in `utils/database.py`.
3. Register table creation during app startup and tests.
4. Register table cleanup in test fixtures and production erase-data flow.
5. Extend settings helpers to read/write `allow_related_exercise_learning`.
6. Add a small backend helper that returns eligible related candidates for a target exercise.
7. Add explicit transfer-ratio lookup and load-basis conversion.
8. Add ignored source-target pair helpers and reset/ignore endpoints.
9. Extend `utils/profile_estimator.py` with related learned lookup after exact log fallback.
10. Add trace fields for related learned calibration.
11. Add Profile UI toggle for related suggestions, gated behind learned suggestions.
12. Add Workout Controls copy/actions for related-source suggestions.
13. Add migration notes because estimator priority can change behavior.
14. Keep promote-to-Profile, dashboard, auto-apply, and fatigue-aware changes out of Phase 2A.

## Testing Plan

### Shipped MVP Unit Tests

- Canonical `epley_1rm()` is used; no RIR-adjusted formula is introduced.
- RIR/RPE affect quality/progression, not e1RM definition.
- Invalid logs are ignored.
- Incomplete logs are ignored.
- Recent logs outrank old logs.
- Exact exercise calibration updates.
- Confidence constants produce expected high/medium/low bands.
- Reset removes learned calibration.
- Missing settings row behaves as `off`.
- Settings mode `off` disables learned estimates.
- Profile fallback still works when learned calibration is disabled or unavailable.
- Existing last-log fallback still works.

### Phase 2A Unit Tests

- Relationship rules allow only explicit same-lift-key / same-pattern compatible pairs.
- Blocked relations do not produce candidates.
- Transfer ratios are directional.
- Per-hand vs total-load conversion is applied once.
- Related confidence uses source confidence, sample count, staleness, and `MIN_RELATED_LOGS`.
- Ignored source-target pairs are excluded.
- Related transfer is unavailable when no settings row exists.
- Related transfer is unavailable when `mode == 'off'`.
- Related transfer is unavailable when `allow_related_exercise_learning == 0`.
- Exact learned calibration outranks related learned calibration.
- Exact last-log fallback outranks related learned calibration.
- Related learned calibration outranks Profile only when all eligibility gates pass.

### Shipped MVP Route Tests

- `/update_workout_log` updates calibration after scored data changes.
- `/update_workout_log` reuses the existing DB handler path without nested writes.
- Estimate endpoint returns learned source only when settings mode is `suggest`.
- Estimate endpoint falls back to current behavior when no settings row exists.
- Reset endpoint clears the correct calibration rows.
- Delete-log endpoint invalidates or recomputes affected calibration.
- All new responses use `success_response()` / `error_response()`.

### Phase 2A Route Tests

- Settings endpoint persists `allow_related_exercise_learning`.
- Invalid related settings values return structured errors.
- Estimate endpoint returns related source only when both learned and related settings are enabled.
- Estimate endpoint falls back unchanged when related is disabled.
- Estimate endpoint falls back unchanged when no transfer ratio exists.
- Ignore endpoint clears only the selected source-target relation.
- Ignore endpoint does not delete source exact calibration.
- All new responses use `success_response()` / `error_response()`.

### Shipped MVP Integration Tests

- With settings off, log `120 kg` squat and verify current estimator output is unchanged.
- With settings on, log `120 kg` squat and verify learned exact-exercise output.
- Verify Profile reference lift rows are not overwritten.
- Verify current exact-log behavior remains available as fallback.
- Verify erase-data removes calibration tables.

### Phase 2A Integration Tests

- With related disabled, a source calibration plus transfer ratio does not affect target estimate.
- With related enabled and no exact target data, target estimate uses the related source.
- After logging the target exercise once, target estimate uses exact last-log fallback instead of related.
- After creating usable exact target calibration, target estimate uses exact learned instead of related.
- Deleting the source's last usable log removes the related suggestion.
- Ignoring a source-target pair restores Profile/cold-start fallback for that target.
- Profile reference lift rows are not overwritten.
- Existing exact-calibration MVP tests remain green unchanged.

### Shipped MVP E2E Tests

- User enables learned suggestions in Profile.
- User edits scored workout log.
- User sees calibration toast.
- User opens Workout Controls.
- User sees learned source badge and explanation.
- User resets learned calibration.
- User disables learned suggestions and sees fallback behavior.

### Phase 2A E2E Tests

- User enables related learned suggestions in Profile.
- User opens Workout Controls for a related target with no exact logs.
- User sees related-source badge, source exercise name, confidence, and trace details.
- User applies the related suggestion client-side.
- User ignores the related source and sees fallback behavior.
- User disables related learned suggestions and sees fallback behavior while exact learned suggestions remain available.

### Visual Testing

Workout Controls badges and Profile settings UI can change visual snapshots. If the UI changes are intentional, run scoped Chromium visual snapshot updates and document them, following the pattern used for prior visual baseline changes.

### Verification Gate

This feature touches product-risk surfaces:

- `utils/database.py`
- `tests/conftest.py`
- `routes/workout_log.py`
- `utils/profile_estimator.py`
- Profile and Workout Plan UI

Required gate:

- targeted pytest during development
- full pytest before merge
- relevant Chromium Playwright specs
- visual snapshot review if UI changes
- product-risk review focused on estimator behavior and data lifecycle

## Recommended Build Order

MVP build order is complete through item 8 below:

1. Exact exercise calibration backend.
2. Settings default-off behavior and regression guard.
3. Estimator priority integration.
4. Workout-log update hook with injected DB handler.
5. Reset and delete invalidation.
6. Trace/source display in Workout Controls.
7. Profile settings UI.
8. E2E and visual coverage.

Phase 2A recommended order:

1. Opus/product review of the transfer model and first allowed ratio set.
2. Add Phase 2A tables and cleanup/reinit paths.
3. Extend settings backend and Profile toggle.
4. Implement candidate generation behind `allow_related_exercise_learning`.
5. Implement transfer-ratio lookup and related trace construction.
6. Integrate estimator priority after exact last-log fallback.
7. Add ignore source-target endpoint and Workout Controls action.
8. Add focused pytest, then E2E for the related-source UI.
9. Run full pytest and relevant Chromium Playwright specs.

This order keeps related transfer behind an explicit second switch until the model is reviewable and testable.
