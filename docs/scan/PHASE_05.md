# Phase 5 — Estimator core: line-by-line audit of `utils/profile_estimator.py`

Full read: lines 1-2418 (5 chunks: 1-500, 501-1000, 1000-1500, 1500-2000, 2000-2418).
Also read: `utils/CLAUDE.md`, `docs/REFACTOR_PLAN.md` §WP2.1 (note: `REFACTOR_PLAN.md`
does not exist in this worktree — it's untracked in the sibling checkout at
`D:/development/Hypertrophy-Toolbox-v3-main/docs/REFACTOR_PLAN.md`; read from there),
`utils/strength_calibration.py` (imports + circular-import boundary),
`utils/lift_matching.py` (already-extracted sibling module), `routes/user_profile.py`
(import surface), `tests/test_profile_estimator.py` (import surface — proxy for the
required `__init__.py` re-export list).

---

## 1. Module docstring + dumbbell-load-basis convention (lines 1-21)

Module docstring states the **per-hand dumbbell convention** (Issue #10) as a
cross-cutting invariant: all dumbbell weights, input and output, are per-hand; the
estimator math itself is unit-agnostic and never converts unless bases disagree. This
is the spec anchor for `_load_basis_factor` (line 1176) and for `DUMBBELL_LIFT_KEYS`
below. **PROTECTED — do not touch the convention or the math**, per the task brief and
`docs/REFACTOR_PLAN.md` §0 rule 2.

`[NEW]` This docstring is the single best place to keep the convention documented
regardless of the split — whichever submodule ends up owning `_load_basis_factor` and
`DUMBBELL_LIFT_KEYS` should keep this docstring attached (verbatim), not paraphrase it.

---

## 2. Constants / lookup-table block (lines 22-740) — ~740 lines, ~30% of the file

Imports (22-31): `math`, `typing`, `utils.database.DatabaseHandler`,
`utils.logger.get_logger`, `utils.normalization.{normalize_equipment,normalize_muscle}`.
No routes/ imports — clean boundary per project convention.

Contents, in file order:
- `Tier` literal type (33)
- `DUMBBELL_LIFT_KEYS` (35-48) — per-hand slug set, load-basis input
- `KEY_LIFTS` (50-133) — full questionnaire slug set (~80 entries)
- `COMPLEX_ALLOWLIST` (135-181) — keyword allowlist for `classify_tier`
- `EXCLUDED_EQUIPMENT` (183-185)
- `TIER_RATIOS` (187-191) — `{complex:1.00, accessory:0.70, isolated:0.40}`
- `KEY_LIFT_TIER` (202-275) — per-slug implied tier, used to normalise
  `TIER_RATIOS[target]/TIER_RATIOS[reference]` (Issue #14 comment, 193-201) — this
  comment is load-bearing spec context, not decoration; keep with whichever module
  gets `_estimate_from_profile`.
- `REP_RANGE_PRESETS` (277-281) + `REP_RANGE_PCT` (282, derived)
- `DEFAULT_PREFERENCES`, `DEFAULT_ESTIMATE` (284-298)
- `CROSS_FALLBACK_FACTOR`, `PROFILE_DEFAULT_SETS` (300-301)
- `KEY_LIFT_LABELS` (307-372) — display names, also consumed by trace builders
- `KEY_LIFT_SIDE` (381-448) — anterior/posterior partition for Profile UI (Issue #24);
  enshrined by `tests/test_profile_estimator.py::test_key_lift_side_partitions_every_slug`
- `COLD_START_PRESET`, `EXPERIENCE_TIER_BOUNDS`, `EXPERIENCE_MULTIPLIERS` (450-469)
- `COLD_START_RATIOS` (477-494) — population 1RM/bodyweight ratios by (muscle, gender)
- `COLD_START_CANONICAL_COMPOUND` (496-508)
- `HIGH_IMPACT_LIFT_PRIORITY` (510-524)
- `ACCURACY_MAJOR_MUSCLE_GROUPS` (526-587)
- **mid-file `lift_matching` re-export** (589-598, see §3 below)
- `MUSCLE_TO_KEY_LIFT` (600-740) — muscle → ordered slug chain, the backbone of the
  Profile/cross-muscle fallback path

`[NEW] [RISK]` This ~740-line data block is **not called out at all** in WP2.1's
`core.py` / `trace.py` / `cohort.py` split — it would default into `core.py` by the
plan's literal wording, but it is consumed by every downstream cluster (core estimation,
trace builders, accuracy/coverage helpers §6, cohort helpers §7, bodymap coverage §8 all
read `KEY_LIFT_LABELS`/`KEY_LIFTS`/`MUSCLE_TO_KEY_LIFT`/`KEY_LIFT_TIER`). Dumping it into
`core.py` makes that file the de-facto "everything" module and the other three
submodules become thin appendages that `from .core import *`-style reach back in for
data. A cleaner seam (not proposed by WP2.1) is a dedicated `constants.py` (or
`lift_data.py`) holding this whole block, imported by `core.py`, `trace.py`, and
`cohort.py` alike. This does not change WP2.1's invariant that the package `__init__.py`
re-exports the full flat namespace — it only changes which submodule *defines* each name.
Flagging as a seed for whoever executes WP2.1, not a required change.

`[NEW]` `REP_RANGE_PCT` (line 282) — confirmed **definition-only** dead code: repo-wide
grep (`REP_RANGE_PCT`) hits only this definition and one doc mention
(`docs/user_profile/PLANNING.md:125`, a completed-checklist reference, not a live
import). Matches `docs/REFACTOR_PLAN.md` WP0.2's deletion candidate list exactly —
`[CONFIRMS-PLAN]`.

`[NEW]` The `target_1rm: float` parameter accepted by `_build_profile_trace` (line 856)
and `_build_cold_start_trace` (line 1025) is **never referenced in either function
body** (verified via targeted grep over each function's line range) — dead parameter,
present at every call site (`_estimate_from_profile` line ~1631, `_estimate_from_cold_start`
line ~1763). Safe to drop later since both are keyword-only (`*,`), but out of scope for
a pure-move WP; flag as a filler cleanup candidate.

---

## 3. `lift_matching` re-export (lines 589-598) — `[CONFIRMS-PLAN]`

```
from utils.lift_matching import DIRECT_LIFT_MATCHERS          # noqa: F401
from utils.lift_matching import match_direct_lift_key as match_direct_lift_key  # noqa: F401
_match_direct_lift_key = match_direct_lift_key
```

This sits literally mid-file, between `ACCURACY_MAJOR_MUSCLE_GROUPS` (587) and
`MUSCLE_TO_KEY_LIFT` (600) — exactly as `docs/REFACTOR_PLAN.md` WP2.1 describes ("mid-file
`lift_matching` re-exports `DIRECT_LIFT_MATCHERS`, `match_direct_lift_key`"). Confirms the
plan's factual claim precisely, including the underscore alias `_match_direct_lift_key`
used internally by every trace builder that computes an `improvement_hint` (lines 937,
999, 1087) and by `_estimate_from_profile` (line 1534). `lift_matching.py` itself is
**already a separate, already-extracted module** (own docstring says "Extracted from
`profile_estimator.py` so both the estimator and `strength_calibration.py` can reference
the matching logic without a circular import chain") — this extraction already happened
in a prior change; WP2.1 only needs to preserve the re-export, not redo the extraction.

Any `__init__.py` re-export list generated from "current module's public + test-imported
names" must include `DIRECT_LIFT_MATCHERS`, `match_direct_lift_key`, and
`_match_direct_lift_key` (the last is underscore-private but is the name every internal
call site actually binds to before the split — moving it must not silently drop it).

---

## 4. Circular-import guard — `[CONFIRMS-PLAN]`, exact locations

`utils/strength_calibration.py:30` imports **at module top level**:
```python
from utils.profile_estimator import (
    DEFAULT_ESTIMATE, DUMBBELL_LIFT_KEYS, KEY_LIFT_LABELS, KEY_LIFTS,
    classify_tier, epley_1rm,
)
```

`utils/profile_estimator.py` imports `utils.strength_calibration` **lazily, inside
function bodies**, at exactly two sites:
- line 1298, inside `_lookup_related_learned_calibration`:
  `from utils.strength_calibration import get_related_calibration_candidate`
- line 1364, inside `_lookup_learned_calibration`:
  `from utils.strength_calibration import (USABLE_SUGGEST_CONFIDENCES, get_calibration_mode, get_learned_calibration)`

The docstring of `_lookup_learned_calibration` (1354-1363) explicitly names the reason:
"Imported lazily because `strength_calibration` imports from this module (avoids a
circular import at load time)." Both lazy-import sites are inside the **priority-chain
lookup functions** (`_lookup_related_learned_calibration`, `_lookup_learned_calibration`)
that live between `estimate_for_exercise` (1195) and `_estimate_from_profile` (1520) —
i.e., squarely inside whatever submodule receives the "core estimation chain" per
WP2.1. **This confirms the plan's invariant is correctly scoped**: as long as
`core.py` (or whatever module receives these two functions) keeps the imports
function-local rather than hoisting them to its own module top, the guard holds.
`strength_calibration.py`'s top-level import of `profile_estimator` names must resolve
against the **package** `utils.profile_estimator` (i.e., the future `__init__.py`), not
against `utils.profile_estimator.core` directly, or that import breaks re-export
transparency — re-verify this at execution time by running
`utils/strength_calibration.py`'s import line unchanged after the split.

---

## 5. Trace builders ("show the math") — lines 743-1100, 1413-1442, 1445-1513

- `_default` (743-749), `_format_experience_label` (752-759),
  `_format_rounding_label` (762-772) — small formatting helpers feeding traces
- `_build_default_trace` (775-816)
- `_build_log_trace` (819-839)
- `_build_profile_trace` (842-960) — **118 lines, >100-line threshold**. Builds the
  step-by-step "Reference lift → Epley 1RM → tier scaling → cross-muscle factor →
  dumbbell load conversion → preset → working weight → rounding" trace, plus an
  `improvement_hint` computed via `_match_direct_lift_key` / `MUSCLE_TO_KEY_LIFT`.
- `_build_profile_bodyweight_trace` (963-1009) — bodyweight-reference variant, same
  shape, shorter (no 1RM math)
- `_build_cold_start_trace` (1012-1100) — 88 lines, population-estimate trace
- `_build_learned_trace` (1413-1442) — learned-calibration trace
- `_build_related_learned_trace` (1445-1513) — related-transfer trace

`[CONFIRMS-PLAN]` This cluster matches WP2.1's proposed `trace.py`
("`_build_profile_trace`, `_build_cold_start_trace`, 'show the math' builders") in
spirit, but the plan under-names the cluster — it omits `_build_default_trace`,
`_build_log_trace`, `_build_profile_bodyweight_trace`, `_build_learned_trace`, and
`_build_related_learned_trace`, all of which are the same "build a `{source, steps:[...]}`
dict" shape and are called exactly once each from the matching lookup/estimate function.
`[RISK]` These builders are **not contiguous** in the file — `_build_learned_trace`
(1413) and `_build_related_learned_trace` (1445) sit physically *between*
`_lookup_learned_calibration` (1351) and `_estimate_from_profile` (1520), interleaved
with core-chain functions rather than grouped with the other trace builders at 743-1100.
A pure "move these named functions" WP2.1 step handles this fine (moves are by symbol,
not by line range), but anyone skimming the file top-to-bottom to find "the trace module"
would miss half of it — worth a one-line note in the WP2.1 PR description.

`[NEW]` All eight trace builders return the same two-key envelope shape
(`{"source": str, "steps": [...]}`, optionally `+confidence/sample_count/improvement_hint`)
— no shared constructor/dataclass exists; each hand-builds the dict literal. Not a
behavior risk, but a real duplication candidate for a later (non-WP2.1) cleanup: a
`_trace(source, steps, **extra)` constructor would remove ~8 repeats of
`{"source": ..., "steps": steps}`.

---

## 6. Core math + tier classification — lines 1103-1192

- `_normalize_for_matching` (1103-1119) + `_COMPLEX_ALLOWLIST_NORMALIZED` (1122-1124,
  module-level derived constant, evaluated once at import time)
- `classify_tier` (1127-1141) — equipment/mechanic/movement_pattern/name → Tier
- `epley_1rm` (1144-1148) — **the** canonical 1RM formula, reused by
  `strength_calibration.py` (imported at its line 36) — single source of truth,
  confirmed no duplicate Epley formula exists elsewhere in the repo
- `round_weight` (1151-1173) — equipment-specific rounding increments/floors
- `_load_basis_factor` (1176-1192) — **PROTECTED math**, per-hand↔total conversion
  ("two dumbbells = one barbell" model). Test-imported directly by name
  (`tests/test_profile_estimator.py:18`) — must be re-exported by `__init__.py`
  exactly as `_load_basis_factor` (underscore, not aliased).

`[RISK]` `utils/strength_calibration.py:523` defines `_promotion_basis_factor`
(source_is_per_hand, target_is_per_hand) — **functionally identical** logic to
`_load_basis_factor` (same `if a == b: return 1.0; return 2.0 if a else 0.5`), just
renamed parameters and a docstring that explicitly cross-references
`profile_estimator._load_basis_factor` acknowledging the duplication ("same 'two
dumbbells = one barbell' model ... but the source side here is the exercise, not a
reference lift_key"). This is a genuine cross-module duplicated-logic finding not
mentioned anywhere in `docs/REFACTOR_PLAN.md`. **Do not fix inside WP2.1** (pure move,
no logic edits, and the two functions differ in the *meaning* of their boolean
arguments even though the arithmetic is identical) — flag as a candidate for a
future micro-WP that extracts a shared `load_basis_factor(a_is_per_hand, b_is_per_hand)`
into `utils/lift_matching.py` (the existing shared-utility home for both modules) with
both call sites becoming thin wrappers.

---

## 7. Estimation priority chain (the PROTECTED core) — lines 1195-1770

`estimate_for_exercise` (1195-1252) is the single public entry point and the literal
implementation of the protected priority chain
(`docs/REFACTOR_PLAN.md` §0 rule 2 / root CLAUDE.md): learned → log → related-learned →
Profile → cold-start → default, each `try` gated by an early return:

```
learned  = _lookup_learned_calibration(...)          # 1213
logged   = _lookup_last_logged(...)                  # 1218
related  = _lookup_related_learned_calibration(...)  # 1223
estimate = _estimate_from_profile(...)                # 1234 (profile_lifts + preferences fetched inline, 1228-1233)
cold_start = _estimate_from_cold_start(...)           # 1239-1242 (demographics fetched inline)
classify_tier(...) == "excluded" → _default("default_excluded")   # 1247-1248
else → _default("default_no_reference")                            # 1249
```
Wrapped in a single `try/except Exception: logger.exception(...); return _default("default_missing")`
(1250-1252) — the entire chain fails safe to defaults, never raises to the route layer.
**This exact order and the `is_dumbbell` tagging on every branch (1215, 1220, 1225, 1236,
1244, 1248, 1249) must not be reordered or dropped** — confirmed this is precisely the
chain named in the task brief and the refactor plan's protected-zone list.

Supporting lookup functions, each returning `Optional[dict]` (None = fall through):
- `_lookup_last_logged` (1255-1291) — `workout_log` table, `COALESCE(scored_*, planned_*)`
- `_lookup_related_learned_calibration` (1294-1348) — delegates to
  `strength_calibration.get_related_calibration_candidate`, lazy import (§4)
- `_lookup_learned_calibration` (1351-1410) — gated on `get_calibration_mode() == "suggest"`
  and confidence band, lazy import (§4)
- `_estimate_from_profile` (1520-1640) — **120 lines, >100-line threshold**. Builds a
  candidate list of `(lift_key, is_cross)` pairs (direct match first, then muscle chain,
  1536-1545), iterates until one has usable profile data, branches bodyweight (1570-1590)
  vs weighted (1592-1638) math. This is the single largest function in the file and the
  most natural "extract-method" target for WP2.2-style cleanup, though WP2.1 is a pure
  move so no internal restructuring should happen in that WP.
- `cold_start_1rm` (1659-1704) / `_classify_experience_tier` (1643-1656) /
  `_estimate_from_cold_start` (1707-1769) — population-estimate fallback chain

`[NEW]` Duplicated preset-resolution snippet, byte-for-byte except variable naming,
appears in both `_lookup_related_learned_calibration` (1308-1315) and
`_estimate_from_profile` (1548-1554):
```python
preference_by_tier = {row.get("tier"): row.get("rep_range") for row in preferences
                       if row.get("tier") and row.get("rep_range")}
preset_key = preference_by_tier.get(<tier_var>, DEFAULT_PREFERENCES[<tier_var>])
preset = REP_RANGE_PRESETS[preset_key]
```
Also the `pre_round_weight = target_1rm * preset["pct_1rm"]; working_weight =
round_weight(pre_round_weight, equipment, tier)` two-liner repeats identically at
1324-1329 (`_lookup_related_learned_calibration`), 1603-1608 (`_estimate_from_profile`),
and 1727-1732 (`_estimate_from_cold_start`) — three occurrences. Neither duplication is
in WP2.1 scope (pure move only) but both are good candidates for a follow-up
extract-method WP once the module is split, since the three call sites will likely end
up in the same `core.py` submodule anyway.

`[CONFIRMS-PLAN]` Both circular-import lazy-imports (§4) live inside this exact cluster
— reinforces that `core.py` is the correct/only submodule that needs the
lazy-import discipline; `trace.py` and `cohort.py` never touch `strength_calibration`.

---

## 8. Accuracy / coverage-guidance cluster — lines 1772-1968 — `[NEW]`, not named by WP2.1

- `_is_lift_filled` (1777-1802), `filled_lift_keys` (1805-1813)
- `accuracy_band` (1816-1878) — population_only/partial/mostly/fully band + copy
- `next_high_impact_lifts` (1881-1900)
- `cold_start_anchor_lifts` (1903-1931)
- `replaced_anchor_lifts` (1934-1968)

This is a **distinct, coherent cluster** (Issue #17 "accuracy-improvement guidance",
per the section comment at 1772-1774) that `docs/REFACTOR_PLAN.md` WP2.1 does not
mention at all — it names only `core.py`/`trace.py`/`cohort.py`. By the plan's literal
wording this cluster defaults into `core.py`, but it has nothing to do with the
learned→log→profile→cold-start priority chain in §7; it's read-only *summary/reporting*
over the same `profile_lifts` data, consumed exclusively by `routes/user_profile.py`
(confirmed via grep — `accuracy_band`, `next_high_impact_lifts`, `cold_start_anchor_lifts`,
`replaced_anchor_lifts` all appear only in `routes/user_profile.py` and
`tests/test_profile_estimator.py`, never in the estimation chain itself). `[RISK]` If
WP2.1's executor interprets "core.py" as "the estimation chain" narrowly, this cluster
has no assigned home and could get scattered arbitrarily. Recommend either (a) naming
it explicitly in the WP2.1 task text (e.g. a fourth `accuracy.py`), or (b) explicitly
stating it belongs in `core.py` as "everything not trace/cohort" — either is fine, but
the plan should say which.

---

## 9. Cohort / demographics-comparison cluster — lines 1971-2296

- Constants: `COHORT_BODYWEIGHT_KG`, `COHORT_HEIGHT_CM`, `COHORT_AGE_YEARS`,
  `EXPERIENCE_TIER_ORDER`, `ADVANCED_COHORT_REACH` (1978-1993)
- `_coerce_float`, `_format_kg`, `_format_cm`, `_format_years`, `_gender_label`,
  `_next_tier_multiplier` (1996-2042) — small formatting/classification helpers
- `cohort_ranges` (2045-2172) — **127 lines, >100-line threshold**. Builds the four
  stat tiles (bodyweight/height/age/experience) + summary string for the "How the
  system sees you" card (Issue #18). Explicitly informational-only — "never mutates or
  drives the estimator output" (docstring 2053-2056), height/age tiles flagged
  `used=False`. This is the estimator's own documentation of the informational-only
  invariant applied to a *sub-feature* — worth preserving verbatim wherever this
  function lands.
- `_build_cohort_summary` (2175-2211) — helper called only by `cohort_ranges`
- `cohort_bars` (2214-2278) — bar-chart rows comparing user 1RM vs cold-start vs cohort
  upper bound
- `coverage_donut` (2281-2295) — filled/total percent, mirrors `accuracy_band` counts
  in donut shape

`[CONTRADICTS-PLAN]` WP2.1 names `cohort.py` as holding **"`cohort_ranges`,
`muscle_coverage_state`"** — but `muscle_coverage_state` (§10 below) is a completely
different concern (bodymap SVG coverage state, not demographic-cohort comparison) that
happens to sit physically after this cluster in the file. Meanwhile `cohort_bars` and
`coverage_donut` — which unambiguously belong with `cohort_ranges` by both name and
function (same constants, same "How the system sees you" card, `cohort_bars` literally
calls `cold_start_1rm` and reuses `EXPERIENCE_MULTIPLIERS`/`_next_tier_multiplier` from
this same block) — are **not** named in WP2.1's `cohort.py` bullet at all, so by the
plan's literal text they'd default into `core.py`, splitting one UI card's backend
across two submodules for no reason. Test evidence backs this reading:
`tests/test_profile_estimator.py` imports `cohort_ranges`/`cohort_bars`/
`ADVANCED_COHORT_REACH`/`EXPERIENCE_MULTIPLIERS` together (lines 1163-1166, 1195, 1208)
and imports `BODYMAP_MUSCLE_KEYS`/`muscle_coverage_state` together separately
(lines 1257, 1282, 1303-1306, 1326, 1564) — the tests themselves already treat these as
two unrelated clusters. **Recommend WP2.1 be corrected before execution**: `cohort.py`
should hold `cohort_ranges` + `_build_cohort_summary` + `cohort_bars` + `coverage_donut`
+ the `COHORT_*`/`ADVANCED_COHORT_REACH`/`EXPERIENCE_TIER_ORDER` constants and the small
formatting helpers (1996-2042); `muscle_coverage_state` + `BODYMAP_MUSCLE_KEYS` should
either join the §8 accuracy/coverage cluster or get their own module (bodymap coverage
is itself cross-referenced against `static/js/modules/bodymap-svg.js` via a drift-guard
test, `test_bodymap_canonical_in_sync` at `tests/test_profile_estimator.py:1318`, which
is a different kind of coupling than anything else in the file).

---

## 10. Bodymap coverage state — lines 2298-2418 — `[NEW]`, distinct from cohort

- `BODYMAP_MUSCLE_KEYS` (2309-2324) — must stay in sync with
  `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES`/`COVERAGE_MUSCLE_CHAIN` in
  `static/js/modules/bodymap-svg.js` (comment 2305-2308); enforced by
  `test_workout_cool_back_region_multi_key_mapping_matches_python_keys` and
  `test_bodymap_canonical_in_sync` (`tests/test_profile_estimator.py`).
- `muscle_coverage_state` (2327-2418) — **91 lines**, four-state classifier
  (measured/cross_muscle/cold_start_only/not_assessed) per `BODYMAP_MUSCLE_KEYS` entry,
  used by the Profile-page bodymap. Reuses `MUSCLE_TO_KEY_LIFT` and `_is_lift_filled`
  (§8) from elsewhere in the file — this function's real dependency is the §8
  accuracy-cluster helper `_is_lift_filled`, not anything cohort-related.

See §9 for why bundling this with `cohort_ranges` (as WP2.1 literally proposes) doesn't
match the file's actual coupling — its nearest neighbor by shared-helper dependency is
`_is_lift_filled`/`filled_lift_keys` in §8, not `cohort_ranges`.

---

## 11. Functions over 100 lines (extract-method candidates, not in WP2.1 scope)

| Function | Lines | Length |
|---|---|---|
| `cohort_ranges` | 2045-2172 | ~127 |
| `_build_profile_trace` | 842-960 | ~118 |
| `_estimate_from_profile` | 1520-1640 | ~120 |

None of these are flagged for internal restructuring in WP2.1 (pure move only); flagging
here for a future WP2.2-style "decompose long functions" pass once the package split
lands, analogous to the existing WP2.2 for `plan_generator.py`.

---

## Cross-cutting seeds

1. **The 5-cluster reality vs. the 3-module plan**: the file's actual seams are
   *constants/data* (§2), *trace builders* (§5), *core estimation chain* (§7),
   *accuracy/coverage summary* (§8), *cohort/demographics comparison* (§9), and
   *bodymap coverage state* (§10) — six groupings, not three. WP2.1's `core.py` /
   `trace.py` / `cohort.py` correctly names two of these (trace, and half of cohort) but
   silently folds constants + accuracy/coverage + bodymap-coverage into an undifferentiated
   `core.py`, and its `cohort.py` bullet pairs the wrong two functions together
   (`cohort_ranges` + `muscle_coverage_state`) while omitting the two that actually belong
   with `cohort_ranges` (`cohort_bars`, `coverage_donut`). Recommend the plan be revised
   to either (a) accept a 4th/5th submodule (`accuracy.py`, `bodymap.py`) or (b)
   explicitly document that `core.py` is intentionally the catch-all for everything but
   trace-building and cohort-comparison, and fix the `cohort.py` member list per §9.

2. **Two independent load-basis-factor implementations** (`profile_estimator._load_basis_factor`,
   line 1176, and `strength_calibration._promotion_basis_factor`, line 523) share
   identical arithmetic and are cross-referenced by docstring but not by code. A future
   (non-WP2.1) micro-WP could extract one shared helper into `utils/lift_matching.py`
   (the module both already depend on for match logic) — flagged, not actioned.

3. **Preset-resolution and rounding two-liners repeat 2-3× inside the file** (§7) —
   good target for a same-module `_resolve_preset()` / `_round_target()` helper once the
   package split lands; explicitly out of scope for the pure-move WP2.1 itself.

4. **Dead `target_1rm` trace parameter** (§2) — unused in both `_build_profile_trace`
   and `_build_cold_start_trace` bodies; cheap filler cleanup once the split is done and
   signatures can be touched again.

5. **`REP_RANGE_PCT`** — confirmed dead per WP0.2, safe to delete in Phase 0 before this
   file is ever touched for the split.
