# Plan Volume Integration - Planning

> Split from `docs/PLAN_VOLUME_INTEGRATION.md` to keep agent context smaller.
> Use `PLAN_VOLUME_INTEGRATION_EXECUTION.md` for the implementation checklist and active phase gates.
> Original section numbers are preserved where useful so historical review references still resolve.
> Cross-references to §5-§13 live in the execution doc.

---

# Plan ↔ Distribute Integration — Volume Progress Panel

> **Status:** Draft v3.1 — revised after Codex 5.5 review (round 3). Phase 0 is greenlit; full implementation is gated by the post-Phase-0 hard stop in §5.5.
> **Author:** planning session with Claude Opus 4.7, 2026-04-24 → 2026-04-25.
> **Scope:** Add a live "sets remaining per muscle" side panel to `/workout_plan` that reads targets from the user's **active** volume plan.
>
> **History:** Codex's round-1 review is preserved verbatim in **Appendix A**; the round-2 verdict (which capped confidence at ~88–90%) is in **§18**. The round-1 response matrix is in §2; the round-2 response matrix is in **§2.1**; the round-3 readiness call and hard-stop requirement are in **§18.5** and **§5.5**.

---

## 1. Context & motivation

### 1.1 Problem

The **Distribute tab** (`/volume_splitter`) and the **Plan tab** (`/workout_plan`) are entirely disconnected today. Once the user decides a weekly-volume split in Distribute (e.g. "16 sets/week Chest, 18 Back, 14 Quads …") there is no in-app reinforcement of those targets while they build the routine. They either memorize the numbers, keep two tabs side by side, or export to Excel.

### 1.2 Goal

While the user is on `/workout_plan`, show them — in real time — **how many sets of each target muscle they have already planned, how many remain, and whether they are under / on / over target**. Targets come from a single "active" volume plan that the user explicitly marks in Distribute. Planned sets are computed from `user_selection` using the same primary / secondary / tertiary contribution weighting that Weekly Summary's TOTAL mode uses.

### 1.3 Non-goals

- No syncing of exercise name, reps, RIR, RPE, or weight.
- No auto-generation of exercises to meet the target (possible follow-up).
- No changes to Weekly Summary, Session Summary, or Progression computations.
- No multi-week / mesocycle modelling — a Plan == one week, as today.
- No authentication; single-user invariant preserved.

### 1.4 Design principles (inherited from CLAUDE.md)

- Targets are **informational only** — never auto-adjust or block user actions (`utils/effective_sets.py:6-7` invariant).
- Do not silently alter calculation logic or API response shapes elsewhere.
- All new JSON endpoints use `success_response` / `error_response` from `utils/errors.py`; do not add to the exceptions list in CLAUDE.md §5.
- All new modules use `get_logger()` and `DatabaseHandler` — no ad-hoc logging or sqlite3.
- **Utils never import from routes** (CLAUDE.md §2). Reversed in Draft v1 by accident; corrected throughout Draft v2.
- **No silent data loss**: every exercise row's weighted contributions must land somewhere countable; unmapped or fallback attribution must be visible to tests and logs.

---

## 2. Revision log (response to Codex 5.5 round 1)

Each row below maps a Codex section to the concrete change in this draft. The review itself is preserved verbatim in **Appendix A**.

