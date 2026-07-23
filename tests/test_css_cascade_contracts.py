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


def test_welcome_tokens_extract_exact_values_without_dead_custom_properties() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "welcome.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "pages-welcome.css").read_text(encoding="utf-8")

    # Route bundle loads in the page_css block, after a11y and before the late
    # motion/theme boundary; no document-wide :has() scope is introduced.
    assert base.index("css/a11y.css") < base.index("{% block page_css %}")
    assert base.index("{% block page_css %}") < base.index("css/motion.css")
    assert base.index("css/motion.css") < base.index("css/theme-dark.css")
    assert "html:has(" not in css

    # New page-local semantic tokens: each defined once and consumed by the
    # exact-repeat white-ink / translucent-white-overlay sites it replaced.
    for token, minimum_consumers in (
        ("--wl-on-accent", 21),
        ("--wl-overlay-soft", 3),
        ("--wl-overlay-strong", 5),
        ("--wl-overlay-border", 2),
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") >= minimum_consumers

    # Dead (unreferenced) custom properties were removed outright: the featured
    # token trio the cards never consumed, plus the orphaned glow/info/duration.
    for dead in (
        "--wl-featured-gradient",
        "--wl-featured-start",
        "--wl-featured-end",
        "--wl-accent-glow",
        "--wl-shadow-glow",
        "--wl-info",
        "--wl-duration-slow",
    ):
        assert dead not in css

    # No raw white literal survives outside the token definitions.
    for literal in (
        "color: #ffffff !important;",
        "color: #ffffff;",
        "border-color: #ffffff !important;",
        "rgba(255, 255, 255, 0.25) !important;",
        "rgba(255, 255, 255, 0.15) !important;",
        "rgba(255, 255, 255, 0.4) !important;",
    ):
        assert literal not in css
    assert css.count("rgba(255, 255, 255, 0.25)") == 1
    assert css.count("rgba(255, 255, 255, 0.15)") == 1
    assert css.count("rgba(255, 255, 255, 0.4)") == 1
    # #ffffff now lives only in the --wl-surface and --wl-on-accent definitions.
    assert css.count("#ffffff") == 2

    # The live featured brand rules keep their own hardcoded !important gradient;
    # the dark override, responsive breakpoints, and page hook stay intact.
    assert (
        "background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%) !important;"
        in css
    )
    assert "[data-theme='dark'] #welcome .bento-featured {" in css
    for breakpoint in ("1024px", "768px", "480px"):
        assert css.count(f"@media (max-width: {breakpoint})") == 1
    assert 'id="welcome" data-page="welcome"' in template


def test_session_summary_tokens_extract_exact_values_value_preserving() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "session_summary.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-session-summary.css").read_text(
        encoding="utf-8"
    )

    # Route bundle loads in the page_css block, after a11y and before the late
    # motion/theme boundary; no document-wide :has() scope is introduced.
    assert base.index("css/a11y.css") < base.index("{% block page_css %}")
    assert base.index("{% block page_css %}") < base.index("css/motion.css")
    assert base.index("css/motion.css") < base.index("css/theme-dark.css")
    assert "html:has(" not in css

    # New page-local semantic tokens: each defined once and consumed by the exact
    # count of the repeated literal it replaced. Distinct roles keep distinct
    # tokens even when values coincide (--ss-label-ink vs --ss-dark-border-strong
    # are both #495057 but light label ink vs dark border).
    for token, consumers in (
        ("--ss-table-border", 6),
        ("--ss-label-ink", 2),
        ("--ss-dark-ink", 9),
        ("--ss-dark-ink-bright", 12),
        ("--ss-dark-border", 5),
        ("--ss-dark-border-strong", 6),
        ("--ss-dark-surface", 3),
        ("--ss-dark-surface-deep", 2),
        ("--ss-dark-elevated", 3),
        ("--ss-dark-cell", 2),
        ("--ss-dark-hover", 2),
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") == consumers

    # Every extracted literal now survives only in its single token definition;
    # #495057 backs two distinct-role tokens so it appears exactly twice.
    for literal in (
        "#e0e0e0",
        "#404040",
        "#d0d0d0",
        "#212529",
        "#343a40",
        "#2d2d2d",
        "#3d3d3d",
        "#1a1a1a",
    ):
        assert css.count(literal) == 1
    assert css.count("#495057") == 2
    assert "--ss-dark-ink-bright: #fff;" in css
    assert "color: #fff;" not in css
    assert "color: #fff !important;" not in css

    # Shared volume-badge classification colors and the light striping/glass
    # literals are deliberately left untouched (single-use / shared semantics).
    for shared in ("#dc3545", "#fd7e14", "#198754", "#6f42c1"):
        assert shared in css
    assert "background-color: #ffffff !important;" in css
    assert css.count("@media") == 9
    assert 'id="session-summary-container"' in template


def test_weekly_summary_tokens_extract_values_and_drop_dead_session_arms() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "weekly_summary.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-weekly-summary.css").read_text(
        encoding="utf-8"
    )

    # Route bundle loads in the page_css block, after a11y and before the late
    # motion/theme boundary; no document-wide :has() scope is introduced.
    assert base.index("css/a11y.css") < base.index("{% block page_css %}")
    assert base.index("{% block page_css %}") < base.index("css/motion.css")
    assert base.index("css/motion.css") < base.index("css/theme-dark.css")
    assert "html:has(" not in css

    # New page-local semantic tokens mirror the WP4.3f Session Summary set (the
    # two bundles were byte-identical for this region). Each is defined once and
    # consumed by the exact count of the repeated literal it replaced. Distinct
    # roles keep distinct tokens even when values coincide (--wk-label-ink vs
    # --wk-dark-border-strong are both #495057 but light label ink vs dark
    # border, split by CSS property).
    for token, consumers in (
        ("--wk-table-border", 6),
        ("--wk-label-ink", 2),
        ("--wk-dark-ink", 9),
        ("--wk-dark-ink-bright", 12),
        ("--wk-dark-border", 5),
        ("--wk-dark-border-strong", 6),
        ("--wk-dark-surface", 3),
        ("--wk-dark-surface-deep", 2),
        ("--wk-dark-elevated", 3),
        ("--wk-dark-cell", 2),
        ("--wk-dark-hover", 2),
    ):
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") == consumers

    # Every extracted literal now survives only in its single token definition,
    # except two intentional keeps: #d0d0d0 also backs the weekly-only
    # #isolated_muscles_filter form-control border (a distinct single-use role),
    # and #495057 backs two distinct-role tokens.
    for literal in (
        "#e0e0e0",
        "#404040",
        "#212529",
        "#343a40",
        "#2d2d2d",
        "#3d3d3d",
        "#1a1a1a",
    ):
        assert css.count(literal) == 1
    assert css.count("#d0d0d0") == 2
    assert css.count("#495057") == 2
    assert "--wk-dark-ink-bright: #fff;" in css
    assert "color: #fff;" not in css
    assert "color: #fff !important;" not in css

    # Finding (a): the dead #session-summary-* selector arms — those ids render
    # only on session_summary.html — were dropped; the live #weekly-summary
    # arms and every declaration remain.
    assert "#session-summary" not in css
    assert "#weekly-summary-container" in css
    assert 'id="weekly-summary-container"' in template

    # The weekly-only filter block stays route-owned and value-untouched
    # (single-use literals: form border #d0d0d0, label ink #505050).
    assert "#isolated_muscles_filter" in css
    assert css.count("#505050") == 1

    # Finding (b): the two parallel dark table systems both retain live owners
    # (audited in both themes), so their single-use dark literals are left
    # untouched rather than folded into tokens.
    for kept_dark in ("#252525", "#2a2a2a", "#2c3034", "#b0b0b0"):
        assert kept_dark in css

    # Shared volume-badge classification colors and the light striping literal
    # are deliberately left untouched (shared semantics); breakpoints preserved.
    for shared in ("#dc3545", "#fd7e14", "#198754", "#6f42c1"):
        assert shared in css
    assert "background-color: #ffffff !important;" in css
    assert css.count("@media") == 9


