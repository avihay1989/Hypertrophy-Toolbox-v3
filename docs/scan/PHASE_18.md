# Phase 18 — CSS part 1

Line-by-line read of `static/css/pages-workout-plan.css` (8226 lines) and
`static/css/components.css` (4511 lines), both in full. Read for context:
`.claude/rules/frontend.md` and `static/css/tokens.css` (433 lines — the
custom-property vocabulary). Cross-checked against `docs/REFACTOR_PLAN.md`
Phase 4 (WP4.1 tokenization audit, WP4.2 dark-mode unification —
`pages-workout-plan.css` is explicitly called out as LAST/highest-risk,
WP4.3 cross-bundle dedupe into `components.css`).

Method for counts below: `grep -oE` pattern counts (`#[0-9a-fA-F]{3,8}` for
hex, `rgba?\(` for rgb/rgba functions, `var\(--[a-zA-Z0-9-]+` for token
consumption, literal `!important`, `data-theme=.dark.` for dark-mode
selector occurrences, `@media` for breakpoint blocks). These are token-level
occurrence counts, not distinct-declaration counts, so they overstate
slightly wherever a single rule uses multiple `rgba()` values in one
`box-shadow` (very common in this codebase's "glass" style) — treat as
"order of magnitude", not exact.

---

## static/css/tokens.css (433 lines) — read for context

- Two unrelated token systems live in one file, un-flagged as such in the
  code itself:
  1. **Lines 1–371**: a "Responsive Scaling System" — `--space-*`,
     `--input-*`, `--btn-*`, `--frame-*`, `--table-*`, `--font-size-*`,
     re-defined per breakpoint across 7 `@media` blocks (720p, 1366, 1536,
     1600, 1920, 2560, 4K+). This is the *source* vocabulary that the
     hand-rolled per-breakpoint duplication in both audited files should have
     consumed but mostly didn't (see "Tokenization audit" below).
  2. **Lines 374–433**: "Calm Glass 2026 redesign tokens" — `--surface-*`,
     `--ink-*`, `--accent`, `--success/warning/danger`, `--shadow-neu-*`,
     `--shadow-elev-*`, `--calm-glass-*`, `--r-*` (radius scale), `--s-*`
     (spacing scale, **overlapping in purpose with `--space-*` from system
     1 but a different numeric scale and naming convention** — `--s-3: 12px`
     vs `--space-md: 0.75rem` are the same 12px value expressed two ways),
     `--ease-out`/`--dur-*`, `--font-sans`. Dark-mode swap block at
     `[data-theme="dark"]` (422–433) only overrides `--surface-*`, `--ink-*`,
     `--shadow-neu-*`, `--calm-glass-*` — the *first* token system's
     `--space/--input/--btn/--frame/--table/--font-size` tokens have **no
     dark-mode variants at all** (they're purely responsive, not
     theme-aware, which is correct for their purpose, but confirms dark mode
     is carried entirely by the second, newer token system plus by
     un-tokenized hardcoded colors in the two audited files).
- **[CONFIRMS-PLAN]** WP4.1's "expand tokens.css; inventory hardcoded
  colors/spacing/radii" premise is correct — there are two live, healthy
  token systems here, but neither is close to fully adopted downstream (see
  per-file adoption counts below).
- **[NEW]** The `--space-md: 0.75rem` (system 1) vs `--s-3: 12px` (system 2)
  overlap is a real merge hazard for WP4.1: a naive "replace hardcoded
  0.75rem with a token" pass could pick either token depending on which
  file/section it's touching, silently creating two parallel spacing
  vocabularies that drift over time. WP4.1 should pick one spacing scale as
  canonical (system 2's `--s-*` is newer / used by the "calm glass" overlay
  that both audited files are trending toward) and document the other as
  legacy/responsive-only.

---

## static/css/components.css (4511 lines)

### Structure / section map
| Lines | Section |
|---|---|
| 1–299 | Button base + glass variants (`.btn-success/.btn-primary/.btn-outline-secondary`, per-ID export/utility buttons: `#clear-filters-btn`, `#load-program-btn`, `#clear-plan-btn`, `#add_exercise_btn`, `#export-to-log-btn`, `#export-to-excel-btn`), loading spinner, focus-state resets (2 near-duplicate global focus-reset blocks, 141–189 and 454–517) |
| 300–1202 | Form controls: `.form-container/.form-label/.form-select/.form-control`, `.filter-dropdown`/`.uniform-dropdown`/`.exercise-dropdown`, validation states, `.input-fields-group` (defined twice, 300–318 minimal + 738–884 full with color-coded RPE/RIR/weight/sets backgrounds), value-changed pulse animation, then a full 7-tier responsive re-statement of form sizing (1039–1202) |
| 1204–1466 | glass effect first, then two more, later, conflicting `.table` base blocks (1204–1264 glass/gradient version, 1471–1546 flat `background-color:#fff` version — see "duplicate selectors" below), `.table-workout`, dark-mode table rules (`[data-theme='dark'] .workout-plan.table-container`, `.table`, `.table-striped`), row selection/hover/sort-indicator styles |
| 1560–2159 | `.workout-log-frame` dark-mode block (large, ~150 lines, all `!important`), `.editable`/`.editable input` (defined twice — see below), drag-and-drop (`.drag-handle`, `tr.sortable-ghost/-drag`), exercise-swap feature (`.exercise-cell`, `.exercise-image-preview`, `.btn-swap`) |
| 2160–2317 | 7-tier responsive re-statement of table sizing |
| 2318–2999 | `.card`, disabled CSS-tooltip system (2352–2372, dead code kept as a comment block — see "dead code" note), `.modal`/`.modal-content`/`.modal-header/-footer`, `#insightsModal`, `#aiAssistantModal`, `#generatePlanModal` (badges, volume-temp range slider gradient), `.toast` + 6 color variants ×2 (light+dark, fully hand-duplicated), `.alert` + 4 color variants |
| 3000–3122 | Alert animation, toast positioning/close button |
| 3123–4446 | "Calm Glass 2026 component overlays" — `.btn-calm-primary/-ghost/-icon/-danger`, `.glass-neumorph-card`, `.input-calm-inset`, `.table-calm` (all scoped via `:is()`/`:where()` to `#workout[data-page="workout-plan"]`, `.workout-log-page`, `.summary-frame.frame-calm-glass`, `.progression-plan-container` — i.e. this "shared" bundle contains page-specific rules gated by page selectors, not just page-agnostic component classes), then a **second, page-scoped `@layer workout { … }` block** (3539–4104) duplicating/overriding much of the calm-glass system specifically for `#workout[data-page="workout-plan"]` |
| 4106–4446 | Dark-mode variants for summary/progression/volume-splitter/welcome pages' calm-glass surfaces, global `body`/`h1-h3` color rules, workout-log modal header/footer overrides |
| 4447–4511 | §5 exercise reference video modal + play button (`.btn-video`, `.exercise-video-embed-wrap`) |

### Hardcoded color vs token usage
- Hex colors: **560** occurrences. `rgba()/rgb()`: **511** occurrences (mostly
  inside multi-stop `linear-gradient()`/`box-shadow` glass effects). `var(--...)`
  consumption: **503** occurrences.
- Roughly 68% of color-ish tokens in this file are still hardcoded
  (560+511=1071 hardcoded vs 503 var() — and a meaningful fraction of the 503
  are non-color tokens like `--wpdd-gap`, `--s-2`, `--dur-fast`). The
  "calm glass" overlay section (3123–4446) is the best-tokenized part of the
  file (heavy `var(--accent)`, `var(--surface-*)`, `var(--ink-*)` use via
  `color-mix()`), while the older glass-button/table/modal/toast sections
  (1–3122) are almost entirely hardcoded hex/rgba, including duplicate
  literal colors for the same semantic buttons this file's own newer section
  already tokenized (e.g. `#4f8cff`/`rgba(79,140,255,…)` "workout accent
  blue" appears as a raw literal well over 40 times across both old and new
  sections instead of consuming `--accent`/`--wp-accent`).
- **[CONFIRMS-PLAN]** WP4.1's "inventory hardcoded colors" framing undersells
  the job here: this isn't just "add missing tokens", it's "the same
  literal color already has a token *in this very file* and the older 70%
  of the file doesn't use it."

### Dark-mode strategy
- `[data-theme='dark']` selector occurrences: **175**.
- No scattered single-property overrides here — dark-mode blocks are
  full rule duplicates (same property list as the light rule, restated with
  dark literals), e.g. `.table`/`.table thead th`/`.table tbody td`
  (1471–1546) each get a same-shaped `[data-theme='dark']` twin immediately
  below; the "calm glass" overlay section instead uses `color-mix()` against
  theme-aware custom properties (`--surface-2`, `--ink-1`) so its dark
  variants are often just re-pointing the same `color-mix()` formula at
  dark-mode token values — a meaningfully cheaper pattern than the older
  hand-duplicated blocks.
- **[RISK]** Two dark-mode *strategies* coexist in one file: (a) legacy
  full-rule-duplicate (~1–3122, ~120 of the 175 dark selectors) and (b)
  token-driven `color-mix()` (~3123–4446, ~55 of the 175). WP4.2-final's
  "collapse dark blocks into token-consuming rules" is a rewrite, not a
  search-and-replace, for the legacy ~70%.

### Duplicate / near-duplicate selectors within the file
- **`.table` base rules defined twice with different visual models**:
  1204–1264 (glass/gradient, `border-radius:12px`, `overflow:hidden`,
  `transform:translateZ(0)` GPU-layer hack) vs 1471–1546 (flat
  `background-color:#fff`, `box-shadow:0 2px 4px rgba(0,0,0,0.1)`,
  `border-radius:8px`). Both are live (not commented out); the second wins
  on source order for any property they both set, but they disagree on
  `border-radius` (12px vs 8px) and shadow model — genuinely conflicting,
  not merely redundant.
- **`.input-fields-group` defined twice**: 300–307 (minimal flex row) and
  738–884 (full spec with color-coded backgrounds) — the second's
  `flex-wrap: wrap` directly contradicts a workout-plan-page override
  elsewhere that forces `flex-wrap: nowrap` (see cross-file section below).
- **`.editable`/`.editable input`/`::selection` block appears twice**
  (1776–1859 and 1903–1947) with near-identical but not byte-identical
  rules (e.g. `.editable:hover` background-color literal repeated
  verbatim in both blocks — pure copy-paste, no semantic difference found).
- **Global focus-reset block duplicated**: 141–189 (button-scoped) and
  454–517 (page-wide `*:focus`) overlap in intent (kill mouse-click focus
  ring, keep `:focus-visible` ring) with different selector lists — a
  merge candidate for WP4.1/WP4.3.
- **7-tier responsive breakpoint block repeated 3 times verbatim in
  structure** (not content) for buttons (325–448), forms (1044–1202), and
  tables (2165–2316) — same seven `@media` conditions
  (`max-width:1280px`, `1281–1366px`, `1367–1536px`, `1537–1600px`,
  `1601–1920px`, `1921–2560px`, `min-width:2561px`) reused as a structural
  template with different property values inside each. This exact
  7-breakpoint list matches `tokens.css`'s responsive scaling system
  media queries — strong evidence the intent was "consume the responsive
  tokens", but most of the blocks hardcode fresh literal `px`/`rem` values
  instead of referencing `var(--input-height-sm)` etc.

### Rules that plausibly belong in the other bundle (cross-bundle overlap)
- **79 class-name tokens are shared between `components.css` and
  `pages-workout-plan.css`** (grep-diff of `\.[a-zA-Z][a-zA-Z0-9_-]*` token
  sets). Notable overlaps where *both* files define real declarations for
  the same class (not just one file referencing a Bootstrap utility):
  `.frame-header`, `.frame-title`, `.filters-title`, `.collapse-toggle`,
  `.frame-header-2025` (+ `-left`/`-right`), `.collapsible-frame` (implied
  via shared child selectors), `.summary-frame`, `.summary-section`,
  `.summary-tables`, `.summary-header`, `.workout-log-frame`,
  `.table-container`, `.selection-actions`, `.muscle-selector-container`
  (+ `-content`/`-controls`/`-wrapper`), `.cascade-dropdown`,
  `.routine-tab-btn`, `.wpdd`/`.wpdd-button`/`.wpdd-filter`/`.wpdd-routine`/
  `.wpdd-exercise`, `.filter-dropdown`, `.exercise-dropdown`,
  `.uniform-dropdown`, `.value-changed`, `.input-calm-inset`,
  `.input-fields-group`, `.input-group`.
- **[RISK] — contradicts a premise of WP4.3's framing ("dedupe rules
  duplicated across ≥2 *page* bundles").** The overlap here isn't between
  two page bundles — it's between the *shared* bundle (`components.css`)
  and one *specific* page bundle (`pages-workout-plan.css`), and a good
  chunk of `components.css`'s own "Calm Glass" section (3123–4446) is
  already explicitly page-scoped (`#workout[data-page="workout-plan"]`,
  `.progression-plan-container`, `.summary-frame.frame-calm-glass`,
  `.volume-splitter-container`) rather than truly global. WP4.3 should
  budget time to first ask "does this rule in components.css actually
  apply everywhere, or is it silently page-scoped already?" before doing
  cross-bundle moves — some of what looks like "shared" content is really
  workout-plan/summary/progression/volume-splitter-specific CSS that ended
  up in the wrong file already, in the *other* direction from what WP4.3
  assumes (page-specific-in-shared-bundle, not shared-content-duplicated-
  across-pages).

### Dead-looking selectors (spot-check ~10 against templates/JS)
Not the primary dead-code hunting ground (that content is concentrated in
`pages-workout-plan.css`, see below), but noted: the disabled CSS-tooltip
system (2349–2372) is already self-documented as dead (`/* CSS tooltip
system disabled... */`, fully commented out) — correctly inert, not a false
finding, just confirms the pattern of "commented-out CSS left in place
instead of deleted" exists here too (minor, ~24 lines).

### `!important` density
- **878** occurrences in 4511 lines (~1 per 5.1 lines). Heaviest
  concentration: the button base block (1–31, every declaration
  `!important`) and the entire "Calm Glass 2026" `@layer workout` block
  (3539–4104, effectively 100% `!important` — see `@layer` risk below for
  why).

### Media-query breakpoint inventory
- **28** `@media` blocks, all either the custom 7-tier device-DPI ladder
  (`max-width:1280px` ... `min-width:2561px`, appearing 3 full times) or
  one-off Bootstrap-style breakpoints (`768px`, `575.98px`, `991.98px`,
  `1200px`) plus `prefers-reduced-motion`/`prefers-contrast: high`
  accessibility queries (2 each).

### `@layer` / cascade-order risk
- `components.css` opens `@layer workout { … }` at line 3539 (closes 4104).
  **No file anywhere in `static/css/` declares an explicit `@layer name1,
  name2, …;` order statement** (verified — `grep -rn "@layer"` across all
  of `static/css/*.css` finds only the four `@layer <name> {` block openers:
  `components.css:workout`, `navbar.css:navbar`, `pages-welcome.css:welcome`,
  `pages-workout-plan.css:workout-dropdowns` and `pages-workout-plan.css:
  workout` — no ordering declaration). **[RISK]** — per the CSS cascade-layers
  spec, *any* unlayered rule automatically outranks *every* layered rule
  regardless of specificity or source order. That means the `@layer workout`
  block in `components.css` (and the two `@layer` blocks in
  `pages-workout-plan.css`) can be silently defeated by an unlayered rule
  anywhere later in the cascade with equal-or-lower specificity — which is
  almost certainly *why* the `@layer workout` block in `components.css` is
  ~100% `!important` (3540–4104): `!important` was the workaround chosen for
  losing the layer/unlayered fight, rather than fixing the layer order. **Any
  WP4.1/WP4.2 rewrite that removes "unnecessary" `!important` inside these
  `@layer` blocks without first adding an explicit layer-order statement will
  silently un-fix real cascade bugs.** This is exactly the kind of trap the
  plan's "not just color" caution should extend to cover.

---

## static/css/pages-workout-plan.css (8226 lines)

### Structure / section map
| Lines | Section |
|---|---|
| 1–943 | Filter dropdown glass style + dark-mode twin, filter view-mode toggle (Simple/Advanced), legacy hierarchical/uniform dropdown rules (869–943, superseded-looking, see dead-code note) |
| 945–1316 | `@layer workout-dropdowns { … }` — custom-property-scoped (`--wpdd-*`) enhanced `<select>` replacement widget (button + popover + search + optgroup), light/dark tokens defined as CSS custom properties inside the layer, single `@media (prefers-reduced-motion)` + `@media (prefers-contrast: high)` |
| 1318–1457 | Global (non-layered) duplicate of the popover/option/search/count-indicator rules from the layer above, this time unscoped to `#workout[data-page="workout-plan"]` (`.wpdd-popover` appended to `document.body`, needs to work outside the wrapper) — a deliberate, commented-as-such duplication, not accidental |
| 1458–2594 | `@layer workout { … }` — the big one: `--wp-*` custom-property vocabulary (colors/spacing/radius/shadow/typography/transition/z-index, light + `[data-theme='dark']` swap), base container, page header, collapsible frame + frame header + frame title (all with dark twins inline), collapse-toggle (2026 "sky blue" glass variant, distinct from `components.css`'s toggle and from this same file's *other*, older collapse-toggle at 5538), workout-controls layout (`.horizontal-layout`, `.buttons-row`/`#action-buttons-row`, `.inline-control-item`), `.input-fields-group` full re-spec (contradicts `components.css`'s two versions — see cross-file note), color-coded input fields (pink/green/yellow, light+dark), value-changed highlight |
| 2594–2735 | Input-focus keyframe animation + reduced-motion override, dark-mode input-fields-group (outside the `@layer` block — layer closed at 2594) |
| 2735–3155 | Per-ID workout-plan action buttons (Add Exercise, Apply Filters, Clear Filters, Export Excel, Export to Log, Generate Plan, Backup Center, Clear Plan) — light + dark, each ~15–35 lines of gradient/shadow, effectively one bespoke component per button |
| 3156–3512 | `.workout-plan-table` — header/body cell styling light+dark, exercise-cell swap-button pill (2 different pill sizes defined: `.btn-swap` at 3411 vs a *narrower* redefinition later — see duplicate-selector note), row hover/stripe light+dark |
| 3513–3591 | Responsive (991.98/576px) + accessibility (`.visually-hidden`, `:focus-visible`, `prefers-contrast: high`) |
| 3593–3741 | Routine tabs (filter-by-routine pills), exercise-match-count badge, `@media (max-width:768px)` tab wrap |
| 3742–4373 | 7-tier responsive re-statement (720p→4K) of input-fields-group, dropdowns, selection-actions — same breakpoint ladder as `components.css`, third+ occurrence in the audited pair |
| 4375–4631 | Superset feature (colors as CSS custom properties `--superset-color-1..4` — a genuinely token-driven mini-system, well done relative to the rest of the file), link/unlink buttons, row indicators, badge, drag-partner pulse animation |
| 4633–4905 | Execution style (AMRAP/EMOM) badges + picker popup, dark-mode adjustments, mobile responsive |
| 4907–5217 | "Advanced mode" table column-width overrides (one rule block per named data column — Exercise/Muscle/Utility/Grips/etc., ~15 near-identical `[data-label="X"]` blocks), routine-tab 3-line label formatting + `@media (max-width:1366px)` compaction |
| 5219–5700 | `.frame-title`/`.filters-section`/`.input-frame`/`.action-frame`/`.horizontal-layout` — **generic, non-workout-plan-specific frame primitives** (see cross-file/mis-filed note), `.collapsible-frame` (a *second*, older, non-`#workout`-scoped, non-2026-glass version of the same concept already defined inside the `@layer workout` block above), `.collapse-toggle` base (older cyan-color variant, pre-dating and now fully shadowed by `.frame-header-2025 .collapse-toggle` at 6387) |
| 5700–5854 | **`.workout-log-frame`** + 7-tier responsive re-statement — this is Workout *Log* page content, not Workout *Plan* |
| 5855–6296 | **`.summary-frame`/`.summary-section`/`.summary-tables`/`.summary-header`/`.method-selector`/`.volume-legend`** + 7-tier responsive re-statement + dark mode — this is Weekly/Session *Summary* page content, not Workout Plan |
| 6298–6571 | "2025 Modern Collapsible Frame Enhancement" — a *third* pass at frame-header/collapse-toggle/animation concepts already covered at both 1458–2594 and 5219–5700, this time grid-based header layout + CSS-grid expand/collapse animation + a newer glassy toggle button skin, dark mode, reduced-motion, high-contrast |
| 6572–7180 | Routine cascade selector (3-step Environment→Program→Routine dropdown), breadcrumb, validation shake animation, 7-tier responsive re-statement (4th+ occurrence of the ladder), dark mode |
| 7208–7810 | **Muscle selector v3.0** (SVG body diagram, tabs, legend, tooltip) — shared component used by the generate-starter-plan modal and (per `components.css`) the progression page too, not workout-plan-specific; includes the **dead "ADVANCED MODE: GROUPED LEGEND" sub-block** (7591–7643, see dead-code section) |
| 7811–8226 | Workout Controls estimate provenance / "show the math" trace expander, Learned-Calibration badge, Fatigue-context chip/advisory/nudge (Phase 2D-A/2D-C surfaces per `docs/MASTER_HANDOVER.md` / `MEMORY.md`) — newest, best-tokenized content in the file (heavy `color-mix()` + `var(--ink-*/--accent)`, minimal raw hex) |

### Hardcoded color vs token usage
- Hex colors: **479**. `rgba()/rgb()`: **899** (highest of the two files —
  driven by the dozen-plus bespoke per-button gradient/shadow blocks at
  2735–3155, each with 3–5 `rgba()` stops per state × light/dark). `var(--...)`
  consumption: **438**.
- Token adoption is bimodal by *era* of the code, matching the section map:
  the `@layer workout` `--wp-*` system (1458–2594) and the newest fatigue/
  learned-calibration section (7811–8226) are well-tokenized; everything
  else — especially the per-button color blocks (2735–3155) and the
  "Advanced mode" column-width blocks (4907–5217) — is 100% hardcoded
  literals with no token consumption at all (column widths/paddings there
  are one-off `px` values with no corresponding `--wp-table-*` token even
  though `--wp-table-cell-padding`/`--wp-table-fs` already exist and are
  used elsewhere in the same file).

### Dark-mode strategy
- `[data-theme='dark']` occurrences: **198**, essentially all full-rule
  duplicates (light rule shape restated with dark literals), same pattern
  as `components.css`'s legacy sections — this file has no `color-mix()`
  dark-mode usage at all until the fatigue/learned-calibration tail
  (7811–8226), which uses it exclusively.
- **[CONFIRMS-PLAN]** WP4.2 lists `pages-workout-plan.css` last/highest-risk
  — confirmed by both volume (198 dark blocks, more than any file this
  auditor has seen in the series) and by the fact that dark-mode rules here
  are scattered across **at least 4 structurally separate frame/toggle
  systems that each reimplement the same concept** (the `@layer workout`
  frame system, the older non-layered `.collapsible-frame`/`.collapse-toggle`
  at 5219+, the "2025 Modern Collapsible Frame Enhancement" at 6298+, and
  per-button dark twins at 2735–3155) — a page-by-page token-swap pass
  cannot treat this as one coherent component; it's at least four.
- **[RISK] Dark rules that change layout, not just color** — confirmed
  concrete cases, both inside `@layer workout`:
  - `[data-theme='dark'] #workout[data-page="workout-plan"] .filters-title`
    (line ~1802) and `.form-label` (line ~2007) both force
    `padding: 0 !important` and `border-radius: 0 !important` in dark mode,
    values that differ from a plain color/background swap — these exist to
    strip a light-mode "chip" background treatment that dark mode doesn't
    want at all, not to recolor it. A pure custom-property color swap
    (WP4.2's stated technique) cannot express "also remove this padding" —
    these two rules need to survive as explicit overrides even after
    tokenization, or be restructured so the light-mode padding is itself
    conditional via a token (e.g. `--wp-title-padding`) rather than deleted
    in dark mode.
  - `[data-theme='dark'] #workout[data-page="workout-plan"] .horizontal-layout`
    sets `background-color: transparent; background: none;` where light
    mode has no background rule on `.horizontal-layout` at all (it's a
    layout container) — a defensive dark-mode-only rule fighting some other
    inherited background, not a swap of an existing light value.

### Duplicate / near-duplicate selectors within the file
- **Three separate "collapsible frame" implementations** coexist:
  (1) `#workout[data-page="workout-plan"] .collapsible-frame` inside
  `@layer workout` (~1671), (2) unscoped `.collapsible-frame` at 5404 (older,
  non-2026-glass, still setting real properties that would apply on
  workout-plan too since the layered version only wins where it's more
  specific / the layer ordering issue documented above applies), (3) the
  "2025 Modern Collapsible Frame Enhancement" grid-header/animation rules at
  6298+ layered on top of both. None are marked deprecated in comments.
- **Two `.collapse-toggle` skins**: cyan/`#00838f` flat version at 5538–5583
  (fully shadowed in practice by higher-specificity `!important` rules from
  `.frame-header-2025 .collapse-toggle` at 6387 and the `@layer workout`
  version at ~1818) and the sky-blue glass version(s). The 5538 block is
  visually dead (its declared values never win) but not *selector*-dead —
  worth flagging for WP4.2/4.3 as a candidate deletion once cascade order is
  verified with a visual diff, not a candidate for blind removal.
- **`.btn-swap` sizing defined twice** at different pixel sizes: 24×24px
  generic version would come from `components.css` (2052–2119, `width:24px;
  height:24px`) while `pages-workout-plan.css` (3411–3430) redefines it
  scoped to `#workout[data-page="workout-plan"] .workout-plan-table .btn.
  btn-swap` at `height:22px !important; min-height:22px !important` — a
  1px-scale override that's easy to lose track of across two files.
- **7-tier responsive breakpoint ladder repeated at least 6 times** in this
  file alone (3742–4373 for input-fields/dropdowns/selection-actions;
  5760–5854 for workout-log-frame; 5950–6032 for summary-frame; 6805–7055
  for cascade-dropdown) — more repetitions than `components.css`, and this
  is the file WP4.1's tokenization pass most needs to collapse into
  `tokens.css` consumption rather than restated literals.

### Rules that plausibly duplicate the other bundle / belong elsewhere
- **`.workout-log-frame` (5700–5854, ~155 lines incl. responsive) is
  Workout Log page content living in the Workout Plan bundle.** Per
  `.claude/rules/frontend.md`'s bundle list, `pages-workout-log.css` is a
  separate route bundle — this content's natural home. `components.css`
  *also* has an even larger `.workout-log-frame` dark-mode block
  (~1595–1774, ~180 lines). **Three-way duplication risk**: verify whether
  `pages-workout-log.css` (not read this phase) has a *third* copy before
  WP4.3 picks a canonical location.
- **`.summary-frame`/`.summary-section`/`.summary-tables`/`.summary-header`/
  `.method-selector`/`.volume-legend` (5855–6296, ~440 lines incl.
  responsive) is Weekly/Session Summary content**, and `components.css` has
  a parallel `.summary-frame.frame-calm-glass` treatment (4118–4225) for the
  same pages. This is the largest single misfiled block found in this
  phase — almost 450 lines of a different page's styling embedded in
  `pages-workout-plan.css`.
- **Muscle selector v3.0 (7208–7810, ~600 lines)** is shared by the
  generate-plan modal (on `/workout_plan`) *and* the progression page (per
  `components.css`'s `.progression-plan-container .exercise-selector`
  rules) — a legitimate `components.css` candidate rather than
  page-specific content, unlike the two findings above which are
  page-*wrong*, not just mis-scoped-as-shared.
- **[NEW]** This changes the shape of WP4.3's job for this file: it isn't
  primarily "find rules duplicated across pages and hoist to
  `components.css`" — it's "find whole page-specific sections that were
  pasted into the wrong page's bundle and move them to their correct page
  bundle (or `components.css` if genuinely cross-page)." The workout-log
  and summary content should almost certainly move to
  `pages-workout-log.css` / `pages-weekly-summary.css` /
  `pages-session-summary.css` respectively, not to `components.css`.

### Dead-looking selectors (spot-checked against templates/ and static/js/)
Checked via `grep -rl` across `templates/` and `static/js/`:

| Selector(s) | Result |
|---|---|
| `.filter-view-toggle` | 1 file — live |
| `.cascade-connector` | 3 files — live |
| `.breadcrumb-placeholder` | 3 files — live |
| `.btn-link-superset` / `.btn-unlink-superset` | 1 file each — live |
| `.superset-header-icon` | 1 file — live |
| `.muscle-tooltip` | 1 file — live |
| `.workout-estimate-fatigue-nudge-btn` | 1 file — live |
| `.wpdd-count-indicator` | 1 file — live |
| `.exercise-match-count` | 2 files — live |
| **`.legend-mode-badge`** (line ~7494) | **0 files — dead** |
| **`.legend-group`, `.legend-group-header`, `.legend-group-children`, `.legend-group-title`, `.legend-item.legend-child`, `.legend-checkbox.small`** (the entire "ADVANCED MODE: GROUPED LEGEND" block, 7591–7643, ~53 lines) | **0 files — dead** |
| **`.view-toggle-group`** (muscle-selector header controls, ~7243) | **0 files — dead** |

- **[NEW]** Re-verified with a second grep pass across `routes/`, `utils/`
  too (not just templates/JS) for `legend-mode-badge`/`legend-group` —
  zero hits repo-wide. This is ~60 lines of confidently dead CSS, all in
  one coherent block (the grouped-legend variant of the muscle selector
  was apparently superseded by the flat `.legend-item`/`.legend-checkbard`
  list that *is* referenced by `muscle-selector.js`). Good, low-risk
  deletion candidate — but out of scope for a CSS-only phase-4 WP per the
  plan's own sequencing (dead-code deletions are Phase 0 territory); flagging
  here so a future WP0.x pass or WP4.1 measure-only step can pick it up.
- Also structurally dead (not selector-dead): the older `.collapse-toggle`
  (5538) and the second `.collapsible-frame` (5404) declarations discussed
  above are selectors that *are* referenced by templates (the classes are
  applied in markup) but whose declared *values* are fully shadowed by
  later, more specific/`!important` rules — "dead paint", not dead
  selectors. Not counted in the dead-selector table since the class is live.

### `!important` density
- **687** occurrences in 8226 lines (~1 per 12 lines — lower density than
  `components.css`'s ~1-per-5, but concentrated: the per-button color blocks
  (2735–3155) and the `@layer workout` collapse-toggle/frame sections are
  90%+ `!important`, while the newer superset/execution-style/fatigue-context
  sections (4375–4905, 7811–8226) use almost none — again tracking the
  file's "era" split.

### Media-query breakpoint inventory
- **68** `@media` blocks — by far the most of any file in this phase pair.
  Breakpoint set used: the same custom 7-tier ladder
  (`≤1280 / 1281–1366 / 1367–1536 / 1537–1600 / 1601–1920 / 1921–2560 /
  ≥2561`, repeated **6 full times**), plus ad hoc Bootstrap-style points
  (`576px`, `768px`, `767.98px`, `575.98px`, `991.98px`, `992px`, `993px`,
  `1200px`, `1201px`, `1366px`) used inconsistently per component (e.g. the
  routine-tab compaction breakpoint is `1366px` while the near-identical
  cascade-dropdown compaction ladder starts its "very compact" tier at
  `1280px` — no single shared "small screen" cutoff).

### `@layer` / cascade-order risk (file-specific)
- Two named layers here: `workout-dropdopdowns` → correction, `workout-
  dropdowns` (951) and `workout` (1463), the latter sharing its name with
  `components.css`'s `@layer workout` block — **per the CSS spec, same-named
  layers merge into one cascade layer regardless of which file declares
  them**, so `components.css`'s `@layer workout` rules and this file's
  `@layer workout` rules interleave into a single merged layer whose
  internal order depends on **file load order** (per
  `.claude/rules/frontend.md`, `components.css` is a global bundle loaded
  before route bundles, so it wins ties) — but there is still no explicit
  `@layer` order statement anywhere, so this whole merged `workout` layer as
  a unit remains vulnerable to being outranked by any unlayered rule in
  *either* file or any other bundle loaded later. Same risk as documented
  under `components.css`, doubled by the two files actually sharing a layer
  namespace. **[RISK]** — WP4.2/4.3 executors touching either file's
  `@layer workout` block must treat both files' occurrences as one unit for
  testing purposes; a visual-diff gate scoped to only one file's changes
  could miss a regression caused by shifting merged-layer internal order.

---

## Cross-cutting seeds

1. **[RISK] No explicit `@layer` order statement exists anywhere in
   `static/css/`, and `components.css` + `pages-workout-plan.css` share one
   named layer (`workout`) that silently merges across files by load order.**
   Nearly 100% of the rules inside these `@layer` blocks carry `!important`
   — almost certainly a workaround for losing to unlayered rules, not a
   style choice. Any WP4.1/WP4.2 pass that "cleans up" `!important` inside
   an `@layer` block without first adding `@layer <explicit order>;` at the
   top of the cascade will likely reintroduce the exact bugs the
   `!important` was added to fix. Recommend WP4.1 add the explicit order
   statement (measure-only, one line) before any other WP4.x touches these
   blocks.

2. **[NEW] `pages-workout-plan.css` contains ~600 lines of content that
   belongs to *other* pages, not just "shared" content that belongs in
   `components.css`.** `.workout-log-frame` (~155 lines) is Workout Log
   page content; `.summary-frame`/`.summary-section`/`.summary-tables`/
   `.summary-header`/`.method-selector`/`.volume-legend` (~440 lines) is
   Weekly/Session Summary content. WP4.3's framing ("dedupe rules
   duplicated across ≥2 page bundles into `components.css`") should be
   read to include "move misfiled page-specific content to its correct
   page bundle", which is a different operation (relocate, not
   generalize-and-share) and changes both the diff shape and the visual-gate
   scope (must re-run the *target* page's screens, not just
   `pages-workout-plan.css`'s own screens).

3. **[CONFIRMS-PLAN] Token adoption is real but bimodal by code "era" in
   both files** — the newest sections (superset colors, fatigue-context/
   learned-calibration in `pages-workout-plan.css`; the "calm glass"
   overlay in `components.css`) are well-tokenized via `var()`/`color-mix()`;
   everything older is close to 0% tokenized and duplicates the same
   literal colors (e.g. `#4f8cff`/`rgba(79,140,255,…)` "workout accent
   blue") dozens of times across both files despite equivalent tokens
   (`--accent`, `--wp-accent`) existing in the same files. WP4.1's
   tokenization pass has a template to follow (the newest code) rather than
   inventing conventions from scratch.

4. **[NEW] Two parallel, overlapping token vocabularies exist in
   `tokens.css` itself** — a legacy responsive-only system (`--space-*`,
   `--input-*`, `--btn-*`, `--frame-*`, `--table-*`, `--font-size-*`, no
   dark-mode variants) and a newer "Calm Glass 2026" system (`--s-*`,
   `--surface-*`, `--ink-*`, `--r-*`, with dark-mode variants) whose
   spacing scales overlap in value but not name (`--space-md: 0.75rem` ==
   `--s-3: 12px`). WP4.1 should pick one canonical spacing scale before
   expanding token consumption, or risk institutionalizing both.

5. **[RISK] The custom 7-tier device-DPI breakpoint ladder
   (720p/1366/1536/1600/1920/2560/4K) is restated as a literal `@media`
   block, not consumed via a shared mechanism, roughly 9 times total across
   the two files** (3 in `components.css`, 6 in `pages-workout-plan.css`) —
   `tokens.css` already defines the canonical version of this ladder for its
   own token re-assignment. Vanilla CSS has no native `@media` "mixin", so
   full deduplication isn't free, but WP4.1 should at minimum audit whether
   each restated block is *consuming* `tokens.css`'s responsive tokens
   (many aren't — they hardcode fresh px/rem values per breakpoint instead)
   before deciding whether to keep the ladder as literal `@media` blocks or
   convert them to consume `var(--input-height-sm)` etc. inside a single
   `@media` block per breakpoint.

6. **[NEW] Confirmed, low-risk dead CSS**: `.legend-mode-badge` and the
   entire "ADVANCED MODE: GROUPED LEGEND" block (`.legend-group`,
   `.legend-group-header/-children/-title`, `.legend-item.legend-child`,
   `.legend-checkbox.small`) and `.view-toggle-group` — zero references in
   `templates/`, `static/js/`, `routes/`, or `utils/`. ~60 lines total, one
   coherent superseded feature (grouped muscle-selector legend). Not a
   Phase-4 CSS-cleanup WP per the plan's own sequencing (dead-code deletion
   is Phase 0's job), but cheap to fold into WP4.1 as a measure-only note or
   a trivial follow-up WP0.x.
