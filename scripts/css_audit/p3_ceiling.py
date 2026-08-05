"""P3-a0 — the P3-owned contract-ceiling emitter for ``static/css/theme-dark.css``.

Why this exists rather than a call into ``measure.contract_anchors()``.
------------------------------------------------------------------------
``measure.contract_anchors()`` and ``measure.pinned_declarations()`` both iterate
``measure.CONTRACT_FILES`` (``measure.py:34-37``), which is exactly the two
*shared* contract files.  Run against this repository they reach **2** of the
ceiling rows the P3 plan enumerates and cannot reach the other twelve, because
twelve of them live in ``tests/test_css_wp4_4_theme_dark_contracts.py`` — a
per-packet file that is not in ``CONTRACT_FILES``.  Extending ``CONTRACT_FILES``
would move both registers, which ``tests/test_css_wp4_4_a_baseline_contracts.py``
pins against the committed baseline, so the shared apparatus cannot be the
source here without a baseline regeneration nobody has claimed.

So this module walks **every working-tree reader of the file**, independently of
``measure.CONTRACT_FILES``.  Nothing shared is read for authority and nothing
shared is written.  ``measure`` is imported for one purpose only: an independent
recount cross-check, reported as a finding when the two disagree.

What "reader" means here
------------------------
Two populations, kept apart because they constrain different things:

``content`` readers
    A test that reads the bytes of ``static/css/theme-dark.css`` from the
    working tree.  These are the deletion ceilings.

``link`` readers
    A test that reads ``templates/base.html`` and asserts something about the
    ``css/theme-dark.css`` link.  These constrain R4 — the file staying linked —
    and impose no deletion ceiling at all.  The P3 plan's 14-row table carries
    exactly one of these and omits the rest; that is one of the discrepancies
    this module reports rather than inherits.

Discovery is by AST, per module, to a fixpoint over names: a module-level
binding whose source mentions the surface makes that name a surface handle, a
module-level function whose body mentions the surface or a known handle becomes
a handle in turn, and a test is a reader when its own source (decorators
included) mentions the surface or any handle.  Grepping for the filename would
miss ``_css()`` in the WP4.4-j contract file; walking only ``CONTRACT_FILES``
would miss the whole file.

Nothing here is inherited from the planning document.  Every figure is measured
at the commit this runs against, and ``PLAN_CLAIMS`` below exists solely as the
comparison target for ``plan_discrepancies()`` — it is never a source.

usage::

    python -m scripts.css_audit.p3_ceiling            # markdown report
    python -m scripts.css_audit.p3_ceiling --json     # the whole record
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

from . import measure

ROOT = Path(__file__).resolve().parents[2]

THEME_DARK_RELATIVE = "static/css/theme-dark.css"
THEME_DARK_BASENAME = "theme-dark.css"
BASE_HTML_BASENAME = "base.html"
LINK_LITERAL = "css/theme-dark.css"

LEDGER_RELATIVE = "docs/CSS_PHASE4_WP4_4_LINUX_INHERITED_REDS.json"
VISUAL_HELPERS_RELATIVE = "e2e/visual-helpers.ts"

# This arc's own per-packet contract files (P-4 / N1 naming). They read
# theme-dark.css — mostly to build synthetic fixtures — so the walk finds them,
# and folding them into the ceiling table would make the arc's own output an
# input to its own ceiling. They are excluded from the table and emitted as a
# COUNTED bucket instead, never dropped: an exclusion without a count is an
# omission.
P3_OWNED_TEST_PREFIX = "test_css_theme_dark_p3_"

COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


def _blank_comments(css: str) -> str:
    """Replace comment bodies with spaces, preserving offsets and line numbers."""
    return COMMENT_RE.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), css)


def _strip_comments(css: str) -> str:
    """The *length-changing* strip the WP4.4-j contract file uses.

    Kept separate from :func:`_blank_comments` on purpose.  The contracts under
    test call ``re.sub(r"/\\*.*?\\*/", "", css)``, so any count this module
    reports as "what that assertion sees" has to be taken over the same text.
    """
    return COMMENT_RE.sub("", css)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _relative(path: Path) -> str:
    """Repository-relative path, with a fallback for synthetic trees.

    The red-path fixtures in ``tests/test_css_theme_dark_p3_audit_contracts.py``
    run the walk against a copy under ``tmp_path``; a bare ``relative_to(ROOT)``
    would raise there and the fixtures could not execute (O15).
    """
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return f"{path.parent.name}/{path.name}"


def _git(args: list[str], root: Path = ROOT) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


# ---------------------------------------------------------------------------
# Arc base — recorded, never inherited
# ---------------------------------------------------------------------------

# The base the planning document pins.  Recorded here ONLY so the emitter can
# report the drift; the measured SHA below is the authority.
PLAN_PINNED_BASE = "4b0670b"


def arc_base(root: Path = ROOT) -> dict[str, object]:
    """The commit this run actually measured, plus the drift against the plan."""
    head = _git(["rev-parse", "HEAD"], root)
    subject = _git(["log", "-1", "--format=%s", "HEAD"], root)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)

    merge_base = None
    for upstream in ("origin/main", "main"):
        try:
            merge_base = _git(["merge-base", "HEAD", upstream], root)
            break
        except subprocess.CalledProcessError:
            continue

    plan_base_full = None
    plan_base_is_ancestor = None
    try:
        plan_base_full = _git(["rev-parse", PLAN_PINNED_BASE], root)
        plan_base_is_ancestor = (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", plan_base_full, "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )
    except subprocess.CalledProcessError:
        pass

    return {
        "measuredCommit": head,
        "measuredCommitShort": head[:7],
        "measuredCommitSubject": subject,
        "branch": branch,
        "mergeBaseWithMain": merge_base,
        "mergeBaseWithMainShort": merge_base[:7] if merge_base else None,
        "planPinnedBase": PLAN_PINNED_BASE,
        "planPinnedBaseFull": plan_base_full,
        "planPinnedBaseIsAncestorOfHead": plan_base_is_ancestor,
        "baseDrift": (
            None
            if merge_base is None or plan_base_full is None
            else merge_base != plan_base_full
        ),
    }


def production_css_status(root: Path = ROOT) -> dict[str, object]:
    """Is ``static/css/**`` byte-identical to what is committed?

    Asserted rather than assumed, per the P3-a0 gate row.  Deliberately scoped
    to the working tree instead of to a fixed base SHA: a base-SHA pin in a
    permanently-collected per-packet contract file would red the moment P3-c
    makes its authorized cut, and no packet may be forced to weaken another
    packet's assertion to ship.
    """
    status = _git(["status", "--porcelain", "--", "static/css"], root)
    unstaged = _git(["diff", "--name-only", "--", "static/css"], root)
    staged = _git(["diff", "--name-only", "--cached", "--", "static/css"], root)
    lines = [line for line in status.splitlines() if line.strip()]
    return {
        "statusPorcelain": lines,
        "unstaged": [line for line in unstaged.splitlines() if line.strip()],
        "staged": [line for line in staged.splitlines() if line.strip()],
        "clean": not lines,
    }


# ---------------------------------------------------------------------------
# The file's own figures — re-measured, never inherited
# ---------------------------------------------------------------------------


def measure_theme_dark(path: Path | None = None) -> dict[str, object]:
    """Every structural figure the plan counted by reading, counted by a tool.

    Three ``!important`` units are reported for the same reason ``measure.py``
    reports three: the file carries the literal ``Zero !important.`` inside a
    comment, so the raw units over-count by exactly one.
    """
    path = path or (ROOT / THEME_DARK_RELATIVE)
    raw_bytes = path.read_bytes()
    text = raw_bytes.decode("utf-8")
    blanked = _blank_comments(text)
    stripped = _strip_comments(text)
    lines = text.splitlines()

    top_level_style_rules = 0
    top_level_at_rules = 0
    nested_blocks = 0
    depth = 0
    for index, char in enumerate(blanked):
        if char == "{":
            start = index
            while start > 0 and blanked[start - 1] not in "{};":
                start -= 1
            prelude = _one_line(blanked[start:index])
            if depth == 0:
                if prelude.startswith("@"):
                    top_level_at_rules += 1
                else:
                    top_level_style_rules += 1
            else:
                nested_blocks += 1
            depth += 1
        elif char == "}":
            depth -= 1

    custom_properties = re.findall(
        r"^\s*(--[A-Za-z0-9-]+)\s*:", text, flags=re.MULTILINE
    )
    blocks: list[dict[str, object]] = []
    depth = 0
    current: dict[str, object] | None = None
    for index, char in enumerate(blanked):
        if char == "{":
            if depth == 0:
                start = index
                while start > 0 and blanked[start - 1] not in "{};":
                    start -= 1
                current = {
                    "selector": _one_line(blanked[start:index]),
                    "openLine": text.count("\n", 0, index) + 1,
                    "customPropertyDeclarations": 0,
                    "names": [],
                }
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and current is not None:
                current["closeLine"] = text.count("\n", 0, index) + 1
                blocks.append(current)
                current = None

    for block in blocks:
        open_line = int(str(block["openLine"]))
        close_line = int(str(block["closeLine"]))
        span = lines[open_line - 1 : close_line]
        names = [
            match.group(1)
            for line in span
            for match in [re.match(r"^\s*(--[A-Za-z0-9-]+)\s*:", line)]
            if match
        ]
        block["names"] = names
        block["customPropertyDeclarations"] = len(names)

    token_blocks = [block for block in blocks if block["customPropertyDeclarations"]]

    important_re = re.compile(r"!\s*important", re.IGNORECASE)

    independent = {
        "path": THEME_DARK_RELATIVE,
        "sha256OfBytesOnDisk": hashlib.sha256(raw_bytes).hexdigest(),
        "bytesOnDisk": len(raw_bytes),
        "bytesNewlineNormalized": len(text.encode("utf-8")),
        "lineEnding": "CRLF" if "\r\n" in text else "LF",
        "lines": len(lines),
        "braceOpeningBlocks": blanked.count("{"),
        "braceClosingBlocks": blanked.count("}"),
        "topLevelStyleRules": top_level_style_rules,
        "topLevelAtRules": top_level_at_rules,
        "nestedBlocks": nested_blocks,
        "customPropertyDeclarations": len(custom_properties),
        "customPropertyBlocks": [
            {
                "openLine": block["openLine"],
                "closeLine": block["closeLine"],
                "selector": block["selector"],
                "declarations": block["customPropertyDeclarations"],
            }
            for block in token_blocks
        ],
        "importantLines": sum(1 for line in lines if important_re.search(line)),
        "importantOccurrences": len(important_re.findall(text)),
        "importantDeclarations": len(important_re.findall(blanked)),
        "whereWrappedSelectorTokens": text.count(":where("),
        "valueChangedOccurrencesCommentStripped": stripped.count(".value-changed"),
        "mediaAtRulesCommentStripped": stripped.count("@media"),
        "declaresLayer": "@layer" in stripped,
        "mentionsSuperset": "superset" in text.lower(),
    }

    # Independent recount cross-check against the shared apparatus.  A
    # disagreement is a finding, not a silent preference for either number.
    shared = measure.surface_counts(path.name)
    independent["sharedApparatusCrossCheck"] = {
        "measure.surface_counts": shared,
        "agreesOnLines": shared["lines"] == independent["lines"],
        "agreesOnImportantDeclarations": (
            shared["importantDeclarations"] == independent["importantDeclarations"]
        ),
        "byteUnitDiffers": shared["bytes"] != independent["bytesOnDisk"],
        "byteUnitNote": (
            "measure.surface_counts() reads with read_text(), which normalizes "
            "CRLF to LF, so its `bytes` figure is the LF-normalized length and "
            "is NOT the on-disk byte count. Any packet computing character or "
            "byte offsets for a cut must resolve this before it cuts."
        ),
    }

    # The two custom-property blocks: does the later one redeclare every name in
    # the earlier one?  This is the F1 shadow *nomination*, emitted as a
    # structural observation and explicitly not as a warrant.
    if len(token_blocks) >= 2:
        first = [str(name) for name in token_blocks[0]["names"]]  # type: ignore[index]
        last = [str(name) for name in token_blocks[-1]["names"]]  # type: ignore[index]
        independent["tokenBlockShadowNomination"] = {
            "earlierBlockNames": first,
            "laterBlockNames": last,
            "everyEarlierNameRedeclaredLater": all(name in last for name in first),
            "namesOnlyInLaterBlock": [name for name in last if name not in first],
            "warrant": (
                "NOMINATION ONLY. Structural redeclaration is not deletion "
                "authority; P-2 requires a var()-consumer graph, a removal-oracle "
                "result and a per-token split control."
            ),
        }

    return independent


# ---------------------------------------------------------------------------
# Working-tree readers of theme-dark.css
# ---------------------------------------------------------------------------


READ_CALLS = {"read_text", "read_bytes"}


def _references(segment: str, names: set[str]) -> bool:
    return any(
        re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", segment) for name in names
    )


def _is_path_expression(segment: str, needle: str) -> bool:
    """Does this source segment build a filesystem path ending in ``needle``?

    ``ROOT / "static" / "css" / "theme-dark.css"`` qualifies; a tuple of bundle
    names that happens to contain the same string does not.  That distinction is
    the whole difference between the ten real readers and the forty-odd
    link-order assertions that merely mention the filename.
    """
    return needle in segment and "/" in segment


def _module_handles(source: str, tree: ast.Module, needle: str) -> tuple[set[str], set[str]]:
    """Module-level path handles and text handles for ``needle``.

    A *path handle* is a name bound to a path expression reaching the file.
    A *text handle* is a name (usually a helper function) that reads one.
    """
    path_handles: set[str] = set()
    text_handles: set[str] = set()

    changed = True
    while changed:
        changed = False
        for node in tree.body:
            segment = ast.get_source_segment(source, node) or ""
            targets: list[str] = []
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                targets = [node.name]
            if not targets:
                continue

            if _is_path_expression(segment, needle) and not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                for name in targets:
                    if name not in path_handles:
                        path_handles.add(name)
                        changed = True

            reads = any(
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr in READ_CALLS
                and (
                    _is_path_expression(
                        ast.get_source_segment(source, sub.func.value) or "", needle
                    )
                    or _references(
                        ast.get_source_segment(source, sub.func.value) or "",
                        path_handles,
                    )
                )
                for sub in ast.walk(node)
            ) or _references(segment, text_handles)
            if reads:
                for name in targets:
                    if name not in text_handles:
                        text_handles.add(name)
                        changed = True

    return path_handles, text_handles


def _css_bound_locals(
    function: ast.FunctionDef, source: str, path_handles: set[str], text_handles: set[str],
    needle: str,
) -> set[str]:
    """Local names inside ``function`` that carry the file's text, to a fixpoint."""
    bound: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function):
            targets: list[str] = []
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
            elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
            if not targets:
                continue
            value = getattr(node, "value", None) or getattr(node, "iter", None)
            if value is None:
                continue
            segment = ast.get_source_segment(source, value) or ""
            carries = (
                _references(segment, text_handles | bound)
                or _references(segment, path_handles)
                or (
                    _is_path_expression(segment, needle)
                    and any(call in segment for call in READ_CALLS)
                )
            )
            if carries:
                for name in targets:
                    if name not in bound:
                        bound.add(name)
                        changed = True
    return bound


def _shape_of(node: ast.Assert, source: str) -> dict[str, object]:
    """Classify an assertion's shape without executing it."""
    test = node.test
    shape = "other"
    bound: object = None
    operator = None
    literal = None
    negated = False

    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        op = test.ops[0]
        comparator = test.comparators[0]
        if isinstance(op, ast.In):
            shape = "substring-presence"
        elif isinstance(op, ast.NotIn):
            shape = "substring-absence"
            negated = True
        elif isinstance(op, ast.GtE):
            shape, operator = "count-floor", ">="
        elif isinstance(op, ast.LtE):
            shape, operator = "count-ceiling", "<="
        elif isinstance(op, ast.Eq):
            shape, operator = "count-exact", "=="
        elif isinstance(op, ast.Lt):
            shape, operator = "ordering", "<"
        if isinstance(comparator, ast.Constant):
            bound = comparator.value
        if isinstance(test.left, ast.Constant) and isinstance(test.left.value, str):
            literal = test.left.value
    elif isinstance(test, ast.Name) or isinstance(test, ast.Call):
        shape = "truthy"
    elif isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        shape = "falsy"

    return {
        "shape": shape,
        "operator": operator,
        "bound": bound,
        "pinnedLiteral": literal,
        "negated": negated,
        "source": _one_line(ast.get_source_segment(source, node) or ""),
    }


def _count_target(node: ast.Assert) -> str | None:
    """The literal a ``<name>.count("X")`` assertion is counting, if any."""
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "count"
            and len(sub.args) == 1
            and isinstance(sub.args[0], ast.Constant)
            and isinstance(sub.args[0].value, str)
        ):
            return sub.args[0].value
    return None


def _len_findall_pattern(
    node: ast.Assert, function: ast.FunctionDef, source: str
) -> str | None:
    """Resolve ``len(x) == N`` where ``x = re.findall(<pattern>, …)``.

    Deliberately narrow.  An earlier draft took the first ``re.findall`` in the
    body regardless of what the assertion compared, and evaluated the
    rule-splitting regex from ``test_the_certified_removals_stay_removed``
    against the whole file — a number with no relationship to the assertion.
    """
    test = node.test
    if not isinstance(test, ast.Compare) or not isinstance(test.left, ast.Call):
        return None
    call = test.left
    if not (isinstance(call.func, ast.Name) and call.func.id == "len"):
        return None
    if not call.args or not isinstance(call.args[0], ast.Name):
        return None
    target = call.args[0].id
    for sub in ast.walk(function):
        if not isinstance(sub, ast.Assign):
            continue
        if not any(
            isinstance(item, ast.Name) and item.id == target for item in sub.targets
        ):
            continue
        value = sub.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "findall"
            and value.args
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            return value.args[0].value
    return None


def _haystack_is_whole_file(
    node: ast.Assert, function: ast.FunctionDef, source: str, css_names: set[str]
) -> bool:
    """Is the right-hand side of an ``in`` check the whole file, or a slice?

    ``assert "value-changed" in block`` where ``block = css.split("@media")[1]``
    is a slice check: the literal occurring elsewhere in the file says nothing
    about whether the assertion can be satisfied by absence.  Only whole-file
    haystacks get the O14 flag.
    """
    test = node.test
    if not isinstance(test, ast.Compare) or not test.comparators:
        return False
    haystack = ast.get_source_segment(source, test.comparators[0]) or ""
    referenced = {
        name
        for name in css_names
        if re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", haystack)
    }
    if not referenced:
        return False
    narrowing = (".split(", ".index(", ".partition(", "[")
    for sub in ast.walk(function):
        if not isinstance(sub, ast.Assign):
            continue
        targets = {item.id for item in sub.targets if isinstance(item, ast.Name)}
        if not targets & referenced:
            continue
        value_source = ast.get_source_segment(source, sub.value) or ""
        if any(token in value_source for token in narrowing):
            return False
    return True


def theme_dark_readers(
    tests_dir: Path | None = None,
    css_path: Path | None = None,
    include_self_owned: bool = False,
) -> list[dict[str, object]]:
    """Every working-tree assertion in ``tests/`` that binds ``theme-dark.css``.

    One record per assertion, because the ceiling is a property of assertions,
    not of test functions: ``test_the_reduced_motion_block_is_preserved`` alone
    carries three separate ceilings.
    """
    tests_dir = tests_dir or (ROOT / "tests")
    css_path = css_path or (ROOT / THEME_DARK_RELATIVE)
    css_text = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    css_stripped = _strip_comments(css_text)

    records: list[dict[str, object]] = []

    for path in sorted(tests_dir.rglob("test_*.py")):
        if path.name.startswith(P3_OWNED_TEST_PREFIX) and not include_self_owned:
            continue
        source = path.read_text(encoding="utf-8")
        if THEME_DARK_BASENAME not in source:
            continue
        tree = ast.parse(source)
        path_handles, text_handles = _module_handles(source, tree, THEME_DARK_BASENAME)
        relative = _relative(path)

        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            locals_ = _css_bound_locals(
                node, source, path_handles, text_handles, THEME_DARK_BASENAME
            )
            css_names = locals_ | text_handles | path_handles
            segment = ast.get_source_segment(source, node) or ""
            reads_css = bool(locals_) or _references(
                segment, text_handles | path_handles
            )
            if not reads_css:
                continue

            for sub in ast.walk(node):
                if not isinstance(sub, ast.Assert):
                    continue
                assertion_source = ast.get_source_segment(source, sub) or ""
                if not (
                    _references(assertion_source, css_names)
                    or _is_path_expression(assertion_source, THEME_DARK_BASENAME)
                ):
                    # An assertion inside a reader test that never touches the
                    # file's text imposes no ceiling on it.
                    continue
                shape = _shape_of(sub, source)

                # Link-class: the assertion constrains the <link>, not the bytes.
                is_link_assertion = shape["pinnedLiteral"] == LINK_LITERAL

                record: dict[str, object] = {
                    "file": relative,
                    "test": node.name,
                    "line": sub.lineno,
                    "readerClass": "link" if is_link_assertion else "content",
                    **shape,
                }

                current: object = None
                headroom: object = None
                counted = _count_target(sub)
                findall_pattern = _len_findall_pattern(sub, node, source)
                if counted is not None:
                    current = css_stripped.count(counted)
                    record["countedLiteral"] = counted
                elif findall_pattern:
                    current = len(
                        re.findall(findall_pattern, css_text, flags=re.MULTILINE)
                    )
                    record["countedPattern"] = findall_pattern

                if isinstance(current, int) and isinstance(shape["bound"], int):
                    if shape["operator"] == ">=":
                        headroom = current - int(shape["bound"])
                    elif shape["operator"] == "==":
                        headroom = 0

                record["currentValue"] = current
                record["headroom"] = headroom

                # O14 — is the assertion satisfiable by the absence of the very
                # thing it protects?
                satisfiable_by_absence = False
                reason = None
                if shape["shape"] == "count-ceiling":
                    satisfiable_by_absence = True
                    reason = (
                        "a `<=` bound passes at zero, so deleting every instance "
                        "of the thing it counts leaves it green"
                    )
                elif shape["shape"] == "substring-presence" and not is_link_assertion:
                    literal = str(shape["pinnedLiteral"] or "")
                    occurrences = css_text.count(literal) if literal else 0
                    whole_file = _haystack_is_whole_file(sub, node, source, css_names)
                    record["pinnedLiteralOccurrencesInCss"] = occurrences
                    record["haystackIsWholeFile"] = whole_file
                    if occurrences > 1 and whole_file:
                        satisfiable_by_absence = True
                        reason = (
                            f"the pinned literal occurs {occurrences} times in the "
                            "file, so a substring check over the whole file stays "
                            "green after the protected instance is deleted"
                        )
                record["satisfiableByAbsence"] = satisfiable_by_absence
                record["satisfiableByAbsenceReason"] = reason

                record["deletionCeiling"] = (
                    record["readerClass"] == "content"
                    and shape["shape"]
                    in {
                        "substring-presence",
                        "count-floor",
                        "count-exact",
                        "count-ceiling",
                        "truthy",
                    }
                )
                records.append(record)

    records.sort(key=lambda item: (str(item["file"]), int(str(item["line"]))))
    return records


def self_owned_readers(
    tests_dir: Path | None = None, css_path: Path | None = None
) -> dict[str, object]:
    """The arc's own contract files, excluded from the table but counted.

    P3-a0's contract file reads ``theme-dark.css`` to build its red-path
    fixtures, so the walk finds it. Folding it into the ceiling table would make
    the arc's own output an input to its own ceiling, and every later P3 packet
    would inflate the table further. The exclusion is emitted here with its
    rows, so it is a bucket rather than an omission.
    """
    tests_dir = tests_dir or (ROOT / "tests")
    everything = theme_dark_readers(
        tests_dir=tests_dir, css_path=css_path, include_self_owned=True
    )
    excluded = [
        record
        for record in everything
        if str(record["file"]).split("/")[-1].startswith(P3_OWNED_TEST_PREFIX)
    ]
    return {
        "prefix": P3_OWNED_TEST_PREFIX,
        "why": (
            "arc-owned per-packet contract files (P-4). They read the file to "
            "build synthetic fixtures; their assertions constrain the emitter, "
            "not the CSS."
        ),
        "excludedAssertionCount": len(excluded),
        "excludedFiles": sorted(
            {str(record["file"]) for record in excluded}
        ),
        "excludedRows": [_row_key(record) for record in excluded],
    }


def link_readers(tests_dir: Path | None = None) -> list[dict[str, object]]:
    """Assertions that constrain the ``css/theme-dark.css`` **link**, not the bytes.

    R4's guard, and the cascade-order guards that pin where the bundle sits in
    ``templates/base.html``.  None imposes a deletion ceiling; every one of them
    forbids unlinking or reordering.  The P3 plan's 14-row table carries exactly
    one member of this class and omits the rest, which is why they are emitted
    separately rather than folded in.
    """
    tests_dir = tests_dir or (ROOT / "tests")
    records: list[dict[str, object]] = []
    for path in sorted(tests_dir.rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        if LINK_LITERAL not in source:
            continue
        tree = ast.parse(source)
        relative = _relative(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Assert):
                    continue
                segment = ast.get_source_segment(source, sub) or ""
                if LINK_LITERAL not in segment:
                    continue
                records.append(
                    {
                        "file": relative,
                        "test": node.name,
                        "line": sub.lineno,
                        "assertion": _one_line(segment),
                        "constrains": "R4 — the file stays linked / stays in order",
                        "imposesDeletionCeiling": False,
                    }
                )
    records.sort(key=lambda item: (str(item["file"]), int(str(item["line"]))))
    return records


def shared_register_reach(root: Path = ROOT) -> dict[str, object]:
    """How far the SHARED registers reach into this file's ceiling, measured.

    Substantiates re-review N1 mechanically rather than by reading: the two
    registers ``measure.contract_anchors()`` / ``measure.pinned_declarations()``
    iterate ``measure.CONTRACT_FILES``, and this reports exactly which
    theme-dark rows that reaches.  It also records the double lock —
    ``tests/test_css_wp4_4_a_baseline_contracts.py:297-298`` asserts both
    registers equal the committed baseline byte-for-byte, so extending
    ``CONTRACT_FILES`` reds a contract the arc may not edit.
    """
    anchors = [
        anchor
        for anchor in measure.contract_anchors()
        if THEME_DARK_BASENAME in list(anchor["surfaces"])  # type: ignore[arg-type]
    ]
    css_text = (root / THEME_DARK_RELATIVE).read_text(encoding="utf-8")
    anchor_tests = {str(anchor["test"]) for anchor in anchors}
    pins = [
        pin
        for pin in measure.pinned_declarations()
        if pin["test"] in anchor_tests and pin["pinnedString"] in css_text
    ]
    rows = theme_dark_readers()
    reachable_rows = [
        _row_key(row) for row in rows if str(row["file"]) in measure.CONTRACT_FILES
    ]
    unreachable_rows = [
        _row_key(row) for row in rows if str(row["file"]) not in measure.CONTRACT_FILES
    ]
    return {
        "ceilingRowsReachable": reachable_rows,
        "ceilingRowsReachableCount": len(reachable_rows),
        "ceilingRowsUnreachable": unreachable_rows,
        "ceilingRowsUnreachableCount": len(unreachable_rows),
        "contractFiles": list(measure.CONTRACT_FILES),
        "contractFilesCoverTheThemeDarkPacketContract": (
            "tests/test_css_wp4_4_theme_dark_contracts.py" in measure.CONTRACT_FILES
        ),
        "anchorsBindingThemeDark": [
            {
                "file": anchor["file"],
                "test": anchor["test"],
                "assertionLines": anchor["assertionLines"],
            }
            for anchor in anchors
        ],
        "pinsPresentInThemeDark": [
            {"file": pin["file"], "test": pin["test"], "line": pin["line"],
             "pinnedString": pin["pinnedString"]}
            for pin in pins
        ],
        "anchorsBindingThemeDarkNote": (
            "contract_anchors() records a surface as `touched` when the test's "
            "SOURCE TEXT mentions the filename, so most of these bind "
            "theme-dark.css only through a `base.index(\"css/theme-dark.css\")` "
            "link-order assertion. "
            "tests/test_css_wp4_4_a_baseline_contracts.py:301 asserting "
            "theme-dark.css is among the bound surfaces is therefore true and "
            "does NOT mean the register enumerates this file's content ceiling."
        ),
        "pinnedDeclarationsNote": (
            "pinned_declarations() is not surface-resolved: a pin recorded for "
            "another surface is listed here whenever its literal also occurs in "
            "theme-dark.css. `background:` and `border-color:` are that noise; "
            "only the two `.frame-header` pins are real ceilings."
        ),
        "doubleLock": (
            "tests/test_css_wp4_4_a_baseline_contracts.py:297-298 asserts "
            "contract_anchors() and pinned_declarations() equal the committed "
            "CSS_PHASE4_WP4_4_A_BASELINE.json exactly, so editing "
            "tests/test_css_cascade_contracts.py at all — even to strengthen a "
            "pin — moves startLine/endLine/assertionLines and reds that contract "
            "too."
        ),
    }


def parametrized_surface_readers(
    tests_dir: Path | None = None,
) -> list[dict[str, object]]:
    """Tests that reach ``theme-dark.css`` through a parametrized surface list.

    These impose no deletion ceiling — every one of them asserts the file does
    **not** style a generation another packet dropped, which deletion satisfies.
    Recorded so no later packet re-derives them and so the count is a bucket
    rather than an omission.
    """
    tests_dir = tests_dir or (ROOT / "tests")
    found: list[dict[str, object]] = []
    for path in sorted(tests_dir.rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        if THEME_DARK_BASENAME not in source:
            continue
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                segment = ast.get_source_segment(source, decorator) or ""
                if "parametrize" in segment and THEME_DARK_BASENAME in segment:
                    found.append(
                        {
                            "file": _relative(path),
                            "test": node.name,
                            "line": decorator.lineno,
                            "decorator": _one_line(segment),
                            "imposesDeletionCeiling": False,
                            "why": (
                                "additive constraint — asserts the surface does "
                                "NOT style a deleted generation; satisfied by "
                                "deletion"
                            ),
                        }
                    )
    return found


# ---------------------------------------------------------------------------
# The Q1 defect, probed rather than argued
# ---------------------------------------------------------------------------

Q1_PAIRS = (
    (':where([data-theme="dark"] #results-body)', "background-color"),
    (':where([data-theme="dark"] #results-body tr)', "background-color"),
    (':where([data-theme="dark"] #results-body td)', "color"),
    (':where([data-theme="dark"] .table-responsive .table)', "color"),
)


def q1_occurrences(css_text: str) -> list[dict[str, object]]:
    """Re-run ``test_the_certified_removals_stay_removed``'s own predicate.

    Reported so the ``occurrences <= 1`` defect is a measured number rather than
    a reading of the source.  The owner granted the ``<= 1`` → ``== 1``
    strengthening unconditionally at Gate 0; **this packet does not perform it**
    and touches no existing contract file.
    """
    css = _strip_comments(css_text)
    results = []
    for selector, prop in Q1_PAIRS:
        blocks = [
            body
            for head, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            if selector in head
        ]
        occurrences = sum(
            len(re.findall(rf"^\s*{re.escape(prop)}\s*:", block, flags=re.MULTILINE))
            for block in blocks
        )
        results.append(
            {
                "selector": selector,
                "property": prop,
                "matchingBlocks": len(blocks),
                "occurrences": occurrences,
                "passesUnderLessThanOrEqualOne": occurrences <= 1,
                "passesUnderEqualsOne": occurrences == 1,
            }
        )
    return results


# ---------------------------------------------------------------------------
# C7 — the uncertifiable set, READ from the committed ledger
# ---------------------------------------------------------------------------


def uncertifiable_elements(ledger_path: Path | None = None) -> dict[str, object]:
    """C7's eight Welcome elements, read from the committed schema-v2 ledger.

    Not re-derived.  ``uncertifiableElements.elements[]`` carries all eight with
    both ``domPath`` and ``selector``, plus the ``adjacentNote`` for
    ``div.developer-credit-banner::before``, in a committed file with no
    dependency on the deleted gitignored ``artifacts/`` tree.
    """
    ledger_path = ledger_path or (ROOT / LEDGER_RELATIVE)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    block = ledger["uncertifiableElements"]
    elements = block["elements"]
    return {
        "source": LEDGER_RELATIVE,
        "declaredCount": block["count"],
        "recoveredCount": len(elements),
        "countAgrees": block["count"] == len(elements),
        "everyElementHasDomPath": all(element.get("domPath") for element in elements),
        "everyElementHasSelector": all(element.get("selector") for element in elements),
        "route": block["route"],
        "appliesToBothThemes": block["appliesToBothThemes"],
        "rule": block["rule"],
        "elements": elements,
        "adjacentNote": block["adjacentNote"],
        "adjacentSelector": "div.developer-credit-banner::before",
    }


# ---------------------------------------------------------------------------
# N8 denominator — documentary reconciliation, no dispatch
# ---------------------------------------------------------------------------


def _count_playwright_tests(spec: Path) -> dict[str, object]:
    """Count ``test('...')`` cases a spec generates, from its own loop shape.

    Deliberately arithmetic over the declared matrices rather than a Playwright
    ``--list``: P3-a0 runs no browser and dispatches no gate, and the whole point
    of the reconciliation is that it is a desk exercise.
    """
    text = spec.read_text(encoding="utf-8")
    return {
        "spec": _relative(spec),
        "serialModeConfigured": "test.describe.configure({ mode: 'serial' })" in text,
    }


def n8_denominator(root: Path = ROOT) -> dict[str, object]:
    """Reconcile 66 + 18 = 84 expected against the 68 reported in every run.

    The gap is **serial-mode collateral**, and it closes exactly.
    ``e2e/visual-baseline-thumbnails.spec.ts`` sets
    ``test.describe.configure({ mode: 'serial' })`` at file scope, so the first
    failure in that file stops the rest of the file from running.  The one
    ledgered thumbnail red is ``plan-desktop-light-advanced``, which the spec's
    own loop order makes the **second** of its eighteen tests.
    """
    ledger = json.loads((root / LEDGER_RELATIVE).read_text(encoding="utf-8"))
    thumbnails = root / "e2e" / "visual-baseline-thumbnails.spec.ts"
    visual = root / "e2e" / "visual.spec.ts"

    thumb_text = thumbnails.read_text(encoding="utf-8")
    serial = "test.describe.configure({ mode: 'serial' })" in thumb_text

    # The thumbnail spec's declared matrices, read off the spec.
    plan_tests = 3 * 2 * 2  # viewports x themes x view modes
    log_tests = 3 * 2  # viewports x themes
    thumbnail_tests = plan_tests + log_tests
    visual_tests = 11 * 3 * 2  # pages x viewports x themes

    ledgered = {
        entry["spec"]: entry["count"] for entry in ledger["linuxInheritedReds"]["specs"]
    }
    thumbnail_red = ledger["linuxInheritedReds"]["specs"][1]["files"][0]

    # Position of the ledgered thumbnail red in the spec's own generation order.
    order = [
        f"plan-{viewport}-{theme}-{mode}"
        for viewport in ("desktop", "tablet", "mobile")
        for theme in ("light", "dark")
        for mode in ("simple", "advanced")
    ] + [
        f"log-{viewport}-{theme}"
        for viewport in ("desktop", "tablet", "mobile")
        for theme in ("light", "dark")
    ]
    red_index = order.index(thumbnail_red.removesuffix(".png"))
    did_not_run = thumbnail_tests - (red_index + 1) if serial else 0

    visual_failed = ledgered["e2e/visual.spec.ts"]
    thumbnail_failed = ledgered["e2e/visual-baseline-thumbnails.spec.ts"]
    failed = visual_failed + thumbnail_failed
    passed = (visual_tests - visual_failed) + (red_index + 1 - thumbnail_failed)

    # The falsifiable half.  Everything above is arithmetic over the ledger and
    # would "close" for any inputs; this compares the derivation against the run
    # results the ledger itself records, which is a claim that can be wrong.
    recorded: list[dict[str, object]] = []
    for spec in ledger["linuxInheritedReds"]["specs"]:
        for run in spec.get("provenance", {}).get("deepGateRuns", []):
            if not isinstance(run, dict) or "result" not in run:
                continue
            text = str(run["result"])
            failed_match = re.search(r"(\d+)\s+failed", text)
            passed_match = re.search(r"(\d+)\s+passed", text)
            flaky_match = re.search(r"(\d+)\s+flaky", text)
            recorded_failed = int(failed_match.group(1)) if failed_match else None
            recorded_passed = int(passed_match.group(1)) if passed_match else None
            if recorded_passed is not None and flaky_match:
                recorded_passed += int(flaky_match.group(1))
            recorded.append(
                {
                    "run": run.get("run"),
                    "ref": run.get("ref"),
                    "result": text,
                    "recordedFailed": recorded_failed,
                    "recordedPassedIncludingFlaky": recorded_passed,
                    "derivationMatches": (
                        recorded_failed == failed and recorded_passed == passed
                    ),
                }
            )

    return {
        "recordedRuns": recorded,
        "recordedRunCount": len(recorded),
        "derivationMatchesEveryRecordedRun": bool(recorded)
        and all(bool(run["derivationMatches"]) for run in recorded),
        "dispatched": False,
        "method": "documentary — deep-gate.yml, the ledger scopeNote, and the "
        "66 + 18 baseline pins; no CI dispatch is authorized at P3-a0",
        "workflow": ".github/workflows/deep-gate.yml",
        "workflowRunsBothSpecsTogether": "e2e/visual.spec.ts e2e/visual-baseline-thumbnails.spec.ts"
        in (root / ".github" / "workflows" / "deep-gate.yml").read_text(
            encoding="utf-8"
        ),
        "committedBaselinePins": {
            "visual.spec.ts": 66,
            "visual-baseline-thumbnails.spec.ts": 18,
            "pinnedAt": "tests/test_css_wp4_4_a_baseline_contracts.py:39-44",
        },
        "specMatrices": {
            "visual.spec.ts": {
                "pages": 11,
                "viewports": 3,
                "themes": 2,
                "tests": visual_tests,
                "serialModeConfigured": _count_playwright_tests(visual)[
                    "serialModeConfigured"
                ],
            },
            "visual-baseline-thumbnails.spec.ts": {
                "planTests": plan_tests,
                "logTests": log_tests,
                "tests": thumbnail_tests,
                "serialModeConfigured": serial,
            },
        },
        "expectedTotal": visual_tests + thumbnail_tests,
        "reportedInEveryRecordedRun": failed + passed,
        "unaccountedBeforeReconciliation": (visual_tests + thumbnail_tests)
        - (failed + passed),
        "reconciliation": {
            "failed": failed,
            "passed": passed,
            "didNotRun": did_not_run,
            "sum": failed + passed + did_not_run,
            "closes": failed + passed + did_not_run == visual_tests + thumbnail_tests,
            "cause": (
                "serial-mode collateral inside "
                "e2e/visual-baseline-thumbnails.spec.ts — the ledgered red "
                f"{thumbnail_red} is test {red_index + 1} of {thumbnail_tests} in "
                "the spec's own generation order, so the remaining "
                f"{did_not_run} never execute"
            ),
        },
        "consequenceForP3c": (
            "`totalCount: 11` is a FLOOR, not the inherited-red count. The "
            f"{did_not_run} thumbnail tests that never ran are unmeasured on "
            "every recorded run, so the ledger cannot certify them as inherited "
            "OR as clean. P3-c must either land a green thumbnail head so the "
            "rest of the file executes, or record the unmeasured set explicitly."
        ),
        "priorArtInRepository": [
            "docs/MASTER_HANDOVER.md:173-178 — the serial-mode explanation",
            "docs/MASTER_HANDOVER.md:187 — '11 failed, 57 passed, 16 did not run'",
            "docs/TESTING_STRATEGY_PLANNING.md §8.7",
        ],
    }


# ---------------------------------------------------------------------------
# Q10 — sizing the shared blind-spot-register repair (SIZE ONLY)
# ---------------------------------------------------------------------------


def _helper_style_blocks(helper_text: str) -> list[dict[str, object]]:
    """Rule blocks inside ``prepareForScreenshot()``'s injected stylesheet."""
    start = helper_text.index("await page.addStyleTag({")
    body_start = helper_text.index("`", start) + 1
    body_end = helper_text.index("`", body_start)
    css = helper_text[body_start:body_end]
    offset_line = helper_text.count("\n", 0, body_start) + 1

    blanked = _blank_comments(css)
    blocks: list[dict[str, object]] = []
    depth = 0
    open_index = 0
    selector_start = 0
    for index, char in enumerate(blanked):
        if char == "{":
            if depth == 0:
                start_index = index
                while start_index > 0 and blanked[start_index - 1] not in "{};":
                    start_index -= 1
                selector_start = start_index
                open_index = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                while (
                    selector_start < open_index
                    and blanked[selector_start] in " \t\r\n"
                ):
                    selector_start += 1
                selector = _one_line(blanked[selector_start:open_index])
                body = css[open_index + 1 : index]
                declarations = [
                    match.group(1)
                    for match in re.finditer(
                        r"^\s*([-A-Za-z0-9]+)\s*:", body, flags=re.MULTILINE
                    )
                ]
                blocks.append(
                    {
                        "selector": selector,
                        "helperLine": offset_line + css.count("\n", 0, selector_start),
                        "declarations": declarations,
                        "text": css[selector_start : index + 1],
                    }
                )
    return blocks


def blind_spot_repair_sizing(helper_path: Path | None = None) -> dict[str, object]:
    """Q10 — size the SHARED blind-spot-register repair. **Sizing only.**

    ``measure.verify_blind_spots()`` checks one direction: each register entry's
    ``helperEvidence`` still appears in the helper.  Nothing checks the converse,
    and ``tests/test_css_wp4_4_a_baseline_contracts.py:224`` then pins the
    register's length against the committed baseline — so a neutralizer added to
    the helper is invisible, and adding the missing entries moves that length.

    This function performs the *converse* derivation read-only so the owner has a
    number.  It writes nothing and modifies nothing.
    """
    helper_path = helper_path or (ROOT / VISUAL_HELPERS_RELATIVE)
    helper_text = helper_path.read_text(encoding="utf-8")
    blocks = _helper_style_blocks(helper_text)

    registered_properties: set[str] = set()
    for entry in measure.BLIND_SPOT_REGISTER:
        registered_properties.update(str(prop) for prop in entry["properties"])  # type: ignore[arg-type]

    unmapped_blocks: list[dict[str, object]] = []
    weakly_mapped: list[dict[str, object]] = []
    token_definition_blocks: list[dict[str, object]] = []
    mapped_blocks: list[dict[str, object]] = []
    unmapped_declaration_count = 0

    for block in blocks:
        declarations = [str(name) for name in block["declarations"]]  # type: ignore[arg-type]
        if declarations and all(name.startswith("--") for name in declarations):
            token_definition_blocks.append(
                {
                    "helperLine": block["helperLine"],
                    "selector": block["selector"],
                    "declarations": declarations,
                    "why": "defines the --visual-surface-* tokens the registered "
                    "flatteners consume; not itself a neutralizer",
                }
            )
            continue

        matching_entries = [
            entry
            for entry in measure.BLIND_SPOT_REGISTER
            if str(entry["helperEvidence"]) in str(block["text"])
        ]
        covered = {
            prop
            for entry in matching_entries
            for prop in (str(value) for value in entry["properties"])  # type: ignore[arg-type]
        }
        missing = [name for name in declarations if name not in covered]
        selective = any(
            str(entry["helperEvidence"]) in str(block["selector"])
            for entry in matching_entries
        )

        record = {
            "helperLine": block["helperLine"],
            "selector": block["selector"],
            "declarations": declarations,
            "matchedRegisterEntries": [
                str(entry["selector"]) for entry in matching_entries
            ],
            "unmappedDeclarations": missing,
        }
        if not matching_entries:
            unmapped_blocks.append(record)
            unmapped_declaration_count += len(declarations)
        elif missing:
            record["note"] = (
                "partially mapped — the matching entry's helperEvidence is a "
                "declaration string, not a selector, so it matches this block by "
                "coincidence"
                if not selective
                else "partially mapped"
            )
            weakly_mapped.append(record)
            unmapped_declaration_count += len(missing)
        else:
            mapped_blocks.append(record)

    return {
        "sizingOnly": True,
        "notImplemented": (
            "Q10 was deferred to P3-a0 for SIZING. This packet does not add an "
            "entry, does not edit scripts/css_audit/measure.py and does not "
            "regenerate docs/CSS_PHASE4_WP4_4_A_BASELINE.json."
        ),
        "helper": VISUAL_HELPERS_RELATIVE,
        "registerEntriesToday": len(measure.BLIND_SPOT_REGISTER),
        "verifyBlindSpotsDirection": "one-way — register entry → helper text only",
        "helperRuleBlocks": len(blocks),
        "fullyMappedBlocks": len(mapped_blocks),
        "tokenDefinitionBlocks": token_definition_blocks,
        "unmappedBlocks": unmapped_blocks,
        "partiallyMappedBlocks": weakly_mapped,
        "unmappedBlockCount": len(unmapped_blocks),
        "partiallyMappedBlockCount": len(weakly_mapped),
        "unmappedDeclarationCount": unmapped_declaration_count,
        "registeredPropertyVocabulary": sorted(registered_properties),
    }


# ---------------------------------------------------------------------------
# The committed tools
# ---------------------------------------------------------------------------

# Curated verdicts, cross-checked mechanically against the directory listing by
# `tool_assessment()`.  Judgement is curated on purpose — a machine cannot say
# whether a differ is reusable — but coverage is not: a tool added or removed
# under `scripts/css_audit/` reds the P3-a0 contract rather than drifting.
TOOL_ASSESSMENT: tuple[dict[str, str], ...] = (
    {
        "tool": "measure.py",
        "role": "static per-surface measurement + the three shared registers",
        "verdict": "reuse unmodified, read-only",
        "why": "P3-a0 imports it solely for an independent recount cross-check. "
        "Its two ceiling registers iterate CONTRACT_FILES (the two shared "
        "files) and cannot enumerate the theme-dark ceiling; that is why "
        "p3_ceiling.py exists. Its BLIND_SPOT_REGISTER is one-way verified "
        "(Q10). Repairing either is P3-a1's question, not a0's.",
    },
    {
        "tool": "specificity.py",
        "role": "selector specificity model, :is()/:where()/:not()/:has()-aware",
        "verdict": "reuse unmodified",
        "why": "The only committed component that already handles the exact "
        "construct this arc turns on — :where() contributing zero. "
        "Unit-checked by test_specificity_model_agrees_with_its_hand_computed_cases. "
        "No P3 replacement is warranted.",
    },
    {
        "tool": "resolution_check.py",
        "role": "M4 — replays CDP cascade data against the specificity model",
        "verdict": "reuse unmodified",
        "why": "Consumes a runtime_probe.mjs capture and reports every place the "
        "model and Blink disagree about ownership. Directly reusable as the "
        "O3 'name the winner' check; needs no P3 variant.",
    },
    {
        "tool": "emit_baseline.py",
        "role": "emits docs/CSS_PHASE4_WP4_4_A_BASELINE.json",
        "verdict": "NOT reusable for regeneration; read-only reference only",
        "why": "Build-path input per test-strategist #10, and the finding is "
        "adverse: a fresh build() at HEAD differs from the committed "
        "baseline in sourceCommit, surfaces, totals AND isFamily, because "
        "the committed baseline describes 46e340e (pre-WP4.4-i). The "
        "isFamily delta (fourBranchTokens 13 -> 0, fourBranchRules 12 -> 0, "
        "threeBranchRules 1 -> 12) reds "
        "test_is_family_enumeration_is_complete_and_classified. So Q10's "
        "'regenerate the baseline' cannot be a whole-file re-emit; it has "
        "to be a scoped patch of oracleBlindSpots alone.",
    },
    {
        "tool": "i_seed_probe_db.py",
        "role": "builds the frozen probe DB from the committed visual seed",
        "verdict": "reuse unmodified — and do not modify it",
        "why": "Carries a named, scoped raw-sqlite3 exception that is conditioned "
        "on not being modified. P3-a1's superset seeding must therefore land "
        "in a new p3_seed_probe_db.py writing only its --out copy.",
    },
    {
        "tool": "runtime_probe.mjs",
        "role": "the WP4.4 runtime cascade harness (rest-state differential, "
        "M5 same-CSS control, M6 sentinel effect, motion oracle, CDP dump)",
        "verdict": "reuse as the capture layer; NOT a removal oracle",
        "why": "Supplies the sweep and the controls but never removes a "
        "declaration and re-reads, so it grants no deletion authority under "
        "M-h3. Its CSS-only universal transition suppressor is beatable by "
        "layered and by more-specific unlayered !important — exactly the "
        "cascade shape theme-dark.css lives in — so O5's per-element "
        "read-back verifier is a P3-a1 addition on top of it, not a "
        "replacement for it.",
    },
    {
        "tool": "j_theme_differential.mjs",
        "role": "whole-page computed differential, 11 routes x 2 themes",
        "verdict": "reuse unmodified as the capture half",
        "why": "Already scoped to the whole document and to both themes with four "
        "fatal controls. This is the instrument that returned j's "
        "uninformative zero; reusing it is correct precisely because the "
        "fix is O1' bracketing, not a different differ.",
    },
    {
        "tool": "j_diff_theme.mjs",
        "role": "diffs two j_theme_differential captures; four refusals",
        "verdict": "reuse unmodified",
        "why": "Already implements every O6 refusal (same-root pair, equal served "
        "digests, failed half-control, empty comparison). Rewriting it "
        "would re-earn refusals that are already certified.",
    },
    {
        "tool": "j_known_live_mutation.mjs",
        "role": "the digest-pinned --bg-primary known-live control",
        "verdict": "reuse unmodified at this base; re-pin deliberately after any cut",
        "why": "EXPECTED_INPUT is e54818bf... and the working-tree file hashes to "
        "exactly that, so the control still runs at the measured base — one "
        "of the plan's open assumptions, now discharged. It is NOT a "
        "per-family control: it re-points every --bg-primary line, so it "
        "cannot separate the two token blocks (P-2 obligation (d)) and it "
        "fires nowhere near families F2/F3.",
    },
    {
        "tool": "j_shadow_certification.mjs",
        "role": "intra-file shadow certifier under identical selector text",
        "verdict": "reuse for F1 nomination only; NOT deletion authority",
        "why": "Statically decidable and conservative, and it excludes custom "
        "properties by design, which is the whole of family F1. It answers "
        "a strictly narrower question than M-h3's removal oracle.",
    },
    {
        "tool": "j_theme_dark_inventory.mjs",
        "role": "structural census of theme-dark.css",
        "verdict": "reuse as the census input to P3-b's partition",
        "why": "Already separates custom properties and the reduced-motion block. "
        "Does not emit a disjoint per-declaration partition with an ordered "
        "predicate chain, which is the P3-b delta.",
    },
    {
        "tool": "i_five_route_computed.mjs",
        "role": "five-route computed differential over the .table-calm subtree",
        "verdict": "NOT reusable as-is — superseded by the j pair for this arc",
        "why": "Build-path input per test-strategist #10. Subtree-scoped to the "
        ":is() family's five routes; theme-dark.css reaches tables, forms, "
        "cards, the navbar, headings and the welcome hero, so its scope is "
        "a guess here. j_theme_differential.mjs is the whole-document "
        "successor. Its control catalogue is worth copying; its scope is not.",
    },
    {
        "tool": "i_diff_computed.mjs",
        "role": "diffs two i_five_route_computed captures",
        "verdict": "NOT reusable — pairs with a capture format this arc does not use",
        "why": "Its --expect-same-css inversion is the pattern P3-a1 should copy "
        "for the same-CSS control, but j_diff_theme.mjs already carries it "
        "for the capture shape this arc produces.",
    },
    {
        "tool": "i_known_live_mutation.mjs",
        "role": "the :is()-branch de-weighting known-live control",
        "verdict": "NOT reusable — mutates components.css, which C8 freezes",
        "why": "Build-path input per test-strategist #10. Its transformation "
        "targets the shared :is() family in components.css; this arc writes "
        "no byte of that file. Reusable only as the design pattern for a "
        "committed, digest-pinned, re-executable mutation.",
    },
    {
        "tool": "i_diff_g3.mjs",
        "role": "diffs the G3 Workout Log regions A/B/C ownership summaries",
        "verdict": "NOT reusable — G3 is a WP4.4-i gate on pages-workout-log.css",
        "why": "Nothing in this arc touches that surface. Its opposite-side / "
        "different-root / differing-digest refusals are the same family "
        "j_diff_theme.mjs already implements.",
    },
    {
        "tool": "i_element_pixel_diff.mjs",
        "role": "element-scoped pixel differential, both roots served in one process",
        "verdict": "conditionally reusable — and it is the only answer to O12",
        "why": "The one committed tool that measures RENDERED pixels at element "
        "scope without the visual-helpers neutralizers. That is exactly what "
        "the superset alpha-compositing hazard needs, because a differential "
        "keyed on the row's own background-color reports zero while the "
        "composite moves. Its scope constant is .table-calm and would need a "
        "P3 target; that is a parameter change, not a rewrite.",
    },
    {
        "tool": "n4_regions_abc.mjs",
        "role": "per-declaration wins/loses ownership measurement (1,101 lines)",
        "verdict": "NOT reusable directly — but it is the closest thing to a census",
        "why": "Region-scoped to pages-workout-log.css and structurally keyed to "
        "that file's selectors. Its wins/loses-with-named-owner record shape "
        "is precisely O3's requirement, and its structural (never "
        "line-keyed) anchor resolution is precisely O11's. The most "
        "valuable single reference for P3-a1's census, and the largest "
        "committed tool in the directory.",
    },
    {
        "tool": "scale_btn_census.mjs",
        "role": "bare `.scale-btn` family census, per-member certification and "
        "post-deletion flip for static/css/a11y.css",
        "verdict": "NOT reusable for theme-dark — family-scoped by construction",
        "why": "Registered here only because `tool_assessment()` enumerates the "
        "committed directory and reds on any tool without a verdict; that "
        "gate is doing its job and this is its designed remedy, not a "
        "reopening of P3, which stays terminated at a0. The tool is keyed "
        "to one class token and to a11y.css's own breakpoint, so it "
        "carries no theme-dark deletion authority and prices nothing. It "
        "is, however, the first committed harness that demonstrates a "
        "post-deletion flip by CDP source range for every member of a "
        "family, which is the record shape a census would need.",
    },
    {
        "tool": "stylelint_surfaces.mjs",
        "role": "seven-surface Stylelint, per-file per-rule counts",
        "verdict": "reuse unmodified",
        "why": "The arc-anchor measurement runs through it. Note the anchor is "
        "this arc's own base, never the pinned WP4.1 baseline, which "
        "predates WP4.3 and would report an improvement as a regression.",
    },
    {
        "tool": "visual_helper_band_proof.mjs",
        "role": "proof harness for the visual-helpers determinism-layer correction",
        "verdict": "reuse for band reconciliation; NOT an evidence source",
        "why": "Named by test-strategist #10 as the band-reconciliation tool. It "
        "compares two variants of the HELPER, not two variants of the "
        "product CSS, so it cannot certify a theme-dark deletion. It is the "
        "right instrument for showing an animated-logo difference sits "
        "inside the recorded band.",
    },
)


def tool_assessment(directory: Path | None = None) -> dict[str, object]:
    """The committed tools, assessed, with coverage checked mechanically."""
    directory = directory or (ROOT / "scripts" / "css_audit")

    committed = sorted(
        path.name
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix in {".py", ".mjs"}
        and path.name != "__init__.py"
        and not path.name.startswith("p3_")
    )
    assessed = sorted(str(entry["tool"]) for entry in TOOL_ASSESSMENT)

    reusable = [
        entry for entry in TOOL_ASSESSMENT if str(entry["verdict"]).startswith("reuse")
    ]
    conditional = [
        entry
        for entry in TOOL_ASSESSMENT
        if str(entry["verdict"]).startswith("conditionally")
    ]
    not_reusable = [
        entry for entry in TOOL_ASSESSMENT if str(entry["verdict"]).startswith("NOT")
    ]

    return {
        "committedTools": committed,
        "committedToolCount": len(committed),
        "assessedTools": assessed,
        "assessedToolCount": len(assessed),
        "coverageComplete": committed == assessed,
        "unassessed": [name for name in committed if name not in assessed],
        "assessedButAbsent": [name for name in assessed if name not in committed],
        "reuseUnmodified": [str(entry["tool"]) for entry in reusable],
        "conditionallyReusable": [str(entry["tool"]) for entry in conditional],
        "notReusable": [str(entry["tool"]) for entry in not_reusable],
        "records": [dict(entry) for entry in TOOL_ASSESSMENT],
        "noRemovalOracleExists": True,
        "noRemovalOracleEvidence": (
            "No h_* file exists under scripts/css_audit/ and no committed tool "
            "removes a declaration and re-reads computed values. Every committed "
            "instrument is a differential, a census, a static certifier or a "
            "lint wrapper, so M-h3's deletion authority is unavailable today."
        ),
    }


# ---------------------------------------------------------------------------
# The plan's own claims — the comparison target, never a source
# ---------------------------------------------------------------------------

# Transcribed from docs/css_theme_dark_p3/PLANNING.md so `plan_discrepancies()`
# has something to diff against.  Gate-0 material. NOT a source for any figure.
PLAN_CLAIMS: dict[str, object] = {
    "lines": 574,
    "topLevelRules": 72,
    "braceOpeningBlocks": 74,
    "customPropertyDeclarations": 34,
    "customPropertySplit": [16, 18],
    "importantDeclarations": 124,
    "ceilingRowCount": 14,
    "ceilingRows": [
        "theme_dark_contracts.py:32",
        "theme_dark_contracts.py:34",
        "theme_dark_contracts.py:35",
        "theme_dark_contracts.py:45",
        "theme_dark_contracts.py:52",
        "theme_dark_contracts.py:53",
        "theme_dark_contracts.py:55",
        "theme_dark_contracts.py:62",
        "theme_dark_contracts.py:68",
        "theme_dark_contracts.py:88",
        "theme_dark_contracts.py:98",
        "a_baseline_contracts.py:128",
        "cascade_contracts.py:1006",
        "cascade_contracts.py:1007",
    ],
    "backdropFilterLiteralOccurrences": 2,
    "backdropFilterCeiling": "at most one of :102 / :144 may lose it",
    "valueChangedOccurrences": 7,
    "brace_budget": 24,
    "linkClassRowsCarried": 1,
    "parametrizedSurfaceReadersRecorded": 2,
    "sharedRegisterCeilingRowsReachable": 2,
}

_ROW_ALIASES = {
    "tests/test_css_wp4_4_theme_dark_contracts.py": "theme_dark_contracts.py",
    "tests/test_css_wp4_4_a_baseline_contracts.py": "a_baseline_contracts.py",
    "tests/test_css_cascade_contracts.py": "cascade_contracts.py",
    "tests/test_css_wp4_4_a11y_contracts.py": "a11y_contracts.py",
    "tests/test_css_wp4_4_layout_contracts.py": "layout_contracts.py",
    "tests/test_version.py": "test_version.py",
}


def _row_key(record: dict[str, object]) -> str:
    alias = _ROW_ALIASES.get(str(record["file"]), str(record["file"]))
    return f"{alias}:{record['line']}"


def plan_discrepancies(
    figures: dict[str, object] | None = None,
    readers: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Every disagreement between the emitted table and the plan's copy."""
    figures = figures or measure_theme_dark()
    readers = readers if readers is not None else theme_dark_readers()
    out: list[dict[str, object]] = []

    def compare(name: str, claimed: object, measured: object, note: str = "") -> None:
        out.append(
            {
                "item": name,
                "planClaim": claimed,
                "measured": measured,
                "agrees": claimed == measured,
                "note": note,
            }
        )

    compare("lines", PLAN_CLAIMS["lines"], figures["lines"])
    compare(
        "top-level rules",
        PLAN_CLAIMS["topLevelRules"],
        figures["topLevelStyleRules"],
        "the plan's 72 counts top-level STYLE rules only; the file also has 1 "
        "top-level at-rule and 1 nested rule",
    )
    compare(
        "brace-opening blocks",
        PLAN_CLAIMS["braceOpeningBlocks"],
        figures["braceOpeningBlocks"],
    )
    compare(
        "custom-property declarations",
        PLAN_CLAIMS["customPropertyDeclarations"],
        figures["customPropertyDeclarations"],
    )
    compare(
        "custom-property split",
        PLAN_CLAIMS["customPropertySplit"],
        [block["declarations"] for block in figures["customPropertyBlocks"]],  # type: ignore[index]
    )
    compare(
        "!important declarations",
        PLAN_CLAIMS["importantDeclarations"],
        figures["importantDeclarations"],
    )
    compare(
        ".value-changed occurrences",
        PLAN_CLAIMS["valueChangedOccurrences"],
        figures["valueChangedOccurrencesCommentStripped"],
    )
    compare(
        "whole-block deletion budget (braces - 50)",
        PLAN_CLAIMS["brace_budget"],
        int(figures["braceOpeningBlocks"]) - 50,  # type: ignore[arg-type]
    )

    backdrop_records = [
        record
        for record in readers
        if record.get("pinnedLiteral") == "backdrop-filter: blur(8px) !important;"
    ]
    measured_occurrences = (
        backdrop_records[0].get("pinnedLiteralOccurrencesInCss")
        if backdrop_records
        else None
    )
    compare(
        "occurrences of the pinned `backdrop-filter: blur(8px) !important;` literal",
        PLAN_CLAIMS["backdropFilterLiteralOccurrences"],
        measured_occurrences,
        "the -webkit- prefixed lines CONTAIN the pinned literal as a substring, "
        "so the substring check has more survivors than the plan records",
    )

    emitted_rows = {_row_key(record) for record in readers}
    claimed_rows = set(PLAN_CLAIMS["ceilingRows"])  # type: ignore[arg-type]
    out.append(
        {
            "item": "ceiling rows",
            "planClaim": sorted(claimed_rows),
            "measured": sorted(emitted_rows),
            "agrees": claimed_rows == emitted_rows,
            "note": "rows in the emitted table that the plan's copy omits: "
            + (", ".join(sorted(emitted_rows - claimed_rows)) or "none")
            + " | rows the plan carries that the emitter does not reach: "
            + (", ".join(sorted(claimed_rows - emitted_rows)) or "none"),
        }
    )

    links = link_readers()
    compare(
        "link-class assertions",
        PLAN_CLAIMS["linkClassRowsCarried"],
        len(links),
        "the plan's table carries exactly one member of this class "
        "(theme_dark_contracts.py:32) and omits the rest; none imposes a "
        "deletion ceiling, but every one of them forbids unlinking or "
        "reordering the bundle",
    )

    parametrized = parametrized_surface_readers()
    compare(
        "parametrized surface readers",
        PLAN_CLAIMS["parametrizedSurfaceReadersRecorded"],
        len(parametrized),
        "recorded by the plan outside its table (a11y_contracts.py:427, "
        "layout_contracts.py:294); additive constraints, satisfied by deletion",
    )

    reach = shared_register_reach()
    compare(
        "ceiling rows reachable from measure.CONTRACT_FILES",
        PLAN_CLAIMS["sharedRegisterCeilingRowsReachable"],
        reach["ceilingRowsReachableCount"],
        "re-review N1, verified mechanically. Reachable: "
        + ", ".join(reach["ceilingRowsReachable"])  # type: ignore[arg-type]
        + f". Unreachable: {reach['ceilingRowsUnreachableCount']} rows, all in "
        "per-packet contract files that CONTRACT_FILES does not list.",
    )

    q1 = q1_occurrences((ROOT / THEME_DARK_RELATIVE).read_text(encoding="utf-8"))
    compare(
        "theme_dark_contracts.py:88 passes at zero",
        True,
        all(row["passesUnderLessThanOrEqualOne"] for row in q1),
        "measured, not read: occurrences per pinned pair = "
        + ", ".join(f"{row['occurrences']}" for row in q1)
        + " — every pair currently declares its longhand exactly once, so the "
        "`<= 1` bound is satisfied AND would still be satisfied at zero",
    )
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def report(root: Path = ROOT) -> dict[str, object]:
    figures = measure_theme_dark()
    readers = theme_dark_readers()
    css_text = (root / THEME_DARK_RELATIVE).read_text(encoding="utf-8")
    return {
        "packet": "P3-a0",
        "emitter": "scripts/css_audit/p3_ceiling.py",
        "independentOf": "measure.CONTRACT_FILES",
        "arcBase": arc_base(root),
        "productionCss": production_css_status(root),
        "themeDarkFigures": figures,
        "ceilingTable": readers,
        "selfOwnedReadersExcluded": self_owned_readers(),
        "linkReaders": link_readers(),
        "sharedRegisterReach": shared_register_reach(root),
        "parametrizedSurfaceReaders": parametrized_surface_readers(),
        "q1OccurrencesProbe": q1_occurrences(css_text),
        "uncertifiableElements": uncertifiable_elements(),
        "n8Denominator": n8_denominator(root),
        "blindSpotRepairSizing": blind_spot_repair_sizing(),
        "toolAssessment": tool_assessment(),
        "planDiscrepancies": plan_discrepancies(figures, readers),
    }


def _markdown(record: dict[str, object]) -> str:
    lines: list[str] = []
    base = record["arcBase"]
    figures = record["themeDarkFigures"]
    add = lines.append

    add("# P3-a0 — emitted contract ceiling for static/css/theme-dark.css\n")
    add(f"Measured commit: `{base['measuredCommit']}`  ")  # type: ignore[index]
    add(f"Plan-pinned base: `{base['planPinnedBase']}` "  # type: ignore[index]
        f"(drift: {base['baseDrift']})\n")  # type: ignore[index]

    add("## File figures\n")
    add("| Figure | Measured |")
    add("|---|---|")
    for key in (
        "lines",
        "braceOpeningBlocks",
        "topLevelStyleRules",
        "topLevelAtRules",
        "nestedBlocks",
        "customPropertyDeclarations",
        "importantDeclarations",
        "importantLines",
        "valueChangedOccurrencesCommentStripped",
        "sha256OfBytesOnDisk",
        "bytesOnDisk",
        "lineEnding",
    ):
        add(f"| `{key}` | {figures[key]} |")  # type: ignore[index]
    add("")

    add("## Ceiling table\n")
    add("| Row | Class | Shape | Current | Bound | Headroom | O14 |")
    add("|---|---|---|---|---|---|---|")
    for row in record["ceilingTable"]:  # type: ignore[union-attr]
        add(
            f"| `{_row_key(row)}` | {row['readerClass']} | {row['shape']} | "
            f"{row['currentValue']} | {row['bound']} | {row['headroom']} | "
            f"{'SATISFIABLE BY ABSENCE' if row['satisfiableByAbsence'] else '-'} |"
        )
    add("")

    add("## Discrepancies against the plan's copy\n")
    add("| Item | Plan | Measured | Agrees |")
    add("|---|---|---|---|")
    for row in record["planDiscrepancies"]:  # type: ignore[union-attr]
        add(
            f"| {row['item']} | {row['planClaim']} | {row['measured']} | "
            f"{'yes' if row['agrees'] else '**NO**'} |"
        )
    add("")

    n8 = record["n8Denominator"]
    add("## N8 denominator\n")
    add(f"- expected: {n8['expectedTotal']}")  # type: ignore[index]
    add(f"- reported: {n8['reportedInEveryRecordedRun']}")  # type: ignore[index]
    add(f"- reconciliation: {n8['reconciliation']}")  # type: ignore[index]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the whole record")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    record = report()
    text = (
        json.dumps(record, indent=2, ensure_ascii=False, default=str) + "\n"
        if args.json
        else _markdown(record)
    )
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
