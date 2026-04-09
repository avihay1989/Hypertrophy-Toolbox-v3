# Puppeteer Browser Test Findings

> Automated browser exploration performed 2026-02-28 using Puppeteer MCP.
> Flask app tested at `http://localhost:5000`.

## Summary

| # | Issue | Severity | Status | Location |
|---|-------|----------|--------|----------|
| 1 | Min rep range > max rep range accepted | HIGH | Fixed | `utils/exercise_manager.py` |
| 2 | Negative RIR accepted | MEDIUM | Fixed | `utils/exercise_manager.py` |
| 3 | No upper-bound validation on weight | LOW | Fixed | `utils/exercise_manager.py` |
| 4 | Export to Workout Log creates duplicate entries | MEDIUM | Fixed | `routes/exports.py` |
| 5 | Generic error toast masks specific API error messages | LOW | Fixed | `static/js/modules/fetch-wrapper.js` |

---

## Issue 1 — Min Rep Range > Max Rep Range Accepted (HIGH)

**Description:** The `add_exercise` API and `ExerciseManager.add_exercise()` accept exercises where `min_rep_range` exceeds `max_rep_range` (e.g., min=100, max=5). The invalid data is stored in the database without any error.

**Reproduction:**
1. POST `/add_exercise` with `min_rep_range: 100, max_rep_range: 5`
2. Server responds 200 OK — "Exercise added successfully"
3. Invalid row persists in `user_selection` table

**Root cause:** `exercise_manager.py:32` only checks for truthy values (`if not all([...])`) but performs no relational validation between min and max.

**Expected:** Return validation error: "Min rep range cannot exceed max rep range."

**Impact:** Downstream calculations (effective sets, volume, progression suggestions) will produce nonsensical results.

**Fix:** Added validation in `ExerciseManager.add_exercise()` — returns `"Error: Min rep range cannot exceed max rep range."` when `min_rep_range > max_rep_range`.

---

## Issue 2 — Negative RIR Accepted (MEDIUM)

**Description:** RIR (Reps In Reserve) of `-5` is accepted and stored. RIR represents how many reps you have left before failure and should be constrained to 0–10 at minimum (>= 0 mandatory).

**Reproduction:**
1. POST `/add_exercise` with `rir: -5`
2. Server responds 200 OK

**Root cause:** No range validation on RIR in `exercise_manager.py`.

**Expected:** Reject negative RIR. Valid range: 0–10.

**Impact:** Negative RIR would break the effort factor calculation in `utils/effective_sets.py` — the RIR-based effort multiplier expects RIR >= 0.

**Fix:** Added `rir < 0` check in `ExerciseManager.add_exercise()` — returns `"Error: RIR cannot be negative."`

---

## Issue 3 — No Upper-Bound Validation on Weight (LOW)

**Description:** Weight of `999999` (kg) is accepted. While not technically invalid at the data type level, a reasonable upper bound prevents accidental data entry errors.

**Reproduction:**
1. POST `/add_exercise` with `weight: 999999`
2. Server responds 200 OK

**Expected:** Either warn or reject unreasonable weights (> 1000 kg). At minimum, the front-end `input[name="weight"]` should have a `max` attribute.

**Fix:** Added `weight < 0` and `weight > 1000` checks in `ExerciseManager.add_exercise()`.

---

## Issue 4 — Export to Workout Log Creates Duplicate Entries (MEDIUM)

**Description:** Clicking "Export to Workout Log" on the Workout Plan page creates duplicate rows in the Workout Log when exercises have already been imported from a previous export.

**Reproduction:**
1. Add Bench Press to workout plan
2. Click "Export to Workout Log" → navigates to `/workout_log` with 1 row
3. Navigate back to Workout Plan
4. Click "Export to Workout Log" again
5. Workout Log now has 2 identical Bench Press rows

**Expected:** Either:
- Warn the user that exercises already exist in the log
- Skip exercises already present (deduplicate)
- Clear the log before re-importing (with confirmation)

**Impact:** Users can accidentally create many duplicate entries, corrupting their session tracking and progressive overload history.

**Fix:** Added duplicate check in `export_to_workout_log()` in `routes/exports.py` — queries `workout_log` for existing `workout_plan_id` before inserting. Skips duplicates and reports count in response message.

---

## Issue 5 — Generic Error Toast Masks Specific API Error Messages (LOW)

**Description:** When the `add_exercise` API returns a structured error response (e.g., `"Exercise already exists in this routine."`), the UI sometimes shows a generic "An unexpected error occurred" toast instead of the specific message.

