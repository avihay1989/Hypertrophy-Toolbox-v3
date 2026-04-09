# Auto Starter Plan Generator - Implementation Tracker

## Project Overview
Movement-pattern-driven workout plan generator.

## Implementation Status

### Phase 1: Core Generator [x] Complete
- [x] Movement pattern taxonomy (`utils/movement_patterns.py`)
  - MovementPattern enum (Squat, Hinge, Push/Pull horizontal/vertical, Core, Isolation)
  - MovementSubpattern enum (bilateral/unilateral, thrust/deadlift, etc.)
  - Pattern classification with keyword matching
- [x] Database schema updates (`utils/db_initializer.py`)
  - Added `movement_pattern` column to exercises table
  - Added `movement_subpattern` column to exercises table
  - Auto-population on initialization
- [x] Session blueprints for 1-3 day splits
  - A: Hinge → H.Push → H.Pull → Squat → Core → LowerIso → UpperIso
  - B: Squat → V.Pull → V.Push → Hinge → Core → UpperIso → LowerIso
  - C: Thrust → Mixed Push → Mixed Pull → Unilateral Squat → Core → Isos
- [x] Exercise selection with goal-sensitive scoring
- [x] Prescription calculator (sets, reps, RIR)
- [x] API endpoints (`routes/workout_plan.py`)
  - POST `/generate_starter_plan`
  - GET `/get_generator_options`
- [x] UI modal and form (`templates/workout_plan.html`)
- [x] Unit tests (38 tests passing)

### Phase 2: Enhanced Features [x] Complete

#### 2.1 Double Progression Logic [x]
- [x] Update `generate_progression_suggestions()` in `utils/progression_plan.py`
- [x] Check if scored_max_reps >= planned_max_reps (hit top of range)
- [x] Suggest weight increase when top of range achieved
- [x] Suggest rep increase when below minimum range
- [x] Conservative behavior for novices
- [x] Add tests for double progression (25 tests)

**Rules:**
| Condition | Suggestion |
|-----------|------------|
| scored_max_reps >= planned_max_reps | Increase weight (+2.5kg if <20kg, else +5kg) |
| scored_max_reps < planned_min_reps | Keep weight, push reps back into range |
| scored_max_reps in range | Continue current load |

#### 2.2 Priority Muscle Reallocation [x]
- [x] Add `priority_muscles` parameter to generator config
- [x] When priority muscles selected:
  - [x] Add +1 set to existing accessory targeting that muscle, OR
  - [x] Boost main lifts if no accessories available
- [x] Stay within 15-24 sets/session budget
- [x] Reduce non-essential add-ons first ("clear volume for volume")
- [x] Never remove core movement patterns
- [x] Add tests

#### 2.3 Pattern Coverage in Summaries [x]
- [x] Add to weekly/session summary:
  - [x] Total sets per routine (warn if outside 15-24)
  - [x] Movement pattern coverage counts
  - [x] Flag missing patterns
  - [x] Flag extreme skew (too much isolation, no hinge, etc.)
- [x] Update `utils/weekly_summary.py` with `calculate_pattern_coverage()`
- [x] Add API endpoint `/api/pattern_coverage`
- [x] Add tests

### Phase 3: Future Enhancements [x] Complete
- [x] AMRAP/EMOM execution styles
  - Added columns: `execution_style`, `time_cap_seconds`, `emom_interval_seconds`, `emom_rounds`
  - UI API endpoint for setting execution style
  - GET `/api/execution_style_options` for frontend options
  - POST `/api/execution_style` for updating exercise execution style
- [x] Merge mode (keep existing + add missing patterns)
  - Added `merge_mode` parameter to `generate_starter_plan()`
  - When enabled, only adds exercises for missing movement patterns
  - Preserves existing exercises in routines
- [x] Time budget optimization
  - Added `time_budget_minutes` parameter (15-180 minutes)
  - Estimates workout duration based on exercise types and sets
  - Automatically reduces volume to fit within time budget
  - Response includes `estimated_duration_minutes` per routine
