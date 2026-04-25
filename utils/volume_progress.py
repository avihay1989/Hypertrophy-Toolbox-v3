"""Planned-set volume aggregation for the Plan tab progress panel."""
from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from typing import Any

from utils.database import DatabaseHandler
from utils.logger import get_logger
import utils.volume_taxonomy as taxonomy

logger = get_logger()

ROLE_WEIGHTS = {
    "primary": 1.0,
    "secondary": 0.5,
    "tertiary": 0.25,
}

DEFAULT_RECOMMENDED_RANGES: dict[str, dict[str, float]] = {
    muscle: {"min": 12.0, "max": 20.0}
    for muscle in taxonomy.BASIC_MUSCLE_GROUPS + taxonomy.ADVANCED_MUSCLE_GROUPS
}

_BASIC_ONLY_TOKEN_TO_BASIC = {
    "splenius": "Neck",
    "sternocleidomastoid": "Neck",
}


def _new_diagnostics() -> dict[str, Any]:
    return {
        "unmapped_muscles": [],
        "ignored_tokens": [],
        "rejected_tokens": [],
        "blank_pst_rows": [],
        "csv_fallback_count": 0,
        "blank_pst_orphan": 0,
    }


def _split_isolated_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [token.strip() for token in re.split(r"[;,]", raw) if token.strip()]


def _split_mapping_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [token.strip() for token in raw.split("|") if token.strip()]


def _unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _mode_muscles(mode: str) -> list[str]:
    return (
        taxonomy.ADVANCED_MUSCLE_GROUPS
        if (mode or "").lower() == "advanced"
        else taxonomy.BASIC_MUSCLE_GROUPS
    )


def _advanced_targets_for_token(raw_token: str) -> tuple[str, ...] | None:
    normalized = taxonomy.normalize_isolated_token(raw_token)
    if not normalized:
        return ()
    expanded = taxonomy.expand_umbrella(normalized)
    if expanded:
        return expanded
    if normalized in taxonomy.IGNORED_TOKENS:
        return None
    if normalized in taxonomy.ADVANCED_MUSCLE_GROUPS:
        return (normalized,)
    if normalized in taxonomy.TOKEN_TO_ADVANCED:
        advanced = taxonomy.TOKEN_TO_ADVANCED[normalized]
        return (advanced,) if advanced else None
    return ()


def _token_is_umbrella(raw_token: str) -> bool:
    return taxonomy.expand_umbrella(taxonomy.normalize_isolated_token(raw_token)) is not None


def _coarse_basic(coarse: str | None) -> str | None:
    key = taxonomy.canonical_pst(coarse)
    if key is None:
        return None
    return taxonomy.COARSE_TO_BASIC.get(key)


def _coarse_representative_advanced(coarse: str | None) -> str | None:
    key = taxonomy.canonical_pst(coarse)
    if key is None:
        return None
    return taxonomy.COARSE_TO_REPRESENTATIVE_ADVANCED.get(key)


def _add_distributed(
    totals: dict[str, float],
    targets: Iterable[str],
    contribution: float,
) -> None:
    unique_targets = _unique_preserving_order(targets)
    if not unique_targets:
        return
    share = contribution / len(unique_targets)
    for target in unique_targets:
        if target in totals:
            totals[target] += share


