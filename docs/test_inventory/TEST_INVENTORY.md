# Test inventory (generated — do not hand-edit)

Produced by `scripts/generate_test_inventory.py`. Regenerate with:

```bash
.venv/Scripts/python.exe scripts/generate_test_inventory.py
```

Every test count in this repository's prose should link here rather than restate a number. See `docs/TESTING_STRATEGY_PLANNING.md` blindspot B3 for what happened the last time counts were maintained by hand.

## Totals

| Metric | Value |
|---|---|
| Playwright tests (chromium) | **605** |
| Playwright spec files | **32** |
| Required functional gate — `E2E Functional (Chromium)` | **474** tests across 25 specs |
| pytest collected nodes (deterministic subset) | **2221** across 105 files |
| pytest test files (all) | **106** |
| Hard waits (lines containing waitForTimeout) | **92** across 15 files |

The required-functional figure is derived from the `e2e-functional-shard` job in `.github/workflows/ci.yml`, not typed in, so it cannot disagree with what CI runs.

## Playwright specs

| Spec | Tests | In required functional set |
|---|---:|:---:|
| `accessibility.spec.ts` | 24 | yes |
| `api-integration.spec.ts` | 57 | yes |
| `body-composition.spec.ts` | 9 | yes |
| `browser-navigation-state.spec.ts` | 3 | yes |
| `dark-mode.spec.ts` | 6 | yes |
| `empty-states.spec.ts` | 16 | yes |
| `erase-flow.spec.ts` | 2 | — |
| `error-handling.spec.ts` | 12 | yes |
| `exercise-interactions.spec.ts` | 21 | yes |
| `fatigue-context.spec.ts` | 6 | — |
| `fatigue-stage4-smokes.spec.ts` | 5 | yes |
| `fatigue.spec.ts` | 8 | yes |
| `learned-calibration.spec.ts` | 8 | yes |
| `listener-cleanup.spec.ts` | 3 | — |
| `nav-dropdown.spec.ts` | 7 | yes |
| `program-backup.spec.ts` | 20 | — |
| `progression.spec.ts` | 26 | yes |
| `replace-exercise-errors.spec.ts` | 3 | yes |
| `smoke-navigation.spec.ts` | 10 | yes |
| `summary-pages.spec.ts` | 20 | yes |
| `superset-edge-cases.spec.ts` | 12 | yes |
| `ui-hardening.spec.ts` | 37 | yes |
| `user-profile.spec.ts` | 24 | yes |
| `validation-boundary.spec.ts` | 23 | yes |
| `visual-baseline-thumbnails.spec.ts` | 18 | — |
| `visual-field-separator.spec.ts` | 42 | yes |
| `visual.spec.ts` | 66 | — |
| `volume-progress.spec.ts` | 16 | yes |
| `volume-splitter.spec.ts` | 27 | yes |
| `workout-log.spec.ts` | 23 | yes |
| `workout-plan-desktop-contract.spec.ts` | 16 | — |
| `workout-plan.spec.ts` | 35 | yes |

## pytest files

`env-dependent` marks a file whose collected count varies with the machine, not the code. Those counts are deliberately not committed — a committed number would report drift on every host that differs from whoever regenerated last — so the headline total above is the deterministic subset and reproduces byte-for-byte on Windows and Linux.

- **`tests/test_guard_destructive_command.py`** — Parametrized over the PowerShell hosts actually installed (HOSTS = [n for n in ('powershell', 'pwsh') if shutil.which(n)], line 58). A Windows box has both and collects 322; the ubuntu runner has pwsh only and collects 163. That is the point of the file -- the guard once passed under pwsh 7 and was a parser error under Windows PowerShell 5.1 -- so the variance is the design, not drift.

