# Phase 20 — CSS part 3 + SCSS

Line-by-line read of `static/css/navbar.css` (1536), `static/css/pages-welcome.css`
(1084), `static/css/pages-volume-splitter.css` (1059), `static/css/a11y.css` (813),
`static/css/theme-dark.css` (621), `static/css/pages-backup.css` (497),
`static/css/tokens.css` (433), `static/css/pages-progression.css` (341),
`static/css/pages-body-composition.css` (324), `static/css/base.css` (123),
`static/css/motion.css` (71), `scss/_fatigue.scss` (528),
`scss/pages/_workout_plan_volume_panel.scss` (299), `scss/custom-bootstrap.scss`
(53), plus `.claude/rules/frontend.md`, `docs/CSS_OWNERSHIP_MAP.md`,
`package.json`, and the `<head>` of `templates/base.html` for load-order and
build-pipeline context. Cross-checked against `docs/REFACTOR_PLAN.md` v2 Phase 4
(WP4.0–WP4.3) and spot-checked selector usage against `templates/**` and
`static/js/**` via grep.

---

## Q1 — `tokens.css` token-vocabulary inventory (433 lines)

Two unrelated token systems live in this one file, added at different times:

- **Legacy responsive scale** (`:17-371`): `--space-{xs,sm,md,lg,xl,2xl}`,
  `--container-max-{sm,md,lg,xl,xxl,fhd,qhd}`, `--input-{height-sm/md/lg,
  padding-x/y, font-size, min-width}`, `--btn-{padding-x/y, font-size,
  height}`, `--frame-{padding, gap, border-radius}`, `--table-cell-{padding-x/y},
  --table-font-size`, `--font-size-{xs,sm,base,lg,xl,2xl,3xl}`. Re-declared
  wholesale inside **7 breakpoint media queries** (`max-width:1280px` through
  `min-width:2561px`) — every one of the ~30 properties gets a new value at
  every breakpoint (comment at `:7-14` documents 7 target resolutions:
  720p/HD, 1366×768, 1536×864, 1600×900, 1920×1080, 2560×1440, 4K). No gaps
  here — this system is complete and internally consistent, just extremely
  verbose (~250 lines of pure breakpoint value tables).
- **"Calm Glass 2026" token system** (`:374-433`, explicitly commented
  "Additive only: do not override legacy responsive or glass token names"):
  `--surface-{0,1,2}`, `--ink-{1,2,3}`, `--accent`/`--accent-ink`,
  `--success`/`--warning`/`--danger`, `--shadow-{neu-out,neu-in,elev-1,elev-2}`,
  `--calm-glass-{bg,border,blur,sat}`, `--r-{sm,md,lg,xl,pill}`, `--s-{1..7}`
  (a *second*, differently-named spacing scale parallel to `--space-*`),
  `--ease-out`, `--dur-{fast,base,slow}`, `--font-sans`. Dark-mode override at
  `:422-433` via `[data-theme="dark"]` swaps `--surface-*`/`--ink-*`/shadow
  values only — the intended token-swap pattern WP4.2 wants everywhere else.
- **Pre-existing third mini-system in `base.css`** (`:6-16`, not in
  `tokens.css` at all): `--bs-border-color`, `--bs-table-border-color`,
  `--glass-{blur,bg,bg-hover,border,shadow,shadow-hover,inset}`,
  `--type-{body,h2,h3}` (fluid `clamp()` typography). `theme-dark.css`
  (`:14-21`) then defines a **second, dark-mode value** for the same
  `--glass-*` names inside `:where([data-theme="dark"])`. **[NEW]** — this is
  a third color/glass-effect token namespace that isn't in `tokens.css`, isn't
  named consistently with `--calm-glass-*`, and isn't discoverable by anyone
  auditing `tokens.css` alone.
- **Gaps for WP4.1** (confirmed by reading the other 13 files in this phase):
  every page/component invented its **own locally-scoped token family**
  instead of consuming `tokens.css`'s Calm Glass tokens — `--wl-*`
  (`pages-welcome.css`, ~35 tokens: colors, spacing, radii, shadows, fluid
  font sizes, easing/duration, a *third* duration-naming scheme
  `--wl-duration-{fast,base,slow}` vs. `tokens.css`'s `--dur-{fast,base,slow}`
  vs. `navbar.css`'s `--nav-transition{,-fast}`), `--nav-*` (`navbar.css`,
  ~25 tokens for its own colors/spacing/radii/shadows/typography, largely
  duplicating what `--surface-*`/`--ink-*`/`--r-*`/`--s-*` already cover),
  `--bc-*` (`pages-body-composition.css`, 10 tokens incl. 5 body-fat-band
  colors), `--backup-*` (`pages-backup.css`, 6 tokens, **no dark-mode
  variant at all** — see Q4), `--volume-*` (`pages-volume-splitter.css`, two
  separate blocks: `--volume-track-*` and a later `--volume-panel-*`/
  `--volume-row-*`/`--volume-muted-text` block), `--fatigue-*`
  (`scss/_fatigue.scss`, ~10 tokens per severity band, redefined 4× for
  light bands + 4× for dark bands). **None of these six local namespaces
  reference the shared `--surface-*`/`--ink-*`/`--accent`/`--success/
  warning/danger` tokens** — each hand-picked its own hex/rgba literals.
  This means WP4.1's "expand tokens.css… define missing tokens" work is not
  primarily about finding raw hardcoded literals (though there are plenty,
  see per-file sections below) — it's about **deciding whether these six
  parallel token namespaces should be collapsed into the shared vocabulary**,
  which is a bigger design decision than the plan's phrasing ("inventory
  hardcoded colors… define missing tokens") suggests. **[RISK]** for WP4.1
  scoping: a literal-only hardcoded-color count will undercount the real
  duplication, which lives one level up in these per-namespace token blocks.
