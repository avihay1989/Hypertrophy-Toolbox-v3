---
description: Plan-review council — Plan v1 → 3 reviewers in parallel (architecture / test-strategist / product-risk) → response matrix → Plan v2.
---

Run the plan-review council from [`.claude/SHARED_PLAN.md`](../../.claude/SHARED_PLAN.md) Tier 2.2 before committing to a non-trivial implementation. Catches design-level mistakes **before** code is written, when revising is cheap.

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

1. **Draft Plan v1.** Write it into `docs/<feature>/PLANNING.md` (or wherever the workstream's planning doc lives) using the [docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md](../../docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md) shell. Include: goal, scope (in/out), artifact list with paths, effort, sequence, expected gates.

2. **Run the three reviewers in parallel.** Send a single message containing three Agent tool calls:
   - `subagent_type: architecture-reviewer` — module boundaries, blueprint/test registration, schema/API contracts.
   - `subagent_type: test-strategist` — pytest/e2e/visual gates and coverage gaps.
   - `subagent_type: product-risk-reviewer` — calculation semantics, local-first invariants, terminology, non-goals.

   Brief each agent the same way: paste the Plan v1 (or its location) and ask them to review per their charter. Do not summarize the plan for them — they read it cold.

3. **Collate findings into the response matrix.** Use the template's table:

   | Finding | Reviewer | Disposition | Action in v2 |
   |---|---|---|---|
   | <summary> | architecture-reviewer | accept / reject / defer | <change> |

   Every finding gets a disposition. "Defer" is allowed only with a one-line reason and a follow-up note in `MASTER_HANDOVER.local.md`.

4. **Write Plan v2** in the same doc, reflecting accepted findings. Mark rejected findings inline so the rationale survives.

5. **Get user sign-off** on Plan v2 before implementation. The Sign-off checklist in the template gates this:
   - [ ] Every finding has a disposition.
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
