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
FRAME_ROUTE_BUNDLES = {
    "plan": "pages-workout-plan.css",
    "log": "pages-workout-log.css",
    "weekly": "pages-weekly-summary.css",
    "session": "pages-session-summary.css",
}


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


def test_shared_frame_and_route_surfaces_have_one_owner() -> None:
    css_dir = ROOT / "static" / "css"
    components = (css_dir / "components.css").read_text(encoding="utf-8")
    routes = {
        name: (css_dir / filename).read_text(encoding="utf-8")
        for name, filename in FRAME_ROUTE_BUNDLES.items()
    }

    shared_marker = "/* Shared frame infrastructure used by Workout Plan"
    shared_start = "/* Frame Base Styles - Glass Effect */"
    log_start = "/* Base Layer Frame for Workout Log - 2026 Glass Style */"
    summary_start = "/* Summary Frame Styles - 2026 Glass Style */"

    assert components.count(shared_marker) == 1
    assert components.count(shared_start) == 1
    assert components.count(
        ":where(#workout, .workout-log-page, .summary-frame) {"
    ) == 1
    assert "html:has(" not in components
    assert "&[data-theme='dark']" not in components
    assert components.count("[data-theme='dark'] & .frame-title") == 2
    assert sum(css.count(shared_start) for css in routes.values()) == 0
    assert len(re.findall(r"^\.frame-header-2025 \{", components, re.MULTILINE)) == 1
    assert sum(
        len(re.findall(r"^\.frame-header-2025 \{", css, re.MULTILINE))
        for css in routes.values()
    ) == 0

    assert routes["log"].count(log_start) == 1
    assert routes["log"].count(summary_start) == 0
    assert routes["weekly"].count(summary_start) == 1
    assert routes["session"].count(summary_start) == 1
    assert routes["weekly"].count(log_start) == 0
    assert routes["session"].count(log_start) == 0
    assert routes["plan"].count(log_start) == 0
    assert routes["plan"].count(summary_start) == 0

    # The weekly-only filter remains route-owned; WP4.2 does not delete it.
    assert "#isolated_muscles_filter" in routes["weekly"]
    assert "#isolated_muscles_filter" not in routes["session"]


def test_relocated_frame_selectors_remain_reachable_from_runtime_hooks() -> None:
    plan = (ROOT / "templates" / "workout_plan.html").read_text(encoding="utf-8")
    log = (ROOT / "templates" / "workout_log.html").read_text(encoding="utf-8")
    weekly = (ROOT / "templates" / "weekly_summary.html").read_text(
        encoding="utf-8"
    )
    session = (ROOT / "templates" / "session_summary.html").read_text(
        encoding="utf-8"
    )
    progression = (ROOT / "templates" / "progression_plan.html").read_text(
        encoding="utf-8"
    )
    log_js = (ROOT / "static" / "js" / "modules" / "workout-log.js").read_text(
        encoding="utf-8"
    )
    plan_js = (
        ROOT / "static" / "js" / "modules" / "workout-plan-page.js"
    ).read_text(encoding="utf-8")
    fixtures = (ROOT / "e2e" / "fixtures.ts").read_text(encoding="utf-8")

    for template in (plan, log):
        assert 'class="collapsible-frame' in template
        assert "frame-header-2025" in template
    assert ".collapsible-frame" in plan_js
    assert ".collapsible-frame" in log_js
    assert 'class="workout-log-frame"' in log
    assert "PAGE_WORKOUT_LOG: '.workout-log-frame'" in fixtures
    assert 'class="summary-frame frame-calm-glass"' in weekly
    assert 'class="summary-frame frame-calm-glass"' in session
    assert 'class="progression-plan-container"' in progression
    for route_hook in ('id="workout"', "workout-log-page", "summary-frame"):
        assert route_hook not in progression


