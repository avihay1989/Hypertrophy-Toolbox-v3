# CSS Phase 4 — WP4.0 Fresh Known-Red Ledger

**Status:** complete on 2026-07-17.

**Measured tree:** `wt/wp4-cascade-foundation` at
`e46b67e183e5f5c7dc04f883c54c49e6925ea17b`, exactly equal to its upstream
before measurement.

**Scope:** measurement and documentation only. WP4.1 has not started.

WP4.0 reran the complete static, Python, required functional Chromium, Windows
visual, and pinned Linux visual gates after WP4.0a. This ledger is based only on
those fresh runs; the May ledger was not inherited. No product code, test,
snapshot, generated CSS, schema, API, or calculation behavior changed.

## Integrity lock

The target worktree was clean before the gates. The screenshot tree contained
78 Windows PNGs and 78 Linux PNGs. Their complete per-file pre/post manifest is
[`CSS_PHASE4_WP4_0_SCREENSHOT_MANIFEST.sha256`](CSS_PHASE4_WP4_0_SCREENSHOT_MANIFEST.sha256).
Aggregating the sorted `sha256  repository/path` lines separately by platform
gave:

| Asset | Pre-run SHA-256 | Bytes/count |
| --- | --- | ---: |
| Windows screenshot manifest | `3388a49eaeec41b42343676d41f3ea377c3fdceb8f79c8ea5ca4296891979923` | 78 PNGs |
| Linux screenshot manifest | `f82b8d4aac260708c971bcc0f2ad3bee3b5930eb78cf8328a4ef5567c06238d5` | 78 PNGs |
| `static/css/bootstrap.custom.min.css` | `0f9e198319318e2db274d7aa15cecd0cf536727d25a925b7c8c71be6f9dea68b` | 100,273 |
| Main live `data/database.db` | `36ecd8b4ebf747dfa8cfcecf1d1c1c54a6abfedf89b66c3ad33b73abc852071f` | 835,584 |

The unrelated, expected WP2.2 edits in the main checkout were also locked
before measurement:

| Main-checkout path | Pre-run SHA-256 | Bytes |
| --- | --- | ---: |
| `CLAUDE.md` | `e190c3b72ab1998cc8cc4ebea2f84349966c5ab934808be1931d4dd9cb4fc197` | 11,643 |
| `docs/MASTER_HANDOVER.md` | `a96768770eec9dd193b6ae7273d9b04322ffb6a7629a35c3f40166890f8c6106` | 64,632 |
| `docs/REFACTOR_PLAN.md` | `973e8c4bb8e2161634a2fe2b124ade8b7cc2904a6c55f7d3f0723b3d40f37702` | 48,398 |
| `utils/plan_generator.py` | `eca05910fc1f08d7c0e5159d6116461ca35ffe3cdaf22d9966fd78b2205085b4` | 61,654 |
| `tests/test_plan_generator_refactor_contracts.py` | `a77935fe3d5f4c75ae56ccfc77ad27c8fe5151c7c54af236addd1257f074037e` | 5,599 |

## Nonvisual gates

| Gate | Fresh result |
| --- | --- |
| `pytest tests/test_css_cascade_contracts.py tests/test_visual_selector_contracts.py -q` | **7 passed** |
| Blocking flake8 `E9,F63,F7,F82,F811,E711,E712,F401` | **0 findings** |
| `npx tsc --noEmit` | **passed** |
| `npm run test:js` | **8 files / 93 tests passed** |
| Full `pytest tests/ -q` | **1,722 passed + 2 failed** in 286.42s |
| Exact required functional Chromium list from `.github/workflows/ci.yml` | **407 passed** in 10.0m |

The functional run used `PW_VISUAL_SEED=1`, Chromium, the complete 24-spec
required list from CI, and the isolated `artifacts/e2e/database.e2e.db`.
The full pytest run likewise used its temporary test database. Neither gate
opened the main checkout's live database.

### Fresh pytest known-red ledger

| Test | Exact result | Classification |
| --- | ---: | --- |
| `tests/test_catalog_invariants.py::test_catalog_primary_muscle_group_has_no_nulls` | found **633**, expected 0 | Visual-seed catalog data debt |
| `tests/test_catalog_invariants.py::test_catalog_movement_pattern_has_no_nulls` | found **454**, expected 0 | Visual-seed catalog data debt |

No other Python test failed.

## Windows visual ledger

Both commands were update-free, used `PW_VISUAL_SEED=1`,
`--project=chromium --retries=2 --reporter=line`, and did **not** use an
update-snapshot flag.

### `e2e/visual.spec.ts`

Fresh aggregate: **59 passed, 1 failed**.

| Final red | Initial | Retry 1 | Retry 2 | Inspected cause |
| --- | ---: | ---: | ---: | --- |
| `visual baseline: workout-plan › workout-plan desktop dark` | 1,039 px | 1,039 px | 1,039 px | Navbar signature GIF plus six exercise video/control frames |

Each attempt's first stability capture was 1,046 pixels before the final
1,039-pixel assertion. Actual, expected, diff, and error-context evidence was
inspected; traces and videos are preserved under
`artifacts/wp4_0/windows-visual-spec`. The differences are localized
animated-frame pixels, not layout or cascade drift.

### `e2e/visual-baseline-thumbnails.spec.ts`

Fresh aggregate: **1 passed, 1 failed, 16 did not run**. The spec is serial, so
the first persistent red prevented the remaining cases from starting.

