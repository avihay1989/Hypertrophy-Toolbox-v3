"""Backend tests for the advisory fatigue context layer (Phase 2D-A).

Covers the default-off settings helpers, the additive `build_fatigue_context`
assembly (source filtering, planned/logged disagreement, advisory fallback for
unranked/unknown/Unassigned muscles), the settings route contract, and the
regression guard that the estimate response is unchanged except for the
additive `fatigue_context` block. See
``docs/user_profile/LEARNED_CALIBRATION_PLAN.md`` §"Phase 2D-A".
"""
import pytest

import utils.fatigue_context as fatigue_context_module
from utils.fatigue_context import (
    DEFAULT_FATIGUE_CONTEXT_PERIOD,
    DEFAULT_FATIGUE_CONTEXT_SOURCE,
    build_fatigue_context,
    get_fatigue_context_settings,
    set_fatigue_context_settings,
)


XHR_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def _bar(muscle, band, *, pct=50.0, has_landmarks=True, score=10.0):
    return {
        "muscle": muscle,
        "score": score,
        "band": band,
        "percent_of_mrv": pct,
        "has_landmarks": has_landmarks,
    }


def _patch_page(monkeypatch, *, planned=None, logged=None):
    """Stub build_fatigue_page_context so assembly logic is deterministic."""
    def _fake(period, today=None):
        return {
            "muscles_planned": planned or [],
            "muscles_logged": logged or [],
        }

    monkeypatch.setattr(fatigue_context_module, "build_fatigue_page_context", _fake)


def _raise_page(*args, **kwargs):
    """Stand-in page builder that blows up — used to prove resilience."""
    raise RuntimeError("fatigue page build failed")


# --------------------------------------------------------------------------- #
# Settings helpers — default-off + round-trip + validation
# --------------------------------------------------------------------------- #

def test_missing_settings_row_reads_as_disabled_defaults(db_handler):
    settings = get_fatigue_context_settings(db=db_handler)
    assert settings == {
        "enabled": False,
        "context_source": DEFAULT_FATIGUE_CONTEXT_SOURCE,  # "both"
        "context_period": DEFAULT_FATIGUE_CONTEXT_PERIOD,  # "this_week"
    }


def test_set_settings_round_trips(db_handler):
    saved = set_fatigue_context_settings(
        db=db_handler,
        enabled=True,
        context_source="logged",
        context_period="last_4_weeks",
    )
    assert saved == {
        "enabled": True,
        "context_source": "logged",
        "context_period": "last_4_weeks",
    }
    assert get_fatigue_context_settings(db=db_handler) == saved


def test_set_settings_partial_update_preserves_other_fields(db_handler):
    set_fatigue_context_settings(
        db=db_handler, enabled=True, context_source="planned", context_period="this_session"
    )
    # Toggle only `enabled`; source/period must be preserved.
    saved = set_fatigue_context_settings(db=db_handler, enabled=False)
    assert saved == {
        "enabled": False,
        "context_source": "planned",
        "context_period": "this_session",
    }


def test_set_settings_rejects_invalid_source(db_handler):
    with pytest.raises(ValueError):
        set_fatigue_context_settings(db=db_handler, context_source="bogus")


def test_set_settings_rejects_invalid_period(db_handler):
    with pytest.raises(ValueError):
        set_fatigue_context_settings(db=db_handler, context_period="forever")


# --------------------------------------------------------------------------- #
# build_fatigue_context — disabled / unknown short-circuits
# --------------------------------------------------------------------------- #

def test_build_returns_none_when_disabled(clean_db, exercise_factory):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest")
    assert build_fatigue_context("Barbell Bench Press", db=clean_db) is None


def test_build_returns_none_for_unknown_exercise(clean_db):
    set_fatigue_context_settings(db=clean_db, enabled=True)
    assert build_fatigue_context("Does Not Exist", db=clean_db) is None


def test_build_returns_none_for_blank_exercise(clean_db):
    set_fatigue_context_settings(db=clean_db, enabled=True)
    assert build_fatigue_context("   ", db=clean_db) is None


# --------------------------------------------------------------------------- #
# build_fatigue_context — ranked muscle assembly
# --------------------------------------------------------------------------- #

def test_build_both_sources_agree(clean_db, exercise_factory, monkeypatch):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest")
    set_fatigue_context_settings(db=clean_db, enabled=True, context_source="both")
    _patch_page(
        monkeypatch,
        planned=[_bar("Chest", "moderate")],
        logged=[_bar("Chest", "moderate")],
    )

    block = build_fatigue_context("Barbell Bench Press", db=clean_db)
    assert block["enabled"] is True
    assert block["muscle"] == "Chest"
    assert block["has_landmarks"] is True
    assert block["is_advisory_fallback"] is False
    assert block["disagree"] is False
    assert block["planned"]["band"] == "moderate"
    assert block["logged"]["band"] == "moderate"
    assert block["headline"] == "Chest fatigue: moderate."
    assert block["advisory"] == "This does not change your suggestion."


