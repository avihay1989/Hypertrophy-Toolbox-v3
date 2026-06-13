from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.media_path import VENDOR_BASE_REL, is_valid_media_path_shape, media_path_resolves

logger = get_logger()

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING_CSV = REPO_ROOT / "data" / "free_exercise_db_mapping.csv"
DEFAULT_VENDOR_BASE = REPO_ROOT / VENDOR_BASE_REL

FALLBACK_STATUSES = frozenset({"confirmed", "manual", "auto"})

# Small hand-curated layer for common Plan rows whose CSV match is blank or
# intentionally rejected because the automated suggestion was wrong.
MANUAL_EXERCISE_MEDIA_OVERRIDES: dict[str, str] = {
    "barbell decline bench press": "Decline_Barbell_Bench_Press/0.jpg",
    "barbell front rack step up - quadriceps focused": "Barbell_Step_Ups/0.jpg",
    "dumbbell suitcase crunch": "Dumbbell_Side_Bend/0.jpg",
    "lever narrow grip seated row": "Leverage_Iso_Row/0.jpg",
    "machine assisted neutral chin up": "Chin-Up/0.jpg",
    "machine plate loaded leg extension": "Leg_Extensions/0.jpg",
}


def _normalize_exercise_name(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


@lru_cache(maxsize=1)
def _load_fallback_media_map() -> dict[str, str]:
    media_by_name: dict[str, str] = {}

    for exercise_name, media_path in MANUAL_EXERCISE_MEDIA_OVERRIDES.items():
        if media_path_resolves(media_path, DEFAULT_VENDOR_BASE):
            media_by_name[_normalize_exercise_name(exercise_name)] = media_path
        else:
            logger.warning(
                "Exercise media override does not resolve",
                extra={"exercise": exercise_name, "media_path": media_path},
            )

    if not DEFAULT_MAPPING_CSV.exists():
        logger.warning("Exercise media mapping CSV not found", extra={"path": str(DEFAULT_MAPPING_CSV)})
        return media_by_name

    with DEFAULT_MAPPING_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            status = (row.get("review_status") or "").strip().casefold()
            media_path = (row.get("suggested_image_path") or "").strip()
            exercise_name = _normalize_exercise_name(row.get("exercise_name"))
            if (
                not exercise_name
                or not media_path
                or status not in FALLBACK_STATUSES
                or exercise_name in media_by_name
            ):
                continue
            if media_path_resolves(media_path, DEFAULT_VENDOR_BASE):
                media_by_name[exercise_name] = media_path

    return media_by_name


def resolve_exercise_media_path(
    exercise_name: object,
    media_path: object = None,
) -> Optional[str]:
    """Return a safe free-exercise-db media path for an exercise.

    Existing database media_path values win. When a live DB has not had the
    reviewed mapping applied yet, fall back to the bundled mapping CSV so Plan
    rows can still render exercise thumbnails.
    """
    if isinstance(media_path, str) and is_valid_media_path_shape(media_path):
        return media_path
    return _load_fallback_media_map().get(_normalize_exercise_name(exercise_name))