- No token exists yet for the five body-fat-band colors
  (`--bc-band-{essential,athletes,fitness,average,obese}`), the four fatigue
  severity accents, or navbar's icon accent colors
  (`#6d5dfc`/`#0f9f8f`/`#d97706` for user-profile/body-composition/backup nav
  icons, `navbar.css:1377-1405`) — these are legitimately page/feature-specific
  semantic colors, not obviously token-worthy, but they're the kind of
  "hardcoded color" WP4.1's scripted inventory will surface and someone will
  need to judge case-by-case.

## Q2 — `theme-dark.css` (621 lines): what it actually overrides

Three generations stacked in one file, oldest first:

1. **`:where([data-theme="dark"])` legacy variable + component block**
   (`:2-453`): defines the *original* dark palette (`--bg-primary`,
   `--text-primary`, `--card-bg`, `--glass-*`, etc., `:2-22`), then ~40
   `:where()`-wrapped, `!important`-heavy overrides for: body background
   gradient, navbar border/shadow (comment at `:38-39` explicitly says navbar
   background itself is NOT handled here — "All navbar styling is handled by
   navbar.css to prevent double-layer glitch"), `.card`/`.modal-content`/
   `.dropdown-menu` glass effect, `.collapsible-frame`/`.filters-section`/
   `.summary-frame`/`.workout-log-frame`, **five separate, near-duplicate
   table dark-mode blocks** (`.table`, `.results-section .table`,
   `.table-responsive .table`, `#results-body`, `.table.table-hover` — all
   setting the same `background-color`/`color`/`border-color` triad against
   overlapping selector sets, `:107-453`), form controls incl. one
   exercise-search-specific block, buttons, the `.tbl-view-mode-toggle`
   component, headers, and a generic `transition: all 0.3s` rule applied to
   `body`/`.navbar`/`.card`/`.table`/`.form-control`/`.btn` regardless of
   theme (`:242-249`, runs in light mode too since it's not gated by
   `[data-theme="dark"]`).
2. **Workout Controls color-coded input backgrounds** (`:454-591`): five
   pastel-background input groups (`min_rep`/`max_rep_range` fuchsia,
   `rir`/`rpe` pistachio, `weight`/`sets` banana) each fully re-specified for
   dark mode with the **identical pastel hex values as light mode**
   (`#fce4ec`, `#e8f5e9`, `#fff9c4`, etc. — compare to whatever
   `pages-workout-plan.css` uses for the light-mode version, not read this
   phase but the values here look deliberately unchanged so the color-coding
   stays legible against dark text). This block exists solely because these
   specific `#workout[data-page="workout-plan"] input#*` selectors live in a
   *different* file (`pages-workout-plan.css`) than their dark-mode
   overrides — a direct, concrete instance of the "dark mode hand-duplicated
   across files" problem the plan cites.
3. **"Calm Glass 2026 dark mode tokens"** (`:593-621`, explicitly commented
   "Replaces the legacy dark-mode variables with the new tokens... Zero
   `!important`"): re-maps `--bg-primary`, `--text-primary`, `--card-bg`,
   `--glass-*`, etc. (the *same* names from block 1) to `var(--surface-0)`,
   `var(--ink-1)`, `var(--calm-glass-bg)`, etc. This is a real token-swap
   block, but it's appended **after** block 1 rather than replacing it —
   block 1's hardcoded hex dark values are now **dead** wherever block 3's
   variable remap covers the same custom-property name (both are inside
   `[data-theme="dark"]`/`:where([data-theme="dark"])`, same specificity
   class, block 3 wins on source order for the variable *values*, but block
   1's ~40 rules that hardcode raw colors directly — not through a
   `--bg-primary`-style variable — are untouched by block 3 and still fire).
- **[CONTRADICTS-PLAN]** on how clean-cut WP4.2-final's "delete or reduce to
  the token-swap block" goal is: block 3 already *is* that token-swap block
  and coexists with, rather than having replaced, blocks 1 and 2. Retiring
  `theme-dark.css` to just block 3 requires first proving every consumer of
  the legacy `--bg-primary`/`--text-primary`/etc. variable names (used across
  at least `pages-volume-splitter.css`, `pages-progression.css`'s dark rules
  read in Phase 19, and others) still resolves correctly once blocks 1/2's
  *hardcoded* (non-variable) overrides are gone — many of block 1's rules
  set colors directly (`background-color: var(--bg-secondary) !important` is
  fine, that's a variable; but e.g. `:167-190`'s `#exercise-search` block
  hardcodes `rgba(40, 40, 52, 0.7)` etc. with no variable indirection at
  all) and would need individual re-authoring, not a mechanical deletion.
  Block 2 (Workout Controls pastel inputs) is entirely non-variable hardcoded
  duplication and has zero token-swap equivalent yet — it cannot be deleted
  without either introducing new pastel-color tokens or moving the dark
  variant next to its light-mode counterpart in `pages-workout-plan.css`.
- Per-page-bundle theme-dark.css load bears on: navbar (border/shadow only,
  not background — see finding above), generic Bootstrap-ish components
  (card/modal/dropdown/table/form/button — these are "global bundle"
  concerns, `components.css`/`layout.css` territory, not really page-scoped),
  and one **workout-plan-page-specific** block (findings above). No
  welcome/backup/body-composition/progression-specific rules exist in this
  file — those four pages carry their own complete `[data-theme='dark']`
  rules locally (see Q4/per-file sections), so `theme-dark.css` is *not* the
  single source of dark-mode truth WP4.2-final's phrasing implies; it's one
  of many.

## Q3 — SCSS pipeline boundary (custom-bootstrap.scss + `_fatigue.scss` +
`_workout_plan_volume_panel.scss`)

- **Build command** (`package.json:6-7`): `sass --load-path=node_modules
  scss/custom-bootstrap.scss static/css/bootstrap.custom.min.css --style
  compressed`. Single entry point, single compiled output file.
- **`scss/custom-bootstrap.scss` (53 lines)** imports, in order: Bootstrap
  functions/variables/mixins/root/reboot, containers+grid, a curated
  component subset (buttons, button-group, nav, navbar, card, alert, badge,
  forms, tables, modal, dropdown, toasts, close — with an explicit
  "NOT included" comment list: accordion, breadcrumb, carousel, list-group,
  pagination, placeholders, popovers, progress, scrollspy, spinners,
  offcanvas), helpers+utilities, then two `$primary`/`$dark`/
  `$font-family-base` variable overrides, then **two page/feature partials**:
  `@import "pages/workout_plan_volume_panel";` and `@import "fatigue";`
  (`:52-53`).
- **[NEW] — the exact boundary answer**: `static/css/bootstrap.custom.min.css`
  is **not** a pure Bootstrap build artifact despite `.claude/rules/frontend.md`
  and `docs/CSS_OWNERSHIP_MAP.md` both describing it only as "Bootstrap build
  artifact" / "Bootstrap build artifact, excluded from the 18-file cap." It
  also contains the fully-compiled `.fatigue-badge`/`.fatigue-bar`/
  `.fatigue-sfr-card` component family (used by `templates/fatigue.html`,
  `templates/_fatigue_badge.html`, `templates/_fatigue_muscle_bar.html`,
  confirmed by grep) and the `.vp-*`/`.volume-active-summary` volume-panel
  drawer component family (used by `templates/workout_plan.html`, confirmed
  by grep). There is no separate `fatigue.css` or `volume-panel.css` on disk
  — SCSS-owned styling for these two features ships bundled inside the
  Bootstrap artifact, invisible to anyone auditing `static/css/*.css` file
  sizes or the 18-bundle cap (`.claude/rules/frontend.md` explicitly excludes
  `bootstrap.custom.min.css` from that cap, so this is a blind spot by
  design, not an oversight — but it means "search `static/css/` for
  `.fatigue-badge`" finds nothing, which could mislead a WP4 executor into
  thinking the class is unstyled or dead).
- **`_workout_plan_volume_panel.scss` self-duplication**: nearly every
  selector in the file is written as a **pair**, e.g.
  `.vp-header-summary, .volume-active-summary` (`:1-2`),
  `.vp-active-summary, .volume-active-summary` (`:11-12`),
  `.vp-active-summary.is-active, .volume-active-summary.is-active` (`:22-23`),
  repeated again for all the dark-mode variants (`:218-229`). This reads like
  an in-progress class rename (`vp-` prefix → `volume-` prefix, or vice
  versa) that was never finished — both class names are defined identically
  everywhere they co-occur, and grep confirms only `.volume-active-summary`
  is actually used in `templates/workout_plan.html`, while bare `.vp-*`
  classes (`.vp-backdrop`, `.vp-drawer`, `.vp-close`, `.vp-state`, `.vp-row`,
  `.vp-bonus`, etc. — the majority of the file, `:28-216`) are NOT paired
  with a `volume-` equivalent and are presumably the actual live drawer
  markup (not verified against the template's full drawer HTML this phase,
  but the pattern is that only the *summary pill* portion has the dual
  naming, not the drawer body). **[NEW]** — candidate for a small SCSS
  cleanup: confirm which of `.vp-active-summary`/`.vp-header-summary` vs.
  their `.volume-*` twins is actually referenced by
  `templates/workout_plan.html` and delete the unused one of each pair
  (repeated 4× across light + dark + `.is-active` variants ≈ 12 duplicate
  lines).
- **`_fatigue.scss` (528 lines)**: single-purpose, well-organized, three
  logical sections match three shipped features (badge, `/fatigue` page
  per-muscle bars, SFR cards — each section-commented with its originating
  phase, e.g. "Phase 2 Stage 2"). Uses nested SCSS (`&:hover`, `&::after`)
  unlike the flat plain-CSS convention everywhere else in `static/css/` —
  consistent with it being the one file in the whole CSS surface that's
  actually SCSS-authored rather than copied-in-as-CSS. No duplication found
  internally; every `--fatigue-*` custom property is scoped per
  band-modifier class (`.fatigue-light/-moderate/-heavy/-very-heavy/
  -unranked`) with light + dark values, cleanly following the exact
  token-swap pattern WP4.2 wants elsewhere. **[CONFIRMS-PLAN]** — this file
  is evidence the token-swap pattern is achievable codebase-wide; it's just
  not applied consistently yet (compare to `pages-backup.css`'s complete
  absence of dark-mode rules, Q4 below).
- **No hand-CSS duplicates SCSS-owned rules** — grepped `.fatigue-` and
  `.vp-`/`.volume-active-summary`/`.volume-panel` class names across
  `static/css/*.css`; the only hits are `pages-volume-splitter.css`'s
  **different, non-conflicting** `.volume-*` classes (`.volume-splitter-*`,
  `.volume-controls`, `.volume-value-pill`, `.volume-indicator`,
  `.volume-badge`, `.volume-classification`, `.volume-legend` — a distinct
  component family from the SCSS-owned `.volume-active-summary`/`.vp-*`
  drawer, confirmed by reading both fully, zero selector overlap despite the
  shared `volume-` word prefix being confusingly close). **[RISK]** — the
  naming collision between SCSS's `.volume-active-summary` (compiled into
  Bootstrap artifact, used on `workout_plan.html`) and plain-CSS's
  `.volume-*` family (`pages-volume-splitter.css`, used on
  `volume_splitter.html`) is a maintenance trap: a future edit to "volume"
  styling could easily target the wrong file, and a repo-wide
  `grep -rn "\.volume-"` (as WP4 dedupe work will do) returns two unrelated
  ownership domains that must not be merged.

