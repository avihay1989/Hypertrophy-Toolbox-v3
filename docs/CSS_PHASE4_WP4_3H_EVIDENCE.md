# CSS Phase 4 WP4.3h Evidence — User Profile Dark/Token Cleanup (audit/minimal)

Date: 2026-07-21

Branch: `worktree-agent-a7691c0529c98c267` (isolated worktree)

Base: local `main` at `bc9da14` (WP4.3g Weekly Summary shipped via PR #162).

## Outcome in one line

WP4.3h is an **audit/minimal** packet. The audit found the User Profile route
bundle **already fully tokenized** on the shared design-token system; **no
`--up-*` extraction is warranted**, so the production CSS is **unchanged**
(byte-identical to `main`). The packet ships the audit as a **pinning cascade
contract** plus documentation.

## Scope and isolation

The only tracked change is the cascade-contract test
`tests/test_css_cascade_contracts.py` (one new test, +64 / -0). The production
bundle `static/css/pages-user-profile.css` is **byte-identical** to `main`
(SHA-256 `3EF8AC5A14B1F874F7DF3895BA7398EAF81C53A42E880852485D6BE01FCC2951`
before and after). No template, JavaScript, API, schema, calculation, shared
CSS, `theme-dark.css`, another page, or WP4.4 work is included. This evidence
file and the two canonical handover documents are the only other edits.

`pages-user-profile.css` is loaded **only** by `templates/user_profile.html`
(via the `page_css` block, line 6); `base.html` does **not** reference it, so
the bundle is genuinely page-local (confirmed by repo-wide grep — the only
non-doc consumer is the template). Load order in `base.html` is preserved:
`a11y.css` < `{% block page_css %}` < `motion.css` < `theme-dark.css`, and the
bundle contains no document-wide `html:has()` scope.

## Step 0 — the audit

The bundle has 274 hex occurrences across 27 distinct values, plus 24 `rgba()`
literals. Classified by how each literal is actually used:

- **254 of 274 hex occurrences are `var(--token, #fallback)` fallbacks** for the
  shared design tokens (`--ink-1/2/3`, `--surface-1/2`, `--line-1`, `--accent`).
  These are the intended design-token pattern — the fallback is the shared
  value, not a page-owned literal — and are out of scope for extraction. Every
  ink / border / surface / line role in the bundle is already carried this way
  (e.g. `color: var(--ink-2, #4a5170)`, `border-bottom: 1px solid
  var(--line-1, #e2e5ee)`), and every dark-mode rule resolves through shared
  tokens via `color-mix(... var(--surface-1 ...) ..., black)`. **There are no
  bare ink / border / surface / line literals left to extract.**

- **Only 20 hex occurrences (8 distinct values) are bare** (not a `var()`
  fallback). All are brand / classification / status hues used as `color-mix()`
  inputs, not ink/border/surface roles:

  | Bare literal | Uses | Role | Shared elsewhere? | Disposition |
  | --- | ---: | --- | --- | --- |
  | `#f59f00` | 4 | coverage-band "partial" amber (band-fill / pill-bg / pill-border / donut) | page-local | keep (classification set) |
  | `#2f9e44` | 4 | coverage-band "fully" green | **shared** with `pages-workout-plan.css` | keep (shared) |
  | `#4c6ef5` (bare) | 4 | coverage-band "mostly" fixed accent hue | (accent hue) | keep (fixed, theme-independent by design) |
  | `#2eb872` | 2 | autosave "saved" green (bg + border mix) | page-local | keep (status set) |
  | `#d93b3b` | 2 | autosave "error" red (bg + border mix) | page-local | keep (status set) |
  | `#1f2937` | 2 | slate ink, accent-text mix partner (light) | **shared** with `layout.css` / `pages-volume-splitter.css` / bootstrap | keep (shared) |
  | `#1f7a4d` | 1 | autosave "saved" text | page-local | keep (single-use) |
  | `#b02a2a` | 1 | autosave "error" text | page-local | keep (single-use) |

- The 24 `rgba()` literals are the bodymap muscle-region slate-grey fills/strokes
  and box-shadow colours; almost all single-use (the only repeats are
  `rgba(0,0,0,0.25)` ×3 shadow, `rgba(150,150,150,0.10)` ×2 and
  `rgba(180,186,208,0.06)` ×2 muscle fills) — a specialized single-purpose SVG
  set, not the ink/border/surface category.

## Why no extraction is warranted

Every candidate fails at least one criterion, so per the packet's explicit
"audit/minimal — do NOT force extractions that aren't warranted" mandate and the
WP4.3f/g precedent (leave classification/status palettes; single-use literals
stay as-is), **nothing is extracted**:

1. **Shared values must stay shared.** `#2f9e44` (also in
   `pages-workout-plan.css`) and `#1f2937` (also in `layout.css`,
   `pages-volume-splitter.css`, and generated bootstrap) are not page-owned;
   folding either into a page-local `--up-*` token would wrongly page-scope a
   value shared across bundles.

2. **The page-local hues form a coherent classification/status palette whose
   other members are shared / the accent / single-use.** The coverage-band scale
   is population_only (`var(--ink-3)`) / partial (`#f59f00`) / mostly
   (`#4c6ef5`) / fully (`#2f9e44` — shared); the autosave-status scale is saved
   (`#2eb872` + `#1f7a4d` single-use) / pending (accent) / error (`#d93b3b` +
   `#b02a2a` single-use). Extracting only the page-local members (`#f59f00`,
   `#2eb872`, `#d93b3b`) would leave an **inconsistent half-tokenized palette** —
   worse than a recognized, intact palette. WP4.3g extracted complete role sets,
   never fragments of a classification scale.

3. **The one non-classification candidate is metric-negative.** A trial
   extraction of `#1f2937` into a single `:root` token was built and measured: it
   **raised** the focused hardcoded-value warning count 226 → 227, because the
   two consuming declarations already carry `var(--accent, #4c6ef5)` fallbacks
   (so they stay flagged) while the new token definition adds a flagged
   declaration. The trial was reverted; the production CSS is unchanged.

The focused hardcoded-value metric here is dominated by legitimate design-token
fallbacks and a coherent classification palette; it cannot fall without
degrading the token-fallback pattern. This is the correct audit-minimal result.

## Contract lock

`test_user_profile_bundle_is_already_token_clean_after_wp43h_audit` pins the
audited state:

- page-local load scope (template loads it; `base.html` does not) and the
  preserved `a11y < page_css < motion < theme-dark` order, no `html:has()`;
- `--up-` absent (no page tokens were manufactured);
- every ink / border / surface / line role still on the shared tokens
  (representative `var(--ink-*/--surface-*/--line-*/--accent, #fb)` sample);
- the shared literals `#2f9e44` (×4) and `#1f2937` (×2) kept bare;
- the page-local classification/status palette kept bare (`#f59f00` ×4,
  `#2eb872` ×2, `#d93b3b` ×2, `#1f7a4d` ×1, `#b02a2a` ×1) plus the fixed
  "mostly" accent-hue color-mixes;
- the `[data-theme='dark']` scope and all 14 `@media` breakpoints preserved.

The combined selector/cascade + visual-selector contract gate is now **20/20**
(`test_css_cascade_contracts.py` 17 + `test_visual_selector_contracts.py` 3).

## Stylelint measurement

Pinned Stylelint `16.11.0` parsed the bundle with zero parse errors,
invalid-option warnings, or errored files. Because the production CSS is
unchanged, the focused delta is **0**:

| Measurement | `main` (HEAD) | WP4.3h final | Delta |
| --- | ---: | ---: | ---: |
| Focused hardcoded-value (`declaration-property-value-disallowed-list`) | 226 | 226 | 0 |
| Focused `declaration-no-important` | 0 | 0 | 0 |
| Focused `no-descending-specificity` | 18 | 18 | 0 |
| Focused `no-duplicate-selectors` | 2 | 2 | 0 |

No monitored important, specificity, or duplicate category changed. (The
226 hardcoded-value warnings are almost entirely the legitimate design-token
fallbacks and the classification palette described above; see "Why no extraction
is warranted" for why the count is not reducible in this packet.)

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed (only `tests/…` modified; CSS byte-identical) |
| worktree isolation | production CSS SHA-256 unchanged vs `main` |
| selector/cascade + visual-selector contracts | **20/20** passed |
| blocking Flake8 selection (changed test) | **0** findings |
| TypeScript `tsc --noEmit` | passed |
| Node `--check` over `static/js` | **64/64** |
| Vitest | **105/105** passed |
| focused User Profile Chromium visual (6 variants) | **6/6** passed update-free |
| User Profile functional (`user-profile.spec.ts`) | **24/24** passed |
| required CI Chromium functional list | _see below_ |
| pytest (full `tests/`) | **1,743** passed, **0** failed |

The 2 historical "catalog known-reds" (visual-seed `primary_muscle_group` /
`movement_pattern` null invariants) are **green** against this worktree's
isolated seed catalog (`test_catalog_invariants.py` 2/2 passed), so the full run
is 1,743 passed / 0 failed with **no new reds**. The single added Python test is
the WP4.3h audit contract.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six User Profile variants (desktop/tablet/mobile × light/dark) | **6/6** passed update-free |
| `visual.spec.ts` + `visual-baseline-thumbnails.spec.ts` (deep) | **60 passed**; only the two WP4.0 known reds failed |
| workout-plan desktop-dark | **1,039 px** (1046 → 1039 on retry) — exact WP4.0 red |
| plan-desktop-light-advanced (thumbnail) | **6,262 px** (6276 → 6262 on retry) — exact WP4.0 red |

Both persistent reds are the exact WP4.0 known reds on the **workout-plan** page,
which this User-Profile-only packet does not touch. Because the production CSS is
byte-identical to `main`, every rendered surface is provably unchanged from the
WP4.3g-verified baseline.

## Integrity locks

- Production bundle SHA-256 (before == after == `main`):
  `3EF8AC5A14B1F874F7DF3895BA7398EAF81C53A42E880852485D6BE01FCC2951`.
- Generated Bootstrap (`bootstrap.custom.min.css`) not touched (no SCSS rebuild;
  page bundles are plain CSS).

## Next action

WP4.3h is complete in the isolated worktree and **stops at the owner gate** — not
pushed, not merged. The remaining WP4.3 line is WP4.3i workout-plan (sectioned)
and WP4.3j workout-log (multi-WP, redesign-sized), then WP4.4 (shared bundles /
navbar / `theme-dark.css`), which is where the User Profile classification/status
palette and shared-slate-ink consolidation would be handled if desired. Do not
begin without explicit direction.
