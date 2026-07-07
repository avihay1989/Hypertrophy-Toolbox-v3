# `profile_estimator` cluster & dependency map (WP2.1a)

*Characterization artifact for Deep Refactor Plan v3 Phase 2 (`docs/REFACTOR_PLAN.md`
WP2.1a → WP2.1b–f). **No production code moves in WP2.1a.** This document freezes the
internal structure of `utils/profile_estimator.py` (2,416 lines) so the staged
`utils/_profile_estimator/` extraction can proceed one leaf at a time without changing
behavior or the public surface.*

The import/export contract this map protects is enforced by
`tests/test_profile_estimator_contract.py` (supported export surface, underscore names
used by tests, `lift_matching` alias identity, both import orders with
`strength_calibration`) plus the consumer-coupling guard added in WP2.1a.

---

## 1. The hard constraint: the `strength_calibration` import cycle

`utils/profile_estimator.py` and `utils/strength_calibration.py` are mutually dependent:

- `strength_calibration` imports from `profile_estimator` **at module load** (`DEFAULT_ESTIMATE`,
  `DUMBBELL_LIFT_KEYS`, `KEY_LIFT_LABELS`, `KEY_LIFTS`, `classify_tier`, `epley_1rm`).
- `profile_estimator` imports from `strength_calibration` **lazily, function-local**, inside
  two functions only:
  - `_lookup_related_learned_calibration()` → `get_related_calibration_candidate`
  - `_lookup_learned_calibration()` → `USABLE_SUGGEST_CONFIDENCES`, `get_calibration_mode`,
    `get_learned_calibration`

The lazy direction is what keeps the cycle importable in **both** orders. **This must not
change during extraction.** The two lazy-importing functions are part of the orchestration
core (Cluster 6) and must stay in the facade module (or an internal core submodule that
keeps the imports function-local). No leaf cluster may take a module-level
`strength_calibration` import.

`epley_1rm` and `match_direct_lift_key` object identity across `profile_estimator`,
`strength_calibration`, and `lift_matching` is asserted by the contract test in both import
orders — extraction must preserve those as the same objects (re-exports, not copies).

---

## 2. The six clusters

Membership below is exhaustive for module-level names. `Tier` (type alias) and `logger`
are module infrastructure, not a cluster.

### Cluster 1 — Constants & lookup tables *(pure data; no intra-module calls)*
`DUMBBELL_LIFT_KEYS`, `KEY_LIFTS`, `COMPLEX_ALLOWLIST`, `_COMPLEX_ALLOWLIST_NORMALIZED`,
`EXCLUDED_EQUIPMENT`, `TIER_RATIOS`, `KEY_LIFT_TIER`, `REP_RANGE_PRESETS`,
`DEFAULT_PREFERENCES`, `DEFAULT_ESTIMATE`, `CROSS_FALLBACK_FACTOR`, `PROFILE_DEFAULT_SETS`,
`KEY_LIFT_LABELS`, `KEY_LIFT_SIDE`, `COLD_START_PRESET`, `EXPERIENCE_TIER_BOUNDS`,
`EXPERIENCE_MULTIPLIERS`, `COLD_START_RATIOS`, `COLD_START_CANONICAL_COMPOUND`,
`HIGH_IMPACT_LIFT_PRIORITY`, `ACCURACY_MAJOR_MUSCLE_GROUPS`, `MUSCLE_TO_KEY_LIFT`,
`COHORT_BODYWEIGHT_KG`, `COHORT_HEIGHT_CM`, `COHORT_AGE_YEARS`, `EXPERIENCE_TIER_ORDER`,
`ADVANCED_COHORT_REACH`, `BODYMAP_MUSCLE_KEYS`.
Plus the `lift_matching` re-export aliases: `DIRECT_LIFT_MATCHERS`, `match_direct_lift_key`,
`_match_direct_lift_key` (identity-preserving; see §1).
**Depends on:** nothing internal (external: `utils.lift_matching`, `utils.constants`).