**Reproduction:**
1. Add Bench Press to Push 1 routine
2. Try adding Bench Press to Push 1 again
3. Toast shows "An unexpected error occurred" instead of "Exercise already exists in this routine."

**Root cause:** The error handling in `sendExerciseData()` (`workout-plan.js:1064-1076`) catches the error but the `error.message` may not correctly extract the server's error message from the structured JSON response.

**Expected:** Toast should display the server's specific error message.

**Root cause (detailed):** In `fetch-wrapper.js`, when an HTTP error occurs, `normalizeError()` correctly extracts the message and throws it. However, when the thrown error object is caught in the retry logic's outer `catch`, it gets passed through `normalizeError()` *again*. The already-normalized object `{ code, message, requestId }` doesn't match any of the known formats (`error.ok === false && error.error`, `instanceof Error`, or `typeof string`), so it falls through to the fallback: `'An unexpected error occurred'`.

**Fix:** Added an early return in `normalizeError()` to detect already-normalized error objects (those with both `code` and `message` properties that aren't native Error instances) and pass them through unchanged.

---

## Passing Tests (No Issues Found)

- **Homepage:** All navigation links work, page renders correctly
- **Routine cascade:** Environment → Program → Workout dropdown chain works properly
- **Plan Summary (Weekly Summary):** Volume table, pattern coverage warnings, sets-per-routine all render correctly
- **Session Summary:** Mode switching (Effective/Raw, Total/Direct) updates table correctly
- **Workout Log scoring:** Click-to-edit scored cells with +/- buttons works
- **Progression Plan:** Exercise selection loads suggestions (technique, volume, weight, reps)
- **Volume Splitter:** Sliders, distribution table, AI suggestions all functional
- **Generate Starter Plan:** Modal renders with all options, plan generation works

---

## Re-Run Validation (Context7 + Puppeteer MCP) — 2026-02-28

> This section supersedes the earlier "Plan Summary" / "Session Summary" pass status above.
> Re-run performed via:
> 1) `context7` MCP (`resolve-library-id`, `query-docs`) for Puppeteer API patterns
> 2) Puppeteer MCP server (`@modelcontextprotocol/server-puppeteer`) for browser execution
> 3) Isolated seeded DB + isolated Flask server (`127.0.0.1:5001`) to avoid mutating active user data

### New Regression Test Results

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| R1 | Weekly Summary: Effective Sets should remain invariant when counting mode switches Effective → Raw | ❌ Failed | `Chest` changed from `10.2` to `12.0` |
| R2 | Session Summary: Effective Sets should remain invariant when counting mode switches Effective → Raw | ❌ Failed | `Seed Routine / Chest` changed from `40.8` to `48.0` |
| R3 | Session Summary: Effective sets should not be multiplied by workout_log row count | ❌ Failed | Expected `10.2`, observed `40.8` with `session_count=4` |

### Root-Cause Mapping

1. `R1`, `R2` map to counting-mode coupling in effective-set aggregation:
   - `utils/weekly_summary.py`
   - `utils/session_summary.py`
2. `R3` maps to row multiplication from `LEFT JOIN workout_log` aggregation:
   - `utils/session_summary.py`

### Repro Artifacts Added

- `e2e/scripts/seed_summary_regression_db.py`
- `e2e/puppeteer_mcp_summary_regression.py`
- `e2e/run_puppeteer_summary_regression.ps1`

### Command Used

```powershell
powershell -ExecutionPolicy Bypass -File e2e/run_puppeteer_summary_regression.ps1
```

### Run Outcome

- Exit code: `1` (expected while regressions are present)
- All 3 targeted checks failed consistently under the seeded scenario.

---

## Post-Fix Re-Run (Context7 + Puppeteer MCP) — 2026-02-28

> After backend fixes in `utils/weekly_summary.py` and `utils/session_summary.py`,
> the same seeded MCP workflow was re-executed with the same command.

### Regression Results After Fix

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| R1 | Weekly Summary: Effective Sets invariant when switching Effective → Raw | ✅ Passed | No per-muscle diffs |
| R2 | Session Summary: Effective Sets invariant when switching Effective → Raw | ✅ Passed | No per-routine/muscle diffs |
| R3 | Session Summary: Effective sets not multiplied by workout_log count | ✅ Passed | Expected `10.2`, observed `10.2`, `session_count=4` |

### Run Outcome

- Exit code: `0`
- All targeted summary regression checks passed via Puppeteer MCP.
