# Fatigue Meter - Generated Calibration Report

**Generated:** 2026-05-11
**Seed:** 42
**Source:** existing starter-plan generator with `persist=False`; live routines were not changed.

This report exists so the owner can label generated plans from the full routine data, not from scores alone.
The `intended anchor` column is only the calibration target used to build the scenario; the owner label is the value that matters.

## How to use this report

1. Read each scenario's full routine tables.
2. Write an owner label for each scenario: `light`, `moderate`, `heavy`, or `very_heavy`.
3. Tune thresholds only if at least two owner labels disagree with the computed bands.

## Summary

| Scenario | Intended anchor | Owner label | Generator options | Post-generate edits | Sets | Weekly score | Weekly band | Session scores |
|---|---|---|---|---:|---:|---:|---|---|
| Generated deload / easy 2-day | light |  | `training_days=2, environment='gym', experience_level='novice', goal='general', volume_scale=0.7, time_budget_minutes=45` | `rir_delta=2, set_delta=-1, min_sets=1` | 18 | 28.1 | light | A: 13.9 light, B: 14.2 light |
| Generated normal 3-day hypertrophy | moderate |  | `training_days=3, environment='gym', experience_level='intermediate', goal='hypertrophy', volume_scale=1.0, time_budget_minutes=60` | `none` | 54 | 88.5 | moderate | A: 29.2 moderate, B: 29.9 moderate, C: 29.4 moderate |
| Generated hard 4-day accumulation | heavy |  | `training_days=4, environment='gym', experience_level='intermediate', goal='hypertrophy', volume_scale=1.35, time_budget_minutes=75, priority_muscles=['quadriceps', 'hamstrings']` | `rir_delta=-1` | 86 | 161.9 | moderate | A: 37.0 moderate, B: 43.5 moderate, C: 37.0 moderate, D: 44.4 moderate |
| Generated overreach 5-day strength | very_heavy |  | `training_days=5, environment='gym', experience_level='advanced', goal='strength', volume_scale=2.0, priority_muscles=['quadriceps', 'hamstrings']` | `force_rir=0, set_delta=1` | 140 | 419.6 | very_heavy | A: 72.8 heavy, B: 71.0 heavy, C: 96.6 very_heavy, D: 81.1 very_heavy, E: 98.1 very_heavy |

## Generated deload / easy 2-day

- Intended anchor: `light`
- Computed weekly score: **28.1 (light)**
- Total sets: **18**
- Generator options: `training_days=2, environment='gym', experience_level='novice', goal='general', volume_scale=0.7, time_budget_minutes=45`
- Post-generate edits: `rir_delta=2, set_delta=-1, min_sets=1`
- Owner label: 

### Routine A - 13.9 (light), 9 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Straight Leg Deadlift | hinge | main | 2 | 5-8 | 4 | 3.9 |
| 2 | Dumbbell Press | horizontal_push | main | 2 | 5-8 | 4 | 2.8 |
| 3 | Cable Wide Grip Seated Row | horizontal_pull | main | 2 | 5-8 | 4 | 2.8 |
| 4 | Barbell Low Bar Squat - Quadriceps focused | squat | main | 2 | 5-8 | 4 | 3.7 |
| 5 | Bodyweight Knee Plank Up Down | core_static | accessory | 1 | 10-15 | 5 | 0.7 |

### Routine B - 14.2 (light), 9 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Low Bar Squat - Quadriceps focused | squat | main | 2 | 5-8 | 4 | 3.7 |
| 2 | Pull Ups | vertical_pull | main | 2 | 5-8 | 4 | 2.8 |
| 3 | Cable Standing Shoulder Press | vertical_push | main | 2 | 5-8 | 4 | 3.0 |
| 4 | Stability Ball Glute Bridge | hinge | main | 2 | 5-8 | 4 | 3.9 |
| 5 | Cable Seated Twist | core_dynamic | accessory | 1 | 10-15 | 5 | 0.8 |


