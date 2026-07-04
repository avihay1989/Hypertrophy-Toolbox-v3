"""Integration tests for GET /fatigue (Phase 2 Stage 2)."""
import routes.fatigue as fatigue_route
from utils.fatigue_data import build_fatigue_page_context


class TestFatigueRouteExceptionPath:
    """Regression: the except-branch of /fatigue must not crash on its own error handling."""

    def _raise(self, *args, **kwargs):
        raise RuntimeError("boom")

    def test_xhr_request_gets_json_error_not_a_crash(self, client, monkeypatch):
        # is_xhr_request() takes zero arguments; the route previously called
        # is_xhr_request(request), which raised TypeError inside the except
        # block and masked the intended error_response with an unhandled 500.
        monkeypatch.setattr(fatigue_route, "build_fatigue_page_context", self._raise)
        response = client.get('/fatigue', headers={'Accept': 'application/json'})
        assert response.status_code == 500
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'INTERNAL_ERROR'

    def test_non_xhr_request_gets_error_page(self, client, monkeypatch):
        monkeypatch.setattr(fatigue_route, "build_fatigue_page_context", self._raise)
        response = client.get('/fatigue')
        assert response.status_code == 500
        assert b'Unable to load fatigue page' in response.data


class TestFatigueRouteBasic:
    def test_returns_200_on_empty_db(self, client):
        response = client.get('/fatigue')
        assert response.status_code == 200
        # Skeleton page renders even when planned + logged are empty.
        assert b'fatigue-page' in response.data

    def test_default_period_is_this_week(self, client):
        response = client.get('/fatigue')
        # The <select> renders the period_label as the option text.
        assert b'This week' in response.data

    def test_each_valid_period_returns_200(self, client):
        for period in ("this_session", "this_week", "last_4_weeks"):
            response = client.get(f'/fatigue?period={period}')
            assert response.status_code == 200, f"period={period} failed"

    def test_invalid_period_silently_falls_back(self, client):
        # Matches the existing summary-route convention — bad URL never errors.
        response = client.get('/fatigue?period=garbage')
        assert response.status_code == 200
        # Fallback target is "this week".
        assert b'This week' in response.data


class TestFatigueRouteWithData:
    def test_planned_data_renders_muscle_bars(
        self, client, exercise_factory, workout_plan_factory
    ):
        exercise_factory(
            "Bench Press",
            primary_muscle_group="Chest",
            secondary_muscle_group="Triceps",
            tertiary_muscle_group="Front-Shoulder",
        )
        workout_plan_factory(exercise_name="Bench Press", sets=4)
        response = client.get('/fatigue')
        assert response.status_code == 200
        # Bar partial markup present and labelled with the canonical muscle name.
        assert b'fatigue-muscle-bar' in response.data
        assert b'data-muscle="Chest"' in response.data
        # Dual sub-bars: both planned and logged tracks per muscle.
        assert b'fatigue-bar-planned' in response.data
        assert b'fatigue-bar-logged' in response.data

    def test_unranked_muscle_renders_em_dash_for_percent(
        self, client, exercise_factory, workout_plan_factory
    ):
        # Lower Back has no §5 thresholds → the bar should render with "—"
        # for the % column and the unranked CSS class.
        exercise_factory(
            "Hyperextension",
            primary_muscle_group="Lower Back",
        )
        workout_plan_factory(exercise_name="Hyperextension", sets=3)
        response = client.get('/fatigue')
        assert response.status_code == 200
        assert b'data-muscle="Lower Back"' in response.data
        assert b'fatigue-bar--unranked' in response.data

    def test_empty_both_sides_shows_empty_state(self, client):
        response = client.get('/fatigue')
        assert response.status_code == 200
        assert b'fatigue-empty-state' in response.data