| Codex § | Codex point | Draft v2 response |
|---|---|---|
| 13.1 | Aggregation can miscount when `advanced_isolated_muscles` mixes roles. | **§7** rewritten. P/S/T role columns are the authoritative source of weighted contributions (1.0 / 0.5 / 0.25). Isolated tokens may only refine the **primary** role, and only when `advanced_token_belongs_to_coarse(token, coarse)` returns True. Secondary / tertiary always use a representative advanced bucket. |
| 13.2 | Taxonomy gap is bigger than the draft said — ~16 unmapped P/S/T values in the live DB. | **§5 (Phase 0)** added as a gating phase. Mandates a live DB audit and an explicit product-decision table before any code ships. Tests in **§9.1.1** fail loudly if any current P/S/T value has no Basic rollup. |
| 13.3 | `exercise_isolated_muscles` tokens are dirtier than stated; current `normalize_advanced_muscles()` drops many. | **§6.1** now defines `TOKEN_TO_ADVANCED` with explicit entries for all dirty tokens found in Phase 0. Tests in **§9.1.1** fail if any current isolated token is unmapped and not explicitly marked as ignored. |
| 13.4 | Do not extend `ADVANCED_MUSCLE_GROUPS` without product review. | Draft v2 **does not** extend the splitter's Advanced UI. `quadriceps` (umbrella), `serratus-anterior`, and similar handled in the mapping layer only — `quadriceps` → distributed across quad advanced sub-buckets by default; `serratus-anterior` → Basic `Chest` / Advanced representative `mid-lower-pectoralis`. See §6.1.5. |
| 13.5 | Migration missing from `/erase-data` and transaction safety missing in activate. | **§4.3** updated — migration is called at startup, at `/erase-data`, and in `tests/conftest.py`; plus the migration is invoked *internally* from `add_volume_tracking_tables()` so all current call sites pick it up automatically. **§8.1.1** specifies a single DB transaction for activate using `commit=False` + explicit commit. |
| 13.6 | Bootstrap offcanvas CSS is excluded from the custom bundle; panel would render unstyled. | **§10.1** switched to a **local drawer** component implemented in `scss/pages/_workout_plan_volume_panel.scss` (new) plus small JS in `plan_volume_panel.js`. No Bootstrap offcanvas dependency; no bundle expansion. |
| 13.7 | Use `api` / `apiFetch` from `fetch-wrapper.js`, not `apiCall`; initialize via `static/js/app.js`. | **§10.2** corrected — module exposes `initializePlanVolumePanel()` imported and called in `initializeWorkoutPlan()` inside `static/js/app.js`. Network calls use `api` from `fetch-wrapper.js`. No inline scripts. |
| 13.8 | Event name too narrow — "sets-changed" misses replace, clear, starter-plan. | **§10.3** renamed event to `workout-plan:volume-affecting-change` with the full trigger list (add, set-count edit, replace, delete, clear, starter plan generate, backup restore while on page). Excluded triggers enumerated explicitly. |
| 13.9 | `status` overloads splitter range status with plan progress status. | **§8.2** response schema splits into `target_status` (`low`/`optimal`/`high`/`excessive`) and `progress_status` (`no_target`/`unplanned_target`/`under`/`on_target`/`over`/`planned_without_target`). |
| 13.10 | Star-only activation is easy to miss. | **§10.5** adds (a) a `Save & Activate` button beside `Export Volume Plan`, (b) an `Active` badge in the history table with `aria-label`, (c) an active-plan summary in the Plan tab header, (d) a post-save toast with a direct `Activate` action. |
| 13.11 | API payload should include diagnostics. | **§8.2** payload now includes a `diagnostics` block with `unmapped_muscles`, `fallback_count`, and `ignored_tokens`. Hidden from the UI; asserted in tests. |
| 13.12 | `utils/volume_progress.py` should be small helpers; do not import routes from utils. | **§6.2** defines eight small helpers. Muscle list constants moved to `utils/volume_taxonomy.py`; `routes/volume_splitter.py` re-imports them from there (backwards-compatible). |
| 13.13 | Need strict pre-flight taxonomy tests plus expanded aggregation tests. | **§9.1** expanded with Codex's full test list plus pre-flight coverage tests that run against the live DB. |
| 13.14 | Backend refetch after volume-affecting changes (no client-side guessing); perf sanity check. | **§8.3** specifies backend-only source-of-truth; **§9.4** adds a performance sanity check. |
| 13.15 | Add Phase 0 taxonomy audit. | **§5** is Phase 0. No code beyond Phase 0 may merge until Phase 0 tests pass on the live DB. |
| Opus refinement | Push back on extending Advanced UI. | Handled — see response to §13.4 above. |
| Opus refinement | Prefer local drawer over importing offcanvas SCSS. | Handled — see response to §13.6 above. |
| Opus refinement | Surface active plan in Plan tab header too. | Handled — see response to §13.10 above. |

### 2.1 Revision log — response to Codex 5.5 round 2 (§18.1 + §18.2)

Each row maps a round-2 must-fix (or secondary recommendation) to the concrete change in Draft v3.

| Round-2 § | Point | Draft v3 response |
|---|---|---|
| 18.1.1 | 633 rows have `primary_muscle_group IS NULL`; 252 of those carry `advanced_isolated_muscles`. §7.2 skips blank roles → silent zero. | **§5.1** adds two new audit queries (blank-P/S/T census, blank-P/S/T-with-isolated-tokens). **§5.2** adds an explicit decision row `D-blank-pst` (default: `ISOLATED_ONLY` fallback path, with a secondary option to `BACKFILL` or `EXCLUDE_WITH_DIAGNOSTIC`). **§7.2** handles the all-blank case per the Phase-0 decision; never falls through silently. **§9.1** Diagnostics gains `blank_pst_rows: list[str]`. **§12.2** adds `test_selected_exercise_with_blank_pst_is_diagnostic_not_silent_loss`. **§14** adds risk R10. |
| 18.1.2 | `fetch_planned_rows()` reads raw CSV `advanced_isolated_muscles` when the canonical store is `exercise_isolated_muscles`. | **§9.1** SQL rewritten to `LEFT JOIN exercise_isolated_muscles` and build the token list server-side. CSV column kept as audit/diagnostic source only. **§12.2** adds `test_fetch_planned_rows_prefers_mapping_table_tokens`. |
| 18.1.3 | `target_status` has no persisted source — `save_volume_plan` hardcodes `status='optimal'` and splitter UI computes locally from editable ranges. | **§8.2.1** added: `target_status` is recomputed server-side from the **default range table** in `utils/volume_progress.py`; the default table is documented as canonical and covers every `BASIC_MUSCLE_GROUPS`/`ADVANCED_MUSCLE_GROUPS` member. Custom range edits in the splitter UI are **not persisted** today — this is a known limit, explicitly documented in §8.2.1 and surfaced in §16 as a follow-up. |
| 18.1.4 | Mapped tokens that fail `advanced_token_belongs_to_coarse()` are dropped silently; §7.3 claims they're recorded but §7.2 pseudocode doesn't. | **§7.2** pseudocode updated: every rejected token is appended to `diagnostics.rejected_tokens` with its coarse role context. **§7.3** guarantee made executable. **§9.1** Diagnostics adds `rejected_tokens: list[dict]` (`{token, role, coarse}` tuples). **§12.2** adds `test_mapped_wrong_family_token_is_rejected_with_diagnostic`. |
| 18.1.5 | Activate endpoint clears active state before verifying the new plan exists → could leave zero rows active on a stale id. | **§8.1.1** rewritten: pre-check plan existence (`SELECT 1 ... LIMIT 1`), then run the two writes with explicit `commit=False`, then verify rowcount on the setter, then commit. Rollback if either check fails. `Deactivate` is a single `WHERE id = ?` update and is idempotent (no pre-read). Removed the obsolete "if DatabaseHandler does not expose commit=False" sentence — it already does (`utils/database.py:200-206`). |
| 18.2 | Secondary tests + audit doc scope. | §12.2 gains the three secondary tests; §5.3 deliverables clarify that `docs/VOLUME_TAXONOMY_AUDIT.md` must include (a) the blank-P/S/T census, (b) rows that carry isolated tokens without a coarse group, and (c) incidence counts for both. §14 adds R10 as requested. |

