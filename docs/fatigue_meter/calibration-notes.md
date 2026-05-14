# Fatigue Meter — Calibration Notes

**Status:** placeholder / sanity baseline only — **no real calibration performed.**
**Created:** 2026-05-04
**Pending:** 4 representative logged weeks, owner felt-experience labels, or
explicit Phase 2 planning.
**Parking decision:** owner chose Option 1, stay parked, on 2026-05-13.

---

## Why this file exists

Phase 1 ships with §24.B threshold bands marked "starting points, not science"
(`utils/fatigue.py:SESSION_FATIGUE_BANDS` and `WEEKLY_FATIGUE_BANDS`). Stage 4
of `PLANNING.md` calls for validating these bands against real data. As of this
file's creation, **no real-data calibration has been performed.** The Stage 3
folded smokes walked on 2026-05-04 (commit `c3f692c`) were entry-evidence only.
Stage 4 entry is complete as of 2026-05-10, but calibration proper remains
blocked until real logged-week data or owner felt-experience labels exist.

This file is a **sanity baseline only**.

---

## Current state (2026-05-04)

`workout_log` is empty: **0 rows.** There is no logged-week history to calibrate
against. The values below are computed from the planned program in
`user_selection`, not from logged sets.

### Planned-state sanity baseline

Computed via `utils.fatigue_data.compute_*_fatigue()` against the live
`user_selection` (24 rows across routines A/B/C/D):

| Metric | Score | Band |
|---|---|---|
| Weekly fatigue (sum across all routines) | 165 | moderate |
| Heaviest planned session (routine D) | 44 | moderate |
| Routine A | 39 | moderate |

