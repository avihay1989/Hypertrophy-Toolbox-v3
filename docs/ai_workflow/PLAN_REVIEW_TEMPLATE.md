# Plan Review Template

*Copy this file into the workstream's planning doc (e.g. `docs/<feature>/PLANNING.md`) and fill in each section. Used by [`.claude/commands/council-plan.md`](../../.claude/commands/council-plan.md). Implements [`.claude/SHARED_PLAN.md`](../../.claude/SHARED_PLAN.md) Tier 2.2 Appendix A2.2.*

---

# Plan Review — <feature / issue>

## Section 0 — Requirements Brief

*Required only for large, ambiguous, or new-workflow tasks under
[QUALITY_GATE.md](QUALITY_GATE.md#plan-stage-routing). Skip this section for trivial
and medium work unless unresolved requirements make Gate 0 useful.*

**Raw request** (verbatim)
> <copy the user's request without paraphrasing>

**Problem**
<what outcome is missing or failing, without proposing the implementation>

**Acceptance criteria**
1. Given <context>, when <action>, then <observable outcome>.
2. <additional criteria>

**Calculation surface**
- `none`; or
- Functions changed: `<module.function>`
- Worked example: before `<inputs → output>`; after `<same inputs → output>`
- Migration notes: <commitment for the PR description and updated test coverage>

**In scope**
- <included outcome or artifact>

**Out of scope / non-goals**
- <explicit exclusion>

**Assumptions made**
- ⚠️ <assumption that could represent invented scope>

**Open questions for the user**
- <blocking decision, or `none`>

### Section 0 sign-off — GATE 0
- [ ] User confirms the acceptance criteria match intent.
- [ ] User reviewed the assumptions and corrected or accepted each one.
- [ ] Blocking questions are answered.

---

## Plan v1

**Goal**: <one sentence: what user-visible outcome this delivers>

**Scope**
- **In**: <bulleted artifacts / changes>
- **Out**: <bulleted explicit non-goals for this iteration>

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| `routes/<X>.py` | new / modify | <one line> |
| `utils/<X>.py` | new / modify | <one line> |
| `templates/<X>.html` | new / modify | <one line> |
| `tests/test_<X>_routes.py` | new / modify | <route HTTP tests> |
| `tests/test_<X>.py` | new / modify | <util unit tests> |

**Effort**: S / M / L · **Owner**: <agent or human> · **Depends on**: <other tickets / tiers>

**Sequence**
1. <step>
2. <step>
3. <step>

**Expected gates** (filled in by `test-strategist`)
- pytest: <files>
- e2e: <specs>
- other: <`/build-css`, `/verify-suite`, etc.>

---

## Agent provenance

*Required for every council run. The manager records each agent ID returned by its `Agent(...)` call and supplies the `product-manager` its own ID back, because an agent cannot know its own ID. The `product-manager` stamps the IDs the manager supplies — **never invent an ID**, never rerun completed council work to manufacture continuity, and record an unrecoverable ID as an evidence gap.*

| Role | Agent ID | Notes |
|---|---|---|
| `product-manager` — Plan v1 | `<id>` / `unknown — not recorded` | Author of Section 0 (if any) and Plan v1. |
| `product-manager` — response matrix + Plan v2 | `<id>` / `unknown — not recorded` | Author of the matrix and Plan v2. |
| `architecture-reviewer` | `<id>` | Step 2 reviewer. |
| `test-strategist` | `<id>` | Step 2 reviewer. |
| `product-risk-reviewer` | `<id>` | Step 2 reviewer. |

**Same product-manager resumed for the matrix + Plan v2?** `yes` (resumed via `SendMessage` to the Plan v1 agent ID) / `no` (a different or fresh `product-manager` wrote them — state which, and why).

**Evidence gap** — fill in only when continuity cannot be established; otherwise write `none`:
> <what could not be established (e.g. the Plan v1 product-manager's ID was never recorded / it was spawned in a prior session / `SendMessage` was unavailable), and what was done instead (e.g. a fresh `product-manager` read the artifact directly, no relay). No ID was invented and no completed council work was rerun.>

---

## Reviewer findings

*Run [`.claude/commands/council-plan.md`](../../.claude/commands/council-plan.md) step 2 — three agents in parallel. Paste each agent's output verbatim below. Do not summarize. Head each section with the reviewer's agent ID, matching the Agent provenance table.*

### architecture-reviewer (agent `<id>`)
<findings>

### test-strategist (agent `<id>`)
<findings>

### product-risk-reviewer (agent `<id>`)
<findings>

---

## Response matrix

Every finding gets a row. "Defer" requires a one-line reason and a note in `MASTER_HANDOVER.local.md`.

| Finding | Reviewer | Disposition | Action in v2 |
|---|---|---|---|
| <one-line summary> | architecture-reviewer | accept / reject / defer | <change applied in Plan v2, or rationale> |
| <one-line summary> | test-strategist | accept / reject / defer | <change> |
| <one-line summary> | product-risk-reviewer | accept / reject / defer | <change> |

---

## Plan v2

*Re-state the plan reflecting accepted findings. If v2 equals v1, keep this section and write "No changes from v1 — all findings rejected or non-blocking." so the audit trail is explicit.*

**Goal**: <unchanged or revised>

**Scope**
- **In**: <revised>
- **Out**: <revised>

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| ... | ... | ... |

**Sequence**
1. <revised step>

---

## Sign-off

- [ ] Gate 0 complete when required by planning size; otherwise marked not applicable.
- [ ] Every finding has a disposition.
- [ ] Agent provenance complete — both `product-manager` IDs, same-PM-resumed yes/no, the three reviewer IDs, and an evidence-gap line (or `none`).
- [ ] User approved Plan v2.
- [ ] Ready to implement — proceed to code, then `/unslop` or `/verify-and-polish` for the diff-time gate.

---

## See also
- [`.claude/commands/council-plan.md`](../../.claude/commands/council-plan.md) — how to run the council.
- [QUALITY_GATE.md](QUALITY_GATE.md) — change-type → required tests/reviewers.
- [`.claude/agents/architecture-reviewer.md`](../../.claude/agents/architecture-reviewer.md), [`.claude/agents/test-strategist.md`](../../.claude/agents/test-strategist.md), [`.claude/agents/product-risk-reviewer.md`](../../.claude/agents/product-risk-reviewer.md) — reviewer charters.
