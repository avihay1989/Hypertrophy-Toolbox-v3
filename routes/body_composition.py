"""Body Composition blueprint (Issue #21).

Hosts the standalone `/body_composition` page plus JSON endpoints for
creating, listing, and deleting tape-measurement snapshots. Reads
gender / age / height / bodyweight from the existing `user_profile`
row (no re-entry). All formula math lives in `utils.body_fat` — this
module only does HTTP plumbing, validation, and DB I/O.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request

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
from utils.errors import error_response, success_response
from utils.logger import get_logger

body_composition_bp = Blueprint("body_composition", __name__)
logger = get_logger()

VALID_GENDERS = {"M", "F"}


def _get_json_payload() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON data")
    return data


def _nullable_text(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    normalized = str(value).strip()
    return normalized or None


def _required_float(value: Any, field: str, lo: float, hi: float) -> float:
    if value in (None, ""):
        raise ValueError(f"{field} is required")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if parsed < lo or parsed > hi:
        raise ValueError(f"{field} must be between {lo:g} and {hi:g}")
    return parsed


def _nullable_float(value: Any, field: str, lo: float, hi: float) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if parsed < lo or parsed > hi:
        raise ValueError(f"{field} must be between {lo:g} and {hi:g}")
    return parsed


def _required_int(value: Any, field: str, lo: int, hi: int) -> int:
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


def _load_profile(db: DatabaseHandler) -> dict[str, Any]:
    row = db.fetch_one("SELECT * FROM user_profile WHERE id = 1")
    return dict(row) if row else {}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_captured_at(value: Any) -> Optional[str]:
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


def _row_to_snapshot(row: Any) -> dict[str, Any]:
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


def _profile_demographics(profile: dict[str, Any]) -> tuple[str, int, float, float]:
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

    gender = _nullable_text(profile.get("gender"))
    if gender not in VALID_GENDERS:
        raise ValueError("gender must be 'M' or 'F'")
    age_years = _required_int(profile.get("age"), "age_years", 10, 100)
    height_cm = _required_float(
        profile.get("height_cm"), "height_cm", HEIGHT_MIN_CM, HEIGHT_MAX_CM
    )
    bodyweight_kg = _required_float(
        profile.get("weight_kg"),
        "bodyweight_kg",
        BODYWEIGHT_MIN_KG,
        BODYWEIGHT_MAX_KG,
    )
    return gender, age_years, height_cm, bodyweight_kg


@body_composition_bp.route("/body_composition")
def body_composition():
    try:
        with DatabaseHandler() as db:
            profile = _load_profile(db)
            snapshot_rows = db.fetch_all(
                """
                SELECT id, captured_at, bodyweight_kg, height_cm,
                       neck_cm, waist_cm, hip_cm, age_years, gender,
                       bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg, notes
                FROM body_composition_snapshots
                ORDER BY captured_at DESC, id DESC
                """
            )
        snapshots = [_row_to_snapshot(row) for row in snapshot_rows]
        latest = snapshots[0] if snapshots else None
        return render_template(
            "body_composition.html",
            profile=profile,
            snapshots=snapshots,
            latest_snapshot=latest,
        )
    except Exception:
        logger.exception("Error rendering body composition page")
        return render_template(
            "error.html",
            error_title="Server Error",
            error_code=500,
            error_message="Unable to load Body Composition.",
        ), 500


@body_composition_bp.route("/api/body_composition/snapshot", methods=["POST"])
def create_snapshot():
    data: dict[str, Any] = {}
    try:
        data = _get_json_payload()

        with DatabaseHandler() as db:
            profile = _load_profile(db)
        gender, age_years, height_cm, bodyweight_kg = _profile_demographics(profile)

        neck_cm = _nullable_float(
            data.get("neck_cm"), "neck_cm", CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM
        )
        waist_cm = _nullable_float(
            data.get("waist_cm"), "waist_cm", CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM
        )
        hip_cm = _nullable_float(
            data.get("hip_cm"), "hip_cm", CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM
        )
        notes = _nullable_text(data.get("notes"))

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

        captured_at = _parse_captured_at(data.get("captured_at")) or _utcnow_iso()

        with DatabaseHandler() as db:
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
                    captured_at,
                    bodyweight_kg,
                    height_cm,
                    neck_cm,
                    waist_cm,
                    hip_cm,
                    age_years,
                    gender,
                    bfp_navy,
                    bfp_bmi,
                    fat_mass_kg,
                    lean_mass_kg,
                    notes,
                ),
            )
            row = db.fetch_one(
                """
                SELECT id, captured_at, bodyweight_kg, height_cm,
                       neck_cm, waist_cm, hip_cm, age_years, gender,
                       bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg, notes
                FROM body_composition_snapshots
                WHERE id = last_insert_rowid()
                """
            )

        snapshot = _row_to_snapshot(row) if row else None
        return jsonify(success_response(data=snapshot, message="Snapshot saved"))
    except ValueError as exc:
        logger.warning("Validation error saving body composition snapshot", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to save body composition snapshot", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to save snapshot", 500)


@body_composition_bp.route("/api/body_composition/snapshots", methods=["GET"])
def list_snapshots():
    try:
        with DatabaseHandler() as db:
            rows = db.fetch_all(
                """
                SELECT id, captured_at, bodyweight_kg, height_cm,
                       neck_cm, waist_cm, hip_cm, age_years, gender,
                       bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg, notes
                FROM body_composition_snapshots
                ORDER BY captured_at DESC, id DESC
                """
            )
        snapshots = [_row_to_snapshot(row) for row in rows]
        return jsonify(success_response(data=snapshots))
    except Exception:
        logger.exception("Failed to list body composition snapshots")
        return error_response("INTERNAL_ERROR", "Failed to list snapshots", 500)


@body_composition_bp.route("/api/body_composition/snapshots/<int:snapshot_id>", methods=["DELETE"])
def delete_snapshot(snapshot_id: int):
    try:
        with DatabaseHandler() as db:
            existing = db.fetch_one(
                "SELECT id FROM body_composition_snapshots WHERE id = ?",
                (snapshot_id,),
            )
            if existing is None:
                return error_response(
                    "NOT_FOUND", f"Snapshot {snapshot_id} not found", 404
                )
            db.execute_query(
                "DELETE FROM body_composition_snapshots WHERE id = ?",
                (snapshot_id,),
            )
        return jsonify(success_response(data={"id": snapshot_id}, message="Snapshot deleted"))
    except Exception:
        logger.exception("Failed to delete body composition snapshot", extra={"id": snapshot_id})
        return error_response("INTERNAL_ERROR", "Failed to delete snapshot", 500)
