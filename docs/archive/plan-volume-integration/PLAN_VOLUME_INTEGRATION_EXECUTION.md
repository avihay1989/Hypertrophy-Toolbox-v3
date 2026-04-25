# Plan Volume Integration - Execution

> Start here when implementing the Plan <-> Distribute volume progress panel.
> Planning context, product rationale, and review history live in `PLAN_VOLUME_INTEGRATION_PLANNING.md`.
> Sections 5-13 are preserved from the original document because the review notes refer to those section numbers.
> Cross-references to §1-§4, §14-§18, and Appendix A live in the planning doc.

## Agent quick start

- Current gate: `PROCEED` recorded in §18.2; Phase 1+ implementation may continue.
- First deliverable: live DB taxonomy audit in `docs/VOLUME_TAXONOMY_AUDIT.md` plus `utils/volume_taxonomy.py` skeleton and strict taxonomy tests is complete.
- Phase 0 passed on the live DB before `routes/`, `templates/`, and `static/js/modules/` feature wiring began.
- Use the files checklist in §13 and verification matrix in §12 as the implementation contract.
- Open the planning doc only for rationale, product decisions, risks, or review history.

---

## 5. Phase 0 — Taxonomy data audit (gating)

> **This phase must complete — and its tests must pass — before Phase 1 begins.** No code in `routes/`, `templates/`, or `static/js/modules/` related to this feature may merge first.

### 5.1 Audit queries

Run against the **live** `data/database.db` (not fixtures) and commit the output to `docs/VOLUME_TAXONOMY_AUDIT.md`.

- [x] `SELECT DISTINCT primary_muscle_group   FROM exercises ORDER BY 1;`
- [x] `SELECT DISTINCT secondary_muscle_group FROM exercises ORDER BY 1;`
- [x] `SELECT DISTINCT tertiary_muscle_group  FROM exercises ORDER BY 1;`
- [x] `SELECT DISTINCT muscle FROM exercise_isolated_muscles ORDER BY 1;`
- [x] `SELECT DISTINCT advanced_isolated_muscles FROM exercises WHERE advanced_isolated_muscles IS NOT NULL;`
- [x] Row counts per distinct value for each of the above, so cleanup effort is prioritised by impact.

**Blank-P/S/T census (added Codex round-2 §18.1.1).** The live DB is known to have ≈633 `exercises` rows with `primary_muscle_group IS NULL`, ≈252 of which still carry non-empty `advanced_isolated_muscles` or rows in `exercise_isolated_muscles`. The audit must enumerate them so Phase 0 can make an explicit product decision:

- [x] `SELECT COUNT(*) FROM exercises WHERE primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='';`
- [x] `SELECT COUNT(*) FROM exercises WHERE (primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='') AND (secondary_muscle_group IS NULL OR TRIM(secondary_muscle_group)='') AND (tertiary_muscle_group IS NULL OR TRIM(tertiary_muscle_group)='');`
- [x] `SELECT exercise_name, advanced_isolated_muscles FROM exercises WHERE (primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='') AND (secondary_muscle_group IS NULL OR TRIM(secondary_muscle_group)='') AND (tertiary_muscle_group IS NULL OR TRIM(tertiary_muscle_group)='') AND advanced_isolated_muscles IS NOT NULL;`
- [x] `SELECT e.exercise_name, COUNT(eim.muscle) AS iso_count FROM exercises e LEFT JOIN exercise_isolated_muscles eim USING (exercise_name) WHERE (e.primary_muscle_group IS NULL OR TRIM(e.primary_muscle_group)='') AND (e.secondary_muscle_group IS NULL OR TRIM(e.secondary_muscle_group)='') AND (e.tertiary_muscle_group IS NULL OR TRIM(e.tertiary_muscle_group)='') GROUP BY e.exercise_name;`

The audit document records every distinct token, its incidence, its proposed Basic rollup, its proposed Advanced canonical, and a product-decision column (`ADD` / `ROLL` / `IGNORE`). A separate section enumerates the blank-P/S/T exercises with per-exercise isolated-token lists and a `BACKFILL` / `EXCLUDE` / `ISOLATED_ONLY` decision column (see §5.2 `D-blank-pst`).

### 5.2 Product decisions required

Locked by the user before Phase 1. Each row becomes a data-driven entry in `utils/volume_taxonomy.py`.

| Token (observed) | Proposed Basic | Proposed Advanced | Decision mode | Notes |
|---|---|---|---|---|
| `Middle-Shoulder` | **open — user** | `lateral-deltoid` | Add to Basic (17th) **or** roll to `Front-Shoulder`/`Rear-Shoulder` | Many exercises use this. Recommended: add to Basic. |
| `Hip-Adductors` / `Adductors` | **open — user** | `inner-thigh` | Add to Basic **or** roll to `Glutes` | Recommended: add to Basic. |
| `Rotator Cuff` | **open — user** | — | Ignore-with-diagnostic **or** roll to shoulder bucket | Recommended: roll to `Rear-Shoulder` with note. |
| `Erectors` / `erector spinae` | `Lower Back` | `lowerback` | Roll | Deterministic. |
| `External Obliques` | `Abdominals` | `obliques` | Roll | Deterministic. |
| `Core` / `Abs/Core` | `Abdominals` | `upper-abdominals` (representative) | Roll | Deterministic. |
| `Rectus Abdominis` / `rectus abdominis` | `Abdominals` | `upper-abdominals` | Roll | Deterministic. |
| `Gluteus Maximus` | `Glutes` | `gluteus-maximus` | Roll | Deterministic. |
| `Latissimus Dorsi` / `latissimus dorsi` / `latissimus-dorsi` | `Latissimus-Dorsi` | `lats` | Roll | Canonicalise spacing/hyphen drift. |
| `Upper Back` | **open — user** | — | Roll to `Middle-Traps` **or** `Traps` | Recommended: `Middle-Traps`. |
| `Trapezius` / `Upper Traps` | **open — user** | `upper-trapezius` | Roll to `Traps` **or** `Middle-Traps` | Recommended: `Traps`. |
| `Upper Chest` | `Chest` | `upper-pectoralis` | Roll | Deterministic. |
| `Shoulders` | **open — user** | representative | Roll to `Front-Shoulder` as default **or** split by heuristic | Recommended: `Front-Shoulder` with diagnostic (underspecified data). |
| `Back` | **open — user** | representative | Roll to `Latissimus-Dorsi` **or** distribute | Recommended: `Latissimus-Dorsi`. |
| `Chest` (isolated token) | `Chest` | `mid-lower-pectoralis` | Roll | Redundant umbrella. |
| `Traps (mid-back)` | `Middle-Traps` | `traps-middle` | Roll | Canonicalise. |
| `Long Head Tricep` / `triceps brachii` | `Triceps` | `long-head-triceps` | Roll | Canonicalise spelling drift. |
| `Rear Delts` | `Rear-Shoulder` | `posterior-deltoid` | Roll | Deterministic. |
| `Inner Quadriceps` / `Inner Quadricep` | `Quadriceps` | `inner-quadriceps` | Roll | Canonicalise case/plural. |
| `general back` | `Latissimus-Dorsi` | `lats` | Roll | Fallback default. |
| `pectoralis major clavicular` | `Chest` | `upper-pectoralis` | Roll | Canonicalise. |
| `pectoralis major sternal head` | `Chest` | `mid-lower-pectoralis` | Roll | Canonicalise. |
| `brachialis` / `brachioradialis` | `Forearms` | `wrist-flexors` (representative) | Roll | Arm isolators mapped to nearest splitter slider. |
| `hamstrings` (generic token) | `Hamstrings` | `medial-hamstrings` (representative) | Roll | Deterministic. |
| `supraspinatus` / `infraspinatus` | Depends on Rotator Cuff decision | depends | Roll / Ignore | Consistent with Rotator Cuff choice. |
| `sternocleidomastoid` / `splenius` | `Neck` | — | Roll | Neck has no advanced split today. |
| `soleus` / `tibialis` / `gastrocnemius` (correct canonical) | `Calves` | same | Roll | Canonical. |
| `Mid and Lower Chest` | `Chest` | `mid-lower-pectoralis` | Roll | Canonicalise. |
| `serratus-anterior` | `Chest` | `mid-lower-pectoralis` (representative) | Roll | Not added as splitter UI slider. |
| `quadriceps` (umbrella token) | `Quadriceps` | distributed equally across `rectus-femoris`, `inner-quadriceps`, `outer-quadriceps` | Roll (distributed) | Not added as splitter UI slider. |

