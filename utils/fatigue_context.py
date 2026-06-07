"""Advisory fatigue context for Workout Controls (Phase 2D-A).

A strictly **additive, post-estimate advisory layer**. It reads the shipped
Fatigue Meter surface (``utils.fatigue_data.build_fatigue_page_context``) and
the exercise's primary muscle, then describes that muscle's accumulated
fatigue as read-only context. It never changes a suggested number, never
touches the estimator priority chain, and never tunes fatigue thresholds.

Guarantees
----------
- **Separate switch.** Settings live in their own single-row
  ``fatigue_context_settings`` table, independent of learned calibration.
- **Default off.** No settings row behaves as disabled, and a disabled layer
  adds **no** key to the estimate response (byte-for-byte unchanged).
- **No new fatigue math.** Bands/percentages come straight from the shipped
  ``utils.fatigue`` landmarks; this module only labels them.
- **Advisory copy only.** Every variant ends with
  "This does not change your suggestion."

See ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md`` §"Phase 2D-A".
"""
from __future__ import annotations

from typing import Any, Optional

from utils.database import DatabaseHandler
from utils.fatigue import (
    DEFAULT_PERIOD,
    MUSCLE_VOLUME_LANDMARKS,
    PERIOD_LABELS,
    VALID_PERIODS,
    canonicalize_muscle_for_fatigue,
)
from utils.fatigue_data import build_fatigue_page_context
from utils.logger import get_logger

logger = get_logger()

# -- Settings vocabulary (defaults locked in the Phase 2D-A plan) -------------
VALID_FATIGUE_CONTEXT_SOURCES = ("planned", "logged", "both")
DEFAULT_FATIGUE_CONTEXT_ENABLED = False
DEFAULT_FATIGUE_CONTEXT_SOURCE = "both"
# context_period reuses the shipped Fatigue Meter period vocabulary
# (utils.fatigue.VALID_PERIODS); the default mirrors the page default.
DEFAULT_FATIGUE_CONTEXT_PERIOD = DEFAULT_PERIOD  # "this_week"

# Advisory line shown on every variant — the locked Phase 2D-A copy guarantee.
FATIGUE_CONTEXT_ADVISORY = "This does not change your suggestion."

_BAND_LABELS = {
    "light": "light",
    "moderate": "moderate",
    "heavy": "heavy",
    "very_heavy": "very heavy",
}


# =============================================================================
# Settings (single-row table, default-off)
# =============================================================================
def get_fatigue_context_settings(*, db: DatabaseHandler) -> dict[str, Any]:
    """Return fatigue-context settings with safe default-off semantics.

    A missing ``fatigue_context_settings`` row reads as disabled with the
    locked defaults, so the advisory layer stays inert until the user opts in.
    """
    row = db.fetch_one(
        """
        SELECT enabled, context_source, context_period
        FROM fatigue_context_settings
        WHERE id = 1
        """
    )
    enabled = bool((row or {}).get("enabled") or 0)
    source = (row or {}).get("context_source")
    if source not in VALID_FATIGUE_CONTEXT_SOURCES:
        source = DEFAULT_FATIGUE_CONTEXT_SOURCE
    period = (row or {}).get("context_period")
    if period not in VALID_PERIODS:
        period = DEFAULT_FATIGUE_CONTEXT_PERIOD
    return {
        "enabled": enabled,
        "context_source": source,
        "context_period": period,
    }


def set_fatigue_context_settings(
    *,
    db: DatabaseHandler,
    enabled: Optional[bool] = None,
    context_source: Optional[str] = None,
    context_period: Optional[str] = None,
) -> dict[str, Any]:
    """Upsert fatigue-context settings; omitted fields keep their current value."""
    current = get_fatigue_context_settings(db=db)
    new_enabled = current["enabled"] if enabled is None else bool(enabled)
    new_source = current["context_source"] if context_source is None else context_source
    new_period = current["context_period"] if context_period is None else context_period

    if new_source not in VALID_FATIGUE_CONTEXT_SOURCES:
        raise ValueError(
            f"context_source must be one of {VALID_FATIGUE_CONTEXT_SOURCES}"
        )
    if new_period not in VALID_PERIODS:
        raise ValueError(f"context_period must be one of {VALID_PERIODS}")

    db.execute_query(
        """
        INSERT INTO fatigue_context_settings (
            id, enabled, context_source, context_period, updated_at
        )
        VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            enabled = excluded.enabled,
            context_source = excluded.context_source,
            context_period = excluded.context_period,
            updated_at = CURRENT_TIMESTAMP
        """,
        (1 if new_enabled else 0, new_source, new_period),
    )
    return get_fatigue_context_settings(db=db)


# =============================================================================
# Advisory block builder
# =============================================================================
def _humanize_muscle(bucket: Optional[str]) -> str:
    if not bucket:
        return "this muscle"
    return bucket.replace("-", " ")


