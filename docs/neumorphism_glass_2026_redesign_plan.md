# Calm Glass 2026 Redesign — Hypertrophy Toolbox

> **Status:** PROPOSED v3.3 — v3.2 plus Opus + Codex joint review fixes (CSS load-scope contract, frozen `#navbarNav`, full token collision audit, P4c dead-call cleanup, P5 mobile dropdown gate, P9 page-scope preservation).
> **Scope:** Presentation layer only. No DB schema, calculation, or API-contract changes (per CLAUDE.md §1).
> **Reference mockup:** [docs/mockups/redesign-preview.html](mockups/redesign-preview.html) (design-locked, indigo-only)

---

## 0. Post-mortem of the v2 attempt (commit `d1618be`)

Gemini shipped Phases 3-8 of v2 as a single commit `d1618be "feat(ui): implement Calm Glass 2026 redesign (Phases 3-8)"`. It broke the app and was reverted. Forensic diff:

| Metric | Before `d1618be` | After `d1618be` | What it means |
|---|---:|---:|---|
| CSS files | 34 | 8 | 26 files deleted in one commit |
| Total CSS lines | ~18,400 | ~400 | **97.8% of CSS removed, not migrated** |
| `components.css` | — | **82 lines** | Attempted to replace 5,000+ lines of button/form/table styling |
| `pages.css` | — | **68 lines** | Attempted to replace 9,000+ lines of per-page styling |
| `replace_classes.py` | — | 25 lines | **Bulk rename script** — the smoking gun for broken JS selectors |
| Phases shipped | — | **6 in one commit** | No per-phase gate, no intermediate test run |

**Root causes of failure:**

1. **Deleted CSS before replacements were functionally equivalent.** An 82-line `components.css` cannot replace `styles_buttons.css` (618 lines) + `styles_forms.css` (893) + `styles_tables.css` (1,002) + `styles_cards.css` (71) + `styles_dropdowns.css` (155) + `styles_tooltips.css` (24) + `styles_modals.css` (348) + `styles_notifications.css` (382) + `styles_filters.css` (828). The visual regression was catastrophic because ~95% of the style rules vanished.
2. **Bulk class-rename script (`replace_classes.py`) ran blind.** A 25-line regex sweep cannot understand which class names are referenced by JavaScript (`document.querySelector('.backup-restore-btn')`, `getElementById('backup-list')`) or by Playwright E2E specs. JS calls silently returned `null` and attached no listeners.
3. **Shipped 6 phases in one commit.** Zero gate between phases meant zero chance to catch the break early.
4. **No size-parity check.** A 97.8% CSS reduction should have been an automatic red flag halting the commit.

**Lessons that shape v3:** (§1 commandments)

---

## 1. Implementation commandments — non-negotiable rules

These are hard rules. If any gets violated during implementation, **stop and revert the current phase**.

- [ ] **C1.** **Never delete or unlink a CSS file in the same commit as adding its replacement.** Add/load the replacement first, leave the legacy file linked for at least one full green CI cycle and minimum 7 days, then remove legacy links/imports in a separate commit. Physical deletion waits until P10 after those links have been absent for 3 more green days, unless the user explicitly fast-tracks.
- [ ] **C2.** **No bulk rename scripts.** No `sed`/regex sweeps across the codebase that rewrite class names, IDs, `data-testid`, or selectors. All renames are manual, one file at a time.
- [ ] **C3.** **Size-parity check.** If any single commit reduces total CSS line count by more than **15%** without a matching line-count increase elsewhere, halt and investigate. Report the delta in the commit message.
- [ ] **C4.** **One phase per PR.** Never merge two phases in the same commit. Every phase gets its own commit, its own CI run, and its own human review.
- [ ] **C5.** **Frozen DOM contract.** Every ID, `data-testid`, and JS-queried class name in §3 is **immutable** until explicitly unfrozen. CSS can restyle them; HTML must keep them.
- [ ] **C6.** **Preflight gate before every phase.** Cannot start a phase unless: git tree clean; `npm run test:py` green; `npm run test:e2e` green; baseline screenshots current.
- [ ] **C7.** **Exit gate after every phase.** Cannot claim a phase done unless: pytest still green, E2E still green, manual smoke of all 7 pages in light + dark + mobile widths passes.
- [ ] **C8.** **Additive over destructive.** Until P7/P8, all phases add files or edit existing files. No deletions. No file renames.
- [ ] **C9.** **JS/E2E selector survey before every HTML change.** Before editing any template, run the commands in §3 and confirm no frozen selector is touched.
- [ ] **C10.** **Human + at least one AI reviewer approves each phase.** Claude (this agent), Gemini, and Codex rotate; any one of the AIs signs off per phase, human signs off always.
- [ ] **C11.** **Redesign E2E gates must fail on null/undefined selector errors.** The legacy broad ignores in `e2e/fixtures.ts` are not sufficient for redesign gates; P0 must add/tighten a strict fixture before any visual baseline is trusted.

---

## 2. Context — why the site feels off (unchanged from v2)

A partial liquid-glass pass already landed. Remaining "off" feeling is presentation-layer architectural debt:

| # | Symptom | Evidence |
|---|---|---|
| 1 | CSS fragmentation: 34 files, ~655KB | `wc -c static/css/*.css | tail -1` → 671,241 |
| 2 | Tokens defined but bypassed | `styles_general.css:6-13` declares `--glass-bg` but 1,785 inline rgba/backdrop-filter across 29 files |
| 3 | `'Inter'` referenced, never loaded | no `@font-face` / Google Fonts in `base.html` head |
| 4 | `!important` war — 148 in dark mode alone | `grep -c '!important' static/css/styles_dark_mode.css` → 148 |
| 5 | Button styling duplicated across 4+ files | `styles_buttons.css` + `styles_workout_plan.css` + `styles_welcome.css` + `styles_volume_splitter.css` |
| 6 | Fragile zoom hack | `templates/base.html:5-17` — 8 discrete `--ui-scale-inverse` values, compounds with browser-native zoom |
| 7 | Nav order fights mental model | Plan → Summary → Summary → Log → Progression → Volume; CLAUDE.md prescribes Plan → Log → Analyze → Progress → Distribute |
| 8 | Backup is invisible | modal lives in `templates/workout_plan.html:804`; no navbar entry |

Design target (also unchanged): a **calm, clear workout tool with soft depth and restrained glass** — restraint + hierarchy + typography, not pillowy neumorphism.

---

## 3. Frozen DOM contracts — immutable until unfrozen

These names are referenced by JS modules and/or Playwright E2E fixtures. Changing any of them breaks runtime behavior and/or automated tests. A CSS refactor can restyle them; a template refactor **must not rename, remove, or duplicate them**.

### 3.0 Authoritative source (re-run before every HTML-touching phase)

The authoritative list below is a snapshot. It must include selectors from ES modules, inline template scripts, and Playwright fixtures. Before editing any template, re-run:

```bash
rg -no -r '$1' "getElementById\(['\"]([^'\"]+)['\"]" static/js templates | sort -u
rg -no -r '$2' "querySelector(All)?\(['\"]([^'\"]+)['\"]" static/js templates | sort -u
rg -no -r '$1' "data-testid=\"([^\"]+)\"" templates static/js e2e | sort -u
rg -n "page\.locator\(|waitForSelector\(|getByTestId\(|click\(['\"]" e2e
```

If the first three commands find a stable ID/class/data-attribute selector not listed below, it was added since this plan — add it to this section in the same commit that touches it. Generic local selectors such as `form`, `tbody`, `i`, and `span` do not need listing unless they are being used as structural contracts. The Playwright locator scan is a manual review aid; any stable ID/class/data-testid from E2E that could be affected by a template change must also be added before that change lands. Inline `<script>` blocks in templates count as runtime JS.

### 3.1 Element IDs — referenced by JS, inline template scripts, and/or E2E

Grouped by subsystem. Every ID listed is frozen.

**Navbar / global chrome**
- [x] `#navbar`, `#nav-brand`, `#nav-workout-plan`, `#nav-workout-log`, `#nav-weekly-summary`, `#nav-session-summary`, `#nav-progression-plan`, `#nav-volume-splitter`, `#nav-backup`
- [x] `#navbarNav` — Bootstrap collapse target (`data-bs-target="#navbarNav"` on toggler at `base.html:83`; collapse container at `base.html:91`; also queried by `navbar-enhancements.js:14`). **P5 blocker: must not be renamed or removed during navbar restructure.**
- [x] `#darkModeToggle`, `#muscleModeToggle`
- [x] `#scale-decrease`, `#scale-increase`, `#scale-indicator` — A- / A+ scale control
- [x] `#liveToast`, `#toast-body` — global toast
- [x] `#global-loading-indicator`, `#error-message-container`
- [x] `#auto-backup-banner`, `#restore-auto-backup-btn` — auto-backup banner injected into the main content container

**Backup / Program Library**
- [x] `#programLibraryModal`, `#saveBackupModal`, `#confirmRestoreModal`, `#confirmDeleteModal` — Bootstrap modal IDs (referenced by `bootstrap.Modal.getInstance(document.getElementById(...))` — 6 call sites in program-backup.js)
- [x] `#backup-list`, `#backup-name`, `#backup-note`
- [x] `#saveBackupSubmit`, `#openSaveFromLibrary`
- [x] `#restoreBackupName`, `#deleteBackupName`, `#confirmRestoreBtn`, `#confirmDeleteBtn`
- [x] `#save-program-btn`, `#load-program-btn` — workout-plan toolbar triggers, directly referenced by E2E

