# Learned Calibration Plan

## Status

MVP + Phase 2A + Phase 2B + Phase 2C + Phase 2D-A learned calibration are shipped on `main`; Phase 2D-B is implemented on `feat/calibration-phase-2d-b-progression-context` (PR open):

- PR #37 / `fd2e2f5`: exact-exercise learned calibration backend, settings, estimator integration, Profile controls, Workout Controls source UI/actions, workout-log notifications, tests, and E2E.
- PR #39 / `62db541`: separate profile-estimator dumbbell/total-load reference fix.
- PR #53 / `0f8b4b7`: Phase 2A read-only, ratio-gated related-exercise transfer — `utils/lift_matching.py`, additive `exercise_transfer_ratios` + `ignored_calibration_transfers` tables, `allow_related_exercise_learning` settings flag (default `0`), estimator priority (exact learned → exact log → related learned → Profile → cold-start → default), Profile toggle, Workout Controls related-source badge/trace/ignore. Ships with **zero** seeded ratios, so no behavior change until learned mode + related mode + a ratio row all exist.
- PR #54 / `bad70c6`: Phase 2B read/control-only review surface on `/user_profile` — learned-calibration list, ignored related-transfer list with per-row unignore, confirmed bulk reset-all / clear-ignored. No estimator math or priority change, no `calibration_events` table, transfer ratios remain internal. Verified: full pytest `1509 passed`; scoped Playwright (`user-profile.spec.ts` + `learned-calibration.spec.ts`) `30 passed`; CI all 8 jobs green.
- PR #55 / `d3cb404`: Phase 2C explicit promote-to-Profile action — exact learned rows can be promoted from the `/user_profile` review table into `user_profile_lifts` by writing the measured top set, basis-converted between dumbbell per-hand and total/system load. No schema change, no estimator-priority change, no silent overwrite (`REFERENCE_LIFT_EXISTS` guard + UI confirm). Verified: full pytest `1524 passed`; CI all 8 jobs green.
- PR #56 / `39fdd17`: Phase 2D-A Advisory Fatigue Context Foundation (merged 2026-06-08) — additive, post-estimate, default-off advisory layer. New single-row `fatigue_context_settings` table (independent of learned calibration) + `GET/POST /api/user_profile/fatigue_context_settings`; the estimate response gains an optional `fatigue_context` block attached **after** `estimate_for_exercise()` returns (omitted when disabled → byte-for-byte unchanged); independent Profile toggle; neutral "Fatigue context" chip/details in Workout Controls; every variant ends with "This does not change your suggestion." Reuses the shipped Fatigue Meter bands/percentages — **no new fatigue math**. Guardrails: no suggestion-number change, no estimator-priority change, no fatigue-threshold/landmark/formula change, no plan-row writes, no auto-apply; `utils/fatigue.py` untouched. Verified: 53 + 159 targeted pytest, 37 Chromium E2E, full pytest **1548 passed**; CI all 8 jobs green before merge.
- Phase 2D-B Progression Fatigue Context Surface (PR open, branch `feat/calibration-phase-2d-b-progression-context`) — extends the advisory layer to the **Progression page (`/progression`) only**, reusing the 2D-A shared toggle, settings, and copy verbatim. `/get_exercise_suggestions` now attaches the same additive `fatigue_context` block as a **sibling to `data`** (the suggestions list is byte-for-byte unchanged), built via a new **batch helper** that performs **one** `build_fatigue_page_context` build per request (no per-exercise scan, no new fatigue math). Rendered as a distinct "Fatigue context" chip + section below the suggestion cards. Guardrails: no suggestion-number change, no progression-decision change, no estimator-priority change, no fatigue-threshold/landmark/formula change, no plan-row writes, no auto-apply; `utils/fatigue.py` untouched. Verified 2026-06-08: focused pytest **115 passed**, broader affected pytest **217 passed**, full `pytest tests/` **1556 passed**; Chromium E2E progression **26 passed**, fatigue-context + user-profile **29 passed**.

**Phases 2A, 2B, 2C, and 2D-A are complete; Phase 2D-B is implemented (PR open).** Phase 2D design review is done (owner answers locked, `38d3b1c`) and the first 2D slice (2D-A) has shipped. Remaining 2D slices: **2D-B** (progression-page advisory surface) is the open PR; **2D-C** (optional manual-adjustment affordance, still no auto-apply) and **2D-D** (actual suggestion modification — gated on owner approval + Stage 4 evidence) are **not started**. See §"Phase 2D-A Technical Implementation Plan", §"Phase 2D-B Progression Fatigue Context Surface", and the 2D split below.

## Goal

Add a learned calibration layer so Workout Controls suggestions can improve from the user's logged performance, not only from Profile reference lifts, demographics, or static defaults.

Example target behavior:

- Profile suggests `Barbell Full Squat - quadriceps focused` at `81.5 kg`.
- User logs `120 kg x 6-8 @ 2 RIR`.
- After learned calibration is enabled, the same squat variation produces a better next Workout Controls suggestion.
- The app explains why the suggestion changed and lets the user keep, apply, reset, or disable learned calibration.

## Current Behavior

The shipped estimate flow prioritizes:

1. Exact exercise learned calibration, when settings mode is `suggest` and confidence is usable.
2. Last logged set for the exact exercise.
3. Profile reference lifts.
4. Cold-start demographics.
5. Static default.

Exact exercises now adapt from recent valid scored logs instead of only mirroring the latest row. Similar exercises still do not learn from logs. Cross-exercise propagation exists only through Profile reference lifts, and workout logs do not write back to those reference lifts.

## Desired Result

Workout Controls should become a smarter suggestion engine with visible source attribution:

- Exact exercise suggestions should use recent valid logged performance.
- Suggestions should use the existing double-progression rules instead of simply mirroring the last row.
- Profile values should remain the user's declared baseline unless the user explicitly promotes learned data.
- The user should always be able to see why a number was suggested.

## Non-Goals

- Do not silently overwrite Profile reference lifts.
- Do not silently rewrite existing planned program rows in `user_selection`.
- Do not auto-change historical workout logs.
- Do not treat one unusual set as permanent truth.
- Do not add related-exercise transfer in MVP.
- Do not introduce a second app-wide strength formula.
- Do not learn from incomplete logs that lack usable weight and rep data.
- Do not calibrate excluded equipment or unsupported edge cases.

## MVP Scope

The MVP should include:

- Exact exercise learned calibration only.
- Workout Controls estimator integration.
- User-visible source and explanation trace.
- Settings with two modes:
  - `off`
  - `suggest`
- Reset learned calibration per exercise.
- Backend tests for calibration logic, estimator priority, settings behavior, and database cleanup.

The MVP should not include:

- Related exercise learning.
- Auto-apply mode.
- Automatic edits to `user_selection`.
- Fatigue-aware set changes.
- Profile dashboard.
- Promote-to-Profile workflow.
- Persisting `Apply suggestion` to `user_selection`.

## Phase 2 Scope

Phase 2 can add:

- Related exercise calibration.
- Dedicated exercise-to-exercise transfer ratio table.
- Calibration event/audit history.
- Profile calibration dashboard.
- Manual `Promote to Profile reference lift` action.
- Fatigue-aware and volume-aware set suggestions.
- E2E coverage for the full related-learning UI flow.

### Phase 2 Scope Split

Phase 2 should be split into reviewable stages:

1. **Phase 2A - related-exercise suggestions only.** Add read-only transfer from one exercise's learned calibration to a related target exercise. No Profile writes, no plan-row writes, no dashboard, no auto-apply.
2. **Phase 2B - review and control surface.** Add an audit/dashboard view, ignored-transfer controls, and bulk reset only after 2A behavior is stable.
3. **Phase 2C - promote to Profile.** Add manual promote-to-Profile as its own explicit action with route tests, response-contract tests, and clear copy that it changes the user's declared baseline.
4. **Phase 2D - fatigue/volume-aware suggestions.** Keep this separate from strength transfer so fatigue logic does not become a hidden modifier inside Workout Controls.

