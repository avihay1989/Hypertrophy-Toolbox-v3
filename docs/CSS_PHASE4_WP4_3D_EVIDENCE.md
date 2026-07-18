# CSS Phase 4 WP4.3d Evidence — Volume Splitter Dark/Token Cleanup

Date: 2026-07-18

Branch: `wt/wp4-3-volume-splitter-dark-token-cleanup`

Base: local `main` at `7a454e599896f228bc16ebdc5563231d8de13f1d`

## Scope and isolation

WP4.3d changed only the Volume Splitter route bundle in production:
`static/css/pages-volume-splitter.css`. The companion change in
`tests/test_css_cascade_contracts.py` pins the preserved cascade contract; this
evidence file and the canonical handover documents are the only documentation
changes. No template, JavaScript, API, schema, calculation, shared CSS,
`theme-dark.css`, another page, or WP4.4 work is included.

The packet was created with:

```powershell
scripts/new-worktree.ps1 -Task wp4-3-volume-splitter-dark-token-cleanup -Seed visual
```

The isolated worktree started clean with `main...HEAD = 0 0`. Main remained at
the exact base SHA and clean throughout. The worktree's seeded database and the
tracked visual fixture both have SHA-256
`6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.

## Ownership audit and changes

The browser loaded the relevant stylesheets in this order:

1. `tokens.css`
2. generated Bootstrap
3. `base.css`
4. `layout.css`
5. `components.css`
6. `navbar.css`
7. `a11y.css`
8. `pages-volume-splitter.css`
9. `motion.css`
10. `theme-dark.css`

The production edit introduces exact-value, page-local semantic tokens for the
three status colors, positive/optimal accents, heading ink, the soft header
accent, and the existing repeated dark surface/ink/border/focus vocabulary.
Only exact repeated expressions were replaced; no near-match was normalized.

The rendered declaration-owner audit proved these route declarations dead or
redundant and removed only them:

- the generic dark `.suggestion-card` background, because every runtime card has
  a `data-type` and its later type-specific dark rule owns that background;
- the standalone dark history background, because the shared important
  component background wins;
- the dark results-section background, because it was not the winning
  declaration;
- the dark results-table heading background/color and body-cell color, because
  shared component rules own those properties.

The live route-owned results borders, cell backgrounds, shadows, focus styles,
and type-specific suggestion-card rules remain. The shared component owners
remain untouched. No document-wide `:has()` selector was introduced.

The runtime probe exercised advanced mode, four slider values, calculation (32
rows spanning all four statuses), all five suggestion cards, save/activate
history, and the delete modal in both themes. It inspected 39 dynamic targets
per theme. Thirty-seven stable targets had identical selectors, classes,
computed values, inline styles, and winning declarations before/after. The two
animated controls showed only transition-frame interpolation during sampling;
their hooks and final CSS declarations are unchanged.

## Contract lock

`test_volume_splitter_tokens_preserve_runtime_ownership_and_dark_winners` pins:

- stylesheet load order and the absence of document-wide `html:has()`;
- the two existing page-local token scopes and their consumers;
- shared ownership for the dead dark properties removed above;
- retention of every live dark results property;
- all five existing responsive breakpoints;
- Volume Splitter template and JavaScript runtime hooks.

The combined selector/cascade and visual-selector contract gate is now 16/16.

## Stylelint measurement

Pinned Stylelint `16.11.0` with `postcss-scss` `4.0.9` parsed all measured
sources with zero parse errors, invalid-option warnings, or errored files.

| Measurement | WP4.3c / pre-edit | WP4.3d final | Delta |
| --- | ---: | ---: | ---: |
| Focused Volume Splitter warnings | 158 | 118 | -40 |
| Focused hardcoded-value warnings | 120 | 84 | -36 |
| Focused `declaration-no-important` | 24 | 20 | -4 |
| Focused descending specificity | 10 | 10 | 0 |
| Focused duplicate selectors | 4 | 4 | 0 |
| Total warnings | 6,404 | 6,364 | -40 |
| Hardcoded-value warnings | 2,957 | 2,921 | -36 |
| Duplicate selectors | 50 | 50 | 0 |
| Duplicate properties | 2 | 2 | 0 |
| Descending specificity | 673 | 673 | 0 |
| `declaration-no-important` | 2,341 | 2,337 | -4 |
| Lexical `!important` | 2,345 | 2,341 | -4 |
| `selector-max-id` | 191 | 191 | 0 |
| `selector-max-specificity` | 188 | 188 | 0 |
| Property-unknown warnings | 2 | 2 | 0 |

No monitored duplicate, specificity, or parse category increased.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| Volume Splitter PostCSS parse | 1/1 passed |
| selector/cascade + visual contracts | 16/16 passed |
| browser rendered comparison | 37 stable targets/theme, zero deltas |
| blocking Flake8 selection | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Node syntax, 63 application files + reporter | 64/64 passed |
| Vitest | 105/105 passed |
| CI workflow YAML validation | 2/2 parsed |
| focused Volume Splitter Chromium | 27/27 passed |
| exact required CI Chromium list | 205/205 + 202/202 = 407/407 passed |
| tracked-file pytest sandbox | 1,737 passed + 2 permitted catalog reds |

The additional Python pass relative to WP4.3c is the new cascade contract. The
only pytest failures were the unchanged visual-seed catalog invariants: 633
null/blank `primary_muscle_group` rows and 454 null/blank `movement_pattern`
rows. The exact CI list used its canonical two-shard topology and a freshly
seeded throwaway database per shard.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Windows Volume Splitter variants | 6/6 passed update-free |
| complete `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels on the initial attempt and both retries |
| complete thumbnail suite | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels on the initial attempt and both retries + 16 not run |