### 5.2.1 Blank-P/S/T decision (`D-blank-pst`) — required for 95% (Codex round-2 §18.1.1)

When an exercise has all three of `primary/secondary/tertiary_muscle_group` blank, the §7 aggregation has three plausible paths. Exactly one must be chosen in Phase 0 and recorded in `utils/volume_taxonomy.py`:

| Mode | Behaviour | Pros | Cons |
|---|---|---|---|
| `BACKFILL` (recommended long-term) | Use the audit output to populate P/S/T for every blank row before Phase 1. | Removes the problem at the source; simplest downstream logic. | Requires catalog edits for ~252 rows; may be out of scope for this feature. |
| `ISOLATED_ONLY` (recommended default) | When all three P/S/T are blank but `exercise_isolated_muscles` / `advanced_isolated_muscles` is non-empty, synthesise a **single primary-weight contribution** (1.0 × sets) split across the isolated tokens using the same refinement rules as §7.2's Advanced branch, plus a per-exercise `diagnostics.blank_pst_rows` entry. | No silent zero; no catalog edits; users who only selected such exercises still get attribution. | Attribution is a single lump primary contribution — no secondary/tertiary weighting. Accepted limit; documented. |
| `EXCLUDE_WITH_DIAGNOSTIC` | Skip the row entirely, append to `diagnostics.blank_pst_rows` and warn. | Simplest; explicit. | Users who have exercises with only isolated data get an invisible zero — the exact silent-loss failure Codex flagged. |

- [x] **User input required.** Default proposal = `ISOLATED_ONLY`. Record the decision in `utils/volume_taxonomy.py` as `BLANK_PST_STRATEGY = 'isolated_only' | 'backfill' | 'exclude'`.
- [x] Whichever strategy is chosen, the row always appears in `diagnostics.blank_pst_rows` so tests and the logger can observe it.

### 5.3 Phase 0 deliverables

- [x] `docs/VOLUME_TAXONOMY_AUDIT.md` committed — lists every distinct token with incidence counts, **plus** a "Blank P/S/T exercises" section enumerating every row captured by the §5.1 blank-P/S/T queries (exercise name, isolated-token list, proposed strategy).
- [x] Product decisions locked in the table above (user input required for the `open — user` rows) **and** the `D-blank-pst` decision from §5.2.1.
- [x] Preliminary `utils/volume_taxonomy.py` skeleton exists and passes the pre-flight tests in §9.1.1. (Implementation of aggregation and endpoints is Phase 1+.)
- [x] Every "open — user" row in §5.2 has a recorded answer.
- [x] `BLANK_PST_STRATEGY` constant set in `utils/volume_taxonomy.py` matching the `D-blank-pst` decision.

### 5.4 Phase 0 exit criterion

`pytest tests/test_volume_taxonomy.py -q` must pass with zero failures **against the live DB copy used during development**. This test is non-optional and will re-run in CI (see §9.1.1).

### 5.5 Hard stop — post-Phase-0 confidence assessment

**No Phase 1+ implementation may begin until this hard stop is completed and recorded.** This is a deliberate gate, not a soft checklist item.

After §5.3 deliverables and §5.4 tests pass, pause and add a short assessment entry to this document before changing `routes/`, `templates/`, `static/js/modules/`, or `utils/volume_progress.py`.

Required assessment:
- [x] Confirm the Phase 0 audit was run against the live development DB named in §5.1.
- [x] Confirm every open product decision in §5.2 has a recorded answer.
- [x] Confirm `BLANK_PST_STRATEGY` is set and tested.
- [x] Re-run `pytest tests/test_volume_taxonomy.py -q` and record the result.
- [x] Estimate confidence for full implementation as a percentage.
- [x] Explicitly choose one gate decision:
  - `PROCEED`: confidence is at least 95%, blockers are closed, and Phase 1 may start.
  - `PATCH_PLAN`: confidence is below 95% or a plan gap remains; update this plan before Phase 1.
  - `STOP`: taxonomy/product risk remains high enough that implementation should not continue.

Assessment template to append under §18:

```markdown
### 18.x Post-Phase-0 confidence assessment

Date:
Reviewer:
Phase 0 test result:
Decisions recorded:
Remaining blockers:
Confidence:
Gate decision:
Notes:
```

---

## 6. Taxonomy module — `utils/volume_taxonomy.py`

Created in Phase 0. Ownership: **single source of truth for everything related to muscle naming** across the feature.

### 6.1 Public exports

```python
# Muscle list constants — moved out of routes/volume_splitter.py.
# The route module re-imports them for backwards compatibility.
BASIC_MUSCLE_GROUPS: list[str]        # see §6.1.1
ADVANCED_MUSCLE_GROUPS: list[str]     # same as today (no UI change)

# Mappings — every entry documented inline with its rationale.
COARSE_TO_BASIC: dict[str, str]
    # Every distinct exercises.primary/secondary/tertiary_muscle_group
    # value (post Phase-0 audit) -> a member of BASIC_MUSCLE_GROUPS.
    # Keys are case-sensitive-normalized (see `canonical_pst()`).

COARSE_TO_REPRESENTATIVE_ADVANCED: dict[str, str]
    # Coarse P/S/T value -> a member of ADVANCED_MUSCLE_GROUPS.
    # Used for secondary/tertiary roles and when primary cannot be refined.

ADVANCED_TO_BASIC: dict[str, str]
    # Every member of ADVANCED_MUSCLE_GROUPS -> a member of BASIC_MUSCLE_GROUPS.

TOKEN_TO_ADVANCED: dict[str, str | None]
    # Every distinct token found in exercises.advanced_isolated_muscles
    # or exercise_isolated_muscles.muscle -> a member of ADVANCED_MUSCLE_GROUPS,
    # or None to mean "explicitly ignored (diagnostic only)".

IGNORED_TOKENS: frozenset[str]
    # Tokens we know about but deliberately do not count. Duplicates the
    # `None` values in TOKEN_TO_ADVANCED for fast membership checks.

DISTRIBUTED_UMBRELLA_TOKENS: dict[str, tuple[str, ...]]
    # Umbrella tokens that distribute across multiple advanced buckets.
    # e.g. "quadriceps" -> ("rectus-femoris","inner-quadriceps","outer-quadriceps")
```

### 6.1.1 Constants moved from `routes/volume_splitter.py`

- [x] Move `BASIC_MUSCLE_GROUPS` and `ADVANCED_MUSCLE_GROUPS` from `routes/volume_splitter.py:15-45` to `utils/volume_taxonomy.py`.
- [x] In `routes/volume_splitter.py` replace the literals with:
  ```python
  from utils.volume_taxonomy import BASIC_MUSCLE_GROUPS, ADVANCED_MUSCLE_GROUPS
  ```
- [x] Keep the existing `get_muscle_list_for_mode()` helper in the route file (it is tiny and route-facing). No behavior change.
- [x] Confirm no callers reach into `routes.volume_splitter` for the muscle lists from outside the route file itself; migrate any that do.

### 6.2 Public functions

