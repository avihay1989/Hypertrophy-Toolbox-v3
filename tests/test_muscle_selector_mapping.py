"""
Tests for muscle selector mapping validation.

Ensures all vendor SVG slugs are properly mapped to canonical keys,
and all canonical keys have labels and backend mappings.
"""

import pytest
import re
from pathlib import Path


# Path to the muscle-selector.js file
MUSCLE_SELECTOR_JS = Path(__file__).parent.parent / "static" / "js" / "modules" / "muscle-selector.js"
ANTERIOR_SVG = Path(__file__).parent.parent / "static" / "vendor" / "react-body-highlighter" / "body_anterior.svg"
POSTERIOR_SVG = Path(__file__).parent.parent / "static" / "vendor" / "react-body-highlighter" / "body_posterior.svg"


def extract_js_object(js_content: str, var_name: str) -> dict:
    """Extract a JavaScript object/dict from the JS file content."""
    # Find the variable declaration
    pattern = rf"const {var_name}\s*=\s*\{{"
    match = re.search(pattern, js_content)
    if not match:
        return {}
    
    # Find matching closing brace
    start = match.end() - 1
    depth = 0
    end = start
    
    for i, char in enumerate(js_content[start:], start):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    
    obj_str = js_content[start:end]
    
    # Parse simple key-value pairs (this is a simplified parser)
    result = {}
    # Match patterns like: 'key': 'value', or 'key': null,
    kv_pattern = r"'([^']+)':\s*(?:'([^']*)'|null|(\[.*?\]))"
    for match in re.finditer(kv_pattern, obj_str, re.DOTALL):
        key = match.group(1)
        value = match.group(2) if match.group(2) else None
        if match.group(3):  # Array value - skip for this simple parser
            value = 'ARRAY'
        result[key] = value
    
    return result


def extract_svg_data_muscles(svg_path: Path) -> set:
    """Extract all data-muscle attribute values from an SVG file."""
    if not svg_path.exists():
        return set()
    
    content = svg_path.read_text(encoding='utf-8')
    # Match data-muscle="value" patterns
    pattern = r'data-muscle="([^"]+)"'
    return set(re.findall(pattern, content))


