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

from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.normalization import normalize_muscle
from utils.profile_estimator import (
    DEFAULT_ESTIMATE,
    _match_direct_lift_key,
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
# Phase 2 reserved constants (not used by the MVP).
MIN_RELATED_LOGS = 3
MIN_RELATED_CONFIDENCE = "medium"

CONFIDENCE_NONE = "none"
CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

CALIBRATION_SOURCE = "exact_logs"

# -- Settings (default-off; estimator integration lands in a later phase) ----
DEFAULT_CALIBRATION_MODE = "off"
VALID_CALIBRATION_MODES = ("off", "suggest")

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
    row = db.fetch_one("SELECT mode FROM user_calibration_settings WHERE id = 1")
    mode = (row or {}).get("mode")
    return mode if mode in VALID_CALIBRATION_MODES else DEFAULT_CALIBRATION_MODE


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
        "lift_key": _match_direct_lift_key(canonical_name),
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
        "progression_status": decision["status"],
    }
    _upsert_calibration(payload, db=db)
    return payload


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
