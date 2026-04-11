# Phase 4 Option C — Full Close-Out Plan

**Author:** Claude (Opus 4.6), 2026-04-11
**Branch:** `spring-cleanup`
**Parent plan:** [docs/code_cleanup_plan.md](code_cleanup_plan.md)
**Companion plan:** [docs/db_seed_fix_plan.md](db_seed_fix_plan.md) (seed regen — already complete at commit `0e0ca3b`)
**Confidence target:** ≥95% at every action, ≥95% aggregated
**Scope:** closes out Phase 4 including `4A`, `4F`, `4G`, `4H`, `4J`, `4K`, `4L`, `4M`, `4O` — excludes deferred `3i`, `3j`, and Phase F architectural cleanup.

---

## Reading Order (fresh agents start here)

Route yourself based on repo state **before** reading the rest of this file:

| If this is true… | Read this section first | Then |
|---|---|---|
| `debug/4O_commit.txt` exists | **§18 Post-4O Decision Tree** | Report state to user per §18.6; do not re-execute any closed action |
| `debug/4O_commit.txt` missing AND `debug/4M_smoke_results.md` exists with failures | **§10 Phase 4M** → 4M-3 | Use §17 Fresh Session Kickoff Prompt with `{{action_id}}`=`4M-3` |
| `debug/4M_smoke_results.md` missing | **§1 Prerequisites** → **§0 Self-Contained Context** | Use §17 prompt starting from the first unfinished action |
| You are Opus re-entering this plan mid-execution after a token-limit handoff | **§15 Execution Notes** (dated entries) | Pick up at the action named in the last dated entry |

Do not read the plan linearly on entry. Each Phase 4 action is self-contained — load only what you need.

---

## 0. Self-Contained Context (for fresh LLM sessions)

**What is already done before this plan starts:**
- Phases 0, 3a–3h are COMPLETE but **uncommitted** (working-tree blob since commit `47736b9`).
- Phase D of `db_seed_fix_plan.md` is COMPLETE and committed at `0e0ca3b`. Seed DB is catalog-only, 1897 exercises + 1598 isolated muscles, `movement_pattern` column present.
- Known Bugs Triage (`code_cleanup_plan.md` §Known Bugs Triage) shows Bug 1 and Bug 2 both `Fixed` — not reproducible.
- Phase 4N seed-path hardening is COMPLETE (`SEED_DB_PATH` points at `data/backup/database.db`, regression test `tests/test_seed_db_paths.py` added, 2 passed).

**Current baseline (verified 2026-04-11):**
- pytest: **934 passed, 1 skipped** (~106s)
- Playwright full Chromium: 315 passed (last verified 2026-04-10)
- Playwright workout-plan spec: 17 passed (last verified 2026-04-10)
- Playwright summary-pages spec: 21 passed (last verified 2026-04-10)
- Live DB: 1897 exercises, 1598 isolated muscles, 4 program_backups, 8 program_backup_items, 1 progression_goals
- Seed DB: 1897 exercises, 1598 isolated muscles, catalog-only, no user-data leakage

**What this plan covers:**
- Commit the working-tree blob (4A — two variants offered).
- Run all Phase 4 audits (`4F`, `4G`, `4H`, `4K`).
- Delete flagged frontend orphans (`4J`).
- Capture file/line deltas (`4L`).
- Run manual workflow smoke (`4M` — user-driven).
- Update CLAUDE.md and close the cleanup plan (`4O`).

**What this plan does NOT cover:**
- `3i` bloated-function decomposition (plan rates 50–60% confidence).
- `3j` export write-path optimization (plan rates 55–60% confidence).
- `db_seed_fix_plan.md` Phase F architectural cleanup (`SEED_DB_PATH` retirement).

---

## 1. Prerequisites (run once before any action)

All prerequisites are read-only or install-only. None modify source.

### P1 — Environment sanity
**Exit artifact:** `debug/P1_env.md`

- [ ] Current branch == `spring-cleanup` (`git branch --show-current`)
- [ ] HEAD == `0e0ca3b` seed regen commit (`git log -1 --oneline`)
- [ ] `.venv/Scripts/python.exe --version` returns a Python 3.10+ version
- [ ] `node --version` and `npx --version` both succeed
- [ ] `npx playwright --version` returns a version string

### P2 — Tool availability
**Exit artifact:** `debug/P2_tools.md`

- [ ] `vulture` importable: `.venv/Scripts/python.exe -c "import vulture; print(vulture.__version__)"`
- [ ] If not present, install: `.venv/Scripts/python.exe -m pip install vulture`
- [ ] `pylint` importable: `.venv/Scripts/python.exe -c "import pylint; print(pylint.__version__)"`
- [ ] If not present, install: `.venv/Scripts/python.exe -m pip install pylint`
- [ ] `rg` (ripgrep) on PATH: `rg --version`
- [ ] Record each tool's version in the exit artifact

### P3 — Baseline capture (single source of truth for all subsequent gates)
**Exit artifact:** `debug/P3_baseline.md`

- [ ] Capture current pytest baseline: `.venv/Scripts/python.exe -m pytest tests/ -q > debug/P3_pytest.txt 2>&1`
- [ ] Expected result: `934 passed, 1 skipped`
- [ ] Capture current `git status --short` output
- [ ] Capture current `git diff --stat 47736b9 HEAD` output (should show seed DB only)
- [ ] Capture current `git diff --stat HEAD` output (should show the full spring-cleanup blob)
- [ ] Record the total file count and total line count from §4L's commands (for delta comparison later)

### P4 — Rollback checkpoint
**Exit artifact:** `debug/P4_rollback.md`

- [ ] Record current HEAD hash: `git rev-parse HEAD` → should be `0e0ca3b`
- [ ] Tag the rollback point: `git tag phase4-rollback-point 0e0ca3b`
- [ ] Verify tag exists: `git tag -l phase4-rollback-point`
- [ ] Document rollback command in artifact: `git reset --hard phase4-rollback-point` (destructive — use only if a phase regresses and cannot be fixed forward)
- [ ] Note: `data/backup/database.db.pre-regen.bak` is still in the working tree from Phase D; keep it until 4O completes

**Prerequisite gate:** all four P1–P4 exit artifacts present before any Phase 4 action runs. If any fails, stop and resolve before continuing.

---

## 2. Execution Rules for LLM Handoffs

- **One action per conversation session** where possible. Max two if they share a file context.
- **Token budget per action:** ≤15k input tokens. Source file reads scoped to line ranges named in each action.
- **Exit artifact required** for every action. No verbal "done" — always a file on disk under `debug/`.
- **Test re-run gate** after every code-modifying action: re-run `.venv/Scripts/python.exe -m pytest tests/ -q`; result must match baseline or exceed it. Any regression → stop, diagnose, rollback if needed.
- **No combining phases.** 4F, 4G, 4H etc. are independent. Each has its own exit criterion.
- **If an action reveals unexpected state,** stop and record a note in §15 before proceeding.
- **Never run `git reset --hard` or delete files without explicit confirmation from the user.** This rule overrides the plan's suggested commands if they conflict.
- **Fresh LLM session continuity:** a session picking up from any action must be able to continue by reading (a) this file, (b) the most recent exit artifact, (c) the files explicitly named in the active action.

