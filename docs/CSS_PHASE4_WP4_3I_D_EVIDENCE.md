# CSS Phase 4 WP4.3i-d Evidence — Workout Plan Muscle Selector Dead-Fallback Removal

Date: 2026-07-22

Branch: isolated worktree `wt/css-wp4-3i-d`

Base: local `main` at `931a23c` (after integrating WP4.3i-c header/frame
ownership as merge `931a23c`; WP4.3i-b `cd49703` and WP4.3i-i `3e8624c` already
present).

## Scope decision — re-scoped from Color-coded Inputs

The packet was first scoped to the Color-coded Inputs cluster
(`#workout[data-page="workout-plan"] .input-fields-group` rep/RIR/weight glass).
An accent-triplet extraction (36 raw literals → 6 page-local `--wp-input-*`
tokens, exact-value, `!important` unchanged) was implemented and measured. It
cleared **zero** Stylelint warnings (`declaration-property-value-disallowed-list`
600 → 600) because that rule fires once per declaration on the mere presence of
`rgba(`/`rgb(`/`#hex`: every glass box-shadow retains ambient
`rgba(0,0,0,…)` / `rgba(255,255,255,…)` layers, so `rgba(var(--accent), α)` stays
flagged. Clearing them would require single-use tokenization of ambient shadow
layers — the "indirection that does not remove a repeat" the WP4.3i-c handoff
explicitly forbids. That edit was reverted (working tree restored to `931a23c`),
and i-d was re-scoped, with owner approval, to the Muscle Selector v3.0 section.

## Finding — the component is already tokenized; the `#hex` are dead fallbacks

The Muscle Selector v3.0 section (`MUSCLE SELECTOR STYLES v3.0` → EOF) consumes
the global "Calm Glass 2026" theme tokens defined in `tokens.css`
(`--accent`, `--surface-0/1/2`, `--ink-1/2/3`, `--success`, `--warning`,
`--danger`). Every flagged `#hex` in this section is only the **fallback** inside
`var(--token, #hex)` — many nested inside `color-mix(in srgb, var(--token, #hex)
…)`. The fallbacks never render, and several do not even match the active token
value (`var(--surface-2, #f5f7fb)` while `--surface-2` is `#ffffff` light /
`#1d2238` dark; `var(--accent, #6d8dff)` in dark rules while `--accent` stays
`#4c6ef5` in dark) — i.e. misleading dead code.

Proof the fallbacks are dead (removal is exact-value):

- All eight referenced tokens are defined in `tokens.css` `:root` (light):
  `--accent: #4c6ef5`, `--surface-1: #f4f6fa`, `--surface-2: #ffffff`,
  `--ink-1: #0f1220`, `--ink-2: #4a5170`, `--success: #10b981`,
  `--warning: #f59e0b`, `--danger: #ef4444`; `[data-theme="dark"]` remaps the
  surface/ink tokens. Non-remapped tokens (`--accent`, `--success`, `--warning`,
  `--danger`) inherit the `:root` value in dark, so all are defined in both
  themes.
- `tokens.css` is a global bundle loaded in `base.html` `<head>` (line 14),
  before the route bundle `pages-workout-plan.css` (`workout_plan.html` line 6);
  WP4.-1 fixed this load order. So `--token` is always the used value and
  `var(--token, #hex)` ≡ `var(--token)`.
- Bare `var(--accent)` / `var(--ink-2)` / `var(--surface-2)` (no fallback) is the
  established convention in sibling bundles (`components.css`, `navbar.css`,
  `theme-dark.css`).

## Change

Pure removal: for the eight Calm-Glass tokens, `var(--token, #hex)` →
`var(--token)`, scoped to the Muscle Selector section only.

- `pages-workout-plan.css`: 80 lines modified in place (**+80 / −80**);
  **85 dead `#hex` fallbacks stripped** (some declarations carried two, e.g.
  `color-mix(in srgb, var(--accent, #4c6ef5) 75%, var(--ink-1, #22283a))`);
  residual local-token fallbacks in the section: **0**.
- No template, JavaScript, API, schema, calculation, visual-baseline, database,
  or generated Bootstrap change. `!important` unchanged (520 → 520).

Deliberately left intact (separate concern, documented scope boundary): the
Bootstrap-integrated `var(--bs-*, #hex)` fallbacks (42 in the section) — those
are idiomatic Bootstrap defaults, not dead local-token fallbacks.

Latent pre-existing observation (NOT changed, refactor invariant): the dark
rules' `var(--accent, #6d8dff)` never rendered `#6d8dff` because `--accent` is
globally defined (`#4c6ef5`) in both themes. Removal preserves the current
rendered value (`#4c6ef5`); it does not "fix" the apparent author intent, which
would be a visual change out of refactor scope.

## Stylelint (pinned 16.11.0, focused bundle)

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,352 | 1,284 | **−68** |
| `declaration-property-value-disallowed-list` | 600 | 532 | **−68** |
| `declaration-no-important` | 520 | 520 | 0 |
| `no-descending-specificity` | 73 | 73 | 0 |
| `selector-max-specificity` | 77 | 77 | 0 |
| `selector-max-id` | 75 | 75 | 0 |
| `no-duplicate-selectors` | 7 | 7 | 0 |

No monitored category increased; no parse/config errors.

## Gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed |
| Cascade/selector contracts | **21/21** passed (20 + new `test_workout_plan_muscle_selector_drops_dead_local_token_fallbacks`) |
| Focused Workout Plan route visual (`visual.spec.ts -g workout-plan`) | **5 passed + 1 known red** — `workout-plan desktop-dark` at exactly **1,039 px** (WP4.0 known red); light/mobile variants byte-identical, both themes update-free |
| Thumbnail matrix clean variants (tablet ×4 both themes + desktop-light/dark-simple) | **6 passed** byte-identical; anchor red `plan-desktop-light-advanced` reproduced at exactly **6,262 px** |
| Vitest | **105/105** (no JS touched) |
| Full pytest | _pending — recorded on completion_ |
| Stylelint focused | 1,352 → 1,284 (`−68` hardcoded); no other category up |

The remaining committed thumbnail reds (`plan-desktop-dark-advanced` 5,618;
`plan-mobile-*` 2,139–2,495) are animated-media baseline drift documented in
WP4.3i-c; the spec's serial mode skips them after the first anchor red. This
change is a text-level fallback removal that cannot alter computed values, and
both observed anchor reds reproduced at their exact stored pixel counts, so the
change is visually inert in both themes. No baseline was updated.

## Contract lock and handoff

`test_workout_plan_muscle_selector_drops_dead_local_token_fallbacks` locks: the
eight token definitions in `tokens.css`; absence of any local-token `#hex`
fallback in the section; the bare-`var()` consumption; the untouched
`var(--bs-*, #hex)` scope boundary; and that no artificial `--wp-ms-*` token was
invented (the fix is pure removal).

WP4.3i-d is complete on its isolated branch. Do not push, open a PR, integrate
this commit, or begin WP4.3i-e without owner approval.
