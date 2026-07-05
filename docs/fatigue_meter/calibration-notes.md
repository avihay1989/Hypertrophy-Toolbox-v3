# Fatigue Meter — Calibration Notes

**Status:** **Stage 4 closed by owner-approved felt-label review, 2026-05-20 — no
threshold changes.** Owner reviewed 5 anchors (1 real logged week + 4 generated
scenarios), 4 of 5 felt labels agreed with the computed band, the lone
disagreement was on the `hard_4d` synthetic scenario (a single data point on a
generator scenario, not on the real production case). Per PLANNING.md §4.2's
"at least 2 disagreements" gate, no threshold tuning is justified. See
"2026-05-20 — owner-approved felt-label calibration review" section below.
**`utils/fatigue.py` thresholds remain the §24.B defaults — unchanged.**
**Created:** 2026-05-04
**Stage 4 closeout:** 2026-05-20 (owner-approved override of parked state).
**Earlier history:** 2026-05-13 parked-status (Option 1) and 2026-05-20 bounded
synthetic-override / coherence analysis pass are preserved below for context.

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
the same date — see `docs/archive/2026/one-off-scripts/fatigue/fatigue_stage4_remaining_smokes.py`
(archived WP0.3) ("badge coherence" check).

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

## 2026-05-20 — owner-approved synthetic-override / coherence pass

**Framing.** Owner explicitly overrode the parked state for a bounded
synthetic-data coherence check via the existing
`scripts/fatigue_calibration_report.py`. Pass labeled
**owner-approved synthetic-data override, NOT real workout-log calibration.**
Stage 4 of `PLANNING.md` remains open; this pass does not satisfy §4.1's
"4 representative recent weeks" requirement, and
[STAGE4_PARKED_HANDOFF.md](STAGE4_PARKED_HANDOFF.md) remains the parked-state
authority.

**Source artifact (unchanged — no re-run performed).** The 2026-05-11 report at
[generated-calibration-report.md](generated-calibration-report.md) (shipped in
commit `fa8c326`, default seed 42, `persist=False`) is the source of record.
No DB rows were written by this pass; no synthetic `workout_log` rows exist;
`data/database.db` was not modified.

### Coherence result: 3 of 4 scenarios land in the intended band

| Scenario | Intended anchor | Computed weekly | Computed band | Coherence |
|---|---|---:|---|---|
| Generated deload / easy 2-day | `light` | 28.1 | light | ✓ matches |
| Generated normal 3-day hypertrophy | `moderate` | 88.5 | moderate | ✓ matches |
| Generated hard 4-day accumulation | `heavy` | **161.9** | **moderate** | ✗ one band low |
| Generated overreach 5-day strength | `very_heavy` | 419.6 | very_heavy | ✓ matches |

The "2026-05-10 — full generated calibration report" entry above already
recorded the `hard_4d` mismatch but deferred a tuning decision because the
prior bar required an owner felt label. Under the 2026-05-20 owner-approved
override bar — *"propose threshold changes only if generated scenarios
clearly contradict their intended labels"* — the `hard_4d`
intended-vs-computed contradiction qualifies for a **proposal**. It does
not qualify for an apply. **No edits to `utils/fatigue.py` have been made.**

### Two proposal hypotheses (neither applied)

**Hypothesis A — threshold drift.** Current weekly band cutoffs from
`utils/fatigue.py:WEEKLY_FATIGUE_BANDS` (per the 2026-05-10 entry above):
`light < 80, moderate 80-200, heavy 200-320, very_heavy > 320`. To make
`hard_4d` (161.9) land in `heavy`, the moderate→heavy boundary would need to
drop from 200 → ≤161, a ~19% compression of the moderate band.

- *Cost:* the currently planned program scores 165 weekly. Lowering the
  cutoff to ≤161 would flip the live `/weekly_summary` badge from
  `moderate` to `heavy` — a user-facing UX change driven by one synthetic
  data point. This is exactly the "shipped-tweak-from-one-noise-sample"
  risk that the 2026-05-10 "felt label required" gate existed to prevent.
- *Scope:* one-line edit in `utils/fatigue.py:WEEKLY_FATIGUE_BANDS`.
- *Reach:* every fatigue badge render is affected immediately.

**Hypothesis B — scenario miscalibration.** The `hard_4d` scenario's
generator parameters (`volume_scale=1.35, rir_delta=-1, 86 sets across 4
sessions`) may not actually produce absolute-heavy effort. The
hand-fabricated synthetic week from the 2026-05-10 assistant-generated
pass above (96 sets, RIR 1 throughout → 217 weekly → `heavy`) carried more
per-session work and landed in the heavy band as designed. The mismatch
therefore may live in the scenario definition, not in the band cutoffs.

- *Cost:* changes to a script file with no live UX effect.
- *Scope:* edit `scripts/fatigue_calibration_report.py::SCENARIOS["hard_4d"]`
  — raise `volume_scale` (e.g. 1.35 → 1.6), lower `rir_delta` further
  (e.g. -1 → -2), and/or add a heavier `priority_muscles` weighting, then
  re-run with the same default seed.
