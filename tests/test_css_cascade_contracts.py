"""Static contracts for the Phase 4 CSS cascade foundation."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS_LINK_RE = re.compile(r"filename=['\"]css/([^'\"]+\.css)['\"]")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LAYER_ORDER_RE = re.compile(r"@layer\s+([^;{}]+);")
LAYER_BLOCK_RE = re.compile(r"@layer\s+([\w-]+)\s*\{")

GLOBAL_BUNDLES = (
    "tokens.css",
    "motion.css",
    "base.css",
    "layout.css",
    "components.css",
    "navbar.css",
    "theme-dark.css",
    "a11y.css",
)
ROUTE_BUNDLES = {
    "welcome.html": "pages-welcome.css",
    "workout_plan.html": "pages-workout-plan.css",
    "workout_log.html": "pages-workout-log.css",
    "weekly_summary.html": "pages-weekly-summary.css",
    "session_summary.html": "pages-session-summary.css",
    "progression_plan.html": "pages-progression.css",
    "user_profile.html": "pages-user-profile.css",
    "body_composition.html": "pages-body-composition.css",
    "volume_splitter.html": "pages-volume-splitter.css",
    "backup.html": "pages-backup.css",
}
LAYER_ORDER = ("workout", "navbar", "workout-dropdowns", "welcome")


def _css_links(template: str) -> list[str]:
    return CSS_LINK_RE.findall(template)


def test_tokens_load_before_every_local_consumer_bundle() -> None:
    base_links = _css_links((ROOT / "templates" / "base.html").read_text(encoding="utf-8"))

    assert base_links[0] == "tokens.css"
    assert base_links.count("tokens.css") == 1
    assert base_links.index("tokens.css") < base_links.index("bootstrap.custom.min.css")


def test_runtime_bundle_cap_and_route_ownership_are_unchanged() -> None:
    base_links = _css_links((ROOT / "templates" / "base.html").read_text(encoding="utf-8"))
    app_global_links = [name for name in base_links if name != "bootstrap.custom.min.css"]

    assert len(app_global_links) == 8
    assert set(app_global_links) == set(GLOBAL_BUNDLES)

    actual_route_bundles = {}
    for template_name, expected_bundle in ROUTE_BUNDLES.items():
        links = _css_links(
            (ROOT / "templates" / template_name).read_text(encoding="utf-8")
        )
        route_links = [name for name in links if name.startswith("pages-")]
        assert route_links == [expected_bundle]
        actual_route_bundles[template_name] = route_links[0]

    assert actual_route_bundles == ROUTE_BUNDLES
    assert len(set(actual_route_bundles.values())) == 10


def test_one_explicit_order_covers_every_existing_layer() -> None:
    stylesheets = {
        path: COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
        for path in (ROOT / "static" / "css").glob("*.css")
        if not path.name.endswith(".min.css")
    }
    declarations = [
        match.group(1)
        for css in stylesheets.values()
        for match in LAYER_ORDER_RE.finditer(css)
    ]
    layer_blocks = {
        match.group(1)
        for css in stylesheets.values()
        for match in LAYER_BLOCK_RE.finditer(css)
    }

    assert declarations == [", ".join(LAYER_ORDER)]
    assert layer_blocks == set(LAYER_ORDER)


def test_bootstrap_artifact_keeps_scss_owned_selector_families() -> None:
    scss_entry = (ROOT / "scss" / "custom-bootstrap.scss").read_text(encoding="utf-8")
    compiled = (ROOT / "static" / "css" / "bootstrap.custom.min.css").read_text(
        encoding="utf-8"
    )

    assert '@import "pages/workout_plan_volume_panel";' in scss_entry
    assert '@import "fatigue";' in scss_entry
    for selector in (
        ".fatigue-badge",
        ".fatigue-page",
        ".volume-active-summary",
        ".vp-drawer",
        "#vpToggle",
    ):
        assert selector in compiled


def test_deprecated_spacing_names_are_neutral_layout_aliases() -> None:
    tokens = (ROOT / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
    spacing_names = ("xs", "sm", "md", "lg", "xl", "2xl")

    for name in spacing_names:
        assert tokens.count(f"--space-{name}:") == 1
        assert f"--space-{name}: var(--layout-space-{name});" in tokens

    assert len(re.findall(r"^\s*--layout-space-[\w-]+:", tokens, re.MULTILINE)) == 41
    assert "--s-1: 4px;" in tokens
    assert "--s-7: 48px;" in tokens


def test_only_exact_local_values_use_shared_aliases() -> None:
    welcome = (ROOT / "static" / "css" / "pages-welcome.css").read_text(
        encoding="utf-8"
    )
    navbar = (ROOT / "static" / "css" / "navbar.css").read_text(encoding="utf-8")

    for local, shared in (
        ("--wl-success", "--success"),
        ("--wl-warning", "--warning"),
        ("--wl-danger", "--danger"),
        ("--wl-duration-fast", "--dur-fast"),
    ):
        assert f"{local}: var({shared});" in welcome

    assert "--nav-gap: var(--s-3);" in navbar
    assert "--nav-padding-y: var(--s-3);" in navbar
    assert "--nav-padding-x: 1rem;" in navbar


def test_stylelint_is_pinned_measure_only_with_committed_baseline() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    baseline = json.loads(
        (ROOT / "docs" / "CSS_PHASE4_WP4_1_STYLELINT_BASELINE.json").read_text(
            encoding="utf-8"
        )
    )

    assert package["devDependencies"]["stylelint"] == "16.11.0"
    assert package["devDependencies"]["postcss-scss"] == "4.0.9"
    assert "css-stylelint-measure:" in workflow
    assert "name: CSS Stylelint Measurement (non-required)" in workflow
    assert "continue-on-error: true" in workflow
    assert baseline["sourceCommit"] == "9ee763889e1e021d6cd1fe8d8782dccb4cb40d52"
    assert baseline["warningCount"] == 7202
    assert baseline["parseErrorCount"] == 0