- [x] Superset auto-suggestion for accessories
  - GET `/api/superset/suggest` endpoint
  - Suggests optimal superset pairings based on antagonist muscle groups
  - Excludes already-supersetted exercises

---

## Technical Decisions

### Schema: 2-Field Approach (Chosen)
Kept `movement_pattern` + `movement_subpattern` instead of 3-field approach.

**Rationale:**
- Already working and tested
- Plane is effectively encoded in pattern names (HORIZONTAL_PUSH vs VERTICAL_PUSH)
- Less migration effort
- Same expressive power

### Overwrite Mode and Merge Mode (Phase 3 Update)
Generator now supports both `overwrite=true` (default) and `merge_mode=true`.

**Merge Mode:**
- Keep existing exercises and only add missing patterns
- Useful for enhancing existing plans
- `merge_mode=true` automatically sets `overwrite=false`

---

## Files Modified/Created

### Phase 1 (Complete)
| File | Action | Purpose |
|------|--------|---------|
| `utils/movement_patterns.py` | Created | Pattern taxonomy, blueprints, classification |
| `utils/plan_generator.py` | Created | Generator logic, scoring, prescriptions |
| `utils/db_initializer.py` | Modified | Added pattern columns, auto-population |
| `routes/workout_plan.py` | Modified | Added API endpoints |
| `templates/workout_plan.html` | Modified | Added modal and button |
| `static/js/app.js` | Modified | Added `generateStarterPlan()` |
| `tests/test_plan_generator.py` | Created | 38 unit/integration tests |

### Phase 2 (Complete)
| File | Action | Purpose |
|------|--------|---------|
| `utils/progression_plan.py` | Modified | Double progression logic with smart suggestions |
| `utils/plan_generator.py` | Modified | Priority muscle reallocation, MUSCLE_TO_PATTERNS mapping |
| `utils/weekly_summary.py` | Modified | Added `calculate_pattern_coverage()` function |
| `routes/weekly_summary.py` | Modified | Added `/api/pattern_coverage` endpoint |
| `routes/workout_plan.py` | Modified | Added `priority_muscles` to generator endpoint |
| `tests/test_double_progression.py` | Created | 25 tests for progression logic |

### Phase 3 (Complete)
| File | Action | Purpose |
|------|--------|---------|
| `utils/db_initializer.py` | Modified | Added `execution_style`, `time_cap_seconds`, `emom_interval_seconds`, `emom_rounds` columns |
| `utils/plan_generator.py` | Modified | Added merge mode, time budget optimization, duration estimation |
| `routes/workout_plan.py` | Modified | Added execution style endpoints, superset suggestion endpoint |
| `tests/test_phase3_features.py` | Created | Tests for Phase 3 features |
| `tests/test_pattern_coverage.py` | Created | 15 tests for pattern coverage |

---

## Test Coverage

### Phase 1 Tests
- `test_plan_generator.py`: 38 tests
  - Pattern classification
  - Blueprint validation
  - Prescription rules
  - Config validation
  - Integration tests

### Phase 2 Tests
- `test_double_progression.py`: 25 tests
  - Weight increment calculation
  - Effort acceptability checks
  - Progression status determination
  - Consistency analysis
  - Suggestion generation integration
- `test_pattern_coverage.py`: 15 tests
  - Muscle-to-pattern mappings
  - Config validation
  - Coverage analysis structure
  - API endpoint responses

**Total: 302 tests passing**

---

## API Reference

### POST `/generate_starter_plan`

Generate a new workout plan based on movement patterns.

