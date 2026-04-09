"""
Tests for routes/session_summary.py - Session summary API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from routes.session_summary import session_summary_bp, _parse_counting_mode, _parse_contribution_mode
from utils.effective_sets import CountingMode, ContributionMode


@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(session_summary_bp)
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
        """'raw' should return RAW counting mode."""
        assert _parse_counting_mode('raw') == CountingMode.RAW

    def test_raw_mode_uppercase(self):
        """'RAW' should return RAW counting mode."""
        assert _parse_counting_mode('RAW') == CountingMode.RAW

    def test_raw_mode_mixed_case(self):
        """'RaW' should return RAW counting mode."""
        assert _parse_counting_mode('RaW') == CountingMode.RAW

    def test_effective_mode_explicit(self):
        """'effective' should return EFFECTIVE counting mode."""
        assert _parse_counting_mode('effective') == CountingMode.EFFECTIVE

    def test_empty_string_defaults_to_effective(self):
        """Empty string should default to EFFECTIVE."""
        assert _parse_counting_mode('') == CountingMode.EFFECTIVE

    def test_none_defaults_to_effective(self):
        """None should default to EFFECTIVE."""
        assert _parse_counting_mode(None) == CountingMode.EFFECTIVE  # type: ignore[arg-type]

    def test_invalid_value_defaults_to_effective(self):
        """Invalid value should default to EFFECTIVE."""
        assert _parse_counting_mode('invalid') == CountingMode.EFFECTIVE
        assert _parse_counting_mode('something') == CountingMode.EFFECTIVE


class TestParseContributionMode:
    """Tests for _parse_contribution_mode helper function."""

    def test_direct_mode_lowercase(self):
        """'direct' should return DIRECT_ONLY contribution mode."""
        assert _parse_contribution_mode('direct') == ContributionMode.DIRECT_ONLY

    def test_direct_mode_uppercase(self):
        """'DIRECT' should return DIRECT_ONLY contribution mode."""
        assert _parse_contribution_mode('DIRECT') == ContributionMode.DIRECT_ONLY

    def test_total_mode_explicit(self):
        """'total' should return TOTAL contribution mode."""
        assert _parse_contribution_mode('total') == ContributionMode.TOTAL

    def test_empty_string_defaults_to_total(self):
        """Empty string should default to TOTAL."""
        assert _parse_contribution_mode('') == ContributionMode.TOTAL

    def test_none_defaults_to_total(self):
        """None should default to TOTAL."""
        assert _parse_contribution_mode(None) == ContributionMode.TOTAL  # type: ignore[arg-type]

    def test_invalid_value_defaults_to_total(self):
        """Invalid value should default to TOTAL."""
        assert _parse_contribution_mode('invalid') == ContributionMode.TOTAL


class TestSessionSummaryEndpoint:
    """Tests for /session_summary endpoint."""

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_json_response_format(self, mock_calc, mock_cats, mock_iso, client):
        """JSON response should have expected structure."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        assert response.status_code == 200
        data = assert_success_payload(response.get_json())
        assert 'session_summary' in data
        assert 'categories' in data
        assert 'isolated_muscles' in data
        assert 'modes' in data

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_json_response_uses_xhr_detection(self, mock_calc, mock_cats, mock_iso, client):
        """XHR callers should receive JSON even without an exact Accept header match."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html'}
        )

        assert response.status_code == 200
        assert response.is_json is True
        data = assert_success_payload(response.get_json())
        assert 'session_summary' in data
        assert 'categories' in data
        assert 'isolated_muscles' in data
        assert 'modes' in data

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_modes_in_json_response(self, mock_calc, mock_cats, mock_iso, client):
        """JSON response should include mode information."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary?counting_mode=raw&contribution_mode=direct',
            headers={'Accept': 'application/json'}
        )
        
        data = assert_success_payload(response.get_json())
        assert data['modes']['counting_mode'] == 'raw'
        assert data['modes']['contribution_mode'] == 'direct'

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_default_modes(self, mock_calc, mock_cats, mock_iso, client):
        """Default modes should be effective/total."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        data = assert_success_payload(response.get_json())
        assert data['modes']['counting_mode'] == 'effective'
        assert data['modes']['contribution_mode'] == 'total'

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_routine_filter_passed(self, mock_calc, mock_cats, mock_iso, client):
        """Routine filter should be passed to calculate_session_summary."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/session_summary?routine=Push',
            headers={'Accept': 'application/json'}
        )
        
        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['routine'] == 'Push'

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_date_range_filter_passed(self, mock_calc, mock_cats, mock_iso, client):
        """Date range should be passed as time_window tuple."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/session_summary?start_date=2024-01-01&end_date=2024-01-31',
            headers={'Accept': 'application/json'}
        )
        
        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['time_window'] == ('2024-01-01', '2024-01-31')

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_no_date_filter_passes_none(self, mock_calc, mock_cats, mock_iso, client):
        """No date parameters should pass None for time_window."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['time_window'] is None

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_counting_mode_passed_to_calculator(self, mock_calc, mock_cats, mock_iso, client):
        """Counting mode should be passed to calculate_session_summary."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/session_summary?counting_mode=raw',
            headers={'Accept': 'application/json'}
        )
        
        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['counting_mode'] == CountingMode.RAW

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_contribution_mode_passed_to_calculator(self, mock_calc, mock_cats, mock_iso, client):
        """Contribution mode should be passed to calculate_session_summary."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}

        client.get(
            '/session_summary?contribution_mode=direct',
            headers={'Accept': 'application/json'}
        )
        
        call_kwargs = mock_calc.call_args[1]
        assert call_kwargs['contribution_mode'] == ContributionMode.DIRECT_ONLY

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_session_summary_response_structure(self, mock_calc, mock_cats, mock_iso, client):
        """Session summary items should have expected fields."""
        mock_calc.return_value = {
            'Push': {
                'Chest': {
                    'weekly_sets': 15,
                    'effective_sets': 12.5,
                    'raw_sets': 15,
                    'sets_per_session': 5,
                    'effective_per_session': 4.2,
                    'status': 'optimal',
                    'volume_class': 'medium-volume',
                    'total_reps': 120,
                    'total_volume': 5000,
                    'warning_level': 'ok',
                    'is_borderline': False,
                    'is_excessive': False,
                }
            }
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        data = assert_success_payload(response.get_json())
        assert len(data['session_summary']) == 1
        item = data['session_summary'][0]
        
        # Check expected fields
        assert item['routine'] == 'Push'
        assert item['muscle_group'] == 'Chest'
        assert item['weekly_sets'] == 15
        assert item['effective_sets'] == 12.5
        assert item['raw_sets'] == 15
        assert item['sets_per_session'] == 5
        assert item['effective_per_session'] == 4.2
        assert item['status'] == 'optimal'
        assert item['volume_class'] == 'medium-volume'
        assert item['total_reps'] == 120
        assert item['total_volume'] == 5000
        assert item['warning_level'] == 'ok'
        assert item['is_borderline'] is False
        assert item['is_excessive'] is False
        assert 'counting_mode' in item
        assert 'contribution_mode' in item


class TestSessionSummaryErrorHandling:
    """Tests for error handling in session_summary endpoint."""

    @patch('routes.session_summary.calculate_session_summary')
    def test_json_error_response(self, mock_calc, client):
        """JSON error response should have error key."""
        mock_calc.side_effect = Exception("Database error")

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        assert response.status_code == 500
        assert_error_payload(
            response.get_json(),
            "INTERNAL_ERROR",
            "Unable to fetch session summary",
        )

    @patch('routes.session_summary.calculate_session_summary')
    @patch('routes.session_summary.render_template')
    def test_html_error_response(self, mock_render, mock_calc, client):
        """HTML error should render error template."""
        mock_calc.side_effect = Exception("Database error")
        mock_render.return_value = "Error page"

        response = client.get('/session_summary')
        
        assert response.status_code == 500


class TestSessionSummaryHTMLRendering:
    """Tests for HTML rendering of session_summary."""

    @patch('routes.session_summary.render_template')
    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_html_render_passes_helpers(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """HTML render should pass volume helper functions."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}
        mock_render.return_value = "Rendered HTML"

        client.get('/session_summary')  # No Accept: application/json header
        
        call_kwargs = mock_render.call_args[1]
        assert 'get_volume_class' in call_kwargs
        assert 'get_volume_label' in call_kwargs
        assert 'get_volume_tooltip' in call_kwargs
        assert 'get_category_tooltip' in call_kwargs
        assert 'get_subcategory_tooltip' in call_kwargs

    @patch('routes.session_summary.render_template')
    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_html_render_passes_modes(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """HTML render should pass counting and contribution modes."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}
        mock_render.return_value = "Rendered HTML"

        client.get('/session_summary?counting_mode=raw&contribution_mode=direct')
        
        call_kwargs = mock_render.call_args[1]
        assert call_kwargs['counting_mode'] == 'raw'
        assert call_kwargs['contribution_mode'] == 'direct'

    @patch('routes.session_summary.render_template')
    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_html_render_template_name(self, mock_calc, mock_cats, mock_iso, mock_render, client):
        """Should render session_summary.html template."""
        mock_calc.return_value = {}
        mock_cats.return_value = []
        mock_iso.return_value = {}
        mock_render.return_value = "Rendered HTML"

        client.get('/session_summary')
        
        template_name = mock_render.call_args[0][0]
        assert template_name == "session_summary.html"


class TestSessionSummaryDataTransformation:
    """Tests for data transformation in session_summary endpoint."""

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_multiple_routines_flattened(self, mock_calc, mock_cats, mock_iso, client):
        """Multiple routines should be flattened into single list."""
        mock_calc.return_value = {
            'Push': {
                'Chest': {'weekly_sets': 10, 'sets_per_session': 5, 'status': 'ok', 
                         'volume_class': 'medium', 'total_reps': 80, 'total_volume': 4000}
            },
            'Pull': {
                'Back': {'weekly_sets': 12, 'sets_per_session': 6, 'status': 'ok',
                        'volume_class': 'medium', 'total_reps': 96, 'total_volume': 4800}
            }
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        data = assert_success_payload(response.get_json())
        assert len(data['session_summary']) == 2
        routines = [item['routine'] for item in data['session_summary']]
        assert 'Push' in routines
        assert 'Pull' in routines

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_legacy_total_sets_alias(self, mock_calc, mock_cats, mock_iso, client):
        """total_sets should be alias for weekly_sets."""
        mock_calc.return_value = {
            'Push': {
                'Chest': {'weekly_sets': 15, 'sets_per_session': 5, 'status': 'ok',
                         'volume_class': 'medium', 'total_reps': 120, 'total_volume': 5000}
            }
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        data = assert_success_payload(response.get_json())
        item = data['session_summary'][0]
        assert item['total_sets'] == item['weekly_sets']

    @patch('routes.session_summary.calculate_isolated_muscles_stats')
    @patch('routes.session_summary.calculate_exercise_categories')
    @patch('routes.session_summary.calculate_session_summary')
    def test_effective_sets_fallback(self, mock_calc, mock_cats, mock_iso, client):
        """effective_sets should fallback to weekly_sets if not present."""
        mock_calc.return_value = {
            'Push': {
                'Chest': {'weekly_sets': 15, 'sets_per_session': 5, 'status': 'ok',
                         'volume_class': 'medium', 'total_reps': 120, 'total_volume': 5000}
                # No effective_sets key
            }
        }
        mock_cats.return_value = []
        mock_iso.return_value = {}

        response = client.get(
            '/session_summary',
            headers={'Accept': 'application/json'}
        )
        
        data = assert_success_payload(response.get_json())
        item = data['session_summary'][0]
        assert item['effective_sets'] == 15  # Fallback to weekly_sets
