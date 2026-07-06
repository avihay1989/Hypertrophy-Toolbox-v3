from flask import Blueprint, render_template, jsonify, request, send_file
from utils.errors import error_response, success_response
from utils.logger import get_logger
from utils.volume_export import export_volume_plan
from utils.volume_ai import generate_volume_suggestions
from utils.volume_progress import activate_volume_plan, deactivate_volume_plan
from utils.volume_taxonomy import BASIC_MUSCLE_GROUPS, ADVANCED_MUSCLE_GROUPS
from utils.volume_splitter_service import (
    get_muscle_list_for_mode,
    build_default_ranges,
    parse_requested_ranges,
    fetch_volume_history,
    fetch_volume_plan,
    delete_volume_plan_record,
    build_volume_excel,
)

# Business logic (history/get/delete queries, range defaults/sanitization, and
# Excel export assembly) lives in utils/volume_splitter_service.py (WP1.7).
# The range helpers are re-exported above so existing import paths such as
# `routes.volume_splitter.build_default_ranges` remain valid. `export_volume_plan`
# stays imported here because tests monkeypatch it on this module.
#
# Second classification vocabulary note (WP1.7): the volume-adequacy status
# labels 'low'/'optimal'/'high'/'excessive' emitted by calculate_volume below
# are a SEPARATE classification vocabulary from the canonical volume muscle
# taxonomy in utils/volume_taxonomy.py. Per WP1.7 this is documented, not
# consolidated. See utils/volume_splitter_service.py for the full note.

volume_splitter_bp = Blueprint('volume_splitter', __name__)
logger = get_logger()


@volume_splitter_bp.route('/volume_splitter')
def volume_splitter():
    requested_mode = (request.args.get('mode') or 'basic').lower()
    default_mode = 'advanced' if requested_mode == 'advanced' else 'basic'
    basic = BASIC_MUSCLE_GROUPS
    advanced = ADVANCED_MUSCLE_GROUPS
    return render_template(
        'volume_splitter.html',
        basic_muscle_groups=basic,
        advanced_muscle_groups=advanced,
        basic_recommended_ranges=build_default_ranges(basic),
        advanced_recommended_ranges=build_default_ranges(advanced),
        default_mode=default_mode
    )

@volume_splitter_bp.route('/api/calculate_volume', methods=['POST'])
def calculate_volume():
    try:
        data = request.get_json() or {}
        mode = (data.get('mode') or 'basic').lower()

        training_days = int(data.get('training_days', 3))
    except (TypeError, ValueError):
        training_days = 3
    except Exception as e:
        logger.exception('Error calculating volume: %s', e)
        return error_response('INTERNAL_ERROR', 'Failed to calculate volume', 500)

    try:
        training_days = max(training_days, 1)

        volumes = data.get('volumes', {}) or {}

        active_muscles = get_muscle_list_for_mode(mode)
        valid_muscles = set(active_muscles)
        requested_ranges = data.get('ranges') or {}
        ranges = parse_requested_ranges(requested_ranges, active_muscles)

        results = {}
        for muscle, weekly_sets in volumes.items():
            if muscle not in valid_muscles:
                continue

            try:
                weekly_sets_value = float(weekly_sets or 0)
            except (TypeError, ValueError):
                weekly_sets_value = 0.0

            sets_per_session = round(weekly_sets_value / training_days, 1)
            # Second classification vocabulary (see module note): 'optimal' /
            # 'low' / 'high' / 'excessive' volume-adequacy status.
            status = 'optimal'

            if weekly_sets_value < ranges[muscle]['min']:
                status = 'low'
            elif weekly_sets_value > ranges[muscle]['max']:
                status = 'high'

            if sets_per_session > 10:
                status = 'excessive'

            results[muscle] = {
                'weekly_sets': weekly_sets_value,
                'sets_per_session': sets_per_session,
                'status': status
            }

        suggestions = generate_volume_suggestions(training_days, results, mode=mode)

        return jsonify(success_response(data={
            'results': results,
            'suggestions': suggestions,
            'ranges': ranges
        }))
    except Exception as e:
        logger.exception('Error calculating volume: %s', e)
        return error_response('INTERNAL_ERROR', 'Failed to calculate volume', 500)

