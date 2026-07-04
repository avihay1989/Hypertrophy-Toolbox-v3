# Phase 4 Scan — Fatigue, Progression, Log

Scope: `utils/fatigue.py`, `utils/fatigue_data.py`, `utils/fatigue_context.py`,
`utils/progression_plan.py`, `utils/body_fat.py`, `utils/workout_log.py`.

Read line-by-line in full (not grepped). Cross-checked against
`docs/REFACTOR_PLAN.md` v2 (council-reviewed, 2026-07-03) — that plan does not
carry a dedicated WP for any of these six files beyond listing three of them
(`utils/fatigue.py`, `utils/fatigue_context.py`, `utils/progression_plan.py`)
in the global protected-zone list (Rule 2). Findings below are tagged
`[CONFIRMS-PLAN]` where they support an existing plan statement,
`[CONTRADICTS-PLAN]` where they conflict, `[NEW]` where the plan is silent,
and `[RISK]` for anything worth flagging regardless of plan status.

---

## `utils/fatigue.py` (751 lines)

**Purpose**: pure calculation module (no DB, no Flask) for the Fatigue Meter.
Docstring explicitly enumerates its own design decisions (D3, D6–D8, D10, D11)
— unusually well self-documented for this codebase.

**Structure**: the file is really four sub-modules concatenated behind
banner comments, each shipped in a different phase/stage:
1. Lines 41–303 — Phase 1 core: pattern/load/intensity multiplier tables
   (`PATTERN_WEIGHTS` 41, `LOAD_MULTIPLIER_BUCKETS` 56,
   `INTENSITY_MULTIPLIER_BUCKETS` 66, `SESSION_FATIGUE_BANDS` 76,
   `WEEKLY_FATIGUE_BANDS` 82), `calculate_set_fatigue` (194),
   `aggregate_session_fatigue` (231), `aggregate_weekly_fatigue` (270),
   `classify_session_fatigue`/`classify_weekly_fatigue` (295/300).
2. Lines 305–529 — Phase 2 per-muscle channel: `MUSCLE_CONTRIBUTION_WEIGHTS`
   (317), `UNASSIGNED_MUSCLE_BUCKET` (328), `MUSCLE_VOLUME_LANDMARKS` (336),
   `canonicalize_muscle_for_fatigue` (363), `classify_muscle_fatigue` (392),
   `muscle_percent_of_mrv` (417), `aggregate_muscles_for_session` (431),
   `summarize_muscle_bars` (495).
3. Lines 532–719 — Phase 2 period selector: `VALID_PERIODS`/`DEFAULT_PERIOD`
   (543/544), `normalize_period` (553), `compute_period_window` (596),
   `filter_rows_by_date_window` (636), `adapt_logged_row` (662),
   `aggregate_logged_muscles` (704).
4. Lines 721–751 — Phase 2 SFR: `compute_sfr` (735).