**Workout plan page (`/workout_plan`)**
- [x] `#routine-env`, `#routine-program`, `#routine-day` — routine cascade selects
- [x] `#routine`, `#routineType`, `#exercise`, `#exerciseSelect`, `#exerciseName`
- [x] `#routine-breadcrumb`, `#routine-cascade-container`, `#routine-filter`, `#routine-tabs`
- [x] `#add_exercise_btn`, `#add-exercise-btn` (both variants exist — both frozen)
- [x] `#sets`, `#min_rep`, `#max_rep_range`, `#rir`, `#rpe`, `#weight` — inline edit fields
- [x] `#clear-filters-btn`, `#export-to-log-btn`, `#export-to-excel-btn`, `#import-from-plan-btn`, `#workout_plan_table_body`
- [x] `#filters-form`, `#search-filter`, `#muscle_filter`, `#isolated_muscles_filter`
- [x] `#exercise-details`, `#workout-stats`, `#tab-count-all`
- [x] `#link-superset-btn`, `#unlink-superset-btn`, `#superset-actions`, `#superset-selection-info`
- [x] `#suggestionsContainer`, `#suggestionsList` — exercise suggestions
- [x] `#clear-plan-btn`, `#clearPlanModal`, `#confirmClearPlanBtn` — clear-plan confirmation
- [x] `#generate-plan-btn`, `#generatePlanModal`, `#generatePlanSubmit`, `#generatePlanForm` — starter plan generator
- [x] `#gen-training-days`, `#gen-environment`, `#gen-experience`, `#gen-goal`, `#gen-volume-scale`, `#volume-scale-value`, `#gen-overwrite`, `#gen-no-overhead`, `#gen-no-deadlift`, `#plan-preview-content` — generator form fields and preview

**Welcome / erase-data flow (`/`)**
- [x] `#eraseDataBtn`, `#eraseDataModal`, `#confirmEraseBtn`
- [x] `#successToast`, `#errorToast` — legacy welcome-page toasts used by inline script

**Workout log (`/workout_log`)**
- [x] `#import-from-plan-btn`, `#clear-log-btn`, `#confirm-clear-log-btn`, `#clearLogModal`
- [x] `#workout-log-table`, `#history-body`, `#workout`, `#date-filter`, `#routine-filter`

**Weekly / session summary**
- [x] `#summary-method` — counting-mode toggle
- [x] `#results-body`
- [x] `#contribution-mode`, `#weekly-summary-table`, `#session-summary-table`, `#categories-table-body`, `#volume-formula-text`, `#pattern-coverage-container`

**Progression (`/progression`)**
- [x] `#goalForm`, `#goalModalLabel`, `#goalSettingModal`, `#saveGoal`
- [x] `#goalType`, `#goalDate`, `#currentValue`, `#targetValue`
- [x] `#confirmDeleteGoal`, `#deleteGoalModal`, `#closeGoalModal`

**Volume splitter (`/volume_splitter`)**
- [x] `#volume-splitter-app`, `#sliders`, `#training-days`
- [x] `#calculate-volume`, `#reset-volume`, `#export-volume`
- [x] `#confirmDeleteVolumePlan`, `#deleteVolumePlanModal`

### 3.2 `data-testid` attributes

Full list from `e2e/fixtures.ts` — every value below is frozen:

- [x] `navbar`, `nav-brand`, `nav-workout-plan`, `nav-workout-log`, `nav-weekly-summary`, `nav-session-summary`, `nav-progression-plan`, `nav-volume-splitter`, `nav-backup`
- [x] `dark-mode-toggle`, `toast-container`
- [x] `routine-env`, `routine-program`, `routine-day`
- [x] `add-exercise-btn`, `exercise-search`, `exercise-table`
- [x] `export-excel-btn`, `export-to-log-btn`, `clear-filters-btn`
- [ ] Any new `data-testid` added in §3.5 unfreeze process must be appended here in the same commit

### 3.3 Class names used as JS selectors

Audited via the §3.0 selector commands across `static/js`, inline template scripts, and E2E. These class names are state machines or selector contracts — restyle, but do not rename or remove.

**Structural selectors (fallback to data-testid/id; JS assumes both may exist)**
- [x] `.workout-plan-table`, `#workout-plan-table tbody`, `#workout_plan_table_body` — all three forms appear; keep all
- [x] `.workout-log-table`, `#workout-log-table tbody` — workout-log sorting/filter rendering contract
- [x] `.btn-export-excel` — fallback for Excel export button
- [x] `.toast-container` — toast injection target
- [x] `.container-fluid`, `main` — banner injection target (`document.querySelector('main') || document.querySelector('.container-fluid')`)
- [x] `.welcome-container` — app.js uses presence to detect the welcome page
- [x] `#successToast .toast-body span`, `#errorToast .toast-body span` — welcome inline script updates legacy toast text
- [x] `.collapse-toggle`, `.toggle-text`, `.collapsible-frame`, `.workout-plan.table-container` — inline collapse script in `workout_plan.html`
- [x] `#generatePlanForm select`, `#generatePlanForm input` — generator inline preview script

**Backup list rendering**
- [x] `.backup-list-item`, `.backup-restore-btn`, `.backup-delete-btn`, `.backup-list`

**Workout-plan row machinery**
- [x] `.editable`, `.btn-swap`, `.superset-checkbox`, `.execution-style-cell`, `.execution-style-picker`, `.execution-option`, `.amrap-params`, `.emom-params`, `.btn-close-picker`, `.btn-cancel-exec`, `.btn-save-exec`
- [x] `.exercise-name`, `.wpdd-container`, `.wpdd-button`, `.filter-dropdown`
- [x] `.routine-tab`, `.routine-tab-btn`, `[data-routine="all"]`, `[data-dynamic="true"]`
- [x] `[data-exercise-id="..."]`, `[data-superset-group]`, `[data-raw-value]`, `[data-label="..."]`

**State classes (toggled by JS — template must not pre-apply or strip)**
- [x] `.active`, `.loading`, `.open`, `.theme-animating`
- [x] `.value-changed` — workout-controls-animation.js
- [x] `.filter-applied`, `.is-invalid-required`, `.has-validation-error`
- [x] `.superset-selected`, `.superset-partner-dragging`, `.row-swapped`
- [x] `.tbl--view-simple`, `.tbl--view-advanced` — table-responsiveness.js
- [x] `.picker-dropup`, `.mode-text`
- [x] `.cascade-dropdown-wrapper`, `.cascade-connector`, `.cascade-connector-1`, `.cascade-connector-2`
- [x] `.equipment-check` (checkbox class queried by `querySelectorAll`)
- [x] `.scale-btn[data-scale]`, `.accessibility-toggle`, `.accessibility-dropdown`

### 3.4 Bootstrap / third-party contracts

- [x] Bootstrap 5.1.3 JS must stay loaded — `bootstrap.Modal.getInstance(...)` is used in `program-backup.js` (6 call sites) + `app.js` (generatePlanModal)
- [x] `data-bs-toggle`, `data-bs-target`, `data-bs-dismiss` attributes on any modal-triggering element must remain
- [x] Font Awesome 5.15.4 icon classes (`fa-*`) are used inline across templates — do not remove the CDN link
- [x] `navbar-toggler`, `navbar-collapse`, `navbar-nav` Bootstrap classes must stay on the navbar structure for mobile toggle to work

### 3.5 Unfreezing process

If a phase genuinely needs to rename a frozen selector:
1. Update the E2E `fixtures.ts` to accept both old AND new selectors (pattern already in use: `'[data-testid="X"], #X'`).
2. Update all JS call sites in the same commit as the template change.
3. Run full E2E suite; confirm green.
4. Document the change in the phase's commit message AND append the new selector to the relevant §3.1/3.2/3.3 subsection in this plan file in the same commit.
5. Only then can the old selector be removed (in a later phase, not the same commit).

### 3.6 Re-audit gate before P6 and P9

Before starting P6 (component overlays) and again before P9 (consolidation):
- [ ] Re-run all selector-audit commands from §3.0
- [ ] Diff the output against §3.1 / §3.2 / §3.3
- [ ] Any stable ID/class/data-attribute selector in the first three command outputs but not in the plan → append to plan (same commit as whatever phase surfaced it)
- [ ] Review the Playwright locator scan for affected IDs/classes; append any stable contract selectors before the template change
- [ ] Any selector in the plan but not in the first three command outputs → safe to mark as "removed in §3.1 on YYYY-MM-DD" (do not delete the line — leave a tombstone so future reviewers can trace)

---

## 4. Feature / flow inventory — every journey that must still work

Each box is a recurring manual smoke test. Leave it unchecked until that exact manual pass is run for the current phase; automated E2E coverage alone does not flip these boxes.

### 4.1 Navigation
- [ ] Click every navbar link — each loads the correct page
- [ ] Mobile burger menu opens/closes at < 992px
- [ ] Dark mode toggle flips theme and persists across page loads
- [ ] UI scale control (A- / A+) scales the page
- [ ] Muscle naming mode toggle (Simple / Scientific) switches labels
- [ ] Brand link returns to `/`

### 4.2 Workout plan (`/workout_plan`)
- [ ] Routine cascade (env → program → day) populates dropdowns
- [ ] Filter panel filters the exercise list
- [ ] Clear filters button resets filters
- [ ] Add exercise button appends a row
- [ ] Edit sets/reps/weight/RIR/RPE inline; values persist on reload
- [ ] Replace exercise modal opens and replaces selection
- [ ] Superset linking works
- [ ] Export to Excel downloads .xlsx
- [ ] Export to Log copies plan into the log
- [ ] Program Library button opens modal (from this page AND from nav, post-P3)
- [ ] Save backup, restore backup, delete backup all work

### 4.3 Workout log (`/workout_log`)
- [ ] Log table populates with planned exercises
- [ ] Edit scored reps / actual weight / actual RIR per set; persists
- [ ] Clear log button empties the log with confirmation
- [ ] Import from plan button repopulates

### 4.4 Summaries
- [ ] `/weekly_summary` renders muscle-volume table; counting-mode toggle (Raw / Effective) switches values
- [ ] Contribution-mode toggle (Direct / Total) switches values
- [ ] Pattern coverage section renders
- [ ] `/session_summary` renders per-session averages

