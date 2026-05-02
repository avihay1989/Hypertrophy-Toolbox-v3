---
status: DRAFT — not opened, not committed, awaiting owner approval
scope: docs-only (BRAINSTORM §26 addendum + PLANNING §3.5 wording recovery)
branch: (not yet created — Stage 1.5 box `git checkout -b feat/fatigue-meter-phase-1` still unticked)
target: main
date: 2026-05-02
---

# DRAFT — docs(fatigue): record §26 post-lock bodymap input + recover Stage 3.5 safety wording

> **Do not open this PR until the owner has explicitly approved the proposed PLANNING.md §3.5 diff and the §26 addendum.** This file is a draft. No `gh pr create` has been run.

## Summary

This is a **docs-only** PR. No production code, schema, route, template, JS module, or SCSS change ships here. Phase 1 implementation has not started — see `BRAINSTORM.md §26.1` ("before any Phase 1 implementation code has been written") and `PLANNING.md §1.5` (feature branch creation box still unchecked).

Two doc changes:

1. **`BRAINSTORM.md §26` — Post-Lock Input addendum.** Captures a user-provided MuscleWiki bodymap reference visualization received 2026-05-01 (one day after Stage 0/1 lock). Documents three options (A: keep Phase 1 as-locked, accelerate Phase 2 with bodymap as anchor; B: re-scope Phase 1 to merge in the bodymap; C: cancel and replan). Recommends Option A with one tweak (Stage 4.3 names the bodymap as Phase 2 anchor). Lists Q1–Q7 for Codex 2nd review. Explicitly does **not** modify §13 (locked decisions), §24.E (Phase 1 lock-in shape), or PLANNING.md Stages 0–3.
2. **`PLANNING.md §3.5` — Safety wording recovery (plus a one-line touch in §3.6).** Rewrites §3.5 with an explicit A → B → C → D → E execution order, marks Step D (fresh-clone smoke) optional/deferred per owner confirmation 2026-05-02, keeps Step E (restore-old-backup smoke) owner-required, and adds an explicit gate that Step E may not begin until Step B is confirmed (no restore of backup id 5 until B green). The previous §3.5 had three flat boxes with no ordering; this preserves all three behaviors (pre-flight backup verify, fresh-clone smoke, restore smoke) and makes them safe to execute. Tagged in the doc itself as **proposed** sequencing pending owner approval. **§3.6 also receives a single-line edit**: the "All boxes in 3.1–3.5 ticked" merge-gate box is amended to acknowledge that Step D may be marked skipped/deferred per its optional flag — without this, §3.5's optional/deferred Step D would be inconsistent with §3.6's "all boxes ticked" requirement.

## Non-goals (per `BRAINSTORM.md §1`, quoted verbatim)

- Fatigue meter is **informational only** — it never blocks a user action, never auto-adjusts a plan, never gates anything.
- No new modal interrupts.
- No prescriptive language in user-facing copy.

This PR ships zero user-facing surface, so the non-goals are trivially satisfied.

## Test count delta

- **pytest:** unchanged. Locked baseline is **1290 passed** (per `PLANNING.md §1.1`; +74 vs `CLAUDE.md §5`'s 1216 figure, which §1.6 will refresh in a later PR).
- **E2E (Chromium):** unchanged. Locked baseline is **422 passed** (per `PLANNING.md §1.1`; +108 vs `CLAUDE.md §5`'s 314 figure).
- This PR does not touch code, so no test count delta is expected. `/verify-suite` not re-run for this PR (docs-only).

## What this PR does NOT do

- Does **not** tick any §3.5 box (Steps A–E remain unchecked).
- Does **not** restore backup id 5.
- Does **not** start Phase 1 implementation.
- Does **not** modify `BRAINSTORM.md §13` (decisions stay locked).
- Does **not** modify `BRAINSTORM.md §24.E` (Phase 1 lock-in shape unchanged).
- Does **not** modify `PLANNING.md` Stages 0–4 outside §3.5 and the single-line §3.6 amendment described above.
- Does **not** create the `feat/fatigue-meter-phase-1` branch.
- Does **not** touch unrelated dirty files in the working tree (muscle-selector docs/tests, body_muscles_integration/, static/bodymaps/, e2e/workout-plan.spec.ts, etc. — those are separate work and will be triaged in their own PRs).

## Files changed (proposed, not yet committed)

- `docs/fatigue_meter/BRAINSTORM.md` — §26 addendum appended (does not edit §1–§25).
- `docs/fatigue_meter/PLANNING.md` — §3.5 rewritten **and §3.6 amended by one line** (other stages untouched).
- `docs/fatigue_meter/PR_DRAFT.md` — this draft file.

## Review status

**Codex 2nd review on `BRAINSTORM.md §26`** — received 2026-05-02. Verdict per question:

| Q | Verdict | Note |
|---|---|---|
| Q1 (Option A vs B) | agree-with-author | Keep Option A; re-scoping Phase 1 would invalidate the locked small-scope gate. |
| Q2 (badge alongside bodymap) | agree-with-author | Badge is useful as calibration / quick-glance surface. |
| Q3 (Phase 2 `/fatigue` page promotion) | agree-with-author | Add explicit Phase 2 promotion note so it isn't re-litigated. |
| Q4 (global "heavy" vs mostly-low per-muscle colors) | **needs-more-info** | Phase 2 must define copy explaining global vs local fatigue. **Carry forward as Phase 2 design constraint.** |
| Q5 (R7 perf for ~12–16 muscles) | agree-with-author | Re-evaluate in Phase 2; cost likely negligible if iterating already-loaded rows. |
| Q6 (schema risk for day filter) | agree-with-author | No schema risk if day filter uses existing `user_selection` fields. |
| Q7 (badge reuse — wishful thinking?) | agree-with-author | Math layer reuse is real; UI surface may be temporary but calculation work is reusable. |

**Net:** Option A is endorsed by Codex 2nd review. Q4's needs-more-info flag is recorded as a Phase 2 design constraint (copy must distinguish global vs local fatigue) and does not block this docs-only PR.

## Test plan

- [x] Codex 2nd review on `BRAINSTORM.md §26` Q1–Q7 received 2026-05-02 — Option A endorsed; Q4 carried forward as Phase 2 copy constraint.
- [ ] Owner confirms Option A endorsement and Q4 Phase-2 carry-forward as recorded above.
- [ ] Owner reviews proposed `PLANNING.md §3.5` ordering and confirms A → B → C → D → E (or supplies an override).
- [ ] Owner confirms Step D remains optional/deferred and Step E remains required.
- [ ] Owner explicitly approves the staged commit (separate approval from PR-open approval).
- [ ] After commit approval: stage only the three fatigue-meter doc files (do not stage the unrelated dirty files), commit with message `docs(fatigue): add §26 post-lock addendum + recover §3.5 safety wording`.
- [ ] Owner explicitly approves opening the PR (separate approval from commit approval). Only then push branch and open PR via `gh pr create`.

## Co-author

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