## Q4 — Per-page-bundle findings

### `pages-welcome.css` (1084 lines)
- Entirely inside `@layer welcome { ... }` (`:6-1079`) except one 3-line
  block appended after the layer closes (`.toast-container { z-index: 1090;
  }`, `:1081-1084`) — that rule is global (`.toast-container`, no `#welcome`
  scope) and arguably belongs in a shared bundle (`components.css` or
  `layout.css`), not this page's file, since toasts render on every page.
  **[NEW]**.
- Defines its own complete `--wl-*` token system (~35 custom properties,
  `:10-83`) with a full dark-mode remap (`:86-104`) and reduced-motion remap
  (`:107-113`) — internally this file is a clean, self-contained token-swap
  example (every color/spacing/radius/duration referenced through a `--wl-`
  variable, confirmed no bare hex outside the `:root`/dark-mode blocks
  **except** ~15 deliberate `!important`-pinned white-on-gradient overrides
  for `.btn-hero-primary`/`.bento-featured` where the design wants a fixed
  white foreground regardless of theme, `:217-249, 408-522` — these are
  intentional, not token gaps).
- All selectors are `#welcome`-scoped, matching the single-page-owner
  convention; no dead-selector risk found (didn't cross-check every class
  against `templates/welcome.html` line-by-line, but the ID-scoping makes
  accidental cross-page leakage structurally impossible).
