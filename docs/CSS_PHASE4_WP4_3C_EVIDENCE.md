# CSS Phase 4 WP4.3c — Progression dark/token cleanup evidence

Date: 2026-07-18

Branch: `wt/wp4-3-progression-dark-token-cleanup`

Worktree: `D:\development\Hypertrophy-Toolbox-v3-main-wp4-3-progression-dark-token-cleanup`

Base: `efe7ab5855d811ef6502894acf5855697ed73a2b` (`main`, zero divergence at start)

## Isolation preflight

Local `main` was clean at the base SHA (ahead of `origin/main` by its existing 20
local commits). The new worktree was clean with `0/0` divergence from `main`.
`git worktree list --porcelain` recorded all eight registered worktrees, including
this new branch/path; no existing worktree was modified or cleaned. After the
packet, local `main` remains at the same SHA and the isolated branch is exactly one
commit ahead.

Protected identities were captured independently because checkout line endings can
give generated Bootstrap a different clean-worktree byte hash. Main Bootstrap was
`24CC9F443D2D0933F1C89DC7203B0618063C4706ADE17627F0A03934C73D75D4`;
the isolated worktree Bootstrap was
`0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
The main live DB, isolated visual-seeded DB, fixture DB, and the 156-file screenshot
manifest were hashed before any test ran and again after all gates.

## Scope and ownership audit

This packet changes only the Progression route bundle and one cascade regression
contract. The template, Progression JavaScript, shared CSS, `theme-dark.css`,
generated Bootstrap, APIs, calculations, schemas, and databases are unchanged.
No other WP4.3 page and no WP4.4 work is included.

The measured runtime stylesheet order is Google Fonts, `tokens.css`, generated
Bootstrap, Font Awesome, `base.css`, `layout.css`, `components.css`, `navbar.css`,
`a11y.css`, Flatpickr, `pages-progression.css`, `motion.css`, then
`theme-dark.css`. Flatpickr therefore remains immediately before the route bundle,
and the route remains before the late shared motion/theme boundary.

The browser audit exercised real suggestion cards, an injected goal-status badge,
the fatigue advisory subtree, the goal modal, and an open Flatpickr calendar.
Shared `components.css` owns generic headings, card titles, dark suggestion-card
copy, and table colors. The Progression bundle owns its route geometry, goal badges,
fatigue presentation, modal interaction geometry, and Flatpickr dark skin.

Before editing, `pages-progression.css` was 341 lines / 8,492 bytes. Its focused
Stylelint result was 65 warnings: 48 hardcoded values, 16
`declaration-no-important`, and one descending-specificity warning.

## Token and dark-mode decisions

- Added page-local `--progression-accent`, `--progression-badge-ink`,
  `--progression-badge-surface`, `--progression-copy-muted`,
  `--progression-copy-muted-dark`, `--progression-success`, and
  `--progression-success-dark` tokens for exact repeated expressions only.
- Added four Flatpickr-subtree tokens for the exact repeated dark calendar accent,
  border, ink, and surface literals. They remain scoped to the existing dark
  `.flatpickr-calendar` owner rather than a document root.
- Kept distinct light/dark semantic tokens where the fallback values differ. No
  near-match was folded into a shared value.
- Removed the route dark suggestion-card copy override after declaration-owner
  evidence showed that the shared important component rule wins.
- Removed the dark fatigue headline and advisory overrides because the global
  `--ink-*` dark remaps already produce the same computed colors.
- Removed only the redundant dark fatigue-chip `color`; its live dark background
  and border mixes remain in the same selector.
- Retained both dark goal-badge rules and all dark Flatpickr rules because browser
  evidence showed that they remain live.

The final bundle is 341 lines / 9,196 bytes. Apart from the browser-proven dead
or redundant dark rules above, no selector was removed or rewritten; no runtime
hook, breakpoint, geometry declaration, specificity, behavior, or stylesheet-order
change was made.
No document-wide `:has()` scope was introduced; WP4.2 established that such a
scope can alter Progression mask compositing without changing computed winners.

## Computed-style and cascade proof

Temporary Playwright audits ran the pre-edit base and the final worktree against
independent disposable visual-fixture database copies. They captured 33 targets
in both light and dark: route/root geometry, heading and selector frames,
suggestion card structure and copy, goal controls and badge, table heading, the
complete fatigue subtree, modal/dialog/content/input geometry, and the open
Flatpickr calendar including month, weekday, day-state, and navigation-icon
surfaces.

All rendered computed values were identical before and after in both themes.
Stylesheet order, target counts, and hook counts were also identical. Declaration
inspection confirmed the shared/route ownership boundaries described above. The
committed contract pins those boundaries, page-local token scope and consumers,
the absence of the dead/redundant dark declarations, all live dark owners, both
existing responsive breakpoints, stylesheet order, and template/JavaScript hooks.

## Stylelint measurement

Pinned Stylelint `16.11.0` with `postcss-scss` `4.0.9` parsed all 21 measured
sources with zero parse errors, invalid-option warnings, or errored files.

| Measurement | WP4.3b / pre-edit | WP4.3c final | Delta |
| --- | ---: | ---: | ---: |
| Focused Progression warnings | 65 | 41 | -24 |
| Focused hardcoded-value warnings | 48 | 24 | -24 |
| Total warnings | 6,428 | 6,404 | -24 |
| Hardcoded-value warnings | 2,981 | 2,957 | -24 |
| Duplicate selectors | 50 | 50 | 0 |
| Duplicate properties | 2 | 2 | 0 |
| Descending specificity | 673 | 673 | 0 |
| `declaration-no-important` | 2,341 | 2,341 | 0 |
| Lexical `!important` | 2,345 | 2,345 | 0 |
| `selector-max-id` | 191 | 191 | 0 |
| `selector-max-specificity` | 188 | 188 | 0 |
| Property-unknown warnings | 2 | 2 | 0 |

The remaining 41 focused warnings are 24 hardcoded-value, 16 important, and one
descending-specificity warning. No monitored cascade or specificity category
increased.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| Progression PostCSS parse | 1/1 passed |
| selector/cascade + visual contracts | 15/15 passed |
| browser rendered computed-style comparison | 33 targets/theme, zero value deltas |
| blocking Flake8 selection | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Node syntax, 63 application files + reporter | 64/64 passed |
| Vitest | 105/105 passed |
| CI workflow YAML validation | 2/2 parsed |
| focused Progression Chromium | 26/26 passed |
| exact required CI Chromium list | 205/205 + 202/202 = 407/407 passed |
| full pytest in a 1,530-file tracked sandbox with its disposable DB | 1,736 passed + 2 permitted catalog reds |

The additional Python pass relative to WP4.3b is the new cascade contract. The
only pytest failures were the unchanged visual-seed catalog invariants: 633
null/blank `primary_muscle_group` rows and 454 null/blank `movement_pattern` rows.
The exact CI list ran in its canonical two-shard topology, with a freshly seeded
throwaway database per shard.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Windows Progression variants | 6/6 passed update-free |
| complete `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels on all attempts |
| complete thumbnail suite | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels on all attempts + 16 not run |

