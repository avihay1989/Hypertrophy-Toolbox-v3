# CLAUDE.md Audit - Live Architecture Debt

Last validated: 2026-04-08

This file intentionally tracks only unresolved, repo-verified architecture debt. Historical provenance and resolved findings were trimmed out during the Tier 1 docs cleanup.

## 1. Database Access Still Bypassing `DatabaseHandler`

These are the current non-helper call sites that still matter:

- `utils/user_selection.py:34` - direct `sqlite3.connect(...)` read path
- `utils/volume_export.py:8` - raw `get_db_connection()` write path
- `routes/volume_splitter.py:154`
- `routes/volume_splitter.py:199`
- `routes/volume_splitter.py:234`

## 2. Response Contract Standardization Is Still Deferred

The current route layer still has mixed response contracts, and some of them are live frontend dependencies rather than cleanup-only inconsistencies:

- `routes/progression_plan.py` still returns bare arrays/objects and includes a redirect-based fetch path
- `routes/session_summary.py` still returns top-level `session_summary`
- `routes/weekly_summary.py` still returns top-level `weekly_summary`
- `routes/volume_splitter.py` still returns several ad hoc shapes such as top-level `results`, direct plan objects, and `success` flags

This debt should stay explicit until the frontend consumers and tests migrate in the same change set.

## 3. No Longer Tracked Here

The following were deliberately removed from this summary because they were resolved or not re-verified as live debt:

- historical file-read provenance
- route/utils `print()` cleanup completed in Tier 2 on 2026-04-08
- summary-page raw/effective display issues that were already fixed
- stale duplicated-CSS claims that were not validated as active architecture debt
