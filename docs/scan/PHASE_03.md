# Phase 3 — Volume & Summary Calculations

Read line-by-line in full: `utils/effective_sets.py` (576), `utils/weekly_summary.py` (465),
`utils/session_summary.py` (300), `utils/volume_progress.py` (508),
`utils/movement_patterns.py` (507), `utils/volume_taxonomy.py` (328),
`utils/volume_classifier.py` (106), `utils/volume_ai.py` (72), `utils/volume_export.py` (56).
Also read `utils/CLAUDE.md`.

**Note on the task brief's reference plan**: `docs/REFACTOR_PLAN.md` does not exist in this
worktree (checked `D:/development/HT-scan/docs/` — no such file, and not in `docs/archive/`
either). This scan's actual grep-based predecessor artifacts are `docs/SCAN_FINDINGS.md` /
`docs/SCAN_PROGRESS.md`, which list Phase 3's files but carry no WP2.3/taxonomy "protected
zone" annotations yet (Phase 3 section is empty, pre-this-write). So there is nothing to
literally CONFIRM/CONTRADICT by ID. Where the brief's description matches what a WP2.3-style
recommendation would plausibly say (decompose `calculate_weekly_summary` /
`calculate_pattern_coverage`; treat volume-taxonomy as protected), I've tagged the finding
`[CONFIRMS-PLAN]` on the merits of the code itself, not against a literal document. Flagging
this so synthesis doesn't assume a WP2.3 doc was actually cross-checked.

---

## utils/effective_sets.py (576 lines)

**Purpose**: Core, protected calculation engine for hypertrophy-relevant "effective sets" —
converts raw sets into a weighted number via effort factor (RIR/RPE), rep-range factor, and
muscle-contribution weight (primary/secondary/tertiary). Declared informational-only
(`effective_sets.py:6-7`), matches root CLAUDE.md §1 non-goals and `utils/CLAUDE.md` gotcha.

**Key functions**:
- `parse_counting_mode` / `parse_contribution_mode` (39-56) — string→enum parsers, default to
  EFFECTIVE / TOTAL respectively on missing/bad input. Simple, no smell.
- `get_effort_factor` (148-186) — RIR preferred over RPE; RPE→RIR via `10 - rpe`; clamps to
  [0,10]; bucket lookup against `EFFORT_FACTOR_BUCKETS` (64-69).
- `get_rep_range_factor` (189-224) — averages min/max reps, bucket lookup against
  `REP_RANGE_FACTOR_BUCKETS` (75-81).
- `calculate_effective_sets` (227-304) — the single per-row entry point. In `CountingMode.RAW`
  it **skips weighting entirely** (267-270: factors forced to 1.0) — i.e. RAW mode is not "raw
  sets converted through effective math and then displayed as raw", it is a genuinely different,
  unweighted code path. `ContributionMode.DIRECT_ONLY` only populates
  `muscle_contributions` for the **primary** muscle (288-293); secondary/tertiary keys are
  simply absent from the dict in that mode (not zeroed — absent).
- `get_session_volume_warning` / `get_weekly_volume_class` (307-346) — bucket classifiers,
  thresholds in module constants (91-103). Note session thresholds are units of *effective*
  sets in a single session, weekly thresholds are *effective sets per week* — same shape of
  bucket-dict pattern reused for two different scales, easy to mix up if someone future adds a
  third scale without renaming.
- `calculate_training_frequency`, `calculate_volume_distribution`,
  `aggregate_session_volumes`, `aggregate_weekly_volumes` (349-518) — a **second, generic
  aggregation pipeline** operating on `EffectiveSetResult`/`SessionVolumeResult`/
  `WeeklyVolumeResult` dataclasses (113-141). **`[NEW][RISK]` This entire pipeline is dead in
  production.** Verified via grep: `aggregate_session_volumes`, `aggregate_weekly_volumes`,
  `calculate_training_frequency`, `calculate_volume_distribution` have zero callers outside
  `tests/test_effective_sets.py`. Neither `weekly_summary.py` nor `session_summary.py` — the
  two modules that actually power `/weekly_summary` and `/session_summary` — call into this
  aggregation layer. They re-derive equivalent per-muscle sums by hand instead (see below).
  Exercised only by direct unit tests against `effective_sets.py`, never through a route or the
  modules that appear to be its intended callers. This is a full duplicate calculation surface,
  not just a couple of helper functions.
- `rpe_to_rir` / `rir_to_rpe` (525-546) — same conversion the RAW inline in `get_effort_factor`
  (`int(round(10 - rpe))`) duplicates locally rather than calling `rpe_to_rir`. **`[NEW]`**
  Trivial duplication (one-line formula), low risk, but another instance of "the reusable
  helper exists but isn't reused."
- `format_volume_summary` (549-575) — API-shaping helper; also has zero non-test callers
  (grep found only `tests/test_effective_sets.py`). `[NEW]`

**Coupling**: Pure module — no DB, no Flask. Imported by `weekly_summary.py`,
`session_summary.py`, `volume_classifier.py` (for the enums/thresholds only). This is the
correct dependency direction (calculation core → higher-level aggregators), but the higher
aggregators only reach for the low-level per-row function (`calculate_effective_sets`) and the
classifier functions — never the aggregate_* layer that appears purpose-built for them.

**Smells/risks**:
- `[RISK]` Two independently-maintained aggregation implementations of the same math: the
  dataclass-based `aggregate_session_volumes`/`aggregate_weekly_volumes` here, and the
  dict-of-dicts hand-rolled aggregation in `weekly_summary.py`/`session_summary.py`. If the
  effective-sets formula ever needs to change control flow (not just a bucket constant), a
  future editor patching `calculate_effective_sets` could reasonably believe
  `aggregate_weekly_volumes` is where weekly totals come from and patch/test that instead of
  the actual live path — silent behavior drift.