### Cluster 2 — Trace builders
`_default`, `_format_experience_label`, `_format_rounding_label`, `_build_default_trace`,
`_build_log_trace`, `_build_profile_trace`, `_build_profile_bodyweight_trace`,
`_build_cold_start_trace`, `_build_learned_trace`, `_build_related_learned_trace`.
**Depends on:** Cluster 1 only. Intra-cluster: `_default`→`_build_default_trace`;
`_build_profile_trace`→`_format_rounding_label`;
`_build_cold_start_trace`→`_format_experience_label`,`_format_rounding_label`.
**Clean leaf** — extractable immediately after Cluster 1.

### Cluster 3 — Accuracy & coverage-guidance helpers
`_is_lift_filled`, `filled_lift_keys`, `accuracy_band`, `next_high_impact_lifts`,
`cold_start_anchor_lifts`, `replaced_anchor_lifts`.
**Depends on:** Cluster 1 + **Core math** (`cold_start_1rm`, `epley_1rm`). Intra-cluster:
`filled_lift_keys`→`_is_lift_filled`; `accuracy_band`/`next_high_impact_lifts`→`filled_lift_keys`;
`cold_start_anchor_lifts`→`cold_start_1rm`; `replaced_anchor_lifts`→`_is_lift_filled`,`epley_1rm`.
**Not a pure leaf** (reaches into core math — see §3).

### Cluster 4 — Cohort ranges / bars / donut
`_coerce_float`, `_format_kg`, `_format_cm`, `_format_years`, `_gender_label`,
`_next_tier_multiplier`, `cohort_ranges`, `_build_cohort_summary`, `cohort_bars`,
`coverage_donut`.
**Depends on:** Cluster 1 + Cluster 3 (`_is_lift_filled`, `filled_lift_keys`) + Core math
(`_classify_experience_tier`, `cold_start_1rm`, `epley_1rm`).
`coverage_donut`→`filled_lift_keys` (Cluster 3). `cohort_ranges`→`_build_cohort_summary`,
`_next_tier_multiplier`, the `_format_*`/`_coerce_float`/`_gender_label` formatters,
`_classify_experience_tier`. `cohort_bars`→`_is_lift_filled`,`_next_tier_multiplier`,
`cold_start_1rm`,`epley_1rm`,`_coerce_float`,`_classify_experience_tier`.

### Cluster 5 — Bodymap coverage state
`muscle_coverage_state`.
**Depends on:** Cluster 1 (`MUSCLE_TO_KEY_LIFT`) + Cluster 3 (`_is_lift_filled`) + Core math
(`epley_1rm`).

### Cluster 6 — Facade / core (estimation priority chain) *(stays in the facade)*
- **Core math primitives** (near-leaves; depended on by Clusters 3/4/5):
  `_normalize_for_matching`, `classify_tier`, `epley_1rm`, `round_weight`, `_load_basis_factor`,
  `_classify_experience_tier`, `cold_start_1rm`.
- **Orchestration** (holds the `strength_calibration` cycle; must stay in facade):
  `estimate_for_exercise`, `_estimate_from_profile`, `_estimate_from_cold_start`,
  `_lookup_last_logged`, `_lookup_related_learned_calibration`, `_lookup_learned_calibration`.
**Depends on:** Cluster 1, Cluster 2 (trace builders), and lazily `strength_calibration`.
`cold_start_1rm`→`_classify_experience_tier`; `classify_tier`→`_normalize_for_matching`;
`_load_basis_factor`→`DUMBBELL_LIFT_KEYS`.

---

## 3. Dependency direction (who imports whom)

```
Cluster 1  constants            ← (leaf; imported by everyone)
Cluster 2  trace builders       → 1
Core math  (subset of 6)        → 1, 2
Cluster 3  accuracy/coverage    → 1, Core math
Cluster 4  cohort               → 1, 3, Core math
Cluster 5  bodymap              → 1, 3, Core math
Orchestr.  (subset of 6)        → 1, 2, Core math, Cluster 3, + lazy strength_calibration
```