- *Reach:* only the synthetic coherence report; the production fatigue
  badge does not change.

### Recommended lower-risk interpretation

**Hypothesis B.** The synthetic pass probes whether the math + bands behave
coherently against an *intended* anchor that the script author defined;
if the scenario builder under-shoots its own intended anchor, the
appropriate first response is to tighten the scenario rather than retune
live thresholds against the running program. Hypothesis A becomes the
right move only when felt experience confirms the engine consistently
under-reports heavy weeks — i.e., the original §4.2 felt-label loop in
`PLANNING.md` runs against real `workout_log` data and the same direction
of bias appears there.

**Neither hypothesis has been applied here.** Picking and acting on one
requires a separate owner decision.

### Invariants honored by this pass

- No DB writes (script uses `persist=False`); not re-run in this pass.
- No `data/database.db` modification beyond the pre-existing runtime dirt.
- No edits to `utils/fatigue.py` (thresholds unchanged).
- No edits to `scripts/fatigue_calibration_report.py`
  (Hypothesis B is a proposal, not an applied edit).
- No Phase 2 work, no `/fatigue` page, no API endpoints, no SFR.
- Stage 4 real-data calibration is **NOT** claimed complete; §4.1 remains
  blocked by 0 rows in `workout_log`.
- [STAGE4_PARKED_HANDOFF.md](STAGE4_PARKED_HANDOFF.md) remains the
  parked-state authority; this override is bounded to this single
  coherence-analysis docs update.

---

## 2026-05-20 — workout_log first-data audit (partial unblock)

`workout_log` is no longer empty: **21 rows, 3 routines (A/B/C), 1 distinct
date (2026-05-20), 1 candidate ISO week (W20)**. All scored fields are
populated for all 21 rows, so the actual-logged-fatigue read uses scored RIR /
reps directly with no planned-field fallback required.

Computed actual-logged fatigue for the one week available (via
`utils.fatigue.aggregate_session_fatigue` /
`aggregate_weekly_fatigue` on the join
`workout_log LEFT JOIN exercises ON e.exercise_name = wl.exercise`, taking
`COALESCE(scored_*, planned_*)` for reps/RIR and `planned_sets` for sets —
the table has no `scored_sets` column):

| Routine | Score | Band | Sets | Scored RIR distribution |
|---|---:|---|---:|---|
| A | 38.47 | moderate | 24 | `[3,2,2,2,2,2,2]` |
| B | 39.66 | moderate | 24 | `[3,3,1,2,3,2,1]` |
| C | 40.44 | moderate | 24 | `[2,2,3,2,2,2,1]` |
| **Week W20 total** | **118.57** | **moderate** | 72 | 3 sessions in 1 day |

Sanity cross-check — same 21 rows scored against the **planned** fields
only: weekly **117.60 / moderate** (Δ +0.97 vs scored). The badge would
render the same band either way; the scored-vs-planned drift is negligible
because scored RIR moved by ≤1 in either direction across rows. Pattern
coverage is clean: 21/21 rows resolve a non-NULL `movement_pattern` via the
exercises catalog join (no neutral-fallback warnings would have been
emitted).

**Stage 4 status as of this audit alone — partially unblocked, still
insufficient.** §4.1 requires 4 representative recent weeks with varied
stress shapes; only 1 week exists. The lone week sits mid-band moderate and
is coherent with the engine's existing call. STAGE4_PARKED_HANDOFF.md was
the parked-state authority up to this point; this audit alone does **not**
satisfy §4.1's quad-week diversity requirement.

**What additional data would unblock §4.1 via the logged-week path:** 3 more
distinct calendar weeks of logged training spanning varied stress shapes
(e.g. one intentionally heavy week, one intentionally lighter week), then a
felt-experience label per week (`light` / `moderate` / `heavy` /
`very_heavy`). The owner-label path described below was taken in lieu of
waiting for those 3 weeks.

---

## 2026-05-20 — owner-approved felt-label calibration review (Stage 4 close)

**Framing.** Owner explicitly overrode the parked state to walk PLANNING.md
§4.1 / §4.2 to a decision today. Five anchors were labeled: the one real
logged week now in `workout_log` (W20, captured in the audit section above)
plus the four generator scenarios from
[generated-calibration-report.md](generated-calibration-report.md). Owner felt
labels were collected via the `light` / `moderate` / `heavy` / `very_heavy`
vocabulary that the band cutoffs use.

### Anchors, computed bands, and owner labels

