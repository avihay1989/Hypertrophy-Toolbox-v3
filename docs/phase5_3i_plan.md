# Phase 5 — 3i/3j Confidence Recovery Audit Plan

**Author:** Claude (Opus 4.6), 2026-04-11 (revised 2026-04-11 per Codex review v1; v2.1 cleanup by Codex)
**Branch:** `spring-cleanup`
**Parent plan:** [docs/code_cleanup_plan.md](code_cleanup_plan.md)
**Companion plan:** [docs/phase4_option_c_plan.md](phase4_option_c_plan.md)
**Reviewers:** Gemini + Codex (read-before-execute)
**Confidence target:** ≥95% per sub-phase, ≥95% aggregate
**Execution model:** read-only validation + exit-artifact writes. Source code is modified by exactly two sub-phases: **5I** (scoped to `tests/test_exports.py`) and **5O** (scoped to `docs/code_cleanup_plan.md`). All other sub-phases are read-only for source code.

**Shell convention (see §1 P0):** every Unix-syntax command in §5 is run via Git Bash at an absolute path, wrapped as `& $BASH -lc "cd '$REPO_UNIX' && <command>"`. Sonnet must not translate commands to PowerShell or re-implement them in Python.

---

## Reading Order (fresh agents start here)

Route yourself based on what already exists **before** reading the rest of this file:

| If this is true… | Read this section first | Then |
|---|---|---|
| `debug/5Z_close.md` exists | §13 Post-5O Decision Tree | Report state to user per §13.3; do not re-execute any closed action |
| `debug/P0_phase5_shell.md` missing | §0 Self-Contained Context → §1 Prerequisites P0 | Use §11 Fresh Session Kickoff Prompt with `{{sub_phase_id}}`=`P0` |
| Any `debug/P<n>_*.md` or `debug/5<letter>_*.md` exists but the next expected artifact per §11 decision table is missing | §11 Fresh Session Kickoff Prompt | Use the decision table to pick the next `{{sub_phase_id}}` |
| You are Opus re-entering this plan mid-execution after a token-limit handoff | §9 Execution Notes (dated entries) | Pick up at the action named in the last dated entry |

Do not read the plan linearly on entry. Each sub-phase action is self-contained — load only the section you need, its "Files referenced" block, and the prior exit artifact.

**Execution order is non-alphabetical.** Letters 5A–5J are stable cross-reference labels, not a sequence. The authoritative sequence is: P0 → P1 → P2 → P3 → P4 → 5A → 5B → 5C → 5D → 5F → 5G → 5H → 5I → 5J → 5E → 5O → 5Z. See §11 decision table.

## Live Progress Tracker (update after every sub-phase)

> **Fresh-agent handoff:** this table is the quick resume state. The authoritative evidence remains the named `debug/` artifact for each checked item. If this table and the artifacts ever disagree, trust the artifacts and update this table before continuing.

**Current resume point (2026-04-15):** Phase 5 is closed. See `debug/5Z_close.md`; 5I landed at `e41460b`, 5O landed at `c0da18e`, and `phase5-rollback-point` was deleted.

- [x] `P0` Shell bootstrap — PASS, `debug/P0_phase5_shell.md`
- [x] `P1` Environment sanity — PASS, `debug/P1_phase5_env.md`
- [x] `P2` Baseline recapture — PASS, `debug/P2_phase5_baseline.md` (`936 passed, 1 skipped`)
- [x] `P3` Git state snapshot — PASS after accepted `73bc1eb` calibration, `debug/P3_phase5_git.md`
- [x] `P4` Rollback checkpoint — PASS, `debug/P4_phase5_rollback.md`
- [x] `5A` `generate_progression_suggestions` — PASS, `debug/5A_progression_plan.md`
- [x] `5B` `calculate_session_summary` — PASS, `debug/5B_session_summary.md`
- [x] `5C` `create_excel_workbook` — PASS, `debug/5C_create_excel_workbook.md`
- [x] `5D` `replace_exercise` — PASS, `debug/5D_replace_exercise.md`; stale targeted-count anomaly resolved in `debug/5D_ANOMALY.md`
- [x] `5F` `suggest_supersets` — PASS, `debug/5F_suggest_supersets.md`
- [x] `5G` `set_execution_style` — PASS, `debug/5G_set_execution_style.md`
- [x] `5H` `link_superset` — PASS, `debug/5H_link_superset.md`
- [x] `5I` Harden `tests/test_exports.py` rollback characterization — PASS, `debug/5I_test_hardening.md`, `debug/5I_postbaseline.md`
- [x] `5J` Validate `_recalculate_exercise_order` — PASS, `debug/5J_recalculate_exercise_order.md`
- [x] `5E` Validate `export_to_excel` — PASS, `debug/5E_export_to_excel.md`
- [x] `5O` Retire §3i and §3j in `code_cleanup_plan.md` — COMMITTED at `c0da18e`, `debug/5O_planmd.patch`, `debug/5O_retirement_summary.md`
- [x] `5Z` Phase 5 close — PASS, `debug/5Z_close.md`

---

## 0. Self-Contained Context (for fresh LLM sessions)

### 0.1 Why this plan exists

The parent plan `docs/code_cleanup_plan.md` marks Phase `3i` (Bloated Function Decomposition) at `50–60%` confidence and status `Deferred`, with the explicit remediation instruction:

> *"Split into one-function sub-phases and only green-light them one at a time. Same shape as `phase4_option_c_plan.md`."*
> — `code_cleanup_plan.md` §Confidence Recovery Plan, §Post-Phase-4 Handoff §18.2 row 3

The parallel Phase `3j` (N+1 UPDATE loop) sits at `55–60%` confidence with the same deferred status and a test-first remediation instruction.

**This plan is that breakdown.** It splits `3i` into eight one-function sub-phases (`5A`..`5H`), adds a ninth sub-phase (`5J`) for `3j`, and adds a tenth sub-phase (`5O`) for the plan-retirement edit to `code_cleanup_plan.md`. Each sub-phase is scoped to ≤15k input tokens so Sonnet 4.6 can execute it under a strict budget.

### 0.2 What is already shipped (CRITICAL — do not miss)

**All eight `3i-a..3i-h` decompositions AND the `3j` executemany batch update already shipped inside commit `12c90ac`** — the "feat(spring-cleanup): complete phases 3a-3h per code_cleanup_plan.md" rollup commit on 2026-04-11. The commit message says `3a-3h`; the diff actually contains `3a-3j`. This is the known self-inconsistency that `code_cleanup_plan.md` §Stage Tracker row for `3i`/`3j` and §18.5 anti-patterns document but never closed.

Evidence (verified 2026-04-11 via `git show 12c90ac -- <file>`):

| Refactor | Evidence in `12c90ac` diff | Verified |
|---|---|---|
| 3i-a `generate_progression_suggestions` decomposed | `+def _build_primary_weight_suggestion`, `+def _build_primary_rep_suggestion`, `+def _build_maintenance_suggestion`, `+def _build_technique_and_volume_suggestions`, `+def _build_manual_progression_options`; main body shrunk from 224 → 74 lines | Yes |
| 3i-b `calculate_session_summary` decomposed | `+def _build_plan_query`, `+def _build_log_query`, `+def _aggregate_muscle_volumes`, `+def _aggregate_session_dates`, `+def _build_summary_output`; main body shrunk from 256 → 49 lines | Yes |
| 3i-c `create_excel_workbook` decomposed | `+def _setup_formats`, `+def _build_superset_color_map`, `+def _write_worksheet`; main body shrunk from 227 → 120 lines | Yes |
| 3i-d `replace_exercise` decomposed | `+def _fetch_current_exercise_details`, `+def _build_replacement_candidates`, `+def _perform_exercise_swap`; main body shrunk from 230 → 143 lines | Yes |
| 3i-e `export_to_excel` decomposed | `+def _recalculate_exercise_order`, `+def _build_export_query`, `+def _fetch_all_sheets`; main body shrunk from 338 → 68 lines | Yes |
| 3i-f `suggest_supersets` decomposed | `+def _group_exercises_by_routine`, `+def _find_antagonist_pairings`; `ANTAGONIST_PAIRS` moved to `utils/constants.py`; main body shrunk from 139 → 61 lines | Yes |
| 3i-g `set_execution_style` decomposed | `+def _validate_and_normalize_execution_params`, `+def _update_execution_style_db`; main body shrunk from 138 → 48 lines | Yes |
| 3i-h `link_superset` decomposed | `+def _validate_superset_link_request`, `+def _apply_superset_link`; main body shrunk from 131 → 68 lines | Yes |
| 3j batch update via `executemany` | `+db.executemany("UPDATE user_selection SET exercise_order = ? WHERE id = ?", ...)`; old per-row loop `UPDATE user_selection SET exercise_order = ? WHERE id = ?` removed | Yes |

At Phase 5 start, the working tree passed **936 passed, 1 skipped** on the full pytest suite (per [CLAUDE.md](../CLAUDE.md) §8 *Verified Test Counts*, last verified 2026-04-11). After 5I test hardening, the live baseline became **938 passed, 1 skipped**. The refactors are demonstrably not breaking the existing test coverage.

### 0.3 What this plan is NOT

- **It is not a re-execution plan.** The code has already been refactored. Re-executing the decomposition would corrupt committed history and risk breaking the 936 green tests. §12 anti-patterns enforces this.
- **It is not a behavioral-equivalence proof at fuzzed-input level.** The plan verifies equivalence at the pytest-coverage level (936 targeted + integration tests) and at the signature/SQL/response-shape level. If the user wants stronger guarantees, that is a separate follow-on: adding characterization tests for branches not covered by the current suite. The plan names this as the only escalation path in §5 sub-phase escalation rule.
- **It is not a `git revert 12c90ac` plan.** The rollup commit also contains `3a-3h` cleanup work that is independently valuable and out of scope for this plan. Rollback (§8) is an **emergency whole-file restore** via `git show 47736b9:<file> > <file>` — this reverts every line in that file that changed between `47736b9` and HEAD, including co-located unrelated cleanup work. See §8 for the blast-radius disclaimer.
- **It does not touch the Phase 4M bugs** (Weekly/Session counter toggle, Progression rendering). Those have their own triage artifacts in `debug/4M_*.md` and are out of scope. They were later closed outside Phase 5: Progression in `ec748ba`, and Weekly/Session summary UX in `b058d19`, `73bc1eb`, and `571a365`.

### 0.4 The self-inconsistency being closed

Four locations in `code_cleanup_plan.md` disagree about the state of 3i and 3j:

| Location | Says |
|---|---|
| §Status Dashboard → Stage Tracker row `3i` | `50-60% / Deferred / requires new breakdown plan` |
| §Status Dashboard → Stage Tracker row `3j` | `55-60% / No-go / still blocked by missing tests` |
| §Confidence Recovery Plan → Recovery Plan for `3i` | unchecked `[ ]` list of sub-phases |
| §3i body (§"3i. Bloated Function Decomposition") | `3i-a..3i-h` marked `[x]` with execution notes |
| §3j body (§"3j. Fix N+1 UPDATE Loop (Deferred / Last)") | all `[x]` with execution notes |

Sub-phase `5O` of this plan edits `code_cleanup_plan.md` to resolve the contradiction: §3i and §3j bodies get retired in favor of a pointer to this plan; the Stage Tracker rows get updated once the audit completes.

---

## 1. Prerequisites (run once before any sub-phase)

All prerequisites are read-only for source code. **P4 writes one git tag** (not a source change); **P0 writes no repo state**.

### P0 — Shell environment bootstrap
**Exit artifact:** `debug/P0_phase5_shell.md`

> **Why this exists.** Every command in §5 is written in Unix syntax (`bash`, `grep`, `sed`, `awk`, `rg`, `diff`, shell redirection). This repo is primarily operated from PowerShell on Windows, where those tools are not on `PATH`. Rather than translating every snippet to PowerShell/Python ad hoc — which would introduce re-implementation bugs — the plan requires Git Bash via an absolute path and defines a single execution convention that every sub-phase uses verbatim.

- [ ] **Verify Git Bash exists at the expected absolute path.** In PowerShell:
    ```powershell
    Test-Path 'C:\Program Files\Git\bin\bash.exe'
    ```
    Expected: `True`. If `False`, **STOP and escalate to the user.** Do **not** attempt to translate commands to PowerShell/rg/Python ad hoc — the plan is not shaped for that mode.

- [ ] **Verify Git Bash version.**
    ```powershell
    & 'C:\Program Files\Git\bin\bash.exe' --version
    ```
    Expected: `GNU bash, version 4.x` or later. Record the version line in the exit artifact.

- [ ] **Define the execution convention.** Every PowerShell session that runs a Phase 5 sub-phase must set these two variables before running any command from §5:
    ```powershell
    $BASH      = 'C:\Program Files\Git\bin\bash.exe'
    $REPO_UNIX = '/c/Users/aviha/Downloads/Hypertrophy-Toolbox-v3-main'
    ```

- [ ] **Canonical command form.** Every Unix snippet in §5 is written as a single-line bash command. Sonnet wraps each one exactly as follows before running:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && <command>"
    ```
    Use double-quoted PowerShell strings so `$BASH` and `$REPO_UNIX` interpolate. The inner bash command uses single quotes for `cd` and any embedded regex/awk strings — see the sanity-check below for the shape.

- [ ] **Sanity-check the convention.** Run a no-op that prints the current HEAD:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git rev-parse HEAD"
    ```
    Expected: prints the current HEAD commit hash. If this fails, **STOP** — the wrapper is broken; do not proceed to P1.

- [ ] **Write `debug/P0_phase5_shell.md`:**
    - Git Bash version line
    - `$BASH` and `$REPO_UNIX` values
    - Output of the sanity-check (HEAD hash)
    - Verdict: `PASS` | `STOPPED`

**P0 exit gate:** `debug/P0_phase5_shell.md` exists with `PASS`. Without P0, no other sub-phase may run — every subsequent `& $BASH -lc` call depends on the convention being verified here.

### P1 — Environment sanity
**Exit artifact:** `debug/P1_phase5_env.md`

- [ ] Current branch == `spring-cleanup`:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git branch --show-current"
    ```
- [ ] HEAD advertises commit `12c90ac` in its reachable history:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git log --oneline | grep -m1 12c90ac"
    ```
- [ ] Python 3.10+ in the repo venv:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe --version"
    ```
- [ ] Record each value in the exit artifact.

### P2 — Baseline recapture
**Exit artifact:** `debug/P2_phase5_baseline.md`

> **Why:** the parent plan's last recorded baseline was `934 passed, 1 skipped` post-4C. Phase 5 P2 captured `936 passed, 1 skipped` after the `ec748ba` progression fix added 2 new tests to `tests/test_progression_plan_routes.py`. Every subsequent action in this plan gates on the **live** pytest number, not the parent plan's stale number. **Note:** after 5I runs, the baseline rolls forward — see `debug/5I_postbaseline.md` for the gate used by 5J and later sub-phases.

- [ ] Run:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/P2_pytest.txt 2>&1"
    ```