---

## 3. Phase 4A — Commit the Working-Tree Blob

**Goal:** move spring-cleanup phases 3a–3h from the working tree into committed history, so every subsequent audit has a stable baseline to diff against.

**Two variants — pick one before starting:**

- **Variant 4A-Simple** — one rollup commit covering all of 3a–3h. Fast (~10 min), loses per-phase `git bisect` granularity. Recommended if you do not anticipate needing to bisect individual cleanup phases.
- **Variant 4A-Canonical** — one commit per phase (3a, 3b W1, 3c, 3d, 3e, 3f, 3g, 3b W2, 3h). Slower (~45 min), preserves bisect. Recommended if you want full fidelity to the plan's golden rule.

**Decision gate:** the user must explicitly pick a variant before 4A starts. Record the choice in `debug/4A_variant.md`.

---

### 4A-Simple — Rollup commit (one action)

#### 4A-S1 — Stage and commit the blob
**Files referenced:** full working tree
**Exit artifact:** `debug/4A_commit.txt` (commit hash)

- [ ] Run `git status --short` and confirm the modified/deleted/untracked set matches the P3 snapshot exactly
- [ ] Stage the blob with explicit file paths — **NOT** `git add -A` (sensitive files risk):
  - [ ] `git add CLAUDE.md app.py`
  - [ ] `git add docs/CHANGELOG.md docs/code_cleanup_plan.md`
  - [ ] `git add e2e/summary-pages.spec.ts`
  - [ ] `git add routes/exports.py routes/session_summary.py routes/weekly_summary.py routes/workout_log.py routes/workout_plan.py`
  - [ ] `git add templates/session_summary.html templates/weekly_summary.html templates/partials/`
  - [ ] `git rm templates/debug_modal.html templates/dropdowns.html templates/exercise_details.html templates/filters.html templates/table.html templates/workout_tracker.html`
  - [ ] `git add tests/test_effective_sets.py tests/test_exports.py tests/test_seed_db_paths.py`
  - [ ] `git rm tests/test_business_logic.py tests/test_data_handler.py tests/test_muscle_group.py`
  - [ ] `git add utils/__init__.py utils/constants.py utils/database.py utils/db_initializer.py utils/effective_sets.py utils/export_utils.py utils/filter_cache.py utils/normalization.py utils/plan_generator.py utils/program_backup.py utils/progression_plan.py utils/session_summary.py utils/volume_classifier.py utils/weekly_summary.py`
  - [ ] `git rm utils/business_logic.py utils/data_handler.py utils/database_init.py utils/filters.py utils/helpers.py utils/muscle_group.py`
- [ ] **DO NOT** stage: `baseline_*.txt`, `cleanup_preflight*.txt`, `phase4*.txt`, `data/backup/database.db.pre-regen.bak`, `debug/`
- [ ] Verify staged set: `git diff --stat --cached` — should show ~40 files, the deletions and modifications only
- [ ] Commit with message:
  ```
  feat(spring-cleanup): complete phases 3a-3h per code_cleanup_plan.md

  Bundles all validated cleanup phases into a single rollup commit:
  - 3a unused import removal in routes/
  - 3b Wave 1 dead-module deletions (helpers, filters, database_init, muscle_group)
  - 3b Wave 2 package-surface contraction (business_logic, data_handler, legacy exports)
  - 3c orphaned template deletion (6 templates)
  - 3d shared parse-function extraction in utils/effective_sets.py
  - 3e summary-page coupling gate (documentation only)
  - 3f method-selector macro extraction to templates/partials/
  - 3g backend-only volume classifier consolidation
  - 3h DB migration + logging cleanup

  Validated at 934 passed, 1 skipped (pytest) + 315 passed (Playwright).
  Per-phase bisect granularity is intentionally forgone; use
  4A-Canonical if per-phase bisect is required.
  ```
- [ ] Record commit hash in `debug/4A_commit.txt`
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/ -q` → must show `934 passed, 1 skipped`. Save to `debug/4A_pytest.txt`.
- [ ] If regresses: `git reset HEAD~1` (keep changes) → stop → diagnose. Do not force forward.

**4A-Simple exit gate:** commit hash recorded, working tree shows only the intentionally-untracked artifacts (`baseline_*.txt`, `phase4*.txt`, `debug/`, `.pre-regen.bak`), pytest matches baseline.

---

### 4A-Canonical — Per-phase commits (nine actions)

> **⚠ SUPERSEDED on 2026-04-11.** 4A-Simple was executed and the rollup commit lives at `12c90ac` (`feat(spring-cleanup): complete phases 3a-3h per code_cleanup_plan.md`). 4A-Canonical was **not taken**. This variant is retained only as documentation of the alternative path.
>
> **Do not run 4A-Canonical on the current branch** — the working-tree blob has already been committed. Any attempt will find an empty staging area.
>
> **Sonnet-readiness:** 4A-Canonical is **NOT Sonnet-safe** as written. The file→phase classification in 4A-C0 is a judgment-heavy task (≥40 files, 9 buckets) and smaller models will misassign. If a future reset requires re-running this variant, an **Opus-produced `debug/4A_canonical_map.md` is a hard prerequisite** — generate it from `git show 12c90ac --stat` cross-referenced against `code_cleanup_plan.md` §Phase 3a–3h, then hand the per-phase file lists to Sonnet baked directly into each C1–C9 action (mirror the explicit list pattern used in 4A-Simple lines 122–132).
>
> **Original warning (retained for context):** this variant requires the executor to correctly assign each file in the blob to one of the nine phases. Misassignment is the main failure mode. To mitigate, each action should list **explicit file paths** derived from the plan's per-phase execution checklist in `code_cleanup_plan.md`.

#### 4A-C0 — Build file→phase map
**Files referenced:** [docs/code_cleanup_plan.md](code_cleanup_plan.md) §[Phase 3a] through §[Phase 3h]
**Exit artifact:** `debug/4A_canonical_map.md`

- [ ] Read [code_cleanup_plan.md](code_cleanup_plan.md) lines 1490–end (per-phase execution checklists)
- [ ] For each file in `git status --short`, map it to exactly one phase based on the checklist
- [ ] Produce a table: `file → phase`
- [ ] Flag any file that cannot be unambiguously mapped → escalate to user before proceeding
- [ ] Exit: the map is committed to `debug/4A_canonical_map.md` with zero unmapped files

#### 4A-C1 through 4A-C9 — One action per phase
Each sub-action follows the same shape. Template:

**Per-phase action template:**
- [ ] Read the file→phase map entry for this phase
- [ ] `git add` only the files mapped to this phase (explicit paths; no wildcards)
- [ ] `git diff --stat --cached` must match the expected file list; any mismatch → stop
- [ ] Commit with message: `<type>(<phase-id>): <short description per code_cleanup_plan.md>`
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/ -q` → must match baseline
- [ ] Record commit hash in `debug/4A_<phase-id>.txt`
- [ ] Any test failure → `git reset HEAD~1` → stop → diagnose

