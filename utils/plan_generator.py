"""
Auto Starter Plan Generator.

Generates workout plans based on movement patterns, user preferences,
and evidence-based programming principles.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.movement_patterns import (
    MovementPattern,
    MovementSubpattern,
    SlotDefinition,
    PrescriptionRules,
    SESSION_BLUEPRINTS,
    ENVIRONMENT_EQUIPMENT,
    classify_exercise,
)

logger = get_logger()


# Estimated starting weights (in kg) by movement pattern and experience level
# These provide reasonable initial values instead of N/A or 0
# Values are conservative to encourage proper form before adding weight
ESTIMATED_WEIGHTS: Dict[str, Dict[str, float]] = {
    # Lower body compound movements
    MovementPattern.SQUAT.value: {
        "novice": 40.0,      # Bar + 10kg plates
        "intermediate": 85.0,
        "advanced": 125.0,
    },
    MovementPattern.HINGE.value: {
        "novice": 50.0,      # Bar + 15kg plates
        "intermediate": 100.0,
        "advanced": 140.0,
    },
    # Upper body compound movements
    MovementPattern.HORIZONTAL_PUSH.value: {
        "novice": 40.0,      # Bar + 10kg plates
        "intermediate": 70.0,
        "advanced": 100.0,
    },
    MovementPattern.VERTICAL_PUSH.value: {
        "novice": 30.0,      # Bar + 5kg plates
        "intermediate": 50.0,
        "advanced": 70.0,
    },
    MovementPattern.HORIZONTAL_PULL.value: {
        "novice": 35.0,      # Cable or dumbbell rows
        "intermediate": 60.0,
        "advanced": 85.0,
    },
    MovementPattern.VERTICAL_PULL.value: {
        "novice": 35.0,      # Assisted or lat pulldown
        "intermediate": 65.0,
        "advanced": 90.0,
    },
    # Core movements (typically bodyweight + optional resistance)
    MovementPattern.CORE_STATIC.value: {
        "novice": 0.0,       # Bodyweight
        "intermediate": 0.0,
        "advanced": 10.0,    # Weighted plank
    },
    MovementPattern.CORE_DYNAMIC.value: {
        "novice": 0.0,       # Bodyweight
        "intermediate": 5.0,
        "advanced": 10.0,
    },
    # Isolation movements
    MovementPattern.UPPER_ISOLATION.value: {
        "novice": 7.5,       # Light dumbbells
        "intermediate": 12.5,
        "advanced": 17.5,
    },
    MovementPattern.LOWER_ISOLATION.value: {
        "novice": 20.0,      # Machine weight
        "intermediate": 35.0,
        "advanced": 55.0,
    },
}

# Mapping from muscle groups to relevant movement patterns and isolation subpatterns
# Used for priority muscle reallocation

# Subpattern-specific weight adjustments (multipliers)
# Some subpatterns use lighter/heavier weights than the pattern default
SUBPATTERN_WEIGHT_MULTIPLIERS: Dict[str, float] = {
    # Hinge subpatterns
    MovementSubpattern.HIP_THRUST.value: 1.2,     # Typically heavier than deadlifts for same level
    MovementSubpattern.DEADLIFT.value: 1.0,
    MovementSubpattern.GOODMORNING.value: 0.5,    # Lighter due to leverage
    # Push subpatterns
    MovementSubpattern.FLY.value: 0.4,            # Much lighter than presses
    MovementSubpattern.DIP.value: 0.0,            # Bodyweight base
    # Pull subpatterns
    MovementSubpattern.FACE_PULL.value: 0.4,      # Light cable work
    MovementSubpattern.PULLUP.value: 0.0,         # Bodyweight base
    # Upper isolation
    MovementSubpattern.BICEP_CURL.value: 1.0,
    MovementSubpattern.TRICEP_EXTENSION.value: 0.8,
    MovementSubpattern.LATERAL_RAISE.value: 0.6,  # Very light
    MovementSubpattern.REAR_DELT.value: 0.5,
    # Lower isolation
    MovementSubpattern.LEG_CURL.value: 0.8,
    MovementSubpattern.LEG_EXTENSION.value: 1.0,
    MovementSubpattern.CALF_RAISE.value: 1.5,     # Can handle more weight
    MovementSubpattern.HIP_ABDUCTION.value: 0.6,
    MovementSubpattern.HIP_ADDUCTION.value: 0.6,
}


MUSCLE_TO_PATTERNS: Dict[str, Dict[str, Any]] = {
    # Upper body muscles
    "chest": {
        "patterns": [MovementPattern.HORIZONTAL_PUSH],
        "isolation_subpatterns": [MovementSubpattern.FLY],
    },
    "biceps": {
        "patterns": [MovementPattern.HORIZONTAL_PULL, MovementPattern.VERTICAL_PULL],
        "isolation_subpatterns": [MovementSubpattern.BICEP_CURL],
    },
    "triceps": {
        "patterns": [MovementPattern.HORIZONTAL_PUSH, MovementPattern.VERTICAL_PUSH],
        "isolation_subpatterns": [MovementSubpattern.TRICEP_EXTENSION],
    },
    "front-shoulder": {
        "patterns": [MovementPattern.VERTICAL_PUSH, MovementPattern.HORIZONTAL_PUSH],
        "isolation_subpatterns": [],
    },
    "middle-shoulder": {
        "patterns": [MovementPattern.VERTICAL_PUSH],
        "isolation_subpatterns": [MovementSubpattern.LATERAL_RAISE],
    },
    "rear-shoulder": {
        "patterns": [MovementPattern.HORIZONTAL_PULL],
        "isolation_subpatterns": [MovementSubpattern.REAR_DELT, MovementSubpattern.FACE_PULL],
    },
    "latissimus dorsi": {
        "patterns": [MovementPattern.VERTICAL_PULL, MovementPattern.HORIZONTAL_PULL],
        "isolation_subpatterns": [],
    },
    "upper back": {
        "patterns": [MovementPattern.HORIZONTAL_PULL, MovementPattern.VERTICAL_PULL],
        "isolation_subpatterns": [MovementSubpattern.FACE_PULL],
    },
    "trapezius": {
        "patterns": [MovementPattern.HINGE],
        "isolation_subpatterns": [],
    },
    "middle-traps": {
        "patterns": [MovementPattern.HORIZONTAL_PULL],
        "isolation_subpatterns": [MovementSubpattern.FACE_PULL],
    },
    "upper traps": {
        "patterns": [MovementPattern.HINGE],
        "isolation_subpatterns": [],
    },
    # Lower body muscles
    "quadriceps": {
        "patterns": [MovementPattern.SQUAT],
        "isolation_subpatterns": [MovementSubpattern.LEG_EXTENSION],
    },
    "hamstrings": {
        "patterns": [MovementPattern.HINGE],
        "isolation_subpatterns": [MovementSubpattern.LEG_CURL],
    },
    "gluteus maximus": {
        "patterns": [MovementPattern.HINGE, MovementPattern.SQUAT],
        "isolation_subpatterns": [MovementSubpattern.HIP_THRUST],
    },
    "calves": {
        "patterns": [],
        "isolation_subpatterns": [MovementSubpattern.CALF_RAISE],
    },
    "hip-adductors": {
        "patterns": [MovementPattern.SQUAT],
        "isolation_subpatterns": [MovementSubpattern.HIP_ADDUCTION],
    },
    # Core muscles
    "abs/core": {
        "patterns": [MovementPattern.CORE_STATIC, MovementPattern.CORE_DYNAMIC],
        "isolation_subpatterns": [],
    },
    "rectus abdominis": {
        "patterns": [MovementPattern.CORE_DYNAMIC],
        "isolation_subpatterns": [MovementSubpattern.CRUNCH],
    },
    "external obliques": {
        "patterns": [MovementPattern.CORE_DYNAMIC],
        "isolation_subpatterns": [MovementSubpattern.ROTATION],
    },
    "lower back": {
        "patterns": [MovementPattern.HINGE],
        "isolation_subpatterns": [],
    },
    # Arm muscles
    "forearms": {
        "patterns": [MovementPattern.HORIZONTAL_PULL, MovementPattern.VERTICAL_PULL],
        "isolation_subpatterns": [],
    },
}


@dataclass
class GeneratorConfig:
    """Configuration for the plan generator."""
    
    # Required inputs
    training_days: int = 2  # 1-5
    environment: str = "gym"  # "gym" or "home"
    experience_level: str = "novice"  # "novice", "intermediate", "advanced"
    goal: str = "hypertrophy"  # "hypertrophy", "strength", "general"
    
    # Volume scaling (1.0 = normal, 0.8 = reduced for heavy lifters)
    volume_scale: float = 1.0
    
    # Optional constraints
    equipment_whitelist: Optional[List[str]] = None
    exclude_exercises: Optional[List[str]] = None
    preferred_exercises: Optional[Dict[str, List[str]]] = None  # pattern -> list of exercises
    movement_restrictions: Optional[Dict[str, bool]] = None  # e.g., {"no_overhead_press": True}
    target_muscle_groups: Optional[List[str]] = None  # Filter to specific muscle groups
    
    # Priority muscle reallocation
    priority_muscles: Optional[List[str]] = None  # Muscles to prioritize (get extra volume)
    
    # Phase 3: Time budget optimization
    time_budget_minutes: Optional[int] = None  # Target workout duration (e.g., 45, 60, 90)
    
    # Phase 3: Merge mode - keep existing + add missing patterns
    merge_mode: bool = False  # If True, keep existing exercises and only add missing patterns
    
    # Behavior flags
    beginner_consistency_mode: bool = True  # Keep same main lifts across sessions for novices
    persist: bool = True  # Insert into user_selection
    overwrite: bool = True  # Delete existing routines before inserting
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.training_days < 1 or self.training_days > 5:
            raise ValueError("training_days must be between 1 and 5")
        if self.environment not in ("gym", "home"):
            raise ValueError("environment must be 'gym' or 'home'")
        if self.experience_level not in ("novice", "intermediate", "advanced"):
            raise ValueError("experience_level must be 'novice', 'intermediate', or 'advanced'")
        if self.goal not in ("hypertrophy", "strength", "general"):
            raise ValueError("goal must be 'hypertrophy', 'strength', or 'general'")
        if self.volume_scale <= 0 or self.volume_scale > 2:
            raise ValueError("volume_scale must be between 0 and 2")
        
        # Validate time budget (Phase 3)
        if self.time_budget_minutes is not None:
            if not isinstance(self.time_budget_minutes, int) or self.time_budget_minutes < 15 or self.time_budget_minutes > 180:
                raise ValueError("time_budget_minutes must be between 15 and 180")
        
        # Merge mode cannot be used with overwrite=True
        if self.merge_mode and self.overwrite:
            logger.info("merge_mode=True implies overwrite=False, adjusting")
            self.overwrite = False
        
        # Validate priority muscles
        if self.priority_muscles:
            if not isinstance(self.priority_muscles, list):
                raise ValueError("priority_muscles must be a list")
            if len(self.priority_muscles) > 2:
                logger.warning(
                    "More than 2 priority muscles provided (%d). Using first 2.",
                    len(self.priority_muscles),
                )
                self.priority_muscles = self.priority_muscles[:2]
            
            # Normalize and validate muscle names
            valid_muscles = set(MUSCLE_TO_PATTERNS.keys())
            normalized = []
            for muscle in self.priority_muscles:
                muscle_lower = muscle.lower()
                if muscle_lower in valid_muscles:
                    normalized.append(muscle_lower)
                else:
                    # Try partial match
                    matches = [m for m in valid_muscles if muscle_lower in m or m in muscle_lower]
                    if matches:
                        normalized.append(matches[0])
                        logger.debug(
                            "Priority muscle '%s' matched to '%s'",
                            muscle,
                            matches[0],
                        )
                    else:
                        logger.warning(
                            "Priority muscle '%s' not recognized. Available: %s",
                            muscle,
                            ", ".join(sorted(valid_muscles)),
                        )
            
            self.priority_muscles = normalized if normalized else None


@dataclass
class ExerciseRow:
    """A single exercise entry in the generated plan."""
    routine: str
    exercise: str
    sets: int
    min_rep_range: int
    max_rep_range: int
    rir: int
    rpe: float
    weight: float
    exercise_order: int
    
    # Metadata (not persisted)
    pattern: Optional[str] = None
    role: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "routine": self.routine,
            "exercise": self.exercise,
            "sets": self.sets,
            "min_rep_range": self.min_rep_range,
            "max_rep_range": self.max_rep_range,
            "rir": self.rir,
            "rpe": self.rpe,
            "weight": self.weight,
            "exercise_order": self.exercise_order,
            "pattern": self.pattern,
            "role": self.role,
        }


@dataclass
class GeneratedPlan:
    """The complete generated workout plan."""
    routines: Dict[str, List[ExerciseRow]]
    config: GeneratorConfig
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "routines": {
                routine: [ex.to_dict() for ex in exercises]
                for routine, exercises in self.routines.items()
            },
            "config": {
                "training_days": self.config.training_days,
                "environment": self.config.environment,
                "experience_level": self.config.experience_level,
                "goal": self.config.goal,
                "volume_scale": self.config.volume_scale,
            },
        }
    
    @property
    def total_exercises(self) -> int:
        """Total number of exercises across all routines."""
        return sum(len(exercises) for exercises in self.routines.values())
    
    @property
    def total_sets_per_routine(self) -> Dict[str, int]:
        """Total sets per routine."""
        return {
            routine: sum(ex.sets for ex in exercises)
            for routine, exercises in self.routines.items()
        }


class ExerciseSelector:
    """Handles exercise selection based on patterns and constraints."""
    
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self._exercise_cache: Optional[List[Dict[str, Any]]] = None
        self._used_exercises: Set[str] = set()
    
    def _get_available_equipment(self) -> Set[str]:
        """Get equipment available based on environment and whitelist."""
        base_equipment = ENVIRONMENT_EQUIPMENT.get(self.config.environment, set())
        
        if self.config.equipment_whitelist:
            return base_equipment & set(self.config.equipment_whitelist)
        
        return base_equipment
    
    def _load_exercises(self) -> List[Dict[str, Any]]:
        """Load all exercises from database with their patterns."""
        if self._exercise_cache is not None:
            return self._exercise_cache
        
        query = """
            SELECT 
                exercise_name,
                primary_muscle_group,
                secondary_muscle_group,
                mechanic,
                utility,
                equipment,
                difficulty,
                movement_pattern,
                movement_subpattern
            FROM exercises
            WHERE exercise_name IS NOT NULL
            ORDER BY exercise_name
        """
        
        try:
            with DatabaseHandler() as db:
                results = db.fetch_all(query)
                self._exercise_cache = [dict(row) for row in results]
                return self._exercise_cache
        except Exception as e:
            logger.exception("Failed to load exercises from database")
            return []
    
    def _is_exercise_allowed(self, exercise: Dict[str, Any]) -> bool:
        """Check if an exercise passes all constraints."""
        exercise_name = exercise.get("exercise_name", "")
        
        # Check exclusion list
        if self.config.exclude_exercises:
            if exercise_name in self.config.exclude_exercises:
                return False
        
        # Check equipment constraints
        equipment = exercise.get("equipment")
        if equipment:
            available = self._get_available_equipment()
            if equipment not in available:
                return False
        
        # Check target muscle groups filter
        if self.config.target_muscle_groups:
            primary = (exercise.get("primary_muscle_group") or "").lower()
            secondary = (exercise.get("secondary_muscle_group") or "").lower()
            
            # Check if exercise targets any of the selected muscle groups
            target_lower = [m.lower() for m in self.config.target_muscle_groups]
            matches_target = any(
                target in primary or target in secondary or primary in target or secondary in target
                for target in target_lower
                if target and (primary or secondary)
            )
            
            if not matches_target and (primary or secondary):
                return False
        
        # Check difficulty level
        difficulty = (exercise.get("difficulty") or "").lower()
        level = self.config.experience_level
        
        difficulty_ranks = {"beginner": 1, "intermediate": 2, "advanced": 3}
        exercise_rank = difficulty_ranks.get(difficulty, 2)
        user_rank = difficulty_ranks.get(level, 1)
        
        # Novice can't do advanced exercises
        if level == "novice" and exercise_rank > 2:
            return False
        
        # Check movement restrictions
        if self.config.movement_restrictions:
            if self.config.movement_restrictions.get("no_overhead_press"):
                name_lower = exercise_name.lower()
                if any(kw in name_lower for kw in ["overhead", "military", "shoulder press"]):
                    return False
            
            if self.config.movement_restrictions.get("no_deadlift"):
                name_lower = exercise_name.lower()
                if "deadlift" in name_lower:
                    return False
        
        return True
    
    def _score_exercise(
        self,
        exercise: Dict[str, Any],
        slot: SlotDefinition,
        routine: str,
    ) -> float:
        """Score an exercise for a given slot. Higher is better."""
        score = 0.0
        exercise_name = exercise.get("exercise_name", "")
        
        # Check if exercise matches requested pattern
        stored_pattern = exercise.get("movement_pattern")
        if stored_pattern and stored_pattern == slot.pattern.value:
            score += 100
        else:
            # Try to classify on the fly
            pattern, subpattern = classify_exercise(
                exercise_name,
                exercise.get("primary_muscle_group"),
                exercise.get("mechanic"),
            )
            if pattern == slot.pattern:
                score += 100
            else:
                return -1000  # Pattern doesn't match
        
        # Subpattern preference bonus
        if slot.subpattern_preference:
            stored_subpattern = exercise.get("movement_subpattern")
            if stored_subpattern == slot.subpattern_preference.value:
                score += 30
            else:
                # Check by name keywords
                name_lower = exercise_name.lower()
                subpattern_keywords = {
                    MovementSubpattern.BILATERAL_SQUAT: ["squat", "leg press"],
                    MovementSubpattern.UNILATERAL_SQUAT: ["split", "lunge", "step"],
                    MovementSubpattern.HIP_THRUST: ["hip thrust", "bridge"],
                    MovementSubpattern.DEADLIFT: ["deadlift", "rdl", "romanian"],
                    MovementSubpattern.BICEP_CURL: ["curl", "bicep"],
                    MovementSubpattern.TRICEP_EXTENSION: ["extension", "pushdown", "skull"],
                    MovementSubpattern.LEG_CURL: ["leg curl", "hamstring"],
                    MovementSubpattern.LEG_EXTENSION: ["leg extension"],
                    MovementSubpattern.CALF_RAISE: ["calf"],
                    MovementSubpattern.LATERAL_RAISE: ["lateral", "side raise"],
                }
                keywords = subpattern_keywords.get(slot.subpattern_preference, [])
                if any(kw in name_lower for kw in keywords):
                    score += 20
        
        # Role-based scoring
        utility = (exercise.get("utility") or "").lower()
        mechanic = (exercise.get("mechanic") or "").lower()
        
        if slot.role == "main":
            # Prefer Basic utility for main lifts
            if utility == "basic":
                score += 20
            # Prefer Compound exercises for main lifts
            if mechanic == "compound":
                score += 15
        else:  # accessory
            # Auxiliary is fine for accessories
            if utility in ("auxiliary", "basic"):
                score += 10
            # Isolated exercises are good for isolation slots
            if slot.pattern in (MovementPattern.UPPER_ISOLATION, MovementPattern.LOWER_ISOLATION):
                if mechanic in ("isolated", "isolation"):
                    score += 15
        
        # Preferred exercises get a big boost
        if self.config.preferred_exercises:
            pattern_prefs = self.config.preferred_exercises.get(slot.pattern.value, [])
            if exercise_name in pattern_prefs:
                score += 50
        
        # Penalize already-used exercises (unless beginner consistency mode)
        if exercise_name in self._used_exercises:
            if self.config.beginner_consistency_mode and self.config.experience_level == "novice":
                # For novices, only penalize accessories, not main lifts
                if slot.role == "main":
                    score += 5  # Actually prefer consistency for main lifts
                else:
                    score -= 30
            else:
                score -= 40  # Variety is preferred for non-novices
        
        # Small random factor to break ties
        score += random.uniform(0, 5)
        
        return score
    
    def select_exercise(self, slot: SlotDefinition, routine: str) -> Optional[Dict[str, Any]]:
        """Select the best exercise for a given slot."""
        exercises = self._load_exercises()
        
        candidates = []
        for exercise in exercises:
            if not self._is_exercise_allowed(exercise):
                continue
            
            score = self._score_exercise(exercise, slot, routine)
            if score > -1000:  # Pattern matched
                candidates.append((score, exercise))
        
        if not candidates:
            logger.warning(
                "No suitable exercise found for pattern %s in routine %s",
                slot.pattern.value,
                routine,
            )
            return None
        
        # Sort by score (descending) and pick the best
        candidates.sort(key=lambda x: x[0], reverse=True)
        selected = candidates[0][1]
        
        # Mark as used
        self._used_exercises.add(selected["exercise_name"])
        
        return selected
    
    def reset_used_exercises(self):
        """Reset the used exercises tracker (between routines if needed)."""
        self._used_exercises.clear()


class PrescriptionCalculator:
    """Calculates sets, reps, and intensity for exercises."""
    
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.rules = PrescriptionRules()
    
    def get_sets(self, role: str) -> int:
        """Get number of sets for a given role."""
        base_sets = self.rules.SETS_BY_ROLE.get(
            self.config.experience_level,
            {"main": 3, "accessory": 2}
        ).get(role, 3)
        
        # Apply volume scaling
        scaled = int(round(base_sets * self.config.volume_scale))
        
        # Ensure minimum of 1 set
        return max(1, scaled)
    
    def get_rep_range(self, role: str, is_core: bool = False) -> Tuple[int, int]:
        """Get rep range for a given role and goal."""
        goal_ranges = self.rules.REP_RANGES.get(
            self.config.goal,
            self.rules.REP_RANGES["hypertrophy"]
        )
        
        if is_core:
            return goal_ranges.get("core", (10, 15))
        
        return goal_ranges.get(role, (8, 12))
    
    def get_rir(self, role: str) -> int:
        """Get RIR for a given role."""
        return self.rules.RIR_DEFAULTS.get(role, 2)
    
    def get_rpe(self, role: str) -> float:
        """Get RPE for a given role."""
        return self.rules.RPE_DEFAULTS.get(role, 8.0)
    
    def get_estimated_weight(
        self,
        pattern: MovementPattern,
        subpattern: Optional[MovementSubpattern] = None,
    ) -> float:
        """
        Get estimated starting weight based on movement pattern and experience level.
        
        Args:
            pattern: The movement pattern (e.g., SQUAT, HORIZONTAL_PUSH)
            subpattern: Optional subpattern for more specific weight adjustments
            
        Returns:
            Estimated starting weight in kilograms (kg)
        """
        experience = self.config.experience_level
        
        # Get base weight for the pattern
        pattern_weights = ESTIMATED_WEIGHTS.get(pattern.value, {})
        base_weight = pattern_weights.get(experience, 20.0)  # Default fallback
        
        # Apply subpattern multiplier if available
        if subpattern:
            multiplier = SUBPATTERN_WEIGHT_MULTIPLIERS.get(subpattern.value, 1.0)
            # Handle bodyweight exercises (multiplier of 0.0)
            if multiplier == 0.0:
                return 0.0  # Bodyweight
            base_weight *= multiplier
        
        # Round to nearest 2.5 kg for practical gym use
        return round(base_weight / 2.5) * 2.5
    
    def calculate_prescription(
        self,
        slot: SlotDefinition,
        exercise_name: str,
    ) -> Dict[str, Any]:
        """Calculate complete prescription for an exercise."""
        role = slot.role
        is_core = slot.pattern in (MovementPattern.CORE_STATIC, MovementPattern.CORE_DYNAMIC)
        
        # Core exercises use "core" role for RIR/RPE but "accessory" for sets
        rir_role = "core" if is_core else role
        sets_role = "accessory" if is_core else role
        
        min_reps, max_reps = self.get_rep_range(role, is_core)
        
        # Get estimated starting weight based on pattern, subpattern, and experience
        estimated_weight = self.get_estimated_weight(slot.pattern, slot.subpattern_preference)
        
        return {
            "sets": self.get_sets(sets_role),
            "min_rep_range": min_reps,
            "max_rep_range": max_reps,
            "rir": self.get_rir(rir_role),
            "rpe": self.get_rpe(rir_role),
            "weight": estimated_weight,
        }


class PlanGenerator:
    """Main class for generating workout plans."""
    
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.selector = ExerciseSelector(config)
        self.prescriber = PrescriptionCalculator(config)
    
    def _get_blueprint(self) -> Dict[str, List[SlotDefinition]]:
        """Get the session blueprint for the configured training days."""
        return SESSION_BLUEPRINTS.get(self.config.training_days, SESSION_BLUEPRINTS[2])
    
    def _build_routine(self, routine_name: str, slots: List[SlotDefinition]) -> List[ExerciseRow]:
        """Build a single routine from its slot definitions."""
        exercises = []
        
        for order, slot in enumerate(slots, start=1):
            selected = self.selector.select_exercise(slot, routine_name)
            
            if selected is None:
                logger.warning(
                    "Skipping slot %d (%s) in routine %s - no exercise found",
                    order,
                    slot.pattern.value,
                    routine_name,
                )
                continue
            
            prescription = self.prescriber.calculate_prescription(
                slot,
                selected["exercise_name"],
            )
            
            row = ExerciseRow(
                routine=routine_name,
                exercise=selected["exercise_name"],
                sets=prescription["sets"],
                min_rep_range=prescription["min_rep_range"],
                max_rep_range=prescription["max_rep_range"],
                rir=prescription["rir"],
                rpe=prescription["rpe"],
                weight=prescription["weight"],
                exercise_order=order,
                pattern=slot.pattern.value,
                role=slot.role,
            )
            exercises.append(row)
        
        return exercises
    
    def _adjust_volume(self, routines: Dict[str, List[ExerciseRow]]) -> Dict[str, List[ExerciseRow]]:
        """Adjust volume to meet session constraints."""
        rules = PrescriptionRules()
        
        for routine_name, exercises in routines.items():
            total_sets = sum(ex.sets for ex in exercises)
            
            # If over max, reduce accessory sets first
            while total_sets > rules.MAX_SETS_PER_SESSION:
                # Find accessories with sets > 1
                for ex in reversed(exercises):
                    if ex.role == "accessory" and ex.sets > 1:
                        ex.sets -= 1
                        total_sets -= 1
                        break
                else:
                    # No more accessories to reduce, reduce main lifts
                    for ex in reversed(exercises):
                        if ex.sets > 2:
                            ex.sets -= 1
                            total_sets -= 1
                            break
                    else:
                        break  # Can't reduce further
            
            # If under min, increase main lift sets
            while total_sets < rules.MIN_SETS_PER_SESSION:
                for ex in exercises:
                    if ex.role == "main" and ex.sets < 5:
                        ex.sets += 1
                        total_sets += 1
                        if total_sets >= rules.MIN_SETS_PER_SESSION:
                            break
                else:
                    break  # Can't increase further
        
        return routines
    
    def _apply_priority_muscle_boost(
        self, 
        routines: Dict[str, List[ExerciseRow]]
    ) -> Dict[str, List[ExerciseRow]]:
        """
        Apply volume boost for priority muscles.
        
        Strategy:
        1. Find exercises that target priority muscles
        2. Add +1 set to existing accessories targeting those muscles
        3. Stay within 24 sets/session budget
        4. Apply "clear volume for volume": reduce non-essential add-ons first
        5. Never remove core movement patterns
        
        Returns:
            Modified routines with adjusted volumes
        """
        if not self.config.priority_muscles:
            return routines
        
        rules = PrescriptionRules()
        priority_lower = [m.lower() for m in self.config.priority_muscles]
        
        # Get relevant patterns and subpatterns for priority muscles
        relevant_patterns: Set[MovementPattern] = set()
        relevant_subpatterns: Set[MovementSubpattern] = set()
        
        for muscle in priority_lower:
            mapping = MUSCLE_TO_PATTERNS.get(muscle)
            if mapping:
                relevant_patterns.update(mapping.get("patterns", []))
                relevant_subpatterns.update(mapping.get("isolation_subpatterns", []))
        
        logger.debug("Priority muscles: %s", priority_lower)
        logger.debug("Relevant patterns: %s", [p.value for p in relevant_patterns])
        logger.debug("Relevant subpatterns: %s", [s.value for s in relevant_subpatterns])
        
        for routine_name, exercises in routines.items():
            total_sets = sum(ex.sets for ex in exercises)
            sets_budget = rules.MAX_SETS_PER_SESSION - total_sets
            
            if sets_budget <= 0:
                # Need to "clear volume" - reduce non-priority accessories first
                cleared = self._clear_volume_for_priority(
                    exercises, 
                    relevant_patterns, 
                    target_sets_to_clear=2
                )
                sets_budget += cleared
            
            if sets_budget <= 0:
                logger.debug(
                    "Routine %s: No budget for priority boost after clearing",
                    routine_name,
                )
                continue
            
            # Find exercises targeting priority muscles (by pattern or muscle group)
            priority_exercises = []
            for ex in exercises:
                # Check by muscle group match (via DB lookup or cached data)
                is_priority = self._exercise_targets_priority_muscle(
                    ex.exercise, priority_lower
                )
                
                # Also check by pattern match
                if ex.pattern:
                    pattern = MovementPattern(ex.pattern) if ex.pattern else None
                    if pattern in relevant_patterns:
                        is_priority = True
                
                if is_priority and ex.role == "accessory":
                    priority_exercises.append(ex)
            
            # Boost priority exercises (add 1 set each, within budget)
            boosted = 0
            for ex in priority_exercises:
                if sets_budget <= 0:
                    break
                if ex.sets < 4:  # Cap accessory sets at 4
                    ex.sets += 1
                    sets_budget -= 1
                    boosted += 1
                    logger.debug(
                        "Boosted %s in routine %s to %d sets",
                        ex.exercise,
                        routine_name,
                        ex.sets,
                    )
            
            if boosted == 0 and sets_budget > 0:
                # No accessories to boost, try boosting main lifts
                for ex in exercises:
                    if sets_budget <= 0:
                        break
                    
                    if ex.pattern:
                        pattern = MovementPattern(ex.pattern) if ex.pattern else None
                        if pattern in relevant_patterns and ex.role == "main" and ex.sets < 5:
                            ex.sets += 1
                            sets_budget -= 1
                            logger.debug(
                                "Boosted main lift %s in routine %s to %d sets",
                                ex.exercise,
                                routine_name,
                                ex.sets,
                            )
        
        return routines
    
    def _clear_volume_for_priority(
        self,
        exercises: List[ExerciseRow],
        relevant_patterns: Set[MovementPattern],
        target_sets_to_clear: int = 2,
    ) -> int:
        """
        Clear volume from non-priority accessories to make room for priority work.
        
        Strategy: "Clear volume for volume" - reduce non-essential add-ons first.
        Never remove core movement patterns entirely.
        
        Returns:
            Number of sets cleared
        """
        cleared = 0
        
        # Protected patterns that should never be reduced to 0
        protected_patterns = {
            MovementPattern.SQUAT,
            MovementPattern.HINGE,
            MovementPattern.HORIZONTAL_PUSH,
            MovementPattern.HORIZONTAL_PULL,
            MovementPattern.VERTICAL_PUSH,
            MovementPattern.VERTICAL_PULL,
            MovementPattern.CORE_STATIC,
            MovementPattern.CORE_DYNAMIC,
        }
        
        # Sort by priority: non-priority isolations first, then other accessories
        def reduction_priority(ex: ExerciseRow) -> int:
            is_priority = False
            if ex.pattern:
                try:
                    pattern = MovementPattern(ex.pattern)
                    is_priority = pattern in relevant_patterns
                except ValueError:
                    pass
            
            if ex.role == "main":
                return 100  # Main lifts last
            if is_priority:
                return 50  # Priority accessories protected
            if ex.pattern in ("upper_isolation", "lower_isolation"):
                return 0  # Non-priority isolations first
            return 25  # Other accessories middle
        
        exercises_sorted = sorted(exercises, key=reduction_priority)
        
        for ex in exercises_sorted:
            if cleared >= target_sets_to_clear:
                break
            
            # Check if this is a protected core pattern
            is_protected = False
            if ex.pattern:
                try:
                    pattern = MovementPattern(ex.pattern)
                    is_protected = pattern in protected_patterns and ex.role == "main"
                except ValueError:
                    pass
            
            # Reduce sets but never below 1, and be careful with main lifts
            min_sets = 2 if ex.role == "main" else 1
            if ex.sets > min_sets and not is_protected:
                reduction = min(ex.sets - min_sets, target_sets_to_clear - cleared)
                ex.sets -= reduction
                cleared += reduction
                logger.debug(
                    "Cleared %d set(s) from %s (now %d sets) for priority reallocation",
                    reduction,
                    ex.exercise,
                    ex.sets,
                )
        
        return cleared
    
    def _exercise_targets_priority_muscle(
        self,
        exercise_name: str,
        priority_muscles: List[str],
    ) -> bool:
        """Check if an exercise targets any of the priority muscles."""
        # Look up exercise in cache
        exercises = self.selector._load_exercises()
        
        for ex in exercises:
            if ex.get("exercise_name") == exercise_name:
                primary = (ex.get("primary_muscle_group") or "").lower()
                secondary = (ex.get("secondary_muscle_group") or "").lower()
                
                for muscle in priority_muscles:
                    if muscle in primary or muscle in secondary:
                        return True
                    # Partial match (e.g., "glute" matches "gluteus maximus")
                    if any(muscle in m or m in muscle for m in [primary, secondary] if m):
                        return True
                
                break
        
        return False
    
    def _get_existing_patterns(self, routine: str) -> Set[MovementPattern]:
        """Get movement patterns already covered in a routine (for merge mode)."""
        patterns: Set[MovementPattern] = set()
        
        try:
            with DatabaseHandler() as db:
                rows = db.fetch_all(
                    """
                    SELECT us.exercise, e.movement_pattern
                    FROM user_selection us
                    LEFT JOIN exercises e ON us.exercise = e.exercise_name
                    WHERE us.routine = ?
                    """,
                    (routine,),
                )
                
                for row in rows:
                    pattern_str = row.get("movement_pattern")
                    if pattern_str:
                        try:
                            pattern = MovementPattern(pattern_str)
                            patterns.add(pattern)
                        except ValueError:
                            pass
        except Exception as e:
            logger.warning("Failed to get existing patterns for routine %s: %s", routine, e)
        
        return patterns
    
    def _estimate_workout_duration(self, exercises: List[ExerciseRow]) -> int:
        """
        Estimate workout duration in minutes based on exercises and sets.
        
        Rules (average time per set including rest):
        - Main compound lifts: 3-4 minutes/set (heavier weights, longer rest)
        - Accessory compounds: 2.5 minutes/set
        - Isolation exercises: 2 minutes/set (shorter rest)
        - Core exercises: 1.5 minutes/set
        """
        total_seconds = 0
        
        for ex in exercises:
            pattern = MovementPattern(ex.pattern) if ex.pattern else None
            
            if ex.role == "main":
                # Main lifts need more rest
                seconds_per_set = 210  # 3.5 minutes
            elif pattern in (MovementPattern.CORE_STATIC, MovementPattern.CORE_DYNAMIC):
                seconds_per_set = 90  # 1.5 minutes
            elif pattern in (MovementPattern.UPPER_ISOLATION, MovementPattern.LOWER_ISOLATION):
                seconds_per_set = 120  # 2 minutes
            else:
                seconds_per_set = 150  # 2.5 minutes
            
            total_seconds += ex.sets * seconds_per_set
        
        # Add warmup time (approximately 5-10 minutes)
        total_seconds += 420  # 7 minutes average warmup
        
        return total_seconds // 60
    
    def _optimize_for_time_budget(
        self, 
        routines: Dict[str, List[ExerciseRow]]
    ) -> Dict[str, List[ExerciseRow]]:
        """
        Optimize the plan to fit within the time budget.
        
        Strategy:
        1. Calculate estimated duration
        2. If over budget, progressively reduce:
           a. Accessory isolation sets
           b. Accessory compound sets
           c. Remove isolation exercises entirely
        3. Never reduce main lift sets below 2
        """
        if not self.config.time_budget_minutes:
            return routines
        
        target_minutes = self.config.time_budget_minutes
        
        for routine_name, exercises in routines.items():
            current_duration = self._estimate_workout_duration(exercises)
            
            if current_duration <= target_minutes:
                logger.debug(
                    "Routine %s within time budget (%d/%d minutes)",
                    routine_name,
                    current_duration,
                    target_minutes,
                )
                continue
            
            logger.info(
                "Optimizing routine %s for time budget (%d -> %d minutes)",
                routine_name,
                current_duration,
                target_minutes,
            )
            
            # Phase 1: Reduce isolation sets
            for ex in exercises:
                if current_duration <= target_minutes:
                    break
                pattern = MovementPattern(ex.pattern) if ex.pattern else None
                if pattern in (MovementPattern.UPPER_ISOLATION, MovementPattern.LOWER_ISOLATION):
                    while ex.sets > 1 and current_duration > target_minutes:
                        ex.sets -= 1
                        current_duration = self._estimate_workout_duration(exercises)
            
            # Phase 2: Reduce accessory compound sets
            for ex in exercises:
                if current_duration <= target_minutes:
                    break
                if ex.role == "accessory":
                    while ex.sets > 1 and current_duration > target_minutes:
                        ex.sets -= 1
                        current_duration = self._estimate_workout_duration(exercises)
            
            # Phase 3: Remove isolation exercises if still over
            if current_duration > target_minutes:
                exercises[:] = [
                    ex for ex in exercises
                    if MovementPattern(ex.pattern) not in (
                        MovementPattern.UPPER_ISOLATION, 
                        MovementPattern.LOWER_ISOLATION
                    ) if ex.pattern
                ]
                current_duration = self._estimate_workout_duration(exercises)
            
            logger.debug(
                "Routine %s optimized to ~%d minutes",
                routine_name,
                current_duration,
            )
        
        return routines
    
    def generate(self) -> GeneratedPlan:
        """Generate the complete workout plan."""
        blueprint = self._get_blueprint()
        routines: Dict[str, List[ExerciseRow]] = {}
        
        for routine_name, slots in blueprint.items():
            # For novice beginner consistency mode, only reset between
            # completely different routine types
            if not (self.config.beginner_consistency_mode and 
                    self.config.experience_level == "novice"):
                self.selector.reset_used_exercises()
            
            # Merge mode: only add slots for missing patterns
            if self.config.merge_mode:
                existing_patterns = self._get_existing_patterns(routine_name)
                
                if existing_patterns:
                    logger.info(
                        "Merge mode: Routine %s has existing patterns: %s",
                        routine_name,
                        [p.value for p in existing_patterns],
                    )
                    
                    # Filter slots to only include missing patterns
                    slots = [
                        slot for slot in slots
                        if slot.pattern not in existing_patterns
                    ]
                    
                    logger.info(
                        "Merge mode: Adding %d new exercises to routine %s",
                        len(slots),
                        routine_name,
                    )
            
            exercises = self._build_routine(routine_name, slots)
            routines[routine_name] = exercises
        
        # Adjust total volume if needed
        routines = self._adjust_volume(routines)
        
        # Apply priority muscle volume boost if configured
        if self.config.priority_muscles:
            routines = self._apply_priority_muscle_boost(routines)
        
        # Apply time budget optimization if configured (Phase 3)
        if self.config.time_budget_minutes:
            routines = self._optimize_for_time_budget(routines)
        
        return GeneratedPlan(routines=routines, config=self.config)
    
    def persist(self, plan: GeneratedPlan) -> Dict[str, int]:
        """Persist the generated plan to the database.
        
        Returns:
            Dictionary with routine names and number of exercises inserted
        """
        if not self.config.persist:
            return {}
        
        results = {}
        routine_names = list(plan.routines.keys())
        
        try:
            with DatabaseHandler() as db:
                # Handle overwrite behavior
                if self.config.overwrite:
                    # Delete existing rows for the routines we're about to create
                    for routine in routine_names:
                        # First delete related workout logs
                        db.execute_query(
                            """
                            DELETE FROM workout_log 
                            WHERE workout_plan_id IN (
                                SELECT id FROM user_selection WHERE routine = ?
                            )
                            """,
                            (routine,),
                        )
                        # Then delete the user_selection rows
                        db.execute_query(
                            "DELETE FROM user_selection WHERE routine = ?",
                            (routine,),
                        )
                else:
                    # Generate new routine names to avoid clobbering
                    # Check for existing routines and add suffix
                    for i, routine in enumerate(routine_names):
                        existing = db.fetch_one(
                            "SELECT COUNT(*) as count FROM user_selection WHERE routine = ?",
                            (routine,),
                        )
                        if existing and existing.get("count", 0) > 0:
                            # Find a unique suffix
                            suffix = 1
                            while True:
                                new_name = f"{routine}_gen{suffix}"
                                check = db.fetch_one(
                                    "SELECT COUNT(*) as count FROM user_selection WHERE routine = ?",
                                    (new_name,),
                                )
                                if not check or check.get("count", 0) == 0:
                                    # Update the routine name in the plan
                                    old_exercises = plan.routines.pop(routine)
                                    for ex in old_exercises:
                                        ex.routine = new_name
                                    plan.routines[new_name] = old_exercises
                                    break
                                suffix += 1
                
                # Get the current max exercise_order
                max_order_result = db.fetch_one(
                    "SELECT COALESCE(MAX(exercise_order), 0) AS max_order FROM user_selection"
                )
                base_order = 0
                if max_order_result is not None:
                    base_order = max_order_result.get("max_order", 0) or 0
                
                # Insert exercises
                insert_query = """
                    INSERT INTO user_selection 
                    (routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight, exercise_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                for routine_name, exercises in plan.routines.items():
                    inserted = 0
                    for ex in exercises:
                        base_order += 1
                        try:
                            db.execute_query(
                                insert_query,
                                (
                                    ex.routine,
                                    ex.exercise,
                                    ex.sets,
                                    ex.min_rep_range,
                                    ex.max_rep_range,
                                    ex.rir,
                                    ex.rpe,
                                    ex.weight,
                                    base_order,
                                ),
                            )
                            inserted += 1
                        except Exception as e:
                            logger.warning(
                                "Failed to insert exercise %s into routine %s: %s",
                                ex.exercise,
                                ex.routine,
                                e,
                            )
                    
                    results[routine_name] = inserted
                    logger.info(
                        "Inserted %d exercises into routine %s",
                        inserted,
                        routine_name,
                    )
        
        except Exception as e:
            logger.exception("Failed to persist generated plan")
            raise
        
        return results


def generate_starter_plan(
    training_days: int = 3,
    environment: str = "gym",
    experience_level: str = "novice",
    goal: str = "hypertrophy",
    volume_scale: float = 1.0,
    equipment_whitelist: Optional[List[str]] = None,
    exclude_exercises: Optional[List[str]] = None,
    preferred_exercises: Optional[Dict[str, List[str]]] = None,
    movement_restrictions: Optional[Dict[str, bool]] = None,
    target_muscle_groups: Optional[List[str]] = None,
    priority_muscles: Optional[List[str]] = None,
    time_budget_minutes: Optional[int] = None,
    merge_mode: bool = False,
    beginner_consistency_mode: bool = True,
    persist: bool = True,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Generate a starter workout plan.
    
    Args:
        training_days: Number of training sessions per week (1-5)
        environment: "gym" or "home"
        experience_level: "novice", "intermediate", or "advanced"
        goal: "hypertrophy", "strength", or "general"
        volume_scale: Volume multiplier (default 1.0)
        equipment_whitelist: List of allowed equipment types
        exclude_exercises: List of exercises to exclude
        preferred_exercises: Dict mapping pattern to preferred exercise names
        movement_restrictions: Dict of movement restrictions (e.g., {"no_overhead_press": True})
        target_muscle_groups: List of muscle groups to target (filter exercises)
        priority_muscles: List of muscles to prioritize (get extra volume)
        time_budget_minutes: Target workout duration in minutes (15-180)
        merge_mode: If True, keep existing exercises and only add missing patterns
        beginner_consistency_mode: Keep same main lifts for novices
        persist: Whether to save to database
        overwrite: Whether to overwrite existing routines (ignored if merge_mode=True)
        
    Returns:
        Dictionary containing the generated plan and metadata
    """
    config = GeneratorConfig(
        training_days=training_days,
        environment=environment,
        experience_level=experience_level,
        goal=goal,
        volume_scale=volume_scale,
        equipment_whitelist=equipment_whitelist,
        exclude_exercises=exclude_exercises,
        preferred_exercises=preferred_exercises,
        movement_restrictions=movement_restrictions,
        target_muscle_groups=target_muscle_groups,
        priority_muscles=priority_muscles,
        time_budget_minutes=time_budget_minutes,
        merge_mode=merge_mode,
        beginner_consistency_mode=beginner_consistency_mode,
        persist=persist,
        overwrite=overwrite,
    )
    
    generator = PlanGenerator(config)
    plan = generator.generate()
    
    result = plan.to_dict()
    result["total_exercises"] = plan.total_exercises
    result["sets_per_routine"] = plan.total_sets_per_routine
    
    # Add estimated duration if time budget optimization was applied
    if config.time_budget_minutes:
        result["estimated_duration_minutes"] = {
            routine: generator._estimate_workout_duration(exercises)
            for routine, exercises in plan.routines.items()
        }
        result["time_budget_minutes"] = config.time_budget_minutes
    
    # Indicate merge mode was used
    if config.merge_mode:
        result["merge_mode"] = True
    
    if persist:
        try:
            inserted = generator.persist(plan)
            result["persisted"] = True
            result["inserted_counts"] = inserted
        except Exception as e:
            result["persisted"] = False
            result["persist_error"] = str(e)
    else:
        result["persisted"] = False
    
    return result