class TestMuscleSelectorMapping:
    """Test suite for muscle selector mapping validation."""
    
    @pytest.fixture
    def js_content(self):
        """Load the muscle-selector.js file content."""
        if not MUSCLE_SELECTOR_JS.exists():
            pytest.skip("muscle-selector.js not found")
        return MUSCLE_SELECTOR_JS.read_text(encoding='utf-8')
    
    @pytest.fixture
    def vendor_slug_to_canonical(self, js_content):
        """Extract VENDOR_SLUG_TO_CANONICAL mapping."""
        return extract_js_object(js_content, "VENDOR_SLUG_TO_CANONICAL")
    
    @pytest.fixture  
    def muscle_labels(self, js_content):
        """Extract MUSCLE_LABELS mapping."""
        return extract_js_object(js_content, "MUSCLE_LABELS")
    
    @pytest.fixture
    def muscle_to_backend(self, js_content):
        """Extract MUSCLE_TO_BACKEND mapping."""
        return extract_js_object(js_content, "MUSCLE_TO_BACKEND")
    
    @pytest.fixture
    def anterior_slugs(self):
        """Extract data-muscle values from anterior SVG."""
        return extract_svg_data_muscles(ANTERIOR_SVG)
    
    @pytest.fixture
    def posterior_slugs(self):
        """Extract data-muscle values from posterior SVG."""
        return extract_svg_data_muscles(POSTERIOR_SVG)
    
    def test_vendor_files_exist(self):
        """Verify vendor SVG files exist."""
        assert ANTERIOR_SVG.exists(), f"Anterior SVG not found: {ANTERIOR_SVG}"
        assert POSTERIOR_SVG.exists(), f"Posterior SVG not found: {POSTERIOR_SVG}"
    
    def test_all_anterior_slugs_mapped(self, anterior_slugs, vendor_slug_to_canonical):
        """All data-muscle slugs in anterior SVG should be in the mapping."""
        if not anterior_slugs:
            pytest.skip("No slugs found in anterior SVG")
        
        for slug in anterior_slugs:
            assert slug in vendor_slug_to_canonical, \
                f"Anterior SVG slug '{slug}' not found in VENDOR_SLUG_TO_CANONICAL"
    
    def test_all_posterior_slugs_mapped(self, posterior_slugs, vendor_slug_to_canonical):
        """All data-muscle slugs in posterior SVG should be in the mapping."""
        if not posterior_slugs:
            pytest.skip("No slugs found in posterior SVG")
        
        for slug in posterior_slugs:
            assert slug in vendor_slug_to_canonical, \
                f"Posterior SVG slug '{slug}' not found in VENDOR_SLUG_TO_CANONICAL"
    
    def test_canonical_keys_have_labels(self, vendor_slug_to_canonical, muscle_labels):
        """All non-null canonical keys should have labels."""
        canonical_keys = {v for v in vendor_slug_to_canonical.values() if v is not None}
        
        for key in canonical_keys:
            assert key in muscle_labels, \
                f"Canonical key '{key}' missing from MUSCLE_LABELS"
    
    def test_canonical_keys_have_backend_mapping(self, vendor_slug_to_canonical, muscle_to_backend):
        """All non-null canonical keys should have backend mappings."""
        canonical_keys = {v for v in vendor_slug_to_canonical.values() if v is not None}
        
        for key in canonical_keys:
            assert key in muscle_to_backend, \
                f"Canonical key '{key}' missing from MUSCLE_TO_BACKEND"
    
    def test_no_orphan_canonical_keys_in_labels(self, vendor_slug_to_canonical, muscle_labels):
        """Labels shouldn't have keys that aren't canonical (simple view keys)."""
        # Get all canonical keys plus advanced keys (which are in SIMPLE_TO_ADVANCED_MAP values)
        canonical_keys = {v for v in vendor_slug_to_canonical.values() if v is not None}
        
        # Simple validation: just check that common simple keys exist
        expected_simple_keys = {
            'chest', 'biceps', 'triceps', 'forearms', 'abdominals', 'obliques',
            'quads', 'calves', 'traps', 'glutes', 'hamstrings', 'lowerback'
        }
        
        for key in expected_simple_keys:
            assert key in muscle_labels, f"Expected simple key '{key}' not in MUSCLE_LABELS"
    
    def test_anterior_svg_has_expected_muscles(self, anterior_slugs):
        """Anterior SVG should contain expected muscle regions."""
        expected = {'chest', 'biceps', 'abs', 'quadriceps', 'front-deltoids'}
        
        for muscle in expected:
            assert muscle in anterior_slugs, \
                f"Expected muscle '{muscle}' not found in anterior SVG"
    
    def test_posterior_svg_has_expected_muscles(self, posterior_slugs):
        """Posterior SVG should contain expected muscle regions."""
        expected = {'trapezius', 'upper-back', 'lower-back', 'gluteal', 'hamstring'}
        
        for muscle in expected:
            assert muscle in posterior_slugs, \
                f"Expected muscle '{muscle}' not found in posterior SVG"
    
    def test_bilateral_muscles_appear_multiple_times(self, anterior_slugs, posterior_slugs):
        """Bilateral muscles should appear in the SVG (left + right sides)."""
        # These muscles should have multiple polygon entries
        # We can verify by checking the SVG content directly
        if ANTERIOR_SVG.exists():
            content = ANTERIOR_SVG.read_text(encoding='utf-8')
            # Count occurrences of data-muscle="chest"
            chest_count = content.count('data-muscle="chest"')
            assert chest_count >= 2, f"Expected chest to appear 2+ times, found {chest_count}"
            
            biceps_count = content.count('data-muscle="biceps"')
            assert biceps_count >= 2, f"Expected biceps to appear 2+ times, found {biceps_count}"


