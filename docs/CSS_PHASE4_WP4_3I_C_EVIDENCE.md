# CSS Phase 4 WP4.3i-c Evidence — Workout Plan Header/Frame Ownership Cleanup

Date: 2026-07-22

Branch: isolated worktree `wt/css-wp4-3i-c`

Base: local `main` at `cd497031485a` after integrating WP4.3i-b commit
`57e2480` as `cd497031485a0db48d46ad9adb8b8c4959dcbc73`.

## Scope and runtime topology

The pre-edit packet was re-established as lines 829–1069 of
`static/css/pages-workout-plan.css`, from the page-header cluster through the
collapsible-frame/title dark-mode copies. After cleanup, the packet begins at
line 829 and the next collapse-toggle packet begins at line 934.

`/workout_plan` is the only route consumer. Chromium and the rendered template
confirmed:

| Runtime hook | Count | Result |
| --- | ---: | --- |
| Direct page header | 1 | Live |
| Direct page-header `h1` / `h2` | 1 / 0 | `h2` selector arm was dormant |
| Unified frame container | 1 | Live element; route margin was overridden |
| Collapsible frames / frame headers | 3 / 3 | Live |
| Frame titles / filters title | 2 / 1 | Live |
| Collapse toggles | 3 | Live with `aria-expanded` wiring |

The Workout Plan template gives all three frames the shared `frame-calm-glass`
contract. `components.css` therefore owns their surface, spacing, header
layout, header gleam, title typography, and underline geometry. The route
continues to own the page-header presentation and the explicit blur suppression
needed to avoid input-interaction repaints. The late `theme-dark.css` header
blur is why a dark route override remains necessary.

## Browser declaration-owner audit

A temporary Chromium CSSOM audit removed and restored each candidate
declaration while recording computed styles and absolute geometry. Hover and
focus states were forced in Chromium so declaration ownership was measured,
not inferred from selector specificity.

Matrix:

- widths: 375, 768, 1280, and 1920 px;
- themes: light and dark;
- states: expanded, collapsed, page-header hover, frame-header hover, and
  collapse-toggle focus;
- accessibility modes: reduced motion and forced colors/high contrast.

| Candidate family | Browser result | Action / actual owner |
| --- | --- | --- |
| Page-header positioning, surface, gleam, heading letter spacing/shadow, and underline shadow/transition | Computed or pixel delta when cleared | Retained |
| Page-header margin, alignment, heading typography/color/geometry, underline geometry/background, and hover width | Zero computed delta in every matching state | Removed; Bootstrap/shared rules win |
| Direct page-header `h2` arm | Zero runtime matches | Removed |
| Dark header surface/shadow/border color | Computed delta when cleared | Retained; redundant border width/style removed |
| Unified-container margin | Matching element, zero computed delta | Removed |
| Frame surface, spacing, header layout/surface/gleam, and title typography/underline | Matching elements, zero computed delta | Removed; `components.css` owns them |
| Light frame/title and dark header blur suppression | Computed delta when cleared | Retained |
| Dark frame surface/gleam copies | Matching elements, zero computed delta | Removed; shared owners win |
| Dark title color, radius, and bottom padding | Computed delta when cleared | Retained |

No new token was introduced. The remaining repeated raw values represent
different roles (gleam, border, box shadow, and text shadow), so combining them
would create a false semantic dependency rather than a live reusable token.

## Result

Production CSS diff against `cd49703`:

- `pages-workout-plan.css`: **+12 / -148**, net **-136 lines**;
- no template, JavaScript, API, schema, calculation, visual-baseline, database,
  or generated Bootstrap change.

Focused Stylelint 16.11.0:

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,371 | 1,352 | **-19** |
| `declaration-property-value-disallowed-list` | 609 | 600 | **-9** |
| `declaration-no-important` | 530 | 520 | **-10** |
| `no-descending-specificity` | 73 | 73 | 0 |
| `selector-max-specificity` | 77 | 77 | 0 |
| `selector-max-id` | 75 | 75 | 0 |
| `no-duplicate-selectors` | 7 | 7 | 0 |

No warning category increased and there were no parse errors.

## Equivalence and gates

The deterministic comparison loaded the exact pre-edit CSS from `cd49703` and
the edited CSS into the same Chromium document and state. It compared full
computed-style snapshots plus absolute geometry in 24 contexts. It also
decoded and compared the page header and all three frame-header surfaces at
four widths in both themes (32 image pairs).

| Gate | Result |
| --- | --- |
| CSSOM declaration-owner audit | Passed across the width/theme/state/accessibility matrix |
| Exact old-vs-new comparison | 24/24 computed-style/geometry contexts and 32/32 decoded-pixel pairs identical |
| Cascade contracts | 20/20 passed |
| Focused Workout Plan Chromium | 35/35 passed |
| Focused route visual | 5/6 passed; stored desktop-dark red reproduced at exactly 1,039 pixels |
| Seeded Workout Plan thumbnail matrix | 6/12 stored baselines passed; six stored reds listed below |
| Focused Stylelint | 1,371 → 1,352 warnings; no category increase |
| `git diff --check` | Passed |
| Full pytest | 1,746 passed in 313.22 s |
| `bootstrap.custom.min.css` | Untouched (SHA-256 `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`) |

Before the final full pytest run, the isolated skip-worktree database was
reseeded from main using the repository's literal `copy-current` semantics.
Port 5000 was free, the source WAL contained zero bytes, and the copied file's
SHA-256 matched main. The database remained skip-worktree and is not part of
this change.

## Stored baseline drift

No baseline was updated. The committed Windows snapshots reproduce exactly the
same known drift present before WP4.3i-c:

| Snapshot | Pixel mismatch |
| --- | ---: |
| `workout-plan-desktop-dark.png` | 1,039 |
| `plan-desktop-light-advanced.png` | 6,262 |
| `plan-desktop-dark-advanced.png` | 5,618 |
| `plan-mobile-light-simple.png` | 2,365 |
| `plan-mobile-light-advanced.png` | 2,495 |
| `plan-mobile-dark-simple.png` | 2,139 |
| `plan-mobile-dark-advanced.png` | 2,373 |

All four tablet snapshots and both desktop simple-mode snapshots pass. The
exact OLD/NEW comparison renders the changed header/frame surfaces from both
CSS versions on the same deterministic DOM and finds zero computed, geometry,
or pixel delta. The stored reds are therefore change-independent baseline
drift, not WP4.3i-c regressions.

## Contract lock and handoff

`test_workout_plan_page_header_and_collapsible_frame_ownership_cleanup` locks:

- absence of the browser-proven dormant page-header, frame, pseudo-element,
  dark-copy, and zero-consumer selector arms;
- retention of the shared component owners and the late dark-theme blur owner;
- retention of live page-header positioning/surface/hover behavior;
- retention of the repaint-safe blur suppression and live dark-title fixes;
- runtime frame/title/toggle topology and collapse JavaScript wiring; and
- the decision not to introduce artificial packet-local tokens.

WP4.3i-c is complete on its isolated branch. Do not push, open a PR, integrate
this commit, or begin WP4.3i-d without owner approval.
