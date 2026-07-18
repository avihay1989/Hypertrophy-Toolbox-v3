# CSS Phase 4 — WP4.2 Evidence

**Worktree:** `wt/wp4-2-shared-frame-dedupe`
**Base:** `158535cdd45550cc1d26e6d2a42180457315a2c2`
**Date:** 2026-07-18

WP4.2 repairs ownership of the frame infrastructure that was copied across the
Workout Plan, Workout Log, Weekly Summary, and Session Summary bundles. It does
not change tokens, APIs, calculations, templates, generated Bootstrap, snapshot
baselines, or databases, and it does not begin WP4.3.

## Ownership and cascade result

The 834-line shared block is now owned once at the end of `components.css` and
is scoped with the zero-specificity direct-container gate
`:where(#workout, .workout-log-page, .summary-frame)`. Dark rules retain their
theme-ancestor shape as `[data-theme='dark'] & ...`. The late Workout Log
surface remains in `pages-workout-log.css`; the summary surface remains in each
summary bundle, including the weekly-only `#isolated_muscles_filter` rule.

The four route bundles no longer carry the common frame block or the misplaced
log/summary copies. Across the five CSS files this is 843 inserted and 4,511
deleted lines, a net reduction of 3,668 hand-authored CSS lines. Runtime
stylesheet order is unchanged: `components.css` still loads before each route
bundle, so route-owned overrides remain later in the cascade.

The regression contract proves single ownership, direct route reachability,
correct dark ancestor nesting, preservation of log/summary route surfaces, and
that Progression contains none of the three ownership hooks.

## Progression regression diagnosis

The first ownership gate used
`:where(html:has(#workout, .workout-log-page, .summary-frame))`. The Progression
DOM has only `.progression-plan-container`, so that selector was false. Browser
inspection found no changed matched rule or computed value. The same winning
declarations remained:

- `pages-progression.css` `.page-header` owned its padding, gradient,
  border-radius, box-shadow, and border after the global bundles;
- the pre-existing `components.css`
  `.progression-plan-container .frame-calm-glass` rule owned the glass surface;
- the pre-existing `components.css` `.table.table-calm` family owned the table
  background, border, radius, shadow, header, cell, stripe, and hover surfaces.

The failure was a Chromium raster/compositor side effect, not a cascade-winner
change. With Playwright's deterministic screenshot masks present, merely adding
the document-wide relational `html:has(...)` rule caused semi-transparent light
Progression surfaces to be recomposited one 8-bit step differently. Of 87,898
raw desktop differing pixels, 87,545 had maximum channel delta 1 and 353 had
delta 2. A diagnostic stylesheet swap isolated the gate: direct scope and the
committed baseline produced the same desktop-light screenshot SHA-256
`F8AA7F6503DD490ED30E31BCAC4ACD464EC9DFCD2C8D9673ED060AD35E2066F`,
while the relational gate produced
`9AE0D27027C5EC921875D90430E8C63BB815DE732486ACCA482BA4807CE078F6`.

Replacing the document-wide relational gate with the direct-container
`:where(...)` gate preserves zero added specificity on intended descendants,
keeps dark theme matching in ancestor form, and removes the unrelated document
from the relational-selector invalidation path. All three Progression light
variants returned to byte-identical baselines.

## Stylelint measurement

Pinned Stylelint `16.11.0` with `postcss-scss` `4.0.9` parsed all 21 sources with
zero parse errors, invalid-option warnings, or errored files.

| Measurement | WP4.1 baseline | WP4.2 final | Delta |
| --- | ---: | ---: | ---: |
| Total warnings | 7,202 | 6,444 | -758 |
| Hardcoded-value warnings | 3,378 | 2,997 | -381 |
| Duplicate selectors | 86 | 50 | -36 |
| Duplicate properties | 8 | 2 | -6 |
| Descending specificity | 783 | 673 | -110 |
| `declaration-no-important` | 2,566 | 2,341 | -225 |
| Lexical `!important` | — | 2,345 | — |
| `selector-max-id` | 191 | 191 | 0 |
| `selector-max-specificity` | 188 | 188 | 0 |

Against the last pre-final measurement supplied in the WP4.2 handoff, the
final direct gate changes total warnings **6,445 → 6,444**, duplicate selectors
**52 → 50**, and descending-specificity warnings **672 → 673**. Duplicate
properties (2), `declaration-no-important` (2,341), lexical `!important`
(2,345), `selector-max-id` (191), and `selector-max-specificity` (188) are
unchanged.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| blocking Flake8 selection | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Node syntax, 63 application files + reporter | 64/64 passed |
| Vitest | 105/105 passed |
| five affected CSS files parsed with PostCSS | 5/5 passed |
| selector/cascade contracts | 12/12 passed |
| CI workflow YAML validation | 2/2 parsed |
| affected functional Chromium set | 84/84 passed |
| exact required CI Chromium list | 407/407 passed |
| full pytest on temporary databases | 1,733 passed + 2 permitted catalog reds |

The two pytest reds are unchanged and exact: 633 null/blank
`primary_muscle_group` rows and 454 null/blank `movement_pattern` rows.
Playwright used `artifacts/e2e/database.e2e.db`; no test used a live database.

## Update-free visual and integrity locks

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Suite | Result |
| --- | --- |
| focused 30 affected variants | 29 passed + the known 1,039-pixel red |
| `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels on all attempts |
| `visual-baseline-thumbnails.spec.ts` | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels on all attempts + 16 not run |

- 156 committed PNGs recomputed with zero manifest mismatches.
- generated Bootstrap SHA-256 remained
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
- target worktree DB SHA-256 remained
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- main live DB SHA-256 remained
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

No snapshot was updated and no push, merge, rebase, or WP4.3 work occurred.

## Next action

WP4.2 was subsequently integrated into local `main` by the history-preserving
merge `d695188`. The narrow post-merge gates passed; nothing was pushed and
WP4.3 had not started. Begin only WP4.3a Backup page dark-mode/token cleanup in
a new visual-seeded isolated worktree.
