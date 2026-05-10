# Quality Gate

*Required gates per change type. Used by `/unslop` and `/verify-and-polish` to decide which tests and reviewers to run. This file is the canonical implemented version of the Tier 1 quality gate.*

## Change-type → gates table

| Change type | Path globs | Required gates | Required reviewers |
|---|---|---|---|
| Route / API | `routes/**`, `app.py` | route pytest target (`tests/test_<route>_routes.py` or `tests/test_<route>.py`) + blueprint-registration coverage in `tests/conftest.py` | `code-reviewer`; + `product-risk-reviewer` if response shape changes |
| DB / schema | `utils/db_initializer.py`, `utils/database.py`, `utils/program_backup.py`, `utils/auto_backup.py` | full `pytest` + manual backup/restore smoke | `code-reviewer` + `architecture-reviewer` |
| Business logic | `utils/**.py` (non-DB) | `pytest tests/test_<module>.py` | `code-reviewer`; + `product-risk-reviewer` if `effective_sets` / `weekly_summary` / `session_summary` / `progression` / `fatigue` touched |
| Frontend (template) | `templates/**` | matching Chromium specs from the feature map below | none required |
| Frontend (JS) | `static/js/**` | matching Chromium specs from the feature map below + manual smoke if interactive | none required |
| CSS | `scss/**` | `/build-css` + `e2e/visual.spec.ts` if visual surface changes | none required |
| E2E spec | `e2e/**` | run the spec; intentionally re-baseline if visual | none required |
| AI workflow / agent config | `.claude/**`, `CLAUDE.md`, `*/CLAUDE.md`, `docs/ai_workflow/**` | manual dry-run/self-review; run tests only if source behavior changed | `code-reviewer` or careful self-review |
| Product docs only | `docs/**`, `*.md` excluding AI workflow files above | none unless examples/scripts changed | none |

> All three Tier 2 reviewers — `architecture-reviewer`, `test-strategist`, `product-risk-reviewer` — are live. Run them at the plan stage via [`/council-plan`](../../.claude/commands/council-plan.md); the table above also names them as code-time reviewers when the relevant change types are touched.

## Diff collection (used by `/unslop`)

Collect all changed files before deriving tests:

```powershell
git diff --name-only HEAD
git diff --name-only --cached
git ls-files --others --exclude-standard
```

If a feature branch has an upstream or known base, also include `git diff --name-only <merge-base>...HEAD`. De-duplicate the final list. Do not rely on plain `git diff --name-only`; it misses untracked Tier 1-style artifacts.

## Targeted-test derivation

For each changed file:

- `routes/X.py` → try `tests/test_X_routes.py`, then `tests/test_X.py`, plus any tests found by `rg "routes\.X|X_bp|/route_name" tests`
- `utils/X.py` → try `tests/test_X.py`, plus any tests found by `rg "utils\.X|from utils.X import" tests`
- `templates/X.html` or `static/js/**/X*` → normalize underscores to hyphens and use the feature map below
- `app.py`, `tests/conftest.py`, `.claude/**`, root configs → fall back to `/verify-suite` (cross-cutting)

Run the union. If the union is empty, run `/verify-suite`.

## Frontend feature → E2E map

| Template / JS hint | Primary E2E specs |
|---|---|
| `welcome`, `base`, `navbar`, `darkMode` | `smoke-navigation.spec.ts`, `nav-dropdown.spec.ts`, `dark-mode.spec.ts` |
| `workout_plan`, `workout-plan`, `filters`, `exercises`, `routine-cascade` | `workout-plan.spec.ts`, `exercise-interactions.spec.ts`, `superset-edge-cases.spec.ts` |
| `workout_log`, `workout-log` | `workout-log.spec.ts` |
| `weekly_summary`, `session_summary`, `summary`, `charts` | `summary-pages.spec.ts` |
| `progression_plan`, `progression-plan` | `progression.spec.ts` |
| `volume_splitter`, `volume-splitter`, `plan_volume_panel` | `volume-splitter.spec.ts`, `volume-progress.spec.ts` |
| `user_profile`, `user-profile`, `bodymap`, `muscle-selector` | `user-profile.spec.ts` |
| `backup`, `program-backup`, `backup-center` | `program-backup.spec.ts` |
| validation, error, empty state, accessibility changes | `validation-boundary.spec.ts`, `error-handling.spec.ts`, `empty-states.spec.ts`, `accessibility.spec.ts` |
| API wrapper / endpoint-shape changes | `api-integration.spec.ts` |
| broad layout or CSS visual changes | `visual.spec.ts` |

## Two gates, two purposes

- **`/unslop`** — routine post-implementation polish. Targeted tests + `code-reviewer` + `unslop-reviewer`.
- **`/verify-and-polish`** — full gate before milestones / refactors / schema changes. `/verify-suite` (full pytest + Chromium E2E) + `code-reviewer` + `unslop-reviewer`.

Both end with `/handover` to record what shipped.

## Known exceptions to treat as pre-existing

Current full-suite baseline (2026-05-10):
- `e2e/nav-dropdown.spec.ts:117` — dark-mode toggle off-viewport at 1440 width; current known red.
- `e2e/program-backup.spec.ts:79` — historical DB-state-pollution flake; passed in the 2026-05-10 full run and passes in isolation.

If the nav-dropdown failure is the only red, do not block unrelated work on it; note it in the handover entry. Treat any reappearance of the program-backup flake as known but record whether it passes in isolation.
