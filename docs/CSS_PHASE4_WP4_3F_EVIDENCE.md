# CSS Phase 4 WP4.3f Evidence — Session Summary Dark/Token Cleanup

Date: 2026-07-19

Branch: `wt/wp4-3-session-summary-dark-token-cleanup`

Base: local `main` at `5e7d290b3168b4c58e5533b45aed3f3b73a8cb52`

## Scope and isolation

WP4.3f changed only the Session Summary route bundle in production:
`static/css/pages-session-summary.css`. The companion change in
`tests/test_css_cascade_contracts.py` pins the preserved cascade contract; this
evidence file and the canonical handover documents are the only documentation
changes. No template, JavaScript, API, schema, calculation, shared CSS,
`theme-dark.css`, another page, or WP4.4 work is included. The production/test
working diff is two files.

`pages-session-summary.css` is loaded only by `templates/session_summary.html`
(via the `page_css` block). The worktree started from base `5e7d290` on branch
`wt/wp4-3-session-summary-dark-token-cleanup`; its seeded database and the
tracked visual fixture both have SHA-256
`6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.

## Change — value-preserving token extraction

The repeated solid-color dark-mode, ink, and border literals were extracted into
eleven page-local semantic tokens (a `:root` block for the two light-context
tokens, a `[data-theme='dark']` block for the nine dark-context tokens, mirroring
the WP4.3d `pages-volume-splitter.css` pattern). Every substitution is
exact-value, so no rendered element changes:

| Token | Value | Role | Consumers |
| --- | --- | --- | ---: |
| `--ss-table-border` | `#d0d0d0` | light table border | 6 |
| `--ss-label-ink` | `#495057` | light label/heading ink | 2 |
| `--ss-dark-ink` | `#e0e0e0` | dark body/legend ink | 9 |
| `--ss-dark-ink-bright` | `#fff` | dark bright ink | 12 |
| `--ss-dark-border` | `#404040` | dark border | 5 |
| `--ss-dark-border-strong` | `#495057` | dark strong border | 6 |
| `--ss-dark-surface` | `#212529` | dark table surface | 3 |
| `--ss-dark-surface-deep` | `#1a1a1a` | dark deep surface | 2 |
| `--ss-dark-elevated` | `#343a40` | dark elevated surface | 3 |
| `--ss-dark-cell` | `#2d2d2d` | dark cell/stripe | 2 |
| `--ss-dark-hover` | `#3d3d3d` | dark row hover | 2 |

Distinct semantic roles keep distinct tokens even when values coincide:
`#495057` backs both `--ss-label-ink` (light label ink, `color:`) and
`--ss-dark-border-strong` (dark border, `border-color:`); the two were split by
CSS property, not merged. Only exact repeated expressions were replaced. Single
or shared literals were deliberately left untouched: the shared volume-badge
classification colors (`#dc3545`, `#fd7e14`, `#198754`, `#6f42c1`), the `white`
keyword badge/select fills, the light striping `#ffffff`/`#f8f8f8`/`#f5f5f5`, and
the translucent-white glass overlays.

No custom property was removed and no rule was deleted; this packet is a pure
value-preserving extraction. No document-wide `:has()` selector was introduced.

### Deferred findings (not in this packet)

Two hygiene opportunities were identified and intentionally left for a later
pass to keep this diff a safe, byte-identical extraction:

- The file carries many `#weekly-summary-container` / `#weekly-summary-table`
  selector arms that are dead on the only page that loads it (those ids exist
  only in `weekly_summary.html`, which loads its own `pages-weekly-summary.css`).
- Two parallel dark table systems style the shared `.summary-*` classes
  (`.table-striped` `#252525`/`#2d2d2d` vs `.summary-tables` `#212529`/`#343a40`).

Removing either requires selector-list surgery / a browser declaration-owner
audit and is better handled alongside the WP4.3g Weekly Summary packet or a
shared-frame dedupe, not folded into this extraction.

## Rendered equivalence

The focused Session Summary visual suite renders all six Windows variants
(desktop / tablet / mobile × light / dark) **byte-identical** to their committed
baselines, update-free — a strict superset of a sampled computed-value audit,
proving zero rendered change in either theme. All twelve committed Session
Summary images (six Linux + six Windows) are byte-identical to base.

## Contract lock

`test_session_summary_tokens_extract_exact_values_value_preserving` pins:

- stylesheet load order (a11y before the page bundle, page bundle before
  `motion.css` before `theme-dark.css`) and the absence of document-wide
  `html:has()`;
- each of the eleven new tokens defined once and consumed by the exact count of
  the repeated literal it replaced;
- every extracted literal surviving only in its single token definition
  (`#495057` twice, for its two distinct-role tokens);
