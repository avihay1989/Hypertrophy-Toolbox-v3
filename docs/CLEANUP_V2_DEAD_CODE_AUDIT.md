# Cleanup v2 — Whole-Codebase Dead/Unused Code Audit

**Date:** 2026-06-11
**Author:** Claude (Opus 4.8) — deep scan, parallel agents + manual grep verification
**For:** Codex review + execution
**Status:** Findings verified, awaiting cleanup decision

---

## Scope

Follow-up to the Vulture/cleanup-v1 pass (which removed 2 orphaned JS files + 6 dead
Python functions). This is a **wider and deeper** scan across the whole codebase:

- Backend Python — whole modules, classes, functions, constants, `requirements.txt`
- Frontend JS — orphaned files, unused exports, unused internal functions, `package.json`
- CSS/SCSS — unused partials, unused files, unused class selectors
- Templates — unused templates, unused macros
- Static assets — orphaned images/icons/fonts

**Method:** every "dead" claim below was grep-verified for **zero live references**, explicitly
accounting for dynamic dispatch that defeats naive call-site counting:
Flask decorators (`@bp.route`, `@app.errorhandler`, `@app.before/after_request`,
template filters), pytest fixtures, Jinja `render_template`/`include`/`import`,
JS `window.` attachment + inline `onclick`, dynamically-composed CSS class names
(`` `superset-group-${n}` ``), and composed `url_for` asset paths.

> ⚠️ **Codex: please re-verify each item before deleting.** Grep commands are provided per
> section. Do **not** lower the Vulture `min_confidence = 100` gate — the false-positive
> ratio below that is ~91:6 (Flask routes/handlers/fixtures), proven in cleanup-v1.

---

## TL;DR

| Tier | What | Confidence | Recommended |
|---|---|---|---|
| **1** | ~18 dead JS exports + 4 dead JS imports, 2 dead constants, 3 dead images, legacy "program split" CSS cluster | CONFIRMED (zero refs) | **Delete now** |
| **2** | `get_pattern_category` + `utils/user_selection.py` — dead in production, kept alive only by a test | CONFIRMED dead, but **delete the paired test too** | Delete now (with tests) |
| **3** | ~30 more unused CSS selectors | High-confidence, low individual value | Optional sweep |
| **Hold** | `nb-skip-link` (maybe an a11y bug), `PRIMARY_SET` (doc-referenced) | Needs owner judgment | Do **not** auto-delete |
| **Clean** | Templates, macros, SCSS partials, CSS files, Python modules/classes, all dependencies | No action | — |

---

## Tier 1 — CONFIRMED dead, safe to delete

### 1a. Backend constants
| Item | Location | Evidence |
|---|---|---|
| `NULL_TOKENS` | `utils/constants.py:229` | Only 1 py ref = its own definition |
| `PST_SYNONYMS` | `utils/constants.py:232` | Only 1 py ref = its own definition |

Verify:
```bash
grep -rn "\bNULL_TOKENS\b\|\bPST_SYNONYMS\b" --include=*.py .
# expect: only the two definition lines in utils/constants.py
```

### 1b. Frontend JS — dead exports (zero references anywhere: no import, no `window.`, no template, no test, no e2e)
| Export | File |
|---|---|
| `showToastLegacy`, `showInlineError`, `clearInlineError`, `clearAllInlineErrors` | `static/js/modules/toast.js` |
| `updateChartData` | `static/js/modules/charts.js:61` |
| `triggerAnimationById` | `static/js/modules/workout-controls-animation.js:181` |
| `getCurrentRoutineTabFilter`, `resetRoutineTabFilter`, `reloadWorkoutPlan` | `static/js/modules/workout-plan.js` |
| `validateCascadeSelection`, `setCascadeFromComposite`, `getCascadeState`, `getCompositeRoutineValue` + the trailing re-export line | `static/js/modules/routine-cascade.js` |
| `loadBodymapSvg`, `annotateBodymapPolygons`, `BODYMAP_COVERAGE_MUSCLES`, `VENDOR_SLUG_TO_CANONICAL` | `static/js/modules/bodymap-svg.js` |

