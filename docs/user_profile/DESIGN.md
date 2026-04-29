
# DESIGN — User Profile feature constants

> ⚠️ **Frozen as v1 spec (2026-04-26). NOT current truth.**
> This document captured the design constants used during the v1
> implementation slices (A–H). Behaviour has evolved materially
> through post-v1 issues — current truth lives in
> [`utils/profile_estimator.py`](../../utils/profile_estimator.py)
> and the Resolution notes in
> [`development_issues.md`](development_issues.md). Notable drifts:
>
> - **§1, §3.1 — `KEY_LIFTS`:** described as 14 slugs; actual set
>   is ~60 after Issue #6 (broad questionnaire expansion), Issue #9
>   (split combined slugs), and Issue #20 (calves / glutes / lower
>   back additions).
> - **§2.3 — `COMPLEX_ALLOWLIST`:** missing Issue #13 (pull-up /
>   chin-up entries) and Issue #20 additions (`glute bridge`,
>   `b-stance hip thrust`, `seated good morning`, etc.).
> - **§4 — Tier ratios:** the flat `target × TIER_RATIOS[tier]`
>   formula is no longer accurate. Issue #14 introduced
>   `KEY_LIFT_TIER` normalisation
>   (`min(TIER_RATIOS[target] / TIER_RATIOS[reference], 1.0)`) to
>   stop same-tier paths from double-discounting.
> - **§7 — `MUSCLE_TO_KEY_LIFT`:** the table here is the v1
>   14-slug version; chains were rewritten by Issue #20.
> - **§8 — Estimation precedence:** Issue #16 added a cold-start
>   demographic anchor-lift seeding step between profile and
>   default. The §10 "demographics MUST NOT be read by the
>   estimator" hard constraint was deliberately reversed.
> - **§10 — v2 deferrals:** the "confidence indicator" item
>   shipped in Issue #17 as the four-band accuracy classifier.
>
> Treat the sections below as a v1 reference for what was decided
> at the time, not as the current contract. PR reviewers: do not
> use this file to gate behavioural changes.

> Pinned design constants for the User Profile feature. **All values here are normative**: implementing slices must use these exact strings, numbers, and lookup keys.

> Read [PLANNING.md](archive/PLANNING.md) for the surrounding plan. Append progress to [EXECUTION_LOG.md](archive/EXECUTION_LOG.md).

---

## 1. Questionnaire — reference lifts

The questionnaire captures one `(weight_kg, reps)` pair per slug. All lifts are optional.

> *** codex 5.5*** Add one implementation note for Slice-E/D: these lift inputs should mean "a recent hard set you remember", not a calculated 1RM. The estimator already computes Epley 1RM from weight and reps; if the UI copy lets users enter an estimated 1RM plus reps, the downstream estimates will be inflated.

| Slug (`lift_key` column value) | UI label | Notes |
| --- | --- | --- |
| `barbell_bench_press` | Barbell or Dumbbell Bench Press | Either variant; user picks |
| `barbell_back_squat` | Barbell Back Squat | |
| `romanian_deadlift` | Romanian or Conventional Deadlift | Either variant; user picks |
| `triceps_extension` | Triceps Extension | Cable / EZ-bar / dumbbell skull crusher all qualify |
| `barbell_bicep_curl` | Barbell Bicep Curl | |
| `dumbbell_lateral_raise` | Dumbbell Lateral Raise | |
| `military_press` | Military / Shoulder Press | Standing or seated barbell OHP |
| `leg_curl` | Leg Curl | Lying / seated machine |
| `leg_extension` | Leg Extension | Machine |
| `weighted_dips` | Weighted Dips | Belt-loaded |
| `weighted_pullups` | Weighted Pull-ups | Belt-loaded |
| `bodyweight_pullups` | Bodyweight Pull-ups | `weight_kg = 0`; reps = best AMRAP |
| `bodyweight_dips` | Bodyweight Dips | `weight_kg = 0`; reps = best AMRAP |
| `barbell_row` | Barbell Row | Bent-over / Pendlay |

