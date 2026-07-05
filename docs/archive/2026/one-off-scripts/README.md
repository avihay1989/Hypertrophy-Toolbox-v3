# Archived one-off scripts (2026)

These scripts were run once (or a handful of times) during a specific migration,
cleanup, or verification pass and have **no remaining code, test, CI, or scheduled
caller** in the repository. They were moved here in WP0.3 (Phase 0, Deep Refactor
Plan) to keep `scripts/` limited to live tooling. They are preserved verbatim as a
historical record — they are not maintained and may not run against the current
schema without adjustment.

`docs/archive/**` is excluded from `pyrightconfig.json`, so these files are no longer
part of the static-analysis surface or the pyright baseline.

## Old path → archived path, and current replacement

### `mapping/` — free-exercise-db mapping pipeline (one-off generation)

| Original path | Reason archived | Current replacement |
|---|---|---|
| `scripts/map_free_exercise_db.py` | One-off generator that produced `data/free_exercise_db_mapping.csv` proposals for human review (workout-cool §4 checkpoint 3). | The curated `data/free_exercise_db_mapping.csv` is committed and applied by the **live** `scripts/apply_free_exercise_db_mapping.py`. |
| `scripts/curate_free_exercise_db_mapping.py` | One-off structural-equivalence curation pass over that CSV (§4 checkpoint 4). | Same — curation is baked into the committed CSV; apply via `scripts/apply_free_exercise_db_mapping.py`. |

### `fatigue/` — fatigue cleanup dry-runs and Stage-4 manual smokes

| Original path | Reason archived | Current replacement |
|---|---|---|
| `scripts/fatigue_stage1_cleanup_dryrun.py` | Dry-run twin of the Stage-1 catalog cleanup. | Live idempotent reproducer `scripts/fatigue_stage1_cleanup.py` (kept). |
| `scripts/fatigue_movement_pattern_cleanup_dryrun.py` | Dry-run twin of the movement-pattern cleanup. | Live reproducer `scripts/fatigue_movement_pattern_cleanup.py` (kept). |
| `scripts/fatigue_stage4_mutation_smoke.py` | One-off Stage-4 manual mutation smoke. | Playwright port `e2e/fatigue-stage4-smokes.spec.ts` (independent, in CI) + live `scripts/fatigue_stage4_observer.py` / `scripts/fatigue_stage4_status.py`. |
| `scripts/fatigue_stage4_remaining_smokes.py` | One-off Stage-4 badge-coherence / remaining smokes. | Same as above. |
| `scripts/fatigue_stage4_restore_smoke.py` | One-off Stage-4 restore smoke. | Same as above. |

### `visual/` — visual-baseline seed (one-off)

| Original path | Reason archived | Current replacement |
|---|---|---|
| `scripts/seed_visual_baseline.py` | One-off seed for `e2e/visual-baseline-thumbnails.spec.ts` inspection artifacts. **Not** the live visual-seed pipeline. | Live visual-seed pipeline: `e2e/scripts/prepare_visual_db.py` + `e2e/scripts/build_visual_seed.py`, selected by `PW_VISUAL_SEED=1` in `playwright.config.ts`. |

## Preserved live tooling (NOT archived)

`scripts/apply_free_exercise_db_mapping.py`, `scripts/fatigue_stage1_cleanup.py`,
`scripts/fatigue_movement_pattern_cleanup.py`, `scripts/fatigue_stage4_observer.py`,
`scripts/fatigue_stage4_status.py`, `scripts/fatigue_calibration_report.py`,
`scripts/pyright_baseline_diff.py`, and the `e2e/scripts/` visual-seed pipeline all
remain in place because they have live callers (tests, CI, or the running app).
