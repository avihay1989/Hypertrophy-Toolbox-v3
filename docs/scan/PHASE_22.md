# Phase 22 — E2E specs + scripts + CI config

Scope read in full: all 28 `e2e/*.spec.ts` (11,604 lines), `e2e/fixtures.ts`,
`e2e/strict-fixtures.ts`, `e2e/visual-helpers.ts`, `e2e/app-modules.d.ts`,
`e2e/CLAUDE.md`, `playwright.config.ts`, `e2e/scripts/*.py` (4 files), all 17
`scripts/*.py`, `.github/workflows/ci.yml`, `.github/workflows/deep-gate.yml`,
`package.json`, `pyrightconfig.json`, `.claude/rules/debugging.md`, and the
relevant sections of `docs/REFACTOR_PLAN.md` (WP0.4, Phase 4, response matrix
items #10 and #12).

---

## 1. E2E coverage map (spec → page/feature)

| Spec | Lines | Page/feature covered | Fixture style |
|---|---|---|---|
| `smoke-navigation.spec.ts` | 187 | All top-level nav links, welcome page, full nav cycle | `fixtures.ts` |
| `dark-mode.spec.ts` | 153 | Theme toggle, localStorage persistence, icon swap, cross-page persistence | `fixtures.ts` |
| `nav-dropdown.spec.ts` | 172 | P5 navbar: dropdown order, Analyze dropdown, static FA icon colors/hover, mobile navbar, Backup link | `strict-fixtures.ts` |
| `workout-plan.spec.ts` | 1036 | Routine cascade, add exercise, filters, export, muscle-mode toggle, Workout Controls math/estimate trace, MuscleMap body-map modal, YouTube video modal, §4 thumbnail rendering (mocked JS-module calls) | `fixtures.ts` |
| `workout-log.spec.ts` | 562 | Table structure, import-from-plan, inline edit (weight/reps/notes), clear modal, date inputs, mobile, YouTube video modal | `fixtures.ts` |
| `exercise-interactions.spec.ts` | 593 | Delete/replace/superset/inline-edit/details-modal/filter/tab-nav per-row actions | `fixtures.ts` |
| `superset-edge-cases.spec.ts` | 551 | Link >2/<2, delete-in-superset, unlink, replace-in-superset, persistence, visual indicator | `fixtures.ts` |
| `replace-exercise-errors.spec.ts` | 228 | Toast messaging for `no_candidates`/`duplicate`/`missing_metadata` (mocked route) | `fixtures.ts` |
| `summary-pages.spec.ts` | 397 | Weekly + Session summary structure, contribution-mode selector contract, legend swatch colors, pattern-coverage API + render | `fixtures.ts` |
| `progression.spec.ts` | 729 | Page structure, goal CRUD lifecycle (real save/complete/delete), methodology text, status indicators, double-progression API, mobile, Phase 2D-B fatigue-context advisory | `fixtures.ts` |
| `volume-splitter.spec.ts` | 512 | Sliders, mode toggle, calculate/reset, export, save/load/delete via volume-history, mobile | `fixtures.ts` |
| `volume-progress.spec.ts` | 505 | `/workout_plan` volume-progress drawer: add/replace/clear/starter-plan refresh, deactivate/delete degrade paths, bonus-from-compounds bucket, viewport×theme layout-geometry matrix | `fixtures.ts` |
| `program-backup.spec.ts` | 407 | Dedicated Backup Center page: create/list/search/sort/restore/delete/rename, inline confirm panel, save-first snapshot, API integration | `fixtures.ts` |
| `user-profile.spec.ts` | 918 | Onboarding banner, section collapse, demographics/lifts/preferences autosave, reference-lift layout (anterior/posterior split, Issue #24), MuscleMap coverage-map states, "How the system sees you" insights card, Body Composition snapshot surfacing | `fixtures.ts` |
| `body-composition.spec.ts` | 127 | `/body_composition` form, ACE band rendering, save/delete snapshot flow, BMI fallback, **JS↔Python BFP parity** (see §5 below) | `fixtures.ts` |
| `fatigue.spec.ts` | 108 | `/fatigue` dedicated page: SFR cards, period selector, empty state, dark-mode parity, 375px overflow, badge round-trip nav | `fixtures.ts` |
| `fatigue-context.spec.ts` | 327 | Advisory fatigue-context toggle (Profile) + Workout Controls chip/advisory/manual-nudge (2D-A/2D-C), all via mocked `/api/user_profile/estimate` | `fixtures.ts` |
| `fatigue-stage4-smokes.spec.ts` | 163 | Stage-4 owner smokes: 375px badge overflow + tap-target, dark-mode contrast capture (writes metrics JSON, one-shot/measurement spec) | `fixtures.ts` |
| `learned-calibration.spec.ts` | 611 | Profile calibration toggle + promote-to-reference-lift, Workout Controls learned/related badges, Apply/Keep/Reset/Ignore actions (mocked), golden-path end-to-end auto-calibration (real backend) | `fixtures.ts` |
| `accessibility.spec.ts` | 522 | Keyboard nav, ARIA landmarks/labels, focus management/trap, skip links, contrast (loose), touch targets, screen-reader live regions | `fixtures.ts` |
| `api-integration.spec.ts` | 924 | Direct API contract tests across Plan/Log/Export/Progression/Volume/Summary/Filters/Error/CORS — **zero DOM selectors**, pure JSON assertions | raw `@playwright/test` (no shared fixture) |
| `empty-states.spec.ts` | 443 | Empty plan/log/filters/summary/progression/volume-splitter states | `fixtures.ts` |
| `error-handling.spec.ts` | 406 | Mocked 500/503/malformed-JSON/network-abort/timeout, double-click debounce, retry/recovery | `fixtures.ts` |
| `validation-boundary.spec.ts` | 491 | Negative/zero/RIR-RPE/decimal/empty/extreme value form submission | `fixtures.ts` |
| `browser-navigation-state.spec.ts` | 81 | Stateless routine-cascade contract: back-nav, refresh, deep-link query ignored | `fixtures.ts` |
| `ui-hardening.spec.ts` | 264 | Toast stacking/last-wins/class-clearing, Workout-Controls form-state persistence (reload/cascade/tab-visibility), modal keyboard/focus/ARIA | `fixtures.ts` |
| `visual.spec.ts` | 56 | Full-page screenshot matrix: 8 pages × 3 viewports × 2 themes = 48 shots | `strict-fixtures.ts` + `visual-helpers.ts` |
| `visual-baseline-thumbnails.spec.ts` | 131 | §4 thumbnail screenshot matrix: workout_plan (3 viewport × 2 theme × 2 mode = 12) + workout_log (3×2=6), plus behavioral src/theme assertions | raw `@playwright/test` + `visual-helpers.ts` |

**Not covered by any spec** (grepped, no hits): `/erase-data` UI flow (only used as a fatigue-page reset helper inside `fatigue.spec.ts`), CSV-import/export edge content validation, multi-tab/concurrent-session behavior.

---

## 2. CI job / required-context inventory

### `ci.yml` (runs on `push`/`pull_request` to `main`/`develop`)
| Job (name) | Required check? | What it runs |
|---|---|---|
| `security-audit` (Security Audit) | required (branch-protected, per memory) | `pip-audit` |
| `lint` (Code Linting) | required | flake8 blocking set (`E9,F63,F7,F82,F811,E711,E712,F401`) + measure-only F841 |
| `frontend-build` (Frontend Build) | required, gates the E2E jobs via `needs:` | `npm ci` + `npm run build:css` |
| `e2e-smoke` (E2E Smoke (Chromium)) | separate from functional gate | `smoke-navigation.spec.ts` only |
| `e2e-functional-shard` (E2E Functional Shard i/2) | **NOT** required (per-shard) | 24 named specs, `--shard=i/2`, matrix `[1,2]`, `fail-fast:false` |
| `e2e-functional` (E2E Functional (Chromium)) | **the** required check — exact name is load-bearing | fan-in gate; green iff both shards succeeded |
| `e2e-backup` (E2E Backup (Chromium, isolated)) | required (own job) | `program-backup.spec.ts` only, isolated server+DB |
| `test` (Run Tests) | required | `pytest tests/ -v --tb=short` |
| `typecheck` (Type Check (tsc blocking + pyright measure-only)) | required — exact name is load-bearing | `pyright` baseline-diff (blocking net-new only) + `tsc --noEmit` (blocking, e2e specs + `playwright.config.ts` scope only — **app JS under `static/js/modules/*` is NOT type-checked**) |

**Specs in `e2e-functional-shard`'s literal list (24):** `accessibility`, `api-integration`, `body-composition`, `browser-navigation-state`, `dark-mode`, `empty-states`, `error-handling`, `exercise-interactions`, `fatigue-stage4-smokes`, `fatigue`, `learned-calibration`, `nav-dropdown`, `progression`, `replace-exercise-errors`, `smoke-navigation`, `summary-pages`, `superset-edge-cases`, `ui-hardening`, `user-profile`, `validation-boundary`, `volume-progress`, `volume-splitter`, `workout-log`, `workout-plan`.

**[NEW] `fatigue-context.spec.ts` is absent from `e2e-functional-shard`'s literal spec list, and absent from `e2e/CLAUDE.md`'s CI-inclusion-contract table.** It exists (327 lines, mocked-backend Phase 2D-A coverage), is well-written, but is only exercised by the manual `deep-gate.yml` `full-e2e` job (which globs `ls e2e/*.spec.ts | grep -vE 'visual'` — that *does* pick it up). So it runs on every manual deep-gate dispatch but **never on a required PR check**. This is either an oversight in the ci.yml literal list (most other named specs from that era were added) or an intentional omission that isn't documented anywhere. Flag for owner: either add it to the shard list or note the exclusion in `e2e/CLAUDE.md`'s contract table like the other three deliberate exclusions (`program-backup`, `visual`, `visual-baseline-thumbnails`).

### `deep-gate.yml` (manual `workflow_dispatch` only)
| Job | Required? | What it runs |
|---|---|---|
| `full-e2e` (Full E2E incl. accessibility) | no | every `e2e/*.spec.ts` except `visual*` (includes `fatigue-context.spec.ts` — see above) |
| `cold-start` | no | boots app with no `data/database.db`, asserts `GET /` → 200 |
| `old-db-migration` | no | builds a pre-migration schema DB, boots app, asserts migrated columns/tables + legacy row byte-equality |
| `visual-linux` | no, `if: inputs.run_visual` | runs `visual.spec.ts` + `visual-baseline-thumbnails.spec.ts` only, pinned `ubuntu-24.04`, `PW_VISUAL_SEED=1`, `compare`/`generate` modes |
| `dependency-health` | no | `pip list --outdated` + `safety check`, both `continue-on-error: true` |

Both required-check names (`E2E Functional (Chromium)` and `Type Check (tsc blocking + pyright measure-only)`) carry explicit in-file comments warning that renaming orphans branch protection — consistent with the memory note `reference_ci_required_check_names.md`.

---

## 3. WP0.4 keep/archive verification table

Verified via `grep -rl <script-name>` across `.py/.yml/.ts/.ps1/.bat/.md`, excluding the script's own file and `docs/REFACTOR_PLAN.md` itself (which trivially references its own name list).

| Script | Plan says | Actual code/test/CI refs found | Verdict |
|---|---|---|---|
| `apply_free_exercise_db_mapping.py` | must stay | `tests/test_free_exercise_db_mapping.py`, `e2e/scripts/build_visual_seed.py` (imports `DEFAULT_CSV`/`DEFAULT_VENDOR_BASE`/`parse_csv`), `scripts/curate_free_exercise_db_mapping.py`, `scripts/map_free_exercise_db.py` | **[CONFIRMS-PLAN]** — real test + e2e-adjacent import coupling |
| `apply_youtube_curated.py` | must stay | `tests/test_youtube_video_id.py` | **[CONFIRMS-PLAN]** |
| `build_musclemap_svgs.py` | must stay | `tests/test_muscle_selector_mapping.py` | **[CONFIRMS-PLAN]** |
| `curate_free_exercise_db_mapping.py` | archive candidate | none (docs only) | **[CONFIRMS-PLAN]** |
| `fatigue_calibration_report.py` | must stay (Stage 4 open) | none in code/tests — only docs (`docs/fatigue_meter/*`, `LEFTOVERS_BY_PRIORITY.md`) | **[CONFIRMS-PLAN]** on the stated rationale (owner-guardrail doc references), but note it has **zero automated callers** — it's a manually-invoked report generator, not live automation. Re-verify Stage 4 closure status before WP0.4 executes. |
| `fatigue_movement_pattern_cleanup.py` | must stay | `tests/test_catalog_invariants.py` | **[CONFIRMS-PLAN]** |
| `fatigue_movement_pattern_cleanup_dryrun.py` | archive candidate | none | **[CONFIRMS-PLAN]** |
| `fatigue_stage1_cleanup.py` | must stay | `tests/test_catalog_invariants.py` | **[CONFIRMS-PLAN]** |
| `fatigue_stage1_cleanup_dryrun.py` | archive candidate | none | **[CONFIRMS-PLAN]** |
| `fatigue_stage4_mutation_smoke.py` | archive candidate | none (`e2e/fatigue-stage4-smokes.spec.ts` is confirmed an independent Playwright port — verified by full read, no shared code/import) | **[CONFIRMS-PLAN]** |
| `fatigue_stage4_observer.py` | must stay (Windows scheduled task) | `tests/test_fatigue_stage4_observer.py`, `scripts/install_fatigue_stage4_observer_task.ps1`, `scripts/run_fatigue_stage4_observer.bat`, `scripts/check_fatigue_stage4_automation.ps1` | **[CONFIRMS-PLAN]** — genuine live automation |
| `fatigue_stage4_remaining_smokes.py` | archive candidate | none | **[CONFIRMS-PLAN]** |
| `fatigue_stage4_restore_smoke.py` | archive candidate | none | **[CONFIRMS-PLAN]** |
| `fatigue_stage4_status.py` | must stay | `tests/test_fatigue_stage4_observer.py`, `scripts/check_fatigue_stage4_automation.ps1` | **[CONFIRMS-PLAN]** |
| `map_free_exercise_db.py` | archive candidate | none in code (only docs + informal docstring cross-refs from `curate_free_exercise_db_mapping.py`'s prose) | **[CONFIRMS-PLAN]** |
| `pyright_baseline_diff.py` | must stay | `.github/workflows/ci.yml` (`typecheck` job, blocking step), `tests/test_pyright_baseline_diff.py` | **[CONFIRMS-PLAN]** — required-CI-gate coupling |
| `seed_visual_baseline.py` | must stay | **none** — zero references in any `.py/.ts/.yml/.ps1/.bat`; only prose mentions in docs (`ACTIVE_DEVELOPMENT.md`, `CHANGELOG.md`, `MASTER_HANDOVER.md`, `workout_cool_integration/EXECUTION_LOG.md`) | **[CONTRADICTS-PLAN] / [RISK]** — see below |

### `seed_visual_baseline.py` discrepancy — detail
This is a **different script from `e2e/scripts/build_visual_seed.py`** (confirmed by reading both in full). `scripts/seed_visual_baseline.py`:
- Writes directly via `DatabaseHandler()` against whatever `utils.config.DB_FILE` resolves to (i.e., a live/worktree DB, not a throwaway path).
- Its own docstring says "Run only in a worktree — the DB has skip-worktree applied so the modified file stays out of the index," i.e. it was a **manual, interactive dev tool** used once during the §4 thumbnail-rendering work (shipped in PR #87/#88 per project memory).
- Has no test, no CI step, no e2e caller, no npm script, no other script importing it.

The plan's own archive-procedure standard is "keep if referenced by tests/CI/docs **or live automation**." This script fails that test on the tests/CI/live-automation prongs — it only has doc mentions (the weakest of the three "keep" reasons, per the procedure's own framing, since doc mentions are exactly what the procedure says isn't sufficient in isolation: "grep code, tests, and workflows — not just docs"). Recommend WP0.4 either (a) reclassify it as an archive candidate given the feature it seeded already shipped, or (b) if the owner still wants it for future thumbnail-variant work, explicitly say so in the plan rather than let it default to "must stay" on a docs-only signal — this is exactly the kind of soft inclusion the archive procedure exists to catch.

---

## 4. CSS-cleanup selector-fragility inventory (Phase 4 risk surface)

Ranked by blast radius — how many specs / how central the selector is — since Phase 4's plan (`WP4.1`–`WP4.3`) explicitly renames/dedupes/tokenizes classes.

### Tier 1 — shared infrastructure, breaks silently across ALL visual specs
- **`e2e/visual-helpers.ts` `prepareForScreenshot()`** hardcodes an override stylesheet keyed to ~25 concrete class names to neutralize animation/shadow/radius noise before every screenshot: `.card`, `.collapsible-frame`, `.frame-calm-glass`, `.glass-neumorph-card`, `.page-header`, `.summary-frame`, `.table-header`, `.table-header-underline`, `.table.table-calm`, `.wpdd-button`, `.wpdd-caret`, `.filter-dropdown`, `.uniform-input`, `.form-select`, `.form-control`, `.toggle-icon`, `.scale-btn-compact`, `.scale-indicator`, `.nav-icon`, `.navbar-brand-icon`, `.navbar-toggler-icon`, `.nav-fa-icon`, `.signature-icon`, plus ID selectors `#workout`, `#navbar`. **Risk:** if Phase 4 renames/dedupes any of these, the override CSS silently stops matching — no test failure, just visual noise (animations/shadows) leaking into every one of the 48 (`visual.spec.ts`) + 18 (`visual-baseline-thumbnails.spec.ts`) screenshots, which *will* fail as pixel diffs but with a confusing signal (looks like a real regression, not a stale-selector bug). **Recommend:** WP4.0's fresh red-ledger pass should also grep `visual-helpers.ts`'s override list against the class-rename map produced by each WP4.x PR, updating it in lockstep.

### Tier 2 — hardcoded computed-style assertions (exact colors/values, not just presence)
- **`nav-dropdown.spec.ts:98-100`**: `toHaveCSS('color', 'rgb(109, 93, 252)')` / `'rgb(15, 159, 143)'` / `'rgb(217, 119, 6)'` for `.nav-fa-icon` per nav item. These are exact RGB values presumably sourced from `navbar.css` (a WP4.2-final target). Any token consolidation that changes these three accent colors — even slightly — breaks this **required-CI** spec (promoted to `e2e-functional`).
- **`summary-pages.spec.ts:31-48` `expectSharedLegendSwatches()`**: exact `background-color` RGB for `.volume-legend .volume-indicator.{low,medium,high,ultra}-volume` (`rgb(220,53,69)`, `rgb(253,126,20)`, `rgb(25,135,84)`, `rgb(111,66,193)`), called from both Weekly and Session Summary describe blocks — 2 required-CI tests. These are Bootstrap-adjacent danger/warning/success/purple tones; a token pass touching `components.css` volume-indicator colors breaks both.
- **`user-profile.spec.ts:110-131`** ("Calm Glass styling tokens"): asserts `cursor: pointer`, `borderTopStyle: solid`, numeric `borderRadius > 4`, numeric `borderWidth > 0` via computed style on `.collapse-toggle`. Looser than exact-RGB but still a literal design-token assertion tied to the "Calm Glass" pattern that WP4.2 (`pages-user-profile.css` is item 8 of 10 in the page order) will touch.
- **`volume-progress.spec.ts` `expectDrawerLayoutStable()`**: asserts `layout.drawerBackground !== 'rgb(255, 255, 255)'` in dark mode (a *negative* assertion, less fragile) plus extensive geometry (`getBoundingClientRect` on `.vp-drawer__header`, `.vp-drawer__body`, `.vp-row`, `.vp-close`, `.vp-progress`) and `overflowY` computed style. Geometry assertions are more resilient to color/token changes than to layout changes, but WP4.2 target list doesn't include a `vp-drawer`-specific bundle by name — verify which bundle owns `.vp-*` before touching layout-adjacent CSS.

### Tier 3 — class-name-as-selector across many specs (breaks if classes are renamed/deduped, not if values change)
Selecting on structural/utility class names rather than `data-testid`: `.workout-log-table`, `.results-section`, `.mode-toggle`, `.method-selector`, `.current-goals`, `.progression-legend`, `.volume-legend`, `.debug-info`, `.reference-lift-row`, `.reference-lift-hand-hint`, `.profile-onboarding`, `.profile-explainer`, `.profile-calibration`, `.profile-fatigue-context`, `.user-profile-layout`, `.suggestion-card`, `.set-goal-btn`, `.status-cell`, `.bc-band-segment`, `.superset-checkbox`, `.tbl-view-mode-toggle`, `.vp-row`/`.vp-progress`/`.vp-bonus`/`.vp-list--bonus` family, `.fatigue-badge`/`.fatigue-badge__info-btn`/`.fatigue-badge__band`. These appear **dozens of times** across `user-profile.spec.ts`, `progression.spec.ts`, `workout-log.spec.ts`, `volume-splitter.spec.ts`, `volume-progress.spec.ts`, `summary-pages.spec.ts`, `superset-edge-cases.spec.ts`. A rename/dedupe in Phase 4 (WP4.2 page-by-page, WP4.3 cross-bundle dedupe) breaks any spec that selects the old name with no fallback — none of these have a `data-testid` alternative wired in.
- **Mitigating factor:** many of the same elements *also* carry `data-*` attributes used for behavior (not styling) — e.g. `data-lift-key`, `data-goal-type`, `data-muscle`, `data-fatigue-context`, `data-bodymap-muscle`, `data-canonical-muscles`, `data-side`. Where both exist, the `data-*` half of a compound selector (e.g. `.reference-lift-row[data-lift-key="..."]`) survives a pure class rename since the attribute predicate does the real selecting; only bare-class selectors like `.reference-lift-hand-hint` or `.vp-bonus__heading` are pure-fragile.

### Tier 4 — genuinely stable (data-testid / id / role-based, safe against Phase 4)
- `fatigue.spec.ts` — 13 of 13 assertions key off `[data-testid="fatigue-*"]`. **Best-practice example in the suite.**
- `api-integration.spec.ts` — zero DOM selectors (pure API/JSON).
- Most `#id`-based selectors (`#weight`, `#sets`, `#min_rep`, `#backup-*`, `#workout-estimate-*`, `#vpDrawer`, `#vpToggle`) — IDs are out of scope for a *class*-cleanup by definition, though WP4.2-final's `navbar.css`/`components.css` work could still touch ID-scoped rules without renaming the ID itself.
- `fixtures.ts`'s own `SELECTORS` map already has a `data-testid, #id` dual-fallback pattern (e.g. `NAVBAR: '[data-testid="navbar"], #navbar'`) but **only 22 of 28 specs import it**, and even among importers most bypass `SELECTORS` for ad-hoc raw-class locators inline (grep found only ~267 `SELECTORS.X` call sites total vs. hundreds of raw `page.locator('.foo')`/`page.locator('#foo')` calls across the suite).

**Net assessment for Phase 4:** the plan's own gate ("visual deep gate + `e2e/accessibility.spec.ts`" per WP, plus `dark-mode.spec.ts` at WP4.2-final) will catch *rendering* regressions but **will not catch a renamed class breaking a non-visual functional spec** (e.g. `nav-dropdown.spec.ts`'s exact-RGB assertions, or any Tier-3 bare-class selector) unless that spec is also in the PR's test scope. Recommend Phase 4 WPs explicitly re-run the **full functional shard set**, not just the visual/accessibility/dark-mode gate named in the plan, whenever a WP touches a bundle whose classes are referenced by Tier 2/3 selectors above.

---

## 5. Body-composition JS↔Python parity test (as requested)

`e2e/body-composition.spec.ts:100-125`, test `'JS preview matches Python persisted Navy BFP within rounding'`:
1. Navigates to `/body_composition`, fills `#bc-neck = 38`, `#bc-waist = 85`.
2. Reads the **live client-side preview** text node `[data-bc-bfp]`, regex-extracts the percentage (`([\d.]+)\s*%`).
3. Clicks `#bc-save`, waits for `[data-bc-history-body] tr` to reach count 1 (confirms the POST completed and the row rendered).
4. Fetches `GET /api/body_composition/snapshots`, reads `data[0].bfp_navy` — the **server-persisted float** from the Python Navy-method calculation.
5. Asserts `Math.abs(previewValue - Number(snap.bfp_navy.toFixed(1))) <= 0.05` — i.e., the JS-side live preview (presumably in `static/js/modules/body-composition.js` or similar) and the Python `utils/` Navy BFP formula must agree to within half a rounding unit at `.toFixed(1)` precision.

This is a genuine cross-language duplicate-implementation drift guard — the JS module recomputes the U.S. Navy BFP formula independently (for instant UI feedback before the round-trip) and this test is the only thing keeping that duplicate formula in sync with the Python source of truth. Any refactor that changes either implementation's rounding/constants without updating the other will fail this test, which is exactly its job. Not currently listed as a "parity test" anywhere in `.claude/rules/` or `CLAUDE.md` — worth naming explicitly if a future refactor touches `utils/body_composition.py`-equivalent logic or the JS module.

---

## 6. Test-suite quality risk — pervasive vacuous assertions

**[RISK] — not explicitly asked for, but directly bears on how much safety net the E2E suite actually provides during any refactor (CSS or otherwise).** A large fraction of the "edge case" specs use tautological or near-tautological assertions that pass regardless of app behavior:
- `expect(true).toBeTruthy()` / `expect(true).toBe(true)` — appears **~15 times** in `validation-boundary.spec.ts` alone (e.g. every "rejects negative/zero/decimal/extreme value" test ends this way after commenting out the real check), plus scattered in `empty-states.spec.ts`, `exercise-interactions.spec.ts`, `superset-edge-cases.spec.ts`, `workout-log.spec.ts`.
- `expect(x || true).toBeTruthy()` pattern — makes the left operand meaningless — found in `exercise-interactions.spec.ts` (`hasReplace || true`, `isVisible || true`, `toastVisible || supersetIndicator > 0 || isEnabled || true`), `superset-edge-cases.spec.ts` (`toastVisible || true` ×2, `hasSupersetClass || true`), `empty-states.spec.ts` (`messageVisible || true` ×2).
- `expect(count >= 0).toBeTruthy()` / `expect(rows >= 0).toBeTruthy()` — count is always `>= 0` by construction (`.count()` never returns negative) — in `empty-states.spec.ts`, `workout-log.spec.ts`.

**Why this matters for the refactor:** `validation-boundary.spec.ts` (23 documented tests per `.claude/rules/testing.md`) reads as real input-validation coverage in the CI inclusion contract and the spec-count ledger, but roughly half its tests cannot fail no matter what the validation logic does — they were likely scaffolded with a real assertion that got commented out/weakened at some point and never restored. This inflates confidence in refactor safety nets that don't actually exist for negative/zero/decimal/extreme-value handling in `add_exercise`. Recommend flagging this as its own cleanup candidate (outside Phase 4) before relying on "validation-boundary passed" as evidence that a routes/utils refactor (Phase 1) didn't regress validation.

---

## 7. `.claude/rules/testing.md` is a stale ledger — additional confirmation of plan item #10

`.claude/rules/testing.md`'s "E2E test map" table lists **17 specs / 315 tests total**, and its baseline says "E2E Playwright: 314 passed (~7.2m, Chromium only)". The actual `e2e/` directory has **28 spec files**. The 11 undocumented specs (`accessibility`\*, `body-composition`, `fatigue-context`, `fatigue-stage4-smokes`, `fatigue`, `learned-calibration`, `nav-dropdown`, `program-backup`\* rename, `ui-hardening`, `visual-baseline-thumbnails`, `volume-progress` — \*some renamed/merged since) postdate this table. This is a second, independent piece of evidence (alongside `docs/REFACTOR_PLAN.md`'s own response-matrix item #10) that stale-ledger drift is a real, recurring problem in this repo's docs, not a one-off — **[CONFIRMS-PLAN]**, and suggests WP0.5 (CLAUDE.md/docs sync) should also touch `.claude/rules/testing.md`, which the current WP0.5 scope (blueprint table, verified-count section, `initialize_exercise_order` line ref) does not mention.

---

## 8. PW_VISUAL_SEED / webServer / DB isolation mechanics (confirmed by reading `playwright.config.ts` + both seed scripts)

- `playwright.config.ts` computes `seedScript = PW_VISUAL_SEED==='1' ? 'prepare_visual_db.py' : 'prepare_e2e_db.py'` and builds `webServer.command = "<python> e2e/scripts/<seedScript> --output <e2eDbPath> && <python> app.py"`, with `webServer.env.DB_FILE` pointed at the same throwaway path (`artifacts/e2e/database.e2e.db`). This is confirmed exactly as `e2e/CLAUDE.md` describes it.
- `prepare_e2e_db.py` imports `apply_migrations`/`assert_safe_output`/`snapshot_database` **from** `prepare_visual_db.py` (not duplicated) — single migration-application code path for both seed modes, reducing drift risk between functional and visual DB schemas.
- `prepare_e2e_db.py` additionally wipes a fixed `USER_STATE_TABLES` tuple (13 tables) after migrating — table-existence-guarded, so an older seed DB lacking a newer table is a no-op rather than an error.
- Both scripts have a path-identity safety guard (`assert_safe_output`) refusing to target `data/database.db` or anything under `data/auto_backup/` unless `--force` is passed — this guard is resolved-path based, not existence-based, so it can't be bypassed by deleting the live DB first.
- **Not documented anywhere I found**: `e2e/scripts/build_visual_seed.py` (which *regenerates* the committed `database.visual.seed.db` fixture, as opposed to `prepare_visual_db.py`, which *snapshots* that already-committed fixture at test-run time) is a fourth script in `e2e/scripts/` beyond the three named in `e2e/CLAUDE.md`'s "Key files" table (which only lists `fixtures.ts` and `fixtures/database.visual.seed.db`, not the `scripts/` subdirectory contents at all). `build_visual_seed.py` is the tool an owner runs manually when the committed seed needs new fixture rows (e.g., adding a curated exercise with a `media_path`) — genuinely live/must-stay by function, just undocumented in the E2E orientation doc.

---

## Cross-cutting seeds

- The CSS-cleanup risk surface is bimodal: **visual specs** will catch pixel regressions but give a confusing signal on stale selectors (silently stop matching, not "selector not found" — Tier 1 finding); **functional specs** with bare-class or exact-computed-style assertions (Tier 2/3) will hard-fail with a clear "selector/assertion broke" signal but are *not* named in Phase 4's stated gate (visual + accessibility + dark-mode only) — the plan should widen the Phase-4 gate to the full functional shard whenever a touched bundle intersects the Tier 2/3 selector list above, especially `navbar.css` (nav-dropdown's exact RGBs) and any bundle owning `.volume-legend`/`.volume-indicator` (summary-pages' exact RGBs, both required-CI).
- `scripts/seed_visual_baseline.py`'s "must stay" classification rests entirely on doc mentions, which is the exact failure mode the archive procedure was written to catch (`docs/scan` note: "grep code, tests, and workflows — not just docs") — worth a second look at WP0.4 execution time, independent of this scan's other findings.
- `e2e/CLAUDE.md`'s CI-inclusion-contract table (the authoritative per-spec CI-placement doc) has one real gap: `fatigue-context.spec.ts` isn't mentioned at all, so a reader can't tell from that table whether its absence from `e2e-functional-shard` is intentional or an oversight — small, cheap fix (one row), same category of doc drift as the stale `testing.md` spec count.
- The vacuous-assertion pattern (§6) means the effective functional-test coverage for basic input validation is smaller than the spec-count/CI-green signal suggests — relevant to any Phase 1/2 routes-and-utils refactor that touches `add_exercise` validation, not just Phase 4.