- `aggregate_session_volumes`'s raw-set "reverse engineering" (430-438: `ratio = eff_sets /
  effective_sets; raw_contribution = raw_sets * ratio`) is a fragile way to recover per-muscle
  raw sets from a per-muscle effective share — it divides back out factors it just multiplied
  in. Since it's dead code this isn't a live risk, but if anyone resurrects this path it's a
  precision/edge-case (effective_sets==0) trap already guarded (436-437) but conceptually
  backwards versus just tracking raw contributions forward like `weekly_summary.py` does.

**Dead code**: `aggregate_session_volumes`, `aggregate_weekly_volumes`,
`calculate_training_frequency`, `calculate_volume_distribution`, `format_volume_summary` —
all reachable only from their own unit tests, not from any route/module in the app. `[NEW][RISK]`

---

## utils/weekly_summary.py (465 lines)

**Purpose**: Powers `/weekly_summary` (route: `routes/weekly_summary.py`) and parts of
`routes/exports.py`. Three independent responsibilities bolted into one file:
`calculate_weekly_summary` (volume aggregation), `calculate_exercise_categories` (Mechanic/
Utility/Force/Difficulty counts), `calculate_isolated_muscles_stats` (isolated-muscle SQL
rollup), `calculate_pattern_coverage` (movement-pattern balance analysis + warnings).

**Key functions**:
- `calculate_weekly_summary` (36-214, **179 lines**) — `[CONFIRMS-PLAN]` genuinely a "monster
  function" by any measure: one SQL query, then a per-row loop computing both effective *and*
  raw weighted sets/reps/volume for every muscle role (primary/secondary/tertiary) with
  DIRECT_ONLY/TOTAL branching inline (123-131), then a second full pass building the output
  dict per muscle (164-212) with ~15 output keys mixing "mode-dependent primary" fields and
  "always both" fields. The `method` parameter (36-38, 62) is accepted purely for backward
  compatibility and is **never used** — `_ = method` (62) is a no-op assignment whose only
  purpose is suppressing an unused-argument lint; callers still pass `'Total'` literally
  (`routes/exports.py:350,653`) or a caller-supplied `method` variable
  (`routes/exports.py:559`) that has no effect on the result. `[NEW]` This is a live, exercised
  dead parameter, not just an unused local — every call site pays the readability cost of
  passing an argument that does nothing.
  - Frequency fallback logic (177-183): `session_count = frequency if frequency > 0 else
    (len(global_sessions) or 1)` — when a muscle has zero qualifying sessions (all under the
    1.0-effective-set frequency floor) it silently divides by the *total distinct routine
    count* instead, or by 1 if there are no routines at all. This reuses one already-computed
    variable (`session_count`) for two semantically different denominators depending on a
    branch; `sets_per_session` for a muscle with real weekly volume but no single session
    crossing the 1.0 threshold gets a value with a different meaning (avg-across-all-routines,
    not avg-per-actual-training-day). `[RISK]` Correct-by-design per the `[NEW]` comment at
    177-179 (intentional fallback for backward compat), but worth flagging as a subtle
    semantic seam if anyone changes routine handling.
  - `legacy_volume_class = get_volume_class(weekly_sets)` (187) computed from
    `utils/volume_classifier.py`'s **raw-set thresholds**, stored under the key
    `'volume_class'`, while `'status'` (193) comes from the **effective-set** classifier via
    `EFFECTIVE_STATUS_MAP`. Two different classification systems co-exist in the same output
    row under near-synonymous names (`status` vs `volume_class`) — legacy CSS-class field kept
    alongside the effective-sets-driven one. `[NEW][RISK]` Template/JS consumers must know
    which of the two fields is "real" for a given UI purpose; a low volume by raw-set count
    could show a different status than by effective-set count for the same muscle (e.g. heavy
    low-RIR failure sets look "low" raw but "medium" effective).
- `calculate_exercise_categories` (217-263) — straightforward SQL + in-memory grouping into 4
  fixed categories (Mechanic/Utility/Force/Difficulty). No smell.
- `calculate_isolated_muscles_stats` (266-289) — pure SQL aggregation via
  `exercise_isolated_muscles` join table; wrapped in try/except logging and returning `[]` on
  DB error, unlike the other three functions in this file which let exceptions propagate
  (`calculate_weekly_summary`, `calculate_exercise_categories` have no try/except at all).
  `[NEW]` Inconsistent error-handling policy within one module — three of four public
  functions here have zero error handling, one swallows and logs. Same asymmetry recurs in
  `calculate_pattern_coverage` (318-323, has try/except) vs `calculate_weekly_summary` (has
  none) — 2-of-4 functions silently degrade to empty results on DB errors, 2-of-4 propagate.
- `calculate_pattern_coverage` (292-464, **172 lines**) — `[CONFIRMS-PLAN]` the other monster
  function: query, per-row pattern classification with an inline **duplicate** of
  `movement_patterns.classify_exercise`'s muscle-based fallback logic (351-372, hand-rolled
  string containment checks — `'quad' in primary_muscle`, `'chest' in primary_muscle`, etc.)
  rather than calling `utils.movement_patterns.classify_exercise`, which already does
  name+muscle classification with a real keyword table (`movement_patterns.py:470-505`).
  `[NEW][RISK]` Two different, unsynchronized muscle→pattern mapping tables exist:
  `movement_patterns.PatternMapping.MUSCLE_GROUP_PATTERNS` (23 explicit muscle keys) and this
  inline elif-chain (7 substring checks, lossier — e.g. `'lat' in primary_muscle or 'back' in
  primary_muscle` folds Latissimus Dorsi and Upper Back into one bucket that
  `movement_patterns.py` keeps split as `VERTICAL_PULL` vs `HORIZONTAL_PULL`). Changing pattern
  taxonomy in one place will not update the other — a real correctness fork, not just a style
  duplication.
  - Then four independent warning generators appended sequentially (378-457): missing-core-
    pattern, sets-per-routine min/max, isolation-vs-compound skew (`total_isolation >
    total_compound * 1.5`), and push/pull ratio (`> 1.5` / `< 0.67`) — each a self-contained
    block with its own magic-number threshold, none reused elsewhere, none extracted to
    named constants except `MIN_SETS`/`MAX_SETS` (397-398). `CORE_PATTERNS` dict (326-333) is
    local to this function only — not shared with `movement_patterns.py`'s pattern enum despite
    describing the same six patterns by string literal instead of the `MovementPattern` enum
    values.

**Coupling**: imports `DatabaseHandler`, `volume_classifier.get_volume_class`,
`effective_sets.{CountingMode,ContributionMode,calculate_effective_sets,
get_weekly_volume_class,MUSCLE_CONTRIBUTION_WEIGHTS}`. `session_summary.py` imports
`STATUS_MAP`/`EFFECTIVE_STATUS_MAP` from here (confirmed at `utils/CLAUDE.md:24`, and verified
by reading `session_summary.py:9` — imports `EFFECTIVE_STATUS_MAP` only, not `STATUS_MAP`,
which as of this reading has **zero consumers** — grep shows `STATUS_MAP` defined at line 19
and referenced nowhere else in `utils/` or `routes/`. `[NEW]` `STATUS_MAP` appears to be a
leftover from before the effective-sets rework (its keys `'low-volume'`/`'ultra-volume'` match
`volume_classifier._VOLUME_TIERS` css-class strings, i.e. the pre-effective-sets naming), fully
superseded by `EFFECTIVE_STATUS_MAP`.

**Dead code**: `STATUS_MAP` (19-24) — defined, exported implicitly via module namespace, never
imported or referenced by any other module. `[NEW]`

---

## utils/session_summary.py (300 lines)

**Purpose**: Per-routine, per-date-window mirror of `weekly_summary.py`'s volume aggregation,
but decomposed into five smaller private helpers plus one public entry point — noticeably
better factored than `weekly_summary.calculate_weekly_summary`.

**Key functions**:
- `_build_plan_query` / `_build_log_query` (21-69) — parametrized SQL builders (routine +
  date-range filters). Clean, injection-safe (placeholders, not string interpolation of
  values).
- `_aggregate_muscle_volumes` (72-156) — **near-line-for-line duplicate** of the per-row
  weighting loop in `weekly_summary.calculate_weekly_summary` (lines 87-159 there vs 88-154
  here): same `avg_reps` calc, same `calculate_effective_sets` call shape, same
  `contributions` list-of-tuples-with-weights pattern, same DIRECT_ONLY skip-and-reweight
  branch (126-129 here ≡ 128-131 in weekly_summary.py). `[NEW][RISK]` This is the single
  clearest duplicated-calculation-logic instance across the two files the task brief called
  out. A bugfix or behavior change to "how a row's sets become per-muscle raw+effective
  contributions" must be applied in both places by hand; nothing enforces they stay identical
  (they already differ subtly — see below).
  - **Behavioral difference vs weekly_summary**: here, routine defaults to `'Unassigned'`
    (90: `row.get('routine') or 'Unassigned'`) when null; `weekly_summary.py` has no such
    fallback (uses `row.get('routine')` directly at line 89, then only uses it for the
    `sessions_by_muscle` frequency dict, guarded by `if routine:` at line 158 — a null routine
    there is silently excluded from frequency tracking rather than bucketed as "Unassigned").
    `[NEW][RISK]` Genuine semantic drift between the two "duplicate" implementations: a
    `user_selection` row with `routine IS NULL` is visible (as "Unassigned") in per-routine
    session-summary output but invisible from weekly-summary's frequency count. Root
    CLAUDE.md's "Unassigned-bucket invariant" language from the fatigue-meter work (memory:
    `project_fatigue_meter_parked.md`) suggests this null-routine-bucketing pattern is an
    established convention elsewhere in the codebase (fatigue.py) that weekly_summary.py does
    not follow — worth checking in Phase 4 whether fatigue.py's Unassigned handling matches
    session_summary.py's or introduces a third variant.
- `_aggregate_session_dates` (159-178) — turns `workout_log` rows into
  `{routine: {muscle: {distinct_date_strings}}}` via the `selection_to_muscles` map built in
  the previous step. Uses date-string truncation (`str(created_at)[:10]`) rather than a real
  date parse — fragile if `created_at` format ever changes, but consistent with how dates are
  handled elsewhere in this codebase (not itself new).
- `_build_summary_output` (181-248) — output formatting; unlike `weekly_summary.py` this
  correctly distinguishes "no logged sessions yet" (`has_logged_sessions=False`,
  `sets_per_session=None`, `warning_level='no_data'`) from "sessions exist but volume is OK"
  — a distinction `weekly_summary.py`'s `calculate_weekly_summary` does not make (it always
  produces a numeric `sets_per_session` via the routine-count fallback described above, never
  `None`/`'no_data'`). `[NEW]` Two summary surfaces with materially different "no data yet"
  semantics for what a user would read as the same concept.
- `calculate_session_summary` (251-299) — thin orchestrator calling the four helpers above in
  sequence. This decomposition (unlike `weekly_summary.py`'s monolith) is exactly the pattern a
  WP2.3-style "decompose the monster function" recommendation would produce — **this file is
  effectively evidence for what `weekly_summary.calculate_weekly_summary` should look like
  post-refactor.** `[CONFIRMS-PLAN]`

**Coupling**: imports `DatabaseHandler`, `volume_classifier.get_volume_class`,
`weekly_summary.EFFECTIVE_STATUS_MAP`, and the same `effective_sets` symbols as
`weekly_summary.py` plus `VolumeWarningLevel`/`get_session_volume_warning` (this file uses the
session-level warning classifier; `weekly_summary.py` does not surface per-session warnings at
all — another asymmetry between the two "mirror" modules).

**Dead code**: none found in this file.

---

## utils/volume_progress.py (508 lines)

**Purpose**: Powers the Plan-tab "volume progress" panel — aggregates *planned* (not logged)
sets from `user_selection` into Basic or Advanced muscle-taxonomy buckets and compares against
an "active" `volume_plans` target row. This is the consumer of `volume_taxonomy.py`'s mapping
tables and the most structurally careful file in this phase.

**Key functions**:
- `fetch_planned_rows` (123-168) — single `GROUP_CONCAT` query joining
  `exercise_isolated_muscles` per exercise; prefers the mapping-table tokens over the legacy
  `advanced_isolated_muscles` CSV column (151-158), tracking `csv_fallback_count` in
  diagnostics when it falls back. Accepts an optional externally-owned `db` handle (164) to
  allow composition inside a single transaction from `get_volume_progress` — good pattern,
  avoids nested `DatabaseHandler` context managers.
- `_advanced_targets_for_token` / `_record_token_resolution` (74-88, 171-188) — three-way
  return contract: `None` = explicitly ignored token (in `taxonomy.IGNORED_TOKENS`), `()` =
  unresolvable (unmapped, diagnosed), non-empty tuple = resolved target(s). `[NEW]` This
  `None`-vs-`()` distinction is load-bearing (callers branch on `if targets is None` vs `if
  not targets`) but is easy to miss on a skim — a maintainer adding a new call site who treats
  `None` and `()` as equivalent falsy values would silently misclassify ignored tokens as
  unmapped-diagnostic ones, changing what shows up in the diagnostics panel without changing
  computed totals. Comment coverage here is good (inline comments explain the states) so this
  is a documentation/contract clarity risk rather than an active bug.
- `_aggregate_blank_pst_row` (191-249) — implements only the `BLANK_PST_STRATEGY ==
  "isolated_only"` path fully (default; hardcoded in `volume_taxonomy.py:85`); the `"exclude"`
  path is a one-line early return (201-202), and `"backfill"` (203-205) just logs a warning and
  returns without aggregating — i.e. **`"backfill"` is a documented-but-unimplemented
  strategy**: choosing it in `volume_taxonomy.BLANK_PST_STRATEGY` would silently drop all
  blank-P/S/T rows from volume totals while logging a warning per row, not actually backfill
  anything. `[NEW][RISK]` Since the constant is hardcoded to `"isolated_only"` in production
  and only flipped via `monkeypatch` in `tests/test_volume_progress.py` (confirmed: grep shows
  `monkeypatch.setattr(taxonomy, "BLANK_PST_STRATEGY", "exclude")` — `"backfill"` is not
  exercised by any test at all), this is currently harmless, but the module docstring's
  framing ("Phase 0 source of truth... decisions confirmed by the user") implies these are
  supported modes, not just documentation of a decision that was never fully executed for one
  of the three named options.
- `_aggregate_advanced_primary` (252-295) — enforces that isolated-muscle tokens on a primary
  row must belong to the same coarse-muscle "family" as the coarse primary value itself
  (271-272: `target_basics == {coarse_basic}`), else the token is rejected
  (`diagnostics["rejected_tokens"]`) and a representative advanced fallback is used instead
  (291-293). This is a real safety net against bad/mismatched catalog data (e.g. an exercise
  whose primary muscle is "Chest" but has an isolated-muscle token pointing at a bicep
  splitter) — well-reasoned, not a smell.
- `aggregate_planned_sets` (298-345) — orchestrator; branches basic vs advanced mode, handles
  blank-P/S/T rows vs normal P/S/T rows, applies `ROLE_WEIGHTS` (15-19, identical values to
  `effective_sets.MUSCLE_CONTRIBUTION_WEIGHTS` — 1.0/0.5/0.25 — but a **separately-defined
  constant**, not imported/shared). `[NEW]` Same primary/secondary/tertiary weighting triple
  defined independently in two modules (`effective_sets.py:84-88` and
  `volume_progress.py:15-19`) with matching values today; nothing enforces they stay in sync if
  either the design changes the weighting scheme.
- `activate_volume_plan` / `deactivate_volume_plan` (348-382) — the only two functions in this
  phase that do writes; `activate_volume_plan` runs two UPDATEs plus a rowcount check inside a
  manual `commit=False`/`connection.rollback()`/`connection.commit()` sequence (355-369) rather
  than relying on `DatabaseHandler`'s own transaction handling — reasonable given it needs
  atomicity across two statements with a rowcount-based abort condition, but it's the one place
  in this phase reaching past the `db.execute_query()` convenience wrapper into raw
  `db.connection` methods. Not itself wrong, just worth flagging as a pattern inconsistent with
  the rest of the file (and the rest of this phase generally uses `db.execute_query`/
  `fetch_all`/`fetch_one` exclusively).
- `_classify_target_status` / `_classify_progress_status` (385-413) — pure classifiers, no
  smell; thresholds (`DEFAULT_RECOMMENDED_RANGES`, 21-24: flat 12–20 for every muscle) are a
  simplification flagged nowhere in-code as provisional, but that's a product-calibration
  question, not a code-structure one — out of scope for this pass per the "don't touch the
  math" instruction.
- `get_volume_progress` (416-507) — orchestrator; the `all_muscles` ordering logic (455-468)
  builds a list via two passes (canonical mode order first, then any leftover muscle sorted
  alphabetically) filtered by "has a target or has planned volume" — correct but a little
  fiddly; would read more clearly as a single sorted-set comprehension, though this is a
  polish note, not a bug.

**Coupling**: `DatabaseHandler`, `utils.volume_taxonomy as taxonomy` (module-level import, used
throughout via `taxonomy.X` rather than named imports — makes call sites explicit about which
module owns which constant, good practice given how many taxonomy tables exist). No import
from `effective_sets.py` or `weekly_summary.py` at all — this module is a fully independent
third aggregation pipeline (planned sets, not logged/session sets), which is appropriate given
its distinct product purpose (Plan-tab targets vs Weekly/Session logged-volume views), but
means there are now **three** separate "loop over user_selection rows and weight by
primary/secondary/tertiary" implementations across this phase's files
(`weekly_summary.calculate_weekly_summary`, `session_summary._aggregate_muscle_volumes`,
`volume_progress.aggregate_planned_sets`) with three different weighting-constant sources
(`effective_sets.MUSCLE_CONTRIBUTION_WEIGHTS` used by the first two, `volume_progress.
ROLE_WEIGHTS` by the third). `[NEW][RISK]`

**Dead code**: none found; `"backfill"` strategy branch is reachable-but-inert dead logic
(see above) rather than fully unreachable code.

---

## utils/movement_patterns.py (507 lines)

**Purpose**: Static taxonomy + keyword-matching classifier used by the starter-plan generator
(`utils/plan_generator.py`, Phase 6) to slot exercises into movement patterns
(squat/hinge/push/pull/core/isolation) and by `utils/db_initializer.py` /
`scripts/fatigue_movement_pattern_cleanup*.py` for one-off backfill/cleanup passes. Almost
entirely declarative data (dataclasses full of dict literals) plus one real function.

**Key functions/data**:
- `MovementCategory`, `MovementPattern`, `MovementSubpattern` (14-85) — three string enums.
  `[NEW][RISK]` **`MovementCategory` is fully dead** — grep across the whole worktree (code +
  tests) finds it defined at line 14 and never referenced anywhere else, including in this same
  file. `MovementPattern` and `MovementSubpattern` are both used extensively (in
  `PatternMapping`, `SESSION_BLUEPRINTS`, `classify_exercise`, and by
  `plan_generator.py`/`test_plan_generator.py`/`test_pattern_coverage.py`), so this is a
  narrowly-scoped dead enum, not a broader problem with the taxonomy.
- `PatternMapping.NAME_KEYWORDS` (94-199) — ~90 keyword→(pattern, subpattern) entries, matched
  longest-first in `classify_exercise` (492) to avoid short keywords (`"squat"`) pre-empting
  more specific ones (`"bulgarian"`, `"split squat"`). Correct approach for substring matching,
  but it's O(n) keyword scan per exercise name with no early-exit structure (a trie or
  length-bucketed dict would be faster) — irrelevant at current catalog sizes (this runs at
  plan-generation and DB-init time, not per-request), so purely a note, not a risk.
- `PatternMapping.MUSCLE_GROUP_PATTERNS` (203-237) — 23-entry muscle→pattern fallback used only
  when no name keyword matches (500-503). **This is the table that
  `weekly_summary.calculate_pattern_coverage`'s inline elif-chain (351-372) duplicates and
  diverges from** — see the weekly_summary.py section above for specifics. `[RISK]`
- `classify_exercise` (470-505) — the only real function in the file; name-keyword-first,
  muscle-group-fallback, `(None, None)` if nothing matches. Instantiates a fresh
  `PatternMapping()` dataclass **on every call** (486) purely to read its two dict fields
  (which are static `field(default_factory=lambda: {...})` literals, i.e. rebuilt from scratch
  every single call rather than being module-level constants). `[NEW][RISK]` Every
  `classify_exercise()` call rebuilds two dicts totaling ~113 entries from the
  `default_factory` lambdas. Not a functional bug, but a real, avoidable per-call cost — this
  is invoked once per exercise during plan generation and DB-init backfill passes
  (`db_initializer.py:600`), so for a catalog of hundreds/thousands of exercises this is
  hundreds/thousands of redundant dict-literal constructions instead of one shared table. An
  easy, safe, high-value fix (hoist `NAME_KEYWORDS`/`MUSCLE_GROUP_PATTERNS` to true module-level
  constants) — flagging for synthesis even though it's marginal at today's data volume, since
  it's low-risk-to-fix and the phase brief allows documenting such observations.
- `SESSION_BLUEPRINTS` (268-409) — the 1/2/3/4/5-day session template tables consumed by
  `plan_generator.py` (Phase 6 territory; noted here only because it lives in this file).
  Pure data, extensive but not smelly — each day-count's slots are hand-curated, not generated
  from a smaller rule set, so adding a 6-day split means hand-writing another dict block.
- `PrescriptionRules` (412-467) — `SETS_BY_ROLE` (417-423) has identical values across all
  three experience levels (`{"main": 3, "accessory": 2}` for novice/intermediate/advanced) with
  comments admitting the level-based differentiation isn't implemented yet ("Can go 3-4 for
  main", "Can scale down with volume_scale") — a scaffold for a feature that doesn't exist yet.
  `[NEW]` Not dead code (the dict is real and consumed by `plan_generator.py`), but the
  per-level keys currently carry no information (three identical dicts) — worth noting as
  "structure ahead of behavior" rather than a defect.
- `ENVIRONMENT_EQUIPMENT` (241-251), `HOME_BASIC_EQUIPMENT` (255) — equipment-set constants.
  `ENVIRONMENT_EQUIPMENT` is consumed by `plan_generator.py:401`. **`HOME_BASIC_EQUIPMENT` is
  fully dead** — grep across the whole worktree (code + tests) finds only its own definition,
  no consumer anywhere. `[NEW][RISK]`

**Coupling**: no DB, no Flask — pure data + one classifier function, correctly a leaf module.
Consumed by `plan_generator.py` (Phase 6), `db_initializer.py` (one-time classification during
schema init/backfill), and two standalone `scripts/fatigue_movement_pattern_cleanup*.py`
maintenance scripts (Phase 7/22 territory).

**Dead code**: `MovementCategory` enum (14-19), `HOME_BASIC_EQUIPMENT` (255) — both confirmed
zero-consumer via full-worktree grep (code and tests).

---

## utils/volume_taxonomy.py (328 lines)

**Purpose**: "Phase 0 source of truth" (per its own docstring, 1-8) for the Plan↔Distribute
muscle taxonomy — Basic (18 muscles) vs Advanced (31 splitter-level muscles) bucket lists, plus
five different lookup/normalization tables bridging catalog muscle-group strings, isolated-
muscle tokens, and the two taxonomy levels. This is unambiguously a **protected calculation/
data zone**: every non-obvious mapping choice is annotated with a `# Decision (Phase 0 §X.Y)`
comment citing an external planning doc (now archived at
`docs/archive/plan-volume-integration/PLAN_VOLUME_INTEGRATION_PLANNING.md` /
`_EXECUTION.md`), and changing any single mapping entry changes what a user's planned volume
"counts as" for a given muscle without changing any UI or query — pure silent-recalculation
risk if edited casually. `[CONFIRMS-PLAN]` treating this file as a protected zone is correct;
this scan found no bugs in it, only one dead-code note below.

