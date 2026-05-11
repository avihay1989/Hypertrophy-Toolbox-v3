# Exercise Import Decisions

This document captures the non-negotiable rules for the Excel to SQLite merge utility.

- **Normalization rules**: Trim leading/trailing whitespace, collapse internal whitespace to a single space, and normalize endash/emdash characters to the ASCII hyphen before any comparisons.
- **Exact name matching**: Import logic only merges rows whose normalized `exercise_name` strings are identical. No fuzzy, partial, or substring matching is permitted.
- **Empty cell handling**: Blank strings and missing values coming from Excel are treated as nulls and never overwrite populated database fields.
- **Case sensitivity flag**: `--nocase` enforces a `COLLATE NOCASE` uniqueness constraint; when omitted, uniqueness is strictly case-sensitive.
- **Update-only flag**: `--update-only` converts unmatched Excel rows into skipped entries instead of inserts.
- **Default paths**: Unless overridden, the tool reads from `data/exercises.xlsx`, writes to `data/database.db`, and emits Markdown artifacts in `docs/`.

## Data semantics

- Equipment semantics: The equipment field intentionally includes both gear (Barbell, Dumbbells, …) and categories (Yoga, Recovery, Stretches, Cardio). These are first-class filter values.
- Enumerations: Incoming `force`, `mechanic`, and `difficulty` values are canonicalized to `Push`/`Pull`/`Hold`, `Compound`/`Isolation`, and `Beginner`/`Intermediate`/`Advanced` respectively before merging.

## ADR Log

New cross-cutting or durable project decisions should be added here as lightweight ADRs. Use the next sequential number, keep the original ADR unchanged after acceptance, and supersede it with a new ADR if the decision changes.

### ADR-001: Exercise import uses exact normalized name matching
- **Date**: 2026-05-11
- **Status**: accepted
- **Context**: The exercise import utility merges external Excel rows into the local SQLite exercise table. Fuzzy or partial matching could accidentally merge distinct movements and corrupt the exercise catalog.
- **Decision**: Import matching is based only on identical normalized `exercise_name` strings. Empty Excel cells never overwrite populated database values, and `--update-only` skips unmatched rows instead of inserting them.
- **Consequences**: Imports are predictable and auditable, but users must clean source exercise names before import when they expect two rows to match.

### ADR-NNN: <title>
- **Date**: YYYY-MM-DD
- **Status**: proposed | accepted | superseded by ADR-MMM
- **Context**: <forces at play>
- **Decision**: <what we chose>
- **Consequences**: <what becomes easier / harder>