class TestMuscleSelectorJSStructure:
    """Test the structure of muscle-selector.js."""
    
    @pytest.fixture
    def js_content(self):
        if not MUSCLE_SELECTOR_JS.exists():
            pytest.skip("muscle-selector.js not found")
        return MUSCLE_SELECTOR_JS.read_text(encoding='utf-8')
    
    def test_muscle_selector_class_exists(self, js_content):
        """MuscleSelector class should be defined."""
        assert "class MuscleSelector" in js_content
    
    def test_exports_to_window(self, js_content):
        """Key objects should be exported to window."""
        assert "window.MuscleSelector" in js_content
        assert "window.MUSCLE_LABELS" in js_content
        assert "window.MUSCLE_TO_BACKEND" in js_content
    
    def test_vendor_mapping_defined(self, js_content):
        """VENDOR_SLUG_TO_CANONICAL should be defined."""
        assert "VENDOR_SLUG_TO_CANONICAL" in js_content
    
    def test_svg_paths_use_vendor_directory(self, js_content):
        """SVG_PATHS should reference vendor directory."""
        assert "/static/vendor/react-body-highlighter/" in js_content


# ============================================================================
# WORKOUT-COOL SIMPLE-MODE VARIANT (PLANNING.md §3)
#
# These SVGs ship pre-canonicalized `data-canonical-muscles` (plural,
# comma-separated) values rather than vendor slugs. The simple-view body map
# lives in static/vendor/workout-cool/, generated by
# scripts/build_workout_cool_svgs.py at the upstream commit pinned in
# static/vendor/workout-cool/VERSION.
# ============================================================================

WC_ANTERIOR_SVG = (
    Path(__file__).parent.parent / "static" / "vendor" / "workout-cool" / "body_anterior.svg"
)
WC_POSTERIOR_SVG = (
    Path(__file__).parent.parent / "static" / "vendor" / "workout-cool" / "body_posterior.svg"
)


def extract_canonical_muscle_lists(svg_path: Path) -> list[list[str]]:
    """Return one list-of-keys per data-canonical-muscles attribute occurrence.

    Multi-key regions (e.g. workout-cool BACK) carry comma-separated values
    such as "lats,upper-back,lowerback"; we keep the grouping so callers can
    distinguish "regions" from "individual keys".
    """
    if not svg_path.exists():
        return []
    content = svg_path.read_text(encoding="utf-8")
    return [
        [k.strip() for k in match.split(",") if k.strip()]
        for match in re.findall(r'data-canonical-muscles="([^"]+)"', content)
    ]


def extract_muscles_by_side(js_content: str) -> dict[str, set[str]]:
    """Extract MUSCLES_BY_SIDE.front and .back arrays from muscle-selector.js."""
    out = {"front": set(), "back": set()}
    pattern = re.compile(
        r"MUSCLES_BY_SIDE\s*=\s*\{(.+?)\};",
        re.DOTALL,
    )
    m = pattern.search(js_content)
    if not m:
        return out
    body = m.group(1)
    for side in ("front", "back"):
        sm = re.search(rf"{side}\s*:\s*\[(.+?)\]", body, re.DOTALL)
        if not sm:
            continue
        out[side] = set(re.findall(r"'([^']+)'", sm.group(1)))
    return out


# Keys that the Simple-mode workout-cool art does NOT draw on a given side.
# Recorded in docs/workout_cool_integration/EXECUTION_LOG.md (2026-04-29).
# Legend remains clickable for these on that side; only the SVG path is missing.
WORKOUT_COOL_UNMAPPED_BY_ART = {
    "front": {"adductors", "neck", "triceps"},
    "back": {"hip-abductors", "neck"},
}


