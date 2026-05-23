# AI Workflow Index

*Navigation map for AI agents and humans working on this repo. The Master Handover is the entry point; everything else here is reference.*

## Spine (read first)
- [Master Handover](../MASTER_HANDOVER.md) — canonical current state
- root [CLAUDE.md](../../CLAUDE.md) — operational guidance
- [`.claude/rules/`](../../.claude/rules/) — subsystem rules (auto-loaded by Claude Code on matching paths)
- `.claude/SHARED_PLAN.md` — optional local planning/audit trail if present; Tier 1 artifacts here should stand on their own

## Active feature plans
- [Fatigue meter](../fatigue_meter/PLANNING.md) — closed; Phase 1 + Stage 4 shipped (Stage 4 closed 2026-05-20 with no threshold changes). Phase 2 entry remains a separate owner decision.
- [workout.cool integration](../workout_cool_integration/PLANNING.md) — §3 + §3.6 + §4 + §4.6 + §5 all shipped (§3.6 Profile bodymap landed 2026-05-23, `18ad223`; §5 first curated batch landed 2026-05-22, `cf21191`)
- [YouTube reference videos](../workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md) — closed 2026-05-23 (`cf21191` 36 rows + `ff244aa` +20 rows = **56 curated rows**); long tail uses the search fallback by design
- [User profile](../user_profile/PLANNING.md) — questionnaire + bodymap + insights card + Body Composition display hooks (#17/#18) all shipped
- [Body Composition Issue #21](../body_composition/development_issues.md) — Resolved 2026-05-23; PR #31 (`20b4b24`) + PR #32 (`94482d7`) + Profile hooks (`de3e4d0`)

## History & decisions
- [CHANGELOG](../CHANGELOG.md)
- [DECISIONS](../DECISIONS.md) — durable project choices and lightweight ADRs
- [Documentation Retention](DOC_RETENTION.md) — when to keep, archive, or delete docs
- [CLAUDE.md audit](../CLAUDE_MD_AUDIT.md)
- [E2E testing notes](../E2E_TESTING.md)
- [CSS ownership map](../CSS_OWNERSHIP_MAP.md)
- [Volume taxonomy audit](../VOLUME_TAXONOMY_AUDIT.md)

## Workflow artifacts
- [Quality Gate](QUALITY_GATE.md) — change-type → required tests/reviewers map
- [Autonomy Model](AUTONOMY.md) — Codex/Claude approval, sandbox, worktree, and review boundaries
- Folder orientation maps (Claude Code auto-loads on path entry):
  - [routes/CLAUDE.md](../../routes/CLAUDE.md)
  - [utils/CLAUDE.md](../../utils/CLAUDE.md)
  - [tests/CLAUDE.md](../../tests/CLAUDE.md)
  - [e2e/CLAUDE.md](../../e2e/CLAUDE.md)
  - [templates/CLAUDE.md](../../templates/CLAUDE.md)
  - [static/js/CLAUDE.md](../../static/js/CLAUDE.md)
- [Plan Review Template](PLAN_REVIEW_TEMPLATE.md) — Plan v1 → council findings → response matrix → Plan v2 (used by `/council-plan`)
- Slash commands: `/handover`, `/unslop`, `/verify-and-polish`, `/council-plan` (in `.claude/commands/`)
- Agents (diff-time): `code-reviewer`, `unslop-reviewer` (in `.claude/agents/`)
- Agents (plan-time, council): `architecture-reviewer`, `test-strategist`, `product-risk-reviewer` (in `.claude/agents/`)

## Baselines (gitignored, generated locally)
- `baseline_pytest.txt`, `baseline_e2e.txt` — last full-suite outputs; not in git