## Integrity locks

- Screenshot manifest: **156 files, 0 mismatches** against main; the established
  aggregate SHA-256 remains
  `9558DA3D823DF8136874C3FE1722B45D16815640DAE580166D73DFD08AA3A977`.
- Generated Bootstrap SHA-256: main checkout
  `24CC9F443D2D0933F1C89DC7203B0618063C4706ADE17627F0A03934C73D75D4`;
  isolated worktree
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
- Target worktree and visual-fixture DB SHA-256:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- Main live DB SHA-256:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

The twelve committed Volume Splitter images remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `1E767DBE4D255B5C007F980F947FB25C2B95737F811BCDCAA4F545400E80261C` |
| Linux desktop light | `A38A8F70BA5C033A86FD16499BEA659256FBD5D1FDE12B2187A41429EC911942` |
| Linux mobile dark | `4DAABDA19343F848E26AE991039A8C1BAC9485EE3F77E7A7979931A59F2DE9A0` |
| Linux mobile light | `3F95BCB5BD1B76C6F2E2944BA8F2798326C158B4242EB21807705A34C10092A1` |
| Linux tablet dark | `5F1FAC97E409CCC3BF06D9B6BED5FEA4A296CA7210109D8CAD2EB37C06118AAB` |
| Linux tablet light | `65E95A72DCC4DF3C1CC19EE33A0FE5CED56516A1B8576F8F693A15CCC1D80A12` |
| Windows desktop dark | `CB6E6F53EF4FFDF6757D7EB5383461ED9EFD46F8A93B6BF367B9A0321EA5BF1B` |
| Windows desktop light | `38E55EEA5229A3DFFFEE50F9E3DFE4E433C73C0F9A3BD64C30C25E5B191A0999` |
| Windows mobile dark | `E0FA2561CA72AA4622A3294E6010418247A32FB8A2688A302DFF7B8D5F33B17A` |
| Windows mobile light | `D9A856CA5ABA66C0264880CD5D690A576E8CDA9885C7A77496205FCAEA04A9CC` |
| Windows tablet dark | `E6BAE24FC2A3E39421B2BA1DD94E2BFC90BA9393ABB9E4EE434203C9D71ECE28` |
| Windows tablet light | `D31077A4184C8E97AFA2180AD5A4B02A7FEAA89AC61CB37420D0014D20D0C326` |

## Next action

WP4.3d was integrated into local `main` by history-preserving merge `40bc09f`.
The narrow post-merge git-diff, contract, PostCSS, Flake8, tsc, Node-syntax, and
Vitest gates passed, and the protected identities remained unchanged. Nothing
was pushed; the worktree/branch remain available for review. Do not begin
Welcome, another WP4.3 page, or WP4.4 without explicit direction.
