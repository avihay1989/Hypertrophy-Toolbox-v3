# Phase 4.2 — Linux Visual Baselines (PLANNING)

> **Status:** COMPLETE (2026-06-06). Shipped via PR #48, #49, #50, and #51;
> final merge commit `04b9819`. Linux visual baselines are committed under
> `e2e/__screenshots__/linux/`; Windows baselines remain under
> `e2e/__screenshots__/win32/`. The visual job is manual-only in the Deep Gate,
> with `generate` and `compare` modes.
> **Author:** Claude Code session, 2026-06-06
> **Parent:** [`docs/CI_CD_IMPROVEMENT_PLAN.md`](../CI_CD_IMPROVEMENT_PLAN.md) §4.2 (Phase 4 manual deep gate).
> **Scope:** Stand up a Linux/Chromium visual-regression baseline set so
> `visual.spec.ts` + `visual-baseline-thumbnails.spec.ts` can run in the
> **manual deep gate only**. **Hard constraint (owner):** visual specs stay
> `workflow_dispatch`-only; they are **never** added to the required PR checks
> / branch protection.

---

## 0. Why this is its own phase

The original 66 committed PNGs under `e2e/__screenshots__/win32/` were rendered on
**Windows/Chromium**:

| Snapshot dir | Count | Source spec |
|---|---|---|
| `visual.spec.ts-snapshots/` | 48 | 8 pages × 3 viewports × 2 themes |
| `visual-baseline-thumbnails.spec.ts-snapshots/` | 18 | plan 3×2×2 (12) + log 3×2 (6) |

CI visual comparison runs on **ubuntu-24.04**. Cross-OS font hinting /
sub-pixel rasterization differs, so Windows baselines are not used on Linux
(CLAUDE.md §5; CI_CD plan §2.2). This phase produced the missing Linux baseline
set and wired a manual Deep Gate job to use it, without disturbing the owner's
local Windows visual workflow.

This phase is **isolated from the required PR gate by design.** Nothing here
touches `ci.yml`, the 8 required status checks, or branch protection. The only
shared-surface change is `snapshotPathTemplate` in `playwright.config.ts`, which
affects how *all* visual runs (local Windows + CI Linux) resolve snapshot paths —
covered in §3.

---

## 1. Rendering strategy: committed Linux PNGs vs pinned Docker render

Two ways to get reproducible Linux renders that match between the baseline-
generation run and the comparison run.

### Option A — Committed Linux PNGs (rendered on `ubuntu-24.04`)
Generate baselines by running `--update-snapshots` once on the GitHub
`ubuntu-24.04` runner, commit the resulting PNGs under a Linux-specific path,
and have the manual visual job compare against them on the same runner image.

- **Pro:** zero new infra — reuses the existing `setup-python` / `setup-node` /
  `npx playwright install --with-deps chromium` steps already in `deep-gate.yml`.
- **Pro:** generation and comparison run on the *same* GitHub-hosted image, so
  the renderer (Chromium build + bundled fonts + freetype) matches by
  construction as long as both runs use the same runner image + pinned
  Playwright version.
- **Pro:** human-in-the-loop review is natural — the owner downloads the
  generated PNGs as an artifact and commits them deliberately (no auto-push).
- **Con:** baselines are pinned to the `ubuntu-24.04` runner image. A runner
  image refresh or a Playwright bump can shift font rendering and require a
  re-baseline. Mitigated by §7 rollback + pinning Playwright; image refresh
  drift is the residual risk.
- **Con:** no local reproduction on the owner's Windows box — a Linux diff can
  only be reproduced in CI (or in Docker ad hoc).

### Option B — Pinned Docker render (`mcr.microsoft.com/playwright`)
Render inside the official Playwright Docker image pinned to an exact tag (e.g.
`mcr.microsoft.com/playwright:v1.xx.x-jammy`), both for generation and
comparison, so the rasterizer is identical regardless of host runner image.

- **Pro:** fully reproducible — same image renders identically in CI and on the
  owner's machine (`docker run` locally), insulated from `ubuntu-latest` drift.
- **Pro:** decouples the baseline from GitHub runner-image churn; only a
  deliberate image-tag bump can move pixels.
- **Con:** real added complexity for a single-user localhost app — a Docker
  layer in the workflow, image pull time (~1–2 min cold), and the app's Python
  venv + Flask server must be brought up *inside* or *alongside* the container
  (the webServer command currently shells a host `python`). Non-trivial rewire
  of how `playwright.config.ts` launches the Flask server.
- **Con:** the Playwright Docker image still must match the local Playwright npm
  version, so it does not remove version-pinning discipline — it adds an image
  pin on top of it.
- **Con:** higher maintenance surface than the problem warrants for a
  manual-only, owner-reviewed gate.

---

## 2. Recommended choice and rationale

**Recommendation: Option A — committed Linux PNGs rendered on `ubuntu-24.04`.**

Rationale:

1. **Matches the constraint.** This gate is manual-only and owner-reviewed. The
   value is "did this PR drift the UI unintentionally," answered by comparing
   against a Linux baseline a human approved. Docker's headline win — bit-exact
   reproduction across arbitrary hosts — is mostly wasted when both generation
   and comparison already run on the *same* GitHub image.