- 4 keyframes (`pulse-glow`, `float`, `shimmer`, `heartbeat`), all
  hover/decorative, no `prefers-reduced-motion` guard on the container-level
  animations themselves (only a duration-zeroing `:root` override at
  `:107-113` which doesn't stop `animation-iteration-count: infinite`
  keyframes already running — reduces their speed to instant-loop rather
  than truly stopping, a minor a11y gap, not scoped to fix here).
- No `!important` outside the deliberate white-text overrides noted above.
  Breakpoints: 1024px, 768px, 480px (three), plus `prefers-contrast: high`
  and `print`.

### `pages-volume-splitter.css` (1059 lines)
- **Confirmed dead CSS, verified against the template**: `.volume-controls-column`,
  `.volume-main-column`, `.volume-side-column` (`:114-135`, an early
  "Left Column / Center Column / Right Column" 3-column layout, plus their
  responsive grid-column rules at `:158-185` and dark-mode block at
  `:206-217`) have **zero matches** in `templates/` (grepped
  `volume-controls-column|volume-main-column|volume-side-column` across
  `templates/**` — no results). The file was later rewritten around a
  different grid system (`.volume-dashboard`, `.volume-toolbar`,
  `.volume-workspace`, `.volume-insights-panel`, the "Wide Dashboard Layout"
  section starting `:638`) but the old column rules were never deleted.
  **[NEW] — dead code, ~35 lines including its dark-mode block, cheap
  deletion candidate for WP4.2 or WP4.3.**
- **Literal duplicate selector with contradictory values, not resolved by
  cascade intent**: `.volume-splitter-container` is defined twice —
  `:12-16` (`max-width: 100%; margin: 0; padding: 1.5rem;`) and again at
  `:661-666` (`width: 100%; max-width: min(1840px, 100%); margin: 0 auto;
  padding: clamp(...)`). The second wins by source order, making the first
  entirely dead. Same pattern for `.volume-history-section`: `:153-155`
  (`margin-top: auto`) vs. `:380-384` (`background-color: #f8f9fa; padding:
  1.5rem; border-radius: 8px`) vs. its own dark variant `:386-388` — these
  don't fully overlap in properties so both partially survive, but it's the
  same "old layout comment block never removed after a redesign" pattern.
  **[NEW]**.
- Two unrelated `:root` token blocks (`:1-9` `--volume-track-*`, and
  `:641-659` `--volume-panel-*`/`--volume-row-*`/`--volume-muted-text`) —
  not a bug (different names, no collision) but reinforces the Q1 finding
  that this file has its own local token vocabulary rather than consuming
  `tokens.css`.
- Heavy `!important` density in the older, pre-"Wide Dashboard" dark-mode
  block (`:431-470`, the `.results-section` dark overrides — 9 rules, every
  declaration `!important`) vs. zero `!important` in the newer Wide
  Dashboard dark-mode block (`:878-895`) — same evidence of two authorship
  eras in one file, older one more defensive/collision-prone.