## Integrity locks

- Screenshot manifest: **156 files, 0 mismatches**, aggregate SHA-256
  `9558DA3D823DF8136874C3FE1722B45D16815640DAE580166D73DFD08AA3A977`.
- Generated Bootstrap SHA-256: main checkout
  `24CC9F443D2D0933F1C89DC7203B0618063C4706ADE17627F0A03934C73D75D4`;
  isolated worktree
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
- Target worktree and visual-fixture DB SHA-256:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- Main live DB SHA-256:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

The twelve committed Progression images also remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `9A741A4E7CCD73342237675CA2E6F3263816C615C52C7AE89D92BF739B14D17D` |
| Linux desktop light | `89E28DF99759A469F1885D3485D7B8F686152F8941BB6DAE8CAA8C2DE8C0F657` |
| Linux mobile dark | `9DEE8A1709E9146E56259C6DA4432EE65F2A95C69CFB241338819ED3282C5148` |
| Linux mobile light | `E3217CF57795CB0EBC7D6A2B1DED9B29BC9F0F702BC8A608BE681C27DBA62678` |
| Linux tablet dark | `42EF9407A160617D866EF0A9D311193FB0379F14EB92D83952670F5BB73A5740` |
| Linux tablet light | `6D2A118B2C0747FF6A4AB4B4AC06FB47B7547249C3194763784FFEAA8D7BE438` |
| Windows desktop dark | `7784D77A07D4F0731158B04446748B0BC565E6683B6BC14C125948D3D2286718` |
| Windows desktop light | `F8AA7F4F37C00CB951B8D35EFE3BD736672337637BB93367EC501AFA8612066F` |
| Windows mobile dark | `3332C0FB8DD98124DBF156AE18974F0478607493AC96E03DAD2A45696D2E6EED` |
| Windows mobile light | `DB3536C401C90FF7A046DC8FCBFDA0BAA154DE12C31980D7674F66ED5337D752` |
| Windows tablet dark | `60239B5BEAFFD9B8F0D17CA5D84146A17DCD3B0AA30DEAD7D705AC94471F5388` |
| Windows tablet light | `5F3966CED177E911BFEA169B481BC9A657D42D1B190A7B6404C379A01D72F0EA` |

## Next action

WP4.3c was subsequently integrated into local `main` by the history-preserving
merge `e7feffa`. Narrow post-merge git-diff, CSS-contract, PostCSS, Flake8, tsc,
Node-syntax, and Vitest gates passed. All 156 screenshot hashes and the protected
Bootstrap and database identities remained unchanged. Nothing was pushed, no
snapshot was changed, and Volume Splitter, another WP4.3 page, and WP4.4 have not
started. Wait for explicit direction before beginning another packet.
