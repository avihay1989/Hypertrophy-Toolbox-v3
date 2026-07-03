# Phase 8 — Routes: workout_plan + filters

Files read in full, line-by-line:
- `routes/workout_plan.py` (1775 lines)
- `routes/filters.py` (489 lines)
- Context: `.claude/rules/routes.md`, `routes/CLAUDE.md`
- Supporting reads for grounding claims below: `utils/filter_predicates.py`, `utils/exercise_manager.py:1-55`, `utils/constants.py` (`MUSCLE_GROUPS`, `ANTAGONIST_PAIRS`, normalization tables), `static/js/modules/workout-plan.js` / `filters.js` (grepped for route consumers), `tests/test_workout_plan_routes.py` (grepped for coverage of suspect dead routes).

---

## 1. `fetch_unique_values` (workout_plan.py:20-101) vs `get_unique_values` (filters.py:356-442)

**[CONFIRMS-PLAN — WP1.1]**

These two functions are near-line-for-line duplicates: both branch on the same five cases (enum columns via `MECHANIC`/`UTILITY`/`DIFFICULTY`, `force` with title-case dedup, `advanced_isolated_muscles` via the junction table, the three muscle-group columns, `equipment` with `TRIM`, and a generic fallback), built on the same whitelist. `filters.py` even predefines `ENUM_VALUE_MAP` (filters.py:152-156) which is the same dict literal as `enum_map` inside `fetch_unique_values` (workout_plan.py:33-37) — two independent constant definitions of `{'mechanic': sorted(set(MECHANIC.values())), ...}`.

The only structural difference: `get_unique_values` (filters.py) is an HTTP endpoint that also validates a `table` param and wraps results in `jsonify(success_response(...))`; `fetch_unique_values` (workout_plan.py) returns a raw Python list for template rendering in `workout_plan()` (workout_plan.py:103-124).

This is exactly the WP1.1 shape: extract a single `utils.filter_values.fetch_filter_values(column) -> list` (or similar) that both the `/workout_plan` page route and the `/get_unique_values/<table>/<column>` API route call. Confirmed as real, non-trivial duplication (~80 lines mirrored).

**Bonus finding**: `/get_unique_values/<table>/<column>` (filters.py:356) has **zero frontend consumers** — grepped all of `static/js/**` and `templates/**`, no `fetch`/`api.get` call references it. Only `tests/` exercise it. Likely the earlier, generic version that `fetch_unique_values` was forked from when the `/workout_plan` page needed the values inline rather than via a round-trip API call. **[NEW]** Worth deciding whether to delete the now-unreferenced endpoint or keep it (public API surface) when doing the WP1.1 extraction — don't just relocate dead code without a decision.

## 2. Routes importing from routes (workout_plan.py:12)

**[CONFIRMS-PLAN — WP1.1] [RISK]**

```python
from routes.filters import ALLOWED_COLUMNS, validate_column_name
```

`routes/workout_plan.py` imports a whitelist and a validator from a sibling *routes* module. Per `routes/CLAUDE.md` and root `CLAUDE.md` §2, the module boundary is `routes → utils`, never `routes → routes`. This is the concrete evidence behind WP1.1's "relocate `ALLOWED_COLUMNS`/`validate_column_name` to utils with re-exports" — today, any edit to `filters.py`'s whitelist shape risks breaking `workout_plan.py`'s unrelated import, and there's no `utils` module owning the concept even though it's pure data + a pure function (no DB access, no Flask dependency) — it has no reason to live in a route file at all.

## 3. `column_exists` / `table_exists` / `initialize_exercise_order` (workout_plan.py:620-688)

**[CONFIRMS-PLAN — WP2.4]**

Three module-level functions with zero HTTP/Flask coupling:
- `column_exists(db, table_name, column_name)` — PRAGMA-based column probe, called from `get_workout_plan` (247-249), `_perform_exercise_swap` (1032), `_validate_superset_link_request` (1179), `unlink_superset` (1353).
- `table_exists(db, table_name)` — used only by `initialize_exercise_order`.
- `initialize_exercise_order()` — a full DB migration routine (adds `exercise_order` column, backfills NULLs, does an `ALTER TABLE` + windowed `UPDATE`) invoked once at app startup from `app.py` (per root CLAUDE.md §2 startup sequence) — this is schema-migration logic, not a route handler, and isn't registered as a Flask route at all.

