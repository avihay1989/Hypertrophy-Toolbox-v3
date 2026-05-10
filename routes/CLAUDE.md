# routes/ — Orientation

## Purpose
HTTP layer. Each file is one Flask blueprint that validates input, calls `utils/`, and returns a response. No business logic, no direct DB access — those live in `utils/`.

## Key files
| File | Blueprint / route |
|---|---|
| `main.py` | `main_bp` — `GET /` (welcome) |
| `workout_plan.py` | `workout_plan_bp` — plan CRUD, starter generator, replace-exercise |
| `workout_log.py` | `workout_log_bp` — log table + updates |
| `weekly_summary.py` | `weekly_summary_bp` — `/weekly_summary`, `/api/pattern_coverage` |
| `session_summary.py` | `session_summary_bp` — `/session_summary` |
| `progression_plan.py` | `progression_plan_bp` — double-progression page + goals |
| `volume_splitter.py` | `volume_splitter_bp` — split-allocator UI + API |
| `user_profile.py` | `user_profile_bp` — reference lifts + estimate API |
| `program_backup.py` | `program_backup_bp` — `/api/backups` snapshot/restore |
| `filters.py` | `filters_bp` — `/api/exercises`, `/api/available_filters` (column whitelist lives here) |
| `exports.py` | `exports_bp` — CSV export |

`POST /erase-data` is a direct route in `app.py:130`, not a blueprint.

## Conventions
- All JSON returns via `success_response()` / `error_response()` from `utils/errors.py`.
- New blueprints register in **three** places: `routes/X.py`, `app.py`, `tests/conftest.py` (fixture). Missing the third = 404 in tests.
- Logger: `from utils.logger import get_logger` then `logger = get_logger()`. Never `print()`.
- Dynamic column names must pass `validate_column_name()` in `filters.py:147` before SQL interpolation.

## Gotchas
- **Latent SQLi risk**: `utils/filter_cache.py:85` interpolates column/table names. Only `warm_cache()` calls it today; any new caller must pre-validate.
- **Known response-contract exceptions** (legacy, do not propagate): `weekly_summary.py:133,139` and `workout_plan.py:1079,1093,1114,1125`.
- No auth — single-user local. Do not expose to untrusted networks.

## See also
- `.claude/rules/routes.md` — endpoint template, response contract, filter/SQL detail
- root [CLAUDE.md](../CLAUDE.md) §2 (architecture) and §5 (current risks)