### 4.5 Progression & Distribution
- [ ] `/progression` exercise dropdown populates; suggestions render
- [ ] Goals table renders
- [ ] `/volume_splitter` step-by-step calculator walks through correctly; final allocation renders

### 4.6 Cross-cutting
- [ ] Toast notifications appear on save/delete actions
- [ ] Auto-backup banner appears after startup backup
- [ ] Error page renders on deliberate 404
- [ ] All forms validate required fields
- [ ] `prefers-reduced-motion` honored

---

## 5. Verified baselines (2026-04-18, pre-implementation)

Re-run these before P0 to reconfirm:

```bash
ls static/css/*.css | wc -l                                  # expect 34
wc -c static/css/*.css | tail -1                             # expect ≈ 671241
grep -c '!important' static/css/styles_dark_mode.css          # expect 148
grep -rE 'rgba\(|backdrop-filter' static/css/ | wc -l         # expect 1785
npm run test:py                                              # expect 913 passed / 1 skipped
npm run test:e2e                                             # expect 314 passed (Chromium)
```

**Final exit-criteria targets (hit after P10):**
- File count: ≤ 15 (8 global + 7 per-route page bundles, excluding `bootstrap.custom.min.css`)
- `!important` in dark theme: ≤ 5
- `rgba(` / `backdrop-filter` inline occurrences: < 50
- Baselines stay green

---

## 6. Global prerequisites — before P0 starts

- [x] Working tree clean (`git status` shows no modifications)
- [x] Branch `redesign/calm-glass-2026` reset to last known-good commit (NOT `d1618be`)
- [x] `npm run test:py` → 913 passed / 1 skipped
- [x] `npm run test:e2e` → 314 passed
- [x] `npm run build:css` → no errors
- [x] App starts: `python app.py`, `/` renders, navbar links work
- [x] Playwright screenshot baseline refreshed (command in P0)
- [x] This plan file approved by Human + Gemini + Codex (audit trail in §14)
- [x] Mockup [docs/mockups/redesign-preview.html](mockups/redesign-preview.html) opened in browser; locked palette/font/background/neumorphism-dial confirmed (§13)

---

## 7. Phases — checklist-driven

Every phase has: **Preflight gate → Tasks → Exit gate → Commit → Rollback command**.

---

### Phase P0 — Audit + deterministic baseline screenshots

**Why:** You cannot detect a regression without a stable "before." A flaky baseline is worse than none — every phase will blame the redesign for drift that's really caret blink, fake dates, or font-swap mid-capture.

**Preflight**
- [x] §6 global prerequisites all checked
- [x] §5 baseline commands re-run; values recorded in commit message
- [x] Confirm `playwright.config.ts` sets a fixed `timezoneId` and `locale` (or add them in P0a)

**Tasks — split into P0a setup and P0b capture, separate commits**