This confirms WP2.4 cleanly: these three functions belong in `utils/` (most naturally alongside `utils/db_initializer.py`, which already owns startup-time schema work per Phase 1/2 boundaries). Today they live in `routes/workout_plan.py` purely because `app.py` happened to import `initialize_exercise_order` from there — an accident of history rather than a design choice.

## 4. `replace_exercise` (workout_plan.py:1043-1170) — WP1.2

**[CONFIRMS-PLAN — WP1.2, partially already done]**

The route itself is already decomposed into helpers: `suggest_replacement_exercise` (922-977), `_fetch_current_exercise_details` (980-989), `_build_replacement_candidates` (992-1009), `_perform_exercise_swap` (1012-1040). So the "extract business logic" work is partially done — but the extraction target was other functions in the *same routes file*, not `utils/`. Every one of those helpers does direct `DatabaseHandler` queries (`_fetch_current_exercise_details`, `_build_replacement_candidates`, `_perform_exercise_swap` all take `db: DatabaseHandler` and run SQL), which per the architecture rule ("routes/*.py → HTTP … utils/*.py → all business logic + DB queries") should not live in `routes/`. WP1.2 should be read as "relocate to utils", not "decompose" — the decomposition already happened, just in the wrong file.

The route function body itself (1043-1170, ~128 lines incl. docstring) is still long for a "thin" route — it interleaves orchestration with a duplicate-name retry loop (1114-1136) that itself contains business logic (re-suggesting from a filtered candidate list). That retry logic is a good candidate to fold into a single `replace_exercise_for_selection(exercise_id, strategy)` utils function returning a structured result, with the route reduced to validate → call → respond.

**Response-contract check — confirmed exactly as documented**: `NO_CANDIDATES` (1097-1102), `SELECTION_FAILED` (1107-1112, 1123-1129), `DUPLICATE` (1131-1136) all pass `status_code=200` to `error_response()`, matching `.claude/rules/routes.md`'s documented exception verbatim, including the `reason=` kwarg convention. No drift found here — this part of the plan/docs is accurate.

## 5. Superset link/unlink/suggest (workout_plan.py:1177-1774) — WP1.3

**[CONFIRMS-PLAN — WP1.3, same shape as WP1.2]**

Same pattern as replace_exercise: helpers already extracted to module level but not to `utils/`:
- `_validate_superset_link_request` (1177-1223) — DB reads + business-rule validation (same routine, not already supersetted).
- `_apply_superset_link` (1226-1250) — DB write + refetch, and note `import time` **inside the function body** (1227) rather than at module top — minor style inconsistency worth fixing during the move.
- `_group_exercises_by_routine` (1643-1650) and `_find_antagonist_pairings` (1653-1710) — pure grouping/pairing logic, no DB access, easiest of the batch to move (could go straight into a `utils/superset_suggestions.py` with no DB coupling at all).
- `_validate_and_normalize_execution_params` (1424-1486) and `_update_execution_style_db` (1489-1541) for the AMRAP/EMOM execution-style endpoints — same shape again, not mentioned by name in the WP1.3 description but same "helper functions holding DB access, stuck in routes/" pattern, so it's in-scope for the same refactor pass.

All of these are strong confirmations that WP1.3's extraction target is real and mechanical (move + re-import), not a redesign.

## 6. `generate_starter_plan_route` (workout_plan.py:714-844) — "claimed already thin"

**[CONFIRMS-PLAN, with a caveat]**

Verified: the route does *only* request-shape validation (six independent `if`/`return error_response(...)` blocks for `training_days`, `environment`, `experience_level`, `goal`, `volume_scale`, `time_budget_minutes`) and then a single call into `utils.plan_generator.generate_starter_plan(...)`. No DB access, no business logic, no computation — it is architecturally thin exactly as claimed.