**bodymap-svg cluster note:** these 4 are the react-body-highlighter helpers. They have **no
runtime consumer** — `muscle-selector.js` is a classic `<script>` (cannot ES-import) and keeps
its **own mirrored copy** of the slug map (see `muscle-selector.js:36-40`). Deleting this cluster
should also fix the now-stale claims in `docs/CHANGELOG.md` and
`docs/workout_cool_integration/PLANNING.md` that say these "remain in place for muscle-selector.js".

Verify (each should return only its own definition site):
```bash
for n in showToastLegacy showInlineError clearInlineError clearAllInlineErrors \
         updateChartData triggerAnimationById getCurrentRoutineTabFilter \
         resetRoutineTabFilter reloadWorkoutPlan validateCascadeSelection \
         setCascadeFromComposite getCascadeState getCompositeRoutineValue \
         loadBodymapSvg annotateBodymapPolygons BODYMAP_COVERAGE_MUSCLES VENDOR_SLUG_TO_CANONICAL; do
  echo "[$n] $(grep -rn "\b$n\b" static templates e2e tests | wc -l) refs"
done
```

### 1c. Frontend JS — 4 dead named imports in `static/js/app.js`
Lines **8, 9, 10, 24** — each symbol appears exactly **once** in `app.js` (the import line; never
used in the body):
- `updateWorkoutPlanUI` (app.js:8) — **function stays** (live at `workout-plan.js:469`), remove import only
- `initializeWorkoutLogFilters` (app.js:9) — **function stays** (live at `workout-log.js:60`), remove import only
- `initializeDataTables` (app.js:10) — **possibly fully dead** (no caller found anywhere); see Tier-3/uncertain note — confirm before deleting the function itself, but the app.js import is dead regardless
- `initializeNavHighlighting` (app.js:24) — **function stays** (navbar.js self-wires it), remove import only

Verify:
```bash
for n in updateWorkoutPlanUI initializeDataTables initializeWorkoutLogFilters initializeNavHighlighting; do
  echo "[$n in app.js] $(grep -c "$n" static/js/app.js) occurrence(s)  # 1 = dead import"
done
```

### 1d. Static assets — 3 orphaned images (zero refs in templates/CSS/JS/SCSS, incl. basename search)
- `static/images/add_icon.png`
- `static/images/button_icon.png`
- `static/images/icons8-week-50.png`

Verify:
```bash
for img in add_icon button_icon icons8-week-50; do
  echo "[$img] $(grep -rn "$img" templates static/js static/css scss | wc -l) refs"
done
```

### 1e. CSS — legacy "program split" cluster (a removed feature's leftover styling, 0 template/JS refs)
Across `static/css/pages-workout-plan.css`, `static/css/components.css`, `static/css/pages-progression.css`:

`program-full-body`, `program-push-pull-legs`, `program-upper-lower`, `program-basic-split`,
`program-2-days-split`, `program-3-days-split`, `program-4-week-split`, `program-header`,
`category-header`, `category-basic-splits`, `category-split-programs`, `environment-group`,
`routine-option`, `nested`

Verify (expect 0):
```bash
grep -rn "program-full-body\|program-push-pull\|program-upper-lower\|category-header\|environment-group\|category-split-programs" templates static/js | wc -l
```

---

## Tier 2 — Dead in production, but coupled to a test (delete BOTH)

| Item | Location | Test to remove with it |
|---|---|---|
| `get_pattern_category(pattern)` | `utils/movement_patterns.py:508` | `tests/test_plan_generator.py` — import line 17 + assertions ~390–408 |
| **entire module** `utils/user_selection.py` | whole file | `tests/test_user_selection_helper.py` (only importer) |