**Phase-specific commit subjects (use verbatim):**
- **4A-C1** `chore(3a): remove unused imports in routes`
- **4A-C2** `chore(3b-wave1): delete dead internal modules (helpers, filters, database_init, muscle_group)`
- **4A-C3** `chore(3c): delete six orphaned templates`
- **4A-C4** `refactor(3d): extract shared parse helpers into utils/effective_sets`
- **4A-C5** `docs(3e): lock summary-page ownership as fallback-only contract`
- **4A-C6** `refactor(3f): extract method_selector macro into templates/partials`
- **4A-C7** `refactor(3g): consolidate raw-volume thresholds in utils/volume_classifier`
- **4A-C8** `chore(3b-wave2): retire legacy package surface (business_logic, data_handler, legacy utils exports)`
- **4A-C9** `chore(3h): finalize DB migration and logging cleanup`

**4A-Canonical exit gate:** nine commits exist on top of `0e0ca3b`, `git log --oneline 0e0ca3b..HEAD` shows exactly nine entries, working tree clean (except intentional untracked artifacts), pytest matches baseline after every intermediate commit.

---

## 4. Phase 4F — Dead-Code Scan (vulture)

**Goal:** surface any dead code the manual cleanup missed. **Read-only by default.** Deletions require explicit user approval per finding.

**Files referenced:** `routes/`, `utils/` (full trees)

### 4F-1 — Run vulture
**Exit artifact:** `debug/4F_vulture.txt`

- [ ] Run: `.venv/Scripts/python.exe -m vulture routes/ utils/ --min-confidence 80 > debug/4F_vulture.txt 2>&1`
- [ ] Count findings: `wc -l debug/4F_vulture.txt`
- [ ] Expected: low double digits or fewer

### 4F-2 — Classify findings
**Exit artifact:** `debug/4F_classification.md`

> **Sonnet-ready mechanical rubric.** For each finding `<name>` at `<file>:<line>`, run **every** command below and record the hit counts. The classification is determined by the rule table — do not use judgment.

**Per-finding verification commands:**
```bash
# 1. Direct references across all code surfaces (the primary signal)
rg -n "\b<name>\b" routes/ utils/ templates/ static/ tests/ e2e/ app.py

# 2. Flask route decorator (treat as DYNAMIC if any hit)
rg -n "@[a-zA-Z_]+\.route.*['\"]\S*<name>|def <name>\s*\(" routes/

# 3. Jinja2 template reference (treat as DYNAMIC if any hit)
rg -n "<name>" templates/ -t html

# 4. pytest fixture / parametrize / mark (treat as DYNAMIC if any hit)
rg -n "@pytest\.(fixture|mark|parametrize).*<name>|fixture.*<name>|def <name>\s*\(.*fixture" tests/

# 5. __all__ export (treat as PUBLIC_API if any hit)
rg -n "__all__" utils/ routes/ | rg "<name>"

# 6. CLAUDE.md reference (treat as PUBLIC_API if any hit)
rg -n "<name>" CLAUDE.md docs/

# 7. Dynamic dispatch via getattr / string lookup (treat as DYNAMIC if any hit)
rg -n "getattr\([^,]+,\s*['\"]<name>['\"]|['\"]<name>['\"].*getattr" routes/ utils/
```

**Classification rule table — apply in this order, first match wins:**

| Signal | Classification | Action |
|---|---|---|
| Command 5 or 6 returns ≥1 hit | **PUBLIC_API** | Leave alone |
| Command 2, 3, 4, or 7 returns ≥1 hit | **DYNAMIC** | Leave alone |
| Command 1 returns 0 hits outside the defining file | **TRUE_DEAD** | Candidate for deletion (4F-3 gate) |
| Command 1 returns hits but none of 2/3/4/5/6/7 match | **UNCLEAR** | Escalate to user |

- [ ] For each finding in `debug/4F_vulture.txt`, run all 7 commands above
- [ ] Record in `debug/4F_classification.md` as a row: `file:line | name | cmd1_hits | cmd2_hits | cmd3_hits | cmd4_hits | cmd5_hits | cmd6_hits | cmd7_hits | classification`
- [ ] Any row classified UNCLEAR → escalate before proceeding to 4F-3

### 4F-3 — Decide and record (no deletions yet)
**Exit artifact:** `debug/4F_decision.md`

- [ ] List all TRUE_DEAD candidates in a "proposed deletions" table
- [ ] **STOP HERE.** Do not delete. Escalate the table to the user for explicit approval.
- [ ] If user approves any deletions, each deletion becomes a separate commit following the 4A-C template (one file per commit, pytest re-run after each)

**4F exit gate:** `debug/4F_vulture.txt`, `debug/4F_classification.md`, `debug/4F_decision.md` all present. Deletions either executed (each its own commit with passing pytest) or explicitly deferred to "out of cycle" in `debug/4F_decision.md`.

---

## 5. Phase 4G — Unused-Import Scan (pylint W0611)

**Goal:** catch any `import X` regression introduced after 3a.

### 4G-1 — Run pylint W0611
**Exit artifact:** `debug/4G_pylint.txt`

- [ ] Run: `.venv/Scripts/python.exe -m pylint --disable=all --enable=W0611 routes/ utils/ > debug/4G_pylint.txt 2>&1`
- [ ] Expected: `Your code has been rated at 10.00/10` with zero `W0611` findings

### 4G-2 — Fix any findings (if present)
**Exit artifact:** per-commit hash in `debug/4G_fixes.md`

- [ ] If findings exist: remove the unused import(s) — one file per commit
- [ ] Each fix commit subject: `chore(4G): remove unused import <name> from <file>`
- [ ] Re-run `.venv/Scripts/python.exe -m pytest tests/ -q` after each fix → must match baseline
- [ ] Re-run pylint W0611 → must show zero findings

**4G exit gate:** pylint W0611 returns zero findings, pytest baseline preserved.

---

## 6. Phase 4H — `print()` Audit

**Goal:** confirm zero `print()` calls in `routes/` and `utils/` (the logging migration was supposed to clear all of them).

### 4H-1 — Run rg
**Exit artifact:** `debug/4H_print.txt`

- [ ] Run: `rg -n "print\(" routes utils -g "*.py" > debug/4H_print.txt 2>&1 || true`
- [ ] Expected: zero hits (command returns non-zero exit when no matches — `|| true` normalizes this)

### 4H-2 — Convert any findings (if present)
**Exit artifact:** per-commit hash in `debug/4H_fixes.md`

- [ ] If findings exist: convert each `print()` to `logger.info()` (or appropriate level) — one file per commit
- [ ] Each commit subject: `chore(4H): convert print() to logger in <file>`
- [ ] Re-run pytest after each fix

**4H exit gate:** zero `print()` hits in `routes/` and `utils/`, pytest baseline preserved.

---

## 7. Phase 4J — Frontend Orphan Deletion

**Goal:** remove the two JS files Phase 0.8 flagged as zero-reference safe-delete candidates.

**Files referenced:**
- `static/js/modules/sessionsummary.js`
- `static/js/updateSummary.js`

