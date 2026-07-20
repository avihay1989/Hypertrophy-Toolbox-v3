# CSS Phase 4 WP4.3g Evidence — Weekly Summary Dark/Token Cleanup

Date: 2026-07-20

Branch: `wt/wp4-3-weekly-summary-dark-token-cleanup`

Base: local `main` at `08256f0` (WP4.3f Session Summary shipped via PR #161).

## Scope and isolation

WP4.3g changed only the Weekly Summary route bundle in production:
`static/css/pages-weekly-summary.css`. The companion change in
`tests/test_css_cascade_contracts.py` pins the preserved cascade contract; this
evidence file and the canonical handover documents are the only documentation
changes. No template, JavaScript, API, schema, calculation, shared CSS,
`theme-dark.css`, another page, or WP4.4 work is included. The production/test
working diff is two files (+70 / -64).

`pages-weekly-summary.css` is loaded only by `templates/weekly_summary.html`
(via the `page_css` block). The worktree started from base `08256f0` on branch
`wt/wp4-3-weekly-summary-dark-token-cleanup`; its commits ahead/behind `main`
are 0/0 (working-tree change only). Its tracked visual fixture has SHA-256
`6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.

## Change 1 — value-preserving token extraction

The repeated solid-color dark-mode, ink, and border literals were extracted into
eleven page-local semantic tokens (a `:root` block for the two light-context
tokens, a `[data-theme='dark']` block for the nine dark-context tokens, mirroring
the WP4.3f `pages-session-summary.css` set — the two bundles were byte-identical
for this region). Every substitution is exact-value, so no rendered element
changes:

| Token | Value | Role | Consumers |
| --- | --- | --- | ---: |
| `--wk-table-border` | `#d0d0d0` | light table border | 6 |
| `--wk-label-ink` | `#495057` | light label/heading ink | 2 |
| `--wk-dark-ink` | `#e0e0e0` | dark body/legend ink | 9 |
| `--wk-dark-ink-bright` | `#fff` | dark bright ink | 12 |
| `--wk-dark-border` | `#404040` | dark border | 5 |
| `--wk-dark-border-strong` | `#495057` | dark strong border | 6 |
| `--wk-dark-surface` | `#212529` | dark table surface | 3 |
| `--wk-dark-surface-deep` | `#1a1a1a` | dark deep surface | 2 |
| `--wk-dark-elevated` | `#343a40` | dark elevated surface | 3 |
| `--wk-dark-cell` | `#2d2d2d` | dark cell/stripe | 2 |
| `--wk-dark-hover` | `#3d3d3d` | dark row hover | 2 |

Distinct semantic roles keep distinct tokens even when values coincide:
`#495057` backs both `--wk-label-ink` (light label ink, `color:`) and
`--wk-dark-border-strong` (dark border, `border-color:`); the two were split by
CSS property, not merged. Only exact repeated expressions were replaced.

Deliberately left untouched:

- the weekly-only `#isolated_muscles_filter` form-control border (`#d0d0d0`,
  a distinct single-use role) and its label ink (`#505050`, single-use), both
  of which remain route-owned;
- the single-use dark literals `#252525`, `#2a2a2a`, `#2c3034`, `#b0b0b0`;
- the shared volume-badge classification colors (`#dc3545`, `#fd7e14`,
  `#198754`, `#6f42c1`), the `white` keyword fills, the light striping
  `#ffffff`/`#f8f8f8`/`#f5f5f5`, and the translucent-white glass overlays.

The edit was produced by a count-asserting Python transform that preserved
CRLF line endings, and validated by expanding every `var(--wk-*)` back to its
literal: the resulting body (from `.volume-indicator` onward) is byte-identical
to the pre-edit weekly bundle with the dead arms removed. No document-wide
`html:has()` selector was introduced.

## Change 2 — deferred finding (a) resolved: dead `#session-summary-*` arms removed

WP4.3f deferred the dead `#session-summary-container`/`-table` selector arms in
the summary bundle. `weekly_summary.html` renders only
`id="weekly-summary-container"` and `id="weekly-summary-table"` (verified by
grep; the `#session-summary-*` ids exist only in `session_summary.html`, which
loads its own bundle). All **12** `#session-summary-*` selector arms were dropped
from the weekly bundle. Every affected rule retained its live `#weekly-summary-*`
arm (or its `.summary-frame`/`.summary-section`/`.summary-tables` class arms), so
no rule was deleted, no declaration was lost, and every token consumer count is
unchanged. The focused visual suite (below) confirms zero rendered change.

## Change 3 — deferred finding (b) audited: two parallel dark table systems both live

WP4.3f also deferred the two parallel dark table systems on the shared
`.summary-*` classes (`.table-striped` `#252525`/`#2d2d2d` vs `.summary-tables`
`#212529`/`#343a40`). A browser computed-declaration-owner audit was run on the
running weekly-summary page (three rendered tables) in **both** themes,
resolving the winning owner for `background-color`, `color`, and
`border-top-color` on `thead th` and odd/even `td` cells. Results:

- **Table 1** (`#weekly-summary-container`): every dark thead/td winner is the
  ID-bearing System-1 rule (`[data-theme='dark'] #weekly-summary-container .table
  thead th` / `.table td`) → `#1a1a1a` / `#2d2d2d` / `#e0e0e0` / `#404040`. The
  System-2 rules and the striping rules are overridden here.
- **Tables 2 & 3** (no ID): thead **bg + border** owned by System-2
  (`.summary-tables .table thead th` → `#343a40` / `#495057`); thead **text
  color** owned by a **shared components.css** rule
  (`.summary-frame.frame-calm-glass .table thead th` → `var(--ink-2)`); odd-row
  **bg** owned by System-2's `nth-of-type(2n+1)` rule (`#2a2a2a`); even-row
  **bg** + all non-ID row **text color** owned by System-1 striping
  (`#2d2d2d` / `#e0e0e0`).

Both page-local dark systems therefore own live winning declarations across the
three tables; a shared component rule owns thead text color on the non-ID
tables. No **whole** dark rule is dead. The only dead items are individual
declarations nested inside otherwise-live multi-declaration rules (e.g.
System-1 striping's odd-row `background`, whose sibling `color` declaration is
the live owner for tables 2/3 odd-row text). Removing them would require
per-declaration cascade surgery that perturbs token consumer counts for a
sub-line benefit and is not cleanly provable in isolation. Per the packet's
"remove only browser-proven-dead declarations; if a removal isn't cleanly
provable, leave it and note it," the dark systems were **left intact and
documented**. The light-mode owner audit confirmed the dark systems are dormant
there (winners are the shared components rules and the page-local light rules).

## Rendered equivalence

The focused Weekly Summary visual suite renders all six Windows variants
(desktop / tablet / mobile × light / dark) **byte-identical** to their committed
baselines, update-free — a strict superset of a sampled computed-value audit,
proving zero rendered change in either theme from the token extraction and the
dead-arm removal. All twelve committed Weekly Summary images (six Linux + six
Windows) are byte-identical to base.

## Contract lock

`test_weekly_summary_tokens_extract_values_and_drop_dead_session_arms` pins:

- stylesheet load order (a11y before the page bundle, page bundle before
  `motion.css` before `theme-dark.css`) and the absence of document-wide
  `html:has()`;
- each of the eleven new tokens defined once and consumed by the exact count of
  the repeated literal it replaced;
- every extracted literal surviving only in its token definition, with two
  intentional keeps proved by count: `#d0d0d0` == 2 (token def + the weekly-only
  filter border) and `#495057` == 2 (its two distinct-role tokens);
- `color: #fff` / `color: #fff !important` no longer appearing, and
  `--wk-dark-ink-bright: #fff` present;
- `#session-summary` absent and `#weekly-summary-container` present (finding a),
  and the `id="weekly-summary-container"` template hook intact;
- the weekly-only `#isolated_muscles_filter` block kept (`#505050` == 1);
- the finding-(b) single-use dark literals (`#252525`, `#2a2a2a`, `#2c3034`,
  `#b0b0b0`) and the shared volume-badge colors intact;
- the light striping `#ffffff` and all nine `@media` blocks preserved.

The combined selector/cascade + visual-selector contract gate is now **19/19**.

## Stylelint measurement

Pinned Stylelint `16.11.0` parsed all measured sources with zero parse errors,
invalid-option warnings, or errored files.

| Measurement | pre-edit (HEAD) | WP4.3g final | Delta |
| --- | ---: | ---: | ---: |
| Focused Weekly Summary warnings | 184 | 144 | -40 |
| Focused hardcoded-value (`declaration-property-value-disallowed-list`) | 77 | 40 | -37 |
| Focused `declaration-no-important` | 55 | 55 | 0 |
| Focused `no-descending-specificity` | 50 | 47 | -3 |
| Focused `no-duplicate-selectors` | 2 | 2 | 0 |
| Total warnings (all CSS/SCSS) | 6,294 | 6,254 | -40 |
| Total `declaration-no-important` | 2,337 | 2,337 | 0 |
| Total `no-descending-specificity` | 673 | 670 | -3 |
| Total `no-duplicate-selectors` | 50 | 50 | 0 |

No monitored important, specificity, or duplicate category increased (focused
and total specificity fell by 3 as a side effect of removing the dead
`#session-summary-*` arms). Cumulative delta vs the WP4.1 pinned baseline
(7,202) is -948.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| worktree isolation (commits ahead/behind main pre-commit) | 0 / 0 (working-tree change only) |
| selector/cascade + visual contracts | 19/19 passed |
| blocking Flake8 selection (changed test) | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Vitest | 105/105 passed |
| focused Weekly Summary Chromium visual | 6/6 passed update-free |
| Weekly functional (`summary-pages.spec.ts`) | 20/20 passed |
| required CI Chromium functional list (2-shard) | 215/215 + 211/211 = 426/426 passed |
| tracked-file pytest | 1,740 passed + 2 permitted catalog reds |

The only pytest failures were the unchanged visual-seed catalog invariants
(null/blank `primary_muscle_group`, null/blank `movement_pattern` — 454
`movement_pattern` rows reported). The additional Python pass relative to WP4.3f
is the new Weekly Summary cascade contract.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Windows Weekly Summary variants | 6/6 passed update-free |
| complete `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels (initial 1,046, settling to 1,039 on retry) |
| complete thumbnail suite | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels (initial 6,276, settling to 6,262 on retry) + 16 not run |

Both persistent reds are the exact WP4.0 known reds on the workout-plan page,
which this Weekly-Summary-only change does not touch. The combined deep run
(`visual.spec.ts` + `visual-baseline-thumbnails.spec.ts`) reported 60 passed and
exactly these two reds.

## Integrity locks

- Screenshot manifest: **156 files, 0 mismatches** against main.
- Generated Bootstrap SHA-256: main checkout
  `24CC9F443D2D0933F1C89DC7203B0618063C4706ADE17627F0A03934C73D75D4`;
  isolated worktree
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`
  (the established worktree-vs-main generated-bundle divergence recorded since
  WP4.3a; the CSS change does not touch it).
- Visual-fixture DB SHA-256:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- Main live DB SHA-256:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

The twelve committed Weekly Summary images remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `362D67E2AB6A841CCDC17EC1FE20F60F7FA0F25A98B11BB0B6C9A15209BA539A` |
| Linux desktop light | `551E4F032394FC9FD60387927162657DBACEC4FD16D599F3A411B4E419794FAC` |
| Linux mobile dark | `0C986DB4BC2D396E632A2DA7B2E18DE70F80AB9CEDBB631D726C8E960E5D4196` |
| Linux mobile light | `DA600BC3FA968EF672975A6A063858E63DD5FBF17A029C6A53F6ED9E78C4F456` |
| Linux tablet dark | `4545F56489C4EE8BF6CB42BAB75E7D11DCA71DD3F58D562688E1D2C1D112DDDC` |
| Linux tablet light | `CFF2D94E1A436C897EBA73833081A496237663F1EDEA24E4BABF3EE60D990C53` |
| Windows desktop dark | `480926DB7A38FEF0F2AFE7114683FD8674BEBEA42B72B8E4C107FCD5531FC99E` |
| Windows desktop light | `89757F8E960DD16BEDB76F87AE3CCAA287A5FD56F636C86B736A166C54AB96DE` |
| Windows mobile dark | `EF25FF6185563C45012A4641C54B03B942EC5707CF33F62EE21970FAD849A10A` |
| Windows mobile light | `2E95912882352FF0B07B83B1F894F3FE8E886B135E209667334F17B88AA8B53F` |
| Windows tablet dark | `1E59347995DA1C8D34F399B8EA85EEFF67F57DC2A8937492F6C00A613E7944E7` |
| Windows tablet light | `3FDD5E78764A102C65A2CF8333D562BC5499F7EDF05878B3A29AFDBAE3186203` |

## Next action

WP4.3g is complete in isolated `wt/wp4-3-weekly-summary-dark-token-cleanup` and
shipped to `main` via PR. The next packet in order is WP4.3h User Profile
(audit / minimal cleanup), then WP4.3i workout-plan (sectioned) and WP4.3j
workout-log (multi-WP, redesign-sized), then WP4.4 (shared bundles / navbar /
`theme-dark.css`). Do not begin without explicit direction.