**[NEW]** These four concerns are independently testable and have almost no
call-graph overlap (SFR only calls into #1's classify function; period
selector doesn't touch #1/#2 tables at all). The file is a good candidate for
a **pure move-only split** (same spirit as the plan's WP2.1 for
`profile_estimator.py`) into e.g. `fatigue_core.py` / `fatigue_muscle.py` /
`fatigue_period.py` / `fatigue_sfr.py`, re-exported from `utils/fatigue.py`
for import stability. The plan doesn't currently propose this — flagging as a
candidate WP for whoever extends Phase 2 module-split work. **All numeric
tables listed above are protected per Rule 2 — a split must not touch a
single value.**

**[RISK] Duplicated "has any scored value" business rule.** `adapt_logged_row`
(662–701) computes `has_any_scored` over
`(scored_rir, scored_min, scored_max, scored_weight)` to decide whether a
logged row counts as 0 sets (skipped). The *exact same* four-field check is
re-implemented independently in `utils/fatigue_data.py::_stimulus_from_rows`
(fatigue_data.py:230–233). Two files must agree on what "a skipped set" means;
today they do, but nothing enforces it — a future edit to one is likely to
miss the other. Not a plan item; new finding.

**[NEW] `canonicalize_muscle_for_fatigue` (363–389)** re-uses
`volume_taxonomy.COARSE_TO_BASIC`/`canonical_pst` and layers one override
(the `Unassigned` sentinel must NOT fold into `Abdominals` the way
`volume_taxonomy` does for its own rollup invariant). This is a deliberate,
well-commented exception, but it means fatigue's muscle-bucketing correctness
depends on a mapping owned by a different module for a different purpose
(volume rollup) — a `volume_taxonomy` change could silently break fatigue
bucketing without any fatigue-specific test catching it unless
`tests/test_fatigue.py` pins the full alias table. Worth a coupling note for
any future `volume_taxonomy.py` refactor (Phase 2/WP2.x territory).

**[RISK] Six catalog muscle labels have no landing zone.** Comment at
336–335 states Front-Shoulder, Rear-Shoulder, Lower-Back, Hip-Adductors,
Middle-Traps, Neck are deliberately absent from `MUSCLE_VOLUME_LANDMARKS` and
render "—"/neutral. This is documented as intentional (Phase 3 follow-up) but
is effectively silent partial coverage — any exercise whose only tracked
muscle is one of these six always renders unranked. Not urgent, just a
gap worth carrying forward in any Phase-3-fatigue tracking doc.

**Minor**: `SFR_FATIGUE_ZERO_SENTINEL` (730) is just `None` — the name implies
a distinct sentinel value but it's the same `None` used everywhere else for
"absent". Harmless, mildly misleading naming.

---

## `utils/fatigue_data.py` (395 lines)

**Purpose**: DB query + page-context assembly layer sitting between the pure
`utils/fatigue.py` math and `routes/fatigue.py` / `routes/session_summary.py`
/ `routes/weekly_summary.py`. **[CONFIRMS-PLAN]** — this is a clean example of
the architecture the root CLAUDE.md prescribes (`routes` → `utils` business
logic → `DatabaseHandler`); no violations found.

**Two independent query surfaces, verified both are live (not dead code):**
- `load_planned_exercises` (53) — Phase-1 shape (no muscle columns). Consumed
  by `compute_session_fatigue_for_routine` (84) and `compute_weekly_fatigue`
  (112), which are in turn called from `routes/session_summary.py:101/104`
  and `routes/weekly_summary.py:91` respectively (badge integration on the
  summary pages).
- `load_planned_exercises_with_muscles` (134) / `load_logged_exercises_with_muscles`
  (158) — Phase-2 shape (adds 3 muscle columns), consumed only by
  `build_fatigue_page_context` (317), which backs the dedicated `/fatigue`
  page (`routes/fatigue.py`).

**[NEW]** These two query pairs run near-identical `LEFT JOIN exercises`
SQL against `user_selection`/`workout_log`, differing only in the SELECT
column list. Confirmed via grep this is *not* dead duplication — each is a
real, distinct caller — but it is duplicated SQL shape that a schema change
(e.g. renaming a joined column) has to be applied twice. Low priority; noting
for anyone doing a DB-layer consolidation pass.

**[RISK] Hardcoded effective-sets config for SFR stimulus.**
`_stimulus_from_rows` (208–251) always calls
`calculate_effective_sets(..., counting_mode=CountingMode.EFFECTIVE,
contribution_mode=ContributionMode.TOTAL)` regardless of whatever
Counting/Contribution mode the user has selected elsewhere (e.g. on
`/weekly_summary`). This is presumably intentional ("stimulus proxy," per the
docstring at fatigue_data.py:213-216) but means the SFR card's stimulus number
can silently diverge from what the user is looking at on the summary page in
the same session — worth a one-line doc note if not already covered in
`docs/fatigue_meter/PLANNING.md`.

**`build_fatigue_page_context` (317–395)** is a 78-line orchestration function
(load planned → aggregate → resolve period window → load logged → filter →
aggregate → SFR → assemble dict). Not a "god function" by this codebase's
standards (each step is a one-line call to an already-extracted helper), but
it is doing I/O, date-window math, and template-shaping all in one place.
Low-risk extract-method candidate if this file is ever split; not urgent.

**`_merge_muscle_rows` (265–314)**: sort/merge logic duplicates the sort key
tuple shape used by `fatigue.summarize_muscle_bars` (fatigue.py:521–528)
almost verbatim (`(0 if has_landmarks else 1, -pct, -score, name)`), just
applied to merged planned+logged rows instead of one side. Same "duplicated
tie-break rule in two files" pattern as the has-any-scored duplication above.
`[NEW]`

---

## `utils/fatigue_context.py` (389 lines)

**Purpose**: additive advisory layer for Workout Controls (Phase 2D-A/B),
reusing the shipped Fatigue Meter page builder rather than new math.
Docstring's guarantees (separate switch, default-off, no new fatigue math,
locked advisory copy) are all verifiably upheld by the code:
- `FATIGUE_CONTEXT_ADVISORY = "This does not change your suggestion."`
  (48) appears in every returned block (`_neutral_block` 165,
  `_block_from_page` 241) — **[CONFIRMS-PLAN]** the plan's protected-zone
  entry for this exact locked copy; verified present and unconditional,
  no code path can build a block without it.