- [ ] Record the last line of `debug/P2_pytest.txt` (e.g., `936 passed, 1 skipped in 125.3s`) as the **Phase 5 baseline** in `debug/P2_phase5_baseline.md`
- [ ] If the live number is **lower** than 936: stop and escalate — the working tree has regressed since CLAUDE.md was last verified
- [ ] If the live number is **higher** than 936: accept as the new baseline and record the new value; the plan uses "≥ Phase 5 baseline" not "== 936"

### P3 — Git state snapshot
**Exit artifact:** `debug/P3_phase5_git.md`

- [ ] Capture the target-file commit history:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git log --oneline 47736b9..HEAD -- utils/progression_plan.py utils/session_summary.py utils/export_utils.py routes/workout_plan.py routes/exports.py"
    ```
    → should list at most `12c90ac`, `ec748ba`, and `73bc1eb`
    → `73bc1eb` is the accepted follow-up that changed Progression no-history prompt copy in `utils/progression_plan.py` after the `ec748ba` plan-values fix.
- [ ] Capture the working-tree state:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git status --short"
    ```
    → record the exact modified/untracked set. Every subsequent sub-phase cross-references this list to detect drift. **After 5I runs, `tests/test_exports.py` is expected to appear as modified — that is not drift, it is 5I's sanctioned output.**
- [ ] Capture HEAD:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git rev-parse HEAD"
    ```

### P4 — Rollback checkpoint
**Exit artifact:** `debug/P4_phase5_rollback.md`

> **Not read-only.** P4 creates a git tag. This is the **only** prerequisite that writes repo state, and it is a repo-metadata write, not a source-file write. Per Codex review, tag creation is **idempotent**: if the tag already exists at the current HEAD, reuse it; if it exists at a different HEAD, halt and escalate (never force-update).

- [ ] Record current HEAD hash (from P3): this is the Phase 5 rollback target.

- [ ] **Check whether the tag already exists.**
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git tag -l phase5-rollback-point"
    ```
    - **If output is empty:** create the tag.
        ```powershell
        & $BASH -lc "cd '$REPO_UNIX' && git tag phase5-rollback-point HEAD"
        ```
    - **If output contains `phase5-rollback-point`:** the tag exists from a prior run. Verify it still points to the current HEAD:
        ```powershell
        & $BASH -lc "cd '$REPO_UNIX' && git rev-parse phase5-rollback-point"
        & $BASH -lc "cd '$REPO_UNIX' && git rev-parse HEAD"
        ```
        If the two hashes are equal → record "tag already exists at current HEAD, reused" in the artifact and skip creation.
        If the two hashes differ → **STOP and escalate**. Do not force-update the tag. An existing tag at a different commit is evidence of a prior Phase 5 attempt whose state the user must reconcile.

