# Fatigue Meter — Calibration Notes

**Status:** placeholder / sanity baseline only — **no real calibration performed.**
**Created:** 2026-05-04
**Pending:** real logged-week data and/or owner felt-experience input.

---

## Why this file exists

Phase 1 ships with §24.B threshold bands marked "starting points, not science"
(`utils/fatigue.py:SESSION_FATIGUE_BANDS` and `WEEKLY_FATIGUE_BANDS`). Stage 4
of `PLANNING.md` calls for validating these bands against real data. As of this
file's creation, **no real-data calibration has been performed.** The Stage 3
folded smokes walked on 2026-05-04 (commit `c3f692c`) were entry-evidence only;
Stage 4 calibration proper remains blocked until at least 2026-05-10 (the
≥7-day post-merge entry criterion in PLANNING.md §4.0).

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

## What this is NOT

- **Not a calibration.** "moderate" here describes how the *plan* looks, not
  how any week *felt*. The threshold-tuning loop in PLANNING.md §4.2 requires
  a felt-experience signal that this file does not provide.
- **Not authoritative.** Numbers are a snapshot of one moment in time; the
  planned program will change as routines are edited.
- **Not a green light to ship threshold tweaks.** No tuning has been performed
  or proposed from this baseline.

---

## Next steps (blocked)

Real calibration requires one of:

1. **Logged-week path.** Log enough weeks to populate `workout_log`, wait until
   2026-05-10+ (Stage 4 entry criterion), then walk PLANNING.md §4.1: pick 4
   representative weeks (one heavy, one normal, two anything), record the
   per-week fatigue score and band, and cross-check against felt experience.
2. **Hypothetical-week path.** Owner provides 4 hypothetical week shapes (sets,
   reps, RIR, movement patterns) plus a felt-experience label for each;
   assistant computes the fatigue score and the cross-check.
3. **Felt-experience-against-current-plan path.** Owner provides a
   felt-experience label for the *currently planned* program (e.g. "this plan
   as designed feels moderate / heavy / etc.") and we compare against the
   `moderate` band the engine reports here.

Until one of those paths runs, threshold values in `utils/fatigue.py` remain
the §24.B defaults — unchanged.

---

## Browser-only smokes still open

Two items from the Stage 3 §3.5 owner-required smoke checklist remain open
(genuinely browser-only, not blocking calibration entry):

- **Item 4 — 375px viewport.** Confirm badge wraps cleanly, no overflow,
  info button stays tappable. Walk during the calibration browser session.
- **Item 5 — dark-mode contrast across all four bands.** Confirm color
  tokens render with sufficient contrast. Walk during the calibration browser
  session.

The console-error sweep is also browser-only; the HTTP-200 proxy walked on
2026-05-04 confirmed no template-side crashes but cannot detect runtime JS
errors.

---

*End of calibration-notes.md. Update this file in place when real calibration
data arrives.*
