"""Contract tests for route-level renders of the shared error page."""

import pytest

import routes.body_composition as body_composition_route
import routes.fatigue as fatigue_route
import routes.program_backup as program_backup_route
import routes.progression_plan as progression_plan_route
import routes.session_summary as session_summary_route
import routes.user_profile as user_profile_route
import routes.weekly_summary as weekly_summary_route


def _raise(*_args, **_kwargs):
    raise RuntimeError("forced route failure")


@pytest.mark.parametrize(
    ("route_module", "failure_target", "url", "expected_message"),
    [
        (
            weekly_summary_route,
            "calculate_weekly_summary",
            "/weekly_summary",
            "Unable to load weekly summary.",
        ),
        (
            session_summary_route,
            "calculate_session_summary",
            "/session_summary",
            "Unable to load session summary.",
        ),
        (
            progression_plan_route,
            "DatabaseHandler",
            "/progression",
            "Unable to load progression plan.",
        ),
        (
            program_backup_route,
            "list_backups",
            "/backup",
            "Unable to load backup center.",
        ),
        (
            body_composition_route,
            "DatabaseHandler",
            "/body_composition",
            "Unable to load Body Composition.",
        ),
        (
            user_profile_route,
            "DatabaseHandler",
            "/user_profile",
            "Unable to load user profile.",
        ),
        (
            fatigue_route,
            "build_fatigue_page_context",
            "/fatigue",
            "Unable to load fatigue page",
        ),
    ],
)
def test_route_error_page_uses_shared_template_contract(
    client,
    monkeypatch,
    route_module,
    failure_target,
    url,
    expected_message,
):
    """Every route supplies the title, status code, and message expected by error.html."""
    monkeypatch.setattr(route_module, failure_target, _raise)

    response = client.get(url)

    assert response.status_code == 500
    assert b"<title>Server Error - Hypertrophy Toolbox</title>" in response.data
    assert b'<h1 class="error-status-code">500</h1>' in response.data
    assert b'<h2 class="error-title">Server Error</h2>' in response.data
    assert expected_message.encode() in response.data