After these edits Opus's self-assessed confidence matched the 95% bar: no aggregation path loses contribution silently, every failure mode is either counted or diagnosed, the mapping table is the canonical token source, the activation transaction is guarded, and `target_status` has one documented source of truth. Codex round-3 narrows that gate: Phase 0 may proceed, but full implementation must wait for the §5.5 post-Phase-0 confidence assessment.

---

## 3. Decisions locked with the user (unchanged from v1)

| # | Decision | Choice |
|---|---|---|
| D1 | Which saved volume plan drives the Plan tab? | Add **is_active** concept — exactly one plan active at a time. |
| D2 | How are exercise sets attributed to splitter muscles? | **Primary + weighted secondary/tertiary** (TOTAL mode), 1.0 / 0.5 / 0.25. |
| D3 | What counts as "weekly planned sets"? | **Sum across ALL routines** in `user_selection`. |
| D4 | Where does the UI live? | **Collapsible side panel** on `/workout_plan` (local drawer implementation — not Bootstrap offcanvas). |

---

## 4. Current state (verified during Phase 1)

### 4.1 Distribute tab
- Blueprint: `routes/volume_splitter.py`.
- `BASIC_MUSCLE_GROUPS` — 16 muscles (`routes/volume_splitter.py:15-19`).
- `ADVANCED_MUSCLE_GROUPS` — 34 muscles (`routes/volume_splitter.py:21-45`).
- Persistence: `volume_plans(id, training_days, created_at)` + `muscle_volumes(...)` — **no `is_active`, no `mode`** (`utils/database.py:467-489`). Cascade delete on plan delete.
- Mode is not persisted today — JS infers from label content.

### 4.2 Plan tab
- Blueprint: `routes/workout_plan.py`. Core table `user_selection` at `utils/db_initializer.py:162-206`.
- No per-muscle aggregation endpoint. No muscle summary UI in `templates/workout_plan.html` (tabs at lines 271-286).
- No Basic/Advanced mode toggle on this page.

### 4.3 Reusable building blocks

| Need | Reuse | Location |
|---|---|---|
| Contribution weights (1.0 / 0.5 / 0.25) | `MUSCLE_CONTRIBUTION_WEIGHTS` | `utils/effective_sets.py:84-88` |
| Raw counting | `CountingMode.RAW` | `utils/effective_sets.py:20-23` |
| TOTAL vs DIRECT_ONLY | `ContributionMode.TOTAL` | `utils/effective_sets.py:26-29` |
| Per-row helper (optional) | `calculate_effective_sets(..., RAW, TOTAL)` | `utils/effective_sets.py:227-304` |
| Aggregation loop pattern | `_aggregate_muscle_volumes()` | `utils/session_summary.py:72-150` |

Note: Draft v2 will not invoke `calculate_effective_sets()` for this feature. It is overkill for raw-set attribution and would couple us to its EFFECTIVE-mode internals. We use its constants and mirror its shape, but compute the simple weighted sum inline for clarity.

---


---

<!-- Sections 5-13 moved to PLAN_VOLUME_INTEGRATION_EXECUTION.md. -->

## 14. Risks & mitigations (updated)

| # | Risk | Mitigation |
|---|---|---|
| R1 | Taxonomy drift over time (new exercises introduce unmapped tokens). | Strict tests in §12.1 run in CI; adding an unmapped token fails the build. |
| R2 | Product decisions for `open — user` rows in §5.2 never get made; feature stalls. | Phase 0 exit criterion requires a decision per row before Phase 1 begins. |
| R3 | Secondary/tertiary Advanced attribution is coarse by design. | Surfaced via `diagnostics.fallback_count`; documented as a known limit of the current `exercises` schema; future schema work could add role-specific isolated tokens. |
| R4 | Two simultaneous activations from two browser tabs (single-user, but the user opens two tabs). | Each click is atomic; the last write wins; UI refetches history after every activate/deactivate so state converges. |
| R5 | Legacy `volume_plans` rows default to `mode='basic'` even if originally Advanced. | User can re-save; not a correctness risk (targets survive). |
| R6 | Program-backup restore imports an `is_active` plan into a DB that already has one. | Add TODO in `utils/program_backup.py` to zero `is_active` on import. Out of scope here; flagged. |
| R7 | Custom drawer drifts visually from other surfaces over time. | Reuse existing status-dot tokens and typography variables; partial lives next to other page-scoped SCSS. |
| R8 | Missed event-emission site leaves stale drawer data. | E2E `replace_exercise` and `clear_plan` specs specifically guard the hard-to-find triggers. |
| R9 | Response-contract regression. | `test_endpoint_response_contract` + CLAUDE.md §5 exceptions list audited. |
| R10 | Blank-P/S/T exercises (≈633 rows, ≈252 with isolated data) silently score zero if the feature ships before Phase 0 resolves them. | Phase-0 audit queries in §5.1 + decision `D-blank-pst` in §5.2.1 + `BLANK_PST_STRATEGY` constant + `test_selected_exercise_with_blank_pst_is_diagnostic_not_silent_loss`. Risk cannot persist past Phase 0 exit. |
| R11 | `target_status` drifts between what the splitter UI shows (editable ranges, not persisted) and what the drawer shows (default-range table). | §8.2.1: backend uses the documented default-range table as the single source of truth; custom range edits surfaced as a follow-up in §16. |
| R12 | Mapped-but-wrong-family tokens (e.g. `long-head-triceps` on a `Chest` primary row) are discarded silently. | §7.2 records them in `diagnostics.rejected_tokens`; `test_mapped_wrong_family_token_is_rejected_with_diagnostic` enforces it. |

