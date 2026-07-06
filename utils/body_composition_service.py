"""Body-composition snapshot service (WP1.6).

Owns the CRUD/query logic and validation/computation for tape-measurement
snapshots that previously lived inline in ``routes/body_composition.py``.
The body-fat *formulas* stay in ``utils.body_fat`` — this module only parses
and validates input, orchestrates those formulas, maps rows, and runs the
snapshot SQL.

Query/persistence helpers take an open :class:`DatabaseHandler` so the route
owns the transaction boundary; pure helpers (parsing, computation, row
mapping) take plain values.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from utils.body_fat import (
    BODYWEIGHT_MAX_KG,
    BODYWEIGHT_MIN_KG,
    CIRCUMFERENCE_MAX_CM,
    CIRCUMFERENCE_MIN_CM,
    HEIGHT_MAX_CM,
    HEIGHT_MIN_CM,
    compute_bmi,
    compute_navy,
)
from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()

VALID_GENDERS = {"M", "F"}

_SNAPSHOT_COLUMNS = """
    id, captured_at, bodyweight_kg, height_cm,
    neck_cm, waist_cm, hip_cm, age_years, gender,
    bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg, notes
"""


# -- parsing / validation helpers -------------------------------------------

def nullable_text(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    normalized = str(value).strip()
    return normalized or None


def required_float(value: Any, field: str, lo: float, hi: float) -> float:
    if value in (None, ""):
        raise ValueError(f"{field} is required")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if parsed < lo or parsed > hi:
        raise ValueError(f"{field} must be between {lo:g} and {hi:g}")
    return parsed


def nullable_float(value: Any, field: str, lo: float, hi: float) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if parsed < lo or parsed > hi:
        raise ValueError(f"{field} must be between {lo:g} and {hi:g}")
    return parsed


def required_int(value: Any, field: str, lo: int, hi: int) -> int:
    if value in (None, ""):
        raise ValueError(f"{field} is required")
    try:
        parsed_float = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if not parsed_float.is_integer():
        raise ValueError(f"{field} must be an integer")
    parsed = int(parsed_float)
    if parsed < lo or parsed > hi:
        raise ValueError(f"{field} must be between {lo} and {hi}")
    return parsed


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_captured_at(value: Any) -> Optional[str]:
    """Parse a client-supplied ISO 8601 timestamp; return None if blank.

    Accepts trailing `Z` as UTC. Echoes the caller's string back unchanged
    when parseable so the saved row preserves the original offset / precision
    the client sent.
    """
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("captured_at must be an ISO 8601 timestamp string")
    normalized = value.strip()
    if not normalized:
        return None
    parse_input = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    try:
        datetime.fromisoformat(parse_input)
    except ValueError as exc:
        raise ValueError("captured_at must be an ISO 8601 timestamp") from exc
    return normalized


def row_to_snapshot(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "captured_at": row["captured_at"],
        "bodyweight_kg": row["bodyweight_kg"],
        "height_cm": row["height_cm"],
        "neck_cm": row["neck_cm"],
        "waist_cm": row["waist_cm"],
        "hip_cm": row["hip_cm"],
        "age_years": row["age_years"],
        "gender": row["gender"],
        "bfp_navy": row["bfp_navy"],
        "bfp_bmi": row["bfp_bmi"],
        "fat_mass_kg": row["fat_mass_kg"],
        "lean_mass_kg": row["lean_mass_kg"],
        "notes": row["notes"],
    }


def profile_demographics(profile: dict[str, Any]) -> tuple[str, int, float, float]:
    """Return validated demographics from user_profile for snapshot creation."""
    if not profile:
        raise ValueError(
            "Complete your User Profile demographics before saving a snapshot"
        )

    required = ("gender", "age", "height_cm", "weight_kg")
    if any(profile.get(field) in (None, "") for field in required):
        raise ValueError(
            "Complete your User Profile demographics before saving a snapshot"
        )

    gender = nullable_text(profile.get("gender"))
    if gender not in VALID_GENDERS:
        raise ValueError("gender must be 'M' or 'F'")
    age_years = required_int(profile.get("age"), "age_years", 10, 100)
    height_cm = required_float(
        profile.get("height_cm"), "height_cm", HEIGHT_MIN_CM, HEIGHT_MAX_CM
    )
    bodyweight_kg = required_float(
        profile.get("weight_kg"),
        "bodyweight_kg",
        BODYWEIGHT_MIN_KG,
        BODYWEIGHT_MAX_KG,
    )
    return gender, age_years, height_cm, bodyweight_kg


def compute_snapshot_fields(
    profile: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Validate input and compute all snapshot column values.

    Pure (no DB): given the saved user_profile row and the request payload,
    return the full set of values to persist. Raises ``ValueError`` on any
    validation or log-domain failure. Body-fat math is delegated verbatim to
    ``utils.body_fat``.
    """
    gender, age_years, height_cm, bodyweight_kg = profile_demographics(profile)

    neck_cm = nullable_float(
        data.get("neck_cm"), "neck_cm", CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM
    )
    waist_cm = nullable_float(
        data.get("waist_cm"), "waist_cm", CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM
    )
    hip_cm = nullable_float(
        data.get("hip_cm"), "hip_cm", CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM
    )
    notes = nullable_text(data.get("notes"))

    if gender == "M" and hip_cm is not None:
        raise ValueError("hip_cm must not be provided when gender is 'M'")

    any_tape = any(v is not None for v in (neck_cm, waist_cm, hip_cm))
    required_tape = (neck_cm, waist_cm) if gender == "M" else (neck_cm, waist_cm, hip_cm)
    all_required_tape = all(v is not None for v in required_tape)
    if any_tape and not all_required_tape:
        missing = "neck_cm, waist_cm" if gender == "M" else "neck_cm, waist_cm, hip_cm"
        raise ValueError(f"Tape measurements are incomplete — all of {missing} are required for the Navy method")

    bmi_result = compute_bmi(
        gender=gender,
        age_years=age_years,
        height_cm=height_cm,
        bodyweight_kg=bodyweight_kg,
    )
    bfp_bmi = bmi_result["bfp"]

    bfp_navy: Optional[float] = None
    if all_required_tape:
        bfp_navy = compute_navy(
            gender=gender,
            height_cm=height_cm,
            neck_cm=neck_cm,
            waist_cm=waist_cm,
            hip_cm=hip_cm if gender == "F" else None,
        )

    effective_bfp = bfp_navy if bfp_navy is not None else bfp_bmi
    fat_mass_kg = (effective_bfp / 100.0) * bodyweight_kg
    lean_mass_kg = bodyweight_kg - fat_mass_kg

    captured_at = parse_captured_at(data.get("captured_at")) or utcnow_iso()

    return {
        "captured_at": captured_at,
        "bodyweight_kg": bodyweight_kg,
        "height_cm": height_cm,
        "neck_cm": neck_cm,
        "waist_cm": waist_cm,
        "hip_cm": hip_cm,
        "age_years": age_years,
        "gender": gender,
        "bfp_navy": bfp_navy,
        "bfp_bmi": bfp_bmi,
        "fat_mass_kg": fat_mass_kg,
        "lean_mass_kg": lean_mass_kg,
        "notes": notes,
    }