2. **Lowest infra cost.** Option A reuses the exact steps already proven in
   `deep-gate.yml`'s `full-e2e` job. No container plumbing, no Flask-in-Docker
   rewire, no second version-pin to keep in sync.
3. **Drift is a manageable, visible event, not a silent failure.** The realistic
   failure mode — an `ubuntu-24.04` image refresh shifting fonts — surfaces as
   a visual diff in a *manual* run the owner is already reading. The response
   is a deliberate re-baseline (§7), the same operation Option A uses for any
   intentional UI change. Docker trades this occasional, visible re-baseline
   for permanent standing complexity.
4. **Reversible.** If runner-image drift ever becomes frequent enough to
   annoy, upgrading Option A → Option B is incremental: pin the runner to the
   Docker image, regenerate, commit. The `{platform}` path split (§3) and the
   job shape (§5) are unchanged by that upgrade.

**Escalate to Docker only if** the council surfaces a concrete reason — e.g. the
owner wants to reproduce Linux diffs locally on Windows as a routine workflow,
or evidence that `ubuntu-24.04` font rendering is unstable enough that Option A
re-baselines would be frequent. Absent that, Option A.

> **Pin Playwright regardless of option.** Whichever path, the visual job must
> use the same Playwright version as `package.json` (it does — `npx` resolves the
> installed version) and that version should be a pinned exact version, not a
> caret range, so a transitive bump can't silently move pixels. Verify
> `package.json` pins `@playwright/test` exactly as part of this phase.

---

## 3. `snapshotPathTemplate` change + how existing Windows baselines move