- `attach_fatigue_context` (368–389) wraps the whole build in
  `try/except Exception` and only mutates the estimate dict on success —
  confirms the "pure decoration, can never break the estimate response"
  guarantee. `[CONFIRMS-PLAN]` (aligns with Rule 1, behavior-preserving /
  non-blocking informational surfaces per root CLAUDE.md §1 non-goals).

**Coupling**: imports `build_fatigue_page_context` from `fatigue_data.py`
(34) and re-runs the **entire planned+logged fatigue scan** per call. The
module's own docstring at 285–290 flags this as a known cost with a
documented follow-up ("a thin single-muscle read helper... if that ever
shows on the hot path"). `build_fatigue_context_batch` (296–365) is the
partial mitigation already shipped — it builds the page at most once per
batch instead of once per exercise. **[CONFIRMS-PLAN]** — no action needed,
this is self-aware, already-mitigated technical debt with its own docs
pointer; not something Phase 4's plan needs to pick up.

**`_neutral_block` vs `_block_from_page`**: both build the same 12-key
response dict independently (165–166, 228–242) rather than sharing a base
dict + overrides. Minor duplication; the two functions' key sets have
already drifted slightly in spirit (`_neutral_block` hardcodes `muscle: None`
and `has_landmarks: False`) so merging them would add a conditional branch
back — probably not worth doing. `[NEW]`, low priority.

**Settings table access** (`get_fatigue_context_settings` 61,
`set_fatigue_context_settings` 88) is a clean single-row upsert pattern
(`ON CONFLICT(id) DO UPDATE`), consistent with the rest of the codebase's
`DatabaseHandler` conventions. No issues found.

---

## `utils/progression_plan.py` (481 lines)

**Purpose**: double-progression suggestion engine for `/progression`, plus
`decide_progression_target` — the shared minimal decision function reused by
`utils/strength_calibration.py:38` (`from utils.progression_plan import
decide_progression_target`). **[CONFIRMS-PLAN]** — verified via grep this
cross-module reuse is real and matches the plan's protected-zone note
("estimator priority chain" + "double-progression decision logic" both name
this file); confirms the coupling the plan warns refactors not to touch.

**Two parallel suggestion pipelines, same core status logic**:
- `decide_progression_target` (99–130) — the newer, minimal, single-top-set
  API shared with the estimator. Calls `_get_progression_status` (70) +
  `_calculate_weight_increment` (39).
- `generate_progression_suggestions` (382–455) — the older, richer,
  multi-card suggestion generator for the `/progression` page UI. Also calls
  `_get_progression_status` and `_calculate_weight_increment`, then branches
  into `_build_primary_weight_suggestion` (182), `_build_primary_rep_suggestion`
  (210), `_build_maintenance_suggestion` (244),
  `_build_technique_and_volume_suggestions` (264), and
  `_build_manual_progression_options` (289).

Both pipelines correctly share the two core decision helpers — this is good,
not duplicated decision logic. `[CONFIRMS-PLAN]` (docstring at 109–120
explicitly states the intent: "do not duplicate these rules in callers").

**[RISK] Suspicious no-op branch in `_calculate_weight_increment` (39–51):**
```python
if current_weight < 20:
    return 2.5 if not is_novice else 2.5
else:
    return 5.0 if not is_novice else 2.5
```
The `<20kg` branch's ternary always evaluates to `2.5` regardless of
`is_novice` — the condition has no effect. This *may* be intentional (small
weights always get a small increment regardless of experience), but the
ternary as written reads as a bug: it looks like it should differentiate by
`is_novice` the same way the `>=20kg` branch does, but structurally cannot.
**Do not change the numeric behavior** (protected calibration logic per
Rule 2) — flagging purely as a readability/intent smell: either collapse to
`return 2.5` with a comment explaining why novice status doesn't matter under
20kg, or fix the logic if the flat 2.5 was actually a mistake. Owner decision
needed, not a refactor-safe cleanup.

**[NEW] Duplicated "Technique Improvement" suggestion literal.** The exact
same dict literal (type `technique`, same title/description/action/priority
text) is built twice: once inside `_build_technique_and_volume_suggestions`
(265–271) and once inline at the top of
`generate_plan_based_progression_suggestions` (361–367). A shared
`_technique_suggestion(exercise)` helper would remove the duplication
without touching any decision logic — pure extract, safe refactor candidate.

**`_analyze_consistency` (133–179)** iterates `history` twice in two separate
`for` loops (145–162 for `consecutive_at_top`, 165–173 for
`consecutive_below_min`), each with its own `break`. Not a bug — the two
counts are independent early-exit scans over the same list — but it's an
easy single-pass consolidation if this file is ever touched for other
reasons. Low priority.

**`save_progression_goal` (457–481)** uses direct dict indexing
(`data['exercise']`, `data['goal_type']`, ...) instead of `.get()` — will
raise `KeyError` (not a friendly validation error) if a route forgets to
supply a field. Every other read path in this file (and the sibling
`workout_log.py`/`fatigue.py`) favors `.get()` with defaults. Inconsistent
defensive-coding style; low risk since the one caller
(`routes/progression_plan.py`) presumably validates first, but worth noting
as a latent trap for a future caller.

---

## `utils/body_fat.py` (203 lines)

**Purpose**: pure BFP/BMI formulas (Navy method, BMI fallback, ACE category
bands, Jackson-Pollock ideal table) for `/body_composition`. No DB, no Flask
— cleanest file in this batch.

**[RISK] Documented but unenforced cross-language duplication.** The module
docstring (1–11) states plainly: *"Must match JS mirror... Any change to the
four public functions here... must be reflected verbatim in
`static/js/modules/body-composition.js`."* This is an honest, load-bearing
comment, but there is **no automated check** tying the two together — a
Python-side formula edit that forgets the JS mirror update would pass
`pytest` cleanly (verified: `tests/test_body_fat.py` only imports from
`utils.body_fat`, never cross-checks the JS file) and only surface as a
live-vs-submitted BFP mismatch a user would notice in the browser. This is a
cross-cutting pattern (see Cross-cutting seeds below), not unique to this
file — but worth flagging here since this is the most explicit instance of it
in the whole scan.

**Validation style**: `_check_range` (70–74) and `_normalize_gender` (61–67)
raise bare `ValueError` with a formatted message, consumed by routes (per the
docstring at 19–20: "routes translate that into a structured 4xx response").
Clean separation; no issues.

**`jackson_pollock_ideal` (175–203)**: linear interpolation over a fixed
8-row published table, clamped at both ends. Straightforward, well-commented,
matches the "reference tables" framing in the module docstring.

---

## `utils/workout_log.py` (153 lines)

**Purpose**: workout-log domain helpers (progression-indicator icons,
assisted-bodyweight handling, log fetch, simple progression check). Smallest
and least cohesive file in the batch — mixes UI-rendering metadata
(icon/class/title dicts for progression-indicator badges) with DB access and
a pure comparison helper in one 153-line module.

**[RISK] Hardcoded assisted-bodyweight exercise list.**
`ASSISTED_BODYWEIGHT_EXERCISES` (7–14) is a frozenset of 6 literal exercise
names (e.g. `"machine assisted chin up"`). This list has no relationship to
the exercise catalog's own classification columns (movement pattern,
equipment) — if a new assisted-bodyweight machine exercise is added to the
catalog, this frozenset must be manually updated or the progression-indicator
arrows silently invert (increasing assistance would show as "weight
increased" instead of "assistance increased"). No test enumerates catalog
exercises against this set to catch drift (`tests/test_workout_log_utils.py`
was not read this pass but is worth a follow-up check). Not itself a plan
item; flagging as a maintenance trap.

**`check_progression` (126–153)** uses direct bracket indexing
(`log_entry['scored_rir']`, etc.) rather than `.get()`, inconsistent with the
`.get()`-everywhere style of `fatigue.py`/`fatigue_data.py`. It also accepts
`log_entry` as either a dict-like or a row via `hasattr(log_entry, 'get')`
check at line 128 for `exercise_name` only — the rest of the function assumes
bracket access unconditionally, so a plain `sqlite3.Row` (which supports both
bracket and no `.get()`) works, but a raw dict missing a key raises
`KeyError` rather than treating it as `None`. Minor internal inconsistency
between line 128's dual-path handling and the rest of the function's
single-path assumption.

**[RISK] Silent failure conflation in `get_workout_logs` (93–124).** The
`try/except Exception` at 119–124 logs and returns `[]` on any DB error —
identical to what an empty, healthy workout log looks like. A caller/template
cannot distinguish "no logs yet" from "the query broke." This matches a
defensive pattern seen elsewhere in the codebase, but is worth flagging since
it degrades an error into a false-empty-state rather than surfacing it (no
`error_response()` path exists here since this is a utils-layer function, not
a route — the swallow happens before the route layer even gets a chance to
translate it into a 5xx).

---

## Cross-cutting seeds

1. **Multi-phase files with banner-comment-delimited sections are a repeat
   pattern** — `fatigue.py`'s four concerns (core/muscle/period/SFR) mirror
   the same "shipped incrementally, never re-organized" shape the plan
   already diagnosed in `profile_estimator.py` (WP2.1) and
   `weekly_summary.py` (WP2.3). `fatigue.py` is a strong candidate for the
   same move-only-split treatment; not currently in the plan.
2. **"Has any scored value" / skip-if-unscored is duplicated logic across
   `utils/fatigue.py::adapt_logged_row` and
   `utils/fatigue_data.py::_stimulus_from_rows`**, and the muscle-bar sort
   tie-break tuple is duplicated across `utils/fatigue.py::summarize_muscle_bars`
   and `utils/fatigue_data.py::_merge_muscle_rows`. Neither is plan-tracked.
   A shared helper (e.g. `_is_row_scored(row)` and `_muscle_sort_key(...)`)
   would remove both without touching any protected number.
3. **Undocumented / unenforced dual-source-of-truth risk**: `body_fat.py`'s
   explicit "must match JS mirror" comment is the clearest instance found
   this phase of a broader pattern worth a repo-wide grep in a later phase —
   any Python calculation module whose docstring or comments mention a JS
   mirror, with zero automated parity test, is a silent-drift risk.
4. **`.get()`-vs-bracket-indexing inconsistency** shows up across this batch:
   `fatigue.py`/`fatigue_data.py` are consistently `.get()`-defensive;
   `progression_plan.py::save_progression_goal` and
   `workout_log.py::check_progression` use bare bracket indexing. Not a bug
   by itself (callers currently guarantee the keys exist), but a
   codebase-wide convention pass could standardize this.
5. **Hardcoded classification lists divorced from the exercise catalog**:
   `workout_log.py::ASSISTED_BODYWEIGHT_EXERCISES` (6 literal names) and
   `fatigue.py`'s six catalog labels missing from `MUSCLE_VOLUME_LANDMARKS`
   are both instances of "a fixed list must stay in sync with a growing
   catalog, with nothing enforcing it." Worth a single follow-up doc noting
   all such lists repo-wide (out of scope for this phase, but seeding it for
   whoever does the catalog-invariants pass mentioned in
   `tests/test_catalog_invariants.py`).
