# Related Exercise Transfer Design (Phase 2A)

This document narrows Phase 2 to the first safe implementation slice: related
exercise suggestions only. It intentionally preserves the shipped MVP model in
which `learned_strength_calibrations.exercise_name` stores exact exercise rows.

Canonical planning source: `docs/user_profile/LEARNED_CALIBRATION_PLAN.md`.

## Problem

Learned Calibration now works for the exact exercise the user logged. If the
user logs `Barbell Bench Press`, Workout Controls can learn that exact exercise,
but a related target such as `Incline Dumbbell Bench Press` still falls through
to exact log, Profile, cold-start, or static defaults unless that target has its
own history.

Phase 2A should make related evidence available without mutating exact rows or
pretending transferred evidence is the same as exact evidence.

## Design Principle

Do related transfer at read time.

- Keep exact learned rows keyed by the real logged exercise name.
- Do not normalize variant logs into parent key-lift rows.
- Do not overwrite Profile reference lifts.
- Do not write planned `user_selection` rows.
- Do not auto-apply.
- Do not create related rows copied from source rows.
- Always show source provenance and transfer math in the estimator trace.

This keeps the data model auditable: exact evidence remains exact, and related
evidence is a derived suggestion.

## Estimator Priority

Phase 2A priority:

1. Exact exercise learned calibration.
2. Exact last-log fallback.
3. Related exercise learned calibration.
4. Profile reference lifts.
5. Cold-start demographics.
6. Static default.

An exact target log immediately suppresses related transfer for that target.

## Settings Gate

Related transfer must require both:

- `user_calibration_settings.mode == 'suggest'`
- `user_calibration_settings.allow_related_exercise_learning == 1`

No settings row must behave as fully off. The existing `off` / `suggest` mode
should remain unchanged; do not add `auto_apply` in Phase 2A.

## Transfer Ratios

Use explicit directional ratios. Do not infer ratios from exercise names.

Suggested table:

```text
exercise_transfer_ratios
- id
- source_exercise_name
- target_exercise_name
- source_lift_key
- target_lift_key
- ratio
- load_basis
- relationship_type
- confidence
- notes
- created_at
- updated_at
```

Direction matters. `Barbell Bench Press -> Incline Dumbbell Bench Press` is not
the same claim as the reverse direction.

The first Phase 2A implementation slice should ship with zero default ratios,
proving plumbing without changing Workout Controls behavior. If seeded ratios
are added later, keep the set tiny and reviewed.

## Ignore Controls

Suggested table:

```text
ignored_calibration_transfers
- id
- source_exercise_name
- target_exercise_name
- created_at
```

Ignoring a related suggestion should suppress only that source-target pair. It
must not delete the source exercise's exact learned calibration.

## Read Path

When estimating a target exercise:

1. Run exact learned lookup.
2. Run exact last-log lookup.
3. If both miss and related transfer is enabled, find eligible source
   calibrations.
4. Join sources to explicit transfer ratios for the target.
5. Exclude ignored source-target pairs.
6. Exclude low-confidence, stale, excluded, or unsupported-basis candidates.
7. Apply the directional ratio and load-basis conversion once.
8. Reuse the existing progression helper where possible for target reps/weight.
9. Pick the strongest candidate by confidence, recency, then sample count.
10. Return `source: "related_learned"` and `reason: "related_calibration"`.

## Write Path

The workout-log write path should remain exact-exercise only:

- A scored log recomputes the exact row for that logged exercise.
- Deleting a log recomputes or clears the exact row for that logged exercise.
- Related suggestions are derived later by the estimator.
- The open `DatabaseHandler` reuse requirement still applies.

Do not upsert related or parent-key rows from a variant log in Phase 2A.

## Trace Payload

The trace must make transfer explicit:

```text
Source: Related learned calibration
Learned from: Barbell Bench Press, 4 scored logs, confidence high
Transfer: Barbell Bench Press -> Incline Dumbbell Bench Press, ratio 0.72
Load basis: total-load to per-hand
Progression: maintain and build reps
```

Trace fields should include:

- source exercise
- target exercise
- source confidence
- source sample count
- source e1RM
- relationship type
- transfer ratio
- load-basis conversion
- final suggested target
- fallback reason explaining why exact learned/log data did not apply

## First Slice Tasks

1. Add additive Phase 2A tables.
2. Extend settings read/write helpers for `allow_related_exercise_learning`.
3. Implement read-only related candidate lookup.
4. Integrate related lookup after exact last-log fallback.
5. Add related trace construction.
6. Add ignore source-target endpoint.
7. Add Profile toggle and Workout Controls related-source copy/actions.
8. Add focused unit, route, integration, and E2E tests.

## Review Questions

1. Should the first slice ship with zero seeded ratios?
2. Which source-target pairs are safe enough to seed later?
3. Should related projection use source `estimated_1rm` or source
   `suggested_weight` as the input?
4. Should unilateral/bilateral pairs remain blocked for Phase 2A?
5. Should all machine/cable transfers require manual ratios?
6. Should bodyweight-loaded movements remain blocked?
