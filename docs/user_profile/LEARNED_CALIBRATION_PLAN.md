# Learned Calibration Plan

## Status

This is a planning document, not an implementation ticket ready to code without review. The MVP should be a low-risk exact-exercise learning feature. Related-exercise propagation belongs in Phase 2.

## Goal

Add a learned calibration layer so Workout Controls suggestions can improve from the user's logged performance, not only from Profile reference lifts, demographics, or static defaults.

Example target behavior:

- Profile suggests `Barbell Full Squat - quadriceps focused` at `81.5 kg`.
- User logs `120 kg x 6-8 @ 2 RIR`.
- After learned calibration is enabled, the same squat variation produces a better next Workout Controls suggestion.
- The app explains why the suggestion changed and lets the user keep, apply, reset, or disable learned calibration.

## Current Behavior

The current estimate flow prioritizes:

1. Last logged set for the exact exercise.
2. Profile reference lifts.
3. Cold-start demographics.
4. Static default.

Exact exercises adapt today, but only by mirroring the latest logged row. Similar exercises do not learn from logs. Cross-exercise propagation exists only through Profile reference lifts, and workout logs do not write back to those reference lifts.

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

Likely MVP tables:

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

Phase 2 can add `calibration_events` when the Profile dashboard or audit history needs a real consumer.

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

## Development Tasks

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

## Testing Plan

### Unit Tests

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

### Route Tests

- `/update_workout_log` updates calibration after scored data changes.
- `/update_workout_log` reuses the existing DB handler path without nested writes.
- Estimate endpoint returns learned source only when settings mode is `suggest`.
- Estimate endpoint falls back to current behavior when no settings row exists.
- Reset endpoint clears the correct calibration rows.
- Delete-log endpoint invalidates or recomputes affected calibration.
- All new responses use `success_response()` / `error_response()`.

### Integration Tests

- With settings off, log `120 kg` squat and verify current estimator output is unchanged.
- With settings on, log `120 kg` squat and verify learned exact-exercise output.
- Verify Profile reference lift rows are not overwritten.
- Verify current exact-log behavior remains available as fallback.
- Verify erase-data removes calibration tables.

### E2E Tests

- User enables learned suggestions in Profile.
- User edits scored workout log.
- User sees calibration toast.
- User opens Workout Controls.
- User sees learned source badge and explanation.
- User resets learned calibration.
- User disables learned suggestions and sees fallback behavior.

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

1. Exact exercise calibration backend.
2. Settings default-off behavior and regression guard.
3. Estimator priority integration.
4. Workout-log update hook with injected DB handler.
5. Reset and delete invalidation.
6. Trace/source display in Workout Controls.
7. Profile settings UI.
8. E2E and visual coverage.
9. Phase 2 related-exercise calibration plan.

This order gives the user a meaningful exact-exercise learning improvement first, while keeping cross-exercise learning behind a separate, more deliberate design pass.