def test_user_profile_tokens_extract_repeated_operands_value_preserving() -> None:
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "user_profile.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-user-profile.css").read_text(
        encoding="utf-8"
    )

    # Route bundle loads in the page_css block, after a11y and before the late
    # motion/theme boundary; no document-wide :has() scope is introduced.
    assert base.index("css/a11y.css") < base.index("{% block page_css %}")
    assert base.index("{% block page_css %}") < base.index("css/motion.css")
    assert base.index("css/motion.css") < base.index("css/theme-dark.css")
    assert "html:has(" not in css

    # WP4.3h is a pure value-preserving extraction. Unlike the summary bundles
    # (which carried repeated *direct* hex values), this bundle was authored on
    # the shared token system: nearly every hex is a var(--token, #fallback)
    # fallback and is left untouched. Only the genuinely repeated *raw* operands
    # were extracted into page-local tokens, each defined once and consumed by
    # the exact count of the literal it replaced.
    theme_independent = (
        ("--up-band-partial", 4),
        ("--up-band-mostly", 4),
        ("--up-band-fully", 4),
        ("--up-autosave-saved", 2),
        ("--up-autosave-error", 2),
        ("--up-region-faint", 2),
    )
    dark_scoped = (
        ("--up-dark-shadow-ink", 3),
        ("--up-dark-region-faint", 2),
    )
    for token, consumers in theme_independent + dark_scoped:
        assert css.count(f"{token}:") == 1
        assert css.count(f"var({token})") == consumers

    # Theme-independent tokens live in :root; the dark-only shadow/region tokens
    # live in the [data-theme='dark'] block so they resolve only under the dark
    # root, exactly where their consuming rules apply.
    root_block = css[css.index(":root {"):css.index("}", css.index(":root {"))]
    for token, _ in theme_independent:
        assert token in root_block
    dark_start = css.index("[data-theme='dark'] {")
    dark_block = css[dark_start:css.index("}", dark_start)]
    for token, _ in dark_scoped:
        assert token in dark_block

    # Every extracted literal now survives only in its single token definition.
    # The coverage-band "mostly" hue coincides with the accent value, but it is a
    # distinct fixed classification role: #4c6ef5 still appears as the 68 shared
    # var(--accent, #4c6ef5) fallbacks plus the one --up-band-mostly definition.
    for extracted in (
        "#f59f00",
        "#2f9e44",
        "#2eb872",
        "#d93b3b",
        "rgba(150, 150, 150, 0.10)",
        "rgba(0, 0, 0, 0.25)",
        "rgba(180, 186, 208, 0.06)",
    ):
        assert css.count(extracted) == 1
    assert "--up-band-mostly: #4c6ef5;" in css
    assert css.count("#4c6ef5") == 69

    # #1f2937 is a repeated raw operand (2x) that is deliberately left inline:
    # both its declarations also carry the shared var(--accent, #4c6ef5) fallback,
    # so tokenizing it would keep those declarations flagged while adding a token
    # definition warning — a net increase. Every extracted token is net-neutral
    # or better, keeping the hardcoded-value category non-increasing.
    assert css.count("#1f2937") == 2

    # The color-mix darkening/lightening keyword operands are intentionally kept:
    # the disallowed-value rule does not flag the `black`/`white` keywords, they
    # are mixing primitives rather than semantic colors, and no prior bundle
    # tokenized them. Their counts are pinned so the extraction stays minimal.
    assert css.count(", black)") == 10
    assert css.count(", white)") == 3

    # The bundle stays !important-free and its breakpoints are preserved.
    assert "!important" not in css
    assert css.count("@media") == 14

    # Template runtime hooks intact.
    assert 'class="user-profile-page"' in template
    assert 'id="profile-lifts-form"' in template


