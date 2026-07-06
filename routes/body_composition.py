"""Body Composition blueprint (Issue #21).

Hosts the standalone `/body_composition` page plus JSON endpoints for
creating, listing, and deleting tape-measurement snapshots. Reads
gender / age / height / bodyweight from the existing `user_profile`
row (no re-entry). Formula math lives in `utils.body_fat`; snapshot
CRUD/query and validation live in `utils.body_composition_service`
(WP1.6). This module only does HTTP plumbing: parse, delegate, and
shape the response envelope.
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, render_template, request

from utils import body_composition_service as service
from utils.database import DatabaseHandler
from utils.errors import error_response, success_response
from utils.logger import get_logger

body_composition_bp = Blueprint("body_composition", __name__)
logger = get_logger()


def _get_json_payload() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON data")
    return data


@body_composition_bp.route("/body_composition")
def body_composition():
    try:
        with DatabaseHandler() as db:
            profile = service.load_profile(db)
            snapshots = service.list_snapshots(db)
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
            profile = service.load_profile(db)
        fields = service.compute_snapshot_fields(profile, data)

        with DatabaseHandler() as db:
            snapshot = service.insert_snapshot(db, fields)

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
            snapshots = service.list_snapshots(db)
        return jsonify(success_response(data=snapshots))
    except Exception:
        logger.exception("Failed to list body composition snapshots")
        return error_response("INTERNAL_ERROR", "Failed to list snapshots", 500)


@body_composition_bp.route("/api/body_composition/snapshots/<int:snapshot_id>", methods=["DELETE"])
def delete_snapshot(snapshot_id: int):
    try:
        with DatabaseHandler() as db:
            deleted = service.delete_snapshot(db, snapshot_id)
        if not deleted:
            return error_response(
                "NOT_FOUND", f"Snapshot {snapshot_id} not found", 404
            )
        return jsonify(success_response(data={"id": snapshot_id}, message="Snapshot deleted"))
    except Exception:
        logger.exception("Failed to delete body composition snapshot", extra={"id": snapshot_id})
        return error_response("INTERNAL_ERROR", "Failed to delete snapshot", 500)