---

## 15. Rollback

Additive only.

- [ ] Drop partial unique index: `DROP INDEX IF EXISTS idx_volume_plans_active;`
- [ ] Leave `is_active` and `mode` columns in place (SQLite drop-column requires table rebuild; not worth the risk).
- [ ] Unregister the `GET /api/volume_progress` handler; 404 degrades the drawer to error state which shows the empty CTA.
- [ ] Remove drawer markup + JS module.
- [ ] Do not rerun any data migration.

---

## 16. Out-of-scope follow-ups

- Auto-suggest exercises to close per-muscle gaps.
- Multi-week / mesocycle progression of targets.
- Weekly Summary cross-reference (actual logged volume vs targets).
- Secondary/tertiary role-specific isolated-muscle columns on `exercises` (would remove the coarse-fallback limit in Advanced mode).
- Program-backup safety: clear `is_active` on import (flagged as R6 TODO).
- Persist custom recommended ranges (`volume_plans.custom_ranges JSON`) so the drawer's `target_status` can honor per-plan overrides instead of the default-range table (see §8.2.1 and R11).
- Backfill `primary_muscle_group` for the ≈633 blank rows (related to R10). Only relevant if `BLANK_PST_STRATEGY='backfill'` is chosen in Phase 0.

---

## 17. Review checklist for Codex round 2 / Gemini

Please verify that each Codex 5.5 point has a matching change by spot-checking these:

- [ ] §13.1 → §7 aggregation is role-authoritative; `advanced_token_belongs_to_coarse` gates refinement; regression test `test_bench_press_with_mixed_isolated_tokens` in §12.2 covers the exact example Codex cited.
- [ ] §13.2 → §5 Phase 0 gate with §5.2 decision table; strict tests in §12.1 fail on any unmapped P/S/T value.
- [ ] §13.3 → `TOKEN_TO_ADVANCED` and `IGNORED_TOKENS` defined in §6.1; test `test_every_isolated_token_handled` proves coverage over the live DB.
- [ ] §13.4 → `ADVANCED_MUSCLE_GROUPS` is NOT extended; umbrella tokens handled via `DISTRIBUTED_UMBRELLA_TOKENS`; serratus via `TOKEN_TO_ADVANCED` only.
- [ ] §13.5 → migration called from startup, `/erase-data`, tests, and internally from `add_volume_tracking_tables()`; activate uses single transaction per §8.1.1.
- [ ] §13.6 → local drawer, no Bootstrap offcanvas dependency; partial imported in `scss/custom-bootstrap.scss`.
- [ ] §13.7 → module uses `api` from `fetch-wrapper.js`; initialized from `static/js/app.js`.
- [ ] §13.8 → event is `workout-plan:volume-affecting-change`; trigger list matches Codex's recommendation; non-triggers enumerated.
- [ ] §13.9 → `target_status` and `progress_status` split; six explicit progress-status values; 0.01 tolerance.
- [ ] §13.10 → Save & Activate button, active badge with `aria-label`, header summary on both tabs, post-save toast.
- [ ] §13.11 → payload includes `diagnostics` with `unmapped_muscles`, `ignored_tokens`, `fallback_count`.
- [ ] §13.12 → eight small helpers in §9; no `routes/` imports; constants moved to `utils/volume_taxonomy.py`.
- [ ] §13.13 → strict Phase-0 tests in §12.1; expanded aggregation tests in §12.2.
- [ ] §13.14 → backend is source of truth (§8.3); perf sanity in §12.4.
- [ ] §13.15 → Phase 0 exists as §5; exit criterion blocks Phase 1.

Round-2 (§18.1) spot-checks:

- [ ] §18.1.1 → §5.1 blank-P/S/T audit queries, §5.2.1 `D-blank-pst` decision, §7.2 step 1 pseudocode, `diagnostics.blank_pst_rows`, R10, `test_selected_exercise_with_blank_pst_is_diagnostic_not_silent_loss`.
- [ ] §18.1.2 → §9.1 SQL prefers `exercise_isolated_muscles`, `diagnostics.csv_fallback_count`, `test_fetch_planned_rows_prefers_mapping_table_tokens`, `test_fetch_planned_rows_falls_back_to_csv_when_mapping_empty`.
- [ ] §18.1.3 → §8.2.1 default-range table as source of truth, R11, `test_target_status_computed_from_default_ranges`, `test_default_recommended_ranges_cover_all_muscles`.
- [ ] §18.1.4 → §7.2 rejected-token diagnostics, §7.3 executable guarantee, `diagnostics.rejected_tokens`, R12, `test_mapped_wrong_family_token_is_rejected_with_diagnostic`.
- [ ] §18.1.5 → §8.1.1 existence + rowcount + rollback guards, `test_activate_nonexistent_plan_returns_404_and_preserves_active`, `test_activate_rollback_when_set_row_disappears`, `test_deactivate_idempotent_for_inactive_plan`.