### 3.1 The template change
Today ([playwright.config.ts:57](../../playwright.config.ts#L57)):

```ts
snapshotPathTemplate: '{testDir}/__screenshots__/{testFilePath}-snapshots/{arg}{ext}',
```

This strips Playwright's default platform token, so the Windows PNGs carry no
platform marker and a Linux run would overwrite/diff them in place. Add a
`{platform}` **directory segment**:

```ts
snapshotPathTemplate: '{testDir}/__screenshots__/{platform}/{testFilePath}-snapshots/{arg}{ext}',
```

`{platform}` resolves to `process.platform` — `win32` on the owner's box,
`linux` on CI. After this change:

- Owner's local Windows visual run → `e2e/__screenshots__/win32/visual.spec.ts-snapshots/…`
- CI Linux visual run → `e2e/__screenshots__/linux/visual.spec.ts-snapshots/…`

The two baseline sets never collide and never overwrite each other.

> **Why a directory segment, not a `-{platform}` filename suffix.** Both are
> valid Playwright tokens. The directory form makes the migration two `git mv`s
> of whole directories (below) instead of renaming 66 individual files, keeps
> each platform's set self-contained, and reads cleanly in `git status`.

### 3.2 Moving the existing Windows baselines — same commit as the template change
This is an **invariant**: the template edit and the move must land together, or
the owner's next local visual run breaks (Playwright would look under `win32/`
and find nothing). Move the two existing dirs under a new `win32/` segment:

```bash
mkdir -p e2e/__screenshots__/win32
git mv e2e/__screenshots__/visual.spec.ts-snapshots \
       e2e/__screenshots__/win32/visual.spec.ts-snapshots
git mv e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots \
       e2e/__screenshots__/win32/visual-baseline-thumbnails.spec.ts-snapshots
```

Result: 66 PNGs relocated under `win32/`, content unchanged (a pure rename, so
no pixels move — local Windows visual runs stay green). The `linux/` tree is
created later by the generation workflow (§4), reviewed, and committed
separately.

> **`.gitignore` note:** `e2e/__screenshots__/**` is already tracked (only
> `e2e/fixtures/database.visual.seed.db` needed an explicit whitelist line). The
> new `linux/` PNGs commit with no `.gitignore` change.

### 3.3 Verify the move locally before pushing
```bash
# Should re-resolve to win32/ and pass with zero diffs (pure rename):
npx playwright test e2e/visual.spec.ts e2e/visual-baseline-thumbnails.spec.ts --project=chromium
```

---

## 4. Exact baseline-generation workflow in CI

Baselines are generated by a **manual** run that produces an artifact the owner
downloads and commits — CI never pushes to `main` (branch-protected; keeps the
human review of every pixel change).

A dedicated job in `deep-gate.yml`, selected by a `workflow_dispatch` input
`visual_mode` ∈ {`compare`, `generate`} (default `compare`). The `generate`
path:

1. `actions/checkout@v4`
2. `actions/setup-python@v5` (3.11, pip cache) + install `requirements.txt`,
   **create the `.venv`** the config expects (see §4.1).
3. `actions/setup-node@v4` (20, npm cache) + `npm ci`
4. `npm run build:css` (visual specs need the built bundle)
5. `npx playwright install --with-deps chromium`
6. **Seed the visual DB** (§4.2 preflight) — both specs need full visual seed
   data (plan rows + `media_path` thumbnails), not the user-state-wiped E2E seed.
7. Run **only** the two visual specs with `--update-snapshots`:
   ```bash
   npx playwright test --project=chromium \
     e2e/visual.spec.ts e2e/visual-baseline-thumbnails.spec.ts \
     --update-snapshots
   ```
   With the §3 template, this writes PNGs under `e2e/__screenshots__/linux/…`.
8. **Upload** `e2e/__screenshots__/linux/**` as artifact `visual-baselines-linux`
   (§5). The owner downloads, unzips into the repo, eyeballs the renders, and
   commits them. The first commit establishes the Linux baseline; thereafter
   `generate` is only re-run for intentional UI changes or runner-drift
   re-baselines (§7).

### 4.1 venv requirement
`playwright.config.ts` prefers `.venv/bin/python` and falls back to `python` if
absent ([playwright.config.ts:5-8](../../playwright.config.ts#L5-L8)). The
deep-gate jobs today install into the system Python and have no `.venv`, so the
fallback `python` is used — fine. The visual job follows the same pattern (no
`.venv` needed); just confirm `python` on PATH has the deps. **Decision:** do
not create a `.venv` in CI; rely on the documented fallback, matching the
existing `full-e2e` job.

### 4.2 Pinning note
The `generate` and `compare` jobs **must** run on the same runner image label
(`ubuntu-24.04`) and the same pinned Playwright version, or the comparison will
diff against a baseline rendered by a different rasterizer. Document this
coupling in a comment in `deep-gate.yml` next to the visual job.

---

## 5. Visual DB preflight for `visual-baseline-thumbnails.spec.ts`

> **⚠️ SUPERSEDED by §10.3 (council).** The per-spec `beforeAll` re-seed below
> is replaced in Plan v2 by seeding the visual DB once in the webServer command
> (before Flask opens it). Three reviewers independently flagged the `beforeAll`
> approach: the CI fallback is inoperative (`PW_REUSE_SERVER` is force-disabled
> under `CI`), two specs re-seeding one open DB is a race, and the
> `?? data/database.db` fallback can clobber the owner's live DB. Read §10.3
> before implementing. The analysis below is retained for rationale.

This is the sharp edge. The two visual specs have **different** DB-seeding
behavior:

- `visual.spec.ts` **self-seeds**: its `test.beforeAll`
  ([visual.spec.ts:32-43](../../e2e/visual.spec.ts#L32-L43)) runs
  `e2e/scripts/prepare_visual_db.py --output $DB_FILE`, snapshotting the full
  committed visual seed (`e2e/fixtures/database.visual.seed.db`) and applying
  migrations. It does not depend on the webServer's seed.
- `visual-baseline-thumbnails.spec.ts` has **no preflight**. It asserts on plan
  rows with `media_path` thumbnails (`img.exercise-thumbnail`, ≥4 rows). The
  default webServer seed (`prepare_e2e_db.py`) **wipes all user-state** including
  the plan, so under the standard E2E seed this spec has no rows and fails.

**Fix (chosen): add a `test.beforeAll` to `visual-baseline-thumbnails.spec.ts`
mirroring `visual.spec.ts`.** It re-seeds `DB_FILE` with the full visual seed
(plan + media) via `prepare_visual_db.py` before its screenshots:

```ts
test.beforeAll(() => {
  const venvPython = process.platform === 'win32'
    ? path.join(process.cwd(), '.venv', 'Scripts', 'python.exe')
    : path.join(process.cwd(), '.venv', 'bin', 'python');
  const pythonExecutable = fs.existsSync(venvPython) ? venvPython : 'python';
  const databasePath = process.env.DB_FILE ?? path.join(process.cwd(), 'data', 'database.db');
  execFileSync(pythonExecutable, ['e2e/scripts/prepare_visual_db.py', '--output', databasePath], { stdio: 'ignore' });
});
```

Rationale for this over alternatives:
- **vs. relying on spec ordering** (letting `visual.spec.ts`'s beforeAll seed for
  both): fragile — cross-file order isn't guaranteed, and the thumbnails spec
  would silently depend on another file running first.
- **vs. a job-level seed step + `PW_REUSE_SERVER=1`**: also works, but couples the
  workflow YAML to the spec's data needs. A self-contained `beforeAll` keeps the
  spec runnable in isolation (locally and in CI), matching `visual.spec.ts`.

> **Open verification item:** `prepare_visual_db.py` rewrites `DB_FILE` while the
> Flask webServer holds it open. `visual.spec.ts` already does this and works
> locally on Windows, but it is **untested on ubuntu under a running server**
> (the visual specs have never run in CI). The first `generate` run is the proof
> point — if SQLite file replacement under the open server misbehaves on Linux,
> fall back to the job-level seed + `PW_REUSE_SERVER=1` approach. Flag this in
> the acceptance run.

---

## 6. Manual workflow job shape + artifact upload paths

Add one job to the existing `deep-gate.yml` (manual `workflow_dispatch`), gated
on an input so a normal deep-gate run does not pay the visual cost unless asked.

```yaml
on:
  workflow_dispatch:
    inputs:
      run_visual:
        description: 'Run the Linux visual job'
        type: boolean
        default: false
      visual_mode:
        description: 'compare against committed Linux baselines, or generate new ones'
        type: choice
        options: [compare, generate]
        default: compare

jobs:
  # ... existing full-e2e / cold-start / old-db-migration / dependency-health ...

  visual-linux:
    name: Visual regression (Linux baselines)
    if: ${{ inputs.run_visual }}
    runs-on: ubuntu-24.04           # PINNED (not ubuntu-latest) per §10.2 — a runner-image
                                     # promotion must not silently move fonts. MUST match the
                                     # image used to generate the committed baselines.
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: 'pip' }
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run build:css
      - run: npx playwright install --with-deps chromium

      - name: Run visual specs
        run: |
          MODE="${{ inputs.visual_mode }}"
          UPDATE=""; [ "$MODE" = "generate" ] && UPDATE="--update-snapshots"
          npx playwright test --project=chromium \
            e2e/visual.spec.ts e2e/visual-baseline-thumbnails.spec.ts $UPDATE

      # generate → upload the freshly rendered Linux baselines for owner review+commit
      - name: Upload generated Linux baselines
        if: ${{ inputs.visual_mode == 'generate' }}
        uses: actions/upload-artifact@v4
        with:
          name: visual-baselines-linux
          path: e2e/__screenshots__/linux/**
          retention-days: 14

      # compare (or generate) failure → upload report + diff images for triage
      - name: Upload Playwright report + diffs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: visual-linux-report
          path: artifacts/playwright
          retention-days: 7
```

Artifact upload paths:
- `e2e/__screenshots__/linux/**` → `visual-baselines-linux` (generate mode; the
  artifact the owner commits).
- `artifacts/playwright` → `visual-linux-report` (on failure; HTML report +
  `test-results` actual/expected/diff PNGs from `outputDir`, per
  [playwright.config.ts:56](../../playwright.config.ts#L56)).

**Privacy:** safe by the same reasoning as the existing E2E artifact contract
(`e2e/CLAUDE.md`) — visual specs run only against the committed
`database.visual.seed.db` (catalog + a synthetic plan), never the owner's live
`data/database.db` or `data/auto_backup/`.

Why a separate job + `run_visual` input rather than adding the visual specs to
`full-e2e`: `full-e2e` deliberately excludes visual (`grep -vE 'visual'`). Keeping
visual in its own opt-in job preserves a fast default deep-gate run and keeps the
generate/compare mode switch local to one job.

---

## 7. Acceptance criteria

The phase is done when **all** hold:

1. `snapshotPathTemplate` includes the `{platform}` directory segment; the 66
   existing PNGs are relocated under `e2e/__screenshots__/win32/` via `git mv`
   (pure rename) in the **same commit**.
2. A local Windows run of both visual specs passes with **zero new diffs** after
   the move (proves the rename didn't disturb the owner's baselines).
3. `visual-baseline-thumbnails.spec.ts` has a `beforeAll` visual-DB preflight; it
   renders ≥4 plan rows with `media_path` thumbnails when run in isolation
   against a freshly seeded `DB_FILE`.
4. A manual `deep-gate.yml` run with `run_visual=true, visual_mode=generate`
   produces a `visual-baselines-linux` artifact containing **66 PNGs** under
   `linux/` (48 + 18), and the renders are visually correct on inspection (no
   missing thumbnails, correct themes/viewports).
5. After the owner commits the `linux/` baselines, a manual run with
   `run_visual=true, visual_mode=compare` passes **green** against them on
   `ubuntu-24.04`.
6. A deliberate, trivial CSS change makes the `compare` run **fail** with a diff
   artifact (proves the gate actually detects drift) — then revert.
7. **No change to `ci.yml`, the 8 required status checks, or branch protection.**
   `deep-gate.yml` remains `workflow_dispatch`-only with no `schedule`/`cron`.
8. `e2e/CLAUDE.md` CI-inclusion contract updated: visual specs move from
   "excluded (Phase 4)" to "manual deep gate — Linux baselines, `run_visual`
   input"; document the `{platform}` split and the dual-baseline maintenance note.

---

## 8. Risks and rollback plan

| Risk | Likelihood | Mitigation |
|---|---|---|
| `prepare_visual_db.py` rewriting `DB_FILE` under the running Flask server misbehaves on Linux (untested) | Medium | First `generate` run is the proof point (§5). Fallback: job-level seed step + `PW_REUSE_SERVER=1` so the server opens an already-seeded visual DB. |
| `ubuntu-24.04` image refresh shifts font rendering → `compare` reds with no code change | Medium (over time) | Re-baseline via `generate` (the same operation as an intentional UI change). It's a *manual* gate, so a human reads the diff and decides. If frequent, escalate to Option B (Docker pin) — the `{platform}` split makes that a drop-in. |
| Template change breaks the owner's local Windows visual run | Low | The move + template edit land in one commit; acceptance criterion #2 verifies zero local diffs before push. |
| Visual job accidentally treated as a required check | Low | `if: ${{ inputs.run_visual }}` + `workflow_dispatch`-only; acceptance #7 asserts no `ci.yml`/branch-protection change. A non-required job cannot block merge. |
| Playwright version drift between generate and compare moves pixels | Low | Pin `@playwright/test` exactly in `package.json`; both modes use the same installed version (§2, §4.2). |
| Linux baselines bloat the repo (66 PNGs added) | Low | Table-scoped thumbnail shots + full-page visual shots are already the committed Windows size class; Linux set is comparable. Acceptable for a tracked baseline. |

### Rollback
This phase is **additive and isolated** — rollback is clean at any stage:

1. **Before committing Linux baselines:** revert the `snapshotPathTemplate` edit
   and the two `git mv`s (single commit) → back to the exact current state;
   `deep-gate.yml` visual job is inert (`run_visual` defaults false) or removed.
2. **After committing Linux baselines:** if the gate proves noisy, delete
   `e2e/__screenshots__/linux/` and set the `visual-linux` job's `if:` to `false`
   (or drop the job). The `win32/` baselines and local Windows workflow are
   untouched throughout. No required check ever depended on this, so there is no
   merge-path impact to unwind.
3. **Full revert:** `git revert` the phase commit(s). Because nothing here is a
   required status check and the only shared edit is the path template (which
   moves cleanly back via the same `git mv` in reverse), revert is risk-free.

---

## 9. Next step

Per `CI_CD_IMPROVEMENT_PLAN.md` §8 process note, run `/council-plan` on this doc
before implementation — specifically to pressure-test the **Option A vs Option B**
decision (§1–§2) and the **DB-preflight-under-running-server** risk (§5). If the
council finds no strong reason for Docker, proceed with Option A as written.

---

## 10. Council review (2026-06-06) → Plan v2

Three reviewers (architecture / test-strategist / product-risk) reviewed Plan v1
cold. **Verdict: needs revision — Option A confirmed, no Docker.**

### 10.0 Docker decision — settled

**All three reviewers independently affirmed Option A (committed Linux PNGs on a
pinned ubuntu runner). None surfaced a concrete reason for Docker (Option B).**
The owner's standing directive ("proceed with Option A unless the council finds a
concrete reason for Docker") is therefore satisfied → **proceed with Option A.**
The only Option-A hardening the council added is pinning the runner image
(§10.2), which is cheaper than Docker and addresses the same drift concern.

### 10.1 Response matrix

| # | Finding | Reviewer | Sev | Disposition | Action in v2 |
|---|---|---|---|---|---|
| 1 | `PW_REUSE_SERVER=1` fallback is inoperative on CI (`playwright.config.ts:9` disables reuse when `CI` set) — the named escape hatch is a dead end | test-strategist | **blocking** | **accept** | Redesign: seed visual DB in the webServer command before Flask opens it (§10.3). Fallback removed entirely. |
| 2 | `?? data/database.db` fallback in the spec `beforeAll` deletes-and-overwrites the owner's live DB when `DB_FILE` is unset in a local isolation run (the exact run §3.3 / acceptance #3 instruct) | product-risk | **high** | **accept** | Redesign (§10.3) removes the per-spec `beforeAll`, eliminating the clobber vector. Also **remove the existing `visual.spec.ts` beforeAll** (same latent hole) and add a hard guard in `prepare_visual_db.py` refusing to `--output` the live DB. |
| 3 | Two visual specs re-seeding the same open `DB_FILE` mid-run is a race (file replacement + WAL coherence under an open server) | test-strategist / arch | **high** | **accept** | Redesign (§10.3): seed once outside both specs; no per-spec reseed → race gone. |
| 4 | Thumbnails `beforeAll` snippet omits the `node:` imports → won't compile → fails the **blocking** required `tsc` check | architecture | **high** | **accept (moot)** | Redesign (§10.3) drops the `beforeAll` snippet entirely, so the import gap disappears. |
| 5 | `visual-baseline-thumbnails.spec.ts` lacks the determinism harness (`installDeterminism`/`prepareForScreenshot`) — no frozen clock, no `fonts.ready`, no scrollbar/animation suppression. Dominant Linux-flakiness source | test-strategist | **high** | **accept** | New **PR-2**: refactor thumbnails to share the harness from `visual-helpers.ts`. **This changes pixels on Windows too → re-baseline the 18 win32 thumbnails (owner `--update-snapshots`, reviewed) in the same PR.** |
| 6 | Deterministic Chromium args are necessary but not sufficient — CLAUDE.md §5 shows 10 sub-pixel drifts on Windows *with* these args. "Match by construction" proves round-trip, not run-to-run stability | test-strategist | **high** | **accept** | Acceptance: run `compare` **twice back-to-back, green both times** before trusting the gate (proves stability, not luck). |
| 7 | `prepare_visual_db.py` migration set is stale vs `app.py` startup — missing the learned-calibration tables that `prepare_e2e_db.py` ensures. Latent 500 if a visual page ever touches them; now load-bearing once baselines freeze | architecture / test-strategist | **medium** | **accept** | PR-2: add the calibration table creators to `prepare_visual_db.py` so the visual seed matches `app.py` startup. Reconcile as a pre-generate check, not a post-hoc eyeball. |
| 8 | PR-(a) bundles the required-path spec edit + 66-file relocation + shared config + workflow job — four blast radii; the irreversible-feeling rename mixed with a `tsc`-checked edit | architecture | **medium** | **accept** | Re-cut PR boundaries (§10.4). PR-1 = pure rename only. |
| 9 | Acceptance "zero new diffs after move" / "66 PNGs" is weak — assert a true `git mv` rename (R100, no content delta) + a **filename manifest**, not a bare count; assert the on-disk count is actually 48 and 18 before the move | test-strategist / arch | **medium** | **accept** | Strengthen acceptance #2/#4 (§10.5). |
| 10 | Pin `runs-on: ubuntu-24.04` (not floating `ubuntu-latest`) so a GitHub image promotion can't silently red the gate; Playwright is *already* exact-pinned (`@playwright/test 1.60.0`) so that v1 "verify" item is a no-op | test-strategist | **low** | **accept** | §10.2: pin runner (edited into §6). Drop the redundant "pin Playwright" task. |
| 11 | Prove the Linux seeding works **on-branch** (throwaway `workflow_dispatch` generate run) before merging, not for the first time on `main` | test-strategist | **low** | **accept** | PR-3 includes an on-branch generate run as a merge precondition (§10.4). |
| 12 | Confirm the new `win32/`/`linux/` path segments aren't caught by any `.gitignore` negation before relying on tracking | architecture | **low** | **accept** | Add `git check-ignore` preflight to acceptance. |
| 13 | Source-side: `prepare_visual_db.py` `DEFAULT_SOURCE` falls back to `data/database.db` if the committed seed is absent → could render real data into an artifact | product-risk | **low** | **accept** | Assert the committed `database.visual.seed.db` exists before any `generate` run (fail fast). |
| 14 | Owner's local-workflow docs (`/verify-suite`, `/run-e2e` skills, `.claude/rules/testing.md`, `docs/E2E_TESTING.md`) reference the flat `__screenshots__/…` path — stale after the `{platform}` move | product-risk | **low** | **accept** | Extend acceptance #8: grep `.claude/**` + those docs for `__screenshots__` and update to the `{platform}` form. |
| 15 | Branch-protection isolation holds: only `deep-gate.yml` + `playwright.config.ts` change, the `visual-linux` job is `if:`-gated + `workflow_dispatch`-only, no required job `name:` renamed → §5 re-PUT invariant not triggered | architecture | — | **confirmed** | No change — verified clean. |
| 16 | Non-goals respected (no cloud / telemetry / cron); artifacts go to standard GitHub Actions storage; `workflow_dispatch`-only intent holds throughout | product-risk | — | **confirmed** | No change. |

No findings rejected. No findings deferred.

### 10.2 v2 change — pin the runner image
`runs-on: ubuntu-24.04` for the `visual-linux` job (both generate and compare),
already edited into §6. Re-baseline cadence is now tied to a deliberate runner
bump, not a silent `ubuntu-latest` promotion. This is the council's accepted
substitute for Docker's reproducibility — far cheaper, same drift protection for
a same-image generate/compare pair.

### 10.3 v2 change — seed the visual DB in the webServer command (replaces §5)
**This is the central v2 redesign.** Instead of a per-spec `beforeAll` rewriting
`DB_FILE` under a running server, the visual job tells the webServer to seed
visual data *before* Flask launches — the same pattern the functional suite
already uses (`prepare_e2e_db.py && python app.py`), just pointed at the visual
seeder.

`playwright.config.ts` selects the seed script by env:

```ts
const visualSeed = process.env.PW_VISUAL_SEED === '1';
const seedScript = visualSeed ? 'prepare_visual_db.py' : 'prepare_e2e_db.py';
const seedDbCommand = `${pythonExecutable} ${path.join('e2e', 'scripts', seedScript)} --output "${e2eDbPath}"`;
```

The `visual-linux` job sets `PW_VISUAL_SEED=1`. Consequences:
- The server opens an already-correct visual DB (plan rows + `media_path`
  thumbnails preserved — `prepare_visual_db.py` does **not** wipe user-state,
  unlike `prepare_e2e_db.py`). The thumbnails spec gets its rows with no preflight.
- **No spec rewrites `DB_FILE` at runtime** → the cross-spec race (finding 3) and
  the CI-fallback dead end (finding 1) both vanish.
- **The `?? data/database.db` clobber vector (finding 2) is removed** — `DB_FILE`
  is set by the webServer env block to the throwaway `artifacts/e2e/database.e2e.db`,
  and no spec process reads it for a `--output` default. **Remove the existing
  `visual.spec.ts` `beforeAll` (lines 32-43)** as part of this — it is now
  redundant and carries the same latent hole.
- Defense-in-depth: add a guard in `prepare_visual_db.py` that **refuses to
  `--output` a path resolving to the live `data/database.db`** (or inside
  `data/auto_backup/`) unless an explicit `--force`, so the seeder can never
  clobber real data regardless of caller.

Invariant: the `visual-linux` job runs **only** the two visual specs; it must
never interleave with functional specs in one server process (their seeds are
incompatible).

### 10.4 v2 change — revised PR split (4 PRs, was 3)
The v1 3-PR split mixed a `tsc`-checked spec edit and the 66-file relocation into
one PR, and the determinism-harness refactor (finding 5) forces a Windows
re-baseline that must be isolated. Re-cut:

- **PR-1 — path template + win32 relocation (pure rename).** `snapshotPathTemplate`
  `{platform}` segment + the two `git mv`s into `win32/`. **Zero pixel change**,
  atomic, trivially revertible. Nothing else rides along.
- **PR-2 — make the visual specs Linux-ready (Windows-verifiable, no CI gate yet).**
  (a) Thumbnails determinism-harness refactor sharing `visual-helpers.ts` **+
  Windows re-baseline of the 18 thumbnail PNGs** (owner `--update-snapshots`,
  reviewed); (b) `prepare_visual_db.py` schema parity (add calibration tables) +
  the live-DB `--output` guard; (c) the `PW_VISUAL_SEED` webServer-seed switch in
  `playwright.config.ts` + **removal of the `visual.spec.ts` beforeAll**. All
  behavior is verifiable on the owner's Windows box.
- **PR-3 — wire the manual job + docs.** The `visual-linux` job (generate/compare
  modes, `if:`-gated, `ubuntu-24.04`) + `e2e/CLAUDE.md` CI-contract update + the
  stale-path doc sweep (finding 14). **Merge precondition:** a throwaway on-branch
  `workflow_dispatch` generate run proves Linux seeding + rendering before merge
  (finding 11). No Linux baselines committed yet, so `compare` would no-op/fail —
  fine, the job is manual.
- **PR-4 — commit baselines + validate.** Commit the reviewed `linux/` PNGs from
  the generate artifact, then run `compare` **twice back-to-back** (finding 6) —
  green both times. Then a throwaway CSS tweak must turn `compare` red (drift
  detection), reverted.

The owner may collapse PR-3/PR-4 if the on-branch generate in PR-3 already
produced a trusted artifact; kept separate here so committing pixels is its own
reviewable step.

### 10.5 v2 change — strengthened acceptance criteria
Supersedes §7; additions/replacements:
- **#2 (rename) — CORRECTED (owner, 2026-06-06):** the move is verified as a pure
  rename, **not** by a blanket "66 passed, 0 failed" local run. `main` already
  carries the documented 10 desktop sub-pixel reds (CLAUDE.md §5), so demanding a
  fully-green local run is wrong. The rename is accepted when **all** hold:
  - snapshot paths resolve to `win32/` correctly (the template change + `git mv`),
  - `git status` shows the move as `R100` (pure rename, no pixel/content delta),
  - every moved snapshot that is **not** a documented known-red still passes,
  - any remaining local visual reds **exactly match the documented pre-existing
    baseline** (the 10 desktop sub-pixel drifts) — no new reds.
- **#3 (preflight):** dropped — replaced by "the `visual-linux` job seeds via
  `PW_VISUAL_SEED=1` and the thumbnails spec renders ≥4 plan rows with no per-spec
  `beforeAll`."
- **#4 (manifest):** the `visual-baselines-linux` artifact matches an explicit
  **66-filename manifest** (48 + 18), not just a count; assert the on-disk win32
  set is exactly 48 and 18 before the move.
- **#5 (stability):** `compare` is green on **two** consecutive runs, not one.
- **New #9:** `git check-ignore e2e/__screenshots__/linux/x.png` returns nothing
  (segment is tracked); committed `database.visual.seed.db` present before any
  generate run; `prepare_visual_db.py` refuses to `--output` the live DB.
- **New #10:** no `__screenshots__` path references remain stale in `.claude/**`
  skills, `.claude/rules/testing.md`, or `docs/E2E_TESTING.md`.

### 10.6 Sign-off checklist
- [x] Every council finding has a disposition (16 findings; 14 accepted, 2
  confirmed-clean, 0 rejected, 0 deferred).
- [x] **User approves Plan v2** (Option A, the §10.3 webServer-seed redesign, and
  the 4-PR split). Approved 2026-06-06.
- [x] Complete — PR #48, #49, #50, and #51 shipped (§12).

---

## 11. PR-2 implementation record (2026-06-06)

PR-2 = "make the visual specs Linux-ready" (§10.4). Implemented on `main` working
tree; one PR.

### 11.1 Discovered fixture defect (root cause, not in Plan v1/v2)
Plan v1/v2 §4.6/§10.3 assumed `prepare_visual_db.py` seeds **"plan rows +
media_path thumbnails"**. That premise was **false for the committed fixture.**
The first `PW_VISUAL_SEED=1` thumbnails run timed out on
`waitForSelector('#workout_plan_table_body tr')` — the committed
`e2e/fixtures/database.visual.seed.db` had **0 `user_selection` rows and no
`media_path` column.**

Root cause (git-confirmed): the 18 thumbnail baselines were generated in
`b5b8c7a` (workout.cool §4.6) against a then-populated DB; commit `de89c89`
(2026-04-29) "refresh visual seed" emptied the plan from the fixture and
`media_path` is only *added* (empty) by migrations, never *populated* by them.
So the thumbnails spec had been un-runnable against the seed ever since (matches
its "did-not-run" status in CLAUDE.md §5). `visual.spec.ts` was unaffected — its
old `beforeAll` ran the same empty-plan `prepare_visual_db.py`, so its baselines
were always *empty-state* renders.

**Owner decision:** regenerate **one canonical populated visual seed** (not a
separate empty-vs-populated split). Rationale: the seed should represent a real
populated app; separate seeds would make the suite less honest.

### 11.2 What PR-2 ships
- **`e2e/scripts/build_visual_seed.py`** (new) — regenerates the committed
  fixture from a **throwaway** DB (never `data/database.db`): full catalog +
  `media_path` applied from the reviewed `data/free_exercise_db_mapping.csv`
  (filtered to mappings whose exercise exists in this seed's catalog) + a small
  deterministic 6-exercise plan (`GYM - Full Body - Workout A`) and matching
  `workout_log` rows (3 scored, 3 planned-only), fixed timestamps for byte
  stability.
- **`e2e/fixtures/database.visual.seed.db`** (regenerated) — now 6 plan rows, 6
  log rows, 108 media-mapped exercises.
- **`prepare_visual_db.py`** — `apply_migrations` mirrors `app.py` startup exactly
  (adds `add_strength_calibration_tables()`, schema parity, council finding #7);
  new `assert_safe_output()` + `--force` refuses `--output` of `data/database.db`
  or `data/auto_backup/*` (finding #2/#13).
- **`prepare_e2e_db.py`** — dropped the now-redundant `_ensure_calibration_tables`
  (parity covers it); shares the live-DB guard.
- **`playwright.config.ts`** — `PW_VISUAL_SEED=1` selects `prepare_visual_db.py`
  in the webServer command (plan-bearing); default keeps the functional suite on
  `prepare_e2e_db.py` (§10.3). No runtime DB rewrite.
- **`visual.spec.ts`** — removed the runtime `beforeAll` DB rewrite + dead imports.
- **`visual-baseline-thumbnails.spec.ts`** + **`visual-helpers.ts`** — thumbnails
  share `installDeterminism` / `prepareForScreenshot` + new
  `elementScreenshotOptions()` (finding #5).

### 11.3 Windows re-baseline scope (broader than originally scoped)
Adding plan+log data to the **shared** seed repopulates every data-driven page,
not just plan/log (owner pre-approved the broader scope). A full compare run
(`PW_VISUAL_SEED=1`) produced **30 fails / 18 pass**, categorized exactly:

**Re-baselined — 42 PNGs (caused by the harness and/or the populated seed):**
- `visual-baseline-thumbnails`: all **18** (determinism harness + populated plan/log).
- `visual/workout-plan-*`: 6 (plan data).
- `visual/workout-log-*`: 6 (log data).
- `visual/weekly-summary-*`: 6 (plan-derived volume).
- `visual/session-summary-*`: 6 (plan+log).

**Left untouched — 6 PNGs (pre-existing documented desktop sub-pixel reds, NOT
caused by this change):**
- `visual/welcome-desktop-{light,dark}` — welcome reads no plan data.
- `visual/volume-splitter-desktop-{light,dark}` — reads no plan data.
- `visual/progression-desktop-{light,dark}` — **progression mobile/tablet passed**,
  proving the log data did *not* alter progression rendering; its only fails are
  the pre-existing sub-pixel desktop reds.

These 6 are a **subset of the documented 10 desktop sub-pixel reds** (the other 4 —
workout-plan-desktop ×2, workout-log-desktop ×2 — were legitimately re-baselined
as part of the data set). **No page outside the approved data-driven set changed.**
Confirmation compare after re-baseline: visual.spec data set **24 passed**,
thumbnails **18 passed**, `tsc --noEmit` clean, functional smoke (default seed)
**10 passed**.

### 11.4 Completed by PR-3/PR-4
The `deep-gate.yml` `visual-linux` job, `e2e/CLAUDE.md` CI-contract update, the
stale-`__screenshots__`-path doc sweep, and committing the Linux baselines were
completed by PR #50 and PR #51. Neither PR touched `ci.yml`, required checks, or
branch protection.

---

## 12. Final closeout (2026-06-06)

Phase 4.2 is fully shipped.

| PR | Merge commit | Result |
|---|---|---|
| #48 | `728fb65` | Added the `{platform}` snapshot path segment and relocated the 66 Windows baselines to `e2e/__screenshots__/win32/` as pure renames. |
| #49 | `7774227` | Made visual specs Linux-ready: canonical populated visual seed, determinism harness, schema parity, live-DB guard, `PW_VISUAL_SEED`, and Windows re-baseline for affected snapshots. |
| #50 | `b1d7a29` | Wired the manual `visual-linux` Deep Gate job and updated the E2E contract/docs. On-branch `generate` mode produced the expected Linux artifact. |
| #51 | `04b9819` | Committed the reviewed 66 Linux PNG baselines under `e2e/__screenshots__/linux/` and validated compare/drift behavior. |

Final verification:
- The PR #50 generate artifact contained exactly **66** non-empty Linux PNGs:
  48 `visual.spec.ts` baselines and 18 `visual-baseline-thumbnails.spec.ts`
  baselines, with filenames mirroring the `win32/` set.
- PR #51 committed exactly those 66 Linux PNGs and no docs/workflow/test/data
  files.
- Linux visual compare passed in two successful Deep Gate runs on the PR branch:
  run `27066624168` and run `27066890745`.
- Deliberate drift detection was proven in run `27067019708`: a temporary CSS
  change made the `Visual regression (Linux baselines)` job fail and uploaded
  `visual-linux-report`; the temporary change was fully reverted before merge.
- The post-merge `main` CI run for PR #51 passed (`27067538178`).

Constraints confirmed:
- `ci.yml`, the 8 required checks, and branch protection were not changed.
- `data/database.db` was not committed.
- `win32/` baselines were not changed in PR #51.
- Visual specs remain `workflow_dispatch`-only and opt-in via the Deep Gate
  inputs.

Known follow-up:
- One manual-deep full-E2E run during PR #51 exposed an unrelated
  `accessibility.spec.ts:283` focus-return flake. It is not caused by the
  PNG-only PR #51 and did not block Phase 4.2, but it should be investigated
  separately to keep the manual Deep Gate trustworthy.

*End of Plan v2 + implementation record.*
