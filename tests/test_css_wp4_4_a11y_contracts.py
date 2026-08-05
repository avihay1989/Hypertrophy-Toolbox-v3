"""WP4.4-d1 + d2 cascade contracts for `static/css/a11y.css`.

d1 deleted a superseded generation of the scale / accessibility-menu UI. These
contracts lock the premises that deletion rested on, and -- just as importantly
-- lock the d1/d2 boundary and the accessibility guarantees d1 was required to
preserve.

d2 re-weighted exactly one annotation and RETAINED the other 50. Its contracts
lock both halves of that result: the certified removal keeps its declaration,
and the retentions -- especially the ones a reader would mistake for oversights
-- keep their `!important`.

Packet-owned. This file never edits, and must not be confused with, the shared
`tests/test_css_cascade_contracts.py`, which d1 and d2 run but do not touch
(Plan v2 section 4d -- only packet i may amend that file).

Every assertion here has a demonstrated red path; see
docs/CSS_PHASE4_WP4_4_D1_A11Y_EVIDENCE.md and
docs/CSS_PHASE4_WP4_4_D2_A11Y_EVIDENCE.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
A11Y = ROOT / "static" / "css" / "a11y.css"
TEMPLATES = ROOT / "templates"
JS = ROOT / "static" / "js"


def _css() -> str:
    return A11Y.read_text(encoding="utf-8")


def _strip_comments(css: str) -> str:
    """Blank comments while preserving BOTH length and line structure.

    Replacing a comment with `" " * len(...)` is length-preserving in characters
    but destroys the newlines inside multi-line comments, so any line number
    computed from the result is wrong -- it under-counts by one per commented
    newline. Measured on this file: the retained print rule sits at source line
    328, and the naive blanker placed it at 304.

    Nothing here does line arithmetic today, but a stripper that silently
    corrupts it is the exact hazard `.claude/rules/verification.md` calls out.
    """
    return re.sub(
        r"/\*.*?\*/",
        lambda m: "".join(c if c == "\n" else " " for c in m.group(0)),
        css,
        flags=re.S,
    )


# The legacy generation d1 deleted. Runtime census was 0 for every one of these
# across 11 routes x 2 themes x 10 widths x 8 data-scale levels, plus print and
# reduced-motion, and every deleted rule was visible to the synthetic oracle
# before deletion.
LEGACY_CLASSES = (
    "scale-control-label",
    "scale-btn-group",
    "accessibility-menu",
    "accessibility-section",
    "accessibility-section-title",
    "scale-labels",
    "scale-label",
    # Added by the bare `.scale-btn` packet, which deleted all eleven rules d1
    # had left in place. The `(?![\w-])` boundary in every consumer below is
    # what keeps the LIVE `.scale-btn-compact` generation out of these
    # assertions -- see LIVE_GENERATION.
    "scale-btn",
)

# The generation that IS live -- present in templates/base.html:190-202 and
# census > 0 in 160/160 measured contexts. d1 must not have touched these, and
# they are what makes the deletion safe rather than merely quiet.
LIVE_GENERATION = {
    "scale-control-compact": 5,
    "scale-btn-compact": 6,
    "scale-indicator": 2,
}


def test_legacy_scale_and_menu_generation_stays_deleted() -> None:
    """No rule targets the superseded generation.

    Red path: restoring any deleted block reintroduces its selector.
    """
    css = _strip_comments(_css())
    offenders = [c for c in LEGACY_CLASSES if re.search(rf"\.{re.escape(c)}(?![\w-])", css)]
    assert offenders == [], (
        f"a11y.css again styles the superseded generation: {offenders}. If one "
        "became reachable, re-run the census -- do not simply re-add the rule. "
        "For `scale-btn` the measured basis was 0 matches in 1,804/1,804 "
        "contexts; see docs/css_scale_btn_cleanup/EVIDENCE.md."
    )


def test_legacy_classes_are_still_unreachable() -> None:
    """Nothing in the app applies the deleted classes.

    This is the premise the deletion rests on, turned into a gate. It is the
    reason a JavaScript *query* was never accepted as proof of reachability:
    `accessibility.js` queries `.accessibility-dropdown` and
    `.scale-btn[data-scale]`, and both resolve to empty sets at runtime.
    d1 recorded that and stopped; the follow-up packet measured it and deleted
    the eleven bare `.scale-btn` rules, which is why that class now appears in
    LEGACY_CLASSES above.

    Red path: adding `class="accessibility-menu"` to a template, or
    `classList.add('scale-labels')` to a JS module, fails this test.
    """
    class_attr = re.compile(r"""class\s*=\s*["']([^"']*)["']""")
    add_call = re.compile(r"""classList\.(?:add|toggle|replace)\(\s*["']([\w-]+)["']""")

    offenders: list[str] = []
    for base, pattern in ((TEMPLATES, "**/*.html"), (JS, "**/*.js")):
        for path in base.glob(pattern):
            text = path.read_text(encoding="utf-8", errors="replace")
            applied: set[str] = set()
            for m in class_attr.finditer(text):
                applied.update(m.group(1).split())
            applied.update(add_call.findall(text))
            for cls in LEGACY_CLASSES:
                if cls in applied:
                    offenders.append(f"{path.relative_to(ROOT)} applies .{cls}")

    assert offenders == [], "a deleted a11y.css class is applied again: " + "; ".join(offenders)


def test_live_compact_generation_is_untouched() -> None:
    """The generation the app actually renders survives d1 intact.

    This is the known-live control that validated the whole oracle: if these
    were not visible, no deletion claim from the run would have counted.

    Red path: deleting any `.scale-btn-compact` rule fails on the count.
    """
    css = _strip_comments(_css())
    wrong = {}
    for cls, expected in LIVE_GENERATION.items():
        found = len(re.findall(rf"\.{re.escape(cls)}(?![\w-])", css))
        if found != expected:
            wrong[cls] = f"{found} (expected {expected})"
    assert wrong == {}, f"the live compact scale generation changed: {wrong}"


def test_live_compact_generation_is_still_rendered() -> None:
    """base.html still emits the live generation d1 preserved.

    Red path: removing `scale-control-compact` from base.html fails this test,
    which is what makes the previous test meaningful rather than circular.
    """
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    for cls in LIVE_GENERATION:
        # Boundary-anchored, NOT `cls in base`. A plain substring check stays
        # green when the class is renamed to `scale-control-compactXX`, because
        # the original name is a prefix of the new one -- the red-path proof
        # caught exactly that, and it is the same defect class as d1's
        # `"*:focus-visible," in css`.
        assert re.search(rf"{re.escape(cls)}(?![\w-])", base), (
            f"templates/base.html no longer renders .{cls}; the a11y.css rules "
            "d1 preserved for it would now be unreachable and must be re-audited"
        )
    assert "data-visual-scale-control" in base, (
        "base.html lost data-visual-scale-control, the registered visual "
        "blind-spot hook the d1 oracle used as a known-live control"
    )


def test_deleted_scale_control_rules_stay_deleted_by_source_shape() -> None:
    """`.scale-control` needs a SOURCE-SHAPE assertion, not a presence check.

    Two `.scale-control` rules were deleted (former lines 126 and 387), but the
    selector text legitimately survives inside the retained `@media print` rule
    `.scale-control, .accessibility-dropdown`. So "is `.scale-control` absent?"
    is the wrong question -- it would fail on the retained rule -- and "is it
    present?" is satisfied by the retained rule even if a deleted block came
    back. Neither separates the two claims.

    What distinguishes them is the RULE SHAPE: `.scale-control` may appear
    exactly once, and only as part of a multi-selector list that also names
    `.accessibility-dropdown`. A restored standalone `.scale-control { ... }`
    block violates that immediately.

    Red path: appending `.scale-control { display: flex; }` fails here.
    """
    css = _strip_comments(_css())

    occurrences = re.findall(r"\.scale-control(?![\w-])", css)
    assert len(occurrences) == 1, (
        f".scale-control appears {len(occurrences)} times in a11y.css, expected "
        "exactly 1 (the retained @media print mixed rule). A deleted standalone "
        "block may have been restored."
    )

    # The single occurrence must be a member of the retained mixed selector list,
    # never the sole subject of its own rule.
    # NB: the hyphen must be LAST inside the class -- `[\w-,]` is parsed as a
    # range from \w to ',' and raises re.PatternError.
    standalone = re.search(r"(?<![\w,-])\.scale-control(?![\w-])\s*\{", css)
    assert standalone is None, (
        "a standalone `.scale-control { ... }` rule exists again; the only "
        "permitted occurrence is inside the retained "
        "`.scale-control, .accessibility-dropdown` print rule"
    )


def test_mixed_selector_lists_kept_their_dead_branch() -> None:
    """A rule mixing a dead branch with a non-candidate branch survives whole.

    `.scale-control, .accessibility-dropdown { display: none !important }` --
    `.accessibility-dropdown` was never audited as a d1 candidate, so trimming
    `.scale-control` out would be re-weighting a rule this packet did not prove.
    That is d2's work, not d1's.

    Red path: trimming `.scale-control,` from that rule fails this test.
    """
    css = _strip_comments(_css())
    assert re.search(r"\.scale-control\s*,\s*\.accessibility-dropdown\s*\{", css), (
        "the mixed `.scale-control, .accessibility-dropdown` rule lost a branch; "
        "d1 is pure deletion and may not trim live-or-unaudited selector lists"
    )


def test_important_count_is_exactly_the_d2_certified_result() -> None:
    """The d1/d2 boundary and d2's own result, expressed as a count.

    d1 was pure deletion: every one of its 14 deleted rules contained zero
    `!important`, so all 51 survived it. d2 re-weighted **one** of them --
    `.is-invalid { box-shadow }` -- after certifying that the declaration
    remains the effective owner in every state it is intended to own, so the
    file now carries 50.

    The number is deliberately exact in both directions. Dropping to 49 means
    an annotation was de-weighted without certification; rising to 51 means
    d2's single certified removal was reverted or a new annotation was added.

    Red path: removing `!important` from any other declaration gives 49 and
    fails; restoring it on `.is-invalid { box-shadow }` gives 51 and fails.
    """
    assert _strip_comments(_css()).count("!important") == 50, (
        "a11y.css !important count moved off d2's certified result of 50 "
        "(d1 left 51; d2 removed exactly one, on `.is-invalid { box-shadow }`)."
    )


def _rule_body(selector: str) -> str:
    """The declaration block of the first rule whose selector list matches."""
    css = _strip_comments(_css())
    m = re.search(
        rf"(?:^|}})\s*{re.escape(selector)}\s*\{{(.*?)\}}",
        css,
        flags=re.S | re.M,
    )
    assert m, f"a11y.css no longer contains a rule for `{selector}`"
    return m.group(1)


def test_d2_certified_removal_kept_its_declaration() -> None:
    """Re-weighting is not deletion.

    d2 removed the `!important` token from `.is-invalid { box-shadow }`. The
    declaration itself, and its exact value, must survive unchanged -- a
    re-weighting packet that deletes the declaration has changed rendering,
    not cascade weight.

    Red path: deleting the box-shadow declaration, or altering its value,
    fails this test.
    """
    body = _rule_body(".is-invalid")
    m = re.search(r"box-shadow\s*:([^;]*);", body)
    assert m, ".is-invalid lost its box-shadow declaration; d2 re-weights, it does not delete"
    value = m.group(1).strip()
    assert value == "0 0 0 0.2rem rgba(220, 53, 69, 0.25)", (
        f".is-invalid box-shadow value changed to `{value}`; d2 may only remove "
        "the !important token, never touch the value"
    )
    assert "!important" not in m.group(0), (
        ".is-invalid box-shadow regained !important; this is d2's one certified removal"
    )


def test_the_asymmetric_sibling_kept_its_important() -> None:
    """`.is-invalid` carries two annotations and only one was certified.

    Bootstrap declares `border-color` on `.is-invalid` **at rest**
    (`.form-control.is-invalid`), but declares `box-shadow` only in its
    `:focus` variants. So de-weighting `border-color` changes the computed
    value and de-weighting `box-shadow` does not. That asymmetry inside a
    single rule is the reason d2 shipped one of the two, and it is exactly the
    kind of thing a later tidy-up would "even out" without measuring.

    Red path: removing `!important` from the border-color line fails.
    """
    body = _rule_body(".is-invalid")
    m = re.search(r"border-color\s*:[^;]*;", body)
    assert m, ".is-invalid lost its border-color declaration"
    assert "!important" in m.group(0), (
        ".is-invalid border-color lost its !important. It is NOT interchangeable "
        "with the box-shadow sibling d2 de-weighted: Bootstrap competes for "
        "border-color at rest, and de-weighting this one changes the computed value."
    )


# Selectors whose `!important` d2 measured and deliberately did NOT remove.
# Each is a live or uncertified owner; none may be de-weighted without its own
# certification run.
RETAINED_ANNOTATIONS = (
    # certification attempted and FAILED: with .has-validation-error also on an
    # ancestor, de-weighting hands the owner to pages-workout-plan.css:4449,
    # which declares the same colour at the same specificity without !important.
    ".selection-field.has-validation-error label",
    # dark twin: de-weighting it loses ownership outright.
    '[data-theme="dark"] .selection-field.has-validation-error label',
    # the focus half of the validation pair -- protected focus system.
    ".is-invalid:focus",
)


@pytest.mark.parametrize("selector", RETAINED_ANNOTATIONS)
def test_measured_retentions_keep_their_important(selector: str) -> None:
    """Retentions that a reader would plausibly mistake for oversights.

    Red path: removing `!important` from any of these fails this test.
    """
    body = _rule_body(selector)
    assert "!important" in body, (
        f"`{selector}` lost its !important. d2 measured this annotation and "
        "retained it deliberately; see docs/CSS_PHASE4_WP4_4_D2_A11Y_EVIDENCE.md."
    )


def test_chromium_invisible_annotations_were_not_removed() -> None:
    """12 annotations never reach Chromium; that is not evidence about them.

    Eight sit inside `@-moz-document url-prefix()`, which Chromium never
    parses, and four are `-moz-box-shadow`, which its declaration parser drops.
    A Chromium-only oracle cannot see them, so it cannot certify them, and
    "the harness reported nothing" must never be read as "safe to remove".

    Red path: de-weighting any declaration inside the `@-moz-document` block,
    or any `-moz-box-shadow`, fails this test.
    """
    css = _strip_comments(_css())
    moz = re.search(r"@-moz-document url-prefix\(\)\s*\{(.*?\n\})\s*\n", css, flags=re.S)
    assert moz, "a11y.css lost its @-moz-document block"
    assert moz.group(1).count("!important") == 8, (
        "the @-moz-document block no longer carries 8 !important declarations; "
        "Chromium cannot see this block, so d2's oracle can never certify it"
    )
    # Count the ANNOTATED declarations, not the property name. Counting
    # `-moz-box-shadow` alone stays green when one is de-weighted, since the
    # property is still there -- the red-path proof caught exactly that.
    annotated = re.findall(r"-moz-box-shadow\s*:[^;]*!\s*important\s*;", css)
    assert len(annotated) == 4, (
        f"a11y.css carries {len(annotated)} annotated -moz-box-shadow "
        "declarations, expected 4. Chromium drops this property at parse time, "
        "so d2's oracle cannot see these -- unmeasurable is not dead."
    )


def test_focus_visible_contract_premise_is_preserved() -> None:
    """The contract-pinned `*:focus-visible,` premise survives d1.

    `tests/test_css_cascade_contracts.py` pins this string against a11y.css.
    d1 runs that shared contract but never edits it; this asserts the source
    side of the same premise so a d1-shaped edit cannot silently break it.

    Red path: deleting the `*:focus-visible,` selector fails this test.
    """
    css = _css()
    # Anchored to line start on purpose. A plain `"*:focus-visible," in css`
    # substring check is satisfied by the per-scale rules -- every
    # `html[data-scale="1"] *:focus-visible,` line CONTAINS that substring -- so
    # deleting the bare global selector would leave the test green. The red-path
    # proof caught exactly that.
    assert re.search(r"^\*:focus-visible,", css, flags=re.M), (
        "a11y.css lost the contract-pinned bare `*:focus-visible,` selector "
        "(the per-scale rules do not substitute for it)"
    )
    # The per-scale focus ladder covers data-scale 1..5 ONLY, and did so before
    # d1 as well -- scales 6..8 declare --ui-scale tokens and inherit the global
    # `*:focus-visible` rule instead. Asserting 1..8 here would be asserting a
    # premise that was never true; the pre-deletion comparison caught exactly
    # that. d1 deleted none of this ladder.
    missing = [
        n for n in range(1, 6)
        if f'html[data-scale="{n}"] *:focus-visible' not in css
    ]
    assert missing == [], (
        f"the per-scale focus-visible ladder is gone for data-scale {missing}"
    )


def test_every_targeted_data_scale_level_still_has_rules() -> None:
    """The `--ui-scale` TOKEN ladder defines every level 1..8.

    Anchored to the standalone block `html[data-scale="N"] {` on purpose, which
    is a strictly stronger claim than either weaker form:

    * `[data-scale="N"]` (the original) is satisfied by any of THREE families
      that carry the substring -- the token ladder, the per-scale focus ladder
      (`html[data-scale="4"] *:focus`), and, until the bare `.scale-btn` packet,
      `.scale-btn[data-scale="4"]`. It could therefore be misread as covering
      the scale BUTTONS, which are an unrelated family.
    * `html[data-scale="N"]` alone is still satisfied by the focus ladder, so
      deleting the token block that actually declares `--ui-scale` left it
      green. Measured, not assumed: mutating the level-4 token block leaves
      both weaker forms passing and only this one red.

    The trailing `{` is what separates the standalone token block from both the
    focus ladder and the grouped font-smoothing selector at the top of the file,
    where each arm ends in a comma rather than a brace.

    Red path: renaming the `html[data-scale="4"]` token block fails this test.
    """
    css = _strip_comments(_css())
    missing = [n for n in range(1, 9) if not re.search(rf'html\[data-scale="{n}"\]\s*\{{', css)]
    assert missing == [], (
        f"a11y.css no longer declares a --ui-scale token block for data-scale "
        f"levels {missing}; the per-scale focus ladder does not substitute for it"
    )


def test_the_emptied_breakpoint_block_holds_no_style_rule() -> None:
    """The `max-width: 991.98px` shell is retained, and stays empty.

    The bare `.scale-btn` breakpoint override was that block's last rule. The
    shell is kept rather than collapsed -- removing an at-rule is structural
    work, not deletion of dead declarations, the same call WP4.3j-b made for
    its five empty media shells. This pins BOTH halves: the block still exists,
    and nothing was quietly re-added inside it.

    This is the media-scoped half of the adversarial red path: restoring the
    override alone reds here as well as on the occurrence count.

    Red path: adding any declaration block inside the 991.98px query fails.
    """
    css = _strip_comments(_css())
    match = re.search(r"@media\s*\(max-width:\s*991\.98px\)\s*\{(.*?)\n\}", css, flags=re.S)
    assert match, "a11y.css lost its `@media (max-width: 991.98px)` block"
    body = match.group(1)
    assert "{" not in body, (
        "the retained `max-width: 991.98px` block contains a style rule again; "
        "it was emptied when the bare .scale-btn family was deleted and is kept "
        "only as a structural shell"
    )


def test_accessibility_js_still_constructs_no_dom() -> None:
    """The premise the whole deletion rests on, turned into a gate.

    `accessibility.js` queries `.scale-btn[data-scale]` at :144 and :202 and
    would toggle `.active` plus `aria-pressed` on whatever it found. Those
    lookups resolve to an empty set ONLY because nothing in the app ever
    creates an element carrying the class -- no template emits it and this
    module builds no DOM at all. If it ever gained a construction path, the
    deleted rules would become reachable and the census would be stale.

    Note for whoever trips this: the JS handler surviving without its styling
    means a re-added scale button would announce `aria-pressed` to assistive
    technology with no visible pressed state. Re-run the census; do not
    reflexively re-add the CSS.

    Red path: adding `document.createElement('button')` to accessibility.js
    fails this test.
    """
    source = (JS / "accessibility.js").read_text(encoding="utf-8")
    patterns = {
        "createElement": r"createElement\s*\(",
        "innerHTML": r"innerHTML\s*=",
        "insertAdjacentHTML": r"insertAdjacentHTML\s*\(",
        "insertAdjacentElement": r"insertAdjacentElement\s*\(",
        "outerHTML": r"outerHTML\s*=",
        "cloneNode": r"cloneNode\s*\(",
        "className=": r"className\s*=",
        "setAttribute(class)": r"""setAttribute\(\s*['\"]class['\"]""",
    }
    builders = [name for name, pattern in patterns.items() if re.search(pattern, source)]
    assert builders == [], (
        f"static/js/accessibility.js now constructs DOM ({builders}). The bare "
        ".scale-btn deletion rests on this module never creating an element "
        "that could carry the class; re-run the census in "
        "docs/css_scale_btn_cleanup/EVIDENCE.md before trusting it again."
    )


def test_a11y_css_declares_no_cascade_layer() -> None:
    """N2 freezes @layer membership arc-wide; a11y.css had zero and keeps zero.

    Red path: wrapping any rule in `@layer navbar { ... }` fails.
    """
    assert "@layer" not in _strip_comments(_css()), (
        "a11y.css now declares an @layer; N2 freezes layer membership for the arc"
    )


def test_no_custom_property_was_deleted() -> None:
    """d1 deleted no custom property (M9).

    The 14 deleted rules declared none. Custom properties are never deleted
    under the ordinary non-winner rule, because a `var()` in another bundle may
    be their only consumer.

    Red path: deleting a `--` declaration from a retained rule fails this test.
    """
    decls = re.findall(r"(?<![\w-])--[\w-]+\s*:", _strip_comments(_css()))
    assert len(decls) == 17, (
        f"a11y.css custom-property declaration count is {len(decls)}, expected 17; "
        "d1 deleted none and must not."
    )


def _sibling_surfaces() -> list[str]:
    """Every runtime CSS bundle except a11y.css and the Bootstrap artifact.

    Derived from the directory rather than hand-listed. The previous 5-tuple
    named `layout`, `components`, `navbar`, `theme-dark` and `base`, which
    silently omitted `motion.css`, `tokens.css` and all eleven `pages-*.css`
    route bundles -- so a resurrected rule in any of those went unnoticed.
    a11y.css itself is excluded because its own contracts above cover it.

    Note the coupling: adding a CSS bundle changes this file's pytest node
    count, so it also moves `docs/test_inventory/` and the blocking drift
    gate. Regenerate the inventory in the same change.
    """
    return sorted(
        path.name
        for path in (ROOT / "static" / "css").glob("*.css")
        if path.name != "a11y.css" and not path.name.startswith("bootstrap.custom.min")
    )


@pytest.mark.parametrize("surface", _sibling_surfaces())
def test_legacy_generation_is_not_resurrected_by_a_sibling_surface(surface: str) -> None:
    """No sibling bundle may start styling the generation a11y.css dropped.

    Red path: adding `.accessibility-menu {}` to components.css fails.
    """
    path = ROOT / "static" / "css" / surface
    css = _strip_comments(path.read_text(encoding="utf-8"))
    offenders = [c for c in LEGACY_CLASSES if re.search(rf"\.{re.escape(c)}(?![\w-])", css)]
    assert offenders == [], (
        f"{surface} now styles the generation WP4.4-d1 deleted: {offenders}"
    )
