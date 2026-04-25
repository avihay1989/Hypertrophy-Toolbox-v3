"""Strict Phase 0 taxonomy checks for plan volume integration.

These tests intentionally read the live development DB at data/database.db.
They do not use the normal test DB fixture because Phase 0 gates on the real
catalog taxonomy, not seeded fixtures.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from utils.constants import ADVANCED_SET
from utils.volume_taxonomy import (
    ADVANCED_MUSCLE_GROUPS,
    ADVANCED_TO_BASIC,
    BASIC_MUSCLE_GROUPS,
    BLANK_PST_STRATEGY,
    COARSE_TO_BASIC,
    COARSE_TO_REPRESENTATIVE_ADVANCED,
    DISTRIBUTED_UMBRELLA_TOKENS,
    IGNORED_TOKENS,
    TOKEN_TO_ADVANCED,
    advanced_to_basic,
    canonical_pst,
    expand_umbrella,
    normalize_isolated_token,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = REPO_ROOT / "data" / "database.db"
AUDIT_DOC = REPO_ROOT / "docs" / "VOLUME_TAXONOMY_AUDIT.md"


def _connect() -> sqlite3.Connection:
    assert LIVE_DB.exists(), f"Live DB is required for Phase 0: {LIVE_DB}"
    conn = sqlite3.connect(LIVE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _distinct_pst_values() -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    with _connect() as conn:
        for column in (
            "primary_muscle_group",
            "secondary_muscle_group",
            "tertiary_muscle_group",
        ):
            rows = conn.execute(
                f"""
                SELECT DISTINCT {column} AS value
                  FROM exercises
                 WHERE {column} IS NOT NULL
                   AND TRIM({column}) <> ''
                 ORDER BY value COLLATE NOCASE
                """
            ).fetchall()
            values.extend((column, row["value"]) for row in rows)
    return values


def _csv_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [token.strip() for token in re.split(r"[;,]", raw) if token.strip()]


def _distinct_isolated_tokens() -> set[str]:
    tokens: set[str] = set()
    with _connect() as conn:
        for row in conn.execute("SELECT DISTINCT muscle FROM exercise_isolated_muscles"):
            tokens.add(row["muscle"])
        for row in conn.execute(
            """
            SELECT advanced_isolated_muscles
              FROM exercises
             WHERE advanced_isolated_muscles IS NOT NULL
               AND TRIM(advanced_isolated_muscles) <> ''
            """
        ):
            tokens.update(_csv_tokens(row["advanced_isolated_muscles"]))
    return tokens


def test_every_pst_value_has_basic_rollup() -> None:
    missing: list[tuple[str, str, str | None]] = []
    invalid: list[tuple[str, str]] = []

    for column, raw in _distinct_pst_values():
        key = canonical_pst(raw)
        if key not in COARSE_TO_BASIC:
            missing.append((column, raw, key))
            continue
        if COARSE_TO_BASIC[key] not in BASIC_MUSCLE_GROUPS:
            invalid.append((raw, COARSE_TO_BASIC[key]))

    assert missing == []
    assert invalid == []


def test_every_pst_value_has_representative_advanced() -> None:
    missing: list[tuple[str, str, str | None]] = []
    invalid: list[tuple[str, str]] = []

    for column, raw in _distinct_pst_values():
        key = canonical_pst(raw)
        if key not in COARSE_TO_REPRESENTATIVE_ADVANCED:
            missing.append((column, raw, key))
            continue
        representative = COARSE_TO_REPRESENTATIVE_ADVANCED[key]
        if representative not in ADVANCED_MUSCLE_GROUPS:
            invalid.append((raw, representative))

    assert missing == []
    assert invalid == []


def test_every_isolated_token_handled() -> None:
    missing: list[tuple[str, str]] = []
    invalid: list[tuple[str, str | None]] = []

    for raw in sorted(_distinct_isolated_tokens()):
        normalized = normalize_isolated_token(raw)
        if normalized in DISTRIBUTED_UMBRELLA_TOKENS:
            continue
        if normalized in IGNORED_TOKENS:
            continue
        if normalized not in TOKEN_TO_ADVANCED:
            missing.append((raw, normalized))
            continue
        advanced = TOKEN_TO_ADVANCED[normalized]
        if advanced not in ADVANCED_MUSCLE_GROUPS:
            invalid.append((normalized, advanced))

    assert missing == []
    assert invalid == []


def test_advanced_to_basic_is_total() -> None:
    missing = [muscle for muscle in ADVANCED_MUSCLE_GROUPS if muscle not in ADVANCED_TO_BASIC]
    invalid = [
        (advanced, basic)
        for advanced, basic in ADVANCED_TO_BASIC.items()
        if advanced in ADVANCED_MUSCLE_GROUPS and basic not in BASIC_MUSCLE_GROUPS
    ]

    assert missing == []
    assert invalid == []


def test_advanced_set_normalizes_to_advanced_muscle_groups() -> None:
    missing: list[tuple[str, str]] = []
    invalid: list[tuple[str, str | None]] = []

    for raw in sorted(ADVANCED_SET):
        normalized = normalize_isolated_token(raw)
        if normalized in ADVANCED_MUSCLE_GROUPS:
            continue
        if normalized in DISTRIBUTED_UMBRELLA_TOKENS:
            continue
        advanced = TOKEN_TO_ADVANCED.get(normalized)
        if advanced is None:
            missing.append((raw, normalized))
            continue
        if advanced not in ADVANCED_MUSCLE_GROUPS:
            invalid.append((normalized, advanced))

    assert missing == []
    assert invalid == []


def test_design_calls_documented() -> None:
    assert advanced_to_basic("lower-trapezius") == "Middle-Traps"
    assert expand_umbrella("quadriceps") == (
        "rectus-femoris",
        "inner-quadriceps",
        "outer-quadriceps",
    )
    assert TOKEN_TO_ADVANCED["serratus-anterior"] == "mid-lower-pectoralis"


def test_blank_pst_strategy_is_set() -> None:
    assert BLANK_PST_STRATEGY in {"isolated_only", "backfill", "exclude"}


def test_blank_pst_audit_section_present() -> None:
    assert AUDIT_DOC.exists(), f"Missing Phase 0 audit doc: {AUDIT_DOC}"
    text = AUDIT_DOC.read_text(encoding="utf-8")
    assert "## Blank P/S/T exercises" in text

    with _connect() as conn:
        blank_count = conn.execute(
            """
            SELECT COUNT(*)
              FROM exercises
             WHERE (primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='')
               AND (secondary_muscle_group IS NULL OR TRIM(secondary_muscle_group)='')
               AND (tertiary_muscle_group IS NULL OR TRIM(tertiary_muscle_group)='')
            """
        ).fetchone()[0]

    if blank_count:
        assert "| Exercise | advanced_isolated_muscles | isolated tokens | iso_count | Proposed strategy |" in text
