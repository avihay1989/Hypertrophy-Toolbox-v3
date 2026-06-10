# Plan Volume Integration

> **SHIPPED / historical reference only (2026-04-25):** Plan ↔ Distribute volume progress integration shipped via `f136f60` (merged as `99f64ad`). The live app now has `utils/volume_progress.py`, `/api/volume_progress`, and `e2e/volume-progress.spec.ts`. Do not use this archived split plan as active implementation instructions.

This plan was split so implementation agents can load only the context they need.

- [Planning](PLAN_VOLUME_INTEGRATION_PLANNING.md): product context, locked decisions, current state, risks, rollback, follow-ups, and Codex review history.
- [Execution](PLAN_VOLUME_INTEGRATION_EXECUTION.md): active gate, Phase 0 audit, implementation specs, file checklist, and verification tasks.

## Recommended Agent Flow

1. Open `PLAN_VOLUME_INTEGRATION_EXECUTION.md` first.
2. Complete Phase 0 and stop at §5.5 for the post-Phase-0 confidence decision.
3. Use `PLAN_VOLUME_INTEGRATION_PLANNING.md` only when you need rationale or historical review context.

## Current Gate

- `PROCEED` for Phase 0 only.
- `PATCH_PLAN` for full implementation until Phase 0 exits cleanly and §5.5 records a `PROCEED` decision.

