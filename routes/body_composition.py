"""Body Composition routes (Issue #21).

Standalone /body_composition tab that accepts tape measurements,
computes BFP via the Navy + BMI methods (logic in
``utils.body_fat``), and persists snapshots to
``body_composition_snapshots``.

Server is the source of truth for demographics: ``gender``, ``age``,
``height_cm``, and ``weight_kg`` are read from ``user_profile`` at
save time. Client-supplied demographic fields in the POST body are
ignored — snapshots are an audit trail of body composition over time
and we never want a stale or hand-edited client value to corrupt
that record.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request

from utils.body_fat import (
    BodyFatValidationError,
    compute_bmi,
    compute_navy,
)
from utils.database import DatabaseHandler
from utils.errors import error_response, success_response
from utils.logger import get_logger

body_composition_bp = Blueprint("body_composition", __name__)
logger = get_logger()

VALID_GENDERS = {"M", "F"}
DEMOGRAPHIC_FIELDS = ("gender", "age", "height_cm", "weight_kg")
SNAPSHOTS_LIMIT_CAP = 1000


def _load_demographics(db: DatabaseHandler) -> tuple[Optional[dict], list[str]]:
    """Return (row_or_None, missing_fields).

    Treats both a missing row and any NULL demographic field as
    "missing" — both block snapshot capture and gate the calculator
    card on the page.
    """
    row = db.fetch_one("SELECT * FROM user_profile WHERE id = 1")
    if not row:
        return None, list(DEMOGRAPHIC_FIELDS)
    missing = [field for field in DEMOGRAPHIC_FIELDS if row.get(field) in (None, "")]
    return row, missing


def _load_snapshots(
    db: DatabaseHandler, *, limit: Optional[int] = None
) -> list[dict]:
    """Return snapshots sorted newest-first.

    The ``id DESC`` tiebreak matters when two snapshots share a
    ``captured_at`` second (rapid double-tap on Save) — without it
    the "latest" can flip between page loads and produce flaky tests.
    """
    sql = (
        "SELECT * FROM body_composition_snapshots "
        "ORDER BY captured_at DESC, id DESC"
    )
    if limit is not None:
        sql += " LIMIT ?"
        return db.fetch_all(sql, (limit,))
    return db.fetch_all(sql)


def _coerce_optional_float(value: Any, field: str) -> Optional[float]:
    """Permit ``None`` / empty string to mean *not provided*; otherwise
    coerce to float and let body_fat range-check on use."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")


@body_composition_bp.route("/body_composition")
def body_composition_page():
    try:
        with DatabaseHandler() as db:
            demographics, missing = _load_demographics(db)
            snapshots = _load_snapshots(db)
        return render_template(
            "body_composition.html",
            demographics=demographics,
            missing_demographics=missing,
            demographics_complete=(not missing),
            snapshots=snapshots,
        )
    except Exception:
        logger.exception("Error rendering body composition page")
        return (
            render_template("error.html", message="Unable to load body composition."),
            500,
        )


