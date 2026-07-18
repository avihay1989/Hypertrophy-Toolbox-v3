# CSS Phase 4 WP4.3b — Body Composition dark/token cleanup evidence

Date: 2026-07-18

Branch: `wt/wp4-3-body-composition-dark-token-cleanup`

Worktree: `D:\development\Hypertrophy-Toolbox-v3-main-wp4-3-body-composition-dark-token-cleanup`

Base: `b80c2229bad998f50c472e9de9ab466b8dfd3371` (`main`, zero divergence at start)

## Scope and ownership audit

This packet changes only the Body Composition route bundle and one cascade
regression contract. The template, Body Composition JavaScript, shared CSS,
generated Bootstrap, APIs, calculations, schemas, and databases are unchanged.
Progression and every later WP4.3 page remain out of scope.

Runtime stylesheet order is `tokens.css`, generated Bootstrap, `base.css`,
`layout.css`, `components.css`, `navbar.css`, `a11y.css`, the route bundle,
`motion.css`, then `theme-dark.css`. The feature root remains
`.body-composition-page[data-page="body-composition"]`; JavaScript still locates
`[data-bc-app]`. The route bundle owns its geometry and `--bc-*` feature palette,
while shared components own generic heading colors.

The browser audit corrected the packet's candidate assumption about the heading:
the route's `h1` color did not win in either theme. In light mode, the shared
`components.css` important heading rule wins; in dark mode, the more-specific
shared dark components rule wins. The late generic `theme-dark.css` heading rule
also matches in dark mode but loses on specificity. Removing the dead route
declarations therefore preserves the actual shared owner rather than transferring
ownership to a new rule.

Before editing, `pages-body-composition.css` was 324 lines / 6,706 bytes. Its
focused Stylelint result was 37 warnings, all hardcoded values. Exact repeated
literals were `#56626a` (five uses), `#283b5a` (two), and `#111` (two). The two
`#fff` border uses remain literal because they are separate retained edge
semantics with no exact shared semantic token.

## Token and dark-mode decisions

- Added page-local `--bc-copy-muted`, `--bc-copy-supporting`, and
  `--bc-band-tick` tokens for exact repeated values only.
- Replaced only exact consumers; no near-match was folded into a token.
- Removed the route-local heading color and its dark selector member because
  shared important component rules already own the rendered color in both themes.
- Removed the dark `--bc-accent-soft` remap. Its only possible consumer,
  `.bc-form-guide`, already has a direct dark background override, so the remap
  changed a computed custom property but no rendered property.
- Retained the rest of the page namespace and dark remaps because they have live,
  feature-specific consumers.

The final bundle is 324 lines / 6,753 bytes. No template or runtime hook,
specificity, media query, responsive breakpoint, `!important`, or stylesheet
load-order change was made.

## Computed-style and cascade proof

A temporary Playwright audit ran against the isolated visual fixture with
`PW_VISUAL_SEED=1`. It captured 17 representative targets in light and dark:
the root, heading, form help/guide, result panel and values, band title/tick/current
copy, supporting copy, citations, trend states, and empty state.

All rendered computed values were identical before and after the edit. The only
intentional raw custom-property delta was the dead dark `--bc-accent-soft` value,
from `rgba(45, 108, 223, 0.18)` to the inherited light value `#e3edff`; the live
guide background remained identical because its direct dark declaration wins.
The heading remained shared-components-owned in both themes. The committed
contract pins that boundary, page-local token scope and live consumers, the
single remaining `--bc-accent-soft` definition, stylesheet order, the 1,100px
breakpoint, and the template/JavaScript hooks.

## Stylelint measurement

Pinned Stylelint `16.11.0` with `postcss-scss` `4.0.9` parsed all 21 measured
sources with zero parse errors, invalid-option warnings, or errored files.

