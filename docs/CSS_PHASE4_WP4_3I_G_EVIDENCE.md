# CSS Phase 4 WP4.3i-g Evidence — Workout Plan Remaining Dead Defined-Token Fallbacks

Date: 2026-07-24

Branch: in-session on local `main` (serial packet, owner-directed). Base: `main`
at `02279aa` (after WP4.3i-f; origin/main synced to the same commit).

## Scope — completing the non-Bootstrap dead-fallback arc

After i-d (Muscle Selector), i-e (dropdown popover), and i-f (plan table), the only
remaining non-`--bs-*` `var(--token, fallback)` sites in `pages-workout-plan.css`
were seven fallbacks whose tokens are **defined**, plus two whose tokens are
intentionally left live. This packet strips the seven dead ones, completing the
arc.

## Finding — seven dead fallbacks (defined tokens); two kept live

**Stripped (token defined → fallback dead):**

| Site | Token | Where defined |
| --- | --- | --- |
| `font-weight: var(--wp-fw-medium, 500)` (2825) | `--wp-fw-medium` | bundle `@layer workout` (773) |
| `color: var(--wp-text-muted, #6b7280)` (2826) | `--wp-text-muted` | bundle (730 light / 798 dark) |
| `background: var(--wp-border, rgba(0,0,0,0.06))` (2827) | `--wp-border` | bundle (734 / 799 / 2702) |
| `height: var(--input-height-md, 38px)` (4382) | `--input-height-md` | `tokens.css` `:root` (55) + responsive |
| `padding: var(--input-padding-y, 0.375rem) var(--input-padding-x, 0.625rem)` (4383) | `--input-padding-y/-x` | `tokens.css` `:root` |
| `font-size: var(--input-font-size, 0.9rem)` (4384) | `--input-font-size` | `tokens.css` `:root` |

The `--wp-*` tokens are page-scoped custom properties (defined inside
`@layer workout` on the workout-plan container) that cascade to their consumers in
the Routine Tabs section; the `--input-*` sizing tokens are always defined at
`:root` in the global `tokens.css` (loaded before this bundle), with responsive
overrides — so every fallback is dead and removal preserves the rendered value.

**Kept intact (verified NOT dead — must never be stripped):**

- `var(--superset-row-color, var(--superset-color-1))` (3625/3669/3689/3699) —
  `--superset-row-color` is assigned **dynamically inline** per superset row; the
  fallback is the live default. (Its fallback is another token, not a literal.)
- `var(--wpdd-shadow-lg, 0 16px 48px rgba(0,0,0,0.18))` (701) — references an
  **undefined** token, so the fallback is the live value.

## Change

Pure removal: `var(--token, fallback)` → `var(--token)` for the 7 dead sites.

- `pages-workout-plan.css`: **+6 / −6** (6 declarations, 7 fallbacks stripped;
  line 4383 carried two). No token/selector/template/JS/API/schema/calculation/
  visual-baseline/database/generated-Bootstrap change.
- `!important` unchanged (520 → 520). Bundle hex: 219 → **218** (−1; only
  `--wp-text-muted`'s `#6b7280` was a hex fallback).
- **Milestone:** the bundle now has **zero** non-`--bs-*` dead `var()` fallbacks —
  the 5 remaining non-Bootstrap fallbacks are all the two intentionally-live tokens
  above.

## Stylelint (focused bundle)

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,265 | 1,263 | **−2** |
| `declaration-property-value-disallowed-list` | 513 | 511 | **−2** |
| `declaration-no-important` | 520 | 520 | 0 |

(−2 = the one `#6b7280` hex + the one `rgba(0,0,0,0.06)`; the other five fallbacks
were non-color values.) No monitored category increased.

## Gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed (no whitespace errors) |
| Cascade/selector contracts | **24/24** passed (23 + new `test_workout_plan_drops_remaining_dead_defined_token_fallbacks`, which also locks the "no non-`--bs-*` dead fallback remains except the two live tokens" milestone invariant) |
| Vitest | **105/105** (no JS touched) |
| Full pytest | **1,750 passed** (1,749 baseline + the new contract test), exit 0 |
| Focused Workout Plan route visual (`visual.spec.ts -g workout-plan`) | **5 passed + 1 known red** — `workout-plan desktop-dark` at **1,039 px** (ratio 0.01), the exact WP4.0/i-d/i-e/i-f baseline; desktop/tablet/mobile light byte-identical → change is computed-value-inert, the red is pre-existing animated-media drift. |
| Stylelint focused | 1,265 → 1,263 (−2 hardcoded); no other category up |

## Remaining after this packet

`pages-workout-plan.css` now ~**218 hardcoded hex / 520 `!important`**. The clean
dead-fallback arc is COMPLETE. What remains on this page is the harder work:
raw-literal → exact-value token extraction (the bulk of the 218 hex) and the 520
`!important` weighting review — redesign-sized, multi-packet. Then WP4.3j (Workout
Log) and WP4.4 (shared bundles / navbar / theme-dark).