Caveat: at ~131 lines (714-844) it is the single longest function in the file measured by line count, entirely because of six near-identical validation blocks repeating the `if not <cond>: return error_response("VALIDATION_ERROR", "...", 400)` shape. **[NEW]** Recommend extracting a `_validate_starter_plan_request(data) -> (params, error)` helper (same pattern already used successfully for `_validate_and_normalize_execution_params`, §5 above) purely for readability — this is a readability/consistency cleanup, not a layering violation, so it's lower priority than WP1.1-1.3.

## 7. SQL injection / dynamic-column audit

**[CONFIRMS-PLAN — validate_column_name is an effective guard, with one gap]**

Every f-string SQL interpolation of a column name in both files was traced back to its source:

| Location | Interpolated value | Guarded? |
|---|---|---|
| `fetch_unique_values` (workout_plan.py:46-96) | `safe_column` from `ALLOWED_COLUMNS.get(column.lower())`, after `validate_column_name()` (23) | Yes |
| `get_workout_plan` (workout_plan.py:271-297) | `extra_cols` built from `column_exists()` booleans (hardcoded literal column names) | Not user input at all |
| `update_exercise` (workout_plan.py:593-597) | `field` restricted to hardcoded `valid_fields = {'sets','min_rep_range',...}` set (583) | Yes (closed set, not whitelist lookup but equivalent) |
| `get_unique_values` (filters.py:391-436) | `safe_table`/`safe_column` from `ALLOWED_TABLES`/`ALLOWED_COLUMNS`, after both `validate_table_name()` and `validate_column_name()` | Yes |
| `get_filtered_exercises` (filters.py:479) | `safe_column` from `ALLOWED_COLUMNS.get(field.lower())`, after `validate_column_name(field)` (461) | Yes |
| `filter_exercises_with_expanded_muscles` (filters.py:298, 326) | `field` from `single_filters`/`multi_value_filters` dict keys | **Indirect** — see below |

**Gap [NEW] [RISK, low severity]**: `filter_exercises_with_expanded_muscles` (filters.py:269-344) is a free function that builds SQL by interpolating dict keys directly (line 298: `f" AND {field} LIKE ?"`, line 326: `f"{field} LIKE ?"`) with **no validation of its own**. It is only safe today because its sole caller, `filter_exercises()` (192-266), validates every key via `validate_column_name(db_field)` (216) before adding to `sanitized_filters`/`expanded_muscle_filters`. If this function is ever called from a second call site (or if the WP1.1 utils-extraction moves it without carrying the invariant with it), the guard would silently disappear. Recommend adding a defensive `validate_column_name()` assertion inside the function itself, or documenting the invariant loudly at the call boundary — don't rely on "the one caller happens to validate first."

## 8. `ANTAGONIST_PAIRS` casing — verified correct

**[CONFIRMS — no bug found, closes the requested watch item]**

Traced the full chain: `utils.constants.MUSCLE_GROUPS` (canonical DB values) uses mixed Title-Case/hyphenated forms, e.g. `"Latissimus Dorsi"`, `"Front-Shoulder"`, `"Upper Back"`, `"Gluteus Maximus"`, `"Middle-Traps"`, `"Quadriceps"`. `ANTAGONIST_PAIRS` (constants.py:261-275) keys/values are exactly the lowercased form of these canonical strings (`'latissimus dorsi'`, `'front-shoulder'`, `'upper back'`, `'gluteus maximus'`, `'middle-traps'`, `'quadriceps'`) — **not** the UI "simple" muscle keys from `filters.py`'s `SIMPLE_TO_DB_MUSCLE` (which use different short keys like `'lats'`, `'quads'`, `'traps-middle'`). The consumer, `_find_antagonist_pairings` (workout_plan.py:1653-1710), reads `e.primary_muscle_group` straight from the `exercises` join (1668, 1679) and lowercases it (`.lower()`) before the `ANTAGONIST_PAIRS.get(muscle1, [])` lookup (1684) — so the vocabularies line up correctly. No casing bug.