def _side_payload(bar: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Project a fatigue page bar dict into the advisory sub-shape, or None."""
    if bar is None:
        return None
    return {
        "band": bar.get("band"),
        "percent_of_mrv": bar.get("percent_of_mrv"),
        "has_landmarks": bool(bar.get("has_landmarks")),
    }


def build_fatigue_context(
    exercise_name: str,
    *,
    db: DatabaseHandler,
) -> Optional[dict[str, Any]]:
    """Build the additive advisory block for one exercise, or None.

    Returns ``None`` (so the caller omits the key entirely) when the layer is
    disabled or the exercise is unknown. When enabled and the exercise exists,
    always returns a block — falling back to neutral advisory copy for
    unranked / unknown / ``Unassigned`` muscles (never blocks, never invents a
    high/low classification without landmarks).
    """
    settings = get_fatigue_context_settings(db=db)
    if not settings["enabled"]:
        return None

    if not exercise_name or not exercise_name.strip():
        return None
    row = db.fetch_one(
        """
        SELECT primary_muscle_group
        FROM exercises
        WHERE exercise_name = ? COLLATE NOCASE
        """,
        (exercise_name.strip(),),
    )
    if not row:
        return None

    source = settings["context_source"]
    period = settings["context_period"]
    bucket = canonicalize_muscle_for_fatigue(row.get("primary_muscle_group"))
    muscle_label = _humanize_muscle(bucket)
    has_landmarks = bool(bucket and bucket in MUSCLE_VOLUME_LANDMARKS)

    # Unknown / NULL primary muscle can never resolve to a fatigue bar, so the
    # result is always the neutral advisory fallback — skip the page build.
    if bucket is None:
        return {
            "enabled": True,
            "muscle": None,
            "muscle_label": muscle_label,
            "has_landmarks": False,
            "source": source,
            "period": period,
            "period_label": PERIOD_LABELS[period],
            "planned": None,
            "logged": None,
            "disagree": False,
            "is_advisory_fallback": True,
            "headline": f"Fatigue context isn't ranked for {muscle_label} yet.",
            "advisory": FATIGUE_CONTEXT_ADVISORY,
        }

    # Phase 2D-A intentionally reuses the shipped Fatigue Meter page builder
    # rather than introducing a single-muscle query — it guarantees identical
    # bands/percentages and zero new fatigue math. It does run the full
    # planned + logged scan per estimate; if that ever shows on the hot path,
    # a thin single-muscle read helper is the documented follow-up (see
    # docs/user_profile/LEARNED_CALIBRATION_PLAN.md §"Phase 2D-A").
    page = build_fatigue_page_context(period)
    planned_by = {b["muscle"]: b for b in page.get("muscles_planned", [])}
    logged_by = {b["muscle"]: b for b in page.get("muscles_logged", [])}
    planned_bar = planned_by.get(bucket) if bucket else None
    logged_bar = logged_by.get(bucket) if bucket else None

    show_planned = source in ("planned", "both")
    show_logged = source in ("logged", "both")
    planned_payload = _side_payload(planned_bar) if show_planned else None
    logged_payload = _side_payload(logged_bar) if show_logged else None

    planned_band = planned_payload.get("band") if planned_payload else None
    logged_band = logged_payload.get("band") if logged_payload else None
    disagree = bool(
        source == "both"
        and planned_band
        and logged_band
        and planned_band != logged_band
    )

    # Advisory fallback whenever there is no ranked band to show — unranked /
    # unknown / Unassigned muscles, or a ranked muscle with no tracked volume.
    has_band = bool(planned_band or logged_band)
    is_advisory_fallback = (not has_landmarks) or (not has_band)

    if is_advisory_fallback:
        if not has_landmarks:
            headline = f"Fatigue context isn't ranked for {muscle_label} yet."
        else:
            headline = f"No fatigue tracked for {muscle_label} yet."
    else:
        if source == "both" and planned_band and logged_band:
            if disagree:
                headline = (
                    f"{muscle_label} fatigue: {_BAND_LABELS.get(planned_band, planned_band)}"
                    f" (planned) · {_BAND_LABELS.get(logged_band, logged_band)} (logged)."
                )
            else:
                headline = (
                    f"{muscle_label} fatigue: "
                    f"{_BAND_LABELS.get(planned_band, planned_band)}."
                )
        else:
            band = planned_band or logged_band
            headline = f"{muscle_label} fatigue: {_BAND_LABELS.get(band, band)}."

    return {
        "enabled": True,
        "muscle": bucket,
        "muscle_label": muscle_label,
        "has_landmarks": has_landmarks,
        "source": source,
        "period": period,
        "period_label": PERIOD_LABELS[period],
        "planned": planned_payload,
        "logged": logged_payload,
        "disagree": disagree,
        "is_advisory_fallback": is_advisory_fallback,
        "headline": headline,
        "advisory": FATIGUE_CONTEXT_ADVISORY,
    }


def attach_fatigue_context(
    estimate: dict[str, Any],
    exercise_name: str,
    *,
    db: DatabaseHandler,
) -> dict[str, Any]:
    """Attach the advisory block to an existing estimate dict (in place).

    Pure decoration: it adds at most the additive ``fatigue_context`` key and
    never alters the estimate's number / source / reason / trace. Any failure
    is swallowed so the advisory layer can never break the estimate response.
    """
    try:
        block = build_fatigue_context(exercise_name, db=db)
    except Exception:
        logger.exception(
            "Failed to build fatigue context for %s", exercise_name
        )
        block = None
    if block is not None and isinstance(estimate, dict):
        estimate["fatigue_context"] = block
    return estimate
