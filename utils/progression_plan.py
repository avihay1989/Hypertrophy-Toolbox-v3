from .database import DatabaseHandler
from datetime import datetime
from typing import List, Dict, Any, Optional


def get_exercise_history(exercise: str) -> List[Dict[str, Any]]:
    """Get the exercise history from workout log."""
    query = """
    SELECT *
    FROM workout_log
    WHERE exercise = ?
    ORDER BY created_at DESC
    LIMIT 10
    """
    
    with DatabaseHandler() as db:
        return db.fetch_all(query, (exercise,))


def _calculate_weight_increment(current_weight: float, is_novice: bool = True) -> float:
    """
    Calculate appropriate weight increment based on double progression rules.
    
    Rules:
    - Under 20kg: +2.5kg
    - 20kg and above: +5kg
    - Novices get smaller increments for safety
    """
    if current_weight < 20:
        return 2.5 if not is_novice else 2.5
    else:
        return 5.0 if not is_novice else 2.5


def _check_acceptable_effort(scored_rir: Optional[int], scored_rpe: Optional[float]) -> bool:
    """
    Check if effort was acceptable for progression (not too easy, not grinding).
    
    Acceptable effort:
    - RIR 1-3 (close to failure but not grinding)
    - RPE 7-9 (challenging but not max)
    """
    if scored_rir is not None:
        return 1 <= scored_rir <= 3
    if scored_rpe is not None:
        return 7.0 <= scored_rpe <= 9.0
    # If no effort data, assume acceptable
    return True


def _get_progression_status(
    scored_max_reps: Optional[int],
    planned_min_reps: Optional[int],
    planned_max_reps: Optional[int],
    scored_rir: Optional[int] = None,
    scored_rpe: Optional[float] = None
) -> str:
    """
    Determine double progression status.
    
    Returns:
    - "increase_weight": Hit top of range with good effort
    - "increase_reps": Below minimum range  
    - "maintain": Within range, continue current load
    - "reduce_weight": Consistently below range (needs history analysis)
    """
    if scored_max_reps is None or planned_max_reps is None or planned_min_reps is None:
        return "maintain"
    
    acceptable_effort = _check_acceptable_effort(scored_rir, scored_rpe)
    
    if scored_max_reps >= planned_max_reps and acceptable_effort:
        return "increase_weight"
    elif scored_max_reps < planned_min_reps:
        return "increase_reps"
    else:
        return "maintain"


def _analyze_consistency(history: List[Dict[str, Any]], min_sessions: int = 2) -> Dict[str, Any]:
    """
    Analyze training consistency for smarter suggestions.
    
    Returns dict with:
    - consecutive_at_top: sessions in a row hitting top of rep range
    - consecutive_below_min: sessions in a row below min rep range
    - avg_reps: average scored_max_reps across history
    """
    if len(history) < min_sessions:
        return {"consecutive_at_top": 0, "consecutive_below_min": 0, "avg_reps": None}
    
    consecutive_at_top = 0
    consecutive_below_min = 0
    total_reps = 0
    valid_reps_count = 0
    
    for session in history:
        scored = session.get("scored_max_reps")
        planned_max = session.get("planned_max_reps")
        planned_min = session.get("planned_min_reps")
        
        if scored is not None:
            total_reps += scored
            valid_reps_count += 1
            
            if planned_max and scored >= planned_max:
                consecutive_at_top += 1
            else:
                break  # Stop counting consecutive
                
    # Reset and count below min
    for session in history:
        scored = session.get("scored_max_reps")
        planned_min = session.get("planned_min_reps")
        
        if scored is not None and planned_min is not None:
            if scored < planned_min:
                consecutive_below_min += 1
            else:
                break
    
    return {
        "consecutive_at_top": consecutive_at_top,
        "consecutive_below_min": consecutive_below_min,
        "avg_reps": total_reps / valid_reps_count if valid_reps_count > 0 else None
    }


