# Code Cleanup & Refactoring Plan

**Project:** Hypertrophy Toolbox v3
**Date:** 2026-04-09
**Scope:** Dead code removal, duplication consolidation, low-risk cleanup, and explicitly deferred semantic changes
**Safety Philosophy:** Every change follows the cycle: capture checkpoint → baseline tests → targeted edit → re-run tests → rollback on failure

** codex 5.4*** The safety loop is right, but I would avoid `git stash push` as the default rollback path in a potentially dirty worktree. For this repo, a safer rule is "capture a patch or commit a checkpoint before risky phases" so unrelated local work does not get buried during cleanup.

### Baseline Test Counts (current snapshot, must be re-recorded)
| Suite | Command | Expected |
|-------|---------|----------|
| pytest | `.venv/Scripts/python.exe -m pytest tests/ -q` | **981 passed, 1 skipped** (validated 2026-04-09 in current repo) |
| Playwright summary surfaces | `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` | **21 passed** (validated 2026-04-09 in current repo) |
| Full Playwright | `npx playwright test` | Latest known green in `docs/archive/DOCS_AUDIT_PLAN.md`; rerun before risky frontend or contract phases |

> **Important:** These counts drift as tests are added/removed. Treat them as a snapshot, not an invariant. Always re-record in this environment before starting. For rollback, prefer a saved patch or checkpoint commit over `git stash push` in a dirty worktree.

** codex 5.4*** I would treat the `Expected` column as a snapshot, not an invariant. Test totals and pass counts drift quickly, so this section should emphasize "record current numbers in this environment" rather than using hardcoded pass counts as success criteria.

---

## Phase 0: Prerequisite Confidence Gate

> **Goal:** Reach ~95% execution confidence before any destructive cleanup starts.
>
> **Phase 0 exit criterion:** Treat this phase as complete only when the checklist evidence supports an estimated ~95% confidence to begin the low-risk cleanup path without functional, UI, flow, or performance regressions.

### 0.1 Checkpoint & Baseline Capture

- [ ] Save a rollback checkpoint before risky edits:
  - [ ] `git status --short | Tee-Object -FilePath cleanup_preflight_status.txt`
  - [ ] `git diff --binary | Out-File -Encoding ascii cleanup_preflight.patch`
- [ ] Re-record full pytest baseline:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath baseline_pytest.txt`
- [ ] Re-record summary-surface browser baseline:
  - [ ] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath baseline_summary_pages.txt`
- [ ] If the upcoming phase touches templates, shared JS, or route contracts, re-record full Playwright first:
  - [ ] `npx playwright test --project=chromium --reporter=line | Tee-Object -FilePath baseline_e2e_full.txt`

### 0.2 Package-Surface Decision (Required before deleting exported utils)

- [ ] Audit package-style imports and references:
  - [ ] `rg -n "from utils import|import utils\.|from utils\.(data_handler|business_logic|helpers|filters|database_init|muscle_group)" app.py routes tests e2e docs CLAUDE.md`
- [ ] Record whether `utils/__init__.py` is treated as:
  - [ ] internal convenience only, or
  - [ ] supported package surface
- [ ] If this decision is not explicit, **do not** delete `utils/data_handler.py` or `utils/business_logic.py`.

### 0.3 Summary-Page Frontend Coupling Audit

- [ ] Document the current ownership of summary-page updates before touching summary templates or JS:
  - [ ] `static/js/app.js`
  - [ ] `static/js/modules/summary.js`
  - [ ] `templates/session_summary.html`
  - [ ] `templates/weekly_summary.html`
  - [ ] `e2e/summary-pages.spec.ts`
- [ ] Confirm which updater path is authoritative for each page during this cleanup cycle.
- [ ] Confirm whether the fallback module in `static/js/modules/summary.js` still depends on the presence of inline page updaters and/or `#counting-mode`.
- [ ] Do not start template dedup or summary-page JS dedup until this ownership note is complete.

### 0.4 Semantic-Change Test Gap Review

- [ ] Before changing the `exercise_order` recalculation loop in `routes/exports.py`, confirm dedicated tests exist for:
  - [ ] successful recalculation
  - [ ] failure / rollback semantics
- [ ] If those tests do not exist, create them first or defer that optimization to the last phase.

### 0.5 Frontend Orphan Audit

- [ ] Audit likely orphan or legacy frontend files before backend cleanup starts:
  - [ ] `static/js/modules/sessionsummary.js`
  - [ ] `static/js/updateSummary.js`
- [ ] Record whether each file is:
  - [ ] live
  - [ ] dormant but intentionally kept
  - [ ] safe delete candidate

### 0.6 Go / No-Go Gate

- [ ] Proceed to Phase 1 only when:
  - [ ] the baseline is green
  - [ ] the package-surface decision is recorded
  - [ ] the summary-page ownership audit is recorded
  - [ ] the semantic-change test gap is closed or explicitly deferred
  - [ ] rollback artifacts exist on disk
- [ ] Treat a passing Phase 0 as authorization to start only the low-risk path first:
  - [ ] `3a`
  - [ ] `3b Wave 1`
  - [ ] `3c`
  - [ ] `3d`
  - [ ] `3e`
  - [ ] `3f`
  - [ ] `3g`
- [ ] Require a second explicit go / no-go decision before:
  - [ ] `3b Wave 2` package-surface contraction
  - [ ] `3j` export write-path semantic optimization

---

## Phase 1: Discovery & Analysis

### 1.1 Tools & Methods

| Tool | Purpose | Command |
|------|---------|---------|
| **vulture** | Detect unused Python code (functions, variables, imports) | `vulture routes/ utils/ --min-confidence 80` |
| **pylint** | Detect unused imports specifically | `pylint --disable=all --enable=W0611 routes/ utils/` |
| **rg** | Trace callers of suspect modules/functions | `rg -n "from utils\.business_logic|import utils\.business_logic|BusinessLogic" routes utils tests app.py` |
| **IDE Find Usages** | Confirm zero callers before deletion (VSCode: right-click → Find All References) | Manual |
| **Template cross-ref** | Find orphaned templates | `rg -n "render_template|include|extends" routes templates` + `Get-ChildItem templates -File` |
| **JS import audit** | Find orphaned JS modules | `rg -n "import .* from|<script" static templates` + `Get-ChildItem static/js -Recurse -File *.js` |

** codex 5.4*** This runbook mixes Windows-only paths like `.venv/Scripts/...` with Unix tooling like `grep`, `find`, `wc`, `ls`, and `xargs`. Since the repo is being worked from PowerShell, I would rewrite these commands to `rg` plus PowerShell equivalents so the plan is executable as written.

### 1.2 Directory Scan Checklist

- [ ] **`routes/`** — Scan all 10 route files for: unused imports, dead functions, raw `print()` calls, inconsistent error response formats
- [ ] **`utils/`** — Scan all utility files for: unused classes/functions, raw `get_db_connection()` usage, raw `print()` calls, stale re-exports
- [ ] **`templates/`** — Cross-reference all 15 templates against `render_template()` calls and `{% include %}` / `{% extends %}` directives
- [ ] **`static/js/modules/` and `static/js/*.js`** — Cross-reference all JS modules against `import` statements in `app.js` and `<script>` tags in templates
- [ ] **`tests/`** — Identify test files that only test dead modules (scheduled for removal alongside module deletion)
- [ ] **`utils/__init__.py`** — Audit every item in `__all__` for actual downstream usage in `routes/` or `tests/`

