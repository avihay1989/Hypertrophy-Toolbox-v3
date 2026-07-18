# CSS Phase 4 WP4.3a — Backup token cleanup evidence

Date: 2026-07-18

Branch: `wt/wp4-3-backup-dark-token-cleanup`

Worktree: `D:\development\Hypertrophy-Toolbox-v3-main-wp4-3-backup-dark-token-cleanup`

Base: `e9062bc6050215451a4008ad2f2668b28efb4269` (`main`, zero divergence at start)

## Scope and ownership audit

This packet changes only the Backup route bundle and one cascade regression
contract. `templates/backup.html`, the Backup JavaScript, shared CSS, generated
Bootstrap, APIs, calculations, and databases are unchanged.

Runtime stylesheet order is `tokens.css`, generated Bootstrap, `base.css`,
`layout.css`, `components.css`, `navbar.css`, `a11y.css`, the route bundle,
`motion.css`, then `theme-dark.css`. Backup's root hook remains
`.backup-center-page[data-page="backup-center"]`; `backup-center.js` still locates
that hook and owns the dynamic record/detail states. The route bundle owns the
Backup geometry and feature palette. The later shared theme continues to own
generic dark headings, controls, and tables. The audit found no page-local dark
selector to remove and no exact shared-token equivalent for the retained core
`--backup-*` values.

Before editing, `pages-backup.css` was 497 lines / 10,705 bytes. Its local
namespace defined `--backup-accent`, `--backup-accent-soft`,
`--backup-accent-deep`, `--backup-warm`, `--backup-border`, and
`--backup-shadow`; `--backup-warm` had no consumer. Exact repeated literals were
confined to the route bundle. No Backup-specific selector or token was defined
in another production stylesheet.

## Token decisions

- Removed unused `--backup-warm`.
- Added page-local semantic aliases for exact repeated values only:
  `--backup-accent-wash`, `--backup-copy`, `--backup-surface-raised`,
  `--backup-warning-border`, and `--backup-warning-ink`.
- Reused existing `--backup-border` for the exact restore-result border value.
- Replaced only byte-equivalent literals in page gradients, targeted/record
  rings, inline editor surfaces, warning and restore states, library/record/detail
  copy, the manual badge, and the empty table.
- Retained the feature namespace because no shared token had the same semantics
  and exact value. Near-matches were deliberately left alone.

The final bundle is 501 lines / 10,977 bytes. No selector, specificity, media
query, `!important`, template hook, runtime hook, or load-order change was made.

## Computed-style and cascade proof

A temporary Playwright audit ran against
`artifacts/e2e/database.e2e.db` with `PW_VISUAL_SEED=1`. It captured light and
dark computed styles plus declaration-owner identities before the edit, selected
the first backup to expose dynamic detail content, then compared the same state
after the edit. The post-edit comparison passed exactly.

The 16 representative targets were the page root, heading, intro, summary card
and copy, active pill, save warning, selected record/name/note, detail stat/label/
note, action confirmation/copy, and detail table header. The compared properties
covered background, background color, borders, box shadow, color, radius, and
padding as applicable. Every computed value was identical in both themes, and
every pre-edit declaration-owner identity remained present. This also preserved
the important cross-bundle boundary where late `theme-dark.css` remains the dark
table/heading winner while `pages-backup.css` remains the route-specific owner.

The committed regression contract pins the route-before-theme source order, the
page-local token scope, absence of route-local dark selectors and `!important`,
single token definitions with live consumers, removal of the unused token, and
the template/JavaScript root hooks.

## Stylelint measurement

Pinned Stylelint `16.11.0` with `postcss-scss` `4.0.9` parsed all 21 measured
sources with zero parse errors, invalid-option warnings, or errored files.

| Measurement | WP4.2 / pre-edit | WP4.3a final | Delta |
| --- | ---: | ---: | ---: |
| Focused Backup warnings | 41 | 32 | -9 |
| Total warnings | 6,444 | 6,435 | -9 |
| Hardcoded-value warnings | 2,997 | 2,988 | -9 |
| Duplicate selectors | 50 | 50 | 0 |
| Duplicate properties | 2 | 2 | 0 |
| Descending specificity | 673 | 673 | 0 |
| `declaration-no-important` | 2,341 | 2,341 | 0 |
| Lexical `!important` | 2,345 | 2,345 | 0 |
| `selector-max-id` | 191 | 191 | 0 |
| `selector-max-specificity` | 188 | 188 | 0 |
| Property-unknown warnings | 2 | 2 | 0 |

All 32 focused warnings remain hardcoded-value warnings. No monitored cascade or
specificity category increased.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| Backup PostCSS parse | 1/1 passed |
| selector/cascade + visual contracts | 13/13 passed |
| browser computed-style/owner comparison | passed in light and dark |
| blocking Flake8 selection | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Node syntax, 63 application files + reporter | 64/64 passed |
| Vitest | 105/105 passed |
| CI workflow YAML validation | 2/2 parsed |
| focused Backup Chromium | 20/20 passed |
| exact required CI Chromium list | 407/407 passed |
| full pytest on temporary databases | 1,734 passed + 2 permitted catalog reds |

The extra Python pass relative to WP4.2 is the new cascade contract. The only
pytest failures were the unchanged visual-seed catalog invariants: 633 null/blank
`primary_muscle_group` rows and 454 null/blank `movement_pattern` rows.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Backup variants | 6/6 passed update-free |
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

The twelve committed Backup images also remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `CF61F9A89A51BB5A327B983C0E05BD36E63AD90C27548BF003A4D17ABA5A48BD` |
| Linux desktop light | `DE79FF2FA1675DBC54A05326471910612E71FA020B547EFC9259BB656524E74E` |
| Linux mobile dark | `E70BA056315C3167186C5BD9C60C74080ED9A69E6D639EFEB1E623580FF30F1E` |
| Linux mobile light | `1E3F54AD91D45FE56D0613964993DD7D987953D9580AB0C2FE75E2C07F9FA971` |
| Linux tablet dark | `31DBA6DDE11E1B57F81B46F41A338BA06287C403EDA3D537152F9A2DB53CF382` |
| Linux tablet light | `A94E984DC68E3A93EE86EA29D126E171D3ED84488736B3C39995775C24AB705D` |
| Windows desktop dark | `FD14065CC0F6A0AAD578EE472D5C5482A05F73431DBC512B04638A0334B18F98` |
| Windows desktop light | `BD5D59CCCB0E23350BB64BA53DFA9939D7FC18261DDF0611354F9EF28396AE8F` |
| Windows mobile dark | `45A4EE74E751438D4BBFE4EF46630435BD3669B33B5E203483E1332E230A1F7D` |
| Windows mobile light | `B9A7535F51645E92DB88142B797486A524C176BA8939573729AEE54CE351BDD7` |
| Windows tablet dark | `A0664ECAAE43AA92591185F84EB3246C7973A71E10EC83B850B8F65B6D3A0353` |
| Windows tablet light | `EE629FC9CA477F44EDDE9C7E89980E5331CB0B26A653B756F712F9A2CD0B5F28` |

## Next action

WP4.3a was subsequently integrated into local `main` by the history-preserving
merge `dc607fe`. Narrow post-merge git-diff, CSS-contract, Flake8, tsc,
Node-syntax, and Vitest gates passed. All 156 screenshot hashes and the protected
Bootstrap and database identities remained unchanged. Nothing was pushed and
WP4.3b had not started. Begin only the Body Composition page packet in a new
visual-seeded isolated worktree.
