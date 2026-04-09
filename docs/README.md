# Hypertrophy Toolbox v3 Documentation

This directory contains the active project docs plus a small archive for historical implementation trackers that are no longer part of the live backlog.

## Active Docs

### Project state
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[DECISIONS.md](DECISIONS.md)** - Data import and normalization rules

### Audits and execution plans
- **[code_cleanup_plan.md](code_cleanup_plan.md)** - Broader cleanup roadmap
- **[CLAUDE_MD_AUDIT.md](CLAUDE_MD_AUDIT.md)** - Live architecture debt snapshot
- **[UI_SCENARIOS_GAP_ANALYSIS.md](UI_SCENARIOS_GAP_ANALYSIS.md)** - UI risk status and deferred items

### Frontend and testing
- **[CSS_OWNERSHIP_MAP.md](CSS_OWNERSHIP_MAP.md)** - Current CSS loading and ownership map
- **[E2E_TESTING.md](E2E_TESTING.md)** - Current Playwright inventory and run commands

### Feature docs
- **[FILTER_VIEW_MODE.md](FILTER_VIEW_MODE.md)** - Simple vs scientific muscle naming mode
- **[program_backups.md](program_backups.md)** - Program backup and restore feature
- **[muscle_selector.md](muscle_selector.md)** - Muscle selector component notes
- **[muscle_selector_vendor.md](muscle_selector_vendor.md)** - Vendor SVG attribution

## Archive

These files are kept for historical reference and implementation context, but they should not be treated as active backlog:

- **[archive/MISSING_TESTS_CHECKLIST.md](archive/MISSING_TESTS_CHECKLIST.md)** - Historical missing-tests tracker
- **[archive/MISSING_TESTS_PART2.md](archive/MISSING_TESTS_PART2.md)** - Follow-up historical test tracker
- **[archive/PUPPETEER_TEST_FINDINGS.md](archive/PUPPETEER_TEST_FINDINGS.md)** - Earlier Puppeteer findings
- **[archive/SUPERSET_FEATURE.md](archive/SUPERSET_FEATURE.md)** - Completed superset feature implementation notes
- **[archive/PLAN_GENERATOR_IMPLEMENTATION.md](archive/PLAN_GENERATOR_IMPLEMENTATION.md)** - Completed starter-plan implementation tracker
- **[archive/DOCS_AUDIT_PLAN.md](archive/DOCS_AUDIT_PLAN.md)** - Archived docs/code audit rollout record and Tier completion snapshot

## Quick Pointers

- Check [CSS_OWNERSHIP_MAP.md](CSS_OWNERSHIP_MAP.md) before changing styles or template CSS loading.
- Check [E2E_TESTING.md](E2E_TESTING.md) before changing Playwright coverage or runner config.
- Check [archive/DOCS_AUDIT_PLAN.md](archive/DOCS_AUDIT_PLAN.md) before re-opening completed audit tiers or reviewing the archived rollout record.

Last updated: 2026-04-09
