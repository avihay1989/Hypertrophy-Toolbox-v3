from __future__ import annotations

import csv
import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.media_path import VENDOR_BASE_REL, is_valid_media_path_shape, media_path_resolves

logger = get_logger()

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING_CSV = REPO_ROOT / "data" / "free_exercise_db_mapping.csv"
DEFAULT_VENDOR_BASE = REPO_ROOT / VENDOR_BASE_REL
DEFAULT_CATALOG_JSON = REPO_ROOT / "static" / "vendor" / "free-exercise-db" / "exercises.json"

FALLBACK_STATUSES = frozenset({"confirmed", "manual", "auto"})
MIN_FUZZY_SCORE = 0.72

# Small hand-curated layer for common Plan rows whose CSV match is blank or
# intentionally rejected because the automated suggestion was wrong.
MANUAL_EXERCISE_MEDIA_OVERRIDES: dict[str, str] = {
    "barbell decline bench press": "Decline_Barbell_Bench_Press/0.jpg",
    "barbell 45 degrees hyperextension": "Hyperextensions_Back_Extensions/0.jpg",
    "barbell front rack step up - quadriceps focused": "Barbell_Step_Ups/0.jpg",
    "cable belt calf raise": "Standing_Calf_Raises/0.jpg",
    "cable seated leg extension": "Leg_Extensions/0.jpg",
    "cable straight back seated row": "Seated_Cable_Rows/0.jpg",
    "dumbbell decline skullcrusher": "EZ-Bar_Skullcrusher/0.jpg",
    "dumbbell heels elevated hip thrust": "Barbell_Hip_Thrust/0.jpg",
    "dumbbell neutral overhead press": "Dumbbell_Shoulder_Press/0.jpg",
    "dumbbell suitcase crunch": "Dumbbell_Side_Bend/0.jpg",
    "dumbbell upright shoulder external rotation with support": "External_Rotation/0.jpg",
    "dumbbell weighted dip - chest focused.": "Dips_-_Chest_Version/0.jpg",
    "lever narrow grip seated row": "Leverage_Iso_Row/0.jpg",
    "machine assisted chin up": "Chin-Up/0.jpg",
    "machine assisted neutral chin up": "Chin-Up/0.jpg",
    "machine plate loaded leg extension": "Leg_Extensions/0.jpg",
}

PHRASE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("skullcrusher", "skull crusher"),
    ("pull-ups", "pull ups"),
    ("pullups", "pull ups"),
    ("chin-ups", "chin ups"),
)

DROP_TOKENS = frozenset(
    {
        "focused",
        "focus",
        "supported",
        "support",
        "degrees",
        "degree",
        "version",
        "variation",
        "with",
    }
)

SINGULAR_TOKENS = {
    "rows": "row",
    "dips": "dip",
    "raises": "raise",
    "extensions": "extension",
    "crunches": "crunch",
    "flyes": "fly",
    "curls": "curl",
    "chins": "chin",
}


def _normalize_exercise_name(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def _tokens_for_match(value: object) -> list[str]:
    text = _normalize_exercise_name(value)
    for old, new in PHRASE_REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens: list[str] = []
    for raw_token in text.split():
        if raw_token in DROP_TOKENS or raw_token.isdigit():
            continue
        tokens.append(SINGULAR_TOKENS.get(raw_token, raw_token))
    return tokens


def _match_key(value: object) -> str:
    return " ".join(_tokens_for_match(value))


@lru_cache(maxsize=1)
def _load_catalog_media_entries() -> tuple[tuple[str, str, str], ...]:
    if not DEFAULT_CATALOG_JSON.exists():
        logger.warning("Exercise media catalog JSON not found", extra={"path": str(DEFAULT_CATALOG_JSON)})
        return ()

    with DEFAULT_CATALOG_JSON.open("r", encoding="utf-8") as f:
        catalog = json.load(f)

    entries: list[tuple[str, str, str]] = []
    for exercise in catalog:
        name = exercise.get("name")
        exercise_id = exercise.get("id")
        images = exercise.get("images") or []
        media_path = images[0] if images else f"{exercise_id}/0.jpg"
        if not name or not media_path_resolves(media_path, DEFAULT_VENDOR_BASE):
            continue
        for candidate_name in (name, exercise_id):
            key = _match_key(candidate_name)
            if key:
                entries.append((str(candidate_name), key, media_path))
    return tuple(entries)


@lru_cache(maxsize=1)
def _load_fallback_media_map() -> dict[str, str]:
    media_by_name: dict[str, str] = {}

    for exercise_name, media_path in MANUAL_EXERCISE_MEDIA_OVERRIDES.items():
        if media_path_resolves(media_path, DEFAULT_VENDOR_BASE):
            media_by_name[_match_key(exercise_name)] = media_path
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
            exercise_name = _match_key(row.get("exercise_name"))
            if (
                not exercise_name
                or not media_path
                or status not in FALLBACK_STATUSES
                or exercise_name in media_by_name
            ):
                continue
            if media_path_resolves(media_path, DEFAULT_VENDOR_BASE):
                media_by_name[exercise_name] = media_path

    for _, exercise_name, media_path in _load_catalog_media_entries():
        media_by_name.setdefault(exercise_name, media_path)

    return media_by_name


def _score_candidate(query_tokens: list[str], candidate_key: str) -> float:
    candidate_tokens = candidate_key.split()
    if not query_tokens or not candidate_tokens:
        return 0.0

    query_set = set(query_tokens)
    candidate_set = set(candidate_tokens)
    common = query_set & candidate_set
    if len(common) < 2:
        return 0.0

    coverage = len(common) / min(len(query_set), len(candidate_set))
    jaccard = len(common) / len(query_set | candidate_set)
    sequence = SequenceMatcher(None, " ".join(query_tokens), candidate_key).ratio()
    return (coverage * 0.55) + (jaccard * 0.25) + (sequence * 0.20)


@lru_cache(maxsize=2048)
def _resolve_fuzzy_media_path(exercise_name: str) -> Optional[str]:
    query_tokens = _tokens_for_match(exercise_name)
    best_score = 0.0
    best_path: Optional[str] = None

    for _, candidate_key, media_path in _load_catalog_media_entries():
        score = _score_candidate(query_tokens, candidate_key)
        if score > best_score:
            best_score = score
            best_path = media_path

    if best_score >= MIN_FUZZY_SCORE:
        return best_path
    return None


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
    name_key = _match_key(exercise_name)
    return _load_fallback_media_map().get(name_key) or _resolve_fuzzy_media_path(
        _normalize_exercise_name(exercise_name)
    )