## Generated normal 3-day hypertrophy

- Intended anchor: `moderate`
- Computed weekly score: **88.5 (moderate)**
- Total sets: **54**
- Generator options: `training_days=3, environment='gym', experience_level='intermediate', goal='hypertrophy', volume_scale=1.0, time_budget_minutes=60`
- Post-generate edits: `none`
- Owner label: 

### Routine A - 29.2 (moderate), 18 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Straight Leg Deadlift | hinge | main | 3 | 6-10 | 2 | 7.0 |
| 2 | Barbell Larsen Bench Press | horizontal_push | main | 3 | 6-10 | 2 | 5.0 |
| 3 | Dumbbell Kneeling Single Arm Row | horizontal_pull | main | 3 | 6-10 | 2 | 5.0 |
| 4 | Barbell Low Bar Squat - glutes focused | squat | main | 3 | 6-10 | 2 | 6.6 |
| 5 | Dumbbell Suitcase Crunch | core_static | accessory | 2 | 10-20 | 3 | 1.5 |
| 6 | Dumbbell Preacher Curl | upper_isolation | accessory | 2 | 10-15 | 2 | 2.0 |
| 7 | Dumbbell Leg Curl | lower_isolation | accessory | 2 | 10-15 | 2 | 2.2 |

### Routine B - 29.9 (moderate), 18 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Squat - Quadriceps focused | squat | main | 3 | 6-10 | 2 | 6.6 |
| 2 | Machine Assisted Pull Up | vertical_pull | main | 3 | 6-10 | 2 | 5.0 |
| 3 | Dumbbell Arnold Press | vertical_push | main | 3 | 6-10 | 2 | 5.4 |
| 4 | TRX Glute Bridge | hinge | main | 3 | 6-10 | 2 | 7.0 |
| 5 | TRX Side Bend | core_dynamic | accessory | 2 | 10-20 | 3 | 1.7 |
| 6 | Dumbbell Seated Overhead Tricep Extension | upper_isolation | accessory | 2 | 10-15 | 2 | 2.0 |
| 7 | Cable Standing Leg Extension | lower_isolation | accessory | 2 | 10-15 | 2 | 2.2 |

### Routine C - 29.4 (moderate), 18 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Feet Elevated Staggered Glute Bridge | hinge | main | 3 | 6-10 | 2 | 7.0 |
| 2 | Barbell Reverse Grip Bench Press | horizontal_push | main | 3 | 6-10 | 2 | 5.0 |
| 3 | Weighted Chin Ups | vertical_pull | main | 3 | 6-10 | 2 | 5.0 |
| 4 | Barbell Step-up - glutes focused | squat | main | 3 | 6-10 | 2 | 6.6 |
| 5 | Cable Standing Crunch | core_dynamic | accessory | 2 | 10-20 | 3 | 1.7 |
| 6 | Dumbbell Lying Lateral Raise | upper_isolation | accessory | 2 | 10-15 | 2 | 2.0 |
| 7 | Dumbbell Single Leg Calf Raise | lower_isolation | accessory | 2 | 10-15 | 2 | 2.2 |


## Generated hard 4-day accumulation

- Intended anchor: `heavy`
- Computed weekly score: **161.9 (moderate)**
- Total sets: **86**
- Generator options: `training_days=4, environment='gym', experience_level='intermediate', goal='hypertrophy', volume_scale=1.35, time_budget_minutes=75, priority_muscles=['quadriceps', 'hamstrings']`
- Post-generate edits: `rir_delta=-1`
- Owner label: 