- [ ] Verify the tag is present:
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git tag -l phase5-rollback-point"
    ```
    Expected: exactly one line, `phase5-rollback-point`.

- [ ] **Document the emergency whole-file restore command** in the artifact:
    ```
    git show 47736b9:<path> > <path>
    ```
    This is a **whole-file** restore, not a per-function restore. It reverts every change to that file between `47736b9` (pre-cleanup snapshot) and HEAD — including any unrelated `3a-3h` cleanup work co-located in the same file. Use only if a sub-phase fails beyond repair AND the user explicitly approves AND the user accepts collateral revert of unrelated work. §8 Rollback Playbook is the authoritative procedure; P4 only records the tag and the restore shape.

**Prerequisite gate:** all five `debug/P0_phase5_shell.md`, `debug/P1_phase5_env.md`, `debug/P2_phase5_baseline.md`, `debug/P3_phase5_git.md`, `debug/P4_phase5_rollback.md` present before any sub-phase (`5A`..`5O`) runs. If any fails, stop and resolve before continuing.

---

## 2. Execution Rules for LLM Handoffs

- **One sub-phase per conversation session.** Never combine.
- **Token budget per sub-phase:** ≤15k **input** tokens. Source file reads MUST use the explicit `offset` / `limit` values given in each sub-phase's "Files referenced" block — do not read whole files.
- **Exit artifact required** for every sub-phase. No verbal "done" — always a file on disk under `debug/5<letter>_*.md` (or `debug/P<n>_*.md` for prerequisites). The artifact is the contract.
- **Full pytest gate** after every sub-phase. Result must be `≥ Phase 5 baseline`. The baseline is `debug/P2_phase5_baseline.md` for sub-phases 5A–5H; after 5I runs, the baseline rolls forward to `debug/5I_postbaseline.md` and every sub-phase from 5J onward gates on that new number. Any regression → STOP, diagnose, escalate.
- **No combining sub-phases.** Each has its own exit criterion.
- **Write scope is strictly enforced.** Phase 5 is read-only for source code **except** for exactly two sanctioned write sub-phases:
  - **5I** may edit `tests/test_exports.py` and ONLY that file. 5I rewrites a defective characterization test and adds two new ones. No other file may be touched by 5I.
  - **5O** may edit `docs/code_cleanup_plan.md` and ONLY that file, and only after `5A`..`5J` + `5E` all report PASS or user-acknowledged ESCALATE.
  - Every other sub-phase may write ONLY to `debug/` artifact files (exit artifacts and diff dump files). Any write outside these allowances → halt the sub-phase, write `debug/<letter>_ANOMALY.md`, escalate to user.
- **Unix-syntax commands MUST be wrapped per P0.** Every snippet in §5 using `bash`, `grep`, `sed`, `awk`, `rg`, `diff`, or shell pipes/redirects is written in Unix syntax. Sonnet wraps each one exactly as `& $BASH -lc "cd '$REPO_UNIX' && <command>"` where `$BASH` and `$REPO_UNIX` are set per P0. **Do not translate commands to PowerShell. Do not re-implement in Python.** If a command's quoting gets ambiguous, halt and escalate — do not guess.
- **Anomaly logging is a file, not an edit to this plan.** If any command output is unexpected (extra files in git status, missing helper, pytest count < baseline, signature delta, drift), STOP and write `debug/<letter>_ANOMALY.md` describing the anomaly. **Never edit `docs/phase5_3i_plan.md`** — this file is an Opus-authored plan document; §9 Execution Notes is updated only by Opus between sessions, never by Sonnet mid-execution.
- **Expected dirty-state exception after 5I.** Once 5I runs, `git status --short` will show `tests/test_exports.py` as `M`. Every sub-phase from 5J onward must treat this one file as expected-dirty and NOT escalate on it. The `debug/5I_test_hardening.md` artifact is the proof that this state is sanctioned. Revert (via user rollback of 5I) returns `tests/test_exports.py` to clean; that also triggers 5J to re-escalate on its next run.
- **Fresh LLM session continuity:** a session picking up mid-plan must be able to continue by reading (a) this file, (b) the most recent `debug/*.md` artifact, (c) the source-file line ranges named in the active sub-phase. Never read the whole plan linearly — use the Reading Order table and jump to the active section.
- **No git operations other than read-only** (`git show`, `git log`, `git diff`, `git status`, `git tag -l`, `git rev-parse`) and the single `git tag phase5-rollback-point` in P4. No `git reset`, no `git revert`, no `git commit`, no `git add`, no `git push`, no `git stash`, no `git checkout -- <file>`.

---

## 3. Frozen Offender Inventory

> **Contract.** The line ranges and helper names below are frozen at 2026-04-11 against `HEAD` reachable from commit `ec748ba`. If a subsequent commit shifts these ranges, each sub-phase's `Grep` for the function / helper name remains authoritative — line numbers are a convenience, names are the contract.

| Sub-phase | File | Function | Current lines | Current size | Pre-cleanup size | Helpers extracted | Test file(s) | Test count |
|---|---|---|---|---|---|---|---|---|
| 5A (3i-a) | `utils/progression_plan.py` | `generate_progression_suggestions` | L347–420 | 74 | 224 | `_build_primary_weight_suggestion` (L147), `_build_primary_rep_suggestion` (L175), `_build_maintenance_suggestion` (L209), `_build_technique_and_volume_suggestions` (L229), `_build_manual_progression_options` (L254) | `tests/test_double_progression.py` + `tests/test_progression_plan_utils.py` | 25 + 43 = 68 |
| 5B (3i-b) | `utils/session_summary.py` | `calculate_session_summary` | L251–299 | 49 | 256 | `_build_plan_query` (L21), `_build_log_query` (L46), `_aggregate_muscle_volumes` (L72), `_aggregate_session_dates` (L159), `_build_summary_output` (L181) | `tests/test_session_summary.py` | 30 |
| 5C (3i-c) | `utils/export_utils.py` | `create_excel_workbook` | L288–407 | 120 | 227 | `_setup_formats` (L183), `_build_superset_color_map` (L224), `_write_worksheet` (L235) | `tests/test_exports.py` | 37 |
| 5D (3i-d) | `routes/workout_plan.py` | `replace_exercise` | L1026–1168 | 143 | 230 | `_fetch_current_exercise_details` (L962), `_build_replacement_candidates` (L974), `_perform_exercise_swap` (L994) | `tests/test_workout_plan_routes.py` | 32 |
| 5E (3i-e) | `routes/exports.py` | `export_to_excel` | L463–530 | 68 | 338 | `_recalculate_exercise_order` (L290), `_build_export_query` (L335), `_fetch_all_sheets` (L388) | `tests/test_exports.py` (same 37 cover both 5C and 5E) | 37 |
| 5F (3i-f) | `routes/workout_plan.py` | `suggest_supersets` | L1712–1772 | 61 | 139 | `_group_exercises_by_routine` (L1641), `_find_antagonist_pairings` (L1651); module-level `ANTAGONIST_PAIRS` moved to `utils/constants.py` | `tests/test_superset.py` + `tests/test_workout_plan_routes.py` | 14 + 32 = 46 |
| 5G (3i-g) | `routes/workout_plan.py` | `set_execution_style` | L1543–1590 | 48 | 138 | `_validate_and_normalize_execution_params` (L1422), `_update_execution_style_db` (L1487) | `tests/test_workout_plan_routes.py` | 32 |
| 5H (3i-h) | `routes/workout_plan.py` | `link_superset` | L1252–1319 | 68 | 131 | `_validate_superset_link_request` (L1175), `_apply_superset_link` (L1224) | `tests/test_superset.py` | 14 |
| 5J (3j)   | `routes/exports.py` | `_recalculate_exercise_order` (the function whose internals changed from per-row `UPDATE` loop to `executemany`) | L290–333 | 44 | ~30 (was inline inside `export_to_excel`) | Batch update via `db.executemany("UPDATE user_selection SET exercise_order = ? WHERE id = ?", ...)` | `tests/test_exports.py` | 37 |

**Signature-freeze baseline commit:** `47736b9` (pre-cleanup snapshot). Every sub-phase compares the current function signature against `git show 47736b9:<file>` to detect any unintended contract change.

**Cross-reference to test counts:** The product of the Phase 5 baseline (P2) minus the sum of test file counts above is the "adjacent / unrelated" test coverage. Sub-phases must not regress either the per-file count or the full-suite count.

> **5I is not a function validation — it is in §5 for ordering only.** 5I hardens `tests/test_exports.py`: it rewrites one defective test (`test_recalculate_exercise_order_atomic_failure`) and adds two new characterization tests (NULL-initialization path, no-op path). It does not validate any production function. It is listed as a sub-phase because 5J's ≥95% confidence depends on 5I's tests existing. After 5I, the `tests/test_exports.py` count in the table above rolls forward by +2 (one net-new rewrite, two additions → `+2 passed`).

---

## 4. Cross-Cutting Invariants

These invariants apply to every sub-phase and must be asserted in each exit artifact. A sub-phase that violates any invariant is marked **ESCALATE** (not FAIL) — the user decides whether to add characterization tests or accept the delta.

| Invariant | How to check | Where |
|---|---|---|
| **I-1 — Public signature unchanged** | `git show 47736b9:<file>` and current file: the function's `def <name>(...)` line and its `->` return annotation are byte-identical (ignoring trailing whitespace and blank-line diffs) | Step 2 of every sub-phase |
| **I-2 — No new SQL tokens in the main function** | `git diff 47736b9..HEAD -- <file>` filtered to `[+-].*\b(SELECT\|INSERT\|UPDATE\|DELETE\|FROM\|WHERE\|JOIN)\b` — every `+` line must correspond to a `-` line with the same SQL shape (the helper extraction moved the SQL but did not rewrite it). When an action has accepted adjacent-file drift, its Step 3 may narrow the check to the target function body to avoid false positives from unrelated helpers. **Exception:** 5J explicitly introduces `executemany` over the old per-row loop — the exception is recorded in §5J. | Step 3 of every sub-phase |
| **I-3 — No response-shape change for route sub-phases** | `git diff 47736b9..HEAD -- <file>` filtered to `[+-].*\b(success_response\|error_response\|jsonify\|return.*data=)\b` — diff must show no new response keys and no removed keys. Applies to 5D, 5E, 5F, 5G, 5H, 5J | Step 4 of route sub-phases |
| **I-4 — No logger level downgrade** | `git diff 47736b9..HEAD -- <file>` filtered to `[+-].*\b(logger\.(info\|warning\|error\|exception\|debug\|critical))\b` — every `-` logger call at level L must be matched by a `+` call at level ≥ L (ERROR not downgraded to WARNING, WARNING not downgraded to INFO, etc.) | Step 5 of every sub-phase |
| **I-5 — Targeted test file count does not regress** | Per-file pytest count ≥ the count recorded in the §3 inventory table | Step 6 of every sub-phase |
| **I-6 — Full-suite pytest ≥ Phase 5 baseline** | `.venv/Scripts/python.exe -m pytest tests/ -q` result compared to `debug/P2_phase5_baseline.md` | Step 7 of every sub-phase |

**Escalation rule:** a sub-phase that detects an I-1..I-4 violation must NOT proceed to "PASS" — the exit artifact records `ESCALATE` with the specific invariant that failed, the exact diff snippet, and a one-sentence hypothesis. The user decides the remediation.

---

## 5. Sub-Phase Actions

### 5A — Validate 3i-a: `generate_progression_suggestions`

**Target file:** [utils/progression_plan.py](../utils/progression_plan.py)
**Target function:** `generate_progression_suggestions`
**Exit artifact:** `debug/5A_progression_plan.md`
**Token budget:** ~4.5k input (source: ~180 lines × ~25 tok/line ≈ 4.5k; test file reads are metadata only via Grep)

**Files referenced (use these exact offsets — do not read whole files):**
- `utils/progression_plan.py` offset=1 limit=6 (imports)
- `utils/progression_plan.py` offset=147 limit=172 (helper bodies `_build_primary_weight_suggestion` through `_build_manual_progression_options`)
- `utils/progression_plan.py` offset=347 limit=75 (current composer body)
- `tests/test_double_progression.py` — Grep count only, no Read
- `tests/test_progression_plan_utils.py` — Grep count only, no Read

**Steps:**

1. **Helper presence audit.** Run:
   - `Grep` pattern `^def _build_primary_weight_suggestion` in `utils/progression_plan.py` → must return ≥1 hit
   - `Grep` pattern `^def _build_primary_rep_suggestion` → must return ≥1 hit
   - `Grep` pattern `^def _build_maintenance_suggestion` → must return ≥1 hit
   - `Grep` pattern `^def _build_technique_and_volume_suggestions` → must return ≥1 hit
   - `Grep` pattern `^def _build_manual_progression_options` → must return ≥1 hit
   - Any miss → record as ESCALATE (I-1) and stop.

2. **Signature freeze check (I-1).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:utils/progression_plan.py | sed -n '/^def generate_progression_suggestions/,/^) -> /p' > debug/5A_sig_baseline.txt"
   & $BASH -lc "cd '$REPO_UNIX' && sed -n '/^def generate_progression_suggestions/,/^) -> /p' utils/progression_plan.py > debug/5A_sig_current.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff -u debug/5A_sig_baseline.txt debug/5A_sig_current.txt"
   ```
   Expected: zero-diff (empty output). Any diff → ESCALATE (I-1).

3. **SQL/response-shape diff (I-2, I-3).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def generate_progression_suggestions/{p=1} p && /^def / && !/^def generate_progression_suggestions/{exit} p{print}' utils/progression_plan.py | rg -n '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|jsonify|success_response|error_response)\b' > debug/5A_sql_diff.txt || true"
   ```
   Expected: empty (this target function touches no SQL and no Flask response helpers — it only consumes `history` dicts and returns a list of dicts). This command intentionally inspects the current `generate_progression_suggestions` body, not the whole file, because the accepted `ec748ba`/`73bc1eb` progression follow-ups added adjacent plan-default helpers above the target function. Any hit → ESCALATE (I-2/I-3).

4. **Logger-level diff (I-4).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git diff 47736b9..HEAD -- utils/progression_plan.py | rg -n '^[+-].*\blogger\.(info|warning|error|exception|debug|critical)\b' > debug/5A_logger_diff.txt"
   ```
   Expected: empty or matched pairs (no downgrade). Manual review if non-empty.

5. **Targeted test rerun (I-5).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_double_progression.py tests/test_progression_plan_utils.py -q > debug/5A_targeted.txt 2>&1"
   ```
   Expected: `68 passed` (25 + 43). Any regression → ESCALATE (I-5).

6. **Full pytest gate (I-6).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5A_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline` from `debug/P2_phase5_baseline.md`. Any regression → STOP, write `debug/5A_ANOMALY.md`, and hand back to the user.

7. **Write exit artifact `debug/5A_progression_plan.md`:**
   ```markdown
   # 5A — generate_progression_suggestions Validation

   **Verdict:** PASS | ESCALATE | FAIL
   **Date:** <YYYY-MM-DD>
   **Phase 5 baseline:** <from P2>

   | Check | Result |
   |---|---|
   | Helpers present (5/5) | <✓ / list of misses> |
   | Signature byte-identical to 47736b9 | <✓ / diff snippet> |
   | SQL/response diff empty | <✓ / snippet> |
   | Logger level diff empty or paired | <✓ / snippet> |
   | Targeted tests | <count> passed |
   | Full pytest | <count> passed, <count> skipped |

   **Anomalies:** <none | list>
   **Next action:** 5B
   ```

**5A exit gate:** artifact written with `PASS` verdict OR user-acknowledged ESCALATE.

---

### 5B — Validate 3i-b: `calculate_session_summary`

**Target file:** [utils/session_summary.py](../utils/session_summary.py)
**Target function:** `calculate_session_summary`
**Exit artifact:** `debug/5B_session_summary.md`
**Token budget:** ~5k input

**Files referenced:**
- `utils/session_summary.py` offset=1 limit=20 (imports and enum)
- `utils/session_summary.py` offset=21 limit=230 (all five helpers)
- `utils/session_summary.py` offset=251 limit=50 (current composer body)
- `tests/test_session_summary.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _build_plan_query`
   - `^def _build_log_query`
   - `^def _aggregate_muscle_volumes`
   - `^def _aggregate_session_dates`
   - `^def _build_summary_output`
   All must return ≥1 hit in `utils/session_summary.py`.

2. **Signature freeze check (I-1).** Same pattern as 5A step 2. Exit artifact: `debug/5B_sig_*.txt`. Zero-diff required.

3. **SQL/response-shape diff (I-2).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git diff 47736b9..HEAD -- utils/session_summary.py | rg -n '^[+-].*\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' > debug/5B_sql_diff.txt"
   ```
   Expected: matched `-`/`+` pairs only (the SQL moved from the main function into `_build_plan_query` / `_build_log_query` — token-for-token). Any unpaired line → ESCALATE (I-2).

4. **No response-shape check needed** — this is a utility, not a route. Note "N/A" in the exit artifact row.

5. **Logger-level diff (I-4).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git diff 47736b9..HEAD -- utils/session_summary.py | rg -n '^[+-].*\blogger\.(info|warning|error|exception|debug|critical)\b' > debug/5B_logger_diff.txt"
   ```
   Expected: empty or matched pairs. Manual review if non-empty.

6. **Targeted test rerun (I-5).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_session_summary.py -q > debug/5B_targeted.txt 2>&1"
   ```
   Expected: `30 passed` (minimum).

7. **Full pytest gate (I-6).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5B_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline`. Any regression → STOP, write `debug/5B_ANOMALY.md`, hand back to user.

8. **Write exit artifact `debug/5B_session_summary.md`** using the same table shape as 5A.

**5B exit gate:** artifact written with `PASS` verdict OR user-acknowledged ESCALATE.

---

### 5C — Validate 3i-c: `create_excel_workbook`

**Target file:** [utils/export_utils.py](../utils/export_utils.py)
**Target function:** `create_excel_workbook`
**Exit artifact:** `debug/5C_create_excel_workbook.md`
**Token budget:** ~5.5k input

**Files referenced:**
- `utils/export_utils.py` offset=1 limit=12 (imports)
- `utils/export_utils.py` offset=183 limit=105 (helpers `_setup_formats`, `_build_superset_color_map`, `_write_worksheet`)
- `utils/export_utils.py` offset=288 limit=125 (current composer body)
- `tests/test_exports.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _setup_formats`
   - `^def _build_superset_color_map`
   - `^def _write_worksheet`
   All must return ≥1 hit.

2. **Signature freeze check (I-1).** Match `def create_excel_workbook(` through the `) -> Response:` line between `47736b9` and current.

3. **SQL/response-shape diff (I-2, I-3).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git diff 47736b9..HEAD -- utils/export_utils.py | rg -n '^[+-].*\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|make_response|create_content_disposition_header)\b' > debug/5C_sql_response_diff.txt"
   ```
   Expected: zero SQL hits (this is pure xlsxwriter code — no DB access). The `make_response` and `create_content_disposition_header` calls should appear as `-`/`+` pairs if the Response assembly was re-indented, or pure `-` if moved to a helper and then a matching `+` in the helper. Any unpaired line → ESCALATE.

4. **Logger-level diff (I-4).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git diff 47736b9..HEAD -- utils/export_utils.py | rg -n '^[+-].*\blogger\.(info|warning|error|exception|debug|critical)\b' > debug/5C_logger_diff.txt"
   ```
   This function has many `logger.info` / `logger.error` calls — expect many matched pairs and **any** unmatched `+` / `-` at a different level is ESCALATE.

5. **Targeted test rerun (I-5).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_exports.py -q > debug/5C_targeted.txt 2>&1"
   ```
   Expected: `≥ 37 passed`.

6. **Full pytest gate (I-6).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5C_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline`. Regression → STOP, write `debug/5C_ANOMALY.md`, escalate.

7. **Write exit artifact `debug/5C_create_excel_workbook.md`.**

**5C exit gate:** artifact written, PASS or acknowledged ESCALATE.

---

### 5D — Validate 3i-d: `replace_exercise`

**Target file:** [routes/workout_plan.py](../routes/workout_plan.py)
**Target function:** `replace_exercise`
**Exit artifact:** `debug/5D_replace_exercise.md`
**Token budget:** ~5k input

**Files referenced:**
- `routes/workout_plan.py` offset=1 limit=25 (imports)
- `routes/workout_plan.py` offset=962 limit=65 (helpers `_fetch_current_exercise_details`, `_build_replacement_candidates`, `_perform_exercise_swap`)
- `routes/workout_plan.py` offset=1026 limit=145 (current composer body, through L1168)
- `tests/test_workout_plan_routes.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _fetch_current_exercise_details`
   - `^def _build_replacement_candidates`
   - `^def _perform_exercise_swap`

2. **Signature freeze check (I-1).** Match `def replace_exercise()` — a no-arg route handler; signature match is simply the function name line and the decorator (if any) immediately above.

3. **Function-bound body extraction.** `routes/workout_plan.py` contains many routes; we cannot diff the whole file without false positives. Extract just `replace_exercise`'s body from the pre-cleanup and current versions using awk boundaries (start at `def replace_exercise`, stop at the next top-level `def`):
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | awk '/^def replace_exercise/{p=1; print; next} p && /^def /{exit} p{print}' > debug/5D_old_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def replace_exercise/{p=1; print; next} p && /^def /{exit} p{print}' routes/workout_plan.py > debug/5D_new_body.txt"
   ```
   Both files must be non-empty. If `debug/5D_old_body.txt` is empty, the function name changed in `47736b9` → ESCALATE (I-1). If `debug/5D_new_body.txt` is empty, the current tree lost the function → hard STOP.

4. **SQL audit (I-2) — within the extracted body only.** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5D_old_body.txt > debug/5D_old_sql.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5D_new_body.txt > debug/5D_new_sql.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5D_old_sql.txt debug/5D_new_sql.txt"
   ```
   **Expected delta pattern:** SQL statements that used to live in the composer may now be absent from the composer body and present in helpers (`_fetch_current_exercise_details`, `_build_replacement_candidates`, `_perform_exercise_swap`). Either (a) a line is in both files unchanged, or (b) a line was removed from the composer AND appears in a helper. Verify the second case by also extracting the helper bodies:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def (_fetch_current_exercise_details|_build_replacement_candidates|_perform_exercise_swap)/{p=1; print; next} p && /^def /{if(!/^def (_fetch_current_exercise_details|_build_replacement_candidates|_perform_exercise_swap)/){p=0}} p{print}' routes/workout_plan.py > debug/5D_helpers_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5D_helpers_body.txt > debug/5D_helpers_sql.txt"
   ```
   Every SQL line removed from `5D_old_sql.txt` (i.e., in old but not new) must appear in `5D_helpers_sql.txt`. Missing → ESCALATE (I-2).

5. **Response-shape audit (I-3) — within the extracted body AND helpers.** The old `replace_exercise` response shape lives in the whole function body (including late `success_response(data=...)` calls near the end — the `-A3` window of the prior revision missed them). Using function-bound extraction:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5D_old_body.txt > debug/5D_old_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5D_new_body.txt > debug/5D_new_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5D_helpers_body.txt > debug/5D_helpers_response.txt"
   ```
   **Decision rule:** every `error_response("<CODE>", ...)` key string that appears in `debug/5D_old_response.txt` must appear in the union of `debug/5D_new_response.txt` + `debug/5D_helpers_response.txt`. The expected error codes are: `"NOT_FOUND"`, `"VALIDATION_ERROR"`, `"NO_CANDIDATES"`, `"DUPLICATE"`, `"SELECTION_FAILED"`, `"INTERNAL_ERROR"`. Any missing code → ESCALATE (I-3).

   > **Codex correction (2026-04-11):** the prior revision used `rg -nA3 'def replace_exercise'` which only captured 3 lines after the `def`, missing the success-response `data=` call around `routes/workout_plan.py:1153`. The awk function-bound extraction above captures the entire function body regardless of its length (currently L1026–1168, 143 lines).

6. **Logger-level diff (I-4).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5D_old_body.txt > debug/5D_old_logger.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5D_new_body.txt > debug/5D_new_logger.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5D_helpers_body.txt > debug/5D_helpers_logger.txt"
   ```
   This function logs at `info`, `warning`, and `exception` levels. No level downgrade between old and (new + helpers) union.

7. **Targeted test rerun (I-5).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_workout_plan_routes.py -q > debug/5D_targeted.txt 2>&1"
   ```
   Expected: `31 passed, 1 skipped` (32 collected). The skipped test is the page-template availability check, which is intentionally skipped in the unit-test environment and matches the full-suite baseline's single skip.

8. **E2E smoke (optional but recommended).** Since `replace_exercise` is exercised by Playwright tests in `e2e/exercise-interactions.spec.ts` and `e2e/replace-exercise-errors.spec.ts`, this action may additionally run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && npx playwright test e2e/exercise-interactions.spec.ts e2e/replace-exercise-errors.spec.ts --project=chromium --reporter=line > debug/5D_e2e.txt 2>&1"
   ```
   This step is optional — if Playwright is not installed, skip and record "E2E skipped — Playwright unavailable" in the exit artifact.

9. **Full pytest gate (I-6).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5D_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline`. Regression → STOP, write `debug/5D_ANOMALY.md`, escalate.

10. **Write exit artifact `debug/5D_replace_exercise.md`** — use the same verdict table shape as 5A, including rows for the function-bound extraction files, the SQL/response/logger audits on composer + helpers union, and the optional E2E result.

**5D exit gate:** artifact written, PASS or acknowledged ESCALATE.

---

### 5E — Validate 3i-e: `export_to_excel`

**Target file:** [routes/exports.py](../routes/exports.py)
**Target function:** `export_to_excel`
**Exit artifact:** `debug/5E_export_to_excel.md`
**Token budget:** ~5k input
**Execution order:** runs **after** 5J. See §10 Action Count Summary for the full ordering. Letters are stable labels, not execution order.
**Depends on:** 5C (same test file), 5I (baseline rollover), **5J (must run first — see Codex review v1)**.

> **Why this ordering.** The earlier plan revision recommended running 5E before 5J because 5E "only validates helper extraction." Codex's review identified this as internally inconsistent: `export_to_excel` internally calls `_recalculate_exercise_order`, so 5E's response-shape and behavior claims cannot be verified without knowing whether `_recalculate_exercise_order`'s semantics (per-row → atomic executemany) are covered. The revised ordering has 5J completing first, producing `debug/5J_recalculate_exercise_order.md`, which 5E then consumes as a prerequisite gate in step 3.

**Files referenced:**
- `routes/exports.py` offset=1 limit=20 (imports)
- `routes/exports.py` offset=290 limit=175 (helpers `_recalculate_exercise_order`, `_build_export_query`, `_fetch_all_sheets`)
- `routes/exports.py` offset=462 limit=70 (current composer body, through L530)
- `tests/test_exports.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _recalculate_exercise_order`
   - `^def _build_export_query`
   - `^def _fetch_all_sheets`

2. **Signature freeze check (I-1).** Match `def export_to_excel()` and the `@exports_bp.route("/export_to_excel", methods=['GET'])` decorator.

3. **5J prerequisite gate.** 5E now runs **after** 5J per Codex review — `export_to_excel` calls `_recalculate_exercise_order` internally, and 5E cannot confidently validate composer equivalence without 5J's characterization verdict in hand. Read `debug/5J_recalculate_exercise_order.md`. Verdict must be PASS or user-acknowledged ESCALATE. If missing, STOP and return to user — do not run 5E before 5J.

4. **Function-bound body extraction.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/exports.py | awk '/^def export_to_excel/{p=1; print; next} p && /^def /{exit} p{print}' > debug/5E_old_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def export_to_excel/{p=1; print; next} p && /^def /{exit} p{print}' routes/exports.py > debug/5E_new_body.txt"
   ```

5. **SQL/response-shape diff (I-2, I-3) — composer body only.** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b|success_response\(|error_response\(|jsonify\(' debug/5E_old_body.txt > debug/5E_old_sql_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b|success_response\(|error_response\(|jsonify\(' debug/5E_new_body.txt > debug/5E_new_sql_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5E_old_sql_response.txt debug/5E_new_sql_response.txt"
   ```
   Route response helpers must appear as matched pairs. **Expected delta:** SQL statements that used to live inline in `export_to_excel` now live in `_build_export_query`, `_fetch_all_sheets`, or `_recalculate_exercise_order`. 5E RECORDS the delta but does NOT re-audit the batch-update shape — that scope belongs to 5J (already completed per step 3's gate). Copy 5J's verdict into 5E's exit artifact as a "dependent sub-phase" row.

6. **Logger-level diff (I-4).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5E_old_body.txt > debug/5E_old_logger.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5E_new_body.txt > debug/5E_new_logger.txt"
   ```
   Manual compare — no level downgrade.

7. **Targeted test rerun (I-5).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_exports.py -q > debug/5E_targeted.txt 2>&1"
   ```
   Expected: `≥` the post-5I count recorded in `debug/5I_postbaseline.md`.

8. **Full pytest gate (I-6).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5E_fullpytest.txt 2>&1"
   ```
   Expected: `≥` the post-5I Phase 5 baseline.

9. **Write exit artifact `debug/5E_export_to_excel.md`** with explicit rows for: the 5J dependent-verdict cross-link, the composer body extraction files, the SQL/response/logger audits, and the pytest gates.

**5E exit gate:** artifact written, PASS or acknowledged ESCALATE.

---

### 5F — Validate 3i-f: `suggest_supersets`

**Target file:** [routes/workout_plan.py](../routes/workout_plan.py)
**Target function:** `suggest_supersets`
**Exit artifact:** `debug/5F_suggest_supersets.md`
**Token budget:** ~5k input

**Files referenced:**
- `routes/workout_plan.py` offset=1641 limit=70 (helpers `_group_exercises_by_routine`, `_find_antagonist_pairings`)
- `routes/workout_plan.py` offset=1712 limit=65 (current composer body)
- `utils/constants.py` — Grep for `ANTAGONIST_PAIRS` (confirms the constants move)
- `tests/test_superset.py` — Grep count only
- `tests/test_workout_plan_routes.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _group_exercises_by_routine` in `routes/workout_plan.py`
   - `^def _find_antagonist_pairings` in `routes/workout_plan.py`
   - `ANTAGONIST_PAIRS` in `utils/constants.py` (at least one definition line, not just a usage)

2. **Cross-file constant move audit.** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | grep -nE 'ANTAGONIST_PAIRS\s*=\s*\{' > debug/5F_old_const.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'ANTAGONIST_PAIRS\s*=\s*\{' routes/workout_plan.py utils/constants.py > debug/5F_new_const.txt"
   ```
   Expected: `5F_old_const.txt` shows a definition in `routes/workout_plan.py`; `5F_new_const.txt` shows the definition has moved to `utils/constants.py` (zero hits in `routes/workout_plan.py`, ≥1 hit in `utils/constants.py`). **Additionally verify that the content (dictionary keys and lists) is byte-identical after normalizing indentation.** In `47736b9`, the dict was indented inside `suggest_supersets`; in current HEAD, it is top-level in `utils/constants.py`. Extract the dict block from both locations (from `ANTAGONIST_PAIRS = {` to the matching closing `}` on a line by itself), strip leading indentation, and diff:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | awk '/^[[:space:]]*ANTAGONIST_PAIRS[[:space:]]*=[[:space:]]*\{/{p=1} p{print} p && /^[[:space:]]*\}/{exit}' | sed -E 's/^[[:space:]]+//' > debug/5F_old_const_block.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^[[:space:]]*ANTAGONIST_PAIRS[[:space:]]*=[[:space:]]*\{/{p=1} p{print} p && /^[[:space:]]*\}/{exit}' utils/constants.py | sed -E 's/^[[:space:]]+//' > debug/5F_new_const_block.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5F_old_const_block.txt debug/5F_new_const_block.txt"
   ```
   Any value delta → ESCALATE (I-2/I-3 generalized: constants are part of the public data contract).

3. **Signature freeze check (I-1).** Match `def suggest_supersets()`:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | grep -E '^def suggest_supersets' > debug/5F_old_sig.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -E '^def suggest_supersets' routes/workout_plan.py > debug/5F_new_sig.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5F_old_sig.txt debug/5F_new_sig.txt"
   ```

4. **Function-bound body extraction.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | awk '/^def suggest_supersets/{p=1; print; next} p && /^def /{exit} p{print}' > debug/5F_old_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def suggest_supersets/{p=1; print; next} p && /^def /{exit} p{print}' routes/workout_plan.py > debug/5F_new_body.txt"
   ```
   Both files must be non-empty.

5. **Response-shape diff (I-3) — function-bound.** The old `suggest_supersets` response lives throughout its 139-line body (pre-cleanup); the new composer is 61 lines but its response data is at the end of the function (around `routes/workout_plan.py:1765`) — **far past a `-A5` window**. Function-bound extraction handles this:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5F_old_body.txt > debug/5F_old_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5F_new_body.txt > debug/5F_new_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5F_old_response.txt debug/5F_new_response.txt"
   ```
   **Decision rule:** every response call with the same semantic key (error codes, data= shape) must be present in both. The diff is unlikely to be byte-empty because the composer now delegates work to helpers — but the **set of error codes** emitted must be identical. Any missing error code → ESCALATE (I-3).

   > **Codex correction (2026-04-11):** the prior revision used `rg -A5 'def suggest_supersets'` which only captured 5 lines after the `def`, missing the actual response `data=` call around `routes/workout_plan.py:1747` and `routes/workout_plan.py:1765`. The awk function-bound extraction captures the whole composer body (currently L1712–1772).

6. **SQL diff (I-2) — composer body only.** `suggest_supersets` was historically all Python logic (antagonist pair lookup, routine grouping) with minimal SQL. Confirm:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5F_old_body.txt > debug/5F_old_sql.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5F_new_body.txt > debug/5F_new_sql.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5F_old_sql.txt debug/5F_new_sql.txt"
   ```
   Expected: matched or empty.

7. **Targeted test rerun (I-5).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_superset.py tests/test_workout_plan_routes.py -q > debug/5F_targeted.txt 2>&1"
   ```
   Expected: `45 passed, 1 skipped` (46 collected). The skipped test is the same intentional page-template availability skip documented in 5D.

8. **Full pytest gate (I-6).** Run:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5F_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline`. Regression → STOP, write `debug/5F_ANOMALY.md`, escalate.

9. **Write exit artifact `debug/5F_suggest_supersets.md`** with rows for: the constant-move audit, signature freeze, function-bound body extraction (old + new), response-shape diff verdict, SQL diff verdict, targeted pytest, full pytest.

**5F exit gate:** artifact written, PASS or acknowledged ESCALATE.

---

### 5G — Validate 3i-g: `set_execution_style`

**Target file:** [routes/workout_plan.py](../routes/workout_plan.py)
**Target function:** `set_execution_style`
**Exit artifact:** `debug/5G_set_execution_style.md`
**Token budget:** ~4.5k input

**Files referenced:**
- `routes/workout_plan.py` offset=1422 limit=120 (helpers `_validate_and_normalize_execution_params`, `_update_execution_style_db`)
- `routes/workout_plan.py` offset=1543 limit=50 (current composer body)
- `tests/test_workout_plan_routes.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _validate_and_normalize_execution_params`
   - `^def _update_execution_style_db`

2. **Signature freeze check (I-1).** Match `def set_execution_style()`.

3. **Function-bound body extraction.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | awk '/^def set_execution_style/{p=1; print; next} p && /^def /{exit} p{print}' > debug/5G_old_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def set_execution_style/{p=1; print; next} p && /^def /{exit} p{print}' routes/workout_plan.py > debug/5G_new_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def (_validate_and_normalize_execution_params|_update_execution_style_db)/{p=1; print; next} p && /^def /{if(!/^def (_validate_and_normalize_execution_params|_update_execution_style_db)/){p=0}} p{print}' routes/workout_plan.py > debug/5G_helpers_body.txt"
   ```

4. **SQL audit (I-2) — composer + helpers.** The helper `_update_execution_style_db` does the DB UPDATE; pre-cleanup the UPDATE was inline.
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5G_old_body.txt > debug/5G_old_sql.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5G_new_body.txt debug/5G_helpers_body.txt > debug/5G_new_sql.txt"
   ```
   Every SQL line in `5G_old_sql.txt` must appear in `5G_new_sql.txt`.

5. **Boundary-condition preservation audit.** `set_execution_style` enforces bounds like `time_cap_seconds` between 10 and 600, `emom_interval_seconds` between 15 and 180, `emom_rounds` between 1 and 20. These are part of the public API contract.
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -E 'time_cap_seconds|emom_interval_seconds|emom_rounds' debug/5G_old_body.txt | grep -oE '[0-9]+' | sort -u > debug/5G_old_bounds.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -hE 'time_cap_seconds|emom_interval_seconds|emom_rounds' debug/5G_new_body.txt debug/5G_helpers_body.txt | grep -oE '[0-9]+' | sort -u > debug/5G_new_bounds.txt"
   & $BASH -lc "cd '$REPO_UNIX' && diff debug/5G_old_bounds.txt debug/5G_new_bounds.txt"
   ```
   Any numeric delta → ESCALATE (I-3 generalized: validation bounds are part of the public contract). Do not use `grep -n` here; line numbers would be captured as false boundary values.

6. **Response-shape diff (I-3).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5G_old_body.txt > debug/5G_old_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5G_new_body.txt debug/5G_helpers_body.txt > debug/5G_new_response.txt"
   ```
   Error codes in old must all appear in new (composer + helpers union).

7. **Logger-level diff (I-4).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5G_old_body.txt > debug/5G_old_logger.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'logger\.(info|warning|error|exception|debug|critical)' debug/5G_new_body.txt debug/5G_helpers_body.txt > debug/5G_new_logger.txt"
   ```

8. **Targeted test rerun (I-5).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_workout_plan_routes.py -q > debug/5G_targeted.txt 2>&1"
   ```
   Expected: `31 passed, 1 skipped` (32 collected). The skipped test is the same intentional page-template availability skip documented in 5D.

9. **Full pytest gate (I-6).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5G_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline`. Regression → STOP, write `debug/5G_ANOMALY.md`, escalate.

10. **Write exit artifact `debug/5G_set_execution_style.md`.**

**5G exit gate:** artifact written, PASS or acknowledged ESCALATE.

---

### 5H — Validate 3i-h: `link_superset`

**Target file:** [routes/workout_plan.py](../routes/workout_plan.py)
**Target function:** `link_superset`
**Exit artifact:** `debug/5H_link_superset.md`
**Token budget:** ~5k input

**Files referenced:**
- `routes/workout_plan.py` offset=1175 limit=80 (helpers `_validate_superset_link_request`, `_apply_superset_link`)
- `routes/workout_plan.py` offset=1252 limit=70 (current composer body)
- `tests/test_superset.py` — Grep count only

**Steps:**

1. **Helper presence audit.** Grep each of:
   - `^def _validate_superset_link_request`
   - `^def _apply_superset_link`

2. **Signature freeze check (I-1).** Match `def link_superset()`.

3. **Function-bound body extraction.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/workout_plan.py | awk '/^def link_superset/{p=1; print; next} p && /^def /{exit} p{print}' > debug/5H_old_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def link_superset/{p=1; print; next} p && /^def /{exit} p{print}' routes/workout_plan.py > debug/5H_new_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def (_validate_superset_link_request|_apply_superset_link)/{p=1; print; next} p && /^def /{if(!/^def (_validate_superset_link_request|_apply_superset_link)/){p=0}} p{print}' routes/workout_plan.py > debug/5H_helpers_body.txt"
   ```

4. **SQL audit (I-2).** The `UPDATE user_selection SET superset_group = ?` should appear in `_apply_superset_link` (moved from the main function).
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5H_old_body.txt > debug/5H_old_sql.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b' debug/5H_new_body.txt debug/5H_helpers_body.txt > debug/5H_new_sql.txt"
   ```
   Every SQL statement in old must have a corresponding statement in new+helpers.

5. **Validation-rule preservation audit — function-bound.** Every branch in the old `link_superset` (routine match, already-linked guard, exercise existence) must correspond to a branch in either the composer or one of the two helpers.
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'routine|superset_group|column_exists' debug/5H_old_body.txt > debug/5H_old_rules.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'routine|superset_group|column_exists' debug/5H_new_body.txt debug/5H_helpers_body.txt > debug/5H_new_rules.txt"
   ```
   Manual compare required. Missing branch → ESCALATE.

   > **Codex correction (2026-04-11):** the prior revision used `rg -nA30 'def link_superset'` which had a 30-line ceiling that could miss late validation branches. Function-bound awk extraction scales to the full function body (currently 68 lines, but was 131 pre-cleanup).

6. **Response-shape diff (I-3).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5H_old_body.txt > debug/5H_old_response.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'success_response\(|error_response\(' debug/5H_new_body.txt debug/5H_helpers_body.txt > debug/5H_new_response.txt"
   ```
   Error codes in old must all appear in new.

7. **Targeted test rerun (I-5).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_superset.py -q > debug/5H_targeted.txt 2>&1"
   ```
   Expected: `≥ 14 passed`.

8. **Full pytest gate (I-6).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5H_fullpytest.txt 2>&1"
   ```
   Expected: `≥ Phase 5 baseline`. Regression → STOP, write `debug/5H_ANOMALY.md`, escalate.

9. **Write exit artifact `debug/5H_link_superset.md`.**

**5H exit gate:** artifact written, PASS or acknowledged ESCALATE.

---

### 5I — Harden `tests/test_exports.py` rollback characterization (WRITE-ENABLED)

**Target file:** [tests/test_exports.py](../tests/test_exports.py)
**Exit artifacts:** `debug/5I_test_hardening.md` **AND** `debug/5I_postbaseline.md`
**Token budget:** ~8k input
**Write scope:** ONLY `tests/test_exports.py`. Any other file modification → halt, write `debug/5I_ANOMALY.md`, escalate.
**Why this sub-phase exists (Codex review v1, 2026-04-11):** Codex's review identified two structural defects in `test_recalculate_exercise_order_atomic_failure` (the rollback characterization test that 5J's ≥95% confidence claim depends on):

  1. **Skipped precondition.** The test gates the rollback assertion behind:
     ```python
     db.fetch_one("PRAGMA table_info(user_selection)").get('name') == 'exercise_order'
     ```
     `fetch_one` returns only the **first** column descriptor (which is almost never `exercise_order` — usually `id` or similar). The `.get('name') == 'exercise_order'` comparison almost always evaluates False, so the test skips the actual rollback assertion silently and "passes" without proving anything.

  2. **Pre-batch raise, not real rollback.** The current monkeypatch replaces `DatabaseHandler.executemany` and raises before the production method runs. That can prove `_recalculate_exercise_order` catches/logs an exception, but it does **not** prove `DatabaseHandler.executemany` rolls back a real SQLite failure during the batch. The rollback semantics of `executemany` — the key semantic change that `3j` introduced — are not actually exercised.

  Additionally, the parent plan `§3j` required characterization tests for **four branches** of `_recalculate_exercise_order`. Only (a) and the (defective) (d) exist. Branches (b) NULL-initialization and (c) no-op are missing. Without them, 5J cannot honestly claim ≥95% confidence.

> **Why a write sub-phase is justified.** The user's instruction (2026-04-11) was explicit: "add a small `5J0` or `5I` test-hardening sub-phase before 5J, explicitly allowed to edit only `tests/test_exports.py`. Then 5J can honestly claim ≥95% if the strengthened tests pass. Do not bury test rewrites inside a 'read-only audit' phase." 5I is exactly that — a sanctioned write-enabled sub-phase, scoped to one file, called out in §2 execution rules, that exists so 5J's confidence claim can be honest rather than conditional.

**Files referenced:**
- `tests/test_exports.py` offset=1 limit=50 (imports + fixtures)
- `tests/test_exports.py` — grep to locate `test_recalculate_exercise_order_atomic_failure`, then read the test body with a small offset window around the found line
- `routes/exports.py` offset=290 limit=45 (helper `_recalculate_exercise_order` — source of truth for what the tests must assert)
- `routes/workout_plan.py` — grep for `def column_exists` to locate the helper used by `_recalculate_exercise_order`

**Steps:**

1. **Baseline the pre-5I state.** Record the existing pass count so the delta can be verified.
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_exports.py -q > debug/5I_pre_targeted.txt 2>&1"
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5I_pre_fullpytest.txt 2>&1"
   ```
   Record `pre_targeted_count` and `pre_full_count` in `debug/5I_test_hardening.md` (both extracted from the last line of the respective `.txt` files).

2. **Locate the defective test.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'def test_recalculate_exercise_order_atomic_failure|def test_recalculate_exercise_order' tests/test_exports.py > debug/5I_test_locations.txt"
   ```
   Read `debug/5I_test_locations.txt`. Find the line number for `test_recalculate_exercise_order_atomic_failure`. Use `Read` tool with `offset=(start - 3)` and `limit=60` to pull the defective test body into context, plus any helper/fixture it uses.

3. **Locate `column_exists`.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '^def column_exists' routes/workout_plan.py > debug/5I_column_exists_loc.txt"
   ```
   Read `routes/workout_plan.py` around the found line to confirm its current signature. Do not guess — use the actual parameter order when rewriting the test precondition.

4. **Fix defect #1 — column-existence precondition.** Rewrite the broken `fetch_one("PRAGMA table_info(...)")` check to use `column_exists` (or an iteration over `fetch_all("PRAGMA table_info(user_selection)")` asserting any row's `name` column equals `'exercise_order'`). The replacement must actually reach the rollback assertion.

   Pattern (adjust for the actual `column_exists` signature discovered in step 3):
   ```python
   from routes.workout_plan import column_exists
   ...
   with DatabaseHandler() as db:
       assert column_exists(db, "user_selection", "exercise_order"), \
           "exercise_order column missing — schema regression"
   ```

5. **Fix defect #2 — exercise the real rollback path.** Rewrite the failure simulation so the production `DatabaseHandler.executemany` method actually runs and SQLite raises during the batch. Do **not** monkeypatch `DatabaseHandler.executemany` to raise directly — that bypasses the method whose rollback behavior 5J is trying to prove.

   **Implementation strategy:** create a temporary SQLite trigger in the test database before calling the endpoint:

   ```sql
   CREATE TRIGGER fail_exercise_order_mid_batch
   BEFORE UPDATE OF exercise_order ON user_selection
   WHEN NEW.exercise_order = 2
   BEGIN
       SELECT RAISE(ABORT, 'simulated mid-batch failure');
   END;
   ```

   With at least three rows needing recalculation, the first update can occur, the second update aborts inside SQLite, `DatabaseHandler.executemany` catches a real `sqlite3.Error`, rolls back the transaction, and re-raises to `_recalculate_exercise_order`. `_recalculate_exercise_order` currently catches that exception, logs an error, sets `updated_count = 0`, and allows `GET /export_to_excel` to continue. The test must reflect that production behavior; do not expect an exception to propagate or an `error_response` unless production code is intentionally changed in a separate plan.

   After calling `GET /export_to_excel`, assert that:

   - (a) the endpoint response matches current production behavior (normally a successful Excel response despite the internal recalc failure)
   - (b) the transaction **rolled back** — `user_selection.exercise_order` values are unchanged from their pre-call state (verify by comparing a pre-snapshot to a post-snapshot via `fetch_all`)
   - (c) the logger recorded an ERROR-level event from the batch update path (use pytest's `caplog`, or an equivalent log-capture fixture already used in the repo)

   Drop the trigger in test cleanup if the test continues after the assertion, or rely on the clean per-test database fixture if that fixture recreates the database between tests.

6. **Add characterization test (b) — NULL-initialization path.** Name: `test_recalculate_exercise_order_null_initialization`. Setup: insert rows into `user_selection` with `exercise_order = NULL`. Call `GET /export_to_excel`, the route that triggers `_recalculate_exercise_order`. Assert: all NULL values are replaced with sequential integers starting from 1 (or whatever the helper's actual initialization rule is — verify in step 2's helper body read).

7. **Add characterization test (c) — no-op path.** Name: `test_recalculate_exercise_order_no_op`. Setup: insert rows with already-distinct, already-sequential `exercise_order` values (e.g., `[1, 2, 3]`). Call `GET /export_to_excel`. Assert: values are unchanged.

8. **Run the targeted test file** and verify the delta:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_exports.py -q > debug/5I_post_targeted.txt 2>&1"
   ```
   Expected: `pre_targeted_count + 2 passed` (one existing test hardened in place → no new test, plus two new tests added → +2). Record `post_targeted_count` in the exit artifact.

9. **Run full pytest** to confirm no regressions elsewhere:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5I_post_fullpytest.txt 2>&1"
   ```
   Expected: `pre_full_count + 2 passed` (same delta). Record `post_full_count`. Any regression outside `tests/test_exports.py` → halt immediately, do **not** revert the edits yourself (the user decides), write `debug/5I_ANOMALY.md` with the failing test names, and hand back.

10. **Verify write scope is honored.**
    ```powershell
    & $BASH -lc "cd '$REPO_UNIX' && git status --short > debug/5I_git_status.txt"
    ```
    Expected: the exact P3 baseline set of modified/untracked files, **plus exactly one additional line**: `M tests/test_exports.py`. Any other new modified file → halt, write `debug/5I_ANOMALY.md`, escalate. Do not hard-code or reinterpret the dirty-state list here; compare against the `git status --short` snapshot recorded in `debug/P3_phase5_git.md`.

11. **Write `debug/5I_postbaseline.md`:**
    ```markdown
    # 5I Post-Baseline

    **Date:** <YYYY-MM-DD>
    **Prior baseline (P2):** <e.g., 936 passed, 1 skipped>
    **New baseline (post-5I):** <e.g., 938 passed, 1 skipped>
    **Delta:** +2 passed (2 new characterization tests; test_recalculate_exercise_order_atomic_failure hardened in place, no net change in its count)
    **Subsequent sub-phases (5J, 5E) gate on:** <new baseline>
    **Sub-phases 5F, 5G, 5H:** already ran before 5I — they used the P2 baseline. Their gates are unaffected.
    **Expected dirty working-tree file:** `tests/test_exports.py` (sanctioned write; do not revert until user approves or 5Z completes)
    ```

12. **Write `debug/5I_test_hardening.md`:**
    ```markdown
    # 5I — tests/test_exports.py Hardening

    **Verdict:** PASS | ESCALATE | FAIL
    **Date:** <YYYY-MM-DD>

    | Check | Result |
    |---|---|
    | Pre-5I targeted count | <pre_targeted_count> |
    | Pre-5I full-suite count | <pre_full_count> |
    | Defect #1 fixed (column-existence precondition uses column_exists) | <✓ / description> |
    | Defect #2 fixed (real SQLite trigger abort exercises DatabaseHandler.executemany rollback) | <✓ / description> |
    | New test: test_recalculate_exercise_order_null_initialization | <✓> |
    | New test: test_recalculate_exercise_order_no_op | <✓> |
    | Post-5I targeted count | <post_targeted_count> (expected: pre + 2) |
    | Post-5I full-suite count | <post_full_count> (expected: pre + 2) |
    | Write scope honored (only tests/test_exports.py modified beyond P3 baseline) | <✓> |
    | debug/5I_postbaseline.md written | <✓> |

    **Next action:** 5J
    ```

13. **Do NOT commit.** The test edits remain uncommitted in the working tree. Subsequent sub-phases (5J, 5E) inherit the dirty state. The user reviews the diff between 5I and 5O, and decides whether to commit the test changes separately from the plan-retirement commit (recommended) or alongside it.

**5I exit gate:** both `debug/5I_test_hardening.md` and `debug/5I_postbaseline.md` exist with PASS. `git status --short` shows P3-baseline-plus-`tests/test_exports.py`. Full pytest passes at the new baseline.

---

### 5J — Validate 3j: `_recalculate_exercise_order` batch update

**Target file:** [routes/exports.py](../routes/exports.py)
**Target function:** `_recalculate_exercise_order` (the new helper that also carries the 3j semantic change)
**Exit artifact:** `debug/5J_recalculate_exercise_order.md`
**Token budget:** ~5k input
**Prerequisites:** **5I must have completed with PASS** (`debug/5I_test_hardening.md` exists with PASS verdict). Without 5I, 5J immediately ESCALATES per the decision rule in step 5.
**Why this sub-phase exists:** the 3j executemany optimization shipped in `12c90ac` bundled with 3i. It introduces an **intentional semantic change** (per-row best-effort → atomic batch with rollback on failure). The parent plan rated 3j at 55–60% confidence because the pre-cleanup state had no dedicated success/rollback tests. 5I hardened `tests/test_exports.py` to cover branches (a), (b), (c), and (d). 5J validates that the code matches the intent and that 5I's tests actually run green.

**Files referenced:**
- `routes/exports.py` offset=290 limit=45 (helper `_recalculate_exercise_order`)
- `debug/5I_test_hardening.md` (prerequisite gate) — read first
- `debug/5I_postbaseline.md` (new pytest baseline for gate I-6) — read second

**Steps:**

1. **5I prerequisite gate.** Read `debug/5I_test_hardening.md`. Verdict must be `PASS`. If the file is missing OR verdict is not PASS → STOP and write `debug/5J_ANOMALY.md` recording "5I prerequisite not met, 5J cannot honestly claim ≥95% confidence; user must decide whether to run 5I first or accept 5J at 55–60%." Do not proceed past this step if 5I is not PASS.

2. **Helper presence audit.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE '^def _recalculate_exercise_order' routes/exports.py > debug/5J_helper_present.txt"
   ```
   Expected: ≥1 hit. Zero → ESCALATE (the helper is missing from the committed tree).

3. **Semantic-change confirmation.**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git show 47736b9:routes/exports.py | grep -nE 'UPDATE user_selection SET exercise_order' > debug/5J_old_update.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'UPDATE user_selection SET exercise_order|executemany' routes/exports.py > debug/5J_new_update.txt"
   ```
   Expected: old file shows per-row UPDATE inside a loop (a `-` line per row or a single line inside a Python `for` loop). New file shows `db.executemany("UPDATE user_selection SET exercise_order = ? WHERE id = ?", ...)` **exactly once** inside `_recalculate_exercise_order`. Any other shape → ESCALATE with the actual diff recorded.

4. **Inline code-comment check — function-bound.** The parent plan `§3j` required "an explicit code comment documenting the semantic change: partial-success logging → all-or-nothing batch update." The comment lives inside the helper body (observed at `routes/exports.py:318` per Codex review), which is far past a `-A3` window after the `def` line. Use awk to extract the entire helper body, then grep within it:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && awk '/^def _recalculate_exercise_order/{p=1; print; next} p && /^def /{exit} p{print}' routes/exports.py > debug/5J_helper_body.txt"
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'atomic|batch|rollback|executemany|semantic|partial|all-or-nothing' debug/5J_helper_body.txt > debug/5J_comment.txt"
   ```
   Expected: ≥1 hit on a comment line (starts with `#`) or an adjacent docstring line that explains the semantic change. Zero hits → ESCALATE (the documentation-of-semantic-change requirement is a public-contract item per the parent plan; missing it is not a hard bug but is a confidence blocker).

   > **Codex correction (2026-04-11):** the prior revision used `rg -nA3 'def _recalculate_exercise_order'`, which only captured 3 lines past the `def` and missed the actual comment around `routes/exports.py:318`. The awk function-bound extraction captures the entire helper body regardless of length (currently ~44 lines), resolving the false-escalate bug.

5. **Characterization test coverage audit (post-5I).** Required branches for `_recalculate_exercise_order`:
   - (a) success path with multiple rows needing recalculation
   - (b) NULL `exercise_order` initialization path
   - (c) already-distinct `exercise_order` no-op path
   - (d) failure / rollback semantics (atomic batch failing mid-batch)

   5I is responsible for creating branches (b), (c), and the hardened (d). 5J verifies by name:
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && grep -nE 'def test_recalculate_exercise_order|def test_recalculate_exercise_order_null_initialization|def test_recalculate_exercise_order_no_op|def test_recalculate_exercise_order_atomic_failure' tests/test_exports.py > debug/5J_coverage.txt"
   ```
   **Decision rule:**
   - **≥4 distinct hits** covering (a), (b), (c), (d) as separate test functions → **PASS**. The parent plan's 55–60% rating is retroactively upgraded to ≥95% because the coverage gap is closed.
   - **<4 hits** → **ESCALATE**. Record the specific missing branch(es) in the exit artifact. **Do not re-run 5I from within 5J** — each sub-phase stays in its lane. If 5I claims PASS but the hits are <4, that is a 5I defect, not a 5J defect; the user must re-run 5I.
   - **0 hits** → **ESCALATE + hard stop**. 5I's output was lost, reverted, or never landed. Halt and return control to the user.

6. **Targeted test rerun (I-5).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/test_exports.py -q > debug/5J_targeted.txt 2>&1"
   ```
   Expected: `≥` the `post_targeted_count` from `debug/5I_postbaseline.md` (typically 39 = 37 + 2).

7. **Full pytest gate (I-6).**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && .venv/Scripts/python.exe -m pytest tests/ -q > debug/5J_fullpytest.txt 2>&1"
   ```
   Expected: `≥` the new Phase 5 baseline recorded in `debug/5I_postbaseline.md`. Regression → STOP, write `debug/5J_ANOMALY.md`, escalate.

8. **Write exit artifact `debug/5J_recalculate_exercise_order.md`** with the coverage table explicitly showing (a)/(b)/(c)/(d) presence, the semantic-change confirmation output, the comment check result, and both pytest gate results.

**5J exit gate:** artifact written with PASS (all four branches covered) OR user-acknowledged ESCALATE with specific missing branch(es). **5J now has a clean path to ≥95% confidence** — the escalation risk is concentrated in 5I; once 5I PASSes, 5J's mechanical checks are a verification layer with a defined correctness bar.

---

### 5O — Retire §3i and §3j in `code_cleanup_plan.md`

**Target file:** [docs/code_cleanup_plan.md](code_cleanup_plan.md)
**Exit artifact:** `debug/5O_planmd.patch`
**Token budget:** ~6k input
**Depends on:** All of `5A`, `5B`, `5C`, `5D`, `5F`, `5G`, `5H`, `5I`, `5J`, `5E` written with PASS or user-acknowledged ESCALATE verdicts (note the non-alphabetical execution order — see §10).

> **Hard prerequisite.** Do not run 5O if any of `debug/5A..5J_*.md` is missing or reports an unacknowledged ESCALATE. The plan-retirement edit must reflect truth — if 5J escalates due to missing characterization tests, 5O must NOT mark 3j as "verified 95%"; it must record the specific escalation and leave 3j flagged for follow-on work.

**Files referenced:**
- `docs/code_cleanup_plan.md` offset=133 limit=20 (Stage Tracker rows for 3i and 3j)
- `docs/code_cleanup_plan.md` offset=205 limit=15 (Post-Phase-4 Handoff §18.2 open-items table rows for 3i and 3j)
- `docs/code_cleanup_plan.md` offset=250 limit=130 (Confidence Recovery Plan §on 3i and 3j)
- `docs/code_cleanup_plan.md` offset=850 limit=100 (§3i body, including `3i-a`..`3i-h` sub-sections)
- `docs/code_cleanup_plan.md` offset=920 limit=25 (§3j body)
- `docs/code_cleanup_plan.md` offset=1700 limit=30 (Execution Checklist [Phase 3i] and [Phase 3j] sections)

**Steps:**

1. **Read the six file regions above.** Do not read the whole file — it is >1700 lines and would blow the token budget.

2. **Edit the Stage Tracker row for `3i`** (around L147). New content:
   ```
   | `3i` Large function decomposition | <verdict>% | <status> | Retroactively validated by `docs/phase5_3i_plan.md` sub-phases 5A–5H. See `debug/5A_*.md`..`debug/5H_*.md` for per-function audits. |
   ```
   Where `<verdict>` and `<status>` come from the aggregate of 5A–5H exit artifacts. If all PASS → `95%+` and `Completed`. If any ESCALATE → keep the old `50-60%` and append "— ESCALATED: see `debug/<letter>_*.md`".

3. **Edit the Stage Tracker row for `3j`** (around L146). New content:
   ```
   | `3j` Export write-path optimization | <verdict>% | <status> | Retroactively validated by `docs/phase5_3i_plan.md` sub-phase 5J. See `debug/5J_recalculate_exercise_order.md`. |
   ```
   Same verdict-derivation rule from `debug/5J_recalculate_exercise_order.md`.

4. **Edit the §Post-Phase-4 Handoff §18.2 open-items table** (around L209–L212). Replace the 3i and 3j rows with pointers to this plan's exit artifacts. Preserve the historical language ("were deferred at 50–60% / 55–60% until `phase5_3i_plan.md`") — do not erase history.

5. **Edit §Confidence Recovery Plan §on 3i and 3j** (around L338–L376). Replace the unchecked `[ ]` sub-phase list under "Recovery Plan for 3i" with a one-line pointer: "Superseded by `docs/phase5_3i_plan.md` — see that file §5 for the executed sub-phases." Same for "Recovery Plan for 3j".

6. **Edit §3i body** (around L855–L920). Replace the whole section with a retirement block:
   ```markdown
   ### 3i. Bloated Function Decomposition (Retired — see phase5_3i_plan.md)

   > **Retired 2026-04-11 by `phase5_3i_plan.md` §5A–§5H.** The decompositions
   > listed below shipped inside commit `12c90ac` bundled with phases `3a-3h`;
   > the confidence-recovery audit required by the parent plan's
   > §Confidence Recovery Plan ran in phase5_3i_plan.md and produced the exit
   > artifacts `debug/5A_*.md` through `debug/5H_*.md`.
   >
   > The original §3i sub-phase bodies (`3i-a`..`3i-h`) are preserved in git
   > history at commit `<5O_commit_hash>` for reference. Do not re-execute.
   ```
   Preserve the original sub-phase bodies ONLY in git history — they are removed from the living document.

7. **Edit §3j body** (around L924–L940). Same retirement block, pointing to `phase5_3i_plan.md §5J`.

8. **Edit §Execution Checklist [Phase 3i] and [Phase 3j]** (around L1701–L1725). Replace both sections with single-line redirects: "Retired — see `docs/phase5_3i_plan.md`." Do not delete the section headings entirely (other parts of the plan reference them by anchor).

9. **Write the patch to `debug/5O_planmd.patch`:**
   ```powershell
   & $BASH -lc "cd '$REPO_UNIX' && git diff docs/code_cleanup_plan.md > debug/5O_planmd.patch"
   ```

10. **Do NOT commit** the edit in this sub-phase. Committing is an explicit separate action the user must approve. 5O is a "propose the diff" action, not a "land the diff" action.

11. **Write exit artifact `debug/5O_retirement_summary.md`** with:
    - Verdict: PROPOSED (not COMMITTED)
    - Patch file: `debug/5O_planmd.patch`
    - Lines changed:
      ```powershell
      & $BASH -lc "cd '$REPO_UNIX' && wc -l < debug/5O_planmd.patch"
      ```
    - Per-section summary: what changed in each of the 6 edited regions
    - User-action-required: "Review the patch, then run `git add docs/code_cleanup_plan.md && git commit -m 'docs(5O): retire §3i/§3j in favor of phase5_3i_plan.md'` to land it. If 5I's `tests/test_exports.py` changes have not yet been committed, decide whether to bundle them into the 5O commit or land them as a separate commit first (recommended: separate commit with message `test(5I): harden _recalculate_exercise_order characterization per Codex review`)."

**5O exit gate:** `debug/5O_planmd.patch` exists, `debug/5O_retirement_summary.md` exists, `git status docs/code_cleanup_plan.md` shows the file as modified but NOT committed. User approval required for the commit.

---

## 6. Close-Out (5Z)

### 5Z — Phase 5 close
**Exit artifact:** `debug/5Z_close.md`

After all sub-phases (5A..5O) complete and the user approves the 5O commit:

- [ ] Aggregate all `debug/5<letter>_*.md` verdicts into a summary table in `debug/5Z_close.md`
- [ ] Record final pytest count from the last sub-phase's full-pytest gate (must still be ≥ Phase 5 baseline)
- [ ] Delete the rollback tag: `git tag -d phase5-rollback-point`
- [ ] Keep all `debug/5*` artifacts for audit trail (do not delete)
- [ ] Report Phase 5 closed to the user with the summary table

**5Z exit gate:** `debug/5Z_close.md` exists, rollback tag deleted, summary table shows all sub-phases resolved (PASS or acknowledged ESCALATE with a follow-on ticket).

---

## 7. Confidence Statement

| Component | Confidence | Justification |
|---|---|---|
| P0 shell bootstrap | **100%** | Read-only detection + two PowerShell variable assignments. Halt-on-missing. |
| P1–P4 prerequisites | **100%** | Read-only or tag-only; P4 is idempotent. |
| 5A `generate_progression_suggestions` | **≥97%** | Pure-Python function with 68 targeted tests already green. No SQL, no route surface. Strongest baseline of any sub-phase. |
| 5B `calculate_session_summary` | **≥96%** | 30 targeted tests, utility function, SQL moved to helpers but identical tokens. |
| 5C `create_excel_workbook` | **≥95%** | 37 targeted tests covering export flows. Function is xlsxwriter-only, no DB, complex but well-tested. Small risk: logging-level delta audit depends on manual diff review. |
| 5D `replace_exercise` | **≥95%** | 32 route tests + 2 Playwright specs (`exercise-interactions`, `replace-exercise-errors`). Route-surface risk mitigated by the success-response key audit (function-bound awk extraction) and optional E2E step. |
| 5F `suggest_supersets` | **≥96%** | 46 combined targeted tests. Cross-file constant move (to `utils/constants.py`) is a mechanical audit with a byte-diff gate. Response-shape audit uses function-bound extraction (post-Codex v1). |
| 5G `set_execution_style` | **≥95%** | 32 route tests. Boundary-condition audit explicitly guards the numeric validation bounds via function-bound extraction of the composer + helpers union — the highest-risk public contract for this function. |
| 5H `link_superset` | **≥95%** | 14 targeted superset tests. Validation-rule audit uses function-bound extraction (post-Codex v1) so the full composer body is checked, not a fixed window. |
| 5I test hardening (`tests/test_exports.py`) | **≥98%** | Write-enabled, scoped exclusively to one test file. Three surgical edits: (1) swap PRAGMA probe for the actual `routes.workout_plan.column_exists` helper, (2) replace the pre-method monkeypatch with a real SQLite trigger abort that exercises `DatabaseHandler.executemany` rollback, (3) add two new tests (`_null_initialization`, `_no_op`). Full pytest gate at +2 count. Write-scope enforced via `git status --short` check. |
| 5J `_recalculate_exercise_order` (3j) | **≥95% after 5I** | Confidence is now **conditional on 5I landing first**. With 5I's strengthened tests (success, NULL-init, no-op, rollback — all 4 branches exercising the real `executemany` path), 5J's coverage audit passes cleanly and 5J reaches `≥95%`. If 5I is skipped or its edits are reverted, 5J falls back to **variable** and is expected to ESCALATE. Function-bound awk extraction of the composer body (not `-A3`) ensures the "no-op guard" comment at L318 is seen. |
| 5E `export_to_excel` | **≥95% after 5J + 5I** | Shares `tests/test_exports.py` with 5C and 5J. **Runs AFTER 5J** (not alphabetical). Confidence depends on 5C, 5I, and 5J all passing — explicit prerequisite gate in step 1 of the sub-phase. |
| 5O plan retirement edit | **≥99%** | Doc-only edit; no source code touched; commit is user-approved not auto-landed. The 5I test commit may be folded into 5O's commit or kept separate per user preference. |
| 5Z close | **100%** | Aggregation + tag cleanup. |
| **Overall Phase 5 aggregate** | **≥95%** conditional on 5I + 5J both passing | With the Codex v1 revision, the aggregate's critical path runs through 5I → 5J. If 5I lands cleanly and 5J's coverage audit reports 4 named branches present, the aggregate is `≥95%`. If 5I cannot land (drift, test failure), the plan degrades to "95% for 5A–5H + 5O, unresolved on 5J." The user must explicitly decide whether that state closes Phase 5 or spawns a follow-on plan. |

**Risk registry — items that could lower confidence if they surface:**

1. **A helper got renamed after 12c90ac.** Only `ec748ba` has touched any target file since, and it only added new functions (`get_exercise_plan_defaults`, `generate_plan_based_progression_suggestions`) — no renames. Mitigation: §3 inventory uses names as the contract, not line numbers.
2. **The pytest count regressed between CLAUDE.md's last update (936/1) and the P2 recapture.** Mitigation: P2 is a fresh pytest run, not a cached value. If it reports <936, the plan halts and escalates.
3. **Sonnet misreads line ranges and grabs too much context.** Mitigation: §2 Execution Rules cap at 15k input tokens per action. Each action's "Files referenced" block gives explicit `offset=X limit=Y` values.
4. **The SQL/response-shape diff has false positives from comment reformatting.** Mitigation: every diff step writes the raw output to a `debug/*_diff.txt` file; manual review of unmatched `-`/`+` lines is part of the sub-phase's escalation decision, not an automated failure.
5. **5J reports ESCALATE even after 5I hardening.** The Codex v1 revision added 5I specifically to close this gap — the 4 named branches (success, NULL-init, no-op, rollback) now have dedicated tests exercising the real `executemany` path. If 5J still escalates, the cause is either (a) 5I's edits did not actually land, (b) the helper function signature drifted between 5I and 5J, or (c) a targeted test is failing for an unrelated reason. Mitigation: 5J's step 1 reads `debug/5I_postbaseline.md` as a hard prerequisite gate, and step-by-step the sub-phase diffs the helper signature against `47736b9`.
6. **5E is run before 5J.** Mitigation: 5E has an explicit prerequisite gate in step 3 requiring `debug/5J_recalculate_exercise_order.md` to exist with a PASS verdict. §11 Fresh Session Kickoff Prompt's decision table enforces the non-alphabetical 5H → 5I → 5J → 5E order.
7. **5O is run before 5A–5J complete.** Mitigation: 5O has a hard prerequisite gate ("do not run if any 5<letter> artifact is missing"). §11 Fresh Session Kickoff Prompt's decision table also enforces sub-phase ordering.
8. **Uncommitted working-tree changes on non-target files drift between P3 capture and the final sub-phase.** Mitigation: each sub-phase re-runs `git status --short` as step 0 (implied by §2 "If any command output is unexpected, STOP") and compares against the exact P3 snapshot. Do not rely on hard-coded stale file lists; `debug/P3_phase5_git.md` is the authority for expected pre-existing noise. After 5I completes, `tests/test_exports.py` is an **expected** addition to the dirty list and does NOT trigger an anomaly.

---

## 8. Rollback Playbook

> **Nomenclature (Codex review v1 correction).** The restore command below is **not** a "surgical per-function rollback" — it restores a **whole file** to its pre-cleanup state via `git show 47736b9:<path> > <path>`, which reverts every line in that file that changed between `47736b9` and HEAD. That includes unrelated `3a-3h` cleanup work co-located in the same file. Calling it "surgical" misrepresents the blast radius. The plan now uses **"emergency whole-file restore"** throughout.

| Scenario | Action |
|---|---|
| A sub-phase reports ESCALATE (I-1..I-4) | STOP. Record the specific invariant and the diff snippet in `debug/<letter>_*.md` (exit artifact) and `debug/<letter>_ANOMALY.md` (anomaly log). Do not proceed. User decides whether to accept the delta or write a remediation sub-plan. |
| A sub-phase reports full-pytest regression (I-6) | STOP immediately. Do not attempt any source-file change. Write `debug/<letter>_ANOMALY.md` with the pytest output. User triages: (a) stale baseline (P2 was just captured in this session, so unlikely — unless 5I ran and the new baseline in `debug/5I_postbaseline.md` is wrong), (b) flaky test (re-run once), (c) real regression (unrelated to this plan — the regression must exist in committed history and would have shown up on a prior run). |
| 5I reports the edit broke a previously-passing test outside `tests/test_exports.py` | STOP. Do NOT revert 5I's edits yourself. Write `debug/5I_ANOMALY.md` with the failing test names and hand back. User reviews and decides: accept the failure as a characterization-test byproduct, patch 5I's tests further, or revert `tests/test_exports.py` to HEAD via `git checkout -- tests/test_exports.py` (user-executed, not Sonnet-executed). |
| 5O patch cannot be applied because `docs/code_cleanup_plan.md` has drifted since P3 | STOP. Re-read P3 git-status snapshot. If the drift is the user editing the plan manually, escalate. Do not attempt a merge-conflict resolution. |
| **Emergency whole-file restore is actually requested by the user** | Run `git show 47736b9:<path> > <path>` to restore a **whole file** to its pre-cleanup state. This reverts every change to that file between `47736b9` and HEAD — including any unrelated `3a-3h` cleanup work, any `ec748ba` progression fix, and any uncommitted working-tree edits. Full pytest will almost certainly break. Only run with explicit user confirmation AND the user's acknowledgment that this is a collateral-revert action affecting multiple phases of work, not a targeted per-function restore. |
| A full Phase 5 abandon is requested | `git tag -d phase5-rollback-point` (user-executed, not Sonnet-executed). If 5I's `tests/test_exports.py` edits are still uncommitted, the user decides whether to `git checkout -- tests/test_exports.py` to discard them or keep them. No other source files were modified by Phase 5, so there is nothing else to revert. Delete `debug/*` artifacts only if the user asks (they are the audit trail). |
| Uncertain / stuck | Stop. Do not improvise. Escalate to the user with the current state and the last known-good artifact. |

> **Hard rule:** the default rollback is **do nothing to source**. Phase 5 is read-only for source code except for the two sanctioned write sub-phases (5I, 5O). If a source file outside those two appears to need modification to recover, that is evidence of a plan bug or a repo-state anomaly — escalate, do not patch.

---

## 9. Execution Notes

### 2026-04-11 (plan creation)
- Plan drafted by Opus 4.6 after user paused the first session at token-allowance limit.
- Key discovery: 3i-a..3i-h AND 3j all shipped inside `12c90ac` despite the commit message naming only `3a-3h`. The parent plan's self-inconsistency is the known artifact of this under-disclosed scope creep.
- All 8 target-function line ranges pinned via direct Read calls.
- All test file counts verified via Grep `def test_` count (25 + 43 + 30 + 37 + 32 + 14 = 181 targeted tests).
- `ec748ba` "fix(progression): use plan values before log history" landed between Phase 4 close and this plan. It only ADDED new functions to `utils/progression_plan.py` / `routes/progression_plan.py` — no renames, no touches to `generate_progression_suggestions`. 5A's signature freeze check against `47736b9` is unaffected.
- Phase 4 was officially closed in `298b9ea` docs commit. CLAUDE.md §8 now shows baseline 936/1.
- Plan does not resume §3i / §3j execution — it validates work already done and then retires the plan sections.
- Reviewers: Gemini + Codex were explicitly named. Design choices prioritized defending the claim "≥95% confidence" with mechanical, named checks rather than narrative prose.

### 2026-04-11 (Codex review v1 revision)
- Codex reviewed v1 and identified 6 findings:
  1. **Shell incompatibility [blocker]** — v1 assumed bare `bash`/`rg`/`awk` would work on the user's Windows PowerShell session; they do not. Every command block needed a Git Bash wrapper.
  2. **Fixed `rg -A3 / -A5 / -A30` windows** missed legitimate response/semantic content in 5D, 5F, and 5J. Example: 5J's inline "no-op guard" comment sits at L318, outside a `-A3` window anchored on the function signature at L290.
  3. **5J's rollback characterization test is structurally broken** — it skips on PRAGMA failure and raises before the batch write, so it cannot exercise the mid-batch rollback path; 5J cannot honestly claim ≥95% based on that test alone.
  4. **5E/5J ordering conflict** — 5E validates `export_to_excel` which calls `_recalculate_exercise_order`, so 5E's verdict depends on 5J's verdict; v1 ran them in alphabetical order.
  5. **Anomaly logging told agents to edit the plan file** — v1 said "record the what and why in §9"; this mixes plan-edit and validation-edit permissions, which violates the read-only scope.
  6. **Rollback over-promised "surgical per-function rollback"** — the refactors landed as whole-file diffs in `12c90ac`, so the only safe rollback is a whole-file restore, not a surgical extraction.
- Revisions applied in v2:
  - Added **P0 shell-bootstrap** step that verifies Git Bash via `Test-Path 'C:\Program Files\Git\bin\bash.exe'`, defines `$BASH` + `$REPO_UNIX` session variables, and specifies the canonical command form `& $BASH -lc "cd '$REPO_UNIX' && <cmd>"`. Halts if Git Bash is missing.
  - Replaced every `rg -A<n>` window with **awk function-bound extraction** (`/^def <name>/{p=1; print; next} p && /^def /{exit} p{print}`) so every audit step operates on the full function body regardless of length.
  - Added new **5I test-hardening sub-phase**, write-enabled but scoped only to `tests/test_exports.py`, which fixes the broken rollback characterization test, adds NULL-init and no-op tests, and writes `debug/5I_postbaseline.md` (+2 count) that 5J and 5E then gate against.
  - Reordered execution so 5J runs BEFORE 5E; 5E now has an explicit prerequisite gate requiring `debug/5J_recalculate_exercise_order.md` to exist with PASS or user-acknowledged ESCALATE.
  - Moved all anomaly logging to `debug/<letter>_ANOMALY.md` files — the plan file itself stays untouched during validation.
  - Renamed rollback to **"emergency whole-file restore"** throughout §8; added explicit "user-executed, not Sonnet-executed" markers on destructive commands; made P4 tag creation idempotent (`git tag -l phase5-rollback-point` check before create).
- Execution order is now explicitly **non-alphabetical**: P0 → P1 → P2 → P3 → P4 → 5A → 5B → 5C → 5D → 5F → 5G → 5H → 5I → 5J → 5E → 5O → 5Z. Letters are stable labels, not execution order.
- Reviewer status: Codex v1 addressed in this revision (v2); Codex v2.1 cleanup applied by Codex while Opus was out of tokens. Gemini review still pending as of this write.

### 2026-04-11 (Codex v2.1 cleanup)
- Corrected 5I's `column_exists` lookup/import from `utils.database` to `routes.workout_plan`, matching the actual repo helper used by `_recalculate_exercise_order`.
- Tightened 5I's rollback characterization: a direct `DatabaseHandler.executemany` monkeypatch would bypass the production rollback path, so 5I now requires a temporary SQLite trigger that aborts during the real `executemany` call and verifies unchanged pre/post `exercise_order` snapshots.
- Made `GET /export_to_excel` the explicit route for 5I's NULL-initialization and no-op tests; removed the stale invented-route wording.
- Removed the hard-coded dirty-state parenthetical from 5I step 10; subsequent agents compare against the exact P3 snapshot plus `M tests/test_exports.py`.
- Fixed the stale nonexistent 5J verdict-artifact note to the real artifact, `debug/5J_recalculate_exercise_order.md`.

### 2026-04-11 (Codex P3 anomaly calibration)
- P3 initially escalated because target-file history included `73bc1eb` in addition to `12c90ac` and `ec748ba`.
- User confirmed `73bc1eb` is intentional progression-plan follow-up work, not suspicious drift. The commit changes no-history Progression prompt copy in `utils/progression_plan.py` and updates its route test expectation.
- P3 expected-history text now accepts `73bc1eb`.
- 5A's SQL/response check now inspects only the `generate_progression_suggestions` target function body; the prior whole-file command would falsely match the accepted `ec748ba` plan-default SQL helper above the target function.

### 2026-04-12 (Codex 5D targeted-count calibration)
- 5D initially escalated because `tests/test_workout_plan_routes.py` reported `31 passed, 1 skipped` while the plan expected `≥ 32 passed`.
- User approved treating this as stale plan wording. The file has 32 collected tests; one page-template availability test is intentionally skipped in the unit-test environment.
- 5D's targeted-test expectation now matches the live repo baseline: `31 passed, 1 skipped`.

### 2026-04-12 (Codex 5F command calibration)
- 5F's original constant-block extraction assumed `ANTAGONIST_PAIRS` was top-level in `47736b9`, but it was indented inside `suggest_supersets`; the current version is top-level in `utils/constants.py`.
- 5F now extracts the dict with optional leading whitespace and strips indentation before diffing, so it validates value identity rather than indentation after the move.
- 5F's signature check now omits `grep -n` because the line number changed while the route handler signature stayed `def suggest_supersets():`.
- 5F's targeted-test expectation now accounts for the same intentional `tests/test_workout_plan_routes.py` skip documented in 5D: `45 passed, 1 skipped` across `tests/test_superset.py` + `tests/test_workout_plan_routes.py`.

### 2026-04-12 (Codex 5G command calibration)
- 5G's boundary-preservation command now avoids `grep -n`, because line numbers would be captured by the subsequent numeric extraction and falsely appear as changed validation bounds.
- 5G's targeted-test expectation now accounts for the same intentional `tests/test_workout_plan_routes.py` skip documented in 5D: `31 passed, 1 skipped`.

### 2026-04-12 (Codex live progress checkpoint)
- Live Progress Tracker added near the top of this plan for Gemini/Claude/Codex handoff resilience.
- Completed with PASS artifacts: P0, P1, P2, P3, P4, 5A, 5B, 5C, 5D, 5F, 5G, 5H, 5I, 5J, 5E. 5O is PROPOSED, not committed.
- Phase 5 is closed; `debug/5Z_close.md` records the close-out.
- Active Phase 5 baseline is now `938 passed, 1 skipped` per `debug/5I_postbaseline.md`.

### 2026-04-12 (Codex 5I test hardening)
- 5I completed with PASS artifacts: `debug/5I_test_hardening.md` and `debug/5I_postbaseline.md`.
- `tests/test_exports.py` now contains the hardened rollback characterization plus NULL-initialization and no-op tests for `_recalculate_exercise_order`.
- Targeted count rolled from `37 passed` to `39 passed`; full-suite baseline rolled from `936 passed, 1 skipped` to `938 passed, 1 skipped`.
- After this 5I checkpoint, the next sub-phase was `5J`, with prior artifact `debug/5I_test_hardening.md`.
- From 5J onward, `tests/test_exports.py` is expected dirty state and `debug/5I_postbaseline.md` is the active pytest baseline.

### 2026-04-12 (Codex 5J recalculation validation)
- 5J completed with PASS artifact: `debug/5J_recalculate_exercise_order.md`.
- `_recalculate_exercise_order` semantic-change validation passed: old per-row update loop became a documented atomic `executemany` batch update.
- All four characterization branches are present: success, NULL initialization, no-op preservation, and rollback semantics.
- Targeted pytest remained `39 passed`; full pytest remained `938 passed, 1 skipped`.
- After this 5J checkpoint, the next sub-phase was `5E`, with prior artifact `debug/5J_recalculate_exercise_order.md`.

### 2026-04-12 (Codex 5E export composer validation)
- 5E completed with PASS artifact: `debug/5E_export_to_excel.md`.
- 5E consumed 5J's PASS verdict and validated `export_to_excel` after the `_recalculate_exercise_order` batch-update semantics were covered.
- SQL/response and logger audits showed expected extraction from the composer into helpers, with no response-shape change or logger-level downgrade.
- Targeted pytest remained `39 passed`; full pytest remained `938 passed, 1 skipped`.
- After this 5E checkpoint, the next sub-phase was `5O`, with prior artifact `debug/5E_export_to_excel.md`.

### 2026-04-13 (Codex 5O plan retirement proposal)
- 5O completed and was committed at `c0da18e`, with artifacts: `debug/5O_planmd.patch` and `debug/5O_retirement_summary.md`.
- `docs/code_cleanup_plan.md` now has a landed retirement patch for §3i and §3j, replacing executable checklist bodies with redirects to `docs/phase5_3i_plan.md` and the 5A-5J debug artifacts.
- Patch size is `363` lines; `git diff --check -- docs/code_cleanup_plan.md` passed.
- 5Z later closed Phase 5 in `debug/5Z_close.md`.

---

## 10. Action Count Summary

**Execution order is non-alphabetical.** Sub-phase letters are stable labels; the sequence below is authoritative:
P0 → P1 → P2 → P3 → P4 → 5A → 5B → 5C → 5D → 5F → 5G → 5H → 5I → 5J → 5E → 5O → 5Z

| # | Sub-phase | Actions | Est. input tokens | Write-enabled? | User-gated? |
|---|---|---|---|---|---|
| 1 | P0 shell bootstrap | 1 | ~2k | no | no |
| 2 | P1 env sanity | 1 | ~3k | no | no |
| 3 | P2 baseline capture | 1 | ~4k | no | no |
| 4 | P3 baseline artifact | 1 | ~3k | no | no |
| 5 | P4 rollback tag (idempotent) | 1 | ~3k | **yes** (`git tag`) | no |
| 6 | 5A `generate_progression_suggestions` | 1 | ~4.5k | no | no |
| 7 | 5B `calculate_session_summary` | 1 | ~5k | no | no |
| 8 | 5C `create_excel_workbook` | 1 | ~5.5k | no | no |
| 9 | 5D `replace_exercise` | 1 | ~5k | no | no (optional E2E) |
| 10 | 5F `suggest_supersets` | 1 | ~5k | no | no |
| 11 | 5G `set_execution_style` | 1 | ~4.5k | no | no |
| 12 | 5H `link_superset` | 1 | ~5k | no | no |
| 13 | **5I test-hardening** (`tests/test_exports.py`) | 1 | ~6k | **yes** (tests only) | no |
| 14 | 5J `_recalculate_exercise_order` | 1 | ~5k | no | no |
| 15 | 5E `export_to_excel` | 1 | ~5k | no | no |
| 16 | 5O plan retirement edit | 1 | ~6k | **yes** (`docs/code_cleanup_plan.md`) | **user approval for commit** |
| 17 | 5Z close | 1 | ~4k | no | no |
| — | **Total** | **17 actions** | **~76k input tokens across the whole plan** | — | — |

**Per-action average:** ~4.5k input tokens. Well within Sonnet 4.6's 200k context window and well below the ≤15k-per-action cap.

**Sanctioned write sub-phases:** P4 (git tag only), 5I (`tests/test_exports.py` only), 5O (`docs/code_cleanup_plan.md` only). Every other sub-phase is read-only for source code. See §2 Execution Rules for the enforcement contract.

---

## 11. Fresh Session Kickoff Prompt (for Sonnet 4.6 handoffs)

**Purpose:** canonical prompt to paste into a fresh Sonnet 4.6 session to execute the next sub-phase. Opus does not re-derive the handoff context each time.

**Usage:** copy the block below, fill in the two `{{placeholders}}`, paste into a new Sonnet session as the first user message.

```
You are continuing spring-cleanup Phase 5 on the Hypertrophy-Toolbox-v3 repo.
Branch: spring-cleanup. Working directory: the repo root.
Platform: Windows 11, PowerShell host. Shell wrapper required (see below).

ACTIVE SUB-PHASE: {{sub_phase_id}}   (e.g., P0, 5A, ..., 5I, 5J, 5E, 5O, 5Z)
PRIOR EXIT ARTIFACT: {{last_artifact_path}}   (e.g., debug/P2_phase5_baseline.md)

SHELL CONVENTION (set once per session, before any sub-phase step):
  $BASH      = 'C:\Program Files\Git\bin\bash.exe'
  $REPO_UNIX = '/c/Users/aviha/Downloads/Hypertrophy-Toolbox-v3-main'
Every command block in the plan that uses rg / awk / grep / git must be run as:
  & $BASH -lc "cd '$REPO_UNIX' && <command>"
If `Test-Path $BASH` is false, STOP and report to the user — do not translate
ad hoc. P0 performs this verification on the first run.

Do the following in order. Do not improvise, do not combine sub-phases, do not
proceed past a sub-phase exit gate without confirming it.

1. Read docs/phase5_3i_plan.md — ONLY the section for the active sub-phase
   above. Do not read the whole plan. Use the section headings as anchors
   (e.g., "### 5A — Validate 3i-a").
2. Read the prior exit artifact named above.
3. Read ONLY the source files explicitly named in the sub-phase's
   "Files referenced" block. Use the exact offset/limit values given.
4. Execute every numbered step in the sub-phase IN ORDER.
5. After each step that runs pytest, the result must be ≥ the active baseline:
   - For 5A–5H: the P2 baseline recorded in debug/P2_phase5_baseline.md.
   - For 5J and 5E: the post-5I baseline recorded in debug/5I_postbaseline.md
     (which is P2 baseline + 2 from the new characterization tests).
   Any regression → STOP.
6. Write the exit artifact EXACTLY as named in the sub-phase. The artifact is
   the contract — no verbal "done" in chat replaces it.
7. Stop at the sub-phase's exit gate. Do not start the next sub-phase.

HARD RULES (override anything else the plan suggests):
- Phase 5 is READ-ONLY for source code EXCEPT for the two sanctioned write
  sub-phases:
    * 5I may edit ONLY tests/test_exports.py (test-hardening before 5J).
    * 5O may edit ONLY docs/code_cleanup_plan.md (plan retirement).
  Every other sub-phase is strictly read-only. Never modify any other .py,
  .js, .html, .css, or .scss file.
- After 5I completes, `git status` will show tests/test_exports.py as dirty.
  That is expected. Do NOT revert it between sub-phases. It is part of the
  5I → 5J → 5E → 5O commit thread.
- NEVER run `git reset`, `git revert`, `git commit`, `git push`, `git add`,
  or `git rm`. The only allowed git operations are read-only: `git show`,
  `git log`, `git diff`, `git status`, `git tag -l`. The two exceptions are:
  (a) P4's `git tag phase5-rollback-point` (idempotent, runs once), and
  (b) the user's own commit step after 5I and 5O write their artifacts.
- NEVER delete any existing debug/* artifact. They are the audit trail.
- If any command output is unexpected (extra files, pytest count < active
  baseline, missing helper, non-empty signature diff), STOP and report to
  the user. Record the anomaly in debug/<letter>_ANOMALY.md — a NEW file,
  one per sub-phase anomaly. Do NOT edit docs/phase5_3i_plan.md §9 from
  within a sub-phase. Do not try to "fix forward".
- Budget: ≤15k input tokens per sub-phase. If reading a file would exceed
  that, read only the line ranges the sub-phase names with offset/limit.
- Any uncommitted working-tree noise recorded in `debug/P3_phase5_git.md` is
  OUT OF SCOPE. Do not touch those files. After 5I, `tests/test_exports.py`
  is the only sanctioned addition to that dirty-state list.

REPORTING: when the sub-phase's exit gate is reached, reply with exactly:
  - The sub-phase ID
  - The exit artifact path
  - One-line verdict: PASS | ESCALATE <invariant> | FAIL
  - The pytest result from the final re-run
  - Any anomaly artifact paths (debug/<letter>_ANOMALY.md) if written
Nothing else. No recap of what you read, no next-step suggestions.
```

**Filling the placeholders — decision table (non-alphabetical execution order):**

| If the last completed artifact is… | `{{sub_phase_id}}` should be… | `{{last_artifact_path}}` should be… |
|---|---|---|
| (none — starting fresh) | `P0` | (none) |
| `debug/P0_phase5_shell.md` | `P1` | `debug/P0_phase5_shell.md` |
| `debug/P1_phase5_env.md` | `P2` | `debug/P1_phase5_env.md` |
| `debug/P2_phase5_baseline.md` | `P3` | `debug/P2_phase5_baseline.md` |
| `debug/P3_phase5_git.md` | `P4` | `debug/P3_phase5_git.md` |
| `debug/P4_phase5_rollback.md` | `5A` | `debug/P4_phase5_rollback.md` |
| `debug/5A_progression_plan.md` | `5B` | `debug/5A_progression_plan.md` |
| `debug/5B_session_summary.md` | `5C` | `debug/5B_session_summary.md` |
| `debug/5C_create_excel_workbook.md` | `5D` | `debug/5C_create_excel_workbook.md` |
| `debug/5D_replace_exercise.md` | `5F` | `debug/5D_replace_exercise.md` |
| `debug/5F_suggest_supersets.md` | `5G` | `debug/5F_suggest_supersets.md` |
| `debug/5G_set_execution_style.md` | `5H` | `debug/5G_set_execution_style.md` |
| `debug/5H_link_superset.md` | `5I` | `debug/5H_link_superset.md` |
| `debug/5I_postbaseline.md` | `5J` | `debug/5I_postbaseline.md` |
| `debug/5J_recalculate_exercise_order.md` | `5E` | `debug/5J_recalculate_exercise_order.md` |
| `debug/5E_export_to_excel.md` | `5O` | `debug/5E_export_to_excel.md` |
| `debug/5O_retirement_summary.md` (and user has committed the patch) | `5Z` | `debug/5O_retirement_summary.md` |

**Note on execution order:** The sequence above is intentionally non-alphabetical. 5E depends on 5J's verdict (because `export_to_excel` calls `_recalculate_exercise_order`), and 5J depends on 5I's strengthened characterization tests. Letters 5A–5J are stable labels for cross-referencing §3 and §5; they are not an execution order.

**Escalation triggers — when Sonnet should stop and hand back to Opus instead of continuing:**

1. Any sub-phase reports full-pytest regression (I-6) vs. the active baseline — this is a hard stop regardless of cause.
2. Any sub-phase reports an I-1 signature delta, I-3 response-shape delta, or I-2 SQL delta that is not cleanly matched `-`/`+` pairs.
3. 5I cannot apply the tests/test_exports.py edit because the file has drifted since P3 — write `debug/5I_ANOMALY.md` and stop.
4. 5J reports that 5I's strengthened tests did not actually exercise the batch-update rollback path — write `debug/5J_ANOMALY.md` and stop.
5. 5O cannot apply the patch cleanly because `code_cleanup_plan.md` has drifted since P3.
6. Any unexpected file in `git status` that is not on the P3 baseline list AND is not `tests/test_exports.py` after 5I.
7. Any user instruction in chat that conflicts with the plan — Sonnet should relay the conflict, not resolve it.

**Do not escalate for:** clean pytest runs matching the active baseline, zero SQL diff hits, empty logger-level diff, matched `-`/`+` pairs in SQL diff, expected-zero rg output, expected +2 test count after 5I. Those are the bulk of Sonnet's work.

---

## 12. Anti-Patterns (Hard Rules — do not do these)

1. **Do not re-execute the `3i-a..3i-h` decompositions.** The code is already refactored in `12c90ac`. Re-refactoring risks breaking the green tests and corrupts committed history. Sub-phase 5A–5H is **validation**, not execution.
2. **Do not `git revert 12c90ac`.** The rollup commit also contains `3a-3h` cleanup work that is independently valuable and out of scope. If an emergency whole-file restore is needed, §8 describes the per-file `git show 47736b9:<path>` extraction and the user runs the write.
3. **Do not bundle the uncommitted working-tree changes** (progression-related UI work) into any Phase 5 sub-phase. They are unrelated scope. §2 Execution Rules names them explicitly.
4. **Do not mark any sub-phase PASS based on "it looks right."** Every PASS verdict must be backed by a concrete mechanical check result recorded in `debug/<letter>_*.md`.
5. **Do not skip 5I because it writes code.** 5I is explicitly sanctioned to edit `tests/test_exports.py` — it is the reason 5J can honestly claim ≥95% after it runs. Skipping 5I would demote 5J to ESCALATE and defeat the purpose of the revision. 5I is also strictly scoped: it may NOT touch any `.py` file outside `tests/test_exports.py`.
6. **Do not skip 5J because it's the hardest.** With 5I's strengthened tests in place, 5J's coverage audit should now pass cleanly. If 5J still escalates, that is a legitimate and useful outcome — 5J documents the gap, it does not pretend to close it.
7. **Do not edit `docs/phase5_3i_plan.md` from inside a sub-phase.** If a sub-phase sees an anomaly, it writes `debug/<letter>_ANOMALY.md` — a new file, one per anomaly. The plan itself stays untouched during validation. Plan edits (if any) are an Opus-level activity, not a Sonnet-level one.
8. **Do not write outside the sub-phase's sanctioned scope.** Only three sub-phases may write to the repo:
   - **P4** writes exactly one git tag (`phase5-rollback-point`) and is idempotent.
   - **5I** writes ONLY to `tests/test_exports.py`.
   - **5O** writes ONLY to `docs/code_cleanup_plan.md`.
   Any other write — including "trivial" whitespace fixes, comment updates, or related-file edits — is a scope violation and triggers `debug/<letter>_ANOMALY.md`.
9. **Do not commit the 5O plan-retirement patch without user approval.** 5O writes the patch file; the user runs `git commit`. The 5I test commit is a separate step, also user-initiated. These are deliberate two-step boundaries.
10. **Do not delete `debug/5*` artifacts** in 5Z or afterward. They are the Phase 5 audit trail and reviewers (Gemini, Codex) may want to inspect them.
11. **Do not read whole files** when an `offset`/`limit` range is specified. The budget cap exists to keep Sonnet under 15k input tokens per action.
12. **Do not conflate 3i-e with 3j.** `5E` validates the `export_to_excel` composer (pure helper extraction). `5J` validates the `_recalculate_exercise_order` batch-update (semantic change). They share the same test file (`tests/test_exports.py`) but they are separate invariant checks, and they have their own independent ESCALATE decision criteria.
13. **Do not interpret `code_cleanup_plan.md` §[Phase 3i] `[x]` marks as authoritative.** They are the exact self-inconsistency this plan closes. Until 5O commits, the authoritative source of truth for 3i/3j status is `phase5_3i_plan.md` §5 exit artifacts. After 5I commits but before 5O commits, the authoritative source of truth for test-level coverage of `_recalculate_exercise_order` is `debug/5I_postbaseline.md`, NOT the old `tests/test_exports.py` snapshot.
14. **Do not assume alphabetical execution order.** 5J runs before 5E. 5I runs before 5J. See §11 decision table for the authoritative sequence.

---

## 13. Post-5O Decision Tree — What Happens After Phase 5 Closes

### 13.1 State of the repo when you land here

After 5Z completes, the following is **true by construction** — do not re-verify unless something smells wrong:

- Rollback tag `phase5-rollback-point` has been deleted.
- `debug/P0_*.md` through `debug/5Z_close.md` exist as the Phase 5 audit trail. Do not delete them. Notable entries include `debug/5I_postbaseline.md` (the +2-test rollover baseline) and any `debug/<letter>_ANOMALY.md` files if anomalies occurred.
- `tests/test_exports.py` has +2 tests vs. the P2 baseline (`test_recalculate_exercise_order_null_initialization` and `test_recalculate_exercise_order_no_op`), plus a fixed `test_recalculate_exercise_order_atomic_failure` that now exercises a trigger-induced real SQLite rollback path through `DatabaseHandler.executemany`. Those edits were either committed alongside 5O (single commit) or as a separate 5I-only commit that landed before 5O. Check `git log --oneline -- tests/test_exports.py` to see which.
- `docs/code_cleanup_plan.md` §3i and §3j bodies are retired in favor of pointers to this plan (landed in the user-approved 5O commit).
- `docs/code_cleanup_plan.md` Status Dashboard → Stage Tracker rows for `3i` and `3j` reflect either `Completed` (if all sub-phases PASSed) or `Completed with ESCALATE: <invariant>` (if any sub-phase escalated).
- Phase 5 touched NO source `.py` file outside `tests/test_exports.py`. Every production `.py` file is unchanged from the pre-Phase-5 state.
- The pytest baseline is `debug/5I_postbaseline.md` (P2 count + 2), which is what 5J and 5E gated against.

### 13.2 What is still open after Phase 5

| # | Item | State after Phase 5 | Owner |
|---|---|---|---|
| 1 | 5J characterization coverage for `_recalculate_exercise_order` batch update | Expected **PASS after 5I hardening** — the 4 named branches (success, NULL-init, no-op, rollback) now have dedicated tests that all exercise the real `executemany` path. If 5J still escalated, see `debug/5J_ANOMALY.md` and `debug/5I_postbaseline.md`. | User decides: accept the verdict or spawn a follow-on test-addition plan |
| 2 | Any other 5A–5H ESCALATE verdicts | Documented in the corresponding `debug/5<letter>_*.md` | Follow-on plan per escalation |
| 3 | `create_performance_indexes()` not in startup | Still open from CLAUDE.md Appendix C | Separate from Phase 5 |
| 4 | 4M bugs | Resolved after Phase 5: Progression in `ec748ba`; Weekly/Session summary UX in `b058d19`, `73bc1eb`, and `571a365` | None |
| 5 | `db_seed_fix_plan.md` Phase F | Still deferred | User decision |
| 6 | Gemini review of this plan | Still pending as of 2026-04-11 (Codex v1 review addressed in v2 revision) | User decides whether to ask Gemini for a second opinion before marking Phase 5 closed |

### 13.3 Reporting format when you land here as a fresh agent

```
Phase 5 is closed per debug/5Z_close.md.

Sub-phase summary (from debug/5Z_close.md):
  5A generate_progression_suggestions: <PASS | ESCALATE>
  5B calculate_session_summary:        <PASS | ESCALATE>
  5C create_excel_workbook:            <PASS | ESCALATE>
  5D replace_exercise:                 <PASS | ESCALATE>
  5F suggest_supersets:                <PASS | ESCALATE>
  5G set_execution_style:              <PASS | ESCALATE>
  5H link_superset:                    <PASS | ESCALATE>
  5I test hardening (tests/test_exports.py): <COMMITTED at <hash>>  ← +2 tests
  5J _recalculate_exercise_order (3j): <PASS | ESCALATE>
  5E export_to_excel:                  <PASS | ESCALATE>
  5O plan retirement edit:             <COMMITTED at <hash>>

Final pytest: <count> passed, <count> skipped (≥ debug/5I_postbaseline.md <base>)

Remaining open items:
  1. <any ESCALATE follow-ons>
  2. Gemini review of this plan (if user wants a second reviewer)
  3. 4M bugs resolved after Phase 5 close-out
  4. Other backlog items from CLAUDE.md Appendix C

Which would you like to work on next?
```

Do not start work on any item without an explicit "go" from the user.

---