def _build_primary_weight_suggestion(scored_weight, planned_min_reps, planned_max_reps, exercise, consistency, is_novice) -> Optional[Dict[str, Any]]:
    if scored_weight is None:
        return None
    weight_increment = _calculate_weight_increment(scored_weight, is_novice)
    new_weight = scored_weight + weight_increment
    if consistency.get("consecutive_at_top", 0) >= 2:
        confidence = "consistently"
        priority = "high"
    else:
        confidence = ""
        priority = "medium"
    
    return {
        "type": "double_progression_weight",
        "title": "Increase Weight (Double Progression)",
        "description": (
            f"You've {confidence} hit the top of your rep range ({planned_max_reps} reps) "
            f"on {exercise}. Increase weight from {scored_weight}kg to {new_weight}kg "
            f"and work back up through the rep range ({planned_min_reps}-{planned_max_reps})."
        ),
        "action": f"Next session: {new_weight}kg × {planned_min_reps}-{planned_max_reps} reps",
        "priority": priority,
        "suggested_weight": new_weight,
        "current_value": scored_weight,
        "suggested_value": new_weight
    }


def _build_primary_rep_suggestion(scored_weight, scored_max_reps, planned_min_reps, planned_max_reps, exercise, consistency, is_novice) -> Optional[Dict[str, Any]]:
    if consistency.get("consecutive_below_min", 0) >= 2:
        if scored_weight and scored_weight > 5:
            reduced_weight = scored_weight - _calculate_weight_increment(scored_weight, is_novice)
            return {
                "type": "reduce_weight",
                "title": "Reduce Weight",
                "description": (
                    f"You've been below the minimum rep range ({planned_min_reps} reps) "
                    f"for {consistency.get('consecutive_below_min')} sessions. Consider reducing "
                    f"weight from {scored_weight}kg to {reduced_weight}kg to get reps back in range."
                ),
                "action": f"Try {reduced_weight}kg and aim for {planned_min_reps}-{planned_max_reps} reps",
                "priority": "high",
                "suggested_weight": reduced_weight,
                "current_value": scored_weight,
                "suggested_value": reduced_weight
            }
    
    return {
        "type": "double_progression_reps",
        "title": "Push Reps Into Range",
        "description": (
            f"Your reps ({scored_max_reps}) are below the target range "
            f"({planned_min_reps}-{planned_max_reps}) on {exercise}. "
            f"Keep the weight at {scored_weight}kg and focus on adding reps."
        ),
        "action": f"Target: {scored_weight}kg × {planned_min_reps}+ reps",
        "priority": "high",
        "current_value": scored_max_reps,
        "suggested_value": planned_min_reps
    }


def _build_maintenance_suggestion(scored_weight, scored_max_reps, planned_min_reps, planned_max_reps, exercise) -> Optional[Dict[str, Any]]:
    if scored_max_reps and planned_min_reps and planned_max_reps:
        reps_to_top = planned_max_reps - scored_max_reps
        if reps_to_top > 0:
            return {
                "type": "maintain_progress",
                "title": "Continue Current Load",
                "description": (
                    f"You're within your rep range on {exercise}. "
                    f"Add {reps_to_top} more rep(s) to hit the top of the range "
                    f"before increasing weight."
                ),
                "action": f"Target: {scored_weight}kg × {planned_max_reps} reps",
                "priority": "medium",
                "current_value": scored_max_reps,
                "suggested_value": planned_max_reps
            }
    return None


def _build_technique_and_volume_suggestions(exercise, planned_sets, status, consistency) -> List[Dict[str, Any]]:
    suggestions = [{
        "type": "technique",
        "title": "Technique Improvement",
        "description": f"Focus on improving your {exercise} form and mobility for better results.",
        "action": "Set a goal date for mastering proper technique",
        "priority": "low"
    }]
    
    if planned_sets and status == "maintain" and consistency.get("consecutive_at_top", 0) == 0:
        suggestions.append({
            "type": "sets",
            "title": "Add Volume",
            "description": (
                f"If you're comfortable at {planned_sets} sets, consider adding one more set "
                f"for increased volume on {exercise}."
            ),
            "action": f"Progress to {planned_sets + 1} sets when ready",
            "priority": "low",
            "current_value": planned_sets,
            "suggested_value": planned_sets + 1
        })
    return suggestions