---

## 18. Codex round-2 review — readiness verdict

> **Reviewer:** Codex 5.5, 2026-04-24.
> **Verdict:** Ready to start **Phase 0** immediately, but not yet 95% ready for full implementation.
> **Confidence:** ~88–90% as written. Expected to reach ~95% after the must-fix items below are folded into the plan.

The draft is substantially stronger than v1. It correctly treats taxonomy and attribution as the core risk, makes P/S/T roles authoritative, avoids Bootstrap offcanvas, broadens refresh events, separates target/progress status, and adds much better backend and E2E coverage. The remaining gaps are mostly precision problems: an implementer could follow the current text and still produce misleading counts in edge cases.

### 18.1 Must-fix before claiming 95%

1. **All-P/S/T-blank exercises can still silently count as zero.**
   - Live DB observation: `exercises` currently has **633 rows with `primary_muscle_group IS NULL`**, including **252 rows with non-empty `advanced_isolated_muscles`**.
   - Current §7.2 skips blank roles. That conflicts with the "no silent data loss" guarantee in §7.3 if one of these exercises is selected.
   - Required plan update: add a Phase-0 decision and tests for rows where primary/secondary/tertiary are all blank. Options include backfilling metadata, explicitly excluding these rows with diagnostics, or allowing a carefully documented isolated-token fallback only for this case.

2. **Token source should prefer `exercise_isolated_muscles`, not raw CSV.**
   - §9.1 currently fetches `ex.advanced_isolated_muscles` only.
   - The app already maintains normalized tokens in `exercise_isolated_muscles`, and Weekly Summary already uses that table.
   - Required plan update: make `fetch_planned_rows()` pull isolated tokens from `exercise_isolated_muscles` as the primary source, with `advanced_isolated_muscles` CSV only as a fallback or audit source.

3. **`target_status` needs a single source of truth.**
   - §8.2 promises `target_status`, but §11 only persists `mode`.
   - Current save path persists raw volumes and `utils/volume_export.py` hardcodes saved `status='optimal'`; splitter status is actually computed from current range settings.
   - Required plan update: either persist status/ranges on save, or explicitly recompute `target_status` from default ranges and document that custom range edits are not persisted.

4. **Rejected but mapped wrong-family tokens need diagnostics.**
   - §7.2 records unknown tokens, but tokens that map successfully and then fail `advanced_token_belongs_to_coarse()` are just ignored for refinement.
   - §7.3 says dropped tokens are recorded, but the pseudocode does not do that.
   - Required plan update: add `diagnostics.rejected_tokens` or equivalent, log these once per request, and assert it in the mixed Bench Press regression test.

5. **Activation transaction needs existence and rowcount guards.**
   - §8.1.1 clears the current active plan before setting the requested one.
   - Required plan update: check that `plan_id` exists before clearing active state, or verify the final update rowcount and rollback on zero rows. Deactivate should clear only `WHERE id = ?` and remain idempotent.

### 18.2 Secondary recommendations

- Add `test_selected_exercise_with_blank_pst_is_diagnostic_not_silent_loss`.
- Add `test_fetch_planned_rows_prefers_mapping_table_tokens`.
- Add a direct test that mapped-but-wrong-family tokens are present in diagnostics, not only absent from attribution.
- Clarify whether `docs/VOLUME_TAXONOMY_AUDIT.md` must include blank P/S/T rows and catalog rows with isolated tokens but no coarse muscle group.
- Consider adding the all-blank P/S/T issue to §14 risks until Phase 0 resolves it.

### 18.3 Implementation gate

Greenlight:
- Phase 0 taxonomy audit and `utils/volume_taxonomy.py` skeleton.

Do not greenlight yet:
- Full backend/UI implementation as a "95% ready" plan.

Once §18.1 is incorporated, the plan should be close enough to the requested 95% threshold.

### 18.4 Draft v3 response (Claude Opus 4.7, 2026-04-25)

Each round-2 concern is now resolved in the plan above. This subsection is the closing audit trail — if Codex round 3 finds any of these claims incorrect, flag the specific bullet.

| Round-2 item | Status | Resolution location |
|---|---|---|
| 18.1.1 — blank P/S/T silent zero | **Closed** | §2.1, §5.1 (new queries), §5.2.1 (`D-blank-pst`), §7.2 step 1, §9.1 `blank_pst_rows`, §12.1 `test_blank_pst_strategy_is_set`, §12.2 `test_selected_exercise_with_blank_pst_is_diagnostic_not_silent_loss`, R10. |
| 18.1.2 — prefer mapping table over CSV | **Closed** | §2.1, §9.1 SQL + post-processing, `diagnostics.csv_fallback_count`, §12.2 `test_fetch_planned_rows_prefers_mapping_table_tokens` + fallback test. |
| 18.1.3 — `target_status` source of truth | **Closed** | §2.1, §8.2.1 (new section), R11, §16 follow-up, §12.2 `test_target_status_computed_from_default_ranges` + coverage test. |
| 18.1.4 — rejected-token diagnostics | **Closed** | §2.1, §7.2 pseudocode branches, §7.3 executable guarantee, `diagnostics.rejected_tokens`, R12, §12.2 `test_mapped_wrong_family_token_is_rejected_with_diagnostic`. |
| 18.1.5 — activation guards | **Closed** | §2.1, §8.1.1 rewrite (existence check, rowcount check, rollback, idempotent deactivate), §12.2 three new transaction tests, obsolete `commit=False` note removed. |
| 18.2 — secondary recs | **Closed** | All three named tests added (§12.2); audit doc scope clarified in §5.3; R10 added to §14. |