** codex 5.4*** I would widen this checklist to include top-level `static/js/*.js`, not only `static/js/modules/`. `static/js/modules/sessionsummary.js` looks like a legacy artifact and even contains literal `<script>` tags, while `static/js/updateSummary.js` is also a likely orphan candidate.

---

## Phase 2: Categorization of Issues

### 2.1 Master Issue Table

| # | Issue Type | Impact | Affected Files | Fix Strategy |
|---|-----------|--------|----------------|--------------|
| 1 | **Legacy module / package-surface candidate** | Medium | `utils/business_logic.py` | Only delete after explicit `utils` package-surface decision, route import removal, and paired test/doc cleanup |
| 2 | **Legacy module / package-surface candidate** | Medium | `utils/data_handler.py` | Only delete after explicit `utils` package-surface decision and paired test/doc cleanup |
| 3 | **Dead module** (superseded) | Medium | `utils/database_init.py` | Delete file (superseded by `utils/db_initializer.py`; not imported anywhere) |
| 4 | **Dead module** (deprecated wrapper) | Medium | `utils/filters.py` | Delete file (`ExerciseFilter` class has zero callers; `filter_predicates.py` is canonical) |
| 5 | **Dead module** (legacy, only self-tested) | Medium | `utils/muscle_group.py` | Delete file; delete `tests/test_muscle_group.py` |
| 6 | **Dead module** (redundant re-export shim + broken import) | High | `utils/helpers.py` | Delete file (strict subset of `__init__.py`; imports nonexistent `get_weekly_summary`) |
| 7 | **Stale re-exports** in package init | Low | `utils/__init__.py:7-8, 56-58, 93-99` | Remove `DataHandler`/`BusinessLogic` imports and `__all__` entries; remove duplicate `get_workout_logs()` wrapper |
| 8 | **Unused imports** in routes | Low | `routes/exports.py:1,5-6,9,19` | Remove `make_response`, `sanitize_filename`, `create_content_disposition_header`, `should_use_streaming`, `import logging` |
| 9 | **Unused import** in routes | Low | `routes/weekly_summary.py:8` | Remove `from utils.business_logic import BusinessLogic` |
| 10 | **Orphaned templates** (not rendered by any route) | Low | `templates/dropdowns.html`, `templates/filters.html`, `templates/table.html`, `templates/exercise_details.html`, `templates/debug_modal.html`, `templates/workout_tracker.html` | Delete after confirming no `{% include %}` references |
| 11 | **Duplicated parse functions** (character-identical) | Medium | `routes/session_summary.py:19-30`, `routes/weekly_summary.py:21-32` | Extract shared helpers to `utils/effective_sets.py`, but keep route-level compatibility wrappers or update route tests in the same change |
| 12 | **Duplicated template HTML** (~23 lines after descoping) | Medium | `templates/session_summary.html`, `templates/weekly_summary.html` | Extract `method_selector` only, and only after the summary-page frontend ownership gate is documented |
| 13 | **Volume classifier** — backend duplication only | Low | `utils/volume_classifier.py:10-35` | Backend-only consolidation first; leave template and JS threshold copies untouched this cycle |
| 14 | **N+1 UPDATE loop / semantic change** | High | `routes/exports.py:359-373` | Add dedicated success + rollback tests first; move to the last phase; treat as intentional semantic change |
| 15 | ~~**Raw `get_db_connection()` bypassing DatabaseHandler**~~ | ~~Medium~~ **Resolved** | ~~`utils/volume_export.py:8`, `routes/volume_splitter.py:154,199,234`, `utils/user_selection.py:34`~~ — migrated in DOCS_AUDIT_PLAN Tier 3. **Only** `utils/database_indexes.py:51` remains: intentional raw access with manual `_DB_LOCK` for PRAGMA operations (documented, not a violation). | No further action needed |
| 16 | **`print()` instead of `get_logger()`** (~52 calls across 20 files) | Medium | `utils/muscle_group.py`(8), `utils/user_selection.py`(5), `routes/progression_plan.py`(11), and 10+ others | Replace with `logger.debug/info/warning/error` |
| 17 | **Bloated functions** (>130 lines) | Medium | `routes/exports.py:export_to_excel` (338 lines), `routes/workout_plan.py:replace_exercise` (230 lines), `utils/session_summary.py:calculate_session_summary` (256 lines), `utils/export_utils.py:create_excel_workbook` (227 lines), `utils/progression_plan.py:generate_progression_suggestions` (224 lines) | Extract sub-functions (see Phase 3g) |
| 18 | **Duplicated SQL JOIN** (user_selection + exercises) | Medium | `utils/session_summary.py:55-71`, `utils/weekly_summary.py:62-76`, `utils/data_handler.py:17-38`, `utils/user_selection.py:31` | Only revisit after Wave 1 / Wave 2 deletion decisions settle the remaining live call sites |
| 19 | **Summary-page dual updater ownership** | High | `static/js/app.js`, `static/js/modules/summary.js`, `templates/session_summary.html`, `templates/weekly_summary.html` | Add prerequisite ownership audit; do not refactor summary templates or JS until one active updater path is documented |

** codex 5.4*** Issues `#1`, `#2`, and `#6` do not all have the same confidence level. `utils/helpers.py` is a strong delete candidate because it has no repo callers and imports a nonexistent `get_weekly_summary`, while `utils/data_handler.py` is a thin public facade exported by `utils/__init__.py` and should be treated as an API-surface decision, not just an internal dead-file cleanup.

### 2.2 Code Smell Definitions

| Smell | Description | Detection Method |
|-------|-------------|-----------------|
| **Dead Import** | `import X` or `from X import Y` where `Y` is never referenced in the file | `pylint --enable=W0611` or `vulture` |
| **Dead Module** | Entire `.py` file with zero callers in production code (`routes/`, `app.py`) | `rg -n "from utils\.module_name|import utils\.module_name" routes app.py` returns empty |
| **Orphaned Asset** | Template/JS/CSS file not referenced by any route, `include`, or `import` | Cross-reference `render_template` calls, `{% include %}` directives, and JS `import` statements |
| **Code Duplication** | Identical or near-identical logic in 2+ locations | Manual review; `jscpd` for automated clone detection |
| **N+1 Query** | DB query executed inside a loop, where a single batch query would suffice | Search for `for.*:` followed by `db.execute_query` or `db.fetch_one` within loop body |
| **Bloated Function** | Function exceeding ~80 lines, typically handling multiple concerns | Manual/editor line count on function bodies; functions >130 lines are priority targets |
| **Inconsistent Abstraction** | Using raw `sqlite3.connect()` or `get_db_connection()` instead of `DatabaseHandler` | `rg -n "get_db_connection|sqlite3\.connect" routes utils` |
| **Print-as-Logging** | Using `print()` instead of the project's `get_logger()` pattern | `rg -n "print\(" routes utils -g "*.py"` |

---

## Phase 3: Execution Strategy

> **Golden Rule:** After every discrete change (one file edit or one file deletion), run the relevant test file. After completing each sub-phase, run the full pytest suite. Never batch multiple untested changes.

** codex 5.4*** I like the bias toward small validated steps. One tweak: for deletion phases, define the verification query first, save its output, then delete, then rerun tests. That gives you stronger evidence than "grep came back empty once" when you later review why a file was removed.

