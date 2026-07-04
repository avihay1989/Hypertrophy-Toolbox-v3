# Phase 19 — CSS part 2

Line-by-line read of `static/css/pages-workout-log.css` (3368 lines, read in
three chunks: 1-1000, 1000-2017, 2000-3368), `static/css/pages-user-profile.css`
(1843), `static/css/layout.css` (1841), `static/css/pages-weekly-summary.css`
(1601), `static/css/pages-session-summary.css` (1587). Context read in full:
`.claude/rules/frontend.md`, `static/css/tokens.css`. Cross-checked against
`docs/REFACTOR_PLAN.md` v2 Phase 4 (WP4.1 tokenization, WP4.2 per-page
dark-mode unification, WP4.3 cross-bundle dedupe, ≥30% line-count reduction
target). Quantitative counts below are from `grep -c`/`grep -o | wc -l`
patterns run directly against each file (method stated per metric); "duplicate
selector" counts are `grep -oE '^\.[a-zA-Z0-9_.:-]+' file | sort | uniq -c`
(top-level selectors only, does not catch selector lists on one line).

---

## Cross-cutting headline finding (read this first)

**`pages-weekly-summary.css` and `pages-session-summary.css` are byte-identical
for 1587 of 1601 lines (99.1%).** `diff` shows the *only* difference is 14
trailing lines unique to `pages-weekly-summary.css` (an `#isolated_muscles_filter`
block, itself dead — see §(f) below). Every rule in `pages-session-summary.css`
— the entire glass frame system, dark-mode blocks, `frame-header-2025`,
tooltip/reduced-motion/high-contrast media queries — is a verbatim copy of
`pages-weekly-summary.css`. **[CONFIRMS-PLAN]** — this is exactly the "prime
suspect pair" the task brief called out, confirmed at the top end of what was
plausible (not "similar," actually identical).

