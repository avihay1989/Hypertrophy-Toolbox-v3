# Plan Review — CI/CD Phase 5: branch protection on `main`

*Council-plan for Phase 5 of [`docs/CI_CD_IMPROVEMENT_PLAN.md`](../CI_CD_IMPROVEMENT_PLAN.md). Phases 0 (#40), 2.1 (#41), 1 (#42), 3 (#43), tsc fast-follow (#44) shipped. This phase enforces the gate.*

---

## Plan v1

**Goal**: Make the now-trustworthy gate actually gate — enable GitHub branch protection on `main` so every change lands via a PR with the required checks green, turning "the checks exist" into "the checks are enforced." `main` IS production for this local-first app (plan §0), so protection is the whole point of the preceding phases.

**Grounding (measured 2026-06-06)**
- Repo: **PUBLIC**, default branch `main`, viewer permission **ADMIN**. `main` currently has **no protection** (`404 Branch not protected`).
- Single-user repo (owner = sole committer). **Critical trap:** GitHub does not let you approve your own PR, so *requiring approving reviews would lock the solo owner out* unless every merge uses an admin override. → required approving reviews must be **0**.
- The 9 check names CI produces (job `name:` values):
  | Check | Job | Required? (proposed) | Why |
  |---|---|---|---|
  | `Run Tests` | pytest (full, incl. backup integrity) | **required** | the strong gate |
  | `E2E Functional (Chromium)` | 20-spec product suite | **required** | product coverage |
  | `E2E Backup (Chromium, isolated)` | backup/restore flow | **required** | data-loss-adjacent |
  | `E2E Smoke (Chromium)` | fast nav smoke | **required** | cheap fast signal |
  | `Type Check (tsc blocking + pyright measure-only)` | tsc blocking | **required** | tsc is now a real gate |
  | `Code Linting` | flake8 syntax-level blocking | **required** | catches syntax/undefined-name |
  | `Frontend Build (npm ci + SCSS)` | CSS build | **required** | build must succeed |
  | `Security Audit` | pip-audit | **required** | known-CVE gate |
  | `Dependency Health Check` | outdated/safety, informational | **NOT required** | `continue-on-error` / informational only |

**Scope**
- **In**:
  - Enable branch protection on `main` via `gh api`/REST with:
    - **Required status checks** = the 8 above (exclude `Dependency Health Check`).
    - **Strict** (require branch up-to-date before merge) — *see Open Q2; default proposal: ON.*
    - **Require a pull request before merging** (block direct pushes to `main`).
    - **Required approving review count = 0** (solo owner; can't self-approve).
    - **enforce_admins = false** (documented admin override / emergency hotfix path — plan §7).
    - No required linear history, no required signed commits, no conversation-resolution requirement (solo repo, low value).
  - Document the applied config + the admin-override escape hatch in `docs/ci_cd_phase5/PLANNING.md` + a short note in `docs/CI_CD_IMPROVEMENT_PLAN.md` (§5/§Phase 5 status).
- **Out**:
  - Requiring `Dependency Health Check` (informational).
  - Requiring approvals (would lock out the solo owner).
  - `enforce_admins = true` (removes the emergency escape hatch).
  - Any change to CI job definitions, code, calculations, schema, or app behavior.
  - Cron/scheduled jobs; Phase 4 (deep gate); the `e2e-functional` sharding fast-follow.

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| GitHub repo settings (`main` protection) | new (via `gh api`) | The actual enforcement — applied only after user sign-off |
| `docs/ci_cd_phase5/PLANNING.md` | new | This doc + the exact applied JSON + override instructions |
| `docs/CI_CD_IMPROVEMENT_PLAN.md` | modify | Mark Phase 5 done; record required-check set |

**Effort**: S · **Owner**: Claude (config) + user (sign-off) · **Depends on**: Phases 1/3 gates being green+stable (done)

**Sequence**
1. Confirm the required-check set + protection options with the user (this council + sign-off).
2. Apply protection via `gh api -X PUT repos/.../branches/main/protection` with the agreed JSON.
3. Verify: re-GET the protection, confirm the 8 checks + settings; confirm a direct push to `main` is now rejected and that `gh pr merge --auto` still works on green.
4. Document the applied config + the admin-override path (how the owner bypasses in an emergency: temporarily disable protection or use admin merge).
5. Do **not** require approvals; do **not** enforce_admins. No cron.

**Expected gates** (filled in by `test-strategist`)
- No pytest/e2e change. The verification is operational: protection GET matches intent; a test direct-push is rejected; auto-merge still functions.

**Open questions for the council**
1. **Required-check set:** is excluding only `Dependency Health Check` right? Should `E2E Smoke` be dropped as redundant with `E2E Functional` (which already includes the smoke spec), to avoid requiring a redundant check? Or kept as a fast independent signal?
2. **Strict mode (require up-to-date before merge):** ON adds safety (no stale-base merges) but forces re-runs/rebases and can fight the documented auto-merge workflow on a busy day. For a solo repo, is strict worth the friction, or set OFF?
3. **enforce_admins:** false (owner keeps an emergency override — recommended for a solo local-first repo) vs true (no bypass, maximally strict). Confirm false is acceptable given `main` = production.
4. **Auto-merge interaction:** the owner's documented workflow auto-merges on green CI. Does required-checks + 0-approvals + (strict?) compose cleanly with `gh pr merge --auto --squash`? Any setting that would silently break it?
5. **Direct-push block:** requiring a PR means the owner can no longer `git push` straight to `main`. Confirm that matches the intended workflow (memory says the owner already pushes to branches then PRs).

---

## Reviewer findings

### architecture-reviewer (agent aa00720f82f925dbb) — verdict: Needs revision
- F1/F2/F3 (confirmed, no change): requiring `Type Check` enforces tsc-must-pass while pyright (continue-on-error) stays informational; requiring `Code Linting` gates only E9/F63/F7/F82 (the F401/etc diagnostics are continue-on-error). Both jobs have a genuinely-blocking step, so the required checks are not hollow.
- **F4 (BLOCKING): check-name drift is the real risk.** Protection pins checks by exact `name:` string. The typecheck job was already renamed once (#44), and `Type Check (tsc blocking + pyright measure-only)` WILL change when pyright flips to blocking. Record the 8 required strings verbatim as a copy-paste payload; add the invariant "renaming any required job's `name:` in ci.yml requires re-PUTting protection in the same PR"; note the upcoming pyright-flip rename.
- F6: show the literal `gh api` JSON payload (use `required_status_checks.contexts`) so the exact gate is reviewable before PUT.
- F7/F5 (nit): keeping `E2E Smoke` required is fine; separate the verbatim required-context list from the rationale table to avoid editing a load-bearing string.

### test-strategist (agent ae8ae426da4817259) — verdict: Needs revision
- Confirmed: 8 names match ci.yml char-for-char; `retries:2` is real; **no known-red family is in any required job** (nav-dropdown/visual/geometry excluded; program-backup runs isolated).
- **B1 (BLOCKING): `E2E Backup` is the flakiest required member** (documented sequential-DB flake; isolation is the mitigation). Require it only with a recorded green-run count, or stage it in after the other 7.
- **B2 (BLOCKING): strict mode OFF.** Strict forces every other open PR to re-run the full required set (incl. 3 E2E jobs at retries:2) on every merge — compounding flake exposure and fighting auto-merge — for ~zero value on a solo serial repo.
- **B3 (BLOCKING): document the auto-merge flake-recovery path** (`gh run rerun --failed` → admin-merge escalation), not just an "emergency" override.
- Non-blocking: keep `E2E Smoke` required (cheap independent up-signal); `Run Tests` anchors and transitively covers backup integrity; static jobs won't flap on ubuntu; `Dependency Health Check` is continue-on-error end-to-end so excluding it is correct (requiring it would be a no-op gate).

### product-risk-reviewer (agent a5901ea123e6ed1f6) — verdict: Needs revision (local-first/non-goals CLEAN)
- Lockout reasoning correct but incomplete. **B1 (BLOCKING):** confirm each required-check name against a real green run; require no spec still marked "candidate." **B2 (BLOCKING):** confirm the (now-dropped) `E2E Functional` sharding prerequisite is moot and the job has a green baseline. **B3 (BLOCKING):** the documented convention is `gh pr merge --merge` (true merge commit) + "do not auto-delete branches unless asked" — the plan's `--squash` references drift it; resolve with the owner.
- N1: strict OFF (agrees with test-strategist). N2: set conversation-resolution explicitly OFF in JSON (don't rely on defaults). N3: confirm the owner accepts losing routine direct-push to `main`. N4: enforce_admins=false is the right trade-off for a solo repo (frictionless path goes through checks; bypass is a deliberate admin action). **N5: record the literal emergency-recovery commands + commit the exact applied JSON** so re-enabling after an emergency is copy-paste.
- Non-goal check CLEAN: branch protection is repo governance, introduces no cloud/telemetry/multi-user/auth into the product; reviews=0 actively respects the single-user stance.

---

## Response matrix

| Finding | Reviewer | Disposition | Action in v2 |
|---|---|---|---|
| Check-name drift; pin exact strings + rename-reapply invariant + literal JSON | architecture (F4/F6) | **accept** | v2 includes the verbatim 8-context payload + the invariant + the pyright-flip rename warning. |
| `Type Check`/`Code Linting` enforce the right blocking steps | architecture (F1-F3) | **accept** (confirms) | No change; documented explicitly. |
| Strict mode OFF | test-strategist (B2) + product-risk (N1) | **accept** | `strict: false` in the payload, with rationale. |
| `E2E Backup` flake risk — require only with green evidence | test-strategist (B1) + product-risk (B1) | **accept** | Evidence recorded: `E2E Backup` green on 6 consecutive `main` runs (#39–#44 era) + PR runs #42/#43/#44. Require it. |
| Document auto-merge flake-recovery + emergency escape hatch with literal commands + commit applied JSON | test-strategist (B3) + product-risk (N5) | **accept** | v2 §Recovery section with exact commands + the saved JSON. |
| `--squash`+auto-delete drifts the documented `--merge`+keep-branches convention | product-risk (B3) | **accept — needs owner ruling** | Surface to owner: the actual repo history (#39/#40, pre-session) is squash too, contradicting the memory. Owner picks the convention; update memory + this doc to match. |
| Confirm losing routine direct-push to `main` | product-risk (N3) | **accept — owner confirm** | Surfaced in sign-off. enforce_admins=false keeps the disable-protection escape hatch. |
| enforce_admins = false | product-risk (N4) | **accept — owner confirm** | Recommended; owner confirms main=production self-bypass is acceptable. |
| Required approving reviews = 0 | all | **accept** | Mandatory for solo repo (can't self-approve). |
| Conversation-resolution explicitly OFF | product-risk (N2) | **accept** | Set `false` in payload, not just absent. |
| Keep `E2E Smoke` required; exclude `Dependency Health Check` | test-strategist + architecture | **accept** | Status quo; documented why DHC is structurally non-blockable. |
| No "candidate" spec in required set | product-risk (B2) | **accept** (moot) | Sharding was dropped (single order-safe job); ui-hardening is proven green 3x; fatigue-stage4-smokes/volume-progress excluded. |

---

## Plan v2

**Goal**: Unchanged — enforce the gate via branch protection on `main`.

**Key changes from v1:** strict = **OFF**; the exact 8-context payload is pinned verbatim with a rename-reapply invariant; a §Recovery section with literal emergency commands + the saved JSON; the `--squash`-vs-`--merge` convention is escalated to the owner; E2E Backup is requirable on recorded green evidence.

**Exact required-status-check contexts (verbatim — must match `ci.yml` job `name:` strings):**
```
Run Tests
E2E Functional (Chromium)
E2E Backup (Chromium, isolated)
E2E Smoke (Chromium)
Type Check (tsc blocking + pyright measure-only)
Code Linting
Frontend Build (npm ci + SCSS)
Security Audit
```
Excluded (informational / continue-on-error end-to-end): `Dependency Health Check`.

**Invariant:** renaming any of the 8 job `name:` values in `.github/workflows/ci.yml` requires re-PUTting branch protection in the same PR (exact-string match). Known upcoming break: when pyright flips to blocking, `Type Check (...)` will be renamed → re-apply protection then.

**Applied protection payload (`PUT /repos/avihay1989/Hypertrophy-Toolbox-v3/branches/main/protection`):**
```json
{
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "Run Tests",
      "E2E Functional (Chromium)",
      "E2E Backup (Chromium, isolated)",
      "E2E Smoke (Chromium)",
      "Type Check (tsc blocking + pyright measure-only)",
      "Code Linting",
      "Frontend Build (npm ci + SCSS)",
      "Security Audit"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "required_conversation_resolution": false,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

**Recovery / escape hatch (record in docs):**
- Routine E2E flake stalling auto-merge: `gh run rerun --failed <run-id>` → auto-merge re-evaluates on green.
- Escalation (flake reproduces / CI down): admin-merge `gh pr merge <#> --admin --merge`.
- Full bypass (emergency, CI broken): `gh api -X DELETE repos/avihay1989/Hypertrophy-Toolbox-v3/branches/main/protection` to drop, ship, then re-PUT the saved JSON above to restore.

**Sequence**
1. Owner sign-off on: strict OFF, enforce_admins false, reviews 0, the 8 contexts, losing direct-push, and the merge convention (squash vs merge + branch-delete).
2. `gh api -X PUT .../branches/main/protection` with the payload (with input file).
3. Verify: re-GET protection equals intent; a test direct-push to `main` is rejected; `gh pr merge --auto` still fires on green.
4. Write the applied JSON + recovery commands into `docs/ci_cd_phase5/PLANNING.md`; mark Phase 5 done in `docs/CI_CD_IMPROVEMENT_PLAN.md`; update `feedback_pr_workflow.md` if the owner rules on the merge convention.

**Expected gates:** operational only — protection GET matches; direct push rejected; auto-merge works.

---

## Sign-off

- [x] Every finding has a disposition.
- [x] User approved Plan v2 + governance decisions (2026-06-06): strict=OFF, enforce_admins=false, reviews=0, squash+delete merges, direct-push-to-main blocked accepted.
- [x] Ready to implement (apply branch protection).
