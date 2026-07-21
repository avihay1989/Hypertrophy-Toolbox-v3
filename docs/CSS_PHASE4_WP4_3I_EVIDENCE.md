# CSS Phase 4 WP4.3i-i Evidence — Workout Plan Dormant Filter Cluster Removal

Date: 2026-07-22

Branch: isolated worktree `worktree-agent-a088ab8d7abc314f1`

Base: local `main` at `e34d254` (WP4.3h User Profile integrated).

## Decision and scope

The original WP4.3i-a commit (`64780a8`) tokenized eleven repeated dark values
inside the top-level "2026 Glass Style" filter cluster. Its browser sentinel
sweep then established that none of those tokenized values controlled a rendered
element. Owner direction was therefore to hold i-a, audit the whole cluster, and
remove browser-proven dead CSS instead of formalizing tokens for CSS that a later
packet would delete.

The agent-local destructive-command guard correctly blocked a requested hard
reset. Commit `354fa4d` safely reverted i-a instead, restoring a tree identical
to `e34d254` while keeping the abandoned commit recoverable in branch history.
This packet starts from that clean tree and supersedes i-a with a deletion-only
WP4.3i-i result. Nothing is pushed and no PR is opened.

Audit scope was the full pre-edit top-level filter region through the legacy
toggle/hierarchical dropdown rules (pre-edit lines 1–946), including:

- the light filter/routine/exercise glass surfaces and active/focus/hover states;
- filter-form layout at all seven documented responsive ranges;
- the dark filter frame, label, dropdown, active, focus, and hover rules;
- the Simple/Advanced `.filter-view-toggle` family and stale `.page-header`
  context;
- the immediately adjacent legacy routine/exercise/filter surface duplicates.

The later `@layer workout-dropdowns` and `@layer workout` systems, shared
components, templates, JavaScript, and generated Bootstrap bundle are unchanged.

## Runtime topology

`/workout_plan` is the only route that loads `pages-workout-plan.css`.
Post-initialization browser counts were:

| Runtime hook | Count | Result |
| --- | ---: | --- |
| `.filters-section` | 1 | Live frame/layout consumer |
| `select.filter-dropdown` | 12 | All receive `.wpdd-native`; hidden behind generated buttons |
| `select.exercise-dropdown` | 1 | Receives `.wpdd-native`; hidden behind generated button |
| `.wpdd-button.wpdd-filter` | 12 | Live rendered filter controls |
| `.wpdd-button.wpdd-exercise` | 1 | Live rendered exercise control |
| `.routine-dropdown` | 0 | No template/runtime consumer |
| `.filter-view-toggle` | 0 | No template/runtime consumer; legacy factory has no in-repo invocation |

The actual surfaces are owned by scoped rules under `@layer
workout-dropdowns`, the `#workout[data-page="workout-plan"]` rules under
`@layer workout`, and the shared `frame-calm-glass` / `input-calm-inset`
components. The route's current naming-mode UI is not the retired
`.filter-view-toggle` component.

## Declaration-owner audit

The audit used Chromium CSSOM removal probes. For every candidate rule, it
captured full computed styles for all matching normal/pseudo elements, cleared
that rule's declarations in-browser, captured again, and restored the exact
rule. Pseudo-classes were forced through the Chrome DevTools protocol, rather
than inferred from selector specificity.

Matrix:

- themes: light and dark;
- widths: 1280, 1366, 1536, 1600, 1920, 2560, and 2561 px;
- native states: default, frame hover, filter hover/focus/active,
  active+hover, active+focus, disabled, exercise hover/focus/filter-applied;
- rendered wpdd states in the before/after proof: default, hover, focus,
  active, active+hover, disabled for filter and hover/focus for exercise.

The rule-level matrix covered 154 theme/width/native-state contexts. The
post-edit before/after matrix covered 252 theme/width/state comparisons and 126
pixel captures.

| Candidate family | Browser result | Final action / actual owner |
| --- | --- | --- |
| Initial `.filters-section` position/z-index/isolation/contain | Matching frame, zero computed delta | Removed; later scoped frame/shared component rules own it |
| Legacy `.dropdown-menu` z-index arm | Zero runtime matches | Removed |
| Base `.filter-dropdown` glass surface | Only `position` changed when rule was cleared | Removed dead background/border/radius/shadow/transition; retained `position: relative` |
| `.filter-dropdown::before` (light and dark) | Owns computed pseudo properties/background | Retained unchanged |
| Filter hover/focus/active glass declarations | Matched under forced states, zero computed delta | Removed; scoped input/wpdd rules own rendered state |
| Native filter focus z-index | Owns computed `z-index` | Retained unchanged |
| `.routine-dropdown` families | Zero runtime matches | Removed, including adjacent legacy duplicate |
| Exercise base/hover/focus surfaces | Matched hidden native select, zero computed delta | Removed; `.wpdd-button.wpdd-exercise` owns rendered surface |
| `.exercise-dropdown.filter-applied` | Only animation properties changed | Retained animation hook/keyframes; removed dead surface declarations |
| `#exercise-search.uniform-input` | Zero runtime matches | Removed (live select id is `exercise`) |
| Filter form/layout and seven responsive ranges | Multiple live font, margin, padding, z-index owners | Preserved; only dead native `.filter-dropdown` size declarations removed |
| Dark frame/label/dropdown/active/focus/hover glass blocks | Matches where applicable, zero computed delta | Removed; scoped/shared dark systems own the values |
| `.filter-view-toggle` light/dark/responsive/page-header family | Zero runtime matches on the only loading route | Removed; independent `.frame-header-2025` flex layout retained |
| Adjacent legacy `.exercise-dropdown` / `.filter-dropdown` surface duplicates | Matches hidden native selects, zero computed delta | Removed |