- `.volume-indicator`/`.volume-badge`/`.volume-classification`/
  `.volume-legend`/`.low-volume`/`.medium-volume`/`.high-volume`/
  `.ultra-volume` (`:965-1016`) are explicitly commented as **shared**:
  *"Summary pages and the volume splitter can both depend on this file
  without redefining the indicator colors or badge chrome locally."*
  **[RISK]** — this directly contradicts `.claude/rules/frontend.md`'s route
  bundle model ("Route bundles… loaded from child templates" — one bundle
  per page) and `docs/CSS_OWNERSHIP_MAP.md`'s "Keep route-specific CSS
  inside the route bundle" rule: if `weekly_summary.html`/
  `session_summary.html` actually consume `.volume-indicator`/`.volume-badge`
  from `pages-volume-splitter.css`, those pages have an undeclared
  cross-bundle CSS dependency not reflected in `CSS_OWNERSHIP_MAP.md`'s
  per-template table (which lists only `pages-weekly-summary.css`/
  `pages-session-summary.css` for those routes). Not verified this phase
  whether summary templates actually load `pages-volume-splitter.css` or
  whether `pages-weekly-summary.css`/`pages-session-summary.css` duplicate
  these same classes locally instead — worth a follow-up grep in whichever
  phase reads those two bundles, and a direct WP4.3 candidate either way
  (move to `components.css` if genuinely shared).
- Breakpoints: 1400px, 1200px (×2, one early grid-based, one later Wide
  Dashboard `max-width: 1199.98px`), 768px (×2), matching the two-era
  pattern above.

### `a11y.css` (813 lines)
- Scope creep beyond "accessibility": alongside the genuine a11y content
  (UI-scale custom properties + 8 `html[data-scale]` levels `:9-121`, the
  Firefox zoom-disable fallback `:90-121`, the "FINAL override… loaded last"
  focus-visible reset `:433-597`), the file also contains the **entire
  navbar-adjacent Scale Control + Accessibility Menu Dropdown component
  CSS** (`:123-417`, `.scale-control`, `.scale-btn-group`, `.accessibility-
  dropdown`, `.accessibility-menu`, etc. — these are navbar UI components,
  arguably `navbar.css` territory, not accessibility rules per se) plus a
  grab-bag of **unrelated global UI states** that have nothing to do with
  accessibility: `.is-invalid`/`.is-invalid:focus` (`:599-607`),
  `.global-loading-indicator` (`:609-636`, confirmed used —
  `templates/error.html` and others per general app patterns),
  `#liveToast.bg-warning`/`#liveToast.bg-info` toast color overrides
  (`:638-656`), `#error-message-container` + its `slideInUp` keyframe
  (`:658-681`), `.form-control.is-valid` (`:684-692`), the entire
  `.error-page-container`/`.error-page-content` family (`:695-746`,
  confirmed used only by `templates/error.html`), and
  `.form-select.is-invalid-required`/`.wpdd.is-invalid-required` required-
  field validation styling with its own `shake-invalid` keyframe
  (`:753-797`). **[NEW]** — none of this is accessibility-specific; it reads
  like "global miscellaneous CSS with nowhere better to go" was dumped into
  the a11y bundle because it's one of the 8 always-loaded global files.
  Legitimate WP4.2-final / WP4.3 candidate: split into `a11y.css` (scale
  system + focus-visible reset only) and move the rest into `components.css`
  where `docs/CSS_OWNERSHIP_MAP.md` already claims ownership of "toasts" and
  generic form states.
- The file's own comment at `:433-436` calls itself *"the FINAL override
  loaded last in the CSS chain"* for focus-visible reset — confirmed true
  per the `<head>` order (`a11y.css` is the last of the 5 pre-page-css global
  bundles, `base.html:22`), but note `tokens.css`/`motion.css`/
  `theme-dark.css` load **after** `a11y.css` (see Load-Order finding below),
  so any of those three files' selectors touching `:focus`/`:focus-visible`
  with equal-or-greater specificity would in fact load later and could
  override this "final" reset — not found in this phase's read of those
  three files (none define `:focus` rules), but the comment's claim is only
  true today by coincidence of what those files happen not to contain, not
  by structural guarantee.