def fetch_planned_rows(db: DatabaseHandler | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch user-selection rows with isolated tokens, preferring the mapping table."""
    diagnostics = _new_diagnostics()

    def _fetch(active_db: DatabaseHandler) -> list[dict[str, Any]]:
        rows = active_db.fetch_all(
            """
            SELECT
                us.id,
                us.routine,
                us.exercise AS exercise_name,
                us.sets,
                ex.primary_muscle_group,
                ex.secondary_muscle_group,
                ex.tertiary_muscle_group,
                ex.advanced_isolated_muscles,
                GROUP_CONCAT(eim.muscle, '|') AS iso_tokens_joined
            FROM user_selection us
            LEFT JOIN exercises ex ON us.exercise = ex.exercise_name
            LEFT JOIN exercise_isolated_muscles eim ON eim.exercise_name = ex.exercise_name
            GROUP BY us.id
            ORDER BY us.routine, us.id
            """
        )

        prepared: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            mapping_tokens = _split_mapping_tokens(item.get("iso_tokens_joined"))
            if mapping_tokens:
                item["isolated_tokens"] = mapping_tokens
            elif item.get("advanced_isolated_muscles"):
                item["isolated_tokens"] = _split_isolated_tokens(
                    item.get("advanced_isolated_muscles")
                )
                diagnostics["csv_fallback_count"] += 1
            else:
                item["isolated_tokens"] = []
            prepared.append(item)
        return prepared

    if db is not None:
        return _fetch(db), diagnostics

    with DatabaseHandler() as active_db:
        return _fetch(active_db), diagnostics


def _record_token_resolution(
    *,
    raw_token: str,
    diagnostics: dict[str, Any],
    unknown_as_unmapped: bool = True,
) -> tuple[str, ...]:
    normalized = taxonomy.normalize_isolated_token(raw_token)
    targets = _advanced_targets_for_token(raw_token)
    if targets is None:
        diagnostics["ignored_tokens"].append(raw_token)
        return ()
    if targets:
        return targets
    if normalized in _BASIC_ONLY_TOKEN_TO_BASIC:
        return ()
    if unknown_as_unmapped:
        diagnostics["unmapped_muscles"].append(raw_token)
    return ()


def _aggregate_blank_pst_row(
    row: dict[str, Any],
    mode: str,
    totals: dict[str, float],
    diagnostics: dict[str, Any],
) -> None:
    exercise_name = row.get("exercise_name") or row.get("exercise") or "(unknown)"
    diagnostics["blank_pst_rows"].append(exercise_name)

    strategy = taxonomy.BLANK_PST_STRATEGY
    if strategy == "exclude":
        return
    if strategy == "backfill":
        logger.warning("blank_pst row leaked past backfill: %s", exercise_name)
        return

    tokens = row.get("isolated_tokens") or []
    if not tokens:
        diagnostics["blank_pst_orphan"] += 1
        return

    try:
        contribution = float(row.get("sets") or 0)
    except (TypeError, ValueError):
        contribution = 0.0
    if contribution <= 0:
        return

    if mode == "advanced":
        advanced_targets: list[str] = []
        for token in tokens:
            advanced_targets.extend(
                _record_token_resolution(raw_token=token, diagnostics=diagnostics)
            )
        if not advanced_targets:
            diagnostics["blank_pst_orphan"] += 1
            return
        _add_distributed(totals, advanced_targets, contribution)
        return

    basic_targets: list[str] = []
    for token in tokens:
        normalized = taxonomy.normalize_isolated_token(token)
        if normalized in _BASIC_ONLY_TOKEN_TO_BASIC:
            basic_targets.append(_BASIC_ONLY_TOKEN_TO_BASIC[normalized])
            continue
        advanced_targets = _record_token_resolution(
            raw_token=token,
            diagnostics=diagnostics,
        )
        for advanced in advanced_targets:
            basic = taxonomy.ADVANCED_TO_BASIC.get(advanced)
            if basic:
                basic_targets.append(basic)

    if not basic_targets:
        diagnostics["blank_pst_orphan"] += 1
        return
    _add_distributed(totals, basic_targets, contribution)


def _aggregate_advanced_primary(
    row: dict[str, Any],
    coarse: str,
    contribution: float,
    totals: dict[str, float],
    diagnostics: dict[str, Any],
) -> None:
    coarse_basic = _coarse_basic(coarse)
    safe_targets: list[str] = []

    for token in row.get("isolated_tokens") or []:
        targets = _advanced_targets_for_token(token)
        if targets is None:
            diagnostics["ignored_tokens"].append(token)
            continue
        if not targets:
            diagnostics["unmapped_muscles"].append(token)
            continue

        target_basics = {taxonomy.ADVANCED_TO_BASIC.get(target) for target in targets}
        if coarse_basic and target_basics == {coarse_basic}:
            safe_targets.extend(targets)
            continue

        diagnostics["rejected_tokens"].append(
            {
                "token": token,
                "role": "primary",
                "coarse": coarse,
                "reason": "umbrella_family_mismatch"
                if _token_is_umbrella(token)
                else "family_mismatch",
            }
        )

    if safe_targets:
        _add_distributed(totals, safe_targets, contribution)
        return

    representative = _coarse_representative_advanced(coarse)
    if representative:
        totals[representative] += contribution
    else:
        diagnostics["unmapped_muscles"].append(coarse)


def aggregate_planned_sets(
    mode: str = "basic",
    db: DatabaseHandler | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Aggregate current workout-plan sets into Basic or Advanced muscle totals."""
    normalized_mode = "advanced" if (mode or "").lower() == "advanced" else "basic"
    totals = {muscle: 0.0 for muscle in _mode_muscles(normalized_mode)}
    rows, diagnostics = fetch_planned_rows(db)

    for row in rows:
        role_values = {
            "primary": taxonomy.canonical_pst(row.get("primary_muscle_group")),
            "secondary": taxonomy.canonical_pst(row.get("secondary_muscle_group")),
            "tertiary": taxonomy.canonical_pst(row.get("tertiary_muscle_group")),
        }

        if all(value is None for value in role_values.values()):
            _aggregate_blank_pst_row(row, normalized_mode, totals, diagnostics)
            continue

        try:
            sets = float(row.get("sets") or 0)
        except (TypeError, ValueError):
            sets = 0.0

        for role, coarse in role_values.items():
            if coarse is None:
                continue
            contribution = sets * ROLE_WEIGHTS[role]
            if normalized_mode == "basic":
                basic = _coarse_basic(coarse)
                if basic:
                    totals[basic] += contribution
                else:
                    diagnostics["unmapped_muscles"].append(coarse)
                continue

            if role == "primary" and row.get("isolated_tokens"):
                _aggregate_advanced_primary(row, coarse, contribution, totals, diagnostics)
                continue

            representative = _coarse_representative_advanced(coarse)
            if representative:
                totals[representative] += contribution
            else:
                diagnostics["unmapped_muscles"].append(coarse)

    return totals, diagnostics


def activate_volume_plan(plan_id: int) -> bool:
    """Mark exactly one volume plan active, rolling back if the target disappears."""
    with DatabaseHandler() as db:
        existing = db.fetch_one("SELECT id FROM volume_plans WHERE id = ?", (plan_id,))
        if not existing:
            return False

        try:
            db.execute_query(
                "UPDATE volume_plans SET is_active = 0 WHERE is_active = 1",
                commit=False,
            )
            rowcount = db.execute_query(
                "UPDATE volume_plans SET is_active = 1 WHERE id = ?",
                (plan_id,),
                commit=False,
            )
            if rowcount != 1:
                db.connection.rollback()
                return False
            db.connection.commit()
            return True
        except sqlite3.Error:
            db.connection.rollback()
            raise


def deactivate_volume_plan(plan_id: int) -> bool:
    """Deactivate a volume plan; inactive plans are treated idempotently."""
    with DatabaseHandler() as db:
        existing = db.fetch_one("SELECT id FROM volume_plans WHERE id = ?", (plan_id,))
        if not existing:
            return False
        db.execute_query("UPDATE volume_plans SET is_active = 0 WHERE id = ?", (plan_id,))
        return True


def _classify_target_status(
    muscle: str,
    target: float,
    sets_per_session: float = 0.0,
) -> str:
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


def _classify_progress_status(planned: float, target: float) -> str:
    if target <= 0 and planned > 0:
        return "planned_without_target"
    if target > 0 and planned <= 0:
        return "unplanned_target"
    if target > 0 and abs(planned - target) <= 0.01:
        return "on_target"
    if planned < target:
        return "under_target"
    if planned > target:
        return "over_target"
    return "on_target"


def get_volume_progress() -> dict[str, Any]:
    """Return active-plan target rows merged with current planned-set totals."""
    with DatabaseHandler() as db:
        active_plan = db.fetch_one(
            """
            SELECT id, training_days, created_at, mode, is_active
            FROM volume_plans
            WHERE is_active = 1
            LIMIT 1
            """
        )
        if not active_plan:
            return {
                "active_plan_exists": False,
                "active_plan": None,
                "rows": [],
                "diagnostics": _new_diagnostics(),
            }

        mode = "advanced" if (active_plan.get("mode") or "").lower() == "advanced" else "basic"
        planned_totals, diagnostics = aggregate_planned_sets(mode, db)
        target_rows = db.fetch_all(
            """
            SELECT muscle_group, weekly_sets, sets_per_session, status
            FROM muscle_volumes
            WHERE plan_id = ?
            ORDER BY muscle_group
            """,
            (active_plan["id"],),
        )

    targets = {
        row["muscle_group"]: float(row.get("weekly_sets") or 0)
        for row in target_rows
    }
    sets_per_session_by_muscle = {
        row["muscle_group"]: float(row.get("sets_per_session") or 0)
        for row in target_rows
    }
    muscle_order = _mode_muscles(mode)
    all_muscles = [
        muscle
        for muscle in muscle_order
        if muscle in targets or planned_totals.get(muscle, 0) > 0
    ]
    all_muscles.extend(
        sorted(
            muscle
            for muscle in set(targets) | set(planned_totals)
            if muscle not in all_muscles
            and (targets.get(muscle, 0) > 0 or planned_totals.get(muscle, 0) > 0)
        )
    )

    rows: list[dict[str, Any]] = []
    for muscle in all_muscles:
        target = targets.get(muscle, 0.0)
        planned = float(planned_totals.get(muscle, 0.0))
        remaining = max(target - planned, 0.0)
        percent = (planned / target * 100.0) if target > 0 else None
        rows.append(
            {
                "muscle_group": muscle,
                "target": round(target, 3),
                "planned": round(planned, 3),
                "remaining": round(remaining, 3),
                "percent": round(percent, 1) if percent is not None else None,
                "target_status": _classify_target_status(
                    muscle, target, sets_per_session_by_muscle.get(muscle, 0.0)
                ),
                "progress_status": _classify_progress_status(planned, target),
            }
        )

    targeted_count = sum(1 for value in targets.values() if value > 0)
    return {
        "active_plan_exists": True,
        "active_plan": {
            "id": active_plan["id"],
            "training_days": active_plan["training_days"],
            "created_at": active_plan["created_at"],
            "mode": mode,
            "targeted_count": targeted_count,
            "summary": (
                f"Active plan: #{active_plan['id']}, "
                f"{active_plan['training_days']}-day {mode} split "
                f"({targeted_count} muscles targeted)"
            ),
        },
        "rows": rows,
        "diagnostics": diagnostics,
    }