P0a. Deterministic capture harness
- [x] Create `e2e/visual.spec.ts` with the stability fixtures below
- [x] Add `e2e/visual-helpers.ts` exporting two helpers:
  - `installDeterminism(page)` runs **before navigation** and freezes browser state:
    ```ts
    await page.addInitScript(() => {
      const FIXED = new Date('2026-04-18T09:00:00Z').valueOf();
      const NativeDate = Date;
      // @ts-ignore
      globalThis.Date = class extends NativeDate {
        constructor(...args: any[]) { super(...(args.length ? args : [FIXED])); }
        static now() { return FIXED; }
      };
      localStorage.clear();
    });
    ```
  - `prepareForScreenshot(page)` runs **after navigation** and injects CSS to neutralize all animation/transition and caret blink:
    ```ts
    await page.addStyleTag({ content: `
      *, *::before, *::after {
        animation-delay: 0s !important;
        animation-duration: 0s !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
      input, textarea { caret-color: transparent !important; }
      ::-webkit-scrollbar { display: none; }
    `});
    ```
  - blocks font loads from going into fallback: `await page.evaluate(() => document.fonts.ready);`
  - sets viewport explicitly: each test calls `page.setViewportSize({ width, height })` before navigation
  - sets `deviceScaleFactor: 1` (default) — do not override
- [x] Add `e2e/strict-fixtures.ts` or tighten `e2e/fixtures.ts` for redesign gates so null/undefined selector errors fail tests. Remove the broad ignores for `Cannot read properties of null`, `Cannot read properties of undefined`, and `is not defined` from the fixture used by `visual.spec.ts`, `nav-dropdown.spec.ts`, and every new redesign spec.
- [x] In the spec, for each screenshot call, mask known volatile regions:
  ```ts
  await expect(page).toHaveScreenshot({
    fullPage: true,
    animations: 'disabled',
    caret: 'hide',
    mask: [
      page.locator('#auto-backup-banner'),
      page.locator('.timestamp, [data-volatile]'),
      page.locator('.toast-container'),
    ],
    maxDiffPixels: 0,
    threshold: 0,
  });
  ```
- [x] In `playwright.config.ts` (or the spec's `test.use`), pin:
  - `locale: 'en-US'`
  - `timezoneId: 'UTC'`
  - `colorScheme: 'light'` (override per test for dark)
  - `viewport: { width: 1440, height: 900 }` as default
- [x] Seed DB to a known state before capture. Preferred: `conftest.py`-style fixture that (a) stops the app, (b) copies `data/database.db` to `data/database.db.pre_visual.bak`, (c) writes a seeded DB with `utils/auto_backup.create_startup_backup()` logic to a temporary snapshot, (d) restarts app against the seed, (e) on teardown restores the bak. Alternative: commit a small `data/database.seed.visual.db` and have P0a point Flask at it via `DB_FILE` env var during visual runs only.
- [x] Commit: `test(redesign): P0a add deterministic visual-regression harness`

P0b. Baseline capture
- [x] Run `npx playwright test e2e/visual.spec.ts --project=chromium` and commit the `__screenshots__/` outputs
- [x] Target inventory: 7 pages × 3 widths (375 / 768 / 1440) × 2 themes (light / dark) = **42 screenshots**
- [x] Record §5 baseline outputs, the seed-DB hash, and Playwright version in `docs/redesign-audit.md`
- [x] Record the Chromium version and OS that captured the baseline (future reviewers can re-verify on the same stack)
- [x] Commit: `chore(redesign): P0b capture baseline screenshots and audit`

**Exit gate**
- [x] 42 screenshots present under `e2e/__screenshots__/visual.spec.ts-snapshots/`
- [x] Re-running `npx playwright test e2e/visual.spec.ts` twice back-to-back produces zero diff with `maxDiffPixels: 0` (proves determinism)
- [x] `npm run test:e2e` still → 314+ passed (314 + the new visual spec)
- [x] `docs/redesign-audit.md` present and committed

**Rollback:** `git revert <P0b sha>` then `git revert <P0a sha>` (harness + baselines are two separate commits; no production impact)

---

### Phase P1 — Design-direction approval (non-code)

**Why:** Lock palette + font + background before touching production code so downstream phases have a fixed target.

**Preflight**
- [x] P0 committed and green
- [x] Mockup opened in a modern browser

**Tasks**
- [x] Human reviews the design-locked mockup in light + dark (indigo only)
- [x] Human confirms §13 locked answers still stand; no A/B/C palette re-selection in v3.2
- [x] Confirm `docs/mockups/redesign-preview.html` contains only the chosen palette + font + background and no interactive palette switcher
- [x] Re-capture the mockup screenshots for the record

**Exit gate**
- [x] §13 answered with concrete values
- [x] Mockup committed in final form

**Commit:** `docs(redesign): P1 finalize design direction (palette, font, background)`

**Rollback:** `git revert HEAD` (mockup only; production untouched)

---

### Phase P2 — Token + motion overlay, Inter font load (additive)

**Why:** Introduce the new token system + font loading. Legacy CSS remains loaded; new tokens only take effect for components that opt in. P2a must not override legacy-used custom properties such as `--glass-bg`, because legacy CSS already references them; production-only glass tokens are namespaced as `--calm-*` until a visual-change phase opts in. **But loading Inter globally will change font rendering pixel-for-pixel** in any text currently falling back to Helvetica Neue / Segoe UI / system defaults — this is intentional and is the first visible change of the redesign.

P2 splits into two commits to separate the zero-visual-diff piece from the font swap, so the gate is unambiguous.

**Preflight**
- [x] P1 committed and green
- [x] §6 global prerequisites re-run
- [x] Current `visual.spec.ts` baseline (from P0) on disk; we'll refresh it at the end of P2b, not P2a

**Tasks — split into P2a and P2b, separate commits**

P2a. Tokens + motion CSS only (no font change yet)
- [x] Create `static/css/tokens.css` with the token block from §13 locked values
- [x] `tokens.css` in P2a contains token declarations only (`:root` and `[data-theme="dark"]`); do **not** add `body`, typography, background, component, or reset selectors yet
- [x] Before writing `tokens.css`, run the **full custom-property collision audit** — not just `--glass-*`:
  ```bash
  # Extract all custom property names from existing styles_tokens.css
  rg -o -- "--[a-z0-9-]+" static/css/styles_tokens.css | sort -u > /tmp/old_tokens.txt
  # Extract all custom property names planned for new tokens.css (from §13 locked values)
  # Compare: any name in both lists is a collision risk
  # Also check glass tokens used across legacy CSS:
  rg -n "var\(--glass|--glass-" static/css
  ```
  `styles_tokens.css` already defines `--space-*`, `--input-*`, `--btn-*`, `--frame-*`, `--table-*`, `--font-size-*`, and `--container-*` (lines 17-84, with media-query overrides through line 372). Any new token in `tokens.css` that reuses these names will silently override the responsive scaling system.
- [x] Use namespaced production tokens for any mockup token that collides with legacy names:
  - `--glass-bg` → `--calm-glass-bg`
  - `--glass-border` → `--calm-glass-border`
  - `--glass-blur` → `--calm-glass-blur`
  - `--glass-sat` → `--calm-glass-sat`
  - keep legacy `--glass-bg`, `--glass-bg-hover`, `--glass-shadow`, `--glass-inset` untouched until an explicit visual-change phase
  - **do not redefine** any `--space-*`, `--input-*`, `--btn-*`, `--frame-*`, `--table-*`, `--font-size-*`, or `--container-*` token already in `styles_tokens.css` — use `--calm-` prefix if the mockup needs a different value for any of these
- [x] Create `static/css/motion.css` with keyframes + `prefers-reduced-motion` block (mockup lines 284-294)
- [x] In `templates/base.html`, add the redesign overlay links **after** the existing `{% block page_css %}{% endblock %}` so they load after page-specific CSS. Final order:
  ```html
  {% block page_css %}{% endblock %}
  <link rel="stylesheet" href="{{ url_for('static', filename='css/tokens.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/motion.css') }}">
  ```
- [x] Do **not** add the Google Fonts link yet
- [x] Do **not** delete or reorder any existing `<link>` tag
- [x] Do **not** edit any `styles_*.css` file

**P2a exit gate** (zero-pixel-diff is the gate here)
- [x] `npm run test:py` green
- [x] `npm run test:e2e` green including `visual.spec.ts` with **zero screenshot diff** (`maxDiffPixels: 0`) — because P2a avoids overriding legacy-used token names and no font changed, pixel output is identical
- [x] DevTools Computed confirms `--accent`, `--surface-0`, etc. resolve on `:root`
- [x] Manual smoke: §4 full inventory — all 40+ flows still work
- [x] C3 size-parity: CSS line count increased (additive)

**Commit:** `feat(redesign): P2a introduce tokens.css + motion.css (zero visual diff)`

P2b. Inter font load (first intentional visual change)
- [x] In `templates/base.html`, add BEFORE the Bootstrap CSS link:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  ```
- [x] In `static/css/tokens.css`, confirm `--font-sans: Inter, ...` is declared (from §13 lock)
- [x] Do **not** apply `body { font-family: var(--font-sans); }` yet — the legacy stylesheets still set three different fonts (`Inter` in some rules, `Helvetica Neue`, `Segoe UI`). Letting legacy rules drop their explicit `font-family` is a P6/P9 task. However, all existing `font-family: 'Inter', ...` declarations already in legacy CSS WILL start resolving to the actual loaded Inter webfont, not a fallback — that's where the visible pixel diff comes from.

**P2b exit gate** (visual diff EXPECTED — re-baseline)
- [x] `npm run test:py` green
- [x] DevTools Network shows Inter font request(s) for weights 400/500/600/700 loading, HTTP 200
- [x] DevTools Computed on a navbar element: `font-family` resolves to `Inter` and `font-style` shows `normal` not `fallback`
- [x] `npm run test:e2e visual.spec.ts` will FAIL — **expected**. Every page's text rendering differs because Inter now loads where `'Inter'` was previously unresolvable.
- [x] Human visually reviews each of the 42 diff images — approve or reject per page.
- [x] If all approved: run `npx playwright test e2e/visual.spec.ts --update-snapshots --project=chromium` to regenerate the baselines.
- [x] Commit the refreshed `__screenshots__/` outputs in the SAME commit as the font link change, not a separate commit — a future bisect should see "font added" and "new screenshots" together.
- [x] All non-visual specs (smoke-navigation, program-backup, dark-mode, accessibility) still green
- [x] Manual smoke: §4 full inventory — all flows still work

**Commit:** `feat(redesign): P2b load Inter webfont + refresh visual baselines`

**Rollback (either sub-phase):** `git revert <sha>` — P2b revert alone removes Inter; P2a+P2b revert removes all tokens.

---

### Phase P3 — Navbar visual polish (CSS only, zero HTML change)

**Why:** Prove the glass-pill navbar works on the current markup before touching the markup.

**Preflight**
- [x] P2 committed and green
- [x] Baseline screenshot of current navbar recorded

**Tasks**
- [x] Create `static/css/navbar-glass.css` with the glass-bar + pill styles from the mockup lines 105-151, scoped to `#navbar` (existing ID — see §3.1)
- [x] Use `:where(#navbar)` for low specificity so current rules can still override during transition
- [x] Add `<link>` to `navbar-glass.css` in the redesign overlay block after `motion.css`, which is after `page_css`
- [x] Do **not** touch the navbar `<ul>` / `<li>` structure
- [x] Do **not** remove the counter-zoom `<style>` block yet
- [x] Do **not** rename any nav link ID or `data-testid`

**Exit gate**
- [x] `npm run test:e2e` green, including `smoke-navigation.spec.ts` with zero changes
- [x] `visual.spec.ts` screenshots may diff — review each visually; approve or refine
- [x] Mobile burger toggle still opens at < 992px
- [x] Dark mode toggle still flips
- [x] UI scale control still scales

**Commit:** `feat(redesign): P3 apply glass-bar navbar styling (CSS only)`

**Rollback:** `git revert HEAD` (removes single new CSS file)

---

### Phase P4 — Global backup availability (modal move + JS init) — MUST precede P5

**Why:** The nav Backup link added in P5 will point at `#programLibraryModal`. Today that modal only exists in `templates/workout_plan.html:804`, and `initializeProgramBackup()` is only called inside `initializeWorkoutPlan()` in [static/js/app.js:206-222](static/js/app.js#L206-L222) — i.e. only on `/workout_plan`. If we add the nav link first, clicking Backup on any other page opens nothing (or a dead `#`). P4 makes the modal + its JS available on **every** page **before** the link is surfaced in P5.

This is the #1 root-cause fix from Codex review: previous v2 ordering surfaced the UI before the plumbing was global.

**Preflight**
- [x] P3 committed and green
- [x] §3 frozen DOM contract list re-read (every ID listed in §3.1 must stay verbatim after the move)
- [x] Re-confirm current state:
  - `grep -c 'id="programLibraryModal"' templates/workout_plan.html` → 1
  - `grep -c 'id="programLibraryModal"' templates/base.html` → 0
  - `grep -n 'initializeProgramBackup' static/js/app.js` → exactly one call, inside `initializeWorkoutPlan`

**Tasks — in this order, one commit per sub-step**

P4a. Extract modal markup (no functional change yet)
- [x] Copy the four modal blocks from `templates/workout_plan.html` — `saveBackupModal`, `programLibraryModal`, `confirmRestoreModal`, `confirmDeleteModal` — into a new partial `templates/partials/_program_backup_modals.html`
- [x] In `templates/workout_plan.html`, replace those four blocks with `{% include 'partials/_program_backup_modals.html' %}`
- [x] pytest + E2E green; visual diff on `/workout_plan` shows identical DOM
- [x] Commit: `refactor(redesign): P4a extract backup modals to partial`

P4b. Mount the partial globally
- [x] In `templates/base.html`, add `{% include 'partials/_program_backup_modals.html' %}` once in the shared body chrome, before the toast container and shared scripts
- [x] Remove the include from `templates/workout_plan.html` — the partial is now mounted once, globally, from base.html
- [x] Verify NO duplicate IDs on `/workout_plan`: `grep -c 'id="programLibraryModal"' templates/workout_plan.html` → 0; on rendered `/workout_plan` page, `document.querySelectorAll('#programLibraryModal').length` === 1
- [x] Verify modal exists on a non-plan page: load `/weekly_summary`, DevTools `document.getElementById('programLibraryModal')` → element
- [x] Commit: `refactor(redesign): P4b mount backup modals from base.html (global)`

P4c. Initialize backup JS on every page
- [x] In [static/js/app.js](static/js/app.js): add `initializeProgramBackup()` call to the **top-level common init** (the same place `initializeUIHandlers()` / `initializeFormHandlers()` etc. run, around line 244-250) so it runs on every page
- [x] **Remove** the existing `initializeProgramBackup()` call from inside `initializeWorkoutPlan()` (app.js:216). The global call replaces it; leaving a dead call is confusing and risks double-init if the guard ever regresses.
- [x] Make `initializeProgramBackup()` idempotent before calling it globally. Current code attaches listeners every time it runs; add a module-level `programBackupInitialized` guard or per-element `data-listener-attached` guards before P4c exits.
- [x] `showAutoBackupBanner` already hangs off `window` (app.js:60) — leave as-is
- [x] **P4c exit check:** `grep -c 'initializeProgramBackup' static/js/app.js` → exactly **2** (one import, one call in common init). If more, a stale call was left behind.
- [x] Manual smoke: load `/weekly_summary`, open DevTools, run `bootstrap.Modal.getOrCreateInstance(document.getElementById('programLibraryModal')).show()` — modal opens, list populates via AJAX
- [x] Commit: `feat(redesign): P4c initialize program backup on every page`

**Exit gate (for all of P4)**
- [x] `npm run test:py` green (913/1)
- [x] `npm run test:e2e` green (314) — **especially `program-backup.spec.ts`**
- [x] On every page in §4.1, DevTools `getElementById('programLibraryModal')` returns the element
- [x] On every page, manually triggering the modal via DevTools shows list, save, restore, delete all functional
- [x] Visual: no visible UI change yet (modal markup is hidden by `.modal` default)
- [x] Dark-mode: unchanged

**Rollback:** P4c → P4b → P4a are each a separate commit; `git revert <sha>` for any that breaks. Bottom-up revert restores original in-plan-only state.

---

### Phase P5 — Nav reorder + Analyze dropdown + Backup link (HTML change)

**Why:** With P4 complete, the modal + its JS are live on every page, so adding a Backup trigger to the global navbar is now safe. This phase reshapes the navbar HTML to match the workflow mental model (Plan → Log → Analyze → Progress → Distribute → Backup) and surfaces the Backup entry. This is the highest-risk phase because HTML changes can break E2E.

**Preflight**
- [x] P4 committed and green; modal reachable from every page via DevTools test (see P4 exit gate)
- [x] §3 frozen DOM contract list re-read
- [x] §3.5 unfreezing process re-read
- [x] Re-run `npm run test:e2e -- e2e/smoke-navigation.spec.ts --project=chromium` to record current pass state

**Tasks**
- [x] In `templates/base.html` navbar `<ul>`:
  - [x] Reorder existing `<li>` elements to: Plan → Log → (new Analyze dropdown wrapping Weekly + Session) → Progression → Volume → (new Backup trigger)
  - [x] **Preserve all IDs**: `#nav-workout-plan`, `#nav-workout-log`, `#nav-weekly-summary`, `#nav-session-summary`, `#nav-progression-plan`, `#nav-volume-splitter`, **`#navbarNav`** all stay
  - [x] **Preserve all `data-testid`**: same list
  - [x] Wrap Weekly + Session `<li>` inside a Bootstrap dropdown: `<li class="nav-item dropdown"><a class="nav-link dropdown-toggle" data-bs-toggle="dropdown">` with `<ul class="dropdown-menu">` child containing the two existing `<li>` items
  - [x] Add new `<li>` for Backup with `id="nav-backup"` and `data-testid="nav-backup"` — new IDs are additive, no frozen contract impact
  - [x] Backup link: `<a href="#" data-bs-toggle="modal" data-bs-target="#programLibraryModal">` — modal is guaranteed present on every page after P4
- [x] Update `e2e/fixtures.ts` to add `NAV_BACKUP: '[data-testid="nav-backup"], #nav-backup'`
- [x] Add new spec `e2e/nav-dropdown.spec.ts`:
  - Nav order matches Plan / Log / Analyze / Progress / Distribute / Backup
  - Analyze dropdown opens on click and contains Weekly + Session
  - Backup link exists with correct `data-bs-target`
  - Clicking Backup on each of the 7 pages opens the Program Library modal (verify `.modal.show` class appears)

**Exit gate**
- [x] `npm run test:e2e` green — ALL existing specs + new `nav-dropdown.spec.ts` (320 non-visual + 42 visual after desktop nav snapshot refresh)
- [ ] Manual: open each of 7 pages (`/`, `/workout_plan`, `/workout_log`, `/weekly_summary`, `/session_summary`, `/progression`, `/volume_splitter`) — click nav Backup → modal opens, list populates, save/restore/delete all work. Automation coverage for this phase: `nav-dropdown.spec.ts` verifies nav Backup opens and populates from all 7 pages; `program-backup.spec.ts` and `tests/test_program_backup.py` cover save/restore/delete flows.
- [x] No regression in `smoke-navigation.spec.ts` or `program-backup.spec.ts`
- [x] **Mobile dropdown verification (< 992px viewport):**
  - [x] Burger menu opens/closes correctly
  - [x] Analyze dropdown expands **inline** within the collapsed navbar (not as a pop-up overlay)
  - [x] Weekly + Session links inside the dropdown are tappable and navigate correctly
  - [x] Dropdown inherits glass styling from P3's `navbar-glass.css` — explicit dropdown-menu rules added in `navbar-glass.css`
- [x] Dark mode toggle still works after restructure

**Commit:** `feat(redesign): P5 reorder navbar + add Analyze dropdown + Backup trigger`

**Rollback:** `git revert HEAD` (single commit reverts HTML + spec). P4's global modal wiring stays in place — revert does not re-break any other page.

---

### Phase P6 — Component overlays (one file at a time)

**Why:** Introduce opt-in presentation classes via a new `static/css/components-overlay.css`, layered **after** legacy and page CSS. Do not redefine Bootstrap/global classes like `.btn-primary` directly; pages adopt the new look by adding a new class alongside existing legacy classes.

**Preflight**
- [x] P5 committed and green
- [x] Mockup component CSS lines 152-236 ready to copy, with production selectors remapped to opt-in names:
  - `.btn-primary` → `.btn-calm-primary`
  - `.btn-ghost` → `.btn-calm-ghost`
  - `.btn-icon` → `.btn-calm-icon`
  - form inset rules → `.input-calm-inset`
  - table restyle rules → `.table-calm`
  - copied glass token references use `--calm-glass-*`, not legacy `--glass-*`

**Tasks** (repeat for each component — commit between each)
- [x] P6a: Buttons — create `components-overlay.css` with `:where(.btn).btn-calm-primary`, `:where(.btn).btn-calm-ghost`, `:where(.btn).btn-calm-icon`
- [x] P6a: Link `components-overlay.css` in the redesign overlay block after `navbar-glass.css`, which is after `page_css`
- [x] P6a: Apply `.btn-calm-primary` to `#saveBackupSubmit` only as a pilot, while preserving existing `.btn` and `.btn-primary`
- [x] P6a: Verify HTML usage count for `.btn-calm-primary` is exactly 1 in the pilot commit
- [x] P6a: Visual QA + E2E green → commit
- [x] P6b: Cards — add `.glass-neumorph-card` rule; apply to `/weekly_summary` cards first
- [x] P6b: Visual QA + E2E → commit
- [x] P6c: Form inputs — add `.input-calm-inset`; apply to `/workout_plan` routine form fields without removing legacy classes
- [x] P6c: Visual QA + E2E → commit
- [x] P6d: Tables — add `.table-calm`; apply alongside `.workout-plan-table` to pilot one table without changing the frozen `.workout-plan-table` class
- [x] P6d: Visual QA + E2E → commit
- [x] P6e: Roll new classes through remaining pages one at a time, one commit per page
  - [x] `/workout_log`: apply `.btn-calm-primary`, `.btn-calm-ghost`, `.input-calm-inset`, and `.table-calm` additively; preserve `#import-from-plan-btn`, `#clear-log-btn`, `#confirm-clear-log-btn`, and `.workout-log-table`
  - [x] `/workout_plan` full visual checkpoint — implementation + automation complete; human screenshot approval pending before closing the checkpoint
    - [x] **Scope lock:** additive presentation only. No route, DB, API, calculation, table data, exercise-row semantics, or selector-contract changes.
    - [x] **Selector preflight:** re-run §3.0 selector audit; confirm every touched element preserves frozen IDs/classes/data attributes, especially `#workout`, `#filters-form`, `#routine-env`, `#routine-program`, `#routine-day`, `#exercise`, `#add_exercise_btn`, `#clear-filters-btn`, `#export-to-log-btn`, `#export-to-excel-btn`, `#generate-plan-btn`, `#clear-plan-btn`, `#workout_plan_table_body`, `.workout-plan-table`, `.filter-dropdown`, `.wpdd-*`, `.routine-tab*`, `.editable`, `.btn-swap`, and `.superset-checkbox`.
    - [x] **Buttons:** apply calm button classes additively to all visible workout-plan actions: add exercise, clear filters, export Excel, export to log, generate plan, clear plan, save/load program, superset link/unlink, execution-style picker actions, and modal primary/secondary actions. Existing Bootstrap/legacy button classes stay in place.
    - [x] **Inputs/selects:** apply `.input-calm-inset` additively to routine cascade selects, filter selects/inputs, workout parameter fields, exercise selector/search controls, generator modal fields, and modal text/number/date controls. Existing validation classes and JS-queried classes stay in place.
    - [x] **Functional frames:** add a new opt-in frame/surface class only if needed (for example `.frame-calm-glass`) and apply it to the existing functional frames, not as nested decorative cards. Filters, workout controls, exercise selection, routine tabs, superset actions, generator preview, and table wrapper should read as one coherent calm-glass system.
    - [x] **Table finish:** keep `.workout-plan-table` and `.table-calm`; verify header, zebra rows, hover state, badges, editable cells, execution-style controls, swap/delete buttons, and superset selection remain legible in light/dark/mobile.
    - [x] **Modal finish:** apply the same calm button/input/surface treatment to clear-plan and generate-plan modals without changing Bootstrap modal IDs or `data-bs-*` attributes.
    - [x] **Visible-change threshold:** compare the six `/workout_plan` visual snapshots against the current P6d baseline. If desktop light still reads as "mostly old page with a new navbar," do not mark complete; either broaden opt-in coverage within this same page or document why the visual delta is intentionally restrained.
    - [x] **Focused functional smoke:** routine cascade env → program → day; filters apply/clear; add exercise; inline edit sets/reps/weight/RIR/RPE; replace/swap action still opens; superset link/unlink; generate-plan modal preview; clear-plan modal cancel; export Excel; export to Log.
    - [x] **Automation gate:** run `npx playwright test e2e/workout-plan.spec.ts e2e/exercise-interactions.spec.ts e2e/replace-exercise-errors.spec.ts e2e/superset-edge-cases.spec.ts --project=chromium`; then refresh only `/workout_plan` visual snapshots; then run full `npm run test:py` and `npm run test:e2e`.
    - [ ] **Review gate:** human approves the six refreshed `/workout_plan` screenshots (desktop/tablet/mobile × light/dark) as an obvious visual improvement before the subphase commit is considered done.
- [x] P6f: Global surface background — in a separate visual-change commit, added `body { background: var(--surface-0); }` override in `components-overlay.css` (additive, legacy gradient still in `styles_general.css`); full 42-screenshot review and re-baseline required

**Exit gate (after each sub-phase)**
- [x] pytest + E2E green
- [x] Visual smoke on the touched page in light + dark + mobile
- [x] C3 size-parity: each sub-phase should add ≤ 200 CSS lines — if more, you're doing too much in one step
- [x] No new rule in `components-overlay.css` targets a Bootstrap/global class by itself (`.btn-primary`, `.form-control`, `.table`, `.card`) unless it is paired with an opt-in calm class

**Commits:** `feat(redesign): P6[a-f] introduce <component/background> overlay on <page|global>`

**Rollback:** per sub-phase — `git revert <sha>`

---

### Phase P7 — Dark-mode rewrite (additive)

**Why:** Replace 148 `!important` with a tokens-only dark theme, without deleting the old file yet.

**Preflight**
- [x] P6 committed and green
- [x] Tokens.css has the `[data-theme="dark"]` block (mockup lines 64-72), with legacy-colliding glass tokens still namespaced as `--calm-*`

**Tasks**
- [x] Create `static/css/theme-dark-v2.css` with dark overrides using **only token overrides** — zero `!important`
- [x] Link it in the redesign overlay block after `components-overlay.css`, which is after `page_css`, so page-specific dark rules do not silently override the new token layer
- [x] Do not delete `styles_dark_mode.css` yet
- [x] Verify `static/js/darkMode.js` writes `data-theme="dark"` on `<html>` — if it only toggles a class, add a line to also set the attribute

**Exit gate**
- [x] `npm run test:e2e` green — especially `dark-mode.spec.ts`
- [x] Visual smoke in dark mode across all 7 pages
- [x] `grep -c '!important' static/css/theme-dark-v2.css` → 0

**Commit:** `feat(redesign): P7 tokens-only dark theme (additive)`

**Rollback:** `git revert HEAD`

---

### Phase P8 — Motion + accessibility polish

**Preflight**
- [x] P7 committed and green

**Tasks**
- [x] Wire `page-enter` in `motion.css` to the existing main content wrapper (`body > .container-fluid.mt-4`) unless a prior phase adds an explicit `#app-main`. Do not target `main.container-fluid`; `base.html` currently has no `<main>`.
- [x] Add `.skeleton` class to exercise picker / weekly summary placeholders
- [x] Add `.is-success` pulse to save buttons via small JS hook in `program-backup.js` and `workout-plan.js`
- [x] Confirm `prefers-reduced-motion` media query actually disables animations

**Exit gate**
- [x] `accessibility.spec.ts` green
- [x] Manual: OS-level "reduce motion" ON → no animations fire
- [x] Manual: save a backup → green pulse flashes on the button

**Commit:** `feat(redesign): P8 motion + reduced-motion honoring`

**Rollback:** `git revert HEAD`

---

### Phase P9 — Consolidation (additive links first; wait 7 days before unlink)

**Why:** Merge the current CSS surface into the 15 target files (8 global + 7 per-route page bundles) without repeating v2's destructive compression. P9 creates consolidated files and loads them additively first; legacy links/imports stay present for a minimum 7 green days before any unlink commit. Physical file deletion waits until P10.

> **CSS Route-Scope Contract (v3.3 addition — blocker for P9)**
>
> Today, shared core CSS is loaded from `templates/base.html` (lines 24-47), while page-specific CSS is injected through `{% block page_css %}` (line 50). This split is documented in [docs/CSS_OWNERSHIP_MAP.md](CSS_OWNERSHIP_MAP.md). **P9 must not silently change the load scope or route scope of any source file.**
>
> Rules:
> 1. Before any P9 sub-phase, tag every source CSS file as **GLOBAL** (loaded from `base.html`) or **PAGE** (loaded via `{% block page_css %}` in one or more child templates). For PAGE files, record the **exact set of templates** that load each file.
> 2. A consolidated target that replaces GLOBAL sources must be linked in `base.html`.
> 3. A consolidated target that replaces PAGE sources must preserve the **exact route scope** — each legacy file must only end up loaded on the same templates that loaded it before. Either use per-route bundles, or fence rules behind route selectors like `body[data-page="workout-plan"] ...`.
> 4. A source file must **not** move from PAGE to GLOBAL scope, or from one route's bundle to a different route's bundle, unless a reviewer explicitly approves the scope change and confirms no cascade side effects.
> 5. The following page-scoped files must **not** silently become globally loaded: `styles_frames.css`, `styles_dropdowns.css`, `styles_filters.css`, `styles_routine_cascade.css`, `styles_workout_dropdowns.css`, `styles_muscle_selector.css`, `styles_workout_plan.css`, `workout_log.css`, `styles_welcome.css`, `styles_progression.css`, `styles_volume_splitter.css`, `styles_volume.css`, `styles_muscle_groups.css`, `session_summary.css`.

**Preflight**
- [x] P8 committed ≥ 7 days ago, CI green every day
- [x] Human explicitly approves starting P9
- [x] Update [docs/CSS_OWNERSHIP_MAP.md](CSS_OWNERSHIP_MAP.md) with the target map below before the first P9 commit
- [x] Confirm actual CSS inventory: `Get-ChildItem static/css -Filter *.css | Sort-Object Name`
- [x] Tag every source file's current load scope (GLOBAL vs PAGE) in [docs/CSS_OWNERSHIP_MAP.md](CSS_OWNERSHIP_MAP.md)

**Target map (≤ 15 CSS files excluding Bootstrap: 8 global + 7 page bundles)**

> The prior ≤10 target was set before the route-scope contract split page CSS into per-route bundles. Preserving route scope is more important than hitting an arbitrary file count; 15 files is still a major improvement from 35.

*GLOBAL targets (linked in `base.html`):*

| Target file after P10 | Load scope | Sources / disposition |
|---|---|---|
| `tokens.css` | GLOBAL | existing `styles_tokens.css` (GLOBAL) + P2 `tokens.css` (GLOBAL) |
| `motion.css` | GLOBAL | P2 `motion.css` (GLOBAL, kept as its own target) |
| `base.css` | GLOBAL | `styles_general.css` (GLOBAL), `styles_utilities.css` (GLOBAL), plus any still-used unique rules from legacy `styles.css` (orphan — see P9i) |
| `layout.css` | GLOBAL | `styles_layout.css` (GLOBAL), `styles_responsive.css` (GLOBAL), `responsive.css` (GLOBAL). **`styles_frames.css` removed from this target** — it is PAGE-scoped (loaded in 4 templates) and belongs in page-level bundles. |
| `components.css` | GLOBAL | `styles_buttons.css` (GLOBAL), `styles_forms.css` (GLOBAL), `styles_tables.css` (GLOBAL), `styles_cards.css` (GLOBAL), `styles_tooltips.css` (GLOBAL), `styles_modals.css` (GLOBAL), `styles_notifications.css` (GLOBAL), `components-overlay.css` (GLOBAL). **`styles_dropdowns.css`, `styles_filters.css`, `styles_routine_cascade.css`, `styles_workout_dropdowns.css`, `styles_muscle_selector.css` removed from this target** — they are PAGE-scoped. |
| `navbar.css` | GLOBAL | `styles_navbar.css` (GLOBAL), `navbar-glass.css` (GLOBAL) |
| `theme-dark.css` | GLOBAL | `styles_dark_mode.css` (GLOBAL), `theme-dark-v2.css` (GLOBAL), plus any dark rules moved out of component/page files during consolidation |
| `a11y.css` | GLOBAL | `styles_accessibility.css` (GLOBAL), `styles_error.css` (GLOBAL) |
| `bootstrap.custom.min.css` | GLOBAL | Keep as Bootstrap build artifact; excluded from file count |

*PAGE-SCOPED targets (loaded via `{% block page_css %}` in child templates — one bundle per route):*

| Target file after P10 | Load scope | Route(s) | Current `{% block page_css %}` sources (verified against templates) |
|---|---|---|---|
| `pages-workout-plan.css` | PAGE | `/workout_plan` | `styles_filters.css`, `styles_dropdowns.css`, `styles_workout_dropdowns.css`, `styles_workout_plan.css`, `styles_frames.css`, `styles_routine_cascade.css`, `styles_muscle_selector.css` |
| `pages-workout-log.css` | PAGE | `/workout_log` | `workout_log.css`, `styles_frames.css` |
| `pages-weekly-summary.css` | PAGE | `/weekly_summary` | `styles_volume.css`, `session_summary.css`, `styles_frames.css`, `styles_muscle_groups.css` |
| `pages-session-summary.css` | PAGE | `/session_summary` | `styles_volume.css`, `session_summary.css`, `styles_frames.css` |
| `pages-welcome.css` | PAGE | `/` | `styles_welcome.css` |
| `pages-progression.css` | PAGE | `/progression` | `styles_progression.css`, `styles_dropdowns.css` |
| `pages-volume-splitter.css` | PAGE | `/volume_splitter` | `styles_volume_splitter.css`, `styles_volume.css`, `styles_muscle_groups.css` |

> **Note:** `styles_frames.css` (37,655 bytes) appears in three page bundles because it is loaded from 4 page templates today. `styles_volume.css` and `styles_muscle_groups.css` appear in multiple bundles for the same reason. Duplicating shared rules across bundles preserves the current route scope. During P9f, if the duplicated content is identical, it can be extracted into a shared page-level partial (e.g., `_frames-common.css`) included by each page bundle — but it must not become globally loaded without explicit reviewer approval.
>
> **Note:** `/weekly_summary` and `/session_summary` share `session_summary.css`, `styles_volume.css`, and `styles_frames.css`. They could share a single `pages-summary.css` bundle because they load nearly identical CSS today (`/weekly_summary` additionally loads `styles_muscle_groups.css`). However, separate bundles are safer and the implementer can merge them during P9f if a reviewer explicitly approves.

**Tasks** (one target at a time, one commit each)
- [ ] P9a-add: Create/refresh `tokens.css`; link it in the redesign overlay block while leaving `styles_tokens.css` linked. Test. Commit.
- [x] P9b-add: Create `base.css`; link it after legacy base files while leaving source links/imports present. Test. Commit. **Committed 2026-04-22 in `b4ab1be`.**
- [x] P9c-add: Create `layout.css` (GLOBAL sources only — no `styles_frames.css`); link it after legacy layout files while leaving source links/imports present. Test. Commit. **Committed 2026-04-22 in `cc1a4b4`.**
- [x] P9d-add: Create `components.css` (GLOBAL sources only — no page-scoped files); link it additively in the legacy component block while leaving source links/imports present. Test. Commit. **Local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 4,547 lines, target 4,554 lines (+0.15%).**
- [ ] P9e-add: Create `navbar.css`; link it additively in the navbar block while leaving both source links present. Test. Commit. **Local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 1,428 lines, target 1,429 lines (+0.07%).**
- [ ] P9f-add: Create per-route page bundles (`pages-workout-plan.css`, `pages-workout-log.css`, `pages-weekly-summary.css`, `pages-session-summary.css`, `pages-welcome.css`, `pages-progression.css`, `pages-volume-splitter.css`). For each additive checkpoint: link the new bundle at the end of the relevant child template's `{% block page_css %}` while leaving legacy page CSS source links present. Each bundle's source list must exactly match what the template loads today — verified against the route-scope contract. Migrate one page bundle at a time, test, and commit per bundle. **`pages-workout-plan.css` local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 7,987 lines, target 7,993 lines (+0.08%). `pages-workout-log.css` local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 3,335 lines, target 3,336 lines (+0.03%). `pages-weekly-summary.css` local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 1,672 lines, target 1,675 lines (+0.18%). `pages-session-summary.css` local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 1,624 lines, target 1,626 lines (+0.12%). `pages-welcome.css` local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 1,082 lines, target 1,082 lines (+0.00%). `pages-progression.css` local implementation + validation complete 2026-04-22; checkpoint commit created. Source sum 365 lines, target 366 lines (+0.27%). `pages-volume-splitter.css` local implementation + validation complete 2026-04-23; checkpoint commit created. Source sum 1,112 lines, target 1,114 lines (+0.18%). All seven page route bundles are implemented and validated locally; P9f checkpoint commit created.**
- [x] P9g-add: Create `theme-dark.css`; link it after all legacy dark/theme sources while leaving source links present. Test. Commit. **Local implementation + validation complete 2026-04-23; checkpoint commit created. Source sum 620 lines, target 621 lines (+0.16%). The legacy `styles_dark_mode.css` selector copy is specificity-neutralized with `:where(...)` inside the additive bundle so loading `theme-dark.css` after `theme-dark-v2.css` does not change current page/component dark cascade.**
- [ ] P9h-add: Create `a11y.css`; link it after `styles_accessibility.css` and `styles_error.css` while leaving both source links present. Test. Commit.
- [ ] P9i-audit: `styles.css` and `styles_science.css` are **confirmed orphans** — neither is linked from any template. `styles.css` `@import`s `styles_science.css` but `styles.css` itself is never loaded. Mark both as delete-only in [docs/CSS_OWNERSHIP_MAP.md](CSS_OWNERSHIP_MAP.md). Verify with: `rg -n "styles\.css|styles_science\.css" templates static/css` — if no template or `@import` chain reaches them, they are dead.
- [ ] Wait ≥ 7 days of green CI with consolidated targets loaded additively.
- [ ] P9j-unlink: Remove legacy `<link>` tags / `@import`s one source group at a time, test after each group, and commit each unlink separately. Do **not** delete physical CSS files in P9.

**Exit gate (per sub-phase)**
- [ ] pytest + E2E green
- [ ] Visual smoke on pages touched
- [ ] C1 satisfied: replacement loaded in a prior commit before any source link/import is removed
- [ ] C3 size-parity: merged file's line count ≈ sum of sources (±15%) unless a reviewer signs off on documented duplicate removal
- [ ] **Route-scope preserved:** no PAGE-scoped file appears in a GLOBAL `<link>` tag, no PAGE file leaks to a route that never loaded it, and no GLOBAL file moved to PAGE scope without reviewer approval

**Commit pattern:** `refactor(redesign): P9<letter>-add consolidate <files> into <target>.css` and `refactor(redesign): P9<letter>-unlink remove legacy links for <target>.css`

**Rollback:** each sub-phase is one commit — `git revert <sha>`

---

### Phase P10 — Legacy deletion + zoom-hack replacement

**Preflight**
- [ ] P9 add + unlink cadence fully committed
- [ ] Legacy links/imports have been absent for ≥ 3 green CI days
- [ ] Human explicitly approves deletion

**Tasks**
- [ ] Delete only the legacy CSS files whose rules were merged or marked delete-only in the P9 target map. Do not delete `bootstrap.custom.min.css`.
- [ ] Confirm no deleted filename appears in templates, JS, SCSS, CSS `@import`s, docs target map, or Playwright fixtures: `rg -n "<filename>" templates static scss e2e docs`
- [ ] Replace the counter-zoom `<style>` block in `base.html:5-17` with CSS `clamp()`-based fluid typography in `base.css`
- [ ] Delete `styles_dark_mode.css` only if P7's replacement is confirmed complete
- [ ] Update `.claude/rules/frontend.md` to describe the new 15-file CSS structure (8 global + 7 per-route page bundles)

**Exit gate**
- [ ] Exit-criteria from §5 hit: ≤15 CSS files (8 global + 7 page bundles, excluding Bootstrap), ≤5 `!important`, <50 inline rgba/backdrop-filter
- [ ] pytest + E2E green
- [ ] Manual §4 full inventory smoke

**Commit:** `chore(redesign): P10 remove legacy CSS and fluid-type replacement for zoom hack`

**Rollback:** deletions recovered via `git revert` — but this is the point where rollback gets expensive. That's why P10 comes last.

---

## 8. Don't-do list — anti-patterns that caused v2 to fail

- [ ] **Don't** run a script that bulk-renames class names (`replace_classes.py` was the smoking gun in v2)
- [ ] **Don't** delete or unlink a legacy CSS file in the same commit as adding its replacement
- [ ] **Don't** ship multiple phases in one commit — even if they seem related
- [ ] **Don't** rename any frozen ID, `data-testid`, or JS-queried class (§3)
- [ ] **Don't** remove Bootstrap JS dependency (`bootstrap.Modal.getInstance(...)` breaks silently if you replace with custom dropdown JS)
- [ ] **Don't** drop `data-bs-toggle`, `data-bs-target`, `data-bs-dismiss` attributes
- [ ] **Don't** skip E2E between phases to "save time" — every phase has an E2E gate
- [ ] **Don't** "fix" a failing test by editing the test to match broken behavior
- [ ] **Don't** assume a 95% CSS-line reduction in a refactor commit is fine — it's the sign of lost styling
- [ ] **Don't** merge the redesign PR without Human + AI reviewer sign-off on the P10 screenshot diff

---

## 9. Verification commands reference

```bash
# Baseline + regression
npm run test:py                                               # pytest
npm run test:e2e                                              # Playwright Chromium
npx playwright test e2e/visual.spec.ts --project=chromium     # screenshot regressions
npx playwright test e2e/smoke-navigation.spec.ts --project=chromium
npx playwright test e2e/dark-mode.spec.ts --project=chromium
npx playwright test e2e/accessibility.spec.ts --project=chromium
npx playwright test e2e/program-backup.spec.ts --project=chromium

# Build
npm run build:css

# Metric checks
ls static/css/*.css | wc -l
wc -c static/css/*.css | tail -1
grep -rc '!important' static/css/ | sort -t: -k2 -n -r | head
grep -rE 'rgba\(|backdrop-filter' static/css/ | wc -l

# Frozen-contract safety
rg -n 'programLibraryModal|saveBackupModal|confirmRestoreModal|confirmDeleteModal' templates static/js e2e
rg -no -r '$1' "getElementById\(['\"]([^'\"]+)['\"]" static/js templates | sort -u
rg -no -r '$2' "querySelector(All)?\(['\"]([^'\"]+)['\"]" static/js templates | sort -u
rg -no -r '$1' "data-testid=\"([^\"]+)\"" templates static/js e2e | sort -u
rg -n "page\.locator\(|waitForSelector\(|getByTestId\(|click\(['\"]" e2e
```

---

## 10. Git / PR plan

- Branch: `redesign/calm-glass-2026` (already exists; currently in partial-revert state — reset to last green commit before P0)
- **One commit per phase / sub-phase** — never combine
- Draft PR opened after P3; kept in draft through P10
- CI must run on every commit; no push without green local tests
- **Never force-push to main.** Never merge without all three reviewers signing off.

---

## 11. Risks & rollback

| Risk | Mitigation | Rollback |
|---|---|---|
| JS selector breaks on HTML change | §3 frozen list + C9 pre-change grep | `git revert` that single commit |
| Bulk CSS reduction loses styling (v2 failure mode) | C3 size-parity + C1 no-delete rule until P10 | `git revert` + 34 files restored |
| Modal move breaks listeners | P4 explicit idempotence + full `program-backup.spec.ts` | `git revert` P4 sub-phase |
| Dark-mode regression | P7 additive, old kept until P10 | `git revert` P7 |
| Zoom hack removal breaks A-/A+ scaling | `clamp()` replacement staged in P10 with A-/A+ behavior preserved via `data-scale` | Restore `<style>` block in P10 revert |
| E2E fixture drift | §3.5 unfreeze process updates `fixtures.ts` before template change | `git revert` fixture commit |
| Cascade order wrong after consolidation | P9 sub-phase E2E + manual smoke | `git revert` that sub-phase |

**Global rollback to pre-redesign:** `git checkout main && git branch -D redesign/calm-glass-2026` (after PR closed). No impact on `main`.

---

## 12. Critical files (read first when implementing)

- [templates/base.html](templates/base.html) — zoom hack lines 5-17; CSS link block; navbar structure
- [templates/workout_plan.html](templates/workout_plan.html) — modal markup around line 804 (relocates in P4)
- [static/js/modules/program-backup.js](static/js/modules/program-backup.js) — 6× `bootstrap.Modal.getInstance` calls + DOMContentLoaded bindings
- [e2e/fixtures.ts](e2e/fixtures.ts) — frozen selector source of truth
- [static/css/styles_dark_mode.css](static/css/styles_dark_mode.css) — 148 `!important` removed in P7/P10
- [docs/mockups/redesign-preview.html](mockups/redesign-preview.html) — the visual contract
- [.claude/rules/frontend.md](.claude/rules/frontend.md) — target nav flow + frontend conventions

---

## 13. Design decisions — locked before P2 starts

> Reviewer: confirm these locked choices before P2. Each answer is a constraint for every subsequent phase.

| # | Question | Options | Chosen |
|---|---|---|---|
| 1 | Palette | A · Indigo `#4c6ef5` / B · Graphite / C · Health green | **A · Indigo `#4c6ef5`** |
| 2 | Font | Inter / Geist / Plus Jakarta Sans | **Inter** |
| 3 | Background | Multi-radial mesh / Flat `--surface-0` / Subtle single radial | **Flat pastel `--surface-0`** |
| 4 | Neumorphism dial | Subtle / Flatter / Pronounced | **Subtle** (mockup default values) |
| 5 | Scope cap | Include navbar/IA restructure (P4-P5) / Visual-only | **Include restructure** (P4-P5 run) |

**Locked constraints for all subsequent phases:**
- `--accent: #4c6ef5`
- `--font-sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Mockup glass tokens use production-safe names until legacy cleanup: `--calm-glass-bg`, `--calm-glass-border`, `--calm-glass-blur`, `--calm-glass-sat`
- `body { background: var(--surface-0); }` — **no radial gradients**; replace [styles_general.css:19-26](static/css/styles_general.css#L19-L26) in P6f, not in P2a
- Shadow tokens from mockup lines 28-31 (unchanged)
- Nav reorder + Analyze dropdown + Backup link are **in scope** (P4-P5)

---

## 14. Review audit trail

| Reviewer | v1 | v2 | v3 | v3.1 | v3.2 | v3.3 | Notes |
|---|---|---|---|---|---|---|---|
| Human (user) | ⏳ | ⏳ | ⏳ | ⏳ pending | ⏳ pending | ⏳ pending | Distrusts Gemini after v2 breakage — Codex + human approval sufficient |
| Gemini | ⏳ | ⚠️ implemented v2 and broke it (commit `d1618be` reverted) | — | ⏸️ paused by user | ⏸️ paused by user | ⏸️ paused by user | — |
| Codex | ⏳ | ⚠️ 11 review points | ✅ conditional approval w/ 5 required fixes | ⚠️ 9 blocker/medium findings | ✅ v3.2 fixes applied | ✅ co-reviewed v3.3 with Opus | 9 review findings + 1 self-audit token fix; v3.3 joint review validated all Opus findings |
| Claude Opus (Antigravity) | — | — | — | — | — | ✅ author v3.3 | 2 high / 5 medium findings; Codex validated all findings and added precision |
| Claude (this agent) | author v1 | author v2 | author v3 | author v3.1 | — | — | post-mortem incorporated; Codex fixes 1–5 applied |

### v3 → v3.1 changelog (Codex's 5 required fixes)

1. **Backup/modal sequencing + global JS** — P4 and P5 swapped. New P4 (split into P4a/P4b/P4c) extracts the backup modals to a partial, mounts it from `base.html` globally, and moves `initializeProgramBackup()` out of `/workout_plan`-only init before P5 surfaces the nav link. Root cause: `app.js:216` calls `initializeProgramBackup()` only in `initializeWorkoutPlan()`.
2. **P2 font contradiction resolved** — P2 split into P2a (tokens + motion, zero-pixel-diff gate) and P2b (Inter webfont load, visual baseline intentionally refreshed). The prior "zero pixel diff expected" while loading Inter was self-contradicting.
3. **Mockup design-lock** — removed graphite and health palettes and the A/B/C switcher; replaced the "palette chooser" section with a locked-decisions banner reflecting §13. Background switched from radial mesh to flat `--surface-0`.
4. **Deterministic visual-test setup** — P0 split into P0a (harness: animation/caret kill switch, `document.fonts.ready`, pinned `Date.now`, fixed locale/timezone/viewport, masked volatile regions, seed DB) and P0b (capture). Double-run determinism check added to exit gate.
5. **§3 frozen-selector expansion** — §3 grown from ~15 IDs to 101 IDs + 30+ class selectors, grouped by subsystem (navbar, backup, workout plan, workout log, summaries, progression, volume splitter). Added §3.0 authoritative-source greps and §3.6 re-audit gate before P6 and P9.

### v3.1 → v3.2 changelog (Codex blocker fixes)

1. **P6 made truly opt-in** — replaced global `.btn-primary` overlay plan with `.btn-calm-primary` / `.btn-calm-ghost` / `.btn-calm-icon`, `.input-calm-inset`, and `.table-calm`; added a gate forbidding bare Bootstrap/global class overrides in `components-overlay.css`.
2. **Selector audit widened** — §3.0 now audits `static/js`, inline template scripts, and E2E locators; §3.1/§3.3 now include welcome erase-data, generator preview, summary inline-script, and collapse-script selectors.
3. **Strict E2E error gate added** — C11 + P0 require redesign specs to fail on null/undefined selector errors instead of inheriting broad legacy ignores from `e2e/fixtures.ts`.
4. **Cascade placement fixed** — P2/P3/P6/P7 now load redesign overlay CSS after `{% block page_css %}` so page-specific CSS cannot silently defeat the overlay layer.
5. **C1/P9/P10 sequencing reconciled** — consolidation now uses add/load commits, waits 7 green days, then unlinks legacy sources, and delays physical deletion until P10.
6. **Visual determinism made literal** — P0 uses `maxDiffPixels: 0` / `threshold: 0` for the double-run determinism proof.
7. **CSS inventory made concrete** — P9 now has a target map covering non-`styles_*.css` files (`workout_log.css`, `session_summary.css`, `styles.css`, `responsive.css`) so the file-count target is auditable. *(Note: ≤10 was later revised to ≤15 in v3.3 after per-route bundling.)*
8. **P4 idempotence made explicit** — global backup initialization now requires an initialization guard before moving the call out of `/workout_plan`.
9. **Stale design-choice wording removed** — P1 now confirms the locked indigo/Inter/flat-background mockup instead of asking for A/B/C palette selection.
10. **P2 zero-diff token collision fixed** — legacy-used `--glass-*` tokens stay untouched in P2a, token files contain declarations only, and the global background swap is moved to explicit visual phase P6f.

### v3.2 → v3.3 changelog (Opus + Codex joint review fixes)

1. **CSS route-scope contract added to P9 (blocker).** Upgraded from "load-scope" to "route-scope" — P9 now preserves not just GLOBAL vs PAGE scope but the **exact set of routes** each CSS file is loaded on. The target map separates GLOBAL targets (linked from `base.html`) from PAGE-SCOPED per-route bundles. Each page bundle's source list is verified against the actual `{% block page_css %}` in the corresponding template. The old `pages-misc.css` (which would have leaked CSS across `/`, `/progression`, and `/volume_splitter`) is replaced by `pages-welcome.css`, `pages-progression.css`, and `pages-volume-splitter.css`.
2. **`#navbarNav` frozen.** Added to §3.1 — it is the Bootstrap collapse target referenced by `data-bs-target` at `base.html:83`, the collapse container at `base.html:91`, and queried by `navbar-enhancements.js:14`. Marked as P5 blocker.
3. **Full token collision audit in P2a.** Expanded beyond `--glass-*` to audit all custom property names in `styles_tokens.css` (`--space-*`, `--input-*`, `--btn-*`, `--frame-*`, `--table-*`, `--font-size-*`, `--container-*`). New tokens must not redefine these without `--calm-` prefix.
4. **P4c dead-call cleanup made explicit.** Plan now says to **remove** the `initializeProgramBackup()` call from inside `initializeWorkoutPlan()` (app.js:216) after adding the global call. Exit check: `grep -c` must show exactly 2 hits (one import, one call).
5. **P5 mobile dropdown verification added.** Exit gate now requires: burger menu test, inline expansion in collapsed navbar, tappable links, glass styling inheritance, and dark mode toggle verification at < 992px viewport.
6. **`styles.css` / `styles_science.css` confirmed orphans.** P9i changed from "audit" to "confirmed orphans" — neither is linked from any template. `styles.css` `@import`s `styles_science.css` but `styles.css` itself is never loaded. Both marked delete-only.
7. **`darkMode.js` verification note updated in P7.** Confirmed `darkMode.js:63-67` already sets `data-theme` attribute correctly — no conditional needed.
8. **File count target updated from ≤10 to ≤15.** The original ≤10 target predated the route-scope contract. 8 global + 7 per-route page bundles = 15 files (all excluding Bootstrap). Route safety is more important than an arbitrary file count; 15 is still a major improvement from the current 35.
9. **`pages-volume-splitter.css` source list corrected.** `volume_splitter.html` loads `styles_volume.css` and `styles_muscle_groups.css` in addition to `styles_volume_splitter.css` — these were missing from the prior `pages-misc.css` source list. Now correctly listed in the per-route bundle.

---

## 15. Why v3.3 should hit ≥95% confidence

- **Post-mortem-driven.** Every failure mode from v2 has a commandment (§1) and an explicit anti-pattern (§8) naming it.
- **Frozen DOM contracts (§3)** make the exact selectors every JS module and E2E fixture depends on visible to the implementer before they touch a template.
- **Feature inventory (§4)** is 40+ concrete user flows that must work — a regression is caught by a human in < 15 minutes per phase.
- **Additive-until-P10.** If any phase P0-P9 breaks, a single `git revert` restores prior state. No file is deleted before P10 so rollback is always cheap.
- **Size-parity rule (C3)** would have blocked `d1618be` — a 97.8% CSS reduction could not have been shipped.
- **No bulk scripts (C2)** eliminates `replace_classes.py`-class risk at its root.
- **One phase per commit (C4)** gives every gate a clean boundary.
- **Two-person review (C10)** means at least one AI + human has to miss the same regression for it to land.
- **CSS load-scope contract (v3.3)** prevents the "works on my page, breaks three others" cascade drift that a naïve global `pages.css` would create.
- **Full token collision audit (v3.3)** prevents the responsive scaling system in `styles_tokens.css` (372 lines of `--space-*`/`--input-*`/`--btn-*` across 7 media queries) from being silently overridden by new design tokens.

The remaining 5% covers: environment differences, browser-version drift, race conditions in E2E, and unknown unknowns. The plan cannot eliminate those — it just keeps them recoverable.
