XHR_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def assert_success(payload):
    assert payload["ok"] is True
    assert payload["status"] == "success"


def assert_error(payload, code):
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["error"]["code"] == code


def test_user_profile_page_renders_with_saved_values(client, clean_db):
    clean_db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, 'Other', 30, 180, 80, 5, CURRENT_TIMESTAMP)
        """
    )
    clean_db.execute_query(
        """
        INSERT INTO user_profile_lifts (lift_key, weight_kg, reps, updated_at)
        VALUES ('barbell_bench_press', 100, 5, CURRENT_TIMESTAMP)
        """
    )

    response = client.get("/user_profile")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "User Profile" in html
    assert "Barbell Bench Press" in html
    assert "Dumbbell Bench Press" in html
    assert 'id="nav-user-profile"' in html
    assert 'value="100.0"' in html


def test_save_user_profile_upserts_demographics(client, clean_db):
    response = client.post(
        "/api/user_profile",
        json={
            "gender": "F",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 80,
            "experience_years": 5,
        },
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["id"] == 1
    assert payload["data"]["age"] == 30

    response = client.post(
        "/api/user_profile",
        json={"gender": "M", "age": 31},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    row = clean_db.fetch_one("SELECT id, gender, age FROM user_profile")
    assert row == {"id": 1, "gender": "M", "age": 31}


def test_save_user_profile_rejects_other_gender(client, clean_db):
    response = client.post(
        "/api/user_profile",
        json={"gender": "Other"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_save_user_profile_rejects_invalid_ranges(client, clean_db):
    response = client.post(
        "/api/user_profile",
        json={"age": 101},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_save_user_profile_lifts_accepts_many_and_clears_nulls(client, clean_db):
    response = client.post(
        "/api/user_profile/lifts",
        json=[
            {"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5},
            {"lift_key": "bodyweight_pullups", "weight_kg": 0, "reps": 12},
        ],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert len(payload["data"]) == 2

    response = client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": None, "reps": None}],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    row = clean_db.fetch_one(
        "SELECT weight_kg, reps FROM user_profile_lifts WHERE lift_key = ?",
        ("barbell_bench_press",),
    )
    assert row == {"weight_kg": None, "reps": None}


def test_save_user_profile_lifts_accepts_new_split_and_added_slugs(
    client, clean_db
):
    """Issue #6 + #9: every newly added slug must be accepted by the API."""
    new_slugs = [
        "conventional_deadlift",
        "dumbbell_bench_press",
        "incline_bench_press",
        "smith_machine_bench_press",
        "machine_chest_press",
        "dumbbell_fly",
        "machine_row",
        "bodyweight_chinups",
        "dumbbell_shoulder_press",
        "machine_shoulder_press",
        "arnold_press",
        "face_pulls",
        "barbell_shrugs",
        "dumbbell_curl",
        "preacher_curl",
        "incline_dumbbell_curl",
        "skull_crusher",
        "jm_press",
        "leg_press",
        "dumbbell_squat",
        "dumbbell_lunge",
        "dumbbell_step_up",
        "hip_thrust",
        "stiff_leg_deadlift",
        "good_morning",
        "single_leg_rdl",
        "standing_calf_raise",
        "machine_hip_abduction",
        "cable_crunch",
        "machine_crunch",
        "weighted_crunch",
        "cable_woodchop",
        "side_bend",
        "back_extension",
    ]
    response = client.post(
        "/api/user_profile/lifts",
        json=[
            {"lift_key": slug, "weight_kg": 50, "reps": 5} for slug in new_slugs
        ],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert len(payload["data"]) == len(new_slugs)


def test_user_profile_page_renders_grouped_questionnaire(client, clean_db):
    """Issue #11 + Issue #24: the questionnaire renders muscle-group headings
    and every new label from Issue #6, partitioned across the anterior +
    posterior cards introduced in Issue #24."""
    response = client.get("/user_profile")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Issue #24 — original "Back" → "Upper Back"; "Shoulders" splits into
    # "Front Shoulders" + "Rear Shoulders / Traps"; "Legs — Quads & Glutes"
    # splits into "Quads" (anterior) + `hip_thrust` moved to "Glutes / Hip"
    # (posterior); "Legs — Hamstrings" → "Hamstrings".
    expected_groups = [
        "Chest",
        "Front Shoulders",
        "Biceps",
        "Core / Abs",
        "Quads",
        "Upper Back",
        "Rear Shoulders / Traps",
        "Triceps",
        "Lower Back",
        "Glutes / Hip",
        "Hamstrings",
        "Calves",
    ]
    for group in expected_groups:
        assert (
            f'class="reference-lift-group-title">{group}<' in html
        ), f"missing group heading for {group!r}"
    # Both anterior + posterior cards must render with the standard data-section
    # hooks the bodymap / E2E tests rely on.
    assert 'data-section="reference lifts anterior"' in html
    assert 'data-section="reference lifts posterior"' in html

    expected_labels = [
        "Dumbbell Bench Press",
        "Incline Barbell/Dumbbell Bench Press",
        "Smith Machine Bench Press",
        "Machine Chest Press",
        "Dumbbell Fly",
        "Machine Row",
        "Bodyweight Chin-ups",
        "Dumbbell Shoulder Press",
        "Machine Shoulder Press",
        "Arnold Press",
        "Face Pulls",
        "Barbell Shrugs",
        "Dumbbell Curl",
        "Preacher Curl (EZ Bar)",
        "Incline Dumbbell Curl",
        "Skull Crusher (EZ Bar / Barbell)",
        "JM Press",
        "Leg Press",
        "Dumbbell Squat",
        "Dumbbell Lunge",
        "Dumbbell Step-Up",
        "Hip Thrust",
        "Romanian Deadlift",
        "Conventional Deadlift",
        "Stiff-Leg Deadlift",
        "Good Morning",
        "Single-Leg RDL",
        "Standing Calf Raise",
        "Machine Hip Abduction",
        "Cable Crunch",
        "Machine Crunch",
        "Weighted Crunch",
        "Cable Woodchop",
        "Side Bend",
        "Back Extension",
    ]
    for label in expected_labels:
        assert label in html, f"missing label {label!r}"


def test_save_user_profile_lifts_rejects_unknown_lift_key(client, clean_db):
    response = client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "benchish", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_save_user_profile_preferences_upserts_tiers(client, clean_db):
    response = client.post(
        "/api/user_profile/preferences",
        json={"complex": "heavy", "accessory": "moderate", "isolated": "light"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["complex"] == "heavy"

    response = client.post(
        "/api/user_profile/preferences",
        json={"complex": "moderate"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    row = clean_db.fetch_one(
        "SELECT rep_range FROM user_profile_preferences WHERE tier = ?",
        ("complex",),
    )
    assert row["rep_range"] == "moderate"


def test_save_user_profile_preferences_rejects_invalid_values(client, clean_db):
    response = client.post(
        "/api/user_profile/preferences",
        json={"complex": "medium"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_estimate_endpoint_returns_profile_estimate(
    client, clean_db, exercise_factory
):
    exercise_factory(
        "EZ Bar Preacher Curl",
        primary_muscle_group="Biceps",
        equipment="Barbell",
        mechanic="Isolation",
    )
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "preacher_curl", "weight_kg": 35, "reps": 8}],
        headers=XHR_HEADERS,
    )

    response = client.get(
        "/api/user_profile/estimate?exercise=EZ%20Bar%20Preacher%20Curl",
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["source"] == "profile"
    assert payload["data"]["reason"] == "profile"
    # Issue #14: iso→iso direct match no longer applies the isolated tier
    # ratio twice. Epley(35,8) ≈ 44.33 × 1.00 (iso/iso) × 0.65 (light) ≈
    # 28.82 → barbell isolated rounding → 28.75 (was 11.25 pre-fix).
    assert payload["data"]["weight"] == 28.75


def test_estimate_endpoint_prefers_last_logged_set(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest", equipment="Barbell")
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )
    plan_id = workout_plan_factory(exercise_name="Barbell Bench Press", weight=80)
    workout_log_factory(
        plan_id=plan_id,
        exercise="Barbell Bench Press",
        planned_sets=4,
        planned_weight=80,
        scored_weight=82.5,
    )

    response = client.get(
        "/api/user_profile/estimate?exercise=Barbell%20Bench%20Press",
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["source"] == "log"
    assert payload["data"]["reason"] == "log"
    assert payload["data"]["weight"] == 82.5
    assert payload["data"]["sets"] == 4


def test_estimate_endpoint_returns_default_for_missing_exercise(client, clean_db):
    response = client.get("/api/user_profile/estimate", headers=XHR_HEADERS)

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["source"] == "default"
    assert payload["data"]["reason"] == "default_missing"


# Issue #17 — Deliverable C — accuracy band rendered in the page context.


def test_profile_page_context_includes_accuracy_band(client, clean_db):
    """The Profile page injects an `accuracy_band` + `next_high_impact_lifts`
    block whose state reflects how many reference lifts are filled."""
    # Empty profile → population_only band.
    response = client.get("/user_profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Population estimate only" in html
    assert "Add even one reference lift" in html or "fill in either" in html
    # The card itself renders.
    assert 'data-section="profile insights"' in html
    assert "How the system sees you" in html

    # After saving a single lift the band advances to "partial".
    response = client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200

    response = client.get("/user_profile")
    html = response.get_data(as_text=True)
    assert "Partially personalised" in html
    # A direct match no longer appears in the next-high-impact list.
    assert ">Barbell Bench Press</li>" not in html
    # But the next-priority slug (Barbell Back Squat) still does.
    assert ">Barbell Back Squat</li>" in html


def test_profile_page_next_high_impact_lifts_excludes_filled(client, clean_db):
    """Already-saved high-impact lifts must not appear in the next-3 list."""
    # Save five high-impact lifts to push the band to "mostly".
    response = client.post(
        "/api/user_profile/lifts",
        json=[
            {"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5},
            {"lift_key": "barbell_back_squat", "weight_kg": 130, "reps": 5},
            {"lift_key": "romanian_deadlift", "weight_kg": 120, "reps": 5},
            {"lift_key": "weighted_pullups", "weight_kg": 20, "reps": 5},
            {"lift_key": "military_press", "weight_kg": 60, "reps": 5},
        ],
        headers=XHR_HEADERS,
    )
    assert response.status_code == 200

    response = client.get("/user_profile")
    html = response.get_data(as_text=True)
    # None of the saved slugs should render as a next-high-impact target.
    for filled_label in (
        "Barbell Bench Press",
        "Barbell Back Squat",
        "Romanian Deadlift",
    ):
        assert f">{filled_label}</li>" not in html
    # The next-priority slug (Barbell Bicep Curl) should be surfaced.
    assert ">Barbell Bicep Curl</li>" in html or ">Triceps Extension</li>" in html


# Issue #18 — stats tiles + cohort bars + coverage donut on the page context.


def test_profile_page_renders_stats_tiles_and_cohort_summary(client, clean_db):
    """Every page render emits the four stats tiles AND the cohort summary
    line, even with an empty profile (so the user can see what's missing)."""
    response = client.get("/user_profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    for key in ("bodyweight", "height", "age", "experience"):
        assert f'data-insights-tile="{key}"' in html

    assert "data-cohort-summary" in html
    assert "Estimator cohort: " in html
    # Empty case: prompts user to fill missing fields.
    assert "fill these to calibrate" in html

    # Height + age tiles are flagged unused so the UI can de-emphasise them.
    assert "Currently unused (collected, not in formula)" in html


def test_profile_page_renders_cohort_bar_after_demographics_and_lift(
    client, clean_db
):
    """With demographics + a saved canonical compound, the cohort-bar
    section emits a row referencing the saved lift slug."""
    client.post(
        "/api/user_profile",
        json={
            "gender": "M",
            "age": 34,
            "height_cm": 178,
            "weight_kg": 75,
            "experience_years": 3,
        },
        headers=XHR_HEADERS,
    )
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )

    response = client.get("/user_profile")
    html = response.get_data(as_text=True)

    # Bars section is unhidden, with a row for the saved bench press.
    assert 'data-insights-bars' in html
    assert 'data-bar-slug="barbell_bench_press"' in html
    # Cohort summary line resolves into a calibrated copy (no "fill these").
    assert "fill these to calibrate" not in html
    assert "Suggestions are calibrated" in html
    # Tiles are populated (no longer empty).
    assert "75 kg" in html  # bodyweight tile value
    assert "Intermediate" in html  # experience tile value


def test_profile_page_donut_count_matches_accuracy_band(client, clean_db):
    """The donut payload mirrors the accuracy-band filled / total counts.
    Both surfaces must agree — they're the same metric expressed twice."""
    client.post(
        "/api/user_profile/lifts",
        json=[
            {"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5},
            {"lift_key": "barbell_back_squat", "weight_kg": 130, "reps": 5},
        ],
        headers=XHR_HEADERS,
    )

    response = client.get("/user_profile")
    html = response.get_data(as_text=True)
    # Donut SVG mounted with the count in the centre label.
    assert "data-insights-donut" in html
    assert "data-donut-count" in html
    # Linear band-meter still renders the same count.
    assert "2 / " in html  # band count uses "{filled} / {total} reference lifts"


# Issue #19 — bodymap coverage view in the page context.


def test_profile_page_renders_bodymap_coverage_section(client, clean_db):
    """The Profile page mounts the muscle-coverage section + the linear
    SR summary. Initial state (no lifts saved) shows every muscle as
    cold_start_only."""
    response = client.get("/user_profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-section="muscle coverage"' in html
    assert "Coverage map" in html
    assert "data-bodymap-svg" in html
    assert "data-bodymap-popover" in html
    assert "data-bodymap-state" in html

    # SR summary lists at least Chest at cold_start_only initially.
    assert 'data-sr-muscle="Chest"' in html
    assert 'data-sr-state="cold_start_only"' in html


def test_profile_page_bodymap_marks_chest_measured_after_saving_bench(
    client, clean_db
):
    """Saving Barbell Bench Press flips the Chest muscle from
    cold_start_only to measured in the page context. Triceps (which has
    bench at the end of its chain) flips to cross_muscle."""
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )

    response = client.get("/user_profile")
    html = response.get_data(as_text=True)

    # Chest entry now reads measured.
    assert (
        'data-sr-muscle="Chest" data-sr-state="measured"' in html
    ), "Chest should be 'measured' after saving Barbell Bench Press"
    # Triceps borrows from bench (chain has triceps_extension first, then
    # cross-fallback to barbell_bench_press) → cross_muscle.
    assert (
        'data-sr-muscle="Triceps" data-sr-state="cross_muscle"' in html
    ), "Triceps should fall back to cross_muscle when only bench is saved"


def test_profile_page_partition_covers_every_lift_exactly_once(client, clean_db):
    """Issue #24: every slug in `KEY_LIFT_LABELS` lands on exactly one of
    the anterior / posterior questionnaire cards — no orphans, no
    duplicates. Drift guard against future Issue #6-style additions
    silently being hidden from the questionnaire."""
    from routes.user_profile import REFERENCE_LIFT_GROUPS, REFERENCE_LIFT_LABELS
    from utils.profile_estimator import KEY_LIFT_LABELS, KEY_LIFT_SIDE

    anterior_slugs: list[str] = []
    posterior_slugs: list[str] = []
    for _group_label, side, entries in REFERENCE_LIFT_GROUPS:
        assert side in {"anterior", "posterior"}, (
            f"group {_group_label!r} has invalid side {side!r}"
        )
        for slug, _label in entries:
            (anterior_slugs if side == "anterior" else posterior_slugs).append(slug)

    # Exhaustiveness — every label-keyed slug appears on exactly one side.
    union = set(anterior_slugs) | set(posterior_slugs)
    assert union == set(KEY_LIFT_LABELS), (
        "questionnaire partition drifted from KEY_LIFT_LABELS: "
        f"missing={set(KEY_LIFT_LABELS) - union}, "
        f"extra={union - set(KEY_LIFT_LABELS)}"
    )
    # No duplicates within either side or across sides.
    assert len(anterior_slugs) == len(set(anterior_slugs))
    assert len(posterior_slugs) == len(set(posterior_slugs))
    assert not (set(anterior_slugs) & set(posterior_slugs)), (
        "slug appears on both anterior and posterior cards: "
        f"{set(anterior_slugs) & set(posterior_slugs)}"
    )
    # Side assignment matches `KEY_LIFT_SIDE` (single source of truth in
    # the estimator).
    for slug in anterior_slugs:
        assert KEY_LIFT_SIDE[slug] == "anterior", (
            f"{slug!r} is rendered on anterior card but KEY_LIFT_SIDE says "
            f"{KEY_LIFT_SIDE[slug]!r}"
        )
    for slug in posterior_slugs:
        assert KEY_LIFT_SIDE[slug] == "posterior", (
            f"{slug!r} is rendered on posterior card but KEY_LIFT_SIDE says "
            f"{KEY_LIFT_SIDE[slug]!r}"
        )
    # `REFERENCE_LIFT_LABELS` continues to round-trip every slug to a label.
    assert set(REFERENCE_LIFT_LABELS) == set(KEY_LIFT_LABELS)


def test_profile_page_context_exposes_anterior_posterior_partition(
    client, clean_db
):
    """Issue #24: the route context exposes
    `reference_lift_groups_anterior` / `reference_lift_groups_posterior`
    so the template can render two side-by-side cards. The page must
    surface chest under the anterior card and hamstrings under the
    posterior card."""
    response = client.get("/user_profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    anterior_marker = 'data-section="reference lifts anterior"'
    posterior_marker = 'data-section="reference lifts posterior"'
    assert anterior_marker in html and posterior_marker in html

    anterior_idx = html.index(anterior_marker)
    posterior_idx = html.index(posterior_marker)

    # Chest sits inside the anterior card; Hamstrings sits inside the
    # posterior card. Compare positional offsets to assert membership
    # without relying on exact DOM walking.
    chest_idx = html.index('class="reference-lift-group-title">Chest<')
    hamstrings_idx = html.index('class="reference-lift-group-title">Hamstrings<')

    assert anterior_idx < chest_idx < posterior_idx, (
        "Chest heading must sit between the anterior card marker and the "
        "posterior card marker"
    )
    assert posterior_idx < hamstrings_idx, (
        "Hamstrings heading must sit after the posterior card marker"
    )