- No breakpoints beyond `max-width: 991.98px`/`768px`/`print`; `!important`
  density is very high in the focus-reset section (~130 lines, nearly every
  declaration `!important`) — intentional per the section's own stated
  purpose (overriding Bootstrap's default focus ring), not a smell.

### `pages-backup.css` (497 lines)
- **Zero `[data-theme='dark']` rules in the entire file** — confirmed by a
  full read, no dark-mode selector exists anywhere. Every color is a
  hardcoded light-mode hex/rgba or one of six local `--backup-*` custom
  properties defined once at `.backup-center-page` (`:2-7`) with **no dark
  variant declared for them either**. This means the Backup Center page's
  dark-mode appearance today depends entirely on generic ancestor rules from
  `theme-dark.css` (`.card`, body background, table rules) plus whatever
  Bootstrap dark defaults apply — the page-specific teal/warm accent palette
  (`--backup-accent: #176b87`, `--backup-warm: #f3ede1`, etc.) and all the
  glass/gradient panel backgrounds (`:8-11`, `:245-268`, `:353-396`) stay
  **light-mode-colored even when `data-theme="dark"` is active**, unless
  Playwright's visual baselines happen to not cover backup-page dark mode
  (not verified this phase). **[RISK]** — this is either a real,
  undocumented dark-mode visual bug, or evidence the Backup Center page
  simply hasn't been dark-mode-styled yet and looks light-themed regardless
  of toggle state. Either way it directly informs WP4.2's execution order:
  the plan lists `pages-backup.css` **first** ("smallest → largest risk")
  precisely because it's simplest, but "simplest" here specifically means
  **"has no existing dark-mode rules to reconcile"** — WP4.2's first PR will
  be *adding* dark-mode token-swap coverage from scratch for this page, not
  migrating existing hardcoded pairs to tokens. **[CONFIRMS-PLAN]** on
  sequencing (correctly the least entangled file) but **[NEW]** on what
  "smallest risk" concretely means for this specific file.
- Otherwise clean: token-driven internally (all six `--backup-*` vars
  referenced consistently, zero stray hardcoded duplicates of the accent
  color found), well-organized single-purpose selectors, two breakpoints
  (1200px, 768px), zero `!important`.

### `tokens.css`, `pages-progression.css`, `pages-body-composition.css`,
`base.css`, `motion.css` — see Q1/Q2 above for tokens.css and theme-dark.css
interaction; additional page-bundle-specific notes:

- **`pages-progression.css` (341 lines) — confirmed cross-page dead CSS**:
  the "Hierarchical Dropdown Styles" / "Uniform Dropdown Styles" section
  (`:212-286`, `.routine-dropdown`, `.exercise-dropdown`, `.filter-dropdown`,
  `.uniform-dropdown`, plus `.col-lg-3.col-md-4.col-sm-6`, `.form-label`,
  `#filters-form .col-lg-3` etc.) targets classes that **do not appear in
  `templates/progression_plan.html`** — grepped `routine-dropdown|exercise-
  dropdown|filter-dropdown|uniform-dropdown` across `templates/**`; the only
  hit is `templates/workout_plan.html`. Cross-checked
  `static/css/pages-workout-plan.css`, which **already fully owns and
  styles** all four classes — light mode, dark mode
  (`[data-theme='dark']`), hover/focus, and six responsive breakpoints
  scoped under `#workout[data-page="workout-plan"]` (confirmed via grep,
  60+ matching lines). The `pages-progression.css` copies are plain-hex,
  have no dark-mode variant, and are loaded on a page (`/progression`) whose
  template contains none of these elements. **[NEW] — ~75 lines of dead,
  wrong-page CSS**, a direct WP4.3 (or Phase-0-adjacent) deletion candidate,
  and a concrete illustration of the "route bundle contains rules for
  another route" violation `docs/CSS_OWNERSHIP_MAP.md` rule 3 exists to
  prevent.
- The rest of `pages-progression.css` splits cleanly into two authorship
  eras like the volume-splitter file: older hardcoded-hex rules (flatpickr
  dark-mode overrides `:145-204`, all hardcoded hex with no token
  references — acceptable since flatpickr is a third-party widget with its
  own class names, but zero `--*` token reuse even where a shared color like
  `#0d6efd`/`#dc3545` already has a token equivalent in `pages-workout-plan.css`'s
  or `tokens.css`'s vocabulary) vs. newer Calm-Glass-token-driven rules
  (`.suggestion-card`, `.current-goals .goal-status-badge`,
  `.progression-fatigue*`, `:29-87, 288-341` — consistently reference
  `var(--ink-2, ...)`, `var(--accent, ...)`, `var(--success, ...)` with
  fallback values, correctly following the intended token-swap pattern).
  **[CONFIRMS-PLAN]** that newer feature work already uses tokens correctly;
  the debt is concentrated in older, page-specific sections.
- **`pages-body-composition.css` (324 lines)**: the cleanest file in this
  phase. Single local token block (`--bc-*`, `:2-11`) with one dark-mode
  override block at the very end (`:294-324`) that touches only what
  actually needs to differ (accent-soft, border, shadow, five specific text
  colors, two gradient backgrounds, one tick-mark color) rather than
  re-declaring everything — the smallest, most surgical dark-mode diff of
  any page bundle read this phase. Zero `!important`, zero dead selectors
  found (all `.bc-*`/`.body-composition-*` classes are single-purpose and
  page-scoped by naming convention even without an ID wrapper). One
  breakpoint (1100px). **[CONFIRMS-PLAN]** as a template for what WP4.2's
  per-page output should look like for every other page.
- **`base.css` / `motion.css` — confirmed duplicate, one side dead**: both
  files define a `.skeleton` class. `base.css:92-102` sets `background`
  (hardcoded `#f0f0f0`/`#e0e0e0` gradient), `background-size`, and
  `animation: skeleton-loading 1.5s infinite` (keyframe at `:104-111`).
  `motion.css:35-47` sets the **same three properties** (`background` via
  `var(--surface-1)`/`var(--surface-2)` tokens, `background-size`,
  `animation: skeleton-shimmer 1.5s infinite linear`) plus two more
  (`border-radius`, `color`/`border-color: transparent !important`), and
  adds a `[data-theme="dark"] .skeleton` override (`:49-57`) that `base.css`
  has no equivalent for. Per the `<head>` load order (`base.css` at
  position 1, `motion.css` after the `page_css` block, position ~9 —
  confirmed in Load-Order finding below), `motion.css`'s declarations win
  for every property both files set, at equal specificity (single class
  selector, no ID/attribute qualifiers on either side). **`base.css`'s
  `.skeleton` block and its `@keyframes skeleton-loading` are 100% dead**
  (never visibly applied; `motion.css`'s `skeleton-shimmer` animation always
  wins). Confirmed the class itself is live (`templates/weekly_summary.html`,
  `static/js/modules/muscle-selector.js` both apply `.skeleton`), so this is
  shadowed-duplicate dead code, not an orphaned selector. **[NEW]**.
- **`base.css` — separately dead, unreferenced classes**: `.loading-spinner`
  (`:82-90`) and `.fade-enter`/`.fade-enter-active` (`:114-123`, plus their
  backing `@keyframes fadeIn` at `:70-79`) have **zero matches** in any
  `.html` or `.js` file repo-wide (grepped `loading-spinner|fade-enter`
  across `*.{html,js}` — no results; the only other hits at all were in
  `pages-workout-plan.css` itself, i.e. more unused CSS referencing the same
  dead names, not an HTML/JS consumer). **[NEW] — confirmed dead, ~35 lines
  combined, safe deletion candidate** (global bundle, so technically
  WP4.2-final/WP4.3 territory rather than a single page's WP).
- `base.css`'s Bootstrap utility overrides (`.text-center`, `.text-muted`,
  `.text-danger`, `:56-67`) duplicate Bootstrap's own utility classes with
  identical or near-identical values (`#6c757d`/`#dc3545` are Bootstrap's
  stock muted/danger grays) — harmless (same computed result either way) but
  pure redundancy against the compiled `bootstrap.custom.min.css`, a small
  WP4.3 dedupe candidate.

### `navbar.css` (1536 lines) — three overlapping redesign generations
- **Generation 1** (`:6-883`, inside `@layer navbar`): a complete,
  well-structured, `--nav-*`-token-driven navbar (colors, glass effect,
  spacing, radius, shadow, typography, transitions all tokenized at
  `:10-61`, full dark-mode remap `:64-76`, reduced-motion remap `:79-84`).
  Internally clean — this alone would be a good WP4.2-final template.
- **Generation 2** ("Legacy Support" + "Override layer", `:885-1021`,
  explicitly outside the `@layer` so it wins on cascade regardless of layer
  order): re-implements navbar background/height/color with **raw hardcoded
  hex** (`rgba(255, 255, 255, 0.75)`, `#4a4a5a`, `#1a1a2e`, `#e9eef7`, etc.)
  and blanket `!important` on nearly every declaration (`:912-1021`, ~30
  rules, all `!important`), duplicating what Generation 1's `--nav-bg`/
  `--nav-text` tokens already express. The file's own comments (`:887-889`,
  `:907-911`) acknowledge this is deliberate defensive layering — "Legacy
  Support… maintained for backward compatibility" and "MUST be outside
  `@layer` for highest specificity" — i.e., **Generation 1's token-driven
  rules are known by the author to be insufficiently specific/reliable on
  their own**, so Generation 2 exists purely to force-win the cascade.
- **Generation 3** ("Calm Glass 2026 navbar overlay", `:1023-1536`, roughly
  half the file): a *third* pass, using `:where()` (zero specificity, relies
  on `!important` where it needs to beat Generation 2, e.g. `:1196, 1202-
  1204, 1219, 1225`) and yet another token layer (`--nav-glass-surface`,
  `--nav-pill-*` — 10 more custom properties, `:1026-1048`, referencing the
  *shared* Calm Glass tokens `--surface-*`/`--accent`/`--r-pill` this time,
  correctly). This generation restyles nav-links as pills, adds dropdown
  support, per-icon accent colors for `#nav-user-profile`/
  `#nav-body-composition`/`#nav-backup` (`:1377-1445`, with hover pop
  animations and a dedicated `@keyframes nav-fa-icon-pop`), and its own
  responsive breakpoint set (992px, 1360px, 1500px — **overlapping but not
  identical to** Generation 1's breakpoints at 576px/768px/991px, `:806-840`).
- **[RISK]** — three generations of the same component, none deleted,
  layered by cascade trickery (`@layer` + `!important` + `:where()`) rather
  than one being replaced by the next. This is the single largest
  "dark-mode-hand-duplicated" + "hardcoded-vs-token" case in the whole CSS
  surface: Generation 1's token system, Generation 2's raw hex + blanket
  `!important`, and Generation 3's newer token system all currently
  co-exist and are all live (confirmed no generation is fully shadowed —
  each wins for a different property subset depending on selector/`!important`
  combination). WP4.2-final's navbar.css work cannot be a simple "replace
  hardcoded pairs with token-consuming rules" pass per the plan's generic
  phrasing — it requires first determining which generation is the
  source of truth for each visual property and deleting the other two,
  which is materially riskier and larger than the plan's per-page treatment
  implies for the other bundles. **[CONTRADICTS-PLAN]** on effort sizing:
  navbar.css (a "shared bundle" in WP4.2-final, done in one pass alongside
  `components.css`/`layout.css`/`a11y.css`/`base.css`/`motion.css`/
  `theme-dark.css`) is likely the single hardest file in that whole WP,
  not comparable in effort to e.g. `base.css`'s two small dead-code deletions
  documented above.
- `!important` count is very high across Generations 2 and 3 combined
  (~70+ occurrences in a 1536-line file) vs. zero in Generation 1 — a stark
  internal contrast confirming the "later generations had to fight the
  earlier ones" narrative above.

## Stylesheet load order (`templates/base.html:10-29`)

Confirmed exact `<head>` order:
1. Google Fonts preconnect + Inter font `<link>`
2. `bootstrap.custom.min.css` (with a CDN `onerror` fallback to Bootstrap 5.1.3)
3. Font Awesome 5.15.4 (CDN)
4. `base.css`
5. `layout.css`
6. `components.css`
7. `navbar.css`
8. `a11y.css`
9. `{% block page_css %}` (the one route bundle each child template injects)
10. `tokens.css`
11. `motion.css`
12. `theme-dark.css`

**[RISK] — load-order finding not previously documented**: `tokens.css`,
`motion.css`, and `theme-dark.css` all load **after** every page-specific
bundle, not before. This doesn't affect `var()` *resolution* (custom
properties resolve at computed-value time regardless of declaration order),
but it does mean these three files win same-specificity cascade ties against
every global bundle (`base.css` through `a11y.css`) **and** every page
bundle. This is exactly the mechanism behind the confirmed `base.css`/
`motion.css` `.skeleton` shadowing above, and it means WP4.2-final's plan to
treat `theme-dark.css` retirement as a same-tier task alongside
`components.css`/`navbar.css`/`a11y.css`/`base.css`/`motion.css` needs to
account for the fact that `theme-dark.css` structurally loads last among
globals and after every page bundle too — any page-bundle dark-mode rule
added during WP4.2's page-by-page passes (WP4.2, before WP4.2-final) is at
risk of being silently overridden by a not-yet-cleaned `theme-dark.css` rule
of equal specificity, unless WP4.2's page-by-page PRs also delete the
corresponding `theme-dark.css` block for that page as they go (the plan's
phrasing — "delete the now-dead duplicated dark blocks (from both the page
bundle and `theme-dark.css`)" — already anticipates this, but it's worth
flagging as confirmed-necessary rather than optional, given the load order).

