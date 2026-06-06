"""Learned strength calibration (MVP — exact-exercise only).

Computes a per-exercise suggestion from the user's recent *logged* performance
so Workout Controls can improve from what was actually lifted, not only from
Profile reference lifts, demographics, or static defaults. See
``docs/user_profile/LEARNED_CALIBRATION_PLAN.md``.

MVP scope and guarantees
------------------------
- **Exact exercise only.** No related-exercise transfer (Phase 2).
- **Recompute-on-write, invalidate-on-delete.** A scored ``workout_log`` write
  recomputes this exercise's row; deleting its last usable log clears the row.
- **Produces, never consumes.** The estimator only *reads* these rows when
  ``user_calibration_settings.mode == 'suggest'`` (wired in a later phase).
  This module only writes them, so creating rows here changes no suggestion
  output on its own.
- **One canonical strength formula.** Strength uses :func:`epley_1rm` and
  next-target decisions delegate to :func:`decide_progression_target` — no
  second e1RM formula and no duplicated progression engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from utils.database import DatabaseHandler, upsert_user_profile_lift
from utils.logger import get_logger
from utils.normalization import normalize_equipment, normalize_muscle
from utils.lift_matching import match_direct_lift_key
from utils.profile_estimator import (
    DEFAULT_ESTIMATE,
    DUMBBELL_LIFT_KEYS,
    KEY_LIFT_LABELS,
    KEY_LIFTS,
    classify_tier,
    epley_1rm,
)
from utils.progression_plan import decide_progression_target

logger = get_logger()

# -- Confidence constants (plan §"Confidence Constants") --------------------
MIN_EXACT_LOGS_MEDIUM = 1
MIN_EXACT_LOGS_HIGH = 3
MAX_RECENT_DAYS = 90
STALE_AFTER_DAYS = 180
MAX_E1RM_VARIANCE_PCT_HIGH = 10
# Related transfer gates (Phase 2A).
MIN_RELATED_LOGS = 3
MIN_RELATED_CONFIDENCE = "medium"

CONFIDENCE_NONE = "none"
CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

CALIBRATION_SOURCE = "exact_logs"

# Outcomes surfaced to the UI after a scored log change (plan §"Notifications").
CALIB_STATUS_OFF = "off"
CALIB_STATUS_UPDATED = "updated"
CALIB_STATUS_LOW_CONFIDENCE = "low_confidence"
CALIB_STATUS_NONE = "none"

# -- Settings (default-off; estimator reads these in `suggest` mode) ----------
DEFAULT_CALIBRATION_MODE = "off"
VALID_CALIBRATION_MODES = ("off", "suggest")

# Confidence bands strong enough to override the existing estimator chain when
# mode is ``suggest``. A ``low`` band (stale / sparse / inconsistent) is *not*
# usable — the estimator falls through to its last-log / Profile chain instead,
# so weak evidence never displaces a real reference lift (plan §"Estimate
# Priority": learned wins only "when confidence is usable").
USABLE_SUGGEST_CONFIDENCES = (CONFIDENCE_MEDIUM, CONFIDENCE_HIGH)

_DT_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)


def get_calibration_mode(*, db: DatabaseHandler) -> str:
    """Return the active calibration mode; ``off`` when no settings row exists.

    A missing ``user_calibration_settings`` row must behave exactly like the
    current estimator (no learned suggestions) — this is the regression guard
    the plan calls out under §"Settings Default".
    """
    return get_calibration_settings(db=db)["mode"]


def get_calibration_settings(*, db: DatabaseHandler) -> dict[str, Any]:
    """Return learned-calibration settings with safe default-off semantics."""
    row = db.fetch_one(
        """
        SELECT mode, allow_related_exercise_learning, min_sessions_for_related
        FROM user_calibration_settings
        WHERE id = 1
        """
    )
    mode = (row or {}).get("mode")
    if mode not in VALID_CALIBRATION_MODES:
        mode = DEFAULT_CALIBRATION_MODE
    allow_related = bool((row or {}).get("allow_related_exercise_learning") or 0)
    return {
        "mode": mode,
        "allow_related_exercise_learning": allow_related,
        "min_sessions_for_related": (row or {}).get("min_sessions_for_related"),
    }


def related_exercise_learning_enabled(*, db: DatabaseHandler) -> bool:
    """True only when learned suggestions and related transfer are both enabled."""
    settings = get_calibration_settings(db=db)
    return (
        settings["mode"] == "suggest"
        and settings["allow_related_exercise_learning"] is True
    )


def set_calibration_settings(
    mode: str,
    *,
    db: DatabaseHandler,
    allow_related_exercise_learning: Optional[bool] = None,
) -> dict[str, Any]:
    """Upsert calibration settings; preserve the related flag when omitted."""
    if mode not in VALID_CALIBRATION_MODES:
        raise ValueError(f"mode must be one of {VALID_CALIBRATION_MODES}")

    if allow_related_exercise_learning is None:
        db.execute_query(
            """
            INSERT INTO user_calibration_settings (id, mode, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                mode = excluded.mode,
                updated_at = CURRENT_TIMESTAMP
            """,
            (mode,),
        )
    else:
        db.execute_query(
            """
            INSERT INTO user_calibration_settings (
                id, mode, allow_related_exercise_learning, updated_at
            )
            VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                mode = excluded.mode,
                allow_related_exercise_learning = excluded.allow_related_exercise_learning,
                updated_at = CURRENT_TIMESTAMP
            """,
            (mode, 1 if allow_related_exercise_learning else 0),
        )
    return get_calibration_settings(db=db)


def set_calibration_mode(mode: str, *, db: DatabaseHandler) -> str:
    """Upsert the single-row calibration mode; return the stored value.

    Turning learned suggestions on is an explicit user action (plan §"Settings
    Default"). Reserved Phase 2 columns keep their schema defaults.
    """
    return set_calibration_settings(mode, db=db)["mode"]


def get_learned_calibration(
    exercise_name: str, *, db: DatabaseHandler
) -> Optional[dict[str, Any]]:
    """Return the stored learned-calibration row for one exact exercise, or None.

    Read-only lookup used by the estimator. Whether the row is strong enough to
    *act on* is decided by the caller against :data:`USABLE_SUGGEST_CONFIDENCES`.
    """
    if not exercise_name or not exercise_name.strip():
        return None
    return db.fetch_one(
        "SELECT * FROM learned_strength_calibrations WHERE exercise_name = ? COLLATE NOCASE",
        (exercise_name.strip(),),
    )


def list_learned_calibrations(*, db: DatabaseHandler) -> list[dict[str, Any]]:
    """Return every learned-calibration row for the Phase 2B review surface.

    Read-only. Most-recently-observed first (then exercise name) so the user
    sees their freshest evidence at the top. Columns mirror what the dashboard
    renders — exercise, confidence, sample count, e1RM, suggestion, observed
    date — and never include internal transfer-ratio tuning data.
    """
    return db.fetch_all(
        """
        SELECT exercise_name, confidence, sample_count, estimated_1rm,
               suggested_weight, suggested_min_reps, suggested_max_reps,
               suggested_rir, suggested_rpe, last_observed_at, updated_at
        FROM learned_strength_calibrations
        ORDER BY last_observed_at DESC, exercise_name COLLATE NOCASE
        """
    )


def list_ignored_transfers(*, db: DatabaseHandler) -> list[dict[str, Any]]:
    """Return every ignored related source→target pair (newest first)."""
    return db.fetch_all(
        """
        SELECT source_exercise_name, target_exercise_name, created_at
        FROM ignored_calibration_transfers
        ORDER BY created_at DESC, id DESC
        """
    )


_CONFIDENCE_RANK = {
    CONFIDENCE_LOW: 1,
    CONFIDENCE_MEDIUM: 2,
    CONFIDENCE_HIGH: 3,
}

_LOAD_BASIS_FACTOR = {
    "total_to_total": 1.0,
    "total_to_per_hand": 0.5,
    "per_hand_to_total": 2.0,
    "per_hand_to_per_hand": 1.0,
}


def ignore_calibration_transfer(
    source_exercise_name: str, target_exercise_name: str, *, db: DatabaseHandler
) -> None:
    """Suppress one related source-target pair without deleting exact evidence."""
    source = (source_exercise_name or "").strip()
    target = (target_exercise_name or "").strip()
    if not source or not target:
        return
    db.execute_query(
        """
        INSERT INTO ignored_calibration_transfers (
            source_exercise_name, target_exercise_name, created_at
        )
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(source_exercise_name, target_exercise_name) DO NOTHING
        """,
        (source, target),
    )


def unignore_calibration_transfer(
    source_exercise_name: str, target_exercise_name: str, *, db: DatabaseHandler
) -> None:
    """Restore one previously-ignored related pair (Phase 2B control).

    Removes only the ignore record — the source exercise's exact learned
    calibration is untouched, so related fallback becomes eligible again for
    that target if a transfer ratio still exists.
    """
    source = (source_exercise_name or "").strip()
    target = (target_exercise_name or "").strip()
    if not source or not target:
        return
    db.execute_query(
        """
        DELETE FROM ignored_calibration_transfers
        WHERE source_exercise_name = ? COLLATE NOCASE
          AND target_exercise_name = ? COLLATE NOCASE
        """,
        (source, target),
    )


def clear_ignored_transfers(*, db: DatabaseHandler) -> None:
    """Remove all ignored related pairs (Phase 2B bulk control)."""
    db.execute_query("DELETE FROM ignored_calibration_transfers")


def get_related_calibration_candidate(
    target_exercise_row: dict[str, Any],
    *,
    db: DatabaseHandler,
    now: Optional[datetime] = None,
) -> Optional[dict[str, Any]]:
    """Return the strongest eligible related calibration for a target exercise.

    Phase 2A is intentionally read-only and ratio-gated: no explicit
    ``exercise_transfer_ratios`` row means no related suggestion, even when a
    plausible source calibration exists.
    """
    if not related_exercise_learning_enabled(db=db):
        return None
    if not target_exercise_row or classify_tier(target_exercise_row) == "excluded":
        return None

    target_name = (target_exercise_row.get("exercise_name") or "").strip()
    if not target_name:
        return None

    now = now or _utcnow()
    target_lift_key = match_direct_lift_key(target_name)
    rows = db.fetch_all(
        """
        SELECT
            c.exercise_name AS source_exercise_name,
            c.lift_key AS source_lift_key,
            c.primary_muscle AS source_primary_muscle,
            c.estimated_1rm AS source_estimated_1rm,
            c.suggested_weight AS source_suggested_weight,
            c.suggested_min_reps AS source_suggested_min_reps,
            c.suggested_max_reps AS source_suggested_max_reps,
            c.confidence AS source_confidence,
            c.sample_count AS source_sample_count,
            c.last_observed_at AS source_last_observed_at,
            r.id AS transfer_ratio_id,
            r.source_lift_key AS ratio_source_lift_key,
            r.target_lift_key AS ratio_target_lift_key,
            r.ratio AS transfer_ratio,
            r.load_basis,
            r.relationship_type,
            r.confidence AS transfer_confidence,
            r.notes AS transfer_notes
        FROM exercise_transfer_ratios r
        JOIN learned_strength_calibrations c
          ON c.exercise_name = r.source_exercise_name COLLATE NOCASE
        LEFT JOIN ignored_calibration_transfers ignored
          ON ignored.source_exercise_name = r.source_exercise_name COLLATE NOCASE
         AND ignored.target_exercise_name = r.target_exercise_name COLLATE NOCASE
        WHERE r.target_exercise_name = ? COLLATE NOCASE
          AND c.exercise_name <> ? COLLATE NOCASE
          AND ignored.id IS NULL
        """,
        (target_name, target_name),
    )

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if row.get("source_confidence") not in USABLE_SUGGEST_CONFIDENCES:
            continue
        if int(row.get("source_sample_count") or 0) < MIN_RELATED_LOGS:
            continue
        observed_at = _parse_dt(row.get("source_last_observed_at"))
        if observed_at is not None and _age_days(now, observed_at) > STALE_AFTER_DAYS:
            continue
        if row.get("transfer_confidence") not in USABLE_SUGGEST_CONFIDENCES:
            continue
        basis_factor = _LOAD_BASIS_FACTOR.get(row.get("load_basis"))
        if basis_factor is None:
            continue
        try:
            source_e1rm = float(row["source_estimated_1rm"])
            transfer_ratio = float(row["transfer_ratio"])
        except (TypeError, ValueError):
            continue
        if source_e1rm <= 0 or transfer_ratio <= 0:
            continue
        ratio_source_key = row.get("ratio_source_lift_key")
        ratio_target_key = row.get("ratio_target_lift_key")
        if ratio_source_key and row.get("source_lift_key") and ratio_source_key != row.get("source_lift_key"):
            continue
        if ratio_target_key and target_lift_key and ratio_target_key != target_lift_key:
            continue

        target_e1rm = source_e1rm * transfer_ratio * basis_factor
        candidate = dict(row)
        candidate.update({
            "target_exercise_name": target_name,
            "target_lift_key": target_lift_key,
            "target_estimated_1rm": target_e1rm,
            "load_basis_factor": basis_factor,
        })
        candidates.append(candidate)

    if not candidates:
        return None

    def sort_key(row: dict[str, Any]) -> tuple[int, datetime, int]:
        observed = _parse_dt(row.get("source_last_observed_at")) or datetime.min
        return (
            _CONFIDENCE_RANK.get(row.get("source_confidence"), 0),
            observed,
            int(row.get("source_sample_count") or 0),
        )

    return max(candidates, key=sort_key)


def _utcnow() -> datetime:
    """Naive UTC `now`, matching SQLite's ``CURRENT_TIMESTAMP`` for age math."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _age_days(now: datetime, created_at: Any) -> float:
    """Days between ``now`` and a log's ``created_at``.

    Unparseable / missing timestamps are treated as age 0 (recent) rather than
    silently dropping the log — being unable to read a timestamp shouldn't make
    a usable set vanish from the sample.
    """
    parsed = _parse_dt(created_at)
    if parsed is None:
        return 0.0
    return max((now - parsed).total_seconds() / 86400.0, 0.0)


def _valid_logs_for_exercise(
    exercise_name: str, db: DatabaseHandler
) -> list[dict[str, Any]]:
    """Recent-first scored logs that carry usable weight and reps.

    Learning is from *actual performance*, so only ``scored_*`` data counts; a
    log without a scored weight and a scored top-set rep count is incomplete
    and ignored (plan non-goal: don't learn from incomplete logs).
    """
    rows = db.fetch_all(
        """
        SELECT id, scored_weight, scored_max_reps, scored_min_reps,
               scored_rir, scored_rpe, planned_min_reps, planned_max_reps,
               planned_rir, planned_rpe, created_at
        FROM workout_log
        WHERE exercise = ? COLLATE NOCASE
        ORDER BY created_at DESC, id DESC
        """,
        (exercise_name,),
    )
    valid: list[dict[str, Any]] = []
    for row in rows:
        weight = row.get("scored_weight")
        reps = row.get("scored_max_reps")
        if weight is None or reps is None:
            continue
        try:
            weight = float(weight)
            reps = int(reps)
        except (TypeError, ValueError):
            continue
        if weight <= 0 or reps <= 0:
            continue
        valid.append(row)
    return valid


def _variance_within_high_band(e1rms: list[float]) -> bool:
    vals = [v for v in e1rms if v > 0]
    if len(vals) < 2:
        return True
    mean = sum(vals) / len(vals)
    if mean <= 0:
        return False
    spread_pct = (max(vals) - min(vals)) / mean * 100
    return spread_pct <= MAX_E1RM_VARIANCE_PCT_HIGH


def _classify_confidence(
    *, sample_count: int, latest_age: float, recent_e1rms: list[float]
) -> str:
    """Map the sample to a confidence band (plan §"Confidence Constants").

    - ``high``  — ≥3 recent (≤90d) valid logs, the latest is recent, and their
      e1RM spread is within 10%.
    - ``medium`` — at least 1 valid log and the latest is within 180d.
    - ``low``   — valid but stale / sparse / inconsistent.
    """
    recent_count = len(recent_e1rms)
    if (
        recent_count >= MIN_EXACT_LOGS_HIGH
        and latest_age <= MAX_RECENT_DAYS
        and _variance_within_high_band(recent_e1rms)
    ):
        return CONFIDENCE_HIGH
    if latest_age <= STALE_AFTER_DAYS and sample_count >= MIN_EXACT_LOGS_MEDIUM:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def _delete_calibration(exercise_name: str, *, db: DatabaseHandler) -> None:
    db.execute_query(
        "DELETE FROM learned_strength_calibrations WHERE exercise_name = ? COLLATE NOCASE",
        (exercise_name,),
    )


def reset_calibration_for_exercise(exercise_name: str, *, db: DatabaseHandler) -> None:
    """Clear the learned calibration row for one exercise (user reset action)."""
    if not exercise_name or not exercise_name.strip():
        return
    _delete_calibration(exercise_name.strip(), db=db)


def reset_all_calibrations(*, db: DatabaseHandler) -> None:
    """Clear every learned-calibration row (Phase 2B bulk reset control).

    Deletes only ``learned_strength_calibrations`` — settings and curated
    transfer ratios are left intact, and rows recompute on the next scored log.
    """
    db.execute_query("DELETE FROM learned_strength_calibrations")


# -- Phase 2C: promote learned calibration → declared Profile reference lift --
#
# The only Phase 2 path that writes user-declared baseline data. It graduates a
# *measured* learned result into ``user_profile_lifts`` so it survives learned
# mode being off/stale once exact log fallback is unavailable, and feeds the
# Profile/cold-start/cohort surfaces that never read learned rows. Estimator
# priority is unchanged: while learned mode is on and the row is usable, Workout
# Controls still serves the learned suggestion, not the promoted Profile value
# (plan §"Phase 2C").


def _promotion_basis_factor(source_is_per_hand: bool, target_is_per_hand: bool) -> float:
    """Convert a measured load from the *exercise* basis to the *lift_key* basis.

    Dumbbell loads are per hand; everything else is a single total/system load
    (same "two dumbbells = one barbell" model as
    :func:`profile_estimator._load_basis_factor`, but the source side here is
    the exercise, not a reference lift_key).
    """
    if source_is_per_hand == target_is_per_hand:
        return 1.0
    return 2.0 if source_is_per_hand else 0.5


def resolve_promotion_target(
    exercise_name: str, *, db: DatabaseHandler
) -> Optional[dict[str, Any]]:
    """Return the promotion plan for one exact learned calibration, or ``None``.

    Promotable only when (plan §"Phase 2C / Eligibility"): a learned row exists
    with usable (``medium``/``high``) confidence; ``exercise_name`` resolves to a
    known ``KEY_LIFTS`` reference-lift slug; and the source log
    (``last_log_id``) still carries a usable scored top set. The measured top
    set is basis-converted into the slug's load basis — no estimator math and no
    rounding to equipment increments (reference lifts hold raw user values).
    """
    if not exercise_name or not exercise_name.strip():
        return None
    row = get_learned_calibration(exercise_name.strip(), db=db)
    if not row or row.get("confidence") not in USABLE_SUGGEST_CONFIDENCES:
        return None

    canonical_name = row.get("exercise_name") or exercise_name.strip()
    lift_key = match_direct_lift_key(canonical_name)
    if not lift_key or lift_key not in KEY_LIFTS:
        return None

    last_log_id = row.get("last_log_id")
    if last_log_id is None:
        return None
    log = db.fetch_one(
        "SELECT scored_weight, scored_max_reps FROM workout_log WHERE id = ?",
        (last_log_id,),
    )
    if not log:
        return None
    scored_weight = log.get("scored_weight")
    scored_reps = log.get("scored_max_reps")
    if scored_weight is None or scored_reps is None:
        return None
    try:
        scored_weight = float(scored_weight)
        scored_reps = int(scored_reps)
    except (TypeError, ValueError):
        return None
    if scored_weight <= 0 or scored_reps <= 0:
        return None

    exercise_row = db.fetch_one(
        """
        SELECT exercise_name, primary_muscle_group, equipment, mechanic, movement_pattern
        FROM exercises
        WHERE exercise_name = ? COLLATE NOCASE
        """,
        (canonical_name,),
    )
    if not exercise_row or classify_tier(exercise_row) == "excluded":
        return None
    source_is_per_hand = (
        normalize_equipment((exercise_row or {}).get("equipment")) == "Dumbbells"
    )
    factor = _promotion_basis_factor(source_is_per_hand, lift_key in DUMBBELL_LIFT_KEYS)
    weight_kg = round(scored_weight * factor, 2)

    existing = db.fetch_one(
        "SELECT weight_kg, reps FROM user_profile_lifts WHERE lift_key = ?",
        (lift_key,),
    )
    existing_reference = None
    if existing and (
        existing.get("weight_kg") is not None or existing.get("reps") is not None
    ):
        existing_reference = {
            "weight_kg": existing.get("weight_kg"),
            "reps": existing.get("reps"),
        }

    return {
        "exercise_name": canonical_name,
        "lift_key": lift_key,
        "lift_label": KEY_LIFT_LABELS.get(lift_key, lift_key),
        "weight_kg": weight_kg,
        "reps": scored_reps,
        "confidence": row.get("confidence"),
        "existing_reference": existing_reference,
    }


def promote_calibration_to_profile(
    exercise_name: str, *, db: DatabaseHandler, overwrite: bool = False
) -> dict[str, Any]:
    """Promote an exact learned calibration into the Profile reference lift.

    Returns a status dict the route maps to a response:

    - ``not_promotable`` — no usable learned row / unresolvable slug / no source
      log (route → ``NOT_PROMOTABLE`` 400).
    - ``exists`` — a reference lift already exists and ``overwrite`` is false; no
      write (route → ``REFERENCE_LIFT_EXISTS`` 400 guard; the UI confirms first).
    - ``promoted`` — written. Graduates the row; does **not** delete it, and
      touches nothing but ``user_profile_lifts``.
    """
    target = resolve_promotion_target(exercise_name, db=db)
    if target is None:
        return {"status": "not_promotable"}
    if target["existing_reference"] is not None and not overwrite:
        return {"status": "exists", "target": target}

    upsert_user_profile_lift(
        target["lift_key"], target["weight_kg"], target["reps"], db=db
    )
    return {
        "status": "promoted",
        "lift_key": target["lift_key"],
        "lift_label": target["lift_label"],
        "weight_kg": target["weight_kg"],
        "reps": target["reps"],
        "overwrote": target["existing_reference"] is not None,
        "previous": target["existing_reference"],
    }


def get_calibration_dashboard(*, db: DatabaseHandler) -> dict[str, Any]:
    """Learned + ignored review payload, with per-row promotion annotations.

    Read-only. Each learned row gains ``lift_key`` / ``lift_label`` /
    ``promotable`` / ``existing_reference`` / ``promote_weight_kg`` /
    ``promote_reps`` so the Profile review table can render the right button
    label and confirm copy without a per-click round-trip (plan §"Phase 2C /
    Route contract"). Never mutates state.
    """
    learned = list_learned_calibrations(db=db)
    for row in learned:
        target = resolve_promotion_target(row.get("exercise_name"), db=db)
        if target is None:
            row["promotable"] = False
            row["lift_key"] = None
            row["lift_label"] = None
            row["existing_reference"] = None
            row["promote_weight_kg"] = None
            row["promote_reps"] = None
        else:
            row["promotable"] = True
            row["lift_key"] = target["lift_key"]
            row["lift_label"] = target["lift_label"]
            row["existing_reference"] = target["existing_reference"]
            row["promote_weight_kg"] = target["weight_kg"]
            row["promote_reps"] = target["reps"]
    return {
        "learned": learned,
        "ignored_transfers": list_ignored_transfers(db=db),
    }


def update_calibration_for_exercise(
    exercise_name: str, *, db: DatabaseHandler, now: Optional[datetime] = None
) -> Optional[dict[str, Any]]:
    """Recompute and upsert the learned calibration for one exact exercise.

    Returns the stored calibration payload, or ``None`` when the exercise is
    unknown, excluded, or has no usable scored logs (in which case any stale
    calibration row is removed). Reuses the caller's open ``DatabaseHandler``
    so the workout-log write path stays in a single transaction.
    """
    if not exercise_name or not exercise_name.strip():
        return None
    exercise_name = exercise_name.strip()
    now = now or _utcnow()

    exercise_row = db.fetch_one(
        """
        SELECT exercise_name, primary_muscle_group, equipment, mechanic, movement_pattern
        FROM exercises
        WHERE exercise_name = ? COLLATE NOCASE
        """,
        (exercise_name,),
    )
    if not exercise_row or classify_tier(exercise_row) == "excluded":
        _delete_calibration(exercise_name, db=db)
        return None

    canonical_name = exercise_row["exercise_name"]
    valid_logs = _valid_logs_for_exercise(canonical_name, db)
    if not valid_logs:
        _delete_calibration(canonical_name, db=db)
        return None

    e1rms = [
        epley_1rm(float(row["scored_weight"]), int(row["scored_max_reps"]))
        for row in valid_logs
    ]
    ages = [_age_days(now, row.get("created_at")) for row in valid_logs]
    recent_e1rms = [
        e1rm for e1rm, age in zip(e1rms, ages) if age <= MAX_RECENT_DAYS
    ]
    confidence = _classify_confidence(
        sample_count=len(valid_logs),
        latest_age=ages[0],
        recent_e1rms=recent_e1rms,
    )

    latest = valid_logs[0]
    weight = float(latest["scored_weight"])
    reps = int(latest["scored_max_reps"])
    planned_min = latest.get("planned_min_reps") or DEFAULT_ESTIMATE["min_rep"]
    planned_max = latest.get("planned_max_reps") or DEFAULT_ESTIMATE["max_rep"]
    scored_rir = latest.get("scored_rir")
    scored_rpe = latest.get("scored_rpe")

    decision = decide_progression_target(
        weight=weight,
        reps=reps,
        planned_min_reps=planned_min,
        planned_max_reps=planned_max,
        rir=scored_rir,
        rpe=scored_rpe,
    )

    payload = {
        "exercise_name": canonical_name,
        "lift_key": match_direct_lift_key(canonical_name),
        "primary_muscle": normalize_muscle(exercise_row.get("primary_muscle_group")),
        "estimated_1rm": round(e1rms[0], 2),
        "suggested_weight": decision["suggested_weight"],
        "suggested_min_reps": decision["suggested_min_reps"],
        "suggested_max_reps": decision["suggested_max_reps"],
        "suggested_rir": scored_rir if scored_rir is not None else latest.get("planned_rir"),
        "suggested_rpe": scored_rpe if scored_rpe is not None else latest.get("planned_rpe"),
        "confidence": confidence,
        "sample_count": len(valid_logs),
        "last_log_id": latest["id"],
        "last_observed_at": (
            str(latest["created_at"]) if latest.get("created_at") is not None else None
        ),
        "source": CALIBRATION_SOURCE,
    }
    _upsert_calibration(payload, db=db)
    return payload


def recompute_calibration_after_log(
    exercise_name: str, *, db: DatabaseHandler, now: Optional[datetime] = None
) -> dict[str, Any]:
    """Recompute one exercise's calibration after a scored log change.

    Returns a small UI-facing summary the workout-log route forwards so the
    client can pick the right notification (plan §"Notifications"):

    - ``off``            — learned calibration is disabled (mode ``off`` / no
      settings row); the row is still recomputed so it's ready if enabled later.
    - ``updated``        — usable confidence (medium/high); the suggestion changed.
    - ``low_confidence`` — recomputed but too weak/stale/sparse to act on.
    - ``none``           — no usable scored logs remain (row cleared / unknown).

    Reuses the caller's open ``DatabaseHandler`` (single transaction with the
    log write — plan §"DatabaseHandler Requirement").
    """
    mode = get_calibration_mode(db=db)
    payload = update_calibration_for_exercise(exercise_name, db=db, now=now)

    if mode != "suggest":
        status = CALIB_STATUS_OFF
    elif payload is None:
        status = CALIB_STATUS_NONE
    elif payload.get("confidence") in USABLE_SUGGEST_CONFIDENCES:
        status = CALIB_STATUS_UPDATED
    else:
        status = CALIB_STATUS_LOW_CONFIDENCE

    return {
        "mode": mode,
        "status": status,
        "exercise": (payload or {}).get("exercise_name", exercise_name),
        "confidence": (payload or {}).get("confidence"),
    }


def _upsert_calibration(payload: dict[str, Any], *, db: DatabaseHandler) -> None:
    db.execute_query(
        """
        INSERT INTO learned_strength_calibrations (
            exercise_name, lift_key, primary_muscle, estimated_1rm,
            suggested_weight, suggested_min_reps, suggested_max_reps,
            suggested_rir, suggested_rpe, confidence, sample_count,
            last_log_id, last_observed_at, source, created_at, updated_at
        ) VALUES (
            :exercise_name, :lift_key, :primary_muscle, :estimated_1rm,
            :suggested_weight, :suggested_min_reps, :suggested_max_reps,
            :suggested_rir, :suggested_rpe, :confidence, :sample_count,
            :last_log_id, :last_observed_at, :source, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT(exercise_name) DO UPDATE SET
            lift_key = excluded.lift_key,
            primary_muscle = excluded.primary_muscle,
            estimated_1rm = excluded.estimated_1rm,
            suggested_weight = excluded.suggested_weight,
            suggested_min_reps = excluded.suggested_min_reps,
            suggested_max_reps = excluded.suggested_max_reps,
            suggested_rir = excluded.suggested_rir,
            suggested_rpe = excluded.suggested_rpe,
            confidence = excluded.confidence,
            sample_count = excluded.sample_count,
            last_log_id = excluded.last_log_id,
            last_observed_at = excluded.last_observed_at,
            source = excluded.source,
            updated_at = CURRENT_TIMESTAMP
        """,
        {key: payload[key] for key in (
            "exercise_name", "lift_key", "primary_muscle", "estimated_1rm",
            "suggested_weight", "suggested_min_reps", "suggested_max_reps",
            "suggested_rir", "suggested_rpe", "confidence", "sample_count",
            "last_log_id", "last_observed_at", "source",
        )},
    )
