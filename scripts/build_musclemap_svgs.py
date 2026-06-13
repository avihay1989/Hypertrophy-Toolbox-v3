#!/usr/bin/env python3
"""
Build static/bodymaps/hypertrophy-advanced/{body_anterior,body_posterior}.svg
from the vendored MuscleMap (melihcolpan/MuscleMap, MIT) male body path data.

Upstream ships its anatomy as SVG path strings embedded in Swift source
(`Sources/MuscleMap/Data/Male{Front,Back}Paths.swift`). We vendor those two
files (plus LICENSE / VERSION) under `static/vendor/musclemap/` and mechanically
re-emit them as two inline-clickable SVGs that carry the muscle-selector
contract:

  - interactive regions: `<path class="muscle-region" data-canonical-muscles="<key>">`
    keyed to the ADVANCED canonical keys in `static/js/modules/muscle-selector.js`
    (`SIMPLE_TO_ADVANCED_MAP`). Each MuscleMap muscle slug maps to exactly one
    advanced key per side via SLUG_SIDE_TO_KEY below.
  - cosmetic parts (head / hair / hands / feet / knees / ankles) go into a
    non-interactive `<g class="body-outline">` so the silhouette reads as a
    full human figure without being clickable.

Coordinate space is kept verbatim from upstream (`BodyViewBox`): anterior
`viewBox="0 95 727 1280"`, posterior `viewBox="718 95 727 1280"` (both bodies
live on one 1445-wide canvas; the non-zero posterior min-x crops the front
half). Stroke weight for this larger viewBox is handled by id-scoped rules in
`static/css/pages-workout-plan.css` (the shared `.muscle-region` widths are
tuned for the ~268-wide workout-cool art), so dark-mode colour rules still win.

Deterministic: same vendored source -> byte-identical SVGs. Re-run after bumping
the vendored files:  python scripts/build_musclemap_svgs.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# Vendored upstream
# ----------------------------------------------------------------------------

VENDOR_DIR = Path("static/vendor/musclemap")
OUT_DIR = Path("static/bodymaps/hypertrophy-advanced")

# MuscleMap male body view boxes (BodyPathData.swift -> BodyViewBox).
ANTERIOR_VIEWBOX = "0 95 727 1280"
POSTERIOR_VIEWBOX = "718 95 727 1280"

# ----------------------------------------------------------------------------
# (slug, side) -> advanced canonical key, or None to render as a non-interactive
# body-outline part, or "" to skip the path entirely (overlapping duplicate).
#
# Sides: "anterior" (MaleFrontPaths) / "posterior" (MaleBackPaths).
#
# Keys MUST match the leaf values of SIMPLE_TO_ADVANCED_MAP in
# static/js/modules/muscle-selector.js. tests/test_muscle_selector_mapping.py
# (TestFirstPartyAdvancedSvgCoverage) asserts the full per-side key set below.
# ----------------------------------------------------------------------------

OUTLINE = None   # render in <g class="body-outline">, non-interactive
SKIP = ""        # drop (overlapping parent/sub duplicate or unused on this side)

SLUG_SIDE_TO_KEY: dict[tuple[str, str], str | None] = {
    # ---- Anterior (front) ----
    # MuscleMap's *parent* muscle shapes tile into a clean human figure; its
    # overlapping sub-region ovals (upperChest/upperAbs/innerQuad/...) are small
    # schematic blobs that leave gaps, so we use the parents and drop the subs.
    ("chest", "anterior"): "chest",
    ("abs", "anterior"): "abs",
    ("quadriceps", "anterior"): "quadriceps",
    ("deltoids", "anterior"): "front-deltoid",
    ("frontDeltoid", "anterior"): SKIP,     # use parent deltoid cap
    ("biceps", "anterior"): "biceps",
    ("triceps", "anterior"): "triceps",
    ("obliques", "anterior"): "obliques",
    ("serratus", "anterior"): SKIP,         # covered by obliques
    ("calves", "anterior"): "calves",
    ("tibialis", "anterior"): "calves",     # shin also selects calves
    ("adductors", "anterior"): "adductors",
    ("neck", "anterior"): "neck",
    ("forearm", "anterior"): "forearms",
    ("upperChest", "anterior"): SKIP,
    ("lowerChest", "anterior"): SKIP,
    ("upperAbs", "anterior"): SKIP,
    ("lowerAbs", "anterior"): SKIP,
    ("innerQuad", "anterior"): SKIP,
    ("outerQuad", "anterior"): SKIP,
    ("hipFlexors", "anterior"): SKIP,
    ("trapezius", "anterior"): OUTLINE,     # front trap shelf, not in front model
    ("hands", "anterior"): OUTLINE,
    ("knees", "anterior"): OUTLINE,
    ("ankles", "anterior"): OUTLINE,
    ("feet", "anterior"): OUTLINE,
    ("head", "anterior"): OUTLINE,
    ("hair", "anterior"): OUTLINE,
    # ---- Posterior (back) ----
    ("neck", "posterior"): "neck",
    ("trapezius", "posterior"): "trapezius",
    ("deltoids", "posterior"): "rear-deltoid",
    # The MuscleMap "upperBack" slug is the big lat-wing sweep; tag it as the
    # lats (the back-width muscle users train). Rhomboids/upper-back have no
    # distinct MuscleMap geometry and stay legend-only in the selector.
    ("upperBack", "posterior"): "lats",
    ("triceps", "posterior"): "triceps",
    ("lowerBack", "posterior"): "lower-back",
    ("forearm", "posterior"): "forearms",
    ("gluteal", "posterior"): "gluteal",
    ("adductors", "posterior"): "hamstring",  # posterior inner thigh -> hamstrings
    ("hamstring", "posterior"): "hamstring",
    ("calves", "posterior"): "calves",
    ("hands", "posterior"): OUTLINE,
    ("ankles", "posterior"): OUTLINE,
    ("feet", "posterior"): OUTLINE,
    ("head", "posterior"): OUTLINE,
    ("hair", "posterior"): OUTLINE,
}

# Cosmetic outline fill/stroke (light mode); dark mode stroke comes from the
# `.body-outline` rule in pages-workout-plan.css.
OUTLINE_FILL = "#d9dee4"
OUTLINE_STROKE = "#3a4a63"

# ----------------------------------------------------------------------------
# Swift parsing
# ----------------------------------------------------------------------------

BLOCK_RE = re.compile(r"BodyPartPathData\((.*?)\n\s*\)\s*,?", re.DOTALL)
SLUG_RE = re.compile(r"slug:\s*\.(\w+)")
STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"', re.DOTALL)


def _array(chunk: str, key: str) -> list[str]:
    """Return the list of quoted strings in `key: [ ... ]` within a chunk."""
    m = re.search(rf"{key}:\s*\[(.*?)\]", chunk, re.DOTALL)
    if not m:
        return []
    return [s.strip() for s in STRING_RE.findall(m.group(1))]


def parse_swift(text: str) -> list[tuple[str, list[str]]]:
    """Parse a Male*Paths.swift file into [(slug, [d, ...]), ...] in order.

    common/left/right are flattened: every path of a slug renders as its own
    region/outline element (bilateral muscles become two paths sharing a key).
    """
    out: list[tuple[str, list[str]]] = []
    for block in BLOCK_RE.finditer(text):
        chunk = block.group(1)
        sm = SLUG_RE.search(chunk)
        if not sm:
            continue
        slug = sm.group(1)
        paths = _array(chunk, "common") + _array(chunk, "left") + _array(chunk, "right")
        if paths:
            out.append((slug, paths))
    return out


# ----------------------------------------------------------------------------
# SVG emission
# ----------------------------------------------------------------------------

def _clean_d(d: str) -> str:
    """Collapse whitespace/newlines inside a path d string."""
    return re.sub(r"\s+", " ", d).strip()


def render_svg(*, side: str, view_box: str, body_id: str,
               parsed: list[tuple[str, list[str]]]) -> str:
    outline: list[str] = []
    regions: list[tuple[str, str, str]] = []  # (slug, key, d)

    for slug, paths in parsed:
        mapping = SLUG_SIDE_TO_KEY.get((slug, side), SKIP)
        for d in paths:
            d = _clean_d(d)
            if mapping is OUTLINE:
                outline.append(d)
            elif mapping == SKIP:
                continue
            else:
                assert mapping is not None  # narrowed: real canonical key, not OUTLINE/SKIP
                regions.append((slug, mapping, d))

    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append("<!--")
    parts.append(f"  Hypertrophy Toolbox Advanced Body Map - {side.capitalize()}")
    parts.append("  Art: MuscleMap (melihcolpan/MuscleMap) @ v1.6.4, MIT License.")
    parts.append("  See static/vendor/musclemap/ (LICENSE + VERSION) and README.md.")
    parts.append("  Generated by scripts/build_musclemap_svgs.py - do not edit by hand.")
    parts.append("-->")
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
        f'id="{body_id}" role="img" aria-label="Advanced {side} muscle map">'
    )
    parts.append("  <defs>")
    parts.append("    <style>")
    parts.append("    .body-outline path { pointer-events: none; }")
    parts.append("    </style>")
    parts.append("  </defs>")
    parts.append("")
    parts.append('  <g class="body-outline" aria-hidden="true">')
    for d in outline:
        parts.append(
            f'    <path fill="{OUTLINE_FILL}" stroke="{OUTLINE_STROKE}" '
            f'stroke-width="1.2" stroke-linejoin="round" d="{d}"/>'
        )
    parts.append("  </g>")
    parts.append("")
    parts.append('  <g class="muscle-regions">')
    last_slug = None
    for slug, key, d in regions:
        if slug != last_slug:
            parts.append(f"    <!-- {slug} -> {key} -->")
            last_slug = slug
        parts.append(
            f'    <path class="muscle-region" data-canonical-muscles="{key}" d="{d}"/>'
        )
    parts.append("  </g>")
    parts.append("</svg>")
    parts.append("")
    return "\n".join(parts)


def build(vendor_dir: Path) -> dict[str, str]:
    front = parse_swift((vendor_dir / "MaleFrontPaths.swift").read_text("utf-8"))
    back = parse_swift((vendor_dir / "MaleBackPaths.swift").read_text("utf-8"))
    return {
        "body_anterior.svg": render_svg(
            side="anterior", view_box=ANTERIOR_VIEWBOX,
            body_id="body-anterior-hypertrophy-advanced", parsed=front,
        ),
        "body_posterior.svg": render_svg(
            side="posterior", view_box=POSTERIOR_VIEWBOX,
            body_id="body-posterior-hypertrophy-advanced", parsed=back,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--vendor-dir", type=Path, default=VENDOR_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--print-stats", action="store_true")
    args = parser.parse_args(argv)

    outputs = build(args.vendor_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        target = args.out_dir / name
        target.write_text(content, encoding="utf-8", newline="\n")
        print(f"[build_musclemap_svgs] wrote {target} ({len(content)} bytes)", file=sys.stderr)
        if args.print_stats:
            keys = sorted(set(re.findall(r'data-canonical-muscles="([^"]+)"', content)))
            print(f"    {len(keys)} keys: {keys}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