```python
def canonical_pst(value: str | None) -> str | None:
    """Normalize a raw P/S/T muscle_group value for dict lookup.
    Strips surrounding whitespace; preserves internal capitalization that is
    meaningful to existing data (e.g. 'Middle-Shoulder' stays capitalized)."""

def normalize_isolated_token(token: str) -> str:
    """Lowercase, strip, collapse internal whitespace to single hyphen or space
    per rule set. Used as the key function for TOKEN_TO_ADVANCED."""

def advanced_token_belongs_to_coarse(token: str, coarse: str) -> bool:
    """Returns True iff normalize_isolated_token(token) maps (via
    TOKEN_TO_ADVANCED + ADVANCED_TO_BASIC) to the same Basic bucket as
    COARSE_TO_BASIC[canonical_pst(coarse)]. If either side is unknown,
    returns False. Used to safely refine the primary role only."""

def coarse_to_basic(coarse: str) -> str:
    """Raises KeyError if missing, so tests (not runtime) catch gaps."""

def coarse_to_representative_advanced(coarse: str) -> str:
    """Raises KeyError if missing."""

def advanced_to_basic(advanced: str) -> str:
    """Raises KeyError if missing."""

def expand_umbrella(token: str) -> tuple[str, ...] | None:
    """Returns the distribution tuple for umbrella tokens, or None."""
```

Design notes:
- Functions raise on missing keys so the strict tests in §9.1.1 fail loudly. Runtime callers in §7 handle unknown tokens by recording them in `diagnostics.unmapped_muscles` rather than attempting lookup — they never hit the raising helpers with unknown inputs.
- No route imports, no DB access in this module — it is pure data + pure functions.

### 6.3 Design calls captured in module docstrings

- [x] `lower-trapezius` → `Middle-Traps` (no Lower-Traps bucket in Basic).
- [x] `quadriceps` (umbrella) → distributed across 3 advanced quad buckets. Never maps to a single advanced key.
- [x] `serratus-anterior` → Basic `Chest` / Advanced representative `mid-lower-pectoralis`. Not added as a splitter UI slider.
- [x] Rotator cuff tokens follow the Phase-0 decision; default proposal = `Rear-Shoulder`.
- [x] Document each decision inline with `# Decision (Phase 0 §5.2): ...` so Codex/Gemini round 2 can grep for the reasoning.

---

## 7. Aggregation algorithm (role-authoritative)

This replaces §5.3 of draft v1 entirely.

### 7.1 Input

For a given row in `user_selection` joined to `exercises`:

```python
sets                    : int   # integer from user_selection
primary_muscle_group    : str
secondary_muscle_group  : str | None
tertiary_muscle_group   : str | None
advanced_isolated_muscles: str | None   # CSV; may be None or malformed
```

### 7.2 Per-row procedure

Token source in this pseudocode = the pre-built list returned by `fetch_planned_rows()` (§9.1), which **prefers `exercise_isolated_muscles` over the CSV `advanced_isolated_muscles`** (Codex round-2 §18.1.2). The CSV is only consulted when the mapping table has no rows for that exercise — in which case `diagnostics.csv_fallback_count` is incremented.

```
# --- Step 1: handle all-blank P/S/T per §5.2.1 D-blank-pst strategy. ---
if all roles are None/blank:
    diagnostics.blank_pst_rows.append(exercise_name)

    if BLANK_PST_STRATEGY == "exclude":
        return                                  # row contributes nothing; diagnosed
    if BLANK_PST_STRATEGY == "backfill":
        # Caller must have resolved P/S/T during Phase 0; a still-blank row here is a bug.
        logger.warning("blank_pst row leaked past backfill: %s", exercise_name)
        return
    # "isolated_only" — synthesise one primary-weight contribution from tokens below.
    contribution = sets * 1.0
    if not isolated_tokens:
        return                                  # no data at all; row truly empty
    distribute contribution across isolated_tokens using the same refinement
    rules as the primary-role Advanced branch below, but without the
    advanced_token_belongs_to_coarse() family gate (there is no coarse to gate on);
    every refined target is recorded. In Basic mode, map each token to its Basic
    bucket via ADVANCED_TO_BASIC(TOKEN_TO_ADVANCED[norm]); if unmapped, append to
    diagnostics.unmapped_muscles and fall back to distributing equally across
    the exercise's isolated-token Basic buckets that *are* mapped, or abort with
    diagnostics.blank_pst_orphan += 1 if none are.
    return

# --- Step 2: normal role loop (unchanged from v2 apart from rejected_tokens). ---
For each role in (primary, secondary, tertiary):
    coarse = row[role + "_muscle_group"]
    if coarse is None or blank:
        continue
    contribution = sets * weight[role]         # 1.0 / 0.5 / 0.25

    if mode == "basic":
        basic = coarse_to_basic(coarse)         # raises if Phase-0 missed it
        add contribution to totals[basic]
        continue

    # --- mode == "advanced" branch ---
    refined = False
    if role == "primary" and isolated_tokens:
        safe_tokens = []
        distributed_tokens = []
        for raw in isolated_tokens:
            norm = normalize_isolated_token(raw)
            if norm in IGNORED_TOKENS:
                diagnostics.ignored_tokens.append(raw)
                continue
            if expand_umbrella(norm):
                if belongs_to_coarse_via_expansion(norm, coarse):
                    distributed_tokens.append(norm)
                else:
                    # Umbrella token rejected — would cross family. Record it.
                    diagnostics.rejected_tokens.append(
                        {"token": raw, "role": role, "coarse": coarse, "reason": "umbrella_family_mismatch"}
                    )
                continue
            adv = TOKEN_TO_ADVANCED.get(norm)
            if adv is None:
                diagnostics.unmapped_muscles.append(raw)
                continue
            if advanced_token_belongs_to_coarse(raw, coarse):
                safe_tokens.append(adv)
            else:
                # Mapped-but-wrong-family — Codex round-2 §18.1.4.
                diagnostics.rejected_tokens.append(
                    {"token": raw, "role": role, "coarse": coarse, "reason": "family_mismatch"}
                )

        total_targets = len(safe_tokens) + sum(len(expand_umbrella(u)) for u in distributed_tokens)
        if total_targets > 0:
            share = contribution / total_targets
            for t in safe_tokens:
                totals[t] += share
            for u in distributed_tokens:
                for sub in expand_umbrella(u):
                    totals[sub] += share
            refined = True

    if not refined:
        rep = coarse_to_representative_advanced(coarse)
        totals[rep] += contribution
        diagnostics.fallback_count += 1
```

At request end, `logger.warning(...)` is emitted **once per request** for each non-empty list in diagnostics (`unmapped_muscles`, `rejected_tokens`, `blank_pst_rows`), with `request_id` from `utils/request_id.py` so the log line can be correlated with the caller.

### 7.3 Safety properties guaranteed

- **Primary sets never leak to a different Basic muscle family.** `advanced_token_belongs_to_coarse()` gates every refinement; if the token belongs to Triceps while primary is Chest, the token is rejected for refinement, Chest still receives the full primary contribution via representative fallback, **and** the rejection is appended to `diagnostics.rejected_tokens` (Codex round-2 §18.1.4). The guarantee is now executable in pseudocode (§7.2), not only prose.
- **No exercise row contributes zero silently.** Every row — including rows with all P/S/T blank — either attributes its `sets` contribution somewhere or appears in a diagnostics list (`blank_pst_rows`, `blank_pst_orphan`) that tests and the logger will see (Codex round-2 §18.1.1).
- **Unknown vs rejected vs ignored vs blank** are four distinct diagnostic buckets. An implementer cannot confuse them because each has its own pseudocode branch and its own dataclass field.
- **Secondary/tertiary attribution stays coarse in Advanced mode** (representative only). Known limit; surfaced via `fallback_count`.
- **Every distinct unmapped / rejected / blank row is logged once per request via `logger.warning`** with the request id and included in the response's diagnostics.

### 7.4 Numeric handling

