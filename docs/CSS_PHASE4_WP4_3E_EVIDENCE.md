# CSS Phase 4 WP4.3e Evidence — Welcome Dark/Token Cleanup

Date: 2026-07-19

Branch: `wt/wp4-3-welcome-dark-token-cleanup`

Base: local `main` at `859ccea8b15a400188d9c5fe066d2fb1bc969d24`

## Scope and isolation

WP4.3e changed only the Welcome route bundle in production:
`static/css/pages-welcome.css`. The companion change in
`tests/test_css_cascade_contracts.py` pins the preserved cascade contract; this
evidence file and the canonical handover documents are the only documentation
changes. No template, JavaScript, API, schema, calculation, shared CSS,
`theme-dark.css`, another page, or WP4.4 work is included. The production/test
working diff is two files (+100 / -44).

The isolated worktree started from base `859ccea` on branch
`wt/wp4-3-welcome-dark-token-cleanup`. The worktree's seeded database and the
tracked visual fixture both have SHA-256
`6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.

## Changes

Two behavior-preserving transformations, both exact-value:

1. **Exact-repeat white-ink and translucent-white overlays extracted to four
   page-local semantic tokens.** `--wl-on-accent: #ffffff` replaces every
   `#ffffff !important` / `#ffffff` white-ink site on the featured bento card,
   hero button ink, and developer-credit banner; `--wl-overlay-soft`
   (`rgba(255, 255, 255, 0.15)`), `--wl-overlay-strong`
   (`rgba(255, 255, 255, 0.25)`), and `--wl-overlay-border`
   (`rgba(255, 255, 255, 0.4)`) replace the exact repeated translucent-white
   surface/border expressions. Only exact repeated expressions were replaced; no
   near-match (the brand accent/gradient literals `#1e40af`, `#3b82f6`,
   `#2563eb`, `#1d4ed8`, the `#0d9488`/`#14b8a6` featured gradients, the
   shimmer/credit multi-stop gradients, `#fff` shorthand color declarations, and
   the other `rgba(255, 255, 255, *)` alphas at 0.2/0.7/0.9) was normalized.

2. **Seven dead (unreferenced) custom properties removed outright.** Each was
   proven to have zero `var()` consumers repo-wide, in both HEAD and the final
   file:
   - `--wl-featured-start`, `--wl-featured-end`, `--wl-featured-gradient` — a
     dead chain: `--wl-featured-gradient` (0 consumers) was the only consumer of
     `--wl-featured-start`/`--wl-featured-end`; the featured cards paint
     hardcoded `linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)` (light) and
     `#0f766e 0%, #14b8a6 100%` (dark) `!important` gradients directly, so the
     token trio and its dark-mode remap were never rendered. The live hardcoded
     gradients and the `[data-theme='dark'] #welcome .bento-featured` override
     remain.
   - `--wl-accent-glow`, `--wl-shadow-glow` — a second dead chain:
     `--wl-shadow-glow` (0 consumers) was the only consumer of
     `--wl-accent-glow`.
   - `--wl-info` — 0 consumers.
   - `--wl-duration-slow` — 0 consumers (including its reduced-motion `0ms`
     remap).

Because every removed declaration is an unused CSS variable and every
substitution is exact-value, no competing declaration on any rendered element was
changed and no cascade winner moved. `#ffffff` now appears only in the
`--wl-surface` and `--wl-on-accent` definitions. No document-wide `:has()`
selector was introduced.

## Rendered equivalence

The focused Welcome visual suite renders all six Windows variants (desktop /
tablet / mobile × light / dark) **byte-identical** to their committed baselines,
update-free. Because the visual comparison checks every pixel, it is a strict
superset of a sampled computed-value audit: it proves the token extraction and
dead-variable removal produce zero rendered change in either theme. All twelve
committed Welcome images (six Linux + six Windows) are byte-identical to base.

## Contract lock

`test_welcome_tokens_extract_exact_values_without_dead_custom_properties` pins:

- stylesheet load order (a11y before the page bundle, page bundle before
  `motion.css` before `theme-dark.css`) and the absence of document-wide
  `html:has()`;
- each of the four new page-local tokens defined once and consumed by at least
  its exact-repeat replacement count (`--wl-on-accent` ≥21, `--wl-overlay-strong`
  ≥5, `--wl-overlay-soft` ≥3, `--wl-overlay-border` ≥2);
- the seven removed dead custom properties are absent;
- no raw white `!important`/plain literal survives outside the two token
  definitions (`#ffffff` count == 2; each removed `rgba(255, 255, 255, *)`
  overlay literal appears exactly once, in its token definition);
- the live featured hardcoded `!important` gradient, the dark featured override,
  all three responsive breakpoints (1024/768/480px), and the
  `id="welcome" data-page="welcome"` template hook.

The combined selector/cascade + visual-selector contract gate is now **17/17**.

## Stylelint measurement

Pinned Stylelint `16.11.0` with `postcss-scss` parsed all measured sources with
zero parse errors, invalid-option warnings, or errored files.