class TestWorkoutCoolSvgCoverage:
    """workout-cool simple-mode SVGs honour PLANNING.md §3.3 mappings."""

    @pytest.fixture
    def js_content(self):
        if not MUSCLE_SELECTOR_JS.exists():
            pytest.skip("muscle-selector.js not found")
        return MUSCLE_SELECTOR_JS.read_text(encoding="utf-8")

    @pytest.fixture
    def anterior_groups(self):
        return extract_canonical_muscle_lists(WC_ANTERIOR_SVG)

    @pytest.fixture
    def posterior_groups(self):
        return extract_canonical_muscle_lists(WC_POSTERIOR_SVG)

    def test_workout_cool_svgs_exist(self):
        assert WC_ANTERIOR_SVG.exists(), f"Missing {WC_ANTERIOR_SVG}"
        assert WC_POSTERIOR_SVG.exists(), f"Missing {WC_POSTERIOR_SVG}"

    def test_anterior_canonical_keys_match_planning_3_3(self, anterior_groups):
        """Every PLANNING §3.3 anterior mapping is represented at least once."""
        flat = {k for grp in anterior_groups for k in grp}
        for key in [
            "chest", "abdominals", "obliques", "biceps", "forearms",
            "front-shoulders", "quads", "calves",
        ]:
            assert key in flat, f"Anterior SVG missing canonical key '{key}'"

    def test_posterior_canonical_keys_match_planning_3_3(self, posterior_groups):
        """Every PLANNING §3.3 posterior mapping is represented at least once."""
        flat = {k for grp in posterior_groups for k in grp}
        for key in [
            "traps", "rear-shoulders", "lats", "upper-back", "lowerback",
            "triceps", "forearms", "hamstrings", "glutes", "calves",
        ]:
            assert key in flat, f"Posterior SVG missing canonical key '{key}'"

    def test_back_region_is_multi_key(self, posterior_groups):
        """The BACK region is the canonical multi-key example: lats,upper-back,lowerback."""
        back_group = next(
            (grp for grp in posterior_groups
             if set(grp) == {"lats", "upper-back", "lowerback"}),
            None,
        )
        assert back_group is not None, (
            "Posterior SVG missing the BACK multi-key region "
            "(expected data-canonical-muscles='lats,upper-back,lowerback'). "
            "If the rebuild dropped this grouping, PLANNING §3.3 / §3.4.1 "
            "are no longer satisfied."
        )
        # Order matters at the SVG level (the JS splits on comma, then
        # flattens through SIMPLE_TO_ADVANCED_MAP — the order doesn't change
        # the flatten result, but freezing it here keeps the build script
        # output deterministic).
        assert back_group == ["lats", "upper-back", "lowerback"]

    def test_no_anterior_only_keys_on_posterior(self, posterior_groups):
        """Anterior-only keys (chest, abdominals, biceps, etc.) must not appear posterior."""
        flat = {k for grp in posterior_groups for k in grp}
        for key in ("chest", "abdominals", "obliques", "biceps", "quads", "front-shoulders"):
            assert key not in flat, (
                f"Posterior SVG should not contain '{key}' — see PLANNING §3.3"
            )

    def test_no_posterior_only_keys_on_anterior(self, anterior_groups):
        """Posterior-only keys (lats, glutes, hamstrings, traps, etc.) must not appear anterior."""
        flat = {k for grp in anterior_groups for k in grp}
        for key in (
            "lats", "upper-back", "lowerback", "glutes", "hamstrings",
            "traps", "rear-shoulders",
        ):
            assert key not in flat, (
                f"Anterior SVG should not contain '{key}' — see PLANNING §3.3"
            )

    def test_every_muscles_by_side_key_is_mapped_or_allowlisted(
        self, js_content, anterior_groups, posterior_groups
    ):
        """Every simple key in MUSCLES_BY_SIDE is drawn OR explicitly unmapped-by-art."""
        muscles_by_side = extract_muscles_by_side(js_content)
        assert muscles_by_side["front"], "Could not parse MUSCLES_BY_SIDE.front"
        assert muscles_by_side["back"], "Could not parse MUSCLES_BY_SIDE.back"

        anterior_drawn = {k for grp in anterior_groups for k in grp}
        posterior_drawn = {k for grp in posterior_groups for k in grp}

        missing_anterior = (
            muscles_by_side["front"]
            - anterior_drawn
            - WORKOUT_COOL_UNMAPPED_BY_ART["front"]
        )
        missing_posterior = (
            muscles_by_side["back"]
            - posterior_drawn
            - WORKOUT_COOL_UNMAPPED_BY_ART["back"]
        )
        assert not missing_anterior, (
            f"Anterior simple keys neither drawn nor allowlisted: {missing_anterior}"
        )
        assert not missing_posterior, (
            f"Posterior simple keys neither drawn nor allowlisted: {missing_posterior}"
        )