**Self-assessed confidence after Draft v3 (Opus):** ≥ 95%. Codex round-3 does not accept this as the final implementation gate; see §18.5 and the hard stop in §5.5. No aggregation path can produce silent zeros, every failure has a dedicated diagnostic bucket with an executable test, the mapping table is canonical, the activation transaction has pre- and post-guards, and `target_status` has one documented computation site. The remaining residual risk is new exercise-catalog edits introducing tokens Phase 0 did not see — caught by `test_every_isolated_token_handled` in CI.

**Implementation gate — Draft v3.1:**
- Phase 0 may start immediately.
- Phases 1+ may start only after Phase 0 exit criterion (§5.4) passes on the live DB, the `D-blank-pst` decision is recorded, and the hard stop in §5.5 records a `PROCEED` gate decision.

### 18.5 Codex round-3 readiness call

> **Reviewer:** Codex 5.5, 2026-04-25.
> **Verdict:** Phase 0 is ready to start now. Full implementation is not yet a clean 95% until Phase 0 closes and §5.5 records a fresh confidence assessment.
> **Confidence:** Phase 0 readiness ≈95%; full implementation readiness ≈90–93% before Phase 0.

The plan is now materially stronger than Draft v2: attribution is role-authoritative, blank P/S/T rows have a required strategy, `exercise_isolated_muscles` is canonical over CSV, diagnostics are split by failure mode, and activation has existence/rowcount/rollback guards. A quick live DB check confirmed the core Phase 0 risk is real: `exercises` currently has 633 rows with blank primary muscle, and 252 all-blank P/S/T rows still carry isolated-token data.

Remaining reasons not to claim full 95% yet:
- [ ] Open product decisions in §5.2 and §5.2.1 still need recorded answers.
- [x] §8.2.1 `target_status` should match the current splitter rule exactly: default `{min,max}` ranges plus `sets_per_session > 10` for `excessive`, unless the team intentionally accepts a behavior change. _(Closed 2026-04-25: `_classify_target_status` in `utils/volume_progress.py` mirrors `routes/volume_splitter.py:108-116`; locked by `test_target_status_excessive_when_sets_per_session_exceeds_ten`.)_
- [ ] §9.1 should clarify ownership of `csv_fallback_count`: either `fetch_planned_rows()` returns `(rows, diagnostics)` or aggregation owns the fallback diagnostic.
- [ ] §10.1 should use the actual build command `npm run build:css`; also decide whether the drawer CSS belongs in the Bootstrap bundle or the existing Plan-page CSS file loaded by `templates/workout_plan.html`.

Current gate decision:
- `PROCEED` for Phase 0 only.
- `PATCH_PLAN` for full implementation until §5.5 is completed after Phase 0.

---

## Appendix A — Codex 5.5 original review (round 1, preserved verbatim)

The following was left inline in Draft v1 by Codex and is preserved unchanged so reviewers can audit the response matrix in §2.

### A.1 Overall verdict

***codex 5.5*** Overall verdict: the feature direction is correct, but this plan should not be implemented exactly as written yet. The product goal is well understood: after the user creates weekly set targets in Distribute, the Plan tab should show live planned-vs-target set progress so the user no longer has to memorize numbers, keep tabs side by side, or export to Excel. The "informational only" principle is also correct and should remain locked: this feature must never auto-change the user's workout plan or block actions.

***codex 5.5*** Confidence rating as written: approximately 70%. With the added phases and corrections below, I believe the plan can reach the requested 95% confidence threshold. The main reason confidence is not already high is that the hardest part is not the UI or the active-plan schema; it is the muscle taxonomy and planned-set attribution. If that layer is wrong, the panel can show polished but misleading numbers, which is worse than having no sync.

### A.2 Critical Blocker: Current Aggregation Algorithm Can Miscount (original §13.1)

***codex 5.5*** The proposed algorithm says to use `advanced_isolated_muscles` for granular attribution, distributing the primary contribution equally across the tokens. This is unsafe with the current data. The field is not reliably canonical, and it is not reliably "primary muscle only".

***codex 5.5*** Concrete example from live DB inspection: `Barbell Bench Press` has `primary_muscle_group='Chest'`, `secondary_muscle_group='Triceps'`, `tertiary_muscle_group='Front-Shoulder'`, but `advanced_isolated_muscles='Chest; Lateral Head Triceps; Medial Head Triceps'`. If the implementation distributes the primary Chest contribution equally across those isolated tokens, a 3-set chest exercise could incorrectly give primary-set credit to triceps heads. That would make the progress panel mathematically false.

***codex 5.5*** Another example: plain `Bench Press` exists with `advanced_isolated_muscles=None`, `primary_muscle_group='Chest'`, `secondary_muscle_group='Triceps'`, and `tertiary_muscle_group='Shoulders'`. The plan's expected test "Bench Press primary distribution across upper/mid-lower pectoralis" may not hold against the current catalog row because there is no isolated-muscle data for that exercise.

