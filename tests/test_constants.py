"""
Tests for utils/constants.py - Application constants and mappings.
"""

from utils.constants import (
    MUSCLE_GROUPS,
    FORCE,
    MECHANIC,
    UTILITY,
    DIFFICULTY,
    EQUIPMENT_SYNONYMS,
    MUSCLE_ALIAS,
)


class TestMuscleGroups:
    """Tests for MUSCLE_GROUPS constant."""

    def test_muscle_groups_is_list(self):
        """MUSCLE_GROUPS should be a list."""
        assert isinstance(MUSCLE_GROUPS, list)

    def test_muscle_groups_not_empty(self):
        """MUSCLE_GROUPS should not be empty."""
        assert len(MUSCLE_GROUPS) > 0

    def test_contains_major_muscle_groups(self):
        """Should contain major muscle groups."""
        major_muscles = ["Chest", "Biceps", "Triceps", "Quadriceps", "Hamstrings"]
        for muscle in major_muscles:
            assert muscle in MUSCLE_GROUPS

    def test_muscle_groups_are_strings(self):
        """All muscle groups should be strings."""
        for muscle in MUSCLE_GROUPS:
            assert isinstance(muscle, str)

    def test_no_duplicate_muscle_groups(self):
        """Should not have duplicate entries."""
        assert len(MUSCLE_GROUPS) == len(set(MUSCLE_GROUPS))


class TestForceMapping:
    """Tests for FORCE constant."""

    def test_force_is_dict(self):
        """FORCE should be a dictionary."""
        assert isinstance(FORCE, dict)

    def test_force_has_push_pull(self):
        """FORCE should have push and pull."""
        assert "push" in FORCE
        assert "pull" in FORCE
        assert FORCE["push"] == "Push"
        assert FORCE["pull"] == "Pull"

    def test_force_normalizes_combined(self):
        """FORCE should normalize combined push/pull values."""
        assert FORCE.get("pull & push") == "Push/Pull"
        assert FORCE.get("push & pull") == "Push/Pull"

    def test_force_has_hold(self):
        """FORCE should have hold type."""
        assert "hold" in FORCE
        assert FORCE["hold"] == "Hold"

    def test_force_values_are_strings(self):
        """All FORCE values should be strings."""
        for key, value in FORCE.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestMechanicMapping:
    """Tests for MECHANIC constant."""

    def test_mechanic_is_dict(self):
        """MECHANIC should be a dictionary."""
        assert isinstance(MECHANIC, dict)

    def test_mechanic_has_compound(self):
        """MECHANIC should have compound."""
        assert "compound" in MECHANIC
        assert MECHANIC["compound"] == "Compound"

    def test_mechanic_handles_isolation_variants(self):
        """MECHANIC should normalize isolation variants."""
        assert MECHANIC.get("isolation") == "Isolation"
        assert MECHANIC.get("isolated") == "Isolation"

    def test_mechanic_values_are_strings(self):
        """All MECHANIC values should be strings."""
        for key, value in MECHANIC.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestUtilityMapping:
    """Tests for UTILITY constant."""

    def test_utility_is_dict(self):
        """UTILITY should be a dictionary."""
        assert isinstance(UTILITY, dict)

    def test_utility_has_basic_auxiliary(self):
        """UTILITY should have basic and auxiliary."""
        assert "basic" in UTILITY
        assert "auxiliary" in UTILITY
        assert UTILITY["basic"] == "Basic"
        assert UTILITY["auxiliary"] == "Auxiliary"

    def test_utility_handles_combined(self):
        """UTILITY should handle combined values."""
        assert "basic or auxiliary" in UTILITY or "auxiliary or basic" in UTILITY

    def test_utility_values_are_strings(self):
        """All UTILITY values should be strings."""
        for key, value in UTILITY.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestDifficultyMapping:
    """Tests for DIFFICULTY constant."""

    def test_difficulty_is_dict(self):
        """DIFFICULTY should be a dictionary."""
        assert isinstance(DIFFICULTY, dict)

    def test_difficulty_has_all_levels(self):
        """DIFFICULTY should have beginner, intermediate, advanced."""
        assert "beginner" in DIFFICULTY
        assert "intermediate" in DIFFICULTY
        assert "advanced" in DIFFICULTY

    def test_difficulty_values_capitalized(self):
        """DIFFICULTY values should be title case."""
        assert DIFFICULTY["beginner"] == "Beginner"
        assert DIFFICULTY["intermediate"] == "Intermediate"
        assert DIFFICULTY["advanced"] == "Advanced"

    def test_difficulty_values_are_strings(self):
        """All DIFFICULTY values should be strings."""
        for key, value in DIFFICULTY.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestEquipmentSynonyms:
    """Tests for EQUIPMENT_SYNONYMS constant."""

    def test_equipment_synonyms_is_dict(self):
        """EQUIPMENT_SYNONYMS should be a dictionary."""
        assert isinstance(EQUIPMENT_SYNONYMS, dict)

    def test_dumbbell_synonyms(self):
        """EQUIPMENT_SYNONYMS should handle dumbbell variants."""
        assert EQUIPMENT_SYNONYMS.get("dumbbell") == "Dumbbells"
        assert EQUIPMENT_SYNONYMS.get("dumbbells") == "Dumbbells"
        assert EQUIPMENT_SYNONYMS.get("db") == "Dumbbells"

    def test_cable_synonyms(self):
        """EQUIPMENT_SYNONYMS should handle cable variants."""
        assert EQUIPMENT_SYNONYMS.get("cable") == "Cables"
        assert EQUIPMENT_SYNONYMS.get("cables") == "Cables"

    def test_smith_machine_synonyms(self):
        """EQUIPMENT_SYNONYMS should handle smith machine variants."""
        assert EQUIPMENT_SYNONYMS.get("smith-machine") == "Smith_Machine"
        assert EQUIPMENT_SYNONYMS.get("smith_machine") == "Smith_Machine"
        assert EQUIPMENT_SYNONYMS.get("smith machine") == "Smith_Machine"

    def test_equipment_synonyms_values_are_strings(self):
        """All EQUIPMENT_SYNONYMS values should be strings."""
        for key, value in EQUIPMENT_SYNONYMS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestMuscleAlias:
    """Tests for MUSCLE_ALIAS constant."""

    def test_muscle_alias_is_dict(self):
        """MUSCLE_ALIAS should be a dictionary."""
        assert isinstance(MUSCLE_ALIAS, dict)

    def test_muscle_alias_not_empty(self):
        """MUSCLE_ALIAS should not be empty."""
        assert len(MUSCLE_ALIAS) > 0

    def test_abdominals_aliases(self):
        """MUSCLE_ALIAS should normalize abdominal variants."""
        canonical = "Rectus Abdominis"
        aliases = ["Abdominals", "Abs", "Lower Abs"]
        for alias in aliases:
            if alias in MUSCLE_ALIAS:
                assert MUSCLE_ALIAS[alias] == canonical

    def test_lat_aliases(self):
        """MUSCLE_ALIAS should normalize lat variants."""
        canonical = "Latissimus Dorsi"
        aliases = ["Lats", "Lat", "Latissimus"]
        for alias in aliases:
            if alias in MUSCLE_ALIAS:
                assert MUSCLE_ALIAS[alias] == canonical

    def test_hip_adductor_aliases(self):
        """MUSCLE_ALIAS should normalize hip adductor variants."""
        canonical = "Hip-Adductors"
        aliases = ["Hip Adductors", "Adductors"]
        for alias in aliases:
            if alias in MUSCLE_ALIAS:
                assert MUSCLE_ALIAS[alias] == canonical

    def test_identity_mappings(self):
        """Canonical names should map to themselves."""
        # Most canonical names should be in the alias map pointing to themselves
        canonical_names = ["Rectus Abdominis", "Latissimus Dorsi", "Hip-Adductors"]
        for name in canonical_names:
            if name in MUSCLE_ALIAS:
                assert MUSCLE_ALIAS[name] == name

    def test_muscle_alias_values_are_strings(self):
        """All MUSCLE_ALIAS values should be strings."""
        for key, value in MUSCLE_ALIAS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestConstantsConsistency:
    """Tests for consistency across constants."""

    def test_force_keys_lowercase(self):
        """FORCE keys should be lowercase for easy lookup."""
        for key in FORCE.keys():
            assert key == key.lower()

    def test_mechanic_keys_lowercase(self):
        """MECHANIC keys should be lowercase for easy lookup."""
        for key in MECHANIC.keys():
            assert key == key.lower()

    def test_utility_keys_lowercase(self):
        """UTILITY keys should be lowercase for easy lookup."""
        for key in UTILITY.keys():
            assert key == key.lower()

    def test_difficulty_keys_lowercase(self):
        """DIFFICULTY keys should be lowercase for easy lookup."""
        for key in DIFFICULTY.keys():
            assert key == key.lower()

    def test_equipment_synonyms_keys_lowercase(self):
        """EQUIPMENT_SYNONYMS keys should be lowercase for easy lookup."""
        for key in EQUIPMENT_SYNONYMS.keys():
            assert key == key.lower()


