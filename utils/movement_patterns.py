"""
Movement Pattern Framework for Auto Starter Plan Generator.

This module defines the taxonomy of movement patterns used for generating
workout plans based on biomechanical categories rather than just muscle groups.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class MovementPattern(str, Enum):
    """Primary movement patterns."""
    # Lower body patterns
    SQUAT = "squat"
    HINGE = "hinge"
    
    # Upper body patterns
    HORIZONTAL_PUSH = "horizontal_push"
    VERTICAL_PUSH = "vertical_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PULL = "vertical_pull"
    
    # Core patterns
    CORE_STATIC = "core_static"
    CORE_DYNAMIC = "core_dynamic"
    
    # Isolation patterns (accessory work)
    UPPER_ISOLATION = "upper_isolation"
    LOWER_ISOLATION = "lower_isolation"


class MovementSubpattern(str, Enum):
    """Sub-patterns for more specific exercise classification."""
    # Squat variants
    BILATERAL_SQUAT = "bilateral_squat"
    UNILATERAL_SQUAT = "unilateral_squat"
    
    # Hinge variants
    HIP_THRUST = "hip_thrust"
    DEADLIFT = "deadlift"
    GOODMORNING = "goodmorning"
    
    # Push variants
    PRESS = "press"
    FLY = "fly"
    DIP = "dip"
    
    # Pull variants
    ROW = "row"
    PULLDOWN = "pulldown"
    PULLUP = "pullup"
    FACE_PULL = "face_pull"
    
    # Core variants
    PLANK = "plank"
    HOLLOW = "hollow"
    PALLOF = "pallof"
    CARRY = "carry"
    LEG_RAISE = "leg_raise"
    CRUNCH = "crunch"
    ROTATION = "rotation"
    
    # Upper isolation variants
    BICEP_CURL = "bicep_curl"
    TRICEP_EXTENSION = "tricep_extension"
    LATERAL_RAISE = "lateral_raise"
    REAR_DELT = "rear_delt"
    
    # Lower isolation variants
    LEG_CURL = "leg_curl"
    LEG_EXTENSION = "leg_extension"
    HIP_ABDUCTION = "hip_abduction"
    HIP_ADDUCTION = "hip_adduction"
    CALF_RAISE = "calf_raise"


@dataclass
class PatternMapping:
    """Mapping rules for classifying exercises into movement patterns."""
    
    # Keywords in exercise names that indicate patterns
    # Maps: keyword -> (pattern, optional subpattern)
    NAME_KEYWORDS: Dict[str, Tuple[MovementPattern, Optional[MovementSubpattern]]] = field(
        default_factory=lambda: {
            # Squat patterns
            "squat": (MovementPattern.SQUAT, MovementSubpattern.BILATERAL_SQUAT),
            "leg press": (MovementPattern.SQUAT, MovementSubpattern.BILATERAL_SQUAT),
            "hack squat": (MovementPattern.SQUAT, MovementSubpattern.BILATERAL_SQUAT),
            "split squat": (MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            "bulgarian": (MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            "lunge": (MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            "step up": (MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            "step-up": (MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            
            # Hinge patterns
            "hip thrust": (MovementPattern.HINGE, MovementSubpattern.HIP_THRUST),
            "glute bridge": (MovementPattern.HINGE, MovementSubpattern.HIP_THRUST),
            "deadlift": (MovementPattern.HINGE, MovementSubpattern.DEADLIFT),
            "rdl": (MovementPattern.HINGE, MovementSubpattern.DEADLIFT),
            "romanian": (MovementPattern.HINGE, MovementSubpattern.DEADLIFT),
            "good morning": (MovementPattern.HINGE, MovementSubpattern.GOODMORNING),
            "goodmorning": (MovementPattern.HINGE, MovementSubpattern.GOODMORNING),
            "back extension": (MovementPattern.HINGE, MovementSubpattern.GOODMORNING),
            "hyperextension": (MovementPattern.HINGE, MovementSubpattern.GOODMORNING),
            "roman chair": (MovementPattern.HINGE, MovementSubpattern.GOODMORNING),
            
            # Horizontal push
            "bench press": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.PRESS),
            "chest press": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.PRESS),
            "push up": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.PRESS),
            "push-up": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.PRESS),
            "pushup": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.PRESS),
            "pec fly": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.FLY),
            "chest fly": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.FLY),
            "fly": (MovementPattern.HORIZONTAL_PUSH, MovementSubpattern.FLY),
            
            # Vertical push
            "overhead press": (MovementPattern.VERTICAL_PUSH, MovementSubpattern.PRESS),
            "shoulder press": (MovementPattern.VERTICAL_PUSH, MovementSubpattern.PRESS),
            "military press": (MovementPattern.VERTICAL_PUSH, MovementSubpattern.PRESS),
            "dip": (MovementPattern.VERTICAL_PUSH, MovementSubpattern.DIP),
            "arnold press": (MovementPattern.VERTICAL_PUSH, MovementSubpattern.PRESS),
            
            # Horizontal pull
            "row": (MovementPattern.HORIZONTAL_PULL, MovementSubpattern.ROW),
            "face pull": (MovementPattern.HORIZONTAL_PULL, MovementSubpattern.FACE_PULL),
            "facepull": (MovementPattern.HORIZONTAL_PULL, MovementSubpattern.FACE_PULL),
            "seal row": (MovementPattern.HORIZONTAL_PULL, MovementSubpattern.ROW),
            "bent over": (MovementPattern.HORIZONTAL_PULL, MovementSubpattern.ROW),
            
            # Vertical pull
            "pull up": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLUP),
            "pull-up": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLUP),
            "pullup": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLUP),
            "chin up": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLUP),
            "chin-up": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLUP),
            "chinup": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLUP),
            "lat pulldown": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLDOWN),
            "pulldown": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLDOWN),
            "pull down": (MovementPattern.VERTICAL_PULL, MovementSubpattern.PULLDOWN),
            
            # Core static
            "plank": (MovementPattern.CORE_STATIC, MovementSubpattern.PLANK),
            "hollow": (MovementPattern.CORE_STATIC, MovementSubpattern.HOLLOW),
            "pallof": (MovementPattern.CORE_STATIC, MovementSubpattern.PALLOF),
            "carry": (MovementPattern.CORE_STATIC, MovementSubpattern.CARRY),
            "farmer": (MovementPattern.CORE_STATIC, MovementSubpattern.CARRY),
            "suitcase": (MovementPattern.CORE_STATIC, MovementSubpattern.CARRY),
            "dead bug": (MovementPattern.CORE_STATIC, MovementSubpattern.HOLLOW),
            
            # Core dynamic
            "leg raise": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.LEG_RAISE),
            "hanging": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.LEG_RAISE),
            "sit up": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.CRUNCH),
            "sit-up": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.CRUNCH),
            "crunch": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.CRUNCH),
            "rotation": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.ROTATION),
            "woodchop": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.ROTATION),
            "wood chop": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.ROTATION),
            "russian twist": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.ROTATION),
            "bicycle": (MovementPattern.CORE_DYNAMIC, MovementSubpattern.ROTATION),
            
            # Upper isolation
            "curl": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.BICEP_CURL),
            "bicep": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.BICEP_CURL),
            "tricep extension": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.TRICEP_EXTENSION),
            "skull crusher": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.TRICEP_EXTENSION),
            "skullcrusher": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.TRICEP_EXTENSION),
            "pushdown": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.TRICEP_EXTENSION),
            "tricep pushdown": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.TRICEP_EXTENSION),
            "kickback": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.TRICEP_EXTENSION),
            "lateral raise": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.LATERAL_RAISE),
            "side raise": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.LATERAL_RAISE),
            "rear delt": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.REAR_DELT),
            "reverse fly": (MovementPattern.UPPER_ISOLATION, MovementSubpattern.REAR_DELT),
            
            # Lower isolation
            "leg curl": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.LEG_CURL),
            "hamstring curl": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.LEG_CURL),
            "leg extension": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.LEG_EXTENSION),
            "quad extension": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.LEG_EXTENSION),
            "hip abduction": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.HIP_ABDUCTION),
            "abduction": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.HIP_ABDUCTION),
            "hip adduction": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.HIP_ADDUCTION),
            "adduction": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.HIP_ADDUCTION),
            "calf raise": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.CALF_RAISE),
            "calf press": (MovementPattern.LOWER_ISOLATION, MovementSubpattern.CALF_RAISE),
        }
    )
    
    # Muscle group -> pattern mapping (fallback when name doesn't match)
    MUSCLE_GROUP_PATTERNS: Dict[str, MovementPattern] = field(
        default_factory=lambda: {
            # Lower body
            "Quadriceps": MovementPattern.SQUAT,
            "Gluteus Maximus": MovementPattern.HINGE,
            "Hamstrings": MovementPattern.HINGE,
            "Hip-Adductors": MovementPattern.LOWER_ISOLATION,
            "Calves": MovementPattern.LOWER_ISOLATION,
            
            # Upper body push
            "Chest": MovementPattern.HORIZONTAL_PUSH,
            "Front-Shoulder": MovementPattern.VERTICAL_PUSH,
            "Middle-Shoulder": MovementPattern.VERTICAL_PUSH,
            "Triceps": MovementPattern.UPPER_ISOLATION,
            
            # Upper body pull
            "Latissimus Dorsi": MovementPattern.VERTICAL_PULL,
            "Upper Back": MovementPattern.HORIZONTAL_PULL,
            "Middle-Traps": MovementPattern.HORIZONTAL_PULL,
            "Rear-Shoulder": MovementPattern.HORIZONTAL_PULL,
            "Trapezius": MovementPattern.HORIZONTAL_PULL,
            "Upper Traps": MovementPattern.VERTICAL_PULL,
            "Biceps": MovementPattern.UPPER_ISOLATION,
            "Forearms": MovementPattern.UPPER_ISOLATION,
            
            # Core
            "Rectus Abdominis": MovementPattern.CORE_DYNAMIC,
            "Abs/Core": MovementPattern.CORE_DYNAMIC,
            "External Obliques": MovementPattern.CORE_DYNAMIC,
            "Lower Back": MovementPattern.HINGE,
            
            # Others
            "Neck": MovementPattern.UPPER_ISOLATION,
        }
    )


# Equipment available in different environments
ENVIRONMENT_EQUIPMENT: Dict[str, Set[str]] = {
    "gym": {
        "Barbell", "Dumbbells", "Cables", "Machine", "Kettlebells",
        "Smith_Machine", "Trapbar", "Plate", "Band", "Bodyweight",
        "Trx", "Bosu_Ball", "Medicine_Ball", "Vitruvian"
    },
    "home": {
        "Bodyweight", "Dumbbells", "Band", "Kettlebells",
        "Trx", "Medicine_Ball", "Bosu_Ball"
    },
}


@dataclass
class SlotDefinition:
    """Definition of an exercise slot in a session blueprint."""
    pattern: MovementPattern
    role: str  # "main" or "accessory"
    subpattern_preference: Optional[MovementSubpattern] = None
    alternative_patterns: Optional[List[MovementPattern]] = None


# Session blueprints for different training day configurations
SESSION_BLUEPRINTS: Dict[int, Dict[str, List[SlotDefinition]]] = {
    # 1 day per week: single full-body
    1: {
        "A": [
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.DEADLIFT),
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.CORE_DYNAMIC, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory"),
        ],
    },
    # 2 days per week: A/B split
    2: {
        "A": [
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.DEADLIFT),
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.CORE_STATIC, "accessory"),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_CURL),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.BICEP_CURL),
        ],
        "B": [
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.HIP_THRUST),
            SlotDefinition(MovementPattern.CORE_DYNAMIC, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.TRICEP_EXTENSION),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.CALF_RAISE),
        ],
    },
    # 3 days per week: A/B/C with plane rotation
    3: {
        "A": [
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.DEADLIFT),
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.CORE_STATIC, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.BICEP_CURL),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_CURL),
        ],
        "B": [
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.HIP_THRUST),
            SlotDefinition(MovementPattern.CORE_DYNAMIC, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.TRICEP_EXTENSION),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_EXTENSION),
        ],
        "C": [
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.HIP_THRUST),
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),  # Or choose weaker plane
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.UNILATERAL_SQUAT),
            SlotDefinition(MovementPattern.CORE_DYNAMIC, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.LATERAL_RAISE),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.CALF_RAISE),
        ],
    },
    # 4 days per week: Upper/Lower split
    4: {
        "A": [  # Upper A - Horizontal focus
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PULL, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.BICEP_CURL),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.TRICEP_EXTENSION),
        ],
        "B": [  # Lower A - Quad focus
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.DEADLIFT),
            SlotDefinition(MovementPattern.SQUAT, "accessory", MovementSubpattern.UNILATERAL_SQUAT),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_EXTENSION),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.CALF_RAISE),
            SlotDefinition(MovementPattern.CORE_STATIC, "accessory"),
        ],
        "C": [  # Upper B - Vertical focus
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "accessory"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.LATERAL_RAISE),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.REAR_DELT),
        ],
        "D": [  # Lower B - Posterior chain focus
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.HIP_THRUST),
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.HINGE, "accessory", MovementSubpattern.GOODMORNING),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_CURL),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.CALF_RAISE),
            SlotDefinition(MovementPattern.CORE_DYNAMIC, "accessory"),
        ],
    },
    # 5 days per week: Push/Pull/Legs (PPL) + Upper/Lower
    5: {
        "A": [  # Push
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.TRICEP_EXTENSION),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.LATERAL_RAISE),
        ],
        "B": [  # Pull
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "accessory"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.BICEP_CURL),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.REAR_DELT),
        ],
        "C": [  # Legs
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.DEADLIFT),
            SlotDefinition(MovementPattern.SQUAT, "accessory", MovementSubpattern.UNILATERAL_SQUAT),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_CURL),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.CALF_RAISE),
            SlotDefinition(MovementPattern.CORE_STATIC, "accessory"),
        ],
        "D": [  # Upper
            SlotDefinition(MovementPattern.HORIZONTAL_PUSH, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PULL, "main"),
            SlotDefinition(MovementPattern.VERTICAL_PUSH, "accessory"),
            SlotDefinition(MovementPattern.HORIZONTAL_PULL, "main"),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.BICEP_CURL),
            SlotDefinition(MovementPattern.UPPER_ISOLATION, "accessory", MovementSubpattern.TRICEP_EXTENSION),
        ],
        "E": [  # Lower
            SlotDefinition(MovementPattern.HINGE, "main", MovementSubpattern.HIP_THRUST),
            SlotDefinition(MovementPattern.SQUAT, "main", MovementSubpattern.BILATERAL_SQUAT),
            SlotDefinition(MovementPattern.HINGE, "accessory", MovementSubpattern.GOODMORNING),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.LEG_EXTENSION),
            SlotDefinition(MovementPattern.LOWER_ISOLATION, "accessory", MovementSubpattern.CALF_RAISE),
            SlotDefinition(MovementPattern.CORE_DYNAMIC, "accessory"),
        ],
    },
}


@dataclass
class PrescriptionRules:
    """Default prescription rules for sets, reps, and intensity."""
    
    # Sets by role and experience level
    SETS_BY_ROLE: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: {
            "novice": {"main": 3, "accessory": 2},
            "intermediate": {"main": 3, "accessory": 2},  # Can go 3-4 for main
            "advanced": {"main": 3, "accessory": 2},  # Can scale down with volume_scale
        }
    )
    
    # Rep ranges by goal and role
    REP_RANGES: Dict[str, Dict[str, Tuple[int, int]]] = field(
        default_factory=lambda: {
            "hypertrophy": {
                "main": (6, 10),
                "core": (10, 20),
                "accessory": (10, 15),
            },
            "strength": {
                "main": (3, 6),
                "core": (8, 12),
                "accessory": (6, 10),
            },
            "general": {
                "main": (5, 8),
                "core": (10, 15),
                "accessory": (8, 12),
            },
        }
    )
    
    # RIR defaults by role
    RIR_DEFAULTS: Dict[str, int] = field(
        default_factory=lambda: {
            "main": 2,
            "accessory": 2,
            "core": 3,
        }
    )
    
    # RPE defaults (derived from RIR: RPE = 10 - RIR)
    RPE_DEFAULTS: Dict[str, float] = field(
        default_factory=lambda: {
            "main": 8.0,
            "accessory": 8.0,
            "core": 7.0,
        }
    )
    
    # Total sets per session constraints
    MIN_SETS_PER_SESSION: int = 15
    MAX_SETS_PER_SESSION: int = 24
def classify_exercise(
    exercise_name: str,
    primary_muscle: Optional[str] = None,
    mechanic: Optional[str] = None,
) -> Tuple[Optional[MovementPattern], Optional[MovementSubpattern]]:
    """
    Classify an exercise into its movement pattern and subpattern.
    
    Args:
        exercise_name: Name of the exercise
        primary_muscle: Primary muscle group targeted
        mechanic: Exercise mechanic (Compound/Isolated)
        
    Returns:
        Tuple of (MovementPattern, MovementSubpattern) or (None, None) if unclassified
    """
    mapping = PatternMapping()
    name_lower = exercise_name.lower()
    
    # Sort keywords by length (longest first) to ensure more specific patterns match first
    # e.g., "bulgarian split squat" should match "bulgarian" before "squat"
    # e.g., "leg curl" should match "leg curl" before "curl"
    sorted_keywords = sorted(mapping.NAME_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True)
    
    # First, try to match by exercise name keywords
    for keyword, (pattern, subpattern) in sorted_keywords:
        if keyword in name_lower:
            return pattern, subpattern
    
    # Fallback: classify by primary muscle group
    if primary_muscle:
        pattern = mapping.MUSCLE_GROUP_PATTERNS.get(primary_muscle)
        if pattern:
            return pattern, None
    
    return None, None

