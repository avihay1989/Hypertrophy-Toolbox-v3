"""Utilities package.

Prefer importing concrete modules such as ``utils.db_initializer`` instead of
relying on package-level re-exports for new code.
"""

# Core imports
from .config import DB_FILE
from .database import DatabaseHandler
from .db_initializer import initialize_database

# Exercise management
from .exercise_manager import (
    get_exercises,
    add_exercise,
    delete_exercise,
    fetch_unique_values,
    save_exercise,
    remove_exercise_by_name,
)

# Summary calculations
from .weekly_summary import (
    calculate_weekly_summary,
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
)
from .session_summary import calculate_session_summary

# Volume and classification utilities
from .volume_classifier import (
    get_volume_class,
    get_volume_label,
    get_volume_tooltip,
    get_category_tooltip,
    get_subcategory_tooltip
)

# Workout log functionality
from .workout_log import (
    check_progression
)

# User selection handling
from .user_selection import get_user_selection

# Plan generator
from .plan_generator import generate_starter_plan

# Define public interface
__all__ = [
    # Core
    "DB_FILE",
    "DatabaseHandler",
    "initialize_database",
    
    # Exercise management
    "get_exercises",
    "add_exercise",
    "delete_exercise",
    "fetch_unique_values",
    "save_exercise",
    "remove_exercise_by_name",
    
    # Summary calculations
    "calculate_weekly_summary",
    "calculate_session_summary",
    "calculate_exercise_categories",
    "calculate_isolated_muscles_stats",
    
    # Volume and classification
    "get_volume_class",
    "get_volume_label",
    "get_volume_tooltip",
    "get_category_tooltip",
    "get_subcategory_tooltip",
    
    # Workout log
    "check_progression",
    
    # User selection
    "get_user_selection",
    
    # Plan generator
    "generate_starter_plan",
]