- Internal totals are `float`; 0.25 increments never need higher precision.
- `remaining = max(0.0, target - planned)` for display; real delta stored separately as `delta = target - planned` (may be negative → `over`).
- `on_target` tolerance: `abs(delta) < 0.01`. Exact equality works in most cases (quarters) but guards against rounding drift.

---

## 8. Data model & API

### 8.1 Schema migration

Add two columns to `volume_plans`:

- `is_active INTEGER NOT NULL DEFAULT 0`
- `mode TEXT NOT NULL DEFAULT 'basic'`

Plus a partial unique index:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_volume_plans_active
  ON volume_plans(is_active) WHERE is_active = 1;
```

Migration function `add_volume_plan_activation_columns()` in `utils/database.py`:
- [x] Detects each column via `PRAGMA table_info(volume_plans)` before `ALTER TABLE` (idempotent).
- [x] Creates the partial unique index with `IF NOT EXISTS` (idempotent).
- [x] Safe to re-run on every startup.

Call-site coverage (Codex §13.5):

- [x] `app.py` startup, next to `add_volume_tracking_tables()` (around line 52). _(Covered transitively — `add_volume_tracking_tables()` invokes the migration internally.)_
- [x] `/erase-data` handler in `app.py:125`, after the tables are recreated. _(Covered transitively via `add_volume_tracking_tables()`; verified by `test_erase_data_recreates_columns_and_index`.)_
- [x] `tests/conftest.py` `_initialize_test_database()` (~line 107-112). _(Covered transitively via `add_volume_tracking_tables()`.)_
- [x] **Belt-and-suspenders**: `add_volume_tracking_tables()` itself calls `add_volume_plan_activation_columns()` as its final step, so any existing or future call site is automatically covered. Fresh call sites still call the migration explicitly in case the order is reversed.

### 8.1.1 Transaction safety for activate/deactivate (Codex round-2 §18.1.5)

Activating plan B must never leave the DB in a "no active plan" transient state on a stale `plan_id`, a missing row, or a mid-transaction exception. `DatabaseHandler.execute_query` already accepts `commit=False` (`utils/database.py:200-206`), so no API extension is needed.

Activate endpoint — `activate_volume_plan(plan_id)`:

```python
with DatabaseHandler() as db:
    # Guard 1: plan must exist before we touch active state.
    exists = db.fetch_one(
        "SELECT 1 FROM volume_plans WHERE id = ? LIMIT 1",
        (plan_id,),
    )
    if exists is None:
        return error_response("PLAN_NOT_FOUND", f"plan {plan_id} does not exist", status_code=404)

    # Guard 2: perform both writes in one transaction; rollback on any failure.
    try:
        db.execute_query(
            "UPDATE volume_plans SET is_active = 0 WHERE is_active = 1",
            commit=False,
        )
        rows = db.execute_query(
            "UPDATE volume_plans SET is_active = 1 WHERE id = ?",
            (plan_id,),
            commit=False,
        )
        # Guard 3: rowcount must be exactly 1; otherwise the plan was deleted
        # between the existence check and the update (single-user, but belt-and-suspenders).
        if rows != 1:
            db.connection.rollback()
            return error_response("PLAN_NOT_FOUND", f"plan {plan_id} disappeared mid-activate", status_code=404)
        db.connection.commit()
    except Exception:
        db.connection.rollback()
        raise   # outer handler converts to error_response("INTERNAL_ERROR", ...)
```

Deactivate endpoint — `deactivate_volume_plan(plan_id)`:

```python
with DatabaseHandler() as db:
    db.execute_query(
        "UPDATE volume_plans SET is_active = 0 WHERE id = ? AND is_active = 1",
        (plan_id,),
    )
    # Always 200. Idempotent: no existence check, no rollback path — zero-row update is fine.
    return success_response(data={"active_plan_id": None})
```

Invariants to prove in tests (see §12.2):
- [x] Activating a non-existent id returns 404 and leaves any currently-active plan untouched.
- [x] If the second UPDATE raises, the transaction rolls back and the previously-active plan is still active.
- [x] The partial unique index still guarantees at most one `is_active=1` row.
- [x] Deactivate is a no-op when the given id is already inactive.

### 8.2 Response payload (final shape)

`GET /api/volume_progress` → 200 always, whether or not a plan is active.

```json
{
  "ok": true,
  "status": "success",
  "data": {
    "active_plan_exists": true,
    "plan_id": 12,
    "mode": "basic",
    "training_days": 4,
    "created_at": "2026-04-24 12:00:00",
    "rows": [
      {
        "muscle": "Chest",
        "target": 16,
        "planned": 9.0,
        "remaining": 7.0,
        "delta": -7.0,
        "pct": 0.5625,
        "progress_status": "under",
        "target_status": "optimal"
      }
    ],
    "diagnostics": {
      "unmapped_muscles": [],
      "ignored_tokens": [],
      "fallback_count": 0
    }
  },
  "requestId": "..."
}
```

Status enumerations:
- `target_status` ∈ {`low`, `optimal`, `high`, `excessive`} — mirrors the splitter's existing recommended-range classification for this muscle's target. `none` when target is 0.
- `progress_status` ∈ {`no_target`, `unplanned_target`, `under`, `on_target`, `over`, `planned_without_target`}.

Rules for `progress_status`:
- `target == 0 and planned == 0` → `no_target`.
- `target > 0 and planned == 0` → `unplanned_target`.
- `target > 0 and planned < target - 0.01` → `under`.
- `target > 0 and abs(planned - target) < 0.01` → `on_target`.
- `target > 0 and planned > target + 0.01` → `over`.
- `target == 0 and planned > 0` → `planned_without_target` (exercise contributes to a muscle the active plan has no target for — UI shows an informational row).

### 8.2.1 `target_status` source of truth (Codex round-2 §18.1.3)

§8.2 promises `target_status` on every row, but the persisted data does not back it:
- `volume_plans` / `muscle_volumes` persist raw target volumes, plus a `status` column that `utils/volume_export.py` currently hardcodes to `'optimal'`.
- The splitter UI computes recommendation status client-side from editable range settings that are **not persisted** anywhere.

Draft v3 resolves this by making the **backend** the single source of truth for `target_status`, not the saved row:

- [x] Add `DEFAULT_RECOMMENDED_RANGES: dict[str, tuple[int, int, int, int]]` to `utils/volume_progress.py`. Each entry is `(low_max, optimal_max, high_max, excessive_min)` keyed by every member of `BASIC_MUSCLE_GROUPS` **and** `ADVANCED_MUSCLE_GROUPS`. Values come from the existing splitter default ranges (extract from `static/js/modules/volume-splitter.js` during Phase 1; commit the extracted constants in Python). _(Implementation matches the splitter's actual rule: `{min, max}` defaults of 12/20 for every muscle, plus `sets_per_session > 10` → `excessive` override read from `muscle_volumes.sets_per_session`. Statuses: `none` when target is 0, otherwise `low` / `optimal` / `high` / `excessive`. Codex round-3 §18.5 parity item closed.)_
- [x] `build_progress_rows()` computes `target_status` per row as (matches `routes/volume_splitter.py:108-116` exactly):
  ```python
  def _classify_target_status(muscle: str, target: float, sets_per_session: float = 0.0) -> str:
      if target <= 0:
          return "none"
      if sets_per_session > 10:
          return "excessive"
      ranges = DEFAULT_RECOMMENDED_RANGES.get(muscle, {"min": 12.0, "max": 20.0})
      if target < ranges["min"]:
          return "low"
      if target > ranges["max"]:
          return "high"
      return "optimal"
  ```
- [x] The persisted `muscle_volumes.status` column is **ignored** for the Plan-tab drawer (documented inline at the query site). It remains whatever `utils/volume_export.py` writes for backward compatibility with the existing Distribute UI; a later cleanup can either drop the column or repurpose it.
- [x] **Known limit — documented.** Custom range edits made in the splitter UI are not persisted today; the drawer's `target_status` therefore reflects the default range table, not any per-user range overrides. This is called out in §16 as an explicit follow-up (`Persist custom recommended ranges`) and in §14 as a minor risk. If the user needs per-plan overrides, that is a follow-up schema change (`volume_plans.custom_ranges JSON`) — out of scope for this feature.

### 8.2.2 Diagnostics payload additions

In addition to `unmapped_muscles`, `ignored_tokens`, `fallback_count` from §8.2, the `diagnostics` block now includes:

| Field | Type | Meaning | Added by round-2 § |
|---|---|---|---|
| `rejected_tokens` | `list[{token, role, coarse, reason}]` | Tokens that mapped to an advanced muscle but failed the family gate. | 18.1.4 |
| `blank_pst_rows` | `list[str]` | Exercise names with all three P/S/T blank at query time. | 18.1.1 |
| `blank_pst_orphan` | `int` | Count of blank-P/S/T rows whose isolated tokens could not be attributed at all. | 18.1.1 |
| `csv_fallback_count` | `int` | Rows where `exercise_isolated_muscles` was empty and we fell back to the CSV `advanced_isolated_muscles`. | 18.1.2 |

Hidden from the UI; asserted in §12.2 tests.

### 8.3 Backend source of truth

- [x] The panel never guesses delta client-side. Every mutation triggers a single backend refetch.
- [x] If two events fire within the 150 ms debounce window, the JS module coalesces to one fetch.

### 8.4 Endpoints

Added to `routes/volume_splitter.py`:

- [x] `POST /api/volume_plan/<int:plan_id>/activate` — body empty; 404 if plan not found; transaction per §8.1.1; response = `success_response(data={"active_plan_id": plan_id})`.
- [x] `POST /api/volume_plan/<int:plan_id>/deactivate` — idempotent; response = `success_response(data={"active_plan_id": None})`.

Modified in `routes/volume_splitter.py`:

- [x] `/api/volume_history` — include `is_active` and `mode` per row.
- [x] `/api/volume_plan/<id>` — include `is_active` and `mode`.
- [x] `/api/save_volume_plan` — accept `mode` (default `'basic'`) and persist it via `utils/volume_export.py`. Accept optional `activate: true` flag for the `Save & Activate` UX (§10.5); if present, run the activation transaction inside the save handler.

Added to `routes/workout_plan.py`:

- [x] `GET /api/volume_progress` — calls `build_progress_payload()`. Returns 200 with `active_plan_exists=false` payload when no active plan; returns 500 with `error_response("INTERNAL_ERROR", ...)` on unexpected exception (per `.claude/rules/routes.md` template).

---

## 9. Backend module — `utils/volume_progress.py`

Eight small helpers (Codex §13.12). Total module size target: ≤ 250 lines.

```python
def get_active_volume_plan() -> dict | None: ...
def get_plan_targets(plan_id: int) -> dict[str, int]: ...
def fetch_planned_rows() -> list[dict]: ...
def role_contributions(row: dict) -> list[tuple[str, str, float]]:
    """Yields (role_name, coarse_muscle, contribution_value) triples."""