**The same ~1352-line block is *also* byte-identical inside
`pages-workout-log.css`** (lines 2017–3368 there == lines 236–1587 of
`pages-weekly-summary.css`, confirmed via `diff` on the extracted ranges,
0 lines of difference). Grepping for `.frame-header-2025` and
`.collapsible-frame {` across the whole `static/css/` tree shows this same
boilerplate block also lives a **fourth time** in `pages-workout-plan.css`
(out of this phase's scope, but relevant to WP4.3 sizing) and a thinner,
non-glass variant in `layout.css` (`.frame-title`/`.input-frame`/`.action-frame`
only, see layout.css section). **[NEW]** — the plan's WP4.3 ("move rules
duplicated across ≥2 page bundles into `components.css`") undersizes the
opportunity if it's scoped only to weekly/session-summary: the real
extractable block is ~1350 lines duplicated 3-4x across page bundles, i.e.
~4000-5400 duplicate lines, of which roughly 2700-4050 lines are pure deletable
waste once consolidated into one shared location (`components.css` or a new
`frames.css`).

---

## pages-weekly-summary.css (1601 lines)

**Structure map:**
- `1-131`: file-header comment ("Shared volume status tokens...") +
  `.volume-indicator`/`.volume-badge`/`.low-volume`/`.medium-volume`/
  `.high-volume`/`.ultra-volume`/`.volume-classification`/`.volume-legend`
  + their dark-mode overrides.
- `83-104`: session/weekly summary table scroll-fix (`translateZ(0)` /
  `backface-visibility` hacks) + border-collapse forcing.
- `113-234`: Bootstrap `.table-striped` override (light + dark), table font
  styling "to match workout plan."
- `236-1587`: **verbatim-duplicated frame boilerplate** — `.frame-title`,
  `.filters-section`, `.input-frame`, `.action-frame`, `.collapsible-frame`
  (+ hover/collapsed states), `.frame-header`, `.workout-log-frame` (!),
  `.summary-frame`/`.summary-section`/`.summary-tables`, `.summary-header`,
  `.method-selector`, `.volume-legend` (redefined, see below),
  `.frame-header-2025` + icon rotation/expand-collapse animation +
  reduced-motion/high-contrast/tooltip media queries. This is the same block
  documented in the headline finding.
- `1588-1601`: trailing `#isolated_muscles_filter` block, absent from
  `pages-session-summary.css`.

**Hardcoded vs `var(--token)`:** 46 `var(--...)` usages vs 113 raw hex colors
and 113 `rgba()/rgb()` literals (method: `grep -oE`/`grep -o | wc -l`). Ratio
is roughly 1 token reference for every 5 hardcoded color values — heavily
under-tokenized relative to `pages-user-profile.css` (below), which is the
newer "Calm Glass" style.

**Dark-mode strategy:** classic duplicated light/dark rule-PAIRS, not a
custom-property swap — 86 `[data-theme='dark']` selector blocks, each
re-declaring full color/background/shadow values rather than swapping a
token. Zero `color-mix()` usage (confirms this file predates the newer
`--surface-*`/`--ink-*`/`color-mix()` pattern seen in `tokens.css`'s "Calm
Glass 2026" block and in `pages-user-profile.css`).

**`!important` density:** 116 occurrences in 1601 lines (~7.2%), concentrated
in the `.frame-header-2025 .collapse-toggle` glass-button block (~30 alone)
and the summary-table Bootstrap-override blocks.

**Within-file duplicate top-level selectors:** `.summary-section` (14×),
`.collapsible-frame.collapsed` (12×), `.summary-tables` (11×), `.summary-frame`
(11×), `.frame-header-2025` (9×), `.input-frame` (8×), `.volume-legend` (4×
— defined once at `:43` as a shared token, then **redefined** at `:1113` with
different values inside the duplicated frame block, i.e. the file
contradicts its own "shared token" header comment), `.filters-section.collapsible-frame.collapsed`
(4×), `.collapse-toggle` (4×).

**Breakpoints:** 22 `@media` blocks — the summary-frame responsive ladder
repeats the same 7-tier resolution scheme (720p/1366/1536/1600/1080p/1440p/4K)
seen throughout the codebase, plus 2 motion/contrast-preference queries.

## pages-session-summary.css (1587 lines)

Identical structure to `pages-weekly-summary.css` minus the trailing
`#isolated_muscles_filter` block (§ headline finding). All counts are
near-identical by construction: 46 `var()`, 111 hex (2 fewer — the deleted
tail block had 2 hex colors), 113 `rgba()`, 116 `!important`, 86 dark-mode
blocks, 22 media queries, 0 `color-mix()`. **[CONFIRMS-PLAN]** for the
weekly/session pairing; **[NEW]** for the exact percentage (99.1%, not just
"similar").

**Dead-looking selector check specific to this pair:** `#isolated_muscles_filter`
and `label[for="isolated_muscles_filter"]` (only in the weekly-summary copy)
have **zero** references in `templates/` or `static/js/` (`grep -rn` across
both, confirmed). **[NEW] [RISK-for-WP4.3]** — this selector should be
deleted outright during consolidation, not "merged" into the shared block;
carrying dead CSS into a shared `components.css` block would spread the dead
weight to every page that imports it.

---

## pages-workout-log.css (3368 lines — largest of the five)

**Structure map:**
- `1-2016`: workout-log-specific content — table column-width distribution
  (`nth-child(1)`...`nth-child(17)`, hardcoded percentages), the "2026 Glass
  Style" sticky-header/cell system (`thead th`/`td` gradients, both themes),
  the "COLUMN COLOR PAIRING SYSTEM" (5 metric lanes × planned/scored × light/dark
  = 20 near-identical gradient blocks, `:400-644`), editable-cell/date-cell/
  number-input-spinner styling, `#clearLogModal` overrides, "COMPREHENSIVE DARK
  MODE TEXT VISIBILITY FIXES" (`:1432-1511`), a second "FINAL OVERRIDE" glass
  block (`:1512-1900` — re-declares much of the `:207-390` header/cell styling
  with `.tbl`/`.tbl--responsive` selector variants layered on, i.e. **internal**
  duplication of the sticky-header glass gradient at two different specificity
  tiers), the "EXPLICIT METRIC LANE PAIRING" custom-property system
  (`:1620-1900`, itself duplicating the `:400-644` color-pairing block's five
  hues as CSS variables plus a third `#workout-log-table.table.table-calm`
  variant of the same five-hue system, `:1799-1900`), then custom
  spinner-button styling (`:1902-2016`).
- `2017-3368`: **the verbatim-duplicated frame-boilerplate block**, identical
  to `pages-weekly-summary.css:236-1587` (see headline finding). This means
  roughly 40% of this file's 3368 lines is pure copy-paste from the summary
  pages, despite `pages-workout-log.css` having no `.summary-frame`/
  `.summary-tables` content of its own to justify carrying `.summary-frame`
  rules (workout-log has no summary UI) — those ~200 lines of `.summary-frame`/
  `.summary-section`/`.summary-header`/`.volume-legend`/`.method-selector`
  rules are dead weight specific to this file. **[NEW] [RISK]** — confirms
  the plan's WP4.2 page-by-page approach must budget for "delete unused
  inherited rules," not just "unify dark mode," on this file.

**Hardcoded vs `var(--token)`:** 155 `var()` usages (highest raw count of the
five, but mostly `var(--frame-padding, ...)`/`var(--space-*, ...)` fallback
patterns, not the newer semantic tokens) vs 181 hex colors and 351 `rgba()/rgb()`
literals — by far the heaviest literal-color user of the five files (the
metric-lane color system alone accounts for ~140 `rgba()` literals across
light+dark×5 hues×2 states).

**Dark-mode strategy:** 217 `[data-theme='dark']` blocks — more than the
weekly+session totals combined (86 each) — because the metric-lane and
sticky-header glass systems each carry a full light/dark pair at multiple
specificity tiers. Zero `color-mix()`. This file is the worst dark-mode
duplication case of the five: **the color values themselves differ between
light/dark (they're not simple lightness inversions), so a naive
custom-property swap (WP4.2's stated approach) is not a drop-in replacement
here** — the five metric-lane hues use materially different RGB triples in
dark mode (e.g. min-reps light `96,165,250` vs the same variable name holding
a *different* semantic role in dark — actually here `--metric-dark-rgb` is a
separate declared variable per lane, so the pattern already *is* a
custom-property system, just an ad hoc one that pre-dates `tokens.css`'s
`--surface-*`/`--ink-*` vocabulary). **[RISK-for-WP4.2]** — migrating this to
the shared token vocabulary means either (a) keeping the bespoke
`--metric-rgb`/`--metric-dark-rgb` pattern as page-local tokens (contradicts
"unify" language) or (b) mapping 5 lanes × 2 themes × ~6 alpha steps to new
shared tokens, materially larger than the "replace hardcoded pairs" framing
in the plan text suggests.

**`!important` density:** 375 occurrences — the highest of the five files by
a wide margin (~11% of lines), concentrated in the sticky-header/cell glass
system and the `.frame-header-2025 .collapse-toggle` block (duplicated from
the summary pages, so those ~30 `!important`s are counted twice across the
codebase).

**Within-file duplicate top-level selectors:** `.workout-log-table` (130×,
expected for a table-heavy file), `.workout-log-frame` (46×), `.tbl--responsive.workout-log-table`
(16×), `.collapsible-frame.collapsed` (14×, duplicated from summary pages),
`.summary-section` (10×, dead — see above), `.frame-header-2025` (9×),
`.workout-log-controls-frame` (8×), `.progression-legend` (8×), `.input-frame`
(8×), `.summary-tables` (7×), `.summary-frame` (7×).

**Breakpoints:** 30 `@media` blocks — most of any file in this phase; the
7-tier resolution ladder appears independently for `.workout-log-frame`
padding, `.workout-log-table thead th` sizing, `.action-frame .btn` sizing,
and the duplicated `.summary-frame` ladder — i.e. the same 7 breakpoints are
re-declared 4 separate times for different rule targets in one file.

**Dead-selector spot-check (10 checked against `templates/`+`static/js/`):**
`#debug-info` (1 template ref — likely a dev-only leftover but not fully
dead), `.date-input` (3 refs, live), `#clearLogModal` (referenced, live),
`.workout-log-controls-frame` (2 refs, live), `.progression-legend` (1 ref,
live). No workout-log-specific dead selectors found in this spot-check beyond
the inherited `.summary-frame`/`#isolated_muscles_filter` dead weight already
noted.

---

## layout.css (1841 lines)

**Structure map:**
- `1-38`: `body`/`.navbar`/`.container-fluid` base layout.
- `40-237`: "Page Header - 2026 Glass/Neumorphic Style" (`.page-header`,
  `.header-underline`, `.summary-section h3`/`.section-title-glass`) + dark
  mode, all hardcoded hex/rgba, zero tokens.
- `199-242`: `.container`, `.input-frame`/`.action-frame` **shallow**
  duplicates (flat white background, `box-shadow: 0 2px 4px rgba(0,0,0,0.1)`
  — a completely different, non-glass visual from the page-bundle versions of
  the same class names). `.frame-title` here (`:227`) is a third visual
  treatment of that class name (plain `color: #333`, no underline, no glass).
  **[RISK]** — because `components.css` loads immediately after `layout.css`
  in `templates/base.html` (confirmed by reading the `<head>` block — actual
  order is `base.css, layout.css, components.css, navbar.css, a11y.css`, then
  `{% block page_css %}`, then `tokens.css, motion.css, theme-dark.css` at the
  very end) and page bundles load after that, these `layout.css` `.frame-title`/
  `.input-frame`/`.action-frame`/`.container` rules are **overridden on every
  page that has a matching page-bundle rule** (all of workout-log,
  weekly-summary, session-summary, workout-plan do). They are only "live" on
  pages with no page-specific override — worth an explicit audit before
  deleting outright.
- `244-1050`: the "RESPONSIVE STYLES" mega-section — the 7-tier breakpoint
  ladder repeated independently for: generic `.container`/`.uniform-dropdown`/
  `.form-container` sizing (`:260-914`), welcome-page `h1`/`p` font sizing
  (`:916-952`), and `.action-frame .btn` sizing (`:954-1048`) — **three
  independent copies of the same 7 breakpoints inside one file**, using two
  different media-query authoring styles (`@media (max-width: 1280px)` vs
  `@media screen and (max-width: 1280px)` for the *same* pixel value in
  different sections — confirmed via `grep -oE '@media[^{]*'`, both forms
  present).
- `1050-1841`: **a completely separate, self-contained "Responsive Tables
  CSS" system** (`.tbl`, `.tbl-wrap`, `.tbl-col-chooser`, `.tbl-view-mode-toggle`,
  container-query-based column priority hiding) with its own `:root` token
  block (`--tbl-*` custom properties, `:1070-1128`) that duplicates
  `tokens.css`'s job at a smaller scope (defines its own border/header-bg/
  hover-bg/stripe-bg tokens with a *separate* dark-mode override block, both
  `[data-theme="dark"]` and a `body.dark-mode` fallback that appears to be
  dead — the app uses `[data-theme]` exclusively per `frontend.md`'s dark-mode
  section, `grep -rn "dark-mode" static/js/modules/` would confirm but this
  fallback class selector has no matching JS toggle in this codebase's
  documented dark-mode module).

**Hardcoded vs `var(--token)`:** 62 `var()` vs 34 hex + 66 `rgba()/rgb()` —
proportionally the most token-friendly of the "old style" files (the `.tbl-*`
system uses its own `--tbl-*` custom properties extensively), but those are
page-local tokens, not the shared `tokens.css` vocabulary — a WP4.1
"tokenization audit" pass would need to decide whether to fold `--tbl-*` into
the shared token set or leave it as a self-contained component system.

**Dark-mode strategy:** only 6 `[data-theme='dark']` blocks in the whole
file (lowest of the five) — most of `layout.css`'s content (`.page-header`,
the responsive ladders) has **no dark-mode handling at all** in this file;
dark styling for `.page-header` etc. must live in `theme-dark.css` or be
absent. **[RISK-for-WP4.2-final]** — this file was not included in the
per-page WP4.2 list (correctly, since WP4.2-final owns shared bundles), but
its near-total absence of dark rules means WP4.2-final's `layout.css` pass
can't just "collapse light/dark pairs into token swaps" here — for most of
this file there is no pair to collapse; dark support must be *added*, not
unified, which is a larger lift than the WP4.2-final framing implies.

**Layout.css vs components.css overlap (explicitly requested):**
`grep`-based selector-name overlap check found only 2 shared top-level
selectors — `.form-container` and `.uniform-dropdown` — but both are defined
in **both** global bundles with different rules (`components.css` additionally
styles `.uniform-dropdown:focus`, `optgroup`, `option` states that `layout.css`
doesn't touch; `layout.css` only carries the breakpoint-driven width/height
ladder). Since `components.css` loads immediately after `layout.css` in
`base.html`, `components.css`'s `:589` base `.uniform-dropdown` rule and its
own breakpoint blocks (`:1051-1189`) win the cascade for any property both
files set — meaning `layout.css`'s 11 `.uniform-dropdown` breakpoint blocks
and 9 `.form-container` breakpoint blocks are **only live for the properties
components.css doesn't redeclare** (unclear without a computed-style diff;
flagged as **[RISK]** for WP4.2-final/WP4.3 — this needs a rule-by-rule
property diff, not just a selector-name diff, before deleting either copy).
Beyond those two selectors, `layout.css` and `components.css` are otherwise
disjoint — `components.css` does not redefine `.frame-title`/`.input-frame`/
`.action-frame`/`.container`, so the "components.css territory" overlap is
narrower than the page-bundle-vs-page-bundle duplication documented above,
but the `tokens.css`-loads-last ordering issue (below) affects both files
equally.