---

## Cross-cutting seeds

1. **`bootstrap.custom.min.css` silently carries two feature-CSS families**
   (`.fatigue-*` from `_fatigue.scss`, `.vp-*`/`.volume-active-summary` from
   `_workout_plan_volume_panel.scss`) that are invisible to anyone scanning
   `static/css/*.css` for size/duplication, since the plan's own frontend
   rule excludes this file from the 18-bundle cap and both
   `.claude/rules/frontend.md` and `docs/CSS_OWNERSHIP_MAP.md` describe it
   only as "Bootstrap build artifact." Any WP4 dedupe/grep pass across
   `static/css/` must also grep the *compiled* `bootstrap.custom.min.css` (or
   the two SCSS source files) to avoid missing real duplication — e.g., the
   `.volume-*` naming collision with `pages-volume-splitter.css` (different
   files, different features, confusingly similar names) is exactly the kind
   of thing a `static/css/`-only grep would misreport.

2. **`navbar.css` has three overlapping, all-still-live redesign generations**
   (token-driven `@layer` block → hardcoded `!important` "legacy/override"
   block → a second, newer token-driven `:where()` "Calm Glass" block), not
   one clean file with scattered hardcoded pairs. WP4.2-final's navbar.css
   work is qualitatively harder than the plan's generic "replace hardcoded
   pairs with token-consuming rules" phrasing suggests — it requires
   determining per-property which generation actually wins today (verified:
   all three currently contribute to the rendered result) before anything
   can be safely deleted. Recommend giving navbar.css its own scoped
   sub-task or extra time budget within WP4.2-final rather than treating it
   as equal-weight to `base.css`/`motion.css` in the same PR.

