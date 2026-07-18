# CSS Phase 4 — WP4.1 Evidence

**Worktree:** `wt/wp4-1-token-vocabulary`
**Base:** `9ee763889e1e021d6cd1fe8d8782dccb4cb40d52`
**Date:** 2026-07-17

WP4.1 consolidates the token vocabulary without changing any computed value or
page appearance. It does not delete selectors, move shared-frame declarations,
change specificity, remove `!important`, or begin WP4.2.

## Inventory and alias decision

The pre-change inventory covers 18 hand-authored runtime CSS files and three
SCSS sources, excluding generated Bootstrap CSS. It found 30,768 lines,
815 custom-property definition occurrences (338 unique), 2,270 `var()` uses,
2,263 hex literals, 2,608 RGB/HSL function calls, 7,086 dimensions or
percentages, 262 durations, and 2,570 `!important` occurrences.

The complete namespace counts, hardcoded-value ranking, and frozen mapping are
in [`CSS_PHASE4_WP4_1_TOKEN_INVENTORY.md`](CSS_PHASE4_WP4_1_TOKEN_INVENTORY.md).
The approved mapping is deliberately narrow:

- `--s-*` remains the fixed component-spacing scale.
- new `--layout-space-*` names receive the exact former responsive
  `--space-*` values at root and all seven viewport ranges;
  `--space-*` remains as a deprecated compatibility alias.
- `--wl-success`, `--wl-warning`, `--wl-danger`, and `--wl-duration-fast`
  alias byte-equivalent shared status/duration tokens.
- `--nav-gap` and `--nav-padding-y` alias the byte-equivalent `--s-3`.
- `--bc-*`, `--backup-*`, `--volume-*`, and `--fatigue-*` remain feature
  namespaces. Rem/pixel near-matches, near-duration matches, feature palettes,
  and unused definitions are not consolidated or deleted.

No `--space-*` consumer is migrated. Future consumers must choose fixed
component spacing or responsive layout spacing by intent.

## Stylelint measurement

`stylelint` `16.11.0` and `postcss-scss` `4.0.9` are exact dev-dependency
pins. The configuration measures hardcoded colors, `!important`, duplicate
declarations/selectors, descending specificity, selector ceilings, unknown
properties, and invalid hex. All findings are warnings.

The committed pre-change baseline is
[`CSS_PHASE4_WP4_1_STYLELINT_BASELINE.json`](CSS_PHASE4_WP4_1_STYLELINT_BASELINE.json):

| Measurement | Pre-change | Post-alias |
| --- | ---: | ---: |
| Files parsed | 21 | 21 |
| Files with warnings | 20 | 20 |
| Total warnings | 7,202 | 7,199 |
| Hardcoded-value warnings | 3,378 | 3,375 |
| `!important` warnings | 2,566 | 2,566 |
| Parse errors | 0 | 0 |
| Invalid-option warnings | 0 | 0 |
| Errored files | 0 | 0 |

The three-warning reduction is exactly the three welcome status literals now
aliased to shared tokens. No debt was hidden or bulk-fixed.

CI adds a new `css-stylelint-measure` job named
`CSS Stylelint Measurement (non-required)`. It is job-level
`continue-on-error`, captures Stylelint's raw JSON through its portable
`--output-file` option, generates a compact delta summary, and uploads the
measurement artifact. No existing job ID, job name, or required-check context
was renamed.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| blocking flake8 selection | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Node syntax, 63 application files + reporter | passed |
| Vitest | 105 passed |
| selector/cascade contracts | 10 passed |
| affected functional Chromium set | 47 passed |
| exact required CI Chromium list | 407 passed |
| full pytest on temporary databases | 1,731 passed + 2 permitted catalog reds |

The two pytest reds are unchanged and exact: 633 null/blank
`primary_muscle_group` rows and 454 null/blank `movement_pattern` rows. No test
used a live `data/database.db`; Playwright used
`artifacts/e2e/database.e2e.db`.

## Update-free Windows visual comparison

Every visual command used `PW_VISUAL_SEED=1`, and no command used
`--update-snapshots`.

| Suite | Result | WP4.0 comparison |
| --- | --- | --- |
| `visual.spec.ts` | 59 passed + 1 known red | `workout-plan desktop dark` was exactly 1,039 differing pixels on the initial attempt and both retries. |
| `visual-baseline-thumbnails.spec.ts` | 1 passed + 1 known red + 16 not run | `plan-desktop-light-advanced` was exactly 6,262 differing pixels on the initial attempt and both retries. |

The diff images were inspected. The first red is confined to the navbar
signature plus six exercise video/control frames. The second is confined to
the transient skip-link/signature frame plus the same six video/control
frames. Counts and locations exactly reproduce
[`CSS_PHASE4_WP4_0_EVIDENCE.md`](CSS_PHASE4_WP4_0_EVIDENCE.md); there is no
layout, token, or cascade drift. The existing pinned-Linux WP4.0 evidence
remains authoritative, so no push was made to dispatch another Linux run.

## Screenshot, artifact, and database locks

- 156 committed PNGs recomputed; comparison with
  `CSS_PHASE4_WP4_0_SCREENSHOT_MANIFEST.sha256` has **zero changes**
  (78 Windows + 78 Linux).
- generated `bootstrap.custom.min.css` stayed byte-identical:
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
- main live DB stayed byte-identical:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.
- completed Phase-4 worktree DB and the WP4.1 visual seed both stayed
  byte-identical:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.

WPB.4 remains unimplemented: preserve one synthetic `Unassigned` session,
leave denominator behavior unresolved, and require intentional review of the
exact golden delta before any behavior change.

## Next action

Review the WP4.1 commit, then integrate it into local `main` with a
history-preserving merge and re-run the narrow integration gates. Do not push
or start WP4.2 until that local integration is clean.