No back-edges into Clusters 3/4/5 from anything except the orchestration/public callers,
and no cluster imports another cyclically. The only cycle in the whole picture is the
`profile_estimator ⇄ strength_calibration` module cycle from §1, broken by lazy imports.

**Key finding for WP2.1b–f:** the plan's "cluster 6 = facade/core" is really *two* pieces —
a **core-math primitives** sub-leaf (`epley_1rm`, `round_weight`, `classify_tier`,
`_normalize_for_matching`, `_load_basis_factor`, `_classify_experience_tier`, `cold_start_1rm`)
that Clusters 3/4/5 depend on, and the **orchestration** chain that owns the
`strength_calibration` cycle. Clusters 3/4/5 are therefore **not pure leaves**: extracting
them requires their core-math dependencies to be importable. Extract or expose the core-math
primitives (as a shared internal `_core`/`_math` submodule, or by importing them from the
facade) **before** moving Clusters 3/4/5.

---

## 4. Recommended extraction order (leaves first)

Each step is a separate PR; the public `utils/profile_estimator.py` facade re-exports every
moved name so the surface in `test_profile_estimator_contract.py` never changes.

1. **WP2.1b — Cluster 1 constants** → `utils/_profile_estimator/constants.py`. Zero call deps;
   safest first move. Preserve `lift_matching` alias identity (re-export, don't re-bind).
2. **WP2.1c — Cluster 2 trace builders** → `utils/_profile_estimator/traces.py`. Depends only
   on constants.
3. **Core-math primitives** → `utils/_profile_estimator/core_math.py` (implied by the §3
   finding; fold into the WP2.1c/d boundary). Enables Clusters 3/4/5 to move.
4. **WP2.1d — Cluster 3 accuracy/coverage** → `utils/_profile_estimator/coverage.py`
   (imports constants + core_math).
5. **WP2.1e — Cluster 4 cohort** → `utils/_profile_estimator/cohort.py`
   (imports constants + coverage + core_math).
6. **WP2.1f — Cluster 5 bodymap** → `utils/_profile_estimator/bodymap.py`
   (imports constants + coverage + core_math).
7. **Orchestration stays** in `utils/profile_estimator.py` as the facade, keeping the two
   lazy `strength_calibration` imports function-local.

Constants are all Cluster 1 even though some are used by exactly one downstream cluster
(e.g. `COHORT_*` by cohort only, `COLD_START_RATIOS`/`COLD_START_CANONICAL_COMPOUND` by
cold-start core, `HIGH_IMPACT_LIFT_PRIORITY` by accuracy). Keep them together in the
constants module per the plan; do not scatter them into consumer modules in this behavior-
preserving extraction.

---

## 5. Production consumers of the public surface

Two modules import the public estimator surface; the WP2.1a consumer-coupling guard asserts
their imported names stay a subset of the module's public names so no extraction PR can
silently drop a re-export they rely on.

- `routes/user_profile.py`: `DEFAULT_PREFERENCES`, `DUMBBELL_LIFT_KEYS`, `KEY_LIFTS`,
  `REP_RANGE_PRESETS`, `accuracy_band`, `cohort_bars`, `cohort_ranges`,
  `cold_start_anchor_lifts`, `coverage_donut`, `estimate_for_exercise`,
  `muscle_coverage_state`, `next_high_impact_lifts`, `replaced_anchor_lifts`.
- `utils/strength_calibration.py`: `DEFAULT_ESTIMATE`, `DUMBBELL_LIFT_KEYS`,
  `KEY_LIFT_LABELS`, `KEY_LIFTS`, `classify_tier`, `epley_1rm` (module-load; see §1).

Method: AST call-graph analysis of `utils/profile_estimator.py` (module-level functions →
referenced module-level names) plus the two consumer import blocks. Read-only; behavior
unchanged.
