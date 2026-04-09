# Superset Feature

## Overview
Superset feature that allows users to visually link 2 exercises within the same routine to be performed back-to-back.

## Status: ✅ Complete

---

## Feature Summary

| Feature | Description |
|---------|-------------|
| Classic superset | Links exactly 2 exercises |
| Same routine constraint | Both exercises must be in the same routine |
| Visual color-coding | 4 rotating colors (purple, teal, green, orange) + bracket connector |
| Drag & drop | Maintains superset adjacency when reordering |
| Excel export | Row highlighting with matching colors |
| Exercise removal | Removes link, partner remains unlinked |
| Program backup/load | Supersets persist across save/load |
| Starter plan generator | Respects overwrite/merge mode |
| Workout log | Supersets NOT carried to log (by design) |

---

## API Endpoints

### POST `/api/superset/link`
Link 2 exercises as a superset.

**Request:**
```json
{"exercise_ids": [123, 456]}
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "superset_group": "SS-A-1738766400000",
    "exercises": [
      {"id": 123, "exercise": "Bench Press"},
      {"id": 456, "exercise": "Barbell Row"}
    ]
  }
}
```

### POST `/api/superset/unlink`
Unlink a superset.

**Request:**
```json
{"exercise_id": 123}
```

### GET `/api/superset/suggest`
Get automatic superset pairing suggestions based on antagonist muscle groups.

**Query params:** `?routine=A` (optional)

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
        "reason": "Antagonist pair: Chest / Upper Back",
        "benefit": "Saves time without compromising performance"
      }
    ],
    "total_pairs": 3
  }
}
```

---

## Files

| File | Purpose |
|------|---------|
| `utils/db_initializer.py` | `superset_group` column migration |
| `routes/workout_plan.py` | Link/unlink/suggest API endpoints |
| `routes/exports.py` | Superset ordering in export query |
| `utils/export_utils.py` | Excel row highlighting (4 colors) |
| `utils/program_backup.py` | Save/load superset data |
| `static/js/modules/workout-plan.js` | UI selection & actions |
| `static/css/styles_workout_plan.css` | Visual styles (colors, brackets, badges) |
| `templates/workout_plan.html` | Checkbox column |
| `tests/test_superset.py` | 14 automated tests |

---

## Test Coverage

**Total project tests:** 321 passing

**Superset tests (14):**
- `test_link_superset_success`
- `test_link_superset_different_routines_fails`
- `test_link_superset_requires_exactly_two_exercises`
- `test_link_superset_already_in_superset_fails`
- `test_link_superset_exercise_not_found`
- `test_unlink_superset_by_exercise_id`
- `test_unlink_exercise_not_in_superset`
- `test_unlink_requires_exercise_id_or_superset_group`
- `test_get_workout_plan_includes_superset_group`
- `test_remove_exercise_unlinks_partner`
- `test_backup_includes_superset_group`
- `test_generate_plan_overwrite_clears_supersets`
- `test_generate_plan_no_overwrite_preserves_existing_supersets`
- `test_reorder_preserves_superset_group`

---

## Technical Notes

- **Superset group format**: `SS-{routine}-{timestamp}` for uniqueness
- **Color cycling**: 4 CSS variables (`--superset-color-1` through `--superset-color-4`)
- **Adjacency**: Supersetted exercises are always sorted adjacent in queries
- **Workout Log**: Explicitly excludes superset data (per requirements)
