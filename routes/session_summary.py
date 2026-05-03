from flask import Blueprint, render_template, request, jsonify
from utils.session_summary import calculate_session_summary
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats
)
from utils.volume_classifier import (
    get_volume_class,
    get_volume_label,
    get_volume_tooltip,
    get_category_tooltip,
    get_subcategory_tooltip
)
from utils.effective_sets import (
    CountingMode,
    ContributionMode,
    parse_counting_mode as shared_parse_counting_mode,
    parse_contribution_mode as shared_parse_contribution_mode,
)
from utils.fatigue_data import (
    compute_heaviest_session_fatigue,
    compute_session_fatigue_for_routine,
)
from utils.logger import get_logger
from utils.errors import error_response, is_xhr_request, success_response

session_summary_bp = Blueprint('session_summary', __name__)
logger = get_logger()


def _parse_counting_mode(value: str) -> CountingMode:
    """Compatibility wrapper around the shared counting-mode parser."""
    return shared_parse_counting_mode(value)


def _parse_contribution_mode(value: str) -> ContributionMode:
    """Compatibility wrapper around the shared contribution-mode parser."""
    return shared_parse_contribution_mode(value)


@session_summary_bp.route("/session_summary", methods=["GET"])
def session_summary():
    routine = request.args.get("routine")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    counting_mode_str = request.args.get("counting_mode", "effective")
    contribution_mode_str = request.args.get("contribution_mode", "total")
    
    time_window = (start_date, end_date) if (start_date or end_date) else None
    counting_mode = _parse_counting_mode(counting_mode_str)
    contribution_mode = _parse_contribution_mode(contribution_mode_str)
    
    try:
        summary_map = calculate_session_summary(
            routine=routine,
            time_window=time_window,
            counting_mode=counting_mode,
            contribution_mode=contribution_mode,
        )
        results = [
            {
                'routine': routine_name,
                'muscle_group': muscle,
                'weekly_sets': data['weekly_sets'],
                'effective_sets': data.get('effective_sets', data['weekly_sets']),
                'raw_sets': data.get('raw_sets', data['weekly_sets']),
                'sets_per_session': data['sets_per_session'],
                'effective_per_session': data.get('effective_per_session'),
                'status': data['status'],
                'volume_class': data['volume_class'],
                'total_sets': data['weekly_sets'],  # Legacy alias
                'total_reps': data['total_reps'],
                'total_volume': data['total_volume'],
                'raw_total_reps': data.get('raw_total_reps', data['total_reps']),
                'raw_total_volume': data.get('raw_total_volume', data['total_volume']),
                # Session state
                'session_count': data.get('session_count', 0),
                'has_logged_sessions': data.get('has_logged_sessions', False),
                # Volume warnings
                'warning_level': data.get('warning_level', 'no_data'),
                'is_borderline': data.get('is_borderline', False),
                'is_excessive': data.get('is_excessive', False),
                # Mode indicators
                'counting_mode': counting_mode.value,
                'contribution_mode': contribution_mode.value,
            }
            for routine_name, muscles in summary_map.items()
            for muscle, data in muscles.items()
        ]
        category_results = calculate_exercise_categories()
        isolated_muscles_stats = calculate_isolated_muscles_stats()

        # Fatigue badge (Phase 1, D3+D10): independent of counting_mode and
        # contribution_mode; reads planned user_selection rows directly.
        # BRAINSTORM §1 non-goal: the badge must never block the page, so
        # any failure here degrades to an empty-state badge.
        fatigue_score = 0.0
        fatigue_band = "light"
        try:
            if routine:
                fatigue_session = compute_session_fatigue_for_routine(routine)
                fatigue_period_label = f"Routine: {routine}"
            else:
                heaviest_routine, fatigue_session = compute_heaviest_session_fatigue()
                if heaviest_routine:
                    fatigue_period_label = f"Heaviest planned routine: {heaviest_routine}"
                else:
                    fatigue_period_label = "No planned routines"
            fatigue_score = fatigue_session.score
            fatigue_band = fatigue_session.band
        except Exception:
            logger.exception("Fatigue badge computation failed; falling back to empty state")
            fatigue_period_label = "Projected fatigue unavailable"

        if is_xhr_request():
            return jsonify(success_response(data={
                "session_summary": results,
                "categories": category_results,
                "isolated_muscles": isolated_muscles_stats,
                "modes": {
                    "counting_mode": counting_mode.value,
                    "contribution_mode": contribution_mode.value,
                }
            }))

        return render_template(
            "session_summary.html",
            session_summary=results,
            categories=category_results,
            isolated_muscles=isolated_muscles_stats,
            counting_mode=counting_mode.value,
            contribution_mode=contribution_mode.value,
            fatigue_score=fatigue_score,
            fatigue_band=fatigue_band,
            fatigue_period_label=fatigue_period_label,
            get_volume_class=get_volume_class,
            get_volume_label=get_volume_label,
            get_volume_tooltip=get_volume_tooltip,
            get_category_tooltip=get_category_tooltip,
            get_subcategory_tooltip=get_subcategory_tooltip
        )
    except Exception as e:
        logger.exception("Error in session_summary: %s", e)
        if is_xhr_request():
            return error_response("INTERNAL_ERROR", "Unable to fetch session summary", 500)
        return render_template("error.html", message="Unable to load session summary."), 500 