Minor code-smell noted in passing: line 1685 `if muscle2 in antagonists or any(m in muscle2 for m in antagonists)` — the second clause is a substring check on top of the exact-match check already covered by `in antagonists`. Given `MUSCLE_GROUPS` is a fixed, non-overlapping vocabulary this doesn't currently produce wrong matches, but it's redundant/confusing as written and would silently start producing false positives if a future muscle-group name became a substring of another (e.g. a hypothetical `"Shoulder"` vs `"Front-Shoulder"`). Low priority, flag only.

## 9. Structured-error-as-string anti-pattern: `add_exercise` (workout_plan.py:136-212)

**[NEW] [RISK]**

`utils.exercise_manager.add_exercise()` (`utils/exercise_manager.py:20-101`, read for grounding) returns **plain strings** as its result/error protocol: `"Exercise added successfully."` on success, or human-readable messages like `"Error: Missing required fields."`, `"Exercise already exists in this routine."` on failure. The route then does message-sniffing to reconstruct a status code and error code (workout_plan.py:169-177):

```python
if result != "Exercise added successfully.":
    message = result or "Failed to add exercise"
    message_lower = message.lower()
    is_validation_error = (
        message_lower.startswith("error:")
        or "missing required fields" in message_lower
        or "already exists" in message_lower
    )
```

This is fragile in both directions: a copy-edit to the string in `exercise_manager.py` (e.g. rewording "already exists" to "is already in this routine") would silently reclassify a 400 as a 500 with no test failure unless the exact substring is covered. This is exactly the kind of contract that should be a structured return (e.g. `(bool, error_code, message)` tuple or a small result dataclass) rather than prose. Worth folding into the WP1.2-style utils extraction pass since `add_exercise` sits in the same file being touched.

## 10. Validation gaps found while tracing bound-checks (routes.md accuracy)

**[CONTRADICTS-PLAN / doc drift]** on `.claude/rules/routes.md`'s claim:

> "Routes validate bounds before calling utils. Example pattern in `routes/workout_plan.py`: sets 1-20, reps 1-100, weight ≥ 0, RIR 0-10."