@volume_splitter_bp.route('/api/volume_history')
def get_volume_history():
    try:
        formatted_history = fetch_volume_history()
        return jsonify(success_response(data=formatted_history))
    except Exception as e:
        logger.exception('Error loading volume history: %s', e)
        return error_response('INTERNAL_ERROR', 'Failed to load volume history', 500)

@volume_splitter_bp.route('/api/save_volume_plan', methods=['POST'])
def save_volume_plan():
    try:
        data = request.get_json() or {}
        mode = data.get('mode') or 'basic'
        plan_id = export_volume_plan(data, mode=mode)

        if plan_id:
            activated = False
            if data.get('activate'):
                activated = activate_volume_plan(plan_id)
                if not activated:
                    return error_response('INTERNAL_ERROR', 'Failed to activate saved plan', 500)

            return jsonify(success_response(
                data={'plan_id': plan_id, 'activated': activated},
                message=(
                    'Volume plan saved and activated successfully'
                    if activated
                    else 'Volume plan saved successfully'
                )
            ))
        return error_response('INTERNAL_ERROR', 'Failed to save plan', 500)
    except Exception as e:
        logger.exception('Error saving volume plan: %s', e)
        return error_response('INTERNAL_ERROR', 'Failed to save plan', 500)

@volume_splitter_bp.route('/api/volume_plan/<int:plan_id>')
def get_volume_plan(plan_id):
    try:
        plan = fetch_volume_plan(plan_id)
        if plan is None:
            return error_response('NOT_FOUND', 'Plan not found', 404)
        return jsonify(success_response(data=plan))
    except Exception as e:
        logger.exception('Error loading volume plan %s: %s', plan_id, e)
        return error_response('INTERNAL_ERROR', 'Failed to load volume plan', 500)


@volume_splitter_bp.route('/api/volume_plan/<int:plan_id>/activate', methods=['POST'])
def activate_saved_volume_plan(plan_id):
    try:
        if not activate_volume_plan(plan_id):
            return error_response('PLAN_NOT_FOUND', 'Plan not found', 404)
        return jsonify(success_response(message='Volume plan activated successfully'))
    except Exception as e:
        logger.exception('Error activating volume plan %s: %s', plan_id, e)
        return error_response('INTERNAL_ERROR', 'Failed to activate plan', 500)


@volume_splitter_bp.route('/api/volume_plan/<int:plan_id>/deactivate', methods=['POST'])
def deactivate_saved_volume_plan(plan_id):
    try:
        if not deactivate_volume_plan(plan_id):
            return error_response('PLAN_NOT_FOUND', 'Plan not found', 404)
        return jsonify(success_response(message='Volume plan deactivated successfully'))
    except Exception as e:
        logger.exception('Error deactivating volume plan %s: %s', plan_id, e)
        return error_response('INTERNAL_ERROR', 'Failed to deactivate plan', 500)

@volume_splitter_bp.route('/api/volume_plan/<int:plan_id>', methods=['DELETE'])
def delete_volume_plan(plan_id):
    try:
        if not delete_volume_plan_record(plan_id):
            return error_response('NOT_FOUND', 'Plan not found', 404)
        return jsonify(success_response(message='Volume plan deleted successfully'))
    except Exception as e:
        logger.exception('Error deleting volume plan %s: %s', plan_id, e)
        return error_response('INTERNAL_ERROR', 'Failed to delete volume plan', 500)

@volume_splitter_bp.route('/api/export_volume_excel', methods=['POST'])
def export_volume_excel():
    data = request.get_json() or {}
    excel_file, download_name = build_volume_excel(data)
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=download_name
    )
