# Phase 6 — Plan generation & calibration (line-by-line audit)

Scope read in full: `utils/plan_generator.py` (1442 lines), `utils/strength_calibration.py`
(846 lines), `utils/lift_matching.py` (196 lines). Context: `utils/CLAUDE.md`,
`docs/REFACTOR_PLAN.md` (WP2.2, WP2.1, WP1.3, global rules).

Line counts above are 1-indexed file lengths as read; they run one line past the
"N lines" figures quoted in the task brief (trailing blank line in each file) — immaterial.

---

## 1. `utils/plan_generator.py`

### 1.1 Module shape
Free function `get_generator_routine_names` (37-41) + two lookup tables
(`ESTIMATED_WEIGHTS` 47-102, `SUBPATTERN_WEIGHT_MULTIPLIERS` 109-131,
`MUSCLE_TO_PATTERNS` 134-223) + dataclasses (`GeneratorConfig` 226-318,
`ExerciseRow` 321-352, `GeneratedPlan` 355-388) + three classes
(`ExerciseSelector` 391-619, `PrescriptionCalculator` 622-719, `PlanGenerator`
722-1347) + free function `generate_starter_plan` (1350-1441, the public entry
point called by `routes/workout_plan.py:807`).

No imports of `profile_estimator` or `strength_calibration` anywhere in this
file (grep confirmed) — the starter-plan generator's weight estimates
(`ESTIMATED_WEIGHTS`, `SUBPATTERN_WEIGHT_MULTIPLIERS`) are a fully independent,
static, movement-pattern-keyed table, unrelated to the profile/learned
estimation chain in `profile_estimator.py`/`strength_calibration.py`. See §4
(cross-cutting seeds) — this is conceptual duplication of "estimate a starting
weight," not code duplication, and out of WP2.2's scope, but worth a doc note
so a future contributor doesn't assume `plan_generator` reads Profile data.

### 1.2 WP2.2 targets — verified against the real function bodies

**`ExerciseSelector._score_exercise`** (`plan_generator.py:495-585`, 91 lines).
[CONFIRMS-PLAN] Genuinely decomposable extract-method candidate. Body has five
clearly separable, order-independent scoring phases, each just adding to a
running `score` float:
1. pattern match / early-exit `-1000` (505-519)
2. subpattern preference bonus incl. a 10-entry keyword dict literal built
   inline every call (522-543) — the dict rebuild-per-call is a minor
   efficiency nit, not required for WP2.2, worth a footnote in the PR
3. role-based scoring (main vs accessory) (545-563)
4. preferred-exercise boost (565-569)
5. already-used-exercise penalty, novice-consistency-aware (571-580)
6. random tie-break `random.uniform(0, 5)` (583)

Because all five phases only *add* to `score` (no branching that depends on
order between them), extracting each into a `_score_<phase>(...) -> float`
helper and summing is safe and preserves the exact same floating-point total
(same operands, same order of summation as written today if the extraction
preserves call order) — **the executor must keep the addition order identical**
(float addition is not perfectly associative-safe across reorderings with the
random term; keep the random term last, as today, to avoid changing which
candidate wins under a tie in edge cases where score is exactly equal absent
the random jitter — extremely unlikely but a literal invariant to state in the
WP).

**`_apply_priority_muscle_boost`** (`plan_generator.py:847-955`, 109 lines).
[CONFIRMS-PLAN] Over the WP2.2-implied ~100-line threshold. Four distinct
sub-concerns nested inside one `for routine_name, exercises in routines.items()`
loop (884-954):
- compute `sets_budget`, call `_clear_volume_for_priority` if over budget (884-902)
- build `priority_exercises` list by muscle-match OR pattern-match (904-919)
- boost accessories in `priority_exercises`, capped at 4 sets (921-935)
- fallback: if nothing boosted, boost main lifts capped at 5 sets (937-954)
Clean extract-method split: `_compute_priority_patterns(priority_lower)` for
lines 870-882 (pattern/subpattern set-building, currently inline before the
loop) and `_boost_priority_for_routine(routine_name, exercises, relevant_patterns,
priority_lower, rules)` for the loop body. No scoring-math reorder needed —
this is volume-arithmetic (`ex.sets +=/-= 1`), not the exercise-selection score,
but the same "preserve order of operations" caution applies: boosting
accessories before falling back to mains is a load-bearing sequence (novices'
"beginner_consistency_mode" downstream behavior in `generate()` interacts with
which exercises got extra sets).