def test_backup_tokens_remain_page_owned_under_the_late_global_theme() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "backup.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "pages-backup.css").read_text(
        encoding="utf-8"
    )
    backup_js = (
        ROOT / "static" / "js" / "modules" / "backup-center.js"
    ).read_text(encoding="utf-8")

    # The route bundle supplies Backup's local vocabulary. The later shared
    # theme keeps ownership of generic dark headings, forms, and tables.
    assert base.index("{% block page_css %}") < base.index("css/theme-dark.css")
    assert css.startswith(".backup-center-page {")
    assert ":root" not in css
    assert "[data-theme" not in css
    assert "!important" not in css

    for token in (
        "--backup-accent-wash",
        "--backup-border",
        "--backup-copy",
        "--backup-surface-raised",
        "--backup-warning-border",
        "--backup-warning-ink",
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") >= 1

    assert "--backup-warm" not in css
    assert 'class="backup-center-page" data-page="backup-center"' in template
    assert "document.querySelector('[data-page=\"backup-center\"]')" in backup_js


def test_body_composition_tokens_keep_page_ownership_and_shared_heading_winner() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "body_composition.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-body-composition.css").read_text(
        encoding="utf-8"
    )
    body_composition_js = (
        ROOT / "static" / "js" / "modules" / "body-composition.js"
    ).read_text(encoding="utf-8")

    # The route bundle owns its exact feature vocabulary and loads before the
    # shared theme. Generic heading color remains shared-components owned under
    # both theme states.
    assert base.index("{% block page_css %}") < base.index("css/theme-dark.css")
    assert css.startswith(".body-composition-page {")
    assert ":root" not in css
    assert "!important" not in css

    for token in (
        "--bc-band-tick",
        "--bc-copy-muted",
        "--bc-copy-supporting",
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") >= 2

    assert css.count("--bc-accent-soft:") == 1
    assert "[data-theme='dark'] .body-composition-header h1" not in css
    heading_block = re.search(
        r"\.body-composition-header h1\s*\{(?P<body>.*?)\}", css, re.DOTALL
    )
    assert heading_block is not None
    assert "color:" not in heading_block.group("body")
    assert "margin-bottom: 0.4rem;" in heading_block.group("body")

    assert css.count("@media (min-width: 1100px)") == 1
    assert 'data-page="body-composition"' in template
    assert 'data-bc-app="true"' in template
    assert "document.querySelector('[data-bc-app]')" in body_composition_js


def test_progression_tokens_preserve_route_ownership_and_live_dark_cascade() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "progression_plan.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-progression.css").read_text(
        encoding="utf-8"
    )
    components = (ROOT / "static" / "css" / "components.css").read_text(
        encoding="utf-8"
    )
    progression_js = (
        ROOT / "static" / "js" / "modules" / "progression-plan.js"
    ).read_text(encoding="utf-8")

    # Flatpickr loads immediately before the route bundle. The route remains
    # before the late shared motion/theme boundary, and no document-wide :has()
    # scope is introduced (it altered Progression mask compositing in WP4.2).
    assert template.index("flatpickr.min.css") < template.index(
        "css/pages-progression.css"
    )
    assert base.index("{% block page_css %}") < base.index("css/motion.css")
    assert base.index("css/motion.css") < base.index("css/theme-dark.css")
    assert "html:has(" not in css
    assert ":root" not in css

    for token, minimum_consumers in (
        ("--progression-accent", 5),
        ("--progression-badge-ink", 2),
        ("--progression-badge-surface", 2),
        ("--progression-copy-muted", 6),
        ("--progression-copy-muted-dark", 2),
        ("--progression-success", 3),
        ("--progression-success-dark", 2),
        ("--progression-calendar-accent", 3),
        ("--progression-calendar-border", 3),
        ("--progression-calendar-ink", 5),
        ("--progression-calendar-surface", 5),
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") >= minimum_consumers

    # Shared important component rules own headings, suggestion-card titles,
    # dark card copy, and table colors. The former route dark card-copy rule
    # was dead; the remaining fatigue dark rule owns only its live mix changes.
    assert ".glass-neumorph-card .card-title" in components
    assert (
        "[data-theme='dark'] .progression-plan-container "
        ".glass-neumorph-card .card-text"
    ) in components
    assert "[data-theme='dark'] .progression-plan-container .suggestion-card .card-text" not in css
    assert "[data-theme='dark'] .progression-fatigue__headline" not in css
    assert "[data-theme='dark'] .progression-fatigue__advisory" not in css
    dark_chip = re.search(
        r"\[data-theme='dark'\] \.progression-fatigue__chip\s*\{(?P<body>.*?)\}",
        css,
        re.DOTALL,
    )
    assert dark_chip is not None
    assert "background:" in dark_chip.group("body")
    assert "border-color:" in dark_chip.group("body")
    assert re.search(r"^\s*color\s*:", dark_chip.group("body"), re.MULTILINE) is None

    # Live route-owned behavior and geometry selectors stay intact.
    for selector in (
        "#goalSettingModal {",
        "#goalSettingModal.show {",
        "[data-theme='dark'] .current-goals .goal-status-badge.bg-primary {",
        "[data-theme='dark'] .current-goals .goal-status-badge.bg-success {",
        "[data-theme='dark'] .flatpickr-calendar {",
        ".progression-fatigue {",
    ):
        assert css.count(selector) == 1
    assert css.count("@media (max-width: 767.98px)") == 1
    assert css.count("@media (max-width: 768px)") == 1

    assert 'class="progression-plan-container"' in template
    assert 'id="exerciseSelect"' in template
    assert 'id="suggestionsFatigueContext" hidden' in template
    assert "document.getElementById('exerciseSelect')" in progression_js
    assert "section.className = 'progression-fatigue'" in progression_js


def test_volume_splitter_tokens_preserve_runtime_ownership_and_dark_winners() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "volume_splitter.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-volume-splitter.css").read_text(
        encoding="utf-8"
    )
    components = (ROOT / "static" / "css" / "components.css").read_text(
        encoding="utf-8"
    )
    volume_js = (
        ROOT / "static" / "js" / "modules" / "volume-splitter.js"
    ).read_text(encoding="utf-8")

    # The route remains between a11y and the late motion/theme boundary. No
    # document-wide :has() scope is introduced (WP4.2 proved it raster-unsafe).
    assert base.index("css/a11y.css") < base.index("{% block page_css %}")
    assert base.index("{% block page_css %}") < base.index("css/motion.css")
    assert base.index("css/motion.css") < base.index("css/theme-dark.css")
    assert "html:has(" not in css
    assert css.count(":root {") == 2
    assert css.count("[data-theme='dark'] {") == 2

    for token, minimum_consumers in (
        ("--volume-status-low", 3),
        ("--volume-status-optimal", 2),
        ("--volume-status-alert", 4),
        ("--volume-positive-accent", 2),
        ("--volume-heading-ink", 3),
        ("--volume-pill-optimal-accent", 2),
        ("--volume-header-accent-soft", 2),
        ("--volume-dark-ink", 12),
        ("--volume-dark-surface", 4),
        ("--volume-dark-surface-subtle", 2),
        ("--volume-dark-border", 5),
        ("--volume-dark-focus-ring", 2),
        ("--volume-dark-focus-halo", 2),
        ("--volume-header-shadow-dark", 2),
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") >= minimum_consumers

    # Components own the dark panel surface, heading ink, and table cell ink.
    # The route keeps its live table surface/border geometry and status palette.
    assert "[data-theme='dark'] .volume-splitter-container .results-section" in components
    assert "[data-theme='dark'] .volume-splitter-container .table thead th" in components
    assert "[data-theme='dark'] .volume-splitter-container .table tbody td" in components
    assert '[data-theme="dark"] .suggestion-card {' not in css
    assert "[data-theme='dark'] .volume-history-section {" not in css

    results_block = re.search(
        r"\[data-theme='dark'\] \.results-section\s*\{(?P<body>.*?)\}",
        css,
        re.DOTALL,
    )
    heading_block = re.search(
        r"\[data-theme='dark'\] \.results-section thead th\s*\{(?P<body>.*?)\}",
        css,
        re.DOTALL,
    )
    cell_block = re.search(
        r"\[data-theme='dark'\] \.results-section tbody td\s*\{(?P<body>.*?)\}",
        css,
        re.DOTALL,
    )
    assert results_block is not None
    assert "background" not in results_block.group("body")
    assert "border-color: var(--volume-dark-border) !important;" in results_block.group("body")
    assert heading_block is not None
    assert "background" not in heading_block.group("body")
    assert re.search(r"^\s*color\s*:", heading_block.group("body"), re.MULTILINE) is None
    assert cell_block is not None
    assert "background: var(--volume-dark-surface) !important;" in cell_block.group("body")
    assert re.search(r"^\s*color\s*:", cell_block.group("body"), re.MULTILINE) is None

    # All existing responsive boundaries and runtime-created hooks stay intact.
    for breakpoint in ("1400px", "1200px", "768px", "1199.98px", "767.98px"):
        assert css.count(f"@media (max-width: {breakpoint})") == 1
    for hook in (
        'id="volume-splitter-app"',
        'id="sliders" class="volume-sliders"',
        'class="results-section d-none"',
        'class="ai-suggestions-section d-none"',
        'class="volume-history-section"',
        'id="deleteVolumePlanModal"',
    ):
        assert hook in template
    assert "row.className = 'muscle-row mb-3'" in volume_js
    assert "card.dataset.type = suggestion.type" in volume_js
    assert "'volume-value-pill--excessive'" in volume_js
    assert "getPropertyValue('--volume-track-bg')" in volume_js