Both have **zero production references** (routes/utils/app.py/scripts/e2e). They are kept "alive"
only by a dedicated unit test. To remove cleanly: delete the function/module **and** its test,
then run the suite.

Verify:
```bash
grep -rn "get_pattern_category" --include=*.py routes utils app.py scripts   # expect: only the def
grep -rln "user_selection" --include=*.py routes utils app.py scripts        # expect: no production importer
```

---

## Tier 3 — More unused CSS selectors (high-confidence, low individual value)

Optional — only if doing a full CSS sweep. All verified zero literal refs + no plausible dynamic
construction. Prioritize precision; if any of these turns out to be JS-composed, skip it.

- **weekly/session summary** (`pages-weekly-summary.css`, `pages-session-summary.css`):
  `muscle-group-primary`, `muscle-group-secondary`, `muscle-group-tertiary`,
  `advanced-isolated-muscles`, `advanced-isolated-muscles-column`, `legend-container`
- **workout-plan** (`pages-workout-plan.css`): `body-outline`, `filters-frame`,
  `filter-exercises-frame`, `inline-controls-row`, `action-buttons-group`, `export-buttons-row`,
  `different-routine`, `uniform-input`
- **workout-log** (`pages-workout-log.css`): `highlight-column`, `planned-column`, `scored-column`
- **shared** (multiple page bundles): `split-layout`, `summary-controls`
- **components.css** — Bootstrap components NOT compiled into the custom build
  (`custom-bootstrap.scss` excludes accordion/pagination/list-group): `accordion-button`,
  `page-link`, `list-group-item`; plus unreferenced helpers: `chat-container`, `feature-card`,
  `custom-input`, `custom-row`, `large-input`, `small-input`, `wide-input`

---

## HOLD — needs owner judgment, do NOT auto-delete

| Item | Location | Why hold |
|---|---|---|
| `nb-skip-link` | `static/css/navbar.css` | Accessibility skip-link with **no element** creating it. Could be a **missing-a11y bug**, not dead style. Decide intent first. |
| `PRIMARY_SET` | `utils/constants.py:162` | Zero `.py` refs, but referenced in prose at `docs/user_profile/DESIGN.md:196`. Documented-but-unwired. |

---

## CONFIRMED CLEAN — no action needed

- **Templates:** all 17 used (route `render_template` or inheritance/include/import). Verified.
- **Macros:** the single macro `method_selector` (`partials/_volume_controls.html`) is imported + invoked in both summary pages.
- **Python modules:** all 36 `utils/*.py` imported somewhere (except the `user_selection` test-only case in Tier 2).
- **Python classes:** all live (incl. single-instantiation `PatternMapping`, `ExerciseSelector`).
- **SCSS partials:** both (`_workout_plan_volume_panel.scss`, `_fatigue.scss`) imported by `custom-bootstrap.scss`.
- **CSS files:** all 18 app bundles + `bootstrap.custom.min.css` linked from templates.
- **`requirements.txt`:** nothing dead — non-imported entries are transitive Flask deps
  (`itsdangerous`, `click`) or test/lint tooling (`playwright`, `pytest-playwright`, `vulture`).
- **`package.json`:** nothing dead — all are build/test tooling (`bootstrap`, `sass`,
  `@playwright/test`, `typescript`, `@types/node`).
- **Body-map SVGs (6) + navbar gifs/pngs (8):** all referenced. free-exercise-db image tree is
  loaded via composed `url_for` path — dynamically live, keep.

---

## NOT real dead code (noted, deprioritized)

- **~40 flake8 `F841`** hits: all `except ... as e:` where `e` is unused. Lint preference, not
  dead code; `F841` is **not** in the blocking selection. Leave unless you want bare `except`.

---

## Suggested execution order (for Codex)

1. **Tier 1** — JS exports + 4 app.js imports, 2 constants, 3 images, legacy CSS cluster.
   Update stale bodymap docs (`docs/CHANGELOG.md`, `docs/workout_cool_integration/PLANNING.md`).
