"""Canonical constants used across the Hypertrophy Toolbox backend."""
from __future__ import annotations

MUSCLE_GROUPS = [
    "Rectus Abdominis",
    "Biceps",
    "Calves",
    "Chest",
    "External Obliques",
    "Forearms",
    "Front-Shoulder",  # TODO: evaluate collapsing into anatomical deltoid naming once UI migrates
    "Gluteus Maximus",
    "Hamstrings",
    "Hip-Adductors",
    "Latissimus Dorsi",
    "Lower Back",
    "Middle-Shoulder",
    "Middle-Traps",
    "Neck",
    "Quadriceps",
    "Rear-Shoulder",
    "Trapezius",
    "Triceps",
    "Upper Back",
]

FORCE = {
    "push": "Push",
    "pull": "Pull",
    "pull & push": "Push/Pull",
    "pull / push": "Push/Pull",
    "push & pull": "Push/Pull",
    "pull or push": "Push/Pull",
    "hold": "Hold",
    "dynamic to static": "Dynamic to Static",
}

MECHANIC = {
    "compound": "Compound",
    "isolation": "Isolation",
    "isolated": "Isolation",
}

UTILITY = {
    "basic": "Basic",
    "auxiliary": "Auxiliary",
    "basic or auxiliary": "Basic",
    "auxiliary or basic": "Auxiliary",
}

DIFFICULTY = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}

EQUIPMENT_SYNONYMS = {
    "dumbbell": "Dumbbells",
    "dumbbells": "Dumbbells",
    "db": "Dumbbells",
    "cable": "Cables",
    "cables": "Cables",
    "smith-machine": "Smith_Machine",
    "smith_machine": "Smith_Machine",
    "smith machine": "Smith_Machine",
}

MUSCLE_ALIAS = {
    # Core / anterior trunk
    "Rectus Abdominis": "Rectus Abdominis",
    "Abdominals": "Rectus Abdominis",
    "Abs": "Rectus Abdominis",
    "Lower Abs": "Rectus Abdominis",
    "Upper Abdominals": "Rectus Abdominis",
    # Latissimus / back
    "Latissimus Dorsi": "Latissimus Dorsi",
    "Latissimus_Dorsi": "Latissimus Dorsi",
    "Latissimus-Dorsi": "Latissimus Dorsi",
    "Latissimus": "Latissimus Dorsi",
    "Lats": "Latissimus Dorsi",
    "Lat": "Latissimus Dorsi",
    "Latissimus dorsi": "Latissimus Dorsi",
    # General back groupings
    "Back; General": "Lower Back",
    "Lower Back": "Lower Back",
    "Lowerback": "Lower Back",
    "Lower_Back": "Lower Back",
    "Upper Back": "Upper Back",
    "Upperback": "Upper Back",
    "Mid; Upper Back": "Upper Back",
    "Mid Upper Back": "Upper Back",
    "Mid/Upper Back": "Upper Back",  # TODO: confirm if this should remain a dedicated grouping
    "Mid/upper Back": "Upper Back",  # TODO: confirm if this should remain a dedicated grouping
    # Hip adductors & related
    "Hip Adductors": "Hip-Adductors",
    "Hip-Adductors": "Hip-Adductors",
    "Iliopsoas": "Hip-Adductors",
    "Adductors": "Hip-Adductors",
    # Glutes
    "Gluteus Maximus": "Gluteus Maximus",
    "Glutes": "Gluteus Maximus",
    "Glute": "Gluteus Maximus",
    "Gluteals": "Gluteus Maximus",
    # Hamstrings
    "Hamstrings": "Hamstrings",
    "Hamstring": "Hamstrings",
    "Hams": "Hamstrings",
    # Quadriceps
    "Quadriceps": "Quadriceps",
    "Quads": "Quadriceps",
    "Quadricep": "Quadriceps",
    # Calves
    "Calves": "Calves",
    "Gastrocnemius": "Calves",
    # Forearms
    "Forearms": "Forearms",
    # Neck
    "Neck": "Neck",
    # Shoulders
    "Front-Shoulder": "Front-Shoulder",
    "Front Shoulder": "Front-Shoulder",
    "Front-Shoulders": "Front-Shoulder",
    "Front Shoulders": "Front-Shoulder",
    "Front Delts": "Front-Shoulder",
    "Front Deltoids": "Front-Shoulder",
    "Anterior Delts": "Front-Shoulder",
    "Anterior Deltoids": "Front-Shoulder",
    "Deltoid; Anterior": "Front-Shoulder",
    "Middle-Shoulder": "Middle-Shoulder",
    "Middle Shoulder": "Middle-Shoulder",
    "Side Delts": "Middle-Shoulder",
    "Lateral Delts": "Middle-Shoulder",
    "Medial Delts": "Middle-Shoulder",
    "Deltoid; Lateral": "Middle-Shoulder",
    "Delts": "Middle-Shoulder",
    "Rear-Shoulder": "Rear-Shoulder",
    "Rear Shoulder": "Rear-Shoulder",
    "Rear Delts": "Rear-Shoulder",
    "Rear Deltoids": "Rear-Shoulder",
    "Posterior Delts": "Rear-Shoulder",
    "Deltoid; Posterior": "Rear-Shoulder",
    # Trapezius / traps
    "Trapezius": "Trapezius",
    "Traps": "Trapezius",
    "Trap": "Trapezius",
    "Middle-Traps": "Middle-Traps",
    "Middle Traps": "Middle-Traps",
    "Mid Traps": "Middle-Traps",
    "Traps (Mid-Back)": "Middle-Traps",
    # Obliques
    "External Obliques": "External Obliques",
    "Obliques": "External Obliques",
    "Oblique": "External Obliques",
    # Arms
    "Biceps": "Biceps",
    "Triceps": "Triceps",
}


