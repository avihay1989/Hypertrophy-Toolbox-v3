---
name: requirements
description: Create or revise only Section 0 of a feature PLANNING.md from a raw request, surface assumptions and blocking questions, record calculation-surface obligations, and stop for Gate 0 owner sign-off.
argument-hint: <raw request and optional docs/<feature>/PLANNING.md path>
---

Create the requirements brief for `$ARGUMENTS`.

1. Read `CLAUDE.md` §1, `docs/ai_workflow/QUALITY_GATE.md` plan-stage routing,
   and `docs/ai_workflow/PLAN_REVIEW_TEMPLATE.md` Section 0.
2. Identify the active `docs/<feature>/PLANNING.md` from the arguments. If no
   path is supplied, derive a short kebab-case feature folder under `docs/`.
3. Inspect only enough repository context to distinguish facts from assumptions.
4. Create or update **Section 0 only** with:
   - the raw request quoted verbatim;
   - the problem stated without prescribing implementation;
   - numbered, observable given/when/then acceptance criteria;
   - in-scope and out-of-scope outcomes;
   - every invented or unverified assumption marked `⚠️`;
   - blocking questions for the owner;
   - a mandatory Calculation surface field: `none`, or the exact functions
     touched, one worked before/after example using the same inputs, and a
     commitment to migration notes plus updated coverage.
   For an ambiguous request that does not yet authorize a calculation change,
   write `none pending Gate 0 clarification`; put possible calculation work in
   an open question, not in the list of touched functions.
5. Preserve any Plan v1/v2, findings, matrices, Evidence, and sign-off history
   already in the file. Never draft or revise the plan itself.
6. Write no file other than the active feature's `PLANNING.md`.
7. Stop at Gate 0. Report the artifact path and request these two explicit owner
   confirmations: the acceptance criteria match intent; all assumptions were
   reviewed and accepted or corrected. Do not proceed to planning.