def test_workout_plan_dormant_filter_glass_cluster_removed() -> None:
    template = (ROOT / "templates" / "workout_plan.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )
    dropdown_js = (
        ROOT / "static" / "js" / "modules" / "workout-dropdowns.js"
    ).read_text(encoding="utf-8")
    view_mode_js = (
        ROOT / "static" / "js" / "modules" / "filter-view-mode.js"
    ).read_text(encoding="utf-8")

    # WP4.3i-i supersedes the abandoned i-a token extraction: browser
    # declaration-owner proof showed that the old light/dark glass surfaces
    # never win after workout-dropdown enhancement. No soon-to-be-deleted
    # --wp-dark-* vocabulary is introduced.
    assert "--wp-dark-" not in css
    for dead_pattern in (
        r"(?m)^\.filter-dropdown:hover\s*\{\s*box-shadow:",
        r"(?m)^\.filter-dropdown\.filter-active,",
        r"(?m)^\.routine-dropdown",
        r"(?m)^#exercise-search\.uniform-input",
        r"(?m)^\.filter-view-toggle",
        r"(?m)^\[data-theme='dark'\] \.filters-section",
        r"(?m)^\[data-theme='dark'\] \.filter-dropdown \{",
        r"(?m)^\[data-theme='dark'\] \.exercise-dropdown",
    ):
        assert not re.search(dead_pattern, css)

    # The few declarations that did own computed values remain: the hidden
    # native filter's positioning/focus mechanics and pseudo highlight, plus
    # the short-lived exercise animation hook. Layout rules and both existing
    # cascade layers are deliberately outside the removal.
    assert re.search(
        r"\.filter-dropdown\s*\{\s*position:\s*relative;\s*\}", css
    )
    assert "select.filter-dropdown:focus {\n    z-index: 1050 !important;" in css
    assert css.count(".filter-dropdown::before") == 2
    assert ".exercise-dropdown.filter-applied {\n    animation: glowPulse" in css
    assert "@keyframes glowPulse" in css
    assert "#filters-form .form-label" in css
    assert css.count("@media") == 44
    assert "@layer workout-dropdowns {" in css
    assert "@layer workout {" in css

    # The route still renders native select hooks and the enhancement still
    # converts them to wpdd controls. The retired naming toggle has no template
    # consumer and its legacy factory has no in-repo invocation (definition
    # only), which is why route-bundle toggle CSS had zero matched elements.
    assert 'class="form-select uniform-dropdown filter-dropdown' in template
    assert 'class="form-select uniform-dropdown exercise-dropdown' in template
    assert "select.classList.add('wpdd-native')" in dropdown_js
    assert "filter-view-toggle" not in template
    assert view_mode_js.count("createToggleButton(") == 1


def test_workout_plan_wpdd_route_ownership_cleanup() -> None:
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )
    components = (ROOT / "static" / "css" / "components.css").read_text(
        encoding="utf-8"
    )
    a11y = (ROOT / "static" / "css" / "a11y.css").read_text(encoding="utf-8")
    dropdown_js = (
        ROOT / "static" / "js" / "modules" / "workout-dropdowns.js"
    ).read_text(encoding="utf-8")

    layer_start = css.index("@layer workout-dropdowns {")
    global_popover_start = css.index("Global Popover Styles", layer_start)
    dropdown_layer = css[layer_start:global_popover_start]
    global_popover = css[
        global_popover_start : css.index("@layer workout {", global_popover_start)
    ]

    # Runtime appends every popover to body, so the old #workout-descendant copy
    # and its mobile selector arm could never match. The global owner stays live.
    assert "document.body.appendChild(popover)" in dropdown_js
    assert '#workout[data-page="workout-plan"] .wpdd-popover' not in dropdown_layer
    assert ".wpdd-search" not in dropdown_layer
    assert ".wpdd-count-indicator" not in dropdown_layer
    assert ".wpdd-popover {" in global_popover
    assert "@media (max-width: 768px)" in global_popover

    # No route consumer generates a routine-flavored wpdd button. The rendered
    # filter/exercise surface and state declarations are owned by calm-glass
    # components, while keyboard focus is owned by the global a11y contract.
    assert ".wpdd-routine" not in dropdown_layer
    assert ".wpdd-button.wpdd-filter" not in dropdown_layer
    assert ".wpdd-button.wpdd-exercise" not in dropdown_layer
    assert ".wpdd-button:hover:not(:disabled)" not in dropdown_layer
    assert ".wpdd-button:focus-visible" not in dropdown_layer
    assert ".wpdd-button:disabled" not in dropdown_layer
    assert '.wpdd-button[aria-expanded="true"] {' not in dropdown_layer
    assert '#workout[data-page="workout-plan"] .wpdd-button,' in components
    assert ".wpdd-button:hover:not(:disabled)," in components
    assert ".wpdd-button:disabled," in components
    assert ".wpdd-button.wpdd-filter.filter-active {" in components
    assert "*:focus-visible," in a11y

    # Route-owned mechanics remain: native-select anchoring/hiding, button
    # transition/truncation/active behavior, and placeholder/caret state.
    for live_contract in (
        '#workout[data-page="workout-plan"] .wpdd {',
        "position: relative;",
        '#workout[data-page="workout-plan"] .wpdd-native {',
        "pointer-events: none;",
        "z-index: -1;",
        '#workout[data-page="workout-plan"] .wpdd-button {',
        "gap: var(--wpdd-gap);",
        "transition: background var(--wpdd-transition)",
        "text-overflow: ellipsis;",
        ".wpdd-button:active:not(:disabled)",
        ".wpdd-button .wpdd-placeholder",
        ".wpdd-button .wpdd-caret",
        '.wpdd-button[aria-expanded="true"] .wpdd-caret',
        "@media (prefers-reduced-motion: reduce)",
        "@media (prefers-contrast: high)",
    ):
        assert live_contract in dropdown_layer

    # Two pre-existing zero-consumer tokens are removed. Every remaining wpdd
    # token has at least one consumer beyond its definition/override.
    assert "--wpdd-accent-hover" not in css
    assert "--wpdd-radius" not in css
    for token in (
        "--wpdd-font",
        "--wpdd-fs",
        "--wpdd-bg",
        "--wpdd-surface",
        "--wpdd-text",
        "--wpdd-muted",
        "--wpdd-border",
        "--wpdd-accent",
        "--wpdd-gap",
        "--wpdd-shadow",
        "--wpdd-shadow-lg",
        "--wpdd-transition",
    ):
        assert css.count(token) >= 2


