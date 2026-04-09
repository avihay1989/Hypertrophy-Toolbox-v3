"""
Tests for routes/weekly_summary.py - Weekly summary API endpoints.

Mirrors test_session_summary_routes.py for the /weekly_summary endpoint.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from routes.weekly_summary import weekly_summary_bp, _parse_counting_mode, _parse_contribution_mode
from utils.effective_sets import CountingMode, ContributionMode


@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(weekly_summary_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def assert_success_payload(payload):
    assert payload["ok"] is True
    assert payload["status"] == "success"
    assert "data" in payload
    return payload["data"]


def assert_error_payload(payload, code, message):
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["message"] == message
    assert payload["error"]["code"] == code
    assert payload["error"]["message"] == message


class TestParseCountingMode:
    """Tests for _parse_counting_mode helper function."""

    def test_raw_mode_lowercase(self):
        assert _parse_counting_mode('raw') == CountingMode.RAW

    def test_raw_mode_uppercase(self):
        assert _parse_counting_mode('RAW') == CountingMode.RAW

    def test_raw_mode_mixed_case(self):
        assert _parse_counting_mode('RaW') == CountingMode.RAW

    def test_effective_mode_explicit(self):
        assert _parse_counting_mode('effective') == CountingMode.EFFECTIVE

    def test_empty_string_defaults_to_effective(self):
        assert _parse_counting_mode('') == CountingMode.EFFECTIVE

    def test_none_defaults_to_effective(self):
        assert _parse_counting_mode(None) == CountingMode.EFFECTIVE

    def test_invalid_value_defaults_to_effective(self):
        assert _parse_counting_mode('invalid') == CountingMode.EFFECTIVE
        assert _parse_counting_mode('something') == CountingMode.EFFECTIVE


class TestParseContributionMode:
    """Tests for _parse_contribution_mode helper function."""

    def test_direct_mode_lowercase(self):
        assert _parse_contribution_mode('direct') == ContributionMode.DIRECT_ONLY

    def test_direct_mode_uppercase(self):
        assert _parse_contribution_mode('DIRECT') == ContributionMode.DIRECT_ONLY

    def test_total_mode_explicit(self):
        assert _parse_contribution_mode('total') == ContributionMode.TOTAL

    def test_empty_string_defaults_to_total(self):
        assert _parse_contribution_mode('') == ContributionMode.TOTAL

    def test_none_defaults_to_total(self):
        assert _parse_contribution_mode(None) == ContributionMode.TOTAL

    def test_invalid_value_defaults_to_total(self):
        assert _parse_contribution_mode('invalid') == ContributionMode.TOTAL


class TestWeeklySummaryEndpoint:
    """Tests for /weekly_summary endpoint."""

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_json_response_format(self, mock_calc, mock_cats, mock_iso, client):
        """JSON response should have expected structure."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = assert_success_payload(response.get_json())
        assert 'weekly_summary' in data
        assert 'categories' in data
        assert 'isolated_muscles' in data
        assert 'modes' in data

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_json_response_uses_xhr_detection(self, mock_calc, mock_cats, mock_iso, client):
        """XHR callers should receive JSON even without an exact Accept header match."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary',
            headers={'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html'}
        )

        assert response.status_code == 200
        assert response.is_json is True
        data = assert_success_payload(response.get_json())
        assert 'weekly_summary' in data
        assert 'categories' in data
        assert 'isolated_muscles' in data
        assert 'modes' in data

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_modes_in_json_response(self, mock_calc, mock_cats, mock_iso, client):
        """JSON response should include mode information."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary?counting_mode=raw&contribution_mode=direct',
            headers={'Accept': 'application/json'}
        )

        data = assert_success_payload(response.get_json())
        assert data['modes']['counting_mode'] == 'raw'
        assert data['modes']['contribution_mode'] == 'direct'

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_default_modes(self, mock_calc, mock_cats, mock_iso, client):
        """Default modes should be effective/total."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        data = assert_success_payload(response.get_json())
        assert data['modes']['counting_mode'] == 'effective'
        assert data['modes']['contribution_mode'] == 'total'

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_method_param_passed(self, mock_calc, mock_cats, mock_iso, client):
        """Method parameter should be passed to calculate_weekly_summary."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/weekly_summary?method=Primary',
            headers={'Accept': 'application/json'}
        )

        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['method'] == 'Primary'

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_default_method_is_total(self, mock_calc, mock_cats, mock_iso, client):
        """Default method should be 'Total'."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['method'] == 'Total'

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_counting_mode_passed_to_calculator(self, mock_calc, mock_cats, mock_iso, client):
        """Counting mode should be passed to calculate_weekly_summary."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/weekly_summary?counting_mode=raw',
            headers={'Accept': 'application/json'}
        )

        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['counting_mode'] == CountingMode.RAW

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_contribution_mode_passed_to_calculator(self, mock_calc, mock_cats, mock_iso, client):
        """Contribution mode should be passed to calculate_weekly_summary."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/weekly_summary?contribution_mode=direct',
            headers={'Accept': 'application/json'}
        )

        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['contribution_mode'] == ContributionMode.DIRECT_ONLY

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_response_structure_with_data(self, mock_calc, mock_cats, mock_iso, client):
        """Weekly summary items should have expected fields."""
        mock_calc.return_value = {
            'Chest': {
                'weekly_sets': 15,
                'effective_weekly_sets': 12.5,
                'raw_weekly_sets': 15,
                'total_reps': 120,
                'total_volume': 5000,
                'frequency': 3,
                'sets_per_session': 5,
                'avg_sets_per_session': 4.2,
                'max_sets_per_session': 6.0,
                'status': 'medium',
                'volume_class': 'medium-volume',
            }
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        data = assert_success_payload(response.get_json())
        assert len(data['weekly_summary']) == 1
        item = data['weekly_summary'][0]

        assert item['muscle_group'] == 'Chest'
        assert item['total_sets'] == 15
        assert item['effective_sets'] == 12.5
        assert item['raw_sets'] == 15
        assert item['total_reps'] == 120
        assert item['total_volume'] == 5000
        assert item['total_weight'] == 5000  # Legacy alias
        assert item['frequency'] == 3
        assert item['sets_per_session'] == 5
        assert item['avg_sets_per_session'] == 4.2
        assert item['max_sets_per_session'] == 6.0
        assert item['status'] == 'medium'
        assert item['volume_class'] == 'medium-volume'
        assert 'counting_mode' in item
        assert 'contribution_mode' in item

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_effective_sets_fallback(self, mock_calc, mock_cats, mock_iso, client):
        """effective_sets should fallback to weekly_sets if effective_weekly_sets missing."""
        mock_calc.return_value = {
            'Chest': {
                'weekly_sets': 15,
                'raw_weekly_sets': 15,
                'total_reps': 120,
                'total_volume': 5000,
                'frequency': 3,
                'sets_per_session': 5,
                'status': 'medium',
                'volume_class': 'medium-volume',
            }
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        data = assert_success_payload(response.get_json())
        item = data['weekly_summary'][0]
        assert item['effective_sets'] == 15  # Fallback to weekly_sets

    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_multiple_muscles_returned(self, mock_calc, mock_cats, mock_iso, client):
        """Multiple muscles should each appear in response."""
        mock_calc.return_value = {
            'Chest': {
                'weekly_sets': 10, 'total_reps': 80, 'total_volume': 4000,
                'sets_per_session': 5, 'status': 'medium', 'volume_class': 'medium',
            },
            'Back': {
                'weekly_sets': 12, 'total_reps': 96, 'total_volume': 4800,
                'sets_per_session': 6, 'status': 'medium', 'volume_class': 'medium',
            },
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        data = assert_success_payload(response.get_json())
        assert len(data['weekly_summary']) == 2
        muscles = [item['muscle_group'] for item in data['weekly_summary']]
        assert 'Chest' in muscles
        assert 'Back' in muscles


class TestWeeklySummaryErrorHandling:
    """Tests for error handling in weekly_summary endpoint."""

    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_json_error_response(self, mock_calc, client):
        """JSON error response should have error key."""
        mock_calc.side_effect = Exception("Database error")

        response = client.get(
            '/weekly_summary',
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 500
        assert_error_payload(
            response.get_json(),
            "INTERNAL_ERROR",
            "Unable to fetch weekly summary",
        )

    @patch('routes.weekly_summary.calculate_weekly_summary')
    @patch('routes.weekly_summary.render_template')
    def test_html_error_response(self, mock_render, mock_calc, client):
        """HTML error should render error template."""
        mock_calc.side_effect = Exception("Database error")
        mock_render.return_value = "Error page"

        response = client.get('/weekly_summary')

        assert response.status_code == 500


class TestWeeklySummaryHTMLRendering:
    """Tests for HTML rendering of weekly_summary."""

    @patch('routes.weekly_summary.render_template')
    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_html_render_passes_helpers(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """HTML render should pass volume helper functions."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}
        mock_render.return_value = "Rendered HTML"

        client.get('/weekly_summary')

        call_kwargs = mock_render.call_args[1]
        assert 'get_volume_class' in call_kwargs
        assert 'get_volume_label' in call_kwargs
        assert 'get_volume_tooltip' in call_kwargs
        assert 'get_category_tooltip' in call_kwargs
        assert 'get_subcategory_tooltip' in call_kwargs

    @patch('routes.weekly_summary.render_template')
    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_html_render_passes_modes(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """HTML render should pass counting and contribution modes."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}
        mock_render.return_value = "Rendered HTML"

        client.get('/weekly_summary?counting_mode=raw&contribution_mode=direct')

        call_kwargs = mock_render.call_args[1]
        assert call_kwargs['counting_mode'] == 'raw'
        assert call_kwargs['contribution_mode'] == 'direct'

    @patch('routes.weekly_summary.render_template')
    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_html_render_template_name(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """Should render weekly_summary.html template."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}
        mock_render.return_value = "Rendered HTML"

        client.get('/weekly_summary')

        template_name = mock_render.call_args[0][0]
        assert template_name == "weekly_summary.html"

    @patch('routes.weekly_summary.render_template')
    @patch('routes.weekly_summary.calculate_isolated_muscles_stats')
    @patch('routes.weekly_summary.calculate_exercise_categories')
    @patch('routes.weekly_summary.calculate_weekly_summary')
    def test_html_render_passes_data(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """HTML render should pass weekly_summary, categories, and isolated_muscles."""
        mock_calc.return_value = {}
        mock_cats.return_value = [{'category': 'Mechanic', 'subcategory': 'Compound', 'total_exercises': 1}]
        mock_iso.return_value = {'biceps': {'exercise_count': 1}}
        mock_render.return_value = "Rendered HTML"

        client.get('/weekly_summary')

        call_kwargs = mock_render.call_args[1]
        assert 'weekly_summary' in call_kwargs
        assert 'categories' in call_kwargs
        assert 'isolated_muscles' in call_kwargs