| # | Anchor | Source | Weekly score | Computed band | Owner felt label | Agreement? |
|---|---|---|---:|---|---|---|
| 1 | Real W20 | `workout_log` 2026-05-20 (scored fields, 21 rows, 3 routines, 72 sets) | 118.57 | moderate | **moderate** | ✓ agree |
| 2 | deload / easy 2-day | generated, `intended_anchor='light'` | 28.1 | light | **light** | ✓ agree |
| 3 | normal 3-day hypertrophy | generated, `intended_anchor='moderate'` | 88.5 | moderate | **moderate** | ✓ agree |
| 4 | hard 4-day accumulation | generated, `intended_anchor='heavy'` | 161.9 | moderate | **heavy** | ✗ disagree (1 band low) |
| 5 | overreach 5-day strength | generated, `intended_anchor='very_heavy'` | 419.6 | very_heavy | **very_heavy** | ✓ agree |

**Result: 4 / 5 felt labels agree with computed band. 1 disagreement
(`hard_4d`, the same case already flagged in the 2026-05-20 synthetic-override
section above).**

### Decision: no threshold changes

PLANNING.md §4.2 requires "at least 2 weeks land in a band that disagrees with
felt experience" before threshold tuning is justified. With **1** disagreement,
that bar is not met. Additional reasoning:

- **The real production anchor agreed.** The single most consequential data
  point — the real logged W20 — landed in the engine's `moderate` band and the
  owner labeled it `moderate`. The live `/weekly_summary` and `/session_summary`
  badges are not mis-reporting against the program currently in use.
- **The lone disagreement is on a synthetic generator scenario, not on real
  training.** Per the 2026-05-20 synthetic-override section above, the safer
  reading of an `intended_anchor`-vs-computed mismatch is Hypothesis B
  (scenario builder under-shoots its own anchor), not Hypothesis A (live
  threshold drift). Lowering `WEEKLY_FATIGUE_BANDS[moderate→heavy]` from 200
  to ≤161 to satisfy `hard_4d` would also flip the user's current planned
  program (165 weekly) from `moderate` to `heavy` — a user-facing UX change
  driven by one synthetic data point. The cost-benefit is wrong: real data
  agrees with the engine.
- **No "same calibration bias" pattern exists.** A directional bias requires
  ≥2 disagreements pointing the same way. The single disagreement is in
  isolation — it cannot be a pattern by definition.

**Therefore `utils/fatigue.py` thresholds are NOT changed.**
`SESSION_FATIGUE_BANDS` (20 / 50 / 80) and `WEEKLY_FATIGUE_BANDS`
(80 / 200 / 320) remain at §24.B defaults. No edits to
`tests/test_fatigue.py` boundary-classification tests. No new PR for
threshold tweaks.

### Disposition of the `hard_4d` mismatch

Recorded as a known limitation in the synthetic generator, not in the
production engine. Hypothesis B's specific follow-up (retune
`scripts/fatigue_calibration_report.py::SCENARIOS["hard_4d"]` to raise
`volume_scale`, lower `rir_delta` further, and/or add heavier
`priority_muscles` weighting so the scenario's computed band matches its
own `intended_anchor`) remains a **deferred** option. It is **not** picked
up as part of this Stage 4 close because:

- it does not change live UX,
- it is a scenario-builder polish, not calibration work,
- the owner did not pre-authorize a scenario-script edit in this override.

The deferred follow-up can be picked up later as a small isolated PR if a
future synthetic pass surfaces the same mismatch again.

### What this closes vs what remains open

- **Closed:** PLANNING.md §4.1 (validate threshold bands), §4.2 (tune if
  needed), §4.3 (Stage 4 exit). Stage 4 status: **complete, owner-reviewed,
  no-change.**
- **Closed:** the "parked" status from STAGE4_PARKED_HANDOFF.md. The handoff
  document is preserved for historical context but is no longer the
  authoritative status — this calibration-notes.md is now authoritative.
- **Open (unchanged):** Phase 2 work remains explicitly NOT started. No
  `/fatigue` page, no API endpoints, no SFR, no multi-channel fatigue, no
  user-calibrated thresholds. Phase 2 entry still requires a separate
  owner decision per PLANNING.md Stage 5.

### Invariants honored by this close

- No edits to `utils/fatigue.py` (thresholds unchanged).
- No edits to `scripts/fatigue_calibration_report.py` (Hypothesis B retune
  remains a documented-not-applied deferred follow-up).
- No edits to `tests/test_fatigue.py` (no boundary changes to lock).
- No new routes, no new endpoints, no new templates, no SCSS changes, no
  new tables.
- `data/database.db` not committed; `workout_log` row count read but not
  mutated by this review.
- Other dirty working-tree files (workout_log routes/CSS/JS,
  workout_cool_integration docs, etc.) left untouched.

---

## Browser smoke status

Stage 3 §3.5 owner-required smoke items 4 and 5 are complete as of 2026-05-10:
the 375px viewport wrap/tappability check and dark-mode contrast sweep both
passed via Playwright Chromium. The console-error sweep remains covered only by
the HTTP-200 proxy from 2026-05-04; no additional browser work is planned before
real calibration data or Phase 2 planning exists.

---

*End of calibration-notes.md. Stage 4 is closed (owner-approved no-change,
2026-05-20). Update this file in place if future logged-week data prompts
a re-review.*