def test_workout_plan_page_header_and_collapsible_frame_ownership_cleanup() -> None:
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )
    components = (ROOT / "static" / "css" / "components.css").read_text(
        encoding="utf-8"
    )
    theme_dark = (ROOT / "static" / "css" / "theme-dark.css").read_text(
        encoding="utf-8"
    )
    template = (ROOT / "templates" / "workout_plan.html").read_text(
        encoding="utf-8"
    )
    page_js = (
        ROOT / "static" / "js" / "modules" / "workout-plan-page.js"
    ).read_text(encoding="utf-8")

    start = css.index("Page Header - 2026 Glass/Neumorphic Style")
    end = css.index("Collapse Toggle Buttons - Modern 2025 Refresh", start)
    cluster = css[start:end]

    # Browser declaration-removal proof showed these route declarations never
    # win over Bootstrap utilities or the shared unlayered/calm-glass owners.
    # The direct page header has no h2 consumer; the table h2 is nested below a
    # separate .table-header and never matched this selector arm.
    for dormant in (
        "margin-bottom: var(--wp-gap-lg);",
        "text-align: center;",
        '>.container-fluid>.table-header h2',
        "font-size: var(--wp-fs-title);",
        "width: 60px;",
        "width: 80px;",
        '.unified-frames-container {',
        '.collapsible-frame:hover {',
        '.frame-header::before {',
        '.frame-header.frame-header-2025 {',
        '.frame-header-2025 .frame-header-right {',
        '.frame-title::after,',
        "[data-theme='dark'] #workout[data-page=\"workout-plan\"] .collapsible-frame",
        "[data-theme='dark'] #workout[data-page=\"workout-plan\"] .frame-header::before",
    ):
        assert dormant not in cluster

    # The shared component system remains the actual surface/layout/pseudo
    # owner; the late dark theme is why the route retains one explicit dark
    # frame-header blur override.
    for shared_owner in (
        '#workout[data-page="workout-plan"] .frame-calm-glass,',
        '#workout[data-page="workout-plan"] .frame-calm-glass .frame-header,',
        '#workout[data-page="workout-plan"] .frame-calm-glass .frame-header.frame-header-2025 {',
        '#workout[data-page="workout-plan"] .frame-calm-glass .frame-header-right {',
        ".collapsible-frame {",
        ".frame-header::before {",
        ".frame-title::after,",
    ):
        assert shared_owner in components
    assert ':where([data-theme="dark"] .frame-header) {' in theme_dark
    assert "backdrop-filter: blur(8px) !important;" in theme_dark

    # Live route ownership is retained: page-header positioning/surface and
    # hover transition, frame/title repaint safeguards, and the dark title
    # values that still win the important cascade.
    for live_contract in (
        "margin-top: -55px;",
        "padding: var(--wp-padding-sm) var(--wp-padding-xl);",
        "backdrop-filter: blur(8px);",
        "position: relative;",
        "overflow: hidden;",
        ">.container-fluid>.table-header::before {",
        ">.container-fluid>.table-header h1 {",
        "letter-spacing: -0.02em;",
        "box-shadow: 0 2px 8px rgba(79, 140, 255, 0.3);",
        "transition: width var(--wp-transition), box-shadow var(--wp-transition);",
        "box-shadow: 0 4px 12px rgba(79, 140, 255, 0.4);",
        "border-color: rgba(255, 255, 255, 0.08);",
        "backdrop-filter: none !important;",
        "color: var(--wp-text) !important;",
        "border-radius: 0 !important;",
        "padding-bottom: 0 !important;",
    ):
        assert live_contract in cluster
    assert len(
        re.findall(r"(?m)^\s+backdrop-filter: none !important;$", cluster)
    ) == 3
    assert len(
        re.findall(r"(?m)^\s+-webkit-backdrop-filter: none !important;$", cluster)
    ) == 3

    # No artificial packet-local token is introduced: the remaining repeated
    # raw values have different roles (gleam, shadow, border, or text shadow).
    assert "--wp-header-" not in cluster
    assert "--wp-frame-" not in cluster

    # Runtime topology and collapse semantics remain wired.
    assert template.count('class="collapsible-frame') == 3
    assert template.count("frame-header-2025") == 3
    assert template.count('class="collapse-toggle"') == 3
    assert '<header class="table-header text-center"' in template
    assert '<h1>Workout Plan</h1>' in template
    assert '<h2 id="workout-plan-table-heading"' in template
    assert "const toggleButtons = document.querySelectorAll('.collapse-toggle');" in page_js
    assert "frame.classList.toggle('collapsed');" in page_js
    assert "this.setAttribute('aria-expanded', !isExpanded);" in page_js