### 3a. Remove Unused Imports

**Estimated impact:** ~10 lines removed across 2 files

- [ ] **`routes/exports.py`** — Remove 5 unused imports
- [ ] **`routes/weekly_summary.py`** — Remove dead `BusinessLogic` import
- [ ] Run `pylint --disable=all --enable=W0611 routes/` to confirm clean

#### Before / After: `routes/exports.py`

```python
# BEFORE (lines 1-19)
from flask import Blueprint, Response, jsonify, request, make_response
from utils.export_utils import (
    create_excel_workbook,
    sanitize_filename,
    create_content_disposition_header,
    generate_timestamped_filename,
    stream_excel_response,
    should_use_streaming,
    MAX_EXPORT_ROWS
)
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_weekly_summary
)
from utils.errors import error_response, success_response
from utils.logger import get_logger
import logging

# AFTER
from flask import Blueprint, Response, jsonify, request
from utils.export_utils import (
    create_excel_workbook,
    generate_timestamped_filename,
    stream_excel_response,
    MAX_EXPORT_ROWS
)
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_weekly_summary
)
from utils.errors import error_response, success_response
from utils.logger import get_logger
```

#### Before / After: `routes/weekly_summary.py`

```python
# BEFORE (line 8)
from utils.business_logic import BusinessLogic

# AFTER
# (line deleted entirely)
```

**Validation:** `python -m pytest tests/test_exports.py tests/test_weekly_summary.py -q`

---

### 3b. Delete Dead Modules

**Estimated impact:** split into a safe Wave 1 and a guarded Wave 2 package-surface contraction.

#### Wave 1 — high-confidence internal deletions

- [ ] **Step 1:** Confirm Phase 0 package-surface decision still allows Wave 1 deletions to be treated as internal-only cleanup.
- [ ] **Step 2:** Remove dead import in `routes/weekly_summary.py:8`
  - [ ] Confirm this was completed in Phase 3a before deleting any legacy module files.
- [ ] **Step 3:** Delete `utils/helpers.py`
  - Rationale: strict subset of `utils/__init__.py`; also imports nonexistent `get_weekly_summary`
  - Verify first: `rg -n "from utils\.helpers|import utils\.helpers" app.py routes utils tests e2e`
- [ ] **Step 4:** Delete `utils/filters.py`
  - Rationale: deprecated wrapper around `filter_predicates.py`
  - Verify first: `rg -n "from utils\.filters|import utils\.filters|ExerciseFilter" app.py routes utils tests e2e`
- [ ] **Step 5:** Delete `utils/database_init.py`
  - Rationale: superseded by `utils/db_initializer.py`
  - Verify first: `rg -n "from utils\.database_init|import utils\.database_init|database_init" app.py routes utils tests e2e`
- [ ] **Step 6:** Treat `utils/muscle_group.py` as Wave 1.5 only if it remains test-only after re-grep
  - Verify first: `rg -n "MuscleGroupHandler|from utils\.muscle_group|import utils\.muscle_group" app.py routes utils tests e2e`
  - [ ] If deleted, delete `tests/test_muscle_group.py` in the same change
  - [ ] If not clearly safe, defer instead of forcing deletion
- [ ] **Step 7:** Update docs and architecture notes that mention any Wave 1 deletions in the same branch (`CLAUDE.md`, plan docs, legacy inventories)
- [ ] **Step 8:** Validate Wave 1 with full pytest:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

#### Wave 2 — guarded package-surface contraction

- [ ] **Step 9:** Record an explicit decision for `utils/__init__.py` package exports:
  - [ ] `DataHandler`
  - [ ] `BusinessLogic`
  - [ ] `get_workout_logs()` wrapper
- [ ] **Step 10:** Only if the decision is "internal legacy exports, safe to remove", edit `utils/__init__.py`
  - [ ] Remove `from .data_handler import DataHandler`
  - [ ] Remove `from .business_logic import BusinessLogic`
  - [ ] Remove `"DataHandler"` and `"BusinessLogic"` from `__all__`
  - [ ] Remove the duplicate `get_workout_logs()` wrapper after confirming `from utils import get_workout_logs` still resolves to the imported function
- [ ] **Step 11:** Delete `utils/business_logic.py` only after all of the following are true
  - [ ] `routes/weekly_summary.py` dead import removed
  - [ ] `rg -n "BusinessLogic|from utils\.business_logic|import utils\.business_logic" app.py routes utils tests e2e docs CLAUDE.md` returns only planned deletions / doc references
  - [ ] `tests/test_business_logic.py` is deleted in the same change
- [ ] **Step 12:** Delete `utils/data_handler.py` only after all of the following are true
  - [ ] package-surface decision is recorded
  - [ ] `rg -n "DataHandler|from utils\.data_handler|import utils\.data_handler|from utils import .*DataHandler" app.py routes utils tests e2e docs CLAUDE.md` returns only planned deletions / doc references
  - [ ] `tests/test_data_handler.py` is deleted in the same change
- [ ] **Step 13:** Re-run full pytest after each Wave 2 deletion, not only at the end
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

** codex 5.4*** I would split this phase into "high-confidence deletions" and "public-surface candidates." `utils/helpers.py`, `utils/filters.py`, `utils/database_init.py`, and likely `utils/muscle_group.py` are strong first-wave candidates; `utils/data_handler.py` deserves an explicit check for package-style imports before removal because it is still re-exported from `utils/__init__.py`.

---

### 3c. Delete Orphaned Templates

**Estimated impact:** 6 files deleted

- [ ] Verify each template has no `render_template`, `{% include %}`, or `{% extends %}` references:
  ```powershell
  rg -n "dropdowns\.html|filters\.html|table\.html|exercise_details\.html|debug_modal\.html|workout_tracker\.html" routes templates static tests e2e
  ```
- [ ] Delete `templates/dropdowns.html`
- [ ] Delete `templates/filters.html`
- [ ] Delete `templates/table.html`
- [ ] Delete `templates/exercise_details.html`
- [ ] Delete `templates/debug_modal.html`
- [ ] Delete `templates/workout_tracker.html`
- [ ] Run E2E smoke navigation tests: `npx playwright test e2e/smoke-navigation.spec.ts`

---

### 3d. Extract Duplicated Parse Functions (DRY)

**Estimated impact:** modest deduplication, but tests currently import the route-local helpers directly.

- [ ] Add `parse_counting_mode()` and `parse_contribution_mode()` to `utils/effective_sets.py`
- [ ] Update both route files to use the shared implementation
- [ ] **Preferred safe path:** keep `_parse_counting_mode()` and `_parse_contribution_mode()` in both routes as thin compatibility wrappers for one cleanup cycle
  - [ ] Existing route tests import these helpers directly and should stay green without test rewrites
- [ ] Add or refresh direct tests for the new shared helpers in `tests/test_effective_sets.py`
- [ ] Only if wrappers are intentionally removed later, update `tests/test_session_summary_routes.py` and `tests/test_weekly_summary_routes.py` in the same change set

#### Before (identical in both files):

```python
# routes/session_summary.py:19-30 AND routes/weekly_summary.py:21-32
def _parse_counting_mode(value: str) -> CountingMode:
    """Parse counting mode from request parameter."""
    if value and value.lower() == 'raw':
        return CountingMode.RAW
    return CountingMode.EFFECTIVE

def _parse_contribution_mode(value: str) -> ContributionMode:
    """Parse contribution mode from request parameter."""
    if value and value.lower() == 'direct':
        return ContributionMode.DIRECT_ONLY
    return ContributionMode.TOTAL
```