| Measurement | pre-edit (HEAD) | WP4.3e final | Delta |
| --- | ---: | ---: | ---: |
| Focused Welcome warnings | 144 | 111 | -33 |
| Focused hardcoded-value (`declaration-property-value-disallowed-list`) | 96 | 63 | -33 |
| Focused `declaration-no-important` | 33 | 33 | 0 |
| Focused `no-descending-specificity` | 15 | 15 | 0 |
| Total warnings (all CSS/SCSS) | 6,364 | 6,331 | -33 |

No monitored important, specificity, or duplicate category increased. Cumulative
delta vs the WP4.1 pinned baseline (7,202) is -871.

## Verification

| Gate | Result |
| --- | --- |
| `git diff --check` | passed |
| worktree isolation (commits ahead/behind main pre-commit) | 0 / 0 (working-tree change only) |
| selector/cascade + visual contracts | 17/17 passed |
| blocking Flake8 selection (changed test) | 0 findings |
| TypeScript `tsc --noEmit` | passed |
| Vitest | 105/105 passed |
| focused Welcome Chromium visual | 6/6 passed update-free |
| Welcome functional (erase-flow + smoke-navigation) | 12/12 passed |
| required CI Chromium functional list (2-shard) | 215/215 + 211/211 = 426/426 passed |
| tracked-file pytest | 1,738 passed + 2 permitted catalog reds |

The required functional list has grown from 407 (WP4.3d) to 426 as later work
added specs; it was run with the canonical two-shard topology and a freshly
seeded throwaway database per shard, 0 failures and 0 flakes. The only pytest
failures were the unchanged visual-seed catalog invariants: 633 null/blank
`primary_muscle_group` rows and 454 null/blank `movement_pattern` rows. The
additional Python pass relative to WP4.3d is the new Welcome cascade contract.

Every visual command used `PW_VISUAL_SEED=1`; no command used
`--update-snapshots`.

| Visual suite | Result |
| --- | --- |
| all six Windows Welcome variants | 6/6 passed update-free |
| complete `visual.spec.ts` | 59 passed + only workout-plan desktop-dark at exactly 1,039 pixels (initial 1,046, settling to 1,039 on retry) |
| complete thumbnail suite | 1 passed + only plan-desktop-light-advanced at exactly 6,262 pixels (initial 6,276, settling to 6,262 on retry) + 16 not run |

Both persistent reds are the exact WP4.0 known reds on the workout-plan page,
which this Welcome-only change does not touch.

## Integrity locks

- Screenshot manifest: **156 files, 0 mismatches** against main; worktree
  aggregate SHA-256
  `93803A55BB5620F80557A9DCF85AB4CEC007A79B914B8F855EE644D00DB4C117`.
- Generated Bootstrap SHA-256: main checkout
  `24CC9F443D2D0933F1C89DC7203B0618063C4706ADE17627F0A03934C73D75D4`;
  isolated worktree
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`
  (the established worktree-vs-main generated-bundle divergence recorded since
  WP4.3a; the CSS change does not touch it).
- Target worktree and visual-fixture DB SHA-256:
  `6477B2AC0F91248F7022D1B7AAE60B98586CB13EC4D94CC37294D4115F0AE6E3`.
- Main live DB SHA-256:
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

The twelve committed Welcome images remained byte-identical:

| Platform / variant | SHA-256 |
| --- | --- |
| Linux desktop dark | `BBE70FC109AAD83F2ABEA1A45B622DB18E36EC06402EEF09D8368C13775B988D` |
| Linux desktop light | `C9D69654FD5B7E60ACBCACD99E9A6B2E28B302E7D53A2326C8A31EE003B23008` |
| Linux mobile dark | `65C904EA47222C637BFDA8F5111DC02CD6B8437114C9C087D8B40C7C3E66A985` |
| Linux mobile light | `01A617CCCCF95E1C16DCB341447BC08624D27114975E0D2E29739D4429053961` |
| Linux tablet dark | `DFA0ADC97ABFC2E1B878132765D83DE411AA2B661DB90726F1CA88230EBE4E06` |
| Linux tablet light | `E24CFCE52191061D8CA7CE31A1F234A4DE139CB08C725E651B57D138FCC70EE6` |
| Windows desktop dark | `CF9D0B9589A28608FB007CE470EAE07185DE1D78CFABB256C23AA926ED37F2E0` |
| Windows desktop light | `5F9223CC5F9213279A9217845272D175EB9A4FD8A2DD99E0FAE5D8C2CC206152` |
| Windows mobile dark | `60B6D8465F36A32863417EC9E633BAD2EEFCC9892BDF54F16891DD586C9D7D61` |
| Windows mobile light | `12A1ADD26B76BF9321306143F51419206C882703EC31516EAB5CD9A783F7C674` |
| Windows tablet dark | `144440DB3658099BEFBDA362C38E195A8BE710124558F308BB0854B384ABC8C1` |
| Windows tablet light | `DDB7E2ABAFFF8D09CC2CD20FCA028D62BDD841DECD636601AB5E92A7FD442F3E` |

## Next action

WP4.3e is complete in isolated `wt/wp4-3-welcome-dark-token-cleanup`. Awaiting
owner direction to integrate into local `main` by history-preserving merge and
whether to push. Do not begin Session Summary, another WP4.3 page, or WP4.4
without explicit direction.