def test_workout_plan_muscle_selector_drops_dead_local_token_fallbacks() -> None:
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )
    tokens = (ROOT / "static" / "css" / "tokens.css").read_text(encoding="utf-8")

    region = css[css.index("MUSCLE SELECTOR STYLES v3.0"):]

    # tokens.css always defines these Calm-Glass tokens at :root (light), so the
    # component's inline var(--token, #hex) fallbacks never rendered. Removing
    # them is exact-value: the token is always the used value.
    for token_def in (
        "--accent: #4c6ef5;",
        "--surface-1: #f4f6fa;",
        "--surface-2: #ffffff;",
        "--ink-1: #0f1220;",
        "--ink-2: #4a5170;",
        "--success: #10b981;",
        "--warning: #f59e0b;",
        "--danger: #ef4444;",
    ):
        assert token_def in tokens

    # No dead local-token hex fallback remains in the muscle-selector section.
    local_fallback = re.compile(
        r"var\(\s*--(?:accent|accent-ink|surface-0|surface-1|surface-2"
        r"|ink-1|ink-2|ink-3|success|warning|danger)\s*,\s*#[0-9a-fA-F]{3,8}\s*\)"
    )
    assert local_fallback.search(region) is None

    # The tokens are now consumed bare, matching the sibling-bundle convention.
    for bare in (
        "background: var(--accent);",
        "color: var(--ink-2);",
        "color-mix(in srgb, var(--accent) 75%, var(--ink-1))",
        "color-mix(in srgb, var(--danger) 78%, var(--ink-2))",
        "background: color-mix(in srgb, var(--surface-1) 80%, black)",
    ):
        assert bare in region

    # Scope boundary: Bootstrap-integrated var(--bs-*, #hex) fallbacks are a
    # separate concern and were deliberately left intact.
    assert "var(--bs-body-color, #212529)" in region
    assert "var(--bs-secondary-color, #6c757d)" in region

    # No artificial packet-local token was invented; the fix is pure removal.
    assert "--wp-ms-" not in region