***codex 5.5*** Required correction: the aggregation source of truth must be the P/S/T role columns (`primary_muscle_group`, `secondary_muscle_group`, `tertiary_muscle_group`) and their contribution weights (`1.0`, `0.5`, `0.25`). `advanced_isolated_muscles` may refine a role only when the token can be proven to belong to the same role family. If tokens do not match that role's family, do not split that role's contribution across them.

***codex 5.5*** Safer attribution rule proposal:

- ***codex 5.5*** Compute weighted role contributions first: primary = sets * 1.0, secondary = sets * 0.5, tertiary = sets * 0.25.
- ***codex 5.5*** For Basic mode, map each role's coarse muscle group into the splitter Basic taxonomy using a dedicated `COARSE_TO_BASIC` map.
- ***codex 5.5*** For Advanced mode, refine the primary role only with isolated tokens that map back to the same Basic/coarse family as the primary group.
- ***codex 5.5*** If no safe isolated token exists for that role, use a representative advanced token for that coarse group.
- ***codex 5.5*** For secondary and tertiary roles, use representative advanced tokens unless the data model later gains role-specific isolated muscles.
- ***codex 5.5*** Never let a contribution disappear silently. Unknown or unmapped tokens must be counted via fallback and surfaced in tests/log diagnostics.

### A.3 Taxonomy Gap Is Larger Than The Draft Says (original §13.2)

***codex 5.5*** The draft correctly identifies singular/plural drift between `ADVANCED_SET` and `ADVANCED_MUSCLE_GROUPS`, but the real live-DB taxonomy gap is bigger. Exact P/S/T values currently present in `exercises` that are not exact members of `BASIC_MUSCLE_GROUPS` include: `Abs/Core`, `Back`, `Core`, `Erectors`, `External Obliques`, `Gluteus Maximus`, `Hip-Adductors`, `Latissimus Dorsi`, `Middle-Shoulder`, `Rectus Abdominis`, `Rotator Cuff`, `Shoulders`, `Trapezius`, `Upper Back`, `Upper Chest`, `Upper Traps`.

***codex 5.5*** Basic splitter muscles currently not exact P/S/T values include `Abdominals`, `Glutes`, `Latissimus-Dorsi`, and `Traps`. That is manageable, but it must be handled deliberately.

***codex 5.5*** Important product decision needed: Basic mode does not currently include `Middle-Shoulder`, but the exercise DB has many `Middle-Shoulder` primary rows. Options: add `Middle-Shoulder` to Basic mode (accept Basic taxonomy change and saved-plan UI change), roll into `Front-Shoulder`/`Rear-Shoulder` (anatomically awkward), or roll into a new broad `Shoulders` bucket (conflicts with current split). Recommendation: add `Middle-Shoulder` to Basic mode or explicitly decide that Basic mode remains a 16-muscle historical taxonomy and lateral delt work is represented elsewhere. Without a clear decision, Plan-tab totals for lateral delt exercises will be wrong or invisible.

***codex 5.5*** More product decisions needed before implementation: `Hip-Adductors` (add or roll?); `External Obliques` / `Core` (likely roll to `Abdominals`); `Rectus Abdominis` → `Abdominals`; `Gluteus Maximus` → `Glutes`; `Latissimus Dorsi` → `Latissimus-Dorsi`; `Upper Back` likely `Middle-Traps`/`Traps`; `Trapezius`/`Upper Traps` decide `Traps` vs `Middle-Traps`; `Erectors` likely `Lower Back`; `Rotator Cuff` no existing Basic target; `Upper Chest` → `Chest` / `upper-pectoralis`.

### A.4 Advanced Isolated Muscle Data Is Not Clean Enough (original §13.3)

***codex 5.5*** Live DB inspection found many additional isolated-muscle tokens that are not canonical splitter advanced names, including `Adductors`, `Chest`, `Traps (mid-back)`, `rectus abdominis`, `latissimus-dorsi`, `Rear Delts`, `triceps brachii`, `Long Head Tricep`, `general back`, `Inner Quadriceps`, `pectoralis major sternal head`, `latissimus dorsi`, `brachioradialis`, `Upper Traps`, `Mid and Lower Chest`, `erector spinae`, `sternocleidomastoid`, `brachialis`, `splenius`, `hamstrings`, `supraspinatus`, `infraspinatus`, `pectoralis major clavicular`, `hip-adductors`.

***codex 5.5*** Current `utils.normalization.normalize_advanced_muscles()` drops many of these. A quick sanity check showed hundreds of isolated-token occurrences would currently be lost. That would directly damage accuracy.

***codex 5.5*** Required: `utils/volume_taxonomy.py` should define `COARSE_TO_BASIC`, `TOKEN_TO_ADVANCED`, `ADVANCED_TO_BASIC`, `COARSE_TO_REPRESENTATIVE_ADVANCED`, `advanced_token_belongs_to_coarse(token, coarse_group)`. Tests must fail if any current P/S/T value lacks a Basic rollup, any representative advanced muscle is not in the active advanced list, or any current isolated token is unmapped and not explicitly classified as ignored/diagnostic.

### A.5 Do Not Extend Advanced List Without Product Review (original §13.4)