def attribute_role_to_basic(coarse: str, contribution: float,
                            totals: dict, diagnostics: Diagnostics) -> None: ...
def attribute_role_to_advanced(role: str, coarse: str, contribution: float,
                               advanced_isolated_muscles: str | None,
                               totals: dict, diagnostics: Diagnostics) -> None: ...
def aggregate_planned_sets(mode: str) -> tuple[dict[str, float], Diagnostics]: ...
def build_progress_rows(plan: dict, planned: dict[str, float]) -> list[dict]: ...
def build_progress_payload() -> dict: ...
```

### 9.1 Module conventions
- [x] `logger = get_logger()` at top.
- [x] No imports from `routes/`. Imports only from `utils/`.
- [x] `Diagnostics` is a dataclass with the following fields (Codex round-2 §18.1.1, §18.1.2, §18.1.4): _(Implemented as a `dict` from `_new_diagnostics()` rather than a `@dataclass`; field set matches.)_
  ```python
  @dataclass
  class Diagnostics:
      unmapped_muscles: list[str] = field(default_factory=list)
      ignored_tokens: list[str]   = field(default_factory=list)
      rejected_tokens: list[dict] = field(default_factory=list)   # {token, role, coarse, reason}
      blank_pst_rows: list[str]   = field(default_factory=list)   # exercise names
      blank_pst_orphan: int       = 0
      fallback_count: int         = 0
      csv_fallback_count: int     = 0
  ```
- [x] `fetch_planned_rows()` is the single DB touchpoint and **prefers `exercise_isolated_muscles` over the CSV column** (Codex round-2 §18.1.2). The CSV column is kept only as a fallback audit source when the mapping table has no rows for the exercise.
  ```sql
  SELECT us.id              AS user_selection_id,
         us.sets,
         ex.exercise_name,
         ex.primary_muscle_group,
         ex.secondary_muscle_group,
         ex.tertiary_muscle_group,
         ex.advanced_isolated_muscles,           -- fallback audit source only
         GROUP_CONCAT(eim.muscle, '|')  AS iso_tokens_joined
    FROM user_selection us
    JOIN exercises ex        ON us.exercise = ex.exercise_name
    LEFT JOIN exercise_isolated_muscles eim
                              ON eim.exercise_name = ex.exercise_name
   GROUP BY us.id;
  ```
  Post-processing:
  ```python
  for raw in rows:
      mapping_tokens = split_pipe(raw["iso_tokens_joined"])
      if mapping_tokens:
          raw["isolated_tokens"] = mapping_tokens
      elif raw["advanced_isolated_muscles"]:
          raw["isolated_tokens"] = split_csv_semicolon(raw["advanced_isolated_muscles"])
          diagnostics.csv_fallback_count += 1
      else:
          raw["isolated_tokens"] = []
  ```
  Uses indexed columns via existing FK. The GROUP BY on `us.id` keeps per-row aggregation simple and does not blow up the row count for exercises with many isolated muscles. Performance sanity in §12.4 confirms p95 < 100 ms.
- [x] `aggregate_planned_sets('basic'|'advanced')` returns `(totals, diagnostics)` — always a complete dict keyed by the mode's muscle list (missing keys default to 0.0) so the UI renders a stable table.

---

## 10. Frontend

### 10.1 Drawer component (local, not Bootstrap offcanvas)

Codex §13.6 — the custom bundle excludes offcanvas. Ship a small local drawer.

- [x] New SCSS partial `scss/pages/_workout_plan_volume_panel.scss`:
  - Fixed-right `.vp-drawer` container, width 360 px desktop / 100% mobile.
  - `.vp-drawer[aria-hidden="false"]` slides in; `.vp-backdrop` fades in behind.
  - Status-dot colours: reuse existing `--status-low/-optimal/-high/-excessive` tokens if present; else define in the same partial.
- [x] Import the partial from `scss/custom-bootstrap.scss` at the bottom of the file.
- [x] Rebuild the bundle via `/build-css`. _(Build artefact `static/css/bootstrap.custom.min.css` is modified; rebuild already committed alongside the partial.)_
- [x] Drawer markup in `templates/workout_plan.html`:
  ```html
  <aside id="vpDrawer" class="vp-drawer" aria-hidden="true"
         aria-labelledby="vpDrawerTitle" role="complementary">
    <header>
      <h2 id="vpDrawerTitle">Volume targets</h2>
      <button type="button" class="vp-close" aria-label="Close volume targets">×</button>
    </header>
    <section id="vpDrawerBody"></section>
  </aside>
  <div id="vpBackdrop" class="vp-backdrop" hidden></div>
  <button id="vpToggle" type="button"
          aria-controls="vpDrawer" aria-expanded="false"
          class="btn btn-outline-primary btn-sm">Volume targets</button>
  ```
- [x] Open/close toggles `aria-hidden`, `aria-expanded`, and the backdrop `hidden`.
- [x] Persist open/closed in `localStorage.getItem('vpDrawer.open')`.

### 10.2 JS module — `static/js/modules/plan_volume_panel.js`

- [x] Exports a single initializer:
  ```js
  import { api } from './fetch-wrapper.js';

  export function initializePlanVolumePanel() {
    const root = document.getElementById('vpDrawer');
    if (!root) return;           // not on this page
    wireDrawer();
    fetchAndRender();
    document.addEventListener(
      'workout-plan:volume-affecting-change',
      debounce(fetchAndRender, 150)
    );
  }
  ```
- [x] `api.get('/api/volume_progress')` is the only fetch.
- [x] Render states: loading / empty / error / data. Empty state copy: "No active volume plan. Activate one from Volume Splitter to track remaining weekly sets." + link to `/volume_splitter`.
- [x] Use existing rendering helpers if present (`renderEmptyState`, `renderLoading`); else keep ≤ 150 lines of module-local DOM code.

### 10.3 Wire into `static/js/app.js`

- [x] Inside `initializeWorkoutPlan()`, after `initializeWorkoutPlanHandlers()`:
  ```js
  import { initializePlanVolumePanel } from './modules/plan_volume_panel.js';
  // ...
  initializePlanVolumePanel();
  ```

### 10.4 Event emission (Codex §13.8)

- [x] New helper in `static/js/modules/workout-plan-events.js` (or inline in the existing module):
  ```js
  export function notifyVolumeAffectingPlanChange(reason) {
    document.dispatchEvent(new CustomEvent('workout-plan:volume-affecting-change', {
      detail: { reason }
    }));
  }
  ```
- [x] Call sites **(must refresh)**:
  - [x] Add exercise success — `static/js/modules/workout-plan.js`.
  - [x] Add exercise success — `static/js/modules/exercises.js` (legacy path).
  - [x] Inline edit success for `sets`.
  - [x] Replace / swap exercise success (Codex §13.8 — this changes attribution even when sets stay the same).
  - [x] Remove exercise success.
  - [x] Clear workout plan success.
  - [x] Starter-plan generation success in `static/js/app.js`.
  - [x] Program-backup restore success if the handler runs while the Plan page is loaded.
- [x] Call sites **(must NOT refresh — enumerated so Codex round 2 can verify)**:
  - Exercise order changes (does not affect weekly totals).
  - Superset link / unlink (sets, count, and muscles unchanged).
  - Execution-style changes (panel is raw-set planning; unaffected by AMRAP/EMOM rules).
  - RIR / RPE / min-max rep / weight edits (panel is raw planned attribution, not effective-set or load-volume).

### 10.5 Activation UX (Codex §13.10 + Opus refinement)

On `/volume_splitter` (`templates/volume_splitter.html` + `static/js/modules/volume-splitter.js`):

- [x] New primary button `Save & Activate` beside `Export Volume Plan`. Posts with `activate: true` and redirects focus to the active-plan summary (`#volume-active-summary`) after the post-save history refresh; locked by `e2e/volume-progress.spec.ts:380` (`§10.5: Save & Activate via UI moves keyboard focus to the active-plan summary`).
- [x] History table — new `Active` column:
  - Rendered as a filled star for the active row, outline star on others.
  - `aria-label="Activate volume plan <id>"` / `"Deactivate active volume plan <id>"`.
  - Row class `is-active` applies a background highlight.
