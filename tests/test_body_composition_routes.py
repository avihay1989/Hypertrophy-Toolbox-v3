"""Route tests for /body_composition (Issue #21).

Coverage map (per the Issue #21 acceptance checklist):
- (a) full demographics → calculator card visible.
- (b) missing user_profile row → empty-state card with /user_profile#demographics CTA.
- (c) one or more demographic field NULL → same empty-state card.
- (d) POST ignores client-supplied demographics (server wins).
- (e) POST returns 400 PREREQUISITE_MISSING for NULL demographics, with per-field list.
- (f) POST returns 400 UNSUPPORTED_GENDER for legacy gender values.
- (g) Partial-tape rejection — does NOT silently fall back to BMI.
- (h) Latest-row tiebreak — same captured_at → higher id wins.
- Standard: BMI-only success, Navy success, list, delete, delete-not-found,
  limit clamping, hip rejection on male.
"""
from __future__ import annotations


XHR_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def _seed_demographics(db, *, gender="M", age=30, height_cm=180.0, weight_kg=80.0):
    db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, ?, ?, ?, ?, 5, CURRENT_TIMESTAMP)
        """,
        (gender, age, height_cm, weight_kg),
    )


def _insert_snapshot(db, *, captured_at, gender="M", bfp_navy=18.0, bfp_bmi=20.0):
    db.execute_query(
        """
        INSERT INTO body_composition_snapshots (
            captured_at, weight_kg, height_cm, age_years, gender,
            bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg
        )
        VALUES (?, 80.0, 180.0, 30, ?, ?, ?, ?, ?)
        """,
        (
            captured_at,
            gender,
            bfp_navy,
            bfp_bmi,
            (bfp_navy or bfp_bmi) / 100.0 * 80.0,
            80.0 - (bfp_navy or bfp_bmi) / 100.0 * 80.0,
        ),
    )


def assert_success(payload):
    assert payload["ok"] is True
    assert payload["status"] == "success"


def assert_error(payload, code):
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["error"]["code"] == code


# ---------------------------------------------------------------------------
# GET /body_composition — page rendering + empty state
# ---------------------------------------------------------------------------


def test_get_page_with_complete_demographics_shows_calculator_card(client, clean_db):
    _seed_demographics(clean_db)
    response = client.get("/body_composition")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-testid="body-composition-calculator"' in html
    assert 'data-testid="body-composition-demographics-required"' not in html


def test_get_page_without_user_profile_row_shows_empty_state(client, clean_db):
    response = client.get("/body_composition")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-testid="body-composition-demographics-required"' in html
    assert "/user_profile#demographics" in html
    assert 'data-testid="body-composition-calculator"' not in html


def test_get_page_with_null_demographic_field_shows_empty_state(client, clean_db):
    # Row exists but `gender` is NULL.
    clean_db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, NULL, 30, 180, 80, 5, CURRENT_TIMESTAMP)
        """
    )
    response = client.get("/body_composition")
    html = response.get_data(as_text=True)
    assert 'data-testid="body-composition-demographics-required"' in html
    assert 'data-testid="body-composition-calculator"' not in html


def test_get_page_renders_snapshot_history(client, clean_db):
    _seed_demographics(clean_db)
    _insert_snapshot(clean_db, captured_at="2026-04-29T10:00:00+00:00")
    response = client.get("/body_composition")
    html = response.get_data(as_text=True)
    assert 'data-testid="body-composition-history-table"' in html
    assert "2026-04-29T10:00:00+00:00" in html


# ---------------------------------------------------------------------------
# POST /api/body_composition/snapshot — success paths
# ---------------------------------------------------------------------------


