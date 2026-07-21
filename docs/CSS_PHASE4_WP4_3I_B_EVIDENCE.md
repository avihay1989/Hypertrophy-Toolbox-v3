# CSS Phase 4 WP4.3i-b Evidence — Workout Plan WPDD Ownership Cleanup

Date: 2026-07-22

Branch: isolated worktree `wt/css-wp4-3i-b`

Base: local `main` at `3e8624c` (the exact WP4.3i-i patch cherry-picked from
`dea3560`; the abandoned i-a commit and its revert are not in main history).

## Scope and runtime topology

The pre-edit packet covered the remainder of the Workout Plan custom-dropdown
cluster, pre-edit lines 468–979 of `pages-workout-plan.css`. After the cleanup,
the scoped `@layer workout-dropdowns` block is lines 468–571, the live global
body-popover owner is lines 573–711, and the next `@layer workout` packet begins
at line 718.

`/workout_plan` is the only route consumer. After JavaScript enhancement it has:

| Runtime hook | Count | Result |
| --- | ---: | --- |
| `select.filter-dropdown` / `.wpdd-button.wpdd-filter` | 12 / 12 | Live native/select and rendered filter pairs |
| `select.exercise-dropdown` / `.wpdd-button.wpdd-exercise` | 1 / 1 | Live native/select and rendered exercise pair |
| `.routine-dropdown` / `.wpdd-button.wpdd-routine` | 0 / 0 | No template or runtime consumer |
| `body > .wpdd-popover` while open | 1 | Live global body-appended popover |
| `#workout .wpdd-popover` | 0 | Structurally impossible: JavaScript appends every popover to `document.body` |

`components.css` owns the rendered wpdd wrapper size, button layout/surface,
hover, disabled, active-filter, and dark-mode states. `a11y.css` owns the global
`focus-visible` ring. The route layer continues to own native-select mechanics,
font context, button gap/transition/truncation/active transform, placeholder,
caret, expanded-caret, reduced motion, and high contrast. The unlayered global
popover block continues to own the body-appended popover and its mobile sheet.

## Browser declaration-owner audit

A temporary Chromium CSSOM audit cleared and restored each candidate rule while
capturing full computed styles. CDP forced pseudo-classes so ownership was
measured rather than inferred from specificity.

Matrix:

- widths: 375, 768, 1280, and 1920 px;
- themes: light and dark;
- states: default, hover, focus-visible, active, filter-active,
  filter-active+hover, disabled, expanded, exercise hover/focus, open popover,
  mobile popover, high contrast, and reduced motion where applicable.

| Candidate family | Browser result | Action / actual owner |
| --- | --- | --- |
| `.wpdd` display and width | Matching live wrappers, zero computed delta | Removed; shared component owns both |
| `.wpdd` position and font context | Computed delta when cleared | Retained |
| `.wpdd-native` | Owns absolute inset, opacity, hit-testing, size, and z-index | Retained unchanged |
| Button surface, sizing, flex, font, and cursor | Matching live buttons, zero computed delta | Removed; shared component owner retained |
| Generic/type hover, disabled, expanded surface, filter-active, exercise, and all dark type rules | Matching states, zero computed delta | Removed; shared component owner retained |
| Route `focus-visible` | Matching forced focus, zero computed delta | Removed; global a11y owner retained |
| Gap, transition, truncation, active transform, placeholder, and caret states | Computed delta when cleared | Retained |
| `.wpdd-routine` family | Zero runtime matches | Removed |
| Scoped `#workout ... .wpdd-popover` family and responsive arm | Zero runtime matches; topology makes matches impossible | Removed; live global owner retained |
| Global body-popover block | Computed deltas at desktop and mobile | Retained unchanged |
| `--wpdd-accent-hover`, `--wpdd-radius` | Definition-only, zero consumers | Removed |

No new token was introduced. Every remaining `--wpdd-*` token has a live
consumer. Native select behavior, popover placement, focus, cascade layers,
reduced motion, and responsive wpdd behavior remain intact.