**`persist`** (`plan_generator.py:1248-1347`, 100 lines). [CONFIRMS-PLAN] Four
sub-concerns inside one `try/with DatabaseHandler() as db:` block:
- overwrite-mode deletion via `_delete_routine_family` (1263-1266) — already
  extracted, thin
- non-overwrite unique-suffix renaming loop, mutates `plan.routines` in place
  while iterating a *separate* `routine_names` snapshot (1267-1291) — self-
  contained, extractable as `_rename_conflicting_routines(db, plan, routine_names)`
- `base_order` computation from `MAX(exercise_order)` (1293-1299) — trivial,
  extractable or leave inline
- insert loop with **per-row exception swallowing** (1310-1334): a failed
  insert is logged as a warning and skipped, but the loop *continues* and
  `results[routine_name]` still gets set to the partial `inserted` count. The
  **outer** `try/except` (1260-1345) re-raises on failure. This two-tier error
  handling (inner: skip-and-continue per row; outer: log-and-reraise on
  connection/setup errors) is a genuine behavioral subtlety — extract-method
  must preserve exactly which errors are swallowed vs. re-raised. [RISK]

**`generate_starter_plan`** (`plan_generator.py:1350-1441`, 92 lines, but ~40
of those are the docstring's `Args:` block). [CONFIRMS-PLAN weakly] Actual
logic is only ~50 lines: build `GeneratorConfig` (1392-1409), run
`generator.generate()` (1411-1412), assemble `result` dict with three optional
additions (`estimated_duration_minutes`, `merge_mode`, `persisted`/
`inserted_counts`/`persist_error`) (1414-1439). This is thinner than
`_score_exercise`/`_apply_priority_muscle_boost`/`persist` and is more "long
because of a big docstring" than "long because of tangled logic" — a modest
extract-method target (`_build_result_payload(plan, config, generator)`), not
a high-value one. Executor should not over-invest here.

### 1.3 Functions NOT in the WP2.2 list but comparably sized [NEW]
- `_optimize_for_time_budget` (`plan_generator.py:1120-1195`, 76 lines) — three
  clearly labeled phases in comments ("Phase 1: Reduce isolation sets", "Phase
  2: Reduce accessory compound sets", "Phase 3: Remove isolation exercises").
  Same shape as the WP2.2 targets; smaller (76 vs the ~90-109 line targets) so
  reasonably left out, but if the executor is already in this file doing
  extract-method work, this is the same pattern and same risk profile.
- `_clear_volume_for_priority` (`plan_generator.py:957-1032`, 76 lines) — also
  a plausible candidate, called only from `_apply_priority_muscle_boost`; sized
  similarly to `_optimize_for_time_budget`. Not urgent.
- `GeneratorConfig.__post_init__` (`plan_generator.py:260-318`, 59 lines) —
  validates 6 independent fields sequentially; smaller, lower priority.

None of these three are large enough to insist on for WP2.2, but they're the
same "extract labeled phases into named helpers" shape, so a follow-up
could fold them in without re-scoping the WP.

### 1.4 Dead / unused code [NEW]
- `ExerciseSelector._score_exercise`'s third parameter `routine: str`
  (`plan_generator.py:499`) **is never read inside the function body**
  (grep-confirmed: no other occurrence of the bare word `routine` between
  lines 495-585). It is passed in from `select_exercise` (`plan_generator.py:596`)
  purely to satisfy the call signature — `select_exercise` itself only uses its
  own `routine` parameter for a warning log message (602-605), never passing it
  to the scoring math. Safe, no-behavior-change cleanup: drop the parameter (or
  keep it for future scoring signals — either is a one-line note the WP2.2
  executor can make while already in this function).
- `persist()`'s non-overwrite branch: `for i, routine in enumerate(routine_names):`
  (`plan_generator.py:1270`) — `i` is never used in the loop body (1270-1291).
  Trivial (`for routine in routine_names:`), same cleanup opportunity.
- Two `except Exception as e:` blocks where `e` is bound but never referenced
  because `logger.exception(...)` already captures the traceback:
  `_load_exercises` (`plan_generator.py:434-436`) and `_get_existing_patterns`
  (`plan_generator.py:1083`, `e` *is* used there via `logger.warning("...%s", e)`
  — false positive, only `_load_exercises` at 434 is the true unused-`e` case).
  Not worth a dedicated PR; fold into WP2.2 if touching that function anyway.

### 1.5 `routes/workout_plan.py:generate_starter_plan_route` re-check [CONFIRMS-PLAN, NEW nuance]
Read `routes/workout_plan.py:714-844` (131 lines). Confirms the council finding
#5 / WP1.3 note: this route is validate-then-delegate-then-respond, no business
logic to extract. **New observation**: the route re-validates `training_days`,
`environment`, `experience_level`, `goal`, `volume_scale`, and
`time_budget_minutes` (lines 753-801) with the *same* constraints
`GeneratorConfig.__post_init__` (`plan_generator.py:260-276`) already enforces
via `ValueError` — and the route's own `except ValueError as e:` handler
(line 839) would already turn a `GeneratorConfig` validation failure into the
same 400 response. This is defense-in-depth duplication (route fails fast with
a route-authored message; if it somehow let a bad value through,
`GeneratorConfig` would catch it with a *different* message) rather than dead
code — both paths are exercised depending on which check fires first. Not a
WP2.2 item (it's in `routes/`, Phase 1 territory), but worth flagging for
whoever eventually revisits `routes/workout_plan.py` again after WP1.3: the
validation could be deleted from the route and rely solely on
`GeneratorConfig.__post_init__` + the existing `ValueError` catch, shrinking
the route further — but that changes the exact error message text returned to
the client, which the CLAUDE.md refactor invariant treats as an API response
shape change requiring explicit sign-off. Flagging, not proposing to do it here.

### 1.6 Superset/persist logic
No superset logic lives in `plan_generator.py` — supersets are handled
entirely in `routes/workout_plan.py` (`link_superset`/`unlink_superset`/
`suggest_supersets`, WP1.3's real target). `plan_generator.persist()` only
inserts plain `user_selection` rows (no `superset_group` column in the insert
at 1302-1306), confirming the starter-plan generator does not create supersets.
[NEW — scope note, not a bug] If a future WP wants supersets in generated
plans, that's new-feature territory, not refactor.

### 1.7 1-5 day generator
`GENERATOR_ROUTINE_PROGRAMS` (28-34) and `SESSION_BLUEPRINTS` (imported from
`movement_patterns.py`, not read this phase) drive `_get_blueprint` (730-740).
`GeneratorConfig.__post_init__` (262-263) enforces `1 <= training_days <= 5`
consistent with `GENERATOR_ROUTINE_PROGRAMS`'s five keys. Confirmed consistent,
no drift found between the two tables during this read.

---

## 2. `utils/strength_calibration.py`

### 2.1 Circular-import direction — re-verified, plan doc is correct as stated
Grepped both directions:
- `strength_calibration.py:26-38` imports `DatabaseHandler`,
  `upsert_user_profile_lift` from `utils.database`, and — **at module top
  level** — `DEFAULT_ESTIMATE`, `DUMBBELL_LIFT_KEYS`, `KEY_LIFT_LABELS`,
  `KEY_LIFTS`, `classify_tier`, `epley_1rm` from `utils.profile_estimator`
  (line 30-37), plus `match_direct_lift_key` from `utils.lift_matching`
  (line 29).
- `utils/profile_estimator.py` imports `strength_calibration` **only inside
  function bodies** — `get_related_calibration_candidate` at line 1298 and a
  second import block at line 1364, both with an explicit comment ("Imported
  lazily because `strength_calibration` imports from this module").

So: **`strength_calibration` → `profile_estimator` is the top-level edge;
`profile_estimator` → `strength_calibration` is the lazy edge.**
`docs/REFACTOR_PLAN.md` states this correctly (finding #8 / WP2.1 invariant:
"`strength_calibration` imports this module at top level; this module imports
`strength_calibration` lazily inside functions"). [CONFIRMS-PLAN] Note for
whoever wrote the Phase 6 task brief: the brief's paraphrase ("strength_calibration
is imported at top-level by profile_estimator") states the edge backwards —
the plan doc itself has it right; only the verbal summary in the task
description was inverted. No document needs correcting.

### 2.2 Confidence vocabulary — protected, confirmed present and used correctly
`MIN_RELATED_CONFIDENCE = "medium"` (line 50) and `CONFIDENCE_NONE = "none"`
(line 52) are both defined; grep-checked usage:
- `CONFIDENCE_NONE` is defined but **not referenced anywhere else in this
  file** (only the four `CONFIDENCE_*` constants `LOW`/`MEDIUM`/`HIGH` are used
  operationally, e.g. in `_CONFIDENCE_RANK` line 216-220 and
  `USABLE_SUGGEST_CONFIDENCES` line 74). `CONFIDENCE_NONE` looks like it's
  consumed by a downstream/UI layer (route or template), not internally.
  [RISK — do not delete despite looking unused-in-module] REFACTOR_PLAN.md
  WP0.2 already explicitly protects it ("Do NOT delete... spec-locked anchors
  for gated workstreams") — this read confirms the protection is warranted:
  a naive "grep this file, see no use, delete" pass would have wrongly flagged
  it. [CONFIRMS-PLAN]
- `MIN_RELATED_CONFIDENCE` likewise is not referenced inside this file (only
  `USABLE_SUGGEST_CONFIDENCES = (CONFIDENCE_MEDIUM, CONFIDENCE_HIGH)` on line
  74 is the operative gate for both exact and related-transfer confidence
  checks — `MIN_RELATED_CONFIDENCE` itself appears to be a documentation/
  external-reference constant, not wired into `get_related_calibration_candidate`'s
  actual filter at line 337 or 344, which both check membership in
  `USABLE_SUGGEST_CONFIDENCES` directly, not `MIN_RELATED_CONFIDENCE`).
  [NEW] Worth a note for the calibration owner (separate from this refactor):
  `MIN_RELATED_CONFIDENCE` may be effectively documentation-only inside this
  module (its value `"medium"` happens to equal the lower bound already baked
  into `USABLE_SUGGEST_CONFIDENCES`), but that's a calibration-semantics
  question, explicitly out of scope for a "no calculation drift" refactor —
  flagging for the owner, not recommending any change.

### 2.3 Function-length check
Nothing in this file approaches WP2.2-style extract-method territory.
Longest functions: `get_related_calibration_candidate` (278-384, 107 lines)
and `update_calibration_for_exercise` (686-769, 84 lines). [NEW — not
requested by the task's WP2.2 scope, but noted for completeness since the task
asked to watch for functions >100 lines]

**`get_related_calibration_candidate`** (`strength_calibration.py:278-384`,
107 lines) — over the 100-line mark. Shape: eligibility gate (290-297) → SQL
join fetch (299-333) → per-row filter+math loop building `candidates`
(335-371) → `max(candidates, key=sort_key)` (373-384). This is calibration
*math* (Phase 2A related-transfer scoring — basis-factor conversion, ratio
gates, staleness gate) explicitly called out in `docs/REFACTOR_PLAN.md` global
rule 2 as adjacent to protected territory ("estimator priority chain",
"calibration formulas" per this task's PROTECTED list). [RISK] If a future WP
extends WP2.2-style decomposition to this file, `get_related_calibration_candidate`
would need a `product-risk-reviewer` gate analogous to WP2.3's, not a plain
`/unslop` — same class of risk as `weekly_summary.py`'s protected aggregation
functions. Not currently in any WP; flagging as a seed only.

### 2.4 No dead code found
All top-level functions in this file are either called by
`routes/workout_log.py`, `routes/user_profile.py`, or by each other (grep
confirmed both routes files import from `utils.strength_calibration`). No
orphaned functions found in this read.

---

## 3. `utils/lift_matching.py`

### 3.1 Shape
Single data table `DIRECT_LIFT_MATCHERS` (21-177, a 145-entry ordered tuple of
`(keyword, lift_key)` pairs) + one function `match_direct_lift_key` (180-195,
16 lines, simple linear scan). This is the smallest of the three files and the
simplest — no extract-method candidates, nothing to decompose. [CONFIRMS-PLAN
by omission — WP2.2/WP2.1 correctly do not target this file]

### 3.2 Ordering invariant — load-bearing, no test file dedicated to it
The module docstring (7-10) and inline comments (e.g. line 19-20, 34, 40, 48,
57-60, 65) repeatedly stress that **entry order in `DIRECT_LIFT_MATCHERS`
matters** — longer/more-specific keywords must precede shorter ones (e.g.
`"weighted pull-up"` before `"pull up"`; `"single-leg rdl"` before generic
deadlift terms). `match_direct_lift_key` does a linear `if keyword in name`
scan and returns on first match (192-194), so this is a genuine ordered
first-match-wins list, not a dict. [RISK] No dedicated `tests/test_lift_matching.py`
exists — grep confirms `match_direct_lift_key`/`DIRECT_LIFT_MATCHERS` are only
exercised indirectly via `tests/test_profile_estimator.py`. Any future
refactor of this file (e.g. converting to a dict, splitting into per-body-part
tables, sorting alphabetically) would silently break the ordering invariant
with no dedicated regression test to catch it. Not a WP2.2 concern (file
untouched by that WP), but a real gap if any future WP does touch this file —
worth a one-line addition to whatever WP eventually revisits
`profile_estimator`/`lift_matching` (WP2.1 territory, not WP2.2).

### 3.3 No duplication with `plan_generator.py`
`plan_generator.py` never imports `lift_matching` — its own exercise
selection/naming logic is pattern-based (`movement_pattern`/`movement_subpattern`
DB columns via `classify_exercise`), not the keyword-substring matching
`lift_matching.py` does for the profile/calibration estimator chain. Confirmed
no overlap or duplicated logic between the two systems.

---

## 4. Cross-cutting seeds

- **WP2.2 as scoped is accurate**: all four named targets
  (`_score_exercise` 91 lines, `_apply_priority_muscle_boost` 109 lines,
  `persist` 100 lines, `generate_starter_plan` ~50 lines of real logic under a
  large docstring) are real, each has a clean extract-method decomposition
  along comment-labeled or logically-separable phases, and none require
  reordering arithmetic — confirms the "extract-method only, no scoring-math
  reorder" instruction is achievable as written.
- **Two same-shape functions just under the WP2.2 radar**:
  `_optimize_for_time_budget` (76 lines) and `_clear_volume_for_priority`
  (76 lines) in `plan_generator.py` are the same "labeled-phases" shape as the
  four WP2.2 targets. A follow-up WP (or an expanded WP2.2) could fold them in
  cheaply.
- **`persist()`'s two-tier exception handling is the highest-risk single
  detail in this phase**: inner per-row insert failures are swallowed (logged,
  loop continues, partial `results` count) while the outer block re-raises.
  Any extract-method split of `persist()` must preserve which exceptions are
  caught at which level — call this out explicitly in the WP2.2 PR description
  as a no-drift proof item, similar to what WP2.3 already requires for
  `weekly_summary.py`.
- **`get_related_calibration_candidate`** in `strength_calibration.py`
  (107 lines) is a new >100-line function not currently on any WP's radar. It
  is calibration math (Phase 2A related-transfer), adjacent to the protected
  "calibration formulas" list — if it's ever decomposed, gate it like WP2.3
  (product-risk-reviewer), not a plain code-only WP.
  `strength_calibration.CONFIDENCE_NONE`/`MIN_RELATED_CONFIDENCE` are correctly
  protected by WP0.2 despite looking unused by a naive grep of this file alone
  — this read independently confirms the protection call was right.
- **`lift_matching.py`'s ordering invariant has no dedicated test file** —
  only indirect coverage via `tests/test_profile_estimator.py`. Not urgent
  (file isn't targeted by any current WP), but if WP2.1 (the
  `profile_estimator.py` split) ever touches lift matching, add
  `tests/test_lift_matching.py` characterization tests first.
- **Two trivial dead-code nits found in `plan_generator.py`**: the unused
  `routine` parameter on `_score_exercise` (line 499) and the unused loop
  variable `i` in `persist()`'s rename loop (line 1270). Cheap to fold into the
  WP2.2 PR since both functions are already being touched; not worth a
  separate WP.
- **`generate_starter_plan_route` re-validates fields `GeneratorConfig.__post_init__`
  already validates** (routes/workout_plan.py:753-801 vs.
  plan_generator.py:260-276). Confirmed the route is still "thin" (no business
  logic, just validation), so WP1.3's "verified already thin, no extraction"
  finding stands — but the duplicate validation is a latent inconsistency
  (different error message text for the same failure depending on which check
  fires) worth a footnote for whoever revisits `routes/workout_plan.py` next;
  changing it is an API-response-shape change requiring explicit sign-off per
  the CLAUDE.md refactor invariant, so not proposed as an in-scope fix here.
- **No code-level coupling found between `plan_generator.py` and
  `profile_estimator.py`/`strength_calibration.py`** — the starter-plan
  generator's `ESTIMATED_WEIGHTS` static table and the profile/learned
  estimation chain are two independent "guess a starting weight" systems that
  never call each other. Not a bug, but worth flagging in case a future
  feature request ("make the starter plan use my Profile lifts") assumes they
  already talk to each other — they don't.
