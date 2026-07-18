# CSS Phase 4 — WP4.1 Token Inventory and Alias Plan

**Design frozen before consumer changes:** 2026-07-17 on
`wt/wp4-1-token-vocabulary` at
`9ee763889e1e021d6cd1fe8d8782dccb4cb40d52`.

This packet inventories the current vocabulary, defines the alias and
deprecation direction, and adds measurement tooling. It does not delete
selectors, relocate declarations, reduce specificity, remove `!important`,
or start WP4.2.

## Measurement scope

The inventory covers all 18 hand-maintained runtime CSS bundles and the three
SCSS sources. The generated `static/css/bootstrap.custom.min.css` and its source
map are excluded from lint/token counts and remain byte-locked. Counts are
lexical occurrences, so a shadow or gradient containing several literals can
contribute more than one color or dimension.

| Metric | Pre-change count |
| --- | ---: |
| Source files | 21 |
| Lines | 30,768 |
| Bytes | 906,707 |
| Custom-property definition occurrences | 815 |
| Unique custom-property definitions | 338 |
| `var()` references | 2,270 |
| Unique referenced properties | 308 |
| Hex literals | 2,263 |
| `rgb`/`rgba`/`hsl`/`hsla` functions | 2,608 |
| Dimension/percentage literals | 7,086 |
| Duration literals | 262 |
| `!important` occurrences | 2,570 |

The most repeated raw colors are `#4c6ef5` (225), `#fff` (143), `#ffffff`
(117), and `#495057` (70). The most repeated dimensions are `1px` (816),
`8px` (476), `2px` (377), `4px` (371), `1rem` (268), and `0.5rem` (219).
These are inventory signals only; replacing them is page-by-page WP4.3/4.4
work, not part of this packet.

## Spacing vocabulary decision

`--space-*` and `--s-*` overlap only at the default root size. They are not
interchangeable: `--space-*` is rewritten at seven viewport ranges, while
`--s-*` is a fixed pixel component scale. Aliasing one directly to the other
would change responsive behavior or root-font scaling.

The approved direction is therefore:

| Current name | Status | Canonical direction |
| --- | --- | --- |
| `--s-1` … `--s-7` | canonical | Fixed component spacing; unchanged values. |
| `--space-xs` … `--space-2xl` | deprecated compatibility aliases | Alias to new `--layout-space-*` names. Existing consumers stay valid. |
| `--layout-space-xs` … `--layout-space-2xl` | canonical | Responsive layout spacing; receives the exact former `--space-*` values at every breakpoint. |

No `--space-*` consumer is migrated in WP4.1. Future work must choose fixed
`--s-*` or responsive `--layout-space-*` by intent, not by a coincidental
default-value match.

Pre-change spacing measurements:

| Namespace | Unique definitions | Definition occurrences | Unique refs | Ref occurrences | Defined, unused |
| --- | ---: | ---: | ---: | ---: | ---: |
| `--space-*` | 6 | 41 | 4 | 35 | 2 |
| `--s-*` | 7 | 7 | 6 | 55 | 1 |

## Six local namespaces

| Namespace | Unique defs | Def occurrences | Unique refs | Ref occurrences | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| `--wl-*` | 53 | 71 | 48 | 217 | Keep page semantics. Alias only exact shared status/duration values now. |
| `--nav-*` | 49 | 72 | 44 | 194 | Keep navbar geometry/palette. Alias exact spacing values; existing pill tokens already consume shared Calm Glass tokens. |
| `--bc-*` | 10 | 13 | 10 | 17 | Retain. Five body-fat bands are feature semantics, not global status colors. |
| `--backup-*` | 6 | 6 | 5 | 17 | Retain until the backup page's WP4.3 pass; no visually equivalent shared palette exists. |
| `--volume-*` | 9 | 18 | 6 | 9 | Retain. Track and panel tokens belong to different volume surfaces and have theme remaps. |
| `--fatigue-*` | 12 | 85 | 12 | 34 | Retain. Values are intentionally rebound per band/theme inside SCSS and compile into Bootstrap. |

Defined-but-unreferenced local tokens are recorded, not deleted: five `--wl-*`,
five `--nav-*`, one `--backup-*`, and three `--volume-*`. Selector/token
deletion belongs to WP4.2 or the appropriate page packet after reachability
proof.

## Exact neutral aliases approved for WP4.1

Only byte-equivalent values with the same unit and semantics are aliased:

| Compatibility token | Canonical source | Preserved value |
| --- | --- | --- |
| `--space-xs` … `--space-2xl` | matching `--layout-space-*` | All existing root/breakpoint values |
| `--wl-success` | `--success` | `#10b981` |
| `--wl-warning` | `--warning` | `#f59e0b` |
| `--wl-danger` | `--danger` | `#ef4444` |
| `--wl-duration-fast` | `--dur-fast` | `150ms` (the existing reduced-motion `0ms` override stays local) |
| `--nav-gap` | `--s-3` | `12px` |
| `--nav-padding-y` | `--s-3` | `12px` |

Near matches are deliberately not aliases: rem-to-pixel spacing, navbar radii
versus spacing tokens, `--wl-duration-base` (250ms versus 240ms),
`--wl-duration-slow` (400ms versus 360ms), and feature palettes. Those would
change behavior or erase useful semantics.

## Stylelint baseline

Stylelint `16.11.0` and `postcss-scss` `4.0.9` are exact dev-dependency pins.
The rules measure hardcoded colors, `!important`, duplicate declarations and
selectors, descending specificity, selector ceilings, unknown properties, and
invalid hex values. They intentionally report debt without fixing or blocking
it.

| Rule | Pre-change warnings |
| --- | ---: |
| Hardcoded color/property values | 3,378 |
| `declaration-no-important` | 2,566 |
| Descending specificity | 783 |
| Selector ID ceiling | 191 |
| Selector specificity ceiling | 188 |
| Duplicate selectors | 86 |
| Duplicate properties | 8 |
| Unknown properties | 2 |
| All other configured rules | 0 |
| **Total** | **7,202** |

All 21 sources parsed; there were zero parse errors, invalid-option warnings,
or errored files. The compact committed report is
`docs/CSS_PHASE4_WP4_1_STYLELINT_BASELINE.json`. CI uploads the full raw JSON
and a compact current summary, then reports a non-blocking delta from this
baseline. No existing job name or required-check context is changed.