@body_composition_bp.route("/api/body_composition/snapshot", methods=["POST"])
def save_body_composition_snapshot():
    payload = None
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return error_response("VALIDATION_ERROR", "Invalid JSON body", 400)

        try:
            neck_cm = _coerce_optional_float(payload.get("neck_cm"), "neck_cm")
            waist_cm = _coerce_optional_float(payload.get("waist_cm"), "waist_cm")
            hip_cm = _coerce_optional_float(payload.get("hip_cm"), "hip_cm")
        except ValueError as exc:
            return error_response("VALIDATION_ERROR", str(exc), 400)

        notes = payload.get("notes")
        if notes is not None and not isinstance(notes, str):
            return error_response("VALIDATION_ERROR", "notes must be a string", 400)

        with DatabaseHandler() as db:
            demographics, missing = _load_demographics(db)
            if missing:
                return error_response(
                    "PREREQUISITE_MISSING",
                    "Profile demographics are required before saving a snapshot.",
                    400,
                    missing_fields=missing,
                )

            gender = demographics["gender"]
            if gender not in VALID_GENDERS:
                return error_response(
                    "UNSUPPORTED_GENDER",
                    f"Gender '{gender}' is not supported. "
                    f"Update demographics on /user_profile.",
                    400,
                )

            age = int(demographics["age"])
            height_cm = float(demographics["height_cm"])
            weight_kg = float(demographics["weight_kg"])

            # Hip is female-only — reject explicitly for males to keep
            # the contract clean rather than silently dropping it.
            if gender == "M" and hip_cm is not None:
                return error_response(
                    "VALIDATION_ERROR",
                    "hip_cm is only used for the female Navy formula.",
                    400,
                    field="hip_cm",
                )

            # All-or-nothing tape contract: either every gender-specific
            # tape field is filled (Navy + BMI) or all are blank (BMI
            # fallback). Partial fills must surface as a validation error
            # so they don't silently degrade to BMI and mask user input.
            if gender == "M":
                tape_fields = {"neck_cm": neck_cm, "waist_cm": waist_cm}
            else:
                tape_fields = {
                    "neck_cm": neck_cm,
                    "waist_cm": waist_cm,
                    "hip_cm": hip_cm,
                }
            non_null = {k: v for k, v in tape_fields.items() if v is not None}
            tape_complete = len(non_null) == len(tape_fields)
            tape_blank = len(non_null) == 0
            if not (tape_complete or tape_blank):
                missing_tape = [k for k, v in tape_fields.items() if v is None]
                return error_response(
                    "VALIDATION_ERROR",
                    "Provide all tape measurements or none — partial tape "
                    "input is not supported.",
                    400,
                    missing_fields=missing_tape,
                )

            # Always compute BMI — it's the universal fallback.
            try:
                bfp_bmi = compute_bmi(
                    gender=gender,
                    age=age,
                    height_cm=height_cm,
                    weight_kg=weight_kg,
                )
            except BodyFatValidationError as exc:
                return error_response(
                    "VALIDATION_ERROR", exc.message, 400, field=exc.field
                )

            bfp_navy: Optional[float] = None
            if tape_complete:
                try:
                    if gender == "M":
                        bfp_navy = compute_navy(
                            gender="M",
                            height_cm=height_cm,
                            neck_cm=neck_cm,
                            waist_cm=waist_cm,
                        )
                    else:
                        bfp_navy = compute_navy(
                            gender="F",
                            height_cm=height_cm,
                            neck_cm=neck_cm,
                            waist_cm=waist_cm,
                            hip_cm=hip_cm,
                        )
                except BodyFatValidationError as exc:
                    return error_response(
                        "VALIDATION_ERROR", exc.message, 400, field=exc.field
                    )

            # Derived masses prefer the Navy estimate when present.
            primary_bfp = bfp_navy if bfp_navy is not None else bfp_bmi
            fat_mass_kg = (primary_bfp / 100.0) * weight_kg
            lean_mass_kg = weight_kg - fat_mass_kg

            captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

            db.execute_query(
                """
                INSERT INTO body_composition_snapshots (
                    captured_at, weight_kg, height_cm,
                    neck_cm, waist_cm, hip_cm,
                    age_years, gender,
                    bfp_navy, bfp_bmi,
                    fat_mass_kg, lean_mass_kg,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at,
                    weight_kg,
                    height_cm,
                    neck_cm,
                    waist_cm,
                    hip_cm,
                    age,
                    gender,
                    bfp_navy,
                    bfp_bmi,
                    fat_mass_kg,
                    lean_mass_kg,
                    notes,
                ),
            )
            saved = db.fetch_one(
                "SELECT * FROM body_composition_snapshots "
                "WHERE id = last_insert_rowid()"
            )

        return jsonify(success_response(data=saved, message="Snapshot saved"))
    except Exception:
        logger.exception(
            "Failed to save body composition snapshot",
            extra={"payload": payload},
        )
        return error_response("INTERNAL_ERROR", "Failed to save snapshot", 500)


@body_composition_bp.route("/api/body_composition/snapshots")
def list_body_composition_snapshots():
    raw = request.args.get("limit")
    limit: Optional[int] = None
    if raw is not None:
        try:
            limit = int(raw)
        except (TypeError, ValueError):
            return error_response("VALIDATION_ERROR", "limit must be an integer", 400)
        if limit < 1:
            return error_response("VALIDATION_ERROR", "limit must be ≥ 1", 400)
        limit = min(limit, SNAPSHOTS_LIMIT_CAP)
    try:
        with DatabaseHandler() as db:
            rows = _load_snapshots(db, limit=limit)
        return jsonify(success_response(data=rows))
    except Exception:
        logger.exception("Failed to list body composition snapshots")
        return error_response("INTERNAL_ERROR", "Failed to list snapshots", 500)


@body_composition_bp.route(
    "/api/body_composition/snapshots/<int:snapshot_id>",
    methods=["DELETE"],
)
def delete_body_composition_snapshot(snapshot_id: int):
    try:
        with DatabaseHandler() as db:
            existing = db.fetch_one(
                "SELECT id FROM body_composition_snapshots WHERE id = ?",
                (snapshot_id,),
            )
            if existing is None:
                return error_response("NOT_FOUND", "Snapshot not found", 404)
            db.execute_query(
                "DELETE FROM body_composition_snapshots WHERE id = ?",
                (snapshot_id,),
            )
        return jsonify(
            success_response(data={"id": snapshot_id}, message="Snapshot deleted")
        )
    except Exception:
        logger.exception(
            "Failed to delete body composition snapshot",
            extra={"snapshot_id": snapshot_id},
        )
        return error_response("INTERNAL_ERROR", "Failed to delete snapshot", 500)