def test_build_both_sources_disagree_shows_both(clean_db, exercise_factory, monkeypatch):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest")
    set_fatigue_context_settings(db=clean_db, enabled=True, context_source="both")
    _patch_page(
        monkeypatch,
        planned=[_bar("Chest", "heavy")],
        logged=[_bar("Chest", "light")],
    )

    block = build_fatigue_context("Barbell Bench Press", db=clean_db)
    assert block["disagree"] is True
    assert block["is_advisory_fallback"] is False
    assert "(planned)" in block["headline"]
    assert "(logged)" in block["headline"]
    assert "heavy" in block["headline"]
    assert "light" in block["headline"]


def test_build_planned_source_only(clean_db, exercise_factory, monkeypatch):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest")
    set_fatigue_context_settings(db=clean_db, enabled=True, context_source="planned")
    _patch_page(
        monkeypatch,
        planned=[_bar("Chest", "heavy")],
        logged=[_bar("Chest", "light")],
    )

    block = build_fatigue_context("Barbell Bench Press", db=clean_db)
    assert block["planned"]["band"] == "heavy"
    assert block["logged"] is None
    assert block["disagree"] is False
    assert block["headline"] == "Chest fatigue: heavy."


def test_build_logged_source_only(clean_db, exercise_factory, monkeypatch):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest")
    set_fatigue_context_settings(db=clean_db, enabled=True, context_source="logged")
    _patch_page(
        monkeypatch,
        planned=[_bar("Chest", "heavy")],
        logged=[_bar("Chest", "light")],
    )

    block = build_fatigue_context("Barbell Bench Press", db=clean_db)
    assert block["planned"] is None
    assert block["logged"]["band"] == "light"
    assert block["headline"] == "Chest fatigue: light."


# --------------------------------------------------------------------------- #
# build_fatigue_context — advisory fallback (never block, never classify)
# --------------------------------------------------------------------------- #

def test_build_unranked_muscle_falls_back_to_advisory(clean_db, exercise_factory, monkeypatch):
    # "Neck" has no §5 landmarks -> neutral advisory, never high/low.
    exercise_factory("Neck Curl", primary_muscle_group="Neck")
    set_fatigue_context_settings(db=clean_db, enabled=True)
    _patch_page(monkeypatch)  # no bars

    block = build_fatigue_context("Neck Curl", db=clean_db)
    assert block is not None
    assert block["has_landmarks"] is False
    assert block["is_advisory_fallback"] is True
    assert "isn't ranked" in block["headline"]
    assert block["advisory"] == "This does not change your suggestion."


def test_build_unassigned_muscle_falls_back_to_advisory(clean_db, exercise_factory, monkeypatch):
    exercise_factory("Mystery Move", primary_muscle_group="Unassigned")
    set_fatigue_context_settings(db=clean_db, enabled=True)
    _patch_page(monkeypatch)

    block = build_fatigue_context("Mystery Move", db=clean_db)
    assert block["muscle"] == "Unassigned"
    assert block["has_landmarks"] is False
    assert block["is_advisory_fallback"] is True


def test_build_ranked_muscle_without_data_falls_back(clean_db, exercise_factory, monkeypatch):
    # Chest IS ranked, but no planned/logged bars exist -> advisory, not a band.
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest")
    set_fatigue_context_settings(db=clean_db, enabled=True)
    _patch_page(monkeypatch)

    block = build_fatigue_context("Barbell Bench Press", db=clean_db)
    assert block["has_landmarks"] is True
    assert block["is_advisory_fallback"] is True
    assert block["planned"] is None
    assert block["logged"] is None


def test_build_null_primary_muscle_falls_back_without_page_build(
    clean_db, exercise_factory, monkeypatch
):
    # A NULL primary_muscle_group can never resolve to a fatigue bar: the block
    # must short-circuit to the neutral advisory fallback WITHOUT ever calling
    # the page builder (which here would raise if reached) and never raise.
    exercise_factory("Mystery Lift", primary_muscle_group=None)
    set_fatigue_context_settings(db=clean_db, enabled=True)
    monkeypatch.setattr(fatigue_context_module, "build_fatigue_page_context", _raise_page)

    block = build_fatigue_context("Mystery Lift", db=clean_db)
    assert block is not None
    assert block["muscle"] is None
    assert block["has_landmarks"] is False
    assert block["is_advisory_fallback"] is True
    assert block["planned"] is None
    assert block["logged"] is None
    assert block["disagree"] is False
    assert "isn't ranked" in block["headline"]
    assert block["advisory"] == "This does not change your suggestion."