Phase 2A is shipped (PR #53). Phase 2B is shipped (PR #54). Phase 2C is shipped (PR #55). **Phase 2D is the only remaining Phase 2 slice**, and must start with design review before coding.

## Phase 2B Review and Control Surface

### Goal

Give the user a Profile surface to *inspect* learned calibration state and *manage* ignored related transfers, **without changing estimator math**. This is a read/control layer over the rows Phase 2A already writes — it does not promote to Profile, write reference lifts, write plan rows, auto-apply, add fatigue/volume awareness, change estimator priority, or seed transfer ratios.

### Locked decisions (Opus review, 2026-06-06)

1. **Placement** — a new section on `/user_profile`, beside the existing Learned Calibration settings. No new route/page/nav entry.
2. **No `calibration_events` table** — deferred until a real audit-history consumer exists (plan §"Data Model"). 2B reads live state only.
3. **Transfer-ratio rows stay internal** — the surface shows learned calibrations + ignored pairs only. Curated ratios are not user-visible (there are zero seeded today).
4. **Bulk reset requires UI confirmation** — destructive actions (reset all learned, clear all ignored) prompt before firing.
5. **Clear ignored transfers: per-pair + global** — each ignored pair has an un-ignore (remove) control, plus a bulk "clear all ignored" control.

### Surface contents

- **Learned calibrations** (read-only list): exercise name, confidence, sample count, estimated 1RM, suggested weight + rep range, last observed date.
- **Ignored related transfers** (list with per-row remove): source exercise, target exercise, created date.
- **Bulk controls**: "Reset all learned calibration" and "Clear all ignored transfers", both confirmed.
- Existing per-exercise reset (Plan page) and per-pair ignore (Workout Controls) are unchanged.

### Backend (additive, no schema change)

New helpers in `utils/strength_calibration.py` (all reuse the caller's `DatabaseHandler`):

- `list_learned_calibrations(*, db)` — all rows, most-recently-observed first.
- `list_ignored_transfers(*, db)` — all ignored source→target pairs.
- `unignore_calibration_transfer(source, target, *, db)` — delete one pair.
- `clear_ignored_transfers(*, db)` — delete all ignored pairs.
- `reset_all_calibrations(*, db)` — delete all learned-calibration rows (does not touch settings or transfer ratios).

New routes in `routes/user_profile.py` (all `success_response()` / `error_response()`):

- `GET  /api/user_profile/calibration/dashboard` — `{learned: [...], ignored_transfers: [...]}`.
- `POST /api/user_profile/calibration/unignore_transfer` — `{source_exercise, target_exercise}`.
- `POST /api/user_profile/calibration/clear_ignored_transfers`.
- `POST /api/user_profile/calibration/reset_all`.

### Acceptance criteria

- The dashboard route returns learned rows + ignored pairs and never mutates state.
- Un-ignore removes exactly one pair and leaves the source's exact learned calibration intact (restoring related fallback for that target).
- Clear-ignored removes all ignored pairs only.
- Reset-all clears all learned-calibration rows but leaves `user_calibration_settings` and `exercise_transfer_ratios` untouched.
- Estimator output is byte-for-byte unchanged by adding this surface (no priority/math change).
- All new responses use the standard contract; bulk actions confirm in the UI.

### Out of scope for 2B

Promote-to-Profile (2C), Profile/plan-row writes, auto-apply, fatigue/volume-aware suggestions (2D), user-visible/seeded transfer ratios, and `calibration_events` history.

## Phase 2C Promote-to-Profile Plan

### Goal

Give the user one explicit action to **graduate** an exact learned calibration into their **declared Profile reference lift** — the only Phase 2 step that writes into user-declared baseline data. This is the first Phase 2 surface that mutates `user_profile_lifts`, so it is gated, confirmed, and never silent.

### Why this is not a no-op (and not the estimator change)

Estimator priority is unchanged: `exact learned → exact log → related learned → Profile → cold-start → default`. While learned mode is on and the row is usable, Workout Controls still serves the **learned** suggestion, not the promoted Profile value. Promotion's effect surfaces elsewhere:

- It becomes the **declared baseline** used when learned data and exact log fallback are unavailable (for example learned mode off or row reset/stale, with no exact target log taking priority).
- It feeds the **cross-muscle fallback chain**, **accuracy band**, **cohort bars/donut**, and **cold-start replacement** on `/user_profile`, none of which read learned-calibration rows.
- It is idempotent and reversible via backup/restore.

So promotion is "save this measured number as my permanent baseline," distinct from the live learned suggestion. UI copy must make that distinction explicit.

### Zero new schema

Both endpoints of the write already exist: source `learned_strength_calibrations` (keyed by `exercise_name`) and sink `user_profile_lifts` (keyed by `lift_key`, columns `weight_kg` + `reps`, `upsert_user_profile_lift()` in `utils/database.py`). Phase 2C adds **no table and no column** — so no `tests/conftest.py` table-list change, no `/erase-data` change (`user_profile_lifts` is already wiped), and no backup/restore snapshot-compatibility concern. This is the single biggest risk reducer for the phase.

### Locked decisions (Opus review, 2026-06-06)

1. **What gets written** — the user's **measured top set**: `scored_weight × scored_max_reps` from the source log (`learned_strength_calibrations.last_log_id` → `workout_log`), basis-converted into the target `lift_key`'s load basis (see §"Load basis"). Keeps reference-lift semantics ("what I actually lifted", run through Epley) intact and round-trips: the estimator re-derives the same e1RM. Not the progression `suggested_weight` (forward-looking) and not a 1-rep e1RM entry (loses rep context).
2. **Placement** — a per-row **"Promote to reference lift"** action in the Phase 2B learned-calibration review table on `/user_profile` only. Not on the Workout Controls trace (keeps a Profile-mutating action on the Profile page, off the fast-moving plan flow, and testable in isolation).
3. **Promotable sources** — **exact learned rows only**, with usable confidence (`medium`/`high`) and an `exercise_name` that resolves to a known `KEY_LIFTS` slug via `match_direct_lift_key()`. Not related-transfer, not exact-last-log, not Profile/cold-start/default, not `low` confidence.
4. **Overwrite policy** — **never silent**. If a reference lift already exists for the slug, the UI shows a confirm with current → new before writing. **No preservation table** in 2C (keeps it additive-minimal, consistent with the 2B deferral of `calibration_events`); the prior value stays recoverable via backup/restore. Server enforces a no-silent-overwrite guard as a backstop.

### Eligibility (a learned row is promotable only when all hold)

- A `learned_strength_calibrations` row exists for the exercise with confidence in `USABLE_SUGGEST_CONFIDENCES` (`medium`/`high`).
- `match_direct_lift_key(exercise_name)` resolves to a slug in `KEY_LIFTS` (the questionnaire vocabulary). Exercises with no direct reference-lift slug are **not** promotable.
- The source log (`last_log_id`) still exists and carries a usable `scored_weight` + `scored_max_reps`.
- The exercise is not `excluded` by `classify_tier()`.

### Load basis

Reference-lift slugs in `DUMBBELL_LIFT_KEYS` are stored **per hand**; everything else is **total/system load**. The source exercise's `scored_weight` is in the *exercise's* basis (per hand iff its equipment normalizes to `Dumbbells`). Convert source→target explicitly (same "two dumbbells = one barbell" model as `_load_basis_factor()`, but source side is the exercise, not a lift_key):

- `exercise_per_hand == lift_key_per_hand` → ×1.0
- per-hand exercise → total-load slug → ×2.0
- total-load exercise → per-hand slug → ÷2.0

Store `weight_kg = round(converted, 2)`; **no** equipment increment-rounding (reference lifts hold raw user-entered values). Store `reps = int(scored_max_reps)` (truthful measured reps; `epley_1rm` caps at 12 internally, so no pre-cap needed).

### Backend (additive, no schema change)

New helpers in `utils/strength_calibration.py` (reuse the caller's `DatabaseHandler`):

- `resolve_promotion_target(exercise_name, *, db) -> Optional[dict]` — returns the full promotion plan or `None` when not promotable: `{exercise_name, lift_key, weight_kg, reps, confidence, existing_reference}` where `existing_reference` is `{weight_kg, reps}` or `None`. Encapsulates the eligibility gates, the `last_log_id` lookup, and the basis conversion.
- `promote_calibration_to_profile(exercise_name, *, db, overwrite=False) -> dict` — resolves, enforces the no-silent-overwrite guard, writes via `upsert_user_profile_lift()`, and returns `{lift_key, weight_kg, reps, overwrote, previous}`. **Does not delete the learned row** (promotion graduates, it does not consume) and touches nothing but `user_profile_lifts`.

### Route contract (`routes/user_profile.py`, thin; `success_response()` / `error_response()`)

1. **Enrich** existing `GET /api/user_profile/calibration/dashboard` — each `learned[]` row additionally carries `lift_key`, `lift_label`, `promotable` (bool), `existing_reference` (`{weight_kg, reps}` | null), `promote_weight_kg`, `promote_reps`. Additive keys only; `ignored_transfers` unchanged; still read-only. Lets the table render the correct button label and confirm copy without a per-click round-trip.
2. **New** `POST /api/user_profile/calibration/promote` — body `{exercise: <name>, overwrite?: bool}`.
   - Missing/blank `exercise` → `error_response("VALIDATION_ERROR", ..., 400)`.
   - Not promotable (no usable learned row / unresolvable slug / missing source log) → `error_response("NOT_PROMOTABLE", ..., 400)`.
   - Existing reference present and `overwrite` falsy → `error_response("REFERENCE_LIFT_EXISTS", ..., 400)` (guard backstop; UI confirms before sending `overwrite: true`).
   - Otherwise write → `success_response(data={lift_key, lift_label, weight_kg, reps, overwrote, previous}, message="Promoted to Profile reference lift")`.

### UI copy (Profile review table)

- Button: **"Promote to reference lift"**. When not promotable, render **disabled with a tooltip**: "No matching Profile reference lift for this exercise." (discoverable + explains the gate).
- No existing value — lightweight confirm: "Save **{w} kg × {reps}** as your declared Profile reference lift for **{lift_label}**? This sets your saved baseline (separate from the live learned suggestion)."
- Overwrite — confirm shows old → new: "Replace your declared Profile reference lift for **{lift_label}**? This changes your saved baseline. Current: {old_w} kg × {old_reps}. New (from your logged set): {new_w} kg × {new_reps}. Your learned suggestion already drives Workout Controls — this only updates the baseline used when learned data is unavailable."
- Success toast: "Promoted to Profile reference lift: {lift_label} {w} kg × {reps}."
- Copy must keep "**learned suggestion**" and "**declared Profile reference**" visibly distinct.

### Data lifecycle

- Writes **only** `user_profile_lifts`. No plan-row (`user_selection`) writes, no `workout_log` rewrites, no learned-calibration deletion, no settings/transfer-ratio changes.
- No new table → `/erase-data`, `tests/conftest.py` cleanup lists, and backup/restore are unchanged and already correct.
- The learned row persists after promotion and continues to win in estimator priority while usable; promotion is idempotent.

### Estimator priority

**Unchanged.** Phase 2C does not touch the estimator chain. Migration note for the PR: promotion can change *future* suggestions only through the pre-existing Profile/cold-start fallback path and the accuracy/cohort displays — there is no priority or formula change.

### Tests

Unit (`tests/` calibration suite):
- `resolve_promotion_target` returns `None` for: no learned row; `low` confidence; `exercise_name` with no `KEY_LIFTS` slug; missing source log.
- Correct `weight_kg`/`reps` for same-basis (barbell exercise → barbell slug).
- Per-hand → total conversion (×2) and total → per-hand conversion (÷2).
- `existing_reference` populated when a reference lift already exists for the slug.
- `promote_calibration_to_profile` writes the converted value; is idempotent; **does not** delete the learned row; **does not** touch other reference lifts, settings, or transfer ratios.

Route:
- Promote success with no existing value → 200 `ok`, `user_profile_lifts` written.
- Existing + `overwrite=false` → `REFERENCE_LIFT_EXISTS`, no write.
- Existing + `overwrite=true` → overwrites, `previous` returned.
- Missing `exercise` → `VALIDATION_ERROR` 400.
- Not promotable (low confidence / unresolvable slug) → `NOT_PROMOTABLE` 400.
- Dashboard returns the new `promotable` / `existing_reference` annotations.
- All responses use `success_response()` / `error_response()` (response-contract test).

Integration (estimator priority proof):
- Log → usable learned row → promote → `user_profile_lifts` holds the measured (basis-converted) set.
- With learned mode **on**, post-promotion estimate still serves the **learned** source (priority unchanged).
- With learned mode **off** (or learned row reset) and no exact-log fallback, post-promotion estimate now serves the **promoted Profile** value (baseline took effect).
- Regression guard: non-promote actions (dashboard GET, ignore/unignore, clear-ignored, reset-all, settings) do **not** mutate `user_profile_lifts`.

E2E (after implementation, focused Chromium):
- Enable learned → log a set → open Profile review table → Promote → confirm → reference lift populated + success toast.
- Promote over an existing value shows the old → new confirm.

### Out of scope for 2C

Auto-apply, plan-row (`user_selection`) writes, promoting related/last-log/cold-start sources, an in-app preserved-history table, fatigue/volume-aware suggestions (2D), and any estimator priority/formula change.

### Open (non-blocking) defaults — proceed unless owner objects

- Non-promotable rows: **disabled button + tooltip** (vs hide). Chosen for discoverability.
- `REFERENCE_LIFT_EXISTS` guard returns **HTTP 400** (vs 200 + `reason`): the UI confirms before sending `overwrite: true`, so reaching the server without it is a true error, not the normal confirm flow.
- Store **raw measured reps** (no pre-cap at 12; `epley_1rm` caps internally).
- **No** `promoted_at`/source marker on the reference lift (no schema change; consistent with the no-preservation-table decision).

## Phase 2D Design Review Questions

Phase 2D is the remaining Phase 2 slice and is **not ready to code**. Answer these product/design questions before implementation so fatigue or volume does not become a hidden modifier inside Workout Controls.

### Core behavior

1. Should fatigue/volume affect the actual suggested **weight**, **reps**, **sets**, or only add explanation/caution text?
2. Should Phase 2D ever automatically reduce a suggestion, or should it only recommend a manual adjustment the user can accept?
3. If fatigue/volume changes a suggestion, should that change be temporary for the current planning context only, or persisted anywhere?
4. Should Phase 2D change the existing estimator priority chain, or remain a post-estimate advisory layer?

### Owner answers - Core behavior (2026-06-07)

1. Fatigue/volume should only add explanation/caution text.
2. Fatigue/volume should only recommend a manual adjustment the user can accept.
3. Not applicable for the first slice because Phase 2D does not change the actual suggestion.
4. Phase 2D remains a post-estimate advisory layer; it does not change estimator priority.

### Inputs

1. Should the feature use planned fatigue, logged fatigue, this-session fatigue, weekly fatigue, last-4-weeks fatigue, or some combination?
2. Which fatigue/volume source is authoritative when planned and logged signals disagree?
3. Should it use per-muscle fatigue only, movement-pattern fatigue, set-volume landmarks, SFR, or a combined score?
4. Should unranked/unknown muscles or `"Unassigned"` buckets block adjustments, fall back to advisory text, or be ignored?

### Owner answers - Inputs (2026-06-07)

1. Provide a user-selectable fatigue context lens: planned, logged, this-session, weekly, last-4-weeks, or combined.
2. Option C: show both planned and logged when they disagree.
3. Provide a user-selectable context lens for per-muscle landmarks, movement-pattern fatigue, SFR, or combined score, but start with the existing code-supported options first.
4. Fall back to advisory text for unranked / unknown / `Unassigned`; never block and never classify them as high/low without landmarks.

### Guardrails

1. What thresholds allow fatigue/volume to influence a suggestion?
2. Should low-confidence learned calibration disable fatigue-aware changes, or should fatigue still apply to Profile/log/default estimates?
3. Should high fatigue ever override exact learned calibration, or only decorate it with caution text?
4. How do we prevent double-counting fatigue when the user has already logged a reduced performance set that learned calibration sees?

### Owner answers - Guardrails (2026-06-07)

1. No fatigue/volume thresholds should change the actual suggestion in the first slice. Show read-only context only, e.g. “Chest fatigue: moderate. This does not change your suggestion.”
2. Fatigue context should still show even when learned-calibration confidence is low, because fatigue context is separate from strength-estimate confidence.
3. High fatigue should not override exact learned calibration in Phase 2D. It should only add caution text or recommend a manual adjustment.
4. Prevent double-counting by not automatically changing the suggestion. Learned calibration handles logged performance; Phase 2D only adds separate fatigue context and manual adjustment advice.

### Trace and UX

1. How visible should the fatigue/volume modifier be in Workout Controls trace?
2. What exact copy distinguishes strength evidence from fatigue/volume context?
3. Should the UI show a separate badge such as `Fatigue adjusted`, or keep the existing learned/profile/default source badge unchanged?
4. Should the user be able to disable fatigue-aware suggestions independently from learned calibration?

### Owner answers - Trace and UX (2026-06-07)

1. Show fatigue/volume context only inside “show the math” / details, below the strength evidence.
2. Use the label “Fatigue context” to distinguish recovery/volume advice from the strength suggestion.
3. Add a small neutral “Fatigue context” chip if useful. Do not use “Fatigue adjusted” unless the actual suggestion number is changed.
4. Yes, fatigue context should have a separate toggle from learned calibration, so strength learning can stay on while fatigue advice is hidden.

### Scope boundaries

1. Should Phase 2D be limited to Workout Controls suggestions, or also affect Profile review/dashboard surfaces?
2. Should Phase 2D include route/API changes, or can it be implemented entirely inside the estimate response trace?
3. Should Phase 2D include E2E coverage immediately, or start with backend trace/contract tests first?
4. What is explicitly out of scope: plan-row writes, auto-apply, fatigue-threshold tuning, volume-landmark changes, calibration formula changes, or all of these?

### Owner answers - Scope boundaries (2026-06-07)

1. Phase 2D should be designed as an app-wide fatigue-context system, not only a Workout Controls detail. Workout Controls remains the first and most important surface, but the settings and copy should be reusable for other surfaces later.
2. Phase 2D should include a full settings/API surface now, so the user can control fatigue-context behavior, selected lens, and visibility explicitly instead of relying only on hidden estimate-response fields.
3. Phase 2D should include both backend trace/contract tests and E2E coverage in the first implementation PR, because the feature includes both API/settings behavior and visible UI behavior.
4. All listed risky behaviors are out of scope for Phase 2D first slice: plan-row writes, auto-apply, fatigue-threshold tuning, volume-landmark changes, calibration-formula changes, and estimator-priority changes.

Note: answers 1–3 intentionally choose a broader first implementation than the conservative default. Answer 4 keeps the safety boundary: the feature may be more visible/configurable, but it still must not change suggestions automatically or tune fatigue math.

## Phase 2D Design-Review Decision List + Recommended Defaults

> **Superseded where they diverge:** the owner answered the design review on 2026-06-07 (see the "Owner answers" sections above). Those answers are authoritative. The owner kept the conservative *safety* boundary (advisory-only, manual-accept, no number change, no estimator-priority change, no fatigue-math tuning) but deliberately chose a **broader first slice** than the conservative defaults below — a full settings/API surface, user-selectable fatigue-context lenses, an app-wide-reusable design, and backend tests **plus** E2E in the first PR. Where a recommended default below conflicts with an owner answer (notably S1–S3 and I1/I3), the owner answer wins. The table is retained for rationale only.

Recommended answers below are **defaults to review, not decisions** — bias is toward the most conservative first slice that still ships visible value. Nothing here is implemented. Each default keeps Phase 2D a **post-estimate advisory layer** that never silently changes a number and never persists.

### Core behavior

| # | Question | Recommended default |
|---|---|---|
| C1 | Affect weight / reps / sets, or only explanation/caution text? | **Advisory text only.** Do not modify suggested weight, reps, or sets in the first slice. |
| C2 | Auto-reduce, or only recommend a manual adjustment? | **Recommend only.** No automatic reduction; the user accepts any change. |
| C3 | If a suggestion changes, temporary or persisted? | **Temporary / display-only.** Persist nothing (no `user_selection`, `workout_log`, or `user_profile_lifts` writes). |
| C4 | Change estimator priority chain, or stay a post-estimate advisory layer? | **Post-estimate advisory layer.** Estimator priority (`exact learned → exact log → related learned → Profile → cold-start → default`) is unchanged. |

### Inputs

| # | Question | Recommended default |
|---|---|---|
| I1 | Planned / logged / this-session / weekly / last-4-weeks fatigue, or a combination? | **Reuse the existing Fatigue Meter Phase 2 surface** (`utils/fatigue_data.build_fatigue_page_context`) — per-muscle, with the same this-session / this-week / last-4-weeks windows already shipped. Do not invent a new fatigue computation. |
| I2 | Authoritative source when planned and logged disagree? | **Logged** when present (real evidence); fall back to planned only when no logged data exists. Surface both, never silently pick. |
| I3 | Per-muscle / movement-pattern / set-volume landmarks / SFR / combined? | **Per-muscle % MRV** (already shipped + ranked) for the first slice. Defer movement-pattern and SFR-combined scoring. |
| I4 | Unranked/unknown muscles or `"Unassigned"` — block, advisory text, or ignore? | **Advisory text / neutral `—`** (never block). The six unranked labels and `"Unassigned"` stay neutral, matching the shipped `fatigue == 0 → "—"` sentinel. |

### Guardrails

| # | Question | Recommended default |
|---|---|---|
| G1 | What thresholds let fatigue/volume influence a suggestion? | **None influence the number** in the first slice (advisory only). Use the existing shipped `*_FATIGUE_BANDS` strictly for the context label — no new thresholds, no tuning. |
| G2 | Low-confidence learned calibration → disable fatigue text, or still apply to Profile/log/default? | **Always show fatigue context** regardless of strength source; it decorates, it does not gate. |
| G3 | Should high fatigue ever override exact learned calibration? | **Never override.** Decorate with caution text only. |
| G4 | Prevent double-counting when a reduced logged set already fed learned calibration? | Because the first slice **changes no number**, double-counting is structurally impossible. Copy must frame fatigue as *context about accumulated work*, distinct from the strength evidence the estimator already used. |

### Trace / UX

| # | Question | Recommended default |
|---|---|---|
| T1 | How visible is the fatigue/volume modifier in the Workout Controls trace? | A **separate, clearly-labeled advisory line** in the "show the math" trace, below the strength evidence — visually distinct, never merged into the strength explanation. |
| T2 | Copy distinguishing strength evidence from fatigue/volume context? | Strength stays under "Learned/Profile source"; fatigue gets its own eyebrow, e.g. **"Fatigue context (advisory)"**. The two must never read as one combined recommendation. |
| T3 | Separate `Fatigue adjusted` badge, or keep the existing source badge? | **Keep the existing source badge unchanged.** Add at most a neutral, non-source `Fatigue context` chip — never a badge that implies the number was adjusted. |
| T4 | Can the user disable fatigue-aware suggestions independently of learned calibration? | **Yes** — an independent display toggle, defaulting **off**, separate from the learned-calibration mode switch. |

### Scope boundaries

| # | Question | Recommended default |
|---|---|---|
| S1 | Workout Controls only, or also Profile review/dashboard surfaces? | **Workout Controls only** for the first slice. |
| S2 | Route/API changes, or entirely inside the estimate response trace? | **Inside the estimate response trace** (additive keys on the existing estimate endpoint). No new routes in 2D-A. |
| S3 | E2E immediately, or backend trace/contract tests first? | **Backend trace/contract tests first** (2D-A), then E2E once the UI exists (2D-B). |
| S4 | What is explicitly out of scope? | **All of:** plan-row writes, auto-apply, fatigue-threshold tuning, volume-landmark changes, calibration-formula changes, and any estimator-priority change. |

### Fatigue-threshold tuning gate

Phase 2D must **not** retune `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS`, must not edit `tests/test_fatigue.py` boundary tests, and must not tune `scripts/fatigue_calibration_report.py::SCENARIOS` — unless the existing Fatigue Meter Phase 2 **Stage 4 real-use evidence gate** is satisfied (≥2 same-direction real-use disagreements) **and** the owner gives a fresh go-ahead. Phase 2D consuming the shipped bands as a read-only label does not trip this gate.

## Phase 2D Recommended Implementation Split

Owner-locked 2026-06-07 (see the "Owner answers" sections above). This split reflects the owner's chosen **broader first slice**: 2D-A now bundles settings + API + estimate trace + Workout Controls UI + tests **and** E2E into one PR, instead of the conservative trace-then-UI staging the recommended-defaults table proposed. The safety boundary is unchanged — no automatic number change, no estimator-priority change, no fatigue-math tuning. Each sub-phase is independently shippable and reviewable; later sub-phases are gated on the earlier ones proving stable.

1. **2D-A — Advisory Fatigue Context Foundation.** The full first slice, shipped as one PR:
   - Add fatigue-context settings: enabled/disabled (a **separate toggle from learned calibration**, so strength learning can stay on while fatigue advice is hidden) and the selected lens/source.
   - Make the lens/source **user-selectable** (planned, logged, this-session, weekly, last-4-weeks, or combined), but start with the existing code-supported options first (`utils.fatigue_data.build_fatigue_page_context`); do not invent a new fatigue computation.
   - Add additive settings/API support so the user can control fatigue-context behavior, selected lens, and visibility explicitly — not only via hidden estimate-response fields. Design the settings + copy to be **reusable app-wide** later, with Workout Controls as the first and primary surface.
   - Add a `fatigue_context` block to the existing estimate response trace (additive keys only), sourced read-only. When planned and logged signals disagree, **show both** — never silently pick. Fall back to **advisory text / neutral `—`** for unranked / unknown / `Unassigned` muscles; never block and never classify them high/low without landmarks.
   - Render the context inside the **"show the math" / details** in Workout Controls, below the strength evidence, under the label **"Fatigue context"**. A small neutral **"Fatigue context"** chip is allowed if useful; **do not** use a "Fatigue adjusted" badge (the number does not change). Keep the existing learned/profile/default source badge unchanged.
   - **Do not** change suggested weight / reps / sets. **Do not** change estimator priority (`exact learned → exact log → related learned → Profile → cold-start → default`). Read-only context only, e.g. "Chest fatigue: moderate. This does not change your suggestion."
   - Tests: backend trace/contract tests + a regression guard proving estimate weight/reps/sets are byte-for-byte unchanged, **plus** focused Chromium E2E in the **same PR** (the slice includes both API/settings behavior and visible UI behavior).
2. **2D-B — broader app-wide fatigue-context surfaces. IMPLEMENTED (PR open, 2026-06-08).** Owner narrowed the first 2D-B surface to the **Progression page only** (`/get_exercise_suggestions`), reusing the 2D-A shared toggle/settings/copy and a new one-page-build batch helper. Still advisory-only; still no number or progression-decision change. See §"Phase 2D-B Progression Fatigue Context Surface". Further surfaces (Profile dashboard, etc.) remain a future option, not in this slice.
3. **2D-C — optional manual adjustment affordance (still no auto-apply).** A client-side "apply a fatigue-suggested adjustment" affordance the user must explicitly accept, populating Workout Controls inputs only — no persistence to `user_selection`, `workout_log`, or `user_profile_lifts`. Same client-side-only contract as the MVP `Apply suggestion`.
4. **2D-D — actual suggestion modification (much later, gated).** Only consider letting fatigue/volume change the suggested number after 2D-A..2D-C are stable, the owner **explicitly approves**, and Stage 4 real-use evidence supports it. Would require migration notes and a deliberate estimator-contract review.

## Phase 2D-A Technical Implementation Plan

> **SHIPPED to `origin/main` 2026-06-08 — PR #56, squash `39fdd17` `feat(calibration): Phase 2D-A advisory fatigue context foundation`.** Squashed the four-commit local stack (`facd241` advisory fatigue context + `34840ee` 2D-A technical plan + `38d3b1c` 2D owner decisions + docs refresh). Implemented as planned below: new `fatigue_context_settings` table, `GET/POST /api/user_profile/fatigue_context_settings`, additive `fatigue_context` block attached after `estimate_for_exercise()`, independent Profile toggle, neutral chip + advisory section in Workout Controls "show the math". New `utils/fatigue_context.py`, `tests/test_fatigue_context.py`, `e2e/fatigue-context.spec.ts`. Verified 2026-06-08: pytest 53 + 159 passed across the calibration/profile/db/migration/harness/fatigue suites; Playwright (Chromium) 37 passed across `fatigue-context` + `learned-calibration` + `user-profile`; **full `pytest tests/` 1548 passed**; CI all 8 checks green before merge. Local `main` is in sync with `origin/main` (0 commits ahead); feature branch `feat/calibration-phase-2d-fatigue-context` deleted locally + remotely. Guardrails held: no suggestion-number change, no estimator-priority change, no fatigue-threshold/landmark/formula changes, no plan-row writes, no auto-apply.

Implementation-ready preflight for **2D-A — Advisory Fatigue Context Foundation** (technical decisions locked 2026-06-07). Nothing here changes a suggested number or the estimator priority chain; it implements the owner-locked answers above as a strictly additive, post-estimate advisory layer.

### Locked technical decisions

1. **Settings storage** — a **new single-row `fatigue_context_settings` table** (`id INTEGER PRIMARY KEY CHECK (id = 1)`), **not** new columns on `user_calibration_settings`. Keeps fatigue context separate from learned calibration (owner: independent toggle) and reusable app-wide; matches the existing single-row settings pattern.
2. **User-selectable lens is two orthogonal dimensions**, not one flat list:
   - `context_source`: `planned` | `logged` | `both`
   - `context_period`: `this_session` | `this_week` | `last_4_weeks` (reuses `utils.fatigue.VALID_PERIODS`)
3. **Defaults**: `enabled = false`, `context_source = both`, `context_period = this_week`. `both` directly satisfies the owner decision to **show both planned and logged when they disagree**.
4. **`fatigue_context` is an additive post-estimate response block only.** It never alters `weight` / `sets` / `min_rep` / `max_rep` / `rir` / `rpe` / `source` / `reason` / `trace`.
5. **Attach after `estimate_for_exercise()` returns**, from the route/decorator layer (`routes/user_profile.py` `get_user_profile_estimate`), so the estimator's six early-return paths and the priority chain stay **byte-for-byte unchanged**. Do not edit `utils/profile_estimator.py` return logic.
6. **Omit/null the block when disabled** (and when no muscle resolves). Disabled → response identical to today.
7. **No suggested weight/reps/sets changes. No estimator-priority change.**
8. **No fatigue-threshold or volume-landmark tuning** — no edits to `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS`, no `tests/test_fatigue.py` boundary edits, no `scripts/fatigue_calibration_report.py::SCENARIOS` tuning (the existing Stage 4 gate still applies; consuming shipped bands as a read-only label does not trip it).
9. **Reuse existing fatigue data/helpers** (`utils.fatigue_data.build_fatigue_page_context` and the `utils.fatigue` band/period helpers); do not invent new fatigue math.
10. **Backend contract tests and focused Chromium E2E ship in the same (first) implementation PR.**

### Files likely touched

- **Backend**: `utils/database.py` (new idempotent `add_fatigue_context_settings_table()` registered in startup); `utils/fatigue_context.py` *(new — settings get/set helpers + `build_fatigue_context(exercise_name, estimate, *, db)`)*; `routes/user_profile.py` (new `GET/POST /api/user_profile/fatigue_context_settings`; attach the block after `estimate_for_exercise()` in `get_user_profile_estimate`); `app.py` (startup creation + `/erase-data` drop/reinit lists); `tests/conftest.py` (table creation + erase/clean lists).
- **Frontend**: `templates/workout_plan.html` (optional neutral chip in the provenance row); `static/js/modules/workout-plan.js` (render a distinct "Fatigue context" advisory section below the strength steps in `renderEstimateTrace`, gated on the toggle); `templates/user_profile.html` + `static/js/modules/user-profile.js` (new independent toggle section, separate from Learned Calibration); `scss/_fatigue.scss` or the Workout Plan CSS bundle (neutral chip + advisory line; rebuild via `/build-css` if SCSS changes).
- **Tests** *(authored during implementation, not in this preflight)*: `tests/test_fatigue_context.py`, additions to the estimate/route test file, `e2e/fatigue-context.spec.ts`.

### Settings table + API contract

```sql
CREATE TABLE IF NOT EXISTS fatigue_context_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    context_source TEXT NOT NULL DEFAULT 'both'
        CHECK (context_source IN ('planned','logged','both')),
    context_period TEXT NOT NULL DEFAULT 'this_week'
        CHECK (context_period IN ('this_session','this_week','last_4_weeks')),
    updated_at DATETIME
)
```

- `GET  /api/user_profile/fatigue_context_settings` → `success_response(data={enabled, context_source, context_period})`; no row → the defaults above.
- `POST /api/user_profile/fatigue_context_settings` body `{enabled?, context_source?, context_period?}` → validate against the CHECK vocabularies (reuse `VALID_PERIODS`), upsert single row, return saved settings; invalid value → `error_response("VALIDATION_ERROR", ..., 400)`.
- `GET /api/user_profile/estimate` — unchanged path/params; response gains the additive `fatigue_context` key only when `enabled` and a muscle resolves.

### `fatigue_context` response shape (additive)

```jsonc
"fatigue_context": {
  "enabled": true,
  "muscle": "Chest",            // resolved primary muscle, or null
  "has_landmarks": true,        // false → neutral advisory path
  "source": "both",             // echo of context_source
  "period": "this_week",
  "period_label": "This week (Mon–Sun)",
  "planned": { "band": "moderate", "percent_of_mrv": 64.0, "has_landmarks": true },
  "logged":  { "band": "light",    "percent_of_mrv": 28.0, "has_landmarks": true },
  "disagree": true,             // planned.band != logged.band
  "headline": "Chest fatigue: moderate (planned) · light (logged)",
  "advisory": "This is context only and does not change your suggestion.",
  "is_advisory_fallback": false // true for unranked / unknown / Unassigned
}
```

- `planned` / `logged` populated per `context_source`; with `both`, include both sides and set `disagree` — never silently pick one.
- Unranked muscle / `Unassigned` / no catalog muscle → `has_landmarks: false`, `band: null` (or `"—"`), `is_advisory_fallback: true`, neutral copy; never classified high/low, never blocks.

### UI placement + copy (owner-locked)

- Render inside the existing **"Show the math"** trace container (`#workout-estimate-trace`) as a **distinct section below** the strength steps — never merged into the strength explanation. The source badge stays unchanged.
- Optional neutral **"Fatigue context"** chip in the provenance row (reuse the `.fatigue-badge__band` chip pattern, neutral — not confidence-colored). **Do not** use a "Fatigue adjusted" badge (the number does not change).
- Eyebrow label: **"Fatigue context"**. Every variant ends with "does not change your suggestion":
  - Ranked, agree: `"Chest fatigue: moderate. This does not change your suggestion."`
  - Ranked, disagree (`both`): `"Chest fatigue: moderate (planned) · light (logged). This does not change your suggestion."`
  - Unranked / `Unassigned`: `"Fatigue context isn't ranked for this muscle yet. This does not change your suggestion."`
- Display gated behind the independent toggle (default off); off → no chip, no section, block omitted server-side.

### Test plan

- **Backend**: settings helpers (no row → defaults; round-trip; invalid value rejected); `build_fatigue_context` (ranked bands per side; `disagree`; `context_source` filtering; unranked / `Unassigned` / unknown-exercise → advisory fallback, never raises); **regression guard** proving the estimate response is byte-for-byte identical with the block disabled and that enabling it adds only `fatigue_context` (numbers, `source`, `reason`, `trace` unchanged); priority-unchanged proof across learned/log/related/profile/cold-start/default; route happy + validation paths; response-contract test; `/erase-data` + conftest lifecycle.
- **E2E (Chromium, same PR)**: enable the independent toggle on Profile (separate from learned-calibration toggle); Workout Controls shows the distinct "Fatigue context" section below strength evidence with the mandatory copy and unchanged inputs; disagree case shows both sides; unranked muscle shows neutral fallback; toggle off → nothing rendered. Follow `e2e/learned-calibration.spec.ts` conventions (reset settings in `beforeEach`, route-mock the estimate for deterministic traces).

### Open technical questions (carry into implementation, not product re-litigation)

1. Confirm the two-dimension lens (`context_source` + `context_period`) matches owner intent vs. a single flat selector.
2. Per-estimate cost: `build_fatigue_page_context` does two full-table scans + all-muscle aggregation per call; the estimate endpoint fires on each exercise selection. Mitigate by computing only when enabled; if needed, a thin single-muscle read helper over the same query (no new fatigue math) is an in-slice optimization, not a scope change. Acceptable at single-user localhost scale.
3. Verify exercise `primary_muscle_group` and the fatigue-bar muscle key normalize identically (e.g. `normalize_muscle()`), so a ranked muscle is not silently routed to the advisory-fallback path; cover with an explicit test.

## Phase 2D-B Progression Fatigue Context Surface

> **Implemented on `feat/calibration-phase-2d-b-progression-context` (PR open, 2026-06-08).** Owner-approved scope (D1–D5 locked): the second 2D slice extends the 2D-A advisory layer to the **Progression page only**. Strictly additive, advisory-only, default-off; reuses 2D-A wholesale. No new fatigue math, no suggestion-number change, no progression-decision change.

### Scope (owner decisions D1–D5)

- **D1 — Progression page only.** `/progression`'s per-exercise suggestions (`POST /get_exercise_suggestions`) are the single new surface. Not the Profile dashboard, not weekly/session summaries (those already show per-muscle fatigue and carry no live suggestion to contextualize).
- **D2 — Distinct details section + neutral chip.** Rendered below the suggestion cards in `#suggestionsFatigueContext`, never merged into a card. Same neutral "Fatigue context" chip pattern as Workout Controls; never a "Fatigue adjusted" badge.
- **D3 — Batch helper / one page build per request.** New `build_fatigue_context_batch(exercise_names, *, db)` in `utils/fatigue_context.py` reads settings once and calls the shipped `build_fatigue_page_context` **at most once** per request (lazily, only when a ranked muscle resolves) — no per-exercise scan. Per-exercise output is identical to `build_fatigue_context` (shared `_neutral_block` / `_block_from_page` helpers).
- **D4 — One shared toggle.** Reuses the 2D-A `fatigue_context_settings` row and `GET/POST /api/user_profile/fatigue_context_settings`. No per-surface toggle.
- **D5 — Copy reused verbatim.** Same `FATIGUE_CONTEXT_ADVISORY` and headline builder; mandatory "This does not change your suggestion." on every variant.

### Response contract (additive, suggestions list unchanged)

`POST /get_exercise_suggestions` keeps `data` as the suggestions **list** (existing contract, `Array.isArray` consumer unaffected) and attaches the advisory block as a **top-level sibling** `fatigue_context` on the response envelope — present only when the shared toggle is enabled and the exercise's primary muscle resolves; omitted entirely otherwise. The attach is exception-guarded so it can never break suggestions.

### Files touched

- **Backend**: `utils/fatigue_context.py` (extract `_neutral_block` + `_block_from_page`; add `build_fatigue_context_batch`); `routes/progression_plan.py` (attach sibling block, guarded).
- **Frontend**: `templates/progression_plan.html` (`#suggestionsFatigueContext` host); `static/js/modules/progression-plan.js` (`renderProgressionFatigueContext` + wiring); `static/css/pages-progression.css` (neutral chip + advisory section, light + dark; hand-maintained route bundle — no SCSS rebuild).
- **Tests**: `tests/test_fatigue_context.py` (+5 batch tests: disabled→`{}`, single↔batch parity, one page build for many exercises, unknown/blank omitted, NULL-muscle fallback without a page build); `tests/test_progression_plan_routes.py` (+3: omitted-when-disabled, additive-only-when-enabled with `data` byte-for-byte unchanged, unranked fallback); `e2e/progression.spec.ts` (+1 real-backend spec: toggle on → section + mandatory copy renders with cards present; toggle off → section absent — placed here because `progression.spec.ts` runs in CI, `fatigue-context.spec.ts` does not).

### Guardrails (all hold)

No suggested weight/reps/sets change · no progression-decision change (`data` proven byte-for-byte unchanged) · no estimator-priority change · no fatigue-threshold/landmark/formula change (`utils/fatigue.py` untouched) · no plan-row (`user_selection`) writes by the feature · no auto-apply · one shared toggle · 2D-C/2D-D out of scope.

### Verification (2026-06-08)

- Focused pytest (`test_fatigue_context` + `test_progression_plan_routes` + `test_progression_plan_utils` + `test_double_progression`): **115 passed**.
- Broader affected pytest (`test_fatigue_context` + `test_user_profile_routes` + `test_fatigue` + `test_fatigue_routes` + `test_database_user_profile` + `test_db_migration` + `test_harness_isolation`): **217 passed**.
- Full `pytest tests/`: **1556 passed** (1548 2D-A baseline + 8 new).
- Chromium E2E `progression.spec.ts`: **26 passed** (incl. the new 2D-B test).
- Chromium E2E `fatigue-context.spec.ts` + `user-profile.spec.ts`: **29 passed** (2D-A regression-clean after the engine refactor).

## Phase 2A Related-Exercise Transfer Plan

### Product Principle

Related transfer should be conservative and explainable:

- Use related logs only when the target exercise has no usable exact learned calibration and no exact last-log fallback.
- Keep the existing Profile reference chain as the fallback if related evidence is weak, stale, or hard to explain.
- Never silently overwrite Profile lifts, planned program rows, or historical logs.
- Show that a suggestion is transferred, not exact: e.g. `Related: learned from Barbell Bench Press`.
- Allow the user to reset/ignore a transferred source without deleting the source exercise's exact calibration.

### Priority

Phase 2A estimator priority should be:

1. Exact exercise learned calibration.
2. Exact last-log fallback.
3. Related exercise learned calibration.
4. Profile reference lifts.
5. Cold-start demographics.
6. Static default.

This keeps exact user evidence above transferred evidence. It also means a single target-exercise log immediately suppresses related transfer for that target.

### Settings

Use the existing reserved settings fields before adding new user-facing modes:

- `user_calibration_settings.mode`: remains `off` / `suggest`.
- `user_calibration_settings.allow_related_exercise_learning`: must default to `0`.
- No settings row must still behave as fully off.
- Related transfer can only run when `mode == 'suggest'` and `allow_related_exercise_learning == 1`.

Do not add `auto_apply` in Phase 2A.

### Transfer Eligibility

A source calibration may transfer to a target exercise only when all are true:

- Source has usable confidence (`medium` or `high`) and at least `MIN_RELATED_LOGS` valid source logs.
- Source is not stale by exact-calibration rules.
- Source and target are not the same exact exercise.
- Target has no usable exact learned calibration and no exact last-log fallback.
- Target is not excluded by `classify_tier()`.
- Source and target pass a deterministic relationship rule.
- The relationship has an explainable transfer ratio.
- The user has not ignored this source-target pair.

### Relationship Rules

Start with a deterministic, testable relationship score. Do not use fuzzy text similarity as the primary signal.

Inputs available today:

- `lift_key` from `utils.lift_matching.match_direct_lift_key()`.
- `primary_muscle_group`.
- `movement_pattern`.
- `equipment`.
- `mechanic`.
- Existing per-hand vs total-load handling via `_load_basis_factor()`.

Initial allowed relations:

1. **Same direct lift key**: e.g. barbell bench variants that map to the same key-lift vocabulary.
2. **Same primary muscle + same movement pattern + compatible mechanic**: e.g. horizontal push to horizontal push, squat to squat.
3. **Equipment-compatible pairs only**: barbell/machine/cable/dumbbell/bodyweight compatibility must be explicit, not inferred from names.

Initial blocked relations:

- Different primary muscle.
- Different movement pattern, unless manually whitelisted.
- Unilateral vs bilateral transfers until a ratio is explicitly defined.
- Bodyweight exercises where external load is not the main performance variable.
- Exercises classified as `excluded`.
- Any pair whose load basis cannot be explained as total-load or per-hand.

### Transfer Ratios

Do not hard-code one universal ratio for all related exercises.

Recommended first slice:

- Add a small `exercise_transfer_ratios` table for curated source-target pairs.
- Store directional ratios (`source_exercise_name`, `target_exercise_name`, `ratio`, `basis`, `confidence`, `notes`).
- Seed only a tiny safe set after review, or allow the table to start empty and prove the plumbing first.
- Direction matters: `bench -> incline dumbbell press` is not necessarily the same as `incline dumbbell press -> bench`.

If an MVP-without-seed is preferred, Phase 2A can first compute candidates but never return them until ratios exist. That gives tests and dashboard/audit visibility without changing Workout Controls behavior.

### Suggested Schema

Additive, idempotent tables:

#### `exercise_transfer_ratios`

- `id`
- `source_exercise_name`
- `target_exercise_name`
- `source_lift_key`
- `target_lift_key`
- `ratio`
- `load_basis`: `total_to_total`, `total_to_per_hand`, `per_hand_to_total`, `per_hand_to_per_hand`
- `relationship_type`: `same_lift_key`, `same_pattern`, `manual`
- `confidence`: `low`, `medium`, `high`
- `notes`
- `created_at`
- `updated_at`

#### `ignored_calibration_transfers`

- `id`
- `source_exercise_name`
- `target_exercise_name`
- `created_at`

Optional later table for Phase 2B:

#### `calibration_events`

- `id`
- `event_type`
- `exercise_name`
- `related_source_exercise_name`
- `payload_json`
- `created_at`

### Algorithm Sketch

When estimating a target exercise:

1. Run the shipped exact learned lookup.
2. Run the shipped exact last-log lookup.
3. If both miss, and related learning is enabled, query candidate source calibrations.
4. Join candidate source rows to explicit transfer ratios for the target.
5. Discard ignored source-target pairs.
6. Discard low-confidence, stale, excluded, or unsupported-basis candidates.
7. Convert source `estimated_1rm` through the directional ratio and load-basis factor to produce target `estimated_1rm`.
8. Use the target exercise's rep goals and the existing progression helper to derive target `suggested_weight` where possible.
9. Pick the highest-confidence candidate; tie-break by most recent `last_observed_at`, then largest sample count.
10. Return `source: "related_learned"`, `reason: "related_calibration"`, and a trace that names the source exercise and ratio.

### Trace Requirements

Workout Controls trace must show:

- Source exercise.
- Source confidence and sample count.
- Source observed top set / e1RM.
- Relationship type.
- Transfer ratio and load-basis conversion.
- Final progression decision.
- Why exact learned/log data did not apply.

Example:

```text
Source: Related learned calibration
Learned from: Barbell Bench Press, 4 recent logs, confidence high
Transfer: Bench Press -> Incline Dumbbell Press, ratio 0.72, total-load to per-hand
Estimated strength: 92 kg source e1RM -> 33 kg/hand target
Progression: maintain and build reps
```

### User Controls

Phase 2A controls:

- Enable/disable related learned suggestions in Profile.
- Reset learned data for the target exercise (already exists for exact rows).
- Ignore this related source for this target.
- Keep current.
- Apply suggestion client-side only.

Do not add promote-to-Profile or auto-apply in Phase 2A.

### Data Lifecycle

- `/erase-data` must clear transfer ratios only if they are user-generated. If curated app-default ratios are shipped, they should be recreated by startup/seed logic rather than deleted permanently.
- Deleting a source workout log should recompute the exact source calibration; related suggestions should derive from the new exact row at read time instead of storing copied related rows.
- Deleting a target log should not delete source calibration.
- Backup/restore must be safe with old snapshots missing Phase 2 tables.
- The workout-log write path must continue reusing the open `DatabaseHandler`.

### Open Decisions For Opus Review

1. Should Phase 2A ship with zero default transfer ratios first, proving plumbing without behavior change?
2. Which first 10-20 source-target pairs are safe enough to seed?
3. Should related transfer use source `suggested_weight` or source `estimated_1rm` as the ratio input?
4. Should exact last-log fallback always beat related learned evidence, or should stale/low-quality exact logs fall below high-confidence related evidence?
5. Should unilateral/bilateral pairs be blocked for the whole first slice?
6. Should machine/cable exercises require manual ratios only?
7. Is a per-exercise ignore enough, or do we need ignore-by-source-target pair from the start?
8. How should bodyweight-loaded movements be represented, or should they remain blocked?

### Phase 2A Acceptance Criteria

- With related learning disabled, estimate endpoint output is byte-for-byte equivalent to shipped MVP behavior.
- With related learning enabled but no transfer ratios, output is still unchanged.
- The first Phase 2A implementation slice ships with zero seeded transfer ratios.
- With one valid curated transfer ratio, target uses related calibration only after exact learned and exact log miss.
- Exact target log immediately suppresses related transfer.
- Low/stale source confidence does not override Profile reference lifts.
- Trace clearly names source exercise, relationship, ratio, confidence, and fallback reason.
- Reset/ignore controls do not delete the source exercise's exact learned calibration.

## Strength Formula

Learned calibration must use the existing canonical app formula:

```python
epley_1rm(weight, reps)
```

That function currently caps reps at 12:

```text
estimated_1rm = weight * (1 + min(reps, 12) / 30)
```

RIR should not be added to reps for e1RM in MVP. RIR/RPE should be used for set-quality and progression decisions, not for defining a second strength formula.

Example:

```text
120 kg x 8 @ 2 RIR
canonical e1RM = 120 * (1 + 8 / 30) = 152 kg
```

If the product later wants an RIR-adjusted e1RM, it should be changed deliberately app-wide, routed through one shared helper, documented with worked examples, and covered by re-baselined tests.

## Progression Engine

Learned calibration should not create a duplicate next-weight engine.

The estimator should delegate next-target decisions to the existing progression logic in `utils/progression_plan.py`, especially:

- effort window: RIR 1-3 or RPE 7-9
- increase weight after reaching the top of the rep range with acceptable effort
- maintain weight while building reps
- reduce weight after repeated below-range performance
- existing increment rules

Implementation should extract a public reusable helper from `utils/progression_plan.py` if needed. Do not call private progression helpers from the estimator, and do not duplicate progression rules in `utils/strength_calibration.py`.

## Settings Default

No settings row should behave as `off`.

This preserves existing behavior and protects current estimator tests. Turning learned suggestions on should be an explicit user action from the Profile settings UI.

Required regression guard:

- With no `user_calibration_settings` row, the estimate endpoint must produce the same output as the current estimator chain for existing Profile/log scenarios.

## Estimate Priority

### MVP Priority

1. Exact exercise learned calibration, only when settings mode is `suggest` and confidence is usable.
2. Exact last-log fallback.
3. Profile reference lifts.
4. Cold-start demographics.
5. Static default.

### Phase 2 Priority

1. Exact exercise learned calibration.
2. Exact last-log fallback.
3. Related exercise learned calibration.
4. Profile reference lifts.
5. Cold-start demographics.
6. Static default.

Exact-exercise evidence must always beat related-exercise transfer.

## Confidence Constants

Confidence must be numeric enough to test. Start with named constants in `utils/strength_calibration.py`:

```python
MIN_EXACT_LOGS_MEDIUM = 1
MIN_EXACT_LOGS_HIGH = 3
MAX_RECENT_DAYS = 90
STALE_AFTER_DAYS = 180
MAX_E1RM_VARIANCE_PCT_HIGH = 10
# Phase 2 reserved constants:
MIN_RELATED_LOGS = 3
MIN_RELATED_CONFIDENCE = "medium"
```

Initial confidence rules:

- `high`: at least 3 valid exact logs, latest valid log within 90 days, and e1RM variance within 10%.
- `medium`: at least 1 valid exact log within 180 days.
- `low`: valid but stale, sparse, missing effort data, or inconsistent.
- `none`: invalid, incomplete, unsupported, or settings disabled.

RIR/RPE presence can raise the quality score, but missing RIR/RPE should not invalidate a log that has plausible weight and reps.

## User Experience

Workout Controls should show a compact source line when learned suggestions are enabled:

```text
120 kg x 6-8, 2 RIR
Learned from 3 recent squat logs - confidence: high
```

Expandable details should show:

- Last valid top set.
- Canonical e1RM.
- Progression decision.
- Rounding logic.
- Confidence reason.

Example:

```text
Source: Learned calibration
Last valid top set: 120 kg x 8 @ 2 RIR
Estimated strength: ~152 kg e1RM
Progression: maintain 120 kg and aim for the top of the rep range
Confidence: high
```

## Notifications

After a meaningful scored log update:

```text
Calibration updated for Barbell Full Squat.
```

If confidence is low:

```text
Logged set saved. More data needed before learned calibration changes this exercise.
```

If calibration is disabled:

```text
Logged set saved. Learned calibration is currently off.
```

Do not notify about related exercises in MVP.

## User Actions

MVP actions:

- `Enable learned suggestions`
- `Disable learned suggestions`
- `Apply suggestion`
- `Keep current`
- `Reset learned data for this exercise`

For MVP, `Apply suggestion` is client-side only. It should populate the current Workout Controls inputs with the suggested weight/reps/RIR/RPE and should not persist to `user_selection` or call a new plan-row update endpoint. Persisting suggested values into planned program rows can be considered later as an explicit user action with its own endpoint, response-contract tests, and migration notes.

Phase 2 actions:

- `Reset all learned calibration`
- `Promote to Profile reference lift`
- `Ignore related calibration`

## Data Model

Shipped MVP tables:

### `learned_strength_calibrations`

- `id`
- `exercise_name`
- `lift_key`
- `primary_muscle`
- `estimated_1rm`
- `suggested_weight`
- `suggested_min_reps`
- `suggested_max_reps`
- `suggested_rir`
- `suggested_rpe`
- `confidence`
- `sample_count`
- `last_log_id`
- `last_observed_at`
- `source`
- `created_at`
- `updated_at`

Normalize before persisting:

- `primary_muscle` must use `normalize_muscle()`.
- `lift_key` must reuse the existing key-lift vocabulary from `utils/profile_estimator.py`.

### `user_calibration_settings`

- `id INTEGER PRIMARY KEY CHECK (id = 1)`
- `mode`: `off`, `suggest`
- `allow_related_exercise_learning`, reserved for Phase 2 and default `0`
- `min_sessions_for_related`, reserved for Phase 2
- `updated_at`

Phase 2A should add `exercise_transfer_ratios` and `ignored_calibration_transfers` only if related transfer is enabled. Phase 2B can add `calibration_events` when the Profile dashboard or audit history has a real consumer.

## Data Lifecycle

Add all calibration tables to:

- app startup table creation
- `tests/conftest.py` app setup
- `tests/conftest.py` erase/cleanup table lists
- production `/erase-data` route in `app.py`

Handle stale calibration references:

- On `/delete_workout_log`, either invalidate affected calibration rows or recompute calibration for the deleted exercise.
- On `/erase-data`, delete all calibration rows.
- Prefer recompute-on-write and invalidate-on-delete for MVP.

Backup and restore should remain safe for old snapshots. These tables are additive and idempotent; restoring a pre-calibration backup should leave learned calibration empty, with settings behaving as `off`.

## DatabaseHandler Requirement

The workout-log hook must reuse the open `DatabaseHandler`.

When `/update_workout_log` updates a row, call calibration with `db=db` inside the same handler block. Do not open a nested `DatabaseHandler` while the write path is active.

## Shipped MVP Tasks

1. Create `utils/strength_calibration.py`.
2. Add numeric confidence constants.
3. Add calibration tables in `utils/database.py`.
4. Register table creation during app startup and tests.
5. Register table cleanup in test fixtures and production erase-data flow.
6. Implement exact-exercise calibration from recent logs.
7. Use existing `epley_1rm()` for strength estimates.
8. Extract or expose a public progression helper and delegate next-target decisions to it.
9. Add calibration update after successful `/update_workout_log`, reusing the existing DB handler.
10. Invalidate or recompute calibration on `/delete_workout_log`.
11. Extend `utils/profile_estimator.py` with learned calibration only when settings mode is `suggest`.
12. Add trace fields for learned calibration.
13. Add settings and per-exercise reset endpoints.
14. Add Profile UI controls for calibration settings.
15. Add Workout Controls source badges and explanation details.
16. Add migration notes because estimator priority changes product behavior.

## Phase 2A Development Tasks

1. Lock the transfer model after Opus/product review.
2. Add additive Phase 2A tables in `utils/database.py`.
3. Register table creation during app startup and tests.
4. Register table cleanup in test fixtures and production erase-data flow.
5. Extend settings helpers to read/write `allow_related_exercise_learning`.
6. Add a small backend helper that returns eligible related candidates for a target exercise.
7. Add explicit transfer-ratio lookup and load-basis conversion.
8. Add ignored source-target pair helpers and reset/ignore endpoints.
9. Extend `utils/profile_estimator.py` with related learned lookup after exact log fallback.
10. Add trace fields for related learned calibration.
11. Add Profile UI toggle for related suggestions, gated behind learned suggestions.
12. Add Workout Controls copy/actions for related-source suggestions.
13. Add migration notes because estimator priority can change behavior.
14. Keep promote-to-Profile, dashboard, auto-apply, and fatigue-aware changes out of Phase 2A.

## Testing Plan

### Shipped MVP Unit Tests

- Canonical `epley_1rm()` is used; no RIR-adjusted formula is introduced.
- RIR/RPE affect quality/progression, not e1RM definition.
- Invalid logs are ignored.
- Incomplete logs are ignored.
- Recent logs outrank old logs.
- Exact exercise calibration updates.
- Confidence constants produce expected high/medium/low bands.
- Reset removes learned calibration.
- Missing settings row behaves as `off`.
- Settings mode `off` disables learned estimates.
- Profile fallback still works when learned calibration is disabled or unavailable.
- Existing last-log fallback still works.

### Phase 2A Unit Tests

- Relationship rules allow only explicit same-lift-key / same-pattern compatible pairs.
- Blocked relations do not produce candidates.
- Transfer ratios are directional.
- Per-hand vs total-load conversion is applied once.
- Related confidence uses source confidence, sample count, staleness, and `MIN_RELATED_LOGS`.
- Ignored source-target pairs are excluded.
- Related transfer is unavailable when no settings row exists.
- Related transfer is unavailable when `mode == 'off'`.
- Related transfer is unavailable when `allow_related_exercise_learning == 0`.
- Exact learned calibration outranks related learned calibration.
- Exact last-log fallback outranks related learned calibration.
- Related learned calibration outranks Profile only when all eligibility gates pass.

### Shipped MVP Route Tests

- `/update_workout_log` updates calibration after scored data changes.
- `/update_workout_log` reuses the existing DB handler path without nested writes.
- Estimate endpoint returns learned source only when settings mode is `suggest`.
- Estimate endpoint falls back to current behavior when no settings row exists.
- Reset endpoint clears the correct calibration rows.
- Delete-log endpoint invalidates or recomputes affected calibration.
- All new responses use `success_response()` / `error_response()`.

### Phase 2A Route Tests

- Settings endpoint persists `allow_related_exercise_learning`.
- Invalid related settings values return structured errors.
- Estimate endpoint returns related source only when both learned and related settings are enabled.
- Estimate endpoint falls back unchanged when related is disabled.
- Estimate endpoint falls back unchanged when no transfer ratio exists.
- Ignore endpoint clears only the selected source-target relation.
- Ignore endpoint does not delete source exact calibration.
- All new responses use `success_response()` / `error_response()`.

### Shipped MVP Integration Tests

- With settings off, log `120 kg` squat and verify current estimator output is unchanged.
- With settings on, log `120 kg` squat and verify learned exact-exercise output.
- Verify Profile reference lift rows are not overwritten.
- Verify current exact-log behavior remains available as fallback.
- Verify erase-data removes calibration tables.

### Phase 2A Integration Tests

- With related disabled, a source calibration plus transfer ratio does not affect target estimate.
- With related enabled and no exact target data, target estimate uses the related source.
- After logging the target exercise once, target estimate uses exact last-log fallback instead of related.
- After creating usable exact target calibration, target estimate uses exact learned instead of related.
- Deleting the source's last usable log removes the related suggestion.
- Ignoring a source-target pair restores Profile/cold-start fallback for that target.
- Profile reference lift rows are not overwritten.
- Existing exact-calibration MVP tests remain green unchanged.

### Shipped MVP E2E Tests

- User enables learned suggestions in Profile.
- User edits scored workout log.
- User sees calibration toast.
- User opens Workout Controls.
- User sees learned source badge and explanation.
- User resets learned calibration.
- User disables learned suggestions and sees fallback behavior.

### Phase 2A E2E Tests

- User enables related learned suggestions in Profile.
- User opens Workout Controls for a related target with no exact logs.
- User sees related-source badge, source exercise name, confidence, and trace details.
- User applies the related suggestion client-side.
- User ignores the related source and sees fallback behavior.
- User disables related learned suggestions and sees fallback behavior while exact learned suggestions remain available.

### Visual Testing

Workout Controls badges and Profile settings UI can change visual snapshots. If the UI changes are intentional, run scoped Chromium visual snapshot updates and document them, following the pattern used for prior visual baseline changes.

### Verification Gate

This feature touches product-risk surfaces:

- `utils/database.py`
- `tests/conftest.py`
- `routes/workout_log.py`
- `utils/profile_estimator.py`
- Profile and Workout Plan UI

Required gate:

- targeted pytest during development
- full pytest before merge
- relevant Chromium Playwright specs
- visual snapshot review if UI changes
- product-risk review focused on estimator behavior and data lifecycle

## Recommended Build Order

MVP build order is complete through item 8 below:

1. Exact exercise calibration backend.
2. Settings default-off behavior and regression guard.
3. Estimator priority integration.
4. Workout-log update hook with injected DB handler.
5. Reset and delete invalidation.
6. Trace/source display in Workout Controls.
7. Profile settings UI.
8. E2E and visual coverage.

Phase 2A recommended order:

1. Opus/product review of the transfer model and first allowed ratio set.
2. Add Phase 2A tables and cleanup/reinit paths.
3. Extend settings backend and Profile toggle.
4. Implement candidate generation behind `allow_related_exercise_learning`.
5. Implement transfer-ratio lookup and related trace construction.
6. Integrate estimator priority after exact last-log fallback.
7. Add ignore source-target endpoint and Workout Controls action.
8. Add focused pytest, then E2E for the related-source UI.
9. Run full pytest and relevant Chromium Playwright specs.

This order keeps related transfer behind an explicit second switch until the model is reviewable and testable.
