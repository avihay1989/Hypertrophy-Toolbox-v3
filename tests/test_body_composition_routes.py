"""Routes coverage for the Body Composition blueprint (Issue #21).

Exercises GET /body_composition (page), POST /api/body_composition/snapshot,
GET /api/body_composition/snapshots, and DELETE /api/body_composition/snapshots/<id>.
"""
from __future__ import annotations


XHR_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def _seed_profile(db, *, gender="M", age=34, height=180.0, weight=80.0):
    db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, ?, ?, ?, ?, 5, CURRENT_TIMESTAMP)
        """,
        (gender, age, height, weight),
    )


def assert_success(payload):
    assert payload["ok"] is True
    assert payload["status"] == "success"


def assert_error(payload, code):
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["error"]["code"] == code


def test_body_composition_page_renders_with_profile(client, clean_db):
    _seed_profile(clean_db)
    response = client.get("/body_composition")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Body Composition" in html
    assert 'data-page="body-composition"' in html
    assert 'id="nav-body-composition"' in html
    assert 'data-profile-gender="M"' in html
    assert 'data-profile-age="34"' in html


def test_body_composition_page_renders_without_profile(client, clean_db):
    response = client.get("/body_composition")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Body Composition" in html
    # Missing-demographics warning surfaces when no profile row exists.
    assert "Profile incomplete." in html


def test_post_snapshot_navy_male(client, clean_db):
    _seed_profile(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "neck_cm": 38.0,
            "waist_cm": 85.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    snapshot = payload["data"]
    assert snapshot["bfp_navy"] is not None
    assert snapshot["bfp_bmi"] is not None
    assert snapshot["hip_cm"] is None
    assert snapshot["fat_mass_kg"] is not None
    assert snapshot["lean_mass_kg"] is not None
    # Lean + fat should reconcile to bodyweight to within rounding.
    assert abs(snapshot["lean_mass_kg"] + snapshot["fat_mass_kg"] - 80.0) < 0.01

    rows = clean_db.fetch_all(
        "SELECT id, gender, bfp_navy FROM body_composition_snapshots"
    )
    assert len(rows) == 1
    assert rows[0]["gender"] == "M"


def test_post_snapshot_navy_female_requires_hip(client, clean_db):
    _seed_profile(clean_db, gender="F", height=165, weight=60)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "F",
            "age_years": 30,
            "height_cm": 165.0,
            "bodyweight_kg": 60.0,
            "neck_cm": 32.0,
            "waist_cm": 70.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_post_snapshot_navy_female_with_hip(client, clean_db):
    _seed_profile(clean_db, gender="F", height=165, weight=60)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "F",
            "age_years": 30,
            "height_cm": 165.0,
            "bodyweight_kg": 60.0,
            "neck_cm": 32.0,
            "waist_cm": 70.0,
            "hip_cm": 95.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    snapshot = response.get_json()["data"]
    assert snapshot["bfp_navy"] is not None
    assert snapshot["hip_cm"] == 95.0


def test_post_snapshot_male_rejects_hip(client, clean_db):
    _seed_profile(clean_db, gender="M")
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "neck_cm": 38.0,
            "waist_cm": 85.0,
            "hip_cm": 100.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert "hip_cm must not be provided" in payload["error"]["message"]


def test_post_snapshot_bmi_only(client, clean_db):
    _seed_profile(clean_db, gender="F", height=165, weight=60)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "F",
            "age_years": 30,
            "height_cm": 165.0,
            "bodyweight_kg": 60.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    snapshot = response.get_json()["data"]
    assert snapshot["bfp_navy"] is None
    assert snapshot["bfp_bmi"] is not None
    assert snapshot["neck_cm"] is None
    assert snapshot["waist_cm"] is None
    assert snapshot["hip_cm"] is None


def test_post_snapshot_uses_profile_demographics_not_payload(client, clean_db):
    _seed_profile(clean_db, gender="M", age=34, height=180.0, weight=80.0)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "F",
            "age_years": 99,
            "height_cm": 150.0,
            "bodyweight_kg": 50.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    snapshot = response.get_json()["data"]
    assert snapshot["gender"] == "M"
    assert snapshot["age_years"] == 34
    assert snapshot["height_cm"] == 180.0
    assert snapshot["bodyweight_kg"] == 80.0


def test_post_snapshot_rejects_missing_profile(client, clean_db):
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "neck_cm": 38.0,
            "waist_cm": 85.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_post_snapshot_rejects_out_of_range_height(client, clean_db):
    _seed_profile(clean_db, height=999.0)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 999.0,
            "bodyweight_kg": 80.0,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_post_snapshot_rejects_partial_tape(client, clean_db):
    _seed_profile(clean_db)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "waist_cm": 85.0,  # neck missing
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert "incomplete" in payload["error"]["message"].lower()


def test_post_snapshot_rejects_log_domain_violation(client, clean_db):
    _seed_profile(clean_db)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "neck_cm": 40.0,
            "waist_cm": 40.0,  # waist - neck = 0 -> log10 undefined
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert "larger than neck" in payload["error"]["message"]


def test_post_snapshot_uses_provided_captured_at(client, clean_db):
    _seed_profile(clean_db)
    timestamp = "2026-05-21T08:00:00Z"
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "captured_at": timestamp,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["captured_at"] == timestamp


def test_post_snapshot_accepts_iso_offset_captured_at(client, clean_db):
    _seed_profile(clean_db)
    timestamp = "2026-05-21T08:00:00+02:00"
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "captured_at": timestamp,
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["captured_at"] == timestamp


def test_post_snapshot_rejects_malformed_captured_at(client, clean_db):
    _seed_profile(clean_db)
    response = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
            "captured_at": "yesterday",
        },
        headers=XHR_HEADERS,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert_error(payload, "VALIDATION_ERROR")
    assert "captured_at" in payload["error"]["message"]


def test_list_snapshots_returns_descending(client, clean_db):
    _seed_profile(clean_db)
    earlier = {
        "gender": "M", "age_years": 34, "height_cm": 180.0, "bodyweight_kg": 80.0,
        "captured_at": "2026-05-19T08:00:00Z",
    }
    later = {**earlier, "captured_at": "2026-05-20T08:00:00Z"}
    client.post("/api/body_composition/snapshot", json=earlier, headers=XHR_HEADERS)
    client.post("/api/body_composition/snapshot", json=later, headers=XHR_HEADERS)

    response = client.get("/api/body_composition/snapshots", headers=XHR_HEADERS)
    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    data = payload["data"]
    assert len(data) == 2
    assert data[0]["captured_at"] == "2026-05-20T08:00:00Z"
    assert data[1]["captured_at"] == "2026-05-19T08:00:00Z"


def test_list_snapshots_empty(client, clean_db):
    response = client.get("/api/body_composition/snapshots", headers=XHR_HEADERS)
    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"] == []


def test_delete_snapshot_success(client, clean_db):
    _seed_profile(clean_db)
    created = client.post(
        "/api/body_composition/snapshot",
        json={
            "gender": "M",
            "age_years": 34,
            "height_cm": 180.0,
            "bodyweight_kg": 80.0,
        },
        headers=XHR_HEADERS,
    ).get_json()["data"]
    snapshot_id = created["id"]

    response = client.delete(
        f"/api/body_composition/snapshots/{snapshot_id}",
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"] == {"id": snapshot_id}

    remaining = clean_db.fetch_all(
        "SELECT id FROM body_composition_snapshots WHERE id = ?",
        (snapshot_id,),
    )
    assert remaining == []


def test_delete_snapshot_not_found(client, clean_db):
    response = client.delete(
        "/api/body_composition/snapshots/9999",
        headers=XHR_HEADERS,
    )
    assert response.status_code == 404
    assert_error(response.get_json(), "NOT_FOUND")


def test_page_lists_existing_snapshots(client, clean_db):
    _seed_profile(clean_db)
    clean_db.execute_query(
        """
        INSERT INTO body_composition_snapshots (
            captured_at, bodyweight_kg, height_cm, age_years, gender,
            bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("2026-05-20T10:00:00Z", 80.0, 180.0, 34, "M", 16.1, 20.3, 12.9, 67.1),
    )
    response = client.get("/body_composition")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "16.1 %" in html
    assert "67.1 kg" in html
    assert 'data-bc-snapshot-id' in html