# --------------------------------------------------------------------------- #
# Settings route contract
# --------------------------------------------------------------------------- #

def test_settings_route_get_defaults(client, clean_db):
    response = client.get(
        "/api/user_profile/fatigue_context_settings", headers=XHR_HEADERS
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"] == {
        "enabled": False,
        "context_source": "both",
        "context_period": "this_week",
    }


def test_settings_route_post_saves(client, clean_db):
    response = client.post(
        "/api/user_profile/fatigue_context_settings",
        json={"enabled": True, "context_source": "logged", "context_period": "last_4_weeks"},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["enabled"] is True
    assert payload["data"]["context_source"] == "logged"
    assert payload["data"]["context_period"] == "last_4_weeks"

    # Persisted across a fresh GET.
    after = client.get(
        "/api/user_profile/fatigue_context_settings", headers=XHR_HEADERS
    ).get_json()
    assert after["data"]["enabled"] is True


def test_settings_route_rejects_invalid_source(client, clean_db):
    response = client.post(
        "/api/user_profile/fatigue_context_settings",
        json={"context_source": "nope"},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_settings_route_rejects_invalid_period(client, clean_db):
    response = client.post(
        "/api/user_profile/fatigue_context_settings",
        json={"context_period": "nope"},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


# --------------------------------------------------------------------------- #
# Estimate response — additive only + regression guard
# --------------------------------------------------------------------------- #

def _estimate(client, exercise):
    return client.get(
        f"/api/user_profile/estimate?exercise={exercise}", headers=XHR_HEADERS
    ).get_json()["data"]


def test_estimate_omits_fatigue_context_when_disabled(client, clean_db, exercise_factory):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest", equipment="Barbell")
    data = _estimate(client, "Barbell%20Bench%20Press")
    assert "fatigue_context" not in data


def test_estimate_adds_only_fatigue_context_when_enabled(
    client, clean_db, exercise_factory
):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest", equipment="Barbell")
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )

    off = _estimate(client, "Barbell%20Bench%20Press")
    assert "fatigue_context" not in off

    client.post(
        "/api/user_profile/fatigue_context_settings",
        json={"enabled": True},
        headers=XHR_HEADERS,
    )
    on = _estimate(client, "Barbell%20Bench%20Press")

    # The additive block is present...
    assert on["fatigue_context"]["enabled"] is True
    assert on["fatigue_context"]["advisory"] == "This does not change your suggestion."
    # ...and EVERY pre-existing field is byte-for-byte unchanged.
    for key in (
        "weight", "sets", "min_rep", "max_rep", "rir", "rpe",
        "source", "reason", "is_dumbbell", "trace",
    ):
        assert on[key] == off[key], f"estimate field '{key}' changed when fatigue context enabled"


def test_estimate_fatigue_context_carries_advisory_for_unranked(
    client, clean_db, exercise_factory
):
    exercise_factory("Neck Curl", primary_muscle_group="Neck", equipment="Barbell")
    client.post(
        "/api/user_profile/fatigue_context_settings",
        json={"enabled": True},
        headers=XHR_HEADERS,
    )
    data = _estimate(client, "Neck%20Curl")
    assert data["fatigue_context"]["is_advisory_fallback"] is True
    assert "isn't ranked" in data["fatigue_context"]["headline"]


def test_estimate_survives_fatigue_context_failure(
    client, clean_db, exercise_factory, monkeypatch
):
    # The advisory layer must never break the estimate: if the page builder
    # raises while enabled, the decorator swallows it and the estimate returns
    # exactly as it would with the layer off (no `fatigue_context` key).
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest", equipment="Barbell")
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )

    off = _estimate(client, "Barbell%20Bench%20Press")
    assert "fatigue_context" not in off

    client.post(
        "/api/user_profile/fatigue_context_settings",
        json={"enabled": True},
        headers=XHR_HEADERS,
    )
    monkeypatch.setattr(fatigue_context_module, "build_fatigue_page_context", _raise_page)

    response = client.get(
        "/api/user_profile/estimate?exercise=Barbell%20Bench%20Press", headers=XHR_HEADERS
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    data = payload["data"]

    # Failure is swallowed: no block added, and the estimate is unchanged.
    assert "fatigue_context" not in data
    for key in (
        "weight", "sets", "min_rep", "max_rep", "rir", "rpe",
        "source", "reason", "is_dumbbell", "trace",
    ):
        assert data[key] == off[key], f"estimate field '{key}' changed on fatigue failure"