def _build_manual_progression_options(exercise, current_weight, current_reps, planned_sets, is_novice) -> List[Dict[str, Any]]:
    options = []
    
    if current_weight is not None:
        weight_increment = _calculate_weight_increment(current_weight, is_novice)
        new_weight = current_weight + weight_increment
        weight_description = f"Increase the weight for {exercise} from {current_weight}kg to {new_weight}kg."
        weight_action = f"Set weight goal: {new_weight}kg"
    else:
        new_weight = None
        weight_description = f"Set a weight goal for {exercise}."
        weight_action = "Set weight goal"
    
    options.append({
        "type": "weight",
        "title": "Increase Weight",
        "description": weight_description,
        "action": weight_action,
        "priority": "medium",
        "suggested_weight": new_weight,
        "current_value": current_weight,
        "suggested_value": new_weight
    })
    
    if current_reps is not None:
        target_reps = current_reps + 2
        reps_description = f"Increase your reps for {exercise} from {current_reps} to {target_reps} reps."
        reps_action = f"Set reps goal: {target_reps} reps"
    else:
        target_reps = None
        reps_description = f"Set a repetition goal for {exercise}."
        reps_action = "Set reps goal"
    
    options.append({
        "type": "reps",
        "title": "Increase Repetitions",
        "description": reps_description,
        "action": reps_action,
        "priority": "medium",
        "current_value": current_reps,
        "suggested_value": target_reps
    })
    
    if planned_sets is not None:
        sets_description = (
            f"Add an extra set to {exercise}. Currently doing {planned_sets} sets, "
            f"progress to {planned_sets + 1} sets."
        )
        sets_action = f"Set volume goal: {planned_sets + 1} sets"
    else:
        sets_description = f"Set a volume goal for {exercise}."
        sets_action = "Set volume goal"
    
    options.append({
        "type": "sets",
        "title": "Add Another Set",
        "description": sets_description,
        "action": sets_action,
        "priority": "medium",
        "current_value": planned_sets,
        "suggested_value": planned_sets + 1 if planned_sets else None
    })
    
    return options


def generate_progression_suggestions(
    history: List[Dict[str, Any]], 
    is_novice: bool = True
) -> List[Dict[str, Any]]:
    """
    Generate progression suggestions using double progression methodology.
    
    Double Progression Rules:
    1. Train within a rep range (e.g., 8-12 reps)
    2. When you hit the TOP of the range with good technique → increase weight
    3. When below MINIMUM of range → keep weight, focus on reps
    4. When in range → continue current load
    
    Args:
        history: List of workout_log records, most recent first
        is_novice: If True, use more conservative increments
        
    Returns:
        List of suggestion dictionaries with type, title, description, action, priority
    """
    if not history:
        return []
    
    latest = history[0]
    exercise = latest.get("exercise", "this exercise")
    suggestions = []
    
    scored_max_reps = latest.get("scored_max_reps")
    scored_weight = latest.get("scored_weight")
    planned_min_reps = latest.get("planned_min_reps")
    planned_max_reps = latest.get("planned_max_reps")
    planned_weight = latest.get("planned_weight")
    planned_sets = latest.get("planned_sets")
    scored_rir = latest.get("scored_rir")
    scored_rpe = latest.get("scored_rpe")
    
    current_weight = scored_weight if scored_weight is not None else planned_weight
    current_reps = scored_max_reps if scored_max_reps is not None else planned_max_reps
    
    consistency = _analyze_consistency(history)
    status = _get_progression_status(
        scored_max_reps, planned_min_reps, planned_max_reps, scored_rir, scored_rpe
    )
    
    if status == "increase_weight":
        suggestion = _build_primary_weight_suggestion(
            scored_weight, planned_min_reps, planned_max_reps, exercise, consistency, is_novice
        )
        if suggestion:
            suggestions.append(suggestion)
            
    elif status == "increase_reps":
        suggestion = _build_primary_rep_suggestion(
            scored_weight, scored_max_reps, planned_min_reps, planned_max_reps, exercise, consistency, is_novice
        )
        if suggestion:
            suggestions.append(suggestion)
            
    elif status == "maintain":
        suggestion = _build_maintenance_suggestion(
            scored_weight, scored_max_reps, planned_min_reps, planned_max_reps, exercise
        )
        if suggestion:
            suggestions.append(suggestion)
    
    suggestions.extend(_build_technique_and_volume_suggestions(
        exercise, planned_sets, status, consistency
    ))
    
    suggestions.extend(_build_manual_progression_options(
        exercise, current_weight, current_reps, planned_sets, is_novice
    ))
    
    return suggestions

def save_progression_goal(data: Dict[str, Any]) -> int:
    """Save a new progression goal to the database and return its id."""
    query = """
    INSERT INTO progression_goals (
        exercise,
        goal_type,
        current_value,
        target_value,
        goal_date,
        created_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    """
    
    params = (
        data['exercise'],
        data['goal_type'],
        data['current_value'],
        data['target_value'],
        data['goal_date'],
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    with DatabaseHandler() as db:
        db.execute_query(query, params)
        return db.cursor.lastrowid