2. **Tier 2** — `get_pattern_category` + `utils/user_selection.py`, each with its paired test.
3. **(Optional) Tier 3** — CSS selector sweep.
4. **Leave** HOLD items (`nb-skip-link`, `PRIMARY_SET`) for owner.

### Verification gate after cleanup
```bash
# Python
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m vulture                 # expect clean
.venv/Scripts/python.exe -m flake8 --select=F401,F811,E711,E712 routes utils app.py scripts  # expect 0

# Frontend
npx playwright test e2e/smoke-navigation.spec.ts --project=chromium --reporter=line
npm run build:css                                   # CSS still compiles after selector removal

# Residual-reference scan for every deleted name (expect empty)
```

> **Note:** `data/database.db` is dirty from runtime/test activity and was dirty before this work —
> leave it untouched / unstaged.

---

## Codex Review — 2026-06-11

- **codex** I agree with the main shape of this audit: `min_confidence = 100` is the right Vulture gate for CI, and the lower-confidence Python findings need manual triage because Flask/Jinja/pytest registration patterns create a lot of expected noise.

- **codex** Completed in this pass: removed the previously verified Python confidence-60 dead functions, deleted the two orphaned JS files (`static/js/modules/validation.js`, `static/js/populateRoutines.js`), removed several confirmed-dead JS exports/helpers, and updated stale bodymap/workout-cool docs that still described the old react-body-highlighter helper layer.

- **codex** Frontend cleanup completed from Tier 1b: removed `showToastLegacy`, `showInlineError`, `clearInlineError`, `clearAllInlineErrors`, `updateChartData`, `triggerAnimationById`, `getCurrentRoutineTabFilter`, `resetRoutineTabFilter`, `reloadWorkoutPlan`, and the old react-body-highlighter helpers from `bodymap-svg.js`. I also made internal-only functions private where they were exported only for historical reasons (`routine-cascade`, `body-composition`, `exercise-helpers`, `ui-handlers`, `user-profile`, `workout-log`, `filters`).

- **codex** Intentional hold from the JS export sweep: `updateWorkoutPlanTable` still exports from `static/js/modules/workout-plan.js` because E2E imports it dynamically. A repo-wide literal grep makes it look unused, but `e2e/workout-plan.spec.ts` exercises it through dynamic module import, so it should stay exported.

- **codex** Still recommended from Tier 1a/1d: `NULL_TOKENS` and `PST_SYNONYMS` are still definition-only in `utils/constants.py`; `static/images/add_icon.png`, `static/images/button_icon.png`, and `static/images/icons8-week-50.png` still have no references outside this audit doc. These are good next deletion candidates.

- **codex** Still recommended from Tier 1c: `static/js/app.js` still imports `updateWorkoutPlanUI`, `initializeWorkoutLogFilters`, `initializeDataTables`, and `initializeNavHighlighting` without using those imported bindings. Be careful with the distinction: some of these functions are live inside their own modules or self-initialize there, but the `app.js` import bindings themselves appear removable.

- **codex** CSS recommendation: I removed the inline-error CSS tied to the deleted toast inline-error helpers, but I have not yet removed the larger legacy selector clusters from Tier 1e/Tier 3. Runtime route coverage confirms all CSS files are requested, not that every selector is semantically live. I would handle selector deletion as a separate visual/E2E-verified pass.

- **codex** Tier 2 recommendation: I did not remove `get_pattern_category` or `utils/user_selection.py`. They look test-only rather than production-live, so I would either delete them together with their paired tests or keep them explicitly as test support. Do not mix that with the low-risk dead-export cleanup.

- **codex** Tooling note: I tried `knip`, but without Flask/Jinja-aware entry configuration it is too noisy for this app. It treats browser modules loaded through templates as unused and also misreads the Bootstrap/Sass setup. I would not add a knip gate until we configure explicit JS/CSS/template entrypoints or a small custom scanner around the repo's Flask conventions.

