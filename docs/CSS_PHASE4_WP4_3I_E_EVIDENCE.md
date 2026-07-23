# CSS Phase 4 WP4.3i-e Evidence — Workout Plan Dropdown Popover Dead-Fallback Removal

Date: 2026-07-24

Branch: in-session on local `main` (serial packet, owner-directed; no isolated
worktree this packet).

Base: local `main` at `a9e1804` (after integrating WP4.3i-d Muscle Selector
dead-fallback removal as merge `a9e1804`; WP4.3i-i `3e8624c`, i-b `cd49703`,
i-c merge `931a23c` already present).

## Scope — the `.wpdd-popover` custom-dropdown component

The "Global Popover Styles" section (`pages-workout-plan.css`, the `.wpdd-popover`
block ~585–686) styles the custom filter/routine dropdown popover that
`static/js/modules/workout-dropdowns.js:84` creates at runtime
(`popover.className = 'wpdd-popover'`). It is a **live** component (not dormant —
WP4.3i-b already removed the dormant `wpdd` duplicate rules; this is the retained
canonical block). It consumes the page-local `--wpdd-*` design tokens.

## Finding — the `#hex`/shadow/font fallbacks are dead

Every `var(--wpdd-*, fallback)` in the block carries a fallback that never
renders, because the `--wpdd-*` tokens are always defined before use:

- **Defined page-local in this same bundle**: `:root` (light, lines 474–491) sets
  `--wpdd-bg: #ffffff`, `--wpdd-surface: #f8f9fa`, `--wpdd-text: #1a1f2e`,
  `--wpdd-muted: #6b7280`, `--wpdd-border: #e5e7eb`, `--wpdd-accent: #4f8cff`,
  `--wpdd-font`, `--wpdd-shadow`, `--wpdd-fs/-gap/-transition`;
  `[data-theme="dark"]` (496–508) remaps bg/surface/text/muted/border/shadow/
  transition. Non-remapped tokens (`--wpdd-accent`, `--wpdd-font`) inherit the
  `:root` value in dark, so all consumed tokens are defined in **both** themes.
- Each fallback exactly equals its **light** token value
  (`var(--wpdd-bg, #ffffff)` ↔ `--wpdd-bg: #ffffff`, etc.), so removal is
  unambiguously exact-value — even more clearly than WP4.3i-d, where several
  fallbacks did not match the active token.
- The bare-`var(--wpdd-*)` convention (no fallback) is **already** the established
  style in the sibling "Enhanced Dropdown Container" section (lines 517–558) of
  the same bundle.

## Change

Pure removal: `var(--wpdd-X, <fallback>)` → `var(--wpdd-X)` for all 15 consumption
sites in the `.wpdd-popover` block. No token definition, selector, `!important`,
template, JavaScript, API, schema, calculation, visual-baseline, database, or
generated Bootstrap change.

- `pages-workout-plan.css`: **+15 / −15** (15 lines modified in place, confined to
  hunks 585–686); **15 dead fallbacks stripped** = 13 `#hex` + 1 `box-shadow`
  ambient-rgba layer (`--wpdd-shadow`) + 1 font stack (`--wpdd-font`); residual
  `var(--wpdd-*, …)` fallbacks: **0**.
- `!important` unchanged (520 → 520). Total hardcoded hex in the bundle:
  244 → **231** (−13).
- Deliberately untouched (separate concern, WP4.3i-d scope boundary): the
  Bootstrap-integrated `var(--bs-*, #hex)` fallbacks elsewhere in the bundle —
  idiomatic Bootstrap defaults, not dead local-token fallbacks.

## Stylelint (focused bundle)

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,284 | 1,273 | **−11** |
| `declaration-property-value-disallowed-list` | 532 | 521 | **−11** |
| `declaration-no-important` | 520 | 520 | 0 |
| `no-descending-specificity` | 73 | 73 | 0 |
| `selector-max-specificity` | 77 | 77 | 0 |
| `selector-max-id` | 75 | 75 | 0 |

(−11 rather than −13: two hex sat in declarations that retain another disallowed
value, e.g. the `box-shadow` still carries an ambient `rgba(0,0,0,…)` layer.) No
monitored category increased; no parse/config errors.

## Gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed (no whitespace errors) |
| Cascade/selector contracts | **22/22** passed (21 + new `test_workout_plan_wpdd_popover_drops_dead_local_token_fallbacks`) |
| Vitest | **105/105** (no JS touched) |
| Full pytest | **1,748 passed** (1,747 baseline + the new contract test), exit 0 |
| Focused Workout Plan route visual (`visual.spec.ts -g workout-plan`) | **5 passed + 1 known red** — `workout-plan desktop-dark` at exactly **1,039 px** (ratio 0.01), identical to the WP4.0 / WP4.3i-d stored baseline; light/tablet/mobile variants byte-identical, both themes update-free. The `.wpdd-popover` is `[hidden]` in static screenshots, so the component never appears in the matrix — the red is pre-existing animated-media drift, not this change. |
| Stylelint focused | 1,284 → 1,273 (−11 hardcoded); no other category up |

This change is a text-level fallback removal that cannot alter computed values
(the `--wpdd-*` tokens are always defined and each fallback matched its token), so
it is visually inert in both themes; any observed visual reds are the pre-existing
WP4.0 known baselines on the untouched animated-media rows.

## Contract lock

`test_workout_plan_wpdd_popover_drops_dead_local_token_fallbacks` locks: the six
core `--wpdd-*` token definitions; the live `.wpdd-popover` selector; absence of
any `var(--wpdd-*, …)` fallback; and the bare-`var()` consumption convention.

## Remaining after this packet

`pages-workout-plan.css` still has ~231 hardcoded hex / 520 `!important` → further
WP4.3i sub-packets remain before the Workout Plan page is clean, then WP4.3j
(Workout Log) and WP4.4 (shared bundles). All WP4.3i-* commits remain on local
`main`, unpushed — the owner runs the push.