Traced this claim against actual code and it does not hold:
- **No bound validation exists in `routes/workout_plan.py` at all** for `add_exercise` — the route (136-212) forwards `data.get(...)` straight into `add_exercise_to_db()` with zero range checks of its own. The bound-checking (what little exists) lives in `utils/exercise_manager.py:add_exercise()` (correct layer per architecture, but wrong per the doc's specific claim about *where*).
- The bounds that actually exist there are narrower than documented: only `min_rep_range > max_rep_range`, `rir < 0`, `weight < 0`, `weight > 1000`. There is **no upper bound on `sets` (claimed ≤20), no upper bound on reps (claimed ≤100), and no upper bound on RIR (claimed ≤10)** anywhere in the traced path.
- **`update_exercise` (workout_plan.py:556-618) has no bound validation whatsoever** — it dynamically builds an `UPDATE` from any of `{sets, min_rep_range, max_rep_range, rir, rpe, weight}` (583) with only a "field is in this set" check, no value-range check, no min/max cross-check. So today a user can `add_exercise` with a sane range and then `update_exercise` it to `min_rep_range=999, max_rep_range=1, weight=-50, rir=-5` with no server-side rejection. **[RISK]** — real behavioral gap, not just a docs issue.

**[NEW] [RISK] falsy-value bug**: `utils/exercise_manager.py:32` — `if not all([routine, exercise, sets, min_rep_range, max_rep_range, weight]):` treats `weight == 0` as "missing" (Python falsy), so **adding a bodyweight exercise with an explicit weight of 0 is rejected as "Missing required fields"** rather than accepted. This is plausibly a real user-facing bug in a hypertrophy app where bodyweight movements are common; recommend `is None` checks per-field instead of a blanket `all()`/truthiness check. (This lives in `utils/exercise_manager.py`, technically Phase 2 territory, but it's directly reachable through the `add_exercise` route audited here so flagged now rather than losing the thread.)

Same falsy-check shape recurs in this file:
- `remove_exercise` (workout_plan.py:333): `if not exercise_id or not str(exercise_id).isdigit()` — `exercise_id == 0` would be rejected, though not reachable in practice since `user_selection.id` is an autoincrement PK starting at 1.
- `update_exercise_order` (workout_plan.py:701): `if not entry.get("id") or not entry.get("order"):` — `order == 0` would be rejected as invalid. Not reachable today because the only caller (`static/js/modules/workout-plan.js:2391`, `order: index + 1`) is 1-indexed, but it's a landmine if that ever changes to 0-indexed, and it's inconsistent with `exercise_order`'s own semantics elsewhere (nothing else in the codebase asserts 1-indexing as an invariant).

**[NEW] [RISK] partial-write-on-validation-failure**: `update_exercise_order` (workout_plan.py:690-711) validates and writes *inside the same loop, interleaved*:
```python
with DatabaseHandler() as db:
    for entry in data:
        if not entry.get("id") or not entry.get("order"):
            return error_response("VALIDATION_ERROR", "Invalid entry data", 400)
        db.execute_query("UPDATE user_selection SET exercise_order = ? WHERE id = ?", ...)
```
If entry 3 of 5 fails validation, entries 1-2 have already been written (assuming `DatabaseHandler.execute_query` isn't deferred to a single commit at context-exit — full transactional semantics weren't verified here since `utils/database.py` is Phase 2 scope, but the *code shape* is the same "validate mid-loop, write immediately" bug pattern regardless of the transaction boundary). Recommend validating the whole batch first, then writing.

## 11. Dead/unreferenced routes

**[NEW]**

Grepped `static/js/**`, `templates/**` for callers; cross-checked `tests/` for coverage:

| Route | Tested? | Frontend caller found? |
|---|---|---|
| `GET /get_routine_options` (workout_plan.py:406) | Yes (`tests/test_workout_plan_routes.py:357`) | **No** |
| `GET /get_user_selection` (workout_plan.py:484) | Yes (`tests/test_workout_plan_routes.py:308,315`) | **No** |
| `GET /get_exercise_details/<id>` (workout_plan.py:214) | Yes (multiple test files) | **No** |
| `GET /get_filtered_exercises` (filters.py:444, POST actually) | presumably | **No** |
| `GET /get_unique_values/<table>/<column>` (filters.py:356) | presumably | **No** |

`get_routine_options` returns a large hardcoded dict of routine-name hierarchies (Gym/Home Workout → Full Body/Split Programs/Basic Splits → routine name lists, workout_plan.py:406-482, 76 lines of static data). This is almost certainly a holdover from **before** the starter-plan generator (`GENERATOR_ROUTINE_PROGRAMS` / `/get_generator_options`, workout_plan.py:847-919) existed — per user MEMORY the 1-5 day generator shipped recently (PR #87) and superseded older routine-selection UI. Candidate for deletion, but confirm with a template/JS grep sweep across the whole repo (only `static/js` + `templates` were checked here) before removing, and check git blame / PR #87 diff to confirm the old UI it served was actually retired rather than just renamed.

`filters.py`'s `/get_filtered_exercises` and `/get_unique_values/<table>/<column>` appear to be an earlier, more generic filtering API that `/filter_exercises` (which *is* used, `static/js/modules/filters.js:69`) superseded — `/filter_exercises` additionally supports the simple/advanced muscle-key expansion (`expand_simple_muscle_value`) that `/get_filtered_exercises` lacks. Same "confirm before delete" caveat applies.

## 12. Whitelist triplication in the filter subsystem

**[NEW] [RISK]**

Three independent whitelists must be kept in sync for a filter field to actually work end-to-end:
1. `FILTER_MAPPING` (filters.py:79-105) — display name / snake_case → db column
2. `ALLOWED_COLUMNS` (filters.py:115-139) — SQL-injection whitelist, consulted by `validate_column_name()`
3. `FilterPredicates.VALID_FILTER_FIELDS` (`utils/filter_predicates.py:20-34`) — a *third*, independently-maintained whitelist used only by `FilterPredicates.build_filter_query()`

These have already drifted: `VALID_FILTER_FIELDS` includes `"target_muscles"` (filter_predicates.py:29) which does not exist in `ALLOWED_COLUMNS` or `FILTER_MAPPING` in `filters.py` — so `target_muscles` can never actually be reached through any HTTP route (both `/filter_exercises` and `/get_filtered_exercises` reject it before it would reach `FilterPredicates`). This is dead/unreachable configuration, and concrete proof that the "update three places" burden documented in `.claude/rules/routes.md` ("To add a filterable column: ALLOWED_COLUMNS, VALID_FILTER_FIELDS, PARTIAL_MATCH_FIELDS, simple-muscle mapping") is a real maintenance hazard, not just a checklist inconvenience — it has already silently drifted once. Worth considering a single source of truth for "filterable field" (e.g. one whitelist in `utils/`, with `PARTIAL_MATCH_FIELDS` as an attribute on it) as part of any WP1.1 work that touches this area.

## 13. Functions over 100 lines (candidates for splitting regardless of layer)

- `generate_starter_plan_route` (workout_plan.py:714-844, ~131 lines) — see §6.
- `replace_exercise` (workout_plan.py:1043-1170, ~128 lines incl. docstring) — see §4.
- `unlink_superset` (workout_plan.py:1324-1419, ~96 lines) — under 100 but close; same "helper extraction already started elsewhere, not applied here" pattern as §5.

No function in `filters.py` exceeds 100 lines; longest is `get_unique_values` at ~87 lines (356-442), itself the WP1.1 duplication target from §1.

## 14. Misc / minor

- `import random` (workout_plan.py:936) and `import time` (workout_plan.py:1227) are function-local imports rather than module-top imports — harmless but inconsistent with the rest of the file's style; worth normalizing if these functions get moved to `utils/` anyway.
- `get_exercise_details` (workout_plan.py:214-236) selects `us.rir, us.weight` but omits `us.rpe`, while the near-identical `get_workout_plan` query (workout_plan.py:271-297) includes `us.rpe`. Minor inconsistency between two structurally similar queries; likely just drift over time rather than intentional.
- `_apply_superset_link`'s `superset_group` id is `f"SS-{routine_name}-{int(time.time())}"` (workout_plan.py:1228) — second-resolution timestamp, theoretically collidable if two supersets are created in the same routine within the same wall-clock second (e.g. rapid double-click or a test creating two in a tight loop). Single-user local app makes this low severity, flagging only.

---

## Cross-cutting seeds

- **The "helper functions already extracted, just to the wrong file" pattern repeats at least three times** in this one file (`replace_exercise` §4, superset endpoints §5, execution-style endpoints §5) — this suggests WP1.2/WP1.3 are mechanical `git mv`-style relocations plus import fixups, not redesigns from scratch. Worth calling out in the plan as lower-risk/higher-confidence work than a from-scratch extraction would be.
- **The magic-string error protocol** between `utils/exercise_manager.py` and `routes/workout_plan.py` (§9) is a pattern worth grepping for across the rest of the codebase during Phase 23 synthesis — if `utils/exercise_manager.py` does it, other older `utils/*.py` modules audited in earlier phases may too, and it'd be worth a single "return structured results, not prose" cleanup pass rather than fixing it once in isolation here.
- **Falsy-value validation bugs** (`not weight`, `not exercise_id`, `not entry.get("order")`, §10) come from the very Pythonic-looking-but-wrong idiom `if not value:` used to mean "is this field present" when `0` is a legitimate value for weight, sets-index, or similar numeric fields. Worth a targeted grep for `if not \w+:` / `all(\[` near numeric-field validation across `utils/` and `routes/` in Phase 23 — this phase found 3 instances in one file, likely more exist.
- **Whitelist/config drift already happened once** (`target_muscles` dead field, §12) in a system explicitly documented as "three places to update." This is the kind of thing that argues for consolidating config-as-data (whitelists, valid-field sets) into one canonical source per concept during any refactor, not just moving code between files.
- **Dead-route detection needs a repo-wide grep, not a per-phase one** — this phase found 5 candidate-dead routes (§11) via a `static/js` + `templates` grep scoped to this phase's two files' routes. Recommend a dedicated pass at Phase 23 that greps *every* route path defined across all of `routes/` against *all* of `static/js/**` + `templates/**` in one shot, since dead-route evidence for e.g. `filters.py` routes could also hide in JS modules not yet read (Phases 12-17).