These numbers were also independently confirmed at the rendered-HTML level on
the same date — see `scripts/fatigue_stage4_remaining_smokes.py` ("badge
coherence" check).

---

## 2026-05-10 — entry-session decisions

**Badge render confirmed in browser.** Owner opened `/weekly_summary` and
`/session_summary` on 2026-05-10. Both pages render the Phase 1 badge correctly:

- `/weekly_summary` → "Projected fatigue / Planned weekly volume / 165 / moderate"
- `/session_summary` → "Projected fatigue / Heaviest planned routine: D / 44 /
  moderate"

No regression. Stage 4 entry is not gated by a UI bug.

**Felt-label path declined.** The "fast sanity" §4.1 unblock route
(option iii in "Next steps" below — owner provides a felt-experience label for
the currently planned program, assistant compares against the engine's
`moderate`) was offered and declined. Reasoning:

- Both data points sit **mid-band moderate** on their respective scales.
  Band cutoffs from `utils/fatigue.py:74-85`: weekly `light < 80, moderate 80-200,
  heavy 200-320, very_heavy > 320`; session `light < 20, moderate 20-50, heavy
  50-80, very_heavy > 80`. Weekly 165 sits ~mid moderate; session 44 sits
  ~upper-mid moderate.
- Without prior felt-experience data points to anchor against, a "moderate"
  label is tautological and a "light" / "heavy" label is one isolated noise
  sample, not a calibration signal.
- Owner's read of the rendered badge — "it's not says much" — is consistent
  with the same reasoning: the badge alone offers no frame of reference for
  calibration without comparison data.

**Browser smokes 4 + 5 walked early (2026-05-10).** Both PASS via
`e2e/fatigue-stage4-smokes.spec.ts` (5/5 Playwright Chromium tests green;
screenshots + metrics in `artifacts/fatigue-stage4-smokes/`). PLANNING.md
§3.5 items 4 + 5 ticked. PLANNING.md §4.0 is also ticked as of 2026-05-10:
the early tick was accepted because `workout_log` was empty, so no real
calibration could happen in the remaining wall-clock gap anyway.

Notable observation: the badge info button bounding box at 375 px is 70×24
CSS px — below the WCAG 2.5.5 AAA tap-target minimum of 44×44 — but
consistent with the project-wide `btn-link p-0` icon-button pattern and not
a Phase 1 regression. Flagged here for future mobile-friendliness work, not
treated as a smoke-blocker.

**Path forward (unchanged):** park fatigue meter work until `workout_log` has
≥4 weeks of representative data, owner supplies felt-experience labels, or we
explicitly choose to start Phase 2 planning.

---

## 2026-05-10 — assistant-generated synthetic pass

Owner asked whether the assistant could generate representative programs and
proceed without waiting for logged `workout_log` history. We ran a synthetic
stress test against the shipped `utils.fatigue` functions. This is useful for
checking whether the default bands are internally coherent, but it is still
not a real calibration against lived training fatigue.

### Synthetic scenarios

| Scenario | Generated shape | Intended stress label | Weekly score | Weekly band | Session scores |
|---|---|---:|---:|---|---|
| Synthetic deload | 3 sessions, 8 working sets each, mostly RIR 4-5 | light | 30 | light | 10, 11, 10 |
| Synthetic normal hypertrophy | 4 sessions, 15 working sets each, mostly RIR 2-4 | moderate | 88 | moderate | 22, 22, 22, 22 |
| Synthetic hard accumulation | 4 sessions, 24 compound-biased working sets each, RIR 1 | heavy | 217 | heavy | 54, 54, 54, 54 |
| Synthetic overload | 5 sessions, 32 working sets each, mostly RIR 0-1 | very_heavy | 463 | very_heavy | 93, 93, 93, 93, 93 |

### Synthetic read

All four generated scenarios land in the intended order and in the intended
weekly band. The current planned program's weekly score of 165 remains
plausibly between the synthetic normal week (88, moderate) and synthetic hard
accumulation week (217, heavy), which supports leaving the Phase 1 defaults
alone for now.

**Decision:** no threshold changes. This pass finds no obvious inversion or
band-boundary failure, but it does not replace real calibration because the
"felt" labels were generated by the assistant rather than supplied by training
experience.

---

## 2026-05-10 — full generated calibration report

`scripts/fatigue_calibration_report.py` writes
[generated-calibration-report.md](generated-calibration-report.md): four
scenarios (deload / normal / hard / overreach) built via the starter-plan
generator with `persist=False`, scored by the shipped fatigue math, with full
per-exercise routine tables and a per-scenario `Owner label:` slot.

**Owner labels: all four blank.** No felt-experience labels have been written
into the report. `intended_anchor` is the assistant's build target, not an
owner label.

**Hard 4-day mismatch (recorded, not actioned).** The hard scenario was built
with `intended_anchor='heavy'` (`training_days=4, volume_scale=1.35,
rir_delta=-1`, 86 total sets across A/B/C/D) but computed weekly 161.9 →
`moderate`; all four routine sessions also landed `moderate` (37.0, 43.5, 37.0,
44.4). The score sits mid-band relative to the weekly moderate range (80-200),
and the denser synthetic "hard accumulation" reference above (96 sets, RIR 1
throughout, 217 → `heavy`) carried more work per session, so this is
consistent with the band boundaries rather than evidence of miscalibration.

**Decision:** no threshold changes. A single intended-vs-computed mismatch
without an owner felt label is not a calibration signal — same "felt label
required" caveat as the synthetic pass above. Re-evaluate when owner labels
are filled in or `workout_log` is no longer empty.

---

## What this is NOT

- **Not a calibration.** "moderate" here describes how the *plan* looks, not
  how any week *felt*. The threshold-tuning loop in PLANNING.md §4.2 requires
  a felt-experience signal that this file does not provide.
- **Not a real-data calibration.** The 2026-05-10 synthetic pass generated
  plausible week shapes and checked the math, but it did not observe actual
  performance, recovery, soreness, motivation, or owner felt experience.
- **Not authoritative.** Numbers are a snapshot of one moment in time; the
  planned program will change as routines are edited.
- **Not a green light to ship threshold tweaks.** No tuning has been performed
  or proposed from this baseline.

---

## Next steps (blocked)

Real calibration requires one of:

1. **Logged-week path.** Log enough weeks to populate `workout_log`, then walk
   PLANNING.md §4.1: pick 4 representative weeks (one heavy, one normal, two
   anything), record the per-week fatigue score and band, and cross-check
   against felt experience.
2. **Hypothetical-week path.** Owner provides 4 hypothetical week shapes (sets,
   reps, RIR, movement patterns) plus a felt-experience label for each;
   assistant computes the fatigue score and the cross-check. A weaker
   assistant-generated version was run on 2026-05-10; it found no reason to
   tune thresholds, but does not substitute for owner felt labels.
3. **Felt-experience-against-current-plan path.** Owner provides a
   felt-experience label for the *currently planned* program (e.g. "this plan
   as designed feels moderate / heavy / etc.") and we compare against the
   `moderate` band the engine reports here.

Until one of those paths runs, threshold values in `utils/fatigue.py` remain
the §24.B defaults — unchanged.

## 2026-05-13 — owner chose parked path

Owner chose **Option 1: stay parked** after reviewing the Stage 4 state.

This is now an intentional complete-for-now state, not an unresolved work item.
Future agents should not keep trying to make progress on fatigue calibration
without new signal. The operational handoff is
[STAGE4_PARKED_HANDOFF.md](STAGE4_PARKED_HANDOFF.md).

Proceed with other repo work unless one of the reopen criteria in that handoff
is met.

---

## Browser smoke status

Stage 3 §3.5 owner-required smoke items 4 and 5 are complete as of 2026-05-10:
the 375px viewport wrap/tappability check and dark-mode contrast sweep both
passed via Playwright Chromium. The console-error sweep remains covered only by
the HTTP-200 proxy from 2026-05-04; no additional browser work is planned before
real calibration data or Phase 2 planning exists.

---

*End of calibration-notes.md. Update this file in place when real calibration
data arrives.*
