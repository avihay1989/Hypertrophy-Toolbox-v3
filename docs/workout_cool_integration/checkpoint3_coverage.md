# free-exercise-db mapping coverage

`blank_floor = 60` (scores below this emit blank `suggested_fed_id` / `suggested_image_path`).

| Subset | Size | Matched | High ≥80 | Med 60–79 | Low 35–59 | Blank <35 |
|---|---:|---:|---:|---:|---:|---:|
| Whole catalogue | 1897 | 735 (38.7%) | 245 (12.9%) | 490 (25.8%) | 835 (44.0%) | 327 (17.2%) |
| Strength subset | 1506 | 721 (47.9%) | 242 (16.1%) | 479 (31.8%) | 702 (46.6%) | 83 (5.5%) |
| Usage top-200 | 1 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 1 (100.0%) |
| Starter plan (default args) | 17 | 13 (76.5%) | 6 (35.3%) | 7 (41.2%) | 4 (23.5%) | 0 (0.0%) |
| Common strength (usage + starter) | 18 | 13 (72.2%) | 6 (33.3%) | 7 (38.9%) | 4 (22.2%) | 1 (5.6%) |

## Subset definitions

- **Whole catalogue** — all rows in `exercises`
- **Strength subset** — excludes equipment in {Stretches, Yoga, Recovery, Cardio}
- **Usage top-200** — top by appearance count in `user_selection` + `workout_log`
- **Starter plan (default args)** — exercises chosen by `generate_starter_plan(persist=False)` with defaults (3 days, gym, novice, hypertrophy)
- **Common strength (usage + starter)** — PLANNING §4.7 candidate: top-N usage UNION default starter-plan exercises