# -- Muscle reconciliation canonical sets -----------------------------------
# Canonical primary/secondary/tertiary labels
PRIMARY_SET = {
    "Abs/Core",
    "Anterior Delts",
    "Biceps",
    "Calves",
    "Chest",
    "Delts",
    "Forearms",
    "Glutes",
    "Hamstrings",
    "Hip-Adductors",
    "Latissimus-Dorsi",
    "Lower Back",
    "Medial Delts",
    "Mid/Upper Back",
    "Middle-Traps",
    "Neck",
    "Obliques",
    "Quadriceps",
    "Rear Delts",
    "Traps",
    "Triceps",
    "Upper Traps",
    "Front-Shoulder",
    "Middle-Shoulder",
    "Rear-Shoulder",
}

# Canonical advanced tokens (lowercase, hyphenated)
ADVANCED_SET = {
    "lateral-deltoid",
    "anterior-deltoid",
    "posterior-deltoid",
    "upper-pectoralis",
    "mid-lower-pectoralis",
    "long-head-bicep",
    "short-head-bicep",
    "lateral-head-triceps",
    "long-head-triceps",
    "medial-head-triceps",
    "wrist-extensors",
    "wrist-flexors",
    "upper-abdominals",
    "lower-abdominals",
    "obliques",
    "serratus-anterior",
    "groin",
    "inner-thigh",
    "rectus-femoris",
    "quadriceps",
    "inner-quadricep",
    "outer-quadricep",
    "soleus",
    "tibialis",
    "gastrocnemius",
    "medial-hamstrings",
    "lateral-hamstrings",
    "gluteus-maximus",
    "gluteus-medius",
    "lowerback",
    "lats",
    "lower-trapezius",
    "traps-middle",
    "upper-trapezius",
}

# Tokens to treat as nulls
NULL_TOKENS = {"", "nan", "none", "n/a", "na", "null", "-"}