**`!important` density:** 24 (~1.3% of lines) — lowest of the five files,
concentrated in the welcome/action-button breakpoint overrides (`height: Npx
!important`, `min-width: Npx !important`).

**Breakpoints:** 36 `@media` — most of any file in this phase; includes both
`@media (...)` and `@media screen and (...)` spellings for identical pixel
values (confirmed duplicate authoring style, not just duplicate content).

**[NEW] [RISK] Token-cascade load-order finding (affects all of Phase 4):**
Reading `templates/base.html:10-28` directly (not just `frontend.md`'s
description) shows the actual `<link>` order is:
```
base.css, layout.css, components.css, navbar.css, a11y.css,
{% block page_css %}  <-- route bundles insert here
tokens.css, motion.css, theme-dark.css
```
`.claude/rules/frontend.md` describes the 8 global bundles as
"`tokens.css`, `motion.css`, `base.css`, `layout.css`, `components.css`,
`navbar.css`, `theme-dark.css`, `a11y.css`" (tokens listed first), but the
actual document order puts `tokens.css` **after every route/page bundle**.
This works today only because nothing outside `tokens.css` itself
re-declares the same `:root` custom-property names — if a future WP4.1/4.2
page bundle adds a `:root`-scoped token override (e.g. a page-specific
`--frame-padding` tweak), `tokens.css`'s later `:root` block would silently
win the cascade and clobber it, the opposite of the intuitive "more specific
page CSS wins" expectation. **This should be corrected (or at minimum
explicitly documented as intentional) before WP4.1 lands new tokens**, since
WP4.1's entire premise — "define missing tokens, no visual change" — assumes
token definitions are stable and consumed downstream, not sitting after the
consumers in source order.

