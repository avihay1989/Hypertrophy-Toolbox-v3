#!/usr/bin/env python3
"""
Build static/vendor/workout-cool/{body_anterior,body_posterior}.svg from the
upstream Snouzy/workout-cool React/TSX components at a pinned commit SHA.

The upstream art lives as 14 TSX files:

  src/features/workout-builder/ui/muscle-selection.tsx   (parent SVG container
                                                          + body silhouette
                                                          outlines + accents)
  src/features/workout-builder/ui/muscles/<muscle>-group.tsx  (13 files; one
                                                          per simple-level
                                                          muscle group)

Upstream uses a SINGLE 535x462 viewBox containing two bodies side-by-side:
  - LEFT half  (X <  ~268) is the anterior (front-facing) body.
  - RIGHT half (X >= ~268) is the posterior (back-facing) body.

This script:

  1. Fetches the upstream sources at the pinned SHA from
     raw.githubusercontent.com. (Alternative: --src-dir for offline rebuild.)
  2. Strips React-isms and rewrites every interactive <path> with our own
     class / data-canonical-muscles attribute conventions, using the
     ENUM_SIDE_TO_CANONICAL table below to encode PLANNING.md §3.3.
  3. Splits paths by X-cluster into two SVG files. Each output preserves
     the upstream path data verbatim; only attribute names change.
     - body_anterior.svg  uses viewBox "0   0 268 462".
     - body_posterior.svg uses viewBox "268 0 267 462" (non-zero min-x crops
       the left half away; path coords stay in their original 268-535 range).
  4. Body silhouette outlines and decorative accent paths (the static fill
     ones, no getMuscleClasses) go into a <g class="body-outline"> in the
     correct half.

The script is intentionally deterministic: same upstream SHA -> byte-identical
SVG output. To refresh the art, bump the SHA in `static/vendor/workout-cool/
VERSION` plus UPSTREAM_SHA below and re-run.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from typing import Iterable, NamedTuple

# ----------------------------------------------------------------------------
# Pinned upstream
# ----------------------------------------------------------------------------

UPSTREAM_REPO = "Snouzy/workout-cool"
UPSTREAM_SHA = "77f25a922b51be7d96bd051c5d2096959f0d61a8"
UPSTREAM_RAW = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_SHA}"

MUSCLE_GROUP_FILES = [
    "abdominals", "back", "biceps", "calves", "chest", "forearms", "glutes",
    "hamstrings", "obliques", "quadriceps", "shoulders", "traps", "triceps",
]

# ----------------------------------------------------------------------------
# (vendor enum, side) -> list of our canonical keys; None means drop the path
# entirely on that side.
#
# Sides:
#   anterior  = LEFT half of upstream 535x462 (X < X_SPLIT)
#   posterior = RIGHT half (X >= X_SPLIT)
#
# Multi-key regions (e.g. BACK posterior) carry comma-separated canonical
# keys in data-canonical-muscles. The runtime JS must flatten through
# SIMPLE_TO_ADVANCED_MAP before mutating selectedMuscles (see PLANNING.md
# §3.4.1).
# ----------------------------------------------------------------------------

X_SPLIT = 268.0  # midpoint between the two bodies in the 535x462 viewBox

ENUM_SIDE_TO_CANONICAL: dict[tuple[str, str], list[str] | None] = {
    ("CHEST", "anterior"): ["chest"],
    ("CHEST", "posterior"): None,
    ("ABDOMINALS", "anterior"): ["abdominals"],
    ("ABDOMINALS", "posterior"): None,
    ("OBLIQUES", "anterior"): ["obliques"],
    ("OBLIQUES", "posterior"): None,
    ("BICEPS", "anterior"): ["biceps"],
    ("BICEPS", "posterior"): None,
    ("TRICEPS", "anterior"): ["triceps"],
    ("TRICEPS", "posterior"): ["triceps"],
    ("FOREARMS", "anterior"): ["forearms"],
    ("FOREARMS", "posterior"): ["forearms"],
    ("SHOULDERS", "anterior"): ["front-shoulders"],
    ("SHOULDERS", "posterior"): ["rear-shoulders"],
    # MUSCLES_BY_SIDE.front in muscle-selector.js does NOT include 'traps'.
    # Anterior trap paths are dropped to keep the front-tab model in sync.
    ("TRAPS", "anterior"): None,
    ("TRAPS", "posterior"): ["traps"],
    ("BACK", "anterior"): None,
    ("BACK", "posterior"): ["lats", "upper-back", "lowerback"],
    ("QUADRICEPS", "anterior"): ["quads"],
    ("QUADRICEPS", "posterior"): None,
    ("HAMSTRINGS", "anterior"): None,
    ("HAMSTRINGS", "posterior"): ["hamstrings"],
    ("GLUTES", "anterior"): None,
    ("GLUTES", "posterior"): ["glutes"],
    ("CALVES", "anterior"): ["calves"],
    ("CALVES", "posterior"): ["calves"],
}

# Embedded CSS for both output SVGs. Intentionally minimal: page-level
# rules in pages-workout-plan.css fully cover every state of `.muscle-region`
# (default / hover / selected / partial / non-selectable, plus dark mode).
# Adding rules here would land later in the cascade than the page CSS — same
# specificity, runtime-injected — and override the page palette, breaking
# dark mode and partial-hover transitions. So we only set behaviors the page
# CSS does NOT cover (outline click-through).
EMBEDDED_STYLE = """
    .body-outline path {
      pointer-events: none;
    }