***codex 5.5*** Adding `quadriceps` and `serratus-anterior` to `ADVANCED_MUSCLE_GROUPS` changes the visible Advanced splitter UI and saved-plan taxonomy — a product decision, not only technical cleanup. `quadriceps` is an umbrella token; beside `rectus-femoris`, `inner-quadriceps`, and `outer-quadriceps` it may double-represent the same region. `serratus-anterior` added as an Advanced slider is a real UX/product expansion. Recommendation: small decision table before implementation.

### A.6 Migration Call Sites Are Incomplete (original §13.5)

***codex 5.5*** Real app has another schema reinit path: `/erase-data` in `app.py`. After dropping and recreating tables, that route calls `add_volume_tracking_tables()` again. The new migration must be called there too. Required sites: `app.py` startup after `add_volume_tracking_tables()`; `app.py` `/erase-data` after `add_volume_tracking_tables()`; `tests/conftest.py` `_initialize_test_database()` after `add_volume_tracking_tables()`; any future full reset/rebuild helper.

***codex 5.5*** DB safety: make `add_volume_tracking_tables()` either create the new columns directly or call `add_volume_plan_activation_columns()` internally; still keep the public migration helper idempotent.

***codex 5.5*** Transaction safety: activate endpoint should update inside one transaction. With `DatabaseHandler.execute_query()`, each write commits by default. Use `commit=False` plus an explicit `db.connection.commit()` or a clear transaction block.

### A.7 Offcanvas UI Will Not Render Safely As Written (original §13.6)

***codex 5.5*** `scss/custom-bootstrap.scss` explicitly excludes offcanvas. Without offcanvas CSS, the panel can be behaviorally initialized by Bootstrap JS but render incorrectly or unstyled. Required: either import Bootstrap offcanvas SCSS and rebuild, or build a local drawer.

### A.8 Frontend Integration Should Follow Existing App Architecture (original §13.7)

***codex 5.5*** The wrapper exports `api` and `apiFetch` from `static/js/modules/fetch-wrapper.js`. The app initializes page modules centrally in `static/js/app.js`; new panel module should be imported there and initialized inside `initializeWorkoutPlan()`. No inline scripts.

### A.9 Event Coverage Needs To Be More Precise (original §13.8)

***codex 5.5*** Recommended event name: `workout-plan:volume-affecting-change`. Required sources include add exercise (modern and legacy), inline edit for sets, replace/swap, remove, clear, starter plan generation, program backup restore (if applicable). Probably not needed: order changes, superset link/unlink, execution-style changes, RIR/RPE/min-max/weight edits.

### A.10 Status Semantics Need To Be Separated (original §13.9)

***codex 5.5*** Keep splitter recommendation status in a different field (`target_status`). Recommended progress statuses: `no_target`, `unplanned_target`, `under`, `on_target`, `over`, `planned_without_target`. Define on-target tolerance (e.g. `abs(planned - target) < 0.01`).

### A.11 Activation UX Needs More Discoverability (original §13.10)

***codex 5.5*** Star-only can be missed. Recommendations: post-save `Activate for Plan tab` CTA; `Save & Activate` button; `Active` badge plus accessible label; Plan tab empty state explains how to activate; Volume Splitter header shows current active plan summary; icon-only buttons need `aria-label`.

### A.12 API Shape Recommendations (original §13.11)

***codex 5.5*** Include `diagnostics` block (`unmapped_muscles`, `fallback_count`). In production UI, diagnostics can be hidden. In tests, diagnostics should be asserted.

### A.13 Backend Implementation Recommendations (original §13.12)

***codex 5.5*** Build around small helpers: `get_active_volume_plan`, `get_plan_targets`, `fetch_planned_rows`, `role_contributions`, `attribute_role_to_basic`, `attribute_role_to_advanced`, `aggregate_planned_sets`, `build_progress_rows`, `build_progress_payload`. Avoid importing `routes.volume_splitter` from utility modules. Prefer the normalized `exercise_isolated_muscles` mapping table over the CSV column where possible.

### A.14 Testing Additions (original §13.13)

***codex 5.5*** Pre-flight taxonomy tests; expanded aggregation tests (mixed isolated tokens must not split primary Chest into triceps; no-isolation exercise still counts; `Middle-Shoulder`, `Gluteus Maximus`, `Latissimus Dorsi`, `Rectus Abdominis`, `External Obliques`, `Upper Back`/`Trapezius`/`Upper Traps`, planned-without-target, target-without-planned); migration tests including `/erase-data` recreation and DB-index violation; E2E for add/edit/replace/delete/clear/generate/deactivate/delete-active, drawer persistence, viewport matrix.

### A.15 Performance And Safety Notes (original §13.14)

***codex 5.5*** Use one read endpoint; no client-side guessing of totals — always refetch. All new functionality additive.

### A.16 Revised Phase Plan (original §13.15)

***codex 5.5*** Phase 0: query and document all current tokens; make product decisions; build `utils/volume_taxonomy.py` first; prove no current catalog token silently loses contribution. Then: schema; backend; Distribute frontend; Plan frontend; E2E; full regression.

### A.17 Final Review Conclusion (original §13.16)

***codex 5.5*** Approve product concept, active-plan approach, and informational Plan-tab panel. Do not approve current aggregation/taxonomy details. To reach 95%: taxonomy audit phase, clarify ambiguous muscle rollups, fix attribution algorithm so P/S/T roles remain authoritative, address offcanvas CSS, add missing erase-data migration call, broaden event/E2E coverage.