#### After:

```python
# utils/effective_sets.py (append to existing file)
def parse_counting_mode(value: str) -> CountingMode:
    """Parse counting mode from request query parameter."""
    if value and value.lower() == 'raw':
        return CountingMode.RAW
    return CountingMode.EFFECTIVE

def parse_contribution_mode(value: str) -> ContributionMode:
    """Parse contribution mode from request query parameter."""
    if value and value.lower() == 'direct':
        return ContributionMode.DIRECT_ONLY
    return ContributionMode.TOTAL
```

```python
# routes/session_summary.py — updated import
from utils.effective_sets import CountingMode, ContributionMode, parse_counting_mode, parse_contribution_mode

# routes/weekly_summary.py — same import
from utils.effective_sets import CountingMode, ContributionMode, parse_counting_mode, parse_contribution_mode
```

**Validation:** `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary.py tests/test_weekly_summary.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_effective_sets.py -q`

---

### 3e. Summary-Page Frontend Coupling Gate

**Estimated impact:** no code change required by default; this is a safety gate before touching summary templates or summary JS.

- [ ] Record which updater path is authoritative for each summary page during this cleanup cycle:
  - [ ] `static/js/app.js` page initializers
  - [ ] `static/js/modules/summary.js` fallback updater path
  - [ ] `templates/session_summary.html` inline `updateSessionSummary()`
  - [ ] `templates/weekly_summary.html` inline `updateWeeklySummary()`
- [ ] Confirm whether `static/js/modules/summary.js` still depends on the presence of the inline updater and/or `#counting-mode` to short-circuit safely
- [ ] Confirm that `GET /api/pattern_coverage` stays on its current deferred contract from `DOCS_AUDIT_PLAN.md`
- [ ] Do not start 3f until this ownership note is complete and committed to the plan / review notes
- [ ] Validate current behavior before any template refactor:
  - [ ] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`

---

### 3f. Extract Jinja2 Method Selector Macro (Descoped)

**Estimated impact:** ~23 duplicated lines → single shared macro (descoped from original ~78 estimate)

> **Review finding (2026-04-08):** Line-by-line comparison revealed the volume-legend sections are **NOT identical** between templates. Three specific differences exist:
> 1. Session line 69 shows session warning thresholds (`<=10 OK | 10-11 Borderline | >11 Excessive`); Weekly line 71 shows the effective sets formula instead.
> 2. Session has an extra `<p>` tag with the formula before the `<details>` expand section; Weekly omits it.
> 3. The `<details>` block in Session starts with the formula then Effort Factor; Weekly starts directly with Effort Factor.
>
> **Decision:** Descope to `method_selector` macro only. The volume-legend stays page-specific until a content-block design is validated.

- [ ] Start only after Phase 3e is complete
- [ ] Create `templates/partials/_volume_controls.html` with `method_selector` macro
- [ ] Update `templates/session_summary.html` to use the macro for the method selector only
- [ ] Update `templates/weekly_summary.html` to use the macro for the method selector only
- [ ] Leave volume-legend sections as page-specific (NOT extracted)
- [ ] Do not rename or remove inline updater functions unless the Phase 3e ownership note explicitly allows it

#### After: New file `templates/partials/_volume_controls.html`

```html
{% macro method_selector(update_function_name) %}
<div class="method-selector">
    <div class="mb-3">
        <label for="counting-mode" class="form-label">Set Counting Mode</label>
        <select id="counting-mode" class="form-select"
                onchange="{{ update_function_name }}()">
            <option value="effective" selected>Effective Sets (Effort & Rep Range Weighted)</option>
            <option value="raw">Raw Sets (Unweighted)</option>
        </select>
        <small class="form-text text-muted">
            <strong>Effective Sets:</strong> Weights sets by effort (RIR/RPE) and rep range to estimate hypertrophy stimulus. Lower RIR = more credit.<br>
            <strong>Raw Sets:</strong> Simple set count without any adjustments.
        </small>
    </div>
    <div class="mb-3">
        <label for="contribution-mode" class="form-label">Muscle Contribution Mode</label>
        <select id="contribution-mode" class="form-select"
                onchange="{{ update_function_name }}()">
            <option value="total" selected>Total (Primary + Secondary + Tertiary)</option>
            <option value="direct">Direct Only (Primary Muscle Only)</option>
        </select>
        <small class="form-text text-muted">
            <strong>Total:</strong> Counts volume from all muscles worked (Primary 100%, Secondary 50%, Tertiary 25%).<br>
            <strong>Direct Only:</strong> Only counts sets where the muscle is the primary target.
        </small>
    </div>
</div>
{% endmacro %}
```

#### Usage in both templates:

```html
{% from "partials/_volume_controls.html" import method_selector %}
<!-- In session_summary.html: -->
{{ method_selector("updateSessionSummary") }}
<!-- volume-legend stays inline (page-specific content) -->

<!-- In weekly_summary.html: -->
{{ method_selector("updateWeeklySummary") }}
<!-- volume-legend stays inline (page-specific content) -->
```

**Validation:** `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` + filtered API/browser checks if fetch behavior changes + visual spot-check of both pages

** codex 5.4*** The shared controls and legend shell are good macro candidates, but the pages are not fully identical. `weekly_summary.html` has plan-specific explanatory text and extra pattern-coverage content, so I would scope the extraction narrowly and consider whether the larger duplication worth tackling next is actually the inline JS, not the Jinja markup.

---

### 3g. Consolidate Volume Classifier Threshold Functions (Backend-only)

**Estimated impact:** ~10 lines reduced in backend helper code only. This phase intentionally does **not** deduplicate template or JS threshold logic.

- [ ] Confirm this phase is backend-only
  - [ ] Do **not** touch `templates/session_summary.html`
  - [ ] Do **not** touch `templates/weekly_summary.html`
  - [ ] Do **not** touch `static/js/modules/summary.js`
  - [ ] Do **not** touch `static/js/modules/sessionsummary.js` or `static/js/updateSummary.js`
- [ ] Refactor `utils/volume_classifier.py:10-35`
- [ ] Preserve public API (`get_volume_class`, `get_volume_label`) — no callers need to change

#### Before (`utils/volume_classifier.py:10-35`):

```python
def get_volume_class(total_sets):
    if total_sets < 10:
        return "low-volume"
    elif total_sets < 20:
        return "medium-volume"
    elif total_sets < 30:
        return "high-volume"
    else:
        return "ultra-volume"

def get_volume_label(total_sets):
    if total_sets < 10:
        return "Low Volume"
    elif total_sets < 20:
        return "Medium Volume"
    elif total_sets < 30:
        return "High Volume"
    else:
        return "Excessive Volume"
```

#### After:

```python
_VOLUME_TIERS = [
    # (threshold, css_class, label)  — evaluated top-down, first match wins
    (30, "ultra-volume",  "Excessive Volume"),
    (20, "high-volume",   "High Volume"),
    (10, "medium-volume", "Medium Volume"),
    (0,  "low-volume",    "Low Volume"),
]