def test_post_snapshot_bmi_only_when_tape_blank(client, clean_db):
    _seed_demographics(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        json={},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    saved = payload["data"]
    assert saved["gender"] == "M"
    assert saved["bfp_navy"] is None
    assert saved["bfp_bmi"] is not None
    # Derived masses fall back to BMI when Navy is absent.
    assert saved["fat_mass_kg"] is not None
    assert saved["lean_mass_kg"] is not None


def test_post_snapshot_navy_when_male_tape_complete(client, clean_db):
    _seed_demographics(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        json={"neck_cm": 38, "waist_cm": 85},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    saved = response.get_json()["data"]
    assert saved["bfp_navy"] is not None
    assert saved["bfp_bmi"] is not None
    # Derived mass uses the Navy estimate (not BMI) when present.
    expected_fat = saved["bfp_navy"] / 100.0 * saved["weight_kg"]
    assert abs(saved["fat_mass_kg"] - expected_fat) < 1e-6


def test_post_snapshot_navy_when_female_tape_complete(client, clean_db):
    _seed_demographics(clean_db, gender="F", height_cm=165, weight_kg=60)
    response = client.post(
        "/api/body_composition/snapshot",
        json={"neck_cm": 32, "waist_cm": 75, "hip_cm": 100},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    saved = response.get_json()["data"]
    assert saved["gender"] == "F"
    assert saved["bfp_navy"] is not None
    assert saved["hip_cm"] == 100


# ---------------------------------------------------------------------------
# POST snapshot — server is the source of truth for demographics (case d)
# ---------------------------------------------------------------------------


def test_post_snapshot_ignores_client_supplied_demographics(client, clean_db):
    _seed_demographics(clean_db, gender="M", age=30, height_cm=180, weight_kg=80)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            # Client tries to override every demographic — must be ignored.
            "gender": "F",
            "age": 99,
            "height_cm": 250,
            "weight_kg": 200,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    saved = response.get_json()["data"]
    assert saved["gender"] == "M"
    assert saved["age_years"] == 30
    assert saved["height_cm"] == 180.0
    assert saved["weight_kg"] == 80.0


# ---------------------------------------------------------------------------
# POST snapshot — prerequisite + unsupported gender (cases e, f)
# ---------------------------------------------------------------------------


def test_post_snapshot_returns_prerequisite_missing_when_demographics_null(
    client, clean_db
):
    clean_db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, 'M', NULL, NULL, 80, 5, CURRENT_TIMESTAMP)
        """
    )
    response = client.post(
        "/api/body_composition/snapshot",
        json={},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "PREREQUISITE_MISSING")
    missing = payload["error"]["missing_fields"]
    assert "age" in missing
    assert "height_cm" in missing
    assert "gender" not in missing


def test_post_snapshot_returns_prerequisite_missing_when_user_profile_absent(
    client, clean_db
):
    response = client.post(
        "/api/body_composition/snapshot",
        json={},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "PREREQUISITE_MISSING")


def test_post_snapshot_returns_unsupported_gender_for_legacy_other_value(
    client, clean_db
):
    _seed_demographics(clean_db, gender="Other")
    response = client.post(
        "/api/body_composition/snapshot",
        json={},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "UNSUPPORTED_GENDER")


# ---------------------------------------------------------------------------
# POST snapshot — partial-tape rejection (case g) + male hip rejection
# ---------------------------------------------------------------------------


def test_post_snapshot_rejects_partial_tape_input_male(client, clean_db):
    _seed_demographics(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        json={"neck_cm": 38},  # waist missing — must NOT silently fall back to BMI
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert "waist_cm" in payload["error"]["missing_fields"]


def test_post_snapshot_rejects_partial_tape_input_female(client, clean_db):
    _seed_demographics(clean_db, gender="F", height_cm=165, weight_kg=60)
    response = client.post(
        "/api/body_composition/snapshot",
        json={"neck_cm": 32, "waist_cm": 75},  # hip missing
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert "hip_cm" in payload["error"]["missing_fields"]


def test_post_snapshot_rejects_hip_for_male(client, clean_db):
    _seed_demographics(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        json={"neck_cm": 38, "waist_cm": 85, "hip_cm": 100},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert payload["error"].get("field") == "hip_cm"


def test_post_snapshot_propagates_navy_log_domain_error(client, clean_db):
    _seed_demographics(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        # waist <= neck → log domain.
        json={"neck_cm": 40, "waist_cm": 40},
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


# ---------------------------------------------------------------------------
# GET /api/body_composition/snapshots — list + limit + ordering tiebreak (case h)
# ---------------------------------------------------------------------------


def test_get_snapshots_returns_empty_list_when_none_exist(client, clean_db):
    response = client.get("/api/body_composition/snapshots", headers=XHR_HEADERS)
    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"] == []


def test_get_snapshots_orders_newest_first_with_id_tiebreak(client, clean_db):
    # Two snapshots with the same captured_at — id DESC must be the tiebreaker.
    same_ts = "2026-04-29T10:00:00+00:00"
    _insert_snapshot(clean_db, captured_at=same_ts, bfp_navy=15.0)
    _insert_snapshot(clean_db, captured_at=same_ts, bfp_navy=18.0)

    response = client.get("/api/body_composition/snapshots", headers=XHR_HEADERS)
    rows = response.get_json()["data"]
    assert len(rows) == 2
    # The later-inserted row (higher id) must be the latest.
    assert rows[0]["id"] > rows[1]["id"]
    assert rows[0]["bfp_navy"] == 18.0


def test_get_snapshots_respects_limit_query_param(client, clean_db):
    for i in range(3):
        _insert_snapshot(
            clean_db,
            captured_at=f"2026-04-2{i}T10:00:00+00:00",
        )
    response = client.get(
        "/api/body_composition/snapshots?limit=1", headers=XHR_HEADERS
    )
    rows = response.get_json()["data"]
    assert len(rows) == 1


def test_get_snapshots_clamps_limit_to_cap(client, clean_db):
    response = client.get(
        "/api/body_composition/snapshots?limit=99999", headers=XHR_HEADERS
    )
    # No rows yet, but request must not error — clamp is silent.
    assert response.status_code == 200
    assert response.get_json()["data"] == []


def test_get_snapshots_rejects_invalid_limit(client, clean_db):
    response = client.get(
        "/api/body_composition/snapshots?limit=abc", headers=XHR_HEADERS
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_get_snapshots_rejects_zero_limit(client, clean_db):
    response = client.get(
        "/api/body_composition/snapshots?limit=0", headers=XHR_HEADERS
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


# ---------------------------------------------------------------------------
# DELETE /api/body_composition/snapshots/<id>
# ---------------------------------------------------------------------------


def test_delete_snapshot_removes_row(client, clean_db):
    _insert_snapshot(clean_db, captured_at="2026-04-29T10:00:00+00:00")
    snapshot_id = clean_db.fetch_one(
        "SELECT id FROM body_composition_snapshots"
    )["id"]

    response = client.delete(
        f"/api/body_composition/snapshots/{snapshot_id}", headers=XHR_HEADERS
    )
    assert response.status_code == 200
    assert_success(response.get_json())

    remaining = clean_db.fetch_one(
        "SELECT COUNT(*) AS count FROM body_composition_snapshots"
    )
    assert remaining["count"] == 0


def test_delete_snapshot_returns_404_when_missing(client, clean_db):
    response = client.delete(
        "/api/body_composition/snapshots/9999", headers=XHR_HEADERS
    )
    assert response.status_code == 404
    assert_error(response.get_json(), "NOT_FOUND")