3. **`theme-dark.css` is not a single coherent block** — it's a legacy
   hardcoded-hex + `!important` layer (including a workout-plan-input-specific
   pastel-color duplication block that exists solely because its light-mode
   counterpart lives in a different file), plus a newer, cleaner
   variable-remap layer appended at the end that only *partially* supersedes
   the legacy layer (only for consumers that go through the remapped
   `--bg-primary`-style names; direct hardcoded-hex rules in the legacy layer
   are untouched by it). WP4.2-final's "delete or reduce to the token-swap
   block" goal is achievable but requires per-rule triage, not a bulk
   deletion of everything above the existing Calm Glass block.

4. **Confirmed, verified-against-templates dead CSS ready for cheap deletion**
   (no design judgment needed, just grep-and-delete): `pages-volume-splitter.css`'s
   `.volume-controls-column`/`.volume-main-column`/`.volume-side-column`
   (~35 lines incl. dark-mode block); `pages-progression.css`'s entire
   "Hierarchical/Uniform Dropdown Styles" section targeting
   `workout_plan.html`-only classes (~75 lines, zero dark-mode coverage to
   lose); `base.css`'s `.loading-spinner`/`.fade-enter*`/`fadeIn` keyframe
   (~35 lines, zero repo-wide HTML/JS references) and its fully-shadowed
   `.skeleton`/`skeleton-loading` block (~20 lines, superseded by
   `motion.css`). None of these four require the WP4.0 visual-gate baseline
   to move, since none render visibly different before/after removal — good
   candidates for a fast, low-risk WP4.1-adjacent or Phase-0-style cleanup
   PR ahead of the heavier per-page token work.

5. **Every page/component invented its own local token namespace instead of
   consuming `tokens.css`'s shared Calm Glass vocabulary** (`--wl-*` in
   welcome, `--nav-*` in navbar, `--bc-*` in body-composition, `--backup-*`
   in backup, `--volume-*`/`--volume-panel-*` in volume-splitter, `--fatigue-*`
   in the SCSS-compiled fatigue components — six parallel systems, none
   referencing `--surface-*`/`--ink-*`/`--accent`/`--success/warning/danger`).
   WP4.1's "expand tokens.css… define missing tokens" is scoped by the plan
   as a hardcoded-literal inventory, but the bigger duplication lives one
   level up, in these already-tokenized-but-parallel namespaces. Recommend
   WP4.1 explicitly catalogs these six namespaces (not just raw hex counts)
   so later per-page WPs know whether to collapse a page's local tokens into
   the shared set or leave them (e.g., `pages-body-composition.css`'s
   5-color body-fat-band scale is legitimately page-specific and probably
   shouldn't become a global token).

6. **`pages-backup.css` has zero dark-mode rules today** — not a duplication
   problem but a coverage gap: the page's teal/warm accent palette and glass
   panels are not confirmed to re-theme under `data-theme="dark"` at all.
   Since the plan sequences this file first in WP4.2 ("smallest → largest
   risk"), the executor should go in expecting to **add** dark-mode
   token-swap rules from scratch, not migrate existing hardcoded pairs — a
   different (arguably easier, since there's nothing conflicting to remove)
   task than every other page in the WP4.2 sequence.