def _classify(total_sets):
    """Return (css_class, label) for a raw set count."""
    for threshold, css_class, label in _VOLUME_TIERS:
        if total_sets >= threshold:
            return css_class, label
    return "low-volume", "Low Volume"

def get_volume_class(total_sets):
    """Return the CSS class for volume classification (raw sets based)."""
    return _classify(total_sets)[0]

def get_volume_label(total_sets):
    """Return the text label for volume classification."""
    return _classify(total_sets)[1]
```

**Validation:** `.\.venv\Scripts\python.exe -m pytest tests/test_volume_classifier.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q`

** codex 5.4*** This refactor is safe, but it is also relatively low ROI compared with the stronger cleanup wins above. If scope widens, I would prioritize dead JS detection and logger/DB normalization ahead of this cosmetic consolidation.

---

### 3h. Migrate Raw DB Access & Replace `print()` with Logger

> **These tasks are already captured in the archived audit record [`docs/archive/DOCS_AUDIT_PLAN.md`](archive/DOCS_AUDIT_PLAN.md).**
> To avoid duplication, this plan defers to that document for execution steps.

| Task | Covered By | Scope |
|------|-----------|-------|
| Migrate `get_db_connection()` → `DatabaseHandler` in 4 files | `archive/DOCS_AUDIT_PLAN.md` — **Tier 3** (6 steps with Codex review comments, `lastrowid` nuances, FK pre-checks) | `utils/user_selection.py`, `utils/volume_export.py`, `routes/volume_splitter.py` (3 endpoints), `utils/database_indexes.py` |
| Replace `print()` → `get_logger()` in ~20 files | `archive/DOCS_AUDIT_PLAN.md` — **Tier 2** (file-by-file table, migration template, safety rationale) | ~52 `print()` calls across `routes/` and `utils/` |

- [x] Execute `archive/DOCS_AUDIT_PLAN.md` Tier 2 (logging)
- [x] Execute `archive/DOCS_AUDIT_PLAN.md` Tier 3 (DB migration)
- [x] Validate both: `python -m pytest tests/ -q` (full suite) — current validated snapshot: `981 passed, 1 skipped`

** codex 5.4*** Since this plan still touches `routes/weekly_summary.py`, `routes/session_summary.py`, and later `routes/exports.py` in `3j`, I would opportunistically remove the local `print()` calls in those same edits instead of guaranteeing a second pass later. That keeps touched files moving toward the project standard in one trip.

---

### 3i. Bloated Function Decomposition (Optional / Lower Priority)

These are candidates for future refactoring. Each function should be broken into smaller, named sub-functions that each handle one concern.

| Function | File | Lines | Suggested Extractions |
|----------|------|-------|-----------------------|
| `export_to_excel()` | `routes/exports.py` | 338 | `_recalculate_exercise_order()`, `_build_export_query()`, `_fetch_all_sheets()` |
| `calculate_session_summary()` | `utils/session_summary.py` | 256 | `_build_plan_query()`, `_build_log_query()`, `_aggregate_muscle_volumes()` |
| `replace_exercise()` | `routes/workout_plan.py` | 230 | `_validate_replacement_input()`, `_build_candidate_pool()`, `_select_replacement()` |
| `create_excel_workbook()` | `utils/export_utils.py` | 227 | `_setup_formats()`, `_build_superset_color_map()`, `_write_worksheet()` |
| `generate_progression_suggestions()` | `utils/progression_plan.py` | 224 | `_build_weight_suggestion()`, `_build_rep_suggestion()`, `_build_maintenance_suggestion()` |
| `suggest_supersets()` | `routes/workout_plan.py` | 139 | `_fetch_exercises_for_pairing()`, `_find_superset_pairs()` |
| `set_execution_style()` | `routes/workout_plan.py` | 138 | `_validate_style_input()`, `_apply_style_to_exercises()` |
| `link_superset()` | `routes/workout_plan.py` | 131 | `_validate_superset_prerequisites()`, `_create_superset_group()` |

> These decompositions preserve the public function signature. Internal helpers are prefixed with `_` and placed directly above the calling function in the same file.

**Validation:** Run the specific test file for each modified module after each extraction.

---

### 3j. Fix N+1 UPDATE Loop (Deferred / Last)

**Estimated impact:** N sequential DB writes → 1 batch write, but with an intentional semantic change if converted to atomic `executemany()`.

- [ ] Add or confirm targeted tests in `tests/test_exports.py` for the `exercise_order` recalculation branch
  - [ ] success path with multiple rows needing recalculation
  - [ ] failure / rollback semantics if atomic batch mode is adopted
- [ ] If the tests do not exist yet, add them before editing `routes/exports.py`
- [ ] Reconfirm `DatabaseHandler.executemany()` exists and keeps transaction semantics clear
- [ ] Only after the tests exist, replace the per-row update loop in `routes/exports.py`
- [ ] Keep an explicit code comment documenting the semantic change: partial-success logging → all-or-nothing batch update
- [ ] Validate targeted export and flow coverage:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_exports.py tests/test_ui_flows.py -q`
  - [ ] `npx playwright test e2e/workout-plan.spec.ts --project=chromium --reporter=line`
- [ ] Re-run full pytest immediately after this phase:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

** codex 5.4*** The batch update is a reasonable optimization, but it is not a pure cleanup. Treat it as the last phase, after the deletion and dedup work are stable, because it changes failure semantics on a live write path.

---

## Phase 4: Validation & Regression

### 4.1 Pre-Cleanup Baseline

Run before starting any changes:

- [ ] Record pytest results: `.\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath baseline_pytest.txt`
- [ ] Record summary-page browser gate: `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath baseline_summary_pages.txt`
- [ ] If the upcoming phase touches templates, shared JS, or route contracts, record full Playwright too: `npx playwright test --project=chromium --reporter=line | Tee-Object -FilePath baseline_e2e_full.txt`
- [ ] Record file counts:
  ```powershell
  (rg --files utils -g "*.py" | Measure-Object).Count
  (rg --files routes -g "*.py" | Measure-Object).Count
  (Get-ChildItem templates -File | Measure-Object).Count
  (rg --files static/js/modules -g "*.js" | Measure-Object).Count
  (rg --files static/js -g "*.js" | Measure-Object).Count
  ```
- [ ] Record total Python line count:
  ```powershell
  $pyFiles = rg --files -g "*.py" -g "!.venv/**" -g "!node_modules/**"
  ($pyFiles | ForEach-Object { (Get-Content $_ | Measure-Object -Line).Lines } | Measure-Object -Sum).Sum
  ```

** codex 5.4*** This subsection has been normalized to PowerShell-friendly commands so the baseline checklist can be executed exactly as written on this repo's current Windows workflow.

### 4.2 Per-Change Validation Protocol

| Change Type | Test Command | Scope |
|-------------|-------------|-------|
| Wave 1 module deletion | `.\.venv\Scripts\python.exe -m pytest tests/ -q` + `rg` import audit | Full suite + import safety |
| Wave 2 package-surface deletion | `.\.venv\Scripts\python.exe -m pytest tests/ -q` + package/doc audit | Full suite + API-surface safety |
| Route helper extraction | `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_effective_sets.py -q` | Targeted route + helper contract |
| Backend helper edit used by templates | relevant util tests + relevant route tests | Targeted |
| Template / summary-page markup edit | `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` + visual check | Browser + manual |
| Shared summary JS or route-contract edit | targeted summary browser spec + filtered API integration + full Playwright if shared modules change | Browser + contract |
| Semantic DB write-path change | `.\.venv\Scripts\python.exe -m pytest tests/test_exports.py tests/test_ui_flows.py -q` + full pytest | Targeted + suite |

