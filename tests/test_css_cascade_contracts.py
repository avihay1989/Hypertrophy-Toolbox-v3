"""Static contracts for the Phase 4 CSS cascade foundation."""

from __future__ import annotations

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