**`KEY_LIFTS`** in `utils/profile_estimator.py` is exactly the frozenset of these 14 slugs.

**Resolved (Opus 4.7, 2026-04-26):** UI copy for the questionnaire (Slice-E) and any inline help in the workout-plan caption (Slice-F) must phrase these inputs as "a recent hard working set you remember (weight × reps)", **not** as a 1RM. The estimator runs Epley over the stored `(weight_kg, reps)`; if a user enters an already-calculated 1RM as `weight_kg` with low reps, the downstream estimate compounds. Concrete copy directive for Slice-E: each row's helper text must say "your recent hard set", and the section header must NOT use the word "1RM".

---

## 2. Tier classification (`classify_tier`)

Returns one of `'complex' | 'accessory' | 'isolated' | 'excluded'`.

### 2.1 Excluded equipment (return `'excluded'` and skip estimation)
Equipment column values (canonical TitleCase per `utils/normalization.py`):
```
Trx
Bosu_Ball
Cardio
Recovery
Yoga
Vitruvian
Band
Stretches
```
**`EXCLUDED_EQUIPMENT`** frozenset uses these exact strings; comparison is case-sensitive after `normalize_equipment()` runs on the DB row.

### 2.2 Isolated tier
Match if **either** condition holds (after lowercase normalization on the values read from DB):
- `mechanic.lower() == 'isolation'`, OR
- `movement_pattern in {'upper_isolation', 'lower_isolation'}` (string values from `utils.movement_patterns.MovementPattern`).

### 2.3 Complex tier
Match if the lowercased exercise name contains **any** keyword from `COMPLEX_ALLOWLIST`:
```
barbell back squat
barbell front squat
back squat
front squat
conventional deadlift
sumo deadlift
romanian deadlift
trap bar deadlift
deadlift
barbell bench press
dumbbell bench press
incline barbell bench
incline dumbbell bench
flat bench press
overhead press
military press
shoulder press
weighted dip
weighted pull-up
weighted pullup
weighted chin-up
weighted chinup
barbell row
pendlay row
t-bar row
bent-over row
hip thrust
power clean
hang clean
snatch
push press
```
Substring match; `'split squat'` does NOT match `'back squat'` or `'front squat'` because the keywords require the leading qualifier.

**Resolved (Opus 4.7, 2026-04-26):** Replaced bare `"clean"` with `"power clean"` and `"hang clean"` to avoid false-positive matches on names like "Cable Clean Grip Row". `"snatch"` retained — the only common false positive is "Snatch Grip Deadlift" which is itself a complex lift, so the misclassification is benign.

### 2.4 Accessory tier
Anything that is not excluded, not isolated, and not in the complex allowlist. Mechanic for these is typically `Compound` or `Hold`.

---

## 3. Epley 1RM (`epley_1rm`)

```
1RM = weight × (1 + min(reps, 12) / 30)
```
- Reps clamped at 12. Above 12 the formula is unreliable; use 12 as ceiling.
- `weight = 0` (bodyweight): function returns `0.0` (not None), and downstream estimator copies reps verbatim and emits `weight = 0`.
- `reps <= 0`: function returns `0.0` (treated as no data).

---

## 4. Tier ratios (`TIER_RATIOS`)

Multiplier applied to a key-lift 1RM to estimate the 1RM of a non-key exercise of the same primary muscle but different tier.

```python
TIER_RATIOS = {
    "complex":   1.00,
    "accessory": 0.70,
    "isolated":  0.40,
}
```

Not user-tunable in v1.

---

## 5. Rep-range → working-set values (`REP_RANGE_PRESETS`)

Used to convert estimated 1RM to a suggested working weight, plus the matching min/max reps and RPE/RIR. The user picks one preset per tier.

