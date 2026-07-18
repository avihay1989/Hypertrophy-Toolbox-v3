---
description: Plan-review council — Plan v1 → 3 reviewers in parallel (architecture / test-strategist / product-risk) → response matrix → Plan v2.
---

Run the plan-review council from [`.claude/SHARED_PLAN.md`](../../.claude/SHARED_PLAN.md) Tier 2.2 before committing to a non-trivial implementation. Catches design-level mistakes **before** code is written, when revising is cheap.

Planning-size routing is canonical in
[QUALITY_GATE.md](../../docs/ai_workflow/QUALITY_GATE.md#plan-stage-routing). When that
table requires Gate 0, complete and obtain sign-off on the template's Section 0 before
Step 1 below. Trivial and medium tasks skip Section 0 unless unresolved requirements
justify escalating to Gate 0.

## When to use
- New feature with cross-cutting impact (new blueprint, new table, new calculation).
- Refactor that touches a calculation engine (`utils/effective_sets.py`, `utils/weekly_summary.py`, `utils/session_summary.py`, `utils/progression_plan.py`, `utils/volume_*.py`, `utils/fatigue.py`).
- Schema change.
- Any plan that mentions a non-goal (auth, cloud sync, telemetry) — the council will block early.

## When NOT to use
- One-line bug fix with an obvious test target.
- Comment / typo / product-docs-only edit (i.e. `docs/**` excluding `docs/ai_workflow/**`). Edits to `.claude/**`, root `CLAUDE.md`, folder `CLAUDE.md`, or `docs/ai_workflow/**` are agent config — they change agent behavior and may still warrant the council.
- A plan small enough that targeted review during implementation (`/unslop` or `/verify-and-polish`) covers it.

## Steps

> **Ownership note.** The manager is read-only and performs **no** document writes in any step below. After Gate 0 it delegates every council-document write (Plan v1, the response matrix, Plan v2) to `product-manager`, which owns writes to the active `docs/<feature>/PLANNING.md`. The manager orchestrates: it classifies, delegates drafting, spawns the reviewers, and synthesizes proposed dispositions.

> **Agent-ID provenance note (mechanism).** An agent cannot know its own ID — the ID is returned to the **manager** when the `Agent(...)` call returns. So the manager must **record** every council agent's returned ID and **hand the `product-manager` its own ID back to it** so the `product-manager` can stamp it into the artifact. Every council run fills the **Agent provenance** block of [PLAN_REVIEW_TEMPLATE.md](../../docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md): the PM ID for Plan v1, the PM ID for the matrix + Plan v2, whether the same PM was resumed, and the three reviewer IDs.

1. **Draft Plan v1.** After any size-required Gate 0 sign-off, the read-only manager delegates Plan v1 drafting to `product-manager`, which writes Plan v1 into `docs/<feature>/PLANNING.md` (or wherever the workstream's planning doc lives) using the [docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md](../../docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md) shell. Include: goal, scope (in/out), artifact list with paths, effort, sequence, expected gates.

   **ID stamping.** The PM's agent ID does not exist until the `Agent(product-manager, ...)` call **returns** — i.e. after Plan v1 is already written — so the initial brief can never carry it. The manager **records the returned agent ID** and keeps it for the whole council run, then **supplies it back to that same agent** in a follow-up `SendMessage`, instructing it to stamp the ID into the artifact's **Agent provenance → `product-manager` — Plan v1** row. If `SendMessage` is unavailable, the stamp is deferred: the Step-4 `product-manager` writes the Plan v1 ID that the manager recorded and supplies. Either way the `product-manager` writes only the ID the manager supplies; it never guesses one.

2. **Run the three reviewers in parallel.** The manager sends a single message containing three Agent tool calls:
   - `subagent_type: architecture-reviewer` — module boundaries, blueprint/test registration, schema/API contracts.
   - `subagent_type: test-strategist` — pytest/e2e/visual gates and coverage gaps.
   - `subagent_type: product-risk-reviewer` — calculation semantics, local-first invariants, terminology, non-goals.

   Brief each agent the same way: paste the Plan v1 (or its location) and ask them to review per their charter. Do not summarize the plan for them — they read it cold.

   The manager records all three returned agent IDs and passes them to the `product-manager` in Step 4 for stamping alongside each reviewer's verbatim findings.

3. **Synthesize proposed dispositions.** The manager collates the reviewers' findings and proposes a disposition for each, ready for the owner to confirm at Gate 1. Use the template's table:

   | Finding | Reviewer | Disposition | Action in v2 |
   |---|---|---|---|
   | <summary> | architecture-reviewer | accept / reject / defer | <change> |

   Every finding gets a disposition. "Defer" is allowed only with a one-line reason and a follow-up note in `MASTER_HANDOVER.local.md`. The manager itself writes nothing into the doc.

4. **Write the response matrix and Plan v2.** The manager resumes the **same** `product-manager` — by `SendMessage` to the agent ID recorded in Step 1 — which writes the synthesized response matrix and Plan v2 into the same doc, reflecting accepted findings. Mark rejected findings inline so the rationale survives.

   **ID stamping + continuity.** In the resume message the manager re-supplies the PM's agent ID and the three reviewer IDs, and instructs the `product-manager` to complete the artifact's **Agent provenance** block:
   - **PM agent ID (matrix + Plan v2)** — the ID of the agent doing this write.
   - **Same PM resumed?** — `yes` when the Step-1 PM was resumed via `SendMessage`; `no` when a different or fresh `product-manager` performed this write (state which, and why).
   - **Reviewer agent IDs** — the three IDs from Step 2.

   If the Step-1 PM cannot be resumed, the manager instructs a **fresh** `product-manager` to read the artifact directly (no relay) and to fill the **Evidence gap** line of the provenance block. That is a reportable gap, not a failure to hide. **Scope the gap to what is actually missing — do not discard evidence you have:**
   - **ID recorded, resume impossible** (`SendMessage` unavailable, or the agent's session ended): the manager still supplies the recorded Plan v1 ID and the fresh `product-manager` **still stamps it**. Set **Same PM resumed? = no** and scope the Evidence gap to **continuity only**. Writing `unknown — not recorded` for an ID that *was* recorded destroys real evidence and is forbidden.
   - **ID never recorded** (e.g. the PM was spawned in a prior session and its ID was not captured): stamp `unknown — not recorded`, set **Same PM resumed? = no**, and record an Evidence gap covering **both** the missing ID and the broken continuity.

   **Hard rules (all steps).**
   - **Never invent an agent ID.** An unknown ID is written as `unknown — not recorded`, never as a plausible-looking string.
   - **Never rerun completed council work** (Plan v1, a reviewer pass, or Plan v2) merely to manufacture continuity evidence. Rerun only when the plan's content genuinely changed.
   - **An unrecoverable ID is reported as an evidence gap**, in the artifact's Agent provenance block and in the manager's status report. It is never papered over, and continuity is never claimed that did not occur.

5. **Get user sign-off** on Plan v2 before implementation. The Sign-off checklist in the template gates this:
   - [ ] Gate 0 complete when required by planning size; otherwise marked not applicable.
   - [ ] Every finding has a disposition.
   - [ ] Agent provenance block complete — PM IDs (Plan v1; matrix + Plan v2), same-PM-resumed yes/no, three reviewer IDs, and an evidence-gap line where continuity could not be established (or `none`). A blank evidence-gap line does not pass sign-off.
   - [ ] User approved Plan v2.
   - [ ] Ready to implement.

6. **Implement.** During implementation, use [`.claude/commands/unslop.md`](unslop.md) or [`.claude/commands/verify-and-polish.md`](verify-and-polish.md) for the post-code gate — those run `code-reviewer` + `unslop-reviewer` against the staged diff. The council does not re-run after code lands; the diff-time gates do.

## Failure handling
- A reviewer returns "blocking" → revise Plan v1, re-run that reviewer (the other two can stay if their inputs didn't change).
- All three return "sound" → still write a Plan v2 (even if it equals v1) so the response matrix exists for future readers.
- Reviewers disagree → user decides; record both findings + the chosen action.

## Cost note
Three parallel reviewers triples the agent-call cost vs. a single review. Reserve `/council-plan` for plans where the cost of *building the wrong thing* dominates the cost of three reviews. For routine plans, skip straight to implementation + `/unslop`.

## See also
- [docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md](../../docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md) — the template Plan v1/v2 + matrix lives in.
- [docs/ai_workflow/QUALITY_GATE.md](../../docs/ai_workflow/QUALITY_GATE.md) — change-type → gates the test-strategist applies.
- `.claude/agents/architecture-reviewer.md`, `.claude/agents/test-strategist.md`, `.claude/agents/product-risk-reviewer.md` — reviewer charters.
- [`.claude/commands/unslop.md`](unslop.md), [`.claude/commands/verify-and-polish.md`](verify-and-polish.md) — diff-time gates that run after `/council-plan` is done.
