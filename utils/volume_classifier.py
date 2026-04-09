"""Volume classification utilities for both raw and effective sets."""

from utils.effective_sets import (
    get_weekly_volume_class as get_effective_volume_class,
    get_session_volume_warning,
    VolumeWarningLevel,
)


def get_volume_class(total_sets):
    """Return the CSS class for volume classification (raw sets based).
    
    This is the legacy classification based on raw set counts.
    For effective sets classification, use get_effective_volume_class.
    """
    if total_sets < 10:
        return "low-volume"
    elif total_sets < 20:
        return "medium-volume"
    elif total_sets < 30:
        return "high-volume"
    else:
        return "ultra-volume"


def get_volume_label(total_sets):
    """Return the text label for volume classification."""
    if total_sets < 10:
        return "Low Volume"
    elif total_sets < 20:
        return "Medium Volume"
    elif total_sets < 30:
        return "High Volume"
    else:
        return "Excessive Volume"


def get_effective_volume_label(effective_sets):
    """Return the text label for effective sets volume classification."""
    vol_class = get_effective_volume_class(effective_sets)
    labels = {
        'low': 'Low Volume',
        'medium': 'Medium Volume',
        'high': 'High Volume',
        'excessive': 'Excessive Volume',
    }
    return labels.get(vol_class, 'Low Volume')


def get_volume_tooltip(volume_label, total_sets):
    """Return tooltip text for volume classification."""
    ranges = {
        'Low Volume': 'Below 10 sets',
        'Medium Volume': '10-19 sets',
        'High Volume': '20-29 sets',
        'Excessive Volume': '30+ sets',
    }
    return f"{volume_label}: {ranges.get(volume_label, 'Unknown')} (Current: {total_sets:.1f} sets)"


def get_session_warning_tooltip(effective_per_session):
    """Return tooltip text for session volume warnings.
    
    Args:
        effective_per_session: Effective sets per session for a muscle.
        
    Returns:
        Tooltip describing the session volume status.
    """
    warning = get_session_volume_warning(effective_per_session)
    
    if warning == VolumeWarningLevel.OK:
        return f"Session volume OK ({effective_per_session:.1f} effective sets) - Within productive limits"
    elif warning == VolumeWarningLevel.BORDERLINE:
        return f"Session volume BORDERLINE ({effective_per_session:.1f} effective sets) - Approaching productive limits"
    else:
        return f"Session volume EXCESSIVE ({effective_per_session:.1f} effective sets) - May exceed productive stimulus"

def get_category_tooltip(category):
    tooltips = {
        'Mechanic': 'Classification based on joint involvement in the exercise',
        'Utility': 'Classification based on exercise role in training',
        'Force': 'Classification based on primary force direction'
    }
    return tooltips.get(category, '')

def get_subcategory_tooltip(category, subcategory):
    tooltips = {
        'Mechanic': {
            'Compound': 'Multi-joint exercises like squats and bench press',
            'Isolated': 'Single-joint exercises focusing on specific muscles'
        },
        'Utility': {
            'Auxiliary': 'Supportive exercises that complement main lifts',
            'Basic': 'Foundational exercises targeting major muscle groups'
        },
        'Force': {
            'Push': 'Exercises involving pushing motions away from body',
            'Pull': 'Exercises involving pulling motions toward body'
        }
    }
    return tooltips.get(category, {}).get(subcategory, '')