- `color: #fff` no longer appearing outside the token definition;
- the shared volume-badge colors, the light striping `#ffffff`, all nine
  `@media` blocks, and the `id="session-summary-container"` template hook intact.

The combined selector/cascade + visual-selector contract gate is now **18/18**.

## Stylelint measurement

Pinned Stylelint `16.11.0` parsed all measured sources with zero parse errors,
invalid-option warnings, or errored files.

| Measurement | pre-edit (HEAD) | WP4.3f final | Delta |
| --- | ---: | ---: | ---: |
| Focused Session Summary warnings | 183 | 146 | -37 |
| Focused hardcoded-value (`declaration-property-value-disallowed-list`) | 76 | 39 | -37 |
| Focused `declaration-no-important` | 55 | 55 | 0 |
| Focused `no-descending-specificity` | 50 | 50 | 0 |
| Focused `no-duplicate-selectors` | 2 | 2 | 0 |
| Total warnings (all CSS/SCSS) | 6,331 | 6,294 | -37 |

No monitored important, specificity, or duplicate category increased. Cumulative
delta vs the WP4.1 pinned baseline (7,202) is -908.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| selector/cascade + visual contracts | 18/18 passed |
| blocking Flake8 selection (changed test) | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Vitest | 105/105 passed |
| focused Session Summary Chromium visual | 6/6 passed update-free |
| required CI Chromium functional list (2-shard) | 215/215 + 211/211 = 426/426 passed |
| tracked-file pytest | 1,739 passed + 2 permitted catalog reds |

The only pytest failures were the unchanged visual-seed catalog invariants (633
null/blank `primary_muscle_group`, 454 null/blank `movement_pattern`). The
additional Python pass relative to WP4.3e is the new Session Summary cascade
contract.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Windows Session Summary variants | 6/6 passed update-free |
| complete `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels (initial 1,046, settling to 1,039 on retry) |
| complete thumbnail suite | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels (initial 6,276, settling to 6,262 on retry) + 16 not run |

Both persistent reds are the exact WP4.0 known reds on the workout-plan page,
which this Session-Summary-only change does not touch.

## Integrity locks

- Screenshot manifest: **156 files, 0 mismatches** against main.
- Generated Bootstrap SHA-256: main checkout
  `24CC9F443D2D0933F1C89DC7203B0618063C4706ADE17627F0A03934C73D75D4`;
  isolated worktree
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`
  (the established worktree-vs-main generated-bundle divergence recorded since
  WP4.3a; the CSS change does not touch it).
- Target worktree and visual-fixture DB SHA-256:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- Main live DB SHA-256:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

The twelve committed Session Summary images remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `64340708ADA6926C99716A4F23575BDF18BE9989CB2C149BD17FB687A9FB7612` |
| Linux desktop light | `64B23002713EC92FF09E2744DCBE15E3371D7654657847DA731A68725FBE1DD6` |
| Linux mobile dark | `F5036468E1F9CE659F8ECEE91C8D1835EA39EA57B395D9AC3294E9637A030C43` |
| Linux mobile light | `227A5E35DD0B1BD4808D76BAC89A0CCBDE74AB997E838BEDCE52C420BED9A0A6` |
| Linux tablet dark | `65D22A6887F1D479717D2259CC5E96F93B835DD4033525678B74A8FF05D2AD39` |
| Linux tablet light | `96E0356928C5DEE976C5C082A0E026ADEAF8BD45DB33F3106594673832767494` |
| Windows desktop dark | `3ADE310CED838F26C202CA559A9E4935D1B0EB13CC8DC49C2764285D07A80081` |
| Windows desktop light | `8A5C325B62701ACC61F62764ED6456E768ED9827FD2889E0245318FD0A205989` |
| Windows mobile dark | `E1E6DE038B2C3719A9C5A02EFE162972D9CA372DAC6CC24CB49C573C97C28184` |
| Windows mobile light | `8A900834B2F094177E0AA9A441EE5EFD2026DC7F23E717423F96D308FEDAED76` |
| Windows tablet dark | `F81807CF6B724BE6CD48CC816FE4774D6B6356C53ABB7A0DA9674FB3A3945ABB` |
| Windows tablet light | `2143992EFE8BD6B7C988267304F1E4080583D607B4CD87DBD54309BCD78B10DB` |

## Next action

WP4.3f is complete in isolated `wt/wp4-3-session-summary-dark-token-cleanup` and
shipped via PR to `main`. The next packet in order is WP4.3g Weekly Summary
(a good place to also resolve the deferred dead `#weekly-*` arms and the two
parallel dark table systems). Do not begin it without explicit direction.