# -- query / persistence helpers (caller owns the transaction) --------------

def load_profile(db: DatabaseHandler) -> dict[str, Any]:
    row = db.fetch_one("SELECT * FROM user_profile WHERE id = 1")
    return dict(row) if row else {}


def fetch_snapshot_rows(db: DatabaseHandler) -> list[Any]:
    return db.fetch_all(
        f"""
        SELECT {_SNAPSHOT_COLUMNS}
        FROM body_composition_snapshots
        ORDER BY captured_at DESC, id DESC
        """
    )


def list_snapshots(db: DatabaseHandler) -> list[dict[str, Any]]:
    return [row_to_snapshot(row) for row in fetch_snapshot_rows(db)]


def insert_snapshot(db: DatabaseHandler, fields: dict[str, Any]) -> Optional[dict[str, Any]]:
    db.execute_query(
        """
        INSERT INTO body_composition_snapshots (
            captured_at, bodyweight_kg, height_cm,
            neck_cm, waist_cm, hip_cm, age_years, gender,
            bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fields["captured_at"],
            fields["bodyweight_kg"],
            fields["height_cm"],
            fields["neck_cm"],
            fields["waist_cm"],
            fields["hip_cm"],
            fields["age_years"],
            fields["gender"],
            fields["bfp_navy"],
            fields["bfp_bmi"],
            fields["fat_mass_kg"],
            fields["lean_mass_kg"],
            fields["notes"],
        ),
    )
    row = db.fetch_one(
        f"""
        SELECT {_SNAPSHOT_COLUMNS}
        FROM body_composition_snapshots
        WHERE id = last_insert_rowid()
        """
    )
    return row_to_snapshot(row) if row else None


def delete_snapshot(db: DatabaseHandler, snapshot_id: int) -> bool:
    """Delete a snapshot; return ``True`` if it existed, ``False`` otherwise."""
    existing = db.fetch_one(
        "SELECT id FROM body_composition_snapshots WHERE id = ?",
        (snapshot_id,),
    )
    if existing is None:
        return False
    db.execute_query(
        "DELETE FROM body_composition_snapshots WHERE id = ?",
        (snapshot_id,),
    )
    return True