---

## pages-user-profile.css (1843 lines)

**Structure map:** almost entirely 2024-era "Calm Glass" design-system code
(distinct from the four files above), organized by feature: frame-header-2025
collapse-toggle override scoped to `.user-profile-page` (`1-105`), onboarding/
explainer disclosure widget (`107-296`), calibration review table (`297-358`),
reference-lifts form + segmented/checkbox inputs (`359-882`), responsive
grid-area layout switches for 3 breakpoint tiers (`723-899`), "How the system
sees you" insights card — band meter, donut, tiles, cohort bars (`900-1465`),
bodymap/coverage-map SVG + popover + legend (`1466-1843`).

**Hardcoded vs `var(--token)`:** 261 `var()` usages vs 274 hex + 28 `rgba()`
— by far the best-tokenized file of the five (roughly 1:1 token-to-hex
ratio, vs weekly/session-summary's 1:5). Almost every hex value found is a
**fallback inside a `var()` or `color-mix()` call**, e.g.
`color-mix(in srgb, var(--accent, #4c6ef5) 75%, var(--ink-1, #22283a))` — i.e.
this is genuinely using the token system with defensive fallbacks, not
hardcoding. 144 `color-mix()` usages (the only file of the five that uses it
at all) — this is the "Calm Glass 2026" pattern from `tokens.css:374-433`
(`--surface-*`, `--ink-*`, `--accent`) in active use. **[CONFIRMS-PLAN]** —
this file is a template for what WP4.2 should make the other four look like;
it also proves the target pattern already exists and works in production, so
WP4.2 isn't inventing a new approach, just propagating an existing one.

**Dark-mode strategy:** 62 `[data-theme='dark']` blocks, but almost every one
is a **single-property override** re-pointing a `color-mix()` call at
`--surface-1`/`--ink-2` instead of `--surface-2`/`--ink-1` — genuinely close
to "token swap," not full rule duplication. This is the only file of the
five where dark mode is cheap to maintain (small, targeted overrides) rather
than a parallel copy of every rule.

**`!important` density:** 0 (confirmed via `grep -o '!important' | wc -l`) —
the only file of the five with zero `!important` usage. Strong signal this
newer code was written without needing to fight cascade/specificity battles
from older glass-era CSS.

**Within-file duplicates:** minimal — this file reads as purpose-built rather
than copy-pasted; no top-level selector repeats more than 2-3× (mostly
dark-mode pairs), unlike the 10-14× repeats in the older files.

**Breakpoints:** 14 `@media` — fewest of the five, all purposeful
(`1200px`/`1600px` grid-area layout switches, `768-1199.98px` tablet,
`991.98px`/`767.98px`/`575.98px` mobile stacking, 1 `prefers-reduced-motion`).

**Dead-selector spot-check:** `.profile-calibration-ignored-row`,
`.reference-lift-hand-hint`, `.profile-autosave-retry`,
`.profile-bodymap-sr-summary` all confirmed referenced in
`templates/`/`static/js/` (1 ref each — likely a single shared partial
template, not dead). No dead selectors found in this file's spot-check.

---

## Cross-bundle duplication summary (task item e)

| Pair | Shared/near-identical lines | % of smaller file |
|---|---|---|
| `pages-weekly-summary.css` ↔ `pages-session-summary.css` | 1587 of 1587 | **99.1%** (weekly has 14 extra dead lines) |
| `pages-workout-log.css` (`:2017-3368`) ↔ `pages-weekly-summary.css` (`:236-1587`) | 1352 | **84.4%** of workout-log's total 1601-line-equivalent block, **~40%** of workout-log's whole 3368-line file |
| `.volume-indicator`/`.volume-badge`/`.low-volume`/etc. | ~30 lines | present **verbatim a third time** in `pages-volume-splitter.css` (out of this phase's file list, confirmed via grep) despite the weekly/session-summary file's own header comment claiming these are already "shared volume status tokens" — the comment describes an aspiration, not the actual file layout (there is no shared file; it's copy-pasted 3×) |
| `.frame-header-2025`/`.collapsible-frame` boilerplate | ~1350 lines | also present in `pages-workout-plan.css` (4th copy, out of scope for this phase but relevant to WP4.3 total-line-count planning) |

**[NEW]** Net effect: of the 5 files read this phase (10,240 lines total),
roughly **2700-2850 lines are exact duplicates of content that exists
verbatim in at least one sibling file** (the weekly/session pair's ~1587
shared lines counted once, plus workout-log's 1352-line copy of the same
block counted as pure addition). That's ~26-28% of this phase's file set
before even touching the cross-page-bundle overlap with `pages-workout-plan.css`
or the layout.css/components.css `.uniform-dropdown`/`.form-container`
overlap. This materially de-risks the plan's ≥30% total-`static/css`
reduction target for these five files specifically — WP4.3 (cross-bundle
dedupe) alone, scoped just to the weekly/session/workout-log frame block,
could plausibly hit 25-30% reduction on this subset without touching
hardcoded-color tokenization at all.

---

## Cross-cutting seeds

1. **[CONFIRMS-PLAN, sized larger than assumed]** Weekly-summary and
   session-summary are 99.1% byte-identical (not just "similar" — this was
   confirmed with `diff`, not eyeballing). The same ~1350-line frame-boilerplate
   block is a **third** verbatim copy inside `pages-workout-log.css` and a
   **fourth** inside `pages-workout-plan.css`. WP4.3's "cross-bundle dedupe"
   should be scoped and planned as one extraction (~1350 lines → `components.css`
   or a new `frames.css`) touching 4 page bundles at once, not discovered
   incrementally per-page during WP4.2.
2. **[NEW] [RISK]** `tokens.css` loads *after* `layout.css`, `components.css`,
   `navbar.css`, `a11y.css`, and every route's `page_css` block in the actual
   `templates/base.html` `<head>` (confirmed by reading the file directly —
   `.claude/rules/frontend.md` lists tokens.css first, which does not match
   reality). No current bug because nothing else sets the same `:root`
   custom-property names, but this inverts the expected "tokens define
   defaults, later CSS can override" cascade model and should be fixed or
   explicitly justified before WP4.1 adds new tokens that any page bundle
   might want to locally override.
3. **[NEW] [RISK-for-WP4.2]** `pages-workout-log.css`'s dark-mode duplication
   is not a simple "swap the same values" case: it uses a bespoke five-hue
   `--metric-rgb`/`--metric-dark-rgb` custom-property system (already
   partially tokenized, just not with the shared `tokens.css` vocabulary) with
   materially different RGB values per theme, layered at 2-3 specificity
   tiers with 375 `!important`s (highest of any file audited this phase).
   WP4.2's "replace hardcoded light/dark rule pairs with token-consuming
   rules" framing undersizes this file's actual migration cost.
4. **[CONFIRMS-PLAN]** `pages-user-profile.css` is the template WP4.2 should
   be copying: 0 `!important`, 144 `color-mix()` usages, ~1:1 token-to-hex
   ratio, and dark mode implemented as single-property token swaps rather
   than full rule duplication. It proves the target end-state already works
   in this codebase.
5. **[NEW]** `layout.css`'s "Responsive Tables CSS" section (`:1050-1841`,
   ~800 lines, `.tbl`/`.tbl-wrap`/`.tbl-col-chooser`/container-query column
   hiding) is a self-contained component system with its own `--tbl-*` token
   block and its own separate dark-mode override (plus an apparently-dead
   `body.dark-mode` class fallback alongside the `[data-theme="dark"]` rule
   the rest of the app uses) — this reads like it belongs in `components.css`
   rather than `layout.css`, and is a good WP4.3 candidate independent of the
   frame-boilerplate finding above.
6. **[NEW]** Confirmed-dead selectors this phase (zero references in
   `templates/`+`static/js/`, safe deletion candidates ahead of any
   consolidation so dead weight isn't propagated into a shared file):
   `#isolated_muscles_filter` + its label (weekly-summary only), the
   `tooltipFadeIn` `@keyframes` (weekly-summary, session-summary, workout-log
   — declared 3×, used 0×), `.tbl-show-sm`/`.tbl-show-md`/`.tbl-show-lg`/
   `.tbl-hide-sm` (layout.css "breakpoint helpers" section — none referenced
   anywhere).