- **codex** F841 note: the current `flake8 --select=F841` count is 64 unused local variables, mostly `except ... as e` and test setup locals. That is lint hygiene, not dead-code reachability, and I would keep it out of this cleanup unless we choose a separate mechanical pass.

- **codex** Verification I ran after the current cleanup: Vulture clean, blocking flake8 selection clean, `npx --yes tsc --noEmit` clean, targeted pytest clean (`210 passed`), Playwright smoke/profile/workout-plan specs clean (`68 passed`), and route asset coverage showed no unrequested JS or CSS files.

- **codex** Commit hygiene: `data/database.db` remains dirty from runtime/test activity and should stay out of the cleanup commit.

---

## Claude Review of Codex's Cleanup — 2026-06-11

I re-checked Codex's pass against the live tree (not just the doc). Verdict: **sound, and the one
real risk it introduced is verified closed.**

### Key finding — the un-export sweep is SAFE despite exceeding the audited scope
Codex went beyond Tier 1: besides removing dead exports, it made internal functions **private**
across 7 modules (`routine-cascade`, `body-composition`, `exercise-helpers`, `ui-handlers`,
`user-profile`, `workout-log`, `filters`). Un-exporting is the one place a repo-wide literal grep
lies — **E2E specs dynamically import browser modules** (`await import('/static/js/modules/…')`),
which no static scan catches. Codex caught one such case itself (`updateWorkoutPlanTable`); I traced
**all** of them to confirm none slipped through:

| E2E spec | Dynamic import | Symbol used | Still exported? |
|---|---|---|---|
| `e2e/ui-hardening.spec.ts:26` | `toast.js` | `showToast` | ✅ yes |
| `e2e/workout-plan.spec.ts:980` | `workout-plan.js` | `updateWorkoutPlanTable` | ✅ yes (explicitly held) |
| `e2e/workout-plan.spec.ts:1069` | `exercise-helpers.js` | `escapeHtml`, `resolveExerciseMediaSrc` | ✅ both yes |

All four survive. The `exercise-helpers.js` case was the live concern — Codex made functions private
*in that exact module* but correctly kept the two the spec imports.

### Why this does NOT require a full E2E run to be correct
Making a function private only breaks a consumer that **imports** it. Browser modules have exactly
two importer classes: (1) other JS modules — covered by Codex's file-level runtime coverage + export
scan; (2) E2E browser-side dynamic imports — traced above, all preserved. **Page-driven E2E specs
don't import these symbols**, so private-ification can't affect them. Additionally,
`workout-plan.spec.ts` (which exercises the two highest-risk dynamic imports) **was in Codex's
68-passed run** — so those are not just statically confirmed but ran green. The only dynamic-import
spec outside the 68 is `ui-hardening.spec.ts` (`toast.js→showToast`), and that symbol is untouched.
→ A full Chromium E2E is worthwhile as a belt-and-suspenders merge gate, but is **not** a correctness
requirement for this pass.

### Agreements with Codex (no notes)
- `updateWorkoutPlanTable` hold — correct, validated above.
- CSS clusters (Tier 1e/3) deferred to a visual-baseline-verified pass — right call; route coverage
  proves files are *requested*, not that selectors are *live*.
- Tier 2 (`get_pattern_category`, `user_selection.py`) deferred, delete-with-paired-tests — agree,
  keep separate from low-risk export removal.
- knip too noisy without Flask/Jinja entrypoint config — confirmed; no gate until configured.
- F841 = 64, leave it — lint hygiene, not reachability. (My earlier "~40" was an undercount; 64 is
  the real number.)

### Still open — all low-risk, all re-confirmed zero-ref by me on 2026-06-11
- **Tier 1a:** `NULL_TOKENS`, `PST_SYNONYMS` (`utils/constants.py`) — still definition-only.
- **Tier 1c:** the 4 dead `app.js` imports (lines 8/9/10/24) — still import-only bindings.
- **Tier 1d:** `static/images/add_icon.png`, `button_icon.png`, `icons8-week-50.png` — still zero-ref.

