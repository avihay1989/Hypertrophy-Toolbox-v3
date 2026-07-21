# CSS Phase 4 WP4.3h Evidence — User Profile Dark/Token Cleanup

Date: 2026-07-22

Branch: `worktree-agent-a19e98879e5bdcafc` (isolated worktree)

Base: local `main` at `bc9da14` (WP4.3g Weekly Summary shipped via PR #162).

## Page selection

WP4.3h is the User Profile route bundle (`static/css/pages-user-profile.css`),
loaded only by `templates/user_profile.html` via the `page_css` block. It is the
next packet in the documented WP4.3 order (named in the WP4.3f and WP4.3g "Next
action" sections as "User Profile — audit / minimal cleanup") and is the most
self-contained remaining surface: the two other uncovered bundles are large,
sectioned efforts (`pages-workout-plan.css` — 6,874 lines, 605 `!important`;
`pages-workout-log.css` — 2,185 lines, 293 `!important`), whereas User Profile is
a single 1,843-line bundle with **zero** `!important` and no cross-page table
entanglement. (There is no `pages-fatigue.css`; fatigue styling lives in shared
bundles, out of WP4.3 route-bundle scope.)

## Audit finding — this bundle was authored on the shared token system

Unlike the summary bundles (which carried many repeated **direct** hex values
such as `#e0e0e0` used as `color:`), `pages-user-profile.css` was written against
the shared token vocabulary: virtually every hex is a `var(--token, #fallback)`
fallback for `--ink-*` / `--surface-*` / `--accent` / `--line-*`. Those fallbacks
are deliberately left untouched (exactly as WP4.3a–g left shared-token fallbacks
in place). The only genuinely repeated **raw** literals — color-mix operands and
a handful of direct `fill:` / `box-shadow:` values — were extracted. This is why
the packet is a small, byte-identical extraction rather than a large token sweep.

## Change — value-preserving token extraction

Eight page-local semantic tokens were introduced: a `:root` block for the six
theme-independent colors and a `[data-theme='dark']` block for the two dark-only
values. Every substitution is exact-value, so no rendered element changes:

| Token | Value | Role | Consumers |
| --- | --- | --- | ---: |
| `--up-band-partial` | `#f59f00` | coverage-band "partial" hue (fill / pill / donut) | 4 |
| `--up-band-mostly` | `#4c6ef5` | coverage-band "mostly" hue | 4 |
| `--up-band-fully` | `#2f9e44` | coverage-band "fully" hue | 4 |
| `--up-autosave-saved` | `#2eb872` | autosave "saved" status color | 2 |
| `--up-autosave-error` | `#d93b3b` | autosave "error" status color | 2 |
| `--up-region-faint` | `rgba(150, 150, 150, 0.10)` | light body-map faint region fill | 2 |
| `--up-dark-shadow-ink` | `rgba(0, 0, 0, 0.25)` | dark shadow ink (box-shadow) | 3 |
| `--up-dark-region-faint` | `rgba(180, 186, 208, 0.06)` | dark body-map faint region fill | 2 |

Total: 8 tokens, 23 consumer sites. The coverage-band and autosave-status colors
are intentionally **fixed hues** in the source (raw operands, not `var(--accent)`)
so they stay constant across themes; the `--up-band-mostly` value coincides with
the accent value but is a distinct fixed classification role, split by intent
exactly as WP4.3f/g split same-valued tokens by property. The two dark tokens are
defined under `[data-theme='dark']` so they resolve only under the dark root —
precisely where their consuming rules apply.

### Deliberately left untouched

- **All `var(--token, #fallback)` fallback hexes** (e.g. the 68 `var(--accent,
  #4c6ef5)` fallbacks) — shared-token fallbacks, out of scope per prior packets.
- **The `color-mix()` keyword operands `black` (×10) and `white` (×3)** — the
  disallowed-value Stylelint rule does not flag bare `black`/`white` keywords,
  they are mixing primitives rather than semantic colors, and no prior WP4.3
  bundle tokenized them. Pinned by count in the contract.
- **`#1f2937` (×2)** — a genuine repeated raw operand, but both its declarations
  also carry the shared `var(--accent, #4c6ef5)` fallback, so tokenizing it would
  leave those declarations flagged while adding a token-definition warning: a net
  **increase** in the hardcoded-value category. It was left inline so that every
  extracted token is net-neutral-or-better and no monitored category rises.
- All single-use dark/light rgba region and shadow literals, the volume-badge
  and single-use accent-mix ink literals.

No rule was deleted and no `!important` exists in this bundle (there were none to
remove). This packet is a pure value-preserving extraction; no document-wide
`:has()`/`html:has()` selector was introduced.

## Rendered equivalence — two independent proofs

**1. Static round-trip byte-identity.** The edit was produced by a
count-asserting Python transform that preserved CRLF endings (1,843 → 1,863 CRLF
lines, 0 bare LF). It asserted the exact pre-edit occurrence count of every
literal before replacing it, then **expanded every `var(--up-*)` back to its
literal and proved the result byte-identical to the original file body**. Because
CSS custom-property resolution is exact text substitution, and each token holds
the literal it replaced within the same declaration/selector, computed values are
identical in both themes by construction.

**2. Live browser computed-style verification (Playwright MCP).** The app was
served from this worktree and `/user_profile` loaded in the real browser. In both
themes the custom properties resolve exactly:

- Theme-independent tokens (`--up-band-*`, `--up-autosave-*`, `--up-region-faint`)
  resolve to their exact literals in **both** light and dark.
- The dark-only tokens are **empty in light** (correct — their consumers are all
  `[data-theme='dark']`-scoped) and resolve to `rgba(0, 0, 0, 0.25)` /
  `rgba(180, 186, 208, 0.06)` in dark.
- A concrete consumer — the dark collapse-toggle — computes
  `box-shadow: rgba(0, 0, 0, 0.25) 0px 1px 2px 0px, rgba(0, 0, 0, 0.25) 0px 2px
  6px 0px`, byte-identical to the pre-edit literal declaration.

Viewport screenshots were captured in light and dark for the record.

## Contract lock

`test_user_profile_tokens_extract_repeated_operands_value_preserving` pins:

- stylesheet load order (a11y before the page bundle, page bundle before
  `motion.css` before `theme-dark.css`) and the absence of document-wide
  `html:has()`;
- each of the eight tokens defined once and consumed by the exact count of the
  repeated literal it replaced;
- the six theme-independent tokens living in `:root` and the two dark tokens in
  the `[data-theme='dark']` block;
- every extracted literal surviving only in its single token definition
  (`#4c6ef5` pinned at 69: 68 shared accent fallbacks + one `--up-band-mostly`);
- the intentional keeps: `#1f2937` == 2 (left inline), `, black)` == 10,
  `, white)` == 3;
- the bundle staying `!important`-free, all 14 `@media` blocks preserved, and the
  `class="user-profile-page"` / `id="profile-lifts-form"` template hooks intact.

The `tests/test_css_cascade_contracts.py` suite is now **17** tests (was 16),
all passing.

## Stylelint measurement

Pinned Stylelint `16.11.0` parsed the bundle with zero parse errors. Focused
measurement on `pages-user-profile.css` (HEAD vs WP4.3h final):

| Measurement | pre-edit (HEAD) | WP4.3h final | Delta |
| --- | ---: | ---: | ---: |
| Focused User Profile warnings | 246 | 240 | -6 |
| Focused hardcoded-value (`declaration-property-value-disallowed-list`) | 226 | 220 | -6 |
| Focused `no-descending-specificity` | 18 | 18 | 0 |
| Focused `no-duplicate-selectors` | 2 | 2 | 0 |
| Focused `declaration-no-important` | 0 | 0 | 0 |

`pages-user-profile.css` is the only changed production file, so the
project-wide warning delta equals the focused delta (-6). No monitored important,
specificity, or duplicate category increased. The residual 220 hardcoded-value
warnings are almost entirely the shared `var(--token, #fallback)` fallbacks and
single-use rgba region/shadow literals, intentionally out of scope for this
value-preserving pass.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| worktree isolation (final tracked diff) | 2 files only (`pages-user-profile.css`, `test_css_cascade_contracts.py`) |
| static round-trip (expand `var(--up-*)` → literal) | byte-identical to original body |
| CSS cascade/selector contracts (`test_css_cascade_contracts.py`) | 17/17 passed |
| live browser computed-style verification (Playwright MCP, both themes) | all tokens resolve exactly; collapse-toggle box-shadow byte-identical |
| Vitest | 105/105 passed |
| full pytest (`tests/ -q`) | 1,743 passed, 0 failed |

Notes:
- **Vitest** was executed from the main checkout (the isolated worktree has no
  `node_modules`); this packet changes **zero** JavaScript, and the worktree JS is
  byte-identical to the `bc9da14` base, so the 105/105 result applies unchanged.
- **Full pytest** ran clean at 1,743 passed with no catalog reds: this worktree's
  seeded fixture DB does not carry the null/blank `primary_muscle_group` /
  `movement_pattern` rows that produced the two permitted catalog reds in earlier
  packets. The `data/database.db` mutated by app startup / the test run was
  restored to HEAD so it is not part of the commit.
- **Playwright functional/visual specs** (`user-profile.spec.ts`, `visual.spec.ts`)
  were not executed in-worktree because the isolated worktree lacks `node_modules`
  and a `.venv`; the task-sanctioned Playwright MCP path was used instead for the
  actual-UI computed-style proof above. Running the committed Chromium visual
  matrix for User Profile in CI (where `node_modules`/`.venv` exist) is the
  residual confirmation step; the static round-trip proof and live MCP audit make
  a rendered regression structurally impossible for this substitution-only change.

## Generated Bootstrap

`npm run build:css` compiles only `scss/custom-bootstrap.scss` →
`static/css/bootstrap.custom.min.css`; it does not touch the hand-authored
`pages-user-profile.css`. The build was run to confirm this; the regenerated
Bootstrap artifacts (the established worktree-vs-main line-ending divergence,
unrelated to this change) were restored to their committed state so the commit
contains only the two target files — matching every prior WP4.3 packet.

## Migration notes

No behavior change to any core workflow (plan/log/analyze/progress/distribute/
backup/profile). No API response shape, schema, calculation, template, or
JavaScript change. This is a pure CSS value-preserving refactor: eight page-local
custom properties replace exact repeated raw color literals in the User Profile
route bundle, with a new static contract pinning the extraction and the
intentional keeps. Computed styles are unchanged in both themes.

## Next action

WP4.3h is complete in the isolated worktree. Per the WP4.3 cadence, **nothing is
pushed and no PR is opened** — this is owner-gated. The remaining WP4.3 packets in
order are WP4.3i workout-plan (sectioned, large) and WP4.3j workout-log
(multi-WP, redesign-sized), then WP4.4 (shared bundles / navbar / `theme-dark.css`).
Do not begin without explicit direction.