### 4.3 Test File → Module Coverage Map

| Test File | Covers Module | Action After Module Deletion |
|-----------|--------------|------------------------------|
| `tests/test_business_logic.py` | `utils/business_logic.py` | Delete test file |
| `tests/test_data_handler.py` | `utils/data_handler.py` | Delete test file only if Wave 2 deletes the module |
| `tests/test_muscle_group.py` | `utils/muscle_group.py` | Delete test file only if Wave 1.5 deletes the module |
| `tests/test_session_summary.py` | `utils/session_summary.py` | Must still pass after parse function extraction |
| `tests/test_weekly_summary.py` | `utils/weekly_summary.py` | Must still pass after parse function extraction |
| `tests/test_session_summary_routes.py` | `routes/session_summary.py` | Must still pass if compatibility wrappers are kept or updated in the same change |
| `tests/test_weekly_summary_routes.py` | `routes/weekly_summary.py` | Must still pass if compatibility wrappers are kept or updated in the same change |
| `tests/test_volume_classifier.py` | `utils/volume_classifier.py` | Must still pass after threshold consolidation |
| `tests/test_exports.py` | `routes/exports.py` | Must be expanded before the deferred batch-update phase |
| `tests/test_ui_flows.py` | export and page flows | Must still pass after export/write-path changes |
| `tests/test_workout_log_routes.py` | `routes/workout_log.py` | Must still pass |
| `tests/test_workout_plan_routes.py` | `routes/workout_plan.py` | Must still pass after any route changes |
| `tests/test_effective_sets.py` | `utils/effective_sets.py` | Must still pass after adding parse functions |

### 4.4 Post-Cleanup Verification Checklist