**Key data/functions**:
- `BASIC_MUSCLE_GROUPS` (18-37), `ADVANCED_MUSCLE_GROUPS` (39-81) — the two canonical ordered
  lists; order matters downstream (`volume_progress._mode_muscles` returns these lists directly
  and `get_volume_progress` uses list order to decide default row ordering before falling back
  to alphabetical for extras).
- `COARSE_TO_BASIC` / `COARSE_TO_REPRESENTATIVE_ADVANCED` (88-170) — two ~40-entry dicts mapping
  raw catalog `primary/secondary/tertiary_muscle_group` strings to Basic and (a single
  representative) Advanced bucket respectively. Both dicts must stay in sync key-for-key (same
  ~40 coarse names) since `volume_progress.py` looks values up in both depending on mode — no
  automated check enforces this parity today (e.g. a test asserting `COARSE_TO_BASIC.keys() ==
  COARSE_TO_REPRESENTATIVE_ADVANCED.keys()` doesn't exist in what this phase read; would need
  to check `tests/test_volume_taxonomy.py` in Phase 21 to confirm). `[NEW]` Flagging as a
  candidate parity-test gap, not a proven bug — the two dicts do appear to have matching key
  sets on manual inspection (both start with "Abdominals"/"Abs/Core"/"Back"/... and end with
  matching entries), but nothing in this file enforces that invariant going forward.