| File | Collected |
|---|---:|
| `tests/test_agent_workflow_contracts.py` | 75 |
| `tests/test_auto_backup.py` | 7 |
| `tests/test_body_composition_routes.py` | 20 |
| `tests/test_body_fat.py` | 43 |
| `tests/test_bootstrap_version_contract.py` | 1 |
| `tests/test_calibration_integration.py` | 28 |
| `tests/test_catalog_invariants.py` | 2 |
| `tests/test_catalog_seed.py` | 3 |
| `tests/test_catalog_seed_bootstrap.py` | 10 |
| `tests/test_catalog_upgrade.py` | 19 |
| `tests/test_config.py` | 20 |
| `tests/test_constants.py` | 45 |
| `tests/test_css_audit_digest_normalization_contracts.py` | 5 |
| `tests/test_css_cascade_contracts.py` | 30 |
| `tests/test_css_field_separator_contracts.py` | 10 |
| `tests/test_css_theme_dark_p3_audit_contracts.py` | 37 |
| `tests/test_css_wp4_4_a11y_contracts.py` | 36 |
| `tests/test_css_wp4_4_a_baseline_contracts.py` | 9 |
| `tests/test_css_wp4_4_base_contracts.py` | 8 |
| `tests/test_css_wp4_4_components_contracts.py` | 9 |
| `tests/test_css_wp4_4_i_is_repair_contracts.py` | 8 |
| `tests/test_css_wp4_4_layout_contracts.py` | 15 |
| `tests/test_css_wp4_4_motion_contracts.py` | 5 |
| `tests/test_css_wp4_4_navbar_contracts.py` | 19 |
| `tests/test_css_wp4_4_theme_dark_contracts.py` | 7 |
| `tests/test_database_dispatch.py` | 25 |
| `tests/test_database_user_profile.py` | 4 |
| `tests/test_db_migration.py` | 7 |
| `tests/test_double_progression.py` | 30 |
| `tests/test_downstream_normalization.py` | 5 |
| `tests/test_effective_sets.py` | 42 |
| `tests/test_erase_data_guard.py` | 10 |
| `tests/test_error_page_contract.py` | 7 |
| `tests/test_errors_utils.py` | 31 |
| `tests/test_exercise_manager.py` | 37 |
| `tests/test_exercise_media.py` | 6 |
| `tests/test_export_weekly_summary_sheet.py` | 4 |
| `tests/test_exports.py` | 52 |
| `tests/test_fatigue.py` | 134 |
| `tests/test_fatigue_context.py` | 29 |
| `tests/test_fatigue_golden.py` | 1 |
| `tests/test_fatigue_routes.py` | 14 |
| `tests/test_fatigue_stage4_observer.py` | 26 |
| `tests/test_filter_predicates.py` | 39 |
| `tests/test_filter_registry.py` | 10 |
| `tests/test_filter_values.py` | 8 |
| `tests/test_free_exercise_db_mapping.py` | 85 |
| `tests/test_guard_destructive_command.py` | env-dependent |
| `tests/test_harness_isolation.py` | 3 |
| `tests/test_lift_matching.py` | 3 |
| `tests/test_logger.py` | 14 |
| `tests/test_maintenance.py` | 19 |
| `tests/test_muscle_selector_mapping.py` | 15 |
| `tests/test_node_version_contract.py` | 3 |
| `tests/test_normalization.py` | 6 |
| `tests/test_package_asset_staging.py` | 22 |
| `tests/test_packaging_contract.py` | 5 |
| `tests/test_pattern_coverage.py` | 23 |
| `tests/test_phase3_features.py` | 19 |
| `tests/test_plan_generator.py` | 35 |
| `tests/test_plan_generator_refactor_contracts.py` | 6 |
| `tests/test_playwright_version_contract.py` | 1 |
| `tests/test_priority0_api_contract.py` | 11 |
| `tests/test_priority0_filters.py` | 16 |
| `tests/test_priority0_fk_integrity.py` | 8 |
| `tests/test_priority7_error_handling.py` | 28 |
| `tests/test_profile_estimator.py` | 95 |
| `tests/test_profile_estimator_contract.py` | 6 |
| `tests/test_program_backup.py` | 36 |
| `tests/test_progression_plan_routes.py` | 18 |
| `tests/test_progression_plan_utils.py` | 46 |
| `tests/test_pyright_baseline_diff.py` | 13 |
| `tests/test_python_version_contract.py` | 13 |
| `tests/test_real_app_db_isolation.py` | 5 |
| `tests/test_replace_exercise.py` | 17 |
| `tests/test_runtime_migration.py` | 24 |
| `tests/test_runtime_paths.py` | 22 |
| `tests/test_schema_registry.py` | 5 |
| `tests/test_session_summary.py` | 30 |
| `tests/test_session_summary_routes.py` | 31 |
| `tests/test_static_cache_policy.py` | 12 |
| `tests/test_strength_calibration.py` | 36 |
| `tests/test_superset.py` | 14 |
| `tests/test_superset_service.py` | 9 |
| `tests/test_template_landmarks.py` | 2 |
| `tests/test_trailing_slash_routing.py` | 6 |
| `tests/test_ui_flows.py` | 17 |
| `tests/test_user_profile_routes.py` | 30 |
| `tests/test_utils_package.py` | 1 |
| `tests/test_version.py` | 22 |
| `tests/test_visual_capture_contracts.py` | 15 |
| `tests/test_visual_selector_contracts.py` | 5 |
| `tests/test_volume_ai.py` | 26 |
| `tests/test_volume_classifier.py` | 43 |
| `tests/test_volume_progress.py` | 31 |
| `tests/test_volume_splitter_api.py` | 12 |
| `tests/test_volume_taxonomy.py` | 8 |
| `tests/test_weekly_summary.py` | 4 |
| `tests/test_weekly_summary_golden.py` | 1 |
| `tests/test_weekly_summary_routes.py` | 30 |
| `tests/test_weekly_summary_unassigned.py` | 20 |
| `tests/test_workout_log_calibration_route.py` | 7 |
| `tests/test_workout_log_routes.py` | 58 |
| `tests/test_workout_log_utils.py` | 30 |
| `tests/test_workout_plan_routes.py` | 67 |
| `tests/test_youtube_video_id.py` | 40 |

## Hard waits by file

Flake-and-latency debt (blindspot B5). Phase 5 step 16 burns this down worst-file-first; this table is the tracker.

| File | Lines with `waitForTimeout` |
|---|---:|
| `e2e/accessibility.spec.ts` | 1 |
| `e2e/dark-mode.spec.ts` | 1 |
| `e2e/empty-states.spec.ts` | 9 |
| `e2e/error-handling.spec.ts` | 11 |
| `e2e/exercise-interactions.spec.ts` | 7 |
| `e2e/fatigue-stage4-smokes.spec.ts` | 1 |
| `e2e/learned-calibration.spec.ts` | 2 |
| `e2e/listener-cleanup.spec.ts` | 1 |
| `e2e/progression.spec.ts` | 7 |
| `e2e/summary-pages.spec.ts` | 2 |
| `e2e/superset-edge-cases.spec.ts` | 17 |
| `e2e/ui-hardening.spec.ts` | 1 |
| `e2e/validation-boundary.spec.ts` | 2 |
| `e2e/volume-splitter.spec.ts` | 23 |
| `e2e/workout-log.spec.ts` | 7 |