- [x] Active plan summary line in the Distribute header: `Active plan: #12, 4-day basic split (12 muscles targeted)`. Muted text when no plan active: `No active plan — activate one to drive the Plan tab.`.
- [x] Post-save toast: `Plan #12 saved. [Activate for Plan tab]`. Inline action button added in `static/js/modules/volume-splitter.js:exportVolumePlan` and supported by `static/js/modules/toast.js`.

On `/workout_plan`:

- [x] Active plan summary line in the page header above the routine tabs. Mirrors the one on Distribute. Clicking opens the drawer.

### 10.6 Accessibility

- [x] All new icon-only buttons have `aria-label`.
- [x] Drawer uses `role="complementary"`, `aria-labelledby`, `aria-hidden`; toggle uses `aria-controls`, `aria-expanded`.
- [x] Empty-state link has readable text; not just a chevron.
- [x] Progress-bar rows: wrap numeric progress in a `<progress>` element with `aria-valuenow`, `aria-valuemax`.

### 10.7 Bonus-from-compounds section (post-§12.5 smoke refinement)

Surfaced during §12.5 manual smoke: rows with `target=0` but `planned>0` were rendering as `N / 0`, which read as a divide-by-zero artefact rather than informative attribution.

- [x] Rows where `progress_status === 'planned_without_target'` are now rendered in a separate `.vp-bonus` section under the heading **"Bonus from compounds"** with the muted note _"Sets attributed to muscles you did not target in this plan."_
- [x] Targeted rows continue to render in the main `.vp-list` with the existing `planned / target` format and progress bar.
- [x] Bonus rows render only `N sets` (or `1 set`) — no `/ 0` denominator, no progress bar, italic to de-emphasize.
- [x] ARIA: bonus section uses `aria-labelledby` pointing at the heading; each bonus total has `aria-label` describing the muscle and source.
- [x] Locked by `e2e/volume-progress.spec.ts` (`untargeted muscles render under "Bonus from compounds", not as N / 0`).

---

## 11. Persistence of `mode` on save (Codex §13.5 follow-on)

- [x] `utils/volume_export.py:export_volume_plan()` accepts `mode: str = 'basic'` and writes it to the new column.
- [x] `routes/volume_splitter.py:/api/save_volume_plan` reads `mode` from the request body and forwards.
- [x] Remove the label-sniffing heuristic in `static/js/modules/volume-splitter.js` once the column is populated for new saves; keep a one-time fallback for legacy rows saved before the migration (treat as `'basic'` and re-save on next edit). _(`loadPlan()` now prefers `plan.mode` and falls back to label sniffing only when missing.)_

---

## 12. Verification

### 12.1 pytest — `tests/test_volume_taxonomy.py` (new, strict, Phase 0)

Runs against the live DB (read-only queries). Each failure blocks the feature.

- [x] `test_every_pst_value_has_basic_rollup` — for every row returned by `SELECT DISTINCT primary/secondary/tertiary_muscle_group`, `COARSE_TO_BASIC` has an entry whose value is in `BASIC_MUSCLE_GROUPS`.
- [x] `test_every_pst_value_has_representative_advanced` — same, for `COARSE_TO_REPRESENTATIVE_ADVANCED` → `ADVANCED_MUSCLE_GROUPS`.
- [x] `test_every_isolated_token_handled` — for every row returned by `SELECT DISTINCT muscle FROM exercise_isolated_muscles` plus every CSV item in `exercises.advanced_isolated_muscles`, the normalized token is either in `TOKEN_TO_ADVANCED`, in `IGNORED_TOKENS`, or in `DISTRIBUTED_UMBRELLA_TOKENS`.
- [x] `test_advanced_to_basic_is_total` — every member of `ADVANCED_MUSCLE_GROUPS` has an `ADVANCED_TO_BASIC` entry mapping to a member of `BASIC_MUSCLE_GROUPS`.
- [x] `test_advanced_set_normalizes_to_advanced_muscle_groups` — every token in `utils.constants.ADVANCED_SET`, after `normalize_isolated_token`, lives in `ADVANCED_MUSCLE_GROUPS` OR has a `TOKEN_TO_ADVANCED` mapping to one.
- [x] `test_design_calls_documented` — `advanced_to_basic('lower-trapezius') == 'Middle-Traps'`, `expand_umbrella('quadriceps') == ('rectus-femoris','inner-quadriceps','outer-quadriceps')`, `TOKEN_TO_ADVANCED['serratus-anterior'] == 'mid-lower-pectoralis'`. Pins decisions as executable code.
- [x] `test_blank_pst_strategy_is_set` (Codex round-2 §18.1.1) — `BLANK_PST_STRATEGY in {'isolated_only','backfill','exclude'}`. Guarantees Phase 0 made the `D-blank-pst` decision before any code ships.
- [x] `test_blank_pst_audit_section_present` — `docs/VOLUME_TAXONOMY_AUDIT.md` contains a section header `## Blank P/S/T exercises` and at least one row if the live DB has any such exercises (the test reads the live DB to decide the expectation).