- `ADVANCED_TO_BASIC` (172-206) — inverse of Advanced→Basic (31 entries, one per
  `ADVANCED_MUSCLE_GROUPS` item) — a plain dict, but only accessed through the wrapper function
  `advanced_to_basic()` (318-320) which does a raw `[advanced]` lookup (will `KeyError` on an
  unmapped key rather than returning `None`) — different failure mode than every other lookup
  in this file, which use `.get()` with `None`/`()`/empty-tuple fallbacks. `[NEW]` Minor API
  inconsistency: this is the only accessor in the module that can raise instead of returning a
  sentinel, and it's also the only piece of this file **not called from production code at
  all** — see dead-code note.
- `DISTRIBUTED_UMBRELLA_TOKENS` (208-212) — currently a single entry (`"quadriceps"` splits
  across three advanced quad buckets); `expand_umbrella()` (323-325) is the generic accessor
  for future additions to this table.
- `TOKEN_TO_ADVANCED` (214-279) — the largest table (~65 entries), isolated-muscle-token →
  Advanced-bucket-or-`None`; `IGNORED_TOKENS` (281-283) is derived from it as a `frozenset`
  comprehension over entries whose value is `None` (splenius/sternocleidomastoid — "no
  dedicated advanced neck slider exists today", comment at 276). Clean derivation, no
  duplication.
- `_PST_ALIASES` (286-297), `canonical_pst()` (300-307) — normalizes raw coarse muscle strings
  (case/hyphen variants) before dict lookup; `normalize_isolated_token()` (310-315) does the
  equivalent for isolated tokens (lowercase, underscore→hyphen, collapse repeated hyphens,
  strip leading/trailing hyphens).
- `advanced_to_basic()` (318-320) — **`[CONFIRMS-PLAN]` this is the "test-enshrined dead code"
  the task brief asked to watch for.** Confirmed via full-worktree grep: its only non-definition
  reference is `tests/test_volume_taxonomy.py:175` (`assert advanced_to_basic("lower-trapezius")
  == "Middle-Traps"`) and a mention in the archived planning doc
  (`docs/archive/plan-volume-integration/PLAN_VOLUME_INTEGRATION_EXECUTION.md:759`, which
  explicitly frames it as "pins decisions as executable code" — i.e. it was deliberately written
  as a test-only assertion helper, not intended for runtime use). `volume_progress.py` never
  calls `taxonomy.advanced_to_basic()` — it inlines the equivalent lookup directly as
  `taxonomy.ADVANCED_TO_BASIC.get(advanced)` (`volume_progress.py:242`) rather than using the
  wrapper function, which is also why the wrapper's raise-on-KeyError behavior never surfaces
  in production (production always uses the safe `.get()` form on the same dict). So: not
  "orphaned/forgotten" dead code, but genuinely **only exists to be a test fixture**, exactly as
  flagged in the task brief.

**Coupling**: pure module — no DB, no Flask, no imports except `re` (stdlib). Sole consumer is
`utils/volume_progress.py` (imported as `utils.volume_taxonomy as taxonomy`). This is the
correct shape for a "taxonomy source of truth" module.

**Dead code**: `advanced_to_basic()` (318-320) — test-only, confirmed by the task brief's own
framing and independently verified here via grep. Not called by any production code path;
`volume_progress.py` duplicates its logic inline via `.get()` instead of calling it.

---

## utils/volume_classifier.py (106 lines)

**Purpose**: Thin, well-scoped presentation-layer helper bridging both classification systems
(legacy raw-set tiers here, effective-set tiers imported from `effective_sets.py`) into
CSS-class strings, labels, and tooltip text consumed directly by `weekly_summary.html` /
`session_summary.html` (confirmed via grep — `get_volume_label`, `get_volume_tooltip` etc. are
passed as Jinja globals in `routes/weekly_summary.py:120-123` and
`routes/session_summary.py:137-140`).

**Key functions**:
- `_VOLUME_TIERS` (9-14) + `_classify()` (17-23) — the "legacy" raw-set classification (30+
  ultra, 20+ high, 10+ medium, else low), private, used by `get_volume_class`/
  `get_volume_label`. This is the system `weekly_summary.py`'s `legacy_volume_class` field
  (line 187, discussed above) draws from.
- `get_volume_class` / `get_volume_label` (26-37) — public wrappers over `_classify()`.
- `get_effective_volume_label` (40-49) — bridges to `effective_sets.get_weekly_volume_class`
  (imported as `get_effective_volume_class`, 4) then relabels via a locally-duplicated 4-entry
  dict (43-48) that **duplicates** `weekly_summary.EFFECTIVE_STATUS_MAP`'s key set
  conceptually (both map `low/medium/high/excessive` → display strings) but the value strings
  differ in purpose (`EFFECTIVE_STATUS_MAP` maps to itself, a CSS-status passthrough; this one
  maps to human labels like `'Low Volume'`). Not a bug — different consumers, different output
  shape — but another small instance of "the same four-way classification re-expressed with a
  new dict literal in a third place" (`effective_sets.WEEKLY_VOLUME_THRESHOLDS` keys, this
  file's `labels` dict, and `weekly_summary.EFFECTIVE_STATUS_MAP` all enumerate the same four
  strings independently). `[NEW]`