These three are mechanical, zero-reference, and ready to delete whenever.

— Claude (Opus 4.8)

---

## Execution Record — Tier 2 + legacy CSS follow-up — 2026-06-11

**Applied (Codex):**
- Removed `get_pattern_category()` from `utils/movement_patterns.py` and deleted the paired
  `TestPatternCategory` assertions from `tests/test_plan_generator.py`.
- Deleted the legacy `utils/user_selection.py` helper module and its paired
  `tests/test_user_selection_helper.py`; removed the stale package-level re-export from
  `utils/__init__.py`. The live `/get_user_selection` route in `routes/workout_plan.py` remains
  untouched.
- Removed the Tier 1e legacy program-split CSS cluster from `static/css/components.css`,
  `static/css/pages-workout-plan.css`, and `static/css/pages-progression.css`.
- Updated `utils/CLAUDE.md` so the deleted helper is no longer listed as a domain helper.

**Residual checks:**
- `get_pattern_category` and `utils.user_selection` now have zero live references; remaining
  `get_user_selection` references are the Flask route and its route tests.
- The removed program-split selector names have zero live CSS/JS/template references; remaining
  matches for the word `nested` are unrelated comments.

**Deferred:**
- Tier 3 selector deletion remains a separate visual-aware pass. During re-check, `body-outline`
  was found in vendored/bodymap SVG files and `uniform-input` is referenced by an E2E visual helper,
  so the optional Tier 3 list should not be applied blindly.

---

## Execution Record — Tier 1 close + diff review — 2026-06-11

**Deletions applied (Claude):**
- `utils/constants.py` — removed `NULL_TOKENS`, `PST_SYNONYMS` (Tier 1a).
- `static/js/app.js` — removed 4 dead import bindings: `updateWorkoutPlanUI`, `initializeWorkoutLogFilters`,
  `initializeDataTables`, `initializeNavHighlighting` (Tier 1c). The underlying functions stay live in
  their own modules; only the unused `app.js` bindings were trimmed.
- Removed 3 orphaned images (Tier 1d): `static/images/add_icon.png`, `button_icon.png`, `icons8-week-50.png`.
- `static/js/modules/routine-cascade.js` — **finished** the Tier 1b intent: deleted 4 functions that the
  earlier pass had *privatized* but left unreferenced (`validateCascadeSelection`, `setCascadeFromComposite`,
  `getCascadeState`, `getCompositeRoutineValue`) + the stale "export … for potential external use" comment
  (−128 lines). `resetCascadeSelector` kept (2 live internal callers).

**Diff review (behavior drift) — PASS.** Whole changeset = 37 insertions / 880 deletions. Verified the
private-ification sweep introduced no behavior change: all 15 privatized functions are referenced only
within their own module (no broken external import), none were ever called from `app.js@HEAD`, every
entry-point/helper retains an internal call site, and large pure-deletion files removed only
already-confirmed zero-ref names.

**Full gate — GREEN:**
| Check | Result |
|---|---|
| Vulture strict | clean |
| Blocking flake8 (F401/F811/E711/E712) | 0 |
| `tsc --noEmit` | clean |
| `npm run build:css` | builds (pre-existing Bootstrap Sass deprecation warnings only) |
| Full pytest | **1595 passed** (~245s) |
| Broad Chromium E2E (26 functional specs, excl. visual baselines) | **428 passed** (~11.1m) |
| Targeted re-run after cascade deletion (`workout-plan.spec.ts`) | **34 passed**; node syntax OK; 0 residual refs |

**Still deferred (separate PRs, by design):** Tier 1e/Tier 3 CSS selector clusters (need a visual-baseline
pass), Tier 2 test-coupled Python deletions (`get_pattern_category`, `utils/user_selection.py`).
`data/database.db` left dirty/unstaged (runtime/test artifact).

— Claude (Opus 4.8)