| Final red | Initial | Retry 1 | Retry 2 | Inspected cause |
| --- | ---: | ---: | ---: | --- |
| `§4 visual baseline — workout_plan thumbnails › plan-desktop-light-advanced` | 6,262 px | 6,262 px | 6,262 px | Transient visible skip-link/signature state plus six exercise video/control frames |

Each attempt's first stability capture was 6,276 pixels. Evidence is preserved
under `artifacts/wp4_0/windows-thumbnail-spec`. The 16 not-run cases were:
plan desktop dark simple/advanced; plan tablet light/dark simple/advanced; plan
mobile light/dark simple/advanced; and log desktop/tablet/mobile light/dark.

## Fresh pinned Linux comparison

The update-free `visual_mode=compare` dispatch ran on the workflow's pinned
`ubuntu-24.04` runner against the exact measured commit:

- [Deep Gate run 29539611526](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29539611526)
- Head SHA: `e46b67e183e5f5c7dc04f883c54c49e6925ea17b`
- Downloaded artifact: `visual-linux-report` (artifact 8391995113,
  212,237,228 bytes), preserved locally at
  `artifacts/wp4_0/linux-run-29539611526`
- JUnit aggregate: **78 tests; 51 passed, 11 failed, 16 not run**

The workflow completed with the expected overall `failure` because the visual
job was red. Check-suite readback proves it was isolated: Dependency Health
Check, Cold start (missing DB) smoke, Full E2E incl. accessibility (Chromium),
and Old-DB migration compatibility all completed successfully; only
[Visual regression (Linux baselines)](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29539611526/job/87758850015)
failed.

Every final-red report and its diff was inspected, together with the two
workout-plan retry variants that changed count. The downloaded artifact also
preserves actuals, expecteds, error contexts, traces, and videos. The 11
persistent reds were:

| Final red | Initial | Retry 1 | Retry 2 | Inspected cause |
| --- | ---: | ---: | ---: | --- |
| thumbnails › `plan-desktop-light-advanced` | 6,681 | 6,681 | 6,681 | Skip-link/signature frame plus six video/control frames |
| welcome › `welcome desktop light` | 807 | 807 | 807 | Shared navbar signature frame only |
| workout-plan › `workout-plan desktop light` | 1,125 | 8,850 | 1,125 | Signature + six video/control frames; retry 1 caught a wider table animation frame |
| workout-plan › `workout-plan desktop dark` | 957 | 51,050 | 957 | Signature + six video/control frames; retry 1 caught a wider table/card animation frame |
| workout-log › `workout-log desktop light` | 1,028 | 1,028 | 1,028 | Signature + six exercise GIF/video frames |
| workout-log › `workout-log desktop dark` | 1,012 | 1,012 | 1,012 | Signature + six exercise GIF/video frames |
| weekly-summary › `weekly-summary desktop light` | 807 | 807 | 807 | Shared navbar signature frame only |
| session-summary › `session-summary desktop light` | 807 | 807 | 807 | Shared navbar signature frame only |
| progression › `progression desktop light` | 807 | 807 | 807 | Shared navbar signature frame only |
| body-composition › `body-composition desktop light` | 807 | 807 | 807 | Shared navbar signature frame only |
| volume-splitter › `volume-splitter desktop light` | 807 | 807 | 807 | Shared navbar signature frame only |

The two workout-plan retry-1 variants returned to their original exact count
on retry 2, directly demonstrating animated-frame timing rather than a stable
layout change. The other nine persistent failures reproduced exactly on all
three attempts.

One additional test was flaky but is included in the 51 passes:
`user-profile desktop light` could not obtain two consecutive stable
screenshots on the initial attempt (successive samples 60,575, 31,220, 26,210,
and 3,145 pixels), then passed retry 1. Its diff was confined to the navbar
signature and two exercise thumbnail GIF frames.

The same 16 serial thumbnail cases listed in the Windows section did not run.
Profile and Backup introduced no persistent red. The 11 final original-attempt
counts independently reproduce the prior WP4.0a comparison ledger, while this
run additionally records the retry behavior and the recovered profile flake.

Relevant provenance:

- [WP4.0a Linux generate run 29536203369](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29536203369)
- [WP4.0a Linux compare run 29536626464](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29536626464)

## Conclusion

The fresh ledger contains two visual-seed catalog pytest reds, one persistent
Windows visual red, one persistent Windows serial-thumbnail red, 11 persistent
Linux visual reds, and one Linux initial-attempt flake that passed retry. Every
visual diff is confined to known animated signature, exercise GIF/video-control,
or transient skip-link frame pixels. No unexplained CSS/cascade regression was
found.

Post-run recomputation proved the 156 committed screenshots, Bootstrap artifact,
main live database, and five pre-existing main-checkout WP2.2 files
byte-identical to their pre-run hashes. The target branch head remained
`e46b67e`; only this evidence and its documentation were edited. WP4.0 is
complete. WP4.1 is next and has not started.

## Post-measurement integration handoff

After the immutable WP4.0 measurements above, the parallel main-checkout packet
was committed locally as `c461840` (WP2.2) followed by `0cbedac` (optional WP3.6
and final Phase-3 status documentation). Those commits do not alter or invalidate
the evidence captured at `e46b67e`; they are not yet present on this branch. The
safest next operation is to rebase this Phase-4 branch onto local `main`, merge
the four overlapping current-state documents deliberately, and rerun focused
post-rebase gates before WP4.1. No push or merge is part of WP4.0.