```python
REP_RANGE_PRESETS = {
    "heavy":    {"min_rep": 4,  "max_rep": 6,  "pct_1rm": 0.85, "rir": 1, "rpe": 9.0},
    "moderate": {"min_rep": 6,  "max_rep": 8,  "pct_1rm": 0.77, "rir": 2, "rpe": 8.0},
    "light":    {"min_rep": 10, "max_rep": 15, "pct_1rm": 0.65, "rir": 2, "rpe": 7.5},
}
```

**Default sets** for all profile-derived estimates: `sets = 3`.

**Default preferences** when the user has not saved any:
```python
DEFAULT_PREFERENCES = {
    "complex":   "heavy",
    "accessory": "moderate",
    "isolated":  "light",
}
```

---

## 6. Weight rounding (`round_weight`)

Round the `pct_1rm × 1RM × tier_ratio` product before returning it.

> *** codex 5.5*** The current `Barbell` floor of 20 kg conflicts with the worked EZ Bar Preacher Curl example. In the live database, `EZ Bar Preacher Curl` has `equipment = 'Barbell'`; applying a 20 kg floor would turn the documented ~11 kg estimate into 20 kg. Recommendation: make the floor tier/name aware, e.g. apply the 20 kg empty-bar floor only to complex barbell lifts, and use a lower/no floor for isolated barbell/EZ-bar curls. This should be resolved before Slice-C implements `round_weight()`.

| Equipment (post-`normalize_equipment`) | Rounding | Floor |
| --- | --- | --- |
| `Barbell`, `Trapbar`, `Smith_Machine`, `Plate` — **complex tier** | nearest **1.25 kg** | **20 kg** (empty bar) |
| `Barbell`, `Trapbar`, `Smith_Machine`, `Plate` — **accessory / isolated tier** | nearest **1.25 kg** | **1.25 kg** (smallest plate pair on a fixed/EZ bar) |
| `Dumbbells` | nearest **0.5 kg** if result < 10 kg, else nearest **1 kg** | **1 kg** |
| `Cables`, `Machine`, `Kettlebells`, `Medicine_Ball` | nearest **1 kg** | 1 kg |
| `Bodyweight` | always returns `0.0`; rounding skipped | — |
| Anything else (or unknown) | nearest **1 kg** (safe default) | 1 kg |

**Resolved (Opus 4.7, 2026-04-26):** Added explicit floor column. Dumbbells floor at **1 kg** (matches the smallest dumbbell most commercial gyms stock — Opus 4.6 suggested 2 kg but that over-corrects). Floors are applied *after* rounding.

**Resolved (Opus 4.7, 2026-04-26 — codex 5.5 follow-up):** Free-weight floor is now **tier-aware**. The 20 kg empty-bar floor only applies to complex-tier lifts (squat, deadlift, bench, OHP, row, etc.). Accessory/isolated lifts with `equipment = 'Barbell'` (e.g., `EZ Bar Preacher Curl`, `Barbell Bicep Curl`) floor at 1.25 kg, preserving the worked-example `~11 kg` preacher-curl estimate. Implementation note for Slice-C: `round_weight()` therefore takes both `equipment` **and** `tier` as inputs (signature `round_weight(weight: float, equipment: str, tier: str) -> float`); `_estimate_from_profile` already has `tier` available from the `classify_tier()` call earlier in the flow, so plumbing it through is one extra parameter.

### 6.1 Dumbbell weight convention — per hand

