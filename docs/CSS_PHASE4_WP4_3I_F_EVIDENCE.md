# CSS Phase 4 WP4.3i-f Evidence — Workout Plan Table Dead Global-Token Fallback Removal

Date: 2026-07-24

Branch: in-session on local `main` (serial packet, owner-directed; no isolated
worktree). Base: `main` at `7eb02ad` (after WP4.3i-e; origin/main synced to the
same commit this session).

## Scope — the "Workout Plan Table — 2026 Glass/Neumorphic" section

The table section (`pages-workout-plan.css` lines ~2276–2632) styles the plan
table's selected/active/hover row states with `color-mix()` blends over the global
"Calm Glass 2026" theme tokens (`--accent`, `--surface-1`, `--surface-2`,
`--ink-1`, `--ink-2`) from `tokens.css`.

## Finding — the `#hex` are dead fallbacks (some don't even match the token)

Every flagged `#hex` in this section is only the fallback inside
`var(--token, #hex)`. The tokens are always defined before use:

- `tokens.css` defines them at `:root` (light): `--accent: #4c6ef5`,
  `--surface-1: #f4f6fa`, `--surface-2: #ffffff`, `--ink-1: #0f1220`,
  `--ink-2: #4a5170`; `[data-theme="dark"]` remaps the surface/ink tokens.
- `tokens.css` is a global bundle loaded in `base.html` `<head>` before the route
  bundle (WP4.-1 load-order fix), so `var(--token, #hex)` ≡ `var(--token)`.
- Several fallbacks are **misleading dead code** — they don't match the active
  token: `var(--surface-1, #1a2332)` and `var(--ink-2, #d6ddf5)` are dark-ink/
  dark-surface literals written into rules while the tokens resolve to their real
  (token-driven) values. Removal preserves the current *rendered* value (the
  token); it does not "fix" the apparent author intent (that would be a visual
  change, out of refactor scope).

This mirrors WP4.3i-d (Muscle Selector) and WP4.3i-e (dropdown popover); it
completes the global-token dead-fallback removal for the plan-table section.

## Change

Pure removal: `var(--token, #hex)` → `var(--token)` for the 12 dead fallbacks in
the table section (some declarations carried two, e.g.
`color-mix(in srgb, var(--surface-2, #ffffff) 90%, var(--accent, #4c6ef5) 10%)`).

- `pages-workout-plan.css`: **+9 / −9** (9 declarations, 12 fallbacks stripped;
  3 lines carried two). Residual global-token `#hex` fallback in the section: **0**.
- `!important` unchanged (520 → 520) — only the fallback was removed, the per-rule
  weighting is untouched. Bundle hex: 231 → **219** (−12).
- No token/selector/template/JavaScript/API/schema/calculation/visual-baseline/
  database/generated-Bootstrap change.

Deliberately left intact (verified NOT dead, separate concerns):
`var(--superset-row-color, …)` (3625–3699) is assigned **dynamically inline**
per superset row, so its fallback is live; `var(--wpdd-shadow-lg, …)` (701)
references an **undefined** token, so its fallback is live; Bootstrap
`var(--bs-*, #hex)` fallbacks are idiomatic defaults.

## Stylelint (focused bundle)

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,273 | 1,265 | **−8** |
| `declaration-property-value-disallowed-list` | 521 | 513 | **−8** |
| `declaration-no-important` | 520 | 520 | 0 |

(−8 rather than −12: the three double-fallback `color-mix` declarations each fire
one disallowed-list warning, so clearing both hex from one declaration clears one
warning.) No monitored category increased; no parse/config errors.

## Gates

| Gate | Result |
| --- | --- |
| `git diff --check` | Passed (no whitespace errors) |
| Cascade/selector contracts | **23/23** passed (22 + new `test_workout_plan_table_drops_dead_global_token_fallbacks`) |
| Vitest | **105/105** (no JS touched) |
| Full pytest | **1,749 passed** (1,748 baseline + the new contract test), exit 0 |
| Focused Workout Plan route visual (`visual.spec.ts -g workout-plan`) | **5 passed + 1 known red** — `workout-plan desktop-dark` at **1,039 px** (ratio 0.01), the exact WP4.0/i-d/i-e baseline. Critically, the edited `color-mix()` rules apply in **both** themes, yet desktop/tablet/mobile **light** all pass byte-identical → the change is computed-value-inert and the dark red is pre-existing animated-media drift. |
| Stylelint focused | 1,273 → 1,265 (−8 hardcoded); no other category up |

Text-level fallback removal cannot alter computed values (tokens always defined),
so it is visually inert in both themes; any observed red is the pre-existing WP4.0
`workout-plan desktop-dark` baseline (1,039 px) on untouched animated-media rows.

## Contract lock

`test_workout_plan_table_drops_dead_global_token_fallbacks` locks the five
`tokens.css` definitions, the absence of any global-token `#hex` fallback in the
table section, and the bare-`var()` consumption inside the section's `color-mix()`
blends with `!important` weighting preserved.

## Remaining after this packet

`pages-workout-plan.css` now ~**219 hardcoded hex / 520 `!important`**. Remaining
non-`--bs-*` fallbacks that are genuinely dead and clean-removable next:
`--wp-text-muted` (2826, page-local, Routine Tabs section) plus any page-local
`--wp-*` token fallbacks — a candidate WP4.3i-g. After the dead-fallback arc, the
harder raw-literal → exact-value token-extraction packets remain, then WP4.3j
(Workout Log) and WP4.4 (shared bundles).