### Routine A - 37.0 (moderate), 21 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Incline Bench Press | horizontal_push | main | 4 | 6-10 | 1 | 7.9 |
| 2 | Lever Narrow Grip Seated Row | horizontal_pull | main | 4 | 6-10 | 1 | 7.9 |
| 3 | Barbell Seated Military Press | vertical_push | main | 4 | 6-10 | 1 | 8.6 |
| 4 | Bodyweight Assisted Chin Up | vertical_pull | accessory | 3 | 10-15 | 1 | 5.4 |
| 5 | Dumbbell Concentration Curl | upper_isolation | accessory | 3 | 10-15 | 1 | 3.6 |
| 6 | Cable Pushdown with back support | upper_isolation | accessory | 3 | 10-15 | 1 | 3.6 |

### Routine B - 43.5 (moderate), 22 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Safety Barbell Squat - glutes focused | squat | main | 4 | 6-10 | 1 | 10.6 |
| 2 | Barbell Single Leg Deadlift | hinge | main | 4 | 6-10 | 1 | 11.2 |
| 3 | Dumbbell Split Squat - glutes focused | squat | accessory | 4 | 10-15 | 1 | 9.6 |
| 4 | Machine Plate Loaded Leg Extension | lower_isolation | accessory | 4 | 10-15 | 1 | 5.4 |
| 5 | Machine 45 Degree Calf Raise | lower_isolation | accessory | 3 | 10-15 | 1 | 4.1 |
| 6 | Dumbbell Suitcase Crunch | core_static | accessory | 3 | 10-20 | 2 | 2.6 |

### Routine C - 37.0 (moderate), 21 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Machine Assisted Narrow Pull Up | vertical_pull | main | 4 | 6-10 | 1 | 7.9 |
| 2 | Chest Dip | vertical_push | main | 4 | 6-10 | 1 | 8.6 |
| 3 | Cable Decline Bench Chest Fly | horizontal_push | accessory | 3 | 10-15 | 1 | 5.4 |
| 4 | Cable Upright Row | horizontal_pull | main | 4 | 6-10 | 1 | 7.9 |
| 5 | Dumbbell Incline Lateral Raise | upper_isolation | accessory | 3 | 10-15 | 1 | 3.6 |
| 6 | Dumbbell Rear Delt Fly | upper_isolation | accessory | 3 | 10-15 | 1 | 3.6 |

### Routine D - 44.4 (moderate), 22 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Stability Ball Hip Thrust | hinge | main | 4 | 6-10 | 1 | 11.2 |
| 2 | Safety Barbell Squat - glutes focused | squat | main | 4 | 6-10 | 1 | 10.6 |
| 3 | Barbell Zercher Good Morning | hinge | accessory | 4 | 10-15 | 1 | 10.2 |
| 4 | Cable Seated Leg Curl | lower_isolation | accessory | 4 | 10-15 | 1 | 5.4 |
| 5 | Kettlebell Seated Calf Raise | lower_isolation | accessory | 3 | 10-15 | 1 | 4.1 |
| 6 | Dumbbell Shoulder Internal Rotation  | core_dynamic | accessory | 3 | 10-20 | 2 | 3.0 |


## Generated overreach 5-day strength

- Intended anchor: `very_heavy`
- Computed weekly score: **419.6 (very_heavy)**
- Total sets: **140**
- Generator options: `training_days=5, environment='gym', experience_level='advanced', goal='strength', volume_scale=2.0, priority_muscles=['quadriceps', 'hamstrings']`
- Post-generate edits: `force_rir=0, set_delta=1`
- Owner label: 

### Routine A - 72.8 (heavy), 27 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Reverse Grip Bench Press | horizontal_push | main | 7 | 3-6 | 0 | 21.8 |
| 2 | Dumbbell Weighted Dip - Triceps focused. | vertical_push | main | 7 | 3-6 | 0 | 23.7 |
| 3 | Cable Decline Bench Chest Fly | horizontal_push | accessory | 5 | 6-10 | 0 | 13.2 |
| 4 | Cable Pushdown | upper_isolation | accessory | 3 | 6-10 | 0 | 5.3 |
| 5 | Cable Low Single Arm Lateral Raise | upper_isolation | accessory | 5 | 6-10 | 0 | 8.8 |

