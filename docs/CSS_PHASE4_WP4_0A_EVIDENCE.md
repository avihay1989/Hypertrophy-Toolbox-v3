# WP4.0a Visual and Functional Selector Evidence

Status: **complete 2026-07-17**. Work started from the committed WP4.-1 parent
`6e0a408` in the isolated `wt/wp4-cascade-foundation` worktree. The selector
packet is commit `9c08c10`; the reviewed Linux additions are commit `ab9dc7b`.
Both commits are pushed on that branch. WP4.0 is not included.

## Selector hardening

`e2e/visual-helpers.ts` no longer selects presentation classes. The screenshot
normalizer now uses explicit contracts:

- `data-visual-surface` for deterministic dark surfaces;
- `data-visual-header` and `data-visual-accent` for the workout/profile heading
  treatment;
- `data-visual-icon`, `data-visual-control`,
  `data-visual-scale-control`, and `data-visual-dropdown-toggle` for volatile
  chrome;
- native `input`, `textarea`, and `select` semantics for form normalization.

Server-rendered templates and the four JS-created component paths carry the
hooks. The thumbnail baselines now target `data-testid="exercise-table"` and
`data-testid="workout-log-table"`; User Profile gained
`data-testid="user-profile-page"`. The hooks have no production CSS rules and
do not alter runtime layout or behavior.

Three static contracts in `tests/test_visual_selector_contracts.py` prevent the
removed presentation selectors and literal RGB checks from returning, and
require Profile/Backup visual coverage.

## Token-aware functional assertions

- The existing light/dark Profile, Body Composition, and Backup icon colors
  are unchanged. Each rule now exposes its same literal through the local
  `--nav-icon-accent` variable. `nav-dropdown.spec.ts` resolves the variable,
  proves computed color equality, proves all three semantic accents remain
  distinct, and retains the Profile/Backup hover-motion assertions.
- Weekly and Session legend swatches now carry `data-volume-level`. The shared
  assertion compares their computed backgrounds with Bootstrap's existing
  `--bs-danger`, `--bs-orange`, `--bs-success`, and `--bs-purple` properties.
  This retains all four exact color relationships without embedding RGB output
  formatting in the spec.

## Visual coverage and review

`visual.spec.ts` now covers ten routes. Adding User Profile and Backup at three
viewports and two themes increases each platform set from 48 to 60 images.

Windows results:

- Twelve new images were intentionally written with
  `--update-snapshots=missing`, then all 12 passed an update-free comparison in
  39.2 seconds.
- All Profile/Backup mobile, tablet, and desktop images were visually reviewed
  in both themes for route content, responsive layout, clipping, and theme
  application.
- A SHA-256 manifest proved all 48 pre-existing Windows images stayed
  byte-identical. No existing snapshot was rebaselined.
- The full expanded spec ran **59 passed + 1 unchanged known-red** in 1.7
  minutes. The red is the pre-WP4 animated-frame mismatch in
  `workout-plan-desktop-dark`, still exactly 1,039 pixels.
- The serial thumbnail spec ran **1 passed + 1 unchanged known-red + 16 not
  run**. Its first red remains `plan-desktop-light-advanced`, exactly 6,262
  pixels; file-level serial mode skips the later cases after that failure.

Linux status:

- Pinned `ubuntu-24.04` generate run
  [29536203369](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29536203369)
  passed all **78** visual tests and uploaded the 78-file
  `visual-baselines-linux` artifact.
- Artifact review found 12 missing Profile/Backup images, 49 byte-identical
  legacy images, and 17 regenerated legacy hashes. All 12 new images were
  reviewed across the three viewports and two themes. Only those 12 were
  imported; none of the 17 legacy variants was accepted.
- Update-free compare run
  [29536626464](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29536626464)
  proved all **12/12** new Profile/Backup images byte-identical. Its combined
  result was **51 passed + 11 pre-existing animated-GIF-only reds + 16 not
  run** after the serial thumbnail spec stopped at its first red.
- Diff review confined every red to the existing animated signature or
  exercise-thumbnail pixels: six shared desktop-light signature reds at 807
  pixels each; workout-plan light/dark at 1,125/957; workout-log light/dark at
  1,028/1,012; and `plan-desktop-light-advanced` at 6,681. No Profile or Backup
  image failed. The Linux set is now 60 route images plus 18 thumbnails.

## Verification

- Focused selector/cascade contracts: **7 passed**.
- Focused route tests: **111 passed**.
- Blocking flake8: **0**; `tsc --noEmit`: passed; Vitest: **93 passed**.
- Full pytest: **1,722 passed + 2 unchanged known-red catalog invariants**.
  The visual seed still has 633 blank primary-muscle values and 454 blank
  movement-pattern values; no new Python red appeared.
- Complete required Chromium functional set: **407 passed** in 11.0 minutes.
- `git diff --check`: passed. No SCSS changed, so `npm run build:css` was not
  required; `bootstrap.custom.min.css` stayed byte-identical at SHA-256
  `0F9E198319318E2DB274D7AA15CECD0CF536727D25A925B7C8C71BE6F9DEA68B`.
- The main checkout's expected WP2.2 file hashes and status stayed unchanged.
  Its live `data/database.db` stayed byte-identical at SHA-256
  `36ECD8B4EBF747DFA8CFCECF1D1C1C54A6ABFEDF89B66C3AD33B73ABC852071F`.

WP4.0a is complete. Next is WP4.0, the fresh known-red ledger; no WP4.0 or later
CSS work is included here.
