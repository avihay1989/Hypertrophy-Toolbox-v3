# Fatigue Meter — Phase 2 PLANNING

**Status:** planning extracted / awaiting owner decision. **Phase 2 is NOT approved for implementation.**
**Date extracted:** 2026-05-23
**Source:** split out of [`PLANNING.md`](PLANNING.md) Stage 5/6 and [`BRAINSTORM.md`](BRAINSTORM.md) (§4–§9, §11, §13, §20 Phase 2 matrix).
**Predecessor state:** Phase 1 shipped 2026-05-03 (PR #7, single global server-rendered badge). [Stage 4 closed 2026-05-20](calibration-notes.md) by owner-approved felt-label review (4 of 5 anchors agreed; no threshold changes). `utils/fatigue.py`, `tests/test_fatigue.py`, and `scripts/fatigue_calibration_report.py::SCENARIOS` are the locked Phase 1 working state and must not be edited without a fresh owner override.

This document mirrors the shape of `PLANNING.md` (entry / tasks / exit per stage) but contains **no Tasks-ready boxes** — Stage 0 of Phase 2 (lock D2.x decisions) has not started.

---

## 1. Why Phase 2 — Problem statement (beyond the Phase 1 badge)

Phase 1 ships a single global descriptive score on `/session_summary` and `/weekly_summary`. It answers the question *"is this plan heavy?"* and nothing else.

Three concrete questions Phase 1 cannot answer:

1. **What is heavy?** A 165 weekly score gives no signal about whether the load is biased toward one muscle group, one movement pattern, or one joint system. Two programs with identical global scores can be radically different in distribution.
2. **Is the heaviness worth it?** Phase 1 reports fatigue with no reference to stimulus. A high-fatigue / low-stimulus program (junk volume) reads the same as a high-fatigue / high-stimulus program. The Stimulus-to-Fatigue Ratio (SFR) discussion in `BRAINSTORM.md §4.6` exists exactly to surface this distinction.
3. **Where is the headroom?** Without a per-muscle breakdown there is no signal for "biceps are at typical-recoverable; quads have room" — the per-muscle question is the one most likely to change a routine design decision.

Stage 4's calibration close confirmed the §24.B thresholds are sane against one real logged week + four synthetic anchors. That removes recalibration as the next investment and frees the next investment for **resolution** (channel split + drill-down + ratio).

---

## 2. Recommended Phase 2 MVP scope

The smallest credible Phase 2 that delivers user-visible value on top of Phase 1:

- **(a) Local-channel split.** Per-muscle fatigue accumulator (`BRAINSTORM.md §4.2` — Channel A only). Sum `set_fatigue × muscle_contribution_weight` grouped by muscle, surfaced as a per-muscle bar list.
- **(b) Dedicated `/fatigue` route + page.** New blueprint, new template. Houses the per-muscle breakdown and the SFR card. The existing badge on `/session_summary` and `/weekly_summary` stays as-is and gains a "View per-muscle breakdown →" link (`BRAINSTORM.md §7` Option C).
- **(c) Per-muscle MEV/MAV/MRV defaults.** Hardcoded constants per `BRAINSTORM.md §5` table. No UI override (carry forward Phase 1's D2 stance: defaults only in V2).
- **(d) Stimulus-to-Fatigue Ratio (SFR) card.** Reuses `effective_sets` output as the stimulus proxy; divides by the Phase-1 fatigue score. Display with a sentinel for the `fatigue == 0` case (per `BRAINSTORM.md §16.1` SFR test row).

That's it. Four concrete additions, all additive, no schema change, no API.

---

## 3. Deferred to Phase 3 or later

Explicitly out of Phase 2 MVP, kept on file:

- **Systemic + Joint channels** (`BRAINSTORM.md §4.3` Channel B, §4.4 Channel C). Local-first ships the largest single piece of user value; the other two channels can layer in once the per-muscle UX is validated.
- **Decay model** (`BRAINSTORM.md §4.5`). Cheap to add later (one function with τ per channel); expensive to debug if shipped wrong. Phase 1's D6 lock applies forward.
- **%1RM path** (`BRAINSTORM.md §3.2`). Requires populated `user_profile` reference lifts — `data-audit.md` recorded zero usable rows at Phase 1 baseline; the data does not yet exist.
- **Technique modifier** (`BRAINSTORM.md §3.4`). Phase 1's D7 lock applies forward — we still don't capture the data.
- **Calibration table** (`user_fatigue_thresholds`). **First schema change in the feature** — belongs to Phase 3 and triggers the `BRAINSTORM.md §18` rollback escalation.
- **`/api/fatigue/*` endpoints.** Phase 1's D9 lock applies forward. Revisit only when a client genuinely needs JSON (e.g. a future mobile companion or an external integration).
- **Logged-data path.** Phase 1's D10 override picked planned-only (`user_selection`); a future stage may want to surface "planned vs actual" side-by-side. Out of MVP because it doubles the surface area.
- **Plan-projection mode in a dedicated route** (`BRAINSTORM.md §9` Phase 3). Subsumed by the Phase-1 D10 override (Phase 1 *is* the projection path); a dedicated projection toggle is unnecessary until logged-data ships.

---

## 4. Open decisions for the owner

Same shape as `PLANNING.md §0.1` and `BRAINSTORM.md §13` / §24.A. **None of these are locked.** A future Stage 0 walk-through will tick approve or write an override on each row before any implementation begins.

| # | Decision | Author recommendation | Notes |
|---|---|---|---|
| **D2.1** | Channel split for Phase 2 | **Local-only (Channel A)** | §2(a) above. Systemic + Joint stay deferred to Phase 3. |
| **D2.2** | Page placement | **Dedicated `/fatigue` + keep existing badge with a link** (Option C from `BRAINSTORM.md §7`) | Embed-only would crowd the summary cards; dedicated-only would orphan the badge. |
| **D2.3** | Threshold source | **Hardcoded `BRAINSTORM.md §5` defaults; no UI override in V2** | Carries forward Phase 1's D2 stance. Calibration table is Phase 3. |
| **D2.4** | Sets basis for per-muscle channel | **Raw sets** (carry forward Phase 1 D3 override) | Per-muscle channel needs to be CountingMode-invariant for the same reason the global badge is — fatigue has its own multipliers and shouldn't double-count effort. |
| **D2.5** | Data scope | **Planned only (`user_selection`)** — same as Phase 1 D10 override | Adding logged side-by-side doubles UI surface area and Stage 2 chapter count; defer. |
| **D2.6** | SFR denominator | **Global fatigue (Phase 1 score) for the page-level SFR card; per-muscle SFR is a stretch goal, not MVP** | Per-muscle SFR is more useful but requires per-muscle stimulus, which `effective_sets.py` already exposes — feasibility check moves into Stage 0. |
| **D2.7** | Ship `/api/fatigue/*` in Phase 2? | **Skip** (carry forward Phase 1 D9) | Page is server-rendered; no client needs JSON. SQL-injection surface stays at zero. |
| **D2.8** | Any schema touch in Phase 2? | **No** — additive only | First schema change is Phase 3 territory by design. If a Phase 2 chapter wants a table, that chapter does not belong in Phase 2. |
| **D2.9** | Where does per-muscle data come from? | **Reuse `effective_sets`-style per-muscle aggregation against `user_selection`** — see `utils/effective_sets.py:402` pattern | Avoids forking a parallel pipeline; honors D13 (don't reuse aggregated rows — re-query with the fatigue-relevant columns). |
| **D2.10** | Copy boundaries | **Same as Phase 1** — descriptive, no "MRV"/"MEV" in user-facing copy; bands stay neutral ("above the typical recoverable range") | `BRAINSTORM.md §11 Q7` + Phase 1 §3.3 verified non-prescriptive copy as a hard gate. |

Stretch decisions that may surface during Stage 0:
- Whether per-muscle bars sort by absolute fatigue, by `% of MRV`, or by the user's choice.
- Whether the page supports a period selector (this session / this week / 4-week) on day one or ships single-period and adds the selector later.
- Whether the per-muscle empty-state shows all muscles at zero (visually noisy) or hides them with a "no planned exercises yet" copy block.

---

## 5. Proposed staged implementation plan

Mirrors `PLANNING.md`'s stage shape. No tasks are pre-checked; this is a forecast, not a commitment.

### Stage 0 — Lock D2.x decisions (humans only, no code)
- Walk D2.1–D2.10 above (and any stretch decisions surfaced during the walk). Each row gets `approve` or an override + rationale.
- Sync locked decisions back into `BRAINSTORM.md §13` as a new Phase-2 block (do not overwrite the Phase 1 D1–D13 rows).
- Exit: every D2 row ticked.

### Stage 1 — Pre-development prerequisites
- Lock the post-Phase-1 baseline (current `CLAUDE.md §5` numbers — re-verify against the working tree at Stage 1 entry).
- Data audit refresh: re-count NULL `primary_muscle` and NULL `movement_pattern` rows for catalog and `user_selection`. Phase 1 carved both >5% items as Phase-1 limitations; Phase 2 makes per-muscle the load-bearing path, so those carve-outs become Stage-1 blockers — they must be resolved or explicitly re-scoped.
- Pre-flight backup via `POST /api/backups` (label `pre-fatigue-meter-phase-2-YYYY-MM-DD`).
- Dependency check: confirm Phase 2 needs no new Python deps (likely true); confirm chart strategy (`BRAINSTORM.md §11 Q6` — match whatever `volume_splitter` already uses; do not introduce Chart.js unless that's already the answer).
- Create feature branch.
- Exit: baseline file + data-audit refresh + backup id + branch all recorded.

### Stage 2 — Implementation chapters
Each chapter is a single small commit with its own gate, matching Phase 1's pattern.

| Chapter | Goal | Net new files | Net edited files |
|---|---|---|---|
| 2.1 | Extend `utils/fatigue.py` with per-muscle accumulators (pure functions; no DB). | — | `utils/fatigue.py` |
| 2.2 | Unit tests for per-muscle math (extend `tests/test_fatigue.py`). | — | `tests/test_fatigue.py` |
| 2.3 | Add `routes/fatigue.py` blueprint + `templates/fatigue.html` skeleton. Register in `app.py` AND `tests/conftest.py` (the #1 testing pitfall — Phase 1 R1). Use `success_response()` for any JSON the template inlines via a route helper; no `/api/*` route. | `routes/fatigue.py`, `templates/fatigue.html` | `app.py`, `tests/conftest.py` |
| 2.4 | Per-muscle bar partial + SFR card. SCSS color/state additions for bars. | `templates/_fatigue_muscle_bar.html`, possibly `static/js/modules/fatigue.js` if a real chart lib is in play (otherwise inline SVG) | `scss/_fatigue.scss`, `scss/custom-bootstrap.scss` (extend `@import` block), `templates/fatigue.html` |
| 2.5 | Nav link + dark-mode parity + copy review + "View per-muscle breakdown →" link from the existing summary badges back to `/fatigue`. | — | `templates/base.html`, `templates/_fatigue_badge.html` (link), run `/build-css` |
| 2.6 | Docs + CHANGELOG + test counts + flip this `PHASE2_PLANNING.md` status banner. | — | `CLAUDE.md §5`, `docs/CHANGELOG.md`, `docs/fatigue_meter/PHASE2_PLANNING.md` |

Per-chapter gates follow Phase 1 §2.X exactly: pytest delta documented, targeted E2E spec green, no test-count regression in unrelated files, code-reviewer pass on diff before merge.

### Stage 3 — Verification & merge gate (95% confidence checkpoint)
Same shape as `PLANNING.md §3`. Adds two Phase-2-specific items:
- **Per-muscle data-fidelity sanity check.** Per-muscle scores for a known routine match a hand-calculated value across at least 3 muscles.
- **Link reciprocity.** Badge → `/fatigue` and `/fatigue` → summary pages both load without console errors.

### Stage 4 — Post-merge calibration window
≥2 weeks of real use before any per-muscle threshold tweaks. Same "no tuning without ≥2 disagreements" bar as Phase 1 §4.2.

---

## 6. Files likely touched

Phase 2 MVP is **purely additive** — no existing route handler logic changes, no schema, no `utils/effective_sets.py` edit.

### ADD
| File | Purpose |
|---|---|
| `routes/fatigue.py` | New blueprint; one route (`GET /fatigue`); no `/api/*`. |
| `templates/fatigue.html` | Per-muscle breakdown + SFR card. Extends `base.html`. |
| `templates/_fatigue_muscle_bar.html` | One row per muscle. Reused inside the page; possibly inlined depending on the SCSS pattern. |
| `static/js/modules/fatigue.js` | **Only if a real chart lib is reused** from elsewhere in the project. Otherwise inline SVG bars and skip this file (matches `BRAINSTORM.md §8` "inline SVG to avoid new deps"). |
| `e2e/fatigue.spec.ts` | Page-load, per-muscle bars, SFR card, empty-state, dark mode. |

### EDIT
| File | Why |
|---|---|
| `utils/fatigue.py` | Per-muscle accumulator functions (pure; no DB). |
| `tests/test_fatigue.py` | Per-muscle math + SFR tests. |
| `app.py` | Register `fatigue_bp`. |
| `tests/conftest.py` | Register `fatigue_bp` in the test app fixture. **Phase 1 R1 — missing this = silent 404s.** |
| `templates/base.html` | Nav link to `/fatigue`. |
| `templates/_fatigue_badge.html` | Add "View per-muscle breakdown →" link to the new page. |
| `scss/_fatigue.scss` | Per-muscle bar color states, dark-mode aware. |
| `scss/custom-bootstrap.scss` | If a new partial is split out, add `@import`. |
| `static/css/bootstrap.custom.min.css` | Rebuilt by `/build-css`. |
| `CLAUDE.md §5` | Test count line update + date. |
| `docs/CHANGELOG.md` | Phase 2 entry. |
| `docs/fatigue_meter/PHASE2_PLANNING.md` | Flip status banner at Stage 2.6. |

### NOT touched in Phase 2 (regression flag if any of these change)
`utils/effective_sets.py`, `utils/session_summary.py`, `utils/weekly_summary.py`, `utils/database.py`, `utils/db_initializer.py`, `utils/program_backup.py`, `utils/auto_backup.py`, `data/database.db` (schema), `scripts/fatigue_calibration_report.py::SCENARIOS`.

---

## 7. Test plan

Builds on Phase 1's `tests/test_fatigue.py` and Phase 1's E2E baselines (`CLAUDE.md §5`).

### Unit tests (extend `tests/test_fatigue.py`, pure-math, no DB)
- Per-muscle accumulator:
  - Single exercise with one primary muscle → that muscle's score = per-set × sets; all other muscles = 0.
  - Two exercises hitting overlapping muscles → per-muscle scores sum correctly.
  - Exercise with NULL `primary_muscle` → contribution falls into `unassigned` bucket; per-muscle total still computed; warning logged.
  - Secondary / tertiary muscle weighting matches `effective_sets.py` contribution constants.
- SFR:
  - `fatigue == 0` → SFR returns sentinel (`None` or documented marker), not crash, not `inf`.
  - `fatigue > 0, stimulus = 0` → SFR returns `0`.
  - Both positive → ratio matches expected to 3 decimal places on a hand-calculated example.
- Threshold classification (per-muscle bands):
  - Muscle below MEV → `light`.
  - Muscle in MAV → `moderate`.
  - Muscle above MRV → `very_heavy`.
  - Boundary values deterministic per docstring.

### Integration (route handler returns correct template context)
- `GET /fatigue` against seeded `user_selection` → 200, template context contains `muscles`, `sfr`, `period_label`, and the canonical `fatigue_*` keys.
- `GET /fatigue` against empty `user_selection` → 200, empty-state copy rendered, no crash.

### E2E (`e2e/fatigue.spec.ts`)
- Page loads with no console errors.
- Per-muscle bars render and are sorted (D2.10 stretch-decision-pending).
- SFR card visible with label, ratio, explanation copy.
- Empty-state path: brand-new DB → page does not crash, bars area shows "No planned exercises yet".
- Dark-mode parity across all bands.
- Link from `/session_summary` badge → `/fatigue` works (and vice-versa).

### Targeted regression sweep (Phase 1 §16.4 + new spec)
- `e2e/summary-pages.spec.ts` — touched indirectly via the new "View per-muscle breakdown" link in the badge partial.
- `e2e/workout-plan.spec.ts`, `e2e/workout-log.spec.ts` — sibling pages.
- `e2e/accessibility.spec.ts` — new DOM means new ARIA assumptions.
- `e2e/fatigue.spec.ts` — the new spec itself.

### Manual smoke (browser walk, Phase 1 §3.5 pattern)
- All navbar routes load without console errors (now 10 with `/fatigue`).
- Add exercise → badge + per-muscle bars update consistently.
- Restore the pre-Phase-2 backup → every page loads.
- 375px viewport: per-muscle bars wrap cleanly; no horizontal overflow.
- Dark mode: bar fills + thresholds readable across all bands.

---

## 8. Rollback & safety

### Phase 2 MVP rollback
Phase 2 MVP is purely additive (no schema change). Rollback path matches Phase 1:
- `git revert <merge-commit>` per chapter or per merge. Because each chapter has a green gate, partial rollback is safe.
- `static/css/bootstrap.custom.min.css` rebuilds from SCSS — revert SCSS + rerun `/build-css` to undo Chapter 2.4 / 2.5.
- No DB migrations to undo (no schema changes in Phase 2 MVP).

### Pre-flight backup
Take a fresh manual backup via `POST /api/backups` at Stage 1 (label `pre-fatigue-meter-phase-2-YYYY-MM-DD`). **Phase 1's backup id `5` is not sufficient** — it predates the body-composition + workout-cool work that landed between Phase 1 merge and Phase 2 start; restoring it would discard substantial unrelated user state.

### Schema-creep guardrail
If a Phase 2 chapter discovers it wants a table (e.g. a per-muscle override row, an SFR snapshot), **stop and escalate to Phase 3 framing**. Phase 2's "purely additive, no schema" stance is the entire reason rollback is cheap. The first schema change ships in Phase 3 with `BRAINSTORM.md §18` becoming load-bearing (document down SQL inline, audit `utils/program_backup.py` for new-table inclusion, manual backup before merge).

### Emergency rollback path
- Restore the pre-Phase-2 labeled backup via `POST /api/backups/<id>/restore`.
- `git revert <merge-commit>` on `main`.
- Investigate offline.

---

## 9. Explicit non-goals (Phase 2)

Carry-forward from `BRAINSTORM.md §1` and §22, plus Phase-2-specific items:

- **Never blocks a user action.** Per-muscle bars and SFR are descriptive only.
- **No auto-deload, no auto-adjust, no prescriptive copy.** "Above MRV" stays out of user-facing copy; use "above the typical recoverable range" or color + number with no verb.
- **No modal interrupts.** No popups for "you're over MRV"; soft inline only.
- **No HRV / soreness / readiness integrations** (would need wearables or daily opt-in inputs).
- **No multi-user comparisons** (single-user app).
- **No predicting injury risk** (medical claim).
- **No notifications / push reminders.**
- **No sharing / exporting fatigue charts** to external services.
- **Phase 2 does not retire the Phase 1 badge.** Both coexist — the badge stays on the summary pages and gains a link to the new page.
- **No schema change in Phase 2 MVP.** First schema change is Phase 3.
- **No `/api/fatigue/*` endpoints in Phase 2** (carry forward D9).
- **No %1RM path in Phase 2** (Phase 3 — requires populated `user_profile` reference lifts).
- **No decay model in Phase 2** (Phase 3).
- **No technique modifier in Phase 2** (`BRAINSTORM.md §3.4` Phase 4 / opt-in only).
- **No logged-data path in Phase 2 MVP.** Phase 1's planned-only D10 carries forward.
- **Per-muscle bars are not a coaching prescription.** They describe distribution; they do not recommend a rebalance.

---

## 10. Open follow-ups / parking lot

Tracked here so they don't get lost during Stage 0:
- Per-muscle SFR (D2.6 stretch) — feasibility hinges on `effective_sets.py` exposing per-muscle stimulus in a shape the SFR card can consume without a parallel pipeline.
- Period selector (this session / this week / 4-week) — Phase 1 ships single-period; the dedicated page is the natural home for the selector but may ship later.
- "View per-muscle breakdown →" link copy — must stay descriptive; not `"View MRV breakdown"`.
- Recovery of the deferred `BRAINSTORM.md §10` partial-week handling for the per-muscle view ("X / N expected for this point in week"). Likely a Phase 3 polish item.

---

## 11. Companion file references

| File | Relation |
|---|---|
| [`PLANNING.md`](PLANNING.md) | Phase 1 source-of-action; Stage 5/6 now point here. |
| [`BRAINSTORM.md`](BRAINSTORM.md) | Source-of-thought; full historical context for §4/§5/§7/§9/§11/§13/§20 Phase 2 matrix. |
| [`calibration-notes.md`](calibration-notes.md) | Stage 4 close 2026-05-20 — why thresholds are stable enough to invest in resolution next. |
| [`STAGE4_PARKED_HANDOFF.md`](STAGE4_PARKED_HANDOFF.md) | Superseded by the 2026-05-20 owner-approved Stage 4 close; preserved for history. |
| [`../LEFTOVERS_BY_PRIORITY.md`](../LEFTOVERS_BY_PRIORITY.md) row #15 | Tracks Phase 2 as owner-gated; points back here. |

---

*End of PHASE2_PLANNING.md. Status remains "planning extracted / awaiting owner decision" until Stage 0 walks D2.1–D2.10.*