**Request Body:**
```json
{
  "training_days": 2,
  "environment": "gym",
  "experience_level": "novice",
  "goal": "hypertrophy",
  "volume_scale": 1.0,
  "equipment_whitelist": ["Barbell", "Dumbbells", "Cable"],
  "exclude_exercises": ["Deadlift"],
  "movement_restrictions": {"no_overhead_press": true},
  "priority_muscles": ["Chest", "Biceps"],
  "time_budget_minutes": 60,
  "merge_mode": false,
  "persist": true,
  "overwrite": true
}
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `training_days` | int | 3 | Sessions per week (1-5) |
| `environment` | string | "gym" | "gym" or "home" |
| `experience_level` | string | "novice" | "novice", "intermediate", "advanced" |
| `goal` | string | "hypertrophy" | "hypertrophy", "strength", "general" |
| `volume_scale` | float | 1.0 | Volume multiplier (0.5-1.5) |
| `equipment_whitelist` | array | null | Filter available equipment |
| `exclude_exercises` | array | null | Exercises to exclude |
| `movement_restrictions` | object | null | Movement limitations |
| `priority_muscles` | array | null | Muscles to prioritize |
| `time_budget_minutes` | int | null | Target workout duration in minutes (15-180) |
| `merge_mode` | bool | false | Keep existing exercises, only add missing patterns |
| `persist` | bool | true | Save to database |
| `overwrite` | bool | true | Replace existing routines (ignored if merge_mode=true) |

**Response:**
```json
{
  "success": true,
  "data": {
    "routines": {
      "A": [
        {
          "routine": "A",
          "exercise": "Romanian Deadlift",
          "sets": 3,
          "min_rep_range": 6,
          "max_rep_range": 10,
          "rir": 2,
          "rpe": 8.0,
          "weight": 0.0,
          "exercise_order": 1,
          "pattern": "hinge",
          "role": "main"
        }
      ]
    },
    "total_exercises": 14,
    "sets_per_routine": {"A": 21, "B": 21},
    "persisted": true
  }
}
```

### GET `/get_generator_options`

Get available options for the plan generator.

**Response:**
```json
{
  "success": true,
  "data": {
    "training_days": {"min": 1, "max": 3, "default": 2},
    "environments": ["gym", "home"],
    "experience_levels": ["novice", "intermediate", "advanced"],
    "goals": ["hypertrophy", "strength", "general"],
    "available_equipment": ["Barbell", "Dumbbells", ...],
    "movement_restrictions": ["no_overhead_press", "no_deadlift"],
    "priority_muscles": {
      "available": ["Chest", "Biceps", "Quadriceps", ...],
      "max_selections": 2
    }
  }
}
```

### GET `/api/pattern_coverage`

Analyze movement pattern coverage in current workout plan.

**Response:**
```json
{
  "success": true,
  "data": {
    "per_routine": {
      "A": {"squat": 3, "hinge": 3, "horizontal_push": 3, ...}
    },
    "total": {"squat": 6, "hinge": 6, ...},
    "warnings": [
      {
        "level": "high",
        "type": "missing_pattern",
        "message": "Missing vertical pull exercises",
        "description": "Consider adding pull-ups or lat pulldowns."
      }
    ],
    "sets_per_routine": {"A": 21, "B": 21},
    "ideal_sets_range": {"min": 15, "max": 24}
  }
}
```

### POST `/api/execution_style` (Phase 3)

Set AMRAP/EMOM execution style for an exercise.

**Request Body:**
```json
{
  "exercise_id": 123,
  "execution_style": "amrap",
  "time_cap_seconds": 90
}
```

**Execution Styles:**
| Style | Parameters | Description |
|-------|------------|-------------|
| `standard` | (none) | Traditional set-based training |
| `amrap` | `time_cap_seconds` (10-600) | As Many Reps As Possible within time cap |
| `emom` | `emom_interval_seconds` (15-180), `emom_rounds` (1-20) | Every Minute On the Minute |

**Response:**
```json
{
  "ok": true,
  "data": {
    "id": 123,
    "exercise": "Bicep Curl",
    "execution_style": "amrap",
    "time_cap_seconds": 90,
    "emom_interval_seconds": null,
    "emom_rounds": null
  }
}
```

### GET `/api/execution_style_options` (Phase 3)

Get execution style options with descriptions and tooltips.

**Response:**
```json
{
  "ok": true,
  "data": {
    "styles": {
      "standard": {"name": "Standard", "description": "Traditional set-based training"},
      "amrap": {"name": "AMRAP", "full_name": "As Many Reps As Possible", "defaults": {"time_cap_seconds": 60}},
      "emom": {"name": "EMOM", "full_name": "Every Minute On the Minute", "defaults": {"emom_interval_seconds": 60, "emom_rounds": 5}}
    },
    "limits": {
      "time_cap_seconds": {"min": 10, "max": 600},
      "emom_interval_seconds": {"min": 15, "max": 180},
      "emom_rounds": {"min": 1, "max": 20}
    }
  }
}
```

### GET `/api/superset/suggest` (Phase 3)

Get automatic superset pairing suggestions based on antagonist muscle groups.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `routine` | string | Optional routine name to filter suggestions |

**Response:**
```json
{
  "ok": true,
  "data": {
    "suggestions": [
      {
        "routine": "A",
        "exercise_1": {"id": 1, "name": "Bench Press", "muscle": "Chest"},
        "exercise_2": {"id": 2, "name": "Barbell Row", "muscle": "Upper Back"},
        "reason": "Antagonist pair: Chest / Upper Back - allows one muscle to rest while the other works",
        "benefit": "Saves time without compromising performance"
      }
    ],
    "total_pairs": 3
  }
}
```

---

## Movement Pattern Taxonomy

### Primary Patterns

| Pattern | Category | Description | Example Exercises |
|---------|----------|-------------|-------------------|
| `squat` | Lower Body | Hip + knee extension (anterior chain) | Back Squat, Leg Press, Bulgarian Split Squat |
| `hinge` | Lower Body | Hip extension, minimal knee (posterior chain) | Deadlift, RDL, Hip Thrust, Good Morning |
| `horizontal_push` | Upper Body | Horizontal pressing | Bench Press, Push-ups, Chest Fly |
| `vertical_push` | Upper Body | Vertical pressing | OHP, Dips, Arnold Press |
| `horizontal_pull` | Upper Body | Horizontal pulling | Barbell Row, Face Pull, Cable Row |
| `vertical_pull` | Upper Body | Vertical pulling | Pull-ups, Lat Pulldown |
| `core_static` | Core | Anti-movement/stability | Plank, Pallof Press, Carries |
| `core_dynamic` | Core | Movement-based | Leg Raises, Crunches, Rotations |
| `upper_isolation` | Isolation | Upper body accessories | Curls, Extensions, Lateral Raises |
| `lower_isolation` | Isolation | Lower body accessories | Leg Curl, Leg Extension, Calf Raises |

### Subpatterns

| Subpattern | Parent Pattern | Description |
|------------|----------------|-------------|
| `bilateral_squat` | squat | Both legs (squat, leg press) |
| `unilateral_squat` | squat | Single leg (split squat, lunge) |
| `hip_thrust` | hinge | Glute-dominant hip extension |
| `deadlift` | hinge | Deadlift variations |
| `goodmorning` | hinge | Good morning variations |
| `bicep_curl` | upper_isolation | Elbow flexion |
| `tricep_extension` | upper_isolation | Elbow extension |
| `lateral_raise` | upper_isolation | Shoulder abduction |
| `leg_curl` | lower_isolation | Knee flexion |
| `leg_extension` | lower_isolation | Knee extension |
| `calf_raise` | lower_isolation | Ankle plantar flexion |

---

## Session Blueprints

### 1-Day Split (Routine A Only)
Full-body session covering all major patterns:
```
1. Hinge (main) - e.g., Deadlift
2. Horizontal Push (main) - e.g., Bench Press
3. Horizontal Pull (main) - e.g., Barbell Row
4. Squat (main) - e.g., Back Squat
5. Core (accessory) - e.g., Plank
6. Lower Isolation (accessory) - e.g., Leg Curl
7. Upper Isolation (accessory) - e.g., Bicep Curl
```

### 2-Day Split (A/B Rotation)
**Routine A:**
```
1. Hinge (main)
2. Horizontal Push (main)
3. Horizontal Pull (main)
4. Squat (main)
5. Core (accessory)
6. Lower Isolation (accessory)
7. Upper Isolation (accessory)
```

**Routine B:**
```
1. Squat (main)
2. Vertical Pull (main)
3. Vertical Push (main)
4. Hinge (main)
5. Core (accessory)
6. Upper Isolation (accessory)
7. Lower Isolation (accessory)
```

### 3-Day Split (A/B/C Rotation)
Adds Routine C with emphasis on unilateral and thrust patterns:
```
1. Hip Thrust (main)
2. Mixed Push (main)
3. Mixed Pull (main)
4. Unilateral Squat (main)
5. Core (accessory)
6. Upper Isolation (accessory)
7. Lower Isolation (accessory)
```

---

## Rep Range Rules

### By Goal + Exercise Type

| Exercise Type | Hypertrophy | Strength | General |
|---------------|-------------|----------|---------|
| Lower body technical compound | 6-10 | 3-6 | 5-8 |
| Upper body technical compound | 6-12 | 3-6 | 5-10 |
| Machine/low-tech compound | 8-15 | 6-10 | 8-12 |
| Isolation | 10-15 | 8-12 | 10-15 |
| Core | 10-15 | 8-12 | 10-15 |

### By Session Order
- **Early exercises** (slots 1-3): Use lower end of rep range
- **Late exercises** (slots 5+): Use higher end of rep range

### Sets Per Role

| Role | Novice | Intermediate | Advanced |
|------|--------|--------------|----------|
| Main lift | 3 | 4 | 4-5 |
| Accessory | 2 | 2-3 | 3 |

### Session Volume Targets
- **Minimum**: 15 sets/session
- **Maximum**: 24 sets/session
- **Typical**: 18-21 sets/session

---

## Double Progression Algorithm

```
FOR each exercise in workout_log:
  IF scored_max_reps >= planned_max_reps AND acceptable_effort:
    → Suggest: "Increase weight by {increment}kg"
    increment = 2.5kg if current_weight < 20kg else 5kg
    (novices always get 2.5kg)
    
  ELSE IF scored_max_reps < planned_min_reps:
    IF consecutive_failures >= 2:
      → Suggest: "Reduce weight by {increment}kg"
    ELSE:
      → Suggest: "Keep weight, focus on adding reps"
      
  ELSE (in range but not at top):
    → Suggest: "Continue current load, add {reps_to_top} reps"
```

**Acceptable Effort:**
- RIR 1-3 (close to failure but not grinding)
- RPE 7-9 (challenging but controlled)

---

## Priority Muscle Reallocation

When `priority_muscles` is specified:

1. **Find relevant exercises** by pattern or muscle group match
2. **Boost volume**:
   - Add +1 set to accessories targeting priority muscles
   - Cap accessories at 4 sets max
   - If no accessories available, boost main lifts (up to 5 sets)
3. **If over budget** (>24 sets), use "clear volume for volume":
   - Reduce non-priority isolation sets first
   - Never reduce core movement patterns (squat/hinge/push/pull)

**Muscle-to-Pattern Mapping Example:**
```python
"chest" → patterns: [HORIZONTAL_PUSH]
        → isolation: [FLY]
        
"biceps" → patterns: [HORIZONTAL_PULL, VERTICAL_PULL]
         → isolation: [BICEP_CURL]
         
"quadriceps" → patterns: [SQUAT]
             → isolation: [LEG_EXTENSION]
```

---

## References
- User spec document (Feb 2026)
- Existing `SUPERSET_FEATURE.md` for execution style patterns