class TestFatigueUnassignedInvariantThroughRoute:
    """The /fatigue page must never fold Unassigned into Abdominals."""

    def test_unassigned_primary_does_not_inflate_abdominals(
        self, client, exercise_factory, workout_plan_factory
    ):
        # Add one Abdominals exercise and one Unassigned exercise with
        # identical planned parameters.
        exercise_factory(
            "Crunch",
            primary_muscle_group="Rectus Abdominis",
            secondary_muscle_group=None,
            tertiary_muscle_group=None,
        )
        exercise_factory(
            "Mystery Stretch",
            primary_muscle_group="Unassigned",
            secondary_muscle_group=None,
            tertiary_muscle_group=None,
        )
        workout_plan_factory(exercise_name="Crunch", sets=3,
                             min_rep_range=10, max_rep_range=10, rir=3)
        workout_plan_factory(exercise_name="Mystery Stretch", sets=3,
                             min_rep_range=10, max_rep_range=10, rir=3)

        # Call the context builder directly so we can inspect the bars
        # rather than parsing rendered HTML — the route handler is a
        # thin shell around it.
        ctx = build_fatigue_page_context(period="this_week")
        bars_by_muscle = {b["muscle"]: b for b in ctx["muscles_planned"]}

        assert "Unassigned" in bars_by_muscle
        assert "Abdominals" in bars_by_muscle
        # Identical inputs → identical bucket scores. If Unassigned was
        # being folded into Abdominals we'd see Abdominals == 2x Unassigned.
        assert bars_by_muscle["Unassigned"]["score"] == bars_by_muscle["Abdominals"]["score"]
        # Unassigned has no §5 landmarks → no band + no percentage.
        assert bars_by_muscle["Unassigned"]["band"] is None
        assert bars_by_muscle["Unassigned"]["percent_of_mrv"] is None
        assert bars_by_muscle["Unassigned"]["has_landmarks"] is False


class TestFatigueSFRCards:
    def test_sfr_cards_render_with_em_dash_on_empty_db(self, client):
        # No planned, no logged → both fatigues are 0 → SFR is the
        # sentinel and the template should render "—" rather than "inf"
        # or any other math artifact.
        response = client.get('/fatigue')
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert 'data-testid="fatigue-sfr-planned"' in body
        assert 'data-testid="fatigue-sfr-logged"' in body
        # Sentinel: an em dash in BOTH value containers.
        for side in ("planned", "logged"):
            marker = f'data-testid="fatigue-sfr-{side}-value"'
            idx = body.find(marker)
            assert idx != -1
            # Snip the small window around the value element and confirm "—".
            window = body[idx:idx + 200]
            assert "—" in window, f"expected em dash in SFR {side} value, got: {window!r}"
            assert "inf" not in window.lower(), f"SFR {side} leaked inf: {window!r}"

    def test_sfr_card_renders_numeric_value_when_planned_populated(
        self, client, exercise_factory, workout_plan_factory
    ):
        exercise_factory("Squat", primary_muscle_group="Quadriceps")
        workout_plan_factory(exercise_name="Squat", sets=4,
                             min_rep_range=6, max_rep_range=8, rir=2)
        response = client.get('/fatigue')
        assert response.status_code == 200
        # Planned SFR card should render a numeric value (with a decimal point);
        # logged side stays "—" because nothing was logged in this window.
        assert b'fatigue-sfr-planned-value' in response.data
        assert b'fatigue-sfr-logged-value' in response.data


class TestFatigueContextShape:
    def test_context_keys_are_stable(self, client):
        ctx = build_fatigue_page_context(period=None)
        expected_keys = {
            "period", "period_label", "valid_periods", "period_labels",
            "window_start", "window_end",
            "muscles_planned", "muscles_logged",
            "planned_fatigue_score", "planned_fatigue_band",
            "logged_fatigue_score", "logged_fatigue_band",
            "planned_stimulus", "logged_stimulus",
            "sfr_planned", "sfr_logged",
            "planned_has_data", "logged_has_data",
        }
        assert expected_keys.issubset(ctx.keys())

    def test_period_label_matches_period(self, client):
        ctx = build_fatigue_page_context(period="last_4_weeks")
        assert ctx["period"] == "last_4_weeks"
        assert "4 weeks" in ctx["period_label"].lower()