**Resolved (Opus 4.7, 2026-04-27 — Issue #10):** All dumbbell weights — both **inputs** (Reference Lifts on `/user_profile`) and **outputs** (Workout Controls suggestions on `/workout_plan`) — are expressed as **weight per hand**, i.e. the mass of one dumbbell. A user holding 20 kg in each hand records `weight_kg = 20` (not 40) for `dumbbell_bench_press`, and the estimator returns `weight = 20` (not 40) for the working weight on a dumbbell exercise.

**Rationale:** Per-hand is the gym industry standard, matches how dumbbells are physically labelled (each dumbbell carries its own per-piece weight), and is what users naturally type when reading the rack.

**No estimator-math change is required.** The chain `epley_1rm` → `TIER_RATIOS` → `REP_RANGE_PRESETS` → `round_weight` is unit-agnostic — it operates on `weight` as an opaque scalar end-to-end. As long as input and output share the same convention (and the user is consistent across questionnaire and Workout Controls), the math is correct without conversion. Aggregations downstream (`utils/weekly_summary.py`, `utils/session_summary.py`) compute `total_volume = sets × reps × weight` and inherit the same convention; per-hand volume is internally consistent across barbell and dumbbell exercises but is **not** directly comparable to total-load tonnage from other tracking apps.

**UI surfacing:**
- `utils/profile_estimator.py:DUMBBELL_LIFT_KEYS` is the canonical set of dumbbell-loaded reference-lift slugs (per-hand convention applies).
- `estimate_for_exercise()` returns `is_dumbbell: bool` on every estimate (true when `normalize_equipment(exercise.equipment) == "Dumbbells"`). The Workout Controls weight field on `/workout_plan` shows a "Per hand (one dumbbell)" hint when this flag is true.
- `routes/user_profile.py:_load_profile_context` flags each questionnaire row's `is_dumbbell` from `DUMBBELL_LIFT_KEYS`. `templates/user_profile.html` renders the same hint below dumbbell weight inputs.

**Migration:** None required (verified 2026-04-27 against `data/database.db`). At cutover, only one dumbbell-slug row had a value (`dumbbell_lateral_raise = 12 kg × 8`) and 12 kg is unmistakably per-hand. All other dumbbell slugs were NULL. New entries flow through the convention via the helper text.

---

## 7. Reference-lift mapping (`MUSCLE_TO_KEY_LIFT`)

Keys are the canonical primary-muscle labels found in `MUSCLE_GROUPS` (`utils/constants.py:4-25`) **and** the `PRIMARY_SET` aliases (`utils/constants.py:162-188`). Values are an ordered fallback chain of `lift_key` slugs — first hit wins.

```python
MUSCLE_TO_KEY_LIFT = {
    # Chest
    "Chest":                 ["barbell_bench_press"],

    # Lower body
    "Quadriceps":            ["barbell_back_squat", "romanian_deadlift"],
    "Hamstrings":            ["leg_curl", "romanian_deadlift"],
    "Gluteus Maximus":       ["romanian_deadlift", "barbell_back_squat"],
    "Glutes":                ["romanian_deadlift", "barbell_back_squat"],  # alias
    "Hip-Adductors":         [],  # no reference lift

    # Back
    "Latissimus Dorsi":      ["weighted_pullups", "bodyweight_pullups", "barbell_row"],
    "Latissimus-Dorsi":      ["weighted_pullups", "bodyweight_pullups", "barbell_row"],  # alias
    "Upper Back":            ["barbell_row", "weighted_pullups"],
    "Mid/Upper Back":        ["barbell_row", "weighted_pullups"],  # alias
    "Middle-Traps":          ["barbell_row"],
    "Trapezius":             ["barbell_row"],
    "Lower Back":            ["romanian_deadlift"],

    # Shoulders
    "Front-Shoulder":        ["military_press", "barbell_bench_press"],
    "Anterior Delts":        ["military_press", "barbell_bench_press"],  # alias
    "Middle-Shoulder":       ["dumbbell_lateral_raise", "military_press"],
    "Medial Delts":          ["dumbbell_lateral_raise", "military_press"],  # alias
    "Rear-Shoulder":         ["barbell_row"],
    "Rear Delts":            ["barbell_row"],  # alias

    # Arms
    "Biceps":                ["barbell_bicep_curl"],  # weighted_pullups removed — added-weight signal misleads cross-fallback (see §10)
    "Triceps":               ["triceps_extension", "weighted_dips", "barbell_bench_press"],

    # No reference lift (estimator falls back to default)
    "Calves":                [],
    "Forearms":              [],
    "Rectus Abdominis":      [],
    "Abs/Core":              [],
    "Neck":                  [],
    "External Obliques":     [],
    "Obliques":              [],
}
```

**Lookup order in `_estimate_from_profile`:**
1. Read `primary_muscle_group` from the exercises row.
2. Run it through `normalize_muscle()` (`utils/normalization.py:178-191`) to canonicalize.
3. Look up the canonical key in `MUSCLE_TO_KEY_LIFT`.
4. Walk the fallback list; return the first slug for which `user_profile_lifts` has a row with `weight_kg IS NOT NULL` (or `reps > 0` for bodyweight slugs).
5. If no entry hits, return `None` — caller falls back to hardcoded defaults.

**Cross-muscle ratio adjustments (already baked into the chain):**
Some fallbacks are cross-muscle approximations (e.g., `Triceps → barbell_bench_press` when triceps_extension and weighted_dips are missing). The estimator applies a flat **0.6 cross-fallback factor** to the resulting 1RM whenever the chosen slug isn't the *first* entry in the chain — captures the rough "shoulder press is ~60% of bench" rule. Constant: `CROSS_FALLBACK_FACTOR = 0.6`.

**Resolved (Opus 4.7, 2026-04-26):** Removed `weighted_pullups` from the Biceps fallback chain. The added-weight on a weighted pull-up is not a reliable cross-fallback signal for biceps strength because the user's bodyweight is not captured (see §10 v2 deferral). For `Latissimus Dorsi`, `weighted_pullups` remains as the *primary* entry — there's no cross-fallback factor on the first entry, and a user who fills that field is intentionally signaling their pulling strength. The biceps chain now degrades to defaults if `barbell_bicep_curl` is missing, which is preferable to producing a misleading ~4 kg curl estimate.

---

## 8. Estimation precedence (orchestrated by `estimate_for_exercise`)

Strict order; first source that yields a result wins.

1. **Last logged set** — most recent row in `workout_log` for this exact exercise name (queried by `id DESC LIMIT 1`, no JOIN). Returns `{weight, sets, min_rep, max_rep, rir, rpe, source: 'log', reason: 'log'}` using `COALESCE(scored_*, planned_*)` columns from the log row.
2. **Profile estimate** — runs `_estimate_from_profile(exercise_row, profile_lifts, preferences)`:
   - Tier = `classify_tier(exercise_row)`
   - If tier == `'excluded'` → return `None` (escalate to step 3).
   - Pick reference lift via §7. If chain exhausted → return `None`.
   - Compute reference 1RM via `epley_1rm(weight_kg, reps)` from `user_profile_lifts`.
   - `target_1rm = reference_1rm × TIER_RATIOS[tier] × cross_fallback_factor_if_applicable`
   - `working_weight = round_weight(target_1rm × preset['pct_1rm'], equipment, tier)`
   - Return `{weight: working_weight, sets: 3, min_rep, max_rep, rir, rpe, source: 'profile', reason: 'profile'}` (or `reason: 'profile_cross'` when a cross-muscle fallback supplied the reference lift).
3. **Hardcoded defaults** — `{weight: 25, sets: 3, min_rep: 6, max_rep: 8, rir: 3, rpe: 7.0, source: 'default', reason: 'default_no_reference'}`. Mirrors the current hardcoded HTML defaults at [templates/workout_plan.html:69-113](../../templates/workout_plan.html#L69-L113).

**`source` field is required on every return.** UI uses it to render the provenance caption.

> *** codex 5.5*** The response contract should also include a stable optional reason such as `reason: 'log'|'profile'|'excluded_equipment'|'missing_reference'|'missing_exercise'|'error'`. Keep `source` for the UI caption, but a reason field will make tests and troubleshooting much cleaner without exposing internal errors to users.

**Resolved (Opus 4.7, 2026-04-26 — codex 5.5 follow-up):** `reason` field **adopted** as a required key on every return from `estimate_for_exercise`. Stable enum:

```
reason ∈ {
    'log',                  # source == 'log'
    'profile',              # source == 'profile' — first-entry fallback chain hit
    'profile_cross',        # source == 'profile' — non-first entry (CROSS_FALLBACK_FACTOR applied)
    'default_excluded',     # source == 'default' — equipment in EXCLUDED_EQUIPMENT
    'default_no_reference', # source == 'default' — empty MUSCLE_TO_KEY_LIFT chain or no profile data
    'default_missing',      # source == 'default' — exercise not found in DB
}
```

`source` (`'log'|'profile'|'default'`) drives UI caption text only — never branched on by tests. `reason` is the contract surface for `tests/test_profile_estimator.py` assertions and for troubleshooting via logs. No exception ever leaves `estimate_for_exercise`; on unexpected DB error, return the default struct with `reason='default_missing'` and emit `logger.exception(...)`.

> 🔍 **REVIEW (Opus 2026-04-26):** The estimation precedence logic is sound. One note for Slice-C2 implementing agents: the "last logged set" lookup queries `workout_log` directly — there is **no need to JOIN to `user_selection`**. The `workout_log` table stores all needed columns (`scored_weight`, `scored_min_reps`, etc.) as recorded at log time. See PLANNING.md Phase C.2 review comment for the exact COALESCE column mapping.

---

## 9. Validation ranges (used by Phase D routes)

| Field | Min | Max | Notes |
| --- | --- | --- | --- |
| `gender` | — | — | One of `{'M', 'F', 'Other'}`; nullable |
| `age` | 10 | 100 | int; nullable |
| `height_cm` | 100 | 250 | float; nullable |
| `weight_kg` (demographics) | 30 | 300 | float; nullable |
| `experience_years` | 0 | 80 | float; nullable |
| `weight_kg` (lifts) | 0 | 1000 | float; nullable |
| `reps` (lifts) | 0 | 100 | int; nullable |
| `lift_key` | — | — | Must be in `KEY_LIFTS` frozenset |
| `tier` | — | — | One of `{'complex','accessory','isolated'}` |
| `rep_range` | — | — | One of `{'heavy','moderate','light'}` |

---

## 10. Open questions / deferred to v2

> *** codex 5.5*** Demographics are collected in v1 but mostly unused by the estimator, except as future context for bodyweight-aware calculations. That is acceptable, but the implementation docs should state it plainly so agents do not invent age/gender/bodyweight formulas late in the build and create unreviewed behavior.

**Resolved (Opus 4.7, 2026-04-26 — codex 5.5 follow-up):** Pinning explicitly. **In v1, `_estimate_from_profile` reads ONLY `user_profile_lifts` and `user_profile_preferences`. It MUST NOT read `gender`, `age`, `height_cm`, `weight_kg`, or `experience_years` from `user_profile`.** Demographics are collected for v2 (bodyweight-add-on for weighted pull-ups/dips, possible age/experience-aware tier ratios) and for the user's own reference, but the estimator function signature does not even take them as inputs. This is a **hard constraint** for Slice-C: any implementation that imports demographic columns into the estimate path is out-of-scope and must be rejected at review.

- **Per-exercise overrides** — user might want to pin "preacher curl uses 65% of standing curl 1RM" rather than the flat 40% tier ratio. Out of scope for v1.
- **Auto-update from logged data** — currently last-logged-set wins, but the questionnaire data is *not* refreshed from logs. A future job could refresh `user_profile_lifts` whenever a heavier 1RM is observed. Out of scope for v1.
- **Bodyweight-add-on for weighted lifts** — a user weighing 80 kg doing weighted pull-ups with +30 kg is moving 110 kg. v1 ignores this; treat the 30 kg as the strength signal directly. If demographics weight is set in v2, we may add it to bodyweight pull-up / dip 1RM calculations.
- **Confidence indicator** — UI could show "estimate based on 3/14 reference lifts". Deferred.