### 4J-1 — Re-verify zero references
**Exit artifact:** `debug/4J_refs.txt`

- [ ] Run: `rg -n "sessionsummary|updateSummary" static templates e2e tests routes utils app.py > debug/4J_refs.txt 2>&1 || true`
- [ ] Expected: zero hits (or only the two files' own self-references if they `export default` something)
- [ ] If any hit references either file from outside the file itself → **STOP.** The file is not orphaned. Record the reference in `debug/4J_refs.txt` and mark deletion as deferred.

### 4J-2 — Delete the two files (if 4J-1 passes)
**Exit artifact:** `debug/4J_commit.txt`

- [ ] `git rm static/js/modules/sessionsummary.js static/js/updateSummary.js`
- [ ] Commit with subject: `chore(4J): remove orphaned frontend modules (sessionsummary.js, updateSummary.js)`
- [ ] Record commit hash in `debug/4J_commit.txt`

### 4J-3 — Post-delete Playwright validation
**Exit artifact:** `debug/4J_e2e.txt`

- [ ] Run: `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line > debug/4J_e2e_summary.txt 2>&1`
- [ ] Run: `npx playwright test --project=chromium --reporter=line > debug/4J_e2e_full.txt 2>&1`
- [ ] Expected: `21 passed` (summary) and `315 passed` (full) or better
- [ ] If either regresses → `git reset --hard HEAD~1` (only after user confirmation) → stop → diagnose

**4J exit gate:** two files deleted, commit present, both Playwright gates green.

---

## 8. Phase 4K — Package-Surface Audit

**Goal:** confirm no regression reintroduced a legacy package import after 3b Wave 2.

### 4K-1 — Run rg
**Exit artifact:** `debug/4K_package.txt`

- [ ] Run: `rg -n "from utils import .*DataHandler|from utils import .*BusinessLogic|from utils\.helpers|from utils\.filters|from utils\.database_init|from utils\.muscle_group" app.py routes tests e2e > debug/4K_package.txt 2>&1 || true`
- [ ] Expected: zero hits

### 4K-2 — Fix any findings (if present)
**Exit artifact:** per-commit hash in `debug/4K_fixes.md`

- [ ] If findings exist: update each import to the canonical concrete module — one file per commit
- [ ] Each commit subject: `chore(4K): restore concrete-module import in <file>`
- [ ] Re-run pytest after each fix

**4K exit gate:** zero legacy-surface hits, pytest baseline preserved.

---

## 9. Phase 4L — File & Line Count Delta

**Goal:** populate [code_cleanup_plan.md](code_cleanup_plan.md) §4.5 with actual before/after numbers.

### 4L-1 — Capture current counts
**Exit artifact:** `debug/4L_counts.md`

- [ ] `utils/` Python file count: run glob `utils/*.py` and count results
- [ ] `routes/` Python file count: same pattern
- [ ] `templates/` file count: count all files (not just .html) in `templates/` directory
- [ ] `static/js/modules/` file count: count `.js` files only
- [ ] `static/js/` total file count: count `.js` files recursively
- [ ] Total Python LOC: sum `wc -l` across every `*.py` excluding `.venv/` and `node_modules/`
- [ ] Record all six numbers in `debug/4L_counts.md`

### 4L-2 — Compare to P3 baseline
**Exit artifact:** `debug/4L_delta.md`

- [ ] Read baseline numbers from `debug/P3_baseline.md`
- [ ] Compute delta for each metric
- [ ] Record as a table: `metric | baseline | current | delta`

**4L exit gate:** delta table exists. Values will be written into `code_cleanup_plan.md` §4.5 in Phase 4O.

---

## 10. Phase 4M — Manual Workflow Smoke (USER-DRIVEN)

**Goal:** walk through the six core workflows from [CLAUDE.md](../CLAUDE.md) §1.2 in the running app and record anything that misbehaves.

**This phase cannot be automated.** The LLM's role is only to prepare the smoke checklist artifact and to review results the user records.

### 4M-1 — Start the app
**Exit artifact:** `debug/4M_app_startup.md`

- [ ] `.venv/Scripts/python.exe app.py` (background or separate terminal)
- [ ] Confirm startup log shows: `Running on http://127.0.0.1:5000`
- [ ] Confirm no startup errors or warnings about seed DB missing
- [ ] Record PID for later cleanup

### 4M-2 — User runs the seven workflows in Edge 146+ incognito
**Exit artifact:** `debug/4M_smoke_results.md`

The user fills in pass/fail + notes for each row. The LLM does not fill in results.

- [ ] **Plan** (`/workout_plan`): open page, apply one filter, add one exercise to a routine, reorder it. Expected: all actions succeed, no console errors.
- [ ] **Log** (`/workout_log`): import from plan, edit scored reps/weight/RIR on one row, save. Expected: save succeeds, edited value persists on reload.
- [ ] **Analyze — Weekly** (`/weekly_summary`): toggle counting mode (Raw ↔ Effective), toggle contribution mode (Direct ↔ Total). Expected: numbers recompute and change visibly.
- [ ] **Analyze — Session** (`/session_summary`): same toggles + set a time-window filter. Expected: numbers recompute; time-window filter narrows results.
- [ ] **Progress** (`/progression`): pick an exercise from the dropdown, view suggestions. Expected: suggestions render with non-empty values.
- [ ] **Distribute** (`/volume_splitter`): move one slider, click recalculate. Expected: output updates.
- [ ] **Backup** (`/api/backups` modal on workout plan page): create a backup → list it → restore it → delete it. Expected: every step succeeds and reflects in the backup list.

### 4M-3 — Record failures as triage entries (if any)
**Exit artifact:** `debug/4M_triage.md`

> **Sonnet-ready capture procedure.** For each failing workflow, execute the commands in the matching block below. Copy raw command output into `debug/4M_<workflow>_logs.txt` and reference it from `debug/4M_triage.md`. Do not paraphrase log content — paste it verbatim.

**General log tail (always run first):**
```bash
tail -n 200 logs/app.log > debug/4M_tail200.log
rg -n "ERROR|Traceback|WARNING" debug/4M_tail200.log > debug/4M_errors.log
```

**Per-workflow capture blocks** — run only the block(s) matching the failed row(s) in `debug/4M_smoke_results.md`:

<details>
<summary><b>Weekly Summary</b> — counter not recomputing on Raw↔Effective toggle</summary>

```bash
# Server-side: every hit on the weekly summary route and its API deps
rg -n "GET /weekly_summary|weekly_summary|counting_mode|CountingMode" logs/app.log | tail -100 > debug/4M_weekly_server.log

# Code-side: confirm the toggle handler exists and is wired
rg -n "counting_mode|CountingMode" routes/weekly_summary.py utils/weekly_summary.py templates/weekly_summary.html static/js/

# User captures manually in Edge DevTools:
#   - Console tab: copy ALL red/yellow messages after toggle click
#   - Network tab: copy the request URL + response body of the XHR fired on toggle
#   Paste both into debug/4M_weekly_browser.log
```

**Known ask from 4M-2 run (2026-04-11):** user also requested renaming "Weekly Summary" → "Plan Summary". File as a separate triage entry (rename is scope, not a bug).
</details>

<details>
<summary><b>Session Summary</b> — counter not recomputing on Raw↔Effective toggle</summary>

```bash
rg -n "GET /session_summary|session_summary|counting_mode|CountingMode" logs/app.log | tail -100 > debug/4M_session_server.log

rg -n "counting_mode|CountingMode" routes/session_summary.py utils/session_summary.py templates/session_summary.html static/js/

# User captures manually in DevTools → paste into debug/4M_session_browser.log
```

**Cross-check hint:** session and weekly toggle bugs share the same suspect surface (`CountingMode` wiring). If weekly's root cause is found, check session for the same pattern before separate triage.
</details>

<details>
<summary><b>Progression</b> — options missing + current values not auto-populated</summary>

```bash
rg -n "GET /progression|POST /api/progression|progression" logs/app.log | tail -100 > debug/4M_progression_server.log

rg -n "def.*progression|progression_goals|current_value" routes/progression_plan.py utils/progression_plan.py templates/progression.html

# User captures manually in DevTools → paste into debug/4M_progression_browser.log
```

**Important hint from 4M-2 run (2026-04-11):** user explicitly noted "**as they were before**" — this is almost certainly a **pre-existing bug**, not a spring-cleanup regression. Verify with the command in the regression-check block below before treating as a blocker.
</details>

**Regression vs pre-existing check (run once, all failures):**
```bash
# Confirm the rollback tag still exists
git tag -l phase4-rollback-point

# Show which commit touched the suspect files since the rollback tag
git log phase4-rollback-point..HEAD --oneline -- \
  routes/weekly_summary.py utils/weekly_summary.py templates/weekly_summary.html \
  routes/session_summary.py utils/session_summary.py templates/session_summary.html \
  routes/progression_plan.py utils/progression_plan.py templates/progression.html

# If a file shows zero commits → bug is pre-existing (mark "out of cycle")
# If a file shows 1+ commits → bug may be a regression — inspect those commits
```

**Fixed-forward exception added 2026-04-11:** commit `ec748ba`
(`fix(progression): use plan values before log history`) intentionally touches
`routes/progression_plan.py`, `utils/progression_plan.py`, and progression tests
to resolve the 4M progression smoke failure. Treat `ec748ba` as an approved
fixed-forward 4M bugfix, not as a Phase 4 cleanup regression. Post-fix pytest
baseline is `936 passed, 1 skipped`.

**Triage entry format** (one row per failing workflow in `debug/4M_triage.md`):

| Workflow | Regression? | Root cause hypothesis | Evidence files | Decision |
|---|---|---|---|---|
| e.g. Weekly Summary | Yes/No/Unknown | one sentence | `debug/4M_weekly_*.log` | Fix forward / Rollback / Out of cycle |

- [ ] Run the general tail block
- [ ] Run every per-workflow block matching a failed row
- [ ] Run the regression-check block
- [ ] Write the triage table in `debug/4M_triage.md`, one row per failure
- [ ] **Do not attempt fixes in this action.** 4M-3 is capture-only; fixes happen in a follow-on phase.

### 4M-4 — Stop the app
- [ ] Ctrl+C in the Flask terminal or `Stop-Process -Id <PID>` (Windows)
- [ ] Confirm the DB lock is released: `Get-Process python -ErrorAction SilentlyContinue`

**4M exit gate:** seven workflow results recorded. Any failures become triage entries and enter Phase 4N-cleanup. If zero failures, proceed directly to 4O.

---

## 11. Phase 4N-cleanup — Already Done, Verify Only

**Goal:** confirm the seed-path hardening that landed as 4N on 2026-04-10 is still in place.

**Context:** `docs/code_cleanup_plan.md` §Known Bugs Triage §Hardening says `SEED_DB_PATH` was updated to `data/backup/database.db`, the compatibility copy was removed, and `tests/test_seed_db_paths.py` was added with 2 passing tests.

### 4N-cleanup-1 — Verify current state
**Exit artifact:** `debug/4N_verify.md`

- [ ] Confirm `SEED_DB_PATH` in [utils/db_initializer.py:16](../utils/db_initializer.py#L16) == `REPO_ROOT / "data" / "backup" / "database.db"`
- [ ] Confirm `SEED_DB_PATH` in [utils/database.py:30](../utils/database.py#L30) == same path
- [ ] Confirm `data/Database_backup/database.db` does NOT exist (no compatibility copy)
- [ ] Confirm `tests/test_seed_db_paths.py` exists
- [ ] Run: `.venv/Scripts/python.exe -m pytest tests/test_seed_db_paths.py -q > debug/4N_pytest.txt 2>&1`
- [ ] Expected: `2 passed`

**4N-cleanup exit gate:** all four verifications pass. If any fails, the hardening has regressed since 2026-04-10 — stop and escalate.

---

## 12. Phase 4O — Close the Plan

**Goal:** update [CLAUDE.md](../CLAUDE.md) and [code_cleanup_plan.md](code_cleanup_plan.md) to reflect the post-cleanup reality.

### 4O-1 — Update CLAUDE.md §8 test counts
**Files referenced:** [CLAUDE.md](../CLAUDE.md)
**Exit artifact:** diff patch in `debug/4O_claudemd.patch`

- [ ] Update `Verified Test Counts` line to: `pytest: 934 passed, 1 skipped (~106s)` and playwright counts from 4J-3 (or baseline if 4J deferred)
- [ ] Update `last verified` date to `2026-04-11`
- [ ] **Legacy modules table — mechanical check for `utils/volume_export.py`:**
  ```bash
  # Does the file still exist?
  ls utils/volume_export.py 2>/dev/null && echo "EXISTS" || echo "DELETED"

  # Does it still use the raw connection pattern the table flags?
  rg -n "get_db_connection|conn\.commit\(\)" utils/volume_export.py 2>/dev/null
  ```
  **Decision rule (no judgment):**
  - File **DELETED** → remove its row from the Deprecated / Legacy Modules table
  - File **EXISTS** and `get_db_connection` still matches → **leave the row as-is**
  - File **EXISTS** but `get_db_connection` no longer matches → update the row's "Evidence" column to reflect the new state (do NOT remove the row without explicit user approval)

> Operator decision after 4O-1 escalation (2026-04-11):
> `utils/volume_export.py` exists but the raw DB evidence is stale.
> DOCS_AUDIT_PLAN Tier 3 migrated it to `DatabaseHandler`, and
> `tests/test_volume_splitter_api.py::test_export_volume_plan_rolls_back_on_insert_failure`
> covers rollback semantics. For 4O-1, remove `utils/volume_export.py` from
> `CLAUDE.md` Current Exceptions and Deprecated / Legacy Modules; keep only
> `utils/database_indexes.py` as the intentional raw DB maintenance exception.
- [ ] Save diff: `git diff CLAUDE.md > debug/4O_claudemd.patch`

### 4O-2 — Update code_cleanup_plan.md §4.5 with 4L numbers
**Files referenced:** [code_cleanup_plan.md](code_cleanup_plan.md)
**Exit artifact:** diff patch in `debug/4O_planmd.patch`

- [ ] Open `docs/code_cleanup_plan.md` §4.5 "Expected Reduction Summary"
- [ ] Replace the placeholder `est.` values with actuals from `debug/4L_counts.md`
- [ ] Mark the Status Dashboard §Stage Tracker row for Phase 4 as `Completed`
- [ ] Resolve the 3i self-inconsistency: if 3i stays deferred, remove the `[x]` marks in the [Phase 3i] checklist or add a clarifying note

### 4O-3 — Update docs/CHANGELOG.md
**Files referenced:** [docs/CHANGELOG.md](CHANGELOG.md)
**Exit artifact:** diff patch in `debug/4O_changelog.patch`

- [ ] Add single entry summarizing the spring-cleanup sequence: phases completed, test-count change, files removed, architectural notes
- [ ] Link to the 4A commit hash(es)
- [ ] Link to `0e0ca3b` (seed regen)

### 4O-4 — Commit the documentation updates
**Exit artifact:** `debug/4O_commit.txt`

- [ ] `git add CLAUDE.md docs/code_cleanup_plan.md docs/CHANGELOG.md`
- [ ] Commit subject: `docs(4O): close spring-cleanup Phase 4 — verified counts and reduction delta`
- [ ] Record commit hash
- [ ] Final pytest re-run: `.venv/Scripts/python.exe -m pytest tests/ -q` → `934 passed, 1 skipped`

### 4O-5 — Clean up rollback artifacts
**Exit artifact:** `debug/4O_cleanup.md`

- [ ] Confirm Phase 4 is fully green (all exit gates passed)
- [ ] Delete the 24h rollback file: `rm data/backup/database.db.pre-regen.bak` (only if D commit `0e0ca3b` is older than 24h OR user explicitly confirms)
- [ ] Delete the rollback tag: `git tag -d phase4-rollback-point`
- [ ] Keep `debug/` directory for audit trail (do not delete)

**4O exit gate:** CLAUDE.md, code_cleanup_plan.md, CHANGELOG.md all updated and committed. Final pytest green. Rollback artifacts cleaned up.

---

## 13. Confidence Statement

| Component | Confidence | Justification |
|---|---|---|
| P1–P4 prerequisites | **100%** | Read-only or install-only; no risk. |
| 4A-Simple (rollup commit) | **≥97%** | Explicit file list (no `-A`); pytest gate after commit; reversible via `git reset HEAD~1` within the same session. |
| 4A-Canonical (9 commits) | **≥95%** | Higher surface area (9 commits instead of 1), mitigated by file→phase map and per-commit pytest. Slightly lower than Simple. |
| 4F vulture scan | **≥98%** | Read-only by default; deletions require explicit user approval per finding. |
| 4G pylint W0611 | **≥99%** | Command is read-only; any fixes are one-line removals with pytest gate. |
| 4H print audit | **≥99%** | Same shape as 4G; fixes are trivial logger conversions. |
| 4J orphan deletion | **≥96%** | Phase 0.8 already verified zero references; 4J-1 re-verifies before deletion; Playwright gates catch runtime regression. |
| 4K package-surface audit | **≥99%** | Read-only command; any fix is a one-line import change. |
| 4L file/line delta | **100%** | Measurement only; no writes. |
| 4M manual smoke | **user-gated** | LLM cannot rate this; the user is the oracle. Confidence is `pass` if user reports no failures, otherwise triage entries feed a future 4N cycle. |
| 4N-cleanup verify | **100%** | Pure verification of already-completed work. |
| 4O documentation close-out | **≥99%** | Doc-only edits; final pytest gate catches any accidental code reference. |
| **Overall Option C aggregate** | **≥95%** | Each action is gated, reversible, and independently verifiable. The lowest-confidence link (4A-Canonical at 95%) is user-electable; 4A-Simple keeps the aggregate comfortably above 95%. |

**Risk registry (items that could lower confidence if they surface):**
1. vulture false positives misclassified as TRUE_DEAD → mitigated by 4F-3 human-approval gate
2. 4A-Canonical file→phase misassignment → mitigated by 4A-C0 mapping artifact and per-commit pytest
3. 4J orphan file referenced dynamically (e.g., via string concatenation in a template) → mitigated by 4J-3 Playwright re-run
4. 4M surfaces a real bug → triggers a new 4N cycle, not a confidence loss for this plan
5. User runs 4F/4J deletions without reviewing the 4F-3/4J-1 artifacts → mitigated by plan's explicit "STOP HERE" gates

---

## 14. Rollback Playbook

| Scenario | Action |
|---|---|
| A 4A commit regresses pytest | `git reset HEAD~1` (keeps changes in working tree), diagnose, re-stage correctly, commit again |
| A 4J deletion regresses Playwright | After user confirmation: `git reset --hard HEAD~1` |
| A 4F deletion regresses pytest | After user confirmation: `git reset --hard HEAD~1` |
| Any phase reveals corrupt live DB | Restore from `data/database.phase4_preseed.backup.db` (snapshot from 2026-04-10) |
| Phase D seed fix needs rollback | Restore from `data/backup/database.db.pre-regen.bak` (still present until 4O-5) |
| Full Phase 4 needs to be abandoned | `git reset --hard phase4-rollback-point` (tag set in P4) — this discards all Phase 4 commits but keeps Phase D seed fix at `0e0ca3b` |
| Uncertain / stuck | Stop. Do not improvise. Escalate to user with the current state and the last known-good artifact. |

---

## 15. Execution Notes

### 2026-04-11 (morning)
- Plan created as the Option C breakdown requested after `db_seed_fix_plan.md` Phase D+E closed green.
- Variant decision (4A-Simple vs 4A-Canonical) is explicitly deferred to the user — record the choice in `debug/4A_variant.md` before starting 4A.
- All prerequisites (P1–P4) must run before any Phase 4 action. No exceptions.
- Phase 4M is user-driven; LLM role is artifact preparation and result intake only.

### 2026-04-11 (afternoon) — execution log
- P3 baseline captured (`debug/P3_*`). 934 passed / 1 skipped confirmed.
- **4A-Simple taken** and committed at `12c90ac`. 4A-Canonical marked SUPERSEDED.
- 4F vulture scan complete — decision artifacts at `debug/4F_vulture.txt`, `debug/4F_classification.md`, `debug/4F_decision.md`.
- 4G pylint W0611: zero findings (`debug/4G_pylint.txt`).
- 4H print audit: zero hits (`debug/4H_print.txt`).
- 4J orphan deletion committed at `596acde`. Playwright gates green (`debug/4J_e2e_*.txt`).
- 4K package-surface audit: zero hits (`debug/4K_package.txt`).
- 4L counts and delta recorded (`debug/4L_counts.md`, `debug/4L_delta.md`).
- 4M smoke test run — **3 failures** (Weekly/Session counter toggle, Progression). Triage pending in 4M-3.
- **Remaining actions: 4M-3, 4M-4, 4N-cleanup, 4O.**

### 2026-04-11 (evening) — Sonnet-readiness pass (Opus)
- Plan hardened for handoff to smaller models (Sonnet 4.6) to conserve Opus token allowance.
- **Gap 1** — 4A-Canonical marked SUPERSEDED with an explicit Sonnet-safety warning; the variant is preserved as documentation only.
- **Gap 2** — 4F-2 classification rubric replaced with a mechanical 7-command verification table (no judgment calls).
- **Gap 3** — 4M-3 triage replaced with per-workflow log-capture command blocks + regression-vs-pre-existing decision command. Known failures from the 2026-04-11 run are baked in directly.
- **Gap 4** — 4O-1 legacy-module check converted from "read and decide" to a grep assertion with a three-way decision rule.
- **Gap 5** — §17 "Fresh Session Kickoff Prompt" added; Sonnet handoffs now follow a single canonical entry template.
- The remaining actions (4M-3, 4M-4, 4N-cleanup, 4O) are now safe to execute under Sonnet 4.6 using the §17 prompt.

### 2026-04-11 (evening) — progression fixed-forward exception

- Commit `ec748ba` (`fix(progression): use plan values before log history`) was added after user approval to fix the 4M progression failure before Phase 4 close-out.
- Independent review found no blocking issues. Verified with focused progression Python tests (`83 passed`), Playwright progression lifecycle smoke (`1 passed`), and full pytest (`936 passed, 1 skipped`).
- 4M-3 should record Progression as fixed-forward in `ec748ba`; only Weekly Summary and Session Summary remain out-of-cycle/open unless separately fixed.

---

## 16. Action Count Summary

| Phase | Actions | Estimated total tokens (input) | User-gated? |
|---|---|---|---|
| P1–P4 prerequisites | 4 | ~8k | no |
| 4A-Simple | 1 | ~10k | variant choice |
| 4A-Canonical | 10 (C0 + C1–C9) | ~60k total | variant choice |
| 4F vulture | 3 | ~15k | 4F-3 user approval for deletions |
| 4G pylint | 2 | ~5k | no |
| 4H print | 2 | ~5k | no |
| 4J orphan delete | 3 | ~12k | no (but Playwright gate) |
| 4K package audit | 2 | ~5k | no |
| 4L delta | 2 | ~5k | no |
| 4M smoke | 4 | ~10k | **fully user-driven** |
| 4N-cleanup verify | 1 | ~5k | no |
| 4O close plan | 5 | ~20k | no |
| **Total (4A-Simple path)** | **29 actions** | **~100k input tokens across all actions** | |
| **Total (4A-Canonical path)** | **38 actions** | **~150k input tokens across all actions** | |

**Per-action average:** ~3k input tokens. Safe for a 200k-context-window model with significant headroom for the active file reads each action requires.

---

## 17. Fresh Session Kickoff Prompt (for Sonnet 4.6 handoffs)

**Purpose:** this section gives the canonical prompt to paste into a fresh Sonnet 4.6 session to execute the next action in this plan. It exists so Opus does not have to re-derive the handoff context each time — saving Opus token allowance.

**Usage:** copy the block below, fill in the three `{{placeholders}}`, paste into a new Sonnet session as the user's first message.

```
You are continuing spring-cleanup Phase 4 on the Hypertrophy-Toolbox-v3 repo.
Branch: spring-cleanup. Working directory: the repo root.

ACTIVE ACTION: {{action_id}}   (e.g., 4M-3, 4N-cleanup-1, 4O-1)
PRIOR EXIT ARTIFACT: {{last_artifact_path}}   (e.g., debug/4M_smoke_results.md)

Do the following in order. Do not improvise, do not combine steps, do not
proceed past an exit gate without confirming it.

1. Read docs/phase4_option_c_plan.md — ONLY the section for the active action
   above. Do not read the whole plan. Use the section headings as anchors.
2. Read the prior exit artifact named above.
3. Read ONLY the source files explicitly named in the active action's
   "Files referenced" block. Use line-range offsets when the action gives them.
4. Execute every checklist item in the active action IN ORDER.
5. After each code-mutating step, re-run:
      .venv/Scripts/python.exe -m pytest tests/ -q
   Result must be "934 passed, 1 skipped" (the baseline). Any regression → STOP.
6. Write the exit artifact EXACTLY as named in the action. The artifact is
   the contract — no verbal "done" in chat replaces it.
7. Stop at the action's exit gate. Do not start the next action.

HARD RULES (these override anything else the plan suggests):
- NEVER use `git add -A` or `git add .` — always list explicit file paths.
- NEVER run `git reset --hard`, `git push --force`, or `git clean -fd`
  without explicit user confirmation in chat.
- NEVER delete files flagged by vulture/pylint/rg without reaching the
  action's user-approval gate first.
- NEVER modify CLAUDE.md, docs/code_cleanup_plan.md, or docs/CHANGELOG.md
  unless the active action explicitly tells you to.
- If any command output is unexpected (extra files, missing tags, pytest
  count ≠ 934/1), STOP and report to the user. Record the anomaly in
  docs/phase4_option_c_plan.md §15 as a new dated entry. Do not try to
  "fix forward" without approval.
- Budget: ≤15k input tokens per action. If reading a file would exceed
  that, read only the line ranges the action names.

REPORTING: when the action's exit gate is reached, reply with exactly:
  - The action ID
  - The exit artifact path and its one-line summary
  - The pytest result from the final re-run
  - Any anomalies recorded in §15
Nothing else. No recap of what you read, no next-step suggestions.
```

**Filling the placeholders — decision table:**

| If the last completed artifact is… | `{{action_id}}` should be… | `{{last_artifact_path}}` should be… |
|---|---|---|
| `debug/4M_smoke_results.md` (with failures) | `4M-3` | `debug/4M_smoke_results.md` |
| `debug/4M_triage.md` | `4M-4` | `debug/4M_triage.md` |
| `debug/4M_app_stopped.md` or equivalent | `4N-cleanup-1` | `debug/4M_triage.md` |
| `debug/4N_verify.md` | `4O-1` | `debug/4N_verify.md` |
| `debug/4O_claudemd.patch` | `4O-2` | `debug/4O_claudemd.patch` |
| `debug/4O_planmd.patch` | `4O-3` | `debug/4O_planmd.patch` |
| `debug/4O_changelog.patch` | `4O-4` | `debug/4O_changelog.patch` |
| `debug/4O_commit.txt` | `4O-5` | `debug/4O_commit.txt` |

**Current resume point (as of 2026-04-11 evening):** `{{action_id}}` = `4M-3`, `{{last_artifact_path}}` = `debug/4M_smoke_results.md`. See §15 for execution-log context.

**Escalation triggers — when Sonnet should stop and hand back to Opus instead of continuing:**

1. Any action's exit gate fails and the fix is not obvious from the checklist.
2. Any unexpected file in `git status` that is not on the P3 baseline list.
3. Any pytest regression not covered by the action's rollback instruction.
4. Any vulture/pylint/rg output that does not match the "expected" line in the action.
5. Any 4M-3 triage entry where the regression-vs-pre-existing check is ambiguous (commits touched the file but the diff is non-trivial).
6. 4O-1 legacy-module check returning the "EXISTS but get_db_connection no longer matches" branch — the evidence-update wording is a judgment call and should escalate.
7. Any user instruction in chat that conflicts with the plan — Sonnet should relay the conflict, not resolve it.

**Do not escalate for:** clean pytest runs, matching baselines, expected-zero rg output, or mechanical commit-message composition. Those are the bulk of the remaining work and are exactly why Sonnet is cheaper here.

---

## 18. Post-4O Decision Tree — What Happens After Phase 4 Closes

> **Fresh agent entry point.** If you are reading this because `debug/4O_commit.txt` exists and `.pre-regen.bak` has been cleaned up (per 4O-5), Phase 4 is **closed**. This section tells you what to do next so you do not default to re-opening work that was deliberately deferred.
>
> **Why this section exists:** this was drafted after an Opus session ran out of tokens mid-conversation while walking the user through post-Phase-4 options. The content below is the full decision tree so a smaller model (or a fresh session of any model) can execute it without needing Opus to re-derive it.

### 18.1 State of the repo when you land here

After 4O-5 completes, the following is **true by construction** — do not re-verify unless something smells wrong:

- `spring-cleanup` branch has the full cleanup committed. Key commits: `12c90ac` (3a–3h rollup via 4A-Simple), `596acde` (4J orphan removal), plus a `4O` docs commit recorded in `debug/4O_commit.txt`.
- [CLAUDE.md](../CLAUDE.md) §8 `Verified Test Counts` reflects the post-cleanup baseline.
- [docs/code_cleanup_plan.md](code_cleanup_plan.md) Status Dashboard → Stage Tracker row for `Phase 4` is marked `Completed`.
- [docs/CHANGELOG.md](CHANGELOG.md) has the spring-cleanup entry.
- Rollback tag `phase4-rollback-point` has been deleted; `data/backup/database.db.pre-regen.bak` has been deleted.
- `debug/` directory is preserved as the audit trail — do not delete.

### 18.2 What is still open (ranked)

| # | Item | Source of record | State | Recommended ownership |
|---|---|---|---|---|
| 1 | Merge `spring-cleanup` → `main` | This plan | Ready to merge | User decision |
| 2 | 4M bugs (Weekly/Session counter toggle, Progression rendering) | `debug/4M_triage.md` | Deferred as "out of cycle" (Path A) OR already fixed (Path B) — check the triage file | New small plan if Path A |
| 3 | 3i bloated-function decomposition | [code_cleanup_plan.md](code_cleanup_plan.md) Stage Tracker | Deferred at **50–60%** confidence by the parent plan | Do NOT auto-resume |
| 4 | 3j export write-path optimization | [code_cleanup_plan.md](code_cleanup_plan.md) Stage Tracker | Deferred at **55–60%** confidence (missing characterization tests) | Do NOT auto-resume |
| 5 | [db_seed_fix_plan.md](db_seed_fix_plan.md) Phase F — `SEED_DB_PATH` retirement | db_seed_fix_plan.md | Deferred, architectural | User decision |
| 6 | `create_performance_indexes()` not in startup | [CLAUDE.md](../CLAUDE.md) Appendix C | Open question, no owner | User decision |

### 18.3 Hard rule: do NOT auto-resume code_cleanup_plan.md

**This is the main failure mode this section prevents.**

A fresh agent reading [code_cleanup_plan.md](code_cleanup_plan.md) might see `3i` and `3j` marked as "deferred" or "no-go" and interpret that as "to-do list." **It is not.** Both phases were explicitly rated below the parent plan's 95% confidence bar:

- **3i** — 50–60%: *"The phase is too broad; it bundles multiple unrelated high-blast-radius refactors. Must split into one-function sub-phases and only green-light them one at a time."*
- **3j** — 55–60%: *"Current change would alter write semantics without dedicated tests proving intended behavior. Add characterization tests, choose target semantics, and only then implement."*

**Un-deferring either phase requires a new breakdown plan** (in the same shape as this file), not a direct execution attempt. The breakdown plan must first satisfy the "What Must Happen To Reach ~95%" column of [code_cleanup_plan.md](code_cleanup_plan.md) §Confidence Recovery Plan. Skipping that and running the phases as written will regress the codebase.

### 18.4 Recommended next-move ranking

Execute in this order, stopping at the first one the user approves:

1. **Merge `spring-cleanup` → `main`.** Long-lived cleanup branches lose value the longer they sit. Confirm with the user, then standard PR or fast-forward merge. This is the baseline "Phase 4 is done" exit.
2. **Tackle the 4M bugs** (if any remain open per `debug/4M_triage.md`). The 2026-04-11 smoke run surfaced 3 failures — Weekly Summary counter toggle, Session Summary counter toggle, Progression rendering. If Path A was taken (pre-existing), they are now sitting as "out of cycle" tickets and are the **highest-leverage next work**: they affect the user directly and have been triaged already. Write a small bugfix plan per bug, do not bundle them.
3. **Write a 3i breakdown plan** — ONLY if the user specifically asks for function decomposition. Start by satisfying the "must split into one-function sub-phases" clause. Expect it to be ~10× the planning overhead of phase4_option_c itself.
4. **Execute db_seed_fix_plan.md Phase F** — `SEED_DB_PATH` retirement. Architectural simplification with no user-visible payoff. Defer unless the user specifically wants a single-source-of-truth for the constant.
5. **Write a 3j breakdown plan** — ONLY after the characterization tests for `routes/exports.py` write path exist. Lowest priority of the five.

### 18.5 Explicit anti-patterns

Do **not** do any of the following without explicit user instruction:

- Run `3i-a..3i-h` checklist items from [code_cleanup_plan.md](code_cleanup_plan.md) `[Phase 3i]` just because they are marked `[x]` — those marks are a known plan self-inconsistency that 4O-2 resolved by marking `3i` as deferred.
- Delete `debug/` to "clean up" — it is the audit trail for Phase 4 and is referenced by every exit artifact.
- Re-run 4M-2 manual smoke "just to double-check" — 4M is user-driven and Sonnet cannot execute it.
- Interpret open items in [CLAUDE.md](../CLAUDE.md) Appendix C "Unknowns & Resolved" as to-do items — they are noted uncertainties, not backlog.
- Revert any 3a–3h cleanup commit to "fix" a 4M bug without first confirming the bug is a regression per the §10 4M-3 regression-check block. Pre-existing bugs must be fixed forward, not by rolling back cleanup.

### 18.6 Reporting format when you land here

If you are a fresh agent and you have just read this section, your first reply to the user should be:

```
Phase 4 is closed per debug/4O_commit.txt at <hash>.

Remaining open items:
  1. Merge spring-cleanup → main (ready)
  2. 4M bugs: <N> open tickets from debug/4M_triage.md  (OR "resolved as regressions in <commit>")
  3. 3i/3j deferred (require new breakdown plans)
  4. db_seed Phase F deferred
  5. create_performance_indexes() open question

Recommended: merge spring-cleanup, then tackle 4M bugs.
Which would you like to start with?
```

Nothing else. Do not start work on any of the items without an explicit "go" from the user. The decision is the user's, not yours.

---