- `get_volume_tooltip` (52-60), `get_session_warning_tooltip` (63-79),
  `get_category_tooltip`/`get_subcategory_tooltip` (82-105) — pure string formatting, ranges
  hardcoded as display text (`'Below 10 sets'` etc., 54-59) that must be kept in sync by hand
  with `_VOLUME_TIERS` (9-14) — if the raw-set tier boundaries ever change, this tooltip text
  will silently go stale (no shared source of truth between the numeric tiers and their
  English-language descriptions). `[NEW][RISK]` — low severity (display text only, not a
  calculation), but a real drift risk since nothing ties the strings to the numbers
  programmatically.

**Coupling**: imports only from `effective_sets.py`; imported by `weekly_summary.py`,
`session_summary.py`, `volume_progress.py` is *not* a consumer (uses its own classifiers in
`_classify_target_status`/`_classify_progress_status` instead) — a fourth, independent
classification vocabulary (`none`/`low`/`high`/`optimal`/`excessive` for targets,
`on_target`/`under_target`/`over_target`/etc. for progress) that doesn't reuse anything from
this file. `[NEW]` Reasonable given it classifies a different thing (progress-toward-target,
not absolute volume), but worth synthesis awareness that this phase now has **four** distinct
low/medium/high-style classification vocabularies across
`effective_sets.py`/`volume_classifier.py`/`weekly_summary.py`/`volume_progress.py`.