def test_workout_plan_wpdd_popover_drops_dead_local_token_fallbacks() -> None:
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )

    # The --wpdd-* dropdown tokens are page-local: this bundle defines them in its
    # own :root (light) and [data-theme="dark"] blocks, loaded once before use, so
    # the .wpdd-popover component's var(--wpdd-*, fallback) fallbacks never
    # rendered. Removing them is exact-value (each fallback equalled the light
    # token). Non-remapped tokens (--wpdd-accent/-font) inherit :root in dark.
    for token_def in (
        "--wpdd-bg: #ffffff;",
        "--wpdd-surface: #f8f9fa;",
        "--wpdd-text: #1a1f2e;",
        "--wpdd-muted: #6b7280;",
        "--wpdd-border: #e5e7eb;",
        "--wpdd-accent: #4f8cff;",
    ):
        assert token_def in css

    # The live popover component remains (its class is set in workout-dropdowns.js).
    assert ".wpdd-popover {" in css

    # No dead local-token fallback (hex, shadow, or font stack) remains for any
    # --wpdd-* consumption site.
    assert re.search(r"var\(\s*--wpdd-[a-z]+\s*,", css) is None

    # Tokens are now consumed bare, matching the sibling Enhanced Dropdown block.
    for bare in (
        "background: var(--wpdd-bg);",
        "color: var(--wpdd-text);",
        "box-shadow: var(--wpdd-shadow);",
        "font-family: var(--wpdd-font);",
        "color-mix(in srgb, var(--wpdd-accent) 24%, transparent)",
    ):
        assert bare in css