## Result

Production CSS diff against `3e8624c`:

- `pages-workout-plan.css`: **+1 / -263**, net **-262 lines**
  (6,391 → 6,129 physical lines);
- one responsive media arm removed, leaving 44 route media queries;
- no template, JavaScript, API, schema, calculation, visual baseline, or
  generated Bootstrap change.

Focused Stylelint 16.11.0:

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,420 | 1,371 | **-49** |
| `declaration-property-value-disallowed-list` | 646 | 609 | **-37** |
| `declaration-no-important` | 535 | 530 | **-5** |
| `no-descending-specificity` | 79 | 73 | **-6** |
| `selector-max-specificity` | 78 | 77 | **-1** |
| `selector-max-id` | 75 | 75 | 0 |
| `no-duplicate-selectors` | 7 | 7 | 0 |

No monitored category increased and there were no parse errors.

## Equivalence and gates

Temporary comparison specs were removed after the proof.

| Gate | Result |
| --- | --- |
| CSSOM declaration-owner audit | Passed across the full width/theme/state matrix |
| Exact old-vs-new wpdd comparison | 88/88 computed-style pairs and 88/88 decoded-pixel captures identical |
| Exact old-vs-new table comparison | 12/12 table images identical after deterministic screenshot warm-up (three viewports, two themes, two modes) |
| Cascade contracts | 19/19 passed |
| Focused Workout Plan Chromium | 35/35 passed |
| Focused route visual | 5/6 passed; stored desktop-dark red reproduced at exactly 1,039 pixels |
| Seeded Workout Plan thumbnail matrix | 6/12 stored baselines passed; six stored reds listed below |
| Focused Stylelint | 1,420 → 1,371 warnings; no category increase |
| `git diff --check` | Passed |
| Full pytest | 1,745 passed in 291.43 s |
| `bootstrap.custom.min.css` | Untouched |

The worktree's default `visual` seed intentionally differs from the shipped
catalog and produced two catalog-invariant failures (633 blank primary groups,
454 blank movement patterns) in an initial full-suite run. The isolated,
skip-worktree database was reseeded from main using `copy-current` semantics;
the shipped catalog has 0/0 gaps, and the complete rerun passed 1,745 tests.
No database file is part of this change.

## Stored baseline drift

No baseline was updated. The committed Windows snapshots currently reproduce:

| Snapshot | Pixel mismatch |
| --- | ---: |
| `workout-plan-desktop-dark.png` | 1,039 |
| `plan-desktop-light-advanced.png` | 6,262 |
| `plan-desktop-dark-advanced.png` | 5,618 |
| `plan-mobile-light-simple.png` | 2,365 |
| `plan-mobile-light-advanced.png` | 2,495 |
| `plan-mobile-dark-simple.png` | 2,139 |
| `plan-mobile-dark-advanced.png` | 2,373 |

All four tablet table snapshots and both desktop simple-mode table snapshots
pass. The 88-pair changed-surface comparison and the independent 12-case exact
table comparison both render the pre-edit CSS from `3e8624c` and the edited CSS
on the same deterministic DOM/state. They show zero old-vs-new pixel delta, so
the stored reds are change-independent baseline drift rather than WP4.3i-b
regressions.

## Contract lock and handoff

`test_workout_plan_wpdd_route_ownership_cleanup` locks:

- body-appended popover topology and retention of the live global/mobile owner;
- absence of the impossible scoped popover copy, unused routine/type/state
  surface duplicates, and two zero-consumer tokens;
- retention of shared component and global a11y owners;
- retention of native-select, button transition/truncation/active, caret,
  reduced-motion, and high-contrast mechanics; and
- a consumer for every remaining wpdd token.

The prior i-i cascade contract now expects 44 media queries after removal of the
dormant scoped mobile-popover arm. The next unstarted packet, WP4.3i-c, begins at
the re-established page-header/collapsible-frame cluster around current lines
829–1069. Do not push, open a PR, or begin i-c without owner approval.