### Routine B - 71.0 (heavy), 27 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Bodyweight Assisted Chin Up | vertical_pull | main | 7 | 3-6 | 0 | 21.8 |
| 2 | Cable Seated Cable Row | horizontal_pull | main | 7 | 3-6 | 0 | 21.8 |
| 3 | Dumbbell Kneeling Single Arm Row | horizontal_pull | accessory | 5 | 6-10 | 0 | 13.2 |
| 4 | Dumbbell Curl | upper_isolation | accessory | 3 | 6-10 | 0 | 5.3 |
| 5 | Cable Reverse Fly | upper_isolation | accessory | 5 | 6-10 | 0 | 8.8 |

### Routine C - 96.6 (very_heavy), 29 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Barbell Low Bar Squat - glutes focused | squat | main | 7 | 3-6 | 0 | 29.1 |
| 2 | Barbell Deadlift | hinge | main | 7 | 3-6 | 0 | 30.9 |
| 3 | Barbell Step Up - Quadriceps focused | squat | accessory | 5 | 6-10 | 0 | 17.6 |
| 4 | Cable Hamstring Curl | lower_isolation | accessory | 4 | 6-10 | 0 | 7.9 |
| 5 | Dumbbell Single Leg Calf Raise | lower_isolation | accessory | 4 | 6-10 | 0 | 7.9 |
| 6 | Dumbbell Suitcase Crunch | core_static | accessory | 2 | 8-12 | 0 | 3.1 |

### Routine D - 81.1 (very_heavy), 28 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Dumbbell Bench Press | horizontal_push | main | 7 | 3-6 | 0 | 21.8 |
| 2 | Chin Ups | vertical_pull | main | 7 | 3-6 | 0 | 21.8 |
| 3 | Dumbbell Seated Overhead Press | vertical_push | accessory | 3 | 6-10 | 0 | 8.6 |
| 4 | Dumbbell Lying Row | horizontal_pull | main | 7 | 3-6 | 0 | 21.8 |
| 5 | Cable Preacher Curl | upper_isolation | accessory | 2 | 6-10 | 0 | 3.5 |
| 6 | Dumbbell Skullcrusher | upper_isolation | accessory | 2 | 6-10 | 0 | 3.5 |

### Routine E - 98.1 (very_heavy), 29 sets

| # | Exercise | Pattern | Role | Sets | Reps | RIR | Fatigue |
|---:|---|---|---|---:|---|---:|---:|
| 1 | Plate Glute Bridge to Chest Press | hinge | main | 7 | 3-6 | 0 | 30.9 |
| 2 | Barbell Low Bar Squat - Quadriceps focused | squat | main | 7 | 3-6 | 0 | 29.1 |
| 3 | Barbell Hyperextension | hinge | accessory | 5 | 6-10 | 0 | 18.7 |
| 4 | Cable Seated Leg Extension | lower_isolation | accessory | 4 | 6-10 | 0 | 7.9 |
| 5 | Barbell Toes Up Calf Raise | lower_isolation | accessory | 4 | 6-10 | 0 | 7.9 |
| 6 | TRX Twisting Jack-knife | core_dynamic | accessory | 2 | 8-12 | 0 | 3.5 |

## Optional edit-file format

To test your own post-generate edits, create a JSON file and rerun:

```powershell
python scripts/fatigue_calibration_report.py --edits docs/fatigue_meter/my-calibration-edits.json
```

Example:

```json
{
  "scenarios": {
    "normal_3d": {
      "post_generate": {
        "rir_delta": -1
      },
      "exercise_edits": [
        {
          "match": {
            "routine": "A",
            "exercise_contains": "Squat"
          },
          "set_delta": 1,
          "rir": 1
        }
      ]
    }
  }
}
```

*End of generated calibration report. Regenerate after changing generator behavior or edit inputs.*