- [ ] **Full pytest:** `.\.venv\Scripts\python.exe -m pytest tests/ -q` — expect current baseline adjusted only by intentionally deleted test files, zero failures
- [ ] **Summary surfaces browser gate:** `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
- [ ] **Full E2E:** `npx playwright test --project=chromium --reporter=line` — required if any template, shared JS, or route-contract work landed
- [ ] **Dead code scan:** `vulture routes/ utils/ --min-confidence 80` — expect zero or near-zero findings
- [ ] **Unused import scan:** `pylint --disable=all --enable=W0611 routes/ utils/` — expect zero findings
- [ ] **Print audit:** `rg -n "print\(" routes utils -g "*.py"` — expect zero hits (covered by `archive/DOCS_AUDIT_PLAN.md` Tier 2)
- [x] **Raw DB access audit:** `rg -n "get_db_connection|sqlite3\.connect" routes utils` — only intentional hits remain in `utils/database_indexes.py` for the locked `optimize_database()` maintenance path plus the helper implementation in `utils/database.py`
- [ ] **Frontend orphan audit:** `rg -n "sessionsummary|updateSummary" static templates`
- [ ] **Package-surface audit:** `rg -n "from utils import .*DataHandler|from utils import .*BusinessLogic|from utils\.helpers|from utils\.filters" app.py routes tests e2e`
- [ ] **File count comparison:** Compare against baseline counts from 4.1
- [ ] **Line count comparison:** Compare total Python LOC against baseline

** codex 5.4*** I would add one more post-cleanup audit here for dead or duplicate frontend code, because the discovery phase already points toward that scope and the current checklist stops short of confirming it. At minimum, re-check `static/js/modules/sessionsummary.js`, `static/js/updateSummary.js`, and any JS left behind after deleting `templates/dropdowns.html`.

### 4.5 Expected Reduction Summary

| Metric | Before (est.) | After (est.) | Reduction |
|--------|---------------|--------------|-----------|
| Python files in `utils/` | ~27 | ~23 to ~21 | Depends on whether Wave 2 deletions proceed |
| Template files | 15 | 9 (+1 partial) | -5 files |
| Dead imports | ~7 | 0 | -7 |
| Duplicated parse functions | 2 route copies | 1 shared helper + optional temporary wrappers | Safer incremental reduction |
| N+1 query loops | 1 | 0 only if 3j executes | Performance fix, deferred by default |
| Raw `get_db_connection()` calls | ~8 | 0 | Thread safety fix |
| `print()` calls in prod code | already 0 | 0 | Already completed in archived audit |
| Total lines removed (est.) | — | — | Intentionally variable; safety preferred over maximum reduction |

---

## Execution Priority

| Priority | Sub-phase | Risk | Effort |
|----------|-----------|------|--------|
| 0 (required first) | **Phase 0** Confidence gate | Very low | 30-60 min |
| 1 | **3a** Remove unused imports | Very low | 5 min |
| 2 | **3b Wave 1** High-confidence deletions | Low | 15-30 min |
| 3 | **3c** Delete orphaned templates | Very low | 5 min |
| 4 | **3d** Compatibility-first parse extraction | Low | 10-20 min |
| 5 | **3e** Summary-page frontend coupling gate | Very low | 10-15 min |
| 6 | **3f** Extract descoped method-selector macro | Medium (visual regression) | 20 min |
| 7 | **3g** Backend-only volume classifier cleanup | Low | 10 min |
| 8 | **3b Wave 2** Package-surface contraction | Medium | 20-40 min |
| ~~9~~ | ~~**3h** DB migration + logging cleanup~~ | ~~Medium~~ | **COMPLETED** (see `archive/DOCS_AUDIT_PLAN.md` Tiers 2-3) |
| 10 (last / optional) | **3j** N+1 update loop semantic optimization | Medium-High (write path) | 20-40 min |
| 11 | **3i** Decompose bloated functions | Medium (wide scope) | 2+ hours |

---

## Architectural Review Findings (2026-04-09)

### Review Confidence Scores

| Phase | Confidence | Risk | Notes |
|---|---|---|---|
| **3a** Remove unused imports | **98%** | Very Low | All 5 imports confirmed unused beyond import lines |
| **3b Wave 1** High-confidence deletions | **94%** | Low | `helpers`, `filters`, and `database_init` are strong candidates; `muscle_group` is conditional |
| **3b Wave 2** Package-surface contraction | **70%** | Medium | `DataHandler` and `BusinessLogic` still touch package surface / tests / docs and require an explicit API decision |
| **3c** Delete orphaned templates | **99%** | Very Low | Zero render/include references for all 6 |
| **3d** Extract parse functions | **95%** | Low | Safe if route-level compatibility wrappers are kept for one cycle; lower confidence if wrappers are deleted immediately |
| **3e** Summary-page frontend coupling gate | **99%** | Very Low | Analysis / documentation gate only; needed before touching summary templates or shared summary JS |
| **3f** Extract Jinja2 macro | **88%** | Medium (visual regression) | Safe if limited to `method_selector` and inline updater ownership remains stable |
| **3g** Consolidate volume classifier | **95%** | Low | Safe as backend-only cleanup; lower confidence if widened into template / JS dedup |
| **3h** DB migration + logging | **99%** | N/A | Already completed and validated at `981 passed, 1 skipped` |
| **3i** Decompose bloated functions | N/A | Deferred | Not assessed — optional/lower priority |
| **3j** Fix N+1 loop | **70%** | Medium-High | Defer until dedicated export-path tests prove the intended semantics |

### Key Corrections Applied
1. **Baseline evidence refreshed:** current validated snapshot is `981 passed, 1 skipped` plus `21` passing summary-surface browser tests
2. **Phase 3b split:** high-confidence internal deletions are separated from package-surface contraction work
3. **Phase 3d hardened:** route-level parse helper compatibility is now called out explicitly because route tests import those helpers directly
4. **Phase 3e added:** summary-page frontend ownership must be documented before template dedup proceeds
5. **Phase 3g narrowed:** backend-only for this cycle; template / JS threshold dedup is deferred
6. **Phase 3j deferred:** the export write-path optimization moved to the end and is blocked on dedicated tests

### Volume Classifier Boundary Verification

| Input | `get_volume_class` (current) | `_classify()[0]` (proposed) | Match |
|---|---|---|---|
| -1 | `"low-volume"` | `"low-volume"` (fallback) | Yes |
| 0 | `"low-volume"` | `>= 0` hit | Yes |
| 9.99 | `"low-volume"` | `>= 0` hit | Yes |
| 10 | `"medium-volume"` | `>= 10` hit | Yes |
| 19.99 | `"medium-volume"` | `>= 10` hit | Yes |
| 20 | `"high-volume"` | `>= 20` hit | Yes |
| 29.99 | `"high-volume"` | `>= 20` hit | Yes |
| 30 | `"ultra-volume"` | `>= 30` hit | Yes |
| 100 | `"ultra-volume"` | `>= 30` hit | Yes |

Note: Plan only refactors `get_volume_class()` and `get_volume_label()` (lines 10-35). The other 5 public functions (`get_effective_volume_label`, `get_volume_tooltip`, `get_session_warning_tooltip`, `get_category_tooltip`, `get_subcategory_tooltip`) are untouched.

---

## Execution Checklist (Uncompleted Phases)

> **Pre-flight:** Record current baseline before starting any work.
> ```powershell
> .\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath baseline_pytest.txt
> npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath baseline_summary_pages.txt
> ```

---

### [Phase 0] Prerequisite Confidence Gate
- [ ] **0-1.** Save rollback artifacts before risky edits:
  - [ ] `git status --short | Tee-Object -FilePath cleanup_preflight_status.txt`
  - [ ] `git diff --binary | Out-File -Encoding ascii cleanup_preflight.patch`
- [ ] **0-2.** Re-run full pytest baseline:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- [ ] **0-3.** Re-run summary-surface browser baseline:
  - [ ] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
- [ ] **0-4.** If template/shared-JS/contract work is planned in this cycle, re-run full Playwright now:
  - [ ] `npx playwright test --project=chromium --reporter=line`
- [ ] **0-5.** Audit package-surface imports and references:
  - [ ] `rg -n "from utils import|import utils\.|from utils\.(data_handler|business_logic|helpers|filters|database_init|muscle_group)" app.py routes tests e2e docs CLAUDE.md`
- [ ] **0-6.** Record whether `utils/__init__.py` is treated as supported API or internal-only convenience.
- [ ] **0-7.** Audit summary-page ownership:
  - [ ] `static/js/app.js`
  - [ ] `static/js/modules/summary.js`
  - [ ] `templates/session_summary.html`
  - [ ] `templates/weekly_summary.html`
  - [ ] `e2e/summary-pages.spec.ts`
- [ ] **0-8.** Audit likely orphan frontend files:
  - [ ] `static/js/modules/sessionsummary.js`
  - [ ] `static/js/updateSummary.js`
- [ ] **0-9.** Confirm whether the export recalculation branch already has dedicated success and failure tests.
- [ ] **0-10.** Record go / no-go:
  - [ ] baseline green
  - [ ] package-surface decision recorded
  - [ ] summary-page ownership recorded
  - [ ] semantic-change test gap resolved or deferred

---

### [Phase 3a] Remove Unused Imports
- [ ] **3a-1.** Edit `routes/exports.py` — remove 5 unused imports:
  - [ ] Remove `make_response` from Flask import (line 1)
  - [ ] Remove `sanitize_filename` (line 5)
  - [ ] Remove `create_content_disposition_header` (line 6)
  - [ ] Remove `should_use_streaming` (line 9)
  - [ ] Remove `import logging` (line 19)
- [ ] **3a-2.** Edit `routes/weekly_summary.py` — remove dead import:
  - [ ] Remove `from utils.business_logic import BusinessLogic` (line 8)
- [ ] **3a-3.** Validate: `.venv/Scripts/python.exe -m pytest tests/test_weekly_summary.py -q`
- [ ] **3a-4.** Validate: `.venv/Scripts/python.exe -m pytest tests/ -q` — same pass count as baseline

---

### [Phase 3b Wave 1] High-Confidence Internal Deletions
- [ ] **3bW1-1.** Confirm the Phase 0 package-surface decision still allows Wave 1 deletions to be treated as internal-only.
- [ ] **3bW1-2.** Confirm the dead `BusinessLogic` import in `routes/weekly_summary.py` is already removed.
- [ ] **3bW1-3.** Delete `utils/helpers.py` only after:
  - [ ] `rg -n "from utils\.helpers|import utils\.helpers" app.py routes utils tests e2e` returns no runtime callers
- [ ] **3bW1-4.** Delete `utils/filters.py` only after:
  - [ ] `rg -n "from utils\.filters|import utils\.filters|ExerciseFilter" app.py routes utils tests e2e` returns no runtime callers
- [ ] **3bW1-5.** Delete `utils/database_init.py` only after:
  - [ ] `rg -n "from utils\.database_init|import utils\.database_init|database_init" app.py routes utils tests e2e` returns no runtime callers
- [ ] **3bW1-6.** Evaluate `utils/muscle_group.py` as optional Wave 1.5:
  - [ ] `rg -n "MuscleGroupHandler|from utils\.muscle_group|import utils\.muscle_group" app.py routes utils tests e2e`
  - [ ] If still test-only, delete `utils/muscle_group.py` and `tests/test_muscle_group.py` together
  - [ ] If not clearly safe, defer it
- [ ] **3bW1-7.** Update docs / inventories for deleted modules in the same branch (`CLAUDE.md`, cleanup plan, legacy inventories)
- [ ] **3bW1-8.** Validate with full pytest:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

---

### [Phase 3b Wave 2] Package-Surface Contraction
- [ ] **3bW2-1.** Record the explicit decision for `DataHandler`, `BusinessLogic`, and the duplicate `get_workout_logs()` wrapper in `utils/__init__.py`
- [ ] **3bW2-2.** If and only if the decision is "safe to remove package exports", edit `utils/__init__.py`:
  - [ ] Remove `from .data_handler import DataHandler`
  - [ ] Remove `from .business_logic import BusinessLogic`
  - [ ] Remove `"DataHandler"` and `"BusinessLogic"` from `__all__`
  - [ ] Remove the duplicate `get_workout_logs()` wrapper
- [ ] **3bW2-3.** Delete `utils/business_logic.py` only after:
  - [ ] `rg -n "BusinessLogic|from utils\.business_logic|import utils\.business_logic" app.py routes utils tests e2e docs CLAUDE.md` shows only planned removals
  - [ ] `tests/test_business_logic.py` is deleted in the same change
- [ ] **3bW2-4.** Delete `utils/data_handler.py` only after:
  - [ ] `rg -n "DataHandler|from utils\.data_handler|import utils\.data_handler|from utils import .*DataHandler" app.py routes utils tests e2e docs CLAUDE.md` shows only planned removals
  - [ ] `tests/test_data_handler.py` is deleted in the same change
- [ ] **3bW2-5.** Re-run full pytest after each Wave 2 deletion:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

---

### [Phase 3c] Delete Orphaned Templates
- [ ] **3c-1.** Pre-verify runtime references:
  - [ ] `rg -n "dropdowns\.html|filters\.html|table\.html|exercise_details\.html|debug_modal\.html|workout_tracker\.html" routes templates static tests e2e`
- [ ] **3c-2.** Delete `templates/dropdowns.html`
- [ ] **3c-3.** Delete `templates/filters.html`
- [ ] **3c-4.** Delete `templates/table.html`
- [ ] **3c-5.** Delete `templates/exercise_details.html`
- [ ] **3c-6.** Delete `templates/debug_modal.html`
- [ ] **3c-7.** Delete `templates/workout_tracker.html`
- [ ] **3c-8.** Validate: `npx playwright test e2e/smoke-navigation.spec.ts`

---

### [Phase 3d] Extract Duplicated Parse Functions
- [ ] **3d-1.** Add shared `parse_counting_mode()` and `parse_contribution_mode()` to `utils/effective_sets.py`
- [ ] **3d-2.** Update `routes/session_summary.py` to use the shared implementation
  - [ ] Preferred safe path: keep `_parse_counting_mode()` and `_parse_contribution_mode()` as thin wrappers for one cycle
- [ ] **3d-3.** Update `routes/weekly_summary.py` the same way
  - [ ] Preferred safe path: keep `_parse_counting_mode()` and `_parse_contribution_mode()` as thin wrappers for one cycle
- [ ] **3d-4.** Add or refresh direct tests in `tests/test_effective_sets.py`
- [ ] **3d-5.** If wrappers are removed instead, update `tests/test_session_summary_routes.py` and `tests/test_weekly_summary_routes.py` in the same change
- [ ] **3d-6.** Validate:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary.py tests/test_weekly_summary.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_effective_sets.py -q`