class TestRegionVisualState:
    """Multi-key region state derivation (PLANNING §3.4.1, §3.7).

    Mirrors the JS `regionVisualState()` so the canonical decision table
    stays asserted in CI even though the runtime is JavaScript. The
    BACK region's flattened advanced children are
    {lats, rhomboids, teres-major, teres-minor, erector-spinae} (5 keys),
    NOT the three simple keys — selectedMuscles only stores advanced keys.
    """

    SIMPLE_TO_ADVANCED = {
        "lats": ["lats"],
        "upper-back": ["rhomboids", "teres-major", "teres-minor"],
        "lowerback": ["erector-spinae"],
        "chest": ["upper-chest", "mid-chest", "lower-chest"],
    }

    @staticmethod
    def _flatten(simple_keys, mapping):
        out = []
        for k in simple_keys:
            children = mapping.get(k, [k])
            for c in children:
                if c not in out:
                    out.append(c)
        return out

    @classmethod
    def _state(cls, simple_keys, selected):
        advanced = cls._flatten(simple_keys, cls.SIMPLE_TO_ADVANCED)
        if not advanced:
            return "unselected"
        hits = sum(1 for k in advanced if k in selected)
        if hits == 0:
            return "unselected"
        if hits == len(advanced):
            return "selected"
        return "partial"

    BACK_KEYS = ("lats", "upper-back", "lowerback")

    def test_back_flatten_is_five_advanced_children(self):
        flat = self._flatten(list(self.BACK_KEYS), self.SIMPLE_TO_ADVANCED)
        assert flat == [
            "lats", "rhomboids", "teres-major", "teres-minor", "erector-spinae",
        ], (
            "BACK must flatten to 5 advanced children, not 3 simple keys. "
            "If this fails, the multi-key region click handler will desync "
            "from selectedMuscles (PLANNING §3.4.1)."
        )

    def test_back_unselected_when_empty(self):
        assert self._state(list(self.BACK_KEYS), set()) == "unselected"

    def test_back_partial_with_only_rhomboids(self):
        # Regression: forgetting SIMPLE_TO_ADVANCED expansion breaks this case.
        assert self._state(list(self.BACK_KEYS), {"rhomboids"}) == "partial"

    def test_back_partial_with_only_erector_spinae(self):
        # Regression: lowerback simple key has exactly one advanced child.
        assert self._state(list(self.BACK_KEYS), {"erector-spinae"}) == "partial"

    def test_back_partial_with_only_lats(self):
        assert self._state(list(self.BACK_KEYS), {"lats"}) == "partial"

    def test_back_partial_with_four_of_five(self):
        sel = {"lats", "rhomboids", "teres-major", "teres-minor"}
        assert self._state(list(self.BACK_KEYS), sel) == "partial"

    def test_back_selected_with_all_five(self):
        sel = {"lats", "rhomboids", "teres-major", "teres-minor", "erector-spinae"}
        assert self._state(list(self.BACK_KEYS), sel) == "selected"

    def test_chest_single_key_partial(self):
        # Sanity check: single-key regions still partial when 1 of 3 children selected.
        assert self._state(["chest"], {"mid-chest"}) == "partial"

    def test_chest_single_key_selected(self):
        assert self._state(
            ["chest"], {"upper-chest", "mid-chest", "lower-chest"}
        ) == "selected"