def test_workout_plan_table_drops_dead_global_token_fallbacks() -> None:
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )
    tokens = (ROOT / "static" / "css" / "tokens.css").read_text(encoding="utf-8")

    # The Calm-Glass tokens the Workout Plan Table section consumes are always
    # defined at :root (light) in tokens.css, loaded before this bundle, so the
    # section's var(--token, #hex) fallbacks never rendered. Several fallbacks did
    # not even match the active token (e.g. var(--surface-1, #1a2332) in a dark
    # rule while --surface-1 is #f4f6fa light), i.e. misleading dead code; removal
    # preserves the current rendered value (the token).
    for token_def in (
        "--accent: #4c6ef5;",
        "--surface-1: #f4f6fa;",
        "--surface-2: #ffffff;",
        "--ink-1: #0f1220;",
        "--ink-2: #4a5170;",
    ):
        assert token_def in tokens

    # Scope the assertion to the Workout Plan Table section.
    start = css.index("Workout Plan Table - 2026 Glass")
    region = css[start:css.index("Responsive Design", start)]

    dead = re.compile(
        r"var\(\s*--(?:accent|ink-1|ink-2|surface-0|surface-1|surface-2)"
        r"\s*,\s*#[0-9a-fA-F]{3,8}\s*\)"
    )
    assert dead.search(region) is None

    # Tokens are now consumed bare inside their color-mix()/direct usages; the
    # per-rule !important weighting is unchanged (fallback removal only).
    for bare in (
        "color-mix(in srgb, var(--surface-2) 90%, var(--accent) 10%) !important",
        "border: 1px solid color-mix(in srgb, var(--accent) 26%, transparent) !important",
        "color: var(--ink-2) !important",
        "color-mix(in srgb, var(--surface-1) 84%, var(--accent) 16%) !important",
    ):
        assert bare in region


def test_workout_plan_drops_remaining_dead_defined_token_fallbacks() -> None:
    css = (ROOT / "static" / "css" / "pages-workout-plan.css").read_text(
        encoding="utf-8"
    )
    tokens = (ROOT / "static" / "css" / "tokens.css").read_text(encoding="utf-8")

    # These page-local (@layer workout) tokens are defined before use, so their
    # var(--token, fallback) fallbacks never rendered.
    for token_def in ("--wp-fw-medium: 500;", "--wp-text-muted: #6b7280;",
                      "--wp-border: #e5e7eb;"):
        assert token_def in css
    # The --input-* sizing tokens are always defined at :root in tokens.css.
    for token_def in ("--input-height-md: 38px;", "--input-padding-x:",
                      "--input-padding-y:", "--input-font-size:"):
        assert token_def in tokens

    # The specific consumption sites are now bare.
    for bare in (
        "font-weight: var(--wp-fw-medium);",
        "color: var(--wp-text-muted);",
        "background: var(--wp-border);",
        "height: var(--input-height-md);",
        "padding: var(--input-padding-y) var(--input-padding-x);",
        "font-size: var(--input-font-size);",
    ):
        assert bare in css

    # Milestone invariant: the non-Bootstrap dead-fallback removal arc
    # (WP4.3i-d/-e/-f/-g) is complete. Every remaining non-`--bs-*` var() fallback
    # in the bundle is one of the two intentionally-LIVE ones:
    #   - var(--superset-row-color, …): assigned dynamically inline per row.
    #   - var(--wpdd-shadow-lg, …): references an undefined token.
    fallbacks = [
        m.group(0)
        for m in re.finditer(r"var\(\s*--[a-z0-9-]+\s*,", css)
        if "--bs-" not in m.group(0)
    ]
    offenders = [
        f for f in fallbacks
        if "--superset-row-color" not in f and "--wpdd-shadow-lg" not in f
    ]
    assert offenders == [], offenders
