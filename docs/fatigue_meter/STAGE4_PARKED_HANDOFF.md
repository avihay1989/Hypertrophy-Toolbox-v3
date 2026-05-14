# Fatigue Meter - Stage 4 Parked Handoff

**Date:** 2026-05-13
**Decision:** owner chose Option 1: stay parked.
**Status:** ready-to-proceed elsewhere; fatigue calibration remains blocked by missing signal.

---

## What is done

- Phase 1 shipped in PR #7 as commit `9d14f63`.
- Stage 4 entry is complete: post-merge smokes are recorded in `PLANNING.md` and `calibration-notes.md`.
- The rendered badges were confirmed on `/weekly_summary` and `/session_summary`.
- Synthetic checks found no reason to change thresholds.
- Current local `workout_log` has 0 rows, so there are no real logged weeks to calibrate.

## Owner decision

The owner chose **Option 1: stay parked** after the 2026-05-10 Stage 4 entry session.

This means the correct next action is not more fatigue-meter implementation. The parked state is intentional and should be treated as complete-for-now.

## Do not do

- Do not edit `utils/fatigue.py` threshold bands.
- Do not start Phase 2 planning.
- Do not add a `/fatigue` page, API endpoints, SFR, or multi-channel fatigue logic.
- Do not invent workout history or owner labels to satisfy `PLANNING.md` §4.1.
- Do not treat the generated calibration report as real calibration unless the owner fills in labels.

## Reopen criteria

Reopen Stage 4 only when at least one of these is true:

1. `workout_log` contains at least 4 representative logged weeks and the owner can label how those weeks felt.
2. The owner fills owner labels in `docs/fatigue_meter/generated-calibration-report.md`.
3. The owner explicitly overrides the parked state and asks for Phase 2 planning anyway.

## Next agent instruction

If the owner asks "where do we proceed?", proceed with the repo's current non-fatigue next safe step from `docs/MASTER_HANDOVER.md`.

For fatigue-specific work, the next safe step is:

1. Check whether `workout_log` has real rows.
2. If it does not, report that Stage 4 is still parked by owner choice and continue with another requested workstream.
3. If it does, summarize candidate recent weeks and ask the owner for felt-experience labels before proposing threshold changes.

## Optional owner worksheet

When real logged weeks exist, record this for four weeks:

| Week | Training shape | Computed score | Computed band | Owner felt label | Notes |
|---|---|---:|---|---|---|
| Heavy week |  |  |  |  |  |
| Normal week |  |  |  |  |  |
| Any week 1 |  |  |  |  |  |
| Any week 2 |  |  |  |  |  |

Owner felt label must be one of: `light`, `moderate`, `heavy`, `very_heavy`.

Threshold tuning is only justified if at least two owner labels disagree with computed bands.

