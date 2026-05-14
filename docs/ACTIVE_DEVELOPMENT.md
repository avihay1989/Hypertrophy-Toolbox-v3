# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

Finish workout.cool §4 exercise thumbnails through mapping curation, mapping apply, route contracts, thumbnail UI, escaping, and validation.

## Current Branch

`feat/workout-cool-section-4-checkpoint-3`

Known history:

- `origin/main` at `7a77315`: workout.cool §4 checkpoint 2, free-exercise-db assets vendored.
- Current branch at `1ff57ff`: workout.cool §4 checkpoint 3, mapping proposals and coverage report generated.

## Already Done

- §4 checkpoint 1: `media_path` schema, path validator, and `scripts/apply_free_exercise_db_mapping.py`.
- §4 checkpoint 2: `static/vendor/free-exercise-db/` assets, `LICENSE`, `NOTICE.md`, `VERSION`, `exercises.json`, and 873 `0.jpg` images.
- §4 checkpoint 3: `scripts/map_free_exercise_db.py`, `data/free_exercise_db_mapping.csv`, and `docs/workout_cool_integration/checkpoint3_coverage.md`.
- §4 checkpoint 4 (in-branch, uncommitted): `scripts/curate_free_exercise_db_mapping.py` flipped 98 rows `auto` → `confirmed` via the structural-equivalence rule; a follow-up manual pass flipped 10 rows to `manual` and 5 rows to `rejected`. Final review-status distribution: 1784 auto, 98 confirmed, 10 manual, 5 rejected — **113 reviewed** rows, clearing the §4.7 tertiary acceptance bar (≥50). Scoped apply dry-run on the 108 confirmed+manual rows passes cleanly. Targeted pytest gate `tests/test_free_exercise_db_mapping.py`: **79 passed in 2.52s on 2026-05-14**. Stale `assert rows == []` in `TestMappingCsv.test_csv_passes_validator` was retired (it pre-dated the populated CSV in `1ff57ff`).
- Fatigue meter Phase 1 / Stage 4 entry is parked by owner choice (Option 1 confirmed 2026-05-13). Do not work on fatigue unless explicit reopen criteria are met.

## Next Task

Commit the in-branch checkpoint-4 slice, then open checkpoint 5.

### Step 1 — commit checkpoint 4

Stage only these files:

- `scripts/curate_free_exercise_db_mapping.py` (new)
- `data/free_exercise_db_mapping.csv` (curated)
- `tests/test_free_exercise_db_mapping.py` (stale-assertion fix)
- `docs/workout_cool_integration/EXECUTION_LOG.md` (follow-up entry)
- `docs/MASTER_HANDOVER.md` (current-state update)
- `docs/ACTIVE_DEVELOPMENT.md` (this file)
- `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` (new) + `docs/fatigue_meter/PLANNING.md` + `docs/fatigue_meter/calibration-notes.md` (the matching 2026-05-13 parked-decision slice referenced from `MASTER_HANDOVER.md`)

Do **not** stage unrelated dirty files: `data/database.db`, `.mcp.json`, `.claude/settings.json`, `package.json`, `package-lock.json`, `requirements.txt`, `e2e/nav-dropdown.spec.ts`. They are local/runtime drift and belong in their own commits if anywhere.

### Step 2 — open checkpoint 5 (route SELECT updates + trailing-whitespace fix)

The pre-existing trailing-whitespace catalogue row at CSV line 909 (`'Dumbbell Shoulder Internal Rotation '`) still blocks the unscoped apply dry-run. Resolve via **path (a) — DB-side TRIM in `utils/db_initializer.py`** using the guarded metadata-repair pattern shipped in `6246854`:

```sql
UPDATE exercises SET exercise_name = TRIM(exercise_name)
WHERE exercise_name != TRIM(exercise_name);
```

After that:

1. Regenerate `data/free_exercise_db_mapping.csv` from the cleaned DB and validate (or re-run `scripts/curate_free_exercise_db_mapping.py` if the row content survives the trim).
2. Confirm unscoped `scripts/apply_free_exercise_db_mapping.py --dry-run` is now clean.
3. Add SELECT-column changes to surface `media_path` in the page/JSON contracts:
   - `routes/workout_plan.py` — `/workout_plan` and `/get_workout_plan` (or equivalent JSON endpoint).
   - `routes/workout_log.py` and `utils/workout_log.py` — `/workout_log` and `/get_workout_logs` (or equivalent).
4. Extend `tests/test_workout_plan_routes.py` and `tests/test_workout_log_routes.py` for the new field.
5. Re-run the §4 pytest gate and adjacent regression batch.

### Step 3 — open checkpoint 6 (thumbnail rendering + escapeHtml rollout)

Per PLANNING.md §4.4 Option A — server-rendered thumbnail tags on plan/log pages, plus the `escapeHtml()` rollout in `static/js/modules/workout-plan.js`. Out of scope for checkpoints 4 and 5.

## Agent Authority

Agents may, without asking the owner:

- Update docs that are stale relative to committed branch state.
- Curate high-confidence CSV rows.
- Mark obvious mismatches as `rejected`.
- Add focused tests for the current checkpoint.
- Run targeted pytest / Playwright checks.
- Continue from one listed task to the next after tests pass.

Agents must not:

- Redo checkpoint 2 vendoring.
- Regenerate checkpoint 3 mapping proposals unless the mapper itself changes.
- Mutate committed `data/database.db` as source of truth.
- Start fatigue-meter work.
- Start Phase 2 fatigue planning.
- Edit `utils/fatigue.py`.
- Touch unrelated dirty files unless the active task requires it.

## Stop Conditions

Ask the owner only if:

- A destructive DB reset, branch reset, or file deletion is required.
- License / attribution status is unclear.
- A product behavior change would exceed the approved plan.
- Tests reveal a broad unrelated regression.
- The mapping policy cannot be resolved by the rules above.
- The owner explicitly redirects the work.

Transport failures, idle stream stalls, or stale chat titles are not repo blockers. Start a fresh agent session and point it at this file.

## Required Checkpoint Closeout

Before calling a checkpoint done:

- Update `docs/MASTER_HANDOVER.md`.
- Update `docs/workout_cool_integration/EXECUTION_LOG.md`.
- Record tests run and results.
- Leave the diff commit-ready, with generated DB/runtime files excluded unless explicitly intended.