"""

# ----------------------------------------------------------------------------
# Path extraction
# ----------------------------------------------------------------------------

PATH_RE = re.compile(r"<path\b([^>]*?)/>", re.DOTALL)
ATTR_STRING_RE = re.compile(r'(\w[\w-]*)\s*=\s*"([^"]*)"', re.DOTALL)
ATTR_BRACE_RE = re.compile(r"(\w[\w-]*)\s*=\s*\{([^}]*)\}", re.DOTALL)
ENUM_ATTR_RE = re.compile(r"ExerciseAttributeValueEnum\.([A-Z_]+)")


class ParsedPath(NamedTuple):
    d: str                  # raw d attribute value (multi-line)
    enum: str | None        # vendor enum name from data-elem, e.g. "CHEST"
    is_muscle: bool         # True iff className uses getMuscleClasses(...)
    is_invisible: bool      # True iff className == "fill-transparent"
    static_fill: str | None # fill attribute value if present and not in muscle
    stroke: str | None
    stroke_width: str | None
    upstream_id: str | None # id attribute from upstream
    first_x: float          # X of the first M command in d (for cluster split)


def parse_path_block(inner: str) -> ParsedPath | None:
    """Parse the inner attributes of a single <path .../> tag."""
    string_attrs = {m.group(1): m.group(2) for m in ATTR_STRING_RE.finditer(inner)}
    brace_attrs = {m.group(1): m.group(2).strip() for m in ATTR_BRACE_RE.finditer(inner)}

    d = string_attrs.get("d")
    if not d:
        return None

    # className handling: in upstream, it's either string-form ("fill-transparent")
    # or brace-form ({getMuscleClasses(...)}). Order doesn't matter; we look at
    # both spellings.
    cls_string = string_attrs.get("className")
    cls_brace = brace_attrs.get("className")

    is_muscle = bool(cls_brace and "getMuscleClasses" in cls_brace)
    is_invisible = cls_string == "fill-transparent"

    # data-elem={ExerciseAttributeValueEnum.X}
    enum: str | None = None
    de = brace_attrs.get("data-elem")
    if de:
        m = ENUM_ATTR_RE.search(de)
        if m:
            enum = m.group(1)

    # First M command in d (always uppercase absolute)
    m = re.search(r"M\s*([+-]?\d*\.?\d+)\s*[, ]\s*[+-]?\d*\.?\d+", d)
    first_x = float(m.group(1)) if m else 0.0

    return ParsedPath(
        d=d,
        enum=enum,
        is_muscle=is_muscle,
        is_invisible=is_invisible,
        static_fill=string_attrs.get("fill"),
        stroke=string_attrs.get("stroke"),
        stroke_width=string_attrs.get("strokeWidth"),
        upstream_id=string_attrs.get("id"),
        first_x=first_x,
    )


def extract_paths(source: str) -> list[ParsedPath]:
    """Find every <path .../> in a TSX source, returning parsed records."""
    out: list[ParsedPath] = []
    for match in PATH_RE.finditer(source):
        inner = match.group(1)
        # Skip paths embedded in unrelated JSX blocks; the muscle-group files
        # only contain <path/> at SVG-relevant positions, so a permissive
        # match is fine. Verified manually — see EXECUTION_LOG.md.
        parsed = parse_path_block(inner)
        if parsed is not None:
            out.append(parsed)
    return out


# ----------------------------------------------------------------------------
# Source loading
# ----------------------------------------------------------------------------

def fetch_upstream() -> dict[str, str]:
    """Fetch the parent + 13 muscle-group TSX files at UPSTREAM_SHA."""
    sources: dict[str, str] = {}
    base = f"{UPSTREAM_RAW}/src/features/workout-builder/ui"
    files = [("muscle-selection.tsx", f"{base}/muscle-selection.tsx")] + [
        (f"muscles/{name}-group.tsx", f"{base}/muscles/{name}-group.tsx")
        for name in MUSCLE_GROUP_FILES
    ]
    for rel, url in files:
        with urllib.request.urlopen(url) as resp:
            sources[rel] = resp.read().decode("utf-8")
    return sources


def load_local(src_dir: Path) -> dict[str, str]:
    sources: dict[str, str] = {}
    sources["muscle-selection.tsx"] = (src_dir / "muscle-selection.tsx").read_text("utf-8")
    for name in MUSCLE_GROUP_FILES:
        rel = f"muscles/{name}-group.tsx"
        sources[rel] = (src_dir / rel).read_text("utf-8")
    return sources


# ----------------------------------------------------------------------------
# SVG emission
# ----------------------------------------------------------------------------

def indent_d(d: str, indent: str) -> str:
    """Re-indent the multi-line d attribute consistently."""
    lines = [ln.strip() for ln in d.splitlines() if ln.strip()]
    return ("\n" + indent).join(lines)


def render_outline_path(p: ParsedPath, indent: str = "    ") -> str:
    attrs: list[str] = []
    if p.static_fill is not None:
        attrs.append(f'fill="{p.static_fill}"')
    if p.stroke is not None:
        attrs.append(f'stroke="{p.stroke}"')
    if p.stroke_width is not None:
        attrs.append(f'stroke-width="{p.stroke_width}"')
    if p.upstream_id is not None:
        attrs.append(f'data-upstream-id="{p.upstream_id}"')
    attr_str = (" " + " ".join(attrs)) if attrs else ""
    return (
        f"{indent}<path{attr_str}\n"
        f'{indent}      d="{indent_d(p.d, indent + "         ")}"/>'
    )


def render_muscle_path(p: ParsedPath, canonical: list[str], indent: str = "    ") -> str:
    keys = ",".join(canonical)
    return (
        f'{indent}<path class="muscle-region" data-canonical-muscles="{keys}"\n'
        f'{indent}      d="{indent_d(p.d, indent + "         ")}"/>'
    )


def render_svg(*, side: str, view_box: str, body_id: str,
               outline_paths: list[ParsedPath],
               muscle_blocks: list[tuple[str, list[ParsedPath], list[str]]]) -> str:
    """
    Assemble the final SVG text for one body.

    muscle_blocks: list of (header_label, [paths], [canonical-keys]) tuples,
    so the output is grouped per upstream enum for readability.
    """
    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append("<!--")
    parts.append(f"  Body {side.capitalize()} View")
    parts.append(f"  Source: workout-cool ({UPSTREAM_REPO}) @ {UPSTREAM_SHA}")
    parts.append("  License: MIT (Mathias Bradiceanu, 2023). See LICENSE + NOTICE.md.")
    parts.append("  Generated by scripts/build_workout_cool_svgs.py — do not edit by hand.")
    parts.append("-->")
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
        f'id="{body_id}">'
    )
    parts.append("  <defs>")
    parts.append("    <style>")
    parts.append(EMBEDDED_STYLE.rstrip())
    parts.append("    </style>")
    parts.append("  </defs>")
    parts.append("")
    parts.append('  <g class="body-outline">')
    for p in outline_paths:
        parts.append(render_outline_path(p, indent="    "))
    parts.append("  </g>")
    parts.append("")
    parts.append('  <g class="muscle-regions">')
    for label, paths, canonical in muscle_blocks:
        if not paths:
            continue
        parts.append(f"    <!-- {label}: {','.join(canonical)} -->")
        for p in paths:
            parts.append(render_muscle_path(p, canonical, indent="    "))
        parts.append("")
    parts.append("  </g>")
    parts.append("</svg>")
    parts.append("")
    return "\n".join(parts)


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def side_for_x(x: float) -> str:
    return "anterior" if x < X_SPLIT else "posterior"


def build(sources: dict[str, str]) -> dict[str, str]:
    parent = sources["muscle-selection.tsx"]

    # 1. Outline paths from the parent. We only treat <path> elements that
    # appear OUTSIDE of any muscle-group component (the parent only renders
    # those components by name, so any <path> in the parent file is by
    # definition outline/accent).
    parent_paths = extract_paths(parent)

    outline_anterior: list[ParsedPath] = []
    outline_posterior: list[ParsedPath] = []
    for p in parent_paths:
        if p.is_invisible:
            continue
        bucket = outline_anterior if side_for_x(p.first_x) == "anterior" else outline_posterior
        bucket.append(p)

    # 2. Muscle paths per group file. We walk the 13 files in the upstream
    # render order so the output reads predictably top-to-bottom.
    enum_order = [
        "BICEPS", "FOREARMS", "CHEST", "TRICEPS", "ABDOMINALS", "OBLIQUES",
        "QUADRICEPS", "SHOULDERS", "CALVES", "TRAPS", "BACK", "HAMSTRINGS",
        "GLUTES",
    ]
    enum_to_filename = {
        "BICEPS": "biceps", "FOREARMS": "forearms", "CHEST": "chest",
        "TRICEPS": "triceps", "ABDOMINALS": "abdominals",
        "OBLIQUES": "obliques", "QUADRICEPS": "quadriceps",
        "SHOULDERS": "shoulders", "CALVES": "calves", "TRAPS": "traps",
        "BACK": "back", "HAMSTRINGS": "hamstrings", "GLUTES": "glutes",
    }

    muscle_blocks_anterior: list[tuple[str, list[ParsedPath], list[str]]] = []
    muscle_blocks_posterior: list[tuple[str, list[ParsedPath], list[str]]] = []
    accents_anterior: list[ParsedPath] = []
    accents_posterior: list[ParsedPath] = []

    for enum in enum_order:
        filename = enum_to_filename[enum]
        rel = f"muscles/{filename}-group.tsx"
        paths = extract_paths(sources[rel])

        anterior_muscle: list[ParsedPath] = []
        posterior_muscle: list[ParsedPath] = []

        for p in paths:
            if p.is_invisible:
                continue
            side = side_for_x(p.first_x)
            if not p.is_muscle:
                # Static accent (e.g. inter-pec sternum shading). Park it on
                # the body-outline group of the matching side so we keep
                # visual fidelity but it never receives muscle-region styling.
                (accents_anterior if side == "anterior" else accents_posterior).append(p)
                continue
            (anterior_muscle if side == "anterior" else posterior_muscle).append(p)

        # Bucket the muscle paths into anterior / posterior, applying the
        # ENUM_SIDE_TO_CANONICAL drop / re-key rules.
        anterior_keys = ENUM_SIDE_TO_CANONICAL.get((enum, "anterior"))
        posterior_keys = ENUM_SIDE_TO_CANONICAL.get((enum, "posterior"))

        if anterior_keys and anterior_muscle:
            muscle_blocks_anterior.append((enum, anterior_muscle, anterior_keys))
        if posterior_keys and posterior_muscle:
            muscle_blocks_posterior.append((enum, posterior_muscle, posterior_keys))

    # Append static accents to the outline groups so they render under any
    # muscle-region overlay.
    outline_anterior.extend(accents_anterior)
    outline_posterior.extend(accents_posterior)

    anterior_svg = render_svg(
        side="anterior",
        view_box="0 0 268 462",
        body_id="body-anterior-workoutcool",
        outline_paths=outline_anterior,
        muscle_blocks=muscle_blocks_anterior,
    )
    posterior_svg = render_svg(
        side="posterior",
        view_box="268 0 267 462",
        body_id="body-posterior-workoutcool",
        outline_paths=outline_posterior,
        muscle_blocks=muscle_blocks_posterior,
    )

    return {
        "body_anterior.svg": anterior_svg,
        "body_posterior.svg": posterior_svg,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=None,
        help=("Local directory containing previously-fetched upstream sources "
              "(layout: muscle-selection.tsx + muscles/<name>-group.tsx). When "
              "omitted, sources are fetched from raw.githubusercontent.com at "
              f"the pinned SHA {UPSTREAM_SHA}."),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("static/vendor/workout-cool"),
        help="Where to write body_anterior.svg and body_posterior.svg.",
    )
    parser.add_argument(
        "--print-stats",
        action="store_true",
        help="Print muscle-region path counts per side after building.",
    )
    args = parser.parse_args(argv)

    if args.src_dir:
        print(f"[build_workout_cool_svgs] Reading sources from {args.src_dir}", file=sys.stderr)
        sources = load_local(args.src_dir)
    else:
        print(f"[build_workout_cool_svgs] Fetching upstream @ {UPSTREAM_SHA}", file=sys.stderr)
        sources = fetch_upstream()

    outputs = build(sources)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        target = args.out_dir / name
        target.write_text(content, encoding="utf-8", newline="\n")
        print(f"[build_workout_cool_svgs] wrote {target} ({len(content)} bytes)", file=sys.stderr)

    if args.print_stats:
        for name, content in outputs.items():
            count = content.count('class="muscle-region"')
            print(f"  {name}: {count} muscle-region paths", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
