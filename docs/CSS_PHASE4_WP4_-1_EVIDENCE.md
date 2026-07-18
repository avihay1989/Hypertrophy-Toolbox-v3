# WP4.-1 Cascade and Load-Order Evidence

Verified 2026-07-16 from committed `main` at `8c6acb6` in the isolated
`wt/wp4-cascade-foundation` worktree. The worktree was created with
`scripts/new-worktree.ps1 -Seed visual`; Playwright used only
`artifacts/e2e/database.e2e.db`.

## Runtime loading audit

Repository-wide inspection covered every stylesheet `<link>`, Jinja `page_css`
block, CSS file, SCSS input, test, script, and workflow reference.

- `templates/base.html` owns the same eight app-wide bundles and the separate
  Bootstrap artifact. Final local order is `tokens.css`,
  `bootstrap.custom.min.css`, `base.css`, `layout.css`, `components.css`,
  `navbar.css`, `a11y.css`, the child `page_css` block, `motion.css`, then
  `theme-dark.css`. Tokens therefore precede Bootstrap's SCSS-owned consumers,
  every other global consumer, and every route bundle.
- The ten route owners are unchanged: welcome, workout plan, workout log,
  weekly summary, session summary, progression, user profile, body composition,
  volume splitter, and backup each load their existing `pages-*.css` bundle.
  `/fatigue` continues to use the fatigue SCSS compiled into Bootstrap; error
  pages continue to use only global CSS.
- External styles remain Google Fonts and Font Awesome globally, plus Flatpickr
  on progression. They are third-party sheets, not app bundle owners.
- Runtime ownership remains exactly 18 app bundles (8 global + 10 route), with
  `bootstrap.custom.min.css` separate from the cap.

## Cascade audit

Before WP4.-1, first occurrence established the implicit layer sequence as
`workout`, `navbar`, `workout-dropdowns`, `welcome`: `components.css` opened
`workout`, `navbar.css` opened `navbar`, and the plan/welcome route bundles
introduced the remaining names. WP4.-1 declares that same sequence once at the
top of the first local sheet:

```css
@layer workout, navbar, workout-dropdowns, welcome;
```

The declaration covers every existing named layer. All 19 local runtime sheets
(18 app bundles plus Bootstrap) still contain unlayered rules; the four files
with named layer blocks also retain unlayered sections. This packet does not
move rules into or out of layers, change specificity, or remove `!important`.

## Compiled Bootstrap selector inventory

The CSSOM audit of `static/css/bootstrap.custom.min.css` records:

| Metric | Count |
|---|---:|
| Bytes | 100,273 |
| Top-level rules | 775 |
| Selector-rule occurrences (including nested media rules) | 1,097 |
| Selector entries before deduplication | 1,562 |
| Unique selector groups | 1,059 |
| Unique selector entries | 1,429 |

Of the 1,429 unique entries, 1,314 come from the selected Bootstrap 5.1.3
core/layout/component/helper/utility imports. The remaining 115 are app-owned
selectors compiled from the two existing SCSS partials:

- `scss/_fatigue.scss`: 58 entries across `.fatigue-badge*`, `.fatigue-bar*`,
  `.fatigue-page*`, `.fatigue-sfr-card*`, fatigue band classes, responsive
  variants, and `[data-theme=dark]` variants.
- `scss/pages/_workout_plan_volume_panel.scss`: 57 entries across
  `.volume-active-summary*`, `.vp-*`, `#vpToggle`, `.activate-plan`,
  `.volume-history-section`, status variants, responsive variants, and
  `[data-theme=dark]` variants.

This is collision evidence, not a relocation: SCSS remains the owner of both
families. No SCSS changed, so `npm run build:css` was intentionally not run.
The compiled CSS SHA-256 remains
`0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.

## Verification

Pre-change baseline:

- Vitest: 93 passed.
- Full pytest: 1,715 passed, 2 known-red catalog invariants. The required visual
  worktree seed contains 633 blank primary-muscle values and 454 blank movement
  patterns; both failures predate CSS edits.
- Required functional Chromium set: 407 passed in 10.3 minutes.
- Seeded visual pair: 48 passed, 2 known animated-GIF frame mismatches, 16 not
  run after Playwright's failure stop. The reds were 6,262 pixels in
  `plan-desktop-light-advanced` and 1,039 pixels in `workout-plan desktop dark`,
  localized to looping navbar/exercise GIFs.

Post-change gate:

- Focused CSS contracts: 4 passed; blocking flake8: 0; `tsc --noEmit`: passed;
  Vitest: 93 passed.
- Full pytest: 1,719 passed plus the same 2 known-red catalog invariants (the
  four new passes are the CSS contracts).
- Required functional Chromium set: 407 passed in 10.3 minutes.
- Seeded visual pair reproduced the pre-change result and exact mismatch counts.
  Independent `visual.spec.ts` execution completed the full matrix at 47 passed
  and the same one GIF-only red. The thumbnail spec is file-level serial, so an
  animated-GIF mismatch skips its remaining cases; excluding one GIF red moves
  the mismatch to another plan case. Stabilizing that harness belongs to
  WP4.0a and was not folded into WP4.-1.
- No `--update-snapshots` command was used. The committed screenshot-tree
  aggregate hash stayed `5468e316f103291f67e88011e7281097c15f0c00`.
- `git diff --check` passed. The main checkout's live DB SHA-256 stayed
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

Next Phase 4 packet: WP4.0a, visual/functional selector hardening. No WP4.0a
change is included here.
