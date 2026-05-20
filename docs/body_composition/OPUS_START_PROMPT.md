# Opus Start Prompt — Body Composition Issue #21

Use this prompt when starting the Body Composition workstream with Opus.

```text
We are in d:\development\Hypertrophy-Toolbox-v3-main.

Read these first:
- CLAUDE.md
- docs/MASTER_HANDOVER.md
- docs/ACTIVE_DEVELOPMENT.md
- docs/body_composition/development_issues.md
- .claude/rules/database.md, .claude/rules/routes.md, .claude/rules/frontend.md, .claude/rules/testing.md as they become relevant

Current decision:
- Start Body Composition Issue #21 as the next product workstream.
- Do not re-evaluate the whole docs folder for what to do next; the owner-approved queue is recorded in docs/ACTIVE_DEVELOPMENT.md.
- Fatigue Phase 1 is closed. Do not edit utils/fatigue.py, tests/test_fatigue.py, or scripts/fatigue_calibration_report.py.
- Profile-page display hooks are deferred until /body_composition ships.
- YouTube curation is optional content work, not this task.
- Do not delete or move the visual-baseline or calm-glass worktrees.

Goal:
Implement the first conservative slice of Body Composition Issue #21:
1. Add pure formula/business logic in utils/body_fat.py:
   - compute_navy(...)
   - compute_bmi(...)
   - ace_category(bfp, gender)
   - jackson_pollock_ideal(age, gender)
   Include the "must match JS mirror" comment from the issue spec.
2. Add focused pytest coverage in tests/test_body_fat.py:
   - Navy male + female cases
   - log-domain rejection
   - BMI adult male/female + boy/girl
   - ACE boundary rows
   - Jackson & Pollock interpolation and age clamp
3. Add the idempotent DB migration add_body_composition_snapshots_table() in utils/database.py:
   - body_composition_snapshots table exactly per docs/body_composition/development_issues.md
   - captured_at descending index
   - DatabaseHandler pattern only
4. Register the migration in app.py startup sequence near add_user_profile_tables().
5. Add or extend migration tests, preferably tests/test_db_migration.py if that is the local pattern.

Out of scope for this first slice:
- Do not build the template, navbar link, JS, chart, or Playwright spec yet unless the first slice is fully green and you explicitly choose to continue.
- Do not integrate values back into /user_profile.
- Do not alter existing estimator outputs.

Verification:
- Run targeted pytest for new formula tests and migration tests.
- If changes touch shared startup/migration behavior, run a broader relevant pytest subset.
- Update docs/ACTIVE_DEVELOPMENT.md and docs/MASTER_HANDOVER.md with what changed and the exact tests run before handing back.
- Leave data/database.db uncommitted/ignored as runtime dirt.

Please implement, not just plan. Keep edits tightly scoped and follow existing repo patterns.
```