### 12.2 pytest — `tests/test_volume_progress.py` (new)

Aggregation:
- [x] `test_bench_press_basic_mode_no_isolation` — `Bench Press` (no `advanced_isolated_muscles`) with 3 sets → Basic `Chest=3.0`, `Triceps=1.5`, `Front-Shoulder=0.75` (tertiary `Shoulders` rolls to `Front-Shoulder`). Asserts primary role never leaks to triceps.
- [x] `test_bench_press_with_mixed_isolated_tokens` — `Barbell Bench Press` whose `advanced_isolated_muscles='Chest; Lateral Head Triceps; Medial Head Triceps'` → primary Chest contribution stays entirely in Chest/pectoralis buckets (because triceps-head tokens don't match Chest coarse); secondary Triceps uses representative `long-head-triceps` at 0.5×sets. Explicitly regression-tests Codex §13.1. _(Implemented as `test_advanced_mode_primary_refinement_rejects_wrong_family_tokens`.)_
- [x] `test_advanced_mode_primary_refinement_safe_tokens_only` — exercise with `primary='Chest'` and `advanced_isolated_muscles='upper-pectoralis; mid-lower-pectoralis'` → 3 sets split 1.5 / 1.5 across those two keys.
- [x] `test_middle_shoulder_respects_phase0_decision` — an exercise with `primary='Middle-Shoulder'` produces the Basic rollup chosen in Phase 0 (test reads the decision from the taxonomy module so it stays in sync).
- [x] `test_unknown_token_goes_to_diagnostics_not_silent_loss` — an exercise with `advanced_isolated_muscles='some-unmapped-token'` still produces full primary-contribution attribution via representative fallback; `diagnostics.unmapped_muscles` contains `"some-unmapped-token"`. _(Implemented as `test_unknown_token_goes_to_diagnostics_with_representative_fallback`.)_
- [x] `test_mapped_wrong_family_token_is_rejected_with_diagnostic` (Codex round-2 §18.1.4) — seed `Bench Press` with `primary='Chest'` and isolated tokens `['long-head-triceps']`. Token maps successfully via `TOKEN_TO_ADVANCED` but fails `advanced_token_belongs_to_coarse`. Assertions: (a) Chest receives full primary contribution via representative fallback; (b) `diagnostics.rejected_tokens` contains exactly one entry with `token='long-head-triceps'`, `role='primary'`, `coarse='Chest'`, `reason='family_mismatch'`; (c) Triceps totals unchanged. _(Covered by `test_advanced_mode_primary_refinement_rejects_wrong_family_tokens`.)_
- [x] `test_selected_exercise_with_blank_pst_is_diagnostic_not_silent_loss` (Codex round-2 §18.1.1) — seed an exercise with P/S/T all NULL and `exercise_isolated_muscles=['upper-pectoralis','long-head-triceps']`, selected with 4 sets. Parameterise across `BLANK_PST_STRATEGY ∈ {'exclude','isolated_only'}`:
  - `exclude`: `totals == {}` for this exercise's contributions; `diagnostics.blank_pst_rows == [exercise_name]`.
  - `isolated_only`: primary-weight contribution (4.0) distributed between Chest bucket and Triceps bucket (Basic mode) or between `upper-pectoralis` / `long-head-triceps` (Advanced mode); `diagnostics.blank_pst_rows == [exercise_name]`. _(Implemented as `test_selected_exercise_with_blank_pst_uses_isolated_only_strategy` for the default strategy and `test_selected_exercise_with_blank_pst_exclude_strategy_records_diagnostic_only` for the `exclude` branch via `monkeypatch.setattr(utils.volume_taxonomy, "BLANK_PST_STRATEGY", "exclude")`.)_
- [x] `test_fetch_planned_rows_prefers_mapping_table_tokens` (Codex round-2 §18.1.2) — seed an exercise with `advanced_isolated_muscles='SHOULD_BE_IGNORED'` (non-canonical token) **and** canonical rows in `exercise_isolated_muscles=['upper-pectoralis']`. Aggregate and assert: (a) `upper-pectoralis` receives contribution; (b) `'SHOULD_BE_IGNORED'` does NOT appear in `diagnostics.unmapped_muscles`; (c) `diagnostics.csv_fallback_count == 0`.
- [x] `test_fetch_planned_rows_falls_back_to_csv_when_mapping_empty` — same exercise but `exercise_isolated_muscles` empty. Assert `csv_fallback_count == 1` and the CSV tokens drive attribution (or diagnostics if unmapped).
- [x] `test_ignored_token_is_not_attributed_but_is_recorded` — tokens in `IGNORED_TOKENS` appear in `diagnostics.ignored_tokens`.
- [x] `test_planned_without_target_row` — plan has `Glutes=0`, user added glute work → row appears with `progress_status='planned_without_target'`.
- [x] `test_target_without_planned_row` — plan has `Calves=12`, no calf exercises → row has `planned=0`, `progress_status='unplanned_target'`.
- [x] `test_on_target_tolerance` — planned 15.995, target 16 → `progress_status='on_target'`.

Schema / activation:
- [x] `test_migration_idempotent` — running `add_volume_plan_activation_columns()` twice is a no-op.
- [x] `test_migration_called_via_add_volume_tracking_tables` — calling `add_volume_tracking_tables()` on a fresh DB results in the columns and index being present.
- [x] `test_erase_data_recreates_columns_and_index` — POST `/erase-data` with confirm token, then read `PRAGMA table_info(volume_plans)` + `PRAGMA index_list(volume_plans)` — all present.
- [x] `test_only_one_plan_active_at_a_time` — save two plans, activate A, activate B → A cleared.
- [x] `test_activate_is_transactional` — monkey-patch the second `execute_query` to raise → DB still has A active (not both or neither).
- [x] `test_activate_nonexistent_plan_returns_404_and_preserves_active` (Codex round-2 §18.1.5) — with plan A active, POST `/api/volume_plan/999999/activate` → response is 404 with `PLAN_NOT_FOUND`; A is still active; zero rows have been touched.
- [x] `test_activate_rollback_when_set_row_disappears` (Codex round-2 §18.1.5) — monkey-patch the SET update to return rowcount 0 → response is 404, `is_active=1` count is still exactly 1, and the previously-active plan is still active (via rollback).
- [x] `test_deactivate_idempotent_for_inactive_plan` — POST deactivate on a plan that is already `is_active=0` → 200, no rows changed, still at most one active plan in the DB.
- [x] `test_partial_unique_index_prevents_two_active` — direct `INSERT ... is_active=1` when one already exists → `IntegrityError`.
- [x] `test_mode_persists_on_save` — save `mode='advanced'`, read back.
- [x] `test_target_status_computed_from_default_ranges` (Codex round-2 §18.1.3) — save `muscle_volumes.status='optimal'` explicitly and a target that the default-range table classifies as `low`. Response row has `target_status='low'` (backend overrides stored value). Confirms the drawer uses `DEFAULT_RECOMMENDED_RANGES`, not `muscle_volumes.status`.
- [x] `test_target_status_excessive_when_sets_per_session_exceeds_ten` (Codex round-3 §18.5) — `training_days=2` with `weekly_sets=22` → `sets_per_session=11` → `target_status='excessive'`. Locks parity with the splitter UI's `sets_per_session > 10` override.
- [x] `test_target_status_none_when_target_zero` — muscle untargeted in plan but planned > 0 → `target_status='none'` (not `'low'`); `progress_status='planned_without_target'`.
- [x] `test_default_recommended_ranges_cover_all_muscles` — `set(DEFAULT_RECOMMENDED_RANGES) >= set(BASIC_MUSCLE_GROUPS) | set(ADVANCED_MUSCLE_GROUPS)`. Prevents a missing-key KeyError at runtime.

API contract:
- [x] `test_no_active_plan_endpoint_returns_200_empty` — `GET /api/volume_progress` → 200 with `active_plan_exists=false`.
- [x] `test_endpoint_response_contract` — every new endpoint returns `{ok, status, data, requestId}` or the error variant.
- [x] `test_diagnostics_populated_when_bad_tokens_present` — seed a fake exercise with an unmapped token, assert diagnostics reflect it. _(Covered by `test_unknown_token_goes_to_diagnostics_with_representative_fallback`.)_

### 12.3 Playwright — `e2e/volume-progress.spec.ts` (new)

- [x] `happy path basic`: Distribute → Save & Activate a Basic plan → Plan tab → drawer opens → add Bench Press 3 sets → Chest row updates to `3.0/target` within 500 ms → clear → row reverts to `0/target`.
- [x] `replace exercise still refreshes` — add an exercise, then simulate replace (clear + add different-muscle exercise at same sets) and dispatch `replace-exercise` → drawer rebalances Chest → Quadriceps even though `sets` didn't change (Codex §13.8).
- [x] `clear plan refreshes` — `/clear_workout_plan` + `clear-workout-plan` event → all populated rows return to `planned=0`.
- [x] `starter plan generate refreshes` — `/generate_starter_plan` + `starter-plan-generated` event → at least one tracked muscle row leaves zero.
- [x] `advanced mode switches taxonomy` — Save & Activate an Advanced plan → drawer rows now keyed by advanced muscle names.
- [x] `deactivate → empty state` — deactivate from history → drawer empty state.
- [x] `delete active plan degrades gracefully` — delete active plan → drawer empty state, no JS error.
- [x] `drawer open state persists across reload`.
- [x] `viewport matrix` — desktop 1440, tablet 768, mobile 375 × light + dark; drawer renders correctly (basic visual assert on layout, not pixel-perfect). Covered by `e2e/volume-progress.spec.ts` viewport matrix tests; `npx playwright test e2e/volume-progress.spec.ts --project=chromium` -> 14 passed.

### 12.4 Performance sanity

- [x] Seed fixture with ~80 `user_selection` rows across routines; call `/api/volume_progress`; expect average response time well under the 100 ms slow-query log threshold (`utils/database.py:235`). Implemented in `tests/test_volume_progress.py:test_volume_progress_performance_sanity` with a 200 ms guardrail to absorb CI variance while still catching gross regressions.
- [ ] If slow: `EXPLAIN QUERY PLAN` on `fetch_planned_rows()` query; confirm the join uses the `user_selection.exercise` FK index. _(Not run; only relevant if the perf sanity test starts failing.)_

### 12.5 Manual smoke

- [x] `.venv/Scripts/python.exe app.py`; exercise every Phase-0 edge case; sanity-check totals against a pocket calculator. _(2026-04-25: user smoke on plan #160 with Chest=16/Quads=16/Triceps=10 targets and 5 exercises across 3 routines. All 7 displayed muscle totals tied out to P=1.0 / S=0.5 / T=0.25 weights against `aggregate_planned_sets()`. Surfaced one UX gap fixed in §10.7: untargeted-but-hit muscles previously rendered as `N / 0`; now grouped under "Bonus from compounds".)_
- [x] Run `/verify-suite` (pytest + Chromium E2E). Update `CLAUDE.md` §5 verified test counts. _(2026-04-25 refresh: `.venv/Scripts/python.exe -m pytest -q` -> 966 passed; `npx playwright test e2e/volume-splitter.spec.ts e2e/workout-plan.spec.ts e2e/volume-progress.spec.ts --project=chromium` with `PW_REUSE_SERVER=1` -> 60 passed. Full E2E baseline of 314 was not re-run this session.)_

---

## 13. Files touched (summary)

### New
- [x] `utils/volume_taxonomy.py`
- [x] `utils/volume_progress.py`
- [x] `static/js/modules/plan_volume_panel.js`
- [x] `scss/pages/_workout_plan_volume_panel.scss`
- [x] `tests/test_volume_taxonomy.py`
- [x] `tests/test_volume_progress.py`
- [x] `e2e/volume-progress.spec.ts`
- [x] `docs/VOLUME_TAXONOMY_AUDIT.md` (Phase 0 deliverable)

### Modified
- [x] `utils/database.py` — `add_volume_plan_activation_columns()`; `add_volume_tracking_tables()` calls it internally.
- [x] `app.py` — call the migration at startup; also at `/erase-data`. _(Covered transitively via `add_volume_tracking_tables()` at both call sites.)_
- [x] `tests/conftest.py` — call the migration. _(Covered transitively via `add_volume_tracking_tables()`.)_
- [x] `utils/volume_export.py` — persist `mode`.
- [x] `routes/volume_splitter.py` — import muscle lists from `utils/volume_taxonomy.py`; add activate/deactivate; include `is_active`/`mode` in history/detail; accept `mode` + optional `activate` on save.
- [x] `routes/workout_plan.py` — `GET /api/volume_progress`.
- [x] `templates/workout_plan.html` — drawer markup + active-plan header summary.
- [x] `templates/volume_splitter.html` — Save & Activate button; Active column; active-plan header summary.
- [x] `static/js/modules/volume-splitter.js` — send `mode` on save; wire Save & Activate; render/toggle Active column.
- [x] `static/js/modules/workout-plan.js` and `static/js/modules/exercises.js` — emit `workout-plan:volume-affecting-change` on the triggers enumerated in §10.4.
- [x] `static/js/app.js` — call `initializePlanVolumePanel()` in `initializeWorkoutPlan()`.
- [x] `scss/custom-bootstrap.scss` — import the new partial.
- [x] `CLAUDE.md` §5 — refresh verified test counts.

---

## 18. Phase 0 assessments

### 18.1 Post-Phase-0 confidence assessment

Date: 2026-04-25
Reviewer: Codex
Phase 0 test result: `pytest tests/test_volume_taxonomy.py -q` -> 8 passed in 0.02s
Decisions recorded: Yes, in `docs/VOLUME_TAXONOMY_AUDIT.md` and `utils/volume_taxonomy.py`, using the execution-plan recommended/default choices. Explicit user confirmation is still required before Phase 1 because §5.2 marks several rows as open-user decisions.
Remaining blockers: User confirmation of the provisional taxonomy decisions, especially adding `Middle-Shoulder` and `Hip-Adductors` to Basic, rolling `Rotator Cuff` to `Rear-Shoulder`, rolling generic `Shoulders` to `Front-Shoulder`, and keeping `BLANK_PST_STRATEGY = "isolated_only"`.
Confidence: 90%
Gate decision: `PATCH_PLAN`
Notes: Live audit was run against `data/database.db`. The live DB has 633 exercises with all P/S/T fields blank; 252 have isolated-token data. Phase 0 tests pass against that DB, but Phase 1+ implementation should not start until the product decisions above are explicitly approved or changed.

### 18.2 Post-Phase-0 confidence assessment

Date: 2026-04-25
Reviewer: Codex
Phase 0 test result: `.venv/Scripts/python.exe -m pytest tests/test_volume_taxonomy.py -q` -> 8 passed in 0.02s
Decisions recorded: Yes; user instruction to proceed confirms the recommended/default taxonomy decisions recorded in `docs/VOLUME_TAXONOMY_AUDIT.md` and `utils/volume_taxonomy.py`, including `BLANK_PST_STRATEGY = "isolated_only"`.
Remaining blockers: None for Phase 1.
Confidence: 95%
Gate decision: `PROCEED`
Notes: Phase 0 audit was run against live development DB `data/database.db`. Full implementation may begin.

