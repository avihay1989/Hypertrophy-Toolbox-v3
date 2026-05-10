# Plan Review Template

*Copy this file into the workstream's planning doc (e.g. `docs/<feature>/PLANNING.md`) and fill in each section. Used by [`.claude/commands/council-plan.md`](../../.claude/commands/council-plan.md). Implements [`.claude/SHARED_PLAN.md`](../../.claude/SHARED_PLAN.md) Tier 2.2 Appendix A2.2.*

---

# Plan Review — <feature / issue>

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
| `tests/test_<X>.py` | new / modify | <one line> |

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

## Reviewer findings

*Run [`.claude/commands/council-plan.md`](../../.claude/commands/council-plan.md) step 2 — three agents in parallel. Paste each agent's output verbatim below. Do not summarize.*

### architecture-reviewer
<findings>

### test-strategist
<findings>

### product-risk-reviewer
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

- [ ] Every finding has a disposition.
- [ ] User approved Plan v2.
- [ ] Ready to implement — proceed to code, then `/unslop` or `/verify-and-polish` for the diff-time gate.

---

## See also
- [`.claude/commands/council-plan.md`](../../.claude/commands/council-plan.md) — how to run the council.
- [QUALITY_GATE.md](QUALITY_GATE.md) — change-type → required tests/reviewers.
- [`.claude/agents/architecture-reviewer.md`](../../.claude/agents/architecture-reviewer.md), [`.claude/agents/test-strategist.md`](../../.claude/agents/test-strategist.md), [`.claude/agents/product-risk-reviewer.md`](../../.claude/agents/product-risk-reviewer.md) — reviewer charters.