---

### [Phase 3e] Summary-Page Frontend Coupling Gate
- [ ] **3e-1.** Record which updater path is authoritative for each summary page
  - [ ] `static/js/app.js`
  - [ ] `static/js/modules/summary.js`
  - [ ] `templates/session_summary.html`
  - [ ] `templates/weekly_summary.html`
- [ ] **3e-2.** Confirm whether `static/js/modules/summary.js` still relies on inline updaters and/or `#counting-mode` for safe short-circuit behavior
- [ ] **3e-3.** Confirm `GET /api/pattern_coverage` remains on its current deferred contract
- [ ] **3e-4.** Validate current summary behavior before template refactor:
  - [ ] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`

---

### [Phase 3f] Extract Jinja2 Method Selector Macro (Descoped)
- [ ] **3f-1.** Start only after Phase 3e is complete
- [ ] **3f-2.** Create `templates/partials/_volume_controls.html` with `method_selector` macro
- [ ] **3f-3.** Update `templates/session_summary.html`:
  - [ ] Add `{% from "partials/_volume_controls.html" import method_selector %}`
  - [ ] Replace the method-selector block only
  - [ ] Leave the volume-legend block untouched
  - [ ] Do not rename/remove inline `updateSessionSummary()` unless Phase 3e explicitly allows it
- [ ] **3f-4.** Update `templates/weekly_summary.html`:
  - [ ] Add the import line
  - [ ] Replace the method-selector block only
  - [ ] Leave the volume-legend block untouched
  - [ ] Do not rename/remove inline `updateWeeklySummary()` unless Phase 3e explicitly allows it
- [ ] **3f-5.** Validate:
  - [ ] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
- [ ] **3f-6.** Visual spot-check:
  - [ ] `/session_summary`
  - [ ] `/weekly_summary`

---

### [Phase 3g] Consolidate Volume Classifier (Backend-only)
- [ ] **3g-1.** Confirm this phase is backend-only:
  - [ ] Do not touch `templates/session_summary.html`
  - [ ] Do not touch `templates/weekly_summary.html`
  - [ ] Do not touch `static/js/modules/summary.js`
  - [ ] Do not touch `static/js/modules/sessionsummary.js`
  - [ ] Do not touch `static/js/updateSummary.js`
- [ ] **3g-2.** Edit `utils/volume_classifier.py` — replace `get_volume_class()` (lines 10-23) and `get_volume_label()` (lines 26-35) with table-driven `_VOLUME_TIERS` + `_classify()`:
  - [ ] Add `_VOLUME_TIERS` list (descending thresholds: 30, 20, 10, 0)
  - [ ] Add `_classify(total_sets)` helper returning `(css_class, label)`
  - [ ] Rewrite `get_volume_class()` to delegate to `_classify()[0]`
  - [ ] Rewrite `get_volume_label()` to delegate to `_classify()[1]`
  - [ ] Do NOT touch `get_effective_volume_label`, `get_volume_tooltip`, `get_session_warning_tooltip`, `get_category_tooltip`, `get_subcategory_tooltip`
- [ ] **3g-3.** Validate:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_volume_classifier.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q`

---

### [Phase 3i] Decompose Bloated Functions (Optional — Deferred)
> Not scheduled for this cleanup cycle. Candidates documented in Section 3i above.

---

### [Phase 3j] Fix N+1 UPDATE Loop (Deferred / Last)
- [ ] **3j-1.** Add or confirm targeted tests in `tests/test_exports.py` for the recalculation branch
  - [ ] success path
  - [ ] failure / rollback semantics
- [ ] **3j-2.** If those tests do not exist, add them before editing `routes/exports.py`
- [ ] **3j-3.** Only after the tests exist, replace the per-row update loop with `executemany()`
- [ ] **3j-4.** Add an explicit code comment documenting the semantic change
- [ ] **3j-5.** Validate targeted export / flow behavior:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_exports.py tests/test_ui_flows.py -q`
  - [ ] `npx playwright test e2e/workout-plan.spec.ts --project=chromium --reporter=line`
- [ ] **3j-6.** Re-run full pytest:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

---

### Post-Cleanup Final Gate
- [ ] **Full pytest:** `.\.venv\Scripts\python.exe -m pytest tests/ -q` — zero failures
- [ ] **Summary surfaces browser gate:** `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
- [ ] **Full E2E:** `npx playwright test --project=chromium --reporter=line` — required if template/shared-JS/contract phases executed
- [ ] **Dead code scan:** `vulture routes/ utils/ --min-confidence 80`
- [ ] **Unused import scan:** `pylint --disable=all --enable=W0611 routes/ utils/`
- [ ] **Print audit:** `rg -n "print\(" routes utils -g "*.py"` — expect zero
- [ ] **Frontend orphan audit:** `rg -n "sessionsummary|updateSummary" static templates`
- [ ] **Package-surface audit:** `rg -n "from utils import .*DataHandler|from utils import .*BusinessLogic|from utils\.helpers|from utils\.filters" app.py routes tests e2e`
- [ ] **File count comparison** against baseline
- [ ] **Line count comparison** against baseline
- [ ] **Update CLAUDE.md** Section 8 test counts and Section 8 deprecated/legacy table