**Dead code**: none found; every function here has a confirmed template/route consumer.

---

## utils/volume_ai.py (72 lines)

**Purpose**: Rule-based (not actually AI/ML) "suggestions" generator for the volume-splitter
page. Single function, `generate_volume_suggestions` (1-72), consumed by
`routes/volume_splitter.py` (Phase 10 territory).

**Observations**:
- Despite the module name, this is pure hand-written heuristic rules (total-volume ceiling,
  per-muscle sets-per-session bounds, category-volume floor) — no ML/AI involved. Naming is
  aspirational/misleading relative to actual implementation, worth a note but not a functional
  issue. `[NEW]`
- The `"basic"` vs `"advanced"` muscle-group category maps (32-58) are **a third, independent
  restatement** of the Basic/Advanced muscle taxonomy already centralized in
  `volume_taxonomy.py` (`BASIC_MUSCLE_GROUPS`/`ADVANCED_MUSCLE_GROUPS`), but grouped
  differently (push/pull/legs buckets of ~3-12 muscles each) and using **its own literal
  muscle-name strings** rather than importing from `volume_taxonomy.py` at all — no import of
  `utils.volume_taxonomy` anywhere in this file. `[NEW][RISK]` If `volume_taxonomy.py`'s
  canonical muscle names ever change (e.g. a rename like the in-flight `Front-Shoulder`→deltoid
  collapse TODO noted in Phase 1's findings, `constants.py:11,92-93`), this file's hardcoded
  string lists (`'Front-Shoulder'`, `'Latissimus-Dorsi'`, `'anterior-deltoid'`, etc.) will
  silently stop matching and the category-volume suggestion logic (60-70) will go quietly inert
  for the renamed muscle rather than erroring — because the lookup at line 62
  (`muscle_volumes.get(label, {})`) treats a missing key as an empty dict, not a failure.
- `mode` parameter validated/normalized defensively (5-7) even though callers
  (`routes/volume_splitter.py`) presumably only ever pass "basic"/"advanced" — reasonable
  input hardening for a function that receives request-derived data, not a smell.

**Coupling**: no DB, no other `utils` imports at all — fully standalone, which is precisely
why it was free to duplicate the taxonomy strings instead of importing them.

**Dead code**: none — single function, single confirmed caller.

---

## utils/volume_export.py (56 lines)

**Purpose**: Persists a computed volume-splitter allocation into the `volume_plans` /
`muscle_volumes` tables (the same tables `volume_progress.py` reads back via
`get_volume_progress`). Single function, `export_volume_plan` (8-55).

**Observations**:
- `requested_mode` derivation (13) — `volume_data.get("mode") if mode == "basic" and
  volume_data.get("mode") else mode` — a one-line conditional whose intent (prefer an explicit
  `mode` key inside the payload dict over the function's own `mode` parameter, but only when
  the parameter is still at its default `"basic"`) is non-obvious without tracing both call
  sites. `[NEW]` Minor readability smell — would be clearer as a short if/else, not a
  correctness issue (the two-line effective result, `plan_mode` at line 14, is correct either
  way since it re-validates against `"advanced"`/anything-else regardless of how
  `requested_mode` was derived).
- Uses raw `db.cursor.lastrowid` (25) and manual `commit=False` on every `execute_query` call,
  then returns without ever calling `db.connection.commit()` explicitly in the success path —
  relies on `DatabaseHandler.__exit__` to commit on clean exit (this phase didn't read
  `database.py` to confirm that behavior — flagging for cross-reference against Phase 2's
  findings on `DatabaseHandler`'s context-manager commit semantics). If `__exit__` does NOT
  auto-commit on a normal (non-exception) exit, every row this function inserts would be lost
  silently. `[RISK]` — needs Phase 2 cross-check, not resolvable from this phase's files alone.
- try/except only catches `sqlite3.Error` (53), not the generic `Exception` — if
  `volume_data['volumes']` is missing or malformed (e.g. `KeyError` on line 27, or a
  non-numeric `weekly_sets` causing `float()` to raise at line 45), the exception propagates
  uncaught rather than being logged/handled like the `sqlite3.Error` case is. `[NEW]`
  Inconsistent-with-itself: the function's whole shape suggests "defensively return None on
  failure" but only covers DB-layer failures, not data-shape failures from the caller-supplied
  `volume_data` dict.

**Coupling**: `DatabaseHandler`, `logger` only. Sole caller `routes/volume_splitter.py`.

**Dead code**: none.

---

## Cross-cutting seeds

1. **Three-to-four independent "loop over user_selection rows, weight by P/S/T role"
   implementations** exist across this phase alone:
   `weekly_summary.calculate_weekly_summary` (inline, 87-159),
   `session_summary._aggregate_muscle_volumes` (72-156, near-duplicate of the above with a
   confirmed null-routine-handling divergence — "Unassigned" fallback here, silent exclusion
   there), `volume_progress.aggregate_planned_sets` (independent weighting via its own
   `ROLE_WEIGHTS` constant rather than `effective_sets.MUSCLE_CONTRIBUTION_WEIGHTS`), plus the
   **fully dead** fourth implementation in `effective_sets.aggregate_session_volumes`/
   `aggregate_weekly_volumes` that nothing in production actually calls. Any WP2.3-style
   decomposition work should treat "extract one shared per-row P/S/T-weighting helper" as the
   highest-value, lowest-risk move in this phase — it's pure duplication with already-observed
   drift, not a design tension between legitimately different needs (planned-vs-logged volume
   is a legitimate reason for `volume_progress.py` to differ; the weekly-vs-session duplication
   is not similarly justified since `session_summary.py` already proves the shared logic can be
   factored into helpers).
2. **`calculate_weekly_summary` (179 lines) and `calculate_pattern_coverage` (172 lines) in
   `weekly_summary.py` are real monster functions** by line count and responsibility-mixing
   (SQL + two-pass aggregation + classification + output-shaping in one function body each).
   `session_summary.py`'s helper-decomposed structure for the *same conceptual problem*
   (aggregate → classify → shape output as separate functions) is a working, already-shipped
   template for how to split `calculate_weekly_summary` without changing its math — reducing
   refactor risk since the target shape already exists and is tested elsewhere in the codebase.
3. **A live, duplicated, and diverging muscle→movement-pattern classification** exists between
   `movement_patterns.PatternMapping.MUSCLE_GROUP_PATTERNS` (23 explicit entries) and
   `weekly_summary.calculate_pattern_coverage`'s inline elif-chain fallback (7 substring
   checks) — this is a correctness fork (different muscles land in different patterns between
   the two), not just style duplication, and sits inside the "don't change the math" protected
   zone, so any fix needs product sign-off on which mapping is authoritative before code moves.
4. **Four independent low/medium/high/excessive-style classification vocabularies** coexist for
   what a user experiences as "how much volume is this": `effective_sets.py`'s
   `WEEKLY_VOLUME_THRESHOLDS`/`SESSION_VOLUME_THRESHOLDS` (the effective-set source of truth),
   `volume_classifier.py`'s `_VOLUME_TIERS` (legacy raw-set thresholds, still live and rendered
   to users as `'volume_class'` alongside the effective-set-derived `'status'` field in the same
   summary row), `weekly_summary.EFFECTIVE_STATUS_MAP`/`STATUS_MAP` (the latter now fully dead),
   and `volume_progress._classify_target_status`/`_classify_progress_status` (a fifth,
   differently-shaped vocabulary for planned-vs-target comparison). Confirming with product
   which of these are still meant to be user-visible vs which are historical leftovers
   (`STATUS_MAP` clearly the latter) would materially shrink this phase's surface area.
5. **Confirmed dead code inventory for this phase**: `effective_sets.aggregate_session_volumes`,
   `aggregate_weekly_volumes`, `calculate_training_frequency`, `calculate_volume_distribution`,
   `format_volume_summary` (all test-only); `weekly_summary.STATUS_MAP` (unused constant);
   `volume_taxonomy.advanced_to_basic()` (test-fixture-only, exactly as the task brief
   predicted); `movement_patterns.MovementCategory` (unused enum) and
   `movement_patterns.HOME_BASIC_EQUIPMENT` (unused constant). None of these are large, but
   together they're a nontrivial share of `effective_sets.py`'s 576 lines (roughly the last 175
   lines, 349-518, are dead-in-production aggregation code) — a bigger single cleanup target
   than any of the other individual dead-code items found.
6. **One cross-phase question for Phase 2**: `volume_export.export_volume_plan` never calls
   `db.connection.commit()` explicitly despite passing `commit=False` on every write — whether
   this is safe depends on `DatabaseHandler.__exit__`'s commit-on-clean-exit behavior, which
   Phase 2 (not yet read at the time of this writing) will need to confirm or refute.