# P/S/T alias map (case-insensitive keys) → canonical
PST_SYNONYMS = {
    "shoulders": "Delts",
    "rear shoulders": "Rear-Shoulder",
    "posterior deltoid": "Rear-Shoulder",
    "posterior delts": "Rear-Shoulder",
    "rear delts": "Rear-Shoulder",
    "anterior deltoid": "Front-Shoulder",
    "front delts": "Front-Shoulder",
    "front shoulder": "Front-Shoulder",
    "lateral deltoid": "Middle-Shoulder",
    "lateral delts": "Middle-Shoulder",
    "middle delts": "Middle-Shoulder",
    "medial delts": "Middle-Shoulder",
    "inner thigh": "Hip-Adductors",
    "groin": "Hip-Adductors",
    "rectus femoris": "Quadriceps",
    "tibialis": "Calves",
    "feet": "Calves",
    "lower abdominals": "Abs/Core",
    "upper traps": "Upper Traps",
    "lower traps": "Traps",
    "latissimus dorsi": "Latissimus-Dorsi",
}

# Advanced alias map (case-insensitive keys) → canonical advanced
ADV_SYNONYMS = {
    "upper pectoralis": "upper-pectoralis",
    "upper-pectoralis": "upper-pectoralis",
    "mid lower pectoralis": "mid-lower-pectoralis",
    "mid-lower pectoralis": "mid-lower-pectoralis",
    "anterior deltoid": "anterior-deltoid",
    "posterior deltoid": "posterior-deltoid",
    "lateral deltoid": "lateral-deltoid",
    "long head triceps": "long-head-triceps",
    "medial head triceps": "medial-head-triceps",
    "lateral head triceps": "lateral-head-triceps",
    "long head bicep": "long-head-bicep",
    "short head bicep": "short-head-bicep",
    "upper abdominals": "upper-abdominals",
    "lower abdominals": "lower-abdominals",
    "lower traps": "lower-trapezius",
    "upper traps": "upper-trapezius",
    "middle traps": "traps-middle",
    "latissimus dorsi": "lats",
    "latissimus-dorsi": "lats",
    "inner quadricep": "inner-quadricep",
    "outer quadricep": "outer-quadricep",
    "gluteus medius": "gluteus-medius",
    "gluteus maximus": "gluteus-maximus",
    "lower back": "lowerback",
    "rectus femoris": "rectus-femoris",
    "serratus anterior": "serratus-anterior",
    "serratus-anterior": "serratus-anterior",
    "serratus": "serratus-anterior",
    "quadriceps": "quadriceps",
    "quadriceps femoris": "quadriceps",
    "quadricep": "quadriceps",
    "quads": "quadriceps",
    "quad": "quadriceps",
}

# Group labels that must NEVER appear in advanced
GROUP_LABELS_FORBIDDEN_IN_ADV = {
    "chest",
    "triceps",
    "biceps",
    "delts",
    "shoulders",
    "front-shoulder",
    "middle-shoulder",
    "rear-shoulder",
    "abs/core",
    "hamstrings",
    "glutes",
    "forearms",
    "traps",
    "upper traps",
    "middle-traps",
    "lower back",
    "mid/upper back",
    "latissimus-dorsi",
    "lats",
}

# Antagonist pairing rules for optimal supersets
ANTAGONIST_PAIRS = {
    # Upper body
    'biceps': ['triceps'],
    'triceps': ['biceps'],
    'chest': ['upper back', 'latissimus dorsi', 'middle-traps'],
    'latissimus dorsi': ['chest', 'front-shoulder'],
    'upper back': ['chest', 'front-shoulder'],
    'front-shoulder': ['latissimus dorsi', 'upper back'],
    'rear-shoulder': ['front-shoulder', 'middle-shoulder'],
    # Lower body
    'quadriceps': ['hamstrings', 'gluteus maximus'],
    'hamstrings': ['quadriceps'],
    'gluteus maximus': ['quadriceps', 'hip-adductors'],
    'calves': ['quadriceps', 'hamstrings'],  # Non-competing with main movers
}