class TestMuscleGroupCompleteness:
    """Tests for muscle group completeness."""

    def test_includes_shoulders(self):
        """Should include shoulder variations."""
        shoulder_muscles = [m for m in MUSCLE_GROUPS if "Shoulder" in m]
        assert len(shoulder_muscles) >= 2  # At least front and rear

    def test_includes_traps(self):
        """Should include trapezius muscles."""
        trap_muscles = [m for m in MUSCLE_GROUPS if "Trap" in m]
        assert len(trap_muscles) >= 1

    def test_includes_core_muscles(self):
        """Should include core muscles."""
        assert "Rectus Abdominis" in MUSCLE_GROUPS
        assert any("Oblique" in m for m in MUSCLE_GROUPS)

    def test_includes_back_muscles(self):
        """Should include back muscles."""
        back_muscles = [m for m in MUSCLE_GROUPS if "Back" in m or "Latissimus" in m]
        assert len(back_muscles) >= 2

    def test_includes_arm_muscles(self):
        """Should include arm muscles."""
        assert "Biceps" in MUSCLE_GROUPS
        assert "Triceps" in MUSCLE_GROUPS
        assert "Forearms" in MUSCLE_GROUPS

    def test_includes_leg_muscles(self):
        """Should include leg muscles."""
        assert "Quadriceps" in MUSCLE_GROUPS
        assert "Hamstrings" in MUSCLE_GROUPS
        assert "Calves" in MUSCLE_GROUPS
        assert "Gluteus Maximus" in MUSCLE_GROUPS
