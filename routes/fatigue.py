"""Fatigue Meter — Phase 2 dedicated route.

Renders `/fatigue`: the per-muscle breakdown page plus two SFR cards
(planned + logged) and the period selector. Server-rendered only — no
`/api/fatigue/*` per D2.7 (carry-forward of Phase 1 D9). The Phase 1
badge on `/session_summary` and `/weekly_summary` stays in place and
gains a link here (Chapter 2.8).
"""
from flask import Blueprint, render_template, request

from utils.errors import error_response, is_xhr_request
from utils.fatigue_data import build_fatigue_page_context
from utils.logger import get_logger

fatigue_bp = Blueprint('fatigue', __name__)
logger = get_logger()


@fatigue_bp.route('/fatigue', methods=['GET'])
def fatigue_page():
    period = request.args.get('period')
    try:
        context = build_fatigue_page_context(period)
    except Exception:
        logger.exception("Error building /fatigue context")
        if is_xhr_request(request):
            return error_response("INTERNAL_ERROR", "Failed to load fatigue page", 500)
        return render_template('error.html', error_message="Unable to load fatigue page"), 500
    return render_template('fatigue.html', **context)