No newly introduced token survives. The only retained dark declaration in the
audited visual cluster is the browser-owned
`[data-theme='dark'] .filter-dropdown::before` pseudo background; it is
single-use, so tokenization would add indirection without removing a repeat.

## Result

Production CSS diff against `e34d254`:

- `pages-workout-plan.css`: **+4 / -487**, net **-483 lines**
  (6,874 → 6,391 physical lines);
- lexical `!important`: **605 → 535 (-70)**;
- no template, JavaScript, API, schema, calculation, visual baseline, or
  generated Bootstrap change.

Pinned Stylelint 16.11.0, focused bundle:

| Rule | Before | After | Delta |
| --- | ---: | ---: | ---: |
| All warnings | 1,592 | 1,420 | **-172** |
| `declaration-property-value-disallowed-list` | 739 | 646 | **-93** |
| `declaration-no-important` | 605 | 535 | **-70** |
| `no-descending-specificity` | 84 | 79 | **-5** |
| `no-duplicate-selectors` | 11 | 7 | **-4** |

No monitored category increased.

## Equivalence and gates

| Gate | Result |
| --- | --- |
| Per-rule CSSOM owner audit | Complete across 154 contexts |
| Exact old-CSS vs new-CSS filter-frame comparison | 252 computed/state comparisons exercised; 126/126 screenshots byte-identical |
| Deterministic old-CSS vs new-CSS table comparison | 12/12 byte-identical (three viewports, two themes, two modes) |
| Cascade contract | 18/18 passed (new deletion/retention contract included) |
| Focused Workout Plan Chromium | 35/35 passed |
| Focused route visual | 5/6 pass; only exact WP4.0 desktop-dark known red, 1,039 px |
| Thumbnail visual | Six distinct committed baselines pass; stale desktop-advanced and mobile-light-simple mismatches are change-independent by the 12/12 old-vs-new proof |
| Pinned Stylelint | 1,592 → 1,420; no category increase |
| `git diff --check` | Passed |
| Full pytest | 1,744 passed in 296.99 s |
| `bootstrap.custom.min.css` | Untouched |

The committed Windows thumbnail run reproduced the documented
`plan-desktop-light-advanced` 6,262-pixel red. A second committed snapshot,
`plan-desktop-dark-advanced`, also differed by 5,618 pixels on this machine. A
continued run passed six distinct stored baselines before
`plan-mobile-light-simple` reproduced another 2,365-pixel mismatch. A dedicated
deterministic harness then served the exact `e34d254` CSS and the edited CSS to
separate contexts using the repository's visual helpers. All twelve combinations
of desktop/tablet/mobile, light/dark, and simple/advanced produced byte-identical
table images. Therefore the stored snapshot mismatches are not caused by this
removal. No baseline was updated, and the temporary comparison spec was removed.

## Contract lock

`test_workout_plan_dormant_filter_glass_cluster_removed` asserts that:

- no abandoned `--wp-dark-*` token vocabulary is introduced;
- the top-level dead glass, routine, exercise-search, toggle, and dark selector
  families stay absent;
- the computed owners (`position`, focus z-index, both pseudo rules, animation
  hook/keyframes) remain;
- filter form layout, 45 remaining media queries, and both workout cascade
  layers remain;
- native route hooks and wpdd enhancement remain wired; and
- the retired toggle has no route-template consumer/in-repo factory invocation.

## Remaining WP4.3i map

Line numbers are approximate post-i-i and must be re-verified at packet entry.

| Packet | Cluster | Current approximate range |
| --- | --- | --- |
| i-b | `@media` / wpdd button dark blocks | 500–850 |
| i-c | table-header and collapsible-frame | 1,090–1,330 |
| i-d | collapse-toggle, horizontal layout, labels | 1,335–1,550 |
| i-e | selection actions | 1,700–1,780 |
| i-f | input-fields-group controls | 1,795–2,130 |
| i-g | cascade dropdown and breadcrumb | ~5,250–5,390 |
| i-h | workout-estimate provenance/trace/fatigue/nudge | ~6,000–6,391 |

WP4.3i-i is complete in the isolated worktree. The next implementation packet
is i-b. Do not push, open a PR, or begin i-b without owner direction.

## Migration notes

No core workflow behavior, API contract, database schema, calculation, template,
or JavaScript changed. This is browser-proven dead CSS removal. Rendered wpdd
controls, responsive filter layout, native focus/position mechanics, and the
exercise animation hook are preserved.