| Measurement | WP4.3a / pre-edit | WP4.3b final | Delta |
| --- | ---: | ---: | ---: |
| Focused Body Composition warnings | 37 | 30 | -7 |
| Total warnings | 6,435 | 6,428 | -7 |
| Hardcoded-value warnings | 2,988 | 2,981 | -7 |
| Duplicate selectors | 50 | 50 | 0 |
| Duplicate properties | 2 | 2 | 0 |
| Descending specificity | 673 | 673 | 0 |
| `declaration-no-important` | 2,341 | 2,341 | 0 |
| Lexical `!important` | 2,345 | 2,345 | 0 |
| `selector-max-id` | 191 | 191 | 0 |
| `selector-max-specificity` | 188 | 188 | 0 |
| Property-unknown warnings | 2 | 2 | 0 |

All 30 focused warnings remain hardcoded-value warnings. No monitored cascade or
specificity category increased.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| Body Composition PostCSS parse | 1/1 passed |
| selector/cascade + visual contracts | 14/14 passed |
| browser rendered computed-style comparison | identical in light and dark |
| blocking Flake8 selection | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Node syntax, 63 application files + reporter | 64/64 passed |
| Vitest | 105/105 passed |
| CI workflow YAML validation | 2/2 parsed |
| focused Body Composition Chromium | 9/9 passed |
| exact required CI Chromium list | 407/407 passed |
| full pytest in a tracked-file sandbox with a disposable DB copy | 1,735 passed + 2 permitted catalog reds |

The extra Python pass relative to WP4.3a is the new cascade contract. The only
pytest failures were the unchanged visual-seed catalog invariants: 633 null/blank
`primary_muscle_group` rows and 454 null/blank `movement_pattern` rows.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Windows Body Composition variants | 6/6 passed update-free |
| complete `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels on all attempts |
| complete thumbnail suite | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels on all attempts + 16 not run |

## Integrity locks

- Screenshot manifest: **156 files, 0 mismatches**.
- Generated Bootstrap SHA-256:
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
- Target visual-seeded DB SHA-256:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- Main live DB SHA-256:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

The twelve committed Body Composition images also remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `F27945192F190936857B3BF35F5D567FB4C732F3B7931A3CACBD6F7A7F21EB24` |
| Linux desktop light | `822F54C29C0CA0B79C11A3C025D43C70250C152D170F26A0DA679EFAF9FCFCCD` |
| Linux mobile dark | `EDA8D02840DE4B2F29FC088FF406F08CB3F36C210FA8F1EEA3A00D01A30CD5A9` |
| Linux mobile light | `6BF06F2E3A0D37747CF51F9F089A24E3157E56FAF77323954D3756988E5D3742` |
| Linux tablet dark | `DD08B541654BF699BAC25BE147D4771109EF1E9AEACC97273CE1F0E0FB5AB770` |
| Linux tablet light | `BE233855F554765BE991F875DFF2A421C7D3CD363C2AFBDFAC216E910CA65AC5` |
| Windows desktop dark | `339272D385C49F8BCAB2874CC0E19227C2CD9E4AB6EAD623090BE283354B6089` |
| Windows desktop light | `1838AD648BEB8184A40EF58E6E122A215CA11A9140B803EB045CFBE8561C4F1B` |
| Windows mobile dark | `8960BE35EECD350F65BA9AEC211D3B9BB7CEF2070D378254C5FEC78C8434059A` |
| Windows mobile light | `6B278A888139AF8480A8318265341699D464CA28BEBD6E8AD10F3EA605847853` |
| Windows tablet dark | `B19A26769326E82506160C7F6D89A1D2EB1F99A3F2C7009DC66D22F6C78D7D67` |
| Windows tablet light | `79288861BB34EE935C8ABF3138C27367E862EF4DA1A58B79F55FF32C77308DCE` |

## Next action

WP4.3b was subsequently integrated into local `main` by the history-preserving
merge `92291ed`. Narrow post-merge git-diff, CSS-contract, Flake8, tsc,
Node-syntax, and Vitest gates passed. All 156 screenshot hashes and the protected
Bootstrap and database identities remained unchanged. Nothing was pushed, and
Progression, another WP4.3 page, and WP4.4 had not started. Wait for explicit
direction before beginning another packet.
